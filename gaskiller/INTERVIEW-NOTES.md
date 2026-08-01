# Gas Killer — slop computer interview prep

Prep notes for Austin's interview with the Gas Killer team (planned as of 2026-07-31).
Background: [`CLIENT-API.md`](CLIENT-API.md) (their doc) and
[`SAFETY-REVIEW.md`](SAFETY-REVIEW.md) (our review — verdict: safe).

## The one-paragraph pitch, in our words

An EigenLayer AVS that runs contract calls too big for any block — flagship demo:
transformer inference written in pure integer Solidity (~545B simulated gas for a
Qwen3-0.6B answer, ~3.6T for Qwen3.5-35B-A3B) — off-chain on a staked operator
committee that must agree byte-exactly, then settles the result on Sepolia in one
~384k-gas BLS-verified transaction. Deterministic (greedy, temp 0, integer math), so
the on-chain token ids match the HuggingFace reference exactly.

## Live demo logistics (if we run one on air)

- **Only the 0.6B is stream-viable**: ~4 min end to end. The 35B is ~72–75 min.
- **One in-flight ask per model** — a second gets `429`. Don't let chat spam it.
- **Cold start**: first ask after an operator fleet restart adds 15–30 min (weight
  re-verification). **Fire a warm-up ask shortly before going live** and have the
  polling loop ready with its `ask_id`.
- Check `GET /healthz` right before the segment — testnet compute can be down.
- `POST /bridge/ask` needs no key and is CORS-open, so a browser demo works.
- Payload gotchas: prompt must be pre-tokenized ids with the chat template applied
  (§2.2 of their doc); answer comes back as raw ids you decode client-side.
- Verify on-chain live for the payoff moment: `stateTransitionCount()` (selector
  `0xf4833e20`) on `0xd3f7F985F14f1942Fb09e5735e5499FEFF56E80b`, then pull the
  `ChatAnswered` event by `pipeline_root`. Use our Alchemy Sepolia endpoint.

## Question threads, roughly in order of juice

1. **"Where's the ZK?"** The name/framing suggests zk proofs, but the live system is
   staked-committee re-execution + BLS aggregation — no validity proofs, and §3.5 of
   their own doc says fraud proofs are future work. Is the endgame validity proofs
   (zkEVM over the segment chain?), fraud proofs, or is committee-trust the product?
   What's the honest timeline?
2. **The coordinator is the soft center.** Committees are deterministic-rotation, not
   VRF — their doc admits a malicious coordinator could grind assignments. Boundary
   state between segments has no DA custody receipts. What breaks first if the
   coordinator is adversarial, and what's the fix ordering?
3. **Why inference as the flagship?** LLM inference is the least
   settlement-shaped workload (huge compute, one tiny commitment). Is it a stunt to
   prove the gas ceiling is gone, or do they believe in on-chain inference as a
   product? What's the real customer workload for Path B?
4. **The single-SSTORE rule** (§3.4) is a fascinating constraint — everything must
   pack into one 32-byte slot, output goes out as events. Two of their own consumers
   failed to settle over a second write. How far can real apps go under that shape?
5. **Economics.** ~4 min and a whole committee for an 8-token 0.6B answer; the 35B is
   weight-bandwidth-bound over 34 GB (fast executor only buys 1.08×). What does a unit
   of this compute cost vs. an oracle-attested API call, and who pays operators?
6. **The weight overlay trick** (§3.3): 34 GB mounted as `EXTCODECOPY`-able phantom
   code, committed on-chain as one 32-byte manifest (9,400,000× compression). Flat
   manifest, no per-chunk Merkle — hence 9-min eager hashing at boot. Why not a
   Merkle tree, and does that change with fraud proofs?
7. **Determinism as a primitive.** Bit-exact integer inference (Solidity ≡ Python ≡
   float reference, sharded ≡ monolithic, 10-op ≡ 3-op) is independently interesting —
   reproducible AI answers with an on-chain receipt. Do they see the determinism layer
   as a standalone artifact?
8. **EigenLayer AVS reality check.** What does restaked security actually buy today
   with no slashing wired up? What's the operator set, and who runs it?

## Numbers to have at hand

| Fact | Value |
|---|---|
| 0.6B answer, end to end | ~4 min (~2 min infer + ~1 min settle) |
| 35B answer, end to end | ~72–75 min |
| Simulated gas | ~545 B (0.6B) / ~3.6 T (35B) |
| Settled gas | ~350–384 k, one transaction |
| Settlement | Sepolia; 0.6B consumer `0xd3f7…E80b`, 35B `0xfd0E…336d` |
| 35B artifact | 34,714,656,811 bytes, committed as one 32-byte manifest |
| Committee | k=2 per segment; byte-identical or abort; one dissent blocks quorum |
| Trust today | staked committee + full-quorum chain verify; no VRF / fraud proofs / slashing |
