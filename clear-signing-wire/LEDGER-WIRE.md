# Ledger Ethereum app: clear-signing wire format (APDU level)

I read both repos at their current heads, cloned under `.../scratchpad/`:
- `LedgerHQ/app-ethereum` @ `5a489407` (2026-09-22), app version 1.22.5 (`Makefile:38-40`)
- `LedgerHQ/device-sdk-ts` @ `7bc0bb4a` (2026-09-25), signer-eth 1.18.1, context-module 2.6.0

Path shorthand: `AE/` = app-ethereum, `CM/` = `device-sdk-ts/packages/signer/context-module/src`, `SE/` = `device-sdk-ts/packages/signer/signer-eth/src/internal/app-binder`.

# 1. APDU framing

**Frame.** Every command is `CLA INS P1 P2 Lc data`. CLA is `0xE0`. The data field holds at most 255 bytes: the SDK sets `APDU_MAX_PAYLOAD = 255` (`device-management-kit/src/api/apdu/utils/ApduBuilder.ts:7`), and the Python test client slices every payload at `0xff` (`AE/client/.../command_builder.py:411,428,562`). The HID / BLE framing (channel `0101`, tag `0x05`, sequence index) is in `AE/doc/ethapp.adoc:1755-1822`.

**INS list** (`AE/src/apdu_constants.h:12-38`):

| INS | Name | INS | Name |
|---|---|---|---|
| 02 | GET_PUBLIC_KEY | 1C | EIP712_STRUCT_IMPL |
| 04 | SIGN | 1E | EIP712_FILTERING |
| 06 | GET_APP_CONFIGURATION | 20 | GET_CHALLENGE |
| 08 | SIGN_PERSONAL_MESSAGE | 22 | PROVIDE_TRUSTED_NAME |
| 0A | PROVIDE_ERC20_TOKEN_INFO | 24 | PROVIDE_ENUM_VALUE |
| 0C | SIGN_EIP_712_MESSAGE | 26 | GTP_TRANSACTION_INFO |
| 0E | GET_ETH2_PUBLIC_KEY | 28 | GTP_FIELD |
| 10 | SET_ETH2_WITHDRAWAL_INDEX | 2A | PROVIDE_PROXY_INFO |
| 12 | SET_EXTERNAL_PLUGIN | 30 | PROVIDE_NETWORK_CONFIG |
| 14 | PROVIDE_NFT_INFORMATION | 32 | PROVIDE_TX_SIMULATION |
| 16 | SET_PLUGIN | 34 | SIGN_EIP7702_AUTHORIZATION |
| 18 | PERFORM_PRIVACY_OPERATION | 36 | PROVIDE_SAFE_ACCOUNT |
| 1A | EIP712_STRUCT_DEF | 38 | PROVIDE_GATING |

**Certificates are loaded with a separate OS-level command**, not an eth-app INS: `CLA=0xB0 INS=0x06 P1=<key-usage number> P2=00`, data = the certificate (`device-management-kit/src/api/command/os/LoadCertificateCommand.ts:97-105`).

**Chunking conventions are not uniform:**
- **INS 22, 24, 26, 28, 2A, 34:** P1=`01` for the first chunk, `00` for the rest. The first chunk starts with a 2-byte big-endian total payload length. The device reassembles the chunks, then parses (`AE/src/tlv_apdu.c:25-80`).
- **INS 36 and 38 are inverted:** P1=`00` first, `01` following (`ethapp.adoc:1631-1750`).
- **INS 32:** P1 selects the sub-command (payload vs opt-in) and P2 does the chunking (`ethapp.adoc:1502-1560`).
- **INS 04 / 08 streaming:** P1=`00` first block, `80` subsequent blocks. The first block starts with the BIP-32 path: count byte, then u32 BE indexes.

