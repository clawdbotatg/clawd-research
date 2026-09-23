# Jev vs Laya (2026-09-23)

Two models in the same new category: a **decision model** that never generates text. You hand it
a state and typed questions (`choice` / `score` / `noul`), it returns probabilities over the
options you offered, in one forward pass. Same wire format on both (`POST /v1/systemone`).

| | **Jev 1.13.0** (TypeSafe AI) | **Laya 0.3.x** (Convai Innovations) |
|---|---|---|
| Released | 2026-09-15 (waitlist dropped 09-20) | 2026-09-18 (english, typed-decisions), 09-19 (multilingual) |
| Weights | closed, hosted API only | **Apache 2.0**, `pip install laya`, HF `convaiinnovations/laya` |
| Size | undisclosed | 421M (ModernBERT-large + 2-layer decision head); multilingual 322M (mmBERT-base) |
| Context | 64K total, 32K state | **512** tokens (english), 1,024 (multilingual / typed-decisions), mmBERT to 8K via RoPE |
| Option budget | up to **255** choice options | options share a 192–256 token head budget: 77 options ≈ 3 tokens each |
| Price | $0.042 / Mtok in, output free | $0, your hardware |
| Latency (vendor) | 70–500 ms | 33 ms on a T4; laya-mlx 7–14 ms on M3 Max |
| Rate limit | 250K tok/s, 1,200 req/min | none |
| Languages | English-first | router picks english vs multilingual (45/51 languages usable) |
| Runtimes | Python + JS SDKs | PyTorch, `laya-mlx` (Apple Silicon), CoreML port, `laya-serve` Jev-compatible HTTP, MCP judge |

## The story

Laya's author (Nandakishor M, "Mukkunnoth") says he published the same non-autoregressive
schema-decision idea in March and September 2025 (SalesRLAgent, arXiv:2510.01237), then watched
TypeSafe launch Jev as a breakthrough with no paper and no weights. Instead of arguing, he rebuilt
it end-to-end and released it open under the Laya name, three days after Jev. Both camps call the
training method RLCD (RL with strictly proper scoring-rule rewards). Dev.to post: "I Built
Non-Autoregressive Decision Models a Year Ago. Then a Frontier Lab Called It a Breakthrough."
19K GitHub stars in five days. Lobsters commenters' pushback is fair: architecturally this is a
runtime-schema classifier, not a new science.

## What the vendor numbers say (and don't)

Laya's model card puts itself ahead of Jev on typed-decisions (0.766 vs 0.727), AG News, DAIR
Emotion and calibration, and 7.8x faster. Read the footnotes:

- **Jev's numbers are third-party published, never run by Laya's authors** (no TypeSafe key).
  Different samples, different prompts.
- **The 0.766 is a checkpoint fine-tuned on that benchmark's own training split.** Zero-shot the
  base Laya scores 0.362 on it, vs 0.318 random and 0.461 majority-class. The card's own words:
  "a fast base to specialise, not a zero-shot decision engine."
- **Jev wins where the option list is long**: Banking77, 0.870 vs 0.425. Laya's fixed head budget
  gives each of 77 labels 3–4 tokens. Remedies exist (`head_max_len=512`, `predict_shortlist`,
  coarse-to-fine) but each costs accuracy or a second pass.
