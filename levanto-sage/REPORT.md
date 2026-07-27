# Levanto Sage — Research Report

*Researched 2026-07-27. Sources: docs.levanto.ai (llms.txt index, quickstart, pricing, use-cases, SDK pages), the published agent skill (`docs.levanto.ai/levanto-sage-decide.md`), levanto.ai marketing page, and live probes against `sage.levanto.ai`.*

## TL;DR

Levanto Sage (by Levanto Labs) is a **decision API, not a text-generation API**. You POST content plus a question; it returns a structured decision with a **calibrated probability and confidence score** in ~100–300ms. No prompting for JSON, no parsing, no "simulated" confidence — the confidence signal is the product. Pricing is **$3 per 1M input tokens, output free**, plus $0.01 per grounding web search.

**Verdict for us:** genuinely useful for the *decision* slots in our systems (model routing, agent guardrails, session triage, moderation) — but it is **not a cheap-LLM replacement**. Per input token it costs 3× Haiku 4.5 and ~80× our Bankr qwen3-coder path. Its value is calibration + latency + zero-parsing, not raw price. Since decisions are tiny (hundreds of tokens), absolute cost per decision is ~$0.001–0.01, which is fine.

---

## 1. What it is

- **Product**: "Sage" — "the decision layer for AI agents." Turns `content + question → structured decision + probability/confidence`. Context-aware classifier; no training or fine-tuning needed.
- **Positioning**: for workflows where software needs to **decide, not write** — route, approve, block, score, rank, tag, escalate. Marketing tagline: "the first AI to say I don't know" — automate on high confidence, escalate to a human on low confidence.
- **Endpoint**: `https://sage.levanto.ai` — `GET /ready` (no auth), `POST /decide`, `POST /decide/batch` (Bearer key, `lv_live_...`).
- **Model**: responses report `meta.model: "levanto-sage-v0.6"` and `latency_ms` (~80–310ms in doc examples). Live probe: `/ready` returned 200 in 344ms from here; `/decide` without a key correctly 401s.
- **SDKs**: `npm install levanto` (Node 18+, zero deps) and `pip install levanto` (3.9+, httpx, sync + async clients), with per-kind shortcuts like `client.yesno(doc, "question?")` and built-in retries.
- **Agent-ready**: they publish an `llms.txt`, an OpenAPI schema, and a ready-made agent skill file — clearly built to be wired into Claude/Cursor agents.

## 2. The five decision kinds

