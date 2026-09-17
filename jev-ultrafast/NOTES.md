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
  $0.04 / $0.15 per Mtok in/out. `TYPESAFE_API_KEY` set 2026-09-17 (key named jev-ultrafast in austin's org).
- Dedicated Chrome: `./start-chrome.sh` (headless) or `./start-chrome.sh --windowed`.
  Profile in `chrome-profile/` (gitignored), CDP on 127.0.0.1:9444. `.env` sets
  `BU_NAME=jev` and `BU_CDP_URL=http://127.0.0.1:9444` so browser-harness uses it and
  never touches the real Chrome. Verified: `scripts/check_guards.py` passed 21 real
  browser checks with no model calls.

Run:

1. `./start-chrome.sh` (refuses if the port is held; see the port-collision note below)
2. `cd upstream && uv run --env-file .env jev`, open http://127.0.0.1:8766, Start demo.
   `--env-file` is required: `demo.py` imports browser-harness before it reads `.env`, so
   without it the harness looks for a daemon named `default`, spawns one, and that one dies
   with "daemon already running on bu-jev.sock" (the UI shows "Paused · needs attention").
   Or: `uv run --env-file .env python examples/flights.py`.

## Results on this Mac (2026-09-17)

| Task | Time | Actions | Result |
|---|---|---|---|
| Wikipedia main page -> Gödel article | 3.0 s | 2 | landed on the article |
| Google Flights ZRH->LON one-way 2026-09-20 | 8.0 s | ~12 | all 7 checks pass, real BA/easyJet results |

First bare API call: 283 ms, 347 input tokens, two questions answered in one request.

## Bug found + patched: covered elements spin the loop (2026-09-17)

Goal: "im looking for a flight from denver to mumbai land nov 1 fly out nov 7". The run got to
the date picker in 6 actions, then burned 113 model calls choosing "Sunday, November 1, 2026"
and never clicking it. November is the third month in the picker, clipped off the right edge
of its horizontal scroller. `snapshot.js` still lists it (checkVisibility ignores overflow
clipping), Jev correctly picks it, the executor's hit test correctly refuses it as covered,
`tick` retries, repeat until the 120-call demo budget.

Fix (`covered-elements.patch`, applied in `upstream/`, not yet upstreamed): in `snapshot.js`
drop any control whose center fails the same `elementFromPoint` test the executor uses. Then
the model sees only "Next" for November and the run completes: 11 actions, 15 calls, 11.0 s,
Denver -> Mumbai, Next month, Nov 1, Nov 7, Search, DONE. Worth a PR to browser-use.

Inspector note: "Page observed · ready for a decision" after Start demo is idle by design;
nothing moves until Run automatically or Choose next. Run automatically doubles as a pause
toggle. Clicks from the clawd-browser bridge did not fire the Start button; `el.click()` did.

## Where it stops working: the Airlines filter (2026-09-17)

Goal with "United only" fails every time at the 60-action cap. Two layers:

1. Google's airline checkboxes are Material-style: the native input is opacity 0 behind a
   styled `<label>`. The snapshot dropped them (invisible input, label not in the selector).
   Patched: for hidden checkbox/radio inputs, geometry, visibility and the hit test come
   from `labels[0]` in both `snapshot.js` and `browser.py` (in `covered-elements.patch`).
   After that the checkboxes appear in the action list.
2. United is 1,000 px down a 425 px scroll list inside the dialog. The model only sees
   visible text, so it has no evidence United exists. It clicked "Select all airlines"
   48 times in a row and never chose SCROLL_DOWN, even with the goal literally saying to
   scroll the list. Not a quick fix: the state would need a "more below" signal for inner
   scrollers, or a text search over offscreen controls.

Applied the filter by hand via CDP: Google returns "No United flights found" for
DEN-BOM Nov 1 to Nov 7. Closest unfiltered option was Lufthansa + United, 1 stop, $1,638.

## Port-collision trap

The first launcher used port 9333. Another headless Chrome (a clone of the real profile,
running since Sep 10) already held 127.0.0.1:9333, so mine only bound IPv6 and every CDP
call landed in that other browser. `start-chrome.sh` now uses 9444, refuses to start if the
port is held, and prints the target list so you can see it's only about:blank.

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
