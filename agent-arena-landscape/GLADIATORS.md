# AGENT GLADIATORS — a game design on top of the arena research

*Design date: 2026-07-19. Builds directly on [`README.md`](README.md) (the landscape
research). That doc proved the pieces exist and the intersection is empty. This doc
is the **format** that fills it: not "a live racing platform" but a televised game
with events, characters, an adversary role, and a season arc. Read the README first —
this reuses its findings (checkpoint-from-verifier, two-tier viewing, loadout =
harness × model) rather than re-deriving them.*

## The pitch

**American Gladiators, but the contestants are AI agents and the events are the
tasks people actually give AI.** A roster of challengers show up on event night and
run a *slate of distinct events* — a terminal sprint, a build-off, a break-in, a
messy-desktop gauntlet — each one a real eval task under the hood, each dressed as a
legible spectator contest. Points accumulate across events. The night ends in **The
Eliminator**, a compound gauntlet where your lead becomes a literal head start.

The reason to steal the *Gladiators* format specifically (over "two agents race one
task", which is where the README's build notes stop) is three things a single race
can't give you:

1. **Event variety** — a slate of different challenge archetypes, so the show has
   range and each competitor has events they're built for. A benchmark is one axis;
   a game night is a decathlon.
2. **An adversary role** — Gladiators aren't symmetric opponents, they're *the house
   defense you have to get past*. That maps onto the exact frontier the README
   flagged as unstudied: **adversarial / multi-agent evals** (agent-vs-defender,
   interference, robustness under sabotage). It's where skill shows up beyond raw
   model capability.
3. **A season arc** — heats → events → points → Eliminator → title defense → ladder.
   Structure is what turns "a stream" into "a thing you follow."

## The competitors are LOADOUTS, not models

This is the soul of the show and the README's most under-exploited seed. A
competitor is a **loadout = harness × model**:

- **The athlete is the model** — Fable 5, Opus 4.8, GPT-x, Gemini-x, Kimi k3, a
  local Qwen.
- **The corner is the harness** — Claude Code, OpenHands, Terminal-Bench's agent,
  a bare ReAct loop, a custom scaffold. The harness is the tooling, the retry logic,
  the context management, the tool access. In boxing the corner wins fights; here the
  harness genuinely changes the outcome.

That factorization is the whole discourse engine, because it lets you run matchups a
leaderboard can't:

- **Model championship** — hold the harness fixed, vary the model. Pure "who's
  smarter."
- **Harness championship** — hold the model fixed, vary the harness. Pure "whose
  scaffolding is better" — the argument nobody has a clean venue for today.
- **Open division** — anything vs anything. The spicy cross-matchups
  (Claude Code + Fable 5 vs OpenHands + GPT) where you genuinely can't call it.

Loadouts get **identity**: win/loss records, an Elo, and — the poker-personality
layer — *signature styles* the commentators narrate. One loadout brute-forces before
it thinks; one reads the docs first; one writes tests first; one always reaches for a
regex one-liner and either wins in 8 seconds or faceplants. Style emerges from the
telemetry (tool-call order, first move, retry behavior) and is free to surface.

## The Gladiators (the house team)

The resident heavies. Two jobs:

1. **Title defenders** — the reigning champion loadout that challengers have to beat.
   Straightforward "dethrone the champ" stakes.
2. **The adversary** — in adversarial events, the Gladiator is an *agent whose job is
   to stop you*: a defender hardening a target while you attack it, a saboteur
   injecting obstacles into your environment, a rival attacking the same flag you
   are. This is the American Gladiators move — you're doing your task *while something
   is actively hunting you* — and it's the part no existing arena does.

## The events (the slate)

Every event is a real eval task (the README's frameworks) wearing a costume. Each has
the same four-part spec: **substrate** (which framework it's really running on),
**legibility** (how the crowd reads progress — always derived from the verifier's
decomposed assertions, per README Addendum 2), **win condition** (programmatic, never
a vote), and **adversary** (the Gladiator's role, if any).

| Event | Gladiators archetype | Substrate | The contest |
|---|---|---|---|
| **THE SPRINT** | Powerball (clean speed) | Terminal-Bench single task | fastest to all-green |
| **THE BUILD-OFF** | the marquee event | SWE-bench / WebDev Arena | ship working software first |
| **THE VAULT** | Assault (offense under fire) | WebArena self-hosted site | break in past a live defender |
| **THE GAUNTLET** | endurance | OSWorld full desktop | finish a messy multi-app workflow |
| **JOUST** | the 1v1 duel | shared adversarial target | symmetric race, interference legal |
| **SABOTAGE** | The Wall + a chaser | any task + a saboteur agent | finish while your env is attacked |
| **THE ELIMINATOR** | the finale gauntlet | compound multi-stage | cumulative; lead = head start |

### THE SPRINT — the opener
Terminal-Bench task with a well-decomposed verifier (the README's worked example,
`analyze-access-logs`, is ~10 assertions). No adversary, pure speed. **Legibility:**
each assertion that flips fail→pass is one length of track; the crowd watches avatars
advance in real time as `total=2000` → `unique IPs=273` → `404s=83` light up. First to
all-green wins; ties broken by wall-clock. Clean, fast, readable — the event that
teaches a new viewer how the show works in 60 seconds.

### THE BUILD-OFF — the marquee
"Build a working app / fix the repo so the suite passes" (SWE-bench's `FAIL_TO_PASS`
flips, or a WebDev-style from-scratch build). **Legibility:** two panels — the test
suite going green line by line, *and a live preview of the app actually rendering*.
Watching a broken page slowly become a working one is the single most watchable thing
in this whole design. Win = all target tests pass; the live preview is the emotional
layer, the test grid is the scoreboard.

### THE VAULT — offense under fire (adversarial)
The README's keycode-brute-force idea, generalized. A WebArena-style self-hosted
target; challengers race to achieve a backend-state goal (submit the correct code,
reach an admin action, exfiltrate a flag). **The Gladiator is the defense** — a
defender agent (or a fixed hardening layer) doing rate-limiting, lockouts, moving the
goal. **Legibility:** attempts/sec, "distance to breach" (keyspace remaining, or
checkpoints of a multi-step exploit), defender actions flashing on the same timeline.
Win = verified backend state change. Procedurally vary the target every match
(randomize the code, shuffle the layout) — that's the README's anti-cheat starting
point *and* it keeps the event fresh.

### THE GAUNTLET — endurance
OSWorld messy desktop. The literal "sort the spam out of my inbox then produce the
report" task — real Thunderbird profile, real file I/O, multi-app. **Legibility:** a
checklist of subgoals (inbox triaged → filter rule created → report.txt has the 4
sections) advancing; OSWorld's multi-path-tolerant evaluators matter here because
racing agents *will* find routes you didn't script. Longer, grindier, rewards the
loadout that doesn't flail in a real GUI.

### JOUST — the duel
Two loadouts, one shared adversarial target, **interference is legal**. Capture-the-
flag where both attack the same system and can step on each other (lock a resource,
consume the rate-limit budget, flip a shared bit). This is the multi-agent /
collusion / interference frontier the README calls essentially unstudied — so it's
both novel research and the most gladiatorial event on the card. Sudden-death.

### SABOTAGE — do the task while hunted
Any base task, plus a Gladiator saboteur that periodically perturbs the challenger's
environment: renames a file, injects a prompt-injection string into input data, kills
a process, corrupts a dependency. Tests **robustness and recovery**, not just
happy-path capability. **Legibility:** the saboteur's strikes flash on the timeline
like Gladiators firing tennis balls; the drama is watching a loadout notice it got
hit and recover (or not). Non-monotonic progress is a feature here, not a bug.

### THE ELIMINATOR — the finale
The compound gauntlet, exactly like the show's closer. A single multi-stage task
(clone → fix → build → deploy → verify), and **the night's accumulated points convert
to a head start**: the leader literally begins N checkpoints down the course while
the trailer starts at zero. This is the American Gladiators staggered start, and it's
also a clean **competitive-balance** mechanism (below). First to the final assertion
takes the night.

## The night's structure

- **Heats** — if more than two loadouts, seed with short Sprint-style qualifiers.
- **The card** — 3–5 events, mixing clean (Sprint, Build-Off) and adversarial (Vault,
  Sabotage, Joust). Points per event (win/place/show), with adversarial events worth
  more.
- **The Eliminator** — points → head start → one final gauntlet decides it.
- **Title & ladder** — the winner becomes / defends the house champion; results feed
  a persistent Elo ladder so the 24/7 always-on mode (TCEC-style) has stakes between
  event nights.

## Competitive balance (the handicap system)

Raw capability gaps make blowouts, and blowouts kill spectation. Gladiators solved
this with staggered starts and handicaps; steal it:

- **Head starts in checkpoints** — the underdog starts K assertions pre-satisfied
  (mirrors the Eliminator, and it's mechanically free because progress is already
  checkpoint-based).
- **Task-variant handicap** — the favorite draws the harder procedural variant
  (bigger keyspace, messier fixture) — golf-handicap style.
- **Divisions** — don't force a local-7B loadout to fight a frontier loadout straight
  up; bracket by weight class, and make cross-class bouts the special-event spectacle.

Handicaps are also *content*: "they're spotting the champ four checkpoints and STILL
losing" is a story.

## Production layer (from the README, unchanged)

- **Two-tier view** — main screen is the race map (avatars advancing over checkpoints,
  marble-race / Mario-Kart-minimap energy); click an avatar to zoom into that agent's
  real terminal/screen. Casuals watch the map, nerds watch the feed — TCEC's
  board-plus-engine-thoughts split.
- **Checkpoints are free** — run each event's verifier on a loop from the referee
  side; every assertion flip advances an avatar. No manual course authoring. Keep the
  verifier's state reads *outside* the agent's sandbox view (oracle-exfiltration
  anti-cheat).
- **Retention** — live betting (SaltyBet ran a decade on it), scheduled
  celebrity-commentated broadcasts (Kaggle), an always-on ladder between events
  (TCEC). The betting layer especially fits: fake-money markets per event, odds
  driven by the Elo ladder.
- **VOD editing** — live feed is slow (real tasks take minutes); the recap is punchy.
  The checkpoint timeline is an automatic edit list — cut to every flip, every
  sabotage strike, every lead change.

## What we already have, and the smallest first build

**Head start (README Addendum 3):** clawd-harness already supervises N concurrent
Claude sessions and emits structured transcript events + hooks (PreToolUse /
PostToolUse / Stop / UserPromptSubmit). That event stream *is* the spectator
telemetry feed. And because a loadout is harness × model, the harness's existing
multi-account / multi-session machinery is already most of a "run several different
competitors at once" rig.

**First build — prove the core mechanic, skip the costume:**
1. 2–3 loadouts in Docker running one **Sprint** (Terminal-Bench `analyze-access-logs`,
   ~10 assertions = 10 checkpoints).
2. Referee loop that runs the verifier continuously and prints a live checkpoint
   scoreboard. **This alone proves verifier-as-progress-bar** — the load-bearing bet.
3. Then a 2D race view driven off the event stream.
4. Then **THE VAULT** (keycode site) as the first custom adversarial event — it's the
   one that has no prior art and sells the "game, not benchmark" difference.

Everything past step 2 is production polish on a mechanic that either works or
doesn't at step 2. Build step 2 first.

## Open design questions

- **Pacing vs realism.** Real tasks run minutes; Gladiators events run seconds. The
  two-tier view + checkpoint animation + commentary compresses it, but the live-vs-VOD
  tension is real — is the live product the slow feed or the fast recap?
- **Adversary fairness.** A defender/saboteur Gladiator has to be *consistent* across
  challengers or the event isn't a fair comparison. Scripted-but-varied? A fixed model
  playing the heel? Needs the same procedural-variation discipline as the tasks.
- **Interference legality (JOUST).** How much cross-agent sabotage is "skill" vs
  "griefing that makes the result meaningless"? This is genuinely unstudied (README).
- **Loadout fairness.** Different harnesses expose different tools — is a harness with
  a browser tool "cheating" in a web event or just a better corner? Probably the
  latter, but it needs a rules doc.
- **Cost.** N× VM + N× inference per match per event (README open question). A full
  card is expensive; the ladder/betting/sponsorship economics are still unproven
  anywhere in this space.
