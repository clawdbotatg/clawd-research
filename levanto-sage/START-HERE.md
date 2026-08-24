# START HERE — Levanto Sage research handoff

You've been handed a completed research package on **Levanto Sage**
(`sage.levanto.ai`, docs at `docs.levanto.ai`) — a commercial decision API.
Research was done live against the real API on 2026-07-27/28 by a previous
agent. This file orients you; the other files are the findings.

**Source of truth:** this is a copy of
`~/clawd/clawd-harness/projects/clawd-research/levanto-sage/` (a git repo). If
you make changes worth keeping, they belong there too — this `~/sage` copy is
untracked.

---

## The 60-second version

**Sage is a fast multiple-choice scorer with LLM world knowledge.** You give it
content *and* the set of possible answers; it returns a calibrated probability
in ~200–300ms. **It cannot generate text.** That one design fact explains every
measurement in these files.

The research was commissioned to answer "can we use this for cheap tasks and
model routing?" **The answer to "cheap" is no.** At $3/1M input tokens it costs
more per decision than Claude Haiku 4.5 and ~75× more than a small open model.
It wins on three other axes:

- **Latency** — 285ms median vs Haiku's 802ms (2.8×)
- **Wire format** — 12/12 clean structured parses; Haiku managed 0/12 on the
  same task (it fenced and prosed its JSON despite being told not to)
- **A calibrated probability you can threshold on**

So: use it for **decisions on a hot path**, never for bulk or offline work.

---

## Read in this order

| # | File | Why |
|---|---|---|
| 1 | **`README.md`** | The index and the measured numbers. Overlaps this file; skim it. |
| 2 | **`API-NOTES.md`** | **Read before writing any Sage code.** Every undocumented quirk. Will save you an hour. |
| 3 | **`REPORT.md`** | The product: all five decision kinds, API surface, pricing, limits, errors. |
| 4 | **`RESULTS.md`** | The live benchmarks — cost, latency head-to-head, capability probes. |
| 5 | **`OPEN-QUESTIONS.md`** | **Read before doing new work.** What was deliberately not done, and how to close each gap. |
| 6 | `USE-CASES.md` | Every example Levanto publishes (16) plus 22 invented for the commissioning org's stack. |
| 7 | `INJECTION.md`, `VIDEO-CHAT.md` | Two candidate production integrations, benchmarked in depth. Org-specific — see the glossary below. |
| 8 | **`MEETING-2026-07-30.md`**, **`MEETING-2026-08-21.md`** | Vendor calls. 07-30 explains the architecture; **08-21 is the current plan** (monthly builds, Sage Wisdom skill, batch-16 API). Read 08-21 before picking up any work. |

---

## Three findings that generalize beyond this vendor

**1. Question wording dominates every other variable.** On the injection task, a
terse one-liner scored **+0.38** class separation while a careful explanation of
the full policy scored **+0.03** — at double the tokens. The winner borrowed the
target domain's own verb ("hijack"). Sage is a classifier, not an
instruction-follower; long context dilutes rather than sharpens.
**Always sweep phrasings before shipping** — `demo_calibrate.py` exists for
exactly this and is the single most useful script here.

**2. Half the API is unusable.** `yesno` and `scale` are excellent and
well-calibrated. **`choice` saturates** — it returned 0.99–1.00 confidence on
every answer including five wrong ones, and collapsed to a single default option
on 6 of 8 inputs elsewhere. **`tags` has no per-tag description field**, so the
id string is the entire class definition; a benign payload scored 0.98. The
pattern that worked three separate times: **an ensemble of `yesno` questions
plus a deterministic mapping in plain code.**

**3. Its inability to generate text is a safety property, not just a limit.**
The clearest example is in `VIDEO-CHAT.md`: that system must keep its cheap
model *blind* to the user's question, or it starts answering and talks over the
real response. Sage can be shown anything, because there is no channel through
which an answer could leak. Worth reaching for whenever a component must sit
near untrusted text or near an answer it mustn't spoil.

---

## Epistemic status — what to trust

**Solid** (measured live, multiple runs): latency, pricing arithmetic, response
shapes, which decision kinds work, the relative ranking of question phrasings.

**Provisional** (measured once, on hand-written samples): every specific
threshold in these docs. `INJECTION.md`'s 0.60 cutoff and `VIDEO-CHAT.md`'s
complexity cutoffs come from 12 and 9 synthetic samples respectively. The
*approach* is validated; the *operating point* is not.

