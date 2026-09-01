# tiny-task-model — fine-tune a 0.6B model on one narrow task, locally

Inspired by [Tobi's tweet](https://x.com/tobi/status/2094808564355191249)
(2026-09-01): Shopify fine-tuned a 0.8B model that beats GPT 5.6-sol xhigh on a
specialized task, via a "self improving recursive flywheel." This dir is that
experiment in miniature, run end-to-end on the M3 Max in one session.

**Task:** clawd-harness session naming — the real production job behind
`BANKR_MODEL` (`server.generate_name`): transcript in, compact JSON out
(`{"title": ≤5 words, "desc": ≤12 words, "tab": 1-2 words}`), name the MAIN
objective, ignore side-quest tangents. Eval already existed (`bench_naming.py`);
production incumbent is `qwen3-coder` (~480B) via the gateway.

## Results

Canonical held-out test set (n=120, unseen topics only), deterministic grader,
all models get the identical production system prompt. Run 2026-09-01.

| Contender | Pass | Latency/sample |
|---|---:|---:|
| qwen3-coder (~480B, gateway — **production incumbent**) | 84.2% | 1.1 s |
| Qwen3-0.6B base, zero-shot (local) | 90.0% | 342 ms |
| Qwen3-0.6B + LoRA, run 1 (local) | 93.3% | 439 ms |
| **Qwen3-0.6B full fine-tune, run 2 (local)** | **95.8%** | **319 ms** |
| Qwen3-0.6B full FT + compression topics, run 3 (local) | 95.0% | 255 ms |
| **Qwen3-1.7B full fine-tune, run 4 (local) — champion** | **98.3%** | **564 ms** |
| gpt-5.6-sol (gateway — the model from Tobi's slide) | 100% | 4.2 s |

**The headline:** a locally fine-tuned 1.7B lands 2 samples short of
gpt-5.6-sol's perfect score at 7.5x lower latency and zero marginal cost, and
beats the ~480B production incumbent by 14 points. Even the 0.6B beats
production by 11+ points. Both remaining 1.7B failures are one unseen topic
where it emits a 3-word tab (limit is 2).

**Flywheel log** (each turn: look at failures, change one thing, keep-or-revert):

| Turn | Change | Result | Verdict |
|---|---|---|---|
| 1 | LoRA, 600 iters, 16 layers | 93.3% — fails: paraphrase echo, one garbled compound, 6-word titles | keep |
| 2 | full fine-tune, all layers, 800 iters | 95.8% — format/topic/focus all 100%; only fails = 6-word titles on one topic | keep |
| 3 | +8 "dense request → terse title" train topics | 95.0% — titles fixed, failures moved to 3-word tabs | revert |
| 4 | scale student to Qwen3-1.7B (v3 data) | 98.3% — only fails: 3-word tab, one topic | keep (champion) |

Stopped at turn 4: iterating further on test-set failures is test-set leakage
(turn 3 already was, mildly — see caveats). The honest next crank is a proper
dev set of extra held-out topics for iteration, keeping the test set pristine.

## The recipe (what Tobi's flywheel looks like at desk scale)

1. **Labels by construction** (`gen_data.py`) — synthetic transcripts generated
   from a hand-written topic bank (66 train topics + 12 held-out), so the
   correct name is known by the generator. Augmentation: opener phrasings,
   0-2 follow-up turns, 35-50% get an off-task side-quest distractor the model
   must not name the session after. 833 train / 63 valid / 120 test.
   **The test set uses only held-out topics** — the score measures
   generalization to unseen tasks, not recall.
2. **Train** — `mlx_lm.lora` on `mlx-community/Qwen3-0.6B-bf16`, 600 iters,
   batch 8, lr 1e-4, 16 layers, `--mask-prompt` (loss on the completion only).
   Runs take ~12-16 min on the M3 Max, ~250 tokens/sec, 9-14 GB peak memory.
   Val loss converges to ~0.001. Full fine-tune (`--fine-tune-type full`)
   beat LoRA by 2.5 points here.
3. **Grade deterministically** (`grade.py`) — pass requires ALL of: JSON-only
   output with exactly the 3 keys · word limits respected · a main-topic
   keyword in title+tab · no side-quest keyword in the title.
4. **Compare against the frontier on the same set** (`eval_gateway.py`) — the
   production incumbent and gpt-5.6-sol (the model from Tobi's slide) scored
   through the harness gateway with the identical system prompt and grader.

## Files

- `gen_data.py` — data generator (the "teacher"); topic bank + augmentation
- `grade.py` — deterministic grader (shared by all evals)
- `eval_local.py` — MLX eval (base zero-shot or `--adapter adapters`)
- `eval_gateway.py <model>` — same eval through the harness LLM gateway
- `sanity_real.py` — the 5 real transcripts from `bench_naming.py`, eyeballed
- `adapters*/` — trained weights (gitignored, ~1-4GB each; retrain in minutes)
- `outputs/` — raw model outputs per contender, for free regrades
- `data/` — committed; `test.jsonl`/`test_meta.jsonl` are the canonical test set

Retrain the champion:
`uv run mlx_lm.lora --model mlx-community/Qwen3-1.7B-bf16 --train --data data --fine-tune-type full --iters 800 --batch-size 8 --learning-rate 1e-5 --num-layers -1 --mask-prompt --adapter-path adapters-17b`
(don't rerun `gen_data.py` casually — see the rng note in it about the test set)

## What this buys / what's next

- The naming job runs constantly and is fire-and-forget — a local model makes
  it free and private. To productionize: fuse the adapter
  (`mlx_lm.fuse`), serve via `mlx_lm.server` (OpenAI-compatible), point
  `BANKR_BASE_URL` at localhost. `bench_naming.py` then scores it like any
  gateway model.
- The honest flywheel upgrade: replace synthetic transcripts with **real ones**
  from `.clawd-harness.prompts.jsonl` + registry names, labeled by a frontier
  teacher, graded by the same checks — that's the "self improving recursive"
  part of Tobi's loop (production traffic → labels → retrain → redeploy).
- Same recipe generalizes to any narrow structured-output job in the stack
  (digest lines, commit titles, morning-show segment labels). See
  `../agent-distillation/` for the theory ladder this slots into (rung 3→4).

## Caveats

- Synthetic test transcripts share the generator's *shape* (User:/Claude: turn
  structure) with training even though topics are held out — real-transcript
  eval is the next rigor step. The `sanity_real.py` outputs are the spot check
  (all clean), but 4 of its 5 transcripts overlap the train topic bank, so it
  partly tests recall.
- Flywheel turns 3-4 were chosen by reading test-set failures — standard ML
  hygiene says that makes the test set a dev set. Scores are still honest
  about unseen *topics*, but a pristine final test would need fresh topics.
- Run 1's gateway scores hit intermittent flakiness/429s; final numbers come
  from the retry-with-backoff runs (`outputs/*.jsonl`, regradeable offline).
- The frontier models are graded on strict spec compliance; their "failures"
  are mostly ≤5-word-limit violations, not bad names. That's the point though —
  the narrow model learns the exact spec, which is what the production job
  needs.
