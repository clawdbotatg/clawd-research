#!/usr/bin/env python3
"""simple-eval: one cheap score for any LLM or harness. See PLAN.md.

Targets:
  --base-url URL --model NAME [--api-key-env VAR] [--auth bearer|xapikey]
      any OpenAI-compatible endpoint (ollama, bankr, openrouter, ...)
  --cmd 'claude -p --model haiku'
      any CLI harness; prompt goes to stdin, response read from stdout.
      CLAUDECODE / CLAUDE_CODE_* / ANTHROPIC_API_KEY are scrubbed from the
      child env (nested-claude embedded-mode trap).
  --self-test
      grade every task's bundled reference answer (zero tokens; must be 100%).

Examples:
  python3 run_eval.py --self-test
  python3 run_eval.py --name qwen3-coder --base-url https://llm.bankr.bot/v1 \
      --model qwen3-coder --api-key-env BANKR_API_KEY --auth xapikey
  python3 run_eval.py --name fable --cmd 'claude -p --model claude-fable-5' --concurrency 4
"""
import argparse
import concurrent.futures
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS_DIR = HERE / "tasks"
RESULTS_DIR = HERE / "results"

# ---------------------------------------------------------------- helpers

def norm(t, casefold=True):
    """Normalize a short answer: collapse whitespace, strip fences/quotes/trailing dot."""
    t = (t or "").strip()
    t = t.strip("`").strip()
    t = re.sub(r"\s+", " ", t)
    t = t.strip().rstrip(".").strip()
    t = t.strip("\"'").strip()
    return t.casefold() if casefold else t

def lines(r):
    return [l.strip() for l in (r or "").strip().splitlines() if l.strip()]

def paras(r):
    return [p.strip() for p in re.split(r"\n\s*\n", (r or "").strip()) if p.strip()]

def sents(t):
    parts = re.split(r"[.!?]+(?:\s+|$)", (t or "").strip())
    return [p.strip() for p in parts if re.search(r"\w", p)]

def words(t):
    return re.findall(r"[A-Za-z0-9']+", t or "")

def acro(ls):
    out = []
    for ln in ls:
        c = next((c for c in ln if c.isalpha()), "")
        out.append(c.upper())
    return "".join(out)

def ans_line(r):
    """Content after the last 'Answer:' marker, else the last non-empty line."""
    found = None
    for l in (r or "").strip().splitlines():
        m = re.match(r"\s*[*#>\s]*answer\s*[:=]\s*(.+?)\s*$", l, re.I)
        if m:
            found = m.group(1)
    if found is None:
        m = re.search(r"answer\s*[:=]\s*(.+?)\s*$", r or "", re.I | re.M)
        if m:
            found = m.group(1)
    if found is not None:
        return found.strip().strip("*").strip()
    ls = lines(r)
    return ls[-1] if ls else ""

def extract_num(r):
    a = ans_line(r)
    nums = re.findall(r"-?\$?\d[\d,]*\.?\d*", a)
    if nums:
        return float(nums[0].replace("$", "").replace(",", ""))
    nums = re.findall(r"-?\$?\d[\d,]*\.?\d*", r or "")
    if nums:
        return float(nums[-1].replace("$", "").replace(",", ""))
    return None

def jload(r):
    r = (r or "").strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", r, re.S)
    for c in ([fenced[-1]] if fenced else []) + [r]:
        c = c.strip()
        try:
            return json.loads(c)
        except Exception:
            pass
        for op, cl in (("{", "}"), ("[", "]")):
            i, j = c.find(op), c.rfind(cl)
            if 0 <= i < j:
                try:
                    return json.loads(c[i : j + 1])
                except Exception:
                    pass
    raise ValueError("no JSON found in response")

def extract_code(r):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", r or "", re.S)
    if blocks:
        for b in reversed(blocks):
            if "def " in b:
                return b
        return blocks[-1]
    return r or ""

def jmatch(exp, got):
    """expected-vs-got JSON: numbers ~equal, '~str' = substring, dicts allow extra keys."""
    if isinstance(exp, bool):
        return isinstance(got, bool) and exp == got
    if isinstance(exp, (int, float)):
        return isinstance(got, (int, float)) and not isinstance(got, bool) and abs(exp - got) < 1e-6
    if isinstance(exp, str):
        if not isinstance(got, str):
            return False
        if exp.startswith("~"):
            return exp[1:].casefold() in got.casefold()
        return norm(exp) == norm(got)
    if isinstance(exp, list):
        return isinstance(got, list) and len(exp) == len(got) and all(jmatch(e, g) for e, g in zip(exp, got))
    if isinstance(exp, dict):
        return isinstance(got, dict) and all(k in got and jmatch(v, got[k]) for k, v in exp.items())
    if exp is None:
        return got is None
    return exp == got

