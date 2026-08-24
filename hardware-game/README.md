# The Hardware Game (working title)

Austin's concept (2026-08-24): a competitive resource-management game where you spend a
**fake budget on real hardware**. A crawler keeps a live catalog of actual CPUs / GPUs /
RAM / motherboards / laptops / DGX Sparks at real street prices. Each round everyone gets
the same budget, builds machines, and every game tick the machines **produce commodities**
(hashes, spreadsheets, AI inference, rendered frames…) that sell for in-game money.
Most money wins the round. Feels like Bitcoin mining × fantasy football × M.U.L.E.

Three research passes feed this doc:

- **[PRIOR-ART.md](PRIOR-ART.md)** — every adjacent game surveyed (PC Building Sim,
  RollerCoin, tycoons, idle math, seasons, fantasy-market games)
- **[ECONOMY-DESIGN.md](ECONOMY-DESIGN.md)** — market pricing, round structure,
  anti-meta mechanics, onchain architecture, the AI-employee idea
- **[TOKENOMICS.md](TOKENOMICS.md)** — the real-money layer: $100 buy-in → curve →
  burn-to-mint token, sell-only valve, graduation to open trading, seasons
- **[RESOURCES.md](RESOURCES.md)** — the full sink/faucet graph: 5 constraints,
  hardware classes, sloperators, 6 raw commodities, 10 refined goods, contract board
- **[PRIOR-ART-TOKENS.md](PRIOR-ART-TOKENS.md)** — buy-in/curve game history: FOMO3D,
  Words3 (closest precedent), Axie/StepN spirals, one-way valves, legality landscape
- **[../hardware-db/DATA-SOURCES.md](../hardware-db/DATA-SOURCES.md)** — the real-data
  layer: which price/benchmark sources to crawl and how specs map to production rates

## The headline finding

**Nobody has built this.** All the pieces exist separately and are individually proven:

| Piece | Proven by |
|---|---|
| Real licensed parts + real benchmark numbers as game stats | PC Building Simulator 2 (3DMark-modeled scores) |
| Fake budget on real live-priced assets | DFS salary caps, fantasy-stock games (MarketDraft, Visionrare) |
| Buy rigs → rigs produce → pro-rata payouts | RollerCoin |
| Fresh-economy seasonal resets | Path of Exile leagues, Dark Forest rounds |
| Auction/market pressure on shared scarce resources | Power Grid, M.U.L.E., Offworld Trading Company |

The combination — a live-scraped retail catalog where a GPU price drop or a DGX restock
mid-round is a **balance patch reality wrote for you** — is an open lane. (Closest miss:
PC Creator 2 has live *coin* prices but parody parts — fake parts kill the fantasy.)

## The design that fell out of the research

