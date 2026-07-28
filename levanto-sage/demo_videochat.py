#!/usr/bin/env python3
"""Filler-loop router for clawd-video-chat.

Replaces the blind Haiku "ack" in ~/clawd/random-agent/clawd-video-chat/
server.py handle_filler() (line 561). ONE batch call returns:

  - complexity 0-4  -> gates whether the Haiku recap fires at all
  - playful/opinion/tools flags -> pick which canned utterance to speak

Why Sage rather than Haiku here: server.py:586-592 deliberately hides the
user's question from Haiku, because "if Haiku can see the question it slips
into answering it, which then double-speaks once the real brain answers."
Sage cannot generate text, so it can be shown the question with zero leak
risk. The filler goes from blind to informed without reintroducing that bug.

Measured: ~377ms median, ~297 tok/turn, $0.892/1k turns.

NOTE: `choice` was tried first for utterance selection and FAILED — it
collapsed to "acknowledge" on 6 of 8 inputs despite rich option descriptions.
The working design is yesno flags + the deterministic mapping below (free).

Key from env: SAGE_API_KEY.
"""

import json
import os
import sys
import time
import urllib.request

ENDPOINT = "https://sage.levanto.ai/decide/batch"

LEVELS = [
    {"level": 0, "description": "Trivial — greeting, mic check, yes/no. Frontier model replies almost instantly."},
    {"level": 1, "description": "Simple factual question answerable in a sentence or two."},
    {"level": 2, "description": "Moderate — needs some explanation, mild reasoning."},
    {"level": 3, "description": "Complex — multi-step reasoning, comparison, or planning."},
    {"level": 4, "description": "Very complex — deep analysis, tool use, research, or a long multi-part task."},
]

QUESTIONS = [
    {"id": "complexity", "kind": "scale", "levels": LEVELS,
     "instructions": "How complex is this request — how long will a frontier model need to answer it?"},
    {"id": "playful", "kind": "yesno",
     "instructions": "Is the speaker being playful, joking, or teasing rather than asking a serious question?"},
    {"id": "opinion", "kind": "yesno",
     "instructions": "Is the speaker asking for an opinion, prediction, or subjective take rather than a fact?"},
    {"id": "tools", "kind": "yesno",
     "instructions": "Would answering this require looking something up, reading files, or using external tools?"},
]

# Pre-render these as audio once; then the first sound lands in ~377ms +
# playback instead of waiting on TTS. Biggest perceived-latency win available.
UTTERANCES = {
    "acknowledge": ["Mhm.", "Right.", "Okay."],
    "thinking": ["Hmm.", "Let me think about that.", "Hmm, lemme see."],
    "intrigued": ["Ooh.", "Interesting.", "Huh, good one."],
    "working": ["Let me dig into that.", "Gimme a sec.", "Let me pull that up."],
    "amused": ["Ha.", "Alright, alright.", "Heh."],
}

RECAP_THRESHOLD = 2.0   # complexity >= this -> fire the Haiku recap
ACK_CEILING = 1.0       # complexity < this -> plain acknowledgement
WORKING_FLOOR = 3.0     # complexity >= this -> "working" regardless of flags


def route(utterance: str, key: str) -> dict:
    body = json.dumps({"requests": [{"content": utterance, "questions": QUESTIONS}]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "clawd-video-chat/1.0",  # NOT Python-urllib — WAF 403s it
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.load(r)
    out = {}
    for a in resp["results"][0]["answers"]:
        # NB: batch nests one level deeper than the docs imply
        res = a["result"]["result"]
        out[a["result"]["id"]] = res.get("expectation", res.get("probability"))
    return out


def utterance_for(s: dict) -> str:
    """Deterministic mapping — no second API call, no cost."""
    if s["playful"] > 0.6:
        return "amused"
    if s["complexity"] < ACK_CEILING:
        return "acknowledge"
    if s["tools"] > 0.6 or s["complexity"] >= WORKING_FLOOR:
        return "working"
    if s["opinion"] > 0.6:
        return "intrigued"
    return "thinking"


def decide(utterance: str, key: str) -> dict:
    """Returns the filler plan. FAILS OPEN — a filler is cosmetic and must
    never block a turn; on error fall back to today's blind-Haiku ack."""
    try:
        s = route(utterance, key)
    except Exception as e:
        print(f"sage route failed, falling back: {e}", file=sys.stderr)
        return {"utterance": None, "complexity": None, "needsRecap": False, "fallback": True}
    return {
        "utterance": utterance_for(s),
        "complexity": round(s["complexity"], 2),
        "needsRecap": s["complexity"] >= RECAP_THRESHOLD,
        "scores": {k: round(v, 2) for k, v in s.items()},
        "fallback": False,
    }


DEMO = [
    "can you hear me okay?",
    "what's the capital of France?",
    "hey clawd, tell me a joke about ethereum devs",
    "what do you think about the direction AI agents are heading? like philosophically",
    "can you look at the leftclaw repo and figure out why the sanitization loop keeps failing on job 406",
    "explain how prompt caching works and when I should use the 1 hour TTL versus the 5 minute one",
    "hmm... so... what was I saying",
    "walk me through building a full x402 paywall with wagmi from scratch",
    "you're being kind of slow today buddy",
]

if __name__ == "__main__":
    key = os.environ.get("SAGE_API_KEY") or sys.exit("set SAGE_API_KEY")
    args = " ".join(sys.argv[1:]).strip()
    if args:
        print(json.dumps(decide(args, key), indent=2))
        sys.exit(0)

    print(f"{'said':46}{'cx':>5}{'play':>6}{'opin':>6}{'tool':>6}{'-> speak':>13}{'recap':>7}{'ms':>6}")
    lat = []
    for line in DEMO:
        t0 = time.perf_counter()
        d = decide(line, key)
        ms = (time.perf_counter() - t0) * 1000
        lat.append(ms)
        s = d["scores"]
        print(f"{line[:44]:46}{s['complexity']:>5.1f}{s['playful']:>6.2f}{s['opinion']:>6.2f}"
              f"{s['tools']:>6.2f}{d['utterance']:>13}{('YES' if d['needsRecap'] else '-'):>7}{ms:>6.0f}")
    lat.sort()
    print(f"\nmedian {lat[len(lat) // 2]:.0f}ms per turn (one batch call)")
