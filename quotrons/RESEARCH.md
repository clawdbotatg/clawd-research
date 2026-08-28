# Quotrons — handoff notes

Researched 2026-08-28 from https://www.quotrons.cash/docs (live page, JS-rendered —
plain fetch gets nothing, use a real browser or their llms.txt endpoints).
Companion file: `llms-full-2026-08-13.txt` — the project's own machine-readable
reference, vendored here. **It predates the Ink venue and the Stonks Incinerator
sections**; those live only on the docs page (summarized below).

## What it is, in one paragraph

ERC-404 experiment on **Robinhood Chain (chain id 4663)** by Mavrk, Inc.
4,444 $QUOTRON tokens; holding a whole token materializes a pixel-art NFT
"terminal" (historical stock-quote machines) in your wallet. Burning the token
("hardwiring") makes the terminal permanent and it starts earning tokenized
stock rewards from trading fees, forever. The terminals do nothing functional —
"lit" just means the NFT's screen animates its assigned stock ticker. It's a
yield-bearing collectible, not a computer. V2 — V1 was retired 2026-08-12 after
a stale-ERC721-approval exploit on its mirror; V2 redistribution was zero-action.

## The three mechanisms worth knowing (why this got researched)

### 1. The routing lock — token-enforced fees on Uniswap v4 (the novel bit)

Problem: every v4 pool settles through the one PoolManager singleton, so a token
can't distinguish its pool from a copycat by address. Their solution:

- Token blocks all transfers to/from the PoolManager by default.
- Their hook, during a swap in the registered pool (`afterSwap`), writes a
  settlement authorization into **transient storage** (tstore/tload) — exact
  amount, exact direction, dies with the transaction
  (`quotron.authorizePoolTransfer(delta)`).
- The token's transfer check decrements the authorization on settlement;
  anything unauthorized reverts `UnauthorizedPoolSettlement`. Inbound to the
  PoolManager additionally requires `msg.sender == canonicalRouter`.
- A rogue v4 pool runs without their hook → no authorization → can't trade,
  and **can't even be seeded** (seeding is itself a transfer to the PoolManager).
- Router asserts every authorization fully consumed post-swap (closes the
  ERC-6909 claim-banking hole).

Result: the 3% fee is enforced in the token, not the venue — unavoidable on v4.
Limits (they state them): v2/v3-style pairs never touch the PoolManager, so
those are banned reactively by runtime **codehash** (owner action; EOAs
unbannable by construction, wallet-to-wallet transfers always free). A novel AMM
works until identified.

This is the first clean solution I've seen to "make a token fee unskippable on
v4." Pattern is reusable independent of the token.

### 2. Burn as state conversion

Invariant, in the token: `economicUnits() = totalSupply + totalHardwired * UNIT`
— always 4,444. Every unit is either **liquid** (tradable, generates fees) or
**hardwired** (permanent NFT, consumes fees). Burning doesn't destroy value; it
moves a unit from the fee-generating float to the fee-consuming claimant set.
Self-limiting: each burn shrinks the float and adds a permanent claimant, so
per-terminal yield dilutes as commitment rises. First hardwire on a track claims
that track's entire accrued pot (ten tracks, ten "races"). `totalSupply` really
drops (no dead-address parking). One-way — no un-hardwire function exists.

### 3. Self-consuming gacha

Dark terminals are random draws from a **lazy Fisher–Yates** pool over unclaimed
IDs (zero-storage until touched; slot value 0 ⇒ slot+1). Seed =
keccak(prevrandao, timestamp, block, recipient, nonce) — admitted
pseudorandomness, not an oracle. Dissolution is LIFO (newest dark terminal
dissolves first). Sell below a whole unit + rebuy = reroll for a rarer tier.
Every hardwire removes that ID from the pool forever, so odds concentrate on the
remaining dark supply — the flipper game and holder game consume each other.

## Economics

- **Fee: permanent 3%** of WETH-side volume, taken by the hook (pool LP fee
  forced to 0). Carve is parts-per-240 in `QuotronV2FeeLib`:
  reflections 160 (2.0000% of volume), locked LP 51 (0.6375%), $STONKBROKER
  buy-and-burn 17 (0.2125%), creator 12 (0.15%). Swap fee only — transfers free.
- Fees queue as WETH; a keeper converts to the ten stocks in **epochs**
  (≥0.1 WETH to open, cap 100 WETH, ≥60s apart), split equally across ten
  sealed routes. Per track: 82.5% to hardwired terminals by weight, 12.5% split
  across three basket relics, 5% to the Gold Indicator relic (gets all ten
  stocks).
