# simple-eval

One cheap score for any LLM or harness. 60 original tasks, 6 categories
(reasoning · code · instructions · extract · precision · context), all graded
programmatically — zero judge tokens, ~40–60k tokens per full run. Design and
rationale: [PLAN.md](PLAN.md).

## Run it

```bash
# verify the graders (zero tokens, must print 60/60)
python3 run_eval.py --self-test

# any OpenAI-compatible endpoint (ollama, bankr, openrouter, ...)
python3 run_eval.py --name qwen3-coder \
  --base-url https://llm.bankr.bot/v1 --model qwen3-coder \
  --api-key-env BANKR_API_KEY --auth xapikey

python3 run_eval.py --name qwen3-local \
  --base-url http://localhost:11434/v1 --model qwen3:8b

# any CLI harness (prompt on stdin, response on stdout)
python3 run_eval.py --name fable --cmd 'claude -p --model claude-fable-5' --concurrency 4

# the leaderboard
python3 report.py
```

Overall = mean of category means, with a 95% bootstrap CI printed alongside —
with 60 items the CI is ±4–6 pts, so treat small gaps as noise (use `--runs 3`
to tighten). Results are saved to `results/<name>.json` and committed; the
leaderboard is the point.

Notes: `--cmd` scrubs `CLAUDECODE`/`CLAUDE_CODE_*`/`ANTHROPIC_API_KEY` from the
child env so a nested `claude` runs as a real subscription session. `claude -p`
may use tools (running code, etc.) — that's the harness being evaluated, not
cheating.