**SIGN (INS 04) P2 modes** (`ethapp.adoc:98-160`; `AE/src/features/sign_tx/cmd_sign_tx.c:14-18,116-181`):
- `00` **basic.** Stream the RLP and the review starts when parsing finishes. Returns v(1) ‖ r(32) ‖ s(32).
- `01` **store only.** Stream the unsigned RLP (EIP-2718 type byte ‖ RLP). The device parses it and keeps the calldata in RAM, compressed per 32-byte word (`AE/src/features/generic_tx_parser/calldata.c:31-80`). Returns 9000 with no data.
- `02` **start flow.** Empty data. Before showing the review, the device checks that the running fields hash matches the one in TX_INFO (`validate_instruction_hash`) and that exactly one tx context remains.

The SDK builds the three variants as follows (`SE/command/SignTransactionCommand.ts:67-70`, `StoreTransactionCommand.ts:52-55`, `StartTransactionCommand.ts:43-46`):
- basic: `E0 04 00|80 00`
- store: `E0 04 00|80 01`
- start: `E0 04 00 02`

**Legacy-tx chunking quirk.** For legacy EIP-155 txs, the host must not start the last chunk exactly on the v,r,s marker, or the app signs too early. The SDK shrinks the chunk size to avoid it (`SE/task/SendSignTransactionTask.ts:127-185`).

# 2. Clear-signing a contract call via the generic parser (ERC-7730 path)

## TLV encoding

Tags and lengths are both DER-style variable-length integers: a value ≥ 0x80 is written as `0x80|n` followed by n bytes (`AE/client/.../tlv.py:33-57`). So tag `0xFF` goes on the wire as `81 FF`, which is why the SDK appends the TX_INFO signature with tag `"81ff"` (`CM/shared/model/SignatureTags.ts:2`; `CM/shared/utils/HexStringUtils.ts:37-53`).

## Sequence

The device-side spec is the diagram in `AE/doc/gcs.md:5-25`. The SDK does this, in order:

1. **GET_APP_CONFIGURATION**, then optionally the Web3-Checks opt-in (`SE/device-action/SignTransaction/SignTransactionDeviceAction.ts:261-365`), then GET_ADDRESS.
2. **Build contexts** from CAL. The ERC-7730 path is chosen only if all of these hold (`SE/task/BuildBaseContexts.ts:140-147,244-268`; `SE/../shared/EthAppVersions.ts:11`):
   - the app is newer than 1.14.0,
   - the device is not a Nano S,
   - the TRANSACTION_INFO context came back with a certificate.
3. **Send contexts in priority order** (`BuildBaseContexts.ts:280-300`): proxy info (5), then tx-check and gating (10), then dynamic network and icon (30), then TRANSACTION_INFO (50), then fields and their sub-contexts (70).
4. **Store the tx right before the first TRANSACTION_INFO.** `SIGN P2=01` goes out immediately before the first TRANSACTION_INFO. Later TX_INFOs are for nested calldata (`SE/task/ProvideTransactionContextsTask.ts:152-176`).
5. **Load the certificate before each context that carries one**, via `B0 06` (`SE/task/ProvideContextTask.ts:81-88`).
6. **TX_INFO:** `E0 26` (`SE/task/ProvideContextTask.ts:106-116`).
7. **Per field:** first its sub-contexts, then the field.
   - Sub-contexts: token (`0A`), NFT (`14`), enum (`24`), or trusted name (`22`, with a fresh `GET_CHALLENGE` before it). The host pulls the needed address or value out of the calldata using the field's path (`SE/task/BuildSubcontextsTask.ts:89-315`).
   - Then `E0 28` for the field itself.
8. **`E0 04 00 02`** to start the review (`SE/task/SendSignTransactionTask.ts:59-64`).
9. **Blind-sign fallback.** If that fails for any reason other than a user refusal, the SDK retries with basic SIGN P2=00 (`SignTransactionDeviceAction.ts:552-608`).

## TRANSACTION_INFO TLV

Spec: `AE/doc/tlv_structs.md:24-39`. Parser: `AE/src/features/generic_tx_parser/gtp_tx_info.c:15-27`.

