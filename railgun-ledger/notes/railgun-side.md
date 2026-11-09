# What a RAILGUN hardware signer must do (for the wedgie)

Date: 2026-11-09. Read-only research. All paths are relative to
`/private/tmp/claude-501/-Users-austingriffith-clawd-clawd-harness-projects-clawd-research/1f7315fa-d4b5-45a7-8685-e5d79c7bb897/scratchpad/src/`.

Repos/artifacts used:
- `ledger-client/` (Railgun-Community, v0.4.3)
- `ledger-client-release/` — v0.4.3 release tgz. It carries the **real RAILGUN Ledger app binaries**
  base64-inlined (`package/dist/core/installer/bundled-artifacts.generated.js`). Extracted to
  `nanosp.elf` / `flex.elf`. **They are not stripped**: full symbol table. App name `RAILGUN`, app_version `0.0.2`,
  api_level 26, ledger-secure-sdk v26.6.2.
- `engine/` (git main = 9.6.0), `wallet/` (git main = 10.9.0)
- `npm-pkgs/` — the published `@railgun-community/engine@9.9.1` and `@railgun-community/wallet@11.3.0`. These are
  ahead of git main and hold the clear-sign code.
- `ZKNOX-HW-PRIVACY/`, `ZKNOX-LibC/`, `ZKN-PRIVACYHW/` (the older ZKNox EdDSA-Poseidon app), and `npm-pkgs/circ/`
  (`@railgun-community/circomlibjs@0.0.8`).

**RAILGUN-HW firmware source is not public.** `gh api repos/{Railgun-Community,ZKNoxHQ}/RAILGUN-HW` returns 404,
and code search finds it only as a name inside ledger-client. The firmware facts below come from: the ELF symbols
and strings, the shared ZKNOX-LibC source (which the app links: same symbol names), and the ledger-client wire
builders that were written against `RAILGUN-HW/js/*.js`.

---

## 1. RAILGUN firmware (RAILGUN Ledger app 0.0.2)

### Keys: the "9075" path is wrong. The device uses the engine's paths.
- `ledger-client/src/core/transport/apdu.ts:37-43` defines `RAILGUN_BIP32_PATH = m/44'/9075'/0'/0/0`. It is only
  exported (`src/index.ts:137`) and used as a display string (`ledger-controller.ts:302`). **It is never sent.** The
  APDUs carry only `account(4 BE)`.
- ELF rodata (`objdump` of the symbols `PATH_SPENDING`, `PATH_VIEWING`, `PATH_DKG_COMM`, `PATH_7702`):
  - `PATH_SPENDING` = `2c000080 c0070080 00000080 00000080 00000080` → `m/44'/1984'/0'/0'/0'`
  - `PATH_VIEWING` = `420'/1984'/0'/0'/0'`
  - `PATH_DKG_COMM` = `421'/...`
  - `PATH_7702` = `7702'/1984'/...` (the 7702 EOA really derives at `m/44'/60'/1984'/7702'/acct'/chainId'/idx'`; README:138)
- Derivation code: `ZKNOX-LibC/src/keys/zkn_keyderivation.h:44-62` and `zkn_keyderivation.c:28-45`.
  - Master = `HMAC-SHA512(key="babyjubjub seed", BIP39 seed)`, then SLIP-0010 hardened children
    (`os_derive_bip32_with_seed_no_throw(HDW_ED25519_SLIP10, …, "babyjubjub seed")`).
  - The string `babyjubjub seed` is also in the app's rodata.
  - **Both keys come from this one master**, viewing key included. Viewing does not use the standard ed25519 SLIP-10 seed.
- Engine match:
  - `engine/src/key-derivation/bip32.ts:5,71-77` (`CURVE_SEED='babyjubjub seed'`, IL=key, IR=chaincode) and
    `bip32.ts:41-62` (hardened CKD).
  - `wallet-node.ts:18-19` (prefixes `m/44'/1984'/0'/0'/` and `m/420'/1984'/0'/0'/`, then `index'`).
  - Spending private key = node IL (`wallet-node.ts:94-99`). Viewing private key = IL of the 420' node (`wallet-node.ts:107-111`).
  - The two sides **match for index 0.**
  - Difference: the device puts the account at level 2 (`zkn_keyderivation.c:57`, `path[2]=account`). The engine
    puts the wallet index at level 5. So device account N≠0 is **not** Railway index N.
