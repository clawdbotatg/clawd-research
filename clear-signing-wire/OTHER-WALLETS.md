# How non-Ledger hardware wallets get clear-signing metadata for Ethereum: wire formats compared

Short answer: only Trezor ships vendor-signed metadata, streamed to the device and scoped to each call. The device asks for it mid-signing, and Trezor now encodes a subset of ERC-7730 for it. Keycard Shell signs its whole metadata database. Keystone keeps an unsigned ABI database on the microSD card. GridPlus sends an ABI the host fetched and nobody signed. BitBox02 has no calldata metadata, only a built-in token list.

Every repo was a `git clone --depth 1` into the scratchpad.

| Repo | Commit | Date |
|---|---|---|
| trezor-firmware | `3227ea8` | 2026-09-26 |
| keystone3-firmware | `0c0ae46` | 2026-09-18 |
| keystone-airgaped-base | HEAD | — |
| gridplus-sdk | `ba9cecd` | 2026-03-19 |
| bitbox02-firmware | `4474a3e` | 2026-09-25 |
| keycard-shell | HEAD | 2026-09-15 |

I also downloaded Trezor's full signed definitions archive (`definitions.tar.xz`).

---

## 1. Trezor

**Transport.** Protobuf messages over USB HID/WebUSB. Newer devices can also use THP, the encrypted Trezor Host Protocol (`messages-thp.proto`). Host libraries are Trezor Suite, Trezor Connect and trezorlib.

**How tx bytes arrive.** In `common/protob/messages-ethereum.proto`:
- `EthereumSignTx` (L63) and `EthereumSignTxEIP1559` (L87) carry the fields already parsed: nonce, fees, `to`, value, chain_id, access list, and an experimental `auth7702` (L104). The first ≤1024 bytes of calldata go in `data_initial_chunk`, plus a total `data_length`.
- The device then pulls the rest with `EthereumTxRequest{data_length}` and `EthereumTxAck{data_chunk}`, ≤1024 bytes each (L127–153).
- In `core/src/apps/ethereum/sign_tx.py`, the device buffers up to `_MAX_DATA_STORED = 6144` bytes (L109) and hashes RLP as it goes.
- Calldata over 6 KB is never clear-signed. The comment at L173–176 says why: fetching more would leave nothing to fall back to for blind signing.

**Metadata sent.** `EthereumDefinitions{encoded_network, encoded_token, encoded_display_format}` (L239–243). The host can attach it up front. On newer firmware the device can also ask for it mid-flow:
- The host sets `supports_definition_request=true` (L77/L102).
- The device sends `EthereumDefinitionRequest{chain_id, token_address, func_sig}` (L162).
- The host replies `EthereumDefinitionAck{definitions}` (L174). "Not found" is allowed.
- Lookup order in `_find_display_format` (`clear_signing.py:1138`): built-ins, then the up-front blob, then the wire request.
- The device also asks this way for tokens it finds while decoding, and for nested calls (L384, L1109).

The payload schema is in `common/protob/messages-definitions.proto`. `DefinitionType` (L12) now has `ETHEREUM_DISPLAY_FORMAT = 3`. `EthereumDisplayFormatInfo` (L222–230) is a compiled form of ERC-7730:
- Keys: `chain_id`, `address`, `func_sig`, plus `intent`.
- `parameter_definitions`: an ABI type tree, `EthereumABIValueInfo` (atomic, dynamic, tuple, array) built on a fixed `EthereumABIType` enum.
- `field_definitions`: `EthereumERC7730FieldInfo` entries, each with a path (int-index path, `@from/@value/@to` container path, or constant), a label, and a formatter.
- Formatters: addressName, amount, tokenAmount (with threshold for "Unlimited"), unit, raw, date, calldata (nested, including multicall `bytes[]`), enum.
- Not supported: `$` and `#` paths (L164).

