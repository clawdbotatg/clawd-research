# Gas Killer — LLM Service API

> Received from the Gas Killer team 2026-07-31, reproduced verbatim.
> Our review of this doc: [`SAFETY-REVIEW.md`](SAFETY-REVIEW.md).

**Client integration guide.** Everything you need to create tasks against the live
deployment, plus the architectural context to reason about what happens after you do.

- **Base URL:** `https://testnet.gaskiller.xyz`
- **Settlement chain:** Ethereum Sepolia (chain id `11155111`)
- **Status:** verified live 2026-07-31. `/healthz` 200 · `/bridge/healthz` ok ·
  fork head `11389815` · 0.6B `stateTransitionCount` = 33 · 35B = 3
- **Scope:** this is a testnet demo deployment. Contracts and settled history are
  permanent; the compute environment is not, and can be taken down between sessions.
  Check `/healthz` before assuming availability.

Part 1 is the overview. Part 2 is the API reference you integrate against. Part 3 is the
technical appendix — architecture, trust model, and the constraints that explain why the
API looks the way it does.

---

# Part 1 — Overview

## What this is

Gas Killer is a verifiable off-chain compute service for EVM smart contracts, built as an
EigenLayer AVS. A contract call that would cost far more gas than a block can hold is
executed off-chain by a committee of staked operator nodes, which agree byte-exactly on
the resulting state diff, BLS-aggregate their signatures, and land **one** transaction
on-chain that applies it.

The flagship demonstration is a language model. The transformer forward pass is written
in pure, integer-only Solidity. Running it is a real EVM execution — just an enormous one:
about 545 billion gas of simulated compute for a Qwen3-0.6B answer, and about 3.6 trillion
for Qwen3.5-35B-A3B. The quorum executes it, agrees on the output tokens, and settles the
answer in a single ~384,000 gas transaction.

Three properties matter for anyone building on this:

1. **The output is reproducible.** Greedy decoding at temperature 0, integer arithmetic
   throughout. The on-chain event carries raw token ids, and those ids match the
   Python/HuggingFace reference token-for-token.
2. **Agreement is the security.** Operators do not trust the coordinator or each other.
   Each verifies the commitment chain and its own executed work before signing, and one
   dissent starves the quorum.
3. **Settlement is one transaction.** No multi-step protocol, no on-chain replay of the
   computation. One `verifyAndUpdate` call carrying a BLS-verified state diff.

## The two ways to create a task

| | Path A — ask the model | Path B — settle your own call |
|---|---|---|
| Endpoint | `POST /bridge/ask` | `POST /trigger` |
| Auth | none | `Authorization: Bearer gk_…` |
| You supply | token ids + response length | a target contract and its calldata |
| Runs | sharded LLM inference, then settles | one settlement round |
| Use it for | experimenting with on-chain inference | pointing the quorum at your own contract |

**These paths do not mix, and this is the most common misunderstanding.** You cannot use
`POST /trigger` to hand-craft a `fulfil()` call against the demo LLM consumers. The
operator validator gate refuses to sign a `fulfil` round unless the `pipelineRoot` in your
calldata corresponds to an inference the committee actually ran and can re-verify segment
by segment. A fabricated root produces a round that never reaches quorum — no error, just
no settlement. Inference is reachable only through `POST /bridge/ask`; the coordinator
endpoint that drives it (`POST /shard/infer`) is bound to the router's internal port and
is never exposed publicly.

Use Path A to work with the models. Use Path B to work with your own contracts.

---

# Part 2 — API reference

## 2.0 Common

**Base URL:** `https://testnet.gaskiller.xyz`

A Cloudflare relay exists at `https://gk-router-proxy.ronturetzky.workers.dev` for
networks that TLS-intercept the load balancer IP. Same paths. Use it only as a fallback if
the primary base URL fails to connect.

**Health and identity — no auth:**

