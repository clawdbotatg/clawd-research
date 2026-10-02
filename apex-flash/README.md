# apex-flash-1 (Cantina) — fit for One Dollar Audit?

Researched 2026-10-02. Source: Cantina tweet 2026-10-01, cantina.security/apex-flash, HF model card + config.

## What it is
- Cantina + Yeta Labs RL post-train (GRPO, LoRA r256 + 16 full experts) of **GLM-5.3-Flash**.
- 321B MoE (288 experts, 8 active, ~18B active), 1M context, **MIT**, open weights:
  `cantina-security/apex-flash-1` and `-abliterated` (refusals removed).
- Built as a **worker under a bigger orchestrator**, trained in the **Codex** harness.
- Training data: 50 real paid bug cases → 150 tasks. 72% authz/identity/scope,
  18% accounting/precision, 4% sig replay, 4% payment rules, 2% SSRF.
  Not stated how much is Solidity. Reads like mostly web/backend + "protocol".

## Their numbers (own held-out set, 60 tasks, one run each)
| Model | Solved | Cost |
|---|---|---|
| Claude Opus 5 High | 43/60 | $74.68 |
| apex-flash-1 | 40/60 | $2.38 |
| GLM-5.3-Flash base | 36/60 | $4.56 |

One run, 60 tasks: 40 vs 43 vs 36 is inside noise. No public benchmark yet.

## Can we run it?
- **No hosted API** for apex yet (not on OpenRouter as of today).
- Self-host: BF16 ≈ 640 GB → 8×H100-class. 4-bit ≈ 180 GB → doesn't fit this Mac (128 GB);
  only a ~2-bit quant would, and that hurts quality. Two DGX Sparks (256 GB) could hold 4-bit.
- **Base GLM-5.3-Flash IS on OpenRouter**: $0.15 in / $0.50 out per M tokens.
  Per Cantina's table that's ~4 fewer tasks out of 60 than apex. Cheapest way to test the idea today.

## How it would fit
Today every $1 audit runs all-Opus on Claude subscriptions (3 context + 5–8 breadth +
12 Pashov attack agents + synthesis). The pain is subscription burn (job 681 walled
before writing a report; 08-17 drain). `AUDIT-WORKER-POOL-PLAN.md` in clawd-containers
already plans long-lived workers + an Opus judge.

Fit: Opus stays orchestrator + final judge; apex/GLM runs the **worker lenses**
(breadth checklists, attack lenses) via Codex pointed at an OpenAI-compatible endpoint.
That moves most tokens off the subscriptions.

Conflict: the worker-pool plan says "all security reasoning stays on Opus". This
change breaks that rule on purpose; only do it if the eval below says recall holds.

## Risks
- Paid product. A weaker worker = missed bugs = bad audit with our name on it.
- Their eval isn't smart-contract specific. Unknown on reentrancy, oracle, MEV, upgrade bugs.
- Abliterated variant: no reason to use it. Opus doesn't refuse audits; it only adds risk.
- Self-hosting a 321B model is real ops work; no API means no quick swap.

## How to decide (cheap)
We already own the eval: ~800 completed jobs with reports on IPFS.
1. Pick ~20 past jobs with confirmed Medium+ findings.
2. Re-run only the worker lenses with GLM-5.3-Flash (OpenRouter) in Codex; keep Opus judge.
3. Score recall of known findings + false-positive count vs the original all-Opus report.
4. If GLM base is close, apex is worth hosting (or wait for a provider). If GLM base is
   far off, apex's +4/60 won't close it.

Cost of step 2 on GLM: dollars, not subscription hours.
