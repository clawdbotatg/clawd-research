# "Alt mempool" — what the EF account-abstraction team is doing and why

Researched 2026-09-23.

## Short version

"Alt mempool" is not one thing. It is the EF AA team's (Yoav Weiss, Alex Forshtat, Dror Tirosh, Shahaf Nacson) answer to one problem, applied three times over five years:

> If a transaction's validity is decided by arbitrary EVM code instead of a fixed ECDSA check, how does a node that relays it know it will get paid?

Nodes must simulate the validation code before relaying. If that code reads state anyone can change, one cheap state write can invalidate thousands of pending transactions at once and the relaying nodes ate the cost for nothing. They call this the **mass invalidation attack**. Every "mempool rules" document they have written exists to bound it.

The thing that is new this week: on **2026-09-22** Forshtat opened [ethereum/ERCs PR #2028](https://github.com/ethereum/ERCs/pull/2028), a draft ERC titled **"Frame Transaction Alternative Mempools"**. It is the alt-mempool layer for EIP-8141 (Frame Transactions), which core devs scheduled for the Hegotá fork on 2026-08-27.

## The three generations

| Year | Spec | What "alt mempool" means there |
|---|---|---|
| 2021 | [ERC-4337](https://eips.ethereum.org/EIPS/eip-4337) "Account Abstraction Using Alt Mempool" | A whole second mempool, off-protocol. UserOperations go to bundlers, not to Ethereum's tx pool. "Alt" = alternative to the protocol mempool. |
| 2023 | [ERC-7562](https://eips.ethereum.org/EIPS/eip-7562) validation scope rules | The 4337 mempool gets a **canonical** ruleset plus opt-in **alt-mempools**, each a YAML doc identified by its IPFS hash, with its own reputation. "Alt" = alternative ruleset within the 4337 world. |
| 2026 | [EIP-8141](https://eips.ethereum.org/EIPS/eip-8141) + [PR #2028](https://github.com/ethereum/ERCs/pull/2028) | AA becomes a real tx type (0x06). The protocol's own public mempool gets a strict ruleset with **no staking and no reputation**. PR #2028 adds a **standard alternative mempool** that brings stake and reputation back for the use cases the strict rules kill. |

## Why they went off-protocol in the first place (2021)

Vitalik's original note ([alt_abstraction](https://notes.ethereum.org/@vbuterin/alt_abstraction)) says it plainly: EIP-86 and EIP-2938 tried to let contracts pay gas at the protocol level and died because the tx-pool rules needed to keep that safe were too complex to get consensus on. So they built the mempool outside the protocol, "inspired by alternate mempools such as Flashbots." Bundlers eat the simulation cost and package UserOps into normal transactions. No consensus change needed.

That worked, but it created its own problems:

- Each bundler ran a private queue, so users depended on one company's RPC for censorship resistance. Yoav's [unified mempool note](https://notes.ethereum.org/@yoav/unified-erc-4337-mempool) is about why a shared P2P mempool matters.
- The shared 4337 mempool only went live on mainnet, Arbitrum and Optimism in **November 2024**, and in 2026 it is still described as between "permissioned sharing" and "controlled decentralization." Most production traffic still bypasses it via private relays.
- The safety rules (ERC-7562) got long: opcode bans, associated-storage rules, staking, reputation with throttle/ban states. The team's own draft admits "the benefit of arbitrary validation largely disappears once you layer on all the restrictions."

## Why bring it into the protocol now (EIP-8141)

Frame Transactions were posted 2026-01-29 by lightclient with Vitalik, Felix Lange, the AA team, Derek Chiang, Toni Wahrstätter and Stavros Vlachakis. The headline motivation is **post-quantum**: get ECDSA out of the account layer without picking a PQ algorithm today. Let code originate transactions and any signature scheme becomes possible.

A frame tx is a list of 1 to 64 frames. VERIFY frames run static and must call a new `APPROVE` opcode to authorize execution and/or name a payer. Gas is escrowed from the payer. No EntryPoint contract, no bundler, no UserOperation struct.

Because the tx is now a native type, its mempool is the protocol's public mempool, run by every execution client. That is the part that makes clients nervous, and it is why 8141 carries a **public mempool rules** section that is ERC-7562 with the risky parts cut out:

- Only four validation-prefix shapes allowed.
- Validation gas capped at 100k execution gas.
- Reads only from `tx.sender`'s own storage. No reading anyone else's state.
- Long list of banned opcodes (TIMESTAMP, NUMBER, BASEFEE, BALANCE, etc.).
- A **canonical paymaster**: one blessed bytecode admitted by exact code match, with per-node balance reservation.
- Any other paymaster is capped at **one pending tx** network-wide.
- **No staking, no reputation.** Anything 7562 would allow only for a staked party is simply rejected.

Transactions outside those rules "may be accepted into a local or private mempool, but must not be propagated through the public mempool."

Status: SFI'd for Hegotá at ACDE #244 on 2026-08-27, with the chair's caveat that "the EIP number may change; the implementation may significantly change." Base and Offchain Labs prefer the competing EIP-8130 (Coinbase's verifier-contract design, no simulation at all) but said they will work with 8141. Hegotá follows Glamsterdam, which is now targeting mainnet in early December 2026, so Hegotá is a 2027 fork. Erigon opened its 8141 tracking issue on 2026-09-18.

## What PR #2028 actually adds (the new "alt mempool")

The strict public mempool cannot host anything whose validity depends on shared state. The draft names the casualties: token paymasters that pull USDC from the user during validation, privacy-pool withdrawals that read a shielded pool's Merkle root, paymasters with a per-user budget in their own storage, signer registries. Under 8141 alone those all fall back to private submission, which is exactly the centralization 4337's shared mempool spent three years trying to escape.

So the draft defines three named rulesets:

1. **Canonical public mempool** — EIP-8141's, unchanged.
2. **Standard alternative mempool** — this document. A permissionless P2P mempool that extends the public rules with stake and reputation.
3. **Non-standard alternative mempools** — anyone's ruleset, identified by the IPFS hash of its description doc, exactly like ERC-7562 alt-mempools.

A tx that breaks a public rule must never travel on the public mempool. It can travel on any alt mempool whose rules it satisfies.

What the standard alt mempool relaxes, and the price:

| Relaxation | Who gets it | Price |
|---|---|---|
| Read storage associated with the sender in other contracts (ERC-20 balance slots etc.) | any existing sender | none |
| Read any storage, read/write your own associated storage, use BALANCE | **staked entities** only | ≥ ~$1000 native token locked in a new **Staking Registry** contract, 1-day unstake delay, never slashed |
| 1M validation gas instead of 100k | staked entities | same stake |
| More than one pending tx per sponsor | unstaked payers with a good inclusion record | reputation: `10 + inclusionRate × included` pending txs |
| Non-static writes before the pay frame (pull tokens first) | anyone, via a new `pre_verify` frame bound to the approving frame that follows it | attributed to the entity, so its reputation eats any failure |

Reputation is the 7562 machinery ported over: per-entity `seen` / `included` counters decaying 23/24 per hour, OK / THROTTLED / BANNED states, 72-hour ban when a tx passes revalidation but fails at inclusion. Peers that send never-valid txs get marked spammers and disconnected permanently.

The stake lives in a separate registry because frame txs have no EntryPoint to hold it. It is explicitly "for off-chain detection only": the lockup raises the cost of spinning up fresh abusive identities.

Backwards compat is the stated design goal. A contract written against ERC-7562 needs no change to its validation logic. `validateUserOp` becomes a `self_verify` or `only_verify` frame, `validatePaymasterUserOp` becomes a `pay` frame, `initCode` becomes a `deploy` frame.

## Why split it this way

The team's own rationale, paraphrased:

- The public mempool is deliberately narrow because it has no way to attribute blame. Every execution client must run it, so it must be simple and boring. Wallet authors who target it never need to know the alt-mempool doc exists.
- The alt mempool is where blame attribution (stake + reputation) lives, so it can afford to be permissive. Node operators opt in. If it turns out to be attackable, the public mempool is untouched.
- This is the same layering 7562 used, so the 4337 ecosystem's paymasters and privacy pools carry over. Keeping those users is the point; otherwise 8141 ships and the interesting AA apps stay on private relays.

The draft's own last security note is worth quoting: "Neither ERC-7562's rules nor the frame transaction rules here have seen adversarial production traffic at meaningful scale. Most historical ERC-4337 traffic bypassed the public peer network through private relays."

## Open questions to watch

- **Who runs the standard alt mempool?** Execution clients only have to run the public one. Someone has to implement and operate the staked/reputation mempool as a sidecar or a client option. That is the same "who runs bundlers" question 4337 had.
- **Staking Registry is not protocol.** A bug there weakens the storage and balance rules for every node trusting it.
- **8141 vs 8130.** If ACD reshapes 8141 toward 8130's verifier-contract model, the validation prefix changes and this draft changes with it. The PR still has a placeholder `discussions-to` link and an empty author field, so it is very early.
- **Timeline.** Hegotá is 2027 at best. The 4337 shared mempool remains the only thing live today.

## Sources

- [ERCs PR #2028: Frame Transaction Alternative Mempools](https://github.com/ethereum/ERCs/pull/2028) (draft, 2026-09-22; full text saved as `erc-draft-frame-tx-mempool-rules.md` here)
- [EIP-8141: Frame Transaction](https://eips.ethereum.org/EIPS/eip-8141) and its [Magicians thread](https://ethereum-magicians.org/t/eip-8141-frame-transaction/27617)
- [ERC-7562: Account Abstraction Validation Scope Rules](https://eips.ethereum.org/EIPS/eip-7562)
- [ERC-4337: Account Abstraction Using Alt Mempool](https://eips.ethereum.org/EIPS/eip-4337)
- [EIP-7701](https://eips.ethereum.org/EIPS/eip-7701) (withdrawn, superseded by 8141)
- [Vitalik, "Proposal for account abstraction via alternative mempool" (2021)](https://notes.ethereum.org/@vbuterin/alt_abstraction)
- [Yoav Weiss, "Unified ERC-4337 mempool"](https://notes.ethereum.org/@yoav/unified-erc-4337-mempool)
- [Christine Kim, ACDE #244 recap](https://christinedkim.substack.com/p/acde-244) (SFI decision + caveats)
- [ETH Daily: Frame Transactions Hegotá headliner](https://ethdaily.io/frame-transactions-hegota-headliner)
- [ERC-4337 docs: UserOp mempool overview](https://docs.erc4337.io/bundlers/userop-mempool-overview.html)
- [Etherspot: shared mempool launch (Nov 2024)](https://etherspot.io/blog/erc-4337-shared-mempool-official-launch-on-ethereum-mainnet-arbitrum-and-optimism/)
