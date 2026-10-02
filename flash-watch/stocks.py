#!/usr/bin/env python3
"""Pull weekly closes since 2025 for the memory stocks into seed/stock_<ID>.json."""
import datetime, json, os, urllib.request

TICKERS = {"MU": ("MU", "Micron"), "SNDK": ("SNDK", "SanDisk"), "LRCX": ("LRCX", "Lam Research"),
           "005930.KS": ("SAMSUNG", "Samsung"), "000660.KS": ("HYNIX", "SK Hynix"), "285A.T": ("KIOXIA", "Kioxia")}

here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(here, "seed"), exist_ok=True)
for t, (sid, name) in TICKERS.items():
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=2y&interval=1wk"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
    closes = r["indicators"]["quote"][0]["close"]
    pts = [{"d": datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%Y-%m-%d"), "c": round(c, 2)}
           for ts, c in zip(r["timestamp"], closes) if c]
    pts = [p for p in pts if p["d"] >= "2024-12-23"]
    doc = {"ticker": t, "name": name, "cur": r["meta"]["currency"], "pts": pts}
    with open(os.path.join(here, "seed", f"stock_{sid}.json"), "w") as f:
        json.dump(doc, f)
    print(sid, len(pts), pts[-1])
