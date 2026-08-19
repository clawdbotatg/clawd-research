# Deepstate (deepstate.sh) — deep dive

*Researched 2026-08-19, prep for Austin's podcast with Joseph DeLong (Friday).*

## TLDR

Deepstate is a **fully onchain central limit order book (CLOB) DEX on Robinhood Chain**,
built by **Joseph DeLong** (ex-SushiSwap CTO). Its first market is **NVDA/USDG** —
Robinhood's tokenized-Nvidia token vs Paxos's Global Dollar stablecoin. The pitch:
real order books (price-time priority, like Nasdaq) are better than AMMs for
equity-like assets, and Deepstate's radix-tree design makes a true onchain book
gas-feasible on an EVM chain. Two tokens: **DEEP** (rewards for whoever holds
best bid / best ask) and **STATE** (governance, minted by burning DEEP). Zero
founder allocation; company (Deep State Inc.) monetizes via a 10bps interface fee.

## Who is Joe

**Joseph DeLong** (joseph.eth):
- Long-time Ethereum contributor: ConsenSys (Eth2 client), MolochDAO, Dapper Labs (Flow).
- **CTO of SushiSwap**, resigned Dec 2021 citing "chaos within and without" and
  DAO infighting — later gave a famous ETHDenver talk arguing DAOs need hierarchy.
- Founded **Astaria** (NFT lending protocol), then senior director at **Kraken**.
- Currently **CEO of Colossus** — a stablecoin credit-card network aiming to bypass
  Visa/Mastercard.
- Deepstate is, in his words, "a side project that outgrew nights and weekends."
- Announced Deepstate on X on July 24, 2026; whitepaper (dated June 29) on GitHub.

## The venue: Robinhood Chain

- Ethereum **L2 on Arbitrum Orbit**, mainnet **July 1, 2026** ("The World is Flat"
  keynote, London). ~100ms blocks, settles to Ethereum, ETH for gas, no chain token.
- **Permissionless contract deployment** — Deepstate needed no Robinhood sign-off.
- Day-one apps: Uniswap, Chainlink, Morpho (Robinhood Earn ~7% USDG lending,
  Lloyd's-insured), Lighter (perps order book), 1inch, Arcus.
- Strong debut: top-5 by DEX volume (Bernstein), passed Base on daily actives mid-July;
  ~$13M tokenized-stock volume in week one.
- Single Robinhood-run sequencer (normal for a young L2).

### Robinhood Stock Tokens (what "NVDA" actually is)

- **Tokenized DEBT securities** issued by **Robinhood Assets (Jersey) Limited** —
  price exposure only. No share ownership, no voting; if the issuer fails you're a
  *creditor of a Jersey entity*, not an NVDA shareholder.
- Standard **ERC-20, 18 decimals**; dividends/splits handled by an onchain
  multiplier (`uiMultiplier()`, ERC-8056) fed by Chainlink.
- Minting/redemption only via authorized participants (currently BBVI); redemption
  is for cash, not shares.
- **Not offered to US persons**; restricted in UK/Canada/Switzerland too. Enforcement
  is largely interface/issuance-level — the ERC-20 itself circulates, which is the
  spicy regulatory question everyone's circling (can DEXs/AI agents route around
  the geofence?).
- 190+ stocks/ETFs tokenized, available in 120+ countries.

## What Deepstate is

An experimental, **fully onchain CLOB**: order placement, matching, custody, and
settlement all in contracts. Ambition: be the *primary* market for an asset, not
just a settlement venue.

### The tech (whitepaper)

- Each resting order packs into a **single 32-byte word**: price tick, quantity,
  rounding-correction code, time-priority nonce.
- Orders live in a **binary radix tree** keyed by price + arrival order.
- **4.3 billion logarithmically spaced price ticks**; tree depth is a fixed 64 bits,
  so per-trade work (gas) is **bounded regardless of book size**. This is the trick
  that makes an EVM CLOB practical.
- DeLong credits **"Warp"** — a matching-engine design by Joseph Poon (Lightning/
  Plasma co-author) & Christopher Jeffrey, presented at EthCC 2023 — as the
  foundation. Warp was also announced/presented at **Stanford Blockchain
  Conference 2023** (there was a dedicated "WARP Assembly" event at Stanford
  Blockchain Week '23) — Austin saw Poon present it there. So Deepstate is not
  Warp itself, but DeLong's own implementation built on Warp's onchain
  matching-engine idea; Warp the project was pitched more broadly as a
  cross-chain DeFi paradigm. Good podcast thread: "what did you keep and what
  did you throw away from Poon's design?"
- Matching contract is **permissionless, non-custodial, non-upgradeable**; other
  frontends can use it directly.

### Why CLOB > AMM (his thesis)

AMMs quote from pooled inventory — passive, always-stale-ish, LPs eat adverse
selection (bad for assets with a strong external reference price like NVDA).
A CLOB makes market makers compete on **price, size, and time**: precise quoting,
visible depth/spread, fast repricing around earnings/news, capital-efficient
inventory. Notably, Robinhood Chain's own perps venue (Lighter) is also an order
book — even Robinhood's ecosystem treats AMMs as a weak fit for equities.

### Tokens & the flywheel

- **DEEP** — reward token. Earned ONLY by the **best bid** and **best ask** in a
  pool (top-of-book). Resting deeper gives the book depth but earns nothing.
- **STATE** — governance vault share. Depositing DEEP into the vault **burns it
  permanently** and mints STATE (ERC-4626 + voting).
- **USDG** — Paxos Global Dollar, the vault's fixed-value asset and quote currency.

Loop: make markets → hold top-of-book → accrue DEEP → burn into STATE → vote +
pro-rata claim on vault fees. Passive STATE holders **dilute** as active makers
keep earning/depositing — governance drifts toward whoever actually runs the market.

- Launch rewards: **exactly 1,000,000,000 DEEP** prefunded into one NVDA/USDG
  rewarder. **395 days**, 50% bid side / 50% ask side, each side's clock starts at
  its first top order. Front-loaded logarithmic curve; unclaimed capacity is
  **lost forever** (rewarder has no minter role, no owner withdrawal).
- Reward accrual = position (must be top) × time (wall-clock seconds) × quantity
  (a size function scales the budget — small top orders earn proportionally less).
- **Zero founder/team token allocation.**

### Fees & the weird vault

- Official interface: **10bps protocol + 10bps company fee**. Direct or third-party
  integrations skip the company fee. Protocol fee is taken from the taker's output:
  `floor(out × 10 / 10,000)`.
- Protocol fees accumulate in the vault; STATE holders redeem pro-rata
  (`redeemValue` in USDG or `redeemAssets` for a caller-specified ERC-20 list).
- **`buyFees`: anyone can buy the vault's entire listed fee balance for a flat
  10,000 USDG** — no auction, no oracle. Deliberately dumb: it's an arbitrage
  invitation that converts messy multi-asset fees into USDG. (DEEP/STATE/USDG
  excluded from the sweep.) Governance *cannot* change the 10k price.

### Governance

- 5 contracts, all **non-upgradeable, non-proxied**: DeepstateV1 (book/matching),
  DEEP token, Vault, Governor (OZ-based), NVDA/USDG Rewarder.
- Governor owns everything; deployer renounced admin. Canonical deployment:
  1 STATE seeded to a dead address, **15-day launch delay, 3-day voting delay,
  7-day voting period**, **no timelock** (executes right after a vote passes).
- Governance CAN: set protocol fee (≤100bps), manage reward hooks, **grant a
  future MINTER_ROLE on DEEP** (uncapped supply!), tune governor params.
- Governance CANNOT: upgrade logic, block permissionless pool creation, control
  deepstate.sh listings, change reward schedules or the 10k buyFees price.

### Protocol vs company

| Layer | Who controls |
|---|---|
| Contracts (book, matching, vault, rewards) | STATE governance |
| deepstate.sh interface (listings, routing, hosting) | **Deep State Incorporated** |
| Third-party frontends | their operators |
| Prices/inventory | individual makers |

## Risks (their own docs are refreshingly blunt: "assume loss is possible")

- **NVDA leg is trust-me**: entirely dependent on Robinhood's Jersey issuer —
  solvency, custody, legal enforceability, corporate actions are all offchain risk
  the order book can't fix.
- **"Superior price" is book-local**: no oracle; top-of-book can be stale or
  manipulated and still earn rewards. Thin books let a marginal price "win."
- **Top-of-book-only rewards** may buy a shiny spread but no real depth;
  incentivizes tick-stacking; mercenary liquidity may leave as emissions decay.
- **DEEP has no supply cap**: a future governance-granted minter could mint→
  deposit→capture governance→drain the vault. Accepted as a known critical
  (mitigation = voting delays + bootstrap period). No timelock = no escape window.
- **Vault redemption is in-kind pro-rata**, no price normalization — you get token
  quantities, not target dollar value; omitted assets just stay behind.
- **buyFees underprices inventory by design**; non-standard (fee-on-transfer/
  rebasing) tokens break accounting assumptions and can brick flows.
- 12 accepted audit findings are published, mostly "intentional tradeoff" flavored.
- Regulatory: the whole stock-token category is non-US, and a permissionless DEX
  on top makes the geofence even leakier.

## Podcast question ideas

1. SushiSwap → Astaria → Kraken → Colossus → Deepstate: what did the Sushi DAO
   meltdown teach you that's baked into Deepstate's governance design?
2. Why is this a *side project* while you're CEO of Colossus? Who runs it long-term
   if governance is designed to dilute toward market makers?
3. Warp/radix tree: what actually broke in prior EVM CLOB attempts, and what's the
   real gas cost of place/cancel/match on Robinhood Chain today?
4. Only best-bid/best-ask earn — isn't that a recipe for 1-tick spread with zero
   depth behind it? Why not reward the top N levels?
5. The `buyFees` 10k-USDG flat sweep is deliberately underpriced — walk me through
   why an auction was the wrong call.
6. No timelock + governance can grant unlimited DEEP minting — why accept that?
7. NVDA token is Jersey-issued debt, banned for US persons, but it's a plain ERC-20
   on a permissionless chain. Who's responsible for the fence — you, Robinhood, nobody?
8. Zero founder allocation — how does Deep State Inc. make money, and what happens
   if a third-party frontend just skips your 10bps?
9. What happens to the book during earnings, halts, splits (the multiplier), or
   when the underlying market is closed and the token trades 24/7?
10. Is the endgame that the *token* becomes the primary market and price discovery
    happens onchain before Nasdaq opens?

## Sources

- Docs: https://docs-production-cdea.up.railway.app/ (overview, superior-price,
  contracts, risks — llms.mdx endpoints)
