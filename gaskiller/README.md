# Gas Killer — research notes

Gas Killer is a verifiable off-chain compute service for EVM contracts, built as an
EigenLayer AVS. Its flagship demo runs transformer inference (Qwen3-0.6B and
Qwen3.5-35B-A3B) as pure integer Solidity — hundreds of billions to trillions of
simulated gas — with a staked operator committee agreeing byte-exactly on the result
and settling it on Sepolia in one ~384k-gas transaction.

Context: Austin is interviewing the team on slop computer (as of 2026-07-31).

| File | Contents |
|---|---|
| [`CLIENT-API.md`](CLIENT-API.md) | Their client integration doc, verbatim as received 2026-07-31 |
| [`SAFETY-REVIEW.md`](SAFETY-REVIEW.md) | Our security review of the doc + API (verdict: safe) |
| [`INTERVIEW-NOTES.md`](INTERVIEW-NOTES.md) | Prep for the interview: live-demo logistics, question threads |

Key framing note: despite the "zk" first impression, there are **no ZK proofs** in the
current system — it's staked-committee re-execution with BLS-aggregated signatures.
See the safety review and interview notes.
