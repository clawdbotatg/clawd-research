# TROPIC01 on a wedgie

Question (2026-10-19): can we get Tropic Square's TROPIC01 on a STEMMA QT board the size of the
Adafruit Trust M (4351), so it wedges into the wedgie the same way? Maybe make our own.

Details: [CHIP.md](CHIP.md) (chip, crypto, SDKs, gotchas) · [SOURCING.md](SOURCING.md) (buying,
boards, bridge chips, Adafruit outline). Source repos are cloned (gitignored) in `src/`.

## Short answer

- **Yes, we can make one. Nobody sells one.** No STEMMA QT / Qwiic / Grove TROPIC01 board exists.
- **The chip is SPI only.** STEMMA QT is I2C. So a true Qwiic board needs a small bridge MCU.
- **It can't sign Ethereum txs (no secp256k1).** It signs P-256 and Ed25519 only, and nothing says
  k1 is coming. Uses for us: PIN-gated secret storage (the Trezor Safe 7 pattern: seed encrypted,
  chip unlocks it after a PIN, Pico signs), or P-256 smart-account signer via the P256VERIFY
  precompile — the same job the Trust M does today, but with real PIN slots and an open design.
- **Every command runs in an encrypted Noise session.** The host needs X25519 + AES-GCM. Pure
  MicroPython X25519 on an RP2040 is likely 8–20 s per handshake (estimate, not measured); a native
  `.mpy` module makes it tens of ms. That is the main software job.

## Two board options (both in the Adafruit 25.40 × 17.78 mm outline)

| | A. STEMMA QT + bridge | B. 6-pin SPI |
|---|---|---|
| Plugs in like Trust M | yes, 4 wires, shares the bus | no, 6 wires into the header |
| Extra parts | CH32V003F4U6 ($0.32, 3×3 mm, LCSC C5299908) or STM32C011F4U6 ($1.95, SWD) | none |
| Firmware | small I2C→SPI bridge + custom libtropic HAL | none; libtropic has a Pico HAL |
| Security | bridge sees only ciphertext | same |
| Effort | bigger | small |

Ruled out: NXP SC18IS602B (200-byte buffer < 257-byte frames, discontinued). SC18IS606 works
but is slow, TSSOP-16, $6.69, out of stock.

Option B wiring on the wedgie (all free pins): SCK GP6, MOSI GP7, MISO GP0, CS GP1, 3V3 pin 36,
GND. The chip needs 3.0–3.6 V, so a 5 V host would need a regulator on the board.

Chip circuit is tiny: TROPIC01 (QFN32 4×4 mm, 0.4 mm pitch) + 3× 100 nF + 47k pull-up on MISO
(Tropic's open TS1702 Mini Board, CERN-OHL-P — we can copy it).

## Buying

- **Bare chips: Tropic Square only**, €5 samples via tropicsquare.com/order-devkit (asks for a
  company; hand-reviewed; ~€35–55 shipping outside EU). Order **TR01-C2P-T301** (older numbers are
  deprecated). No distributor or LCSC listing.
- **JLCPCB doesn't stock it.** Consign our chips (ask JLC first: crypto parts can hit their ECCN
  rule) or have JLC build the rest and hand-solder the QFN.
- **To start today without a board:** MikroE Secure Tropic Click MIKROE-6559, $19, in stock at
  Mouser/DigiKey; or Tropic Mini Board €9.50. Wire either to the SPI pins above.

## Gotchas

- Update chip firmware first (latest 2.2.0, pick by silicon rev; no downgrades). Leave maintenance
  mode after, or handshakes fail.
- Factory pairing key (slot 0) is public on purpose: use it once to install our own, then
  invalidate slot 0.
- Some config writes are one-way or can trigger permanent alarm mode (erratum). Read CHIP.md §6
  before touching config.
- Ledger laser-fault attack (public 2026-06) bypasses FW signature checks on all current parts;
  needs a decapped chip, >€30k gear, weeks. Hardened silicon expected late 2026.

## Suggested path

1. Buy 2 Click boards + 10 bare T301 samples.
2. Wire a Click board to GP6/GP7/GP0/GP1 on a spare wedgie. Get pytropicsquare (MicroPython)
   doing a handshake; time it on RP2040 vs RP2350. Swap its session RNG to `os.urandom`.
3. If the handshake is too slow, build a native X25519 `.mpy`.
4. Then design board A in tscircuit (Adafruit outline, two STEMMA QT, CH32V003 bridge) and order
   from JLC with consigned chips.
