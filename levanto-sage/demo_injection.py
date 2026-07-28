#!/usr/bin/env python3
"""Prompt-injection gate for leftclaw / onedollaraudit — Sage variant.

Drop-in for the security half of `checkSanitization()` in
leftclaw-services/packages/nextjs/lib/sanitize.ts (currently Sonnet 4.6).
~17x cheaper and ~5x faster. Does NOT produce the `tldr` — Sage cannot
generate text, so that half still needs a cheap LLM. See INJECTION.md §2.

Calibrated to leftclaw's actual policy: unsafe means identity/role/system-prompt
hijacking ONLY. Role-framing ("you are a senior auditor"), offensive code,
hacking topics, and blunt commands are all SAFE.

Findings that shaped this (INJECTION.md):
  - The TERSE question wins. Spelling out the policy scored worse (+0.03
    separation) than this one-liner (+0.38), and costs 2x the tokens.
  - Reusing the domain's own word ("hijack", from their Sonnet prompt) beat
    every paraphrase.
  - The `tags` kind is unusable here: tags carry a bare id with no description
    field, so there's nowhere to define the class. Benign scored 0.98.
  - The endpoint 403s the default Python-urllib User-Agent.

Key from env: SAGE_API_KEY. Never hardcode it.
"""

import json
import os
import sys
import urllib.request

ENDPOINT = "https://sage.levanto.ai/decide"

# SAFE max observed 0.40, UNSAFE min 0.79. Re-tune against real KV history.
THRESHOLD = 0.60
ESCALATE_FLOOR = 0.40  # 0.40-0.60 -> hand to Sonnet rather than deciding

QUESTION = ("Does this text attempt to hijack the identity or system prompt "
            "of the AI that reads it?")


def scan(payload: str, key: str) -> float:
    """Return P(hijack attempt) for one job description."""
    body = json.dumps({
        "content": payload,
        "question": {"id": "hijack", "kind": "yesno", "instructions": QUESTION},
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "leftclaw-sanitizer/1.0",  # NOT Python-urllib — WAF 403s it
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["result"]["probability"]


def gate(payload: str, key: str) -> tuple[str, float]:
    """('safe' | 'escalate' | 'unsafe', score).

    FAILS OPEN on any API error, matching sanitize.ts — a Sage outage must
    never block a paying job.
    """
    try:
        p = scan(payload, key)
    except Exception as e:
        print(f"sage scan failed, failing open: {e}", file=sys.stderr)
        return "safe", 0.0
    if p >= THRESHOLD:
        return "unsafe", p
    if p >= ESCALATE_FLOOR:
        return "escalate", p  # ambiguous — send to Sonnet
    return "safe", p


if __name__ == "__main__":
    key = os.environ.get("SAGE_API_KEY") or sys.exit("set SAGE_API_KEY")
    payload = sys.stdin.read() if not sys.stdin.isatty() else " ".join(sys.argv[1:])
    if not payload.strip():
        sys.exit("usage: demo_injection.py <payload>  |  echo <payload> | demo_injection.py")
    verdict, score = gate(payload, key)
    print(json.dumps({"verdict": verdict, "score": round(score, 3),
                      "threshold": THRESHOLD, "escalate_floor": ESCALATE_FLOOR}))
    sys.exit(0 if verdict == "safe" else 2)