| Tag | Field | Type |
|---|---|---|
| 00 | VERSION | u8 |
| 01 | CHAIN_ID | u64 |
| 02 | CONTRACT_ADDR | 20 bytes |
| 03 | SELECTOR | 4 bytes |
| 04 | FIELDS_HASH | 32 bytes |
| 05 | OPERATION_TYPE | ASCII, shown after "Review …" |
| 06 | CREATOR_NAME | ASCII, optional |
| 07 | CREATOR_LEGAL_NAME | ASCII, optional |
| 08 | CREATOR_URL | ASCII, optional |
| 09 | CONTRACT_NAME | ASCII, optional |
| 0A | DEPLOY_DATE | u32 unix time, optional |
| FF (wire `81FF`) | SIGNATURE | DER |

- **Version must be 1.** v1 requires tags 00–05 plus FF (`gtp_tx_info.c:157-181`). The doc table still says "constant 0x0", which is stale. The SDK's unit-test fixture (an Aave `withdraw` descriptor, `HttpCalldataDescriptorDataSource.test.ts:61`) also uses version 0.
- **Signed digest:** SHA-256 over the raw TLV bytes of every tag except the signature (`gtp_tx_info.c:143-148`; `cmd_tx_info.c:17`).
- **Checks the device makes:**
  - the selector must equal the stored calldata's selector (`gtp_tx_info.c:41-59`);
  - address, selector and chain ID must match the next un-described tx context, in order;
  - the address may instead match the proxy's implementation address, if a PROXY_INFO was loaded (`tx_ctx.c:196-226`).

## FIELD TLV

Spec: `tlv_structs.md:63-107`. Parser: `gtp_field.c:38`, v1 required at `gtp_field.c:233-247`.

| Tag | Field | Notes |
|---|---|---|
| 00 | VERSION | must be 1 |
| 01 | NAME | label |
| 02 | PARAM_TYPE | see enum below |
| 03 | PARAM | nested TLV |
| 04 | VISIBLE | optional: ALWAYS / MUST_BE / IF_NOT_IN |
| 05 | CONSTRAINT | optional, repeatable, up to 5 |

PARAM_TYPE values: RAW 0, AMOUNT 1, TOKEN_AMOUNT 2, NFT 3, DATETIME 4, DURATION 5, UNIT 6, ENUM 7, TRUSTED_NAME 8, CALLDATA 9 (nested call), TOKEN 0A, NETWORK 0B.

- **FIELDs are not signed.** The device keeps a running SHA3-256 (FIPS-202, not Keccak: `cx_sha3_init_no_throw(…,256)`, `tx_ctx.c:309`) over each FIELD's full TLV payload. The 2-byte length prefix is not included (`cmd_field.c:38`). At start-flow the result must equal TX_INFO.FIELDS_HASH. This proves authenticity, order and completeness. A field the formatter rejects is rolled back out of the hash (`cmd_field.c:32-48`).
- **The PARAM_\* sub-TLVs** are in `tlv_structs.md:109-246`. Example, TOKEN_AMOUNT: 00 version, 01 VALUE, 02 token VALUE, 03 native-currency address (repeatable), 04 threshold (u256), 05 above-threshold label.

## VALUE and the calldata path

VALUE (`tlv_structs.md:248-281`):
- 00 version
- 01 TYPE_FAMILY: uint 1, int 2, ufixed 3, fixed 4, address 5, bool 6, bytes 7, string 8
- 02 TYPE_SIZE
- exactly one source: 03 DATA_PATH, 04 CONTAINER_PATH (FROM 0 / TO 1 / VALUE 2 / CHAIN_ID 3), or 05 CONSTANT