- **Known Laya bugs** worth knowing before building on it: `noul` can follow its own
  `true:`/`false:` labels instead of the state (#156, workaround: 2-option `choice`);
  `act_probability` carries no signal (#185, use `confidence`); `score` is the weakest primitive;
  ships over-confident until you refit temperature on your data.

The most honest independent comparison is the `laya-browser-agent` README (Apple M4, real
Chromium, hosted Jev vs local Laya browser fine-tune): single-step goals local 4/12 vs hosted 8/12,
cross-lingual 1/6 vs 5/6, text triage 3/7 vs 7/7, and the local model clicked "Delete my account"
at p=0.93. Its recommendation: hosted Jev when accuracy and safety calibration matter, local Laya
for latency, privacy or zero marginal cost with guards around it.

## Browser agents (the jev-ultrafast lineage)

- `ipenywis/laya-ultrafast`: jev-ultrafast with the Jev call swapped for laya-mlx. Mac only.
  Google Flights ZRH→LON 5/5 in 7.5–12 s (vs our 8.0 s on Jev), 33 ms per decision, still one
  Mercury/Ollama call to turn the goal into field values. Keeps Jev as a fallback flag.
- `ChenneyZhuang/laya-browser-agent`: element table + confidence gate + toggle/loop guards +
  Jev-compatible server, default checkpoint `cklxx/laya-browser` (browser fine-tune, 0%→62% task
  success, top-1 element 0.10→0.66, trained on one 16 GB 4070 Ti with a local Qwen3-8B teacher).
  Latency scales with options offered: 10 → 183 ms, 60 → 678 ms, 120 → 1.2 s.
- Official `docs/finetune_browser_agent.md` in the Laya repo documents the same recipe.
- None solve what killed us on Jev (`../jev-ultrafast/NOTES.md`): targets below the fold or inside
  inner scrollers. The "vocabulary gap" (type a word the page never shows) is open on both.

## Same-Mac head-to-head (ours)

`bench.py`, 2026-09-23. Three suites that map to things in `../jev-ultrafast/USES.md`. Same
states, same questions, same wire format. Jev is the hosted API from this Mac; Laya is the
`laya-mlx` 0.2.0 float16 build on the M3 Max (a PyTorch CPU run on the relay box gave identical
picks, `results-*-relaycpu.json`). 47 calls per engine.

| | **Jev 1.13.0** | **Laya english** | **Laya typed-decisions** |
|---|---|---|---|
| p50 latency | 218 ms (max 317) | **14 ms** (max 147) | **14 ms** (max 85) |
| Cold load | 0 | 1.7 s both checkpoints | |
| **A. injection gate, `noul`**: safe max / unsafe min | 0.27 / 0.94 (**+0.67** gap) | 0.63 / 0.89 (+0.26) | 0.55 / 0.61 (+0.06) |
| **A. injection gate, 2-way `choice`** | 0.06 / 0.96 (**+0.90** gap) | 0.62 / 0.94 (+0.32) | 0.76 / 0.74 (**overlap**) |
| **B. element pick**, 8 / 24 / 60 options, jev-ultrafast format | **5/5 · 4/5 · 5/5** | 0/5 · 0/5 · 0/5 | 3/5 · 0/5 · 0/5 |
| B. re-run, plain-string criteria (Laya's format) | | 2/5 · 2/5 · 2/5 | 1/5 · 3/5 · 1/5 |
| B. re-run, element label as the option key | | 1/5 · 1/5 · 3/5 | 1/5 · 3/5 · **4/5** |
| **C. autopilot triage** continue / needs_human / done, 8 cases | **8/8** | 3/8 (answers "done" 7 times) | 7/8 |

What the rows mean:

- **Injection gate (leftclaw policy, 8 safe incl. role-framing and exploit-PoC, 4 hijacks).** Jev
  separates cleanly with either phrasing and its worst safe case is the grade-manipulation one,
  same as Sage found. Laya english is usable but tight: its worst safe case is "write a reentrancy
  exploit PoC" at 0.62–0.63, so a threshold that catches all four hijacks (0.89) leaves no
  escalate band. The typed-decisions checkpoint is worse here, not better: it was fine-tuned on
  invoice / security-incident / support workflows and that shows.
- **Element pick.** In jev-ultrafast's exact request (nested dict per option, index keys) base Laya
  never found the target once, and at 8 options its probability on the right answer was below
  chance (0.078 vs 0.125); it locks onto "Sign in" / "Terms". Given the target text as the option
  key and few distractors it gets 3–4 of 5, but that isn't the format the agent sends, and the
  picks are mostly lexical overlap with the goal ("Nonstop only", "Accept all"). This is exactly
  the 0.10 top-1 zero-shot figure the `laya-browser` fine-tune card reports as its starting point.
  The browser ports that work (`laya-ultrafast`, `laya-browser-agent`) either fine-tune or change
  the policy to narrow yes/no questions; drop-in replacement of Jev is not what they do.
- **Autopilot triage.** Base Laya says "done" to almost everything (it's the option whose
  description most resembles the state). typed-decisions gets 7/8 and misses one "continue" as
  "done" at p=0.39: a real near miss, and the one error that would matter in the pilot (it would
  stop a session mid-task). Jev 8/8 with p≥0.95 on every case.
- **Latency.** Laya really is ~15x faster from this desk (14 ms vs 218 ms) and the model loads in
  under two seconds. Real, and the reason to keep watching it.
- **Both are day-one models.** Laya's checkpoint ships a temperature outside its own clamp range
  (`laya-mlx` warns on load); Jev has no changelog and its jaggedness page 404s.

## Verdict

**Use Jev for anything we'd ship this month.** On our three real use cases it is the accurate,
calibrated one: clean margins on the injection gate, 14/15 on element picks including 60-option
tables, 8/8 on autopilot triage. At $0.042/Mtok and ~1K tokens per call that is 4 cents per
thousand decisions; price is not the objection it was with Sage. The objections are the ones that
come with any hosted API: closed weights, 30-day-old company, key in `.env`.

**Laya is the right thing to fine-tune, not the right thing to call.** Zero-shot it is a 421M
classifier that keys on lexical overlap, and its own card says so ("a fast base to specialise").
Where it earns a place: a task with a few hundred labeled examples where 14 ms and $0 matter and
we can run the Kaggle notebook (4–5 h on free T4s) or the 16 GB-GPU browser recipe. Concretely
from `../jev-ultrafast/USES.md`: the autopilot `continue / needs_human / done` gate has thousands
of labeled Stops in the harness transcripts already, and typed-decisions is at 7/8 before any of
that. Same story as `../tiny-task-model/` (Qwen3-1.7B beat prod on session naming after a narrow
FT): small + local + specialised wins, small + local + zero-shot doesn't.

**Don't** swap Laya into `browser_run` or the leftclaw injection gate as a drop-in. Both fail the
same way the community reports: over-confident on the wrong element or the wrong verdict.

**Cascade is the interesting middle.** Laya first at 14 ms, escalate to Jev below a confidence
floor. The typed-decisions autopilot miss was at p=0.39 and the injection near-misses at 0.6–0.7,
so a floor around 0.8 would have routed every error to Jev while keeping most calls local. Worth
measuring on real transcript tails before building.

## Files

- `bench.py` — the head-to-head; `results-*.json` per engine.
- `.venv/` (gitignored) — `uv venv --python 3.12 .venv && uv pip install laya-mlx requests`.
- Weights land in `~/.cache/huggingface/hub/models--convaiinnovations--laya` (~1.6 GB for two checkpoints).

## Sources

- Laya repo https://github.com/NandhaKishorM/laya · model card https://huggingface.co/convaiinnovations/laya
- Spec pages https://systemonemodels.org/models/laya/ · https://systemonemodels.org/models/jev/
- Priority story https://dev.to/nandakishor_m_6cc0adfde9f/i-built-non-autoregressive-decision-models-a-year-ago-then-a-frontier-lab-called-it-a-18me
- Ports: https://github.com/ipenywis/laya-ultrafast · https://github.com/ChenneyZhuang/laya-browser-agent · https://github.com/kiuckhuang/laya-jev
- Coverage: https://aiweekly.co/alerts/convai-ships-laya-a-421m-modernbert-decision-model-apache-20 · https://mer.vin/news/laya-the-33ms-open-source-decision-model-beating-jev/