- Derived values:
  - Spending pubkey = circomlib `prv2pub` (Blake-512 then prune, `Base8·(s>>3)`).
  - Viewing pubkey = ed25519 of the 32-byte viewing key.
  - Nullifying key = `poseidon([vpk])`; MPK = `poseidon([Ax, Ay, nk])` (`wallet-node.ts:103-117`).

### APDU surface (CLA 0xE0), `ledger-client/src/core/transport/apdu-profile.ts:96-122`

| INS | Name | Data → response |
|-----|------|-----------------|
| 0x01 | GET_PUBKEY | account(4) → Ax‖Ay (64). P1=1 shows "Spending pubkey" with a "Show as QR" option. |
| 0x13 | GET_VIEWING_KEY | Returns the **viewing private key** (32). Screen: "Export RAILGUN / Viewing key / to software wallet / Allow viewing access". |
| 0x10 | GET_VIEWING_PUBKEY | → 32 |
| 0x14 | GET_RAILGUN_ADDRESS | Derives and shows the `0zk1…` (127 ASCII). Screen: "Address verification". |
| 0x12 | SIGN_HASH (blind) | account(4)‖msg(32) → 0x60‖R8x‖R8y‖S‖msg = 129 B (`apdu.ts:303-323`, `apdu-response.ts:55-57`, big-endian) |
| 0x11 | CLEAR_SIGN | Stateful, see below |
| 0x07 / 0x08 / 0x09 | ETH pubkey / 7702 auth / ETH tx-hash | For the RelayAdapt7702 ephemeral EOA |

The host builds the 0zk address from the spending pubkey plus the viewing private key
(`wallet-artifacts.ts:158-179`). The shareable viewing key = `vpk + packed spending pubkey`.

### Blind sign (0x12)
- The device signs the opaque 32 bytes with EdDSA-Poseidon. Screens: "Blind signing ahead", "Sign hash",
  "opaque 32-byte hash".
- The host computes `msg = poseidon([merkleRoot, boundParamsHash, ...nullifiers, ...commitmentsOut])`
  (`engine/src/wallet/hardware-wallet.ts:64-79`).
- Device cost: one Blake-512 pair plus one Poseidon(5) for `hm`, plus BabyJubJub scalar multiplications.

### Clear sign (0x11): protocol, `ledger-client/src/core/transport/clear-sign-apdu.ts:23-31, 189-330`

Order: `INIT(P1 0x00)` → `NULLIFIER(0x20)×n` → `BP_FIELDS(0x10)` → `[OUT_BROADCASTER 0x30]` → `[OUT_CHANGE 0x31]`
→ `OUT_TRANSFER 0x32 | OUT_UNSHIELD 0x33` → `FINALIZE(0x40)`.

Message layouts:
- **INIT**: acct(4)‖root(32)‖nIn‖nOut[‖walletSource(15)]
- **BP_FIELDS** (69 B): tree(2)‖minGasPrice(6, uint48)‖unshield(1)‖chainId(8)‖adaptContract(20)‖adaptParams(32)
- **OUT_BROADCASTER**: MPK‖VKpub‖tokenHash‖value(32)‖0000
- **OUT_CHANGE**: token‖value‖0000
- **OUT_TRANSFER**: 0zk(127 ASCII)‖token‖value‖outputType(1)‖memoLen(2)‖memo(≤32)
- **OUT_UNSHIELD**: addr(20)‖token‖value

Responses:
- broadcaster/change: 223 B = `random16‖Blind1 32‖Blind2 32‖IV16‖tag16‖ct96‖senderRandom15`
- transfer: 239 B (adds annotationIv 16)
- unshield: 32 B (the commitment)
- FINALIZE: 129 B (sig + msgHash)
- Dual-tx (tx token ≠ fee token): 2×128 B, with a fixed shape (`docs/engine-clear-sign-integration.md:136-160`)

Shape caps:
- ledger-client: n∈[1,4], m∈[1,3], n+m≤5 (`clear-sign-apdu.ts:112-123`).
- Engine 9.9.1 is stricter: n≤3 (`npm-pkgs/.../engine-9.9.1/package/dist/wallet/clear-sign.d.ts:24`).
- Reason for n+m≤5: the sighash takes 2+n+m inputs, max 7, i.e. t=8. The device only carries `POSEIDON1..7_MIXCOLUMN`.
- V2 txid only, no memo text on the engine side.

