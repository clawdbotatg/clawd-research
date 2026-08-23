# Agent distillation — naming the "effective → reliable → cheap" process

*Brainstorm, 2026-08-23.*

**The pattern:** let a frontier model rip on a problem with full autonomy until it
works; document what it did; run it again with the doc; then progressively
replace the squishy, non-deterministic brain with something deterministic,
cheap, and fast — until the LLM is only handling exceptions.

## Names

| Name | From | Captures | Misses |
|---|---|---|---|
| **Agent distillation** | ML teacher→student | frontier = teacher, script/cheap model = student; behavior preserved, cost drops | the fallback path |
| **Tracing JIT / trace compilation** | PyPy, LuaJIT, V8 | interpreter (frontier) runs first; hot path recorded + compiled; **guards** assert assumptions; **deopt** falls back to the interpreter on guard failure | needs explaining outside eng |
| **Annealing** | metallurgy / simulated annealing | explore hot, cool slowly, stable crystal at the end; LLM temperature pun is free | implies one-shot; real loop re-heats |
| **Hardening** | security / metallurgy | reliability + determinism | cost |
| **Crystallization** | chemistry | liquid → lattice | not operational |
| **Proceduralization / knowledge compilation** | Anderson ACT-R (1982); Fitts & Posner 3-stage skill acquisition: cognitive → associative → autonomous | exactly the three phases: figure it out / document + fewer errors / automatic + cheap | academic |
| **Amortization** | amortized inference | pay the frontier once, amortize over N runs | only the cost angle |
| **Routinization** | Weber | charisma → bureaucracy | sounds boring (which is the point) |

Kent Beck's *make it work → make it right → make it fast* = **effective → reliable → cheap**.

**Recommendation:** say *distillation* to people; design it as a *tracing JIT*
(because that model forces you to build guards + deopt); keep *annealing* for
the talk title.

## The ladder (what the process actually is)

The LLM retreats one rung at a time, from "does everything" to "handles exceptions."

0. **Rip** — frontier model, max autonomy, human in loop. Capture the full trace
   (transcript, tool calls, dead ends).
1. **Trace** — extract the successful trajectory. Needed vs. wandered. Dead ends
   become "don't do X" lines.
2. **Codify** — SKILL.md / runbook / contracts. Re-run the frontier *with* it.
   Fewer tokens + fewer turns ⇒ the doc works.
3. **Downgrade** — cheaper model following the doc. Run N times, measure pass
   rate. Needs an eval (→ `simple-eval/`).
4. **Fence** — replace LLM steps with deterministic code wherever the output is
   deterministic. LLM survives only at judgment points (messy input, branch
   decisions).
5. **Guard** — assertion at every step + independent verifier. Guard failure
   **escalates back to the frontier** (the deopt); the frontier's fix is folded
   back into the doc/code. This is what makes it a loop instead of one-way decay.
6. **Measure** — the scalar: **LLM tokens per successful run → 0**, plus pass
   rate and p50 latency per rung.

Asymmetry: going *down* the ladder is cheap and deliberate; going back *up*
(deopt) is expensive and automatic. That is the JIT shape.

## Prior art / adjacent

- **Voyager** (Wang et al. 2023) — agent writes reusable skills from successful
  trajectories into a skill library. The academic precedent for rung 1→2.
- **DSPy** calls prompt optimization "compiling." Karpathy's Software 3.0 → the
  trip back to Software 1.0.
- Anthropic *Building effective agents*: this process is the move from "agent"
  back toward "workflow."
- **Expert systems / knowledge engineering** (1980s): interview the expert,
  codify rules. Now the expert is the frontier model.
- Cog-sci: Kahneman System 2 → System 1; Soar "chunking."

## What we already have

- The `agentify-task` skill (harness) *is* rungs 2–5: contracts, gated
  idempotent orchestrator, independent verifier, cold-start runbook.
- **Gaps** if this becomes a named methodology: rung 5's escalation path
  (script fails → re-invoke frontier with the failure → diff the fix back in) and
  rung 6's metric (tokens per successful run, tracked per rung over time).
