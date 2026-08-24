# Sage Wisdom — goal + implementation plan

*Drafted 2026-08-24. Builds on the research package in this dir (read
`START-HERE.md` first) and the 2026-08-21 call with Chris. This is the plan for
the skill itself; the Aug "$1 audit injection gate" build is a separate,
parallel deliverable that doubles as this skill's first proof.*

---

## 1. Goal

**A published skill (`sage-wisdom`) you drop into any Claude Code harness. It
reads the local build — code, prompts, logs, pipelines — and walks the
"effective → efficient" loop for you:**

> First you make it work. Then you ask *"what did we learn?"* — and you make it
> work better: cheaper, faster, more deterministic.

Concretely, the skill finds every place the pipeline spends an LLM call and
asks, for each one: **is this the cheapest thing that can do this job
reliably?** Then it doesn't just propose the swap — it **builds a small eval
from your own traffic and proves the swap head-to-head** before you commit.

The two canonical conversations it should produce:

- *"You're using Opus 4.8 for prompt-injection detection. Sage would do this at
  ~1/17th the cost and 5× faster — want me to generate some example injections
  and run them through both to prove it?"*
- *"You're calling Sonnet 5 to average these numbers every run. That should be
  a script. Want me to profile the two against each other to make sure?"*

Sage is the headline (it's co-launched with Levanto), but the skill's honest
frame is the **descent ladder**: for every LLM call site, walk down until
something breaks —

```
frontier LLM  →  small LLM  →  Sage (fast calibrated classifier)  →  plain code
   (keep)         (cheaper)      (faster + deterministic-ish)         (free, exact)
```

Sage occupies a specific rung: **decision-shaped work on a hot path** — where
you need latency, a guaranteed wire format, or a probability you can threshold
on, and where the can't-generate-text property is a safety feature. The skill
must know when Sage is *not* the answer (bulk classification → small LLM is
75× cheaper; arithmetic → code) or it's a sales brochure, not wisdom.

**Personification (from the 08-21 call):** sage-in-a-robe. Plays Chris's ASCII
animation on first load, asks 2–3 profile questions ("what do you build?"),
then goes off to read the repo and comes back with proposals across four
buckets: **speed, cost, security, QA**.

---

## 2. Why the eval is the heart of it

Everything measured in this research says you cannot swap a model on vibes:

- **Question wording dominates** (+0.38 vs +0.03 separation on the same task).
- **Sage scores are non-deterministic run-to-run** — rankings stable, margins
  not. A threshold from one sweep is not an operating point.
- The first injection benchmark here was **invalidated by not reading the real
  code** (assumed Opus + generic policy; reality was Sonnet 4.6 + a narrow
  "identity hijack only" policy).

So the skill's differentiator is the **prove-it loop**, run per proposal:

1. **Read the real call site** — the actual prompt, model, policy, and
   fail-open/fail-closed philosophy. Never benchmark against an assumption.
2. **Build a golden set** — prefer replaying real traffic (logs, KV stores,
   transcripts); fall back to ~12–20 synthetic samples written *to the host's
   actual policy*, including its known false-positive traps.
3. **Sweep phrasings** (Sage) or implementations (script/small-model), terse
   first, using the domain's own vocabulary. Multiple runs — margins wobble.
4. **Report a head-to-head table**: accuracy on the golden set, p50 latency,
   $/1k calls, current vs candidate. Recommendation with threshold + escalation
   band, or an honest "keep what you have."
5. **Leave the eval behind** as a regression harness — rerun it when the model
   version bumps (`meta.model`), when traffic drifts, or monthly.

That last step is the "synthesize your own skills and memory" part of the
loop: each optimization ships with the instrument that keeps it honest.

---

## 3. What ships

A directory (published as a repo / gist Levanto can drop into their harnesses):

```
sage-wisdom/
├── SKILL.md            # the skill itself (frontmatter + methodology)
├── intro.sh            # Chris's ASCII animation (slot — see Open items)
├── sage_client.py      # minimal stdlib client, quirks baked in
├── sweep.py            # generalized phrasing/threshold sweeper (from demo_calibrate.py)
├── shootout.py         # head-to-head runner: current impl vs candidate on a golden set
└── reference.md        # condensed API truth (from API-NOTES.md) the skill reads on demand
```

### SKILL.md structure

1. **Frontmatter** — name `sage-wisdom`, description written so it triggers on
   "make my pipeline cheaper/faster", "where should I use Sage", "optimize my
   LLM costs", "review my AI spend".
2. **First-load ritual** — play `intro.sh`, introduce the sage persona (light
   touch: flavor in greetings and verdicts, never in the numbers), ask the
   profile questions.
3. **Discovery pass** — how to find LLM call sites in a repo: grep for SDK
   imports/model ids/API URLs, read prompt files, check for cron/CI loops,
   estimate each site's volume × tokens × price. Output: a ranked table of
   call sites with monthly cost and "descent candidate" classification.
4. **The descent ladder + Sage fit test.** When to propose code, a small
   model, or Sage. Sage fit = decision-shaped + hot path or thresholdable
   probability needed or must-not-generate-text safety. Explicit anti-fit
   list: bulk offline work, text generation, anything price-driven alone.
5. **The prove-it loop** (§2 above), as instructions with the scripts.
6. **Sage integration knowledge** (condensed, with pointers to reference.md):
   - `yesno` + `scale` only; `choice` saturates, `tags` has no descriptions.
     Ensemble of yesno + deterministic mapping in code.
   - Terse questions, domain vocabulary, sweep before shipping.
   - Batch response nests one level deeper than docs (`result.result.*`).
   - WAF 403s default Python UA; `/ready` is free.
   - Fail open/closed: match the host system's philosophy.
   - v0.7: batch-16, `latency_mode: "fast"`, ~156ms for 16 yesno; re-verify
     calibration whenever `meta.model` moves.
7. **Proposal format** — the four buckets (speed/cost/security/QA), each
   proposal as: finding → estimated savings → "want me to prove it?" → eval →
   implementation offer. Never implement before the eval agrees.
8. **Key handling** — `SAGE_API_KEY` from env only; prepaid, real money; never
   commit; point users at Levanto for a key.

### The scripts

- **`sage_client.py`** — ~80 lines, stdlib only. Handles UA, auth, single +
  batch decide, the envelope-nesting quirk, `latency_mode`, `ok`/`error`
  checking, fail-open wrapper. Every quirk we paid to learn, encoded once.
- **`sweep.py`** — generalize `demo_calibrate.py`: takes a JSON file of
  {samples, labels, phrasings}, runs N repetitions, reports separation ±
  spread, recommends threshold + escalation band. Model-version-stamped output.
- **`shootout.py`** — takes a golden set + two runnables ("current" = a
  command or API call, "candidate" = Sage question / script / model), emits
  the head-to-head table (accuracy, p50/p95 latency, $/1k). This is the eval
  artifact that stays in the host repo.

---

## 4. Implementation phases

**Phase 0 — refresh the ground truth on v0.7 (½ day, needs key).**
Marco's 08-19 email: Sage 0.7 is live (batch-16, `latency_mode: "fast"`, new
OpenAPI at `sage.levanto.ai/openapi.json`). All numbers in this dir are v0.6.
- Fetch the new OpenAPI; diff against REPORT.md's surface.
- Re-run `demo_calibrate.py` on the injection samples (OPEN-QUESTIONS #9 —
  calibration is the thing most likely to shift silently).