What the device computes (ELF symbols `handler_clear_sign` 3.7 KB, `commit_current_tx`, `encrypt_and_store_output`,
`railgun_note_encrypt_with_randomness`, `build_and_store_annotation`, `railgun_build_annotation_v2`,
`relay_adapt_recompute_unshield_base`, `feed_word`/`feed_bytes_padded`/`cx_keccak_256_hash_iovec`, `SNARK_SCALAR_FIELD`):
- **Nullifiers are taken from the host, not recomputed.** The proof binds them to the key.
- **Output commitments** = `poseidon([npk, tokenHash, value])` with `npk = poseidon([MPK, random])`.
  The device picks `random`. Change uses its own MPK. The 0zk is decoded on-device (`CHARSET_REV`, `bech32_polymod`).
  Unshield uses `npk = recipient address` (`engine/src/note/transact-note.ts:228-229`).
- **Note encryption (V2)**: AES-256-GCM over `[encodedMPK, tokenHash, random‖value, memo]`.
  - Key = `sha256(ECDH)`: ed25519 scalar of own vpk × the receiver's blinded viewing key.
  - Both viewing pubkeys are blinded by `scalar = sha512(sharedRandom XOR senderRandom) mod n`.
  - Refs: `engine/src/utils/keys-utils.ts:105-205`, `transact-note.ts:236-298`. The ELF has `cx_aes_gcm_*`.
- **Annotation**: AES-256-CTR under the **viewing private key** of `[outputType‖senderRandom15, zeros, walletSource]`
  (`engine/src/note/memo.ts:141-170`).
- **boundParamsHash** = `keccak256(abi.encode(tuple(uint16,uint48,uint8,uint64,address,bytes32,(bytes32[4],bytes32,bytes32,bytes,bytes)[]))) mod p`
  (`engine/src/transaction/bound-params.ts:10-21`). The device streams the ABI words into keccak itself.
- **Sighash** = Poseidon over root, bp-hash, nullifiers, commitments; then EdDSA-Poseidon.
- **The device therefore needs the viewing private key**, not only the spending key.

Screens (ELF strings): "Review RAILGUN", "Amount", "Address", "Broadcaster fee", "Redirect via broadcaster",
"Unshield WETH", "Chain ID", "Adapt contract/params", "RelayAdapt V2", "Unknown adapter", "Hold to sign".
There is a `KNOWN_TOKENS` table (640 B) plus `format_value_smart` to format token amounts.

### Poseidon
- Standard circomlib parameters: BN254, x^5, RF=8, `RP=[56,57,56,60,60,63,64,63,60,66,60,65,70,60,64,68]`.
  The ELF `POSEIDON_NROUNDS_P_TABLE` has exactly these values; circomlibjs is at `npm-pkgs/circ/package/src/poseidon.js:16-17`.
- The Ledger app stores **only the MDS matrices** for t=2..8 (6,496 B) and **regenerates the round constants with
  the Grain LFSR at runtime** (`ZKNOX-LibC/src/hash/zkn_poseidon_constants.c:22-126, 444-482`).
- Full ARK+MDS tables if stored in flash:
  - t=2..8: ≈81 KB
  - t=2..17 (all of circomlib): ≈395 KB
  - circomlibjs "opt" constants: ≈752 KB
- On a 2 MB RP2040, storing full tables is fine.

### Perf
No published numbers in any repo. Unconfirmed.

---

## 2. Engine / wallet SDK side

- **Merged and released.** Engine PR #137 "hardware wallet via external signer connector" (branch `zy0n/ledger-base`)
  was merged 2026-05-29 and ships from engine 9.6.0 (`engine/src/wallet/hardware-wallet.ts`).
- Clear-sign support (`wallet/clear-sign.js`, `ClearSignMode` prefer/require/never) is only in **npm engine 9.9.1**.
  Git main is behind.
- The "multi-sig-wallet branch" that ledger-client mentions (`zy0n/multi-sig-wallet`) is stale wording.
- Wallet SDK 11.3.0 exports (`dist/services/railgun/wallets/hardware-wallets.d.ts:49`):
  - `createHardwareRailgunWallet(encKey, shareableViewingKey, creationBlocks, connector, accountIndex)`
  - `loadHardwareRailgunWallet`, `setHardwareWalletConnector`
  - `setHardwareWalletClearSignEnabled/Mode/MaxTransactions`, `setHardwareWalletEphemeralSignerProvider` (7702)
- How it works: a HardwareWallet is a view-only wallet. The host gets the vpk plus the spending pubkey.
  `getSpendingKeyPair` returns a zero private key.
