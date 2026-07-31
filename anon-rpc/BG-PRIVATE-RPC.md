# BuidlGuidl Private RPC — Tor-on-bgclient, and paying for it anonymously

*Design exploration, 2026-07-30. Follows the [anon-rpc research](README.md) and
[integration plan](INTEGRATION.md). This is the "what if BuidlGuidl actually built the
missing half of the EF's private-reads stack" doc — an architecture sketch + a survey of
ways to charge for it without deanonymizing the payer. Nothing here is committed product;
it's a thinking document with buildable next steps.*

## The thesis in one paragraph

BuidlGuidl already runs the two things the EF's anon-rpc stack is missing: a fleet of
volunteer Ethereum nodes ([client.buidlguidl.com](https://client.buidlguidl.com/)) and a
network that routes RPC calls *to* those nodes even behind home NAT
([rpc.buidlguidl.com](https://rpc.buidlguidl.com/) → `mainnet.rpc.buidlguidl.com`). The
EF built the standard (anon-rpc), the courier (tor-js = Arti/Tor in WASM), and the domainless
transport (KPS) — but openly admits it has no anonymity network deployed and no incentive
layer for the gateways that anonymous browsers need. **If every bgclient also ran Tor and
served reads as an onion service, BuidlGuidl would become both the front door and the back
door of private reads on Ethereum** — and a small anonymous-payment layer could make running
a node pay for itself.

## Why this fits BuidlGuidl specifically

Two gaps the anon-rpc research flagged as *unsolved*:

1. **Gateway economics.** Browsers can't reach Tor relays directly; they need volunteer
   "gateway" bridges. The EF hand-waves "incentivized variants." BG has the machines.
2. **A keyless, Tor-friendly endpoint.** The anon lane can't use `alchemy.com/v2/<key>` — the
   key re-identifies the app through Tor (the "API-key trap" in INTEGRATION.md). BG RPC is
   **already keyless**, mission-aligned, and won't block Tor traffic like a commercial
   provider would.

**Verified today (no new software):** the tor-js spike pointed at `mainnet.rpc.buidlguidl.com`
returns mainnet state through a real Tor exit —

```
tor bootstrap: 1.7s
via tor: {"IsTor":true,"IP":"107.189.10.175"}
eth via tor → mainnet.rpc.buidlguidl.com: chainId=1 block=25650450 beacon=88933045 ETH (3 reads in 3.3s)
PASS
```

So the floor already works. The rest of this doc is about climbing from "works over the public
exit" to "Tor all the way to the node, no exit, operator anonymous too, and paid for."

## The core idea: bgclient + Tor + onion service

Today bgclient serves an RPC port and the rpc.buidlguidl.com router does clever websocket
tunnelling to reach it behind NAT. Replace that with an **onion service on each node**:

```
wallet (tor-js worker) ──3 hops──▶ rendezvous ◀──3 hops── bgclient onion service ──▶ local geth/reth
```

What each party sees:

| Party | Sees |
|-------|------|
| Wallet's ISP / local censor | encrypted Tor traffic to a guard; not the destination, not the query |
| Tor relays | encrypted cells; no endpoints |
| **Node operator** | the query content (`eth_call` for address X) — but **never the user's IP or identity** |
| **The user** | never learns the node operator's IP either — onion services hide the server |

### Why onion service, not just "Tor to the public endpoint"

This is the load-bearing insight — running Tor *on the node* is strictly better than users
Tor-ing to `mainnet.rpc.buidlguidl.com`, for four compounding reasons:

1. **It replaces the websocket-relay NAT hack.** Onion services are outbound-only: the node
   dials into Tor and publishes a rendezvous point, reachable from anywhere with **no port
   forward, no public IP, no relay server in the middle.** Tor is the most battle-tested NAT
   traversal on earth; it subsumes the exact problem rpc.buidlguidl.com was built to solve.
2. **The operator gets privacy too.** Exposing a home node publicly today leaks a residential
   IP — "this address in Denver runs an Ethereum node" advertises a likely crypto holder at a
   street address. Behind an onion service the operator's IP is hidden from users. **Mutual
   anonymity** — a recruiting *feature* for running a node, not a cost.
3. **No exit nodes anywhere.** Traffic never leaves the Tor network (the destination is inside
   it), so you don't burn Tor's scarcest, most-congested, sometimes-hostile resource, and no
   exit can see or tamper with anything.
4. **Onion addresses are self-authenticating.** A v3 `.onion` *is* the hash of the service's
   ed25519 public key — same philosophy as KPS's `ip:port:certhash` and anon-rpc's
   `workerHash()`. No CA, no DNS, no impersonation without the key. A signed list of node
   onions is all the "registry" you need.

### The browser gap (where this meets anon-rpc)

Native apps and Node dial onions today with stock `tor`/Arti. Browsers can't — and here the
two ideas lock together:

- **tor-js can't dial `.onion` yet.** Arti upstream has onion-client support; tor-js doesn't
  expose it (checked — no `onion`/HSDir surface in its public API). This is a concrete,
  well-scoped upstream contribution, and Morris has an open "what do you need?" issue.
- **Browsers still need a KPS gateway** to enter Tor at all. A bgclient could run the small
  `tor-js-gateway` crate alongside its node — so **BG machines are the entry bridges *and*
  the onion endpoints.** Gateways only relay encrypted Tor cells (can't see queries or
  destinations), so it's low-liability, nothing like an exit.

Full vision: *bgclient ships {node + tor onion service + tor-js-gateway}; wallet runs the
hash-pinned tor-js worker configured with BG gateways; a request enters Tor through one
volunteer node and terminates at another node's onion.* BuidlGuidl on both ends, EF standard
in the middle, no third party anywhere.

## Discovery & load balancing (the job the router does today)

The one function that can't just vanish is "which node do I talk to, and spread the load."
Options, increasing decentralization:

- **(a) Directory-only rpc.buidlguidl.com.** It stops proxying traffic and just hands out a
  signed list of node onion addresses. It learns *who asks for the list* (mitigable — fetch
  over Tor too), never *what they query*. Big trust reduction from today with almost no work.
- **(b) OnionBalance.** Tor's built-in HS front: one canonical `buidlguidl….onion` whose
  descriptor points at N backend node instances; Tor spreads load transparently. Wallets
  configure a single stable address — exactly the UX of today's single URL. **Recommended
  starting point.**
- **(c) On-chain node registry.** The node list (onion + stake + reputation) lives in a
  contract — which rhymes perfectly with the anon-rpc specifier pattern and sets up the
  payment layer below.

## Honest problems (the design must answer these)

- **Query content is still visible to the answering node.** Tor hides *who*; it doesn't hide
  *what*. A node operator can log "someone watches address X." Unlinkable to a person, but not
  invisible. Mitigations: (1) spreading queries across many mom-and-pop nodes beats one Alchemy
  seeing everything; (2) the real fix is **PIR** — see next section.
- **Circuit-level linkability.** Queries sharing a Tor circuit are linkable *to each other* as
  a session even if not to a person. Need to check tor-js's circuit-rotation policy and
  possibly force fresh circuits per query-batch.
- **Abuse / DoS without IP rate-limiting.** Anonymous traffic means no per-IP throttle, and
  Cloudflare-ing the endpoint would defeat the whole point. Onion services have **built-in
  proof-of-work DoS defense** (tor ≥ 0.4.8) — tailor-made here. The payment layer below is
  also an abuse control: pay-per-request *is* rate limiting.
- **Response integrity.** Anonymous users have no account and no recourse, so a lying node is
  harder to hold accountable. A **Helios-style light-client verification** on top (verify state
  proofs against a trusted block hash) would make reads trust-minimized end to end — a very
  BuidlGuidl-shaped addition.
- **Latency.** ~0.7–1.1s per read through Tor, a few seconds for first onion connection. Fine
  for wallet balance/state polling (the actual use case); wrong for trading UIs.

## Chapter two: + PIR (content privacy)

PIR (Private Information Retrieval) is the complement to Tor: it lets a node answer
`eth_getBalance(X)` **without learning which address X was** — via homomorphic encryption
(you send an encrypted index, the server computes over the whole DB blindfolded, only you
decrypt) or a two-non-colluding-server XOR trick. Its intrinsic cost: the server must touch
*every* record per query (else which records it touched would leak the query), so it scales
with DB size — brutal for hundreds of GB of Ethereum state. Hence the EF Reads team's two PIR
projects: **GPU-accelerated PIR** and batch-PIR **"Skirrt"** (amortize across many queries).
Research-stage, not `npm install`-able.

So "BG + PIR" is the endgame, not the launch: chapter one is Tor-on-bgclient (hides *who*);
chapter two is BG nodes additionally running PIR server software when it matures (hides
*what*) — at which point a wallet read is private in both dimensions, nobody knows who asked
*and* not even the answering node knows what was asked. BG's volunteer fleet is a natural host:
PIR needs many independent, mission-aligned servers willing to burn compute for privacy.
*(A dedicated GPU-PIR / Skirrt maturity deep-dive is a good follow-up — same treatment as
anon-rpc.)*

## Paying for it — anonymously

Austin's framing: users **pay (possibly with shielded ETH) for access**, then **per RPC
request they attach something** the serving node can later **redeem for payment** — and the
payment must not be linkable to the requests (so zk / blind signatures, not "sign with your
funded address"). This is a real, well-studied problem shape; the naive version fails and the
good versions have names.

### Why the naive version fails

"Sign each request with your wallet key so we know you paid" links every request to your
funding address and IP-anonymity is pointless. "Give paying users a shared bearer token"
means one token = infinite use and no per-request metering. The requirement is a credential
that is (1) **issued only to payers**, (2) **unlinkable** to the payment and to other uses,
and (3) **rate-limited / spent** so N payment buys N (or N-per-epoch) requests, with a
**double-spend (nullifier) story**. That's exactly what blind signatures and zk-membership
schemes provide.

### The landscape verdict

**Both halves you need are mature in 2026 — nobody has wired them together for ETH RPC.**
Shielded-ETH funding rails are live and unlinkable per-request credentials are shipped
(Nym) or standardized (Privacy Pass) — but the only project that ever shipped "paid private
RPC," **HOPR RPCh**, is marked *development paused* (dead). The EF mentions incentives for
private reads exactly once, as a **"2027+, explore micropayments" bullet** with no spec; the
EthSystems private-reads RFP and the anon-rpc repo have zero economics. **The niche is
genuinely open** — which is the opportunity.

Every viable design is the same three-part sandwich:

```
shielded-ETH deposit  →  blind / threshold CREDENTIAL  →  batched Merkle-claim redemption
   (Railgun today)        (one unlinkable spend/request)     (server settles sublinearly)
```

The middle piece is the real decision. Three mechanism families, in order of fit:

### 1. Threshold e-cash (Coconut / compact-ecash, à la Nym) — best fit, only shipped end-to-end blueprint

Pay from shielded ETH into an Ethereum deposit contract → a **t-of-n set of node operators
blind-issues a "ticketbook"** (Nym's shape: deposit → book of ~50 tickets, derived offline
on-device) → spend one **unlinkable, re-randomized ticket per RPC request** over Tor → servers
batch the revealed **serial numbers** and get **paid pro-rata from the pool**. Every show is
unlinkable to issuance and to other shows.

- **Why it wins for *our* topology:** it has **offline double-spend detection** — each spend
  reveals a serial (caught at redemption) *and* a double-spending tag whose algebra recovers
  the cheater's key. That is precisely what lets a **multi-server** network work **without a
  shared online nullifier log** — the single hardest problem in a fleet of independent BG
  nodes, solved natively. RLN and plain Privacy Pass can't do this.
- **Shipped:** Nym's NymVPN runs exactly this loop in production (accountless pay-as-you-go
  since April 2026: deposit tokens → threshold zk-nym → spend at gateway → operators redeemed
  from pool). The `nym-compact-ecash` crates are Apache-licensed and chain-agnostic.
- **Fast:** ~35 ms algebraic verify per ticket (3–10× faster than a Groth16 nullifier proof),
  credential is a few group elements.
- **Tradeoff:** you must stand up a **t-of-n issuer quorum with DKG** — real operational
  complexity and a threshold-collusion trust assumption (a colluding quorum could inflate).
  On-chain verify needs BLS12-381 pairings — feasible post-**EIP-2537 (Pectra)**, but you'd
  batch/optimistically redeem to avoid per-ticket on-chain cost.

### 2. Chaumian ecash (Cashu-style BDHKE) — simplest, fastest, with a *live* pay-per-request precedent

Single mint blind-signs tokens (secp256k1 BDHKE, ~100 µs/sig, token fits an HTTP header); the
**token *is* the money**, so node redemption and global double-spend come for free (mint keeps
a spent-secret list). The pay-per-request-over-402 flow **already runs in production** on the
Cashu side — **Routstr** is a reverse proxy selling anonymous pay-per-call AI inference with a
`X-Cashu` header + change in `X-Cashu-Refund`; architecturally identical to pay-per-RPC.

- **Tradeoff:** a **single custodial mint that can rug or silently inflate the float** (DLEQ
  proves a note is genuine, not that the mint is solvent). And **no ETH-backed mint exists** —
  Cashu is Lightning/BTC today; you'd build the ETH-backed BDHKE mint (~500 lines of crypto;
  the custody/backing is the hard part). Federate it (Fedimint-style t-of-n) to reduce rug
  risk — at which point it converges toward option 1.
- **Verdict:** the fastest way to a *working demo*; the mint-trust is the thing to design out.

### 3. Privacy Pass (batched Blind-RSA) + Pocket-style claim back-end — most standards-mature, you build the money layer

Publicly-verifiable blind-RSA tokens: pay-gated issuance (**Kagi already does exactly this** —
subscribers get 3,000 unlinkable tokens/month, works over their Tor onion), node verifies
**offline** with the public key, later settles its collected `{nonce, authenticator}` set
against a paymaster who counts-without-linking. Batched-issuance draft is **at IESG** (~113-byte
tokens); the **ACT** draft even carries a hidden prepaid *balance* decremented per use ("for
privately accessing web APIs such as AI models" — almost our exact phrasing).

- **Prior art for the redemption half:** **Pocket Network** already runs industrial-grade
  "server redeems evidence of served relays" — a Sparse Merkle Sum Trie of signed
  request/response digests, commit-a-claim then reveal-a-probabilistic-proof, sublinear in
  request count, ~13.5B relays/month. **But Pocket/Lava have zero requester privacy** (every
  relay is signed by the app/consumer key). The novel move: **swap the app-signature-per-relay
  for an unlinkable one-show credential**, so the SMST commits credential nullifiers instead of
  identities. Nobody has done this swap.
- **Tradeoff:** Privacy Pass gives **authorization, not value** — you bolt on the whole
  settlement + cross-node double-spend layer yourself, and doing so **essentially re-derives
  ecash**, which is why 1–2 are more direct.

### What the other schemes contribute (and why they're not the core)

- **Semaphore + RLN (Waku's rate-limiter).** Deposit-to-join a Merkle group, per-request zk
  proof + epoch nullifier, **over-use *slashes your stake*** by Shamir-revealing your key.
  ~150 ms/proof (zerokit). But it meters **per-epoch, not cumulatively**, the deposit is a
  *slashable bond not a spendable balance* (slashing punishes spam, never *pays* the server),
  and cross-server double-claim needs a shared log. Make it pay-per-request and **you've
  re-derived threshold ecash.** Keep only its **slashing trick** as a spam belt-and-suspenders
  on top of option 1/2. (Also honesty flag: Waku's economic membership has been "nearly
  mainnet" for ~2 years — still testnet.)
- **Orchid probabilistic nanopayments.** Lottery-ticket micropayments (EV = price; only rare
  winners touch chain) solve **gas-per-request**, not unlinkability — the funder wallet is
  visible on-chain and all tickets from one pot are linkable to each other. Project is in
  **maintenance mode** (no protocol work since ~2022). A later gas-amortization optimization,
  not a v1.
- **x402 (Coinbase HTTP 402).** Now a **Linux Foundation** standard (April 2026, USDC over
  Base, gasless via EIP-3009) — but **no privacy in the core** (every payment links
  payer→recipient publicly). The interesting bit: **`brave-experiments/private-x402-gateway`**
  is a working PoC where **x402 buys a batch of Privacy Pass tokens** spent one-per-request
  over an OHTTP relay — x402 as the *funding front-end*, blind tokens as the per-request layer.
  Exactly our option 3, with x402 as the deposit leg.

### Funding the anonymous side (shielded ETH) — verified rails

For payment ⊥ identity to mean anything, the **deposit itself** must not link to the payer's
mainnet identity. Live options, 2026:

- **Railgun** — the workhorse. On **Ethereum mainnet** (+L2s), ~$95–108M TVL, shield→`0zk`,
  unshield to *any* fresh 0x via a Broadcaster, compliance via **Private Proofs of Innocence**.
  **Strongest live option** — real liquidity + arbitrary-recipient payout. Fund the deposit
  contract / mint from the shielded side.
- **Privacy Pools (0xbow)** — mainnet since March 2025, **Association-Set** compliance (screened
  deposits, withdraw to fresh address, ragequit if rejected). Cleanest regulatory story, but
  small caps (0.1–1 ETH) and small anonymity sets today. Best if compliance optics matter.
- **Aztec** — Ignition mainnet Nov 2025, Alpha v5 (July 2026) does **client-side proving on
  phones** + **private fee payment via Fee-Paying Contracts** (pay fees privately in arbitrary
  assets — directly our shape). **Best forward substrate** (the credential issuer could *be* an
  Aztec contract), youngest liquidity.
- Avoid Tornado-style no-screening rails — withdrawals still get heuristically flagged.

The pattern for all three credential families: **shield ETH → fund the mint/pool/deposit from
the shielded side → the buyer's clearnet identity never touches the access credential.** The
credential is what the node redeems; the shielded rail is what keeps "who paid" unknowable.

### Recommended path

For BuidlGuidl's actual topology — a fleet of *independent* volunteer nodes, no natural
central operator — **threshold e-cash (option 1) is the principled target** because offline,
multi-server double-spend detection is exactly the fleet problem, and Nym proved the whole
loop ships. But **start with a Cashu-style single mint (option 2) for the v1 demo**: it's
~500 lines, has a production 402 precedent to copy (Routstr), and lets you prove the
*end-to-end UX* (shielded deposit → blind token → Tor request → node redeems) before taking
on DKG. The migration mint→federation→threshold-quorum is a natural hardening path, not a
rewrite. Bolt RLN-style slashing on top only if spam proves to be a problem.

## Build ladder (each rung independently shippable)

- **v0 — today.** tor-js users point at `mainnet.rpc.buidlguidl.com`. Proven. Hides user IP,
  costs nothing, no code. *(Done.)*
- **v1 — onion service on one node.** Install `tor`; `HiddenServiceDir` + `HiddenServicePort
  80 127.0.0.1:8545` behind a **read-only JSON-RPC method allowlist proxy** (bgclient
  conceptually already gates methods for the router). Query it through Tor from another box.
  *Whole concept proven end to end — an afternoon.*
- **v2 — bake into bgclient.** Opt-in flag bundles tor (or Arti), prints the node's `.onion`
  at startup, registers with the directory. Operators opt into mutual anonymity.
- **v3 — OnionBalance front.** One canonical `buidlguidl….onion` over N nodes; rpc.buidlguidl.com
  demotes from proxy to signed directory.
- **v4 — browser path.** Contribute `.onion` dialing to tor-js (or run tor-js-gateway on
  nodes); publish an on-chain **anon-rpc specifier** = "the BuidlGuidl worker" (tor-js +
  BG gateway set + BG onion). Would be the **first non-passthrough worker on the EF standard.**
- **v5 — payments.** Add the anonymous credential layer: shielded deposit (Railgun) → blind
  token → one token per request over Tor → node redeems. **Start with a Cashu-style single
  mint** (copy the Routstr 402 pattern, ~500 lines) to prove the UX; **migrate toward
  threshold e-cash** (Nym's compact-ecash shape) for real multi-node settlement without a
  shared online log. Payment doubles as the abuse/rate-limit control.
- **vN — PIR.** When GPU-PIR/Skirrt matures, BG nodes run PIR servers: private *what* on top
  of private *who*.

**Recommended first move:** v1 on Austin's own node tonight (concrete demo for the BG crew),
in parallel file the tor-js onion issue. Walking into a conversation with Andrew Morris
holding "hundreds of volunteer machines to be your gateways *and* onion endpoints" is the
answer to the gap the EF's own docs admit is unsolved.

**The cautionary prior art:** **HOPR RPCh** (2023) was literally "the first private RPC
provider" — mixnet-relayed RPC, node-runners paid in HOPR — and its repo now reads
*"development paused."* Private RPC + payments has been built once and didn't sustain. The
lesson isn't "don't" — it's that the *distribution/adoption* problem outweighs the crypto.
BuidlGuidl's edge over HOPR is that it already **has the node fleet and the users**; the
mistake to avoid is over-investing in the payment cryptography before proving anyone routes
reads through it for free (v0–v3). Payments (v5) should follow demonstrated usage, not precede
it.

## Open questions

- tor-js circuit rotation policy — per-request fresh circuits to kill session linkability?
- Does the JSON-RPC method allowlist need to change for anonymous callers (block
  `eth_sendRawTransaction`? or allow it — anonymous *broadcast* is also valuable)?
- Payment: mint-trust (fast) vs zk-pool (trustless) — pick per the research synthesis.
- Response integrity: bundle a Helios-style verifier in the worker so anonymous ≠ trust-me?
- Legal posture of running onion RPC endpoints on volunteer home machines (reads only, no
  exit traffic — should be low, but document it for operators).
