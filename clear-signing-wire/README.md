# Clear signing: what actually goes over the wire to a hardware wallet

Research 2026-09-27, read from source (app-ethereum @5a48940, device-sdk-ts @7bc0bb4a,
python-erc7730 @72c0fb8, registry @53d86dc, ERCs @bd8c36bc, trezor-firmware @3227ea8,
keystone3, gridplus-sdk, bitbox02, keycard-shell).

Detail files:
- [LEDGER-WIRE.md](LEDGER-WIRE.md) — every INS, every TLV tag, trust keys, backend URLs, byte examples
- [ERC7730-PIPELINE.md](ERC7730-PIPELINE.md) — the JSON spec (v2.1.0), registry → converter → CAL → device, what gets dropped
- [OTHER-WALLETS.md](OTHER-WALLETS.md) — Trezor, Keystone, GridPlus, BitBox02, Keycard wire formats + lessons for a small MCU
- [ledger-usdc-transfer-example.py](ledger-usdc-transfer-example.py) — builds the APDUs for a USDC transfer (unsigned; not run on a device)

Earlier authoring-side research (descriptor → registry PR): `~/clawd/clawd-harness/projects/clear-signing-skill/docs/RESEARCH.md`.

## The one-paragraph version

ERC-7730 is a JSON file. **The device never sees it.** Each vendor compiles it on its own
server into a small binary, signs that with its own key, and the host streams the binary to
the device next to the tx. On Ledger that's TLV over APDUs; on Trezor it's a protobuf with a
Merkle proof. The two formats and keys are incompatible. There is no shared device wire format.

## Ledger flow for one contract call

```
host                                              device (Ethereum app)
E0 04 00 01  SIGN "store"  (path + unsigned tx) → parse, keep calldata in RAM, no UI
B0 06 0B 00  load PKI cert (usage 11 = calldata) → OS holds the key for next check
E0 26        TRANSACTION_INFO TLV (signed)        → check chain/addr/selector vs stored tx
             {chain, addr, selector, FIELDS_HASH, "Send", creator, contract name, sig}
  per field:
  E0 0A/14/22/24  token / NFT / trusted name / enum (each signed, own cert)
  E0 28        FIELD TLV (NOT signed)             → running SHA3-256 over field bytes
             {label, param type, path into calldata}
E0 04 00 02  SIGN "start"                         → hash == FIELDS_HASH? show screens, sign
```

Key points:
- **Only TRANSACTION_INFO is signed.** It commits to `FIELDS_HASH` = SHA3-256 (FIPS, not keccak)
  of all FIELD TLVs in order. So fields are authenticated, ordered and complete without each
  carrying a signature.
- **The device reads values itself.** A FIELD carries a *path* (TUPLE n / REF / ARRAY / LEAF /
  SLICE steps over 32-byte ABI words), not the value. The host can't lie about amounts or
  addresses; it can only pick which signed descriptor to send, and the device checks that
  descriptor against chain + address + selector of the tx it stored.
- Signatures: secp256k1 ECDSA over SHA-256, DER. Keys come from a PKI cert loaded right before
  (`B0 06 <usage>`), fetched from `global.api.prd.ledger.com/cal/v1/certificates`. Descriptors
  come from `…/cal/v1/dapps?output=descriptors_calldata`.
- Trusted names (ENS etc.) and proxy info need a fresh `GET_CHALLENGE` nonce, so they can't be replayed.
- Nested calldata (Safe execTransaction, multicall-ish) = a second TRANSACTION_INFO pushed mid-field-loop.
- No descriptor → plain SIGN → "enable blind signing" wall.
- EIP-712 is a separate, older path: send struct defs + values field by field (`E0 1A`/`E0 1C`),
  with per-field signed "filters" (`E0 1E`) that give labels/formats. Much lossier than calldata.

## Who signs what (the real trust model)

| Layer | Signer | What the device trusts |
|---|---|---|
| ERC-7730 JSON in the EF registry | nobody (CI + human review) | — |
| ERC-8176 auditor attestation | EAS offchain; today 1 auditor (Cyfrin), 174 attestations | nothing — no firmware checks it |
| Ledger TLV | Ledger CAL key via PKI cert | this |
| Trezor protobuf | SatoshiLabs CoSi Ed25519, Merkle root over ~58K defs | this |

The auditor signs the JSON; the device verifies the vendor's compiled blob. Anything the
converter drops is invisible to the auditor.

## What gets lost converting ERC-7730 → Ledger

- `interpolatedIntent` dropped entirely. `intent` must be a string ≤30 chars.
- Labels ≤20 chars, enums ≤255 values (1 byte), ≤5 constraints, only on raw/addressName.
- EIP-712 path: enum/unit/duration fall back to RAW, no "Unlimited" threshold, `mustMatch` not enforced.
- Device can't do ARRAY_LEAF / TUPLE_LEAF paths yet. Multicall / Universal Router / Safe MultiSend
  can't be described at all (ERC PR #1402 open).

## Trezor (the other real implementation, live 2026-09-08)

- Device *pulls* metadata: `EthereumDefinitionRequest{chain, address, selector}` →
  host replies with a signed blob from `data.trezor.io/.../display-format/<addr>-<sel>.dat`.
  Works for nested calls too, since the device names what it needs.
- Blob = `"trzd" | ver | type | data_version | protobuf | merkle proof | CoSi sig`. A version floor
  in firmware makes old definitions expire.
- 8 formatters; clear-signs only if calldata ≤ 6 KB. EIP-712 still shows raw fields.

Keystone (SD-card ABI DB, apparently unsigned), GridPlus (host-fetched ABI, unsigned) and
BitBox02 (ERC-20 transfer only) have no ERC-7730 support.

## If we build our own device

The best design so far combines the Ledger and Trezor ideas:
1. Compile on the host, sign, and never parse JSON on the device. The device needs an ABI
   word-walker plus about 8 formatters.
2. The device reads values from calldata by path (Ledger). Check chain, address and
   selector on the device.
3. One signed header commits to a hash of the field list (Ledger `FIELDS_HASH`), or sign
   a Merkle root (Trezor). Either way the device only has to check one signature.
4. The device pulls the metadata it needs (Trezor). This handles nested calls cleanly.
5. Use a version floor, and a nonce for anything that resolves names.
6. Open question: whose key? Our own pipeline (registry + attestation policy + our key), or
   Trezor's public blobs as an unofficial dependency. No cross-vendor format exists yet, so
   there's room to propose one.

## Flags

- Ledger's docs say TX_INFO/FIELD version 0; the device code requires 1.
- How Ledger's CAL imports from the registry is closed source. We assume it runs python-erc7730
  or something equivalent.
- The USDC example is built from the parser rules but was never run on a device or emulator.
