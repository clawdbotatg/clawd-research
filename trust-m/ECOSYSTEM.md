# OPTIGA Trust M: software and hardware ecosystem

Researched 2026-10-08. Context: our Pico + MicroPython driver (IFX I2C link layer,
OpenApplication / GetDataObject / CalcSign / GetRandom), P-256 keys used as Safe passkey
signers, and on-chain attestation of the factory certificate.

"Unconfirmed" = I could not check it against a primary source.

## TL;DR

- The official C host library is alive: **release-v5.8.3, 2026-09-17**, MIT, 142 stars. It has
  20 low-level commands. We use 4. The big gaps are GenKeyPair, SetDataObject (incl. metadata),
  VerifySign, CalcSSec (ECDH), DeriveKey, symmetric encrypt/decrypt + HMAC, protected update, and
  the Shielded Connection handshake.
- **No secp256k1. Ever.** Curves are NIST P-256/384/521 and Brainpool r1 256/384/512. P-256 + the
  RIP-7212 / EIP-7951 precompile is the right path. Nobody on GitHub signs Ethereum txs on a Trust M.
- **Factory cert chain differs by chip version.** V1 (CA 101) is all P-256 below the root. V3 /
  Express / MTR leaf certs are issued by **CA 300 / CA 306, which are P-384 keys** under a
  **P-521 root**. On-chain verify of a V3 leaf needs P-384 ECDSA in Solidity (no precompile).
  Our deployed contract pins CA 101, so it only works for V1 chips.
- **Security monitor throttling is real and not changeable on stock chips.** ~1 private-key op
  per 5 s is the sustained budget. Bursts are fine until the counter hits 128, then each op
  slows down, up to ~5 s per op. The config object (0xE0C9) is locked on retail parts.
- **No MicroPython driver exists besides ours.** One new CircuitPython driver (jimmckeeth,
  AGPL-3.0, Sept 2026). Adafruit has no official CircuitPython lib.
- Cheapest board: **Adafruit 4351, $4.95**, out of stock at Adafruit today (DigiKey link offered).

---

## 1. Official C host library: `Infineon/optiga-trust-m`

| Item | Value |
|---|---|
| Repo | https://github.com/Infineon/optiga-trust-m |
| License | MIT (REUSE-managed; per-file headers) |
| Stars | 142 |
| Latest release | **release-v5.8.3, 2026-09-17** (changelog entry 2026-09-14) |
| Recent cadence | 5.8.3 (09-14), 5.8.2 (09-04), 5.8.1 (08-12), 5.8.0 (07-17), 5.7.0 (05-22), 5.6.0 (03-05), 5.5.0 (02-19) |
| Crypto dep | Mbed TLS **4.x only** since 5.8.0 (TF-PSA-Crypto). 2.x/3.x on branch `feature/mbedtls-3.x` |
| API docs | https://infineon.github.io/optiga-trust-m/index.html |
| Spec PDFs | https://github.com/Infineon/optiga-trust-m-overview/tree/main/docs/pdf (Solution Reference Manual v3.70, Datasheet v3.70, IFX I2C Protocol v2.03, Keys & Certificates v3.10, Config Guide v2.2) |

Recent 5.8.x fixes are security hardening of the host side: CalcSign response length check,
signature encoding validation, random response length check, UART overflow fix. Worth copying
into our driver: **never trust a length field from the chip.**

### Structure

```
include/  optiga_crypt.h  optiga_util.h  cmd/  comms/  ifx_i2c/  pal/  common/
src/      crypt/  util/  cmd/  comms/ifx_i2c/ (physical, data-link, transport, presentation layers)
extras/pal/  linux  linux_uart  libusb  windows_uart  esp32_freertos  xmc4800  xmc4800_freertos
             zephyr  NEW_PAL_TEMPLATE  test_pal  + pal_crypt_{psa,openssl,wolfssl}.c
examples/ optiga/ (one file per API)  mbedtls_port/  utilities/authenticate_chip/  tools/protected_update_data_set/
config/   mbedtls_4.x_default_config.h  tf_psa_default_config.h
```

Layers: CRYPT / UTIL (async high-level API with callbacks) -> CMD (APDUs) -> COMMS (IFX I2C
stack + optional Shielded Connection) -> PAL (I2C, GPIO, timer, OS event, datastore).

### PAL ports