**Important:** Sage scores are **non-deterministic run-to-run**, with no
temperature or seed parameter. Re-running an identical sweep reproduced the
phrasing *ranking* exactly but with materially different margins (+0.38 → +0.55).
Never set a production threshold from a single run.

**One correction is baked into the docs, so don't be confused by it:** the first
injection benchmark was miscalibrated — it assumed the target used Opus and a
generic definition of prompt injection. Reading the actual source showed it used
Sonnet 4.6 with a much narrower policy, which invalidated the first result and
forced a full re-run. `INJECTION.md` §0 documents this. The numbers in that file
are the corrected ones. If you find `$0.66/1k`, `threshold 0.75`, or `11/11`
quoted anywhere, that's the dead first pass.

---

## Running the benchmarks

**You need a key.** None is stored on disk anywhere in this package, by design.
Ask Austin for a `lv_live_...` key. Prepaid, no free tier — calls spend real
credits, though the entire research effort cost well under a cent.

```bash
export SAGE_API_KEY=lv_live_...          # never commit this
python3 demo_calibrate.py    # ← sweep question phrasings. Run this FIRST for any new task.
python3 demo_router.py       # model-tier routing + cost table
python3 demo_videochat.py    # filler-loop router: complexity + flavor flags
python3 demo_latency.py      # Sage vs Haiku vs qwen  (also needs BANKR_API_KEY)
echo "some payload" | python3 demo_injection.py    # exit 0 = safe, 2 = blocked
```

Pure stdlib, no dependencies. `GET /ready` needs no auth if you just want to
check the service is up.

**The one gotcha that will bite you immediately:** the WAF returns **403
Forbidden** for the default `Python-urllib/3.x` user agent, even with a valid
key on a valid request. Set any normal UA. All five scripts already do.

---

## Glossary — local context the other docs assume

These files were written inside a specific codebase and name things without
explaining them. All paths are on this machine.

- **clawd / clawd-harness** — Austin's web harness for driving interactive
  Claude Code sessions. `~/clawd/clawd-harness`. The commissioning context.
- **leftclaw-services / onedollaraudit** — a smart-contract audit job board.
  Its prompt-injection sanitizer at
  `~/clawd/clawd-harness/projects/leftclaw-services/packages/nextjs/lib/sanitize.ts`
  is the subject of `INJECTION.md`. **Read that file before touching that
  design** — its narrow safety policy is the whole reason the first benchmark
  was wrong.
- **clawd-video-chat** — a live voice agent.
  `~/clawd/random-agent/clawd-video-chat/server.py`, function `handle_filler()`
  (~line 561) is the subject of `VIDEO-CHAT.md`. The comment block above that
  function is the key artifact.
- **Bankr** — an OpenAI-compatible LLM proxy (`llm.bankr.bot`) used as the
  price/latency baseline for non-Anthropic models.
- **qwen3-coder** — the small model that won a prior 41-model survey for the
  harness's session-naming job. It's the "75× cheaper" comparison point and the
  recommended partner for work Sage structurally cannot do (writing summaries).
- **simple-eval** — an in-house 60-task eval suite at
  `~/clawd/clawd-harness/projects/clawd-research/simple-eval`.

---

## Status: nothing is wired into production (yet — Aug build changes that)

**Committed next step (2026-08-21 call):** ship the `INJECTION.md` gate into
$1 audit as the August "effective → efficient" build, then a router in
September, plus a `sage-wisdom.md` skill co-launched with Levanto. Details and
action items in `MEETING-2026-08-21.md`; deferred work in `OPEN-QUESTIONS.md`
still applies (re-tune thresholds on real leftclaw traffic first).

Both candidate integrations are **benchmarked designs with runnable harnesses
only**. No code in `leftclaw-services` or `clawd-video-chat` has been changed.
If you're being asked to implement one, start with `OPEN-QUESTIONS.md` — the
first item is that the thresholds need re-tuning against real traffic before
they gate anything that matters.

**Vendor risk, stated plainly:** model `levanto-sage-v0.6`, vendor describes
itself as "onboarding teams." No SLA, no documented rate limits, no status page
found, prepaid credits only. Every design in these docs **fails open** — match
that. And re-run `demo_calibrate.py` if `meta.model` on a response ever shows
something other than `v0.6`; calibration is the thing most likely to shift
silently under you.