DATA_PATH (`tlv_structs.md:283-328`; execution in `gtp_data_path.c:114-340`) works on 32-byte slots counted after the selector. It keeps a current offset and a `ref_offset` (base for offsets). Steps:
- `01 TUPLE u16` — `ref = off; off += n`.
- `03 REF` (empty) — read a u16 from the last 2 bytes of the current slot. The rest of the slot must be zero, and the value must be 32-aligned. Then `off = ref + raw/32`.
- `02 ARRAY {01 weight u8, 02 start i16, 03 end i16}` — read the length at the current slot, `off += 1`, `ref = off`, then `off += idx*weight`. With no start/end, the device iterates every element, depth-first, up to 8 nested arrays. Negative indexes count from the end.
- `04 LEAF u8` — STATIC 3 reads one slot. DYNAMIC 4 reads a length slot, then the bytes. ARRAY_LEAF (1) and TUPLE_LEAF (2) are rejected ("Not yet implemented", `gtp_data_path.c:171-173`).
- `05 SLICE {01 start, 02 end}` — only after a DYNAMIC leaf of bytes or string.

Examples: static arg *n* = `[TUPLE n, LEAF STATIC]`. A `bytes` arg = `[TUPLE n, REF, LEAF DYNAMIC]`.

# 3. How trust works

**Signatures.** Every signed blob uses secp256k1 ECDSA over SHA-256, DER-encoded. The test client does the same: `sign_deterministic(…, hashlib.sha256, sigencode_der)` (`AE/client/.../keychain.py:26-36`).

**Verification** (`AE/src/ledger_pki.c:5-63`):
- The app calls the OS `check_signature_with_pki(hash, expected_key_usage, curve, sig)`. This succeeds only if a certificate with that key usage was loaded (B0 06) just before.
- **Legacy fallback:** if no certificate is loaded, the app falls back to a hardcoded key, but only for callers that pass one. Those are ERC-20 token info, the EIP-712 filters, external plugin (all using `LEDGER_SIGNATURE_PUBLIC_KEY`), NFT, and SET_PLUGIN.
- **No fallback for the newer structs:** calldata / TX_INFO, enum, trusted name, proxy, network, tx-simulation, Safe and gating pass `NULL`, so they need the PKI certificate.
- **Build-time switches:** test and staging keys are compile flags, e.g. `HAVE_CAL_TEST_KEY` (`AE/src/public_keys.h:23-90`). `HAVE_BYPASS_SIGNATURES` skips all checks in test builds (`ledger_pki.c:21-31`).

**Hardcoded keys:**
- CAL production key `045e6c1020c1…94979183` (`public_keys.h:38-43`; `ethapp.adoc:274`).
- NFT metadata key and NFT-selector key (`public_keys.h:47-90`).
- **Doc/code mismatch:** the doc lists a different key for SET_EXTERNAL_PLUGIN (`0482bbf2…`, `ethapp.adoc:450`), but the code verifies against `LEDGER_SIGNATURE_PUBLIC_KEY` with usage COIN_META (`AE/src/features/set_external_plugin/cmd_set_external_plugin.c:44-53`).

**Key usages** (the P1 of B0 06) (`CM/shared/utils/KeyUsageMapper.ts:4-20`):

| # | Usage | # | Usage |
|---|---|---|---|
| 1 | genuine_check | 9 | seed_id_auth |
| 2 | exchange_payload | 10 | tx_simu_signer |
| 3 | nft_meta | 11 | calldata |
| 4 | trusted_name | 12 | network |
| 5 | backup_provider | 13 | swap_template |
| 6 | protect_orchestrator | 14 | les_multisig |
| 7 | plugin_meta | 15 | gated_signing |
| 8 | coin_meta | | |

Which usage each command checks is listed at every `check_signature_with_pubkey` call site. Examples: TX_INFO and enum use CALLDATA (`gtp_tx_info.c:188-196`); proxy uses TRUSTED_NAME (`proxy_info.c:196-200`).

