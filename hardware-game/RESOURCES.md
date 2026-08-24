# The Resource Graph: every sink and faucet

The economy in one sentence: **CREDITS buy hardware and watts; hardware turns watts
into raw compute commodities; operators refine raw commodities into AI-made goods;
goods fulfill contracts that mint $GAME.** Nothing converts backward (goods never
become credits — that's the no-compounding rule), so the whole graph flows one way
from buy-in to token.

```
CREDITS ──> hardware (capex) ──┐
CREDITS ──> watts (opex)  ─────┼──> TIER 1 raw ──┐
CREDITS ──> wages (opex)  ─────┘                 ├──> TIER 2 goods ──> contracts ──> $GAME
                 operators (sloperators) ────────┘
constraints gating everything: power · space · heat · bandwidth · operator attention
```

## Layer 0 — Constraints (never produced, only expanded; the knapsack walls)

| Constraint | What sets it | Expanded by | Why it exists |
|---|---|---|---|
| **Power feed** (watts) | Base 1,500W | Transformer upgrades (escalating cost) | The second budget. Real TDP per part. A 5090 vs two 4070s becomes a real decision. |
| **Space** (rack units) | Base rack | Racks, rooms | Caps machine *count*; makes small-form (Mac Studio, DGX Spark) genuinely different from towers. |
| **Heat** (BTU out) | Σ watts drawn | Fans, AC units (which draw watts themselves!) | Over cooling cap → machines throttle %. Cooling eats power — a real datacenter PUE tradeoff. |
| **Bandwidth** (Gbps) | Base uplink | Fiber upgrades, NICs, switches | Gates how much output you can *deliver* per tick. A hash farm with a thin pipe strands product. |
| **Operator attention** (slots) | 0 at start | Hiring sloperators | Every machine needs supervision to run at 100% duty; unsupervised machines idle at ~30%. |

Five walls is the ceiling — money+watts is the core knapsack, the other three are
coarse (buy the upgrade or don't), not fine-grained bookkeeping.

## Layer 1 — Hardware (the crawled catalog; capex, all CREDIT sinks)

| Class | Role in the graph | Real data driver |
|---|---|---|
| **GPU** | Produces HASH, FRAME; runs MODELS (TOKEN) | hashrate.no/WhatToMine (hashrate **+ watts**), TechPowerUp/dbgpu, tokens/sec benches |
| **CPU** | Produces CYCLE, QUERY | PassMark multi + single-thread |
| **RAM** | Multiplier: batch size / concurrent jobs per machine | capacity + speed |
| **Storage (SSD/HDD)** | **Warehouse**: GB-DAY capacity — you can only stockpile goods you can store (burn-timing skill needs capex!) | capacity, IOPS |
| **Motherboard** | Slot counts: how many GPUs/RAM per machine | spec sheets |
| **PSU** | Converts feed-watts → usable watts at an efficiency % (80+ ratings are real!) | wattage + 80Plus tier |
| **Case / rack** | Space units consumed; airflow modifier | form factor |
| **Cooling (fans, AC)** | Raises heat cap; draws watts | BTU/wattage |
| **Network (NIC, switch)** | Raises bandwidth | port speeds |
| **Whole systems** (laptop, Mac Studio, DGX Spark, Antminer) | Pre-built: fixed recipe of the above, often space/watt-efficient, never upgradable | measured system benches (DGX Spark + Mac Studio tokens/sec exist) |

Plus **facility upgrades** (transformer, AC, racks, fiber) — the big lumpy credit
sinks that shape build orders, Power Grid style.

## Layer 2 — Sloperators (the workforce)

Machines don't run themselves; **operators are real AI models from a second crawled
catalog** (the mirror of the parts catalog):

- **API operators**: real frontier models, wage = real $/Mtok scaled into credits/tick.
  High quality, zero setup, pure opex drain.
- **Open-weight operators**: no wage — but they must be *hosted on your own hardware*,
  eating VRAM + watts + a machine slot. The build-vs-buy weld between the catalogs.
- **Stats from real benchmarks**: quality (SWE-bench/MMLU-tier composite), speed
  (tok/s), span (how many machines one operator supervises).
- **Quality gates**: every Tier-2 good is stamped Q1/Q2/Q3 by its operator's quality
  tier. Q1 is **SLOP** — mass-produced, floods its market fast. High contracts demand
  Q2+. The slop-vs-craft decision is the operator decision.
- A new model launch mid-season is a free patch: a cheap open-weight model drops and
  suddenly self-hosting flips the meta.

## Layer 3 — Tier-1 raw commodities (machines + watts → raw; benchmark-driven)

| Commodity | Produced by | Real driver | Flavor |
|---|---|---|---|
| **HASH** | GPU/ASIC raw compute | hashrate benchmarks (algo-specific) | brute-force number crunching |
| **TOKEN** | GPU/system running a loaded model | tokens/sec (VRAM bandwidth) | raw LLM inference stream |
| **CYCLE** | CPU multicore | PassMark CPU Mark | general compute-hours |
| **QUERY** | CPU single-thread + RAM + IOPS | single-thread + storage | serving/database ops |
| **FRAME** | GPU raster/render | 3DMark-class benches | rendered frames |
| **GB-DAY** | Storage at rest | capacity | data custody (also the warehouse constraint) |

Six raw resources, each keyed to a *different* real benchmark axis — the
rock-paper-scissors is inherited from silicon, not authored. An EPYC box is a
CYCLE/QUERY monster and a HASH disaster; a DGX Spark is a TOKEN fountain that makes
zero FRAMEs.

## Layer 4 — Tier-2 refined goods (what people actually use AI to make)

Transformer workshops ingest raw + watts + operator attention. Recipes (tunable):

| Good | Recipe (raw inputs) | Real-world mirror |
|---|---|---|
| **SPREADSHEET** | TOKEN + CYCLE + QUERY | data analysis / financial modeling |
| **SOFTWARE** | TOKEN (code) + CYCLE (build/CI) + QUERY (tests) | AI coding |
| **IMAGE** | TOKEN + FRAME | diffusion: prompt + GPU render |
| **VIDEO** | IMAGE + FRAME + GB-DAY | gen-video: frames at scale + storage |
| **COPY** | TOKEN | text/stories/marketing slop — cheapest good, floods first |
| **AGENT-HOUR** | TOKEN + CYCLE + QUERY | computer-use agents doing desk work |
| **BLOCK** | HASH + bandwidth | the crypto-mining lane: raw hash → settled proof |
| **DATASET** | GB-DAY + QUERY + TOKEN | cleaned/labeled data — *special: consumable that temporarily boosts an operator's quality tier (capped, non-stacking — a boost, never a compounding loop)* |
| **RENDER** | FRAME + CYCLE + GB-DAY | film/3D render farm output |
| **AUDIO** | TOKEN + CYCLE | music/voice generation |

Ten goods is the full menu; a round probably *activates* 6 of them (rotate per
season — league mechanics for free).

## Layer 5 — Contracts → $GAME (the only exit)

The NPC buyer is a **contract board**: each epoch posts contracts — "deliver
3 SPREADSHEET + 1 SOFTWARE + 2 IMAGE, min Q2 → basket credit toward this epoch's
emission." Burned baskets split the epoch's fixed $GAME emission pro-rata
(TOKENOMICS.md). Contract composition is where all the market dynamics live:

- Board repricing = the dynamic market (a good everyone floods gets demanded less).
- Weekly commit-revealed **demand events** ("a studio needs VIDEO — video contracts
  ×2 this epoch") shake the equilibrium.
- Mixed baskets mean no mono-build reaches the mint; the *ratio* of goods demanded is
  the balance dial the GM pre-commits.
- Q1 SLOP contracts always exist (M.U.L.E. floor — nothing is worthless) but pay
  little; quality climbs pay disproportionately.

## The full sink/faucet ledger

**CREDIT faucets**: buy-in 10k; optional stipend drips (day 2/4/6).
**CREDIT sinks** (should drain ~everything by round end): hardware + price-ladder
premiums, auctions, facility upgrades, electricity (dynamic tariff — the biggest
recurring sink), operator wages, maintenance (wear meters).

**Commodity faucets**: machine production (linear in time, benchmark-rated).
**Commodity sinks**: recipe inputs (internal demand), contract burns (the mint),
**storage overflow** (goods beyond GB-DAY capacity spoil at tick end — no infinite
stockpiling without storage capex), DATASET consumption.

**$GAME faucet**: epoch emission only (capped, pro-rata).
**$GAME sinks**: sell-only redemption during round; next season's buy-in burn.

## Sanity rules baked in

1. **One-way flow**: goods never convert to credits — no reinvestment, no compounding
   (ECONOMY-DESIGN.md §4). The DATASET boost is the one feedback edge, and it's capped.
2. **Every mint path crosses an operator** — the wage/hosting sink can't be bypassed.
3. **Every production tick crosses watts** — the tariff sink can't be bypassed.
4. **Stockpile-to-time-the-market requires storage** — the timing skill has a capex
   price, and the "sell wall at epoch end" is naturally damped.
5. Contract ratios + quality gates are the GM's pre-committed balance levers; part
   stats are never touched (they're real).
