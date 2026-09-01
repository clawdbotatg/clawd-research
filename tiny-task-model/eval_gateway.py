#!/usr/bin/env python3
"""Eval gateway models (via clawd-harness's LLM gateway) on the same naming
test set the local models use — apples-to-apples frontier comparison.

Usage: uv run eval_gateway.py <model-id> [--limit N]
Reuses .clawd-harness.env credentials the same way bench_naming.py does.
"""
import argparse, json, sys, time, urllib.request
sys.path.insert(0, "/Users/austingriffith/clawd/clawd-harness")
import server  # noqa: E402  (loads env + config, starts nothing)
from grade import score  # noqa: E402

BASE = server.BANKR_BASE_URL
AUTH = ({"X-API-Key": server.BANKR_API_KEY} if server.BANKR_API == "bankr"
        else {"Authorization": f"Bearer {server.BANKR_API_KEY}"})

def call(model, messages):
    body = {"model": model, "max_tokens": 200, "temperature": 0.0,
            "messages": messages}
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={**AUTH, "content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    return (((payload.get("choices") or [{}])[0]).get("message") or {}).get("content", "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--limit", type=int, default=120)
    args = ap.parse_args()

    tests = [json.loads(l) for l in open("data/test.jsonl")][: args.limit]
    metas = [json.loads(l) for l in open("data/test_meta.jsonl")][: args.limit]

    outputs, t0 = [], time.time()
    for i, t in enumerate(tests):
        for attempt in range(6):
            try:
                outputs.append(call(args.model, t["messages"]))
                break
            except Exception as e:
                if "429" in str(e) and attempt < 5:
                    time.sleep(5 * (attempt + 1))
                    continue
                outputs.append(f"<error: {e}>")
                break
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(tests)}…", flush=True)
    dt = time.time() - t0

    import os, re as _re
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/" + _re.sub(r"[^\w.-]", "_", args.model) + ".jsonl", "w") as f:
        for o in outputs:
            f.write(json.dumps({"out": o}) + "\n")

    rate, checks, fails = score(outputs, metas)
    print(f"\n{args.model} (gateway)")
    print(f"pass rate: {rate:.1%}  ({len(tests)} samples, {dt/len(tests)*1000:.0f} ms/sample)")
    print("  " + "  ".join(f"{k}={v:.1%}" for k, v in checks.items()))
    for i, r, raw in fails[:6]:
        print(f"  FAIL #{i} {r}: {raw!r}")

if __name__ == "__main__":
    main()
