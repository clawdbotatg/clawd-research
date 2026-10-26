# PII/PHI sanitizer with a Sage exit check

Question (Austin, 2026-10-26): strip patient identifiers from medical text with a
cheap local model, swap in placeholders, send to a frontier model, swap the real
values back on return. How do we know the outbound text is clean? Idea: ask Sage
(now running in a TEE on NEAR AI, [announcement](https://x.com/near_ai/status/2114778299918368873))
as a last check before anything leaves.

**Short answer: it works on our test set.** With the right question format, Sage
caught every leak the local stripper missed, and nothing with PHI got sent. The
test set is small and hand-built, so this is a good sign, not proof.

- `LANDSCAPE.md` — how others do it, HIPAA rules, BAAs, tools, recall numbers, TEE question.
- `bench.py` + `cases.py` — Sage as a classifier on already-sanitized notes (50 short, 48 long).
- `pipeline.py` + `raw_cases.py` — the full loop on 50 raw fake notes.

## Result 1: how you ask Sage matters more than anything

Sanitized notes, 28 with one missed identifier, 22 clean (with traps: drug
names, eponyms, year-only dates, age 88, `[MRN_1]` placeholders). Two runs each;
scores were identical across runs.

| How we asked | Leaks caught (≥0.5) | Clean notes flagged | Input tok |
|---|---|---|---|
| one yes/no: "any identifier of a real person?" | 2/56 | 0/44 | ~140 |
| one yes/no: "any HIPAA identifier (name, date, …)?" | 48/56 | 0/44 | ~140 |
| 6 yes/no, one per identifier type, take max | 56/56 | 4/44 | ~6×140 |
| **one `tags` question, 6 tags, take max** | **56/56** | **0/44** | ~1,600 |

- A single "is it clean?" question misses things. It never flagged age 96, a
  photo reference, or the head-coach-of-a-named-school detail. The "real person"
  wording failed almost entirely, likely because the names look made up.
  The research matches this: yes/no judges under-report (LANDSCAPE.md §4).
- **Ask per identifier type.** `tags` with one line per type (name, date,
  contact, ID number, place, unique detail) was best: every leak scored 1.00,
  every clean note ≤0.13.
- The name tag needs "not a disease or drug named after someone". Without it,
  "Lou Gehrig's disease" gets flagged.
- Long notes (~200 words, one leak buried in the middle): still 56/56 caught,
  but "Lou Gehrig" got flagged again in 4/40 clean notes. That errs on the safe side.
- Cost: `tags` reads the note once per tag, so a check costs about 6× the note's
  tokens (~1.6K for a short note, ~4K for a 200-word one). Latency ~0.5–2 s.

## Result 2: the full loop

`raw note → regex (phones, dates, IDs…) → local Qwen lists remaining identifiers → placeholders → Sage tags check → if flagged, Qwen tries again, told which type was flagged (max 2 retries) → still flagged = block for a human → frontier → put real values back`

| | qwen3:8b | qwen3:14b |
|---|---|---|
| Notes with PHI after regex alone | 50/50 | 50/50 |
| Notes with PHI after regex + Qwen | 4/50 | 14/50 |
| Of those, Sage flagged | **4/4** | **14/14** |
| Fixed by the Sage-guided retry | 3 | 13 |
| Blocked for human review | 5 | 6 |
| **Sent with PHI in it** | **0/45** | **0/44** |
| Blocked but actually clean | 4 | 5 |
| Median time per note | 5.8 s | 8.3 s |

- Qwen's most common miss was the patient's own name at the start of a line
  ("Gerald Huang labs: Na 138…"). Sage caught it every time.
- The "false" blocks are mostly arguable. Two of them: a doctor's name left in
  (Qwen was told doctors are fine; many de-id policies remove them anyway), and
  "head coach of the [PLACE_1] varsity football team", which can still single
  someone out. Expect about 10% of notes to go to a human at this setting.
- Retry with a hint works: telling the stripper "a checker says a name is still
  in here" fixed most misses on the second pass.
- One bug worth remembering: a retry must never edit text inside an existing
  placeholder, or you get `[[OTHER_4]]` garbage (`sub_outside` in pipeline.py).
- The gate **fails closed**: if Sage errors or times out, the note is blocked.
  We hit a real 504 during testing. This is the opposite of the leftclaw gate,
  which fails open, and that's on purpose: a missed outage here means PHI goes out.

## What this means for the design

1. **Pick the legal mode first.** All the big frontier APIs (OpenAI, Anthropic,
   Vertex, Azure, Bedrock) will sign a BAA. With a BAA, sanitizing is extra
   safety, not a legal need. Without one, the sanitizer has to meet Safe Harbor,
   and one missed name means PHI went out. Details in LANDSCAPE.md §1–2.
2. **The placeholder map is allowed** under HIPAA 164.514(c) if placeholders are
   counters (`[PATIENT_1]`), never hashes of the real value, and the map stays
   local and is guarded like PHI. `Vault` in pipeline.py does this.
3. **Use Sage as a per-type `tags` check, not one yes/no.** Block on any tag ≥0.5
   or on a null answer. Feed the flagged type back to the stripper for one or two
   retries, then send to a human.
4. **Keep bracket placeholders.** LANDSCAPE suggests fake-but-realistic names
   ("John Doe") so misses blend in. Don't, if Sage is the checker: it can't tell
   a fake name from a real one that leaked.
5. **The TEE helps, but doesn't settle HIPAA.** Sage only ever sees text that
   already passed the stripper, so normally it gets no PHI. But a leak is exactly
   the case where it does. HHS has said a cloud host that can't read the data
   still needs a BAA. Nobody has ruled on TEEs, and NEAR has published nothing on
   HIPAA. Ask Levanto/NEAR whether they'll sign a BAA.
6. **Rehydration check:** reject a frontier reply that contains a placeholder we
   never issued (`Vault.rehydrate` returns them).

## Limits of this test

- 50 notes, hand-written by me, one fake patient name. I knew the answers when I
  wrote the cases. Real notes are longer, messier, and OCR'd.
- The real test is the n2c2 2014 / PhysioNet de-id sets (need a data-use
  agreement), plus a bigger adversarial set. Target: ≥99% recall on names, zero
  regex-class misses.
- The frontier call is mocked; no real model was called.
- Thresholds came from one session on one model version (`levanto-sage-v1.3`).
  Re-check them after any Sage update.

## Run it

```
set -a; . ~/sage/.env; set +a          # SAGE_API_KEY
python3 bench.py 2                     # all strategies, short notes, 2 runs
LONG=1 STRATS=tags python3 bench.py 2  # long notes
python3 pipeline.py qwen3:8b           # full loop, needs ollama running
```
