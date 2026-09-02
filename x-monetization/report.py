#!/usr/bin/env python3
"""X Original Content Rewards tracker.

Reads snapshots/<date>-daily.csv (X analytics "Account overview" export,
Verified toggle ON, 3M window), snapshots/<date>-posts.csv (Content tab export,
Posts, 3M) and snapshots/<date>.json ({"qualified": <program counter>}).

Prints: where the counter is, pace, what rolls off the 90-day window soon,
projected crossing date, and which posts moved since the previous snapshot.

Usage: python3 report.py [YYYY-MM-DD]   (default: newest snapshot)
"""
import csv, glob, json, os, re, sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshots")
TARGET = 500_000
WINDOW = 90

def num(s):
    s = str(s).strip().replace(",", "")
    m = re.match(r"^([\d.]+)([KM]?)$", s)
    if not m: return 0
    v = float(m.group(1)); return int(v * {"": 1, "K": 1e3, "M": 1e6}[m.group(2)])

def load_daily(path):
    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            d = datetime.strptime(row["Date"], "%a, %b %d, %Y").date()
            out[d] = int(row["Impressions"])
    return out

def load_posts(path):
    out = {}
    if not os.path.exists(path): return out
    with open(path) as f:
        for row in csv.DictReader(f):
            key = row.get("Post id") or row.get("Post link") or row.get("Post text", "")[:60]
            out[key] = {"text": row.get("Post text", "")[:70].replace("\n", " "),
                        "imps": num(row.get("Impressions", 0)),
                        "date": row.get("Date", "")}
    return out

def snapshots():
    ds = sorted({os.path.basename(p)[:10] for p in glob.glob(os.path.join(SNAP, "*-daily.csv"))})
    return ds

def main():
    ds = snapshots()
    if not ds: sys.exit("no snapshots")
    today = sys.argv[1] if len(sys.argv) > 1 else ds[-1]
    prev = ds[ds.index(today) - 1] if ds.index(today) > 0 else None
    daily = load_daily(os.path.join(SNAP, f"{today}-daily.csv"))
    meta = {}
    jp = os.path.join(SNAP, f"{today}.json")
    if os.path.exists(jp): meta = json.load(open(jp))
    t = datetime.strptime(today, "%Y-%m-%d").date()
    days = sorted(daily)
    verified90 = sum(daily[d] for d in days if d > t - timedelta(days=WINDOW))
    qualified = meta.get("qualified")
    ratio = (qualified / verified90) if qualified and verified90 else 0.557

    def span(n): return sum(daily.get(t - timedelta(days=i), 0) for i in range(1, n + 1))
    p7, p28 = span(7) / 7, span(28) / 28

    print(f"== {today} ==")
    if qualified:
        print(f"counter: {qualified:,} / {TARGET:,}   gap {TARGET - qualified:,}  ({ratio:.0%} of verified qualifies)")
    print(f"verified 90d: {verified90:,}   pace 7d {p7:,.0f}/day   28d {p28:,.0f}/day")
    if prev:
        pm = os.path.join(SNAP, f"{prev}.json")
        if os.path.exists(pm):
            pq = json.load(open(pm)).get("qualified")
            if pq and qualified: print(f"counter moved {qualified - pq:+,} since {prev}")

    # roll-off: days leaving the window over the next 14 days
    print("\nrolling off next 14 days (verified imps leaving the window):")
    cum = 0
    for i in range(1, 15):
        leaving = t - timedelta(days=WINDOW - 1) + timedelta(days=i - 1)
        v = daily.get(leaving, 0); cum += v
        flag = "  <-- cliff" if v > 3 * max(p28, 1) else ""
        print(f"  {(t + timedelta(days=i)).isoformat()}  loses {leaving.isoformat()} {v:>7,}  (cum {cum:,}){flag}")

    # projection at 7d and 28d pace
    print("\nprojection (qualified), assuming pace holds:")
    for label, pace in (("7d pace", p7), ("28d pace", p28)):
        q = qualified or verified90 * ratio
        cross = None
        for i in range(1, 91):
            leaving = t - timedelta(days=WINDOW - 1) + timedelta(days=i - 1)
            q += (pace - daily.get(leaving, 0)) * ratio
            if cross is None and q >= TARGET: cross = t + timedelta(days=i)
            if i in (14, 30, 60): print(f"  {label:8} +{i:2}d: {q:>9,.0f}", end="")
            if i == 60: print()
        print(f"  {label:8} crosses: {cross.isoformat() if cross else 'never at this pace'}")

    # post movers
    posts = load_posts(os.path.join(SNAP, f"{today}-posts.csv"))
    if posts:
        print("\ntop posts (all-user impressions, Content export):")
        for k, p in sorted(posts.items(), key=lambda kv: -kv[1]["imps"])[:8]:
            print(f"  {p['imps']:>8,}  {p['date'][:12]:12} {p['text']}")
        if prev:
            pp = load_posts(os.path.join(SNAP, f"{prev}-posts.csv"))
            if pp:
                mv = [(p["imps"] - pp.get(k, {}).get("imps", 0), p) for k, p in posts.items()]
                mv = [m for m in mv if m[0] > 0]
                print(f"\nbiggest movers since {prev}:")
                for d, p in sorted(mv, key=lambda x: -x[0])[:8]:
                    tag = "NEW" if p["imps"] == d else "   "
                    print(f"  {d:>+8,} {tag} {p['text']}")

if __name__ == "__main__":
    main()