The device never sees the ERC-7730 JSON. The host side (Trezor's pipeline) compiles it into this proto.

**Trust model (strongest of the group).** The blob format is in `docs/common/external-definitions.md` L103–131 and `core/embed/rust/src/definitions/blob.rs`:

```
"trzd" | ver('1'|'2') | type(1) | data_version u32 LE | len u16 LE | protobuf
| n_proofs(1) | n×32 merkle proof | CoSi sigmask(1) | CoSi sig(64)
```

- Merkle leaf = `SHA256(0x00‖entry)`. Internal node = `SHA256(0x01‖min‖max)`, with sorted pairs.
- One Ed25519 CoSi signature covers the root of all definitions.
- Three production keys are hardcoded (`constants.rs` L49). Version 1 needs 2 signatures, version 2 needs 1 (L18–23).
- The firmware rejects `data_version < MIN_DATA_VERSION` (`generated.rs`, `blob.rs:51`). That makes definitions expire about a month before each firmware release.
- The type byte, plus the "cross-parseability" rule (L19–30), stops a token blob being replayed as a display format.

So the host is untrusted transport and Trezor is the only signer.

**Hosting.** Files live under `https://data.trezor.io/firmware/definitions/eth/chain-id/<id>/{network.dat, token-<addr>.dat, display-format/<addr>-<selector>.dat}` (`python/src/trezorlib/definitions.py:143–161`).
- The live archive has 57,879 files, of which 1,220 are display formats. 301 are on mainnet, mostly 1inch and LiFi routers.
- I decoded one (a mainnet "Stake ETH" deposit). It is `trzd1` type 3. Sizes run 96 B to 9.7 KB, median 712 B.
- Some Uniswap router address/selector combinations I guessed returned 404. Coverage depends on the registry.

**Native display.** Built-in networks and tokens (`common/defs/ethereum/*.json`). Hardcoded display formats for ERC-20 `approve`/`transfer` and WETH (`clear_signing_definitions.py`). Hand-written staking and "yielding" flows. Otherwise hex.

**SLIP-24 payment requests.** `payment_req` (L76/L101) is a signed merchant or swap-provider request. On Ethereum it only works for ERC-20 transfers (`clear_signing.py`).

**ERC-7730 status.** Issue #6733. Changelog entries: 2.11.1 "Uniswap swap functions", 2.12.2 (July 2026) "Improved clear signing". Publicly launched 2026-09-08 on Safe 3/5/7 and Model T, not Model One.

**EIP-712** (`messages-ethereum-eip712.proto`):
- The device drives a stream.
- `EthereumTypedDataStructRequest{name}` / `StructAck{members[type,name]}` fetch type definitions.
- `EthereumTypedDataValueRequest{member_path}` / `ValueAck{value}` fetch values. For arrays the value is a uint16 count.
- The device rebuilds the hash itself, so it never has to hold the whole JSON.
- It shows raw field names and values. There is no ERC-7730 formatting for typed data yet (I found no display-format use in `sign_typed_data.py`).
- Model One falls back to `EthereumSignTypedHash` (L219), which is hash only.

---

## 2. Keystone 3 Pro

**Transport.** Air-gapped, using animated QR codes with BC-UR framing and CBOR. The request is `eth-sign-request`, tag 401 (`ur-registry-eth/src/RegistryType.ts`). The CBOR map (`EthSignRequest.ts` L14–22):
1. requestId
2. signData
3. dataType (1 = legacy tx, 2 = typedData JSON, 3 = personal, 4 = typed tx)
4. chainId
5. derivationPath
6. address
7. origin

There is also `eth-batch-sign-request` (40404). A USB keyring package exists too (`metamask-keystone-usb-keyring`).

**How tx bytes arrive.** Not streamed. The whole unsigned RLP tx sits in one CBOR `signData` field, split across QR frames by UR fountain codes.

**Metadata sent.** None. The request has no field for it. All decoding happens on the device from local data:
- ERC-20 table compiled in: `ERC20_CONTRACTS[]` with symbol, address, decimals (`src/ui/gui_chain/multi/web3/gui_eth.c:314`).
- About 490 KB of built-in ABI JSON (`src/ui/gui_assets/abi/abi_ethereum.c`), looked up by `address_selector` (`GetEthContractFromInternal`, ~L2045). Safe `execTransaction` is special-cased.
- An external SQLite database on the microSD card: `0:contracts/<chainId>_<addr[2]>_contracts.db`, query `Select functionABI, name from contracts where selectorId=… and address=…` (`src/user_sqlite3.c:633–654`). `"0:"` is the SD volume (`src/user_fatfs.c:30`).
- Decoding is full `ethabi` JSON-ABI parsing in Rust on the device (`rust/apps/ethereum/src/abi.rs`).

**Trust.** Built-in data is covered by firmware signing. For the SD-card DB I found no signature check in `OpenDb`/`GetDBContract`. Whoever controls the card controls the labels. This is my reading of the code; flag it as likely unsigned.

**Native display.** Contract name, method name, and parameters as name, type, value. That is ABI-level, not intent-level: no "Swap 1 ETH for X USDC". There are special swap parsers in `swap.rs`, plus permit warnings.

**ERC-7730.** No "7730" anywhere in the firmware tree.

**EIP-712.** The whole typed-data JSON is sent in `signData`. The device parses it with serde_json, with depth and NUL guards (`lib.rs:81–180`), hashes it, and shows it.

---

## 3. GridPlus Lattice1

**Transport.** Encrypted request/response over an ECDH-paired channel. It is usually relayed through GridPlus's routing server (`BASE_URL = https://signing.gridpl.us`, `constants.ts:148`); the Lattice is a network device. The firmware is closed source, so what the device does is inferred from the SDK.

**How tx bytes arrive.** Generic signing request:
- Base frame of `baseDataSz = 1519` bytes (`constants.ts:422`).
- At most 1 extra frame of 1500 bytes (L351).
- Anything bigger is prehashed. The SDK sends keccak(payload), and the device can only show a hash (`genericSigning.ts` ~L140–165).
- No device-pulled streaming.

**Metadata sent.** A calldata "decoder" appended to the payload as `u32 reserved (2895728) | u32 len | RLP(def)`, max 1024 bytes (`genericSigning.ts:86–102`, `constants.ts:458–460`):
- `def` is `[fnName, ...params(type-idx, size, array sizes, nested)]`, RLP-encoded (`util.ts:507`).
- The host builds it by calling Etherscan-like APIs for the verified ABI (`constants.ts:516+`), falling back to 4byte.directory (`util.ts:491`, `fetchCalldataDecoder` L623–689).
- It recurses into nested `bytes`/`bytes[]` calldata, such as multicall (`calldata/evm.ts:73`).
- The decoder is dropped silently if it doesn't fit, because a prehashed payload can't carry it.

**Trust.** Nobody signs the decoder. The only check is that the canonical name hashes to the selector (`parseCanonicalName` L40). The firmware presumably re-checks this; I can't confirm, since it's closed. A malicious host can pick among 4byte collisions and invent parameter names. The device protects against wrong types and positions, not wrong meaning.

**Also on the device.** User-written key/value "address tags" (`addKvRecords`, `api/addressTags.ts`), 63-byte strings, entered by the user and unsigned.

**EIP-712.** The full typed data is sent as CBOR (`ethereum.ts:865–940`), up to 18 params per type. Oversized messages are prehashed.

**ERC-7730.** Nothing in the SDK. The last SDK commit is March 2026.

---

## 4. BitBox02

**Transport.** Protobuf over USB HID, inside a Noise-encrypted channel with pairing-code verification.

**How tx bytes arrive.** `ETHSignRequest` / `ETHSignEIP1559Request` (`messages/eth.proto` L41–79) carry the parsed fields. Calldata goes either inline in `data` (≤6144 B, `sign.rs:31`) or streamed:
- Set `data_length`.
- The device pulls with `ETHSignDataRequestChunkResponse{offset,length}`, 4096-byte chunks (`sighash.rs:239`), up to 1 MB (`sign.rs:30`).
- The host answers with `ETHSignDataResponseChunkRequest{chunk}`.

Pulling by offset lets the device re-read data. That is a useful pattern.

**Metadata sent.** None.
- The ERC-20 table (`src/rust/erc20_params/src/tokens.txt`, about 2,300 entries) covers mainnet only. `get()` returns None if `chain_id != 1` (`lib.rs:45–46`).
- Only `transfer(a9059cbb)` is parsed (`sign.rs:121–130`). Unknown tokens show "Unknown token / Unknown amount" plus the contract address (L342–397).
- All other calldata is shown as raw data.
- `payment_request` (L78) reuses BTC payment-request signing, the SLIP-24 family.

**EIP-712.** The host sends the full type schema up front (`ETHSignTypedMessageRequest.types`, L106–142). The device pulls each value by path (`ETHTypedMessageValueResponse{root_object, path}`), and large values can be streamed in chunks (L154–159). The device hashes and shows every field.

**ERC-7730.** None in the source. Not on EF contributor lists.

---

## 5. Keycard Shell (quick look)

**Transport.** QR codes, UR-compatible with Keystone's `eth-sign-request` (`app/ur/ur.h:73`). USB is also documented (`docs/USB.md`).

**Metadata.** A signed database of chains (chainlist), tokens (tokenlists) and ABIs, loaded as one update blob.
- Built reproducibly by `tools/shell-db.py` from JSON published at shell.keycard.tech (`docs/shell-db.md`).
- The device checks a secp256k1 ECDSA signature over SHA256 of the blob minus its last 64 bytes, against the built-in `DB_VERIFICATION_KEY`, and rejects older versions (`app/core/updater.c:119–140`).
- ABIs are indexed by an 8-byte `full_selector` (`eth_db.c:26`). I did not confirm whether that binds to a contract address.
- Uniswap Universal Router `execute` commands are hand-parsed (`eth_data.h`).

Keycard is listed as an EF Clear Signing contributor, but I found no 7730 code.

---

## 6. Cross-vendor standards (2025–2026)

- **ERC-7730.** Ledger created it and handed governance to the EF. v2 came out in April 2026. The EF "Clear Signing" launch was 2026-05-12, with a neutral registry (`ethereum/clear-signing-erc7730-registry`, clearsigning.org) and ERC-8176 auditor attestations. The working group is active (sync call 2026-09-23).
- **It standardizes the JSON descriptor, not a device wire format.** clearsigning.org describes no binary or transport encoding. Each wallet vendor decides which attestations to trust. The registry "can contain low-quality or malicious entries by design."
- **Result:** Ledger (its own binary format and signing) and Trezor (`EthereumDisplayFormatInfo` protobuf plus CoSi) both consume ERC-7730 but have **incompatible compiled forms and separate signing keys**. Every other device vendor has to invent its own compiled format. Press coverage says Keystone and GridPlus have not announced ERC-7730 support; I found nothing on BitBox.
- **SLIP-24 payment requests** (Trezor and BitBox) are the other shared piece. They carry signed merchant or recipient attestations, not calldata semantics.

---

## Comparison

| | Trezor | Keystone 3 | GridPlus Lattice1 | BitBox02 | Keycard Shell |
|---|---|---|---|---|---|
| Transport | Protobuf / USB (+THP) | QR (UR/CBOR), USB | Encrypted relay / LAN | Protobuf / USB, Noise | QR (UR), USB |
| Tx bytes | Parsed fields + 1 KB chunks, device-pulled; clear-sign ≤6 KB | Whole RLP in one CBOR field | 1519 B + 1×1500 B, else prehash | Parsed fields + 4 KB chunks by offset, ≤1 MB | Whole RLP (UR) |
| Calldata metadata | Per-(chain, contract, selector) ERC-7730-derived protobuf, pushed or device-requested | None on wire; firmware ABIs + SD-card SQLite DB | Host-fetched ABI "decoder" (RLP), ≤1 KB | None | Signed whole-DB update (ABIs, tokens, chains) |
| Token metadata | Built-in + signed `.dat` per token | Built-in table | Built-in | Built-in, mainnet only, transfer only | Signed DB |
| Signed? By whom | Yes: Ed25519 CoSi (2-of-3 v1 / 1-of-3 v2), Merkle root, freshness floor | Firmware yes; SD DB **apparently not** | **No** (selector-hash check only) | N/A | Yes: secp256k1, Keycard key, versioned |
| Display | Intent + labeled, formatted fields, nested calls | Contract + method + raw params | Method + typed params | Raw data except ERC-20 transfer | Method params, Uniswap special-case |
| EIP-712 | Device-driven struct/value streaming; raw fields | Full JSON parsed on device | Full CBOR, or prehash | Schema up front, values pulled by path | JSON (not examined) |
| ERC-7730 | **Shipped** (Sep 2026) | No | No | No | Contributor, no code |

---

## Lessons for a small-MCU hardware wallet

1. **Compile the descriptor on the host and sign it; never parse JSON on the device.** Trezor's `EthereumDisplayFormatInfo` is the model: a flat ABI type-tree enum plus a list of (path, label, formatter-enum, params), median about 700 B. The device-side interpreter is an ABI word-walker plus about 8 formatters. Keystone-style on-device JSON ABI parsing costs about 500 KB of flash plus serde, and still only gives parameter names, not intent.

2. **Bind every metadata blob to what it describes and check the binding on the device.** Check (chain_id, contract address, selector) against the tx being signed (`matches_call`, `clear_signing.py:936`). Put a type tag in the header and make definition types impossible to parse as each other. Unbound or unsigned metadata (GridPlus 4byte, Keystone SD card) lets the host choose the story.

3. **Sign a Merkle root, not each file.** One signature covers about 58K definitions. Each blob carries a log(n) proof (≈16×32 B), so the device needs only one public key, the hash function and one signature check. Add a `data_version` floor burned into firmware so revoked or buggy descriptors expire. A single signed DB blob (Keycard) is simpler but costs flash and needs full re-flashes.

4. **Let the device pull metadata instead of trusting what the host chose to push.** Trezor's `EthereumDefinitionRequest{chain, address, selector}` means the device, after parsing the selector and any nested callee itself, names exactly which blob it needs. That makes nested and multicall decoding work without the host knowing the device's parse state. "Not found" is a valid answer and falls back to blind signing.

5. **Stream calldata but keep a clear-sign buffer, and make the cutoff explicit.** Hash as you stream. Clear-sign only if the calldata fits in RAM (Trezor 6 KB), because once you've streamed past a chunk you can't re-display it. BitBox's offset-addressed pull (`{offset,length}`) lets a RAM-poor device re-read regions instead of buffering them. Worth copying if you want clear signing on calldata larger than RAM.

6. **For EIP-712, have the device pull the schema and values by member path** (Trezor, BitBox). Memory stays bounded by nesting depth, not message size, and the device computes the hash itself. Never accept a host-supplied hash as the only thing shown, except as an explicit blind mode.

7. **Decide your trust root early.** For ERC-7730 today, the realistic options are:
   - run your own pipeline: pull the EF registry, apply an attestation policy (ERC-8176 signals), compile, and sign with your key; or
   - accept another vendor's signed blobs. Nobody offers this cross-vendor; Trezor's format is documented and its keys are public, but that is an unofficial dependency.

   No shared device wire format exists yet. That gap is open if you want to propose one.

8. **Keep native fallbacks small but real:** ERC-20 transfer/approve (with an "unlimited" threshold), native value, 7702 delegation, and known-address names. Everything else goes through signed descriptors or a loud blind-sign warning.

**Uncertainty:**
- GridPlus firmware is closed, so on-device checks of the decoder are inferred from the SDK.
- Keystone's SD-card DB may be verified somewhere I didn't find, though I saw no signature check in the open path.
- For Keycard, I did not confirm whether the ABI index binds to a contract address.
- Trezor display-format coverage is a snapshot of `definitions.tar.xz` as of 2026-09-27.

Sources:
- [ERC-7730 spec](https://eips.ethereum.org/EIPS/eip-7730)
- [EF clear-signing registry](https://github.com/ethereum/clear-signing-erc7730-registry)
- [clearsigning.org/build](https://clearsigning.org/build/)
- [Trezor issue #6733](https://github.com/trezor/trezor-firmware/issues/6733)
- [Trezor clear signing guide](https://trezor.io/guides/sending-receiving-staking-funds/interacting-with-smart-contracts/clear-signing-on-trezor)
- [The Defiant – EF launches Clear Signing](https://thedefiant.io/news/blockchains/ethereum-foundation-launches-clear-signing-standard)
- [CoinDesk 2026-05-12](https://www.coindesk.com/tech/2026/05/12/the-ethereum-foundation-unveils-new-clear-signing-standard-to-stop-users-from-approving-malicious-crypto-transactions)
- [Cryptonomist – Trezor ERC-7730](https://en.cryptonomist.ch/2026/09/09/trezor-erc-7730-signing/)
- [Cryptopolitan – Trezor Safe wallets](https://www.cryptopolitan.com/trezor-erc-7730-clear-signing-safe-wallets/)
- [Ledger – ERC-7730 v2](https://www.ledger.com/blog-the-evolution-of-clear-signing)
- [Cyfrin – Blind signing solved?](https://www.cyfrin.io/blog/blind-signing-solved)
- [Clear Signing sync call 2026-09-23](https://github.com/ethereum/clear-signing-erc7730-registry/issues/2970)
- [ethereum.org clear signing tutorial](https://ethereum.org/developers/tutorials/clear-signing/)
- `https://data.trezor.io/firmware/definitions/definitions.tar.xz` (checked directly)
