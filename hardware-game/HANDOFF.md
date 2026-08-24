# HANDOFF — read this first

For the next agent (or future me) picking up the hardware game. Everything here was
true as of **2026-08-24**. Austin drove the concept across one long session; all
research, design, and the prototype landed that day.

## What this project is

A competitive tycoon game: players pay a real $100 buy-in, get 10,000 fake CREDITS,
and buy **real hardware** (live-crawled catalog, real street prices, real benchmark
numbers). Machines crunch resources every tick; AI "sloperators" refine them into
goods; goods fill contracts that mint a token whose supply and price floor are fixed
before anyone buys in. Most minted wins the weekly round. Research confirmed **nobody
has built this** — every piece is proven separately, no one has composed them.

## State of play

| Thing | Status |
|---|---|
| Prior-art research (games) | DONE — [PRIOR-ART.md](PRIOR-ART.md) |
| Economy/market design | DONE — [ECONOMY-DESIGN.md](ECONOMY-DESIGN.md) |
| Data-source research | DONE — [../hardware-db/DATA-SOURCES.md](../hardware-db/DATA-SOURCES.md) (its own commit, 74a9efc) |
| Token mechanism + its prior art | DONE — [TOKENOMICS.md](TOKENOMICS.md), [PRIOR-ART-TOKENS.md](PRIOR-ART-TOKENS.md) |
| Resource graph | DONE — [RESOURCES.md](RESOURCES.md) |
| Consolidated master doc | DONE — [GAME-DESIGN.md](GAME-DESIGN.md) ← **the one doc to read if you read one** |
| Playable prototype | DONE, v0 — [prototype/index.html](prototype/index.html), smoke-tested headless |
| Paper round with humans | NOT DONE — the actual next step |
| Any Solidity / crawler code | NOT STARTED (deliberately — feel first) |

Prototype is published as an artifact ("Slopfarm", 🖥️):
`https://claude.ai/code/artifact/b6847cac-c3ba-41ca-b766-7c8e3d13191f`
To update it after editing the file, republish **that URL** via the Artifact tool's
`url` param from any session — publishing without `url` mints a duplicate.

## Decisions Austin has locked (don't relitigate; do flag new evidence)

1. **Earnings are score, not capital** — income can't buy hardware. Kills compounding;
   keeps day 5 of a round alive. (ECONOMY-DESIGN §4.)
2. **Real-money buy-in → curve → burn-to-mint token** — he wants the token layer, not
   just a leaderboard. $100 → 10k credits; fixed per-epoch pro-rata emission; floor
   `R/S_max` known pre-buy-in; sell-only (Moloch-ragequit) during round; batch-settled
   graduation to an open AMM after. (TOKENOMICS.md.)
3. **No player-to-player trading** of commodities/goods — everything internal until it
   burns at the contract board. Kills collusion/wash-trade surface. Revisit only as a
   season mechanic.
4. **Sloperators** (his coinage) — AI models as the workforce. API models cost wages
   (real $/Mtok); open-weight models are free but live in your VRAM. This crossover is
   the game's unique mechanic; protect it.
5. **Prototype-first** — he wants to *feel* the loop before any chain or crawler work.

## The three insights that carry the design

- **Reality is the live-ops team.** Price cuts, launches, restocks = balance patches
  nobody writes. This is the moat; every design choice should keep part stats real
  and untouched (balance via contract ratios and recipes only).
- **The token launch IS the game** — "proof of play" distribution instead of sniper
  bots. Framing matters: chips/tournament, never investment.
- **Prices balance the meta, not the designer.** Pro-rata dilution + contract
  repricing make the best build "whatever everyone else isn't running."

## Biggest open risk (flag to Austin before any real-money build)

**Regulatory** — ranked #1 in PRIOR-ART-TOKENS.md with case law: pot-scales-with-
entries fails the DFS fixed-prize factor; post-round liquid token rhymes with the
Dapper Howey pattern; buy-USDC→credits→token silhouettes sweeps casinos (~17-state
crackdown). The **post-round open-trading phase is severable** — redeem-and-burn-only
v1 is much cleaner. Not legal advice; get real counsel before mainnet.

## The prototype (v0) — how it works, how to work on it

Single offline file, no deps: `prototype/index.html`. Vanilla JS, one `<script>`,
IBM Plex Mono/Sans, committed dark theme. ~500 lines.

