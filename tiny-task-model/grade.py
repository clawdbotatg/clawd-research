#!/usr/bin/env python3
"""Deterministic grader for the session-naming task.

A response passes only if ALL hold:
  format  — output parses as a single JSON object (nothing but the object),
            with exactly the keys title/desc/tab
  limits  — title <=5 words, desc <=12 words, tab <=2 words
  topic   — at least one main-topic keyword appears in title+tab (stem match)
  focus   — no side-quest keyword appears in the title (when a side-quest
            distractor was present in the transcript)
"""
import json, re

def grade(raw, meta):
    r = {"format": False, "limits": False, "topic": False, "focus": True}
    s = raw.strip()
    # tolerate a fenced block but nothing else around the object
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s).strip()
    try:
        obj = json.loads(s)
    except Exception:
        return r, False
    if not (isinstance(obj, dict) and set(obj) == {"title", "desc", "tab"}
            and all(isinstance(v, str) for v in obj.values())):
        return r, False
    r["format"] = True
    title, desc, tab = obj["title"], obj["desc"], obj["tab"]
    r["limits"] = (len(title.split()) <= 5 and len(desc.split()) <= 12
                   and 1 <= len(tab.split()) <= 2)
    hay = (title + " " + tab).lower()
    r["topic"] = any(k.lower() in hay for k in meta["kw"])
    if meta["sq_kw"]:
        r["focus"] = not any(
            re.search(rf"\b{re.escape(k.lower())}\b", title.lower())
            for k in meta["sq_kw"])
    ok = all(r.values())
    return r, ok

def score(outputs, metas):
    """outputs: list of raw strings; returns (pass_rate, per-check rates)."""
    checks = {"format": 0, "limits": 0, "topic": 0, "focus": 0}
    passes = 0
    fails = []
    for i, (raw, meta) in enumerate(zip(outputs, metas)):
        r, ok = grade(raw, meta)
        for k in checks:
            checks[k] += r[k]
        passes += ok
        if not ok:
            fails.append((i, r, raw[:160]))
    n = len(outputs)
    return passes / n, {k: v / n for k, v in checks.items()}, fails
