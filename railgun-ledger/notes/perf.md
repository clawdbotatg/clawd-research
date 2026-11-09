# RAILGUN signer crypto on RP2040 / RP2350: speed estimate

**Bottom line:** a typical 2-in/3-out clear-signed tx takes about **0.55 s on an RP2040 with hand-written asm (about 0.9 s in plain C)**. On an **RP2350 it takes about 60 ms with asm (about 130 ms in C)**. Both are fine for a hardware wallet. About 45% of the time is note encryption (9 ed25519 scalar mults). Another 40% is Poseidon.

## Results (ms)

| Operation | Fr muls | RP2040 asm | RP2040 C | RP2350 asm | RP2350 C |
|---|---|---|---|---|---|
| One Fr Montgomery mul | 1 | 0.030 | 0.062 | 0.003 | 0.007 |
| Poseidon t=4 (commitment) | 784 | 25 | 51 | 2.5 | 5.7 |
| Poseidon t=7 | 1,568 | 50 | 102 | 4.9 | 11 |
| Poseidon t=17 | 5,168 | 163 | 335 | 16 | 37 |
| EdDSA-Poseidon sign (fixed-base table) | ~2,150 + blake512 | 68 | 140 | 7 | 16 |
| EdDSA sign, no table | ~4,470 | 141 | 289 | 14 | 32 |
| One X25519 / ed25519 var-base mult | — | 27 | 31 | 2.7 | 6 |
| Note encryption, per output (3 mults) | — | 87 | 100 | 9 | 20 |
| **Full tx: 2 in, 3 out** | — | **~560** | **~900** | **~57** | **~126** |

Uncertainty: about ±40% on the asm columns. The C columns are a pessimistic bound from gcc output.

## Where the numbers come from

**Fr mul, measured.** I wrote CIOS Montgomery multiply for BN254 Fr two ways and checked both against Python bigints on the Mac. Then I cross-compiled with arm-none-eabi-gcc 16.2 at -O2, fully unrolled, and summed static cycles: load/store 2, ALU/MUL 1, branch 2.
- **M0+, 16-bit limbs** (32x32→32 MUL only): 6,468 instructions, **~8,200 cycles**. It is spill-heavy, because Thumb-1 only has 8 low registers.
- **M33, 32-bit limbs** (`umlal`): 904 instructions, **~1,030 cycles**.
- A 32-bit-limb build for M0+ calls `__aeabi_lmul` 120 times, so it is no help.

