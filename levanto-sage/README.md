# Levanto Sage — research index

Everything we know about [Levanto Sage](https://docs.levanto.ai) (`sage.levanto.ai`),
researched and benchmarked live 2026-07-27 → 2026-07-28 against a real API key.

## What it is, in one line

**A fast multiple-choice scorer with LLM world knowledge.** You supply the
content *and* the answer space; it returns calibrated probabilities in ~200ms.
It cannot generate text — that limitation is also its main safety property.

## The numbers we measured

| | Sage | vs |
|---|---|---|
| Latency (single decision) | **285ms median** | Haiku 4.5 802ms, qwen3-coder 464ms |
| Cost (routing decision, ~180 tok) | $0.55/1k | Haiku $0.33/1k, Sonnet 5 $1.00/1k, qwen $0.007/1k |
| Cost (terse question, ~64 tok) | **$0.19/1k** | Sonnet 4.6 sanitizer $3.39/1k |
| Structured-output reliability | 12/12 clean | Haiku 0/12 clean (fenced JSON + prose) |
| Pricing | $3.00/1M input, **output free**, +$0.01 per grounding search | |

**It is not the cheap option** — small LLMs beat it on price by up to 75×. It
wins on **latency, guaranteed wire format, and a calibrated probability you can
threshold on.** Buy it for decisions on a hot path, not for bulk work.

## Files

| File | What's in it |
|---|---|
| **`REPORT.md`** | Start here. What the product is, all five decision kinds, API surface, pricing, limits, errors, risks. |
| **`RESULTS.md`** | Live benchmarks: cost per decision, latency head-to-head vs Haiku/qwen, and capability probes (trivia, chess). |
| **`USE-CASES.md`** | Every example Levanto publishes (16, across marketing + all doc pages) **plus 22 of ours** for clawd-harness, slop computer, arena, and research. |
| **`INJECTION.md`** | The leftclaw/onedollaraudit sanitization gate. Re-calibrated against the real `sanitize.ts`. ~17× cheaper than the current Sonnet 4.6 call. |
| **`VIDEO-CHAT.md`** | The clawd-video-chat filler loop. Sage can see the user's question safely where Haiku structurally cannot. |
| **`API-NOTES.md`** | Every undocumented quirk and gotcha we hit. **Read before writing any Sage code.** |

## Runnable benchmarks

All read `SAGE_API_KEY` from the environment — never hardcoded, never committed.

```bash
export SAGE_API_KEY=lv_live_...   # never commit this
python3 demo_router.py       # model-tier routing + cost table
python3 demo_latency.py      # Sage vs Haiku vs qwen (needs BANKR_API_KEY too)
python3 demo_videochat.py    # filler-loop router: complexity + flavor
python3 demo_calibrate.py    # ← sweep question phrasings; run this FIRST for any new task
echo "some payload" | python3 demo_injection.py   # the audit gate, exit 0=safe 2=blocked
```

## The three findings that matter most

**1. Question wording dominates everything.** Across every benchmark, rephrasing
the question moved results more than any other variable. On the injection task,
a terse one-liner scored +0.38 separation while a careful policy explanation
managed +0.03 — at half the tokens. **Always sweep phrasings with
`demo_calibrate.py` before shipping**; do not assume a well-written question is
a good one.

**2. Use `yesno` and `scale`; avoid `choice` and `tags`.** `choice` confidence
saturates near 1.00 even when the answer is wrong, and it collapses to one
default option (6/8 in the video-chat test). `tags` accepts only a bare id with
no description field, so there is nowhere to define a nuanced class — benign
input scored 0.98. The pattern that worked three times: **an ensemble of `yesno`
questions plus a deterministic mapping in code.**

**3. Its inability to generate text is a feature.** In clawd-video-chat, Haiku
must be kept blind to the user's question or it starts answering and
double-speaks. Sage can be shown anything, because there is no channel through
which it could leak an answer. That reframes it from "a weaker LLM" to "a safe
component."

## Status / risk

Model `levanto-sage-v0.6`, marketing says "onboarding teams" — young product, no
SLA, no documented rate limits, no status page found. Prepaid credits, no free
tier. **Fail open on cosmetic paths, and match the host system's existing
philosophy on security paths** (leftclaw fails open by design so an outage can't
block paying jobs). Re-verify calibration whenever the model version changes.
