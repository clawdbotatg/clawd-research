# Slots, write limits, and rolling keys (2026-10-08)

Source for the numbers: [SPECS.md](SPECS.md) §6.1 (Infineon SRM Tables 68–79, §5.1).

## Slots

| Slot | What's in it | Size | Rated writes |
|---|---|---|---|
| E0F0 | Factory key | P-256 key | never (locked) |
| E0F1–E0F3 | Your ECC signing keys | 1 key each | ~100 each |
| E0FC–E0FD | RSA keys | 1 key each | ~100 each |
| E0E0–E0E3 | Certificates | ≤1.7 KB each | ~100 each |
| F1E0–F1E1 | Big data | 1,500 B each | ~100 each |
| F1D0–F1DB | Small data | 140 B each | 200,000 total, shared by all 12 |
| E120–E123 | Monotonic counters | 8 B each | 600,000 each |
| E100–E103 | Session (RAM) keys | — | unlimited, wiped at power-off |

- Writing wears storage. Using a key (sign, derive) does not.
- "~100" is Infineon's number for full 20+ year retention, not a hard stop. After ~20k writes, retention drops to ~2 years.
- Whole-chip budget: ~2 million writes.
- Why only ~100 on key slots: Infineon doesn't say. Likely that storage is built for write-once, keep-forever.
- Only key slots (and RAM slots) can sign. A key in a data slot can't do ECDSA. A secret in a data slot can only feed DeriveKey/HMAC.

## Option 1: rolling P-256 keys (hash on chain)

Keep the public key off chain until it's used:

1. Contract stores `hash(pubkey_k)`.
2. To sign: send `pubkey_k` + signature. The signed message includes `hash(pubkey_{k+1})`.
3. Contract checks the hash, verifies P-256 (precompile, ~7k gas), stores the next hash.
4. Each key signs once.

Good:
- Private key never leaves the chip (GenKeyPair on chip).
- Cheap: ~7k gas to verify.
- One signature per key, so EUCLEAK (needs ~40 signatures) can't work.

Bad:
- Each new key is a key-slot write: ~100 per slot, ~300 total at full rating.
- RAM slots don't wear, but the key is gone at power-off (then recovery is needed).
- The public key is visible between broadcast and inclusion. An attacker who breaks ECC in seconds could front-run. Private mempool or commit-reveal fixes it.
- Still elliptic-curve. Fails if ECC breaks fast enough.

## Option 2: hash signatures (WOTS) from one stored secret

- Write one secret into a small data slot once (PRESSEC, read=never). Tested: [V1-DERIVEKEY-TEST.md](V1-DERIVEKEY-TEST.md).
- The chip makes a fresh seed per signature (1.8 s). The Pico builds the WOTS key.
- Nothing new is written per signature, so no wear. Unlimited keys.
- Not elliptic-curve. Survives ECC breaks.
- Weak spot: the one-time key passes through the Pico.

## Summary

| | Rolling P-256 | WOTS from stored secret |
|---|---|---|
| Survives ECC break | Only if the break is slower than block inclusion | Yes |
| Key leaves chip | No | Per-signature key does |
| Chip wear | ~100 keys per slot | None |
| Gas | ~7k + calldata | ~79k (Yul) to ~280k |

Plan: WOTS as the real owner. Rolling P-256 optional for small daily spending.
