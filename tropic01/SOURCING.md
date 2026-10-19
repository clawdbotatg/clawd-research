# TROPIC01 sourcing and a STEMMA QT-style board

Checked 2026-10-19. Prices are what the pages showed that day.

## Short answer

- **You can't buy the bare chip from a distributor.** Mouser, DigiKey and LCSC
  only list the MikroE Click board. Farnell blocked the check (403). The only
  place to get loose chips is Tropic Square's own order form: **"TROPIC01
  Standalone Sample", €5 each**. That order is reviewed by hand, shipping is
  quoted by email (about €35–55 outside the EU), and the form asks for a company name.
  No 10/100/1000 price is published. Ask welcome@tropicsquare.com for volume.
- **Current part number: `TR01-C2P-T301`** ("recommended for new designs",
  ships with app FW 1.0.0 / SPECT 1.0.0). T101, T103, T202 and B2S-T005 are
  deprecated. Tropic's site and a Ledger blog also mention `TR01-C2P-T310`
  (MAINTENANCE mode disabled), but it has no page in the GitHub repo yet.
- **No one sells a STEMMA QT / Qwiic / Grove TROPIC01 board.** The closest is
  the **LaskaKit TROPIC01A module** (€12.24, 78 in stock). It uses a **6-pin
  JST-SH "µŠup-SPI"** cable, not I2C.
- **The chip is SPI only** (CPOL=0, CPHA=0, up to ~27 MHz). STEMMA QT is
  I2C only. To use the same 4-pin cable you need a bridge on the board. The
  practical bridge is a small MCU (CH32V003F4U6 or STM32C011F4U6). The
  SC18IS602B can't do it: its buffer is too small. The SC18IS606 works on
  paper but is slow, large and out of stock.
- **Simplest path for a Pico:** keep the 25.4×17.8 mm Adafruit outline, but
  use a 6-pin JST-SH SPI connector like LaskaKit's. No bridge and no firmware.
  libtropic already has a Pico HAL.

## 1. Bare chip

