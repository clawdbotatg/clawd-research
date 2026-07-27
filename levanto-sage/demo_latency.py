#!/usr/bin/env python3
"""Head-to-head latency: Levanto Sage vs Haiku 4.5 vs qwen3-coder on the
same yes/no routing decision.

Keys from env only: SAGE_API_KEY, BANKR_API_KEY (+BANKR_BASE_URL).
Note: LLMs are called via the Bankr proxy (llm.bankr.bot), which adds some
overhead vs the direct Anthropic API — noted in results.
"""

import json
import os
import statistics
import sys
import time
import urllib.request

SAGE_KEY = os.environ.get("SAGE_API_KEY") or sys.exit("set SAGE_API_KEY")
BANKR_KEY = os.environ.get("BANKR_API_KEY") or sys.exit("set BANKR_API_KEY")
BANKR = os.environ.get("BANKR_BASE_URL", "https://llm.bankr.bot/v1")

QUESTION = "Does this task require a frontier-tier model rather than a small fast model?"
TASKS = [
    "Fix the typo in the README where it says 'recieve' instead of 'receive'.",
    "Write unit tests for the date-parsing helper, covering timezone edge cases.",
    "Find the race condition causing intermittent double-billing in this async payment pipeline spanning 6 services.",
    "Summarize this changelog entry in one sentence.",
    "Migrate this 40k-line codebase from callbacks to async/await keeping every public API backward compatible.",
    "Add a --verbose flag to this CLI script.",
]
ROUNDS = 2  # per task per backend


def post(url: str, headers: dict, body: dict) -> tuple[dict, float]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "User-Agent": "curl/8.7.1", **headers})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.load(r)
    return resp, (time.perf_counter() - t0) * 1000


def sage(task: str) -> tuple[str, float]:
    resp, ms = post("https://sage.levanto.ai/decide",
                    {"Authorization": f"Bearer {SAGE_KEY}"},
                    {"content": task,
                     "question": {"id": "r", "kind": "yesno", "instructions": QUESTION}})
    return resp["result"]["answer"], ms


def llm(model: str, task: str) -> tuple[str, float]:
    resp, ms = post(f"{BANKR}/chat/completions",
                    {"X-API-Key": BANKR_KEY},
                    {"model": model, "max_tokens": 20, "temperature": 0,
                     "messages": [
                         {"role": "system", "content":
                          f'{QUESTION} Reply with ONLY JSON: {{"answer":"yes"|"no"}}'},
                         {"role": "user", "content": task}]})
    text = (resp["choices"][0]["message"]["content"] or "").strip()
    try:
        answer = json.loads(text.removeprefix("```json").removeprefix("```").removesuffix("```"))["answer"]
    except Exception:
        answer = f"UNPARSEABLE({text[:30]!r})"
    return answer, ms


BACKENDS = {
    "sage": lambda t: sage(t),
    "haiku-4.5 (bankr)": lambda t: llm("claude-haiku-4.5", t),
    "qwen3-coder (bankr)": lambda t: llm("qwen3-coder", t),
}


def main() -> None:
    stats: dict[str, list[float]] = {b: [] for b in BACKENDS}
    fails: dict[str, int] = {b: 0 for b in BACKENDS}
    # warm each backend once (connection setup / cold start), excluded from stats
    for name, fn in BACKENDS.items():
        try:
            fn(TASKS[0])
        except Exception as e:
            print(f"warmup {name}: {e}")

    for rnd in range(ROUNDS):
        for task in TASKS:
            for name, fn in BACKENDS.items():
                try:
                    answer, ms = fn(task)
                    stats[name].append(ms)
                    if answer.startswith("UNPARSEABLE"):
                        fails[name] += 1
                    print(f"  r{rnd} {name:20} {ms:7.0f}ms  {answer:4} :: {task[:50]}")
                except Exception as e:
                    fails[name] += 1
                    print(f"  r{rnd} {name:20} ERROR {e}")

    n = ROUNDS * len(TASKS)
    print(f"\n{'backend':22}{'median':>8}{'p10':>8}{'p90':>8}{'parse-fail':>11}")
    for name, ls in stats.items():
        ls.sort()
        med = statistics.median(ls)
        p10, p90 = ls[max(0, int(len(ls) * .1) - 1)], ls[int(len(ls) * .9) - 1]
        print(f"{name:22}{med:>7.0f}ms{p10:>7.0f}ms{p90:>7.0f}ms{fails[name]:>8}/{n}")


if __name__ == "__main__":
    main()
