# V1 chip as a locked secret + one-time key maker (tested 2026-10-08)

Chip: the Trust M in Austin's wedgie (V1, cert issuer "Trust M CA 101", 2019).
UID (E0C2): `cd16338401001c000100000a091b5c000b000d0061801010710809`.
Driven over USB with `mpremote run` using the wedgie firmware's `optiga.Chip` driver.
Slot used: data object `F1DA` (was all zeros). Restored to zeros after every run.

## Result

V1 can hold a secret it will never give back, and still turn it into keys for us.

1. Write a 32-byte secret into `F1DA`.
2. Set metadata: type PRESSEC (`E8=21`), use rule always (`D3=00`), read rule never (`D1=FF`).
3. Reading `F1DA` now fails: error `0x07` (access conditions not satisfied).
4. DeriveKey still works and returns the key to the host.

Output matched a host TLS-PRF exactly:

| Input (label+seed) | Chip output = host TLS-PRF-SHA256(secret, input) |
|---|---|
| `wots-index-0007` | `3925de7e1dd0d0d213c277ef63626cec5bd7fea4d9bcbdcba4bf4c26952cb10b` |
| `wots-index-0008` | `a265c1e8df2f7ae9fb0fda71ddb88ab1e25a6c6dd82ee9bf1e98b4bc5c48743b` |

(Test secret was bytes 1..32. Not a real key.)

## DeriveKey APDU

Command `0x34`, param `0x01` = TLS 1.2 PRF SHA-256. Data is TLVs:

```
01 0002 <secret OID>           e.g. F1DA
03 0002 <output length>        16..256
02 <len> <label||seed>         see min length below
07 0000                        export result to host
```

From Infineon `src/cmd/optiga_cmd.c` (DeriveKey handler).

## Timing and throttle (40 runs)

| What | Result |
|---|---|
| DeriveKey, 32-byte output | **~1.81 s each**, steady (1807–1826 ms) |
| DeriveKey, 16-byte output | 1.83 s |
| DeriveKey, 256-byte output | 10.1 s |
| SHA-256 of 64 bytes (CalcHash), for comparison | 32 ms |
| Security Event Counter (E0C5) | 0 → 26 after 40 derives (each derive adds 1; it drops ~1 per 5 s) |

The throttle starts at SEC ≥ 128, so one derive per signature at human pace never hits it.

## Gotchas

- Without `D3` set, DeriveKey fails `0x07`. The default use rule on data objects is "never".
- Input `idx0` (4 bytes) failed with `0x05` (invalid parameter). 15–16 bytes worked. Exact minimum not pinned down.
- Read rule `NEV` can be undone while lifecycle < operational (change rule `D0 = LcsO < 07`). Real use must lock it: set lifecycle to operational after provisioning, or anyone with I2C access can flip read back to always and read the secret.
- After restore, `F1DA` metadata carries an explicit `D3=FF` that wasn't there before. Same behavior (never).
- `F1DB` on this chip holds 140 bytes of `0x77` from some earlier test. Left untouched.
- The port is held by any Chrome tab using WebSerial (wedgie / slop.computer). Close them or replug the Pico.

## What it means for a PQ wallet

- One chip call per signature (~1.8 s) gives a 32-byte per-index seed. The Pico expands the 67 WOTS chain keys from it.
- Master secret never leaves the chip. Each one-time key does leave, which is fine: the signature reveals it anyway.
- Anyone who controls the Pico (or the I2C bus) can ask for future indexes. Gate it: PIN, button, and the on-chain contract that only accepts the next index.
