# Open questions — what we did NOT do

Research state as of 2026-07-28. Everything here is deliberately deferred, not
forgotten. Each item says what's unknown, why it matters, and how to close it,
so a future session can act without re-deriving the context.

**Nothing is wired into production.** Both "production fits" (INJECTION.md,
VIDEO-CHAT.md) are benchmarked designs with runnable harnesses. No code in
leftclaw-services or clawd-video-chat has been changed.

## You will need a key

No API key is stored on disk anywhere in this repo, by design. The benchmarks
read `SAGE_API_KEY` from the environment. Ask Austin for a `lv_live_...` key
before running anything; the account is prepaid with no free tier, so calls
spend real credits (though the whole research effort cost well under a cent).

## Blocking-ish, cheap to resolve

**1. Thresholds are set from synthetic samples, not real traffic.** The
injection gate's 0.60 / 0.40-escalate operating point comes from 12 samples I
wrote; the video-chat cutoffs from 9 utterances I wrote. The approach is
validated, the operating point is not — and Sage scores are non-deterministic
run-to-run, so a single sweep is doubly weak evidence.
*How to close:* leftclaw's KV store holds every historical verdict — replay
those real descriptions through `demo_injection.py` and set the threshold from
the actual distribution. Same for video-chat: it logs session transcripts.
Cheap enough to run exhaustively.

**2. Job 406 is the natural regression test.** `sanitize.ts` references a real
incident — "a hijacking-shaped description made every check fail." That is
exactly the payload class the Sage gate claims to handle. Pull it and run it
before trusting any of this.

**3. Batch billing is unverified.** Responses carry no usage/token field, so
Levanto's "content is sent once for N questions" claim is a wire-format
statement we could not confirm is also a *billing* statement. Our cost figures
estimate tokens at `len(body)//4`.
*How to close:* note the credit balance, fire a known batch, note it again. Only
matters if a design leans on a batch discount — the injection gate (single
question) does not; the video-chat router (4 questions) does.

**3b. Batch-16 is unbenchmarked.** Levanto (2026-08-21) says up to 16
questions per call return in ~150–200ms total. Nothing here has measured it;
`demo_videochat.py` batches 4. *How to close:* extend `demo_latency.py` with
1/4/8/16-question batches and record p50/p95.

## Known coverage gaps

**4. Adversarial robustness is untested.** Every injection sample is English and
unobfuscated. Base64, homoglyphs, zero-width characters, non-English, and
instructions split across a long document are all unknown. A classifier that
scores 12/12 on plain-English overrides may do much worse on encoded ones, and
this is a security path.

**5. Grounding was never exercised.** The web-search feature (+$0.01 per
executed search) is documented in REPORT.md but never called. It's the one part
of the API with a per-call cost that dwarfs the token cost — 1 search ≈ the
token cost of ~50 terse decisions — so any design using it needs its own cost
model.

**6. No load or failure-mode testing.** No documented rate limits, no status
page found, no SLA. We never hit it concurrently, never saw it fail under load,
and don't know what it does at burst. Every design here fails open, which is the
right hedge, but "fails open" was never actually tested against a real outage.

## Worth doing, not urgent

**7. The `sort` kind is the least explored.** Used once, lightly. It's the
natural fit for several USE-CASES entries (ranking sessions by "needs
attention", ordering a work queue) and we never benchmarked its quality or
established whether its single list-level confidence is thresholdable.

**8. Correlate Sage against simple-eval.** We have a house eval suite
(`clawd-research/simple-eval`, 60 tasks, deterministic grading). Running Sage's
judgment against known-correct answers would give a real accuracy number on
our own data rather than on hand-written samples.

**9. Re-verify on model bump.** Everything here is `levanto-sage-v0.6`. Check
`meta.model` on any response; if it moved, re-run `demo_calibrate.py` before
trusting any threshold in these docs. Calibration is the thing most likely to
shift silently.

## Decisions that were made and should not be relitigated

- **`choice` and `tags` are out.** Both failed on separate tasks for
  structural reasons (saturation; no per-tag description field). Build on
  `yesno` ensembles + `scale` with the mapping in code. See API-NOTES.md.
- **Sage is not the cheap option.** It lost on price to qwen3-coder by ~75×.
  Reach for it when latency, wire-format certainty, or the can't-generate-text
  guarantee is what you need — not to save money on bulk classification.
- **Fail open, everywhere.** Matching leftclaw's existing philosophy, and
  correct on cosmetic paths regardless.
