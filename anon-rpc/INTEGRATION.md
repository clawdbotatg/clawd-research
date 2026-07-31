# anon-rpc × our products — integration & prototype plan

*Companion to [README.md](README.md) (the research itself). Written 2026-07-30 after a
file-level RPC/privacy survey of the slop-computer family in `~/clawd/`. The question this
answers: **where would anon-rpc actually plug into what we ship, what's worth prototyping
now, and what should wait for the tor-js worker to land on-chain?***

## TL;DR

- **The integration seam is one function.** Every scaffold-eth-2 app we ship funnels all
  reads through the wagmi transport in `services/web3/wagmiConfig.tsx`. `AnonRpcWorker`
  gives you a drop-in `worker.fetch`; wrap it in a viem `custom()` transport and the whole
  app's reads go through the sandboxed anon-client — no per-component changes.
- **Our exposure is real and mapped.** Four of our products let the browser hit Alchemy
  directly with the user's own address (worst → least): punk-wallet, denar.ai
  (slop-computer-ai-wallet), slop-computer-wallet, slop-computer-live.
- **But don't flip anything to "anon" yet** — the only on-chain worker is a passthrough, so
  today the transport swap buys architecture, not anonymity. The adoption trigger is a
  tor-js worker published on a specifier. Meanwhile there are two things worth doing now:
  a working spike of the transport (this repo, `prototype/`), and routing
  slop-computer-live's stray wagmi reads through the relay it already has.
- **The API-key trap:** anonymizing the IP is pointless if the URL still says
  `alchemy.com/v2/<our-key>`. The anon path must target keyless endpoints; keyed Alchemy
  stays for the normal path. Details below.
- **KPS is separately useful today** — it would let the fleet relay drop the
  `h.atg.link` + certbot dependency entirely (`ip:port:certhash`, no DNS, no CA).

## What the survey found (where browsers leak IP ↔ address)

Ranked by exposure. File references are into `~/clawd/<repo>`.