# ---------------------------------------------------------------- graders

def grade(task, resp):
    g = task["grader"]
    t = g["type"]
    try:
        if t == "numeric":
            v = extract_num(resp)
            ok = v is not None and abs(v - g["expect"]) <= g.get("tol", 1e-6)
            return ok, f"got {v}"
        if t == "exact":
            cf = not g.get("case_sensitive", False)
            cands = [norm(resp, cf)]
            ls = lines(resp)
            if ls:
                cands.append(norm(ls[-1], cf))
            cands.append(norm(ans_line(resp), cf))
            exp = norm(g["expect"], cf)
            return exp in cands, f"got {cands[-1][:80]!r}"
        if t == "regex":
            scope = ans_line(resp) if g.get("on", "answer") == "answer" else resp
            flags = 0 if g.get("case_sensitive") else re.I
            return bool(re.search(g["pattern"], scope, flags)), f"answer {scope[:80]!r}"
        if t == "json":
            got = jload(resp)
            ok = jmatch(g["expect"], got)
            return ok, "" if ok else f"got {json.dumps(got)[:120]}"
        if t == "pycheck":
            env = {
                "r": resp, "re": re, "lines": lines, "sents": sents, "words": words,
                "paras": paras, "norm": norm, "jload": jload, "ans": ans_line,
                "acro": acro, "num": extract_num, "len": len, "all": all, "any": any,
                "sorted": sorted, "set": set, "isinstance": isinstance, "int": int,
                "float": float, "str": str, "bool": bool, "next": next,
                "__builtins__": {},
            }
            ok = bool(eval(g["expr"], env))
            return ok, "" if ok else f"failed: {resp[:100]!r}"
        if t == "pytests":
            code = extract_code(resp)
            src = code + "\n\n" + g["tests"] + "\nprint('SIMPLE_EVAL_OK')\n"
            fd, path = tempfile.mkstemp(suffix=".py")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(src)
                p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=20)
                ok = p.returncode == 0 and "SIMPLE_EVAL_OK" in p.stdout
                detail = "" if ok else (p.stderr.strip().splitlines()[-1][:140] if p.stderr.strip() else f"exit {p.returncode}")
                return ok, detail
            finally:
                os.unlink(path)
        raise ValueError(f"unknown grader type {t}")
    except Exception as e:  # noqa: BLE001 — a grading crash is a task failure
        return False, f"{type(e).__name__}: {e}"[:140]

# ---------------------------------------------------------------- targets

SCRUB = re.compile(r"^(CLAUDECODE$|CLAUDE_CODE_|ANTHROPIC_API_KEY$|CLAUDE_AGENT_)")

class OpenAITarget:
    def __init__(self, base_url, model, api_key, auth):
        u = base_url.rstrip("/")
        self.url = u if u.endswith("/chat/completions") else u + "/chat/completions"
        self.model = model
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            if auth == "xapikey":
                self.headers["X-API-Key"] = api_key
            else:
                self.headers["Authorization"] = f"Bearer {api_key}"
        self.desc = f"openai:{self.url}:{model}"

    def ask(self, prompt, max_tokens):
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }).encode()
        last = None
        backoffs = [5, 10, 20, 40, 60]
        for attempt in range(len(backoffs) + 1):
            req = urllib.request.Request(self.url, data=body, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=240) as resp:
                    data = json.load(resp)
                content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
                usage = data.get("usage") or {}
                return content, usage
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}: {e.read()[:200]!r}"
                if e.code in (408, 429, 500, 502, 503, 504) and attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    continue
                raise RuntimeError(last) from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = str(e)
                if attempt < len(backoffs):
                    time.sleep(backoffs[attempt])
                    continue
                raise RuntimeError(last) from None
        raise RuntimeError(last or "exhausted retries")

class CmdTarget:
    def __init__(self, cmd):
        self.cmd = cmd
        self.desc = f"cmd:{cmd}"
        self.env = {k: v for k, v in os.environ.items() if not SCRUB.match(k)}

    def ask(self, prompt, max_tokens):
        p = subprocess.run(
            self.cmd, shell=True, input=prompt, capture_output=True, text=True,
            timeout=900, env=self.env, cwd=str(HERE),
        )
        if p.returncode != 0:
            raise RuntimeError(f"cmd exit {p.returncode}: {(p.stderr or p.stdout)[:300]}")
        return p.stdout.strip(), {}

# ---------------------------------------------------------------- run

