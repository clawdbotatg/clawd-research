# Deepstate maker-bot spec + DEEP-per-day math

*2026-08-19. All numbers read live from Robinhood Chain (Alchemy `robinhood-mainnet`,
chainId 4663) and computed from `DeepstateRewarder.sol` source. Read-only research —
nothing deployed, no funds moved.*

## TLDR

Earning DEEP = holding top-of-book on NVDA/USDG. Live data says: emissions are
**5.44M DEEP/day per side right now** and falling; **177 wallets** have claimed,
but **one bot owns 54.9% of everything distributed so far**; and the
**quantity ramp is a closing door** — today ~$9 at top-of-book earns full-rate
rewards, by day 21 it's ~$16k, by day 30 (Sep 14) it's **$1M per side, forever**.
The window for a small player is roughly **the next two weeks**.

## Live onchain state (as of 2026-08-19 ~16:45 PT)

- Rewarder `0xE85A…56D7`: `sideEmissionCap` = **500M DEEP per side** (1B total),
  `emissionDuration` = 34,128,000s = **395 days** — matches docs exactly.
- The order book contract is `0x6cf1…7B96` (labeled "Router" in DeLong's tweet;
  the rewarder's `deepstate` pointer names it as the book).
- Sides activated **Aug 15** (bid/USDG side epoch 1786778649, ask/NVDA side ~99min
  later). We are at **day ~4.7 of 395**.
- `totalAccrued`: bid side 26.78M / ask side 25.33M DEEP vs a theoretical ceiling
  of 27.2M/26.8M → **94–98% of possible rewards are being captured**. Top-of-book
  is occupied essentially continuously. No free lunch sitting around.
- Current top orders: **bid 105,512 USDG (~$105k)**, ask 28.2 NVDA (~$5k).
  Someone is already sizing the bid for the quantity ramp.

## Competition (verified twice; latest 2026-08-20 morning, day 5.3)

- **58.2M DEEP distributed** (21,967 events, **179 distinct claimants**).
  Cross-checked against the rewarder's DEEP balance (1B − 941.79M = 58.21M) —
  matches to 0.001%.
- Concentration: `0x2acb…0706` has **51.0%** (29.7M DEEP) — down from 54.9% a
  day earlier; #2 (`0x8b87…1d3f`) grew to 6.3%. The king is beatable at the
  margin.
- Interpretation: it's a latency + uptime war and one player is winning it, but
  ~half the flow still leaks to others — a competent bot gets a real share.
- Verification note (2026-08-20): all emission math re-checked against the
  contract's own view functions (`fullRewardQuantityAt`, `cumulativeEmissionsAt`)
  — the model in this doc reproduces them to 3+ significant digits. Decimals
  confirmed onchain: USDG 6, NVDA 18, DEEP 18.

## The two curves that decide everything (from Rewarder source)

**1. Emission curve** (per side): `cum(t) = 500M × ln(1 + t/30d) / ln(1 + 395d/30d)`.
Hyperbolic decay — rate = `500M / ((30d + t) · 2.6509)`:

| day | DEEP/day per side | cumulative per side |
|---|---|---|
| 4.7 (now) | 5.44M | 27.2M (5%) |
| 7 | 5.10M | 39.6M (8%) |
| 10 | 4.72M | 54.3M (11%) |
| 14 | 4.29M | 72.2M (14%) |
| 21 | 3.70M | 100.1M (20%) |
| 30 | 3.14M | 130.7M (26%) |
| 90 | 1.57M | 261.5M (52%) |
| 395 | 0.44M | 500M (100%) |

A quarter of all DEEP is emitted in the first month.

**2. Full-reward quantity ramp** (the strategic clock). Reward is scaled by
`min(orderSize / fullRewardQuantity, 1)`; the target grows geometrically for 30
days then freezes at max **forever**:

| day | bid side (USDG) | ask side (NVDA) |
|---|---|---|
| 4.7 (now) | ~$8.5 | ~3.7 NVDA (~$670) |
| 7 | $25 | 7.3 |
| 10 | $100 | 17 (~$3k) |
| 14 | $631 | 53 (~$9.6k) |
| 21 | $15.8k | 388 (~$70k) |
| 30+ | **$1,000,000** | **5,000 NVDA (~$900k)** |

So: today a $100 bid at top-of-book earns the full 63 DEEP/second. On Sep 14 the
same $100 earns 0.01% of it. **The design pushes small players out after week 3
and hands the schedule's remaining 74% to whales.** (Ramp params on chain:
bid 1→1M USDG, ask 1→5,000 NVDA, both `ln(ratio) ≥ 1000×` enforced.)

## Rough DEEP/day scenarios (both sides, at current emission)

`DEEP/day ≈ timeShareOnTop × sizeFactor × rate(t)` per side.

- **Casual (this week, ~$1k inventory, naive bot):** size factor 1 (target still
  tiny), maybe 1–3% top-time against the latency king → **100–300k DEEP/day**.
- **Serious (this week, low-latency bot, both sides):** 10–20% top-time →
  **1–2M DEEP/day**, decaying with the curve.
- **Post-ramp (day 30+, $50k inventory):** size factor caps at 5% on the bid
  side even with 100% top-time → ≤157k DEEP/day and falling. Basically shut out.
- **Post-ramp whale ($1M/side):** full budget contention resumes, 3.14M/day/side
  to fight over.

**What is DEEP worth? Unknown — that's the biggest number in this file.** No
market exists. Fundamental floor: DEEP→STATE→pro-rata vault fees. At $10M/day
volume × 10bps protocol fee ≈ $10k/day into the vault (~$3.6M/yr) against an
eventual ≤1B STATE. Order-of-magnitude only; treat all DEEP/day numbers as
lottery tickets on the protocol working.