| Kind | Input | Output | Limits |
|---|---|---|---|
| **yesno** | binary question | `probability` (P(yes)), `answer`, `confidence` = 2·\|p−0.5\| | — |
| **choice** | options w/ descriptions | `chosen` (argmax), per-option independent probabilities (don't sum to 1), `confidence` = P(chosen correct) | 2–120 options |
| **scale** | rubric | `expectation` (expected level), `confidence` (peakedness) | exactly 5 levels, values 0–4, no other rubric shapes (400 otherwise) |
| **sort** | list of `{id, content}` items + criterion | `sorted` id order + one calibrated list-level `confidence` | 2–120 items |
| **tags** | list of tag ids (optional per-tag `threshold`) | per-tag `probability`/`confidence`, `applies` when threshold given | 1–120 tags |

Request shape is uniform: `{content, question: {id, kind, instructions, ...}}`. Full request (content + instructions + options/rubric/tags + any grounding context) must fit **~32K tokens** — oversized requests fail rather than truncate.

**Batch** (`/decide/batch`): each group = one `content` + many `questions`, so asking N questions about one document sends the content once. Mixed groups per call; per-question `ok`/`result`/`error`.

**Grounding** (optional, yesno/choice/scale/tags): attach `{"grounding": {"trigger": "low_confidence", "confidence_floor": 0.8}}` and Sage runs a web search before deciding when its first-pass confidence is below the floor (or `always`). Adds `grounding_meta` (queries, sources, timing) and **+$0.01 only when a search actually runs**. For tags it's weakest-link: any tag below the floor triggers re-scoring of all tags.

## 3. Pricing & errors

- **$3.00 / 1M input tokens, output free.** No per-call fee. Prepaid credits; low balance → HTTP 402.
- **+$0.01 per executed grounding search.** Confident first pass at `low_confidence` trigger = no surcharge.
- No free tier or trial credits documented. Enterprise volume discounts via team@levanto.ai.
- Errors: 400 schema validation (with clear messages, e.g. the scale-levels rule), 401/402 auth/balance, 503 loading or very-long-content. No rate limits documented.

### Cost comparison (per 1M input tokens)

| Option | Input $/1M | Output $/1M | Notes |
|---|---|---|---|
| **Levanto Sage** | **$3.00** | **free** | calibrated confidence built in; ~100–300ms |
| Claude Haiku 4.5 | $1.00 | $5.00 | must prompt for JSON + parse; confidence is vibes |
| Claude Sonnet 5 | $3.00 (intro $2.00) | $15.00 | overkill for classification |
| qwen3-coder via Bankr (our naming model) | ~$0.036 | ~included | from our 41-model survey: $0.032/1000 calls at ~900 tok |

So the "cheap tasks" framing needs a caveat: **Sage is not cheaper per token than small LLMs — it's cheaper per *reliable decision*.** A 500-token yes/no costs ~$0.0015 (vs ~$0.0006 on Haiku with output), but you get sub-second latency, a wire-format guarantee (no malformed-JSON retries — the exact failure mode that disqualified gemma/grok tiers in our naming survey), and a calibrated confidence number you can threshold on. LLM self-reported confidence is simulated; Sage's is the actual product.

## 4. Where it fits our systems

**Good fits (decision-shaped, confidence-thresholdable):**

1. **Model/effort routing** — `choice` over {haiku, sonnet, opus/fable} given a prompt: "which tier does this task need?" ~$0.001/decision, 200ms, and the confidence score gives a natural policy: high-confidence "haiku" → route cheap; low confidence → default to the strong model. This is the classic router problem and Sage is purpose-built for it. (Note: the router itself costs more per token than the qwen3-tier models it might route *to* — worth it only where routing between expensive tiers, e.g. subscription-pool Opus vs API Haiku.)
2. **Harness AI-controller triage** — the roadmap "AI controller" layer in clawd-harness: `sort` idle sessions by "needs human attention," `yesno` "did this session end in a failure state?", `scale` urgency 0–4. Sage does the deciding; a real LLM does the acting.
3. **Agent guardrails** — their headline use case: check tool calls / outbound actions on the hot path ("does this bash command look destructive?", "does this diff contain a secret-like string?" as a second layer behind gitleaks). Latency is low enough to sit inline.
4. **Moderation/tagging of inbound channels** — Telegram/fleet message screening: `tags` (spam, prompt-injection-attempt, urgent) with thresholds.
5. **Agent-arena / esports judging** — `sort` for ranking N agent outputs by a criterion with a single list-level confidence; `scale` for rubric scoring rounds. Cheap enough to run per-round.

**Poor fits:**

- **Session naming** — that's generation, not decision. qwen3-coder stays.
- **simple-eval grading** — our whole design is deterministic grading; adding a probabilistic judge defeats it. (Could be a *secondary* experiment: does Sage's scale-grade correlate with our deterministic pass/fail?)
- **Anything needing >32K tokens of context** — hard cap, no truncation.

## 5. Risks / open questions

- **Early product**: model is `v0.6`, marketing says "onboarding teams" — likely young startup; no SLA, no documented rate limits, no status page found. Don't put it on a path that breaks the harness if it 503s — always degrade (same rule as our usage-endpoint poller).
- **No free tier documented** — need to buy prepaid credits to even trial it; key acquisition flow appears to be via levanto.ai signup or contacting them.
- **Calibration claims are unverified by us** — "calibrated confidence" is the whole pitch; before trusting thresholds we should run a small benchmark (e.g., 100 labeled routing decisions, check that p≈0.9 bucket is right ~90% of the time).
- **Rigid scale rubric** (exactly 0–4) and independent choice probabilities (don't sum to 1) are minor API quirks to code around.
- **Privacy**: content is sent to their API; nothing reviewed about retention. Don't send secrets/keys in `content`.

## 6. Live demo (done — see RESULTS.md)

We got a key and ran a 12-task model-routing benchmark (`demo_router.py`, key via env only). Headlines: **$0.545/1k decisions** (between Haiku's $0.33 and Sonnet's $1.00; qwen3-coder is 75× cheaper), median **326ms wall latency**, 7/12 routing accuracy, and a calibration finding: **`choice` confidence saturates at ~1.00 even on wrong answers, while `yesno` gives a genuinely informative probability spread (0.04–0.94)**. If we use Sage, phrase decisions as `yesno` questions and threshold on probability. Full details: `RESULTS.md`.

## Appendix: minimal call

```bash
curl -s -H "Authorization: Bearer $SAGE_API_KEY" -H 'Content-Type: application/json' \
  https://sage.levanto.ai/decide -d '{
  "content": "user prompt text here...",
  "question": {"id": "needs_opus", "kind": "yesno",
               "instructions": "Does this task require a frontier-tier model rather than a small/fast one?"}
}'
# → {"id":"needs_opus","kind":"yesno","result":{"probability":0.87,"confidence":0.74,"answer":"yes"},
#    "meta":{"model":"levanto-sage-v0.6","latency_ms":97.4}}
```

Full skill/reference: https://docs.levanto.ai/levanto-sage-decide.md · index: https://docs.levanto.ai/llms.txt
