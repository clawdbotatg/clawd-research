# 0x38276F9EB731e185e7f48D2Bf103Ef10E717ad4B (Base) — what it was, what happened

Researched 2026-09-09 via Alchemy Base RPC (archive reads, logs, block scans),
Basescan page, and local repo history. Blockscout was down; Etherscan API
refuses Base on the free tier.

## One-line answer

A **ZK LLM API test wallet** Austin funded on **2026-03-14** to exercise the
stake → register flow of the zk-llm-frontend on launch day. Its **private key was
compromised within ~70 minutes**: a drainer swept its ETH, installed an
**EIP-7702 sweeper delegation**, and then auto-stole the two 0.005 ETH gas
top-ups Austin and the rightclaw deployer sent it. It is still delegated to the
sweeper today. **Never send anything to this address.**

## Identity

| Fact | Value |
|---|---|
| Type | EOA, **EIP-7702 delegated** — code `0xef0100…` → `0x87C6BD021Ce7a1214Fcf49d942a9088085031a4F` |
| Funded by | `austingriffith.eth` (`0x34aA3F35…c18fDF3`) — 0.001 ETH at 15:23:55Z, then 10,000 CLAWD at 15:24Z |
| Nonce | 16 (15 sent txs + 1 consumed by the 7702 authorization) |
| Balance now | 0 ETH · **5,000 CLAWD stuck** · airdrop spam (AOL, CUKI, ION, NEOS, OPENCLAW, SEC, RUNAS) |
| Labels | None on Basescan. Not in any local repo, transcript, or harness prompt log (only in a CLAWD `holders.json` snapshot). |
| Origin of key | Unknown. Frontend `burnerWalletMode` was `localNetworksOnly` that day, so not a browser burner. Likely an agent-generated test key. |

Counterparties:

| Address | Who |
|---|---|
| `0x34aA3F35…c18fDF3` | austingriffith.eth / atg.eth (funder; also staked itself, leaf 0) |
| `0x4f8AC2fA…e88dFd46` | `deployer.rightclaw.eth` — zkllmapi deployer, deployed both APICredits contracts |
| `0x234d536e…8CD29476` | **APICredits** (Poseidon2 IMT) — `stake(uint256)` / `register(uint256)`; frontend pointed here 14:53Z |
| `0x45284835…84f900F3` | **APICredits** redeploy (block 43358950 ≈16:55Z); frontend switched 16:55Z |
| `0x9f86dB9f…c7a6b07` | $CLAWD token |
| `0x2dCDEA8a…E9BdEC8` | **Drainer EOA** — owner of the sweeper; 693 victim senders, 925 inbound transfers, ~6.53 ETH, active 2026-02-08 → 2026-09-03 on Base |
| `0x87C6BD02…085031a4F` | **Sweeper contract** deployed 2026-02-08 09:38Z by the drainer |
| `0xc333F43f…A6A3c192f` | Drainer's collector for manual sweeps — 10 victims Feb 25–Apr 1 2026, this wallet among them |
| `0x34aaf6bc…c18fdf3`, `0x4f8a2205…88dfd46`, `0x4f8a9291…88dfd46` | **Address-poisoning lookalikes** of atg.eth and the rightclaw deployer (fake "ETH" tokens + 0.000005 ETH dust) |

## Timeline (2026-03-14, UTC; MT = −6h)

| Time | Nonce | Event |
|---|---|---|
| 14:53 | | Frontend commit points at APICredits `0x234d…` (Poseidon2) |
| 15:23:55 | | austingriffith.eth → 0.001 ETH (first funding) |
| 15:24 | | austingriffith.eth → 10,000 CLAWD |
| 15:24 | 0–2 | approve → `stake(1000 CLAWD)` → `register(commitment)` on `0x234d…` (leaf 1) |
| 15:24 | | poisoning: fake "ꓰꓔН." token from `0x34aaf6bc…` (mimics atg.eth) |
| 15:32 | 3–5 | approve → stake 1000 → register (leaf 2) |
| 15:53 | 6–8 | approve → stake 1000 → register (leaf 3) |
| 15:56 | 9–11 | approve → stake 1000 → register (leaf 4) |
| 15:26–16:28 | | airdrop spam: NEOS, ION, SEC, OPENCLAW (9 each) |
| **16:34** | **12** | **Drain #1**: 0.000978791769319714 ETH (whole balance minus gas dust) → collector `0xc333…` |
| **16:35:41** | **13** | **7702 set-code**: type-4 tx `0xfe56dde2…` from drainer `0x2dCD…` (self→self) carrying this wallet's authorization → delegate `0x87C6…` |
| ~16:55 | | rightclaw deployer deploys new APICredits `0x4528…`; frontend commit updates address |
| 17:02 | 14–15 | approve → `stake(1000)` on `0x4528…` (no register; legit tester still working, unaware) |
| 17:02 | | deployer.rightclaw.eth → 0.005 ETH gas top-up → **swept same tx** to `0x2dCD…` |
| 17:02 | | lookalike `0x4f8a2205…` → 0.000005 ETH → swept; fake "ETH" token from `0x4f8a9291…` |
| 17:09 | | austingriffith.eth → 0.005 ETH → **swept same tx** to `0x2dCD…`; fake "ETH" token from `0x34aaf6bc…` again |
| 04-19/20 | | airdrop spam: RUNAS, AOL, CUKI |

