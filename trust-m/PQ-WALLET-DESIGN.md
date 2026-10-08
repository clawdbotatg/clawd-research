# Best PQ wallet with a Trust M V1 (design, 2026-10-08)

Built from: [AI-VS-ECC.md](AI-VS-ECC.md), [PQ-WALLET-LANDSCAPE.md](PQ-WALLET-LANDSCAPE.md),
[V1-DERIVEKEY-TEST.md](V1-DERIVEKEY-TEST.md), [OUR-USAGE.md](OUR-USAGE.md), and `~/clawd/hashsig-safe`.

## Why

- No public attack on secp256k1 or P-256 exists today. The AI scare is opinion plus fast AI math progress.
- Quantum cost estimates for breaking ECC keep dropping. That part is real.
- Any key whose public key is on chain is exposed if ECC breaks. That includes our P-256 chip keys
  used as Safe owners: x,y are public from day one.
- Hash-based signatures only depend on the hash function. They survive both AI and quantum attacks on ECC.

## The design in one picture

```
 Trust M V1                    Pico (RP2350)                          Chain
 ───────────                   ─────────────                          ─────
 master secret K               shows tx, waits for button
 (PRESSEC, read=NEV)  ──PRF──▶ seed_k (32 B, 1.8 s)
 counter E120 = next k         expands 67 WOTS chains (keccak)
                               signs digest, commits pkHash(k+1)
                               verifies its own sig, then releases ──▶ Safe
                                                                      └ only owner: WotsSafeOwner
                                                                        accepts index k once, stores pkHash(k+1)
                                                                      └ recovery: paper WOTS owner via 14-day delay,
                                                                        device can cancel
```

## Parts

| Part | Choice | Why |
|---|---|---|
| Signature | WOTS w=16, keccak, one key per tx, each sig commits the next key | No RNG, no float, no tree. Chain holds the state. Already built (hashsig-safe). |
| Secure chip | Trust M V1 (our 300) | Holds master secret K. Never reveals it (tested). Turns K into per-tx seeds. |
| MCU | RP2350 | Secure boot, OTP, glitch detectors, hardware SHA, room for keccak in C. |
| Screen + button | Required | Chip has no user check. The button is the gate. |
| Account | Safe, WotsSafeOwner as the **only** owner | Any ECDSA/P-256 owner left on the Safe is the weak link. |
| Recovery | Separate paper WOTS owner behind a 14-day delay | K can't be backed up. Backup must be a different key family so restore never reuses an index. |
| Gas | ~280k now, ~79k with a Yul verifier (measured) | Fits EIP-8141's 100k cap later. |

## Key derivation

```
K          = 32 random bytes in Trust M, type PRESSEC, use=ALW, read=NEV, lifecycle locked
acct       = keccak(chainId, ownerContract)
seed_k     = TLS-PRF-SHA256(K, "pqw1" || acct || epoch || k)      on chip, 1.8 s
sk[k][i]   = keccak(seed_k || i)   i = 0..66                       on Pico
```

`acct` in the derivation fixes the hashsig-safe bug: today one seed on two chains or two owners
gives the same one-time key, which can then sign twice.

## Signing flow

1. Host sends the Safe tx. Pico computes the Safe tx hash itself and shows what it does.
2. User presses the button. No press in 2 minutes = no.
3. Pico reads counter E120. Refuse if k < counter, unless the flash journal has (k, same digest): then resend that same signature.
4. Write (k, digest) to the journal. Bump E120 to k+1. Only then derive.
5. Derive seed_k and seed_{k+1} (cache pkHash(k+1) to skip one). Sign. Verify on device. Release.

About 2–4 s per signature, mostly the chip.

## What it stops and what it doesn't

| Threat | Stopped? |
|---|---|
| ECDSA / P-256 broken by AI or quantum | **Yes.** Nothing on chain depends on ECC (relayer EOA only loses gas). |
| Lost or stolen device, flash dumped | **Yes.** K isn't in flash. |
| Firmware bug or power loss reusing an index | **Yes.** Chip counter never goes back; contract accepts each index once. |
| Thief with the device who can run code on the Pico | **No.** They can ask the chip for future seeds. Secure boot + the on-chain delay are the defense. |
| Thief with the device, signed firmware intact | Mostly. Needs the button; add a firmware PIN. |
| Chip dies | Recovered by the paper owner after 14 days. |
| EM side channel on the chip | Unknown for the PRF. EUCLEAK targets ECDSA, which this design doesn't use for funds. |

## Hardening steps on V1

- Lock K: after provisioning, set the object's lifecycle to operational so read=NEV can never be flipped back.
- Optional hard cap: link K's use rule to a monotonic counter (Luc). The chip refuses past N derives,
  so a thief can pull at most N keys.
- Optional bus lock: set K's use rule to Conf(E140) (Shielded Connection), with E140 = KDF(PIN) or a secret
  in RP2350 OTP. Untested. Permanent once set. Try on a spare chip first.
- Give each app its own slot. picowallet and wedgie-safe both use E0F1 today.

## Build order

1. hashsig-safe fixes: bind keys to chain+owner, Yul verifier, generic `execute`, verify-before-release.
2. Pico signer: DeriveKey + keccak WOTS in C, counter journal, screen + button. Reuse wedgie's `optiga` driver.
3. Provisioning tool: TRNG → K into a PRESSEC slot → lock. Never store K.
4. Recovery: paper WOTS owner + Delay module + device cancel. Test the whole loop on a testnet Safe.
5. Migrate: swap every ECDSA/P-256 owner on real Safes for the WOTS owner. Revoke old Permit2 approvals.

## Open questions

- Exact minimum DeriveKey input length (4 bytes failed, 15 worked).
- Does a failed Shielded Connection handshake slow down PIN guessing? (decides the PIN design)
- Can K be made on chip without the host ever seeing it (ECDH into a session, then DeriveKey)? Untested.
- Lock behavior: confirm a locked PRESSEC object still allows DeriveKey.
