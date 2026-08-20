# Building on Deepstate — composability brainstorm

*2026-08-20. What could be built on top of a fully-onchain CLOB with permissionless
pools, permissionless fills, integrator fees (≤100bps to any frontend), top-of-book
hooks (IHook), pull-based settlement, and 190+ tokenized stocks on an FCFS chain.*

## Boring-but-lucrative

1. **Oracle layer.** The book exposes depth-weighted price + spread + top-of-book
   age, all onchain — no Chainlink. Build the manipulation-resistant wrapper once
   (TWAP + depth floor) and every lending/options/liquidation protocol on the
   chain consumes your feed.
2. **Prediction markets** settled against the book price at a timestamp. No
   oracle committee.
3. **Aggregator/frontend war.** `fillWithIntegratorFee` makes anyone a broker
   with their own fee switch (≤100bps). Slickest NVDA terminal / Telegram bot
   clips the flow it brings. "The Robinhood of Robinhood Chain."

## Genuinely new primitives

4. **Top-of-book mining as a token launch mechanism.** Fork the *rewarder*, not
   the book: distribute a new token to whoever makes its market tightest.
   "Proof of market making" as a distribution primitive — replaces airdrops/LBPs.
5. **Maker-position NFTs.** A resting order = escrowed collateral + a DEEP reward
   stream. Tokenize it; sell it, lend against it, build a secondary market for
   top-of-book *time*. Passive capital funds active makers.
6. **Index funds that earn instead of pay.** An onchain basket over the 190
   stock tokens that rebalances with resting limit orders — collects maker
   rewards instead of paying taker fees. TradFi funds pay to rebalance; this one
   gets paid.
7. **Get-paid-to-DCA.** Recurring buys as resting bids slightly below market;
   the order earns DEEP while it waits. A savings app where patience is yield.

## Spicy

8. **The gap market.** The book trades NVDA at 3am Sunday; Nasdaq doesn't.
   Futures on the *Monday-open gap* — a market on what the closed exchange
   doesn't know yet. If onchain price discovery leads, this instrument proves it.
9. **Trust-in-Robinhood market.** NVDA-token vs real-NVDA spread = an onchain
   credit-default swap on the Jersey issuer. The book prices the asset; this
   market prices the trust. A live ticker for "do we believe the custodian."
10. **Hook-driven autonomous finance.** Pools fire IHook on top-of-book changes:
    stop-losses, structured products, reactive vaults — no keepers, no oracles;
    the market event IS the trigger.

## Closest to Austin's world

11. **Agent trading league.** FCFS chain + fully-readable book + (this week)
    tiny capital requirements = the arena for agent-vs-agent market-making
    competition. Real money, objective scoreboard (DEEP earned), true
    adversarial play. The agent-esports thesis (see memory:
    agent-esports-platform / agent-arena-landscape research) with an actual
    economy attached — model-vs-model fleets on a live order book.

## Raw materials reference

- Permissionless pools: any ERC-20 pair, `poolId = keccak(token0, token1)`.
- Hooks: `IHook.execute(poolId, bookId, token, outgoingAmount, incomingNonce)`
  fires on top-order changes (per-side flags).
- Integrator fees: `fillWithIntegratorFee` / `fillRouteWithIntegratorFee`,
  cap `_MAX_FEE_BPS = 100`.
- Views for oracles: `topOrder(bookId, isBid)` (remember the isBid inversion —
  see MAKER-BOT-SPEC.md §3b), `activeBookId(token0, token1)`.
- Settlement: pull-based; `cancel()` claims proceeds (enables atomic patterns).