**Fr mul, from the literature.**
- Düll et al.: on M0, a 256x256 product with 3-level Karatsuba costs **1,294 cycles**, plus 175 for reduction mod 2^255−19 ([paper](https://cryptojedi.org/papers/mu25519-20150417.pdf), Table 1).
- BN254 Fr has no special form, so Montgomery reduction costs about as much as a second product. That gives **~3–4k cycles** in asm.
- Unterluggauer–Wenger cross-check: a BN254 pairing takes 47.6M cycles on a plain M0+, with 80% of it in Fp muls. That implies about 3.5k cycles per mul ([ePrint 2014/800](https://eprint.iacr.org/2014/800.pdf), [slides](https://iacr.org/workshops/ches/ches2014/presentations/0925_Session_05/0925_Session_05_1.pdf)).
- I used **4,000 cycles**.
- M33: Seo et al. report 608 cycles for a generic 256-bit mul on M4 ([MDPI](https://www.mdpi.com/2076-3417/10/4/1539)). Lenngren's X25519 numbers imply about 150 cycles per special-prime field op. I used **450 cycles** for a UMAAL Montgomery mul.

**X25519.**
- M0: **3,589,850 cycles** (Düll 2015). cifra measures 4,070,271 ([GitHub](https://github.com/ctz/cifra)).
- M33 with DSP: **411,061 cycles**; M4: 441,116 (Lenngren, [ePrint 2025/523](https://eprint.iacr.org/2025/523)).
- Ed25519 sign on M0 is about 3M cycles (Fujii–Aranha, [paper](https://www.cs.haifa.ac.il/~orrd/LC17/paper39.pdf)).
- Clocks: RP2040 at 133 MHz with the single-cycle MUL, RP2350 at 150 MHz.

## Op counts

**Poseidon, using the circomlibjs `poseidon_opt` structure.** Per permutation:
- 8 full rounds, each with t S-boxes (3M each) and a dense t×t mix.
- NP partial rounds, each with 1 S-box and a sparse mix (2t−1 muls).
- Muls = 24t + 8t² + NP·(2t+2).
- t=3: 600, t=4: 784, t=6: 1,272, t=7: 1,568, t=8: 1,856, t=10: 2,360, t=17: 5,168.
- Additions cost about 3% on top (~110 cycles each on M0); I added 5% for adds and loads.

**BabyJubJub fixed-base r·B8** (twisted Edwards, extended coords, a=168700 so not the a=−1 fast path):
- Mixed add ≈ 9M, full add ≈ 10M, double ≈ 9M (4M+4S+a·A).
- With a 4-bit window and a precomputed table (63 windows × 15 points × (x, y, d·xy)): 63 mixed adds = 567M, plus about 300M to convert R8 to affine. That is **~870M**. The table needs 90.7 KB of flash.
- Without a table: 251 doubles + 63 adds + inversion ≈ **3,190M**.

**EdDSA sign** = r·B8 + Poseidon t=6 (5 inputs) + scalar math mod l (≈10M) + one blake512 block (~50k cycles on M0, a guess).

## Poseidon constants in flash (parsed from circomlibjs@0.1.7 `poseidon_constants_opt.js`)

There are 32 bytes per element. Optimized C = 8t + NP, S = NP·(2t−1), plus M and P at t² each.

| t | C | M | P | S | bytes |
|---|---|---|---|---|---|
| 3 | 81 | 9 | 9 | 285 | 12,288 |
| 4 | 88 | 16 | 16 | 392 | 16,384 |
| 6 | 108 | 36 | 36 | 660 | 26,880 |
| 7 | 119 | 49 | 49 | 819 | 33,152 |
| 8 | 128 | 64 | 64 | 960 | 38,912 |
| 17 | 204 | 289 | 289 | 2,244 | 96,832 |

- **All widths t=2..17: 769,920 bytes (752 KB).**
- **Widths t ≤ 7: 118,720 bytes (116 KB).**
- Both fit the Pico's 2 MB flash or the Pico 2's 4 MB flash.
- The RP2040 XIP cache is 16 KB. Streaming constants costs ~200 cycles per 32-byte constant on a miss, which is under 5% of a 4k-cycle mul. Copying the active width into SRAM avoids that cost.

## Full tx model (2 inputs, 3 outputs: transfer, change, broadcaster fee)

Verified in `@railgun-community/engine@9.9.1`. Under Ledger clear-signing the device picks `random`/`senderRandom` and re-derives `npk` and the commitments itself (`TransactNote.withExternalRandomness`). Device work:

- 2 nullifiers: Poseidon t=3
- 3 npk: Poseidon(MPK, random), t=3
- 3 commitments: Poseidon(npk, token, value), t=4
- Signed hash: Poseidon(root, boundParamsHash, 2 nullifiers, 3 commitments), 7 inputs, so t=8
- 1 EdDSA-Poseidon sign
- Note encryption, per output:
  - `getNoteBlindingKeys`: 2 ed25519 `Point.multiply`, which blind the sender and receiver viewing keys.
  - `getSharedSymmetricKey`: 1 more scalar mult, then sha256.
  - AES-256-GCM (V2) or XChaCha20-Poly1305 (V3). Both are negligible.
  - These are ed25519 Edwards points, not x25519. I costed each mult as 1 X25519, plus 2 point decompressions (~0.4M cycles each on M0).

Encryption is the biggest single part: 3 × 87 ms on RP2040. Precomputing a table for the sender's own viewing key would turn 1 of the 3 mults per output into a cheap fixed-base mult, saving ~25%.

## Assumptions and risks

- "asm" means hand-written Thumb-1 Karatsuba+Montgomery (M0+) or UMAAL (M33) inside the MicroPython native module. Plain C from gcc is about 2x slower on M0+. MicroPython bigint code would be far slower; don't do that.
- The Fr mul cycle counts are a static sum over unrolled code, not measured on hardware. M33 `umaal` result stalls (noted by Lenngren) could add 10–20%.
- Not included: Merkle-proof checks of the input notes (16 × Poseidon t=3 per input ≈ +0.6 s on RP2040, +60 ms on RP2350), keccak for boundParams, display/USB time, and side-channel hardening.
- Using both RP2040 cores (Poseidon on one, ed25519 on the other) could cut wall time by about 40%.
- Source files: `perf/opt.js`, `mm/mont.c`, `mm/*.dis`, `tools/{parse,cyc,est}.py` in this scratchpad.
