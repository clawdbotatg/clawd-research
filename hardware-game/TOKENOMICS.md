# Tokenomics: Buy-in → Curve → Skill-Weighted Token Launch

Austin's extension (2026-08-24): real-money buy-in ($100 → 10k in-game credits), buy-ins
pool into a curve, gameplay mints the final token via burn recipes, sell-only during the
round, fully liquid after. **The core reframe: the token launch IS the game.** Instead of
pump.fun sniper bots deciding a token's distribution, a week of skilled play does —
"proof of play" distribution.

Supporting research: [PRIOR-ART-TOKENS.md](PRIOR-ART-TOKENS.md) (FOMO3D, Words3, Axie/StepN
spirals, bonding curves, one-way valves, legality landscape, season tokens).

## The mechanism

**Phase 0 — Buy-in.** N seats × $100 USDC → reserve `R`. Each seat mints **10,000
CREDITS — soulbound, in-game only, never withdrawable**. (0xMonaco's lesson: every unit
of "realness" in the inner currency is a unit of design freedom lost. Keep the inner
economy maximally fake; only the terminal token is real.)

**Phase 1 — Setup.** Snake draft (or Power Grid price-ladder open buy) for starting
parts. Game master **commit-reveals the randomness seed** — committed before buy-in
closes, revealed at kickoff — covering the event schedule and catalog perturbations, so
the GM's only powers are pre-committed. Catalog itself is a signed snapshot (real prices,
TDP, benchmark rates) posted before buy-in.

**Phase 2 — Production graph** (deterministic, the sinks/faucets ledger):

```
CREDITS ──buy──> machines (capex)          [faucet: buy-in; sink: catalog + ladders]
CREDITS ──pay──> watts (dynamic tariff)     [the universal input + biggest credit sink]
machines + watts ──> Tier-1 raw:    hashes, inference-tokens, cycles
Tier-1 + watts + transformer machines ──> Tier-2 refined: spreadsheets, software, renders, computer-use
Tier-2 recipe basket ──burn──> $GAME        [the only mint path]
```

Transformers ingesting Tier-1 is the DGX-Spark chain Austin described: the Spark eats
watts and emits inference tokens/minute; a "software factory" eats inference tokens and
emits software. Recipes require **mixed baskets** (e.g. 3 spreadsheets + 1 software +
2 renders → mintable unit) so no mono-build reaches the mint — the recipe is the
anti-meta backstop on top of dynamic commodity prices.

**Phase 3 — Emission.** Per-epoch (hourly) **fixed max emission, split pro-rata among
burners that epoch** (RollerCoin's trick, moved to the mint). Consequences:
- Total supply `S_max` = emission/epoch × epochs is **known before anyone buys in**.
- Floor price `R / S_max` is therefore known before buy-in.
- Hardware/commodity inflation can never inflate the token — burning more baskets into a
  crowded epoch just dilutes that epoch's other burners (self-balancing, like everything
  else in this design).
