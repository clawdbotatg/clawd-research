# How a wedgie could sign for RAILGUN

Deep dive, 2026-11-09. Detail and citations: `notes/railgun-side.md` (RAILGUN side), `notes/perf.md` (speed).
Nothing here is built or measured on a device yet.

## Short version

RAILGUN's own wallet SDK already accepts any hardware signer. The wedgie only has to answer one call:
"sign this hash" with a BabyJubJub key. No help from Anon or Ledger needed. We'd build a
wedgie.dev/railgun page on that SDK, and a wedgie app plus a C module for the math. About 1 second per
signature on today's RP2040. The weak spot is the key: it has to sit in the Pico's memory while signing.

## How the pieces fit

```
wedgie.dev/railgun (browser)                         wedgie (RP2040)
- RAILGUN wallet SDK 11.3.0                          - railgun app (MicroPython)
- holds viewing key: scans balance, history          - rg C module: BN254 math, Poseidon,
- builds tx, makes the zk proof (snarkjs)              BabyJubJub EdDSA, blake512
- WebSerial connector object  ── JSON lines ──▶      - shows the tx, A = sign
- sends via a RAILGUN broadcaster (pays gas)  ◀──    - returns R8x, R8y, S
```

- SDK: `createHardwareRailgunWallet(encKey, shareableViewingKey, blocks, connector, accountIndex)`.
  The wallet is view-only on the host; spending goes through `connector.sign(hash, publicInputs, …)`.
  Merged in engine 9.6.0; the SDK never imports Ledger code, so a second device needs no engine change.
- The connector is a small JS object: `sign`, `getPublicKey`, `requestBatchApproval`, `isConnected`,
  `disconnect` (+ `signClearMultiTransact` for clear signing). We write it over the wedgie's existing
  WebSerial JSON-line channel, the same way /safe talks to the Safe app.
- The proof is made in the browser. The wedgie never sees it.

## Keys

- RAILGUN keys come from a normal 12/24-word seed: HMAC-SHA512 "babyjubjub seed", then hardened paths
  `m/44'/1984'/0'/0'/0'` (spending, BabyJubJub) and `m/420'/1984'/0'/0'/0'` (viewing, ed25519).
  Same as Ledger's app and RAILGUN's wallets. Use account 0 only (other indexes don't match between
  Ledger's app and the engine).
- The Trust M can't do BabyJubJub. So:
  1. Wedgie makes a seed from the chip's random, shows the words once for backup.
  2. Seed goes into a free Trust M data slot (DATA 0–8), set never-readable.
  3. To sign: chip `DeriveKey` (1.8 s) → seed-derived bytes in Pico RAM → derive spending key → sign → wipe.
- Backup words work in any RAILGUN wallet (Railway, Anon) if the wedgie is lost.
- Viewing key goes to the browser once (Ledger does the same, behind an "Allow viewing access" screen).

**Honest gaps vs a Ledger**
- Key is in Pico RAM during signing; the Pico has no secure enclave.
- No PIN on the wedgie today (`PLAN-PIN.md` is a plan). Anyone holding it can sign if they press A.
- BN254 math in C won't be hardened against power/timing attacks.
- The RP2350 "money wedgie" (secure boot, OTP) would close some of this.

## Two signing modes

**1. Blind (build first).** Host sends a 32-byte hash. Wedgie shows a blockie of it, A signs.
Needs only Poseidon with 5 inputs + EdDSA. Works for every tx shape. Same as Ledger's `SIGN_HASH`.

**2. Clear (build second).** Host sends merkle root, nullifiers, bound params, and each output
(transfer to a `0zk…` address, change, broadcaster fee, unshield). The wedgie:
- decodes the 0zk address and shows it with amount and token;
- picks each note's random, computes the note commitments itself;
- encrypts each note (ed25519 key exchange + AES-256-GCM with its viewing key);
- rebuilds the signed hash and signs.
Copy Ledger's message layout (`ledger-client/src/core/transport/clear-sign-apdu.ts`) so the engine's
clear-sign path works unchanged.

**Where the wedgie can beat Ledger**
- Ledger caps clear signing at inputs+outputs ≤ 5 (Poseidon width 7). The wedgie can rebuild round
  constants at runtime like Ledger does, or store tables for more widths, and support every shape (max 16).
  All tables = 770 KB, too big for the 256 KB app cap; widths ≤ 8 = ~120 KB fits.
- Ledger takes nullifiers on trust. The wedgie holds the nullifying key and could recompute them from
  leaf indexes, and even check the merkle proofs (~0.6 s extra).
- Bigger screen: full 0zk address, blockies, a page per output.

## Speed (estimated, not measured)

| | RP2040 C | RP2350 C |
|---|---|---|
| One Poseidon (t=7) | ~100 ms | ~11 ms |
| One EdDSA sign | ~140 ms | ~16 ms |
| Blind sign total | ~0.3 s | ~0.05 s |
| Clear sign, 2 in / 3 out | ~0.9 s | ~0.13 s |
| + chip DeriveKey | +1.8 s | +1.8 s |

So ~2–3 s from A press to signature. Hand-written assembly would roughly halve the math time.

## What doesn't need the wedgie

- **Shield** (public → private) is a normal Ethereum tx. The wedgie has no secp256k1 key, so shield
  from MetaMask, or from the wedgie's Safe (Safe Signer app) sending to the wedgie's 0zk address.
- **Gas** for private sends: RAILGUN broadcasters (SDK supports them in the browser), paid from the
  private balance. No public wallet needed.
- **Unshield** to any address: a normal clear-signed tx with an unshield output.

## Fit with the wedgie today

- Wire: JSON lines ≤ 6 KB. A clear-sign request is ~1–2 KB. Fine.
- RAM: ~70–150 KB free for an app. The C module plus buffers fits; reserve buffers at boot like Safe does.
- C modules: same build as `wedgie-pq`'s Poseidon2 module (armv6m, `.mpy`). Nothing for BN254,
  BabyJubJub, ed25519 or blake512 exists on the device yet.
- Trust M slots: use DATA 0–8 for the seed. KEY2/KEY3 and DATA 9–11 are taken.
- Test on wedgie.dev/virtual first (real RAM limits, software Trust M).

## Build plan

1. **C module** `rg`: BN254 Fr multiply, circomlib Poseidon, BabyJubJub points, EdDSA-Poseidon, blake512.
   Test against circomlibjs vectors on the Mac, then the virtual wedgie. ~1 week.
2. **Key setup** in the app: make seed, show words, store in Trust M, show the 0zk address. ~2 days.
3. **Blind sign** over WebSerial + JS connector + wedgie.dev/railgun page on the SDK (balance,
   send, unshield, broadcaster). ~1 week. First real private send here.
4. **Clear sign**: 0zk decode, note commitments, ed25519 + AES-GCM note encryption, review screens.
   ~1–2 weeks.
5. Later: nullifier/merkle checks on device, PIN, RP2350.

## Open questions

- RAILGUN's Ledger firmware source isn't public; layouts above come from its released binary and the client lib.
- Engine 9.9.1 allows ≤ 3 inputs in clear sign; ledger-client allows ≤ 4.
- Whether Anon would add a wedgie connector (their call; not needed for our own page).
