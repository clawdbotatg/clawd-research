#!/usr/bin/env python3
"""Levanto Sage demo: model-tier routing + cost-vs-other-LLMs comparison.

Reads SAGE_API_KEY from the environment — NEVER hardcode the key.
Runs a set of realistic coding/agent prompts through Sage's `choice` kind
(asking which model tier each task needs), records latency and estimated
input tokens, then compares the cost of doing the same classification job
with Haiku 4.5 / Sonnet 5 / qwen3-coder.

Token estimate: chars/4 (no usage field in Sage responses; noted in results).
"""

import json
import os
import statistics
import sys
import time
import urllib.request

KEY = os.environ.get("SAGE_API_KEY")
if not KEY:
    sys.exit("set SAGE_API_KEY")

ENDPOINT = "https://sage.levanto.ai/decide"

OPTIONS = [
    {"option": "small", "description": "Small fast cheap model (Haiku-class): trivial edits, one-liners, lookups, formatting, simple classification"},
    {"option": "mid", "description": "Mid-tier model (Sonnet-class): normal feature work, multi-file edits, standard debugging"},
    {"option": "frontier", "description": "Frontier model (Opus/Fable-class): hard architecture, long-horizon agentic work, subtle concurrency/security bugs, large refactors"},
]

# (prompt, expected tier) — expected is my label for a rough accuracy check
TASKS = [
    ("Fix the typo in the README where it says 'recieve' instead of 'receive'.", "small"),
    ("Rename the variable `tmp` to `session_buffer` across this one file.", "small"),
    ("Add a --verbose flag to this CLI script that prints each step.", "small"),
    ("Classify this git commit message as feat/fix/chore: 'bump deps'", "small"),
    ("Write unit tests for the date-parsing helper in utils.py, covering timezone edge cases.", "mid"),
    ("Debug why the websocket reconnect loop sometimes drops the first message after resume.", "mid"),
    ("Add pagination to the /sessions REST endpoint and update the two clients that call it.", "mid"),
    ("Refactor the PTY resize-ownership logic across server.py and index.html without regressing the multi-device size-claim protocol described in the docs.", "frontier"),
    ("Design and implement a multi-account subscription router that rebalances idle sessions onto the pool whose weekly window resets soonest, with bounce-rescue and redelivery, across a live production codebase.", "frontier"),
    ("Find the race condition causing intermittent double-billing in this async payment reconciliation pipeline spanning 6 services.", "frontier"),
    ("Migrate this 40k-line codebase from callbacks to async/await while keeping every public API backward compatible.", "frontier"),
    ("Summarize this changelog entry in one sentence.", "small"),
]

# $/1M input, $/1M output (Anthropic first-party rates, Sonnet intro pricing ignored)
PRICES = {
    "levanto-sage": (3.00, 0.0),
    "haiku-4.5": (1.00, 5.00),
    "sonnet-5": (3.00, 15.00),
    "qwen3-coder (bankr)": (0.036, 0.0),  # from our 41-model naming survey: ~$0.032/1000 calls @ ~900 tok
}
LLM_OUTPUT_TOKENS = 30  # JSON classification answer from an LLM doing the same job


def decide(content: str) -> tuple[dict, float, int]:
    body = json.dumps({
        "content": content,
        "question": {
            "id": "route",
            "kind": "choice",
            "instructions": "Which model tier should handle this task? Pick the cheapest tier that can do it reliably.",
            "options": OPTIONS,
        },
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        # the endpoint's WAF 403s the default Python-urllib user agent
        "User-Agent": "curl/8.7.1",
    })
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.load(r)
    wall_ms = (time.perf_counter() - t0) * 1000
    est_tokens = len(body) // 4  # full request body ~= billed input
    return resp, wall_ms, est_tokens


def main() -> None:
    rows, correct, total_tokens, latencies = [], 0, 0, []
    for prompt, expected in TASKS:
        resp, wall_ms, est_tokens = decide(prompt)
        chosen = resp["result"]["chosen"]
        conf = resp["result"]["confidence"]
        server_ms = resp["meta"]["latency_ms"]
        ok = chosen == expected
        correct += ok
        total_tokens += est_tokens
        latencies.append(wall_ms)
        rows.append((prompt[:58], expected, chosen, conf, server_ms, wall_ms, est_tokens, ok))

    print(f"{'task':60} {'exp':8} {'got':8} {'conf':>5} {'srv ms':>7} {'wall ms':>8} {'~tok':>5} ok")
    for r in rows:
        print(f"{r[0]:60} {r[1]:8} {r[2]:8} {r[3]:>5.2f} {r[4]:>7.1f} {r[5]:>8.0f} {r[6]:>5} {'✓' if r[7] else '✗'}")

    n = len(TASKS)
    print(f"\naccuracy: {correct}/{n}   median wall latency: {statistics.median(latencies):.0f}ms"
          f"   est. input tokens total: {total_tokens} (~{total_tokens // n}/decision)")

    per = total_tokens / n
    print(f"\ncost per decision (input ~{per:.0f} tok; LLMs add ~{LLM_OUTPUT_TOKENS} output tok):")
    for name, (pin, pout) in PRICES.items():
        out_tok = 0 if pout == 0 else LLM_OUTPUT_TOKENS
        cost = per / 1e6 * pin + out_tok / 1e6 * pout
        print(f"  {name:22} ${cost:.6f}  (${cost * 1000:.3f} per 1k decisions)")


if __name__ == "__main__":
    main()
