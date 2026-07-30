# anon-rpc — deep research

*Researched 2026-07-30. Sources: the [project site](https://privacy-ethereum.github.io/anon-rpc/), the
normative [SPEC.md](https://github.com/privacy-ethereum/anon-rpc/blob/main/SPEC.md) (v0.3.0, 2026-07-27),
full clones of `privacy-ethereum/anon-rpc`, `privacy-ethereum/kps`, and `privacy-ethereum/tor-js`,
the [proposal article](https://reads.ethereum.foundation/feed/anon-rpc/) on the EF "Reads" team site,
and live mainnet state read via Alchemy.*

## TL;DR

**anon-rpc is not an anonymity network. It's a standard for *pluggable, verifiable* anonymity
clients.** A wallet points at an on-chain "specifier" contract, downloads a JS bundle whose
keccak256 must match the contract's `workerHash()`, runs it in a null-origin sandboxed
Web Worker, and gets back an anonymized `fetch()`. What that fetch *does* — Tor, a mixnet,
Nym, direct devp2p — is entirely up to the worker bundle. The EF's own first real backend is
**tor-js** (Arti compiled to WASM, building real Tor circuits inside the browser, entering the
Tor network through **KPS** WebRTC gateways).

The whole stack is by the **EF "Reads" team** (network-privacy workstream of Privacy Stewards
of Ethereum, ex-PSE), and the code is essentially a two-month-old solo effort by
**Andrew Morris (voltrevo, ex-MetaMask)** with Ali Atiia co-authoring the proposal. It is early,
small (0 GitHub stars), and moving fast — spec went 0.2.0 → 0.3.0 in the last week of July 2026.

## The problem it attacks

Every wallet read (`eth_getBalance`, `eth_call`, log queries…) goes to an RPC gateway that
learns **IP ↔ addresses-of-interest ↔ query patterns**. The EF privacy roadmap calls this the
"private reads" gap: RPC metadata reveals portfolio, intent, and counterparties before any
transaction lands. The proposal's sharper framing: Ethereum's p2p layer is permissionless, but
**"what's actually concentrated isn't the network, it's the role of serving browsers"** —
browsers can only speak HTTPS-to-a-CA-blessed-domain, so serving them became a
Cloudflare-grade oligopoly.

Two distinct fixes get conflated; anon-rpc addresses both but separately:

1. **Censorship/centralization** — let browsers reach *domainless* counterparties (KPS solves this).
2. **Surveillance** — unlink queries from IP/identity (the worker's anonymization strategy solves
   this; Tor first).

## Architecture (the four layers)

```
wallet/dapp (host)
  └─ @anon-rpc/browser-harness  (trusted; npm 0.3.0)
       • reads specifier via any bootstrap RPC (eth_call)
       • fetches bundle from resolvers, verifies keccak256 == workerHash()
       • runs bundle in Web Worker inside null-origin iframe (sandbox=allow-scripts)
       • bridges capabilities over postMessage: fetch calls, KPS, storage, log
            └─ worker bundle  (UNTRUSTED, hash-pinned; the "anon-client")
                 • acceptCall() loop answers fetch calls
                 • routes them however it wants — e.g. tor-js over anonRpcWorker.kps
                      └─ KPS gateway (ip:port:certhash, no domain, no CA)
                           └─ Tor relays … exit … actual RPC provider
```

### Layer 1 — the specifier contract (on-chain code identity)

```solidity
interface IWorkerSpecifier {
  function workerHash() external view returns (bytes32);      // keccak256 of bundle bytes
  function workerResolvers() external view returns (string[]); // advisory fetch locations
}
```

The reference `WorkerSpecifier.sol` is **owner-updatable** (one stable address tracks worker
versions) with `renounceOwnership()` to freeze forever. Resolvers are advisory only —
"the standard verifies the hash; it doesn't care where the bytes came from" (IPFS, mirrors,
KPS peers, gossip all fine). Content-addressing means the system "can self-sustain
indefinitely after its operators walk away."

**Live mainnet state I verified directly (contract `0x4fd77be300f31c5fe6ab266d35d27750a3478d27`):**

- `workerHash()` = `0x194f04bde4925f6bbb0bd8bdfceca7251125eaa0664ce3c0c25dce2a1545338d`
- `workerResolvers()` = one URL: `raw.githubusercontent.com/privacy-ethereum/anon-rpc/keccak/19/4f04…` —
  a **branch named after the hash** (cute content-addressing hack on top of GitHub)
- `owner()` = EOA `0x6d25…0915` (5 txs) — **not renounced**; the owner key can repoint every
  pinned host at new code
- I fetched the 1,704-byte bundle and keccak'd it: **matches the on-chain hash**, and the code
  is byte-for-byte the built `passthrough-worker.ts`.

### Layer 2 — the sandbox (running untrusted code safely)

The harness boots the bundle inside a **Web Worker owned by a null-origin iframe**
(`sandbox="allow-scripts"` only). The worker gets *no* DOM, cookies, host origin, or wallet
keys — its entire platform is the `anonRpcWorker` capability object bridged over a
`MessageChannel` (the iframe only relays the port once; then host↔worker talk directly).
Spec §14 is explicit that this isolation is load-bearing: worker code is treated as untrusted
supply chain even though it's hash-pinned.

### Layer 3 — the capability API (what the worker gets)

```ts
type AnonRpcWorkerApi = {
  signalReady(): void;                 // gates buffered host fetch calls
  signalFailed(reason?): void;         // 0.3.0 addition: worker can refuse readiness
  acceptCall(): Promise<IncomingCall>; // discriminated by kind ("fetch" today)
  config: unknown;                     // host-supplied, frozen for worker lifetime
  kps: KpsApi;                         // dial(addr) / openStream(addr) — byte streams + datagrams
  storage: StorageApi;                 // binary KV, namespaced per specifier address (IndexedDB)
  log: LogApi;                         // best-effort diagnostics, redactable
};
```

Notable design choices (Appendix A of the spec):

- It standardizes a **wrapped API, not a message protocol** — wire encoding stays a harness
  implementation detail.
- **KPS is a built-in capability** precisely so the worker never needs WebRTC (or a full-page
  iframe) itself — a native harness can back the same API with QUIC, keeping workers
  platform-agnostic.
- KPS byte flow rides **transferred WHATWG streams** over the MessagePort, so backpressure is
  the browser's problem and only lifecycle calls round-trip as RPC.

### Layer 4 — KPS (Key Pinned Streams): browsers dialing domainless servers

Sister project, same author. Address = `ip:port:certhash` (sha256 of a self-signed cert,
multibase-u). The trick: **both sides derive the SDP and ICE password from the address
itself**, so a browser can complete a WebRTC/DTLS handshake with zero signalling servers, no
DNS, no CA. Native clients use QUIC/TLS1.3; one server demuxes both transports on a single
UDP port (STUN vs QUIC long-header). Tri-language interop (TS/Go/Rust), every client dials
every server.

Security posture (their SECURITY.md, refreshingly honest):

- MITM: impossible if the address arrives intact (cert pinned on both transports).
- Active probing: ICE password derives from certhash → probers without the address never
  reach DTLS.
- Threat model targets a **"low-effort blanket censor"** (keyword matching). Explicitly out of
  scope: IP blocking and wholesale WebRTC/QUIC bans ("private endpoints — a separate, later
  story").
- Known fingerprint: DTLS 1.2 sends the cert in cleartext and a 200-year validity is unusual
  for WebRTC; fix waits on DTLS 1.3.

## The part that actually anonymizes: tor-js + the gateway

**The mainnet-published worker is a pure passthrough** — its own comments call plain `fetch`
"the single seam a production anon-client replaces with anonymized routing." So today's demo
proves *verifiable code delivery + sandboxed execution*, not anonymity. The real client lives
in `privacy-ethereum/tor-js`:

- **Arti (Tor's Rust implementation) compiled to WASM** — the browser builds real Tor
  circuits itself. Onion encryption terminates *in the page*, not at any proxy.
- Browsers can't open TCP to relays, so they enter Tor via a **tor-js-gateway** reached over
  KPS. The gateway speaks "KPS-HTTP/1" (HTTP/1.1 syntax, one exchange per stream, HTTP/3-ish
  semantics) and multiplexes: `CONNECT` proxying to Tor relays, serving the worker bundle
  (hash-addressed immutable objects), serving `bootstrap.zip.zst` (Tor directory
  fast-bootstrap), and `/metadata.json` capability discovery. The gateway sees only encrypted
  Tor cells — it's a bridge, not a trusted proxy.
- `tor-js/test/anon-rpc-worker/` already runs the **full end-to-end**: published
  `@anon-rpc/browser-harness` → hash-verified tor-js worker → live gateway
  (`170.64.236.147:12298:uEiBHwUMN…`) → real Tor → `check.torproject.org` returns
  `IsTor:true`. Bootstrap ~30s.
- Ships on npm as `tor-js`; ~2.3 MB WASM embedded (31 kB gzipped loader variant via CDN).
  Status: explicitly experimental, no warranty.

So the intended production flow: wallet configures a specifier whose worker embeds tor-js;
every `eth_call` leaves the user's machine as Tor traffic through a domainless WebRTC
gateway, and the RPC provider sees a Tor exit IP. The proposal deliberately **refuses to pick
a winner** among anonymity networks — Tor, Nym, HOPR, Anyone Protocol etc. are all cited;
each would just be a different specifier address, and "networks compete on merit instead of
partnerships."

## Ecosystem context

- Team: **EF "Reads"** (reads.ethereum.foundation) — the private-reads workstream of Privacy
  Stewards of Ethereum. Sibling workstreams: GPU-accelerated **PIR** schemes (query state
  without the server learning what), batch-PIR ("Skirrt"), **VIA**, a verifiable binary-trie
  execution client with ZK proofs. anon-rpc is the *network*-privacy leg; PIR is the
  *content*-privacy leg — full private reads ultimately needs both (Tor hides who's asking;
  PIR hides what's asked even from the exit/provider).
- The proposal calls anon-rpc "a prelude to the **Abstract Access Layer** architecture."
- EthSystems has an open **private-reads RFP** (ORAM, PIR, TEE-RPC, mixnets) — same problem
  space, institutional angle.
- Related prior art by the same author: **Springboard** (browser-extension variant).

## Critical assessment

**What's genuinely good:**

- The **trust factoring is clean**: the harness (small, auditable, npm-published) is trusted;
  the frequently-changing anon-client is not, and is contained by hash-pinning + sandbox.
  This is a supply-chain answer most "just npm install our SDK" privacy projects don't have.
- **KPS is quietly the bigger idea** — signalling-free WebRTC to a pinned cert turns any box
  with a UDP port into browser-reachable infrastructure with no domain, no CA, no TLS cert
  churn. Useful far beyond RPC.
- Real engineering discipline for a young repo: normative RFC-2119 spec, e2e tests that
  prove every §4.2 failure mode against a real KPS server, hermetic CI, spec-version
  enforcement in the published package.

**What to be skeptical of:**

- **Nothing anonymizing is deployed yet on the standard path.** The only on-chain worker is
  the passthrough; "anonymized fetch" on the homepage describes the *interface contract*,
  not current behavior. Anonymity today = run the tor-js worker yourself with a demo
  gateway that "may be down."
- **The specifier owner is the supply chain.** The mainnet specifier is un-renounced, owned
  by an EOA; whoever holds that key ships code to every pinned host. Hash-pinning moves
  trust from "Cloudflare + npm" to "one hot wallet" until owners renounce or govern better.
- **Bootstrap leak:** reading the specifier and (in the demo) the balance query both go
  through user-supplied plain RPC URLs; the boot `eth_call` itself is observable. Chicken-egg
  is acknowledged (`preExisting` / `globalThis.ethereum`), not solved.
- **Gateway economics are unsolved.** Tor entry for browsers needs someone to run KPS
  gateways (bandwidth for full Tor cell traffic). No incentive layer exists; "incentivized
  variants" are hand-waved to the anonymity networks themselves.
- **Timing/volume analysis is out of scope** everywhere in the stack — a wallet polling
  balances every 12s through Tor still has a distinctive cadence, and PIR (which would fix
  the content side) isn't wired in yet.
- **Bus factor ≈ 1.** Essentially all commits across anon-rpc, kps, and tor-js are Andrew
  Morris, June–July 2026. Spec is Draft; API broke twice in the week before this research.

## Why it might matter to us

- The **harness pattern is directly reusable**: `new AnonRpcWorker({ address, preExisting })`
  → `worker.fetch` is a drop-in fetch for any wallet-ish frontend (SE-2 apps, burner
  wallets). Watching for when a tor-js worker gets published on-chain is the real adoption
  trigger.
- KPS (`@kpstreams/webrtc-client` / Go / Rust) is usable standalone today for
  browser↔headless-box streams with no domain or TLS setup — relevant to any of our
  phone-drives-a-box projects.
- The whole thing is also a nice case study in shipping *verifiable* client-side code via an
  L1 pointer — pattern generalizes to any "don't trust the CDN" web app.

## Key links

- Site: https://privacy-ethereum.github.io/anon-rpc/ · Spec §-by-§: `SPEC.md` in repo (v0.3.0)
- Repos: [anon-rpc](https://github.com/privacy-ethereum/anon-rpc) ·
  [kps](https://github.com/privacy-ethereum/kps) ·
  [tor-js](https://github.com/privacy-ethereum/tor-js) ·
  [tor-js-gateway](https://github.com/privacy-ethereum/tor-js-gateway)
- Proposal article: https://reads.ethereum.foundation/feed/anon-rpc/ (Morris & Atiia, 2026-06-02)
- Team site: https://reads.ethereum.foundation/ · npm: `@anon-rpc/browser-harness@0.3.0`, `tor-js`
- Mainnet specifier: `0x4fd77be300f31c5fe6ab266d35d27750a3478d27`
- EF privacy roadmap context: [The Block on private writes/reads/proving](https://www.theblock.co/post/370532/ethereum-foundation-sets-end-to-end-privacy-roadmap-with-private-writes-reads-and-proving) ·
  [EthSystems private-reads RFP](https://ethsystems.org/rfps/rfp-private-reads/) ·
  [EF privacy commitment](https://blog.ethereum.org/2025/10/08/privacy-commitment)