- How the signature enters the proof:
  - `transaction-batch.ts:464-482`: `requestBatchApproval(requests)` → per tx `wallet.sign(publicInputs, subSession)`
    → `signature: [R8x, R8y, S]` goes into the unproved inputs, then the prover.
  - For clear sign, the engine re-derives and checks the device's ciphertexts before proving (`clear-sign.d.ts`).
- Connector type: `sign(expectedHash, publicInputs?, subSession?, clearSign?) → {R8, S, clearSign?}`, optional
  `requestBatchApproval`. The engine docs say plainly: "a second hardware vendor must not require engine changes".
- **A third party can use it today.** Any page can bundle the wallet SDK plus its own connector object (structural
  typing, no Ledger import). A WebSerial wedgie connector only has to implement `sign`, plus clear-sign if it wants.
  ledger-client itself is MIT and ESM; its WebHID/BLE transports are Ledger-specific.

## 3. Anon and others

- Anon (anon.inc, announced on X 2026-11-02): **Ledger only** (Nano S Plus, Flex).
  - The site says nothing about Trezor, Keystone or GridPlus, and offers no connector or SDK for other devices.
  - "Anon keeps your viewing key."
- The pluggable piece is the RAILGUN engine/SDK connector, not Anon.
- RailOxide (Rust desktop): Ledger and Trezor are used only to *derive* the private wallet ("hardware-derived software
  custody"). Spending is signed in desktop memory. Native signing is "when vendors add RAILGUN crypto".
- Tangem lists RAILGUN, but only as an ERC-20 token.

## 4. EdDSA spec

- circomlib `signPoseidon` (`npm-pkgs/circ/package/src/eddsa.js:108-125`):
  1. `h = blake512(prv)` (old BLAKE, not BLAKE2)
  2. `s = prune(h[0:32])`, `A = Base8·(s>>3)`
  3. `r = blake512(h[32:64] ‖ LE32(msg)) mod subOrder`
  4. `R8 = Base8·r`
  5. `hm = Poseidon5(R8x, R8y, Ax, Ay, msg)`
  6. `S = r + hm·s mod subOrder`
- Circuits (`engine/src/solutions/nullifiers.ts:1-13`):
  - In use: all 1-10 inputs × 1-5 outputs except 10x5.
  - Valid but unused: 11x1, 12x1, 13x1, 1x10, 1x13.
- Sighash arity = 2+n+m. Max in use is **16** (10x4 and 9x5; 13x1 and 1x13 too), so **t=17**, the circomlib
  maximum. That is why 10x5 (17) is excluded.
- A full blind signer needs only Poseidon5 (t=6). A clear signer covering every shape needs t up to 17.

## 5. Shield / unshield

- **Shield needs no BabyJubJub signature.** It is a normal ETH transaction: ERC-20 approve, then `shield(ShieldRequest[])`.
- The `shieldPrivateKey` is a key the sender derives from an **EIP-191 `personal_sign("RAILGUN_SHIELD")`**
  (`engine/src/note/shield-note.ts:40-42`).
  - Ledger does this in the **Ethereum app** at `m/44'/60'/0'/0/i` (`ledger-client/src/core/signers/eth-signer.ts:30, 251-270`).
  - It is used for ECDH with the receiver's viewing key: GCM-encrypt the random, CTR-encrypt the receiver vpk under
    `shieldPrivateKey`, `shieldKey = ed25519 pub` (`shield-note.ts:77-110`).
  - Turning the signature into a key (e.g. keccak) is the caller's convention. Not in the SDK.
- The RAILGUN app also has `SHIELD_SELECTOR` / `build_shield_material`, which suggests clear-signed shields via 7702
  (unconfirmed).
- **Unshield to an EOA** is a normal transact signed with EdDSA, with `unshield=1` and a last output whose npk is the
  address. Clear sign uses `OUT_UNSHIELD`. Any EOA or broadcaster can submit it. Base-token unshield goes through
  RelayAdapt (`relay_adapt_recompute_unshield_base`, "Unshield WETH").

## Unconfirmed / open
- RAILGUN-HW source is private. Clear-sign internals are inferred from symbols and wire formats.
- How the 0zk is truncated on screen. Exact flow and order of the review pages.
- Any perf numbers (Ledger or otherwise).
- Whether the device verifies the host nullifiers against anything. It appears not to.
- The meaning of `build_shield_material` / `SHIELD_SELECTOR`.
- The n≤4 (ledger-client) vs n≤3 (engine) mismatch.
- The ELF/binary license. The ledger-client repo is MIT. Whether the RAILGUN app itself is MIT is unknown.
- The keccak step for the shield key.
