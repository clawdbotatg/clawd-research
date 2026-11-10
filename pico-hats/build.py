#!/usr/bin/env python3
"""Merge research JSON files into hats.json and build index.html.

usage: build.py [dir-with-hats-*.json]   (no arg = rebuild from hats.json)
"""
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = """Display
LED
Audio
Motor/Robot
Sensor
Wireless/Network
Power/Battery
Input/Keypad
Expansion/Breakout
Proto
Storage/RTC
Industrial/IO
Kit/Other""".split("\n")


def clean(item):
    out = {k: str(item.get(k, "") or "").strip() for k in
           ("name", "maker", "category", "what", "price", "url", "status")}
    if out["category"] not in CATS:
        out["category"] = "Kit/Other"
    if out["status"] not in ("available", "discontinued", "unknown"):
        out["status"] = "unknown"
    if not re.match(r"^https?://", out["url"]):
        out["url"] = ""
    return out


def main():
    hats_path = os.path.join(HERE, "hats.json")
    if len(sys.argv) > 1:
        items = []
        for path in sorted(glob.glob(os.path.join(sys.argv[1], "hats-*.json"))):
            with open(path) as f:
                rows = json.load(f)
            print(f"{os.path.basename(path)}: {len(rows)}")
            items += rows
    else:
        with open(hats_path) as f:
            items = json.load(f)

    seen, hats = set(), []
    for raw in items:
        h = clean(raw)
        if not h["name"] or not h["url"]:
            continue
        key = h["url"].split("?")[0].rstrip("/").lower()
        name_key = (h["maker"].lower(), h["name"].lower())
        if key in seen or name_key in seen:
            continue
        seen.update([key, name_key])
        hats.append(h)
    hats.sort(key=lambda h: (h["maker"].lower(), h["name"].lower()))

    with open(hats_path, "w") as f:
        json.dump(hats, f, indent=1, ensure_ascii=False)
        f.write("\n")

    with open(os.path.join(HERE, "template.html")) as f:
        page = f.read()
    data = json.dumps(hats, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("__DATA__", data).replace("__DATE__", datetime.date.today().isoformat())
    with open(os.path.join(HERE, "index.html"), "w") as f:
        f.write(page)
    print(f"total: {len(hats)} hats, {len({h['maker'] for h in hats})} makers")


if __name__ == "__main__":
    main()
