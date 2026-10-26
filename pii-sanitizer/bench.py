#!/usr/bin/env python3
"""Can Sage tell a clean sanitized note from one with a leaked identifier?

  set -a; . ~/sage/.env; set +a
  python3 bench.py [runs]          # writes results-<stamp>.json, prints a table

Strategies:
  single:<name>  one yes/no question
  ensemble       one batch call, 7 yes/no probes by identifier class, max()
  tags           one tags question over the Safe Harbor classes, max()
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from cases import CASES, LONG_CASES
if os.environ.get("LONG"):
    CASES = LONG_CASES

BASE = os.environ.get("SAGE_BASE_URL", "https://sage.levanto.ai")
HDR = {"Authorization": f"Bearer {os.environ['SAGE_API_KEY']}",
       "Content-Type": "application/json", "User-Agent": "pii-bench/1.0"}

PREAMBLE = ("Placeholders in square brackets like [PATIENT_1] or [DATE_1] are already "
            "redacted and are fine. ")

SINGLE = {
    "real-person": "Does this text contain any personal identifier of a real person?",
    "terse-leak": "Did any identifying detail about the patient leak through redaction?",
    "phi": PREAMBLE + "Does this text still contain any HIPAA identifier (name, date, "
           "contact, ID number, address, or anything else that could identify the patient "
           "or their family)?",
    "reidentify": PREAMBLE + "Could someone use anything left in this text to figure out "
                  "who the patient is?",
}

ENSEMBLE = {
    "name": PREAMBLE + "Is any person's name or nickname still in this text?",
    "date": PREAMBLE + "Is there a specific calendar date (day and month) or an age over 89?",
    "contact": PREAMBLE + "Is there a phone, fax, email, URL, or IP address?",
    "number": PREAMBLE + "Is there an actual ID number (not a [PLACEHOLDER]) such as SSN, MRN, account, member, license, "
              "plate, or device serial?",
    "place": PREAMBLE + "Is there a street address, ZIP code, or town smaller than a state?",
    "unique": PREAMBLE + "Is there a detail (job, employer, role, photo) unique enough to "
              "identify the patient?",
}

TAGS = [
    {"id": "name", "name": "name: name or nickname of the patient, a relative or another private person; not a [PLACEHOLDER] and not a disease or drug named after someone"},
    {"id": "date", "name": "date: a calendar date with day/month, or an age over 89; a year alone is fine"},
    {"id": "contact", "name": "contact: phone, fax, email, URL or IP address"},
    {"id": "number", "name": "number: SSN, MRN, account, member, license, plate or device serial"},
    {"id": "place", "name": "place: street address, ZIP, or a town/city; a state alone is fine"},
    {"id": "unique", "name": "unique: employer, specific role, or photo that singles the patient out"},
]


def post(path, body):
    t = time.time()
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), HDR)
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=60))
            return r, (time.time() - t) * 1000
        except urllib.error.HTTPError as e:
            if e.code not in (502, 503, 504) or attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def content(text):
    return {"kind": "text", "value": text}


def run_single(text, q):
    r, ms = post("/decide", {"content": content(text),
                             "question": {"kind": "yesno", "id": "q", "instructions": q}})
    return r["result"]["probability"], ms, r["meta"].get("usage")


def run_ensemble(text):
    qs = [{"kind": "yesno", "id": k, "instructions": v} for k, v in ENSEMBLE.items()]
    r, ms = post("/decide/batch", {"requests": [{"content": content(text), "questions": qs}]})
    ans = r["results"][0]["answers"]
    probs = {a["result"]["id"]: a["result"]["result"]["probability"] for a in ans if a.get("ok")}
    usage = [a["result"]["meta"].get("usage") for a in ans if a.get("ok")]
    return max(probs.values()), ms, {"per": probs, "usage": usage}


def run_tags(text):
    r, ms = post("/decide", {"content": content(text), "question": {
        "kind": "tags", "id": "phi", "tags": TAGS,
        "instructions": PREAMBLE + "Tag each kind of identifier that is still present in plain text."}})
    per = {t["id"]: t["probability"] for t in r["result"]["tags"]}
    return max(per.values()), ms, {"per": per, "usage": r["meta"].get("usage")}


def one(case, strat):
    cid, label, kind, text = case
    if strat.startswith("single:"):
        p, ms, extra = run_single(text, SINGLE[strat[7:]])
    elif strat == "ensemble":
        p, ms, extra = run_ensemble(text)
    else:
        p, ms, extra = run_tags(text)
    return {"id": cid, "label": label, "kind": kind, "strat": strat, "p": p, "ms": ms, "extra": extra}


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    strats = os.environ.get("STRATS", ",".join([f"single:{k}" for k in SINGLE] + ["ensemble", "tags"])).split(",")
    jobs = [(c, s) for _ in range(runs) for s in strats for c in CASES]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda j: one(*j), jobs))
    out = f"results-{time.strftime('%Y%m%d-%H%M%S')}.json"
    json.dump(rows, open(out, "w"), indent=1)
    print("wrote", out)
    report(rows)


def report(rows):
    print(f"{'strategy':22} {'leakMin':>7} {'cleanMax':>8} {'sep':>6} {'catch@.5':>8} {'fp@.5':>6} "
          f"{'catch@.2':>8} {'fp@.2':>6} {'p50ms':>6}")
    for s in dict.fromkeys(r["strat"] for r in rows):
        rs = [r for r in rows if r["strat"] == s]
        L = [r["p"] for r in rs if r["label"] == "leak"]
        C = [r["p"] for r in rs if r["label"] == "clean"]
        ms = sorted(r["ms"] for r in rs)[len(rs) // 2]
        f = lambda xs, t: sum(x >= t for x in xs)
        print(f"{s:22} {min(L):7.2f} {max(C):8.2f} {min(L)-max(C):+6.2f} "
              f"{f(L,.5):>4}/{len(L):<3} {f(C,.5):>2}/{len(C):<3} "
              f"{f(L,.2):>4}/{len(L):<3} {f(C,.2):>2}/{len(C):<3} {ms:6.0f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        report(json.load(open(sys.argv[1])))
    else:
        main()
