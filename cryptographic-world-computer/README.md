# "The cryptographic world computer" — Vitalik, 2026-09-27

Source: https://vitalik.eth.limo/general/2026/09/27/the_cryptographic_world_computer.html

## Thesis in one line
By ~2030 Ethereum is a "blockchain" mostly for historical reasons. Every core part of
Satoshi's design (verify = re-execute, one block maker, public tx = privacy via pseudonyms)
gets replaced by cryptography that didn't exist or wasn't mature in 2009 (SNARKs/STARKs,
DAS, PIR, mixnets). Hegota (2027) is the last "normal" fork; after that the story is
recursive STARKs, formal verification, faster PoS, quantum safety.

## Bitcoin whitepaper, section by section (his annotated images)
| Section | 2010 | 2030 |
|---|---|---|
| 2. Transactions | signature per tx, state+history mixed | state and history split; sigs aggregated offchain, one per block; often a ZK proof instead of a sig; quantum-safe sigs |
| 4. PoW | nonce search, one guy makes the block | PoS; multi-party block building (FOCIL, ePBS); tx parts (sigs, proofs) stripped off and aggregated in the mempool |
| 5. Network | broadcast everything, everyone downloads everything | only entry nodes see raw sigs/proofs (post-EIP-8288); PeerDAS = each node downloads a slice (blobs today, full blocks later); fork choice from parallel attestations, not blocks; sender anonymity via mixnets |
| 7. Disk space | prune spent txs | history split from state; state not needed to verify (SNARKs); inner tree nodes often not stored (SNARKs + BALs); distributed state/history storage; DB vs flat files per object type |
| 10. Privacy | pseudonymous keys ("the tape") | ZK-SNARK privacy protocols made first-class by FOCIL + EIP-8288; read privacy (TEE+ORAM, PIR); broadcast privacy (mixnets); programmable privacy = open question |

## What changes for users (2015 → 2030)
- Inclusion: guaranteed real-time inclusion via FOCIL.
- Cost: general compute still expensive, specialized compute much cheaper.
- Privacy: general-purpose private compute still hard; special-purpose apps strongly private.
- Latency: ~17s block / ~200s 12-conf → ~4-8s slot / ~8-32s finality.
- Nodes: still run one for best guarantees, but much lighter. Light clients verify validity, not just consensus.

## The builder takeaway
Gas stops being flat. One big serial tx costs more; the same work split into
parallelizable / prunable pieces (sigs, proofs, "here's why that's allowed") costs less,
ideally aggregated before the block. Long run: only the ordering-sensitive
(non-commutative) state changes go onchain; everything else gets aggregated before inclusion.

## Decentralization becomes a performance feature (sometimes)
Old dream: split work across nodes to scale. Failed because you couldn't verify the work
(committees were slow, complex, no recourse). Proofs fix that. So the network can store
data in parallel, do compute in parallel in the mempool, and hide metadata better than any
server can. Also watch: a decentralized non-chain layer between users and the chain
for latency.

## Later
iO (obfuscation) could remove the privacy vs generality tradeoff; weak versions help
encrypted mempools. Not needed for anything above.

## Hard parts he names
- ZK proofs efficient + safe: hard but encapsulated, AI tools already helping.
- Harder: managing and parallelizing access to very large state.

## Terms
FOCIL = fork-choice enforced inclusion lists (many validators force txs in).
PeerDAS = sample data availability. BALs = block-level access lists (EIP-7928).
EIP-8288 = mempool-level sig/proof aggregation (per his annotation). Strawmap = the lean Ethereum roadmap.