- Fee pots are **destination-locked** (only the reflections sink pulls the
  reflections pot, etc.); no arbitrary sweep function. Creator share taken
  in-swap, no custody.
- **Tiers/weights:** T1 Quotron I Keypad 2,450 @1.0x · T2 Desk Unit 1,330 @1.5x ·
  T3 Quotron 800 530 @2.5x · T4 NASDANK 130 @5.0x · 4 relics (ids 4441–4444)
  with own volume streams. Ten tracks × 444 machines, identical tier mix
  (245/133/53/13). Stocks: NVDA AAPL TSLA GME SPCX SPY PLTR NFLX RDDT MSTR.
- **Broker boost:** hold ≥1 STONK BROKER NFT → 1.25x weight on your hardwired
  standard terminals, read live; anyone can `poke(id)` to re-price a stale boost.
- Rewards accrue masterchef-style; `pending(id)` / `claim([ids])` on the
  reflections contract; pending rewards travel with the NFT on transfer (seller
  can claim right before sale — check at execution).
- Launch used a 90% public fee phase; **finalized irreversibly to 3%** on-chain.

## Live state 2026-08-28 (homepage census)

2,657 / 4,444 hardwired (~60% of supply burned, ~$18.7M at spot). Token
~$7,035. Liquid mcap ~$12.6M, FDV ~$31.3M. All-time rewards to holders:
V1 archived $113,849.84 + V2 live ~$262.5k + OpenSea royalties ~$138.4k
(~$515k total). V1 halt block 34,984,482 (2026-08-12).

## Builder surface (all permissionless, no keys)

**Robinhood Chain, RPC `https://rpc.robinhoodchain.com`.** Note our RPC rule:
use Alchemy where supported; Robinhood Chain may not be on Alchemy — this
public RPC is what their docs use for verification examples.

- Router `0x42024fCFdB4F3089Dd619A0cEF0Cd24E7b841C18`:
  `buyExactEth(minOut, recipient, deadline)` payable, `buyExactQuotron`,
  `sellExactQuotronForEth(quotronIn, minEthOut, recipient, deadline)`.
  Native ETH both directions. **Gotcha: caller is the payer** — fee tier and
  ERC-20 allowance are the caller's, not the end user's.
- Quoter `0xb8960fdC8A0Be155d196C2795b75747763562df2`: `quoteBuyExactEth`,
  `quoteSellExactQuotron`, `quoteBuyExactQuotron`, `currentFeeBps(payer)` —
  views, return full fee breakdown.
