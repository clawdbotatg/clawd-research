# Noir games — how long between turns?

*Researched 2026-08-07*

**Key framing:** Noir is a circuit language, not a chain — it has no block time.
Noir compiles to ACIR and proves via a backend (default: Barretenberg /
UltraHonk). "Time between turns" in a Noir game = **proving time** (client-side,
per move) **+ settlement time** (wherever the proof gets verified). Those are
independent knobs.

## 1. Proving time (the part Noir controls)

Per-move proof generation, real benchmarks:

| Circuit / hardware | Time |
|---|---|
| p256 ECDSA verify (heavy, ~large circuit), M1 MacBook Air, browser, UltraHonk multithreaded | **~2.1s** |
| Same, single-threaded | ~8.1s |
| Same, Samsung Galaxy A23 (budget Android), browser | ~6s |
| RSA sig verify, i7-13700H laptop, UltraHonk | **~0.2s** |
| Same circuit on UltraPlonk (older backend) | 8–33s (why you use Honk) |

Game-move circuits (battleship shot validity, mastermind guess, card reveal)
are far smaller than an ECDSA verify — expect **sub-second to ~2s in a
browser** on desktop, a few seconds on mid mobile. iPhones historically hit
WASM memory limits on big circuits (iPhone 16 OOM'd in the Hylé bench);
Barretenberg's newer client-side prover ("CHONK") targets weak devices.
UltraHonk proving scales roughly with circuit size and got 5–50× faster than
Groth16-era numbers in browser benches.

**Rule of thumb: proving adds ~0.5–3s per turn on desktop, 3–10s on cheap
phones, for reasonable game circuits.**

## 2. Settlement time (where you verify)

Three architectures, three latencies:

1. **P2P / off-chain (Dark Forest style, or state-channel-ish):** exchange
   proofs directly, settle on chain only at game end. **Turn latency ≈ proving
   time only (~1–3s).** Best UX, most plumbing.
2. **Verify on an EVM chain:** UltraHonk has a Solidity verifier
   (~400–500k gas). Turn latency = proving + chain inclusion:
   - Ethereum L1: 12s slots → ~12–24s/turn
   - Base/Arbitrum/OP: ~1–2s blocks → **~2–5s/turn total** (with Flashblocks
     ~200ms preconf, effectively proving-bound)
3. **Aztec network (Noir's home chain, private state built-in):**
   - **Today (Ignition mainnet, launched Nov 2025): 36–72s blocks** — one
     block per 72s slot. A turn-per-block game is ~1 min+ between turns.
   - **Roadmap: 3–4s blocks targeted by end of 2026**, staged, via parallel
     proof gen + network optimizations.

## Bottom line

- If "block time" means Aztec: **~36–72s now, 3–4s promised by end of 2026.**
- If the game verifies on a fast L2: **~2–5s per turn**, dominated by
  client-side proving, not the chain.
- If turns exchange proofs P2P: **~1–3s**, purely proving-bound.
- Design consequence: keep the per-move circuit small (constraint count is
  the latency dial) and settle lazily. Async/correspondence-style games are
  free wins; real-time games on Aztec today are not viable, but fine
  proving-P2P.

## Sources

- https://hyli.ghost.io/benchmarking-in-browser-p256-ecdsa-proving-systems/ (Mar 2025 bench)
- https://blog.base.dev/benchmarking-zkp-systems (RSA 0.2s UltraHonk)
- https://aztec.network/blog/announcing-noir-beta-stabler-faster-zk-applications-in-the-browser
- https://ventureburn.com/what-is-aztec/ + https://www.panewslab.com/en/articles/486298cd-5ba6-4c85-908f-864d58abbfef (block times + 2026 roadmap)
- https://github.com/BattleZips/BattleZips-Noir (reference Noir game)
- https://github.com/weijiekoh/noir_ultrahonk_benchmarks (browser bench harness)
