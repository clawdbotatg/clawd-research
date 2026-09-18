# Where Jev fits in our stack (2026-09-17)

Two different things came out of this week:

1. **browser_run** (fast hands in a real Chrome tab, shipped in clawd-browser-extension 0.9.0).
2. **Jev the API** (a calibrated pick-one/yes-no scorer, ~150 ms, $0.042/Mtok input).
   Same shape as Levanto Sage, ~70x cheaper. Everything in `../levanto-sage/USE-CASES.md`
   Part 2 (22 of our own fits) applies unchanged; the cost objection to Sage is gone.

Ranked by payoff / effort, against repos touched in the last three weeks.

## Tier 1: build next

| # | Where | What | Shape | Why now |
|---|---|---|---|---|
| 1 | clawd-harness `_pilot` (`PILOT_MODEL`, server.py ~774) | The autopilot supervisor asks Haiku "continue / needs_human / done" every Stop. Put Jev in front: a `choice` on the transcript tail decides continue vs needs_human vs done; only `continue` pays for the Haiku call that writes the next prompt. | choice + noul | Autopilot runs on every session on every box. Haiku is ~2 s and a full call per Stop; Jev is 150 ms and can't drift into prose. Halves pilot spend, and "done at 40%" becomes a real signal. |
| 2 | clawd-harness Stop hook | Notification-worthiness gate: "does this finished turn need Austin now" → push / badge / silent by probability. | noul | Sage use-case #1, "the single best fit in our stack". Was blocked on Sage's price. |
| 3 | clawd-harness `/loop` + cron ticks | "Did anything change enough to act?" before spending a model turn. | noul | Every loop tick today is a full frontier turn to say "nothing changed". |
| 4 | mobile-ai-proto | Same jev loop over the phone WebView's command bridge (it already has read/click/type). The phone holds the cookies; Jev does the tapping; the server model plans. | browser_run port | Exactly the extension design, one more transport. |
| 5 | clawd-chatter | `addressed()` is regex (mention/reply/trigger word). Add "is this message asking the bot something?" so it can answer unaddressed questions without spamming. | noul | 150 ms per group message is nothing; the false-positive knob is the threshold. |

## Tier 2: cheap wins when we're in that repo

- **tweet-qa**: it asks Fable/GPT "anything glaringly wrong?" and explains. Jev can't explain, but a noul pre-check ("does this tweet contain a factual, spelling or grammar error?") at 150 ms decides whether to bother the big model at all, and gives the ✅ instantly for clean tweets.
- **clawd-harness limit banner / wedged session**: regex tripwires get a second opinion (Sage #3, #4).
- **Guardrails** (Sage #7–#10): secret-leak second layer on staged diffs, destructive-command gate before the PM types into a PTY, ship-vs-ask classifier for the ~/clawd autonomy rule. These are prose rules today; Jev makes them thresholdable.
- **leftclaw / onedollaraudit** injection gate: already benchmarked on Sage (12/12 at 0.60). Re-run the same harness on Jev; if it holds, it's 17x cheaper than Sonnet AND 70x cheaper than Sage.
- **slop computer live chat**: tag viewer messages, sort the gold. Per-message on a live stream.

## Anti-fits (don't)

- Anything that must **write** text: session names, TLDRs, commit messages, tweet fixes. Jev cannot.
- **browser_run on tasks with hidden targets**: filter popups, long dropdowns, infinite scroll. Proven fail.
- **Anything irreversible in a real browser**: buy/pay/send/post/sign. Keep the refusal list; it stays a human click.
- Bulk offline classification: a qwen-class model is still cheaper per token and can explain itself.

## What to measure before trusting any of it

Same lesson as Sage: `choice` confidence saturates, `noul`/yes-no ensembles calibrate. Sweep
phrasings first (`../levanto-sage/demo_calibrate.py` can be pointed at Jev in an hour), never set
a threshold from one run, and pin `jev-1.13.0` in production, not `jev-latest`.
