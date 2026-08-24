# The Hardware Game — Complete Design Document

*Consolidated 2026-08-24 from three research passes + design sessions with Austin.
Detail docs: [PRIOR-ART.md](PRIOR-ART.md), [ECONOMY-DESIGN.md](ECONOMY-DESIGN.md),
[TOKENOMICS.md](TOKENOMICS.md), [PRIOR-ART-TOKENS.md](PRIOR-ART-TOKENS.md),
[RESOURCES.md](RESOURCES.md), [../hardware-db/DATA-SOURCES.md](../hardware-db/DATA-SOURCES.md).*

## 1. The pitch

A competitive resource-management game where you spend a **fake budget on real
hardware**. A crawler maintains a live catalog of actual CPUs, GPUs, RAM, DGX Sparks,
Mac Studios at real street prices with real benchmark numbers. Every round, every
player gets the same budget; you build machines; every tick your machines crunch —
producing hashes, inference tokens, spreadsheets, software — which fulfill contracts
that mint the round's token. Feels like Bitcoin mining × fantasy football × M.U.L.E.

**Research verdict: nobody has built this.** Every piece is proven separately (PC
Building Simulator's real-benchmark stats, DFS salary caps on real live-priced assets,
RollerCoin's mining loop, Power Grid's markets, Words3's burn-to-claim pot) — no one
has composed them. The killer property: **reality is the live-ops team.** A GPU price
cut, a new chip launch, a DGX restock mid-round is a balance patch nobody had to write.
And with the token layer: **the token launch IS the game** — distribution decided by a
week of skilled play instead of pump.fun sniper bots ("proof of play").

## 2. Round lifecycle

| Phase | What happens |
|---|---|
| **0. Buy-in** | N seats × $100 USDC → reserve `R`. Each seat mints **10,000 CREDITS** (soulbound, in-game only, never withdrawable). Multiple seats allowed — each is its own budget/power feed (parallelism, never compounding). |
| **1. Setup** | Catalog snapshot (real prices/TDP/benchmarks) signed + posted **before buy-in**. GM **commit-reveals** the randomness seed (event schedule, contract perturbations) — committed before buy-in closes, revealed at kickoff. Starting parts via snake draft or price-ladder open buy. |
| **2. Play (~1 week)** | Hourly ticks/epochs. Build, produce, refine, fulfill contracts, mint $GAME. Mid-round stipend drips (day 2/4/6) force re-decisions against a moved market. |
| **3. Sell-only valve** | During play, $GAME redeems against the reserve at the fixed floor `R/S_max` (token burned). No buyers of any kind. Early exits ratchet the floor UP for remaining holders (Moloch-ragequit mechanics). |
| **4. Graduation** | Round ends: emission stops, supply fixed forever. All round-final actions settle in **one batch at one uniform clearing price** — never a last-block race. Redemption stays open forever; part of remaining reserve seeds an open AMM. Now anyone, including non-players, can buy/sell. |
| **5. Next season** | Fresh token per round (identical factory bytecode). Next season's buy-in payable by **burning last season's token** at a posted rate — the demand sink that gives the after-economy a reason to exist. |

## 3. The resource graph (one-way by design)

```
CREDITS ──> hardware (capex) ──┐
CREDITS ──> watts (opex)  ─────┼──> TIER-1 raw ──┐
CREDITS ──> wages (opex)  ─────┘                 ├──> TIER-2 goods ──> contracts ──> $GAME
                 sloperators ────────────────────┘
gated everywhere by: power · space · heat · bandwidth · operator attention
```

Nothing converts backward — goods never become credits, so there is no reinvestment
and no compounding. **Earnings are score, not capital.** All skill lives in what you
build, when you pivot, and when you burn.

**Constraints (5):** power feed (real TDP; the second budget), space (rack units),
heat (cooling cap; AC draws watts — real PUE tradeoff), bandwidth (delivery gate),
operator attention (unsupervised machines idle at ~30%).

**Hardware:** GPU, CPU, RAM (batch multiplier), storage (**the warehouse** — you can
only stockpile what you have GB for; overflow spoils, so market-timing costs capex),
motherboard (slots), PSU (real 80+ efficiency), cases/racks, cooling, NICs, and whole
systems (DGX Spark, Mac Studio, Antminer — efficient, never upgradable). Facility
upgrades (transformer/AC/racks/fiber) are the lumpy Power Grid-style sinks.

**Sloperators (the workforce):** real AI models from a second crawled catalog. API
operators cost wages derived from real $/Mtok; **open-weight operators are wage-free
but hosted on your own VRAM + watts** — the build-vs-buy weld between the two
catalogs, and the mechanic no other tycoon can have. Operator quality stamps every
good Q1/Q2/Q3. **Q1 = SLOP**: mass-producible, floods its market, never worthless
(M.U.L.E. floor) but cheap. A new model launch mid-season is a free balance patch.

**Tier-1 raw (6)** — each keyed to a different real benchmark axis, so
rock-paper-scissors is inherited from silicon, not authored:

| | Driver | |
|---|---|---|
| HASH | hashrate benchmarks (+ real watts) | brute-force compute |
| TOKEN | tokens/sec (VRAM bandwidth) | raw inference stream |
| CYCLE | PassMark multi | compute-hours |
| QUERY | single-thread + IOPS | serving/DB ops |
| FRAME | 3DMark-class | rendered frames |
| GB-DAY | capacity | data custody / warehouse |

**Tier-2 goods (10; ~6 active per round, rotating):** SPREADSHEET, SOFTWARE, IMAGE,
VIDEO, COPY (cheap text slop, floods first), AGENT-HOUR (computer use), BLOCK (the
mining lane: HASH + bandwidth), DATASET (the one feedback edge — consumable operator
boost, capped, non-stacking), RENDER, AUDIO. Recipes combine raw goods (e.g.
SOFTWARE = TOKEN + CYCLE + QUERY).

**Contracts (the only exit):** an NPC contract board posts mixed baskets per epoch
("3 SPREADSHEET + 1 SOFTWARE + 2 IMAGE, min Q2"). Burned baskets split that epoch's
**fixed $GAME emission pro-rata**. Board repricing is the dynamic market; weekly
commit-revealed demand events ("VIDEO ×2 this epoch") shake the equilibrium; mixed
baskets keep any mono-build from reaching the mint.

**Decided:** no player-to-player trading of commodities or goods — everything is
internal to your factory until it burns. Kills the collusion/wash-trade surface and
keeps the game readable.

## 4. Token mechanics (why it can't death-spiral)

- Emission per epoch is **fixed and pro-rata**, so total supply `S_max` — and the
  floor `R/S_max` — are known **before anyone buys in**. Hardware inflation can never
  inflate the token; flooding an epoch just dilutes that epoch's burners.
- The Axie/StepN identity (faucet indexed to player count, sink to player *growth* →
  structural inflation when growth stops) is inverted by construction: the token is a
  claim on money **already in the system**, never fresh supply needing the next cohort.
- Publish the invariant live: `reserve ≥ outstanding supply × floor`. The sell-only
  curve is a hard redemption right — the thing OlympusDAO faked.
- Buy-to-redeem arbitrage (the Nouns-fork drain) is impossible: the only mint path is
  playing. Guard the commodity layer instead: basket → $GAME → floor-USDC must never
  exceed the basket's production cost in credits at rational play.
- Leaderboard = **cumulative $GAME minted**, so cashing out early never hides rank.

Closest deployed precedent: **Words3's `ClaimSystem`** (burn points →
`treasury × share`, gated to round end, on MUD) — this design is Words3 + the
sell-only valve + graduation liquidity + an actual economy underneath.

