# TROPIC01 — what it is and what it'd take to put it on wedgie

Researched 2026-10-19. Sources are cloned under `src/` (shallow clones):
`src/tropic01` (datasheet, API, app notes), `src/libtropic` (C SDK, v4.2.0),
`src/devboards`, `src/pytropicsquare`, `src/libtropic-rs`, `src/libtropic-go`,
`src/ts-tvl` (Python chip model), plus others.

Short names used for citations:

- **DS** = `src/tropic01/doc/datasheet/ODD_TR01_datasheet_vA_11.pdf` (Rev A.11, Nov 2025, FW 2.x). Page numbers = printed page = PDF page.
- **API** = `src/tropic01/doc/api/ODU_TR01_user_api_v1_4_0.pdf`
- **CAT** = `src/tropic01/doc/catalog_list/OD_TR01_catalog_list_2v0.pdf` (PDF page numbers)
- **AN005** = `src/tropic01/doc/application_notes/ODN_TR01_app_005_first_pairing_key_1v3.pdf`
- **AN007** = `src/tropic01/doc/application_notes/ODN_TR01_app_007_fw_update_1v5.pdf`
- **SA** = `src/tropic01/doc/security_advisories/ODR_TR01_SA_2026012900_1v0.pdf`
- **PN** = `src/tropic01/doc/pages/part-numbers.md` and `parts/*.md`

## Bottom line

- **SPI only. No I2C.** So no STEMMA QT / Qwiic board can work by itself. It can't share the wedgie's Qwiic port with the Trust M.
- **No secp256k1.** P-256 ECDSA and Ed25519 EdDSA only. No public roadmap for k1. It can't sign Ethereum txs from an EOA directly.
- Every command (sign, read, store) runs inside an encrypted Noise session. The host needs X25519 + HKDF-SHA256 + AES-256-GCM.
- A **MicroPython library already exists** (`pytropicsquare`). Its handshake is pure Python. Expect roughly 8–20 s per handshake on an RP2040 (estimate, not measured). With a native X25519 `.mpy` it drops to well under 1 s.
- The cheapest way to wire it is the **Mini Board** (€9.50, 14×12 mm, castellated). Use 4 SPI wires plus 3V3/GND on spare Pico pins.
- For Ethereum, the realistic uses are: (a) PIN-gated secret storage (MAC-and-Destroy), so the Pico does the k1 signing, which is the Trezor Safe 7 pattern; or (b) P-256 signing for a smart account that verifies through the P256VERIFY precompile.

## 1. Hardware

### Host interface

| Item | Value | Source |
|---|---|---|
| Bus | 4-wire SPI slave only. Nothing in the datasheet mentions I2C. | DS p1 ("SPI communication interface"), p25 Table 6 |
| SPI mode | CPOL=0, CPHA=0 (mode 0). Byte-oriented, MSB first. | DS p25 §7.3.2 |
| Max clock | T_SCK min 37 ns → about 27 MHz. Examples use 1–5 MHz. | DS p59; `libtropic/examples/linux/spi/*/main.c` (5 MHz); `pytropicsquare/examples/esp32_quickstart.py` (1 MHz) |
| Pins | SPI_SDI (MOSI) pin 5, SPI_SDO (MISO) pin 6, SPI_SCK pin 7, SPI_CSN pin 8, GPO pin 4 (optional IRQ). VCC pins 1, 11, 24. GND pins 2, 12, 23. | DS p6 Table 1 |
| GPO / IRQ | Optional. Active-high "response ready". Set by the CFG_GPO object (FW ≥ 0.4.0). Not available in Start-up mode on TR01-B2/C2 parts. You can just poll the CHIP_STATUS READY bit instead. | DS p27; PN firmware table |
| Chip select | libtropic drives CS as a plain GPIO, not hardware NSS. The whole L2 response must be read in one CS-low transfer. | libtropic `docs/faq.md`; DS p27 |
| MISO | Goes Hi-Z when idle. Needs a pull resistor. The ref design uses 47k to VCC. | DS p26; Mini Board `TS1702` netlist (R1 on SPI_MISO) |

