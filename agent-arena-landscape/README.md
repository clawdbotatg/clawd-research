# Agent Evaluation Frameworks & Competition Arenas — landscape for building "agent esports"

*Research date: 2026-07-17. Method: deep-research workflow — 5 parallel search angles,
22 sources fetched, 105 claims extracted, top 25 adversarially verified (3 independent
refuter votes each): 23 confirmed 3-0, 2 refuted. Individual facts below are the
confirmed ones; the gap analysis at the end is synthesis.*

## The one-paragraph takeaway

The two halves of this space have matured unevenly, and the gap between them is
exactly the product idea. **Evaluation harnesses** (SWE-bench, Terminal-Bench,
WebArena, OSWorld) have converged on a proven architecture — Docker/VM sandbox per
task, tasks shipped as `{initial-state config + instruction + programmatic verifier
(+ oracle solution)}`, fully automated outcome-based scoring — which is precisely
the sandboxing/verification stack a live agent-racing platform needs. **Competition
arenas** prove the spectator formats work (side-by-side VNC streaming, celebrity-
commentated tournaments, real-money leaderboards) but none of them race agents on
*realistic tasks* with *programmatic win conditions* in *real time*. Nobody has
assembled the pieces.

---

## Part A — Evaluation frameworks: how the big ones actually work