**How the host gets certificates.** `GET {cal}/certificates?output=descriptor&target_device=<model>&latest=true&public_key_id=<id>&public_key_usage=<usage>`. The host appends the signature with tag `15` (`CM/modules/multichain/pki/data/HttpPkiCertificateDataSource.ts:38-81`). Key IDs include `cal_calldata_key`, `cal_trusted_name_key`, `domain_metadata_key`, `erc20_metadata_key`, `cal_network`, `cal_gated_signing` and more (`CM/modules/multichain/pki/model/KeyId.ts`). Each descriptor ships `signatures: {prod, test}`, and the host picks one with `config.cal.mode` (default `prod`, branch `main`) (`CM/ContextModuleBuilder.ts:37-53`).

**Challenge (anti-replay):**
- GET_CHALLENGE (`E0 20 00 00 00`) returns a u32 BE value (`AE/src/features/get_challenge/cmd_get_challenge.c:16-57`).
- The device re-rolls the challenge at boot (`main.c:461`) and after every PROVIDE_TRUSTED_NAME (`cmd_trusted_name.c:19`), proxy info (`proxy_info.c:195`) and Safe descriptor.
- A trusted name v2 of type ACCOUNT requires a CHALLENGE tag (`trusted_name.c:537-552`). So the host fetches a fresh challenge before each trusted name and passes it to the backend in the `challenge=` query parameter.

**Unknown contracts.**
- No TX_INFO means the SDK uses basic mode, which only offers plugins, tokens and NFTs.
- In basic mode, calldata with the blind-signing setting off is refused with the "Enable blind signing" screen (`AE/src/features/sign_tx/logic_sign_tx.c:97-105,509-515`). The check is skipped in store mode.
- The setting shows up as bit 0x01 of GET_APP_CONFIGURATION.
- The SDK reports blind-signs to `https://blind-signing.api.ledger.com/ingest/v2/blind-signing-events`.

# 4. EIP-712

**Struct definitions.** `E0 1A 00 00 <name>` for a struct name, and `E0 1A 00 FF` for each field (`ethapp.adoc:623-740`). A field is:
`TypeDesc` ‖ [TypeName len+name] ‖ [TypeSize] ‖ [ArrayLevelCount, levels] ‖ KeyNameLen ‖ KeyName

TypeDesc bits: bit7 = array, bit6 = size given, low nibble = type (0 custom, 1 int, 2 uint, 3 address, 4 bool, 5 string, 6 bytesN, 7 bytes). Array levels: 0 = dynamic, 1 = fixed, the latter followed by a size byte.
- `address from` → `E0 1A 00 FF 06 03 04 66726f6d`
- `uint256 amount` → type desc `42 20`

**Struct implementation.** `E0 1C P1 P2`, with P1 `00` = complete and `01` = partial, more to come.
- P2 `00` = root struct name.
- P2 `0F` = array size (1 byte).
- P2 `FF` = field value, sent as 2-byte BE length ‖ raw value, split into 255-byte slices (`command_builder.py:156-169`).
- Then `E0 0C 00 01 <path>` to sign ("full implementation").

**Filtering.** `E0 1E P1 P2`, with P1 `00` = standard, `01` = discarded (targets a field inside an empty array) (`ethapp.adoc:965-1180`). P2 values:

| P2 | Filter | P2 | Filter |
|---|---|---|---|
| 00 | activate | F9 | calldata value |
| 01 | discarded path | FA | calldata info |
| 0F | message info | FB | trusted name |
| F4 | calldata spender | FC | date/time |
| F5 | calldata amount | FD | amount-join token |
| F6 | calldata selector | FE | amount-join value |
| F7 | calldata chainID | FF | raw field |
| F8 | calldata callee | | |

- **Signed digest:** SHA-256 over magic ‖ chainId (u64 BE) ‖ contract address (the proxy implementation, if one was loaded) ‖ schema hash ‖ … (`AE/src/features/sign_message_eip712/filtering.c:91-121`).
- **Schema hash:** SHA-224 of the `types` JSON with no whitespace (`schema_hash.c:20-62`).
- **The field path is not sent.** The device rebuilds it from its own struct cursor as `key.key.[]` and hashes that (`filtering.c:43-80`).
- **Magic bytes** (`filtering.c:20-32`), with the rest of each signed message:

| Filter | Magic | Signed after the common prefix |
|---|---|---|
| message info | 183 | filters count ‖ display name |
| amount-join token | 11 | path ‖ token index |
| amount-join value | 22 | path ‖ name ‖ token index (FF = verifyingContract, used for Permit) |
| datetime | 33 | path ‖ name |
| trusted name | 44 | path ‖ name ‖ types ‖ sources |
| calldata info | 55 | calldata index ‖ flags |
| calldata value / callee / chainId / selector / amount / spender | 66 / 77 / 88 / 99 / 110 / 121 | path ‖ calldata index |
| raw field | 72 | path ‖ name |

- **Key:** CAL `LEDGER_SIGNATURE_PUBLIC_KEY`, usage COIN_META (`filtering.c:137-145`). The SDK loads an `erc20_metadata_key` / `coin_meta` certificate first (`CM/modules/ethereum/typed-data/domain/DefaultTypedDataContextLoader.ts:112-113`).
- **Host order** (`SE/task/ProvideEIP712ContextTask.ts:134-310`):
  1. extra contexts (network, proxy, gating), then certificate;
  2. struct definitions (types sorted);
  3. activate filtering;
  4. domain implementation;
  5. MessageInfo;
  6. for each message value: token infos (`0A`) and trusted names as needed, then the filter, then the value; discarded paths for empty arrays; nested calldata contexts inline.
- **Source:** filters come from `GET {cal}/dapps?output=descriptors_eip712&descriptors_eip712_version=…&contracts=…&chain_id=…` (`CM/modules/ethereum/typed-data/data/HttpTypedDataDataSource.ts:58-67`).

# 5. Other context APDUs

- **ERC-20 (0A):**
  - Layout: `tickerLen(1) ‖ ticker ‖ addr(20) ‖ decimals u32BE ‖ chainId u32BE ‖ DER sig`.
  - The SHA-256 covers only ticker‖addr‖decimals‖chainId; the length byte is excluded (`AE/src/features/provide_erc20_token_information/cmd_provide_token_info.c:26-63`).
  - The reply is the asset slot index (1 byte).
  - Host source: `GET {cal}/tokens?contract_address&chain_id&output=descriptor`. The host prepends the ticker-length byte itself (`CM/modules/ethereum/token/data/HttpTokenDataSource.ts:25-67`).
- **NFT (14):** `type(1)=01 ‖ version(1)=01 ‖ nameLen ‖ name ‖ addr ‖ chainId u64 ‖ keyId(1) ‖ algo(1)=01 ‖ sigLen ‖ sig`. keyId is 1 for prod, 0 for staging (`cmd_provide_nft_info.c:8-27`). Source: `{metadataService}/v1/ethereum/{chain}/contracts/{addr}`.
- **SET_PLUGIN (16):** same layout, with `selector(4)` added. keyId 2 is prod and may only enable ERC721 / ERC1155; keyId 0 is test (`cmd_set_plugin.c:25-44,206-211`). It returns `0x6984` if the plugin isn't installed. Source: `…/plugin-selector/{selector}`.
- **SET_EXTERNAL_PLUGIN (12):** `nameLen ‖ name ‖ addr ‖ selector ‖ sig`. The signed bytes include the length byte (`cmd_set_external_plugin.c:29-53`). Source: `{cal}/dapps`.
- **Trusted name (22), TLV v2:**
  - Tags: 01 type=03, 02 version=2, 10 not-valid-after, 12 challenge, 13 key id (07 domain service / 09 CAL), 14 algo=01, 15 signature, 20 name, 21 coin type, 22 address, 23 chain ID, 70 type, 71 source, 72 NFT id, 74 owner, 75 owner derivation path.
  - Types: 1 EOA … 6 context address.
  - Sources: LAB 0, CAL 1, ENS 2, UD 3, FN 4, DNS 5, dynamic resolver 6, MAB 7. MAB is not in the doc table, and it requires owner + derivation path (`trusted_name.h:14-40`; `trusted_name.c:440-455,537-560`).
  - Signed digest: SHA-256 of all TLVs except tag 15.
  - Host source: `{metadataService}/v2/names/ethereum/{chain}/reverse/{addr}?types&sources&challenge` or `…/forward/{ens}` (`CM/modules/ethereum/trusted-name/data/HttpTrustedNameDataSource.ts:40,92`).
