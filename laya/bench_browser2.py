"""Fairness re-run of the browser element pick for Laya: plain-string option criteria
(Laya's documented format) instead of jev-ultrafast's nested dicts; records what it chose."""
import json, os, sys, time, statistics
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("bench", os.path.join(os.path.dirname(__file__), sys.argv[1]))
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)

def q_str(goal, els):
    return {"click_target": {"type": "choice",
        "instructions": f"Goal: {goal}. Which element should be clicked next?",
        "criteria": {e["index"]: f"{e['label']} ({e['role']})" for e in els}}}

def q_label(goal, els):  # option KEY is the label itself, index-free
    return {"click_target": {"type": "choice",
        "instructions": f"Goal: {goal}. Which element should be clicked next?",
        "criteria": {e["label"] if e["label"] not in seen or seen.add(e["label"]) else f"{e['label']} #{e['index']}": e["role"] for seen in [set()] for e in els}}}

L = bench.Laya(["english", "typed-decisions"])
out = {}
for m in L.models:
    L(state={"x": "warm"}, questions={"q": {"type": "noul", "instructions": "warm?", "criteria": {"true": "y", "false": "n"}}}, model=m)
    for fmt, qf in (("string", q_str), ("label-key", q_label)):
        res = {}
        for n in (8, 24, 60):
            hits, picks, lat = 0, [], []
            for goal, label in bench.BROWSER:
                els, correct = bench.elements(n, label, bench.FILLERS)
                st = {"page": {"url": "https://example.test", "title": "page", "text": goal}, "elements": [f"[{e['index']}] {e['label']}" for e in els]}
                ans, ms, _ = L(st, qf(goal, els), m)
                a = ans["click_target"]; c = a["choice"]
                lab = {e["index"]: e["label"] for e in els}.get(c, c)
                ok = (c == correct) or (c.split(" #")[0] == label)
                hits += ok; picks.append(lab.split(" #")[0]); lat.append(ms)
            res[n] = {"hits": f"{hits}/5", "picked": picks, "p50_ms": round(statistics.median(lat))}
        out[f"{m}/{fmt}"] = res
        print(m, fmt, json.dumps(res), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "results-laya-browser2.json"), "w"), indent=1)
