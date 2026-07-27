# Levanto Sage — live demo results (2026-07-27)

Ran `demo_router.py` against `sage.levanto.ai` with a real key (key held in
env only — never committed). Task: route 12 realistic coding prompts to a
model tier (`small` / `mid` / `frontier`) via the `choice` kind, then compare
cost against doing the same classification with other LLMs.

## Cost per decision — the headline the demo was for

Measured input: **~181 tokens/decision** (full request body incl. option
descriptions; estimated at chars/4 — Sage returns **no usage field**, so
billing can't be verified from the response).

| Router | $/decision | $/1k decisions | vs Sage |
|---|---|---|---|
| qwen3-coder (Bankr) | $0.000007 | **$0.007** | 75× cheaper |
| Haiku 4.5 (+30 output tok) | $0.000332 | $0.332 | 1.6× cheaper |
| **Levanto Sage** | $0.000545 | **$0.545** | — |
| Sonnet 5 (+30 output tok) | $0.000995 | $0.995 | 1.8× pricier |

So on cost alone Sage sits **between Haiku and Sonnet** — it is *not* the
cheap option; tiny LLMs through Bankr crush it on price. What you're paying
for is latency + wire-format guarantees + the confidence signal.

## Latency — excellent

Server-reported 112–216ms; wall-clock from this machine median **326ms**
(221–455ms). Fast enough to sit inline on an agent hot path, which no
Anthropic model call is.

## Accuracy & calibration — the caveat

- `choice` routing: **7/12 matched my labels.** Some disagreements are
  defensible boundary calls, but "find the race condition across 6 services"
  → `mid` is a genuine miss.
- **`choice` confidence saturates: 0.99–1.00 on every answer, including the
  misses.** As reported by this kind, it is not usable as an
  automate-vs-escalate threshold.
- **`yesno` behaves much better**: p spread 0.04–0.94 across easy/ambiguous
  tasks, and it correctly rated the race-condition task p=0.94 "needs
  frontier" — the very task `choice` misrouted. The earlier smoke test also
  gave a nuanced p=0.16 on a typo-fix.

**Practical takeaway:** if we use Sage for routing, phrase it as one or two
`yesno` questions ("does this need a frontier model?") rather than a 3-way
`choice` — better calibration and a smaller request (~120 vs ~180 tokens).

## Operational notes

- The endpoint's WAF **403s the default `Python-urllib` user agent**; any
  normal UA string works. Their own SDKs presumably set one.
- No usage/billing telemetry in responses; prepaid balance, 402 when empty.
- Model: `levanto-sage-v0.6` on every response.

## Head-to-head latency vs LLMs (`demo_latency.py`, 2026-07-27)

Same yes/no routing decision, 6 tasks × 2 rounds, warmup excluded. Haiku and
qwen called via the Bankr proxy (`llm.bankr.bot`) — a direct Anthropic API
call would shave some proxy overhead but not close the gap.

| Backend | median | p10 | p90 | clean parse |
|---|---|---|---|---|
| **Levanto Sage** | **285ms** | 167ms | 364ms | 12/12 |
| qwen3-coder (bankr) | 464ms | 392ms | 608ms | 12/12 |
| Haiku 4.5 (bankr) | 802ms | 581ms | 911ms | 0/12 |

**Sage is ~2.8× faster than Haiku** on the same decision, and beats even
qwen3-coder. The Haiku "0/12 clean parse" deserves honesty in both
directions: 11/12 were *recoverable* (Haiku wrapped the JSON in markdown
fences and appended prose despite an "ONLY JSON" instruction — a lenient
parser or structured outputs would fix it), and 1/12 was a genuine
non-answer ("I don't see a changelog entry"). But that's exactly the
robustness tax Sage eliminates: its wire format is the contract, so there is
no parser to harden. qwen also showed a 3975ms outlier (proxy hiccup) —
Sage's worst sample across both demos was 455ms.

## Bottom line for us

Cost-wise Sage loses to small LLMs for pure classification. It earns its
keep only where **sub-second inline latency + a thresholdable yes/no
probability** matter — agent guardrails on the hot path, quick
attention/escalation checks in the harness controller. For bulk/offline
classification or naming, qwen3-coder-class models remain ~75× cheaper.
Before any production use, run a proper calibration benchmark on `yesno`
(the `choice` confidence is not trustworthy as observed).