Nothing after 2026-04-20. Every nonce accounted for.

## The sweeper contract (delegate `0x87C6…`)

Decompiled from bytecode (2,727 bytes, solc 0.8.19):

- `receive()`/`fallback()`: if `balance > 0`, forward **all ETH** to hardcoded
  owner `0x2dCDEA8a…` — that is what turned the two gas top-ups into instant theft.
- `destroyMe()` (`0x0c7caded`): `selfdestruct(owner)`, `tx.origin == owner` only.
- `gee()` (`0x5d2bafed`): returns `"wee"` — toy marker.
- `0x9d7a6ef4(calls[], bool)`: owner-only multicall executing in the **victim's
  context**. Reverts "Multicall aggregate: call failed" / "Caller is not owner".
  This means the drainer can still move the 5,000 CLAWD (or anything else that
  lands here) without spending the wallet's own ETH.

Standard EIP-7702 "sweeper" pattern seen since Pectra: leaked key → one type-4
tx → every future deposit is forwarded on arrival. No public label for either
drainer address (web search: nothing indexed).

## Damage

| Lost | Amount |
|---|---|
| ETH drained manually | 0.000978 ETH |
| ETH swept via 7702 | 0.010005 ETH (0.005 + 0.005 + 0.000005) |
| Total | ~0.011 ETH (≈$27 at Basescan's price) |
| CLAWD | 5,000 still in the wallet, attacker-controllable; 4,000 staked in `0x234d…`, 1,000 in `0x4528…` (contract-held, not lost) |

## Takeaways

1. **Do not top up this wallet.** Anything sent is forwarded to the drainer in
   the same transaction. The stuck 5,000 CLAWD would need the drainer's key or
   the wallet's key plus gas the sweeper won't let you keep — write it off.
2. **Key leak → drain in ~70 min** is consistent with a bot that harvests keys
   from public sources and watches them. The sweep came after the tester's last
   register call, so the key was probably exposed at or after ~15:56Z, not at
   generation. No local copy of the key or address exists, so the leak vector
   was not a committed file in these repos. Fits the global rule in
   `~/.clawd-accounts/ef/CLAUDE.md` about leaked keys.
3. **Related hygiene find**: `zk-llm-frontend-v2/packages/nextjs/scaffold.config.ts`
   has an Alchemy API key hardcoded in git (the same key that still works for
   Base reads). The repo is **public** (clawdbotatg/zk-llm-frontend-v2), so rotate that key.
4. On the good side: the ZK credit flow itself worked exactly as designed —
   four stake+register cycles landed leaves 1–4 in the Poseidon2 tree, and the
   redeploy to `0x4528…` took a stake the same hour.

## Method notes

- Alchemy `alchemy_getAssetTransfers` (both directions), `eth_getLogs` with the
  address in topic1/topic2, `eth_getTransactionByHash` for each hash.
- Binary search on `eth_getCode(addr, block)` to find the block the 7702 code
  appeared (43358397), then scanned that block's txs for `authorizationList`.
- Same binary search on the sweeper to find its creation block (41877083).
- Selectors via openchain.xyz: `a694fc3a=stake(uint256)`,
  `f207564e=register(uint256)`, `0c7caded=destroyMe()`, `5d2bafed=gee()`.
- Event topics: `1449c6dd`=Staked, `83086dd2`=NewLeaf, `7de7691b`=CreditRegistered.
