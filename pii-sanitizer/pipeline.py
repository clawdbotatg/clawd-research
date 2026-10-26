#!/usr/bin/env python3
"""The loop Austin described, end to end, on raw fake notes.

  raw note
    -> regex pass (phones, emails, dates, IDs ...)       local
    -> small-model pass (names, places, the rest)        local, ollama
    -> Sage exit check (tags, one per identifier class)  remote
         flagged? -> small-model retry told WHAT was flagged, then re-check
         still flagged after N tries? -> BLOCK (human review)
    -> frontier model sees only placeholders             (mocked here)
    -> rehydrate placeholders back to real values        local

  set -a; . ~/sage/.env; set +a
  python3 pipeline.py [ollama-model]      # default qwen3:8b
"""
import json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import bench
from raw_cases import RAW

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3:8b"
MAX_RETRIES = 2
GATE = 0.5

REGEX = [  # order matters: specific before generic
    ("EMAIL", r"[\w.+-]+@[\w-]+\.[\w.]+"),
    ("URL", r"https?://\S+"),
    ("IP", r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    ("SSN", r"\b\d{3}-\d{2}-\d{4}\b"),
    ("PHONE", r"\(?\b\d{3}\)?[-. ]\d{3}-\d{4}\b"),
    ("DATE", r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    ("DATE", r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}(?:, \d{4})?\b"),
    ("ZIP", r"\b\d{5}(?:-\d{4})?\b(?=\D|$)"),
    ("ID", r"\b(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9-]{6,}\b"),
    ("ID", r"\b\d{2}-\d{4}-\d{3}-[A-Z0-9]\b"),
    ("AGE", r"\b(?:9\d|1[01]\d)[- ]year[- ]old\b"),
]

PROMPT = """You remove patient identifiers from clinical text before it leaves the hospital.
Find every remaining identifier: names or nicknames of the patient, relatives or other private
people (not doctors' titles, not drugs, not diseases), street addresses, towns/cities, ZIP codes,
specific dates, ages over 89, phone/fax/email/URL/IP, any ID or serial number, employers, and
any detail unique enough to single the person out (e.g. a specific job at a named place).
Text inside square brackets like [NAME_1] is already removed — ignore it.
{hint}
Return JSON: {{"spans": [{{"text": "<exact substring>", "type": "NAME|PLACE|DATE|CONTACT|ID|EMPLOYER|OTHER"}}]}}
Return an empty list if nothing is left.

TEXT:
{text}"""


class Vault:
    """Placeholder map. Lives only on the local side; under HIPAA 164.514(c) the
    placeholders must not be derived from the real value (so: counters, not hashes)."""
    def __init__(self):
        self.fwd, self.back, self.n = {}, {}, {}

    def token(self, kind, value):
        key = value.lower()
        if key not in self.fwd:
            self.n[kind] = self.n.get(kind, 0) + 1
            ph = f"[{kind}_{self.n[kind]}]"
            self.fwd[key], self.back[ph] = ph, value
        return self.fwd[key]

    def rehydrate(self, text):
        unknown = [p for p in re.findall(r"\[[A-Z]+_\d+\]", text) if p not in self.back]
        return re.sub(r"\[[A-Z]+_\d+\]", lambda m: self.back.get(m.group(0), m.group(0)), text), unknown


PH = re.compile(r"(\[[A-Z]+_\d+\])")


def sub_outside(pat, repl, text, flags=0):
    """re.sub that never touches text inside an existing placeholder."""
    parts = PH.split(text)
    return "".join(p if PH.fullmatch(p) else re.sub(pat, repl, p, flags=flags) for p in parts)


def regex_pass(text, vault):
    for kind, pat in REGEX:
        text = sub_outside(pat, lambda m: vault.token(kind, m.group(0)), text)
    return text


def llm_pass(text, vault, hint=""):
    body = {"model": MODEL, "stream": False, "think": False, "format": "json",
            "options": {"temperature": 0},
            "messages": [{"role": "user", "content": PROMPT.format(text=text, hint=hint)}]}
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=300))["message"]["content"]
    try:
        spans = json.loads(out).get("spans", [])
    except Exception:
        spans = []
    # longest first so "Linda Huang" wins over "Linda"
    for s in sorted(spans, key=lambda s: -len(s.get("text", ""))):
        t = (s.get("text") or "").strip()
        if len(t) < 2 or "[" in t or "]" in t or t.upper() == t and t.isalpha() and len(t) < 9:
            continue  # placeholders, or the model echoing a type name like PHONE
        kind = re.sub(r"[^A-Z]", "", (s.get("type") or "OTHER").upper()) or "OTHER"
        text = sub_outside(re.escape(t), lambda m: vault.token(kind, m.group(0)), text, flags=re.I)
    return text


