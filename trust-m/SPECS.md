# Infineon OPTIGA Trust M: specs and product family

Researched 2026-10-08. Primary sources are Infineon's own PDFs in the
[optiga-trust-m-overview](https://github.com/Infineon/optiga-trust-m-overview) repo
(Datasheet v3.70, Solution Reference Manual (SRM) v3.70, Config Guide v2.2, Keys & Certificates v3.10,
Release Notes v3.02, I2C Protocol v2.03), the host library repo
[optiga-trust-m](https://github.com/Infineon/optiga-trust-m) and its
[wiki](https://github.com/Infineon/optiga-trust-m/wiki). Short names used below:

- **DS** = [Datasheet v3.70 (2024-10-09)](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/OPTIGA_Trust_M_Datasheet_v3.70.pdf)
- **SRM** = [Solution Reference Manual v3.70](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/OPTIGA_Trust_M_Solution_Reference_Manual_v3.70.pdf)
- **CFG** = [Configuration Guide v2.2 (2024-01-17)](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/OPTIGA_Trust_M_ConfigGuide_v2.2.pdf)
- **KC** = [Keys and Certificates v3.10](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/OPTIGA_Trust_M_Keys_And_Certificates_v3.10.pdf)
- **RN** = [Release Notes v3.02 (2025-02-03)](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/OPTIGA_Trust_M_Release_Notes_v3.02.pdf)
- **I2CP** = [Infineon I2C Protocol v2.03](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/Infineon_I2C_Protocol_v2.03.pdf)
- **DUMPS** = [real-chip object dumps, one per variant](https://github.com/Infineon/optiga-trust-m-overview/tree/main/data/object_dumps)

Flags: **[unconfirmed]** = could not verify from a primary source. **[inferred]** = my reading of the docs, not stated outright.

---

## 1. TL;DR

- One silicon/package family: **SLS 32AIA010Mx**, USON-10 3x3 mm, I2C only, 1.62–5.5 V. Variants differ by firmware version (V1 vs V3) and factory provisioning (standard, Express, MTR).
- **V1 is dead** (MH/MS: end of life, last-time-buy passed). **V3 is current** (MK/ML, plus Express and MTR, which are V3 chips with different provisioning).
- Curves: NIST P-256/384 (V1); V3 adds P-521 and Brainpool P256r1/P384r1/P512r1. **No secp256k1, no Ed25519/X25519, on any version.** RSA 1024/2048 only.
- ECDSA P-256 sign ≈ 60–65 ms, verify ≈ 85 ms, keygen ≈ 55–75 ms, ECDH ≈ 60 ms (DS, P-256 only; no published times for other curves).
- Every chip ships with a **unique P-256 key in 0xE0F0 that can never be read or replaced**, plus a unique X.509 cert in 0xE0E0. V1 certs are issued by "Trust M CA 101", V3 by "CA 300", Express/MTR by "CA 306". Subject is just "Infineon IoT Node" / "InfineonIoTNode" (no serial in the subject).
- Built-in **throttling** (security monitor): after ~5 free + 127 counted private-key uses in quick succession, every further private-key op gets slowed toward **one per 5 s**.
- Cert: hardware platform is **CC EAL6+** (BSI-DSZ-CC-0961, currently V7-2024, valid to 2027-03-23). The Trust M product itself is **not** CC certified; the V3 MK part is **PSA Certified Level 3**.
- **EUCLEAK** (2024): NinjaLab showed the ECDSA side-channel flaw extends to Trust M. Infineon shipped firmware v3.02.2564 in 2025 with "improved side channel resilience". Chips already in the field can't be updated.
- Price ≈ **$0.73–$1.00 at reel volume**, $2 single unit.

---

## 2. Variants and part numbers

### 2.1 The family

| Variant | Sales code | Temp | FW | Factory provisioning | Status (2026) |
|---|---|---|---|---|---|
| Trust M V1 ETR | SLS32AIA010**MH** | −40…+105 °C | v1.x | E0E0/E0F0 P-256 key + cert (CA 101) | **EOL / last-time-buy** |
| Trust M V1 STR | SLS32AIA010**MS** | −25…+85 °C | v1.x | same | **EOL**, LTB was 2026-06-15 |
| Trust M V3 STR | SLS32AIA010**MK** | −25…+85 °C | v3.x | E0E0/E0F0 P-256 key + cert (CA 300) | Active (OPN …XTMB2) |
| Trust M V3 ETR | SLS32AIA010**ML** | −40…+105 °C | v3.x | same | Active (OPN …XTMC1) |
| Trust M Express | ML or MK (different OPN suffix) | both | v3.x | 3 keys+certs (2×P-256 CA 306, RSA-2048 CA 309), locked, cloud-ready (AWS/Azure via CIRRENT Cloud ID) | Active (…MKUSON10XTMB1, …MLUSON10XTMB9) |
| Trust M MTR (Matter) | SLS32AIA010**MM** | −25…+85 °C | v3.x | like Express, plus late-stage Matter DAC provisioning via Kudelski keySTREAM | Active (…XTMA5) |

Sources: DS Tables 1–3 (sales codes, temp ranges); CFG Table 1 (provisioning per variant);
[Infineon KBA "Latest OPN status and active variants", 2026-03-16](https://community.infineon.com/t5/Knowledge-Base-Articles/OPTIGA-Trust-M-Latest-OPN-status-and-active-variants/ta-p/1195051) (status);
V1 EOL from [Rutronik (MS obsolete, LTB 15.06.2026)](https://www.rutronik24.com/product/infineon/sls32aia010msuson10xtma2/12787690.html) and Rochester "End of Life / Last Time Buy" listings via [Findchips](https://www.findchips.com/search/2AI-A).

Notes:
- **Express and V3 share the same sales code (MK/ML)**. Only the OPN suffix tells them apart. The DS lists Express as `SLS32AIA010MLUSON10XTMA9` (now obsolete, replaced by …XTMB9) (DS Table 3; KBA).
- CFG: "The OPTIGA Trust M Express chip is identical to the OPTIGA Trust M V3 chip, however it is provisioned and configured with all of the features required to securely connect the device to the cloud (AWS, Azure)." Same sentence for MTR, plus Matter late-stage provisioning (CFG §1).
- **"Trust M for Azure / AWS pre-provisioned"**: I found no separate AWS-only or Azure-only part. Express is that product. There are partner SKUs (e.g. a CommScope SKU with CommScope certs, per [pki-center.com](https://www.pki-center.com/newsblogs/2025/Infineon-Optiga-Trust-M-Technical-Notes)) and custom provisioning via Infineon/distributors. **[unconfirmed]** whether other partner SKUs exist.
- **Newer parts 2025–2026**: no new silicon or new crypto. The 2026 KBA lists new OPN suffixes (MK…XTMB2, ML…XTMC1, Express …XTMB1/…XTMB9, MTR …XTMA5) and says "the latest firmware is fully backward compatible". All older OPNs are NRND or obsolete. **[inferred]** these new OPNs carry firmware v3.02.2564 (the side-channel fix, see §8); Infineon does not say so directly.
- No PQC Trust M exists. **[unconfirmed]** rumors of a PQC roadmap are third-party only.
- Infineon product page shows "Active and preferred", "$0.83 – $0.97 ea." ([infineon.com/part/OPTIGA-TRUST-M-SLS32AIA](https://www.infineon.com/part/OPTIGA-TRUST-M-SLS32AIA), read 2026-10-08).

### 2.2 V1 vs V3: what changed

From DS Tables 4 and 15, SRM notes ("The OPTIGA Trust M V1 does not support …"):

| Feature | V1 | V3 |
|---|---|---|
| ECC NIST P-256/384 | yes | yes |
| ECC NIST P-521, Brainpool P256r1/P384r1/P512r1 | no | yes |
| RSA 1024/2048 | yes | yes |
| AES-128/192/256 (ECB, CBC, CBC-MAC, CMAC), GenSymKey, AES key slot 0xE200 | no | yes |
| HMAC-SHA256/384/512 | no | yes |
| HKDF-SHA256/384/512 | no | yes |
| TLS 1.2 PRF | SHA-256 only | SHA-256/384/512 |
| Protected update | integrity only, data objects only | integrity **and** confidentiality; data, **keys** and **metadata** |
| Access conditions Auto(), SecStaG/A (boot-phase flag) | no | yes |
| Data object types UPDATSEC, AUTOREF | no | yes |
| Security monitor configurable (0xE0C9) | no | yes (but locked on standard parts, see §6) |
| Metadata tags 0xD8 (metadata update descriptor), 0xF0 (reset type), MUPD access | no | yes |
| GetRandom into session context | no | yes |
| Factory cert CA | Trust M CA 101 | Trust M CA 300 |
| Firmware builds seen | eSW build e.g. 0x0809 in dump | 3.00.2440 (PSA cert), 3.01.2558, 3.02.2564 |

DUMPS show V1 has no 0xE0C9 object; V3 does.

### 2.3 Boards

| Board | Chip | Notes |
|---|---|---|
| [Adafruit 4351](https://www.adafruit.com/product/4351) "Infineon Trust M Breakout – STEMMA QT/Qwiic" | Page says only "OPTIGA TRUST M SLS 32AIA" and lists V1-level specs (P256/P384, 4.5K user memory). Austin's own board reports factory-cert issuer **"Trust M CA 101" → V1** (see `~/clawd/clawd-trust-m` README). | $4.95, out of stock at Adafruit on 2026-10-08. PCB revised silkscreen 2024-07-01, otherwise identical. [PCB repo](https://github.com/adafruit/Adafruit-Infineon-Trust-M-PCB) uses a Trust X footprint symbol and names no OPN. **[unconfirmed]** whether newer Adafruit stock is V3; read 0xE0E0 issuer or 0xE0C2 to check. |
| [MikroE Trust M Click (MIKROE-4236)](https://www.mikroe.com/trust-m-click) | "SLS 32AIA010 OPTIGA Trust M1" (V1) per MikroE | mikroBUS, 3.3/5 V jumper. No MikroE software; uses Infineon repo. |
| SparkFun | Resold the MikroE click ([DEV-18915](https://www.sparkfun.com/mikroe-trust-m-click-dev-18915.html)) and Infineon's IoT Security Dev Kit (DEV-19216). Both retired. SparkFun never made its own Trust M board. | |
| M5Stack | **None found** in search. **[unconfirmed]** | |
| Infineon | Trust M Shield2Go, Trust M Shield (mikroBUS), Trust M Express/MTR shields for PSoC 62S2 kit; [OPTIGA Trust M Eval Kit](https://www.infineon.com/cms/en/product/evaluation-boards/optiga-trust-m-eval-kit/) marked "not for new design" | |

---

## 3. Hardware

### 3.1 Package and pinout

Package **PG-USON-10-2/-4, 3 mm × 3 mm** (DS §4). Pinout (DS Table 6):

| Pin | Name | Function |
|---|---|---|
| 1 | GND | ground |
| 2, 4, 5, 6, 7 | NC | leave floating |
| 3 | SDA | I2C data |
| 8 | SCL | I2C clock |
| 9 | RST | active-low reset, weak internal pull-up |
| 10 | VCC | supply |

Marking: "T&#$@" code, e.g. "TMS10" = Trust M, STR, release 1, software 0; "H YYWW" = production, "E YYWW" = engineering sample (DS Table 5). Engineering samples carry a **test** cert from "Trust M Test CA 000", not a production cert (KC §3).

### 3.2 Electrical (DS §5)

| Parameter | Value |
|---|---|
| VCC | 1.62 – 5.5 V |
| Temp | STR −25…+85 °C, ETR −40…+105 °C |
| I2C modes | SM 100 kHz, FM 400 kHz, FM+ 1 MHz. **Factory default mode = SM & FM** (I2C_MODE 011b), FM+ must be switched on via register 0x89 |
| I2C address | 0x30 default; can be changed, volatile or persistent (register 0x83) |
| Active current | 14 mA typ while running an auth profile (25 °C, 5 V). Software current limit 6–15 mA in 1 mA steps (object 0xE0C4) |
| **Default current limit** | **6 mA** (SRM Table 73; DUMPS e0c4 = 06). Datasheet timings are measured "without power limitation". 9 mA ≈ 60 % of best-case speed; 15 mA = best case (SRM Table 73). So a stock chip is slower than the DS numbers until you raise 0xE0C4. **[inferred]** how much slower at 6 mA; not published. |
| Sleep current | 70 µA typ, 100 µA max (3.3 V, idle, I2C ready) |
| Hibernate | < 2.5 µA (VCC off, I2C lines held) |
| Startup | ≥ 15 ms after power-on or reset; up to 20 ms if NVM write was pending |
| VCC ramp | 1–1000 µs (400 mV → 90 %) |
| Lifetime | 20 years (industrial automation/infrastructure profile), 15 years otherwise (DS front page) |

Sleep: chip auto-sleeps after "sleep activation delay" (0xE0C3, 20–255 ms, default 20 ms) and wakes on its I2C address (SRM §4.2.1). It only sleeps once the security event counter is back at 0 (SRM §4.6.4).

---

## 4. Crypto

All from DS Table 4, SRM §4.4.2 (Tables 57–63), and
[optiga_lib_common.h](https://github.com/Infineon/optiga-trust-m/blob/main/include/common/optiga_lib_common.h).

| Category | Supported | Version |
|---|---|---|
| ECC curves | NIST P-256 (0x03), P-384 (0x04) | V1+V3 |
| | NIST P-521 (0x05), Brainpool P256r1 (0x13), P384r1 (0x15), P512r1 (0x16) | V3 only |
| ECC ops | ECDSA sign/verify (FIPS 186-3), key gen, ECDH (SP 800-56A) | |
| **secp256k1** | **No.** Not in the algorithm identifier table (SRM Table 57), not in the host library enum, not in the cert parser's curve list (SRM §6.4.1). Same for V1 and V3. | none |
| **Ed25519 / X25519 / EdDSA** | **No**, any version. Same evidence. | none |
| RSA | 1024, 2048 ("exponential" format, 4-byte public exponent). Sign: RSASSA-PKCS1-v1.5 with SHA-256/384/512. Encrypt/decrypt: RSAES-PKCS1-v1.5 only. **No PSS, no OAEP, no RSA-3072/4096.** | V1+V3 |
| AES | 128/192/256; ECB, CBC, CBC-MAC, CMAC. **No GCM/CCM/CTR exposed to the host** (CCM is used internally for Shielded Connection and protected update). ECB/CBC need host-side padding. | V3 |
| HMAC | SHA-256/384/512 (gen + verify) | V3 |
| Hash | CalcHash: **SHA-256 only** | V1+V3 |
| KDF | TLS 1.2 PRF SHA-256 (V1+V3), SHA-384/512 (V3); HKDF SHA-256/384/512 (V3). Derive from session context or a data object holding a pre-shared secret (≤ 64 bytes). Output 16–66 bytes into a session, up to 256 bytes if exported. | |
| RNG | TRNG (AIS-31), DRNG (SP 800-90A), RSA pre-master secret. 8–256 bytes per call. | V1+V3 |
| Key agreement | ECDH only. Shared secret can stay in a session context and feed DeriveKey. | |

Signing details (SRM §4.4.1.12): CalcSign signs a **digest you supply** (ECDSA: 10 bytes up to key size; max 64 bytes). Output is DER-ish: r and s as two DER INTEGERs (not wrapped in a SEQUENCE). The SRM does not say whether ECDSA nonces are random or RFC 6979. **[unconfirmed]**; assume random.

Key handling:
- GenKeyPair into a key slot: private key never leaves ("no private key export!"). GenKeyPair with no OID: key pair is returned in plain, i.e. the chip acts as a key generator only (SRM Table 53).
- **Private key import**: only on V3, only via protected update (signed manifest, optional encryption) (SRM §6.7.2). No plain "write private key" command exists.
- Public keys are not stored next to private keys; you get the public key once at generation (or from the cert). **[inferred]** from SRM §6.7.2.1 ("If the target … does not store the public key…").

Ethereum relevance: Trust M **cannot** sign Ethereum transactions (no secp256k1). It **can** produce P-256 signatures that verify on chain via the P-256 precompile (RIP-7212 on L2s / EIP-7951 on L1). That is exactly what `~/clawd/clawd-trust-m` does.

---

## 5. Performance (DS Tables 17–18, SRM Table 64)

Conditions: I2C 400 kHz, 25 °C, 3.3 V, **no current limit** (i.e. 15 mA, not the 6 mA default), no hashing included.

| Operation | V1 (ms) | V3 (ms) | V3 with Shielded Connection (ms) |
|---|---|---|---|
| ECDSA sign P-256 | ~60 | ~65 | ~70 |
| ECDSA verify P-256 (pubkey from host) | ~85 | ~85 | ~95 |
| ECDH P-256 (ephemeral) | ~60 | ~60 (wiki: ~55) | ~65 |
| ECC P-256 keygen | ~75 | ~55 (into session) | ~60 |
| RSA-2048 sign | ~310 | ~310 | ~320 |
| RSA-2048 verify | ~45 | ~40 | ~50 |
| RSA-2048 keygen | ~2900 (varies a lot; RN says can exceed 50 s, lib timeout 180 s) | ~2900 | ~2910 |
| RSA-2048 encrypt / decrypt (127 B) | ~30 / ~310 | ~40 / ~315 | ~50 / ~325 |
| AES-128 ECB enc / dec (256 B in DS, 128 B in SRM) | — | ~28 / ~35 | ~35 / ~42 |
| AES-128 CMAC (128 B) | — | ~28 | — |
| HMAC-SHA256 (128 B) | — | ~90 | ~95 |
| TLS PRF SHA-256 (40 B out) | ~50 (wiki ~135) | ~50 (wiki ~135) | ~55 |
| HKDF-SHA256 | — | ~130 | ~135 |
| SHA-256 throughput | ~12 KB/s | ~15 KB/s | ~14 KB/s |
| Read 256 B / write 256 B | — | ~30 / ~55 (SRM) | — |

- **No official times for P-384, P-521 or Brainpool.** Datasheet and SRM only publish P-256. **[unconfirmed]**; expect several times slower for P-521.
- The DS and the [wiki Crypto-Performance page](https://github.com/Infineon/optiga-trust-m/wiki/Crypto-Performance) disagree on TLS PRF (50 vs 135 ms). The DS is newer.
- These are best-case, single-shot numbers. The security monitor (§6) slows sustained private-key use.

---

## 6. Data model

### 6.1 Object map (SRM Tables 68–70, 73, 79; endurance from SRM Fig. 32 / [wiki image](https://github.com/Infineon/Assets/blob/master/Pictures/trustm_keystore_dataobjects_v04.png))

| OID | What | Size | Default ACs (Read / Change / Exe) | Endurance (writes) |
|---|---|---|---|---|
| E0C0 | Global lifecycle state LcsG | 1 B (0x07 = op) | ALW / NEV | max 100 |
| E0C1 | Global security status (boot-phase flag) | 1 B | ALW / ALW (reset only) | no limit |
| **E0C2** | **Coprocessor UID** | 27 B | ALW / NEV | read-only |
| E0C3 | Sleep activation delay | 1 B, 20–255 ms | ALW / ALW | max 100 |
| E0C4 | Current limit | 1 B, 6–15 mA, default 6 | ALW / ALW | max 100 |
| **E0C5** | **Security event counter (SEC)** | 1 B, 0–255 | ALW / NEV | max 1.6 M |
| E0C6 | Max com buffer size | 2 B (0x0615 = 1557) | ALW / NEV | read-only |
| E0C9 | Security monitor config (V3) | 8 B, default `32 00 05 01 00 00 00 00` | ALW / LcsO<op | max 100 |
| **E0E0** | Device cert 1 (Infineon) | ≤ 1728 B | ALW / **NEV** | max 100 |
| E0E1–E0E3 | Device certs 2–4 | ≤ 1728 B each | ALW / LcsO<op | max 100 |
| E0E8–E0E9 | Trust anchors 1–2 | ≤ 1200 B each | ALW / LcsO<op | max 100 |
| E0EF | Trust anchor 8 (platform integrity / protected update) | ≤ 1200 B | ALW / LcsO<op | max 100 |
| **E0F0** | Device ECC private key 1 (factory) | P-256 | NEV / **NEV** / ALW | max 100 |
| E0F1–E0F3 | ECC private keys 2–4 (user) | any supported curve | NEV / LcsO<op / ALW | **max 100** |
| E0FC–E0FD | RSA private keys 1–2 | 1024/2048 | NEV / LcsO<op / ALW | max 100 |
| E100–E103 | Session contexts 1–4 (volatile; ephemeral keys, ECDH secrets, derived keys) | — | not addressable by Get/SetDataObject | no limit |
| E120–E123 | Monotonic counters 1–4 | 8 B (4 B value + 4 B threshold) | ALW / LcsO<op | max 600 k each |
| E140 | Platform binding secret (Shielded Connection) | 64 B | LcsO<op / LcsO<op ‖ Conf(E140) | max 200 k |
| E200 | AES key (V3) | 128/192/256 | NEV / NEV / ALW | max 100 |
| F1C0 | Application lifecycle LcsA | 1 B | ALW / ALW | max 100 |
| F1C1 | Application security status | 1 B | ALW / ALW | no limit |
| F1C2 | Last error code (clears on read) | 1 B | ALW / NEV | read-only |
| F1D0–F1DB | Arbitrary data "type 3", 12 objects | 140 B each | app-specific (factory: ALW / LcsO<op) | max 200 k, **shared across the group** |
| F1E0–F1E1 | Arbitrary data "type 2", 2 objects | 1500 B each | app-specific | max 100 |

Notes:
- "Up to 10 kB user memory" (DS) counts cert and trust-anchor slots. Plain arbitrary data is 2×1500 + 12×140 = **4680 B** ("4.5 kB", DS §2).
- **The 100-write limit on key slots matters.** Each GenKeyPair into E0F1–E0F3 is a key-object write. Infineon's recommended max for those slots is about 100 rewrites over the chip's life. For high-churn keys use session contexts (E100–E103, unlimited, lost on reset/power-off unless saved via hibernate).
- Global NVM budget: **2 million tearing-safe programming cycles across all objects**. Costs per action: data write = 1; ECC key write ≈ 1 (avg), RSA ≈ 5; protected update 3–6; SEC inc+dec = 2; one hibernate cycle = 5; use of a counter-linked object = +1 (SRM §5.1). VCC on/off cycling capped at 200,000 over life (SRM §4.6.4).
- Data retention: full lifetime up to ~100 writes per cell; after 20 k cycles retention drops to 2 years, after 40 k to ½ year (3 years with hardening) (SRM §5.1).
- Max command/response payload 1553 B (SRM §6.3.1).

### 6.2 Coprocessor UID (0xE0C2), 27 bytes (SRM Table 76)

CIM id (1), platform id (1), model id (1), ROM mask id (2), chip type (6), **batch number (6), wafer X (2), wafer Y (2)**, firmware id (4), **eSW build (2, BCD)**. Batch + wafer X/Y make it unique per die. Bytes 25–26 give the firmware build, e.g. `…25 64` = build 2564 (RN §1.3).

### 6.3 Access conditions (SRM §5.2, Table 66)

Access types: RD (read), CHA (change/write), EXE (use internally), MUPD (metadata update, V3).

| AC | Code | Meaning |
|---|---|---|
| ALW | 0x00 | always |
| NEV | 0xFF | never (internal use only) |
| LcsG / LcsA / LcsO (op, value) | 0x70 / 0xE0 / 0xE1 | global / app / object lifecycle compare (==, >, <) |
| Conf(OID) | 0x20 | data must travel encrypted over Shielded Connection keyed by OID (usually E140); or, for protected update, must be decrypted with the named update secret |
| Int(OID) | 0x21 | data must be MAC'd over Shielded Connection; or, for protected update, manifest must verify against named trust anchor (e.g. E0EF) |
| Auto(OID) | 0x23 | host must first prove knowledge of an AUTOREF secret via HMAC verify (V3). Up to 4 Auto states at once. Clear manually afterwards. |
| Luc(counter) | 0x40 | each use bumps a linked monotonic counter; refuses once threshold hit |
| SecStaG / SecStaA | 0x10 / 0x90 | boot-phase flag style gating (V3) |

Complex ACs: up to 7 terms ANDed per token, up to 3 tokens ORed. ALW/NEV not allowed inside complex ACs.

Data object types (tag 0xE8): BSTR, UPCTR, TA (trust anchor), DEVCERT, PRESSEC (pre-shared secret), PTFBIND (platform binding), UPDATSEC (protected update secret, V3), AUTOREF (V3) (SRM Table 67).

### 6.4 Lifecycle and locking (SRM §5.3, Table 74; §5.5)

- States: **creation (0x01) → initialization (0x03) → operational (0x07) → termination (0x0F)**. One-way only.
- Each object has its own LcsO. Most factory objects start in "creation" with Change = `LcsO < op`. That means **anyone on the I2C bus can rewrite them until you set LcsO = op**. Then they are frozen.
- Metadata (ACs, key usage, type) can only be changed while LcsO < op (V1 and V3). On V3 you can still change it later through a signed protected metadata update if the object has a 0xD8 "metadata update descriptor" and a 0xF0 reset type.
- Termination: protected metadata update can set LcsO = te; the object can then never be read or used (SRM §6.7.3).
- If LcsO tag is absent the object counts as op and its ACs are fixed.
- Global LcsG ships as op (0x07); app LcsA ships as creation (0x01) (DUMPS).
- Infineon's guidance: after installing keys, certs, trust anchors, set CHA = NEV (or protected-update only) and LcsO = op (SRM §6.5).

Metadata tags: 0xC0 LcsO, 0xC1 version (15 bit + invalid flag), 0xC4 max size, 0xC5 used size, 0xD0 change AC, 0xD1 read AC, 0xD3 execute AC, 0xD8 metadata-update descriptor, 0xE0 algorithm, 0xE1 key usage (Auth 0x01, Enc 0x02, Sign 0x10, KeyAgree 0x20), 0xE8 object type, 0xF0 reset type (flush with zeros or random) (SRM Tables 58, 71, 72).

### 6.5 Default factory state (DUMPS, standard V1/V3)

- E0F0: P-256, usage = authentication only, Change NEV, LcsO creation. **Cannot be regenerated or replaced on V1/V3 standard.**
- E0E0: Infineon cert, Change NEV.
- E0F1–E0F3, E0FC–E0FD: empty, Change `LcsO<op` (free for you).
- **E140 platform binding secret = 0x01 0x02 … 0x40**, readable while LcsO < op. The same bytes are hard-coded as the default in Infineon's host library PAL ([pal_os_datastore.c](https://github.com/Infineon/optiga-trust-m/blob/main/extras/pal/linux/pal_os_datastore.c)). **Out of the box the Shielded Connection key is public knowledge.** You must write your own secret and lock E140 for Shielded Connection to mean anything.
- E0C9 (V3) security monitor config is already LcsO = op, so tmax = 5 s and credit = 5 are **locked on standard parts**. The wiki says changing them needs a custom order configuration ([wiki Security-Monitor](https://github.com/Infineon/optiga-trust-m/wiki/Security-Monitor)).
- Express/MTR: almost everything is `Conf(E140) && Auto(F1D0)`, E140 and F1D0 are unique per chip and unreadable (NEV). The secrets come from CIRRENT Cloud ID (Express) or Infineon OSTS / Kudelski (MTR) (CFG Table 1; [overview README](https://github.com/Infineon/optiga-trust-m-overview)).

---

## 7. Features

### 7.1 Shielded Connection (I2CP §6, SRM §6.5.8, §6.6)

- Optional presentation layer in the IFX I2C protocol. Encrypts and authenticates command/response traffic between host and chip.
- Keyed by the 64-byte **platform binding secret** (E140) shared with the host.
- Protocol version 0: TLS PRF SHA-256 from the pre-shared secret → AES-128-CCM-8 keys + nonces; finished-message handshake; per-record sequence numbers (MSEQ/SSEQ). Version 1 (ECDHE + PSK) is defined but only bit 0 is described as the PSK path. **[unconfirmed]** whether Trust M implements PVER 1.
- Can be enforced per object with Conf(E140)/Int(E140) on read, change or execute.
- Infineon's own view: "The security level of the shielded connection is as high as a typical microcontroller/host side hardware security level" (SRM §6.5.8). It binds the chip to one host; it does not protect against a compromised host.
- No host nonce in the handshake (SRM §6.6 note). Recommended secret ≥ 32 bytes; rotate it at runtime over the shielded channel.
- Cost: about +5–10 ms per op (§5 table).

### 7.2 Protected update (SRM §6.7, §2.2.5–2.2.6)

- `SetObjectProtected` takes a **CBOR/COSE manifest** (COSE_Sign1, [RFC 8152](https://tools.ietf.org/html/rfc8152)) signed by a key whose cert sits in a trust anchor (usually E0EF). Manifest names: version, trust anchor OID, target OID, cipher suite, optional decryption secret OID and KDF data, offset/length.
- Payload is split into fragments; each fragment carries the SHA-256 of the next (hash chain), the first hash is covered by the signature.
- Confidentiality (V3): key + nonce derived from a UPDATSEC secret (≤ 64 B) via the KDF in the manifest; fragments encrypted with **AES-CCM-16-64-128**, 13-byte nonce = 11 derived bytes + 2-byte fragment number.
- Rollback protection: target object's version tag (0xC1) must increase. **[inferred]** from the version field and SRM text "version is used and updated by the protected update use case".
- V3 can update data, **ECC/RSA/AES private keys**, and metadata this way. V1: integrity-protected data only.
- Each decryption failure is a security event.
- Infineon ships a [protected update data set generator](https://github.com/Infineon/optiga-trust-m/tree/main/examples/tools) in the host repo.

### 7.3 Hibernate (SRM §4.4.1.2, DS §A.3)

- `CloseApplication(0x01)` saves the app context (security state, the 4 session contexts) to NVM and returns an 8-byte handle. Power off. `OpenApplication` with the handle restores it once.
- **Only works when SEC = 0**; otherwise "command out of sequence".
- Costs 5 NVM cycles per hibernate. VCC switching limited to 200,000 times over life.
- Hibernate current < 2.5 µA.

### 7.4 Security monitor and throttling (DS §7, SRM §4.6)

Events that count:
1. **Private key use** (any CalcSign, ECDH, RSA decrypt with a stored key; session-context keys don't count)
2. **Secret key use** (AES with E200, HMAC with a stored secret)
3. **Key derivation** from a persistent data object
4. **Decryption failure** in protected update
5. **Suspect system behavior** (internal inconsistency, e.g. fault-injection signs) → SEC jumps straight to 255

Policy (defaults):
- tmax = 5 s. Permitted profile: **one protected operation per tmax**.
- SECCREDIT (RAM, cleared on power-up, max 5): every quiet tmax adds a credit (if SEC = 0) or decrements SEC by 1. An event eats a credit first; with no credit it increments SEC (NVM).
- **No delay until SEC reaches 128.** From 128 to 255 the forced delay before each protected op grows linearly up to tmax (5 s) at SEC = 255.
- Full recovery from 255 takes ~1280 s (256 × 5 s); first undelayed op after ~640 s ([wiki](https://github.com/Infineon/optiga-trust-m/wiki/Security-Monitor)).
- **What this means [inferred]**: from cold, you get roughly 5 + 127 ≈ 132 back-to-back signatures at full speed, then a slowdown that converges to **~1 signature per 5 s** sustained. If you sign no more than once per 5 s, SEC stays at 0 and nothing is written to NVM.
- **Max signature count**: no hard cap in the docs. The practical limits are the 1.6 M endurance of the SEC object and the 2 M global NVM budget (each SEC inc+dec = 2 cycles). Bursty signing that keeps SEC moving could wear the chip in roughly 0.8–1 M throttled signatures **[inferred]**; spaced-out signing does not touch NVM.
- tmax = 0 disables the monitor, but on standard V3 parts the config object is locked (§6.5).

### 7.5 Other

- 4 monotonic up-counters (E120–E123), 600 k updates each, usable as general counters or linked usage limits (Luc) on keys/secrets (SRM Table 66). Infineon recommends capping shared-secret use at 2048 via a counter (SRM §6.5.6).
- Boot-phase flag (SecStaG/A, V3): give the bootloader access to an object, then clear the flag so the app can't (SRM Table 75).
- Session contexts: 4 volatile slots for ephemeral ECC keys, ECDH secrets, derived keys (SRM Table 69). Max 4 crypt sessions in parallel (RN §2.8).
- I2C: max packet 0x110, chaining, 3 retries, 10 ms transport timeout, guard time 50 µs (SRM Table 35).

---

## 8. Certifications and known attacks

| Item | Fact | Source |
|---|---|---|
| CC EAL6+ | **Hardware only.** Platform is IFX_CCI_00000Bh, certificate **BSI-DSZ-CC-0961**. Latest: **V7-2024**, EAL6+ (ALC_FLR.1), PP-0084, lab Deutsche Telekom Security, issued 2024-11-11, **valid until 2027-03-23**. | DS §1.5; [BSI 0961 page](https://www.bsi.bund.de/SharedDocs/Zertifikate_CC/CC/SmartCards_IC_Cryptolib/0961.html) |
| What CC does not cover | The Trust M firmware/product. There is no CC certificate naming "OPTIGA Trust M". DS words it as "based on Common Criteria EAL6+ (high) certified hardware". | DS front page; [Infineon forum](https://community.infineon.com/t5/OPTIGA-Trust/CC-Certificate-for-Optiga-Trust-M/td-p/442962) |
| PSA Certified Level 3 | **OPTIGA Trust M v3 SLS 32AIA010MK**, cert **0632793519409-10300**, issued 2024-07-27, lab SGS Brightsight, "PSA Certified Level 3 RoT Component", HW version V3.00.2440. Only the MK (V3 STR) part is listed; ML/Express/MTR are not separately listed. | [psacertified.org](https://products.psacertified.org/products/optiga-trust-m-v3-sls-32aia010mk) |
| Matter | MTR is used for Matter DAC (Kudelski PAA). Product page says "EU CRA Class II (targeted)". | [MTR page](https://www.infineon.com/part/OPTIGA-TRUST-M-MTR) |
| FIPS 140 | None found. **[unconfirmed]** | |
| Production site | Keys generated and certs injected at a CC-certified Infineon site (DS §2 note). | DS |

**EUCLEAK (Sept 2024, CVE-2024-45678)**: NinjaLab's non-constant-time modular inversion in Infineon's ECDSA library. The paper says the flaw "extends to the more recent Infineon Optiga Trust M" and includes Trust M EM traces. Needs physical access, EM probe, a few minutes of signing traces. NinjaLab did not publish a full Trust M key extraction. ([ninjalab.io/eucleak](https://ninjalab.io/eucleak/), [paper PDF](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf)).
- Infineon's fix: RN v3.02.2564 (2025-02-03): "Updated Security chip software with latest Asymmetric Crypto Library v02.09.002 … improved side channel resilience". **[inferred]** this is the EUCLEAK fix; Infineon does not name it.
- Trust M firmware is in ROM/locked; existing chips can't be patched. Check the eSW build in 0xE0C2 bytes 25–26: 2564 or later = patched.
- Trezor Safe 3/5 use Trust M; Trezor says seeds are not at risk because they use it for HMAC-based PIN stretching, not ECDSA ([Trezor forum](https://forum.trezor.io/t/questions-about-the-eucleak-on-the-optiga-trust-m/19001)).
- Practical takeaway: an E0F0 attestation key on a pre-2025 chip should be treated as extractable by a lab with physical access.

---

## 9. Factory provisioning and PKI

PKI chains (KC §4, CFG Table 1, [certificates folder](https://github.com/Infineon/optiga-trust-m-overview/tree/main/data/certificates), parsed with openssl):

| Variant | Device cert (E0E0) issuer | Intermediate key | Root | Root key / validity |
|---|---|---|---|---|
| V1 | Infineon OPTIGA(TM) **Trust M CA 101** | key type **[unconfirmed]**; cert not in Infineon's overview repo | Infineon OPTIGA(TM) ECC Root CA (CFG Table 1) | not in repo |
| V3 | Infineon OPTIGA(TM) **Trust M CA 300** | P-384, valid 2020-08-07 → 2050-08-07 | Infineon OPTIGA(TM) **ECC Root CA 2** | P-521, 2019-11-22 → 2054-11-22 |
| Express / MTR (E0E0, E0E1) | Infineon OPTIGA(TM) **Trust M CA 306** | P-384, 2022-05-10 → 2052-05-10 | ECC Root CA 2 | same |
| Express / MTR (E0E2, RSA) | Infineon OPTIGA(TM) **Trust M CA 309** | RSA-2048, 2022-05-16 → 2047-05-16 | Infineon OPTIGA(TM) **RSA Root CA 2** | RSA-4096, 2019 → 2054 |
| Engineering samples | Infineon OPTIGA(TM) Trust M **Test CA 000** (self-signed root, P-256) | — | — | 2018 → 2043 |

Device cert contents (from DUMPS, decoded):
- V1: `Subject: CN=Infineon IoT Node`, issuer CA 101, 20-year validity (e.g. 2019-06-18 → 2039-06-18), ECDSA-SHA256, P-256.
- V3: `Subject: CN=InfineonIoTNode`, issuer CA 300, ecdsa-with-SHA384, P-256, KeyUsage = digitalSignature (critical), CA:FALSE, policy OID 1.2.276.0.68.1.20.1, 20-year validity.
- Express/MTR: `Subject: C=DE, CN=<64 hex chars>` (a per-chip hash ID), issuer CA 306.
- Stored in E0E0 wrapped in the TLS "certificate chain" format (tag 0xC0, 3-byte lengths) on V1/V3, not as a bare DER cert (DUMPS; SRM Table 73).

Uniqueness:
- **Every chip has its own key pair and its own cert** (CFG: "Chip unique key. Corresponding public key certificate is stored in 0xE0E0"; DS §2 note). Cert serial is a random-looking 4-byte value; **subject is identical on every standard chip**, so the cert does not identify the device by name. Tie a chip to its cert by public key (or by the UID in E0C2, which is not in the cert).
- No revocation info (CRL/OCSP) in the device cert **[inferred]** from the decoded extensions.

Getting CA certs:
- CA 300, CA 306, CA 309, ECC Root CA 2, RSA Root CA 2, Test CA 000: [optiga-trust-m-overview/data/certificates](https://github.com/Infineon/optiga-trust-m-overview/tree/main/data/certificates).
- CA 101 (V1): **not** in the overview repo. Found in Infineon's [pred-main-xmc4700-kit](https://github.com/Infineon/pred-main-xmc4700-kit/tree/master/amazon-freertos/vendors/infineon/secure_elements/optiga_trust_m/certificates) (per `~/clawd/clawd-trust-m` README). CFG Table 1 names its root as "Infineon OPTIGA(TM) ECC Root CA".
- Infineon also hosts CA certs at pki.infineon.com. **[unconfirmed]**, not fetched.

---

## 10. Supply, price, lifecycle

| Item | Value | Source |
|---|---|---|
| Infineon list | $0.83 – $0.97 ea, "Active and preferred" | [Infineon part page](https://www.infineon.com/part/OPTIGA-TRUST-M-SLS32AIA) |
| DigiKey MK…XTMA2 reel | $0.756 @4k, $0.737 @8k, $0.728 @12k; marked discontinued at DigiKey | [DigiKey](https://www.digikey.com/en/products/detail/infineon-technologies/SLS32AIA010MKUSON10XTMA2/13536161) |
| DigiKey ML…XTMC1 (active) | €0.863 @4k, 4,000 in stock | [DigiKey FI](https://www.digikey.fi/en/products/detail/infineon-technologies/SLS32AIA010MLUSON10XTMC1/28890426) |
| Mouser MK…XTMA2 | $2.08 single → $1.01 reel | [Mouser](https://www.mouser.com/ProductDetail/Infineon-Technologies/SLS32AIA010MKUSON10XTMA2?qs=hd1VzrDQEGiOqvmuejHXzQ%3D%3D) |
| V1 MH (EOL) | Arrow 14,620 pcs, $1.16 cut tape / $0.87 reel; Rochester $1.11 → $0.69 | [Arrow](https://www.arrow.com/en/products/sls32aia010mhuson10xtma2/infineon-technologies-ag), Findchips |
| Lead time (MK…XTMA4) | 26 weeks (that OPN is now obsolete) | DigiKey |
| Mouser ML…XTMA2 | "End of Life", PDN 2025-12-5 | [Mouser EU](https://eu.mouser.com/ProductDetail/Infineon-Technologies/SLS32AIA010MLUSON10XTMA2?qs=hd1VzrDQEGihWeRT26uMng%3D%3D) |

Distributor stock and prices are snapshots from search results on 2026-10-08; they move.

Lifecycle summary:
- **V1 (MH/MS): EOL**, last-time-buy passed. Successor = V3 (MK/ML). Not drop-in for software that depends on V1 defaults (different CA, extra objects), but host library supports both.
- **V3 old OPNs (…XTMA2/…XTMA4/…XTMB4): NRND or obsolete.** Buy **SLS32AIA010MKUSON10XTMB2** (STR) or **SLS32AIA010MLUSON10XTMC1** (ETR).
- Express: buy **…MKUSON10XTMB1** or **…MLUSON10XTMB9**. MTR: **…MMUSON10XTMA5**.
- No announced successor product to Trust M; the family is still "preferred". Sibling lines are OPTIGA Authenticate, OPTIGA TPM, OPTIGA Connect. **[unconfirmed]** any 2027+ roadmap.
- Host library is maintained: v5.8.3 released 2026-09-14 (Mbed TLS 4.x migration in 5.8.0) ([CHANGELOG](https://github.com/Infineon/optiga-trust-m/blob/main/CHANGELOG.md)).

---

## 11. Open questions / not confirmed

- Which chip version Adafruit 4351 ships today (Austin's unit is V1 / CA 101).
- Timings for P-384, P-521, Brainpool; timings at the default 6 mA current limit.
- ECDSA nonce generation (random vs RFC 6979).
- CA 101 cert key type and where Infineon officially publishes CA 101 and the v1 ECC Root CA.
- Whether the 2026 OPNs all carry eSW 3.02.2564 (EUCLEAK fix).
- Whether Shielded Connection PVER 1 (ECDHE) is implemented on chip.
- Exact Infineon PDN covering V1 MH/MS.
