# VolatilePairHook (Uniswap v4 ETH/USDC, mainnet)

Context: Alex Nezlobin tweet 2026-10-26, "this pool is third in daily eth-usdc volume ... searchers still haven't fully realized how it works."

## Addresses

- Pool id: `0x98316e8405502774a5d0a0761276b5d26505a8195c1905169864008d5e7a3eea` (ETH/USDC, dynamic fee, tick spacing 4, created block 26186893)
- Hook (UUPS proxy): `0x000022ec4ebd6b12294396e852e4c3876b253cc0`
- Implementation: `0x1ddbf7215be4f8a7623b9b1b0255c6e1e3f6c000` (source verified on Sourcify; security contact security@uniswap.org)

## How the fee works

Fees are in pips (1e6 = 100%). Buying ETH pays the "ask" fee, selling pays the "bid" fee.

1. **Sticky lean (the 2023 thread idea).** Ask + bid always add up to 800 pips (0.08%). Each new block, if price moved up by X since the last block open, the ask fee steps up by X (capped at 300 pips per block, max 800) and the bid fee drops by the same amount. Down moves do the reverse. It stays leaned until price moves back.
2. **One-block backrun charge (the "surprising part").** If the last block moved price ≥ 0.08%, the side that would push it back pays an extra 50% of that move for one block. If the move was ≥ 0.05%, it also adds back the bid/ask drop from step 1.
3. **Inside a block.** The fee grows with how far price has moved since the block opened:
   - trading back toward the open (a backrun) pays +50% of the move, uncapped
   - trading further in the same direction pays +4x the move, capped at +200 pips

Net effect: after a whale pushes the price, the bot that trades it back hands ~half its profit to LPs. Arbs chasing a CEX move pay the leaned-up side.

## Live values (block 26280500, read from local reth)

config: restingSpread 800, backrunCapture 500000 (50%), midFadeRate 4e6 (4x), maxMidFade 200, skewRate 1e6 (1x), maxSkewStep 300, maxSkew 800, backrunThreshold 800, restoreFraction 1e6, restoreThreshold 500

state: askPermFee 638, tempFee 0 → getFee: sell ETH 161 pips (0.016%), buy ETH 639 pips (0.064%)
