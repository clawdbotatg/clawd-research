# EIP-8037 and the Glamsterdam Hoodi delay (2026-10-26)

## What actually happened

- **2026-10-13:** ChainSecurity publishes "Glamsterdam Hard Fork: When Spent Gas Comes Back".
- **2026-10-22, ACDE #248:** devs pull the Hoodi testnet fork set for 10-26, and with it the 200M gas limit test. Sepolia isn't affected.
- No new Hoodi or mainnet date yet. December mainnet is still talked about, but it's unconfirmed. A new Hoodi date is expected after Devcon (Nov 3–6).
- ChainSecurity found **13 live mainnet contracts** that are affected and is in responsible disclosure with them. The EF is still counting how many more there are.

**Two corrections to what was said on the call:**
1. It is **not "indefinitely postponed."** The Hoodi date was pulled and no new one is set.
2. "Top 10/20 DeFi" isn't public. Only "13 real-world examples" is public, with no names. No exploit against a live app has been shown.

## What EIP-8037 does

- It adds `CPSB` = 1530 gas per new state byte.
  - A new storage slot costs 64 × 1530 = **97,920** state-gas, versus 20,000 today.
  - A new account costs 120 × 1530 = **183,600**.
- State-gas is metered on its own track so big deploys aren't capped by the 16.7M per-tx limit (EIP-7825).
- **The reservoir:** any `tx.gas` above `TX_MAX_GAS_LIMIT` goes into a `state_gas_reservoir`. State charges draw from the reservoir first, then from `gas_left`.

Three spec lines cause all of the trouble (eip-8037.md:113-116):
- The reservoir is passed to a child call **in full**, because the 63/64 rule only applies to `gas_left`.
- `GAS` / `gasleft()` returns `gas_left` only. The reservoir is invisible to the contract.
- Undoing state creation (clearing a slot, a reverting frame) **refills `gas_left` immediately** (LIFO order), instead of becoming a refund at the end of the tx.

The EIP's own security section already admits `gasleft()` can go **up** between two reads (line 505). That makes a gas-before minus gas-after measurement go negative: it reverts under checked math and wraps under unchecked.

## Why it breaks live contracts

The contracts at risk catch a failed call and keep going: they mark the call failed, skip it in a batch, or pick a fallback. To stop **insufficient-gas griefing**, where an attacker underfunds a call on purpose so it fails permanently, they rely on one of these checks:

- **A.** A pre-call check that enough gas is available to forward.
- **B.** A post-call check like `if (!ok && gasleft() < budget/63) revert`.
- **C.** No check at all: they count on the failure-recording `SSTORE` being too expensive to finish, so the whole tx reverts.

ChainSecurity found four problems:

1. **The reservoir pays for state, so leftover gas goes further (breaks C).** A cold fresh `SSTORE` costs 22,100 today. Under the new rules it costs 12,100 of execution gas, and the reservoir pays the 97,920. About 15k of leftover gas now finishes the failure handler, where today it runs out.
2. **Clearing a slot refills `gas_left` mid-tx (breaks B and C).** A slot going 0 → 1 → 0 hands back up to 97,920 execution gas right away, which can push past a B threshold.
3. **A reverting intermediary hands back spent state-gas (breaks B and C).** In a C → D → E chain, if D reverts after creating state, its state charges return to C as usable gas.
4. **Old fixed gas budgets may now be too small (breaks A, B1, C).** EIP-8038 raises warm/cold `SSTORE` to 10,100/12,100 and value `CALL` to 11,300. A hardcoded gas stipend that was fine for years may now run out.

The net effect: a call that used to fail by reverting the whole tx now completes and records a permanent failure, and the user can't retry.

## Fix in progress

**LukaszRozmej/EIPs PR #3** (open, 10-23):
- Refills go to the reservoir only, so `gasleft()` can never go up. That fixes problems 1–3.
- Adds a "legacy share": each state charge takes the old price from `gas_left` first. A cold new slot costs 22,100 from `gas_left` again, the same as today.
- **Problem 4 is only partly fixed.** Repricing is the point of the fork, so hardcoded budgets still need an audit.
- Follow-up PR #9 adds a per-frame reservoir cap, because a callee can drain the shared reservoir cheaply through code deposit.
- Status: most reviews are AI agents. Ben Adams is the main human reviewer and wants test vectors and ERC-4337 guidance.

**ethereum/EIPs #12256** fixes a separate accounting bug: a sibling call fills a slot, another clears it, and the caller's `GAS` reads low.

EIP-8037 is still in Last Call with a 2026-11-01 deadline. A reviewer pointed out that a change this big should restart Review under EIP-1.

## Who should care

- Anything that uses `gasleft()` around a try/catch: relayers, keepers, batchers, bridges/retryables, 4337 EntryPoint-style accounting. This is our inference; ChainSecurity names no categories.
- **4337 is already hit:** Pimlico's Alto bundler added `--glamsterdam-enabled`, which caps simulation at 2^24 gas because the EntryPoint can't see reservoir-paid state gas. The result is low estimates and AA26 on-chain.
- Tools: [glamcheck](https://github.com/PyraVim/glamcheck) flags `gasleft()` logic, and [gasworks.tools](https://www.gasworks.tools/methodology) is an impact analyzer.

## Tweets so far

- **@chain_security** (10-22) is the main one: "It has just been decided to delay the Glamsterdam hard fork on the Hoodi testnet because of security impacts we identified…13 real-world examples…" https://x.com/chain_security/status/2113303061078671814
- **@nero_eth (Toni Wahrstätter)** posted the best plain-English thread (~10-26).
  - The main point: hardcoded gas forwarding was always going to be affected by repricing. What's new is that `gasleft()` can go *up*.
  - It ends with a call for app devs and auditors to check their contracts. The original tweet wasn't found; this comes from TechFlow/KuCoin quotes.
- **pcaversaccio** called the risks "serious" in a GitHub comment on 10-21 and asked for a re-look. That's a GitHub comment, not a tweet.
- Everything else is crypto-news rewrites (KuCoin, crypto.news, Blockonomi, TechTimes). Some of them wrongly say "Holesky."
- **Open lane:** no one has posted a short, dev-facing "how do I check my contract" thread with the three spec lines and a code example of each pattern.

## Sources
- https://eips.ethereum.org/EIPS/eip-8037
- https://www.chainsecurity.com/blog/glamsterdam-gas/
- https://github.com/LukaszRozmej/EIPs/pull/3
- https://github.com/ethereum/EIPs/pull/12256
- https://github.com/pimlicolabs/alto/pull/781
- https://crypto.news/ethereum-glamsterdam-hoodi-upgrade-postponed/
- https://www.techtimes.com/articles/329415/20261023/ethereum-glamsterdam-delay-chainsecurity-flags-13-contracts-where-failures-turn-permanent.htm
- https://www.techflowpost.com/en-US/newsletter/141369