| Endpoint | Returns |
|---|---|
| `GET /healthz` | `200` with an empty body when the router is up |
| `GET /bridge/healthz` | `{"ok": true, "asks": 13}` — bridge liveness and asks seen since restart |
| `GET /forkhead` | `{"forkHead": 11389815}` — the simulation fork's head block (you need this for Path B) |
| `GET /avs-metadata` | AVS identity JSON served for the EigenLayer indexer |

**CORS:** `/bridge/*` sends `Access-Control-Allow-Origin: *` and allows `POST, GET,
OPTIONS` with `Authorization` and `Content-Type`, so Path A is callable directly from a
browser. `/trigger` is not CORS-enabled — call it server-side, which is correct anyway
since it takes your API key.

**User-Agent:** send a real one. The ingress WAF returns `403` for the default
`Python-urllib/*` UA, deterministically. Any identifiable string works
(`User-Agent: acme-integration/1`).

**Rate limits:** none are enforced per key. Concurrency is bounded differently — see
§2.5.

## 2.1 Path A — `POST /bridge/ask`

Runs one sharded inference and settles the answer on Sepolia. Returns immediately with an
id; the work continues server-side.

### Request

```http
POST /bridge/ask HTTP/1.1
Host: testnet.gaskiller.xyz
Content-Type: application/json
User-Agent: acme-integration/1
```

```json
{
  "model": "qwen",
  "prompt_ids": [151644, 872, 198, 3838, 374, 34953, 30, 151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271],
  "max_new": 8
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `model` | string | yes | `"qwen"` (Qwen3-0.6B) or `"qwen35"` (Qwen3.5-35B-A3B) |
| `prompt_ids` | int[] | yes | Token ids, already chat-templated. See §2.2 |
| `max_new` | int | no, default `8` | Tokens to generate. Per-model cap in §2.3 |

### Response

```json
{ "ask_id": "9f3c1a20b4de7c15" }
```

`200` means accepted, not complete. Poll for the outcome.

### Polling

```http
GET /bridge/ask/9f3c1a20b4de7c15
```

The response is a snapshot that grows as the ask progresses:

```json
{
  "state": "inferring",
  "model": "qwen",
  "prompt_ids": [151644, 872, 198, "…"],
  "max_new": 8,
  "started": 1785500000.0,
  "segments_done": 31,
  "segments_total": 48,
  "infer_elapsed_ms": 84210
}
```

Terminal success looks like:

```json
{
  "state": "done",
  "model": "qwen",
  "answer_ids": [151667, 271, 34953, 374, "…"],
  "pipeline_root": "0x3efb4704…",
  "infer_seconds": 118.4,
  "transition_index": 33,
  "settle_submitted": true,
  "total_seconds": 176.2
}
```

**States:**

| State | Meaning |
|---|---|
| `queued` | accepted, worker thread not yet started |
| `inferring` | segments executing across the operator committee |
| `settling` | answer known; settlement round submitted to the quorum |
| `done` | settlement round submitted successfully |
| `error` | failed; `error` field carries the reason, truncated to 500 chars |

Two things to know about `done`:

- `done` means the settlement task was **accepted by the router**, not that the
  transaction is mined. The ground truth for completion is on-chain: watch
  `stateTransitionCount()` on the consumer increment past the `transition_index` in the
  status payload (§2.4).
- `segments_done` / `segments_total` are merged in live from the coordinator on each poll
  and are best-effort — they may be absent. `segments_total` is the plan's upper bound;
  a run that hits a stop token finishes below it, so read the fraction as "of planned".

`GET /bridge/ask/<unknown-id>` returns `404` `{"error": "unknown ask_id"}`. Ask state is
in-memory: a bridge restart forgets every ask, so persist your own `ask_id` → outcome
mapping and fall back to the chain.

**Poll every 10–15 seconds.** Runs take minutes to over an hour (§2.5); polling faster
buys nothing and each poll fans out to the coordinator.

### Worked example

```bash
ASK=$(curl -s -X POST https://testnet.gaskiller.xyz/bridge/ask \
  -H 'Content-Type: application/json' \
  -A 'acme-integration/1' \
  -d '{"model":"qwen","prompt_ids":[151644,872,198,3838,374,34953,30,151645,198,151644,77091,198,151667,271,151668,271],"max_new":8}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["ask_id"])')

while true; do
  S=$(curl -s -A 'acme-integration/1' "https://testnet.gaskiller.xyz/bridge/ask/$ASK")
  echo "$S"
  echo "$S" | grep -qE '"state": *"(done|error)"' && break
  sleep 12
done
```

### Errors

All Path A errors are `{"error": "<message>"}`.

| Status | Message | Cause |
|---|---|---|
| `400` | `max_new must be 1..24` | above the model's cap (`1..8` for `qwen35`) |
| `400` | `prompt length must be 1..992` | prompt too long or empty (`1..56` for `qwen35`) |
| `400` | `prompt (N) + max_new (M) exceeds the model's sequence cap (1024)` | combined length over the KV budget |
| `400` | `token id out of vocab range` | an id is negative or ≥ the model's vocab size |
| `400` | `'llama'` | unrecognised `model` — the message is the rejected value, quoted |
| `429` | `another qwen ask is already running; try later` | one in-flight ask per model (§2.5) |
| `404` | `unknown ask_id` | wrong or forgotten id |

## 2.2 Building `prompt_ids`

The bridge takes token ids, not text. You tokenize, and you apply the chat template
yourself — nothing server-side wraps your prompt.

For **Qwen3-0.6B** (`model: "qwen"`), the template is:

```
<|im_start|>user\n{QUESTION}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
```

which as ids is:

```
[151644, 872, 198]  +  tokenize(QUESTION)  +  [151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271]
```

Tokenization is byte-level BPE with exact HuggingFace `tokenizers` parity — verified
30-for-30 token-for-token on the 0.6B. Use the model's `tokenizer.json`, published with
the weights in the `gas-killer/solidity-sdk` release `qwen3-0.6b-onchain-v1`. In a browser,
the reference implementation is `qwen-bpe.js` in the demo frontend
(`RonTuretzky/gaskiller-onchain-llm`).

**Qwen3.5-35B-A3B** (`model: "qwen35"`) uses a different vocabulary — its user-turn prefix
is `[248045, 846, 198]` and its stop ids are `248046` / `248044`. Take the rest of the
template from its own `tokenizer.json` (release `qwen3.5-35b-a3b-onchain-v1`); do not
reuse the 0.6B suffix ids.

Decoding the answer is the same tokenizer in reverse. `answer_ids` and the `ChatAnswered`
event carry raw ids; nothing on the server converts them back to text.

## 2.3 Model limits

| | `qwen` (Qwen3-0.6B) | `qwen35` (Qwen3.5-35B-A3B) |
|---|---|---|
| `max_new` | 1–24 | 1–8 |
| `prompt_ids` length | 1–992 | 1–56 |
| `prompt + max_new` | ≤ 1024 | ≤ 64 |
| Vocabulary (ids must be `< n`) | 151,936 | 248,320 |
| Layers | 28 | 40 |
| Settlement consumer | `0xd3f7F985F14f1942Fb09e5735e5499FEFF56E80b` | `0xfd0EF988216D0346BF115530387021c1b699336d` |
| Typical 8-token answer | ~4 min | ~72–75 min |

The 35B's tight prompt budget is a sequence-cap consequence, not a policy: its boundary
state is far larger per position, so the deployed configuration caps the sequence at 64.

## 2.4 Verifying an answer on-chain

The chain is the source of truth. Two reads:

**Has it settled?** `stateTransitionCount()` — selector `0xf4833e20`, returns `uint256`.
Compare against the `transition_index` from the ask status; settlement has landed when the
count exceeds it.