| # | Product | Exposure | The leak |
|---|---------|----------|----------|
| 1 | **punk-wallet** | severe, continuous | Browser holds the **raw private key in localStorage** (`react-app/src/components/Wallet.jsx:100`) and polls `getBalance` + ERC-20 `eth_call` for that address on a timer from the user's IP (`hooks/Balance.js:33`, `helpers/ERC20Helper.js:96`) across ~20 chains, via a hardcoded shared Alchemy key. The provider sees IP↔address↔cadence for the machine that holds the key. |
| 2 | **denar.ai** (slop-computer-ai-wallet) | high, authenticated | Heavy reads are correctly proxied via `app/api/*` routes — but `useEnsName`/`useEnsAvatar` for the *signed-in* address fire from the browser (`AddressInfoDropdown.tsx:43`, `DetailModal.tsx:202`) through Alchemy URLs committed in `scaffold.config.ts:29-33`. Every session is a known address. |
| 3 | **slop-computer-wallet** | high, inherent to a wallet UI | Multisig state, nonces, predicted addresses, balances for the connected user all read browser-side through the standard SE-2 wagmi config (`wagmiConfig.tsx:20-28`). |
| 4 | **slop-computer-live** | moderate — and the best case study | Two-tier *by design*: the relay proxies portfolio/gas server-side precisely to avoid per-client Alchemy calls (`relay/src/gas.ts:7`, `index.ts:5135`). **But the wagmi path bypasses it**: `hooks/usePersonalWallet.ts:64-88` (`useReadContract` + `useBalance` + `useBytecode` on Base for the visitor's passkey-derived wallet), `PasskeyWalletContext.tsx:67`, `useEnsAvatarFromAddress.ts:12` — all from the guest's browser, key inlined via `NEXT_PUBLIC_ALCHEMY_API_KEY`. So Alchemy learns (guest IP → passkey wallet) for everyone who joins the show. `cypherpunkPlan.md:47-49` already names Alchemy as a trust rung to climb off. |
| 5 | frontpage / contracts | low | Anonymous registry reads; a user address appears only on wallet-connect (tipping / admin). |
| — | container / background / twitter | none | No chain RPC at all. |

Side findings worth fixing regardless of anon-rpc:

- **slop-computer-live's "server-side" routes use the browser-public key**: `app/api/live-slug/route.ts:52`
  and `clear-sign/lib.ts` read `NEXT_PUBLIC_ALCHEMY_API_KEY` — the same value already shipped
  in every browser bundle. Split a server-only `ALCHEMY_API_KEY` so the relay's key-hygiene
  posture holds end to end.
- Several repos ship hardcoded Alchemy keys in committed source (wallet `scaffold.config.ts:15`,
  ai-wallet `scaffold.config.ts:14,29-33`, punk-wallet `constants.js:1,6`, plus the SE-2
  default key in three more). Some are upstream defaults, but they're live in shipped
  bundles; frontpage additionally bakes its key into an immutable IPFS pin.

## The integration seam: one viem transport

The anon-rpc harness API (npm `@anon-rpc/browser-harness@0.3.0`, verified against the live
demo source):

```ts
import { AnonRpcWorker } from "@anon-rpc/browser-harness";

const worker = new AnonRpcWorker({
  address: SPECIFIER,                       // on-chain IWorkerSpecifier
  preExisting: { rpcProvider: { request } } // bootstrap: reads workerHash()+resolvers
});
await worker.ready;   // bundle fetched, keccak-verified, running in the sandbox
worker.fetch;         // fetch-compatible — every call routed through the worker
```

Everything SE-2 does goes through wagmi → viem transports, so this is the whole
integration:

```ts
// anonTransport.ts — drop into any SE-2 app's services/web3/
import { custom, type Transport } from "viem";
import { AnonRpcWorker } from "@anon-rpc/browser-harness";

export function anonTransport(specifier: string, rpcUrl: string, bootstrapUrl: string): Transport {
  let worker: AnonRpcWorker | undefined;
  let id = 0;

  const bootstrap = async (method: string, params: unknown[]) => {
    const r = await fetch(bootstrapUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
    });
    return ((await r.json()) as { result: unknown }).result;
  };

  return custom({
    async request({ method, params }) {
      if (!worker) {
        worker = new AnonRpcWorker({
          address: specifier,
          preExisting: { rpcProvider: { request: (a: any) => bootstrap(a.method, a.params ?? []) } },
        });
        await worker.ready;
      }
      const resp = await worker.fetch(rpcUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params: params ?? [] }),
      });
      const body = (await resp.json()) as { result?: unknown; error?: { message?: string } };
      if (body.error) throw new Error(body.error.message ?? "RPC error");
      return body.result;
    },
  });
}

// wagmiConfig.tsx: transports: { [mainnet.id]: anonTransport(SPECIFIER, RPC_URL, BOOTSTRAP_URL) }
```

Caveats that matter in a Next.js app:

- **Browser-only.** The harness needs a real DOM (null-origin iframe + Web Worker). SSR and
  route handlers must keep a plain `http()` transport; gate the anon transport on
  `typeof window !== "undefined"` or construct it client-side only.
- **Boot cost.** Specifier read + bundle fetch + verify ≈ a second with the passthrough;
  ~30 s Tor bootstrap once the worker is tor-js. Boot lazily (first read), keep one worker
  per page, and show a status pill (the demo's `boot → ready → live` states map cleanly to
  UI).
- **Spec is a moving target.** 0.2.0 → 0.3.0 broke the API in one week; pin exact versions
  and expect churn until the spec leaves Draft.

## The API-key trap (and our Alchemy house rule)

Our standing rule is *never public RPCs, always Alchemy with a key* — the right call for
reliability today. But the anon path inverts the logic: if the worker routes through Tor and
then requests `eth-mainnet.g.alchemy.com/v2/<our-key>`, the provider no longer sees the
user's IP but still sees **our app's identity on every query** — and can aggregate all our
users' addresses under one key. Worse, a per-app key partially deanonymizes: "this Tor exit
query came from a denar.ai user."

So the pattern is a **two-lane config**:

- **Normal lane** (default today): Alchemy with key, browser or server, as now.
- **Anon lane** (once a real worker exists): keyless, CORS-open endpoints
  (`ethereum-rpc.publicnode.com`, `eth.drpc.org`, `1rpc.io/eth`, `cloudflare-eth.com` — the
  demo probes exactly this list) reached *only* through the worker. The reliability argument
  against public RPCs is also weaker here: Tor already adds latency/failure, the lane is for
  privacy-sensitive reads, and no key means nothing to leak or rate-limit-attribute.
- The **bootstrap read** (specifier `eth_call`) is observable either way — spec acknowledges
  this chicken-egg. Fine to do via Alchemy; it reveals "this IP runs an anon-rpc app," not
  which addresses the user cares about.

## Product-by-product integration sketches

### slop-computer-live — do the relay routing now, anon-rpc later

Highest leverage, lowest effort, and it doesn't need anon-rpc at all yet: the relay already
proxies portfolio and gas *specifically* to keep per-client Alchemy calls away — the
personal-wallet wagmi reads just never got routed through it. Moving
`usePersonalWallet`'s reads (multisig lookup, balance, bytecode) behind a relay endpoint
(pattern already exists at `WalletWindow.tsx:207`) closes the "(guest IP → passkey wallet)"
leak with plumbing that's already there. Then anon-rpc becomes the *next* rung on the
cypherpunkPlan ladder: the relay is still a trusted party; a tor-js worker makes even us
unable to link guests' reads. The two-tier design means live can adopt per-surface — keep
relay reads for show-critical latency, anon lane for wallet reads.

### punk-wallet — the strongest philosophical fit, the most work

A burner wallet whose browser holds the key is *exactly* anon-rpc's target user; today it's
our worst leak. But it's ethers v5 (no viem transports), so the seam is a provider subclass
overriding `send(method, params)` to go through `worker.fetch` instead of
`StaticJsonRpcProvider`'s fetch, constructed where `App.jsx:159-165` builds providers.
Doable (~a day), but I'd wait for the tor-js worker — a passthrough buys punk-wallet
nothing, and the multi-chain matrix (~20 networks) multiplies the config work.

### denar.ai — smallest real-product pilot

Two moves: (1) push the remaining client-side ENS reads for the signed-in address into the
existing `app/api/*` proxy pattern (mirrors the live fix — no anon-rpc needed); (2) when
ready to pilot anon-rpc for real, this is the right app: single connected address per
session, already has a status-heavy UI where a "private mode" toggle with a boot pill fits,
and the read volume is modest. The transport above drops into its SE-2 wagmi config.

### slop-computer-wallet — the eventual flagship

A multisig UI is where "the RPC provider watches you check your treasury" bites hardest.
Same one-file transport swap; adopt after the tor-js worker ships and after piloting on
denar.ai. Bonus: the wallet's passkey-signer story + anon reads is a coherent
"cypherpunk multisig" pitch.

## Beyond RPC: two other things worth stealing

**KPS for the fleet relay.** Fleet browsers currently connect via `wss://h.atg.link` — DNS
subdomain, Let's Encrypt cert, nginx TLS termination. That's exactly the dependency KPS
deletes: a relay reachable at `ip:port:certhash` needs no domain, no CA, no cert renewal,
and can be respawned anywhere with a new address string. `@kpstreams/webrtc-client` (browser)
+ the Go/Rust server libs are usable standalone today, independent of anon-rpc's maturity.
Cost: the address becomes an opaque string (QR-code it), and WebRTC data channels replace
WebSockets (framing changes in `relay.py` + the browser client). Worth a spike if the
"disposable relay" property ever matters more than the nice URL.

**Hash-pinned client code for slop-circle.** The classic E2EE-web-app hole is "the server
serves you the JS that holds your keys — so the server can serve you a backdoored build."
anon-rpc's delivery pattern (on-chain keccak pin → fetch bundle from anywhere → verify →
run) is a general answer, and slop-circle ("self-hostable E2EE video circles around a
multisig") is precisely the app whose crypto core deserves it. The multisig itself could be
the specifier: signers vote to bless a new client-bundle hash.

## Publishing our own specifier (the first-mover option)

Deploying a specifier is trivial (`WorkerSpecifier.sol` is ~a page; owner-updatable with
`renounceOwnership()`), and the reference repo's bundle-hosting trick — a GitHub branch
named after the hash — costs nothing. Two workers we could publish:

1. **A tor-js worker.** The e2e in `tor-js/test/anon-rpc-worker` already works against a
   live gateway; nobody has published it on-chain yet. Being the first real (non-passthrough)
   specifier on mainnet is a cheap, visible contribution — and forces us to run/find a KPS
   gateway, which is the honest cost of the whole stack (gateway economics are the unsolved
   part; a $5 VPS carries a demo, not a product).
2. **A "relay worker"** for slop-computer-live: a worker that routes reads to our relay over
   KPS instead of Tor — no anonymity from *us*, but hash-pinned client code + no Alchemy
   exposure + domainless transport. A stepping stone that exercises every layer we'd need.

Keep any specifier we deploy **owner-held, not renounced**, while the spec is Draft —
renouncing pins users to a bundle that a breaking spec rev will strand.

## Phased plan

**Now (independent of anon-rpc maturity):**
1. `prototype/` spike in this repo — harness + viem transport against the mainnet
   passthrough specifier, reading real slop.computer state (episodes registry + a balance).
   Proves the plumbing end to end. *(Built — see `prototype/README.md`.)* The companion
   `prototype/tor-spike.mjs` proves the anonymity half: tor-js in Node, Ethereum reads
   exiting through a real Tor node (18 s bootstrap, ~650 ms/read, keyless RPC). *(Built.)*
2. slop-computer-live: route `usePersonalWallet` reads through the relay; split server-only
   `ALCHEMY_API_KEY` from the `NEXT_PUBLIC_` one.
3. denar.ai: move signed-in-address ENS reads server-side.

**On trigger (a tor-js worker published on-chain — the watch item in memory):**
4. Pilot the anon lane in denar.ai behind a "private mode" toggle (keyless endpoints, boot
   pill, lazy boot).
5. Then slop-computer-wallet, then punk-wallet (ethers v5 provider subclass).

**Later / opportunistic:**
6. Publish our own specifier (tor-js worker or relay-worker).
7. KPS spike for a domainless fleet relay; hash-pinned client bundle for slop-circle.
