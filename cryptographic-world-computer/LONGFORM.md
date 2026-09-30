# The cryptographic world computer: Ethereum in 2030

Long-form research on Vitalik's post of 2026-09-27, placed against where the
protocol actually stands on 2026-09-30.

- Post: https://vitalik.eth.limo/general/2026/09/27/the_cryptographic_world_computer.html
- Short notes: `README.md` in this folder
- Status of every EIP below was checked 2026-09-30. Sources at the bottom.

---

## 1. The claim

Vitalik's argument fits in one sentence: **after the Lean upgrades, Ethereum is
called a "blockchain" mostly for historical reasons.**

It still has a chain of blocks and still uses Satoshi's core ideas. But the parts
that made Bitcoin work in 2009 each get swapped out:

| Core property | 2009 | 2030 |
|---|---|---|
| Verification | download everything, re-run everything | sample data (PeerDAS), check a SNARK |
| Consensus | proof of work | PoS → heavily optimized PoS with fast finality |
| Who builds a block | one miner | several parties (builders, FOCIL committee, mempool aggregators) |

His key line: better databases, networking, formal verification and economics
all fit inside the old loop of "one guy finds the block, everyone downloads and
re-runs it." **The cryptographic changes do not.** That loop breaks. So the result
is a hybrid: Satoshi's ideas plus about 50 years of academic cryptography that
did not exist, or was not mature, in 2009.

He also sets a date: **Hegota (2027) is probably the last "normal" fork**, the
last one someone from 2015 would recognize. Everything after it is recursive
STARKs, automated formal verification, faster consensus and quantum safety.
PeerDAS (Fusaka, Dec 2025) was the first step. After Hegota this becomes "the
main story."

The post is short (about 2,000 words plus six annotated images). It is a framing
piece. It does not add new proposals. Its value is tying about a dozen separate
roadmap items into one idea.

---

## 2. Why "not just a blockchain" is a real claim

It's easy to read this as branding. It isn't only branding. The test is: **what
does a node have to do to be sure the chain is correct?**

- **2009 Bitcoin / 2015 Ethereum:** get every block, re-run every tx, keep the
  state. Trust nobody. Cost grows with usage. This is why block size fights happened.
- **2030 Ethereum (planned):** download a few random slices of each block's data
  (data availability sampling) and check one small proof that the execution was
  right. Cost stays about the same whatever the usage.

That changes the budget of the whole system. In the old model, raising
throughput always raised the cost of running a node. In the new model,
throughput limits move to **provers and builders** (a few big machines), while
**verifying** stays cheap for everyone. Every other change in the post follows
from this one.

The EF zkEVM team's numbers make it concrete: checking a proof takes about the
same time for a 60M-gas block as for a 600M-gas block. In late 2025 zkVMs could
prove 99% of mainnet blocks in under 10 seconds on target hardware. ZisK reports
7.4s on 24 GPUs.

---

## 3. The whitepaper, section by section

Vitalik goes through the Bitcoin whitepaper and marks each section for 2015
(yellow), 2025 (green) and 2030 (blue). Here it is expanded, with the actual
proposal behind each change.

### §2 Transactions: how do you know a tx was authorized?

**2010:** one ECDSA signature per tx, checked by every node, kept forever.

**2030:** sometimes one or more quantum-safe signatures, sometimes a ZK proof
in place of a signature. And, the big change, **signatures don't go onchain at all.**