| Source | Listing | Price | Stock / notes | Link |
|---|---|---|---|---|
| Tropic Square direct | TROPIC01 Standalone Sample | **€5** ex VAT | Order form, reviewed by hand. Shipping quoted later. No MOQ or tiers stated | [order-devkit](https://www.tropicsquare.com/order-devkit) |
| Mouser | Bare chip not listed | — | A "TROPIC01" search goes straight to MIKROE-6559 | [Mouser](https://www.mouser.com/c/?q=TROPIC01) |
| DigiKey | Bare chip not listed | — | Same: only MIKROE-6559 | [DigiKey](https://www.digikey.com/en/products/result?keywords=TROPIC01) |
| LCSC | Nothing | — | "0 results for TROPIC01" | [LCSC](https://www.lcsc.com/search?q=TROPIC01) |
| Farnell | Unknown | — | Page returned 403 to the browser | [Farnell](https://uk.farnell.com/search?st=TROPIC01) |
| Findchips (aggregator) | Nothing | — | No hits for TROPIC01 or TR01-C2P-T301 | [Findchips](https://www.findchips.com/search/TROPIC01) |
| JLCPCB parts lib | **C54337781** "TROPIC01" | "$0.0205" pre-order, min 441 | **Junk entry.** Says Infineon, stock 0, and the price is nonsense. Don't rely on it | [C54337781](https://jlcpcb.com/partdetail/C54337781) |

Tropic's distributor page lists only Laskakit, MIKROE, DigiKey, Mouser and TME,
and every link points to a devboard
([distributors](https://tropicsquare.com/distributors-resellers)).

**JLCPCB assembly:** TROPIC01 is not a basic or extended part, and Global
Sourcing has nothing to buy. The only route is **consignment**: buy chips from
Tropic, ship them to JLC, and they go into "My Parts Lib"
([consign terms](https://jlcpcb.com/help/article/consignment-part-terms-conditions),
[how-to](https://jlcpcb.com/help/article/how-to-use-my-own-parts-for-pcb-assembly-order)).
Points to watch:
- JLC says it **won't process "items on the ECCN list."** DigiKey lists the
  Click board as **ECCN 5A992C** (mass-market crypto). Ask JLC before shipping chips.
- Loose (non-reel) parts cost an extra handling fee. Send spares to cover attrition.
- Overseas consignment (customs-declared) launched in mid-2025
  ([news](https://jlcpcb.com/news/jlcpcb-launches-compliant-overseas-component-consignment-service)).
- Fallback: have JLC assemble everything except U1, then hand-solder the QFN32
  (0.4 mm pitch, exposed pad) with hot air. For small runs that is easier.

**Export:** Tropic's pages say nothing about restrictions. Expect EU dual-use
mass-market crypto (5A992-type). Shipping to the US should be fine.

## 2. Devboards

| Board | PCB rev | Chip PN (current) | Tropic price | Elsewhere | Link |
|---|---|---|---|---|---|
| USB DevKit (STM32U5) | TS1303 (TS1301/1302 old) | T103 | €50 | LaskaKit €41 incl VAT, 9 in stock | [Laskakit](https://www.laskakit.cz/en/tropicsquare-tropic01-devkit/) |
| Raspberry Pi Shield | TS1501 | T103 | €20 | LaskaKit €28.68 incl VAT (6 seen in an earlier listing; not in the TROPIC01 search on 10-19) | [Laskakit](https://www.laskakit.cz/en/tropic-square-ts1501-raspberry-pi-shield/) |
| Arduino Shield | TS1401 | T103 (mikroBUS variant) | €20 | LaskaKit €28.68, 6 in stock | [Laskakit brand page](https://www.laskakit.cz/en/tropic-square/) |
| Mini Board (castellated, 17×12 mm) | TS1702 (TS1701 old) | T101 | €9.50 | — | [devboards](https://github.com/tropicsquare/devboards/tree/main/TROPIC01_Mini_Board) |
| MikroE Secure Tropic Click | **MIKROE-6559** | T101 | €20 | $19.00 at Mouser (22 in stock), DigiKey 1471-MIKROE-6559-ND (64 in stock), TME $18.69 (2). MikroE's own store is out of stock. Arrow shows $8.46 (probably an error) | [MikroE](https://www.mikroe.com/secure-tropic-click), [Mouser](https://www.mouser.com/ProductDetail/Mikroe/MIKROE-6559?qs=jcD%2FCkGBYeN1ayOkQggurQ%3D%3D), [DigiKey](https://www.digikey.com/en/products/detail/mikroelektronika/MIKROE-6559/26394718) |
| **LaskaKit TROPIC01A module** (third party) | — | not stated | — | **€12.24 (€10.12 ex VAT), 78 in stock**, code LA161029. Connectors: 6-pin JST-SH µŠup-SPI + 8-pin header | [product](https://www.laskakit.cz/en/laskakit-tropic01a-bezpecnostni-modul/), [HW repo](https://github.com/LaskaKit/TROPIC01-module) |

Tropic's own devboards are open hardware (CERN-OHL-P-2.0). KiCad sources are in
`src/devboards/`. The Mini Board BOM is the minimum circuit: 3× 100 nF, 47k, and the chip.

Tropic order page and prices: [order-devkit](https://www.tropicsquare.com/order-devkit),
[DevZone](https://www.tropicsquare.com/documentation).

## 3. Anyone with STEMMA QT / Qwiic / Grove?

No. Checked web search, GitHub (40 repos matching "tropic01"), and LaskaKit.
Tindie was behind a Cloudflare check, but search results show nothing there.
Nothing on SparkFun, Adafruit, Pimoroni or Seeed either.
- **LaskaKit µŠup-SPI** is the only cable-connector board, and it is SPI.
  Pinout: black GND, red 3V3, blue SDO, yellow SCK, white SDI, green CS.
- Other hobby boards on GitHub: `riatlabs/cdc-badge` (ESP32-S3 conference
  badge with TROPIC01), `Caza20/libtropic-rpi-pico`, and
  `rddl-network/rddl-tropic01-esp32`.
- Trezor Safe 7 boards don't show up on hobby markets.

## 4. SPI chip on an I2C STEMMA QT bus

**Frame size decides it.** libtropic's max L1 transfer is
1 status + 1 STATUS + 1 LEN + 252 data + 2 CRC = **257 bytes**
(`TR01_L1_LEN_MAX`, `libtropic_common.h`). The datasheet says the host must
read a whole response frame **in one CS-low transfer**. libtropic does this by
reading 1 byte, then 2, then LEN+2, with CS held low. A bridge that does one
SPI transfer per I2C message has to clock out all 257 bytes at once. That
needs a small custom libtropic HAL: on the first read, run the full transfer,
cache it, and answer the next reads from the cache.

| Option | Package | Price (LCSC) | Fits 257 B? | Speed | Verdict |
|---|---|---|---|---|---|
| NXP **SC18IS602B** | TSSOP-16 | C2678036, **discontinued** | **No**: 200 B buffer | 1.8 Mbit/s SPI | Ruled out |
| NXP **SC18IS606** (SC18IS606PWJ) | TSSOP-16 (5×6.4 mm) | C5190384, $6.69/1, $4.78/100, **0 in stock** | Yes, 1024 B buffer | SPI 1.8 Mbit/s, I2C 400 kHz | Works but slow, big, pricey, out of stock |
| WCH **CH32V003F4U6** | QFN-20 3×3 | C5299908, $0.32/5, $0.18/2500, 4,445 in stock | Yes (2 KB RAM) | HW I2C target + HW SPI, 48 MHz | **Best fit.** Needs WCH-LinkE (1-wire SWIO pad) |
| WCH CH32V003J4M6 | SOP-8 | C5346354, $0.27 | Yes | HW SPI pins not bonded out on SOP-8; bit-bang only, shares the SWIO pin | Too tight |
| ST **STM32C011F4U6TR** | UFQFPN-20 3×3 | C5456188, $1.95/1, $1.10/1000, 505 in stock | Yes (6 KB RAM) | HW I2C target + SPI | Good. Plain SWD, better tooling |
| Microchip ATtiny1616-MNR | QFN-20 3×3 | listed at LCSC | Yes (2 KB RAM) | TWI target + SPI, 20 MHz | Works. UPDI programming |
| RP2040 | QFN-56 7×7 + flash + crystal | — | Yes | — | Too big for this board, overkill |

A bridge MCU only ever sees Secure Channel traffic. L3 is encrypted end to end
between the host and TROPIC01, so the MCU doesn't weaken security. A bad MCU
could still drop or replay frames, which is a denial-of-service risk.

**Other wiring:**
- **Use a 6-pin JST-SH (SM06B-SRSS-TB) for SPI.** LaskaKit already does this.
  Wire it to the Pico's SPI0 pins with a 6-wire cable. libtropic `hal/rpi-pico`
  works as-is. JST C160405 is $0.90; XYECONN C56123098 is $0.05.
- **STEMMA QT plus extra wires.** STEMMA QT carries only GND/V+/SDA/SCL, so
  SPI needs 2–3 more wires. Not a real option.
- **SPI-over-Qwiic precedent:** none. SparkFun's Qwiic and Adafruit's STEMMA QT
  are both I2C only.

**Connector:** STEMMA QT and Qwiic are the same 4-pin JST-SH 1.0 mm,
**SM04B-SRSS-TB**. Pinout: 1 GND (black), 2 V+ (red), 3 SDA (blue),
4 SCL (yellow). LCSC: **C160404** (genuine JST, $0.22, 44k in stock) or
**C51940130** (XYECONN clone, $0.04). Qwiic is 3.3 V only. STEMMA QT boards
should take 3–5 V, and TROPIC01 needs **3.0–3.6 V** (datasheet A.11 §9.1).
Add a small 3.3 V LDO if you want 5 V hosts to work. Peak current is about 15 mA.
I2C address: Trust M is 0x30. Pick something else for the bridge, for example
0x28–0x2F, which is also the SC18IS606 range.

## 5. Adafruit 4351 outline (from the Eagle file)

Source: [adafruit/Adafruit-Infineon-Trust-M-PCB](https://github.com/adafruit/Adafruit-Infineon-Trust-M-PCB),
`Adafruit Infineon Trust M.brd`. Product page: [adafruit.com/product/4351](https://www.adafruit.com/product/4351).
Price $4.95, out of stock on 10-19. Listed size 25.5×17.7×4.7 mm.

| Feature | Position (mm, origin bottom-left) |
|---|---|
| Board outline | **25.40 × 17.78** (1.0" × 0.7") |
| Mounting holes, 2.5 mm plated | (2.54, 2.54), (22.86, 2.54), (2.54, 15.24), (22.86, 15.24). Pitch 20.32 × 12.70 (0.8" × 0.5") |
| STEMMA QT left (CONN4, rot 270) | (2.54, 8.89) |
| STEMMA QT right (CONN3, rot 90) | (22.86, 8.89) |
| 5-pin 0.1" header (JP1) | centered (12.70, 2.54) |
| Chip (USON-10) | (12.70, 8.89) |

That leaves roughly 13 × 10 mm in the middle, between the connectors and
above the header row. TROPIC01 (4×4) plus a 3×3 QFN-20 MCU, an SOT-23 LDO and
0402 caps fit there on 2 layers. The KiCad footprint Tropic recommends is
`Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm`.

## Local sources used

- `src/tropic01/doc/pages/part-numbers.md` and the datasheet
  `src/tropic01/doc/datasheet/ODD_TR01_datasheet_vA_11.pdf`: SPI mode,
  TSCK 37 ns min, VCC 3.0–3.6 V, pinout.
- `src/libtropic/include/libtropic_common.h` and `src/lt_l1.c`: frame sizes and
  how CS is held during a read.
- `src/devboards/*/README.md` and the BOMs: board revisions and chip PNs.