| Port | Where | Notes |
|---|---|---|
| Linux I2C | `extras/pal/linux` | `/dev/i2c-1`, libgpiod v1/v2 for reset/VDD pins. This is the Raspberry Pi port. |
| Linux UART | `extras/pal/linux_uart` | Via OPTIGA Trust Adapter (USB-UART bridge to a PSoC) |
| libusb | `extras/pal/libusb` | USB adapter |
| Windows UART | `extras/pal/windows_uart` | |
| ESP32 FreeRTOS | `extras/pal/esp32_freertos` | Pins in `pal_ifx_i2c_config.c` |
| XMC4800 (bare + FreeRTOS) | `extras/pal/xmc4800*` | |
| Zephyr | `extras/pal/zephyr` | Binds `DT_ALIAS(optiga_i2c)` |
| PSoC 6 | Not in this repo | Lives in ModusToolbox (`mtb-example-optiga-*`) |
| Raspberry Pi | = Linux PAL | No separate folder |

### Full API list (what our driver has vs. lacks)

**CMD layer** (`include/cmd/optiga_cmd.h`; command bytes from `src/cmd/optiga_cmd.c`, OR'd with
0x80 = "clear last error"):

| Command | Code | We have it? | What it's for |
|---|---|---|---|
| OpenApplication | 0x70 | yes | Start session; also restores hibernate context |
| CloseApplication | 0x71 | no | Hibernate (save context) |
| GetDataObject | 0x01 | yes | Read data / metadata (param 0x01 = metadata) |
| SetDataObject | 0x02 | **no** | Write data, **write metadata** (lock slots, set lifecycle) |
| SetObjectProtected | 0x03 | **no** | Protected (signed/encrypted) update of data, keys, metadata |
| GetRandom | 0x0C | yes | TRNG/DRNG; also pre-master secret |
| EncryptSym / DecryptSym | 0x14 / 0x15 | **no** | AES ECB/CBC/CBC-MAC/CMAC, **HMAC-SHA256/384/512** |
| EncryptAsym / DecryptAsym | 0x1E / 0x1F | no | RSA only |
| CalcHash | 0x30 | no | SHA-256 on chip (start/update/finalize) |
| CalcSign | 0x31 | yes | ECDSA / RSA sign of a host-supplied digest |
| VerifySign | 0x32 | **no** | ECDSA / RSA verify (pubkey from host or a cert OID) |
| CalcSSec | 0x33 | **no** | **ECDH** shared secret |
| DeriveKey | 0x34 | no | TLS-PRF, HKDF-SHA256/384/512 |
| GenKeyPair | 0x38 | **no** | **Generate ECC/RSA keypair in E0F1-E0F3 (or session)** |
| GenSymKey | 0x39 | no | Generate AES key in 0xE200 |

**CRYPT API** (`optiga_crypt.h`): `random`, `hash` + `hash_start/update/finalize`,
`ecc_generate_keypair`, `ecdsa_sign`, `ecdsa_verify`, `ecdh`, `tls_prf(_sha256/384/512)`,
`hkdf(_sha256/384/512)`, `hmac` + `hmac_start/update/finalize`, `hmac_verify`,
`generate_auth_code`, `clear_auto_state`, `rsa_generate_keypair`, `rsa_sign`, `rsa_verify`,
`rsa_encrypt_message`, `rsa_encrypt_session`, `rsa_decrypt_and_export`, `rsa_decrypt_and_store`,
`rsa_generate_pre_master_secret`, `symmetric_encrypt/decrypt` (+ `_ecb`, `_start/_continue/_final`),
`symmetric_generate_key`, `set_comms_params`, `create`, `destroy`.

**UTIL API** (`optiga_util.h`): `open_application`, `close_application`, `read_data`,
`read_metadata`, `write_data`, `write_metadata`, `update_count`,
`protected_update_start/continue/final`, `set_comms_params`, `create`, `destroy`.

**Not a command, but missing:** the **Shielded Connection** (presentation layer). It is a
handshake over the IFX I2C stack using the Platform Binding Secret (0xE140), TLS-PRF-SHA256 key
derivation, and AES-128-CCM on every frame. Trezor's description: "a shielded I2C session
(AES-128-CCM) between host MCU and secure element"
([Trezor](https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/secure-elements-in-trezor-safe-devices)).
Our plain-text link is fine for a demo; anyone on the bus can see digests and signatures (not keys).

**Priority for our use case:** GenKeyPair (fresh P-256 keys in E0F1-E0F3 per Safe signer) >
SetDataObject for metadata (lock those keys) > VerifySign (self-test) > ECDH/HMAC (pairing,
PIN gating) > Shielded Connection > protected update.

