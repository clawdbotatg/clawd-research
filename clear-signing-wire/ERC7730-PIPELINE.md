# ERC-7730: how a JSON descriptor becomes what a hardware wallet shows

Everything below comes from shallow clones made on 2026-09-27, plus the GitHub API and web searches. The clones are in the scratchpad (`.../scratchpad/{ercs,reg,py,appeth}`). Line numbers refer to those checkouts.

- ERCs HEAD for `ERCS/erc-7730.md`: `bd8c36bc` (2026-09-25)
- Registry: `53d86dc` (2026-09-25). The old LedgerHQ URL now redirects to `ethereum/clear-signing-erc7730-registry`.
- python-erc7730: `72c0fb8` (2026-09-15)
- app-ethereum: `5a48940` (2026-09-22)

---

## 1. File anatomy (v2 schema line, active version 2.1.0)

**Top level:** `$schema`, `context`, `metadata`, `display`, and optionally `includes`.

**Versioning** (`erc-7730.md` L127–203, merged via ERCs #1838 on 2026-06-24):
- Schema versions follow semver. Alias files (`erc7730-v2.schema.json`) sit next to immutable exact-version files.
- A wallet MUST reject a descriptor whose MAJOR version it does not implement.
- Current table: 1.0.0 deprecated, 2.0.0 superseded, **2.1.0 active** (its commit ID is still "TBD"), 3.0.0-next is the draft.
- 2.1.0 differs from 2.0.0 only by adding `threshold`/`message` to the `amount` format (#1991, 2026-09-25).
- The 3.0.0-next draft makes the function-signature regex stricter (a MAJOR change). It also lacks the 2.1.0 `amountParameters`, so the draft is behind the active line. (Found by diffing `assets/erc-7730/*.schema.json`.)

**`context`** (L493–600): binds the file to the data it may format.
- Calldata: `contract.deployments[] {chainId, address}`, plus `contract.factory {deployEvent, deployments}`. `contract.abi` is still there but marked deprecated.
- EIP-712: `eip712.domain` (key/value subset match), `eip712.deployments` (matched against `domain.chainId` + `verifyingContract`), and `eip712.domainSeparator`. `eip712.schemas` is deprecated.
- **The big v2 change** (#1289, "Remove embedded ABI; keys-as-schema", 2025-11-05): the ABI and EIP-712 types now live in the `display.formats` keys.
  - Calldata keys are named fragments such as `transfer(address to,uint256 value)`. The wallet strips the names, takes keccak, and uses the first 4 bytes as the selector (L807–830).
  - EIP-712 keys are the full `encodeType` string, which must hash to the typeHash.

**`metadata`** (L602–768):
- `owner` (optional since 2026-07-22), `contractName`, `info {url, deploymentDate}`
- `token {name, ticker, decimals}`, only for tokens that lack the ERC-20 view functions
- `constants`, referenced as `$.metadata.constants.X`
- `maps {name: {$keyType, values}}`, referenced as `{map, keyPath}`. If no key matches, the whole file is invalid for that transaction.
- `enums {name: {value: label}}`

**`display`** (L770+):
- `definitions` holds reusable field specs, referenced as `$ref: "$.display.definitions.X"` with local `params` overrides.
- Each `formats[key]` entry has `intent` (a string, or a flat object of label/value pairs), `interpolatedIntent` (`"Send {value} to {to}"`, `{{`/`}}` escapes, MUST fall back to `intent` on any failure; L297–395, L1769–1818), and `fields[]`.
- A field is `{path|value, label, format, params, visible, separator, encryption, $id}`.
- A group is `{path?, label?, iteration: sequential|bundled, fields}` (L1118+).
- **`required`/`excluded` are gone in v2.** v1 had `required[]`/`excluded[]` arrays and a `screens` section. v2 uses a per-field `visible`: `always` | `never` | `optional` | `{ifNotIn:[...]}` | `{mustMatch:[...]}` (L1066–1076). `mustMatch` means "hide the field, and error if the value doesn't match."

**Formats** (L1340–1537):

| Type | Formats and params |
|---|---|
| Integer | `raw`; `amount` (native currency; `threshold`/`message` from 2.1.0); `tokenAmount` (`tokenPath`\|`token`, `nativeCurrencyAddress` string or array, `threshold` using ≥ as of 2026-09-25, `message` defaulting to "Unlimited", `chainId`\|`chainIdPath` added 2026-02); `nftName` (`collectionPath`\|`collection`); `date` (`encoding: timestamp|blockheight`); `duration`; `unit` (`base`, `decimals`, `prefix`); `enum` (`$ref`); `chainId` |
| String | `raw` |
| Bytes | `raw`; `calldata` (`calleePath`\|`callee`, `selectorPath`\|`selector`, `chainId*`, `amountPath` → the inner `@.value`, `spenderPath` → the inner `@.from`; L1251–1315) |
| Address | `raw`; `addressName` (`types`: wallet/eoa/contract/token/collection; `sources`: e.g. local/ens; `senderAddress`); `tokenTicker` |
| Bytes (ERC-7930) | `interoperableAddressName` |

v1's `percentage` format was dropped. The encryption hint `{scheme: "fhevm", plaintextType, fallbackLabel}` was added 2026-02 for Zama/ERC-7984.

**Paths** (L242–295): a limited JSONPath with dot notation and three roots:
- `#.` is the decoded structured data. It is also the default when no root is given.
- `$.` is the merged descriptor file.
- `@.` is the container: `@.from`, `@.to`, `@.value`, `@.chainId` (L1318–1338). For EIP-712, `@.to`/`@.chainId` come from the domain, and the wallet SHOULD reject if they are unknown.
- Array index and slice syntax: `x.[0]`, `x.[-1]`, `x.[:20]`, `x.[-20:]` (no step). Slices also work on `bytes`.
- `includes` merges another file, with the including file winning. `fields` are merged by `path` (L397–491).

**Problems in the spec text itself:**
- L857–864 uses formats `"number"` and `"bytes32"`, which the spec does not define.
- The airdrop example uses `recipients[0]` and `recipients.length`, which break the spec's own dot-only `.[0]` rule.
- The spec says a key "MUST NOT" have a space after a comma (L809). **496 of the registry's 938 format keys do** (e.g. Safe's `execTransaction(address to, uint256 value, …)`), and the tooling accepts them.

---

## 2. From registry JSON to device (Ledger)

1. **Registry.** Descriptors pass CI (`.github/workflows/`):
   - `erc7730 lint --require-verified`, which requires the contract to be verified on Sourcify
   - schema validation
   - Sourcify test runner over the mandatory `testsv2/*.tests.json`
   - an LLM analyzer (`LedgerHQ/erc7730-analyzer`)
   - automatic regeneration of `index.calldata.json` / `index.eip712.json`, keyed by `eip155:chain:addr`
   - weekly spec sync from ERCs

   The registry pins **`sourcifyeth/python-erc7730`**, a fork 25 commits ahead of LedgerHQ and 0 behind (`.github/requirements.txt`).

2. **Resolved form** (`erc7730 resolve`; `convert/resolved/v2/convert_erc7730_input_to_resolved.py`). Includes are inlined, URLs fetched, `$ref`/constants/definitions inlined, nested fields flattened where possible, selectors turned into 4-byte form, addresses lowercased (`docs/pages/usage_cli.md` L123–133).

3. **Ledger "calldata descriptor", a.k.a. Generic Parser** (`erc7730 calldata`; `convert/calldata/convert_erc7730_v2_input_to_calldata.py`). The output is one descriptor per (chainId, address, selector):
   - `_convert_v2_selector` (~L195–266) builds TRANSACTION_INFO:
     - `operation_type = first_not_none(intent, $id, selector)`
     - `creator_name = owner`, `contract_name = contractName or context.$id`, `deploy_date`
     - `hash = sha3_256(concat(FIELD TLVs))` (L240). This is **NIST SHA3-256, not keccak**; `doc/tlv_structs.md` agrees.
   - Enums become ENUM_VALUE structs. ID and value are **uint8 only**; the model enforces 0–255.
   - Each field becomes one FIELD struct. Groups are flattened, `visible:"never"` fields are dropped, and a missing `label` is an error.
   - `mustMatch`/`ifNotIn` become `VISIBLE = MUST_BE`/`IF_NOT_IN` plus up to **5** `CONSTRAINT` tags, **only on `raw` and `addressName`**. On other formats the converter errors out, because "the device ignores them" (L270–340).

4. **TLV bytes** (`convert/calldata/v1/tlv.py`). Tags are at L51–206. `common/binary.py tlv()` uses DER-encoded tag and length and is limited to 255 bytes per value.
   - TRANSACTION_INFO tags: VERSION 0x00, CHAIN_ID u64, CONTRACT_ADDR, SELECTOR, FIELDS_HASH, OPERATION_TYPE, CREATOR_NAME / LEGAL_NAME / URL, CONTRACT_NAME, DEPLOY_DATE u32, **SIGNATURE 0xFF**.
   - FIELD holds NAME, PARAM_TYPE, PARAM, VISIBLE, CONSTRAINT. A PARAM_* contains VALUE structs (type family/size plus a DATA_PATH of TUPLE/ARRAY/REF/LEAF/SLICE elements, or a CONTAINER path FROM/TO/VALUE/CHAIN_ID, or a CONSTANT).
   - The library **does not sign**. The 0xFF tag is defined but never emitted. The model has a field described as "Serialized, hex encoded Protobuf payload used for production signature" (`model/calldata/v1/instruction.py` L35–40).

5. **Ledger CAL backend (closed source; inferred from the client).** The host calls `GET https://global.api.prd.ledger.com/cal/v1/dapps?output=descriptors_calldata&chain_id=…&contracts=…&ref=branch:main`. The URL is the default in `device-sdk-ts/.../ContextModuleBuilder.ts` L25; the request is built in `HttpCalldataDescriptorDataSource.ts` L75–82.
   - The response is `descriptors_calldata[address][selector]`: `transaction_info.descriptor = {data, signatures: {prod, test}}`, `enums[id][value] = {data, signatures}`, and each field is `{descriptor, param}` (`CalldataDto.ts`).
   - **Only TRANSACTION_INFO and ENUM_VALUE are signed.** FIELD structs are unsigned; the device checks them through FIELDS_HASH.
   - The host adds the signature tag and loads a PKI certificate for `KeyUsage.Calldata` / `KeyId.CalCalldataKey`, per device model.
   - How Ledger pulls from the registry and runs the conversion is **not public**. I'm assuming CAL runs python-erc7730 or something equivalent.

6. **APDUs** (`app-ethereum doc/ethapp.adoc`, `doc/gcs.md`):
   1. SIGN in "store only" mode (compressed calldata is kept in RAM)
   2. `E0 26` TRANSACTION INFO (L1295)
   3. For each field: supporting metadata (token info, NFT info, `E0 xx` ENUM VALUE L1258, TRUSTED NAME L1211, PROXY INFO `E0 2A` L1375), then `E0 28` TX FIELD DESCRIPTION (L1335)
   4. SIGN to start the flow. The device recomputes the fields hash, shows the fields, and returns r,s,v.

   Nested calldata pushes a second TRANSACTION INFO into a linked list partway through the field loop (`gcs.md`). Related signed structs include PROXY_INFO (PROXY / ISSUED_FROM_FACTORY / DELEGATOR), NETWORK_INFO, TX_SIMULATION (risk score), **SAFE_ACCOUNT** (threshold, signer count, role) and GATING_DESCRIPTOR (`doc/tlv_structs.md` L330–464).

7. **EIP-712 goes a separate legacy route** (`convert/ledger/eip712/convert_erc7730_v2_to_eip712.py`). v2 descriptors become the `ledger-asset-dapps`/`eip712-clearsign` format: per-chain `{contracts: [{address, messages: [{schema, mapper: {label, fields}}]}]}`, with the schema rebuilt from the `encodeType` key.
   - On the device this becomes EIP712 FILTERING APDUs (ethapp.adoc L810+).
   - Each filter carries its own signature over, for example, `183 || chainId || contract || schemaHash || filtersCount || displayName`, where schema hash = sha224 of the `types` JSON.

**What gets lost or simplified**

Ledger calldata path:
- `interpolatedIntent` is **dropped entirely** (the converter never reads it; the linter only length-checks it).
- An `intent` object has no string mapping.
- `separator`, `iteration`, `encryption`, `visible:"optional"` and group labels are dropped.
- `interoperableAddressName` hits "Unsupported format".
- `tokenTicker`'s `chainId` is ignored with a warning (L863–874).
- Chains missing from Ledger's hard-coded network list are skipped (`common/ledger.py`).
- Length caps (`common/ledger.py` L258–265, from `gtp_tx_info.h`): OPERATION_TYPE 30, CREATOR_NAME 22, LEGAL_NAME 30, URL 26, CONTRACT_NAME 30, FIELD_NAME 20, ENUM 20.
- Device PARAM types: RAW, AMOUNT, TOKEN_AMOUNT, NFT, DATETIME, DURATION, UNIT, ENUM, TRUSTED_NAME, CALLDATA, TOKEN, NETWORK.

Ledger EIP-712 path, which loses much more:
- `enum`, `unit`, `duration`, `tokenTicker` and `chainId` all fall back to **RAW**.
- `nftName` becomes TRUSTED_NAME.
- A constant `token`, a constant `value` or any `@.` container path is an error.
- There is **no threshold/"Unlimited"** field in the mapper.
- `mustMatch`/`ifNotIn` are not handled; only `never` is honoured. So a `mustMatch` field on an EIP-712 message would be *shown* rather than *enforced*. That comes from reading the code (L164–167, L231–289). I did not test it on a device.

---

## 3. Status, open work and critiques

**Status:** `status: Draft` (header L7). Created 2024-02-07, first merged 2024-06-26 (#509), with continuous revisions since. It has eight authors from Ledger, WalletConnect/Reown, Sourcify, Ethereum Foundation and others. 2026 work includes semver, the encryption hint, token `chainId`, `owner` made optional, and `amount` threshold.

**Governance:**
- Ledger handed the registry to the Ethereum Foundation in 2026.
- The Foundation's Trillion Dollar Security Initiative (1TS) now looks after the registry, promoted through clearsigning.org and the "Clear Signing Alliance" GitHub org.
- Public launch was 2026-05-12, with a named working group: Ledger, Trezor, ZKnox, Sourcify, Cyfrin, Zama, WalletConnect, Fireblocks, Keycard, MetaMask, Argot.

**Attestation model** (`reg/auditors/README.md`):
- An auditor signs an **EAS offchain attestation** under schema `0xe023eef1…b5c2` (proposed ERC-8176, ERCs #1576, still open).
- The attested data is `descriptorHash = keccak256(RFC 8785 JCS-canonical JSON)`, computed with Cyfrin's `clearsig dh`.
- It is stored at `registry/<entity>/sigs/<file>.eip155-1-0x<auditor>.json`. Revocation goes through EAS, and each wallet picks which auditors it trusts.
- **Today there is one auditor.** All 174 attestations come from `0x3846…31f6` (Patrick Collins / Cyfrin), and 104 of them are for Morpho.
- Nothing I found shows Ledger or Trezor firmware checking ERC-8176. Each vendor still signs its own payloads.

**Registry snapshot:**
- 57 entities, 285 calldata + 102 EIP-712 entity descriptors (407 JSON files including `common-*` and `ercs/`), 307 testsv2 fixtures.
- 78 GitHub contributors. Top committers are Ledger staff (lcastillo, paoun, jnicoulaud), then Sourcify (kuzdogan, manuelwedler).
- Which features are actually used, counted by file:

| Feature | Files |
|---|---|
| `includes` | 220 |
| `interpolatedIntent` | 62 |
| `enum` | 34 |
| `unit` | 29 |
| `calldata` | 20 |
| `nftName` | 18 |
| `ifNotIn` | 3 |
| `encryption` | 1 |
| `mustMatch`, `maps`, `tokenTicker`, `chainId`, `interoperableAddressName` | 0 |

**Main open ERC-7730 pull requests:**
- #1738 (Cyfrin): intent mutability, adding `context.contract.proxy` and `stateRefs` storage-slot preconditions. The auditor README already asks auditors to check these, but they are not in any published schema.
- #2003 (bind proxy descriptors to implementation addresses): closed.
- #1402: command registries and packed multicall (Universal Router, Safe MultiSend).
- #1923: `boundaries` to refuse signing automatically; #1781: `alert` field.
- #1783 and #1906: i18n and translation files. The spec currently says i18n is out of scope.
- #1925: custom encoding layout; #1784: storage layout.
- #1974: behaviour for a non-zero native value; #2031: make `intent` mandatory; #2027: date `specialValues`; #1663: constants and maps in fields.
- Companion ERCs: **ERC-8176** attestations (#1576), **ERC-8213** digest display (#1639), **ERC-8283** on-chain registry of IPFS pointers plus EAS UIDs (#1789), and ERC-8009 proxy clear signing (#1184). ERC-8265 is described in #1789 as a "transaction envelope".

**Critiques:**
- **Trust stops at the vendor's key.** On Ledger, the device trusts the CAL key and the PKI certificate, not the registry or the auditors. Anything a converter drops or maps loosely (EIP-712 enum shown as RAW, hidden `mustMatch`) is invisible to the auditor, who signed the JSON, not the TLV. The spec asks registries for provenance and tamper-evident history (L1699), which ERC-8176 only partly delivers.
- **Hard cases are still weak.**
  - Multicall and Universal Router can't be expressed without #1402.
  - Safe's `execTransaction` uses `format: calldata` over `data` (`registry/safe/common-Safe.json`). Rendering then depends on a descriptor for the inner target and on the device's nesting support. MultiSend's packed bytes can't be described at all.
  - Permit2 is covered as EIP-712 (`uniswap/eip712-uniswap-permit2.json`), but it goes through the lossy legacy route on Ledger.
  - The auditor guide says to *omit* functions whose intent depends on time, `tx.origin`, runtime-resolved targets, or "composition (multicall, AA batch, hook)".
- **Descriptors can go stale.** Proxy upgrades and admin-mutable state can make a correct descriptor show a wrong intent. That is what #1738 tries to fix.
- **Spec and corpus disagree.** Beyond the key-format violations, the spec's examples use undefined formats, and the 3.0.0-next draft is behind 2.1.0.

---

## 4. Other consumers

**Hardware (needs a compact, vendor-signed payload):**
- **Ledger** (flow above). Calldata goes through the Generic Parser; EIP-712 goes through filtering. Served by CAL through Ledger Wallet (formerly Ledger Live), the Device Management Kit and `hw-app-eth`.
- **Trezor**, live 2026-09-08 through Suite, Connect and WalletConnect.
  - Supported: Safe 7/5/3 and Model T; not Model One. Launch protocols: 1inch, Aave, Lido, Tether, LiFi, Hyperliquid.
  - The firmware takes an `EthereumDisplayFormatInfo` protobuf: chain_id, address, func_sig, intent, ABI parameter definitions, field definitions, provider_name (`common/protob/messages-definitions.proto`).
  - Only **8 formatters**: addressName, amount, tokenAmount, unit, raw, date, calldata, enum. There is no nftName, duration, tokenTicker or chainId; duration is open issue #7948.
  - Blobs are fetched from `data.trezor.io/firmware/definitions/eth/chain-id/<id>/display-format/<addr>-<sel>.dat`. They are Merkle-proof plus multisig signed by SatoshiLabs definition keys (`python/src/trezorlib/definitions.py`).
  - Open issues include nested tuples (#7574), recursive ABI parsing (#7890), and an Aave "repay all" wrongly shown as "Unlimited" (#7596).
- **Keycard Shell:** so far ships ERC-8213 digests rather than full ERC-7730 rendering (Walletbeat).

**Software (renders the JSON directly and supplies its own token, ENS and name data):**
- Libraries:
  - Sourcify's TypeScript reference library `sourcifyeth/clear-signing`, which runs in browsers, Node ≥22 and React Native. The wallet has to supply ENS names and token data itself (`ExternalDataProvider`).
  - Rust and TypeScript SDKs funded by 1TS.
  - Cyfrin `clearsig`.
- **Ambire** says it supports ERC-7730.
- WalletConnect runs a certification program (DFNS mentions relying on WalletConnect-verified descriptors).
- **MetaMask, Rabby, Safe{Wallet}:** I could not confirm shipped ERC-7730 rendering. Safe is a descriptor *publisher* in the registry; MetaMask is a working-group member with a 2025 Ledger partnership.
- Walletbeat now scores wallets on ERC-7730 against test transactions.

**Uncertain or unverified:**
- How CAL ingests from the registry and whether the conversion is exactly python-erc7730.
- The "Protobuf production signature" format.
- Whether the EIP-712 `mustMatch` handling I read in the code matches device behaviour.
- The "V2 released April 2026" claim comes from press; the ERC table shows only 2.0.0 and 2.1.0 with no dates.
- The "~28% registry growth" figure is from press (Crypto Briefing, via Cryptonomist).

Sources:
- [ERC-7730](https://eips.ethereum.org/EIPS/eip-7730)
- [Registry](https://github.com/ethereum/clear-signing-erc7730-registry)
- [python-erc7730](https://github.com/LedgerHQ/python-erc7730)
- [app-ethereum](https://github.com/LedgerHQ/app-ethereum)
- [device-sdk-ts](https://github.com/LedgerHQ/device-sdk-ts)
- [trezor-firmware](https://github.com/trezor/trezor-firmware)
- [EF blog 2026-05-12](https://blog.ethereum.org/2026/05/12/clear-signing-announcement)
- [Ledger v2 blog](https://www.ledger.com/blog-the-evolution-of-clear-signing)
- [Trezor rollout (Cryptonomist)](https://en.cryptonomist.ch/2026/09/09/trezor-erc-7730-signing/)
- [Cryptopolitan](https://www.cryptopolitan.com/trezor-erc-7730-clear-signing-safe-wallets/)
- [CoinDesk](https://www.coindesk.com/tech/2026/05/12/the-ethereum-foundation-unveils-new-clear-signing-standard-to-stop-users-from-approving-malicious-crypto-transactions)
- [Clear Signing Alliance](https://clearsigning.org/docs/intro/)
- [Sourcify clear-signing](https://github.com/sourcifyeth/clear-signing)
- [Ambire](https://blog.ambire.com/clear-signing-erc-7730/)
- [Cyfrin](https://www.cyfrin.io/blog/blind-signing-solved)
- [Walletbeat Keycard](https://beta.walletbeat.eth.limo/keycard-shell/)
- [DFNS](https://dfns.co/article/institutional-certified-by-walletconnect)