- **Stonks Incinerator** `0xc388e730807C6F69b959443Ed497C731b8d138F9`:
  ownerless/immutable one-tx liquidator, tokenized stocks → USDG / ETH /
  $QUOTRON. 2.5% service fee to admin Safe. EIP-2612 permit variants
  (permit slots try/catch'd — front-run permits harmless). Generic surface
  `incinerateAny` takes ANY token with a hookless V4 USDG pool (or V3) —
  open infrastructure any project can use. Pool params must match exactly or
  it reverts on an uninitialized pool. Quote by `simulateContract` of the
  exact call.
- Docs page has downloadable ABIs (router/token/hook/quoter), INTEGRATION.md,
  manifest.json, plus `/llms.txt` and `/llms-full.txt`.

### Key contracts (Robinhood Chain, full addresses from llms-full.txt)

| Contract | Address |
|---|---|
| $QUOTRON ERC-404 core | `0x5a86828Efd322bfb16d93cFeD16EE9BC14940D7F` |
| Terminal NFT mirror (ERC-721) | `0x027ACa2794E44f24950D81227DcD516FfBB49d6e` |
| Reflections engine | `0xe04fba61FD54Ba78Dd450A30d8Af40167aF5d3Ec` |
| WETH fee hook | `0x62E200Cc8e4D95cf622f40Dd70f407C883EcB0cc` |
| Canonical ETH router | `0x42024fCFdB4F3089Dd619A0cEF0Cd24E7b841C18` |
| View quoter | `0xb8960fdC8A0Be155d196C2795b75747763562df2` |
| Epoch stock converter | `0x24e62Dd5C7058CC41ad9c5375C137460ea1Da2FE` |
| Stonks incinerator | `0xc388e730807C6F69b959443Ed497C731b8d138F9` |
| Locked LP vault | `0x4b7A4F53D9b7E4B4941bc9CF74e852D55444cCBe` |
| STONK BROKERS collection | `0x539CdD042c2f3d93EbC5BE7DfFf0c79F3B4fAbF0` |
| Recovery Safe (≥2 threshold) | `0x15277aA1ecC13734d57C519a2DAA1cc4A748bA89` |
| Blacklist guardian / creator | `0x7171E64E979265aeD6588577D1c6b60A701d7866` |
| Royalty splitter | `0xd8eb805e96B05cb412A1e48eb3a85B6267f901d7` |
| Canonical QUOTRON/WETH pool id | `0x0b142aaf734f1b063355bfe854e282a13b26dcac86e2e564e74540f9b218d069` |
| V1 (historical) core / mirror / reflections | `0x40686524e56AfF0F1446958725dCF6e6dA5381E6` / `0xbde7BEc47cbFc689e5E952B6cdD113A500abcd83` / `0x666A51Eb731a9CF79d97B4A9c64cD5a4806c877C` |

More (eligibility registry, burn vault/adapter, seeder, migrator, reserve,
fractional sink, WETH, USDG) in `llms-full-2026-08-13.txt` §11.

Provenance commitments: assignment seed `44440707`, `assignmentHash()` on the
token, art/metadata pinned to IPFS (CIDs on the docs page), generator published
— collection reproducible byte-for-byte.

## The Ink venue (separate thing, NOT in llms-full.txt)

Tokenized-equity venue on **Ink (chain id 57073)**: eight Uniswap V4 pools of
Backed **wrapped** xStocks (ERC-4626 wrappers, never raw rebasing tokens) vs
USDG. 0% LP fee + 0.30% hook fee in USDG, split 50/50: terminal-holder pot
(pooled venue-wide, epochs ≥$250 / cap $10k / ≥5min) and per-pool LP vault.
Fee steppable by operator 0.05%–1.00%, bounds immutable — quote live, don't
assume 0.30%. No oracle anywhere; price is the AMM curve; they warn LPs plainly
about 24/7 pools vs 32h/wk equities gap risk. Public LP deposits NOT open yet
(pending audit). Accounting contracts are UUPS proxies (upgrade authority =
the Safe, separate from operator; `renounceUpgradeability()` planned post-audit);
the hook in the swap path is immutable: `0x8bb4516059F9149Bc3b89018Fc7537f1F14a30cc`.

Integration: ordinary V4 — PoolKey uses `DYNAMIC_FEE_FLAG` (0x800000, **not**
3000 — hardcoding 3000 derives a wrong pool id), tickSpacing 60, their hook.
Factory has `poolOf(stock)` / `vaultOf(stock)` / `allStocks(i)`. Public Ink RPC
prunes state and rejects batched calls — use a paid RPC.

Subgraph (Goldsky, no key):
`https://api.goldsky.com/api/public/project_cmssuu23e13si01xt3o30067i/subgraphs/quotrons-ink-stocks/prod/gn`
— pools{symbol, feeBps, priceUsdE6, volumeUSDG, feesToTerminal…}, swaps.

Two donation contracts accept plain WETH from anyone and deploy it next epoch
(terminal pot, liquidity growth sink) — **one-way, no withdrawal**. Ink
addresses are truncated on the docs page (copy buttons / Blockscout links have
full values); only the hook address above is confirmed full.

## Trust assumptions / risks (their own disclosure, verified in doc text)

- Owner can pause token + hook; ban/unban venue codehashes.
- Blacklist guardian (`0x7171…7866`) can freeze (not unfreeze/move).
- **Recovery Safe (`0x1527…bA89`, enforced threshold ≥2) can forcibly move any
  user's balances or terminal NFTs** between non-protocol accounts — this is
  how V1 restitution worked. Every action emits an event.
- Payouts are keeper-dependent (fees accrue safely if keeper stops, but nothing
  pays out).
- The "stocks" are third-party upgradeable tokenized products — issuer can
  pause/alter them. **US-restricted.** Rewards framed as "promotional," not
  dividends.
- ERC721-C royalties (5%: 4% keeper / 1% creator) enforced via transfer
  validator — venue-restricted, wallet-to-wallet always passes; validator
  frozen at launch.
- V1 postmortem: an ERC-721 approval could survive burn + rematerialization;
  V2 clears per-token approval on every ownership/state change incl. hardwire.

## Misc pointers

- X: @Quotrons404 (project) / @quotrons404 (integration contact). OpenSea:
  opensea.io/collection/Quotrons404. Brand kit:
  github.com/mavrkofficial/quotrons-brand-kit.
- Docs have an "Ask the Desk" LLM clerk; site serves full text in DOM for
  crawlers (verified — that's how this doc was made).
- Only supported trading venues: quotrons.cash Exchange tab and Sentry.