The pieces:
- **EIP-8141 Frame Transactions** (scheduled for Hegota, moved to SFI on
  ACDE #244, 2026-08-27). New tx type `0x06`, made of ordered "frames." VERIFY
  frames run the account's own check: ECDSA, ML-DSA, SLH-DSA, passkey, multisig,
  or any ZK proof. An `APPROVE` opcode splits "may execute" from "will pay gas."
  This is native account abstraction. It is also the migration path to quantum
  safety, because the account picks its own scheme instead of the protocol
  hardcoding ecrecover.
- **EIP-8288 In-mempool signature and proof aggregation** (Vitalik + co-author,
  draft, merged into the EIPs repo 2026-09-09). Builds on 8141 with a new frame
  mode (`DEP_VERIFY_FRAME_MODE = 3`). A tx declares its "dependencies" as
  `(scheme, data_hash, verification_key_hash)` triples, up to 256 per frame.
  Mempool nodes check them, then fold them together into one **recursive STARK**.
  A block is valid only with that one proof covering every tx. First target
  scheme: LeanSPHINCS (`0x10`), a hash-based post-quantum signature.

Why it matters: quantum-safe signatures are kilobytes each, not 65 bytes. Put
raw on chain, they'd use up block space. Aggregated, a block pays one proof of
about 100–300 KB plus 96 bytes per statement, however many signatures went in.
Vitalik's number: a quantum-safe private tx could go from **~10M gas today to
the low tens of thousands.** Reported target for 8288 is the fork after Hegota
("I-star"), around 2029. Not scheduled yet.

### §4 Proof of work: who makes the block, and how is the chain picked?

**2010:** nonce search. One miner wins and makes the whole block alone.

**2030:** PoS with few-slot finality. Block making is split up:
- **ePBS, EIP-7732** (Glamsterdam; Sepolia on 2026-10-06, mainnet expected Q4
  2026). Builders and proposers are split inside the protocol, not through relay
  middleware. It also gives provers a 6–9s window, which the zkEVM plan needs.
- **FOCIL, EIP-7805** (Hegota's consensus-layer headliner, confirmed April 2026).
  A committee of validators each publishes an "inclusion list" of pending txs.
  Attesters reject any block that leaves out valid listed txs. The builder still
  orders the block but **can no longer censor.**
- **Mempool aggregators** (8288). Signatures and proofs are pulled off early and
  handled by mempool nodes, not by the builder.

So a block goes from "one person's decision" to a pipeline: mempool nodes
aggregate, the FOCIL committee forces inclusion, the builder orders, the
proposer signs, provers prove.

Consensus itself (from the Strawmap, Feb 2026): slots step down 12 → 8 → 6 → 4
(maybe 3, maybe 2) seconds, each step only once it's shown safe. Finality moves
to a one-round protocol (**Minimmit**) signed by a rotating committee of about
256–1,024 validators using hash-based post-quantum signatures aggregated by
STARKs. Strawmap target: finality in about 6–16 s, down from about 16 minutes
today. The post's own numbers are a bit wider: **~4–8 s slots, ~8–32 s finality.**

### §5 Network: who sees what?

**2010:** broadcast everything to everyone. Every node downloads every block.

**2030:**
- Only **entry nodes** see raw signatures and proofs (after 8288). Everyone else
  sees aggregated data.
- **PeerDAS** (EIP-7594, live since Fusaka, Dec 2025): each node downloads and
  checks only a slice of the data. Today that covers blobs (L2 data). Later it
  covers full execution blocks too.
- Fork choice uses **parallel attestations**, not blocks passed along one by one.
- **Sender privacy** through onion routing and mixnets.

### §7 Disk space: what does a node store?

**2010:** keep everything, prune spent outputs.

**2030:**
- History split from state (already underway: EIP-4444 history expiry work).
- **State not needed to verify.** With a SNARK per block, a verifying node needs
  no state at all. That is "stateless validation," the second optional mode in
  **EIP-8025**.
- **Inner tree nodes often not stored.** With block-level access lists
  (**EIP-7928**, Glamsterdam) saying exactly which slots changed, plus a proof,
  you don't need to keep the full Merkle/binary tree to update the root.
- **Distributed storage:** each node keeps a fraction of history and state.
- **Storage by object type:** DB for hot state, flat files for cold history.

### §10 Privacy

**2010:** pseudonyms. "The tape is public, but identities aren't." In practice
the UTXO graph can be analyzed.

**2030,** by layer:

| Layer | 2010 | 2030 | Mechanism |
|---|---|---|---|
| Writes (what you did) | hope the graph can't be analyzed | ZK-SNARKs | shielded pools, native shielded ETH (a Strawmap north star) |
| Account policy (how your account checks auth) | none, everyone uses ECDSA | ZK-SNARKs + private AA | 8141 VERIFY frames that check a proof, not a public sig |
| Reads (what you looked up) | run a full node or give it up | full node (easy now) or TEE+ORAM / PIR | Kohaku SDK, EF "privreads" |
| Network (where you are) | hope nodes aren't tracking you | onion routing, mixnets | Kohaku mixnet/Tor relay, P2P broadcast |

FOCIL and 8288 are what make privacy protocols **first-class** at the base layer.
Today a shielded tx is huge (so builders can price it out) and censorable
(a builder can just skip it). With 8288 its proof gets aggregated cheaply. With
FOCIL, any single includer can force it in.

The open item he names: **programmable privacy**. Private compute over shared
state with many parties is still unsolved without iO (see §7).

---

## 4. The one-table summary (his table, restated)

| Question | 2010 | 2030 |
|---|---|---|
| Was the tx authorized? | signature | quantum-safe sig(s) or a ZK proof |
| Which chain is canonical? | PoW | PoS, few-slot finality, available chain |
| How are blocks verified? | re-download, re-run | SNARK + PeerDAS |
| Tx path | user → mempool → miner → block | user → private mempool → FOCILer or builder → block; sigs/proofs pulled off and aggregated early |
| Shape of compute | serial | parallel; mempool proves in parallel; gas favors parallel-friendly work |
| How nodes save space | prune old history | small slice of history; distributed storage; skip inner tree nodes; per-type storage |
| What light clients verify | consensus only (trust majority for validity) | consensus **and** validity (DA + compute) |
| Write privacy | assume graph can't be analyzed | ZK-SNARKs |
| Account-policy privacy | none | ZK-SNARKs + private AA |
| Read privacy | full node or nothing | full node (easy) or TEE+ORAM / PIR |
| Network privacy | trust mempool nodes | onion routing, mixnets |

The light-client row may matter most for everyday users. A phone wallet today
trusts that the validator majority is honest about execution. In 2030 the phone
checks the proof itself. That is the difference between "light client" and
"full node in your pocket."

---

## 5. What changes for users

His 2015 vs 2030 scorecard:

| | 2015 | 2030 |
|---|---|---|
| Uptime | 100% | 100% |
| Censorship resistance | yes | **strong: guaranteed real-time inclusion (FOCIL)** |
| Runs as programmed | yes | yes |
| Irreversibility | yes | yes, often with stronger privacy than servers |
| Cost | very high | high for general compute; **much lower for specialized compute** |
| Privacy | none | general private compute still hard; **special-purpose apps strongly private** |
| Latency | ~17 s block, ~200 s for 12 confs | **~4–8 s slot, ~8–32 s finality** |
| Node | run a big node or trust someone | run a node for best guarantees, but much lighter |

Two honest points in this table are easy to miss:
1. **General compute stays expensive.** Cheap compute comes only when the work
   fits a pattern the network can prove or aggregate.
2. **General private compute stays hard.** Private payments, private voting and
   private identity are fine. Private shared-state DeFi with arbitrary logic is not.

---

## 6. The builder takeaway: gas stops being flat

This is the section app developers should read twice.

> "In a simple blockchain, 1 byte = 1 byte and 1 gas = 1 gas."

That stops being true. The same work costs:
- **More** if it's one big serial tx that nobody can split up.
- **Less** if it's split into well-defined dependencies that can be run in
  parallel, pruned, or aggregated, **ideally before the tx reaches the block.**

His picture: a chain of state changes `A→B, B→C, C→D…`, each with its own
"here's why that's allowed." In the future layout only the state changes and
their order go onchain. The "why it's allowed" parts (signatures, proofs,
permission checks) are handled in parallel in the mempool and folded into one
proof.

His long-run guess: **the chain only records non-commutative state changes (the
ones where order matters). Everything else is aggregated first.**

What this means in practice:
- **Signature checks leave your contract.** With 8141/8288 the account's
  VERIFY frame declares a dependency, and the mempool proves it. Contracts that
  run `ecrecover` or verify a proof inline will be on the expensive path.
- **Declare your state access.** BALs (7928) already reward txs whose read/write
  set is known. Parallel execution plus gas repricing (EIP-8037 and related, in
  Glamsterdam) point the same way. Global counters, shared hot slots and
  "touch everything" routers are serial bottlenecks. Expect them to cost more
  over time.
- **Commutative work can be batched.** Balance increments, votes, attestations,
  and appends to a set can be summed or aggregated offchain and posted as one
  proven delta. Designs that need a strict global order for everything waste this.
- **Proof-carrying apps get cheaper, not more expensive.** Today a ZK app pays
  roughly 200–500k gas per proof check. With in-mempool aggregation the marginal
  cost trends toward a hash plus a few bytes. ZK-first app designs that are too
  pricey on L1 today become normal.

Practical rule for anything we build from 2027 on: **keep the parts where
order matters small and onchain. Move everything that just proves something is
allowed into a signature or proof that can be aggregated.**

---

## 7. "Decentralization as a performance feature"

This is the most original idea in the post.

The old view: decentralization is a **tax**. Every node redoes all the work,
so a decentralized system is always slower than a server. You pay for safety.

The new view: **sometimes** it's a strength:
- **Storage:** many nodes can hold more data in parallel than one (PeerDAS,
  distributed history).
- **Compute:** many mempool nodes can check and prove in parallel (8288).
- **Privacy:** only a decentralized network can really hide metadata, meaning
  where a request came from. A single server always knows.

Why the 2010s version of this dream failed: **verification.** Splitting work
across strangers means checking that each piece was done right. Sharding designs
used random committees, which were slow to set up, added latency, and offered no
recourse if the committee lied. Proofs fix this. The work is checked
cryptographically, and the overhead drops "month by month."

The latency point: Ethereum itself will never match a server's latency, but
**infrastructure built around it** could. He suggests a decentralized layer
between users and the chain that is **not itself a chain.** Think preconfirmation
networks, based-rollup sequencer sets, or proof-aggregating mempools. They give
fast soft answers backed by the chain's hard ones.

---

## 8. Later: iO

Indistinguishability obfuscation is the "holy grail." With practical iO, you
could run general computation for any number of async participants fully
encrypted, which ends the privacy-vs-generality tradeoff from §5. Weaker forms
already help build **encrypted mempools**.

He is clear that **nothing in the post depends on iO.** Everything above
happens long before it's practical. Treat it as a far horizon, not a plan.

---

## 9. What's hard (his words and others')

**He names two:**
1. **Efficient and safe ZK proofs.** Hard, but the complexity is contained, and
   "already being heavily optimized with AI tools." The EF zkEVM team's own
   status is "performance has improved, but security work is unfinished."
   Formal verification of zkVMs is the gate for making proofs mandatory.
2. **Large state.** Managing and parallelizing access to very large state is
   "the more difficult, and systemically complex, piece." There are ideas
   (binary trees, BALs, state expiry, distributed state), but they depend on
   what apps end up doing. **This is the real bottleneck.** Proofs make
   *verifying* cheap. They don't make *building* a block over a huge shared
   state cheap.

**Others have raised (Yak Collective study group; press coverage):**
- **Many handoffs.** mempool aggregator → builder → FOCIL committee → proposer
  → prover(s) → verifier → formally verified zkVM → compiler toolchain. Each
  handoff can fail, and the post doesn't discuss that attack surface.
- **"100% uptime" in bad conditions.** If the global network is degraded, the
  chain may stay "live" but not reach finality, which makes it effectively
  unusable. The scorecard glosses over this.
- **An L2 retreat?** Some read the post as quietly moving away from the
  rollup-centric roadmap toward "L1 as a proven, parallel settlement layer."
  Others see normal evolution. The post barely mentions L2s after the opening.
- **Prover centralization.** 1-of-N liveness (one honest prover is enough) is
  good. But if proving takes GPU clusters, the set of block producers could
  shrink. EIP-8025's first design has attesters wait for 3 of 5 independent
  proofs as a safety margin, and that is still in draft.

---

## 10. Timeline: where each piece stands (2026-09-30)

| Item | What it does | Status |
|---|---|---|
| PeerDAS (EIP-7594) | nodes sample slices of data | **Live** (Fusaka, Dec 2025) |
| Fast Confirmation Rule | ~12 s confirmations from attestations | client-side; shipping ~mid-2026 |
| ePBS (EIP-7732) | in-protocol builder/proposer split; 6–9 s proving window | **Glamsterdam**: Sepolia 2026-10-06, mainnet Q4 2026 (date TBD) |
| BALs (EIP-7928) | block lists all touched state → parallel exec, cheaper roots | **Glamsterdam** |
| Gas repricing (EIP-8037 +) | prices closer to real cost; path to 200M gas | **Glamsterdam** |
| FOCIL (EIP-7805) | forced inclusion, censorship resistance | **Hegota** CL headliner, SFI; Q2 2027 (not confirmed) |
| Frame Transactions (EIP-8141) | native AA, any sig scheme, gas in tokens | **Hegota** EL headliner, SFI (spec may still change) |
| Optional execution proofs (EIP-8025) | verify a block by proof, no EL client | proposed for Hegota (PFI), A-tier in EF's Sept review |
| In-mempool aggregation (EIP-8288) | one recursive STARK per block | draft; reported target "I-star" (~2029) |
| Minimmit + PQ committee consensus | one-round finality, hash-based sigs | Strawmap, post-Hegota |
| Mandatory proofs / stateless | proof required for validity | post-Hegota; order vs PQ consensus under review |
| Slot cuts 12→8→6→4(→2) s | latency | Strawmap, stepwise through ~2029 |
| Kohaku, PIR, mixnets | read + network privacy | SDK live since Devcon 2025; PIR in progress; adoption still ~nil |
| iO | encrypted general compute | research only |

Strawmap cadence: about one fork every six months through 2029, seven forks,
updated quarterly by the EF Architecture team. The five north stars are
1 gigagas/s L1, more L2 data, post-quantum crypto, native shielded ETH, and
fast L1.

---

## 11. So what, for us

- **Timing:** the "normal" era has about one fork left. Anything we design now
  that assumes flat gas, public ECDSA-only accounts, or builders who can censor
  is designing for a chain that goes away around 2027–2029.
- **Wallet / signer work** (picowallet, CELL, clear-signing): the account-side
  change is 8141. Accounts pick their own scheme, and hash-based PQ signatures
  (LeanSPHINCS, Winternitz) become the ones the protocol aggregates cheaply.
  A hardware signer that can do a hash-based PQ scheme is aimed at where the
  chain is going. Clear signing still matters because VERIFY frames make
  "what am I approving" more complex, not less.
- **Contracts and apps:** design with small order-sensitive state and push
  proofs and signatures to the edges. Avoid global hot slots.
- **Privacy:** read and network privacy tools exist (Kohaku) but almost nobody
  uses them. That's an open lane for wallets and frontends now, without waiting
  for any fork.
- **Infra:** "a decentralized layer that is not a chain," meaning mempool
  aggregators, provers, preconf networks and PIR servers, is where new
  businesses and public goods will appear. That's the part of the stack this
  post is quietly pointing builders at.

---

## Sources

- Vitalik, "The cryptographic world computer," 2026-09-27 — https://vitalik.eth.limo/general/2026/09/27/the_cryptographic_world_computer.html
- Vitalik on X (launch thread) — https://x.com/VitalikButerin/status/2104160561374343176
- Strawmap — https://strawmap.org/ · Lean roadmap — https://leanroadmap.org/
- The Block, strawmap: seven forks through 2029 — https://www.theblock.co/news/ecosystems/2026-02-26-ethereum-foundation-researchers-publish-strawmap-outlining-seven-forks-through-2029-391406
- CoinDesk, finality in seconds by 2029 — https://www.coindesk.com/tech/2026/02/26/ethereum-foundation-drops-most-ambitious-roadmap-in-years-targets-finality-in-seconds-by-2029
- EIP-8288 — https://eips.ethereum.org/EIPS/eip-8288
- Crypto Briefing on 8288 — https://cryptobriefing.com/eip-8288-recursive-stark-mempools-ethereum/
- Incrypted on 8288 costs — https://incrypted.com/en/vitalik-buterin-explained-how-ethereum-could-make-cheaper/
- EIP-8025 — https://eips.ethereum.org/EIPS/eip-8025 · EF zkEVM blog — https://zkevm.ethereum.foundation/blog/eip-8025-optional-execution-proofs-hegota
- EIP-8141 pattern (IPTF) — https://iptf.ethereum.org/patterns/pattern-native-account-abstraction/ · ERC-8286 — https://eips.ethereum.org/EIPS/eip-8286
- Hegota scope — https://tatum.io/blog/ethereum-hegota · https://cryptodaily.co.uk/2026/08/hegota-focil-frame-transactions-l1-privacy · https://crypto.news/ethereum-hegota-narrows-2027-upgrade-proposals/
- Glamsterdam Sepolia date — https://www.coinspeaker.com/ethereum-news-glamsterdam-sepolia · https://blog.thirdweb.com/ethereum-glamsterdam-upgrade-epbs-bal-200m-gas-limit/
- Privacy stack / Kohaku / PIR — https://ethereum.org/videos/ethereum-privacy-stack-andy-guzman · https://hackmd.io/@brech1/ethereum-privacy-pir · https://iptf.ethereum.org/blog/exploring-hardened-shielded-pools/ · https://www.coindesk.com/tech/2026/05/20/vitalik-buterin-outlines-ethereum-s-privacy-measures-here-is-what-it-means-for-the-network-and-eth
- Reactions — https://yakcollective.substack.com/p/the-cryptographic-world-computer · https://decrypt.co/379461/vitalik-buterin-outlines-cryptographic-world-computer-plan-for-ethereum