**Round shape.** Weekly rounds (Dark Forest's proven 4–10 day cadence), optionally
grouped into monthly seasons. Every player gets the **same fixed budget, every round,
no carryover** — cross-season progression is cosmetic/reputation only (PoE lesson:
season N must be joinable by a newcomer).

**The one structural rule that keeps it competitive: earnings are SCORE, not capital.**
You cannot reinvest income into more hardware (hardware comes only from the round budget,
plus maybe a mid-round stipend drip at day 2/4/6 to force re-decisions). This kills the
compounding snowball that ruins every competitive idle game — a 5% early edge otherwise
becomes 2× by day 4 and the back half of the round is dead. Production is linear in time
by construction; **all the skill lives in prices**.

**Catalog.** Crawled weekly, snapshotted at round open (also kills oracle games).
Scarce SKUs sit on **Power Grid-style price ladders**: K units at the real street price,
each purchase climbs the ladder, so the 8th 5090 buyer pays 1.6×. Everyone *can* have
one; "what is everyone else buying?" becomes the central read. A couple of unicorn parts
per round (one B200, one exotic) get auctioned.

**Second budget: watts.** Every real part has a real TDP. You have a power feed
(upgradable at escalating cost) and pay fake electricity per watt per tick — possibly on
a dynamic tariff (total fleet draw raises it), which doubles as the money sink. This one
constraint recreates real perf-per-watt strategy for free and is thematically honest.
Wear meters instead of RNG failure: usage fills the meter, maintenance spend resets it —
a sink, a decision, no dice (and onchain-friendly).

**Commodities & market.** 4–6 outputs whose rock-paper-scissors is *derived from real
silicon*, not authored: hashes want raw GPU compute, tokens want VRAM bandwidth,
spreadsheets want single-core CPU, frames want balance — an EPYC is a spreadsheet monster
and a terrible miner. Prices move by clamped supply/demand ratio (Victoria 3 formula)
against a growing NPC buyer that drifts toward whatever is cheap (Offworld's colony —
crashed markets self-heal, late-round demand > early = comeback fuel), with an
always-bid floor price (M.U.L.E.'s store). Steal OTC's key rule: **sales move the
price, not production** — so you can warehouse output and time your dumps. The more of
the fleet mining hashes, the less hashes are worth: the meta self-balances and
meta-chasing is self-defeating. Publish the price formula; reading the market IS the game.
Weekly demand events ("colony renders a film — frames ×2") shake the equilibrium.

**Production rates from real benchmarks** (full mapping table in DATA-SOURCES.md):
PassMark single-thread → spreadsheets/tick; CPU Mark → renders (sublinear ^0.9);
WhatToMine per-GPU hashrates (which come with real watts!) → hashes/tick verbatim;
tokens/sec from MLPerf + llama.cpp community benches (measured DGX Spark and Mac Studio
numbers exist) → inference/tick, gap-filled by `bandwidth ÷ model_size × 0.7`.
PSU/mobo/case are gates and constraints, not producers.

**The AI employee (the mechanic no other tycoon can have).** Mirror catalog: real LLMs
crawled with real $/Mtok as **wages** (opex) vs hardware's capex+watts. v1 = stats only:
an employee produces quality-tiered "AI work" commodities; every real model launch is a
free content patch. v2 = the killer crossover: **open-weight employees can run on your
own hardware** — burn VRAM and watts instead of wages. That welds the two catalogs into
one build-vs-buy decision practitioners actually face. v3 (special league only): employees
make *real* LLM calls graded by simple-eval — that's the agent-esports adjacency.

**Onchain (if we go there).** Hybrid: market + purchases + production onchain on an L2,
catalog posted as one signed snapshot per round. No cron ticks needed — production is a
pure function of time, so use the **lazy staking-accumulator pattern**: integrate
`rate × price(t)` over price epochs on any player action or at settlement. Builds are
public by design (no hidden info onchain anyway — embrace it, like Power Grid's open
resource track), contracts open so **bots are first-class players** — 0xMonaco proved
leaderboard + redeployable strategies makes a dev metagame that markets itself.

**Data stack v1** (details + ToS risk table in DATA-SOURCES.md): Best Buy Products API
(free, official, near-real-time prices, covers laptops/Mac Studio too) as the price
backbone; WhatToMine/hashrate.no for hashrate+watts; PassMark CSVs + dbgpu dataset for
perf; MLPerf/llama.cpp for tokens/sec; PCPartPicker only as a one-time compat-taxonomy
snapshot (hostile robots.txt, never the daily crawler); Amazon PA-API is dead (Keepa if
Amazon history matters); eBay sold-listing scrapes for a used market later.

## Why it should work

The daily-fantasy insight transplanted: the whole skill of DFS is finding **mispriced
assets** — and our mispricing is generated continuously by Newegg. Players' real-world
hardware knowledge ("the 9800X3D punches above its price," "used 3090s are the VRAM value
play") becomes game skill. Reality is the live-ops team: every launch, price cut, restock
and shortage is content.

## Open questions for next session

1. **Name + fiction.** Who's the NPC buyer? A colony? "The Cloud"? A megacorp you
   contract for? The fiction picks the commodity list.
2. **Solo-idle satisfaction vs pure competition** — does a casual player who never reads
   the market still have fun watching rigs crunch? (RollerCoin says yes if the pro-rata
   pool pays everyone something.)
3. **Tick feel** — hourly ticks are right for settlement, but the UI should animate
   continuous crunching (the Bitcoin-mining dopamine is the point).
4. **Used market** — player-to-player part resale mid-round? (Depreciation exists; a
   resale market adds a whole trading layer — maybe season 2.)
5. **Scale target** — 10 friends, 500 degens, or open? Pricing formulas hold at small N;
   an EVE-style order book needs big N and is explicitly rejected for v1.
6. **Prototype path** — a one-week paper round in a spreadsheet with ~20 SKUs would
   validate the economy before any code.