```bash
curl -s https://sepolia.drpc.org -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":1,"method":"eth_call",
  "params":[{"to":"0xd3f7F985F14f1942Fb09e5735e5499FEFF56E80b","data":"0xf4833e20"},"latest"]
}'
```

**What was the answer?** The `ChatAnswered` event:

```solidity
event ChatAnswered(
    uint256 indexed transitionIndex,
    bytes32 indexed newRoot,
    bytes32 indexed pipelineRoot,
    uint32[] promptIds,
    uint32[] answerIds
);
```

- `topic0` = `0x3d3288922fb750f4c301145bee4ae0c63a6229879e85c43079b8fb56fc81d187`
- Filter by `pipelineRoot` (topic 3) to find the log for a specific ask — the status
  payload gives you the root.
- Useful `fromBlock` when scanning history: `11256000` (0.6B), `11286700` (35B).

Note on RPC choice for log scans: publicnode returns `403` for deep `eth_getLogs` ranges
and for the default Python UA. drpc and tenderly serve these reliably.

## 2.5 Concurrency, latency, and load

**One in-flight ask per model.** The bridge admits a single `qwen` ask and a single
`qwen35` ask at a time; a second returns `429`. This keeps committee assignment
predictable. Serialize your asks and retry the `429` after a delay proportional to the
expected runtime, not after a second.

**Expected duration** (measured live, 8 tokens):

| Model | Inference | Settlement | End to end |
|---|---|---|---|
| `qwen` | ~2 min | ~1 min | **~4 min** |
| `qwen35` | ~71–74 min | ~1 min | **~72–75 min** |

Scale roughly linearly in `max_new`: about 20 s per token for the 0.6B, about 5.6 min per
token for the 35B, plus a fixed prefill.

**Cold start.** The first ask after any operator fleet restart takes an extra ~15–20
minutes while each node's execution daemon re-verifies the 34 GB weight overlay.
Subsequent asks run at normal speed. If your first ask looks stuck at `inferring`, this is
usually why — give it 30 minutes before treating it as failed.

**`/trigger` load shedding.** The router rejects with `503` `QUEUE_FULL` when its task
queue is at capacity, before doing any validation work. Back off and retry.

## 2.6 Path B — `POST /trigger`

Creates one settlement round: the operator quorum simulates your call against the target
contract, agrees on the resulting state diff, and lands it on-chain.

Use this to point the service at **your own** consumer contract. See §2.7 for what a
consumer must look like, and re-read the warning in Part 1 about not aiming this at the
demo LLM consumers.

### Auth

Your `gk_` key goes in a bearer header:

```http
Authorization: Bearer gk_live_xxxxxxxxxxxxxxxxxxxx
```

Verify it works with a deliberately invalid body — you should get a `400`-family
validation error rather than `401`:

```bash
curl -s -X POST https://testnet.gaskiller.xyz/trigger \
  -H "Authorization: Bearer $GK_KEY" \
  -H 'Content-Type: application/json' -A 'acme-integration/1' \
  -d '{"body":{"target_address":"0x0000000000000000000000000000000000000000","call_data":[1,2,3,4],"from_address":"0x0000000000000000000000000000000000000000","value":"0","block_height":1}}'
```

A missing or wrong key returns:

```json
{"error":{"code":"UNAUTHORIZED","message":"Unauthorized"}}
```

Keys are hashed at rest and cannot be recovered — if you lose it, ask for a new one. Keys
may carry an expiry.

### Request

```json
{
  "body": {
    "target_address": "0xYourConsumer",
    "call_data": [156, 152, 192, 110, 0, 0],
    "transition_index": "auto",
    "from_address": "0x6636A1CCBdf54485067304C1a590DE016DeaD9F0",
    "value": "0",
    "block_height": 11389815
  }
}
```

