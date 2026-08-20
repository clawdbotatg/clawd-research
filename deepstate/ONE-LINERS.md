# Deepstate one-liners

*Quotable lines for the podcast. Say them like you thought of them in the shower.*

## The core idea

- "An AMM is a formula that doesn't know anything — when Nvidia earnings drop,
  the pool's price is stale for a moment and sharks eat the LPs."
- "Stale AMM prices are fine-ish for random crypto pairs, fatal for an asset
  with a real price everyone can see on Nasdaq."
- "If tokenized stocks are the future, they need order books — and nobody had
  built a real one onchain."
- "It's the actual Nasdaq mechanism, living inside a smart contract."

## The tree

- "The radix tree files orders by the bits of the price — so lookup cost is
  fixed by the number of bits, not the number of orders."
- "A naive order book gets slower as it gets deeper. This one costs the same at
  10 orders or 10 million."
- "Every order is one 32-byte slot. Every step of the walk touches exactly one
  slot. That's the whole gas budget."
- "The cost isn't 'how many orders exist' — it's 'how many bits in a price.'
  One is unbounded, the other is 64."

## The rewards

- "Every DeFi protocol pays people to park money. Deepstate pays people to
  compete."
- "It subsidizes a knife-fight over the spread and bets the winner is the
  trader."
- "The design pays for aggression, not depth — that's the experiment." *(from
  a community thread — credit 'someone on X' if quoting)*
- "The counter-theory: you just get two bots leapfrogging each other by a penny
  all day with nothing behind them."
- "Beat the best price by one tick and the reward stream switches to you.
  Instantly. King of the hill, forever, at 63 DEEP a second."
- "Passive holders dilute by design — governance drifts to whoever actually
  runs the market."

## The venue / the asset

- "The venue is decentralized; the merchandise isn't."
- "It's a trustless casino trading a trust-me chip."
- "The NVDA token isn't Nvidia stock — it's an IOU from a Robinhood subsidiary
  on a Channel Island."
- "Robinhood made its name on opaque payment for order flow. Deepstate puts
  order-flow monetization onchain, transparent and permissionless — on
  Robinhood's own chain."
- "The chain is first-come-first-served — you can't pay extra gas to cut the
  line, so the queue actually stays a queue. That's why this chain."
- "Robinhood's flagship blockchain product is banned for Robinhood's own
  customers."
- "Both legs of the first market are house assets: Robinhood's stock IOU
  against Robinhood's partner dollar. The venue is neutral; the money isn't."

## The endgame

- "If the book gets deep enough, Nvidia's price gets discovered onchain at 3am
  on a Sunday — and Nasdaq opens Monday already wrong."
- "The token stops being a shadow of the stock and becomes the leading market."
- "Their docs say it out loud: 'the primary market, not merely a settlement
  venue.'"

## The honesty

- "Their own risk docs say, verbatim: assume loss is possible."
- "No timelock, no upgrades, no founder tokens — the code can't be fixed, but
  it also can't be rugged."
- "Governance can vote unlimited token minting into existence and their audit
  calls that an accepted risk. They shipped it anyway, on purpose."
- "He celebrated $50k in volume — 'I know it is low but it is big to me' — and
  crossed $10M a day within the week."

## The Joe arc

- "He watched a DAO eat itself at Sushi, gave a talk saying DAOs need
  hierarchy — then built a protocol where power flows to whoever does the
  work."
- "A side project that outgrew nights and weekends — while running a company
  trying to kill Visa."

## Bonus hypotheticals to spring on him

- "If a US person's bot buys and sells your NVDA token inside a single
  transaction — 200 milliseconds of ownership — did anything illegal happen,
  and whose problem is it?"
- "Whose job is the fence? Yours, Robinhood's, or nobody's?"