## 5. Economy rules that keep it competitive

1. **No reinvestment** — the one structural rule. A 5% early edge compounds to 2× by
   day 4 otherwise; with earnings-as-score, production is linear in time and skill
   lives in build choice + pivots + burn timing.
2. **Prices balance the meta, not us** — pro-rata epoch dilution + contract repricing
   mean the best build is whatever everyone else isn't running. Meta-chasing is
   self-defeating. Publish all formulas; reading the market IS the game.
3. **Scarce SKUs on Power Grid price ladders** — K units at street price, each
   purchase climbs the ladder (8th 5090 buyer pays 1.6×). 2–3 auctioned unicorn parts
   per round (one B200, one exotic).
4. **Watts can't be bypassed** (every production tick) and **wages can't be bypassed**
   (every mint path crosses an operator) — the two structural credit sinks.
5. **Wear meters, not RNG failure** — usage fills the meter, maintenance spend resets
   it. A sink, a decision, no dice, oracle-free.
6. **Bots are first-class** (0xMonaco): open contracts, published botkit, reputation
   leaderboard. Deterministic + open state means scripting wins anyway — embracing it
   recruits the hardcore dev audience and composes with the agent-esports thread.
7. **Fresh economy every round, cosmetic persistence only** — season N must be
   winnable by a newcomer (PoE league lesson).