- App: https://deepstate.sh/ (live: NVDA/USDG swap + limit orders, © Deepstate Inc.)
- [The Defiant — Ex-Sushi CTO Joseph DeLong to Launch Order Book DEX on Robinhood Chain](https://thedefiant.io/news/defi/ex-sushi-cto-joseph-delong-to-launch-order-book-dex-on-robinhood-chain)
- [defiprime — Robinhood Chain: Open Rails, a Fenced-Off Flagship Asset](https://defiprime.com/robinhood-chain)
- [Robinhood Chain docs — Stock Tokens](https://docs.robinhood.com/chain/stock-tokens/)
- [Robinhood newsroom — Chain mainnet launch](https://robinhood.com/us/en/newsroom/robinhood-accelerates-global-expansion-robinhood-chain-mainnet-stock-tokens-agentic-trading/)
- [CoinDesk — Robinhood Chain strong debut (Bernstein)](https://www.coindesk.com/tech/2026/07/13/robinhood-chain-surges-into-top-five-by-dex-volume-bernstein)
- [Decrypt — SushiSwap CTO resigns](https://decrypt.co/87910/sushiswap-cto-resigns-citing-chaos-within-without-project)
- [The Defiant — DeLong's ETHDenver DAO-hierarchy talk](https://thedefiant.io/news/defi/joseph-delong-sushiswap-postmortem)