def sage_gate(text):
    """Fails CLOSED: if Sage can't answer, the note is treated as flagged."""
    try:
        p, ms, extra = bench.run_tags(text)
    except Exception as e:
        return [f"sage-error:{e}"], 0
    flagged = [k for k, v in extra["per"].items() if v >= GATE]
    return flagged, ms


def residual(text, must_go):
    return [s for s in must_go if s.lower() in text.lower()]


def process(case):
    cid, kind, raw, must_go = case
    v = Vault()
    t0 = time.time()
    after_regex = regex_pass(raw, v)
    text = llm_pass(after_regex, v)
    pass1 = text
    flags_log, sage_ms = [], []
    for attempt in range(MAX_RETRIES + 1):
        flagged, ms = sage_gate(text)
        flags_log.append(flagged)
        sage_ms.append(ms)
        if not flagged:
            break
        if attempt == MAX_RETRIES:
            break
        hint = (f"A checker says these kinds of identifier are STILL in the text: "
                f"{', '.join(flagged)}. Look again carefully and find them.")
        text = llm_pass(text, v, hint)
    blocked = bool(flags_log[-1])
    # mock frontier reply that uses the placeholders it was given
    phs = re.findall(r"\[[A-Z]+_\d+\]", text)
    reply = f"Summary for {phs[0] if phs else 'the patient'}: plan reviewed." if phs else "Plan reviewed."
    back, unknown = v.rehydrate(reply)
    return {"id": cid, "kind": kind, "raw": raw, "must_go": must_go,
            "regex_left": residual(after_regex, must_go), "pass1_left": residual(pass1, must_go),
            "final": text, "final_left": residual(text, must_go), "flags": flags_log,
            "blocked": blocked, "sage_ms": sage_ms, "total_s": time.time() - t0,
            "reply": back, "unknown_placeholders": unknown, "map": v.back}


def main():
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(process, RAW))
    out = f"pipeline-{MODEL.replace(':', '_')}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    json.dump(rows, open(out, "w"), indent=1)
    n = len(rows)
    leaky = lambda key: sum(bool(r[key]) for r in rows)
    sent = [r for r in rows if not r["blocked"]]
    print(f"model {MODEL}, {n} raw notes -> {out}")
    print(f"  notes with PHI left after regex only:        {leaky('regex_left')}/{n}")
    print(f"  notes with PHI left after regex + {MODEL}:   {leaky('pass1_left')}/{n}")
    print(f"  Sage flagged after pass 1:                   {sum(bool(r['flags'][0]) for r in rows)}/{n}")
    print(f"  notes with PHI left after Sage-driven retry: {leaky('final_left')}/{n}")
    print(f"  blocked (still flagged, human review):       {sum(r['blocked'] for r in rows)}/{n}")
    print(f"  SENT with PHI still in it (the bad number):  {sum(bool(r['final_left']) for r in sent)}/{len(sent)}")
    print(f"  blocked but actually clean (false alarm):    {sum(r['blocked'] and not r['final_left'] for r in rows)}")
    print(f"  Sage calls/note avg: {sum(len(r['sage_ms']) for r in rows)/n:.2f}  "
          f"median wall/note: {sorted(r['total_s'] for r in rows)[n//2]:.1f}s")
    for r in rows:
        if r["pass1_left"] or r["final_left"] or r["blocked"]:
            print(f"  {r['id']:4} {r['kind']:24} pass1_left={r['pass1_left']} flags={r['flags']} "
                  f"final_left={r['final_left']} blocked={r['blocked']}")


if __name__ == "__main__":
    main()
