# Gas Killer client API — safety review

Reviewed 2026-07-31, ahead of the slop computer interview. Subject:
[`CLIENT-API.md`](CLIENT-API.md) plus live checks against the deployment.

## Verdict: safe to use and safe to build the interview around

## Live verification (2026-07-31)

Checked the three unauthenticated endpoints with `curl` (custom UA, no keys):

| Check | Doc claimed | Observed |
|---|---|---|
| `GET /healthz` | 200 | **200** |
| `GET /bridge/healthz` | `{"ok": true, "asks": 13}` | `{"ok": true, "asks": 14}` |
| `GET /forkhead` | `11389815` | `11390187` (advanced, as expected) |

The doc matches the live deployment — it's current, not stale marketing.

## Why it's fundamentally low-risk

- **No private keys anywhere in the flow.** `from_address` on `/trigger` is explicitly
  a *simulated* caller — no signature is ever made with it, and neither path asks the
  client to sign anything or expose a wallet. The operator quorum lands the settlement
  transaction itself. There is no way to leak a key through this API because it never
  wants one.
- **Testnet only** (Sepolia, chain 11155111). No real funds anywhere.
- **No secrets in the doc.** The `gk_live_…` key is a placeholder; addresses are public
  contracts; the 64-hex strings are event topics / roots / manifests, not keys. Safe to
  commit (this review and the doc are in the repo on that basis).
- **No embedded-instruction / prompt-injection content** — scanned with that lens since
  it's a third-party doc; it's a straight API reference.
- The one authenticated endpoint (`/trigger`) is correctly server-side-only: it's not
  CORS-enabled, so a `gk_` key can't casually end up in browser code, and the doc says
  keys are hashed at rest.

## Flags (none blocking)

1. **Cloudflare fallback relay** (`gk-router-proxy.ronturetzky.workers.dev`): any
   Path B call through it sends the `Authorization: Bearer gk_…` header through a
   workers.dev script controlled by whoever owns that worker (presumably Ron from the
   team, but it's a personal account, not the project domain). **Rule: primary URL only
   for anything carrying a key**; the relay is fine for keyless Path A calls.
2. **The doc's on-chain verification examples use public RPCs** (`sepolia.drpc.org`).
   Their choice for a public doc; per our own RPC rules, when *we* verify answers
   on-chain we use the Alchemy Sepolia endpoint instead.
3. **Trust model is honestly stated but not trustless** (§3.5 of the doc): this is
   committee-trust — staked operators, k=2 per segment, full-quorum chain verification —
   with no VRF sortition (a malicious coordinator could grind committee assignments),
   no fraud proofs, no slashing economics yet. The doc says so itself, which is to its
   credit.
4. **Naming vs reality: there are no ZK proofs in the current system.** Despite the
   "zk proof project" first impression, the mechanism is staked-committee re-execution
   with BLS-aggregated signatures (an EigenLayer AVS). The commitment chain is *sized
   for* future one-shot fraud proofs but none are wired up. Best interview thread —
   see [`INTERVIEW-NOTES.md`](INTERVIEW-NOTES.md).

## Minor observations

- `/bridge/ask` is unauthenticated with `Access-Control-Allow-Origin: *` — anyone on
  the internet can burn their compute (bounded by the one-ask-per-model gate). Their
  exposure, not ours.
- The "send a real User-Agent" requirement is a WAF blocking default `Python-urllib/*`,
  not evasion of anything — normal bot hygiene.
- Ask state is in-memory on the bridge (restart forgets everything); the chain is the
  real source of truth via `stateTransitionCount()` and the `ChatAnswered` event. Good
  design honesty; clients must persist their own `ask_id`s.