- Benchmark batch 1/4/8/16 in both latency modes (OPEN-QUESTIONS #3b).
- Update reference.md numbers from these runs, not from the old docs.

**Phase 1 — write the package (1 day).**
SKILL.md + the three scripts + reference.md, per §3. Wire the animation slot
(plays once, `--quiet` respected, degrades to a static banner if the terminal
can't handle it).

**Phase 2 — dogfood on our own pipelines (the real test, 1 day).**
Run the skill cold against three targets and grade what it finds:
- **leftclaw/onedollaraudit** — it *should* independently rediscover the
  injection gate (INJECTION.md is the answer key: split design, Sage verdict +
  qwen tldr, fail open, threshold 0.6 with 0.4–0.6 escalation). If it doesn't,
  fix the skill, not the answer.
- **clawd-video-chat** — should find the filler-loop router (VIDEO-CHAT.md).
- **One pipeline with no pre-researched answer** (harness session-naming,
  slop-computer internals, arena) — this is where "I don't know what I don't
  know" gets tested and where a genuinely new find would come from.
Also verify it *doesn't* over-recommend: it should tell the session-naming job
to stay on qwen3-coder (75× cheaper) and tell an averaging call to become code.

**Phase 3 — ship to Chris (per the 08-21 call).**
Send the package for the Levanto team to test in their harnesses; they launch.
Credit: Austin/BG per Chris's request. Iterate on their feedback for a week.

**Phase 4 — the Aug build feeds back in.**
The $1 audit injection gate (due ~Aug 31) is implemented *by following the
skill*, which both ships the monthly build and stress-tests the skill's
instructions end-to-end. Its eval (replayed KV-store verdicts + job 406 as the
regression case) becomes the flagship worked example inside the skill. Tweet
thread: 700 audits, detections, savings — "effective → efficient, month one."

---

## 5. Open items

1. **Chris's ASCII animation is not on this machine.** Searched `~/sage`,
   Downloads, `~/clawd`, Gmail — the zip Chris sent (per the 08-21 call) isn't
   anywhere findable. **Austin: drop the zip into `~/sage/` and the intro.sh
   slot is ready for it.** Building with a placeholder banner until then.
2. **Need a `lv_live_...` key in the environment** for Phase 0/2. No key is on
   disk by design.
3. **Batch billing still unverified** (OPEN-QUESTIONS #3) — matters more now
   that v0.7 makes batch-16 the flagship pattern. Check credit balance around
   a known batch during Phase 0.
4. **Naming/branding**: Chris wants a launch; Austin's instinct is unbranded
   iteration first. Current split: build it as `sage-wisdom`, hand it over,
   let Levanto do the branding push while we keep using it raw.
5. **Source of truth**: this dir is an untracked copy; changes worth keeping
   also belong in `~/clawd/clawd-harness/projects/clawd-research/levanto-sage/`.