- **Enum (24):** 00 version, 01 chain ID, 02 contract, 03 selector, 04 id, 05 value, 06 name, FF signature. Uses the calldata key, and comes from the same CAL response as TX_INFO (`HttpCalldataDescriptorDataSource.ts:146-164`).
- **Proxy (2A):** 01 type, 02 version, 12 challenge, 22 address, 23 chain ID, 41 selector (optional), 42 implementation address, 43 delegation type (proxy 1 / factory 2 / delegator 3), 15 signature (`tlv_structs.md:330-350`). Source: `POST {metadataService}/v2/ethereum/{chain}/contract/proxy/delegate {proxy, data, challenge}`.
- **Network (30):**
  - P2 `00` = TLV: 01 type=08, 02 version, 51 family, 23 chain ID, 52 name, 24 ticker, 53 icon SHA-256, 15 signature.
  - P2 `01` = icon bytes. P2 `02` = get info. Two slots.
  - Source: `{cal}/networks?output=id,descriptors,icons`.
- **Tx simulation / Web3 Checks (32):**
  - TLV: 01 type=09, 22 from address, 23 chain ID, 27 tx hash, 28 domain hash, 80 risk (benign 0 / warning 1 / malicious 2), 81 category, 82 provider message, 83 tiny URL, 84 tx type, 15 signature.
  - The device requires the tx hash (and domain hash, for EIP-712) to equal its own computed hash (`cmd_get_tx_simulation.c:520-560`).
  - The partner name is read from the loaded certificate (`:298-305`).
  - Host source: `POST https://global.api.prd.ledger.com/transaction-checks/v3/ethereum/scan/tx` (and `/scan/eip-712`).
- **Safe (36):** P2 `00` = SAFE_DESCRIPTOR (type 0x27, 14 challenge, 22 address, A0 threshold, A1 signers count, A2 role). P2 `01` = SIGNER_DESCRIPTOR (type 0x0A). Uses key `les_multisig`. Source: `{metadataService}/v2/ethereum/{chain}/safe/account/{addr}`.
- **Gating (38):** type 0x0D, 22 address, 23 chain ID, 40 selector or schema hash, 82 intro message, 83 URL, 84 tx type. Source: `{cal}/gated_dapps`.

**Backend base URLs** (`CM/ContextModuleBuilder.ts:25-29`):

| Purpose | URL |
|---|---|
| CAL | `https://global.api.prd.ledger.com/cal/v1` |
| Web3 Checks | `https://global.api.prd.ledger.com/transaction-checks/v3` |
| Metadata service | `https://nft.api.live.ledger.com` |
| Blind-sign reporter | `https://blind-signing.api.ledger.com/ingest` |

The calldata descriptors come from `GET {cal}/dapps` or `{cal}/tokens` with `?output=descriptors_calldata&chain_id=&contracts=&contract_address=&ref=branch:main` (`CM/modules/ethereum/calldata/di/calldataModuleFactory.ts:14-26`; `HttpCalldataDescriptorDataSource.ts:75-83`). The response gives:
- `transaction_info.descriptor.data` (hex TLV) plus `signatures.{prod,test}`
- `fields[].descriptor` (hex TLV, unsigned)
- `enums`

# 6. Byte-level examples