- Leaderboard = cumulative $GAME minted (so selling early doesn't hide your rank).

**Phase 4 — Sell-only valve (during round).** $GAME redeems against the reserve at the
fixed floor `R/S_max`, token burned on redemption. No outside buyers, no buying at all.
Properties the prior art says to say loudly:
- This is **Moloch ragequit**, the most battle-tested pattern in the list — a hard
  redemption right, the thing OlympusDAO/Wonderland "backing" faked. Publish the
  invariant live: `reserve ≥ outstanding × floor`.
- Every early exit below final value **ratchets the floor up** for remaining holders.
- Buy-to-redeem arbitrage (the Nouns-fork drain) is impossible by construction — the
  only way in is playing.

**Phase 5 — Graduation (round end).** Emission stops; supply fixed forever. All
round-final actions settle in **one batch at one uniform clearing price**
(Hegic-IBCO-style) — never a "last block wins" boundary; FOMO3D's ending was bought for
~4 ETH of block-stuffing and pump.fun graduations get sniped, so the endgame must be a
window, not a race. Then: redemption stays open forever (floor never dies), and part of
the remaining reserve is **pre-seeded into an open AMM pool** (pump.fun's graduation
move) so day-one public depth is known in advance, not a cliff. Now non-players can buy;
floor = redemption, upside = the after-economy.

**Phase 6 — Seasons.** Fresh token per round (poker-tournament accounting: balance
errors quarantined, honest terminal state, identical factory bytecode each time), with
**next season's buy-in payable by burning last season's token** at a posted rate — the
demand sink that gives the post-game economy a reason to exist. Alternative shape if
seasons compound: one persistent token with seasonal *prize pools* funded by recycled
revenue, never fresh emission (Aavegotchi's rarity-farming model — 8+ seasons, no
spiral; TreasureDAO's shared-token maximalism died of concentrated balance debt).

## Why this dodges the classic death spirals

The Axie/StepN accounting identity: faucet indexed to player *count*, sink indexed to
player *growth* → net emission goes structurally positive the moment growth flattens.
Here the mint is **capped against the reserve ex ante** — worst case is a redemption
drain of known maximum depth, not a spiral. The survivor invariant across every game
that lived: *rewards are claims on money already inside the system, never fresh supply
whose value needs the next cohort.* This design has it by construction.

Closest deployed precedent: **Words3's `ClaimSystem`** (Small Brain Games) — burn
points → `treasury × points/totalPoints`, gated until round end, on MUD. This design =
Words3 + the sell-only curve during play + the post-round liquidity phase + an actual
economy underneath instead of Scrabble.

## The five failure modes to engineer around (ranked, from the research)

1. **Regulatory shape.** Entry-funded pot + winner-take-most + post-round liquid token
   trips three patterns at once: it fails *Humphrey v. Viacom*'s key entry-fee-≠-bet
   factor (prize must be **fixed in advance, not scale with entries** — ours is the pooled
   entries), it rhymes with *Dapper Labs*' "controlled cash-out" Howey pattern (which
   survived dismissal, settled $4M), and "buy USDC → non-transferable credits →
   redeemable token" silhouettes the sweeps-casino dual-currency model that ~17 states
   are actively killing (CA AB 831, IL cease-and-desists). Mitigations from the record:
   no house rake from the pot, fully deterministic open-source rules (stronger skill
   story than DFS), geofence hostile states, chip framing never investment framing, and
   consider redeem-and-burn only (skip free-floating post-round trading) for v1. The
   post-game open-trading phase is the single riskiest component — it's severable; ship
   it last, if at all, and watch the CLARITY Act (Senate, Sept 2026).
2. **Endgame MEV.** Any deterministic boundary block is an ordering auction. Batch
   settlement at uniform price; pre-seeded graduation liquidity; no "last actor" prizes.
3. **Bots/collusion harvest the median player.** Words3's winner scripted a 6.1% edge
   while 85% of players lost money; Dark Forest's additive scoring was dominated by DAO
   squads. Deterministic + open state means scripting WILL win — so embrace it
   explicitly (0xMonaco: bots as first-class, ship a botkit, reputation leaderboard),
   keep rounds short and event-shaped, and make seats the sybil unit (more seats = more
   parallel budgets, never compounding).
4. **Commodity-layer arbitrage.** The reserve caps token emission, but if
   basket → $GAME → floor-USDC ever exceeds the basket's production cost in credits,
   play collapses into mechanical farming. Price the floor below marginal production
   cost at rational play; keep CREDITS non-transferable; VRGDA-style pricing on the
   inner economy (0xMonaco's template).
5. **Round cadence dies before contracts do.** Words3, Dark Forest, Sky Strife: the
   failure was always hosting burnout, not mechanism failure — and zero-sum-minus-rake
   means the median player is the yield. Budget round operations as the real product;
   the game must pass Doucet's carnival test (fun worth $100 even if you cash out $0).

## Open questions

1. **How much of the reserve seeds the AMM vs stays redemption backing?** (Zora's
   fee-funded permanent-liquidity ratchet is a nice middle: route trading fees into the
   pool forever.)
2. **Emission curve shape** — flat per epoch, or ramping (late-round epochs emit more =
   comeback fuel, matches the NPC-demand-grows design in ECONOMY-DESIGN.md)?
3. **Recipe governance** — fixed at round start (fully deterministic) vs one mid-round
   commit-revealed "market event" that changes a recipe (shakes the meta, but adds GM
   surface).
4. **Prize concentration** — pure pro-rata mint is gentler than winner-take-most
   (better for failure mode #1 *and* #5); is a steeper payout needed for hype?
5. **Where** — an L2 (Base) with the lazy-accumulator production pattern from
   ECONOMY-DESIGN.md §5; burner wallets for feel.