Note the single top-level `body` wrapper. Omitting it is the most common first mistake and
returns `422`.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `target_address` | address | yes | non-zero, and must have deployed code on L1 or L2 |
| `call_data` | **array of byte integers** | yes | 4–131,072 bytes. See the footgun below |
| `transition_index` | int \| `"auto"` \| `null` | no | omitted / `null` / `"auto"` all mean auto |
| `from_address` | address | yes | non-zero; the simulated caller only |
| `value` | uint256 as string | yes | `"0"` for a pure state-commit call |
| `block_height` | int | yes | non-zero, `≤` head, and within the staleness window |

### Three field-level footguns

**1. `call_data` is a JSON array of bytes, not a hex string.** `"0x9c98c06e…"` is
rejected. Encode the ABI call, then serialize the bytes as integers:

```python
list(calldata_bytes)          # Python  → [156, 152, 192, 110, …]
Array.from(bytes)             # JS      → [156, 152, 192, 110, …]
```

**2. `block_height` must be a block the operators' simulation can reach.** On this
deployment the operators simulate against a forked node that trails the live chain, so
pinning live head kills the round with "block don't exists" — no error at submission,
just silence. **Read `GET /forkhead` and use that value.** If `/forkhead` is unreachable,
live head minus 60 is the fallback the bridge itself uses.

The router validates the height two ways: it must not be ahead of the live head, and
`head - block_height` must not exceed the staleness window. The window is 300 blocks by
default; this deployment runs it at 50,000 to accommodate the fork's lag.

**3. `from_address` is a simulated caller, not a signer.** No signature is made with it
and you do not need its private key. It matters only if your consumer's logic inspects
`msg.sender`. Set it to whatever address your contract expects.

### `transition_index`

The consumer's state transition counter, used for optimistic concurrency.

- `"auto"` (or omitted, or `null`) — the server resolves the next available slot when it
  dequeues the task. Use this. It is what makes parallel submissions safe.
- An explicit integer — validated immediately against the contract's live
  `stateTransitionCount()`, and rejected with `TRANSITION_MISMATCH` on any difference. Use
  it only when you need to bind a task to one exact state.

Any other string is rejected at deserialization.

### Response

```json
{ "success": true, "message": "Task queued" }
```

`200` means queued for the quorum. **No task id is returned on this deployment**, and
there is no task status endpoint here — track the outcome on-chain via
`stateTransitionCount()` and your consumer's own events.

### Errors

Every `/trigger` error uses one envelope:

```json
{ "error": { "code": "STALE_BLOCK", "message": "block_height 11330000 is older than the staleness window (50000 blocks) relative to current chain height 11389815" } }
```

| Status | `code` | Cause |
|---|---|---|
| `401` | `UNAUTHORIZED` | missing, malformed, unknown, revoked, or expired key |
| `422` | `INVALID_REQUEST` | body does not deserialize — usually the missing `body` wrapper, or hex-string `call_data` |
| `400` | `INVALID_ADDRESS` | `target_address` or `from_address` is zero |
| `400` | `INVALID_REQUEST` | empty or <4-byte `call_data`, zero `block_height`, or `block_height` ahead of head |
| `400` | `CALLDATA_TOO_LARGE` | `call_data` over 131,072 bytes |
| `400` | `STALE_BLOCK` | `block_height` older than the staleness window |
| `400` | `TRANSITION_MISMATCH` | explicit `transition_index` does not match live state |
| `400` | `CONTRACT_NOT_FOUND` | no code at `target_address` on any supported chain |
| `503` | `QUEUE_FULL` | router at capacity — back off and retry |
| `503` | `RPC_UNAVAILABLE` | upstream RPC failing; message is intentionally generic |
| `500` | `INTERNAL` | server-side fault |

Validation order matters when debugging: body deserialization runs **before**
authentication, so a malformed body returns `422` even with no key at all. A `401` means
your body parsed fine and your key was rejected.

## 2.7 Pointing the service at your own contract

Your target must be a Gas Killer consumer: a contract built against `GasKillerSDK` (in
`gas-killer/solidity-sdk`) that exposes `stateTransitionCount()` and applies quorum-verified
diffs through `verifyAndUpdate`. Contracts, deploy scripts, and worked examples live in
that repository.