## 6. Data stack (v1)

| Need | Source | Note |
|---|---|---|
| Prices | **Best Buy Products API** | free, official, near-real-time; covers laptops/Mac Studio too |
| Amazon prices | Keepa (€49/mo) | PA-API is dead (2026-05); optional |
| Hashrate **+ watts** | WhatToMine / hashrate.no / minerstat | best-behaved APIs of the lot |
| CPU perf | PassMark CSVs | license path if commercial |
| GPU specs/perf | dbgpu (open dataset, 2,800+ GPUs) | TechPowerUp licensing unnecessary |
| Tokens/sec | MLPerf + llama.cpp community benches | measured DGX Spark + Mac Studio numbers exist; gap-fill `bandwidth ÷ model_size × 0.7` |
| Compat taxonomy | PCPartPicker one-time snapshot | hostile robots.txt — never the daily crawler |
| Used market (later) | eBay sold-listing scrapes | driscoll42/ebayMarketAnalyzer |
| Operator catalog | provider price pages + SWE-bench/MMLU/tok-s boards | the second crawl |

Catalog posted as one signed snapshot per round — one oracle write per week,
disputable because it's public data.

## 7. Chain architecture

Hybrid on an L2 (Base): purchases, contract burns, emission, and redemption onchain;
production computed by the **lazy staking-accumulator pattern** (production is a pure
function of time — integrate `rate × price-epoch` on any player action or settlement;
no cron, no tick transactions). Builds are public by design (no hidden info onchain —
embrace it; the market-read game is richer, like Power Grid's open resource track).
Burner wallets for feel. GM surface minimized: signed catalog + commit-revealed seed +
pre-committed contract schedule.

## 8. Failure modes (ranked) and the engineering answer

1. **Regulatory shape** — entry-funded pot that scales with entries fails the DFS
   fixed-prize factor; post-round liquid token rhymes with Dapper's "controlled
   cash-out" Howey pattern; buy-USDC→credits→redeemable-token silhouettes the
   sweeps-casino model ~17 states are killing. *Answers:* no house rake, fully
   deterministic open-source rules, geofence hostile states, chip framing never
   investment framing — and the **post-round open-trading phase is severable: ship
   redeem-and-burn-only v1**, add open trading later if the CLARITY Act lands.
2. **Endgame MEV** — FOMO3D was won by block-stuffing for ~4 ETH. *Answer:* batch
   settlement at one uniform price; pre-seeded graduation liquidity; no last-actor
   prizes anywhere.
3. **Bots/collusion harvest the median player** — Words3's winner scripted a 6.1%
   edge while 85% lost money. *Answers:* embrace bots openly; no P2P trading (kills
   collusion transfer); seats as the sybil unit (parallel, never compounding); short
   event-shaped rounds.
4. **Commodity-layer arbitrage** — if minting ever beats production cost, play
   collapses into farming. *Answer:* price the floor below marginal production cost;
   credits non-transferable; VRGDA-style inner pricing.
5. **Round cadence dies before contracts do** — every pot-round game (Words3, Dark
   Forest, Sky Strife) died of hosting burnout, not mechanism failure. *Answers:*
   rounds as events; budget operations as the real product; the game must pass the
   carnival test — fun worth $100 even if you cash out $0.

## 9. Open questions

1. **Name + fiction** — who is the contract board? A megacorp? "The Slop Economy"?
   The fiction picks the flavor of the goods list.
2. **Reserve split at graduation** — how much seeds the AMM vs stays redemption
   backing (Zora's fee-funded permanent-liquidity ratchet is a nice middle).
3. **Emission curve shape** — flat per epoch vs ramping late (comeback fuel).
4. **Prize concentration** — pure pro-rata mint vs a steeper payout for hype (gentler
   is better for failure modes #1 and #5).
5. **Casual floor** — if someone ignores the market entirely, is it still satisfying
   to watch their rigs crunch? (RollerCoin says yes, provided everyone earns something.)
6. **Tick feel** — hourly settlement, but the UI should animate continuous crunching;
   the Bitcoin-mining dopamine is the point.

## 10. Next step

**A paper round.** One week, ~20 real SKUs, a spreadsheet (or tiny sim script), 5–10
friends, fake everything including the token. Validates: recipe balance, contract
repricing, whether the stipend drip creates real re-decisions, and whether the
carnival test passes — before any Solidity exists.
