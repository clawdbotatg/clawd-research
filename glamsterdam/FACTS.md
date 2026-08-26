# Glamsterdam dev-tooling facts (checked 2026-08-26)

Two tweetable claims, verified against the meta EIP and live specs.

## 1. Larger contracts — EIP-7954 (SFI ✅)

- Deployed bytecode: **24 KiB (24,576 B) → 64 KiB (65,536 B)**
- Initcode: **48 KiB (49,152 B) → 128 KiB (131,072 B)**
- Both exactly **2.67x**. First raise of the EIP-170 limit since 2016.
- The EIP changes *only* the size limits — gas repricing rides separately
  (EIP-8007 gas repricings, EIP-8037/8038 state-gas changes, also SFI).
- Spec: https://eips.ethereum.org/EIPS/eip-7954

> Tweet: Ethereum's Glamsterdam fork (EIP-7954) raises the contract size
> limit for the first time since 2016: deployed bytecode 24 KiB → 64 KiB,
> initcode 48 KiB → 128 KiB. 2.67x more room — no more shipping your
> protocol in 6 shards.

## 2. Stack-too-deep fix — EIP-8024 (SFI ✅)

- Adds **DUPN, SWAPN, EXCHANGE** — single-byte immediate operand each.
- DUPN/SWAPN reach stack depths **17–235** (they extend, not replace,
  DUP1-16/SWAP1-16); EXCHANGE swaps two non-adjacent items within the
  top 30 (1 ≤ n < m, n + m ≤ 30).
- Backward-compatible with legacy EVM — this is the non-EOF successor to
  EIP-663 (which was EOF-only and died with it).
- solc adoption is **pending** — the error goes away only once the
  compiler targets the new opcodes. Vyper doesn't have the problem.
- Spec: https://eips.ethereum.org/EIPS/eip-8024

> Tweet: Glamsterdam (EIP-8024) adds SWAPN/DUPN/EXCHANGE opcodes so
> compilers can reach past the EVM's depth-16 stack limit — down to item
> 235. Once solc adopts them, "stack too deep" dies as a Solidity error.

## Inclusion + timeline

- Both are **Scheduled for Inclusion** in meta EIP-7773 (Glamsterdam),
  alongside ePBS (EIP-7732), BALs (EIP-7928), etc.
  https://eips.ethereum.org/EIPS/eip-7773
- Glamsterdam live on **Platåberget testnet since 2026-08-20**
  (https://blog.ethereum.org/2026/08/17/plataberget-testnet); Sepolia/Hoodi
  next; mainnet slipped to **~Q4 2026**, no date announced.
