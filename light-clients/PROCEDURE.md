# How to add a light client to a wallet

Written 2026-11-10. Steps for a JS/TS wallet (browser extension, web app, Node).
Background and the Helios vs Colibri comparison are in `README.md` next to this file.

What was tested: the Colibri path in Node (`sim.mjs`). The Helios code below comes from
its package docs and Kohaku's adapter and was not run here.

## 1. Pick one

- **Colibri** if you want transaction simulation, the smallest download (1.4 MB), or mobile bindings.
- **Helios** if you want the more widely used one (2.2k stars), OP Stack L2s, or to use your own Alchemy RPC with no extra server.

Kohaku offers both and lets the user choose per network. You can do the same.

## 2. Line up the data sources

The light client still fetches from servers. It checks what they send.

| | You need |
|---|---|
| Helios | An execution RPC that supports `eth_getProof` (Alchemy does). A consensus RPC (beacon light client data). |
| Colibri, remote mode | A Colibri prover URL. Theirs is hosted; you can run your own in Docker. |
| Colibri, hybrid mode | A prover for the block header proof, plus your own execution RPC for the state. |
| Colibri, local mode | An execution RPC and a beacon API. No prover. Slowest. |

## 3. Decide the trust anchor

The client must start from one block it trusts.

- Easiest: let it fetch a recent checkpoint from the default checkpoint servers.
- Safer: hard-code a checkpoint hash you checked yourself (`checkpoint` in Helios, `trusted_checkpoint` in Colibri) and update it with each release.
- Colibri only: `zk_proof: true` starts from a ZK proof of the whole sync committee chain. Kohaku turns this on by default.

A checkpoint that is too old (weeks to months) is refused. Don't turn that check off.

## 4. Install

```sh
npm i @corpus-core/colibri-stateless   # Colibri 3.0.3
npm i @a16z/helios                     # Helios 0.12.0
```

Both ship a WASM file. Check that your bundler copies it and does not pre-bundle it
(the Colibri workshop excludes it from Vite's dependency pre-bundling for this reason).
In an extension, the content security policy must allow WASM (`wasm-unsafe-eval`).

## 5. Create the client at startup

Colibri:

```ts
import Colibri, { Strategy } from '@corpus-core/colibri-stateless';

const lc = new Colibri({
  chainId: 1,
  prover: ['https://mainnet.colibri-proof.tech'],
  rpcs: [ALCHEMY_URL],
  prover_mode: 'hybrid',
  proofStrategy: Strategy.VerifiedOnly,   // never fall back to unchecked answers
  include_code: true,                      // needed if rpcs is empty
});
```

Helios:

```ts
import { createHeliosProvider } from '@a16z/helios';

const lc = await createHeliosProvider({
  executionRpc: ALCHEMY_URL,
  consensusRpc: CONSENSUS_URL,
  network: 'mainnet',
  // checkpoint: '0x...'   optional hard-coded anchor
}, 'ethereum');
await lc.waitSynced();
```

Create it once and keep it alive. In a Manifest V3 extension the service worker gets
killed, so expect to rebuild it. Helios saves its checkpoint to localStorage so the next
start is faster.

## 6. Plug it in as the provider

Both are EIP-1193 providers. Nothing else in the wallet needs to change.

```ts
import { BrowserProvider } from 'ethers';
const provider = new BrowserProvider(lc);
```

## 7. Handle what it can't do

- **Sending transactions.** Helios can. Colibri cannot: give it a `fallback_provider`, or send through your normal RPC.
- **Logs.** Helios only proves logs from the last 8,191 blocks and it is slow. Kohaku sends `eth_getLogs` straight to the RPC, unchecked. Decide if you accept that for history views.
- **Missing methods.** Colibri has no `eth_gasPrice`, `eth_feeHistory` or `eth_createAccessList`. Route these to the plain RPC. A wrong gas price can't steal funds.
- **Other chains.** Use the light client where it is supported and the plain RPC elsewhere. Show the user which is which.

## 8. Add simulation (Colibri)

Before the sign screen:

```ts
const sim = await lc.request({
  method: 'colibri_simulateTransaction',
  params: [{ from, to, data, value }, 'latest'],   // data is required, use '0x' for a plain send
});
// sim.status, sim.gasUsed, sim.logs (decoded), sim.trace
```

Show the decoded logs (token transfers, approvals) to the user. If simulation fails or a
proof is rejected, say so on the sign screen. Don't hide it.

With Helios you only get `eth_call` and `eth_estimateGas`: return value and gas, no logs.

## 9. Make failures visible

- A rejected proof means the server lied or is broken. Show an error. Never show the unchecked value.
- Show a badge for verified vs unverified, like Kohaku does.
- Keep a setting to switch back to the plain RPC, for when the prover or beacon endpoint is down.

## 10. Test it

1. Point it at a lying RPC and confirm the wallet rejects the answer. Corpus Core hosts one for this: `https://lying-rpc.colibri-proof.tech/forged`.
2. Log every outgoing request and confirm nothing skips the light client that shouldn't.
3. Measure cold start and per-call time in the real target (extension, phone). In Node, Colibri reads took 0.2 to 0.8 s and the first call 1 to 2 s.
4. Kill the prover or RPC and check the wallet fails cleanly.

## What this does not give you

- **Privacy.** The server still sees every address and contract you look up. Colibri's `privacy_mode: 'basic'` keeps calldata away from the server but not the storage slots.
- **Full-node security.** You trust that 2/3 of the 512-member sync committee is honest. They are not slashed for lying.
- **A hardware wallet path.** This is for a wallet with a network connection and a few MB to spare. A Pico-class device would need a host to fetch proofs and only verify on the chip. Colibri's C core is aimed at that; not tested here.