**Real ERC-20 descriptor (USDT) from a device-sdk-ts fixture** (`SE/command/ProvideTokenInformationCommand.test.ts`). I checked this signature against the production CAL key: it verifies against prod and fails against the test key.

```
E0 0A 00 00 67
04 55534454                                  "USDT"
dac17f958d2ee523a2206206994597c13d831ec7     address
00000006 00000001                            decimals=6, chainId=1
3044022078c66ccea3e4dedb15a24ec3c783d7b582cd260daf62fd36afe9a8212a344aed
0220160ba8c1c4b6a8aa6565bed20632a091aeeeb7bfdac67fc6589a6031acbf511c
```

**Generic-parser transfer, rebuilt by me.** This is a USDC `transfer(0xd8dA…6045, 1e6)` on mainnet, built with the app's own encoder rules. I wrote a script (`scratchpad/ex.py`) mirroring `gcs.py`/`tlv.py`, but did not run it on a device or emulator. The TX_INFO signature can't be reproduced without Ledger's key, so it is shown as a placeholder.

```
1) SIGN store   E0 04 00 01 85  05 8000002c 8000003c 80000000 00000000 00000000
   02f86d0180843b9aca008506fc23ac0082ea6094a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
   80b844a9059cbb000000000000000000000000d8da6bf26964af9d7eed9e03e53415d37aa96045
   00000000000000000000000000000000000000000000000000000000000f4240c0
2) (B0 06 0B 00 <calldata certificate>)
3) TX_INFO      E0 26 01 00 Lc  00 LL
   000101  0108 0000000000000001  0214 a0b8…eb48  0304 a9059cbb
   0420 4fab79eb57a8e82145421f66997469d443cd657adec04f0cf3ce8807d0da97b8
   0504 "send"  0606 "Circle"  81ff 47 <DER sig by cal_calldata_key>
4) FIELD "To" (RAW, address, path [TUPLE 0, LEAF STATIC])
   E0 28 01 00 28 0026 0001010102546f020100031a0001010115000101010105020114030a00010101020000040103
5) (E0 0A … USDC token info, needed by the next field's token = container TO)
6) FIELD "Amount" (TOKEN_AMOUNT, value [TUPLE 1, LEAF STATIC], token CONTAINER_PATH TO)
   E0 28 01 00 3a 0038 0001010106416d6f756e7402010203280001010115000101010101020120030a0001010102000104010302
   0c000101010105020114040101
7) SIGN start   E0 04 00 02 00        → v ‖ r ‖ s
```

FIELDS_HASH = SHA3-256(field4 TLV ‖ field6 TLV) = `4fab79eb…97b8`.

For a real signed TX_INFO plus FIELD with a threshold, `CM/modules/ethereum/calldata/data/HttpCalldataDescriptorDataSource.test.ts:61-142` has an Aave `withdraw` descriptor (test-key signature, version 0). Its "Amount to withdraw" field decodes as: TOKEN_AMOUNT, value `[TUPLE 1, STATIC]`, token `[TUPLE 0, STATIC]`, threshold `0xff…ff`, label "Max". Complete runnable flows with test keys are in `AE/tests/ragger/test_gcs.py` (e.g. `test_gcs_nft`, lines 41-209); the test signing PEMs are in `AE/client/.../keychain/`.

# Uncertain or flagged

- **TX_INFO / FIELD version:** the spec doc says 0; the device code requires 1. The code wins.
- **External-plugin key:** the doc names `0482bbf2…`; the code verifies with `LEDGER_SIGNATURE_PUBLIC_KEY`.
- **Legacy certificate fallback:** it runs only when the OS reports a missing or wrong-usage certificate, not a bad signature. I didn't check whether "wrong usage" can hide a mismatched certificate.
- **Backend response schemas:** I read only the DTO types, not live responses. I made no network calls to Ledger's backends.
- **Store-mode limits:** I did not trace compressed-calldata size limits or the max tx size in store mode.
