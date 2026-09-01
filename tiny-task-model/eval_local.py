#!/usr/bin/env python3
"""Eval a local MLX model (optionally with LoRA adapter) on the naming test set.

Usage: uv run eval_local.py [--adapter adapters] [--limit N] [--show-fails]
"""
import argparse, json, time
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from grade import score

MODEL = "mlx-community/Qwen3-0.6B-bf16"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--show-fails", action="store_true")
    args = ap.parse_args()

    model, tokenizer = load(MODEL, adapter_path=args.adapter)
    tests = [json.loads(l) for l in open("data/test.jsonl")][: args.limit]
    metas = [json.loads(l) for l in open("data/test_meta.jsonl")][: args.limit]

    outputs, t0 = [], time.time()
    sampler = make_sampler(temp=0.0)
    for i, t in enumerate(tests):
        prompt = tokenizer.apply_chat_template(
            t["messages"], add_generation_prompt=True, enable_thinking=False)
        out = generate(model, tokenizer, prompt=prompt, max_tokens=120,
                       sampler=sampler, verbose=False)
        outputs.append(out)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(tests)}…", flush=True)
    dt = time.time() - t0

    tag = f"{MODEL}" + (f" + {args.adapter}" if args.adapter else " (zero-shot)")
    import os; os.makedirs("outputs", exist_ok=True)
    fname = "outputs/" + (args.adapter.strip("/").replace("/", "_") if args.adapter else "base") + ".jsonl"
    with open(fname, "w") as f:
        for o in outputs:
            f.write(json.dumps({"out": o}) + "\n")

    rate, checks, fails = score(outputs, metas)
    print(f"\n{tag}")
    print(f"pass rate: {rate:.1%}  ({len(tests)} samples, {dt/len(tests)*1000:.0f} ms/sample)")
    print("  " + "  ".join(f"{k}={v:.1%}" for k, v in checks.items()))
    if args.show_fails:
        for i, r, raw in fails[:10]:
            print(f"  FAIL #{i} {r}: {raw!r}")

if __name__ == "__main__":
    main()