def load_tasks(category=None, limit=None):
    doc = (TASKS_DIR / "context_doc.txt").read_text() if (TASKS_DIR / "context_doc.txt").exists() else ""
    tasks = []
    for f in sorted(TASKS_DIR.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            t["prompt"] = t["prompt"].replace("{{DOC}}", doc)
            tasks.append(t)
    if category:
        tasks = [t for t in tasks if t["category"] == category]
    if limit:
        tasks = tasks[:limit]
    return tasks

def bootstrap_ci(rows, n=2000):
    bycat = {}
    for r in rows:
        bycat.setdefault(r["category"], []).append(1.0 if r["pass"] else 0.0)
    rng = random.Random(42)
    means = []
    for _ in range(n):
        cms = []
        for vals in bycat.values():
            cms.append(sum(vals[rng.randrange(len(vals))] for _ in vals) / len(vals))
        means.append(100 * sum(cms) / len(cms))
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n)]

def run_one(target, task, max_tokens):
    t0 = time.time()
    try:
        resp, usage = target.ask(task["prompt"], max_tokens)
        err = None
    except Exception as e:  # noqa: BLE001
        resp, usage, err = "", {}, str(e)[:200]
    dt = time.time() - t0
    if err:
        return {"id": task["id"], "category": task["category"], "pass": False,
                "detail": f"TARGET ERROR: {err}", "response": "", "latency_s": round(dt, 1), "usage": usage}
    ok, detail = grade(task, resp)
    return {"id": task["id"], "category": task["category"], "pass": ok,
            "detail": detail, "response": resp[:2000], "latency_s": round(dt, 1), "usage": usage}

def summarize(rows):
    bycat = {}
    for r in rows:
        bycat.setdefault(r["category"], []).append(r["pass"])
    cats = {c: {"passed": sum(v), "total": len(v), "pct": round(100 * sum(v) / len(v), 1)}
            for c, v in sorted(bycat.items())}
    overall = round(sum(c["pct"] for c in cats.values()) / len(cats), 1) if cats else 0.0
    return cats, overall

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", help="label for this run (results/<name>.json)")
    ap.add_argument("--base-url")
    ap.add_argument("--model")
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--auth", choices=["bearer", "xapikey"], default="bearer")
    ap.add_argument("--cmd")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--category")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=1200)
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    tasks = load_tasks(args.category, args.limit)
    if not tasks:
        sys.exit("no tasks found")

    if args.self_test:
        rows = []
        for t in tasks:
            ok, detail = grade(t, t["reference"])
            rows.append({"id": t["id"], "category": t["category"], "pass": ok, "detail": detail})
            if not ok:
                print(f"SELF-TEST FAIL {t['id']}: {detail}")
        cats, overall = summarize(rows)
        print(f"\nself-test: {sum(r['pass'] for r in rows)}/{len(rows)} graders green — overall {overall}")
        sys.exit(0 if overall == 100.0 else 1)

    if args.cmd:
        target = CmdTarget(args.cmd)
    elif args.base_url and args.model:
        key = os.environ.get(args.api_key_env, "")
        target = OpenAITarget(args.base_url, args.model, key, args.auth)
    else:
        sys.exit("need --self-test, --cmd, or --base-url + --model")

    if not args.name:
        sys.exit("--name is required for a real run")

    work = tasks * args.runs
    print(f"running {len(work)} tasks against {target.desc} (concurrency {args.concurrency})")
    t0 = time.time()
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, target, t, args.max_tokens): t for t in work}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            rows.append(r)
            done += 1
            mark = "✓" if r["pass"] else "✗"
            if args.verbose or not r["pass"]:
                print(f"  {mark} {r['id']} ({r['latency_s']}s) {r['detail'][:110]}")
            elif done % 10 == 0:
                print(f"  … {done}/{len(work)}")
    elapsed = time.time() - t0

    rows.sort(key=lambda r: r["id"])
    cats, overall = summarize(rows)
    lo, hi = bootstrap_ci(rows)
    tok_in = sum(r["usage"].get("prompt_tokens", 0) for r in rows)
    tok_out = sum(r["usage"].get("completion_tokens", 0) for r in rows)

    print(f"\n{'category':<14}{'score':>7}   passed")
    for c, s in cats.items():
        print(f"{c:<14}{s['pct']:>7}   {s['passed']}/{s['total']}")
    print(f"{'OVERALL':<14}{overall:>7}   (95% CI {lo:.1f}–{hi:.1f})")
    tok_note = f" · tokens in {tok_in:,} out {tok_out:,}" if tok_in else ""
    print(f"{len(rows)} tasks in {elapsed:.0f}s{tok_note}")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = {
        "name": args.name, "target": target.desc,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall": overall, "ci95": [round(lo, 1), round(hi, 1)],
        "categories": cats, "elapsed_s": round(elapsed, 1),
        "tokens": {"in": tok_in, "out": tok_out},
        "runs": args.runs, "tasks": rows,
    }
    path = RESULTS_DIR / f"{args.name}.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"saved {path.relative_to(HERE)}")

if __name__ == "__main__":
    main()
