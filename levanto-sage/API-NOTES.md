# Sage API — undocumented quirks and gotchas

Everything we hit that the docs don't tell you. Read before writing Sage code.
All verified live against `sage.levanto.ai`, model `levanto-sage-v0.6`,
2026-07-27/28.

## Transport

**The WAF 403s the default Python user agent.** `urllib` sends
`Python-urllib/3.x` and gets `HTTP Error 403: Forbidden` — with a valid key, on
a valid request. Set any normal UA and it works:

```python
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
           "User-Agent": "your-app/1.0"}   # NOT the urllib default
```

Cost us a confusing debugging round. Their SDKs presumably set one; raw HTTP
callers must.

**`/ready` needs no auth** and returns 200/503 — use it for health checks
without spending a key.

## Response shapes

**Single `/decide`** — the documented shape is accurate:
```
resp["result"]["probability"]           # yesno
resp["result"]["chosen"] / ["confidence"] / ["probabilities"]   # choice
resp["result"]["expectation"]           # scale
resp["result"]["sorted"]                # sort
resp["result"]["tags"][i]["probability"]  # tags
resp["meta"]["model"], resp["meta"]["latency_ms"]
```

**`/decide/batch` nests ONE LEVEL DEEPER than the docs imply.** The published
skill file suggests `answers[j].result` holds the decision; it actually holds a
*full response envelope*, decision included:

```python
# WRONG (what the docs read like) — raises KeyError: 'probability'
resp["results"][i]["answers"][j]["result"]["probability"]

# RIGHT
resp["results"][i]["answers"][j]["result"]["result"]["probability"]
#                                 ^envelope  ^decision

# the id and per-question meta live on the envelope:
resp["results"][i]["answers"][j]["result"]["id"]
resp["results"][i]["answers"][j]["result"]["meta"]["latency_ms"]
```

Each answer also carries `ok` (bool) and `error` (null on success) at the outer
level. Check `ok` before reading.

**No usage/token field anywhere.** Responses carry no input-token count, so you
cannot verify billing from the response — token figures in our benchmarks are
estimated at `len(body)//4`. Consequence: **their claim that batch sends content
once for N questions is a wire-format statement, not a verified billing one.**
If a batch discount matters to your cost model, verify against the credit
balance before relying on it.

## Behavioral quirks per decision kind

**`choice` — confidence saturates; treat it as unusable for thresholding.**
Across the routing benchmark it returned 0.99–1.00 on *every* answer including
5 wrong ones. In the video-chat test it collapsed to a single default option on
6 of 8 inputs despite rich per-option descriptions. Use `choice` only where you
need an argmax and don't care about confidence, and where a wrong pick is cheap.

**`yesno` — well calibrated; this is the one to build on.** Observed spread
0.04–0.98 across easy/hard/ambiguous inputs, and it correctly reported *low*
confidence on a task it couldn't do (0.19 on a raw-FEN chess position it still
answered correctly). `confidence = 2·|p − 0.5|`, so thresholding on `probability`
is equivalent and clearer.

**`scale` — works well, but the rubric is rigid.** Exactly five levels, integer
values 0–4, no subsets or alternate ranges — anything else is a 400. Returns
`expectation` (a float, e.g. 2.4), not a discrete level.

**`tags` — unusable for nuanced classes.** A tag carries only `id` and optional
`threshold`; **there is no per-tag description field**, so the id string is the
entire class definition. Attempting an injection-detection ensemble this way
scored a *benign* payload at 0.98. Use tags only where the label is
self-evident from its name (`spam`, `promotion`).

**`sort` — accepts only `kind`/`id`/`instructions`.** Any other field on the
question is rejected. Scoring strategy is server-chosen; you get one list-level
`confidence` for the whole ordering.

## Limits (documented, worth restating)

| Kind | Field | Min | Max |
|---|---|---:|---:|
| choice | `options` | 2 | 120 |
| scale | `levels` | 5 | 5 (values 0–4 only) |
| sort | `content.value` items | 2 | 120 |
| tags | `tags` | 1 | 120 |

Whole rendered request must fit **~32K tokens** — content, instructions, option
descriptions, rubric lines, sort items, tag specs, and any grounding-added
context. **Oversized requests fail rather than truncating.** Very long content
can also 503 before the hard cap.

## Errors

| Code | Meaning |
|---|---|
| 400 | Schema validation. Messages are genuinely helpful (e.g. the scale-levels rule). |
| 401 | Missing/invalid key. `{"detail": "API key required. Provide a valid Levanto API key."}` |
| 402 | Prepaid balance too low. |
| 403 | **Usually the user-agent WAF, not auth.** Check your UA before your key. |
| 503 | Model loading, or content too long. |

## Prompt-engineering lessons (the biggest lever)

**Question wording moved results more than any other variable in every
benchmark.** Concretely, on the injection task:

| phrasing | separation | tokens |
|---|---|---|
| long, spells out the whole policy | +0.03 | 128 |
| **terse one-liner using the domain's own verb ("hijack")** | **+0.38** | **64** |
| medium, generic verbs ("override/replace/manipulate") | −0.04 | 69 |

Three rules that held up:

1. **Terse beats thorough.** Explaining the policy in the question made it
   *worse*, twice. Sage is a classifier, not an instruction-follower — long
   context appears to dilute rather than sharpen the signal.
2. **Reuse the domain's own vocabulary.** "Hijack" (the word leftclaw's own
   Sonnet prompt uses) beat every paraphrase.
3. **Decompose by class, not by question count.** One question per attack class
   beat both a single broad question and a tag ensemble. Take the max in code.

**Always sweep phrasings before shipping** — `demo_calibrate.py` exists for
exactly this. A question that reads well to a human is not necessarily one that
separates.

**Scores are not deterministic run-to-run.** Re-running the identical sweep on
the same samples reproduced the *ranking* exactly but with different margins
(terse-hijack +0.38 → +0.55, long-policy +0.03 → +0.06 on a second run). So:
the relative comparison between phrasings is stable and trustworthy, but a
threshold set from a single run is not. **Set thresholds with margin, and derive
them from several runs over real data** rather than from one sweep of synthetic
samples. There is no `temperature` or seed parameter to pin this down.

## Operational

- **Prepaid credits, no free tier**, no documented rate limits, no status page
  found, model `v0.6`, vendor describes itself as "onboarding teams."
- **Pin behavior to a re-run, not to a doc.** A model-version bump can move
  calibration; re-run your threshold sweep when `meta.model` changes.
- **Don't send secrets in `content`** — nothing published about retention.
- **Decide fail-open vs fail-closed deliberately, per host system.** leftclaw's
  sanitizer fails open in four places by design ("API errors must never block
  jobs"); a security gate bolted on there must match that, or a Sage outage
  blocks paying customers.