The service runs an unbounded gas profile so your call can consume orders of magnitude
more gas than a block allows. That budget is paid for with a strict shape (the reasoning
is in §3.4):

- **At most one `SSTORE` in your consumer per settlement.** Pack everything you need to
  commit into a single 32-byte slot. Two writes and the round cannot settle.
- **No `CREATE` / `CREATE2`** during the simulated call.
- **Events are effectively unlimited** — up to a 128 KB transport cap. Emit freely; that
  is where your real output goes.
- **`STATICCALL` results are never extracted.** Read-only calls work, but nothing they
  touch becomes part of the diff.
- **A revert means nothing is signed.** No partial settlement, no error round.

Start from the LLM consumers as a reference: they commit one root to one slot and emit the
full answer as an event.

---

# Part 3 — Technical appendix

## 3.1 What happens between your request and the transaction

```
you ──POST /bridge/ask──▶ bridge
                            │  validates caps, one ask per model
                            ▼
                          router (shard coordinator, internal :8081)
                            │  plans a (position × layer-range) segment DAG
                            │  assigns each segment to a k=2-of-N committee
        node-1 ◀── poll ────┤──▶ node-2 ──▶ node-3
          │  executes Qwen3SegEngine.forwardRange / argmaxRange as a view call
          │  against its own simulation RPC, with the weight overlay mounted
          └──result────────▶ router
                            │  the k results must be byte-identical
                            │  threads boundary state between segments,
                            │  merges argmax shards, assembles the commit chain
                            ▼
                     {answer_ids, pipeline_root}
                            │
        bridge ──fulfil(promptIds, maxNew, answerIds, pipelineRoot)──▶ /trigger
                            │
                     each operator's validator gate re-verifies the chain AND
                     the digests of the segments it executed itself, or refuses
                     to sign — a refusal starves the quorum
                            ▼
                     BLS quorum ──▶ verifyAndUpdate
                     one SSTORE + ChatAnswered log, ~350–384k gas
```

Prefill is batched and runs as a wavefront across stages; decode is inherently serial —
one token at a time — which is what sets the per-token latency floor.

## 3.2 The commitment chain

This is what makes the answer checkable rather than merely reported.

Each forward segment returns a commitment computed **inside the engine**, over everything
that defines it:

```
chk = keccak("gaskiller.seg.v1", posLo, posHi, layerLo, layerHi,
             keccak(tokenIds), keccak(xIn), keccak(kvIn),
             keccak(xOut), keccak(kvAppend))
```

Argmax segments get a synthetic commitment binding their calldata to their returndata.
Concatenating every `chk` in segment order and hashing gives the single value that travels
into settlement:

```
pipeline_root = keccak(concat(chk))
```

The chain is retrievable from the coordinator by root, which is how each operator
independently re-derives the answer's provenance at signing time. The operator's signature
means: *"I verified the commit chain, the answer ids, and the digests of every segment I
executed myself."*

## 3.3 How 34 GB of weights are "on-chain"

Weights are split into ≤24,575-byte chunks. Chunk *i* lives at a derived phantom address:

```
address(i) = keccak("gaskiller.llm.overlay.v1" || manifest || u64be(i))[12:]
manifest   = keccak(keccak(weights) || keccak(tokenizer))
```

The on-chain commitment is that single 32-byte `manifest` — for the 35B, a 9,400,000×
compression of the model. Operators memory-map the real files and the analyzer mounts them
as `EXTCODECOPY`-able code, so the Solidity engine reads weights exactly as if they were
deployed bytecode.

The manifest is flat, with no per-chunk Merkle tree, which is why verification is eager:
each daemon hashes the full artifact at boot (~9 minutes for the 35B). That is the cold
start in §2.5.

