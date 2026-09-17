# jev-ultrafast — taking it for a spin

Source: Gregor Zunic (browser-use) tweet 2026-09-17, https://x.com/gregpr07/status/2100411068426469552
Repo: https://github.com/browser-use/jev-ultrafast (MIT, ~900 stars in its first day). Cloned to `upstream/` (gitignored).

## What it is

A tiny browser agent that does not ask an LLM to *generate* actions. Every step:

1. Snapshot the DOM once (`snapshot.js`) into a numbered element table.
2. One request to TypeSafe's **Jev** model asks two questions at once: which operation
   (CLICK / TYPE_TEXT / SELECT / SCROLL / WAIT / DONE / BLOCKED) and, speculatively, which
   element index for each operation. Jev returns a probability over the offered choices.
3. Only when the operation is TYPE_TEXT does a small LLM (Mercury 2.5 via OpenRouter) write
   the string to type.

Model output is never a selector, coordinate, or code. Every target maps back to an
observed DOM node and is re-validated before input. Headline: Google Flights Zurich to
London in 7.1 s for $0.0039, at 1x speed.

## What TypeSafe / Jev is

Same product category as Levanto Sage (see `../levanto-sage/`): a calibrated
multiple-choice scorer that cannot generate text. Question types: `choice`, `score`,
`noul` (true/false 0..1). Endpoint `POST https://api.typesafe.ai/v1/systemone`.
Founder Diogo Almeida (ex-OpenAI, two years in stealth), "System One Models", trained
with "RLCD". Launch blog: https://typesafe.ai/blog/introducing-system-one-models-and-jev

| | Jev (jev-1.13.0) | Levanto Sage v0.6 |
|---|---|---|
| Input price | **$0.042 / Mtok** ($42 per Btok) | $3.00 / Mtok |
| Output | free | free |
| Claimed latency | 70 to 500 ms end to end | 285 ms median (we measured) |
| Rate limit | 250K tok/s, 1200 req/min | n/a |
| Access | early access, waitlist, console login via Google or email | prepaid, key from Levanto |

That is ~70x cheaper than Sage for the same shape of call. Worth raising with Chris /
Marco at Levanto. Unverified by us until we have a key.

## Running it here

Prereqs done on this Mac:

- `uv sync` in `upstream/` done, `uv run pytest` 31 passed, `ruff` clean.
- `upstream/.env` written (gitignored). OpenRouter key copied from
  `~/clawd/dead-simple-agent/.env`, verified live, no spend cap. Mercury 2.5 is
  $0.04 / $0.15 per Mtok in/out. **`TYPESAFE_API_KEY` is empty.**
- Dedicated Chrome: `./start-chrome.sh` (headless) or `./start-chrome.sh --windowed`.
  Profile in `chrome-profile/` (gitignored), CDP on 127.0.0.1:9333. `.env` sets
  `BU_NAME=jev` and `BU_CDP_URL=http://127.0.0.1:9333` so browser-harness uses it and
  never touches the real Chrome. Verified: `scripts/check_guards.py` passed 21 real
  browser checks with no model calls.

To finish:

1. Get a key at https://console.typesafe.ai/settings/keys (Google login, may land on a
   waitlist). Put it in `upstream/.env` as `TYPESAFE_API_KEY=`.
2. `./start-chrome.sh`
3. `cd upstream && uv run jev`, open http://127.0.0.1:8766, Start demo.
   Or: `uv run --env-file .env python examples/flights.py --keep-open`.

## Known issues (upstream, day one)

- Issue #1: first observation can return an empty element table (readyState sampled on
  about:blank before navigation commits), and the policy answers BLOCKED instead of
  retrying. Library API only. If a run dies in under a second with `blocked`, this is it.
- Issue #5: Windows-only static asset bug, irrelevant here.
- Out of scope per README: shadow roots, iframes, canvas, uploads, pop-up tabs.

## Why it matters for us

- The "choose from an indexed action space, don't generate" pattern is the same idea as
  our Sage router work, now applied to browser control, and it's cheap enough to run on
  every step.
- Candidate for the harness's browser tasks and for the agent-arena work: a deterministic,
  auditable action log (every action is an observed node index) is easy to replay and grade.
