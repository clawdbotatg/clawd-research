#!/usr/bin/env python3
"""Print the simple-eval leaderboard from results/*.json."""
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"

def main():
    runs = []
    for f in sorted(RESULTS.glob("*.json")):
        try:
            runs.append(json.loads(f.read_text()))
        except Exception as e:  # noqa: BLE001
            print(f"skipping {f.name}: {e}")
    if not runs:
        print("no results yet — run run_eval.py first")
        return
    runs.sort(key=lambda r: -r["overall"])
    cats = sorted({c for r in runs for c in r["categories"]})
    head = f"{'model':<22}{'overall':>8}  {'95% CI':<12}" + "".join(f"{c[:9]:>10}" for c in cats) + f"{'tok out':>9}  when"
    print(head)
    print("-" * len(head))
    for r in runs:
        ci = f"{r['ci95'][0]:.0f}-{r['ci95'][1]:.0f}"
        row = f"{r['name']:<22}{r['overall']:>8}  {ci:<12}"
        for c in cats:
            s = r["categories"].get(c)
            row += f"{(s['pct'] if s else '-'):>10}"
        tok = r.get("tokens", {}).get("out", 0)
        row += f"{tok:>9,}  {r['timestamp'][:16]}"
        print(row)

if __name__ == "__main__":
    main()
