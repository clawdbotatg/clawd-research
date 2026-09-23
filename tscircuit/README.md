# tscircuit — "React for PCBs", tested hands-on 2026-09-23

Site https://tscircuit.com · docs https://docs.tscircuit.com · GitHub https://github.com/tscircuit (451 repos) · skill https://github.com/tscircuit/skill

## What it is

You write a circuit as TSX (`<board>`, `<chip>`, `<resistor>`, `<trace>`), it compiles to
Circuit JSON, and from that one file you get schematic, PCB layout, autorouting, 3D
model, Gerbers, BOM with LCSC part numbers, pick-and-place, KiCad project, SPICE
simulation. MIT licensed. Founder Seve Ibarluzea (ex Seam CTO), Boost VC seed, no 2026
raise found. ~2.7k stars on the umbrella repo, 30 contributors on `core`, and it ships
several releases a day (4,720 npm releases; three landed the morning I tested).

The pitch in 2026 is explicitly "the framework for AI-generated electronics": tell any
coding agent "use tscircuit" and it can install the CLI and go. Adafruit covered Seve's
Codex demos in May 2026 as possibly "the first fully vibed PCBs ever made."

## What I verified locally (Mac, node 25, CLI 0.0.2646)

| Step | Result |
|---|---|
| `npm i tscircuit @tscircuit/cli`, `tsci init -y` | Scaffolds a project and drops the agent skill into `.agents/skills/tscircuit/` and `.claude/` automatically |
| `tsci build --pcb-png --schematic-png --3d-png` | 7 s for a 20-part board, incl. autorouting and 3D render |
| `tsci search --jlcpcb AS7341` / `ATECC608B` / `2N7002` | Live LCSC stock and part numbers |
| `tsci import --jlcpcb C2649486` | Generates a typed `<chip>` component with pin labels, footprint (98.75% match), 3D model URL, LCSC number (`cell-hat/imports/`) |
| `tsci check netlist / placement / shorts` | Deterministic pass/fail, exit codes. Placement check told me a header sat in the HAT camera slot |
| `tsci export -f gerbers` | Zip with 9 gerbers, 2 drill files, `bom.csv` (LCSC numbers auto-picked for every passive), `pick_and_place.csv`. Docs say fab export is UI-only; the CLI does it fine |
| `tsci export -f kicad_zip` / `-f glb` | Full KiCad project (2.6 MB) and a 3D GLB |
| `tsci simulate analog rc.circuit.tsx` | ngspice-in-WASM transient on an RC filter, 6 s, prints the table (`rc-sim/`) |

Also available but not run: `tsci snapshot --test` (visual regression in CI), `tsci build
--kicad-pcm` (serve your parts to KiCad as a library), `tsci convert` (kicad_mod → TSX),
`--digikey`/`--mouser` search, `tsci push` to the registry, ordering through
tscircuit.com (Stripe checkout, JLCPCB is the only vendor today).

## The spike: a CELL reader-kit driver HAT (`cell-hat/`)

Built to test the real pipeline on something we care about. It replaces the breadboard
in `cell/BOM.csv`: ATECC608B secure element on the Pi's I2C with 4.7k pull-ups, three
2N7002 low-side switches (gate 100R, 10k pulldown) for the 650 nm laser module, white
LED (68R series) and 940 nm IR LED (47R series), each on a 2-pin header off 5 V, plus a
4-pin pass-through header for the AS7341 breakout. Uses `RaspberryPiHatBoard` from
`@tscircuit/common` (full-size HAT outline with camera slot).

- `index.circuit.tsx` — 80 lines, the whole design
- `out/pcb.png`, `out/schematic.png`, `out/3d.png` — renders
- `out/fab.zip` — Gerbers + drill + BOM + PnP, uploadable to JLCPCB as-is
- Rebuild: `cd cell-hat && npm i && npx tsci build --pcb-png && npx tsci export index.circuit.tsx -f gerbers -o fab.zip`

Not electrically vetted and not ordered. AS7341 wants 1.7–2.0 V VDD, so it stays on the
Adafruit breakout (which has the LDO and level shift) rather than on the HAT. The Pi Zero
is 65×30 mm; this outline is the full 65×56 HAT, fine for the bench, wrong for the case.

## What went wrong (an agent will hit these too)

- `<group>` wrapping each switch stage silently broke routing: 16 "not connected" errors,
  zero explanation. Groups are subcircuits with their own routing scope. Use fragments.
- Autorouter exits 0 while warning "5 chip overlaps detected in final layout": that's the
  schematic autolayout, and it does overlap (see `out/schematic.png`). Schematic output is
  the weak half; PCB is the strong half.
- Noise: every build prints "trace is missing a name" for each trace, "refdes should start
  with R" for RG1/RP1, "no `<schematicsheet>`". An agent needs to learn to filter.
- Version churn is real. Peer-dep warnings on init, footprint-vs-supplier IoU warnings on
  the defaults. Pin the version in `package.json`.
- Full ERC/DRC is not there. Netlist, placement, shorts and courtyard checks exist;
  trace-width vs fab rules is on you.

## What we can do with it

1. **CELL, for real.** The spike is 80% of a bench board. Finish: Zero-size outline,
   mounting holes, a proper laser driver stage, order 5 from JLCPCB (~$10 bare, ~$40 with
   assembly). This turns "you'd be build #1" into a repeatable kit.
2. **Hardware in the harness.** `tsci init` already writes a Claude skill. Publish
   `SKILL-upstream-2026-09-23.md` to the relay skill shelf so any session can design a
   board from a prompt. Agent loop is `check netlist → build --pcb-png → check placement
   → check shorts → export`, all headless with exit codes.
3. **Hardware game.** This is the missing engine for the fake-budget/real-hardware tycoon
   concept: players compose boards, `@tscircuit/eval` + `runframe` render them in the
   browser, and the parts engine prices the BOM from live LCSC stock. Real hardware, real
   prices, no fab needed until a player wins.
4. **An agent PCB benchmark / arena.** Same spec to N agents, graded by `tsci check`
   (deterministic), routed-net ratio, DRC, BOM cost, plus `tsci snapshot` diffs for
   review. Fits the simple-eval bones and the agent esports format. tscircuit's own docs
   mention "dataset-style board families", so they want this data too.
5. **Morning show / X content.** A prompt-to-board-to-order clip is exactly the kind of
   demo that travels; 3D GLB output drops into vgpu or three.js.

## Numbers

| | |
|---|---|
| Build, 20 parts, routed + 3 PNGs | 7 s |
| SPICE transient, 5 ms window | 6 s |
| CLI releases | 4,720 (several per day) |
| Umbrella repo stars | 2,744 |
| Ordering vendors on tscircuit.com | 1 (JLCPCB) |

Sources: tscircuit.com, docs.tscircuit.com (quickstart, fabrication files, ordering,
AI-prompting guide), github.com/tscircuit/{tscircuit,skill,tsci-agent,common}, npm
registry, Adafruit blog 2026-05-07, Tracxn/PitchBook/f4.fund profiles.
