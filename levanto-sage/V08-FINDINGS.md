# Sage v0.8 — live findings (2026-08-24)

Phase 0 run against `sage.levanto.ai` with a fresh key. Everything below
measured or fetched today. Supersedes the v0.6 numbers where noted.

## The service moved twice since our research

`meta.model` default is now **levanto-sage-v0.8** (research was v0.6, Marco's
08-19 email announced 0.7). OpenAPI title: "Sage 0.8.0". Saved to
`openapi-v07.json` (misnamed — it's 0.8).

## Calibration on v0.8: better across the board

Re-ran `demo_calibrate.py` (same 8 injection samples, same 3 phrasings):

| phrasing | v0.6 separation | **v0.8 separation** | tok |
|---|---|---|---|
| terse-hijack (winner) | +0.38 | **+0.80** (NEG max 0.12, POS min 0.92) | 65 |
| generic-override | **−0.04** | **+0.80** (NEG max 0.06, POS min 0.85) | 70 |
| long-policy | +0.03 | +0.21 | 130 |

- Terse still wins, but the margin is now huge, and the generic phrasing went
  from *broken* to co-winner. v0.8 is dramatically better calibrated.
- Latency: **~185ms median** single decision (was 285ms on v0.6).
- Threshold ~0.5 now separates 12/12 with room; the old 0.6 + 0.4–0.6
  escalation band design still holds, more comfortably.

## Pricing model completely changed — redo ALL cost math

No more $3/1M input tokens. Now **monthly decision-unit plans**:

| Plan | Price | Units/mo | Notes |
|---|---|---|---|
| Developer | $14 | 5,000 | no batch fast mode |
| Starter | $49 | 30,000 | fast mode |
| Growth | $249 | 300,000 | fast mode + 128K context |

Unit counting: 1 unit per call; +1 per extra document; ~1 per 4K input tokens;
+1 per grounding search. **"Ten questions about the same document → 1 unit."**
That officially answers OPEN-QUESTIONS #3: batch on one doc bills once.
Overrun returns **402 until next period** — no overage billing.

Consequence for the skill's pitch: the injection gate costs ~1 unit/scan, so
Developer plan = 5,000 scans/mo for $14 ≈ **$2.80/1k** all-in at full
utilization, or effectively free capacity if the plan is shared across uses.
The old "$0.19/1k" token math is dead; compare per-unit now.

## API surface changes (0.8 vs research)

- **`usage` on responses**: `billed_input_tokens`, `rendered_tokens` — billing
  is finally observable. Plus new **`POST /usage/estimate`** (min/max token
  estimate) and **`GET /models`**.
- **Batch schema changed**: questions take `instructions` (not `question`),
  batch items have NO `id` field, `additionalProperties: false` everywhere.
  Old demo scripts' batch calls need updating.
- **`latency_mode: "fast"`** documented: server packs questions about the same
  doc; "materially faster and measurably less accurate — intended for triage";
  ineligible kinds silently fall back; check `meta.compute_mode` per answer.
  Observed `compute_mode: "fanout"` on quality mode.
- **Context limit now 131,072 tokens** (was ~32K) — Growth plan only per
  pricing page.
- `tags` still has no per-tag description (only `id`/`name`/`threshold`) —
  the "use yesno ensembles" rule stands.
- Docs got per-kind pages + an official **`levanto-sage-decide` skill**
  (docs.levanto.ai/levanto-sage-decide.md) — sage-wisdom should complement,
  not duplicate it: theirs = how to call the API; ours = where it belongs in
  your app and proof it's better.

## Batch latency (partial — ran out of units mid-benchmark)

`demo_batch16.py`, quality mode, 5 reps each: 1 question **210ms** p50,
4 questions 276ms, 8 questions 275ms. All `fanout`. Then **402** — the key's
allowance was exhausted (~60 units spent total today, so the plan on this key
is either tiny or was already mostly used). Fast-mode and 16-question runs
still TODO — also note fast mode needs Starter+.

## Still open

- Fast-mode accuracy delta ("measurably less accurate" — measure it on the
  injection golden set before recommending it anywhere).
- 16-question batch p50/p95 in both modes.
- Whether this key's plan supports fast mode at all.
- platform.levanto.ai/intelligence/examples is login-gated (Google OAuth) —
  couldn't scrape; need Austin to log in once or export it.