**Model:** 20 epochs × 30 ticks (1 tick = 1s at 1×). All constants at the top of the
script: `EPOCHS, EPOCH_TICKS, EMISSION, PLAYERS, ELEC`, then `PARTS` (13 real SKUs:
price/watts/RU/VRAM/outputs-per-tick), `FACILITY`, `OPS` (5 operators), `RECIPES`
(5), `CONTRACT_TMPL` (6), `BOTS` (6 archetype rivals), `EVENTS` (epochs 5/10/15).
**All tuning is data edits in those tables** — the sim code shouldn't need touching.

Mechanics implemented: price ladders (+12%/unit sold), watt/RU hard caps (blocked
purchases logged with the fix), storage spoilage, dynamic tariff, wages, VRAM
hosting for open-weight ops, quality tiers (jobs staffed best-operator-first),
auto-deliver per contract template, contract allocs that shift away from crowded
templates (`S.pressure`), stipends at epochs 8/14, sell-at-floor, end screen.

**Deliberate v0 omissions** (listed in the app footer): part assembly (machines are
pre-racked single parts), heat, bandwidth, wear meters, DATASET boosts, auctions.
Add only if the feel test demands them.

**Known v0 quirks:**
- Recipe priority = `RECIPES` array order; earlier jobs starve later ones of shared
  inputs (COPY eats all TOKENs before SHEET sees any). Arguably a feature (player
  manages jobs); revisit if confusing.
- `Math.random()` contract rolls — fine offline; a real round needs the
  commit-reveal seed.
- Bots don't react to events or the player; they ramp `1 + epoch×0.06` with jitter.

**Testing recipe (what was actually verified):**
1. `node --check` the extracted `<script>` (regex it out; see session scrapbook).
2. Headless playthrough with playwright-core from `~/clawd/clawd-harness/tools`
   (has `node_modules`). **Gotcha:** current playwright-core wants a browser build
   that isn't cached — pass
   `executablePath: ~/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell`.
   Drive ticks deterministically: `setSpeed(0)` then call `step()` in a loop with
   `S.running=true`.
3. Verified: zero JS errors over a full round; watt-cap and VRAM guards block;
   full-round mint works (DGX+9950X, auto-deliver all → 2,139 $GAME ≈ 10.7% of
   supply, rank 7/7 — lazy build loses, which is the intended shape).

**Balance reference points from testing:** 1× 3090 = 1 TOKEN/s but cheapest recipe
needs 2 — token starvation is real and sells the DGX. Half-spent budget → last
place. Nobody has played it for fun yet; that's the point of the feel test.

## Repo/process context (for a fresh agent)

- This is `clawd-research` (github.com/clawdbotatg/clawd-research), Austin's ad-hoc
  research repo. Ship-by-default: commit+push finished work, clawdbotatg identity,
  HTTPS, gitleaks pre-commit hook.
- **Gitleaks trap hit this session:** the bip39 rule fires on ordinary prose — 12+
  consecutive lowercase dictionary words in a doc reads as a mnemonic. Fix by
  rewording the sentence (punctuation/caps break the run), never by `--no-verify`
  and never by loosening the config.
- Session memory lives in the auto-memory dir (`hardware-game.md` there mirrors this
  file in compressed form; keep both updated on major moves).
- Related Austin threads that intersect: **agent-esports** (bots-as-players lane),
  **simple-eval** (grader for the Tier-3 "real LLM calls" league),
  **local-ai/DGX-Spark research** (the hardware knowledge behind the catalog).

## Next steps, in order

1. **Austin plays the prototype** → collect feel notes → tune the data tables.
   (Likely asks: longer/shorter epochs, more build variety, clearer "why did I mint
   X" feedback.)
2. **Paper round with 5–10 friends** — even the HTML version works: everyone plays
   the same seed, compare minted. Validates fun before infra.
3. **Name + fiction** — who is the contract board? Picks the goods flavor and the
   token name. ("Slopfarm" is a placeholder that stuck for the prototype.)
4. Crawler v1 (Best Buy API + WhatToMine + PassMark/dbgpu — stack ranked in
   DATA-SOURCES.md) feeding a real weekly catalog snapshot.
5. Contracts (Words3 `ClaimSystem` is the template; L2; lazy-accumulator
   production; batch graduation). Only after 1–4, and only with the regulatory
   question answered.