### Power

| Item | Value | Source |
|---|---|---|
| VCC | 3.0–3.6 V (typ 3.3). Ramp ≤ 1 ms. **3.3 V is fine.** | DS p57 §9.1 |
| IO levels | Same rail as VCC. VIH ≥ VDD−0.7, VIL ≤ 0.8 V. 3.3 V logic matches the Pico directly. | DS p60 |
| Abs max | 3.6 V on supply and IO. −25 to 85 °C. | DS p62 |
| Under/over-voltage alarm | About 2.33 V / 3.85 V | DS p61 |
| Current | Idle 1.95 mA typ, sleep 0.95 mA typ, start-up 7.9 mA. During commands about 9–12 mA typ, peaks 14–25 mA (MAC_And_Destroy 24.9 mA peak, ECDSA 19.5 mA peak). | DS p57 §9.2 |
| Pairing-key I-memory writes | Rated −20 to 85 °C. Older FW fails silently outside that range. | AN005 p9 |

### Package, pinout, passives

- QFN32, 4×4 mm, 0.4 mm pitch, exposed pad. KiCad footprint `QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm` (DS p6, p64–65).
- Reference schematic (DS p63 Fig. 24; Mini Board `src/devboards/TROPIC01_Mini_Board/TS1702/TS1702_schematic.pdf`):
  - 3× 100 nF decoupling caps, one on each VCC pin.
  - 47k pull-up on SDO/MISO.
  - Pins 3, 9, 10, 30, 31 tied to GND (PULLDN). Pin 22 tied to VCC (PULLUP). Pins 13–21 and 26–29 left unconnected (DNC). Thermal pad to GND.
- That's the entire BOM: chip + 3 caps + 1 resistor (Mini Board BOM `TS1702/bom/ts17-tropic01-mini.csv`).

### Boards you can buy (tropicsquare.com/order-devkit, prices ex VAT)

| Board | Price | Notes |
|---|---|---|
| Mini Board TS1701/TS1702 | €9.50 | 14×12 mm, castellated, J2 = MOSI/MISO/SCK/CS, J1 = GPO/VCC/GND. Ships TR01-C2P-T101. |
| MikroE Secure Tropic Click | €20 | mikroBUS. T101. |
| RPi Shield / Arduino Shield | €20 each | RPi shield ships T103. |
| USB DevKit (STM32 USB-SPI bridge) | €50 | For PC use. |
| Bare chip sample | €5 | |

Designs are CERN-OHL-P-2.0 (`src/devboards/README.md`). **No STEMMA QT / Qwiic board exists**, and one can't exist natively because the chip has no I2C.

### Part numbers (CAT PDF p3–5, PN)

Format `TR01-ABC-WPQX-V`:

- **A** = silicon revision. B = ABAB pre-production. C = ACAB production (bootloader 2.0.1).
- **B** = package (2 = QFN32).
- **C** = P production / S sample.
- **W** = vendor (firmware-signing) key. T = Tropic Square. X = TS dev key. E = external/customer.
- **P** = factory config. 0 = empty. 1 = sensors on. 2 = +MBIST. 3 = +FW logging off.
- **Q** = API compatibility. 0 = app FW 1.x. 1 = app FW 2.x.
- **X** = internal tracking.
- **V** = reel type.

| P/N | Ships with app/SPECT FW | Status |
|---|---|---|
| TR01-C2P-T301 | 1.0.0 / 1.0.0 | Recommended for new designs |
| TR01-C2P-T310 | 2.0.0 / 1.0.0 | In CAT + SA, no PN page yet |
| TR01-C2P-T202 | 0.5.0 / 0.3.1 | Deprecated |
| TR01-C2P-T103, T101 | 0.3.1 / 0.3.1 | Deprecated, but still what the devboards ship |
| TR01-B2S-T005 | 0.2.0 / 0.3.1 | Deprecated pre-production sample, sensors off |
| "TROPIC01-ES" | — | Early engineering samples. Different slot-0 pairing key. |