Published artifacts: `qwen3-0.6b-onchain-v1` (597 MB) and `qwen3.5-35b-a3b-onchain-v1`
(34,714,656,811 bytes plus tokenizer) on `gas-killer/solidity-sdk`.

## 3.4 The single-slot rule

The unbounded gas profile admits **at most one consumer `SSTORE` per settlement**, plus an
exempt state-tracker slot. Logs are unlimited within a 128 KB transport cap; `CREATE` is
disallowed; `STATICCALL` effects are never extracted; a revert means nothing is signed.

This is not an arbitrary restriction — it is what keeps the diff a quorum must agree on
small enough to verify and cheap enough to apply. A settlement is a signed commitment to
one 32-byte word.

It has teeth. Two otherwise-working resume-capable LLM consumers could not settle purely
because their `fulfil` wrote two slots, and had to be redeployed to pack into one. If your
consumer stops settling with no visible error, count your writes first.

## 3.5 Trust model, stated honestly

**What holds today.** Committee members are registered, staked operators. Each segment
executes on k=2 independent operators and the coordinator aborts on any divergence. Every
operator in the quorum independently verifies the full commitment chain plus its own
executed segments before signing. A single refusal prevents settlement.

**What this is not, yet.** The current stage is committee-trust plus full-quorum chain
verification. It is not slashing-complete. Specifically absent:

- **VRF sortition.** Committees are assigned by deterministic rotation, so a malicious
  coordinator could grind assignments.
- **Per-segment fraud proofs.** The commitment chain is sized for one-shot proofs, but
  binding them into a challenge is future work.
- **Data-availability custody receipts** for boundary state between segments.
- **Challenge-window economics.**

Treat sharded results as "a staked committee agreed and the whole quorum verified the
chain" — strong for a demonstration and for reproducible research, not yet a trustless
compute market. Design your experiments accordingly, and ask before assuming any
particular guarantee.

## 3.6 Measured performance

| Configuration | 8-token answer |
|---|---|
| 0.6B sharded, fast executor | **~4 min** end to end (~2 min inference + ~1 min settle) |
| 0.6B sharded, interpreter | 17.2 min |
| 0.6B monolithic (unsharded) | 25–49 min |
| 35B sharded | **~72–75 min** (4,423 s / 4,292 s across two runs) |
| 35B monolithic | ~95 min – 2 h 13 min |

- Simulated gas per answer: ~545 B (0.6B), ~3.6 T (35B). Settled gas: 350–384 k.
- The fast executor is 4.2× on the 0.6B but only ~1.08× on the 35B, which is
  weight-bandwidth-bound over 34 GB rather than compute-bound.
- Decode has a serial floor of roughly 4 min/token on the 35B.
- Prefix resume: a warmed prefix cuts a repeat inference from 852 s to 368 s (2.3×).
- More operators buy concurrent committees, not much single-ask speed — 10 operators ran a
  full 0.6B in 852 s against 1,030 s for 3.

**Bit-exactness, independently confirmed:** Solidity ≡ integer Python reference ≡ float
reference (greedy, temperature 0); browser tokenizer ≡ HuggingFace; sharded ≡ monolithic;
10-operator ≡ 3-operator; compiled executor ≡ interpreter. The live 35B answer ids matched
the reference vectors token-for-token across ~3.6 trillion simulated gas.

## 3.7 Deployed contracts (Sepolia, chain 11155111)

| Role | Address |
|---|---|
| 0.6B consumer `GasKillerChatSharded` | `0xd3f7F985F14f1942Fb09e5735e5499FEFF56E80b` |
| 0.6B segment engine `Qwen3SegEngine` | `0x18C8b1677a731f7507ea51D99e23e513D9613Aa4` |
| 35B consumer `GasKillerChat35Sharded` | `0xfd0EF988216D0346BF115530387021c1b699336d` |
| 35B segment engine `Qwen35SegEngine` | `0xcA459C95ee034D21339cd5ad7209441fD54bcd51` |
| 35B forward (separate deploy, staticcalled by the engine) | `0x5097fA57CdB792e188a086EB79d3Ef5DC495679b` |
| AVS service manager | `0xdCec8ce0a03848B55989Bcc711e424Ca31d9eeD9` |
| BLS signature checker | `0x7568336e17d3f52e0ba7a393f144ce16c8924ba5` |

