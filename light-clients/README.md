# Light clients: Helios, Colibri, Kohaku

Researched 2026-11-10. The names in the note were **Colibri** ("kolibri") and **Helios** ("helius").

## Short answer

- Yes, Kohaku has light clients. It ships both Helios and Colibri as RPC provider options.
- Yes, a light client can run a simulator. Colibri already does (`colibri_simulateTransaction`), and the Kohaku wallet uses it on the sign screen.
- I ran it: a USDC `approve(max)` simulated against proven mainnet state in about 200 ms and came back with the decoded `Approval` event, gas used, status and a call trace.

## What a light client gives you

A normal wallet asks an RPC (Alchemy, Infura) and believes the answer. A light client checks the answer:

1. It follows the beacon chain's sync committee (512 validators, rotated about every 27 hours). Their BLS signature covers a recent block header.
2. That header has the state root.
3. Every balance, storage slot or contract code the RPC returns comes with a Merkle proof against that root.

So the RPC can refuse to answer, but it can't lie.

Limits:
- You trust that 2/3 of the sync committee is honest. They are not slashed for lying, so this is weaker than a full node.
- You need one trusted starting checkpoint (or a ZK proof of the committee chain, which Colibri offers).
- The RPC still sees what you ask for. Verified is not private.

## Why simulation falls out of this

A simulator is an EVM plus state. If every piece of state the EVM touches is proven, the simulation result is as trustworthy as the chain itself. No Tenderly, no trust in the RPC's `eth_call`.

Both clients already run a local EVM for `eth_call`. Colibri exposes the full result (logs, trace). Helios only exposes the return value and gas.

## Helios vs Colibri

| | Helios (a16z) | Colibri (corpus.core) |
|---|---|---|
| Repo | a16z/helios, 2.2k stars, MIT | corpus-core/colibri-stateless, 36 stars, MIT (prover server is PolyForm Noncommercial) |
| Latest | 0.12.0, 2026-10-05 (Glamsterdam support) | 3.0.3, 2026-10-28 |
| Language | Rust, WASM for the browser | C core, WASM plus Swift, Kotlin, Python, Dart, Rust bindings |
| WASM size (npm, uncompressed) | 3.3 MB | 1.4 MB |
| Model | Stateful. Syncs and keeps following the chain. Runs as a local RPC on 127.0.0.1:8545 or in-page. | Stateless. Each answer comes with its own proof. Keeps only the sync committee. |
| Needs | Any execution RPC with `eth_getProof`, plus a consensus RPC | A Colibri prover (hosted or self-run), or "local" mode with a plain RPC and beacon API |
| EVM | revm | its own C EVM |
| Simulation | `eth_call`, `eth_estimateGas`, `eth_createAccessList`. No logs or trace. | `colibri_simulateTransaction`: logs (decoded), gas, status, trace. State overrides supported. |
| Old data | `eth_getLogs` only for the last 8,191 blocks, slow | Historic proofs via historical summaries |
| L2s | OP Stack (Optimism, Base, more), trusts sequencer signatures | Ethereum in production. OP Stack, Gnosis, Base at MVP stage. |
| Privacy | none built in | "PAP" mode: the EVM finds storage itself so calldata doesn't go to the RPC. TEE nodes optional for hiding the proof requests too. |
| Sends txs | yes | no `eth_sendRawTransaction` (needs a fallback provider) |

## How Kohaku uses them

Checked in the source (ethereum/kohaku, ethereum/kohaku-extension):

- `@kohaku-eth/provider` has adapters for `helios`, `colibri`, `raw`, `anon`, ethers and viem.
- The Helios adapter can bypass `eth_getLogs` straight to the RPC, because verified logs are slow.
- The Colibri adapter turns on `zk_proof: true` by default.
- The extension lets you pick `rpc`, `helios` or `colibri` per network and shows a badge: "RPC: Verified by Helios / Colibri".
- The badge tooltip says: "Some requests may still fall back to an unverified RPC provider." So it is not all-or-nothing yet.
- Simulation on the sign screen (`useColibriSimulation`) only works when Colibri is the selected provider. With Helios selected you get no simulation.

## What I ran

`sim.mjs` in this folder. Colibri 3.0.3 in Node, remote prover only, no execution RPC, strategy `VerifiedOnly`.

| Call | Time | Result |
|---|---|---|
| `eth_blockNumber` | 0.3–1.7 s (first call boots WASM) | ok |
| `eth_getBalance` | ~0.2 s | ok |
| `eth_call` USDC `balanceOf` | ~0.8 s | ok |
| `colibri_simulateTransaction` USDC `approve(max)` | ~0.2 s | status 1, gas 0xda62, decoded `Approval` log, trace |

Four HTTP requests total, all to the one prover host.

Run it: `npm i && node sim.mjs`

Gotchas found:
- With no `rpcs`, `eth_call` and simulation fail with "All nodes failed" unless `include_code: true` (otherwise it fetches contract code from an RPC).
- The default strategy silently falls back to the unverified RPC when a proof fails. Use `Strategy.VerifiedOnly`.
- `data` is required in the tx object, even for a plain ETH send.
- In remote mode the prover sees your full transaction. Private simulation needs `prover_mode: "hybrid"` + `privacy_mode: "basic"`.

## Not done

- **Helios was not run.** It needs an execution RPC with `eth_getProof`, and there is no Alchemy key in this repo or `~/clawd/.env.clawd`.
- Simulation on top of Helios (untested idea): point `anvil --fork-url` at the local Helios RPC. Every state read anvil makes is then verified, and anvil gives the full trace and logs.
- Did not measure browser cold start or mobile.
- Helios has an open issue (#859, 2026-10-24) titled as `eth_call` prefetch possibly masking proof failures. Title only, not read.

## Sources

- https://github.com/a16z/helios (rpc.md, releases, issues)
- https://github.com/corpus-core/colibri-stateless
- https://github.com/corpus-core/workshop (Devcon 8 "Swap Your RPC" workshop)
- https://corpus-core.gitbook.io/specification-colibri-stateless/specifications/ethereum/supported-rpc-methods
- https://github.com/ethereum/kohaku (packages/provider)
- https://github.com/ethereum/kohaku-extension (useColibriSimulation, NetworkVerificationBadge)