Pairing-key variant: production chips use the **prod0** slot-0 key. Engineering samples use **eng_sample** (libtropic `docs/reference/default_pairing_keys.md`). A custom slot-0 key, known only to you, needs a custom part number ordered from Tropic Square (AN005 p6–8).

## 2. Crypto features

| Feature | Detail | Source |
|---|---|---|
| Signing curves | **ECDSA P-256 (secp256r1)** and **EdDSA Ed25519**. Nothing else. | DS p1, p8, p47 §7.7; API p37 (CURVE: 0x01 P256, 0x02 Ed25519) |
| **secp256k1** | **Not supported.** It isn't in the datasheet, the API, the SPECT arithmetic list (P-256, Ed25519, Curve25519 only, DS p56), or any GitHub issue. No public roadmap. In Trezor Safe 7, keys are **not** stored on TROPIC01. It handles PIN, attestation and randomness. | DS p56; `gh search issues --owner tropicsquare secp256k1` → none; [Trezor](https://trezor.io/guides/trezor-devices/trezor-safe-7/what-is-the-tropic-01-chip) |
| ECDSA input | Host sends a 32-byte hash (any hash it likes). The chip returns (r, s). The nonce is deterministic: TMAC(w, h‖n‖z). Signing with libtropic ≥ 4.0 needs a pre-hashed 32 B input. | DS p49–50; libtropic CHANGELOG 4.0.0 |
| EdDSA input | Full message, 0–4096 B (FW ≥ 1.0.0). | DS p50; PN table |
| ECDH for the user | **None exposed.** X25519 is used only inside the handshake. | DS p47 |
| Key slots | 32 ECC slots. Keys are generated on chip or imported (ECC_Key_Store), masked and encrypted at rest. The private key can't be read back. | DS p21 Table 4, p47 |
| User data | 512 slots × **475 B** on FW ≥ 2.0.0 (444 B before). About 237 KiB total. Must erase before rewrite. ISAP-encrypted with a PUF-derived key. | DS p1, p21, p46; PN table |
| Monotonic counters | 16 × 32-bit, count down to 0 | DS p52 |
| PIN | MAC-and-Destroy (Keccak-based), 128 slots. Atomic try counting with nothing to glitch. Patent pending. | DS p14, p21, p52; `ODN_TR01_app_002_pin_verif_1v2.pdf` |
| TRNG | 2 TRNGs (one internal, one for the host). Up to 128 kbit/s. Random_Value_Get takes up to 255 B per call. | DS p1, p54; libtropic CHANGELOG 4.0.0 |
| Attestation | X.509 chain in I-memory: device cert (holds the chip's X25519 STPUB) → Tropic01-XXXX → Tropic01 CA → Tropic Square Root CA. Read with Get_Info_Req, no session needed. | DS p22, p51; `ODN_TR01_app_003_pki_1v3.pdf` |
| Access control | 4 pairing-key slots. Per-command, per-slot permission bits (UAP). Reversible (R-config) or permanent (I-config). Effective config = I AND R. | DS p42–45 |
| Firmware update | Two banks each for the RISC-V FW and the SPECT FW. EdDSA-signed by the vendor key. No downgrade allowed. Only works in Maintenance (Start-up) mode. Custom signing key is possible via special order. | DS p55–56; AN007 p4–9 |

## 3. Secure channel

Protocol: `Noise_KK1_25519_AESGCM_SHA256`. Full step list is in DS p40–41 Fig. 15.

Host does this:

1. Make an ephemeral X25519 key pair (EH).
2. Send Handshake_Req = EHPUB + PKEY_INDEX.
3. Get back ETPUB + an auth tag.
4. h = SHA-256 chain over protocol_name, SHiPUB, STPUB, EHPUB, index, ETPUB.
5. Three X25519 DHs: EHpriv·ETpub, SHipriv·ETpub, EHpriv·STpub.
6. Custom HKDF (HMAC-SHA256) → kAUTH, then kCMD and kRES.
7. Verify the AES-256-GCM tag over an empty plaintext with AAD = h.

After that, each L3 command is AES-256-GCM with a 32-bit counter nonce (DS p32, p35, p38).

**Host crypto needed:** X25519, SHA-256, HMAC-SHA256, AES-256 (to build GCM). Verifying the cert chain (P-256 / Ed25519 sigs) is optional. You can pin STPUB after the first trusted read.

**What the host must store:** the X25519 private key for its pairing slot (32 B), plus STPUB (or re-read it from the cert each boot). Nothing else persists. A session dies on Sleep, Alarm, a tag error, or nonce wrap. After that you redo the handshake (DS p17, p38).

**Factory pairing keys are public.** The slot-0 private key ships in libtropic source: `src/libtropic/src/libtropic_default_sh0_keys.c`, arrays `lt_sh0priv_prod0` / `lt_sh0priv_eng_sample`. It is also in `pytropicsquare/tropicsquare/constants/pairing_keys.py`. Tropic Square's own guidance (AN005 p6): use slot 0 only to write your own key into slot 1–3, then invalidate slot 0. Invalidation is permanent. If all slots are invalidated, the chip is bricked (DS p44).

### Host implementations

| Library | Language / target | Maturity | Link |
|---|---|---|---|
| libtropic | C, official. HALs: Linux spidev, STM32, ESP-IDF, Arduino, **RPi Pico (RP2040/RP2350, community HAL)**, POSIX USB/TCP. Crypto backends: mbedTLS v4, OpenSSL, wolfCrypt, trezor-crypto. | v4.2.0, active (Oct 2026). Pico HAL is community-maintained. Small bug: the IRQ pin field is named `int_gpio_pin` in the .h but `int_pin` in the .c, so `LT_USE_INT_PIN` won't compile. | github.com/tropicsquare/libtropic, `hal/rpi-pico/` |
| libtropic-arduino | Arduino/PlatformIO wrapper | Demo only, per the docs ("not suitable for production") | github.com/tropicsquare/libtropic-arduino |
| **pytropicsquare** | **Python: CPython + MicroPython.** Transports for machine.SPI, spidev, FTDI, UART devkit, TCP model. | v0.0.3/0.0.4-snapshot, 4 stars, last push 2026-03-27, one author (petrkr). Listed by Tropic Square as third-party. Still says 444 B slots. | github.com/petrkr/pytropicsquare |
| libtropic-rs | Rust, `embedded-hal` 1.0, no_std (aes-gcm, x25519-dalek, sha2) | 0.1.0, community, "not for production" | github.com/tropicsquare/libtropic-rs |
| libtropic-go | Pure Go | Community | github.com/tropicsquare/libtropic-go |
| ts-tvl | Python **chip model** (TCP server) for testing without hardware | Official | github.com/tropicsquare/ts-tvl |
| tropic01manager | GUI on pytropicsquare | Third-party | github.com/petrkr/tropic01manager |
| CircuitPython | **None found** | — | — |

### Can MicroPython on a Pico do it?

Yes. pytropicsquare's MicroPython port does the full L1/L2/L3 stack in pure Python (`tropicsquare/ports/micropython/`):

- X25519 is a bigint Montgomery ladder.
- AES-GCM uses `ucryptolib.aes` ECB plus a pure-Python GHASH.
- HKDF/HMAC is built on `hashlib.sha256`.

The library is about 1.5k lines of core code. It fits in RAM, and you can freeze it with mpy-cross.

Cost: one handshake = 4 X25519 scalar mults on the host. I couldn't measure on wedgie: the device was locked when I tried (`wedgie: locked. Press the green button…`), so nothing ran.

Proxy numbers:
- Pure-Python X25519 is about 1.4 s per exchange on an ESP32-S3 at 240 MHz ([micropython-reticulum](https://github.com/varna9000/micropython-reticulum)).
- An RP2040 at 125 MHz Cortex-M0+ should be slower. My estimate is 2–5 s per mult, so **about 8–20 s per handshake**.
- RP2350 (Cortex-M33, 150 MHz) should be a few times faster.

The fix is a native `.mpy` X25519 module, which runs in tens of ms (Monocypher armv6m build in micropython-reticulum; [pmvr/micropython-curve25519](https://github.com/pmvr/micropython-curve25519) gives 24 ms on STM32F4). A custom firmware with libtropic compiled in also works. One handshake per boot is enough if you keep the chip awake (Ping prevents sleep, DS p53).

Things to check or fix in pytropicsquare before trusting it:
- It makes the ephemeral key with `random.getrandbits()` (`ports/micropython/__init__.py`), which is not a CSPRNG. Use `os.urandom` or TROPIC01's own TRNG.
- It needs `ucryptolib`/`cryptolib` in the firmware build. Check that the wedgie's MicroPython build has it.
- The GCM tag compare isn't constant-time. This is minor on the host side.

## 4. Timing (DS p58, measured by Tropic Square)

| Operation | ms |
|---|---|
| Start-up after power-on | 225 |
| Get_Info_Req (cert chunk, chip ID) | 4.2 |
| Handshake_Req (chip side only) | 162.9 |
| ECDSA_Sign P-256 | 198.6 |
| EDDSA_Sign (100 B msg) | 95.7 |
| ECC_Key_Generate P-256 / Ed25519 | 79.3 / 43.8 |
| MAC_And_Destroy | 28.2 |
| R_Mem read / write / erase | 11.9 / 15.9 / 11.5 |
| Random_Value_Get, Ping, counters | about 10–14 |

Add SPI transfer and host crypto. On pure MicroPython the host handshake (above) dominates by far.

## 5. Openness / licensing

- Datasheet, user API, app notes, errata, security reports and the advisory are all public on GitHub. No NDA is needed to build with it (`src/tropic01/doc/`).
- Open: RTL (`tropic01-rtl`, "TROPIC-1.0" licence), RISC-V app FW (`ts-tr01-app`, BSD-3-Clause-Clear), SPECT ECC FW + compiler, internal SDK, libtropic (BSD-3-Clause-Clear, no patent grant).
- Closed: the bootloader ("legal issues with silicon IP providers", tropic01 README). Analog blocks (TRNG, PUF, flash/OTP, power) and layout are under supplier/fab NDAs (DS p12).
- Some referenced docs (Functional Spec, TMAC spec) are cited by the datasheet. I didn't confirm they're all public. The RTL repo has functional docs in `doc/`.
- Devboard hardware is CERN-OHL-P-2.0.

## 6. Gotchas, errata, firmware

- **Update firmware first.** Chips ship with old FW. Devboards carry T101/T103 with FW 0.3.1. The latest app FW is **2.2.0** (libtropic 4.2.0 `TROPIC01_fw_update_files/`). The tropic01 repo table stops at 2.1.0. Each FW version has its own datasheet/API version. Errata stay tied to the part number (PN, FAQ.md).
- Pick update files by **silicon revision / bootloader** (ABAB = boot 1.0.1, ACAB = boot 2.0.1). Downgrades are rejected (AN007 p9; libtropic `docs/faq.md`).
- **Maintenance mode:** the chip accepts FW updates only after `Startup_Req(MAINTENANCE_REBOOT)`. In that mode Handshake_Req returns UNKNOWN_REQ, which looks like "my handshake is broken". Reboot with `TR01_REBOOT`. An empty or failed FW bank also drops the chip into maintenance mode (DS p18–19, p55; libtropic FAQ).
- The security advisory recommends **disabling maintenance mode** after updating (CFG_STARTUP[MAINTENANCE_ENA]=0). Update both banks. libtropic ≥ 4.0 does this (SA p6; AN007 p14).
- **SA-2026012900** (Ledger Donjon, public 2026-06-03): a laser fault can skip FW signature checks on decapped chips. CVSS 5.7. Needs more than €30k of equipment and 3–4 weeks. Affects **all** current part numbers. ECC keys, user data and MAC-and-Destroy secrets are all at risk. Hardened silicon is in development (Trezor says late 2026). Details of a separate MAC-and-Destroy attack path are embargoed until H1 2027 (SA p3–6).
- Errata to know (PN `parts/TR01-C2P-T101.md`):
  - Noise nonce endianness
  - R_Mem limited to 444 B (fixed in FW 2.0)
  - Mutable_FW_Update GEN_ERR
  - Secondary FW boot failure
  - Startup_Req CRC corruption
  - Verify memory writes
  - Resend_Req may send the wrong chunk (fixed in 2.1.0)
  - **R-Config write can trigger permanent Alarm mode**
  - Voltage monitor off during immutable FW
  - RNGTEST_DIS not programmed on some parts
- **Alarm mode is sticky until power cycle.** HARDWARE_FAIL is permanent: the chip alarms on every boot after that (DS p18, p32).
- Bad wiring looks like chip errors. All-zero MISO reads as "busy". All-0xFF reads as "alarm". Wrong CS gives "L3 data len error". Use short wires and lower the clock if you see CRC errors (libtropic `docs/faq.md`).
- I-config bits are one-way (1→0). One wrong UAP write can permanently lock commands (DS p23, p42).
- The R-memory user data is flash rated for 100k cycles and 10-year retention (DS p61).

## 7. What it'd take on wedgie

**Wiring (alongside Trust M).** Leave the Trust M on Qwiic/I2C0 (GP4/GP5). The screen hat uses GP8-GP13, so SPI1 is taken. Use SPI0 on free pins:

| Mini Board | Pico pin |
|---|---|
| SCK | GP6 (SPI0 SCK) |
| MOSI | GP7 (SPI0 TX) |
| MISO | GP0 (SPI0 RX) |
| CS | GP1 (plain GPIO) |
| GPO (optional) | GP14 or poll instead |
| VCC / GND | 3V3 (pin 36) / GND |

All of these are on the wedgie's free list (`wedgie-dev/public/skill.md`).

**STEMMA QT form factor?** Only with a bridge. Options:
1. A tiny MCU on the board, acting as an I2C target and SPI master. The Noise session runs end-to-end between the Pico and TROPIC01, so the bridge only sees ciphertext and doesn't have to be trusted.
2. An NXP SC18IS602B I2C-to-SPI bridge. Untested. Its 200 B buffer is smaller than a max 256 B L2 frame, and the chip needs each response read in one CS transfer. Workable only if frames stay small.

Either way it's a custom board. Nothing off the shelf.

**Software path:**
1. Run libtropic on a PC or Pi first (USB DevKit or RPi shield). Read the chip ID, update FW to 2.2.0, disable maintenance mode.
2. On the Pico, use pytropicsquare. Swap in `os.urandom` and add a native X25519 `.mpy`.
3. Handshake with slot 0 once, write your own pairing pubkey to slot 1, invalidate slot 0.
4. Store your slot-1 private key on the Pico.

**Ethereum use:**
- **No k1 on chip.** Same pattern as Trezor: keep the k1 seed encrypted on the Pico (or in TROPIC01 user data). Gate the decryption key with MAC-and-Destroy PIN slots. Sign k1 on the Pico.
- Or use the P-256 key as a smart-account signer, verified on chain with the P256VERIFY precompile. That needs a low-s fix on the host.
- Ed25519 has no EVM precompile.
