# CELL — z0r0z's pulse/blood hardware wallet (assessed 2026-08-22)

Source: https://x.com/z0r0zzz/status/2091364241907597467 · repo https://github.com/z0r0z/cell · bounty https://poidh.xyz/mainnet/bounty/24

## Verdict: real design, zero bench builds. Buildable, but you'd be build #1.

- Repo created 2026-08-21, 30 commits, 4 stars, 1 fork. Heavily AI-authored (has `CLAUDE.md`, `.claude/settings.json`) — polished docs ≠ proven hardware.
- **Verified here:** `firmware/run_tests.py` → **PASS, 37 suites** (py3.12 venv; 3.14 system python can't build numpy). Signing stack checked against BIP/RFC/EIP vectors; author also reports a Bitcoin Core regtest round-trip (p2wpkh/p2sh/p2pkh/p2tr/p2wsh 2-of-3).
- **Verified here:** `tools/gen_printables.py` regenerates all 10 STLs, fit checks pass, envelope 116.2×73.2×28.3 mm. (Committed STLs are git-LFS pointers — `brew install git-lfs` or just run the generator.)
- **Not verified by anyone:** README says "Nothing has been built on a bench yet." `firmware/hardware.py` "has never touched hardware." ATECC608B driver, display, buttons, camera, and — the important one — the **laser-speckle clotting gate** and **AS7341 415nm haemoglobin gate** are all paper physics until someone runs milestone 5–7 of `BUILD.md §15`.
- Bounty: **0.111 ETH (~$269), 0 claims, 3 contributors**, "topped up over time" from a $CELL DAICO. Partial claims count: reader-only (milestone 7 spoof panel) is a payable claim; a documented *failure* is too.

## How to build it (the path the author recommends)

**Phase A — reader kit (~$62 + ~$31 consumables), proves the physics in a weekend:**
1. Pi boots with radios dead → 2. AS7341 reads a white card <1% RSD → 3. print 20 cartridges, white patches agree <3% → 4. optical chamber light-tight → 5. **spectrum of dye vs. your blood separates at 415 nm** ("it works" moment) → 6. 10-min speckle time series: blood decorrelates then arrests, dye never speckles → 7. spoof panel + `calibrate.py` → ROC. **That's a bounty claim.**

**Phase B — wallet half (~$32 more):** ATECC608B config + lock (permanent — buy two), firmware on the Pi, provision, regtest, testnet spend gated by a real sample.

## Shopping list (from `BOM.csv`, $94.40 hw + ~$31 consumables)

Reader kit:
- Raspberry Pi Zero 2 W ×1 (~$15) — you'll cut the antenna trace
- AMS AS7341 spectrometer breakout — **Adafruit 4698** (~$16)
- Pi Camera (IMX219 / v2) + **mini-CSI (Zero) cable** — lens gets removed (~$10)
- 650 nm laser diode module ≤5 mW (~$2)
- 5 mm white LED 5000K ×2, 940 nm IR LED ×1
- 2N7002 SOT-23 ×2, passives (68R/47R/10k/2.2k/100nF)
- Breadboard + jumpers, 16 GB A2 microSD
- Black PETG ~90 g, **white PETG ~60 g (separate spool — it's the photometric reference)**
- Consumables: 100 contact-activated 28G lancets (pharmacy), 100 IPA pads, 0.10 mm PET film (laser transparency), 3M 300LSE tape, **1 L sharps container (mandatory)**

Wallet half:
- ATECC608B breakout — **Adafruit 4314** (~$6) ×2 (lock is one-way)
- ST7789 1.3" 240×240 SPI display (~$8) — bezel STL is regenerated to *your* module's dims
- 12 mm tactile switches ×4, USB-C power-only breakout, micro-USB OTG adapter, cheap USB webcam (QR in)
- M2.5×8 screws + heat-set inserts ×8, M2×6 self-tappers ×4, 10 mm × 0.5 mm clear acrylic/glass disc

Printer needs: 120×80 mm bed, PETG temps, **ironing** (cartridge white patch), matte black paint for optical bores. No supports on any part.

## Gotchas to know before ordering
- PETG not PLA (creep under screw preload, light-tightness).
- Camera lens comes OFF (lensless speckle); fixed exposure/gain/AWB or the correlation measurement is destroyed.
- LED is not a laser — speckle needs coherence; the 650 nm diode is mandatory.
- Blood tier rejects anyone on anticoagulants/daily aspirin by design. Touch tier (pulse) is the everyday path.
- `SAFETY.md`: one device one person, commercial lancets only, sharps container.
- Local clone + venv: `cell/repo/` (gitignored). `uv venv -p 3.12 .venv && uv pip install -r firmware/requirements.txt && .venv/bin/python firmware/run_tests.py`.