Manifests: 0.6B `0x23216cb9…c4a7ae9`, 35B `0x7bdf4876…f01fa9`.

Consumer selectors: `fulfil` `0x9c98c06e` · `settlePrefix` `0x7e8de12c` ·
`fulfilResumed` `0x6c4d43bc` · `stateTransitionCount` `0xf4833e20` · `settledRoots`
`0x56408a4f`.

## 3.8 Glossary

| Term | Meaning |
|---|---|
| **Task** | One unit of work submitted to the quorum: a target contract, calldata, and a block to simulate at. Created by `POST /trigger`. |
| **Round** | The operator process of simulating a task, agreeing, BLS-signing, and submitting one `verifyAndUpdate`. |
| **Consumer** | A contract whose state the quorum updates. Holds the settled commitment. |
| **Segment** | One slice of an inference — a position range × layer range — executed as a single view call. |
| **Committee** | The k operators assigned to one segment. Their results must be byte-identical. |
| **`chk`** | A segment's commitment, computed inside the engine over its inputs and outputs. |
| **`pipeline_root`** | `keccak` over all segment `chk` values in order. The value that travels into settlement. |
| **Validator gate** | The node-side check that refuses to sign a round unless the commit chain and the node's own segment digests verify. |
| **Overlay** | The scheme mounting real weight files as `EXTCODECOPY`-able code at derived phantom addresses. |
| **Manifest** | `keccak(keccak(weights) ‖ keccak(tokenizer))` — the single 32-byte on-chain commitment to a model. |
| **Transition index** | The consumer's monotonic settlement counter, used for optimistic concurrency. |
| **Fork head** | The head block of the simulation fork the operators trace against. `GET /forkhead`. |

## 3.9 Constraint checklist

Every one of these has cost someone hours. Read as rules, not suggestions.

1. `call_data` is a JSON array of byte integers. Never a hex string.
2. `POST /trigger` bodies need the top-level `body` wrapper.
3. Pin `block_height` to `GET /forkhead`, not live head. A height the fork lacks kills the
   round silently.
4. Send a real `User-Agent`. The default `Python-urllib/*` gets a deterministic `403`.
5. Prefer `transition_index: "auto"`. Explicit indices are validated against live state
   and will race.
6. One consumer `SSTORE` per settlement. Commit to one slot, emit everything else as logs.
7. One in-flight ask per model. A second gets `429`.
8. `done` from the bridge is not "mined". Confirm on-chain via `stateTransitionCount()`.
9. Give the first ask after any restart 30 minutes before calling it failed — cold start
   re-verifies 34 GB.
10. You cannot hand-craft a `fulfil()` task for the LLM consumers. Inference is only
    reachable through `POST /bridge/ask`.
11. `answer_ids` are raw token ids. Decode them with the model's own tokenizer.
12. This is a testnet demo. Check `/healthz` before each session.

## 3.10 Where the code lives

| Repository | Contents |
|---|---|
| `gas-killer/service` | Router, operator node, shard coordinator, bridge, Helm chart. `router/src/shard.rs` is the coordinator; `router/src/ingress.rs` is the public API; `bridge/bridge.py` is the ask path end to end in ~250 lines. |
| `gas-killer/solidity-sdk` | Consumers, engines, kernels, deploy scripts. Weight artifact releases. |
| `gas-killer/gas-analyzer` | The EVM analysis engine, overlay mounting, and the compiled fast executor. |

Design notes for the sharded path are in `docs/SHARDED_INFERENCE.md` in the service
repository. `bridge/bridge.py` is the most useful single file to read: it is a complete,
dependency-free client for both paths.
