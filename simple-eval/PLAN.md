# simple-eval — one cheap score for any LLM or harness

Goal: run one command against *anything* — local qwen on ollama, a bankr/openrouter
model, `claude -p` on the subscription — and get back a single defensible number,
so we can say **"Fable scored 87.8 tonight; Opus 4.8 scored 82.5."**

## TLDR: how people eval LLMs today (and why we roll our own)

- **Academic benchmarks** (MMLU, GPQA, MATH, HumanEval, MBPP) — run via
  `lm-evaluation-harness`. Saturated and contamination-poisoned for frontier
  models (they've seen the test set); still fine for sanity-checking a small
  local model. Thousands of items = slow + token-hungry.
- **Agentic benchmarks** (SWE-bench, Terminal-Bench, Aider polyglot,
  LiveBench) — closest to real work, but a single run is hours and millions of
  tokens. Great for papers, terrible for "score three models tonight."
- **Arena / preference** (LMArena Elo) — vibes at scale; you can't run it
  yourself and it can't score *your* harness.
- **LLM-as-judge** — flexible grading, but burns judge tokens and carries known
  biases (self-preference, verbosity preference). We avoid it entirely.

The pragmatic move for a house eval: **small, private, novel items with
deterministic programmatic graders.** Nobody trained on our questions, grading
costs zero tokens, and a full run is cheap enough to do nightly.

## Design

**60 original tasks, 6 categories × 10.** All authored fresh here (no
contamination), all machine-gradable:

| category | what it tests | grader |
|---|---|---|
| `reasoning` | multi-step word problems, novel setups | numeric answer, tolerance match |
| `code` | write a small python function | hidden unit tests run in a subprocess |
| `instructions` | precise instruction-following (IFEval-style) | programmatic constraint checkers |
| `extract` | messy text → structured JSON | schema + field-value validation |
| `precision` | exact text/data manipulation (sort, dedupe, transform) | exact / normalized match |
| `context` | Q&A over a ~2k-token document with distractors | exact / regex match |

**Targets** (the "any LLM or harness" part):
- `openai:<base_url>:<model>` — covers ollama, bankr (`llm.bankr.bot`),
  openrouter, anything OpenAI-compatible. Concurrent requests.
- `cmd:<shell template with {prompt}>` — covers `claude -p --model X`, codex,
  any CLI harness. Scrubs `CLAUDECODE`/`CLAUDE_CODE_*`/`ANTHROPIC_API_KEY` from
  the child env (the nested-claude embedded-mode trap from clawd-harness).

**Scoring:**
- Per-category % + **overall = mean of category means** (categories weigh
  equally; a code-heavy model can't swamp the score).
- **95% bootstrap CI on the overall** — printed with every score, so we know
  when a gap is real. With 60 items the CI is roughly ±4–6 pts: 87.8 vs 82.5
  means something; 87.8 vs 86.9 is noise. `--runs N` repeats the suite to
  tighten it.
- Results land in `results/<name>.json`; `report.py` prints the leaderboard
  across all saved runs.

**Token budget:** ~40–60k tokens per full run (prompts are short, responses
capped). Fractions of a cent on cheap APIs; a few minutes of subscription time
via `claude -p`.

**Self-test (zero tokens):** every task ships a reference answer.
`run_eval.py --self-test` grades all 60 references and must score 100% — that's
how we know the graders are right before blaming a model.

## Build phases

1. **Scaffold** — `run_eval.py` (targets, concurrency, retries), graders,
   `tasks/*.jsonl` format, `--self-test`.
2. **Author the 60 tasks** — the real work; original items only.
3. **Green self-test** — 60/60 on reference answers.
4. **Demo runs** — a cheap bankr model for sanity, then `claude -p` haiku vs
   opus vs fable for the headline comparison.
5. **Leaderboard** — `report.py` over `results/`.

## Honest limits

A 60-item eval ranks models coarsely; it will not resolve 1-point gaps and it
tests *skills that proxy for* agentic work, not agentic work itself (no tool
use, no long horizons — that's what agent-arena is for). It's a thermometer,
not a physical.