### Key slots and objects worth knowing (SRM v3.70, Table 68 ff.)

| OID | What | Default access |
|---|---|---|
| 0xE0E0 | Infineon device cert (wrapped in a TLV on some parts) | Read ALW |
| 0xE0F0 | Factory P-256 private key | EXE ALW, Change NEV, Read NEV |
| 0xE0F1-0xE0F3 | User ECC keys | Change while LcsO < op |
| 0xE0FC-0xE0FD | RSA keys | |
| 0xE0E1-E0E3, E0E8-E0E9, E0EF | More certs / trust anchors | |
| 0xE100-0xE103 | Session contexts (volatile keys) | |
| 0xE120-0xE123 | Monotonic counters (can gate a key's use count) | |
| 0xE140 | Platform Binding Secret (Shielded Connection) | |
| 0xE200 | AES key | |
| 0xE0C5 | Security Event Counter (read-only) | |
| 0xE0C9 | Security monitor config (V3 only; **locked on retail parts**) | Change LcsO < 7 |
| 0xF1D0-F1DB / 0xF1E0-F1E1 | App data objects | |

---

## 2. Linux tooling

| Project | What | Status |
|---|---|---|
| [Infineon/linux-optiga-trust-m](https://github.com/Infineon/linux-optiga-trust-m) | `trustm_*` CLI tools + OpenSSL 3 provider. Host lib is a git submodule. | MIT, **V2.2.0 on 2026-08-26** |
| [Infineon/optiga-trust-m-openssl](https://github.com/Infineon/optiga-trust-m-openssl) | Provider split out on its own | MIT, created 2025-08, pushed 2026-08 |
| [Infineon/pkcs11-optiga-trust-m](https://github.com/Infineon/pkcs11-optiga-trust-m) | PKCS#11 module; OpenSC, OpenSSL and AWS IoT examples | v2.25.0, 2025-01-27; license marked "Other" by GitHub (README says MIT) |
| [Infineon/optiga-trust-m-explorer](https://github.com/Infineon/optiga-trust-m-explorer) | Python GUI on the Pi | MIT, pushed 2026-03 |
| [Infineon/openwrt-optiga-trust-m](https://github.com/Infineon/openwrt-optiga-trust-m) | OpenWRT tools | stale (2022) |

CLI tools: `trustm_cert, chipinfo, data, ecc_keygen, ecc_sign, ecc_verify, errorcode, hash,
hkdf, hmac, hmac_verify_Auth, metadata, monotonic_counter, probe, protected_update(_aeskey,
_ecckey, _rsakey, _data), read_data, read_status, readmetadata_{data,private,status}, rng,
rsa_{dec,enc,keygen,sign,verify}, symmetric_{dec,enc,keygen}, update_with_PBS_Auto`.

The OpenSSL provider does `rand`, `req`, `pkey` keygen, `pkeyutl` sign, TLS client/server with an
on-chip key. Keys are referenced by label (`0xE0F1`) or by a "reference key" PEM file.

**How people run it on a Pi:** Pi 4, kernel >= 5.15, enable I2C in `raspi-config`, wire SCL/SDA/
3V3/GND (+ optional RST/VDD GPIOs via libgpiod), then `./trustm_installation_script.sh`. Tested
on Pi OS 6.6.31 aarch64 with OpenSSL 3.0.14. Infineon's own wiring uses the Shield2Go adapter or
a MikroE Pi 4 Click Shield.

**Linux gotcha:** the CLI examples run with Shielded Connection on by default, so **every command
bumps the Security Event Counter**. You must first run `scripts/misc/write_default_shared_secret`
to pair. Use `-X` to bypass, which only works if the lib's default protection level is
`OPTIGA_COMMS_NO_PROTECTION` (README "Secure communication bypass").

Open issues show the provider still has rough edges: `X509_sign()` with EC (#63), uninitialized
keys (#62), ECC hard-coded to SHA-256 (#53).

---

## 3. Other language bindings

| Language / platform | Project | Status | Notes |
|---|---|---|---|
| Python (CPython) | [optigatrust](https://pypi.org/project/optigatrust/) / [Infineon/python-optiga-trust](https://github.com/Infineon/python-optiga-trust) | **1.5.1, 2025-04-01**. MIT. Quiet since. | ctypes wrapper over prebuilt `.so/.dll` of the C lib. Linux I2C (incl. gpiod), UART, libusb; aarch64/armv7l/x86_64, Windows. Keygen, sign/verify, ECDH, RSA, AES, HMAC, metadata, CSR, protected update, chipinfo CLI. I2C bus hard-coded to `/dev/i2c-1` (issue #26). Can't run on MCUs. |
| MicroPython | **None public besides ours** ([clawdbotatg/clawd-trust-m](https://github.com/clawdbotatg/clawd-trust-m) `firmware/trustm.py`) | | Infineon's [micropython-psoc-edge](https://github.com/Infineon/micropython-psoc-edge) port exists; [tesaiot SDK](https://github.com/tesaiot/tesaiot-pse84-devkit-sdk) exposes OPTIGA (cert, ECDSA, RNG) from MicroPython on PSoC Edge E84 via C modules. Not pure Python, not RP2040. |
| CircuitPython | [jimmckeeth/trustm-matrix](https://github.com/jimmckeeth/trustm-matrix) | **AGPL-3.0**, pushed 2026-09-30, 0 stars | From-scratch `trustm.py` + `trustm_crypto.py`, CircuitPython 10.x, on Adafruit 4351. Demo uses RNG. **AGPL: read, don't copy.** No official Adafruit CircuitPython lib found. |
| Arduino | [Infineon/arduino-optiga-trust-m](https://github.com/Infineon/arduino-optiga-trust-m) | **Archived 2023**; last release v1.1.0 (2019) | Frozen. Adafruit's page now just points to the C lib. |
| Rust | [kern-werk/trustm-rs](https://github.com/kern-werk/trustm-rs) | MIT, pushed 2026-09-16, 0 stars | `trustm-sys` + safe `trustm` over the C lib, Linux only, blocking calls, no Shielded Connection, soft reset only. Not on crates.io (unconfirmed). |
| Rust (embedded) | Trezor + [EthereumPhone/PQ1](https://github.com/EthereumPhone/PQ1) | | PQ1 has its own Rust OPTIGA driver on STM32U585 (incl. Shielded Connection, PIN gate via 0xF1D0 + E120 counter). Big, but a good reference. |
| C (independent, lean) | [trezor-firmware core/embed/sec/optiga](https://github.com/trezor/trezor-firmware/tree/main/core/embed/sec/optiga) | Active | `optiga_transport.c` + `optiga_commands.c`: a from-scratch IFX I2C + command implementation, not Infineon's lib. **Best reference for our driver.** |
| Zephyr | `extras/pal/zephyr` + [Infineon/optiga-trust-m-zephyr](https://github.com/Infineon/optiga-trust-m-zephyr) (2024) | Out of tree | Not in Zephyr mainline or `hal_infineon` (unconfirmed absence). Old [zephyrproject-rtos/optiga-trust](https://github.com/zephyrproject-rtos/optiga-trust) is dead (2020). |
| ESP-IDF | [Infineon/azure-esp32-optiga-trust](https://github.com/Infineon/azure-esp32-optiga-trust) `components/optiga` | Pushed 2026-03 | ESP-IDF 5.1.4. Copy the component. No ESP Component Registry entry found. |
| mbedTLS | `examples/mbedtls_port` (ECDSA/ECDH/RNG/RSA ALT) | In main repo | Old [mbedtls-optiga-trust-m](https://github.com/Infineon/mbedtls-optiga-trust-m) archived 2022. |
| Cross-vendor | [essential-contributions/secure-elements](https://github.com/essential-contributions/secure-elements) | 2026-04 | C drivers on a Pi for ST/Microchip/NXP/Infineon + Rust cert verification + `contracts/p256.sol` for RIP-7212. Very close to our project. |

---

## 4. Cloud / IoT integrations and variants

All variants are the same silicon and package; the host code works on all of them
([Config Guide v2.2](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/pdf/OPTIGA_Trust_M_ConfigGuide_v2.2.pdf)).

| Variant | Part | Factory cert issuer | Notes |
|---|---|---|---|
| V1 | SLS32AIA010MH / MS | **Infineon OPTIGA(TM) Trust M CA 101** -> Infineon Root CA | P-256 throughout below root. No 0xE0C9 config. |
| V3 | SLS32AIA010ML / MK | **CA 300 (P-384)** -> ECC Root CA 2 (P-521) | Adds P-521, Brainpool, AES, HMAC, HKDF, SEC config |
| Express | V3-based | CA 306 -> Root CA 2; extra certs in E0E1 and RSA cert (CA 309) in E0E2 | Certs pulled via **CIRRENT Cloud ID** for AWS/Azure. No EOL notice found, but no recent news either. |
| MTR (Matter) | SLS32AIA010MM | Same as Express + late-stage Matter DAC | Claim the reel barcode on **Kudelski keySTREAM**, which issues DAC/PAI under Kudelski's PAA, then inject at the factory ([Infineon MTR](https://www.infineon.com/part/OPTIGA-TRUST-M-MTR), [community blog](https://community.infineon.com/t5/Blogs/What-is-OPTIGA-Trust-M-MTR-and-Why-does-it-Matter/ba-p/810828)) |

- **AWS IoT:** Trust M qualified for FreeRTOS + AWS IoT Core Multi-Account Registration in 2020
  ([AWS](https://aws.amazon.com/about-aws/whats-new/2020/06/infineons-optiga-trust-m-now-qualified-for-use-with-freertos-available-for-use-with-iot-core-multi-account-registration)).
  The FreeRTOS fork [Infineon/amazon-freertos](https://github.com/Infineon/amazon-freertos) is
  archived (2023). Current path: [mtb-example-optiga-mqtt-client](https://github.com/Infineon/mtb-example-optiga-mqtt-client)
  on PSoC 6, or the PKCS#11 module on Linux.
- **Azure:** [azure-esp32-optiga-trust](https://github.com/Infineon/azure-esp32-optiga-trust)
  (ESP32/ESP32-C3, X.509 to IoT Hub). Note: must disable `MBEDTLS_RSA_ALT` because Azure's chain has
  RSA-4096 and the chip tops out at 2048.
- **Matter:** [connectedhomeip lock-app with Trust M as HSM](https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/infineon/psoc6#building-with-optiga-trust-m-as-hsm),
  [getstarted Matter guide](https://github.com/Infineon/getstarted-optiga-trust-m/blob/main/psoc62_cy8ckit_mikrobus/matter/README.md).
  Dev MTR shields ship with Matter *development* credentials.
- **Other PKI:** CommScope PKIWorks provisioning demo (2025) ([pki-center](https://www.pki-center.com/newsblogs/2025/Infineon-Optiga-Trust-M-Technical-Notes)).

---

## 5. Boards you can buy

Prices seen 2026-10-08 unless noted. Stock moves fast; check before ordering.

| Board | Chip | Interface | Price | Stock | Source |
|---|---|---|---|---|---|
| **Adafruit 4351** Trust M breakout | SLS32AIA (version not stated; ours is V1 / CA 101) | STEMMA QT/Qwiic + 0.1" header incl. RST | **$4.95** (10+: $4.46, 100+: $3.96), 1 per order | **Out of stock at Adafruit**; "Buy on DigiKey" offered | [adafruit.com/product/4351](https://www.adafruit.com/product/4351) |
| Same, resellers | | | Pi Hut ~£4.80, RS US $4.95, Jameco $6.55 (pairs), eBay ~$12 | varies | [Pi Hut](https://thepihut.com/products/adafruit-infineon-trust-m-breakout-board-stemma-qt-qwiic-ada4351), [RS](https://us.rs-online.com/product/adafruit-industries/4351/72044460/), [Jameco](https://www.jameco.com/z/4351-Adafruit-Industries-Adafruit-Infineon-Trust-M-Breakout-Board-Stemma-QT-Qwiic_2518263.html) |
| MikroE **Trust M Click** (MIKROE-4236) | SLS32AIA010 "Trust M1" (V1) | mikroBUS | RS UK £7.00 | RS showed out of stock | [RS](https://uk.rs-online.com/web/p/encryption-authentication-development-tools/2162652) |
| SparkFun | None of their own. Resold Trust M Click (DEV-18915) and IoT SDK (DEV-19216), **both retired** | | | | [SparkFun](https://www.sparkfun.com/mikroe-trust-m-click-dev-18915.html) |
| MikroE "Secure 2 Click" | **Not Trust M** (Microchip ATAES132A) | | $11 | | [mikroe](https://www.mikroe.com/secure-2-click) |
| M5Stack | **No Trust M product found** | | | | |
| Infineon **OPTIGA Trust M Shield** V3 (TRUSTMV3SHIELDTOBO1) | V3 | mikroBUS | DigiKey AU A$38.69; Newark CA $46.97 | DigiKey AU 0 in stock, 26-wk lead | [DigiKey AU](https://www.digikey.com.au/en/products/detail/infineon-technologies/TRUSTMV3SHIELDTOBO1/25572552) |
| Infineon **Trust M MTR Shield** (TRUSTMMTRSHIELDTOBO1) | MTR | mikroBUS | DigiKey US ~$41.49 | unconfirmed | [DigiKey](https://www.digikey.com/en/product-highlight/i/infineon/optiga-trust-m-mtr-shield) |
| Infineon **S2GO Security OPTIGA M** (Shield2Go) | V1 | Shield2Go | not found | unconfirmed | [Mouser](https://www.mouser.in/new/infineon/infineon-optiga-m-shield2go-board/) |
| **OPTIGA Trust M IoT Security Dev Kit** (TRUSTMIOTSDKTOBO1) | Trust M + PSoC 62 + CYW43012 Wi-Fi/BT, Feather headers | built in | ~$35.60-36.95 | SparkFun retired; DigiKey had stock (old snapshot) | [SparkFun](https://www.sparkfun.com/infineon-technologies-optigatm-trust-m-iot-security-development-kit.html) |
| OPTIGA Trust Adapter (USB-UART) | | | DigiKey ~$53.51 | | |
| Built in: EZ-USB FX2G3 kit | Trust M on board | | | | [mtb-example-fx2g3-optiga-trust-m](https://github.com/Infineon/mtb-example-fx2g3-optiga-trust-m) |
| Built in: wallets | Trezor Safe 3 / 5 / 7 (V3), BitBox02 Nova (per third-party blog) | | | | [Trezor](https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/secure-elements-in-trezor-safe-devices), [piprime](https://blog.piprime.fr/en/state-of-secure-elements-in-hardware-wallets/) |
| Open hardware | [mimok/TrustM](https://github.com/mimok/TrustM) (Pi breakout), [NaisuXu/OPTIGA_Trust_M_Module](https://github.com/NaisuXu/OPTIGA_Trust_M_Module) | | | | |

**Adafruit 4351 schematic** ([PCB repo](https://github.com/adafruit/Adafruit-Infineon-Trust-M-PCB)):
nets are only VCC, GND, SDA, SCL, RESET; four 10k resistors (I2C pullups + RST pullup); 0.1 uF +
10 uF caps; a green power LED. **No regulator and no level shifter**, so feed it 3.3 V only (chip
range 1.62-3.63 V per datasheet). My read of the netlist; not checked against a photo.

---

## 6. Crypto / web3 usage

**secp256k1: not supported, no workaround on chip.** Datasheet: "ECC: NIST curves up to P-521,
Brainpool r1 curve up to 512." I found no project signing Ethereum or Bitcoin txs on a Trust M.

How wallets actually use it:

| Project | How it uses Trust M |
|---|---|
| [Trezor Safe 3/5/7](https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/secure-elements-in-trezor-safe-devices) | PIN-gated secret storage, genuineness check (chip signs a challenge), entropy. k1 signing stays on the MCU. Trezor provisions **its own** device certs (not the Infineon chain). Chosen because no NDA. |
| [EthereumPhone/PQ1](https://github.com/EthereumPhone/PQ1) | STM32U585 + Trust M V3 + NXP SE050. BIP-39 entropy XOR-split across both SEs; PIN attempts counted in E120 monotonic counter; signing is SPHINCS+ on the MCU. |
| [clawdbotatg/clawd-trust-m](https://github.com/clawdbotatg/clawd-trust-m) / [austintgriffith/picowallet](https://github.com/austintgriffith/picowallet) | Ours. Verifies a factory-key P-256 signature on chain against pinned CA 101 key via RIP-7212/EIP-7951. |
| [essential-contributions/secure-elements](https://github.com/essential-contributions/secure-elements) | Cross-vendor attestation verifier in Rust + `p256.sol` (RIP-7212). Pins "Infineon OPTIGA(TM) Trust M CA 300" with a **96-byte (P-384) public key**. |
| [zknot-io/verifyknot-site](https://github.com/zknot-io/verifyknot-site) | Product authenticity site that references the Trust M CA (details not checked). |

**k1 workarounds people use:** (1) keep the k1 seed on the MCU, encrypted with a key that only
the SE releases after a PIN check (Trezor, PQ1 pattern); (2) use P-256 keys natively with the
P-256 precompile and a smart account (our pattern, also Safe passkey signers); (3) pick a
different chip. Infineon's Blockchain Security 2Go / SECORA Blockchain do k1 (from memory,
unconfirmed here).

**WebAuthn / passkeys:** no Trust M FIDO2 authenticator project found. The chip covers ES256
signing only. A security key would need CTAP2 on the MCU, user presence, and key wrapping
(only 3 user ECC slots + session keys).

### On-chain cert chain verification: what to watch

| Chip | Chain | On-chain cost |
|---|---|---|
| V1 (Adafruit 4351 seen so far) | leaf P-256 <- **CA 101 (P-256, signed by root with ecdsa-with-SHA384)** <- Infineon OPTIGA(TM) ECC Root CA | Leaf check = one P-256 verify with the precompile. Pin CA 101. Verifying CA 101 against the root is a separate step (root key type not checked). |
| V3 / Express / MTR | leaf P-256 <- **CA 300 / 306 (P-384)** <- **ECC Root CA 2 (P-521)** | Leaf check needs **P-384 ECDSA in Solidity**. No precompile. Expensive. Off-chain or ZK verify, or a trusted registry, is more realistic. |
| Test / engineering samples | leaf <- Infineon OPTIGA(TM) Trust M Test CA 000 (P-256, self-signed) | Never trust. |

Sources: Keys & Certificates v3.10 PDF; Config Guide v2.2; CA 101 and Test CA 000 decoded from
`examples/utilities/authenticate_chip/example_authenticate_chip.c` in the host lib.

**Reading 0xE0E0:** some parts return the cert wrapped in Infineon TLV (`0xC0` tag, length,
cert-chain length...). Skip it (KBA235163 says ~9 bytes) until you hit `0x30 0x82`. Issue
[#140](https://github.com/Infineon/optiga-trust-m/issues/140) (Feb 2026, still open) reports V3
"Software Version 1" parts (`SLS32AIA010MLUSON10XTMB4`) where the 0xE0F0 signature does not
verify against the 0xE0E0 cert. If we ever buy V3 parts, test this first.

---

## 7. Practical gotchas

| Gotcha | Detail | Source |
|---|---|---|
| Address 0x30, 7-bit | Default 0x30. People send it unshifted and get NACKs forever. Writing reg 0x83 with bit 15 set makes a new address **persistent**. Don't. | Datasheet; [#39](https://github.com/Infineon/optiga-trust-m/issues/39) |
| NACK when busy or asleep | Chip NACKs its own address while busy or idle/asleep. Retry for up to **100 ms**. Not a fault. | Datasheet Annex; #39 |
| Guard time / polling | Host lib: 50 us guard time between transactions, poll every 1 ms up to 200 tries, data poll 5 ms, 10 ms transaction timeout. | `include/ifx_i2c/ifx_i2c_config.h` |
| Clock stretching | Optional; I2C_STATE (reg 0x82) bit 24 says whether it's on. RP2040 hardware I2C handles stretching. A bit-banged/soft I2C with a short timeout may not. | IFX I2C Protocol v2.03 |
| Bus speed | Default 400 kHz; can negotiate up to 1 MHz (FM+) via reg 0x84. | Datasheet |
| Startup | Wait >= 15 ms after power-on or RST rising edge (20 ms if NVM write was pending). RST low 10 us min, 2.5 ms max. | Datasheet 5.1.4 |
| Reset pin | Weak internal pull-up. The host lib's CloseApplication pulls HW reset low if `OPTIGA_COMMS_DEFAULT_RESET_TYPE = 0`, which **freezes the SEC countdown**. Soft reset (reg 0x88) avoids GPIOs. | [#68](https://github.com/Infineon/optiga-trust-m/issues/68), [#95](https://github.com/Infineon/optiga-trust-m/issues/95) |
| Security monitor throttling | Private-key use, secret-key use, persistent DeriveKey, failed protected update = 1 event each. Budget: 1 per tmax (5 s). Up to 5 credits saved while idle. SEC counts up; **delay starts at SEC = 128 and reaches tmax (~5 s/op) at 255**. SEC drops 1 per 5 s idle. Users see sign time climb from ~75 ms to ~5 s at 1 sign/s. | SRM v3.70 4.6; [#93](https://github.com/Infineon/optiga-trust-m/issues/93), [#91](https://github.com/Infineon/optiga-trust-m/issues/91), [#136](https://github.com/Infineon/optiga-trust-m/issues/136) |
| Can't relax it on retail chips | 0xE0C9 (tmax, credits) is LcsO = op on market parts. Only custom-provisioned orders. V1 has no 0xE0C9 at all. | #91 |
| Power-cycling to "reset" SEC | Don't. SEC lives in NVM. Infineon: wait until SEC = 0 before cutting VCC; VCC on/off is limited to **200,000 times** over life. | SRM 4.6.4 |
| Hibernate | CloseApplication with hibernate only works when **SEC = 0**. Each hibernate = 5 tearing-safe NVM cycles. | SRM |
| Shielded Connection costs SEC | Each shielded command is a security event; Linux tools enable it by default. | linux-optiga-trust-m README |
| Lock-down mistakes | Setting LcsO = operational is **one-way**. Change AC = NEV is permanent once LcsO = op. V3 can undo via protected update only if you configured that before locking. If you overwrite 0xE0E0/0xE0F0 you **can never get the Infineon identity back**. | [#58](https://github.com/Infineon/optiga-trust-m/issues/58), [#75](https://github.com/Infineon/optiga-trust-m/issues/75) |
| Cert writes not atomic | Large cert writes can be half-written if power drops. | SRM Table 68 note |
| NVM endurance | Retention falls to ~2 years after 20k writes, ~0.5 year after 40k writes to the same object. Don't use data objects as counters in a hot loop. | SRM 5.1 |
| Signature format | CalcSign returns two bare DER INTEGERs (no SEQUENCE header). Older lib versions produced bad padding for P-521 (#106, fixed 5.1.0). Normalize r,s yourself and enforce low-s for Safe/WebAuthn verifiers if needed. | [#106](https://github.com/Infineon/optiga-trust-m/issues/106), trustm-rs README |
| ecdsa_verify with cert OID | Only works if the object holds a bare DER cert starting `0x30`. Infineon's TLV-wrapped 0xE0E0 fails; extract the pubkey on the host. | [#127](https://github.com/Infineon/optiga-trust-m/issues/127) |
| Linux perf regression | 5.6.0 Linux PAL was slow ([#143](https://github.com/Infineon/optiga-trust-m/issues/143)); 5.7.0 reworked `pal_os_event`. | changelog |

Rough timings (datasheet, 400 kHz, 25 C): P-256 sign ~60-65 ms, verify ~85 ms, ECDH ~60 ms,
P-256 keygen ~75 ms, Shielded Connection adds ~5 ms per op.

---

## Sources

- Host lib: https://github.com/Infineon/optiga-trust-m (CHANGELOG, `include/`, `src/cmd/optiga_cmd.c`, `extras/pal/`)
- Specs: https://github.com/Infineon/optiga-trust-m-overview/tree/main/docs/pdf
- Linux tools: https://github.com/Infineon/linux-optiga-trust-m
- OpenSSL provider: https://github.com/Infineon/optiga-trust-m-openssl
- PKCS#11: https://github.com/Infineon/pkcs11-optiga-trust-m
- Python: https://github.com/Infineon/python-optiga-trust , https://pypi.org/project/optigatrust/
- CircuitPython: https://github.com/jimmckeeth/trustm-matrix
- Rust: https://github.com/kern-werk/trustm-rs
- Arduino (archived): https://github.com/Infineon/arduino-optiga-trust-m
- Zephyr: https://github.com/Infineon/optiga-trust-m-zephyr , https://github.com/zephyrproject-rtos/optiga-trust
- ESP32/Azure: https://github.com/Infineon/azure-esp32-optiga-trust
- AWS: https://aws.amazon.com/about-aws/whats-new/2020/06/infineons-optiga-trust-m-now-qualified-for-use-with-freertos-available-for-use-with-iot-core-multi-account-registration , https://github.com/Infineon/mtb-example-optiga-mqtt-client
- MTR / Express: https://www.infineon.com/part/OPTIGA-TRUST-M-MTR , https://www.infineon.com/part/OPTIGA-TRUST-M-EXPRESS , https://community.infineon.com/t5/Blogs/What-is-OPTIGA-Trust-M-MTR-and-Why-does-it-Matter/ba-p/810828
- Trezor: https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/secure-elements-in-trezor-safe-devices , https://github.com/trezor/trezor-firmware/tree/main/core/embed/sec/optiga
- PQ1: https://github.com/EthereumPhone/PQ1
- Cross-vendor verifier: https://github.com/essential-contributions/secure-elements
- Adafruit: https://www.adafruit.com/product/4351 , https://github.com/adafruit/Adafruit-Infineon-Trust-M-PCB
- MikroE / SparkFun / DigiKey links inline in section 5
- Issues cited: https://github.com/Infineon/optiga-trust-m/issues (#39, #58, #68, #75, #91, #93, #95, #106, #127, #136, #140, #143)
- Infineon community thread on the 5 s limit (403 to fetch, cited from #136): https://community.infineon.com/t5/OPTIGA-Trust/Optiga-Trust-5-signatures-s-limit/td-p/1048542
