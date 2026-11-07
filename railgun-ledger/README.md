# RAILGUN on a Ledger, and could a wedgie do it

Researched 2026-11-07, from [RAILGUN's tweet](https://x.com/RAILGUN_Project/status/2118744304755573001) (Nov 6).

## What shipped

- [Anon](https://anon.inc/#ledger) (anondotinc) wallet: a Ledger now signs every RAILGUN private send, swap and unshield.
  The spending key stays on the Ledger. Anon keeps the viewing key so it can show balances.
- Nano S Plus (USB) and Flex (USB + Bluetooth). Browser extension, iPhone, Android.
- The Ledger app is **sideloaded** ("Allow unsafe manager"), not in Ledger Live's store.
- Code: [Railgun-Community/ledger-client](https://github.com/Railgun-Community/ledger-client) (MIT, pre-1.0).
  The crypto library is ZKNOX's ([ZKNOX-HW-PRIVACY](https://github.com/ZKNoxHQ/ZKNOX-HW-PRIVACY), Apache-2.0, unaudited).

## How it works

- A RAILGUN tx needs a **BabyJubJub EdDSA-Poseidon signature** from the spending key. It is checked *inside the
  zk circuit*, never posted on chain. So the device only has to sign; the phone/computer makes the proof.
- Message signed = Poseidon(merkleRoot, boundParamsHash, nullifiers…, commitments…). The Poseidon width is
  `nIn + nOut + 2`, so every tx shape needs its own constants table. That is what blocked hardware wallets
  ([krnak's write-up](https://hackmd.io/@krnak/S1gZ_hr6We)).
- Spending key path: `m/44'/9075'/0'/0/0`.
- Two modes:
  - **Blind** (`SIGN_HASH`, INS 0x12): device signs a 32-byte hash it can't check. Works for any shape.
  - **Clear** (`CLEAR_SIGN`, INS 0x11, *experimental*): host streams merkle root, nullifiers, bound params, and
    each output (transfer / change / broadcaster fee / unshield). The device rebuilds the hash, shows
    recipient/token/amount, signs, and **encrypts the output notes itself** (so it also holds the viewing key).
    Capped at `nIn ≤ 4, nOut ≤ 3, nIn+nOut ≤ 5` to fit Ledger flash. Bigger txs fall back to blind.
- The repo's own doc says the engine side of clear signing is not finished. So today's Anon flow is likely
  blind signing for at least some txs. Not confirmed.
- Shield (public → private) uses the normal Ledger Ethereum app. 7702 relay signing is still "under development".

## Can the wedgie do it?

Yes. Signing is easy; key storage is the weak point.

**Easier than Ledger**
- No sideload gate. An app is MicroPython plus a C module, like `wedgie-pq`'s Poseidon2 module.
- 2 MB flash fits Poseidon constants for every width (rough guess ~400 KB for t=2..17), so no 5-slot cap on clear signing.
- Bigger screen for showing recipients, amounts, blockies.

**Weaker than Ledger**
- The Trust M / ATECC608 can't do BabyJubJub. The key has to exist in the Pico's RAM while signing.
- Best option: derive it each time from a locked Trust M secret (`DeriveKey`, tested at 1.8 s; same plan as the PQ wallet).
  The key never sits in flash, but anyone holding the wedgie can trigger a derive unless we add a PIN.
- Ledger has a PIN and a secure element doing the math. This is closer to a "smart Pico wallet" than a Ledger.

**Speed (guess, not measured)**
- RP2040 is a Cortex-M0+ with no 64-bit multiply. A 254-bit field multiply in C is maybe 30–80 µs.
- One Poseidon (t≈7) ≈ 3,500 multiplies, one EdDSA sign ≈ 5,000. Roughly 0.3–1 s to sign, a few seconds with note encryption. Fine.

**Build plan**
1. C module: BN254 field, circomlib Poseidon (all widths), BabyJubJub EdDSA. Port from ZKNOX-LibC or write it;
   test against circomlibjs vectors.
2. Blind sign over WebSerial: wedgie shows the hash blockie, A signs.
3. A WebSerial `HardwareConnector` with the same shape ledger-client exposes (`sign`, `getPublicKey`,
   `requestBatchApproval`, …) so a RAILGUN engine wallet can use it.
4. Somewhere to use it: a wedgie.dev/railgun page on the RAILGUN engine (we own it), or ask Anon to add a
   wedgie connector (their call). Note ledger-client targets the engine's multi-sig-wallet branch, not mainline.
5. Clear signing: rebuild commitments, decode `0zk…` addresses, encrypt notes on the wedgie.

Rough effort: blind signer a few days, clear signing another week or two.
