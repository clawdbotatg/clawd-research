# PQ hardware wallet landscape (Pico + Trust M V1)

Researched 2026-10-08. Goal: design the best post-quantum (and "post-ECDSA-break") hardware wallet we can build from a Raspberry Pi Pico (RP2040 / RP2350) and an OPTIGA Trust M V1.

Tags: **[unconfirmed]** = one source or a source we could not open. **[est]** = our own arithmetic. **[measured]** = we ran it today.

## Short version

- **Protocol.** Ethereum has no PQ signatures yet. The way out is account abstraction: EIP-8141 (frame transactions) is scheduled for Hegotá, a 2027 fork. Every PQ precompile EIP (Falcon, ML-DSA) is still a Draft. No SLH-DSA precompile EIP exists. Until then, PQ accounts = smart contract wallets that verify in plain EVM code.
- **Best scheme for a Pico: hash-based one-time keys (WOTS, w=16) with on-chain key rotation.** That is what hashsig-safe already does. It needs no RNG, no float math, about 1,500 hash calls per signature, and the chain holds the state. Gas is the lowest of any PQ option.
- **Gas.** Our naive Solidity WOTS verify costs about 206k gas. A tight Yul version costs **79k [measured]**. That fits EIP-8141's 100k validation cap. The same verifier on the SHA-256 precompile costs 162k [measured]. So keep keccak on chain.
- **Lattice schemes (Falcon, ML-DSA) are a bad fit.** 0.7M to 8M gas in Solidity, need a good RNG, and have side-channel problems on small chips. Falcon on an M0+ is a trap.
- **Stateless SPHINCS-style (PQ1's choice) is the main alternative.** About 4 KB signatures, 94k–142k gas, no state at all. Signing takes millions of hash calls, which is slow on a Pico.
- **The chip is a non-extractable PRF, not a signer.** It keeps the master secret out of Pico flash and gives us monotonic counters for anti-rollback. It does **not** stop a thief who holds the device: execute=ALW means anyone on the I2C bus can ask for any key. We need a PIN or button gate and an on-chain spending policy.
- **Recovery.** Don't back up the chip secret. Add a second PQ owner (paper WOTS seed or a second device) behind a timelock that the main device can cancel. Every recovery and cancel path must be PQ too.
- **Today's bridge.** A Safe whose only owner is a WOTS owner survives an ECDSA break. The ECDSA relayer only risks its gas money. Watch for leftovers: old ECDSA owners, modules, `signedMessages`, Permit2 approvals, and 7702 EOAs (not fixable yet).
- **Found a bug-class in hashsig-safe.** One-time keys are derived from (seed, index) only, not the chain or owner. Reusing one seed on two chains or two owners reuses one-time keys. The CLI's state file blocks it today, but only if the same state file is used everywhere.

---

## 1. Ethereum protocol status

### 1.1 Timeline

| Date | What | Source |
|---|---|---|
| 2024-03-09 | Vitalik's quantum emergency hard-fork plan | [ethresear.ch](https://ethresear.ch/t/how-to-hard-fork-to-save-most-users-funds-in-a-quantum-emergency/18901) |
| 2025-04 | Hash-based multi-signatures for PQ Ethereum (Generalized XMSS) published | [ePrint 2025/055](https://eprint.iacr.org/2025/055) |
| 2025-12-03 | Fusaka live. EIP-7951 P256VERIFY precompile at 0x100, 6,900 gas | [EIP-7951](https://eips.ethereum.org/EIPS/eip-7951), [Bankless](https://www.bankless.com/read/news/ethereum-fusaka-upgrade-activated) |
| 2026-01 | EF Post-Quantum team formed (Thomas Coratger) | [CoinDesk](https://www.coindesk.com/tech/2026/01/24/ethereum-foundation-makes-post-quantum-security-a-top-priority-as-new-team-forms) |
| 2026-01-29 | EIP-8141 Frame Transactions created | [EIP-8141](https://eips.ethereum.org/EIPS/eip-8141) |
| 2026-03-25 | pq.ethereum.org roadmap launched. L1 PQ "done" around 2029 | [pq.ethereum.org](https://pq.ethereum.org/) |
| 2026-08-27/28 | EIP-8141 SFI'd for Hegotá (ACDE #244). Date differs by source | [Christine Kim](https://christinedkim.substack.com/p/acde-244) |
| 2026-10-06 | Glamsterdam on Sepolia. Mainnet date not set | [EIP-7773](https://eips.ethereum.org/EIPS/eip-7773) |
| 2026-10-07 | Justin Drake "bunker mode": AI may break ECDSA classically, maybe in months. No break shown | [CoinDesk](https://www.coindesk.com/tech/2026/10/08/bitcoin-and-ether-holders-urged-to-prepare-bunker-mode-against-possible-ai-attacks) |

Vitalik's reply to bunker mode: don't scramble. He also warned that lattice security "will take serious hits from the next two years of AI math" (same CoinDesk piece). That is one more reason to prefer hash-based signatures.

### 1.2 Account layer

**EIP-8141 (Frame Transactions)** ([EIP](https://eips.ethereum.org/EIPS/eip-8141))
- Draft, SFI'd for Hegotá (2027). The chair said the number and design "may change."
- First stated motivation: an off-ramp from elliptic curves to PQ.
- A tx is 1–64 frames. A VERIFY frame runs static code and calls `APPROVE`. Any signature scheme works, including ours.
- Native schemes: secp256k1 (2,800 gas), P-256 (6,700 gas). PQ goes in the "arbitrary" slot, verified by EVM code.
- Public mempool rules: **validation capped at 100k gas**, and validation may only read `tx.sender`'s own storage ([alt-mempool notes](../alt-mempool/README.md)). Anything else needs an alt mempool.
- Consequence for us: a WOTS verifier must be under 100k and the public key hash must live in the account's own storage. Today's hashsig-safe keeps it in a separate owner contract, so it would not pass the public rules as-is.

**EIP-8130** (Coinbase/Base) is the rival: owners registered with verifier contracts, no arbitrary validation code. Base and Offchain Labs prefer it but will back 8141 ([Kim](https://christinedkim.substack.com/p/acde-244)).

**EIP-7702 does not make an EOA PQ-safe.** The ECDSA key stays the master. Draft fixes:

| EIP | What | Status |
|---|---|---|
| [7851](https://eips.ethereum.org/EIPS/eip-7851) | Wallet code calls `SETSELFDELEGATE` to set prefix 0xef0101, permanently disabling the ECDSA key | Draft, redesigned several times |
| [8151](https://etherspot.io/blog/eip-8151-proposes-ecrecover-deactivation-awareness-eip-7851-for-delegated-eoas-vitalik-pushes-cypherpunk-ethereum-layer-base-moves-off-op-stack-curvegrid-launches-7702-delegation-checker/) | `ecrecover` returns zero for deactivated keys (stops old permits) | Draft |
| [8164](https://eips.ethereum.org/EIPS/eip-8164) | Swap an EOA's key to ML-DSA-44, 50k gas per verify | Draft |
| [8298](https://eips.ethereum.org/EIPS/eip-8298) | SETCODEFROM: install real code, EIP-3607 then blocks ECDSA txs | Draft |

### 1.3 Emergency plan (Vitalik, 2024)

If a quantum (or other) break hits before migration ([ethresear.ch](https://ethresear.ch/t/how-to-hard-fork-to-save-most-users-funds-in-a-quantum-emergency/18901)):
1. Roll back to before mass theft.
2. Disable EOA transactions.
3. Add a smart-wallet tx type.
4. Let users move funds by proving with a STARK that they know the hash preimage (for example the BIP-32 seed) behind their key.

Limits: only saves keys derived from a hash (seed phrases). Raw keys and hardware keys made from a TRNG with no seed are not saved. A STARK proof of a BIP-32 seed takes about 55 s and 1.8 MB ([Roasbeef tracker](https://gist.github.com/Roasbeef/563f173fe44e2005e003a082716e586f)).

**What this means for our design:**
- If EOA txs get disabled, our ECDSA relayer can't send anything. The Safe must be able to pay its own gas through the new tx type (8141 frame or similar).
- A Trust M P-256 key from the chip's TRNG has no seed, so step 4 can't rescue it.
- A WOTS-owned Safe needs no rescue. It keeps working.

### 1.4 Consensus layer (for context)

- Validators move from BLS to hash-based XMSS ("leanSig"), aggregated by a STARK VM ("leanMultisig") ([ePrint 2025/055](https://eprint.iacr.org/2025/055), [ePrint 2025/1332](https://eprint.iacr.org/2025/1332.pdf)).
- Signature sizes went from 3,112 B (devnet 2) to 2,536 B (devnet 4) to 1,208 B in current leanVM ([LambdaClass](https://blog.lambdaclass.com/ethereum-signature-schemes-explained-ecdsa-bls-xmss-and-post-quantum-leansig-with-rust-code-examples/), [ethlambda PR #606](https://github.com/lambdaclass/ethlambda/pull/606)).
- Hash: Poseidon2, because it is cheap inside a STARK. One PR says leanVM moved to BLAKE2s **[unconfirmed]**.
- Aggregation: about 1,000–1,480 signatures/s, proofs 122–327 KiB ([leanMultisig](https://github.com/leanEthereum/leanMultisig)).
- Takeaway: the EF bet for its own keys is **stateful hash-based signatures**. Same family as our WOTS.

### 1.5 PQ precompile EIPs (all Draft)

| EIP | What | Proposed gas | Sizes |
|---|---|---|---|
| [7619](https://eips.ethereum.org/EIPS/eip-7619) | Falcon-512 verify | 1,465 + 6/word | 666 B sig |
| [7885](https://eips.ethereum.org/EIPS/eip-7885) | NTT precompiles (helps Falcon/ML-DSA in EVM) | ~500–790 per NTT | — |
| [7932](https://eips.ethereum.org/EIPS/eip-7932) | Registry of secondary signature algorithms | 3,000 + per-algo | — |
| [8051](https://eips.ethereum.org/EIPS/eip-8051) | ML-DSA verify | 4,500 | 2,420 B sig, 20,512 B expanded key |
| [8052](https://eips.ethereum.org/EIPS/eip-8052) | Falcon verify (SHAKE or keccak) | 3,000 | 666 B sig, 896 B key |
| — | **SLH-DSA / hash-based** | **none exists** | — |

pq.ethereum.org puts PQ signature precompiles in the "J*" fork, after Hegotá. Realistic mainnet: 2028+ **[est]**.

### 1.6 Wallets

- **Kohaku** (EF wallet toolkit): roadmap has a "post-quantum killswitch" turning on Falcon/Dilithium accounts ([roadmap](https://notes.ethereum.org/@niard/KohakuRoadmap)). ZKnox ships `@kohaku-eth/pq-account`, an ERC-4337 PQ account ([ZKNoxHQ/kohaku](https://github.com/ZKNoxHQ/kohaku)).
- **Ambire**: plumbing for PQ1 (SPHINCS+ hardware wallet driving 4337 accounts), Sept 2026 ([PR #2677](https://github.com/AmbireTech/ambire-common/pull/2677)).
- **Safe**: no official PQ owner or module. [PQBeat](https://github.com/ZKNoxHQ/PQbeat) rates Safe, Ledger, Trezor, MetaMask and Rabby "Stage 0".

---

## 2. On-chain verifiers and gas

### 2.1 Verifier table

| Scheme | Sig size | Verify gas | Source | Status |
|---|---|---|---|---|
| **Our WOTS w=16 keccak, Yul** | 2,144 B | **79k** | [measured], scratch test | Prototype |
| Our WOTS w=16 keccak, naive Solidity | 2,144 B | 206k | [measured] | = hashsig-safe style |
| hashsig-safe `approve` (full tx incl. Safe approveHash) | 2,144 B | ~280k | hashsig-safe README | Unaudited |
| Our WOTS w=16, SHA-256 precompile, Yul | 2,144 B | 162k | [measured] | Prototype |
| Our WOTS w=4 keccak, naive | 4,256 B | 210k | [measured] | — |
| Our WOTS w=256 keccak, naive | 1,088 B | 1.12M | [measured] | Too much hashing |
| WOTS+C (RivaLabs) | 468 B | ~73k | [ethresear.ch](https://ethresear.ch/t/achieving-quantum-safety-through-ephemeral-key-pairs-and-account-abstraction/24273), [code](https://github.com/RivaLabs-Core/NiceTry/blob/40a1286d18dee2a92631da82a52e484fa9a3628c/other-implementations/wots/WotsCVerifier.sol) | Sepolia PoC. Size suggests n=16 **[unconfirmed]** |
| FORS+C few-time (RivaLabs) | 2,448 B | ~35k | same | Sepolia PoC |
| SPHINCS− C13 (keccak, 2^14–2^20 sigs/key) | 3,704 B | 127k | [ethresear.ch SPHINCS−](https://ethresear.ch/t/sphincs-minus-efficient-stateless-post-quantum-signature-verification-on-the-evm/25165) | Research |
| SLH-DSA-Keccak-128-24 (not NIST) | 3,856 B | 94k | same | Research |
| SLH-DSA-SHA2-128-24 (NIST SP 800-230 draft) | 3,856 B | 142k | same | Research |
| PQ1 SPHINCS+C10 (SHA-256) | 4,008 B | not published | [PQ1](https://github.com/EthereumPhone/PQ1) | Audit in progress |
| SLH-DSA-128s / 128f (FIPS 205) | 7,856 / 17,088 B | impractical (SHAKE alone >4M) | [AppliedPQC survey](https://github.com/AppliedPQC/pqc-research/issues/35) | — |
| XMSS-SHA2_10_256 / _20_256 | 2,500 / 2,820 B | ~712k / 745k | [skalenetwork/xmss-solidity](https://github.com/skalenetwork/xmss-solidity) | Halmos-proven, unaudited |
| LMS / HSS | ~1.5–2.5 KB | no Solidity verifier found | — | Gap |
| Lamport (Quasar) | 8 KB | <700k | [ETHGlobal](https://ethglobal.com/showcase/quasar-m8xcv) | Hackathon |
| ETHFALCON (ZKnox) | 666 B | 1.5M–1.9M | [ZKnox](https://zknox.eth.limo/posts/2025/03/21/ETHFALCON.html) | "Do not use in production" |
| falcon512-sol | 666 B | ~741k total | [repo](https://github.com/partylikeits1983/falcon512-sol) | Unaudited |
| ETHFALCON + NTT precompile | 666 B | 479k | [EIP-7885](https://eips.ethereum.org/EIPS/eip-7885) | Testnet |
| ML-DSA-44 (Fireblocks) | 2,420 B | 1.23M + ~4.1M one-time key deploy | [Fireblocks](https://www.fireblocks.com/blog/post-quantum-signatures-ethereum-cheaper-gas) | New |
| ETHDILITHIUM | 2,420 B | 4.9M–8.8M (repo vs blog disagree) | [repo](https://github.com/ZKNoxHQ/ETHDILITHIUM) | Experimental |

How we measured: [scratchpad Foundry test](#appendix-our-gas-test), 50 random digests, `gasleft()` around an external call. Includes call overhead, not tx calldata.

Note on the 100k cap: only hash-based verifiers fit under EIP-8141's public-mempool validation cap. Our Yul WOTS (79k), WOTS+C (73k), FORS+C (35k) and SLH-DSA-Keccak-128-24 (94k) fit. Every lattice verifier needs a precompile to fit.

### 2.2 Calldata

Calldata now matters as much as hashing. Rules ([EIP-7623](https://eips.ethereum.org/EIPS/eip-7623), [EIP-7976](https://eips.ethereum.org/EIPS/eip-7976)):
- Standard: 16 gas per nonzero byte.
- Pectra floor: 40 gas/byte, applies when execution gas < 24 × bytes.
- Glamsterdam floor (EIP-7976, scheduled): 64 gas/byte, applies when execution gas < 48 × bytes.

| Sig bytes | Standard (16/B) | 7623 floor (40/B) | 7976 floor (64/B) |
|---|---|---|---|
| 1,224 (WOTS n=24) [est] | 19.6k | 49k | 78k |
| 2,144 (our WOTS n=32) | 34.3k | 85.8k | 137k |
| 3,704 (SPHINCS− C13) | 59.3k | 148k | 237k |
| 7,856 (SLH-DSA-128s) | 126k | 314k | 503k |
| 17,088 (SLH-DSA-128f) | 273k | 684k | 1.09M |

Our WOTS tx: execution ≈ 79k verify + ~50k storage and Safe call [est] ≈ 130k. That is above 48 × 2,144 = 103k, so we pay standard rate, about 34k for the signature. A faster verifier can push us onto the floor, so after Glamsterdam, smaller signatures beat cheaper verifiers.

### 2.3 Hash costs in the EVM

| Hash | Gas for 64-byte input | Source |
|---|---|---|
| KECCAK256 opcode | 42 + memory | [execution specs](https://raw.githubusercontent.com/ethereum/execution-specs/master/src/ethereum/forks/prague/vm/gas.py) |
| SHA-256 precompile | 84 + 100 STATICCALL + setup ≈ 200 | same |
| Poseidon2 (BN254, Yul/Huff) | 15–20k | [poseidon2-evm](https://github.com/zemse/poseidon2-evm) |

Our measurement agrees: the same WOTS verifier costs 2.0× more on SHA-256 (162k vs 79k).

---

## 3. Which scheme fits a Pico

### 3.1 Big table

Sign times on RP2040 (Cortex-M0+, 133 MHz) and RP2350 (Cortex-M33, 150 MHz). RP2040 ML-DSA numbers are measured ([arXiv 2603.19340](https://arxiv.org/html/2603.19340v5)); the rest are [est] from [pqm4](https://github.com/mupq/pqm4/blob/master/benchmarks.md) and hash speeds.

| Scheme | Sig | PK | Sign RP2040 | Sign RP2350 | RAM | RNG at sign? | State? | EVM verify | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **WOTS w=16, n=32, chain-committed** | 2,144 B | 32 B hash | ~45–70 ms hashing [est] + ~0.1 s chip | ~5–30 ms [est] | <5 KB | No | Yes (on chain) | 79k (Yul) | **Best fit** |
| WOTS w=16, n=24 (SHA-256/192 or keccak/192) | 1,224 B | 24–32 B | similar | similar | <5 KB | No | Yes | ~60k [est] | Good v2 |
| LMS H10 W4 (1,024 sigs per key) | 2,508 B | 60 B | ~45 ms per sig + 110 s keygen [est] | keygen a few s with HW SHA [est] | tree cache | No | Yes (device, critical) | no verifier exists; ~700k like XMSS [est] | Worse than chain-commit |
| XMSS H10 | 2,500 B | 64 B | 5,725 hashes/sign | — | tree state | No | Yes (device) | 712k | Worse |
| SPHINCS− C13 (stateless) | 3,704 B | 64 B | 4.3M hashes ≈ minutes [est] | ~30–60 s soft, faster with HW SHA [est] | ~3 KB | No | No | 127k | Fallback option |
| SLH-DSA-128s | 7,856 B | 32 B | ~100 s [est] | ~51 s soft [est] | ~3 KB | Optional | No | impractical | No |
| SLH-DSA-128f | 17,088 B | 32 B | ~5 s [est] | ~2.5 s [est] | ~3 KB | Optional | No | impractical | No (calldata) |
| ML-DSA-44 | 2,420 B | 1,312 B | 159 ms avg, p99 490 ms (measured) | ~26–81 ms [est] | 55 KB | Yes (hedged) | No | 1.2M–8.8M | Too much gas, needs RNG |
| Falcon-512 | 666 B | 897 B | ~0.7–1.5 s [est], no constant-time M0 build | ~150 ms if FPU path ports [est] | 11–42 KB | Yes | No | 0.7M–1.9M | Avoid on M0+ |

Blockstream measured SLH-DSA-128s at 53–120 s per signature on Jade/Trezor/Ledger/BitBox chips ([Blockstream](https://blog.blockstream.com/hardware-wallets-post-quantum-signatures/)). That matches our estimate.

### 3.2 Why WOTS with on-chain rotation wins

- **The chain is the state.** The contract stores the current key hash and index. Each signature commits to the next key. The device can't "lose" an index the chain already burned.
- **Smallest code.** One hash function and a loop. Fits MicroPython or a few hundred lines of C.
- **No RNG at sign time.** Deterministic from the chip PRF. Lattice schemes need good randomness (ML-DSA hedged mode) or exact Gaussian sampling (Falcon).
- **No float, no rejection loops.** Constant time is easy.
- **Cheapest gas.** 79k verify, fits the 8141 cap.
- **Same family the EF picked for validators** (XMSS-style).

Why not LMS/XMSS: they solve "many signatures under one fixed public key." A smart account doesn't need that, because it can store a new key every tx. LMS/XMSS add a tree (keygen of 1M+ hashes), device-side state that must never roll back, and a 700k-gas verifier. Chain-committed WOTS gets the same result with none of that.

Why not SPHINCS-style: no state is a real advantage (PQ1 chose it for this reason). But signing is millions of hashes, signatures are about 2× bigger, and it is still research-grade on chain. Keep it as the plan B if state management ever bites.

### 3.3 Costs of the WOTS choice

- **One signature per nonce.** You can't sign two alternative txs for the same index. Fee bumps are fine: the gas price lives in the relayer's outer tx, not in what WOTS signs.
- **Pre-signing works in order only.** You can sign k, k+1, k+2 ahead of time; they must land in that order.
- **Signing a different message at a used index leaks the key.** This is the one rule that matters. See 5.3.
- **Faults.** A glitched signature can act like a second signature at the same index ("grafting trees" attack, [ePrint 2018/102](https://eprint.iacr.org/2018/102.pdf)). Fix: compute the signature, run verify on device, compare, then release.

### 3.4 Hash choice

| | keccak-256 | SHA-256 | Poseidon2 |
|---|---|---|---|
| EVM cost per step | ~42 gas | ~200 gas | 15–20k gas |
| Our WOTS verify | **79k** | 162k | absurd |
| RP2040 speed | ~18–20k cycles/permutation in asm [est] ([Keccak team](https://keccak.team/files/Keccak-implementation-3.2.pdf)) | ~11.5k cycles/block in C ([cifra](https://github.com/ctz/cifra)) | slow |
| RP2350 | software only | **hardware unit**, ~73 cycles/block [est] ([datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)) | slow |
| MicroPython | not in `hashlib`; needs a C module | `hashlib.sha256` built in (software on rp2 **[unconfirmed]**) | no |
| Trust M | no | yes (but we only use the chip for the master PRF) | no |

Recommendation:
- **keccak for the WOTS chains.** It halves gas, and gas is paid every tx forever. Signing cost on the Pico is small either way (~1,500 hashes).
- The chip's SHA-256 only matters for the master PRF step, which is SHA-256 anyway (TLS-PRF). Then expand with keccak on the Pico.
- MicroPython users: add keccak as a C user module (XKCP compact). Pure-Python keccak would be far too slow **[est]**.
- n=32 today. n=24 is a fine later step: it cuts calldata 43%. With per-call tweaks (key index, chain index, position, and a per-account public seed) n=24 gives about NIST level 3 ([SPHINCS+ paper](https://sphincs.org/data/sphincs+-paper.pdf), [RFC 9858](https://www.rfc-editor.org/info/rfc9858/)).
- WOTS+C trick: grind a counter so the checksum is fixed. Removes checksum chains, shrinks the signature, and costs the signer a few thousand extra hashes ([RivaLabs](https://ethresear.ch/t/achieving-quantum-safety-through-ephemeral-key-pairs-and-account-abstraction/24273)).

---

## 4. Existing PQ hardware wallets

| Device | PQ for user funds? | Scheme | State / backup | Source |
|---|---|---|---|---|
| **EthereumPhone PQ1** | Yes (only one for Ethereum). Not shipped | SPHINCS+C10 (h=18, d=2, w=8), 4,008 B sig, SHA-256 | Stateless firmware. Contract caps 65,536 uses per key per chain. 24-word BIP-39 backup, entropy XOR-split across Trust M V3 + NXP SE050. 10 wrong PINs wipe. ERC-4337 account, CREATE2 same address on every chain | [PQ1 README](https://github.com/EthereumPhone/PQ1) |
| Trezor Safe 7 | No. Boot and firmware only | SLH-DSA-128 firmware check, ML-DSA-44 device cert | TROPIC01 + OPTIGA + STM32U5. User keys still ECDSA | [trezor.io](https://trezor.io/guides/trezor-devices/trezor-safe-7/the-first-quantum-ready-hardware-wallet) |
| Ledger | No | ML-DSA/ML-KEM in the OS SDK, no side-channel hardening in v1 | Donjon broke pqm4 code with ~40 EM traces | [Ledger SDK](https://www.ledger.com/blog-post-quantum-cryptography-ledger-sdk), [Donjon](https://www.ledger.com/blog-risk-side-channel-attacks-post-quantum-cryptography) |
| QRL Ledger app | Yes (QRL chain) | XMSS, 2 trees × 256 keys | Device holds the index. After restore, user sets the index by hand; QRL says track it "in a spreadsheet." Index reuse = forgery | [QRL docs](https://docs-archive.theqrl.org/wallet/ledger-nano-s/) |
| Foundation Passport Prime | No (Kyber for Bluetooth link only) | — | 2-of-3 Shamir on NFC cards | [nobsbitcoin](https://www.nobsbitcoin.com/foundation-announces-passport-prime-personal-security-platform/) |
| Keystone, GridPlus, Coldcard, Keycard, Tangem | No plans found | — | — | agent search, nothing found |
| Solana Winternitz vault (software) | Yes | WOTS, keccak truncated to 224 bits | Each spend moves funds to a fresh vault. No state | [repo](https://github.com/deanmlittle/solana-winternitz-vault) |
| Blockstream SHRINCS (Liquid, live Mar 2026) | Yes | Stateful compact path + stateless fallback | If the counter is lost, fall back to a 5,777 B stateless signature | [Blockstream](https://blog.blockstream.com/op_checkshrincs-a-hash-based-signature-opcode-for-post-quantum-bitcoin/), [cryptotimes](https://www.cryptotimes.io/2026/09/17/ledger-cto-reviews-shrincs-bitcoin-signature-proposal/) |
| Algorand | Yes (chain) | Falcon-1024 accounts (Algorand 5.0, Aug 2026) | Rekey to migrate | [algorand.co](https://algorand.co/blog/technical-brief-quantum-resistant-transactions-on-algorand-with-falcon-signatures) |

Lessons:
- PQ1 is the closest thing to what we want, and it uses Trust M V3 the same way: storage plus PIN counter, signing on the MCU. Read its Rust OPTIGA driver.
- Every stateful design (QRL, SHRINCS) lists restore-to-a-second-device as its biggest risk. SHRINCS and PQ1 both answer it with a stateless path. Our answer: the chain holds the state, and the backup uses a different key family (section 6).

---

## 5. Recommended design for Pico + Trust M V1

### 5.1 Key derivation

```
chip_secret          PRESSEC in Trust M, read=NEV, execute=ALW or gated (5.4)
acct_id              = keccak(chainId, ownerContract)   (or a CREATE2 salt chosen at init)
seed_k               = TLS-PRF-SHA256(chip_secret, "hs-v2" || acct_id || epoch || k)   32 B, exported
chain_sk[k][i]       = keccak(seed_k || i)               i = 0..66, on the Pico
step(x, k, i, j)     = keccak(x || pub_seed || k || i || j)
```

- One DeriveKey per key. Signing at index k also needs pkHash(k+1), so two DeriveKeys per signature. Cache pkHash(k+1) (it's public) to make it one.
- DeriveKey takes **~1.8 s measured on our V1 chip** (datasheet suggests ~50–135 ms; see [V1-DERIVEKEY-TEST.md](V1-DERIVEKEY-TEST.md)). Each one adds 1 to the Security Event Counter (measured). Using a persistent secret counts as a security event, so sustained use is about 1 per 5 s ([Infineon KB](https://community.infineon.com/t5/Knowledge-Base-Articles/OPTIGA-Trust-M-Security-monitor/ta-p/359081)). Fine for a wallet.
- **Put chain and account into the derivation.** See 5.5.
- Add a per-account public seed to every hash step (WOTS+ style tweak) to kill multi-target attacks across users.

### 5.2 What the chip does and doesn't buy us

| Threat | Chip helps? | Why |
|---|---|---|
| Flash dump of a lost/stolen Pico (RP2040 flash is readable) | **Yes** | Master secret isn't in flash |
| Firmware bug or power loss rolling back the "used index" record | **Yes** | Monotonic counter E120 never goes back (5.3) |
| Thief with the device, execute=ALW | **No** | Anyone on I2C can ask for any seed_k and forge |
| I2C sniffer while you sign | Partly | It sees seed_k for that key only (one-time anyway). Master stays safe |
| EUCLEAK EM attack | N/A for the PRF | EUCLEAK targets ECDSA. Unknown for TLS-PRF **[unconfirmed]** |
| Chip dies | **Makes it worse** | Secret is gone. Recovery must come from another owner (section 6) |

So the chip needs a gate (5.4) and the Safe needs an on-chain spending policy.

### 5.3 State rules (copy SP 800-208)

NIST SP 800-208 §8.1: "store the incremented leaf index value in nonvolatile storage before exporting a signature value" ([PDF](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-208.pdf)).

On the Pico:
1. Read Trust M counter E120 (value = lowest unused index).
2. Refuse to sign at k < counter unless the flash journal says (k, same digest). Then re-emit the same signature.
3. Write journal (k, digest) to flash.
4. Bump E120 to k+1 (monotonic, 600k updates max, [SPECS.md](SPECS.md)).
5. Derive, sign, **verify on device**, compare, release.

Notes:
- The chip doesn't bind the PRF label to the counter. A malicious firmware can still reuse an index. The counter protects against rollback and bugs, not against evil firmware.
- Optional: link the secret's execute rule to a counter with Luc (0x40). Then each DeriveKey bumps a counter and the chip refuses past a threshold. Infineon suggests capping shared-secret use at 2,048 this way ([SPECS.md](SPECS.md)). Gives a hard ceiling on total keys a thief can pull before the chip locks. Costs one NVM write per derive.
- The on-chain nonce is ground truth for what's spent. It is **not** ground truth for what's been signed. Signed-but-unsent signatures exist only on the device and wherever you sent them.

### 5.4 Gating the chip

V1 has no AUTOREF PIN object (V3 does). Options:

| Gate | How | Strength |
|---|---|---|
| Physical button per signature | Firmware waits for a press | Stops remote abuse only |
| Firmware PIN + RP2350 secure boot + OTP | PIN checked by signed firmware | RP2350's 2025 hacking challenge was broken by glitch/laser attacks; moderate |
| Shielded Connection with a PIN-derived binding secret | Set secret's execute rule to Conf(E140); E140 = KDF(PIN). No PIN → no handshake → no DeriveKey | **[unconfirmed]** whether failed handshakes count as security events (throttle). If 5 s/attempt, 6-digit PIN ≈ 58 days, 8-digit ≈ 15 years [est]. Note: locking execute to Conf(E140) is permanent ([OUR-USAGE.md](OUR-USAGE.md)) |
| **On-chain policy** | Safe guard: small spends immediate, big spends delayed N days with cancel by another PQ owner | Strongest. Works even if the device is fully compromised |

Recommend: button + on-chain policy now; test the PIN-derived Shielded Connection on a spare V1 chip.

### 5.5 Fixes for hashsig-safe

1. **Bind keys to chain and owner.** Today `secret(seed, k, i)` uses only the seed and index (`~/clawd/hashsig-safe/signer/wots.mjs`). One seed on two chains, or behind two owner contracts, = the same one-time key signing two messages. `state.json` blocks it, but only with one shared state file. Derive from (seed, chainId, owner, k, i).
2. **Port `Wots.recover` to Yul.** 206k → 79k [measured]. Needed to fit EIP-8141's 100k cap later.
3. **Store the key hash in the account's own storage** (or make the WOTS logic a Safe module / 8141-native account). EIP-8141's public mempool only lets validation read `tx.sender`'s storage.
4. **Add a generic signed `execute(target, data)`** so a WotsSafeOwner can act as a guardian or call recovery/delay modules, not just `approveHash`.
5. **Verify-before-release in the signer** (fault defense).
6. Consider n=24 and WOTS+C later to cut calldata ahead of EIP-7976.

### 5.6 Optional hybrid with P-256

The chip signs P-256 natively, and P256VERIFY costs 6,900 gas on mainnet ([EIP-7951](https://eips.ethereum.org/EIPS/eip-7951)). Requiring both a WOTS signature and a chip P-256 signature means a bug in our WOTS code alone can't drain the Safe. Cost: ~7k gas, a 5 s throttle per P-256 op, and EUCLEAK exposure for that key. Once ECDSA breaks, the P-256 half adds nothing, so make it removable.

### 5.7 C or MicroPython

- MicroPython: fine for UI, I2C, and the chip protocol (we already have it in wedgie). Keccak must be a C module.
- C (pico-sdk): faster keccak, hardware SHA on RP2350, easier constant-time and verify-before-release.
- Prefer **RP2350**: secure boot, OTP, glitch detectors, TRNG, SHA-256 hardware, 520 KB RAM.

---

## 6. Recovery and backup

### 6.1 How to provision the chip secret

| Option | How | Pros | Cons |
|---|---|---|---|
| A. Generated on chip, never seen | GenKeyPair a P-256 key on chip (non-exportable) → ECDH with a fixed public point → shared secret stays in a session context → DeriveKey from the session. The datasheet says session-context derives aren't even a security event ([Infineon KB](https://community.infineon.com/t5/Knowledge-Base-Articles/OPTIGA-Trust-M-Security-monitor/ta-p/359081)) | Host never sees the secret. No backup to steal | **Untested.** ECDH is a private-key op (5 s throttle). No backup at all. EM side channel on ECDH unknown |
| B. Host writes TRNG bytes, stores nothing | Chip TRNG → host RAM → SetDataObject PRESSEC → lock read=NEV | Simple. Tested today | Host saw it once. No backup |
| C. Written from a backed-up seed | BIP-39 → HKDF → PRESSEC | Restore to a new chip gives the same keys | Paper seed = full key. **Restore can reuse indexes** (signed-but-unsent sigs). This is QRL's failure mode |

**Recommend A or B for the device, plus a separate backup owner with its own seed (C-style paper, but a different key family).** The backup never derives the device's keys, so a restore can never reuse a device index. The backup's first and only job is to rotate in a new device.

If you do choose C anyway: after any restore, never resume the old key chain. Start a new epoch and install the new key through a recovery path, not by continuing at the on-chain index.

### 6.2 Recovery designs

All of these need every path, including the cancel path, to be PQ.

| Design | Setup | Normal use | Recovery | Gas / cost |
|---|---|---|---|---|
| **Paper WOTS guardian + timelock** (recommended) | Safe owner #1 = device WOTS owner. Recovery owner = WOTS key from a 24-word paper seed, acting only through a Delay module (e.g., 14 days) | Device only | Paper key signs one "swap owner" tx; waits 14 days; device can cancel | One WOTS sig (~280k today). Paper key used once, then re-key |
| Second device | Two Pico+chip devices, each its own WotsSafeOwner, threshold 1-of-2 or 2-of-2 | Either / both | Other device rotates in a replacement | Each device independent. No shared state |
| 2-of-3 | Device A, device B, paper | Any 2 | Any 2 replace the third | 2 WOTS sigs per tx |
| Social, hash-sig guardians | Candide-style module ([docs](https://docs.candide.dev/wallet/plugins/recovery-with-guardians/)), guardians are WotsSafeOwner contracts calling the module on-chain | Device | M-of-N guardians + delay, owner cancels | Needs generic `execute` (5.5 #4). No published hash-sig guardian design found **[unconfirmed gap]** |
| Commit-delay-reveal | Commit hash of a recovery secret on chain now; reveal after delay | — | Reveal preimage after delay | Works after an ECDSA break with no PQ sig at all ([Chaincode](https://chaincode.com/bitcoin-post-quantum.pdf)). Simplest possible guardian |

Reference delays: Safe/Candide 14 days, Safe RecoveryHub 28 days, Argent 36 hours ([Candide](https://docs.candide.dev/wallet/plugins/recovery-with-guardians/), [Sygnum](https://www.sygnum.com/news/safe-launches-saferecoveryhub-joining-forces-with-sygnum-bank-and-coincover-to-set-new-standard-for-crypto-recovery/), [Argent](https://support.argent.xyz/hc/en-us/articles/360008013258-How-to-add-a-guardian-to-your-Argent-Ethereum-wallet)).

A cheap PQ guardian idea: a **hash-preimage guardian**. Store `H(secret)` on chain. Recovery = reveal `secret` plus the new owner, start a timelock. Front-running risk: a mempool watcher sees `secret` and races. Fix with commit-then-reveal (commit `H(secret, newOwner)` first, reveal later). This is one-time use, which is all a recovery path needs.

Rules:
- No ECDSA guardian anywhere. One ECDSA guardian = the weakest link after a break.
- The cancel/veto path must be PQ too, or a forger cancels your rescue.
- Test recovery on a testnet Safe before funding.

---

## 7. Bridging today

### 7.1 What is exposed if ECDSA breaks

| Asset | Exposed? | Notes |
|---|---|---|
| EOA that has sent a tx | Yes | Public key is on chain |
| EOA never used to sign | Not until it spends | Spending shows the key in the mempool; needs private, fast inclusion. Drake's "bunker mode" advice |
| EOA delegated via 7702 | Yes | ECDSA stays master. No fix until 7851/8298/8164 ship |
| Safe with any ECDSA owner | Yes | Threshold doesn't help if the attacker forges enough owners |
| Safe with P-256 owners (passkeys, Trust M keys, our picowallet/wedgie-safe) | Yes (vs quantum) | Shor breaks P-256 too. A classical ECDSA break may or may not reach P-256 **[unconfirmed]** |
| Safe with only WOTS owners | **No** | Relayer EOA is the only ECDSA left, and it only holds gas money |
| Old off-chain signatures (Permit, Permit2, ERC-2612, Safe `signedMessages`) | Yes | Still valid. `signedMessages` on a Safe stay valid after owners change |

### 7.2 Safe migration steps

1. Deploy a WotsSafeOwner (or better, the v2 from 5.5).
2. One Safe tx (MultiSend): `addOwnerWithThreshold(wots, 1)`, `removeOwner` each ECDSA/P-256 owner, final threshold set.
3. Remove or audit every module and guard. Any module with an ECDSA key (4337 module signers, allowance delegates, recovery modules with ECDSA guardians) is a back door.
4. Revoke Permit2 and token approvals. Old `signedMessages` can't be un-signed, so if the Safe ever signed long-lived off-chain messages, move funds to a fresh Safe.
5. Add the PQ recovery path (6.2) and a Delay guard for big spends.
6. Test one small tx end to end.

Moving to a brand-new Safe whose owners were WOTS from day one is cleaner than cleaning an old one. It avoids leftover approvals and messages.

### 7.3 Gas sponsorship with an ECDSA relayer

- **What a forger can do:** take the relayer's ETH. Nothing else.
- **What they can't do:** change the Safe tx. The WOTS digest binds domain, chain id, owner contract, Safe, nonce, Safe tx hash and next key hash (`~/clawd/hashsig-safe/src/WotsSafeOwner.sol`).
- Keep the relayer balance small. Top it up per tx.
- If EOA txs are ever disabled (Vitalik's emergency plan), the relayer stops working. The long-term answer is an EIP-8141 frame tx where the Safe pays its own gas after a WOTS VERIFY frame.

### 7.4 Replay and front-running

| Risk | Status in hashsig-safe | Fix |
|---|---|---|
| Someone copies the signature from the mempool and submits it | Harmless. Same effect | — |
| Front-run with low gas so the inner Safe call fails | `approve` still burns the key and approves the hash. `approveAndExec` catches the failure | Anyone re-executes with `approvedSignature()`. Or use two txs: approve, then exec |
| Replay on another chain | Digest has chain id. Safe tx hash has chain id | OK |
| **Same seed on two chains/owners** | Keys derived from (seed, k, i) only. Different digests at the same k = forgery. Only `state.json` prevents it | Derive per (chain, owner) — 5.5 #1 |
| Restore from backup re-signs an index | Possible with option C | Use a different key family for backup (6.1) |
| MEV on the Safe tx content (swaps) | Normal sandwich risk | Private RPC / bundles |

---

## 8. Open questions and unconfirmed items

- Does a failed Shielded Connection handshake count as a security event on V1? Decides whether a PIN-derived E140 is a real PIN gate.
- Does the ECDH → session → DeriveKey path (option A) work on V1 with export? Untested.
- MicroPython `hashlib.sha256` speed on RP2040 and whether rp2 uses the RP2350 SHA unit. Not found. Measure.
- Our RP2040/RP2350 sign times are estimates from hash speeds. Measure on hardware.
- WOTS+C 468 B size: parameters not checked.
- EIP-8141 details (100k cap, sender-storage rule) can still change before Hegotá.
- ZKnox Dilithium numbers disagree between repo and blog.
- EIP-8288 (a BLS-successor EIP) mentioned in one paper, not verified.
- leanVM switch to BLAKE2s: one PR only.
- Whether a classical "AI" ECDSA break would also hit P-256. Unknown.

---

## Appendix: our gas test

Foundry, solc optimizer 200 runs, 50 random digests, external call, `gasleft()` delta. Signature bytes in memory/calldata of the call, not tx calldata.

| Variant | Avg gas |
|---|---|
| Naive Solidity, w=4, keccak | 210,285 |
| Naive Solidity, w=16, keccak | 206,414 |
| Naive Solidity, w=256, keccak | 1,116,979 |
| Naive Solidity, w=4, SHA-256 precompile | 254,677 |
| Naive Solidity, w=16, SHA-256 precompile | 316,123 |
| Naive Solidity, w=256, SHA-256 precompile | 2,056,627 |
| **Yul, w=16, keccak** | **79,159** |
| Yul, w=16, SHA-256 precompile | 161,897 |

The Yul loop: one 64-byte scratch buffer, `mstore(buf, x)`, `mstore8` the position byte, `keccak256(buf, 0x40)`, 67 chains, then keccak over the 67 ends. About 157 gas per average step including loop overhead [est from totals].

## Sources (main)

- EIP-8141: https://eips.ethereum.org/EIPS/eip-8141
- ACDE #244 write-up: https://christinedkim.substack.com/p/acde-244
- Vitalik emergency plan: https://ethresear.ch/t/how-to-hard-fork-to-save-most-users-funds-in-a-quantum-emergency/18901
- pq.ethereum.org: https://pq.ethereum.org/
- Bunker mode: https://www.coindesk.com/tech/2026/10/08/bitcoin-and-ether-holders-urged-to-prepare-bunker-mode-against-possible-ai-attacks
- Hash-based multisigs for PQ Ethereum: https://eprint.iacr.org/2025/055
- leanSig note: https://eprint.iacr.org/2025/1332.pdf
- leanMultisig: https://github.com/leanEthereum/leanMultisig
- EIP-7619 / 7885 / 7932 / 8051 / 8052 / 8164 / 8298 / 7851: https://eips.ethereum.org/
- AppliedPQC survey: https://github.com/AppliedPQC/pqc-research/issues/35
- PQBeat: https://github.com/ZKNoxHQ/PQbeat
- ZKnox ETHFALCON: https://zknox.eth.limo/posts/2025/03/21/ETHFALCON.html
- Fireblocks ML-DSA: https://www.fireblocks.com/blog/post-quantum-signatures-ethereum-cheaper-gas
- SPHINCS− on EVM: https://ethresear.ch/t/sphincs-minus-efficient-stateless-post-quantum-signature-verification-on-the-evm/25165
- RivaLabs WOTS+C / FORS+C: https://ethresear.ch/t/achieving-quantum-safety-through-ephemeral-key-pairs-and-account-abstraction/24273
- XMSS Solidity: https://github.com/skalenetwork/xmss-solidity
- EIP-7623: https://eips.ethereum.org/EIPS/eip-7623 · EIP-7976: https://eips.ethereum.org/EIPS/eip-7976
- pqm4: https://github.com/mupq/pqm4/blob/master/benchmarks.md
- ML-DSA on RP2040: https://arxiv.org/html/2603.19340v5
- SP 800-208: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-208.pdf
- SP 800-230 ipd: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-230.ipd.pdf
- Grafting trees fault attack: https://eprint.iacr.org/2018/102.pdf
- EthereumPhone PQ1: https://github.com/EthereumPhone/PQ1
- Trezor Safe 7: https://trezor.io/guides/trezor-devices/trezor-safe-7/the-first-quantum-ready-hardware-wallet
- Ledger PQ SDK: https://www.ledger.com/blog-post-quantum-cryptography-ledger-sdk
- Blockstream HW wallet PQ test: https://blog.blockstream.com/hardware-wallets-post-quantum-signatures/
- QRL Ledger: https://docs-archive.theqrl.org/wallet/ledger-nano-s/
- Solana Winternitz vault: https://github.com/deanmlittle/solana-winternitz-vault
- Candide recovery: https://docs.candide.dev/wallet/plugins/recovery-with-guardians/
- Trust M security monitor: https://community.infineon.com/t5/Knowledge-Base-Articles/OPTIGA-Trust-M-Security-monitor/ta-p/359081
- RP2350 datasheet: https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf
