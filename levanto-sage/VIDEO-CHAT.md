# Sage for the clawd-video-chat filler loop

*Austin's idea, tested live 2026-07-28 against
`~/clawd/random-agent/clawd-video-chat/server.py` `handle_filler()` (line 561).*

**Verdict: strong fit, and it fixes a structural limitation the current design
had to work around. One batch call, ~377ms, ~$0.89/1k turns, and it lets the
filler finally *know what was said*.**

## The insight: Sage can see the question. Haiku can't.

The most interesting thing in `handle_filler()` isn't the prompt — it's the
comment above it (server.py:586-592):

> *"CRITICAL: the ack must NEVER answer the user's question… We deliberately do
> NOT pass the user's message (or history) into this prompt: if Haiku can see
> the question it slips into answering it ('Yes, I can hear you'), which then
> double-speaks once the real brain answers the same thing. With the question
> hidden, the worst it can do is stall."*

The same defensive blindness appears again for the `thinking` kind: reasoning
text is deliberately withheld because *"for simple questions the reasoning IS
the answer."*

So today's ack is **blind by necessity** — it fires a temp-1.0 Haiku call that
has no idea whether you asked "can you hear me?" or "walk me through building
an x402 paywall," and picks a stall noise at random.

**Sage cannot leak the answer, because it cannot produce text at all.** It only
scores options you supply. You can hand it the full user utterance with zero
double-speak risk — there is no channel through which it could answer. That
turns the filler from *blind* to *informed* without reintroducing the failure
mode the comment is guarding against.

## What works (and what doesn't)

**`scale` for complexity — excellent.** Ranked our nine test utterances
sensibly and monotonically: mic check 0.0, capital of France 0.8, joke 0.3,
philosophical question 2.5, "explain prompt caching" 1.9, repo investigation
3.9, x402 walkthrough 3.9.

**`choice` for picking the utterance — fails.** Tested first with five
utterance categories and rich descriptions; it answered `acknowledge` for
almost everything, including the joke and the philosophy question (2/8 varied).
Same saturation seen in the routing benchmark — `choice` collapses to a default.

**`yesno` flavor questions + a deterministic mapping — works.** Three binary
questions discriminate cleanly, and the utterance is then derived in code (free,
no second call):

| utterance | cx | playful | opinion | tools | → pick | recap? |
|---|---|---|---|---|---|---|
| "can you hear me okay?" | 0.0 | 0.35 | 0.31 | 0.06 | acknowledge | – |
| "what's the capital of France?" | 0.8 | 0.41 | 0.01 | 0.11 | *thinking* ⚠ | – |
| "tell me a joke about ethereum devs" | 0.3 | **0.98** | 0.52 | 0.03 | amused | – |
| "what do you think about where AI agents are heading, philosophically" | 2.5 | 0.06 | **0.97** | 0.02 | intrigued | YES |
| "look at the leftclaw repo and figure out why job 406 fails, propose a fix" | **3.9** | 0.07 | 0.02 | **0.91** | working | YES |
| "explain prompt caching, 1h vs 5m TTL" | 1.9 | 0.05 | 0.30 | 0.09 | thinking | – |
| "hmm... so... what was I saying" | 0.5 | 0.77 | 0.39 | 0.08 | amused | – |
| "walk me through building an x402 paywall from scratch" | **3.9** | 0.06 | 0.02 | 0.28 | working | YES |
| "you're being kind of slow today buddy" | 0.0 | **0.95** | 0.20 | 0.06 | amused | – |

⚠ one miss: "capital of France" landed at cx 0.8, just over the 0.8
acknowledge cutoff, so it picked *thinking* instead of *acknowledge*. Fix by
raising the cutoff to ~1.0 — a threshold tune, not a model failure.

**One batch call: ~377ms median, ~297 tokens, $0.892 per 1,000 turns.**

## Proposed architecture

```
user speaks
   │
   ├─► Sage (ONE batch call, ~377ms) ─► complexity 0-4 + playful/opinion/tools
   │        │
   │        ├─ utterance category  ─► speak canned audio IMMEDIATELY
   │        │                          ("Hmm." / "Ooh." / "Ha." / "Let me dig into that.")
   │        └─ complexity ≥ 2      ─► fire Haiku recap to cover the long wait
   │                                  complexity < 2 → skip it, brain lands first
   └─► frontier model (the real answer)
```

**Three wins over the current loop:**

1. **The first utterance fits the input.** A joke gets "Ha," a philosophical
   question gets "Ooh," a repo dig gets "Let me dig into that" — instead of a
   random draw from one blind pool.
2. **The recap becomes conditional.** Today the stall machinery runs the same
   way regardless. Complexity ≥ 2 is a genuine "this will take a while" signal,
   so Haiku's recap only fires when there's actually air to fill. On simple
   turns you skip a Haiku call *and* avoid the awkward recap-then-immediate-
   answer collision.
3. **Latency.** ~377ms for Sage vs ~800ms measured for a Haiku call through
   Bankr (see RESULTS.md). Worth noting: **canned audio beats both.** Since the
   five utterance categories are a fixed set, pre-render them as audio files
   once and the first sound lands in ~377ms + playback rather than waiting on
   TTS. That is the single biggest perceived-latency win available here.

## Integration sketch

Add a `kind: "route"` branch to `handle_filler()` that returns the scores
rather than text, and let the client drive:

```python
# server.py, new branch in handle_filler()
if kind == "route":
    scores = sage_batch(last_user)   # complexity + playful + opinion + tools
    self.send_json({
        "utterance": utterance_for(scores),   # deterministic mapping, free
        "complexity": scores["complexity"],
        "needsRecap": scores["complexity"] >= 2.0,
    })
```

Client: play the canned clip for `utterance` immediately; if `needsRecap`, fire
the existing Haiku `/api/filler` path (which may now safely be a *recap* rather
than a blind stall — see caveat below). Keep the existing `thinking` stall for
turns that run long past the recap.

## Caveats

- **The recap still needs the double-speak guard.** Sage gates *when* to recap;
  it does not make Haiku safe to show the question. If the recap paraphrases the
  ask ("so you want to know about x402 paywalls…") that is fine and is the point
  — but it must still be forbidden from answering. Keep the existing hard rules
  in that prompt; only the *timing* changes.
- **Fail open, like everywhere else.** If Sage errors, fall back to today's
  blind-Haiku ack. A filler is cosmetic — it must never block a turn.
- **Nine test utterances is a sketch, not a calibration.** Re-tune the
  complexity cutoffs (currently: <0.8 acknowledge, ≥2 recap, ≥3 working) against
  real session transcripts — video-chat presumably has plenty logged.
- **Cost is real but tiny in context:** $0.89/1k turns against a voice session
  that is already paying for Haiku fillers *and* a frontier model per turn. If
  the conditional-recap logic skips even a fraction of Haiku calls, Sage likely
  pays for itself.