## Bot architecture (if we build it)

1. **Infra:** Alchemy `robinhood-mainnet` RPC; fresh hot wallet (small balance
   only); ETH bridged for gas (100ms blocks, cheap); USDG + optional NVDA
   inventory.
2. **Quote loop:** read `topOrder(bookId, side)` each block; if not ours and the
   price is inside our fair-value band (external NVDA reference — Chainlink feed
   on-chain or Nasdaq off-hours logic), place/replace one tick better; size =
   `fullRewardQuantityAt(now) × ~1.2`, capped by inventory.
3. **Claim flow (critical, from source):** call `registerClaimant(bookId, order)`
   as soon as an order is placed — the engine deletes ownership on cancel/fill,
   and only a registered claimant can collect afterwards. Batch-collect with
   `distributeRewardsBatch` periodically (anyone can call; it pays the claimant).
3b. **⚠️ Side-naming trap (verified in source, DeepstateV1 line ~2143):** in the
   contract, `isBid=true` means *buying token0 (USDG) with token1 (NVDA)* —
   inverted from human NVDA-market intuition. **To bid for NVDA with USDG you
   place a contract-side ASK (`isBid=false`).** A bot that passes `isBid=true`
   for "bid on NVDA" quotes the wrong side of the book. Same inversion applies
   to reading `topOrder(bookId, isBid)`.
4. **FCFS reality:** Robinhood Chain sequences first-come-first-served — no gas
   bidding. Winning top-of-book races = raw latency to the sequencer. The 55%
   bot is winning that race today; we'd aim for the leak, not the crown.
5. **Risk controls:** max inventory drift (a filled bid = long NVDA through
   earnings, 24/7, with a Jersey-IOU asset); spread floor vs fair value (never
   quote through the reference); kill switch on depeg/halt; gas budget cap
   (repricing every few seconds, forever).

## "Never hold NVDA": the atomic claim-and-dump variant

Verified in `DeepstateV1.sol`: maker settlement is **pull-based**. A taker fill
does NOT push NVDA to the maker's wallet — proceeds accumulate inside the book
contract, and `cancel(token0, token1, epoch, order)` is the single call that
both cancels remaining quantity and **claims filled proceeds** (returns
`baseAmount`/`quoteAmount`, transfers out only then).

So a tiny helper contract gives us a bid-only bot whose wallet never carries an
NVDA balance across any transaction boundary:

1. `claimAndDump()`: call `cancel(...)` (receive NVDA inside the tx) → in the
   same tx, market-sell that exact NVDA amount back into the book against the
   best bid → sweep USDG home. NVDA exists only transiently mid-transaction.
2. Bot runs bid-side only (never needs NVDA inventory; ask side is off the
   table anyway). Max earnable = the bid side's 500M DEEP.
3. On fill detection, fire `claimAndDump` next block (~100–200ms on this chain).

**Cost per round trip:** crossing the spread on the dump + 10bps protocol fee
(direct contract calls skip the 10bps company fee). At a ~15bps spread that's
~25bps of filled volume — this is the real price of never holding, and DEEP
earned must beat it. Quote slightly wide to keep fill frequency (and thus dump
costs) down; the rewards pay for time-on-top, not for getting filled.

**Residual exposure, honestly stated:**
- Price exposure starts at the *fill*, not the claim — between fill and dump
  (~1–2 blocks) we own a claim on NVDA inside the contract. On a 100ms chain
  that's sub-second, but it's not zero.
- **Does it count legally? Probably doesn't change the core question.** The
  moment a bid fills, a purchase of the (Reg-S-restricted, not-for-US-persons)
  security token occurred; holding it for 200ms vs 2 days changes market risk,
  not the fact of acquisition/beneficial ownership. The restriction regime
  mostly binds the issuer and distributors rather than criminalizing the
  holder, and secondary DEX activity is a genuine gray zone — but "atomic dump"
  is a risk-mitigation, not a safe harbor. Real answer needs a securities
  lawyer; the mechanics are ready if the answer is yes.

## The honest caveats

- **US-person issue:** the bid side alone still fills into NVDA stock tokens,
  which Robinhood explicitly doesn't offer to US persons. Decide deliberately
  before funding anything.
- **DEEP may be worth zero.** The whole play is EV-positive only if STATE fee
  flow or a speculative DEEP market materializes.
- The dominant bot can widen its lead (it's earning 28M DEEP/4.7d and can spend
  it); the docs themselves warn rewards buy "aggression, not depth."
- Audit #693 of DeepstateV1 is still in progress — findings land in RESEARCH.md.

## Verdict

If we want DEEP at all, the move is **small and immediate**: this week a few
hundred dollars of USDG and a simple block-tick bot earns full-rate rewards
whenever it holds the top; in three weeks the same play needs five figures, in
four it needs seven. The decision that matters is not bot design — it's
**inventory size × the two-week window × whether holding NVDA tokens as a US
person is acceptable**.

## Volume verification (2026-08-20, day 5.5)

Independently verified 24h volume via protocol-fee transfers (book → vault over
24h ÷ 10bps): 9,462.6 USDG + 42.25 NVDA in fees → **$18.61M implied taker-output
volume**, vs the UI's displayed 18,688,555 USDG — a 0.4% match. Volume roughly
2× DeLong's "$10M first time" tweet. Method note: decoding Matched events
directly is unit-ambiguous (node quantities); the fee method is the clean
oracle. NVDA price at check: $216.56 (update any $183-based figures; ask-side
full-reward max = 5,000 NVDA ≈ $1.08M).
