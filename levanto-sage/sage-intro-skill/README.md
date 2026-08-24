# Sage Intro — animated ASCII first-run banner

Animated terminal intro for the Sage onboarding skill (Claude Code / Codex).
~7.5s sequence: the Levanto arch fades in, sun rises over rippling water, the
SAGE wordmark lands, then five real Sage decisions fire in an accelerating
cascade — one for each decision kind (yes/no, scale, choice, sort, tags):

    "is this tool call safe to auto-run?"    ──▶  yes · confidence 0.94 · 212ms
    "how well does this PR match its spec?"  ──▶  4/10 · confidence 0.88 · 198ms
    "which model tier does this need?"       ──▶  small · confidence 0.91 · 187ms
    "1,000 open tickets: which one first?"   ──▶  #4712 · confidence 0.83 · 341ms
    "what kind of data did the user paste?"  ──▶  pii · confidence 0.97 · 178ms

`preview/sage-intro-preview.gif` shows the intended motion.

## Files

- `scripts/sage-intro.sh` — the whole thing. One file, zero dependencies,
  bash 3.2+ (stock macOS bash works). No figlet, no python, no npm.

## Usage

    bash scripts/sage-intro.sh              # animate (TTY only)
    bash scripts/sage-intro.sh --static     # print the final card, no animation
    bash scripts/sage-intro.sh --dump-all   # every frame, \f-separated (for tooling)

## Built-in degradation (no flags needed)

The script self-selects the right output, so the skill can call it blindly:

| Context                              | Behavior                          |
|--------------------------------------|-----------------------------------|
| Interactive TTY, ≥79 cols            | full ~7.5s animation              |
| Not a TTY (agent Bash tool, pipes)   | static final card, still colored  |
| Terminal narrower than 79 cols       | static final card                 |
| `NO_COLOR` set                       | monochrome                        |
| No truecolor (`COLORTERM` unset)     | 256-color palette fallback        |

## Wiring it into the skill

Important nuance: when the **agent** runs the script through its Bash tool,
there is no TTY — the harness captures output and does not emulate cursor
movement. The script detects this and prints the static card, which renders
cleanly in the transcript. The **full animation** plays only in the user's own
terminal. Recommended first-run flow in SKILL.md:

1. On first invocation, the agent runs
   `bash <skill-dir>/scripts/sage-intro.sh`
   → the static Sage card appears in the transcript immediately (instant
   visual value, zero risk).
2. The agent then offers the live version, e.g.:
   "Run `bash <skill-dir>/scripts/sage-intro.sh` in your terminal to see the
   full intro" — in Claude Code the user can just type
   `! bash <skill-dir>/scripts/sage-intro.sh`.
3. Track first-run however the skill prefers (e.g. touch a
   `.sage-intro-shown` marker next to the script) so the banner doesn't
   replay on every invocation.

## Tuning

All content is data at the top of the script: `Q1..Q5` (questions),
the `rapid` calls in `draw_frame` (answers/confidences/latencies/timing),
`TAGLINE`, and the color table (brand: teal on #0E6A5C family, cream #FBF7EF,
gold sun). Frame timings live in `frame_delay`. Questions must stay ≤ `QPAD`
(39) chars so the arrows column-align; the widest line is 79 cols.
