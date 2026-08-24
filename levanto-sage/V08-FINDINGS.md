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

## Batch latency (quality mode complete, 2026-08-24)

`demo_batch16.py`, 5 reps each, same document, all `compute_mode: fanout`:

| questions | p50 | min |
|---|---|---|
| 1 | 193ms | 169ms |
| 4 | 313ms | 221ms |
| 8 | 266ms | 262ms |
| 16 | **420ms** | 320ms |

Sub-linear scaling: 16× the questions for ~2.2× the latency, and it all bills
as **1 decision unit**. Closes OPEN-QUESTIONS #3b for quality mode.

**Fast mode is plan-gated, confirmed live:** `400 {"detail":"Fast mode is not
available on your plan. Upgrade or contact team@levanto.ai"}`. This key is on
Developer. Marco's 156ms-for-16 number is fast mode — unverifiable until we
have Starter+ (ask Chris for a comped upgrade, it's their headline number).

Note: the earlier 402 that looked like exhaustion happened at ~60 units total
spent — the key's initial allowance was near-empty, not our burn.

## Still open

- Fast-mode: latency AND accuracy delta on the injection golden set
  ("measurably less accurate" per the docs) — needs a Starter+ key.
- `usage` field came back None on batch responses despite being in the
  schema — billing still not observable in practice; unit math relies on the
  pricing page.
- platform.levanto.ai/intelligence/examples is login-gated (Google OAuth) —
  couldn't scrape; need Austin to log in once or export it.