### SWE-bench — the canonical sandboxed-scoring template
- **Measures:** can an agent fix real GitHub issues (patch a repo so its test suite passes).
- **Open source:** yes — [github.com/SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench); harness docs at [swebench.com](https://www.swebench.com/SWE-bench/reference/harness/).
- **Mechanics:** every evaluation runs in Docker with a **three-tier image
  architecture** — base language/tooling images → repo-specific environment images →
  problem-specific instance images — so common layers cache while each run stays
  isolated (99.78% ground-truth reproducibility per the June 2024 containerization
  report). Scoring is a five-step automated pipeline: build images → apply the
  model's patch → run the repo's real test suite → grade deterministically via
  `FAIL_TO_PASS` / `PASS_TO_PASS` test lists → report. Also runs on Modal/AWS with
  the same containers.
- **Builder lesson:** layered-image caching is how you make per-match sandboxes
  spin up fast at scale.

### Terminal-Bench (now on the Harbor framework) — closest prior art for realistic-task racing
- **Measures:** autonomous end-to-end terminal work — compiling code, training
  models, configuring servers.
- **Open source:** yes, Apache-2.0 — [github.com/harbor-framework/terminal-bench](https://github.com/harbor-framework/terminal-bench); paper [arXiv:2601.11868](https://arxiv.org/abs/2601.11868) (Stanford/Laude Institute, Jan 2026).
- **Mechanics:** the harness connects the agent to a **Docker-sandboxed terminal**.
  Each task ships: an instruction, a Dockerfile (initial state), a **programmatic
  test script** that verifies completion, and a reference **"oracle" solution**
  (`solve.sh`). TB 2.0 (Nov 2025) has 89 verified tasks; frontier agents still
  score **<65%** — real headroom means real drama in a race format.
- **Builder lesson:** the `sandbox + verifier + oracle` task format is directly
  reusable as a competition task format. The oracle doubles as your "par time."

### WebArena — the web-task arena pattern
- **Measures:** web tasks on fully functional self-hosted sites (e-commerce,
  forums, GitLab, CMS).
- **Open source:** yes, Apache-2.0 — [github.com/web-arena-x/webarena](https://github.com/web-arena-x/webarena); paper [arXiv:2307.13854](https://arxiv.org/abs/2307.13854); optimized Docker Hub images shipped Feb 2026; ServiceNow maintains hardened verifiers as **webarena-verified**.
- **Mechanics:** scored by **functional correctness of outcomes** — did the backend
  state change correctly — not by matching an action sequence. (Original result:
  GPT-4 agent 14.41% vs human 78.24% success.)
- **Builder lesson (important):** naive substring-match verifiers produced **~11.3%
  false negatives** (WebArena-Verified / BenchJack audits). The fixes — type-aware
  matching, backend-state verification, structured status codes — are the nearest
  thing to anti-cheat/robust-scoring prior art that exists.

### OSWorld — full-desktop sandboxing at scale
- **Measures:** 369 primary tasks (+43 Windows) across real web/desktop apps, OS
  file I/O, and multi-app workflows.
- **Open source:** yes — [github.com/xlang-ai/OSWorld](https://github.com/xlang-ai/OSWorld); [osworld-v1.xlang.ai](https://osworld-v1.xlang.ai/); paper [arXiv:2404.07972](https://arxiv.org/abs/2404.07972) (NeurIPS 2024).
- **Mechanics:** each task = **initial-state setup config + custom execution-based
  evaluation script**. 134 evaluation functions using getters over file contents,
  accessibility trees, browser cookies — with logical evaluators that **accept
  alternative correct solution paths**. Agents run in full VMs (Ubuntu/Windows)
  with parallel headless operation and pluggable providers: VMware, VirtualBox,
  Docker, AWS, Azure, Daytona.
- **Builder lesson:** this is exactly the task format for "sort spam out of my
  inbox" or "brute-force the keycode site" — and multi-path-tolerant evaluators
  matter because racing agents *will* find routes you didn't anticipate.

### Coverage note
LMArena/Chatbot Arena mechanics, OpenAI Evals, lm-evaluation-harness, HELM,
AgentBench, GAIA, and tau-bench were in scope but didn't produce claims that
survived the verification cut — the survey above is representative of the
*agentic/sandboxed* branch, not exhaustive of all eval frameworks. (From the
un-verified search layer: LMArena works by blind pairwise human votes ranked with
a Bradley–Terry model, and raised a $150M Series A at a **$1.7B valuation** in
Jan 2026 — a signal of what arena-shaped products can be worth, per
[TechCrunch](https://techcrunch.com/2026/01/06/lmarena-lands-1-7b-valuation-four-months-after-launching-its-product/).)

---

## Part B — Competition / arena platforms: what exists, what's watchable

### Computer Agent Arena (xlang-ai) — THE existence proof for watchable agent-vs-agent
- [github.com/xlang-ai/computer-agent-arena](https://github.com/xlang-ai/computer-agent-arena) · [arena.xlang.ai](https://arena.xlang.ai) · ICLR 2026 paper ([OpenReview](https://openreview.net/forum?id=3x4SDbXbgl))
- Users watch **two computer-use agents operate live Ubuntu/Windows desktops
  side-by-side** and vote for the better one → continuously updated Elo leaderboard
  (2,201 votes across 12 agents at paper time, with ranking reversals vs static
  benchmarks — head-to-head genuinely measures something different).
- **Published spectation architecture:** React 18/TypeScript frontend with dual
  agent chat panels and a **live VNC viewer into real VMs**; Flask + Socket.IO
  backend orchestrating **auto-scaling multi-region AWS EC2 VM pools**.
- Caveats from verification: the "whole stack is cleanly MIT-forkable" claim was
  **refuted 0-3** — treat the repo as a reference architecture, not a turnkey
  fork. The hosted site returned HTTP 522 on fetch attempts, so current uptime
  unconfirmed.

### Kaggle Game Arena (Google/DeepMind) — proof that commentated AI tournaments entertain
- [kaggle.com/benchmarks/kaggle/game-arena](https://www.kaggle.com/benchmarks/kaggle/game-arena) · [Google blog](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/kaggle-game-arena-updates/)
- Frontier models compete head-to-head in **chess, HUNL poker, and Werewolf**,
  ranked via a pooled Bradley–Terry model. The Feb 2026 tournament ran as
  **multi-day livestreams** (poker battles Feb 2, semis Feb 3, finals + chess
  championship Feb 4) with commentary from **GM Hikaru Nakamura, Doug Polk, Nick
  Schulman, and Liv Boeree**; VODs on Kaggle's YouTube.
- **The entertainment formula:** familiar games + named frontier models +
  celebrity domain commentators + a real ranking at stake. Note it was a
  **bounded event**, not a continuous feed — 24/7 agent competition is unclaimed.

### Real-money trading arenas — real stakes as the draw
- **nof1.ai Alpha Arena S1.5** ([nof1.ai](https://nof1.ai/)): eight LLMs each given
  **$10,000 of real capital** to trade TSLA/NVDA/MSFT/AMZN/NDX, public
  leaderboard; ended Dec 3, 2025 — winner was a "Mystery Model" later revealed as
  xAI Grok 4.20, +12.11% (~$4,844 profit).
- **SpoonOS Arena** ([arena.spoonai.io](https://arena.spoonai.io/)): launched June
  2026 — eight LLMs trading live on **Polymarket** with $500 bankrolls, framed
  around the 2026 FIFA World Cup, community profit-sharing. Spectated via a
  leaderboard (account value, PnL, exposure, win rate) **updated only hourly**.
- **Lesson:** real stakes reliably draw an audience, but both are
  *leaderboard-watching, not action-watching*. Hourly updates show how far short
  of live spectation the format currently falls — and how low the bar is.

### PillagerBench — team-vs-team matches in real-time Minecraft
- [github.com/aialt/PillagerBench](https://github.com/aialt/PillagerBench) (MIT) · [arXiv:2509.06235](https://arxiv.org/html/2509.06235) · IEEE Conference on Games 2025
- Two teams of two LLM agents compete in consecutive timed episodes. Harness
  spawns a Minecraft server + **one Mineflayer (JS API) process per agent**,
  Docker for consistency, Hydra-managed YAML configs for reproducible match
  parameters. (Its "first competitive team-vs-team benchmark" framing failed
  verification 1-2 — don't repeat that; use it as orchestration prior art.)

### Microsoft Agents League — branding outrunning substance (a market signal)
- [github.com/microsoft/agentsleague](https://github.com/microsoft/agentsleague) · Feb 16–Mar 1 2026, **$55K prize pool**
- Marketed as an "esports-inspired hackathon where AI agents battle" — but the
  streamed "live battles" on Microsoft Reactor were **expert live-coding demos**,
  and the actual competition was **asynchronous GitHub submissions** judged
  post-hoc by rubric + a 10% Discord community vote. **No agent-vs-agent combat
  occurred.** A major vendor invested in the esports framing and delivered none
  of the substance — strong evidence of both demand for the format and the gap.

### Adjacent spectator prior art (surfaced in search, not put through full verification)
- **Claude Plays Pokémon / Gemini Plays Pokémon** — parallel Twitch streams of
  LLMs playing Pokémon Red, informally framed as a head-to-head; proof that
  people will watch a raw agent feed for months if there's narrative.
- **agentarena.party** — "Wii-Sports-style" 3D staged debate matches with Elo,
  replays, crowd reactions; entertainment-first framing of agent competition.
- **NetMind Agent Arena** — competitive benchmarking platform with a live
  leaderboard for autonomous agents on real-world challenges.

---

## Part C — Building the thing: assembled takeaways

**Every component is proven somewhere; the intersection is empty.**

| Component | Proven by | Reuse |
|---|---|---|
| Fast per-match sandboxes | SWE-bench 3-tier Docker layering | cache base/env layers, per-match instance layer |
| Realistic-task format | Terminal-Bench / OSWorld | `{initial-state config, instruction, verifier script, oracle solution}` |
| Web-task environments | WebArena self-hosted sites | e-commerce/forum/GitLab/CMS stacks in Docker |
| Live spectation | Computer Agent Arena | VNC-into-VM → Socket.IO → side-by-side React panels |
| Robust scoring / anti-cheat seed | WebArena-Verified | backend-state checks, type-aware matching, multi-path evaluators |
| Entertainment production | Kaggle Game Arena | named models + celebrity commentary + scheduled broadcast |
| Stakes | Alpha Arena / SpoonOS | real money or ranking on the line, public PnL-style scoreboard |

**The gap (medium confidence — absence can't be proven exhaustively):** realistic
tasks, raced live head-to-head, with **programmatic win conditions** (not human
votes), produced for spectators. Today's realistic-task benchmarks are batch-run
and unwatched; today's watchable arenas use games/markets/human votes instead of
verified realistic tasks. The "sort my spam fastest / build the app fastest /
brute-force the keycode site" concept sits exactly in that empty intersection.

Concrete build notes for the racing platform:
1. **Task format:** adopt Terminal-Bench/OSWorld's shape verbatim. The keycode-
   brute-force task is a WebArena-style self-hosted site + a verifier that checks
   backend state ("was the correct code submitted, at what timestamp"). The spam
   task is an OSWorld-style initial-state config (mailbox fixture) + evaluator
   (final label state vs ground truth). Time-to-verified-completion is the score.
2. **Verifiers are the hard part, not the sandbox.** WebArena's 11.3%
   false-negative rate says naive checkers will wrongly decide races. Check
   backend state, tolerate alternative solution paths, and treat verifier
   hardening as ongoing work.
3. **Spectation:** VNC/screen-stream out of the VM → websocket fan-out → split-
   screen. Computer Agent Arena streams to one voting user; **one-to-many
   broadcast (restream to Twitch), synchronized race starts, and sub-second
   scoreboards are unsolved/unclaimed** — that's differentiation, not just risk.
4. **Anti-cheat barely exists as a field.** Nothing verified documents defenses
   against agents gaming evaluator scripts, exfiltrating oracle solutions,
   memorizing tasks, or colluding. Hardened verifiers + fresh procedurally-varied
   task instances per match (randomize the keycode, shuffle the spam) is the
   practical starting point.
5. **Business-model evidence is thin everywhere** — stakes, sponsorship, and
   model-lab bragging rights, not demonstrated revenue. LMArena's $1.7B valuation
   shows arena-shaped platforms can be valued richly; nobody has shown
   agent-spectation revenue yet.

## Open questions
- Unit economics: per-match VM + inference cost vs any audience revenue; no arena
  has published retention numbers.
- Anti-cheat beyond hardened verifiers (evaluator-gaming, oracle exfiltration,
  cross-match collusion) — essentially unstudied.
- Mechanics of the crowdsourced-text-arena branch (LMArena) and the embodied-game
  lineage (MineRL, Mindcraft, poker/Diplomacy leagues) — under-documented in this
  pass; worth a follow-up if either format becomes load-bearing.
- Broadcast-scale streaming latency: nothing verified addresses restreaming VM
  pools to thousands of viewers with race-grade sync.

## Addendum (same day): where can you actually *watch* agents compete, and does anyone run evals live?

Follow-up questions after the main report: (1) links that land you on live/VOD
footage of agents competing, (2) whether anyone runs the realistic-task eval
frameworks as a live watchable competition.

### Watchable today (verified by fetching)
- **TCEC** — [tcec-chess.com](https://tcec-chess.com) + [twitch.tv/tcec_chess_tv](https://www.twitch.tv/tcec_chess_tv) — 24/7 chess-engine championship; live board, eval graphs, engine thoughts. The UX benchmark for "watch AIs compete forever."
- **Chess.com Computer Chess Championship** — [chess.com/computer-chess-championship](https://www.chess.com/computer-chess-championship).
- **SaltyBet** — [saltybet.com](https://www.saltybet.com) — 24/7 AI-controlled MUGEN fighters + live fake-money betting; running 10+ years. The betting layer is the retention engine.
- **Chess Agents** — [chessagents.ai/live](https://chessagents.ai/live) — community-submitted autonomous chess agents, live spectator arena.
- **Claude Plays Pokémon** / **Gemini Plays Pokémon** — [twitch.tv/claudeplayspokemon](https://www.twitch.tv/claudeplayspokemon), [twitch.tv/gemini_plays_pokemon](https://www.twitch.tv/gemini_plays_pokemon) — still-active single-agent feeds.
- **Kaggle Game Arena Feb 2026 VODs** — [official playlist](https://www.youtube.com/playlist?list=PLqFaTIg4myu_tpB0JXRJ5Hb-ApyXDxOlD); Hikaru-commentated broadcasts: [Day 1](https://www.youtube.com/watch?v=6rb2rMahWrE) · [Day 2](https://www.youtube.com/watch?v=4TJwlPVjXcQ) · [Day 3](https://www.youtube.com/watch?v=vzMj2KOyiek) · [Werewolf highlights](https://www.youtube.com/watch?v=vTx4VqpLM_I). The calibration tape for "agent esports done well."
- **AI Diplomacy (Every)** — [every.to/diplomacy](https://every.to/diplomacy) + [github.com/EveryInc/AI_Diplomacy](https://github.com/EveryInc/AI_Diplomacy) (open source). ~50K live Twitch viewers at launch; VODs expired (Twitch 30-day deletion), channel [twitch.tv/ai_diplomacy](https://www.twitch.tv/ai_diplomacy) only live during runs.
- **MoltGamingLab** ([moltgaminglab.com](https://moltgaminglab.com)) claims "esports arena for AI agents" (chess/snake/pong/tetris) but fetched as vaporware: zero agents, zero matches, all placeholders.

**Pattern:** everything watchable is a *game* — legible state, obvious winner. All chess/poker/fighting, none of it is what people actually use AI for.

### Does anyone run eval-framework tasks as a LIVE competition? No.
Searched specifically (July 2026): no one streams realistic-task evals as races.
- **SWE-bench-Live** ([swe-bench-live.github.io](https://swe-bench-live.github.io/), [arXiv:2505.23419](https://arxiv.org/pdf/2505.23419)) — "live" means *auto-updating contamination-free dataset* (fresh GitHub issues monthly), NOT live competition. Still batch-run, results posted to a static leaderboard. Open source.
- **WebDev Arena** ([arena.ai/blog/webdev-arena](https://arena.ai/blog/webdev-arena/)) — nearest to "build an app head-to-head": your prompt → two anonymous models each generate a web app → you interact with both and vote (80K+ votes, Bradley-Terry ranking). But it's *participatory* (you're the judge), one-shot generation (not agentic work you watch unfold), and human-voted (not programmatically verified). Related: HuggingFace's **BigCodeArena** ([blog](https://huggingface.co/blog/bigcode/arena)) adds actual code execution to the vote.
- **Leaderboard aggregators** ([steel.dev](https://leaderboard.steel.dev/), CodeSOTA, agentbeats.dev) — dashboards over batch results, nothing live.
- **Computer Agent Arena** (main report) remains the only live-watchable realistic-task platform, and it's human-voted + currently down.

So the intersection {tasks people actually ask AI to do} × {live, spectator-format} × {programmatic win conditions} is confirmed empty as of 2026-07. The build-block frameworks (SWE-bench, Terminal-Bench/Harbor, OSWorld, WebArena, SWE-bench-Live's auto-curation pipeline) are all open source.

## Refuted during verification (do not cite)
- "Computer Agent Arena's entire stack is MIT-licensed and forkable" — 0-3.
- "PillagerBench is the first competitive team-vs-team multi-agent benchmark" — 1-2.
