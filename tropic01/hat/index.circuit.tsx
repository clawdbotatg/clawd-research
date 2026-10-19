import { SM04B_SRSS_TB_LF__SN_ } from "./imports/SM04B_SRSS_TB_LF__SN_"

// tropic-hat v0.1: a Pico-sized board that goes between the Pico and the Waveshare Pico-LCD-1.3.
// The Pico plugs into a stacking header on top; the header's long tails plug into the screen.
// All 40 pins pass straight through. On it: TROPIC01 on SPI0, and a STEMMA QT port on I2C0 so the
// Trust M (or any Qwiic board) plugs in with a normal JST cable. No wires, no solder for the builder.
//
// Top view = looking at the Pico's chip side, USB end at +y. Pin 1 (GP0) top-left, pin 40 (VBUS) top-right.
// TROPIC01: SCK GP6, MOSI GP7, MISO GP0, CS GP14 (GPO not wired: poll instead).
// STEMMA QT: SDA GP4, SCL GP5. Power from the Pico's 3V3 OUT (pin 36).
// Routed by hand: top = signals + 3V3 + GND pour, bottom = GND pour + the I2C runs and one SDI hop.

const P = 2.54
const LEFT = ["GP0", "GP1", "GND1", "GP2", "GP3", "GP4", "GP5", "GND2", "GP6", "GP7",
  "GP8", "GP9", "GND3", "GP10", "GP11", "GP12", "GP13", "GND4", "GP14", "GP15"]           // pins 1-20, top-down
const RIGHT = ["VBUS", "VSYS", "GND8", "V3V3_EN", "V3V3", "ADC_VREF", "GP28", "GND7", "GP27", "GP26",
  "RUN", "GP22", "GND6", "GP21", "GP20", "GP19", "GP18", "GND5", "GP17", "GP16"]          // pins 40-21, top-down
const pinNum = (side: "L" | "R", i: number) => (side === "L" ? i + 1 : 40 - i)
const picoLabels: Record<string, string[]> = {}
LEFT.forEach((n, i) => (picoLabels[`pin${pinNum("L", i)}`] = [n]))
RIGHT.forEach((n, i) => (picoLabels[`pin${pinNum("R", i)}`] = [n]))

const PicoHeader = (props: any) => (
  <chip
    {...props}
    pinLabels={picoLabels}
    footprint={
      <footprint>
        {LEFT.map((_, i) => (
          <platedhole portHints={[`pin${pinNum("L", i)}`]} pcbX={-8.89} pcbY={24.13 - i * P}
            shape="circle" holeDiameter="1.02mm" outerDiameter="1.7mm" />
        ))}
        {RIGHT.map((_, i) => (
          <platedhole portHints={[`pin${pinNum("R", i)}`]} pcbX={8.89} pcbY={24.13 - i * P}
            shape="circle" holeDiameter="1.02mm" outerDiameter="1.7mm" />
        ))}
      </footprint>
    }
  />
)

// TROPIC01, QFN32 4x4 mm, 0.4 mm pitch (datasheet A.11 p63-64). Pins CCW from pin 1 top-left.
const tropicLabels = {
  pin1: ["VCC1"], pin2: ["GND1"], pin3: ["PD3"], pin4: ["GPO"], pin5: ["SDI"], pin6: ["SDO"], pin7: ["SCK"], pin8: ["CSN"],
  pin9: ["PD9"], pin10: ["PD10"], pin11: ["VCC2"], pin12: ["GND2"], pin13: ["DNC13"], pin14: ["DNC14"], pin15: ["NC15"], pin16: ["NC16"],
  pin17: ["DNC17"], pin18: ["DNC18"], pin19: ["DNC19"], pin20: ["DNC20"], pin21: ["DNC21"], pin22: ["PU22"], pin23: ["GND3"], pin24: ["VCC3"],
  pin25: ["NC25"], pin26: ["DNC26"], pin27: ["DNC27"], pin28: ["DNC28"], pin29: ["DNC29"], pin30: ["PD30"], pin31: ["PD31"], pin32: ["NC32"],
  pin33: ["EP"],
} as const

// Land pattern from datasheet A.11 p64 (e 0.4, L 0.3, b 0.2, EP 2.9) and Tropic's TS1702 board:
// pads 0.7 x 0.2 centred 1.95 mm out, EP 2.65 mm square. Pins CCW: left top-down, bottom, right, top.
const pad = (n: number) => {
  const side = Math.floor((n - 1) / 8), k = (n - 1) % 8, o = -1.4 + k * 0.4
  if (side === 0) return { x: -1.95, y: -o, w: 0.7, h: 0.2 }
  if (side === 1) return { x: o, y: -1.95, w: 0.2, h: 0.7 }
  if (side === 2) return { x: 1.95, y: o, w: 0.7, h: 0.2 }
  return { x: -o, y: 1.95, w: 0.2, h: 0.7 }
}
const TropicFootprint = () => (
  <footprint>
    {Array.from({ length: 32 }, (_, i) => {
      const q = pad(i + 1)
      return <smtpad portHints={[`pin${i + 1}`]} pcbX={q.x} pcbY={q.y} width={q.w} height={q.h} shape="rect" />
    })}
    <smtpad portHints={["pin33"]} pcbX={0} pcbY={0} width={2.65} height={2.65} shape="rect" />
    <silkscreenpath route={[{ x: -2.4, y: 2.0 }, { x: -2.4, y: 2.4 }, { x: -2.0, y: 2.4 }]} />
  </footprint>
)

// pcbPath points are in the anchor's component frame. J1 sits at the origin unrotated, so paths
// anchored on a J1 pin are global mm. U1 is unrotated at (UX, UY): u() turns global mm into its frame.
const UX = -3, UY = 13
const u = (x: number, y: number) => ({ x: x - UX, y: y - UY })
const via = (x: number, y: number, toLayer: "top" | "bottom") => ({ x, y, via: true, toLayer })
const V3 = [{ x: 7.6, y: 15.2 }, { x: 7.6, y: 16.2 }]   // 3V3 leaves pin 36 and runs left along y = 16.2

export default () => (
  <board width="21mm" height="51mm" thickness="1.6mm"
    fabricatorPreset="jlcpcb_standard_20260912"
    pcbStyle={{ viaPadDiameter: 0.5, viaHoleDiameter: 0.3 }}
    minTraceWidth={0.15} minTraceToPadEdgeClearance={0.1}
    minViaEdgeToPadEdgeClearance={0.15} minBoardEdgeClearance={0.3}>
    <PicoHeader name="J1" pcbX={0} pcbY={0} />
    <copperpour layer="top" connectsTo="net.GND" boardEdgeMargin="0.4mm" />
    <copperpour layer="bottom" connectsTo="net.GND" boardEdgeMargin="0.4mm" />

    {/* TROPIC01 (consigned: not in JLC's library). */}
    <chip name="U1" manufacturerPartNumber="TR01-C2P-T301" pinLabels={tropicLabels}
      footprint={<TropicFootprint />} pcbX={UX} pcbY={UY} />

    {/* ground pins: short stubs into the exposed pad; the EP drops to both pours through 4 vias */}
    <trace from="U1.GND1" to="U1.EP" pcbPathRelativeTo="U1.GND1" pcbPath={[{ x: -1.0, y: 1.0 }]} />
    <trace from="U1.PD3" to="U1.EP" pcbPathRelativeTo="U1.PD3" pcbPath={[{ x: -1.0, y: 0.6 }]} />
    <trace from="U1.PD9" to="U1.EP" pcbPathRelativeTo="U1.PD9" pcbPath={[{ x: -1.4, y: -1.2 }]} />
    <trace from="U1.PD10" to="U1.EP" pcbPathRelativeTo="U1.PD10" pcbPath={[{ x: -1.0, y: -1.0 }]} />
    <trace from="U1.GND2" to="U1.EP" pcbPathRelativeTo="U1.GND2" pcbPath={[{ x: -0.2, y: -1.0 }]} />
    <trace from="U1.GND3" to="U1.EP" pcbPathRelativeTo="U1.GND3" pcbPath={[{ x: 1.0, y: 1.0 }]} />
    <trace from="U1.PD30" to="U1.EP" pcbPathRelativeTo="U1.PD30" pcbPath={[{ x: -0.6, y: 1.0 }]} />
    <trace from="U1.PD31" to="U1.EP" pcbPathRelativeTo="U1.PD31" pcbPath={[{ x: -1.0, y: 1.0 }]} />
    <trace from="U1.EP" to="net.GND" />
    {[[-0.6, -0.6], [0.6, -0.6], [-0.6, 0.6], [0.6, 0.6]].map(([x, y]) => (
      <via pcbX={UX + x} pcbY={UY + y} holeDiameter="0.3mm" outerDiameter="0.5mm" connectsTo="net.GND" />
    ))}

    {/* SPI. MISO goes up to GP0 past the pull-up; the rest fan out left and run down beside the header.
        SDI hops under MISO on the bottom layer. */}
    <capacitor name="C1" capacitance="100nF" footprint="0402" pcbX={-6.0} pcbY={15.4} pcbRotation={180} />
    <capacitor name="C2" capacitance="100nF" footprint="0402" pcbX={-3.4} pcbY={9.9} />
    <capacitor name="C3" capacitance="100nF" footprint="0402" pcbX={0.5} pcbY={14.2} pcbRotation={270} />
    <resistor name="R1" resistance="47k" footprint="0402" pcbX={-6.2} pcbY={18.5} />
    <trace from="U1.SDO" to="J1.GP0" pcbPathRelativeTo="U1.SDO" pcbPath={[u(-7.4, 12.4), u(-7.4, 23.2)]} />
    <trace from="U1.SDO" to="R1.pin1" pcbPathRelativeTo="U1.SDO" pcbPath={[u(-7.4, 12.4), u(-7.4, 18.5)]} />
    <trace from="U1.SCK" to="J1.GP6" pcbPathRelativeTo="U1.SCK" pcbPath={[u(-6.9, 12.0), u(-6.9, 4.6)]} />
    <trace from="U1.CSN" to="J1.GP14" pcbPathRelativeTo="U1.CSN" pcbPath={[u(-5.7, 11.6), u(-5.7, -20.6)]} />
    <trace from="U1.SDI" to="J1.GP7" pcbPathRelativeTo="U1.SDI"
      pcbPath={[u(-5.5, 12.8), { ...u(-5.8, 13.2), via: true, toLayer: "bottom" }, { ...u(-6.3, 10.9), via: true, toLayer: "top" }, u(-6.3, 2.6)]} />

    {/* 3V3 from pin 36 to the three decoupling caps (one per VCC pin), the pull-ups and the STEMMA QT port */}
    <trace from="J1.V3V3" to="C1.pin1" maxLength="60mm" pcbPathRelativeTo="J1.V3V3" pcbPath={[...V3, { x: -5.49, y: 16.2 }]} />
    <trace from="J1.V3V3" to="R1.pin2" maxLength="60mm" pcbPathRelativeTo="J1.V3V3" pcbPath={[...V3, { x: -5.2, y: 16.2 }, { x: -5.2, y: 18.5 }]} />
    <trace from="J1.V3V3" to="C3.pin1" maxLength="60mm" pcbPathRelativeTo="J1.V3V3" pcbPath={[...V3, { x: 0.5, y: 16.2 }]} />
    <trace from="J1.V3V3" to="C2.pin1" maxLength="60mm" pcbPathRelativeTo="J1.V3V3" pcbPath={[...V3, { x: 1.4, y: 16.2 }, { x: 1.4, y: 9.3 }, { x: -3.91, y: 9.3 }]} />
    <trace from="J1.V3V3" to="J2.pin2" maxLength="60mm" pcbPathRelativeTo="J1.V3V3" pcbPath={[...V3, { x: 1.4, y: 16.2 }, { x: 1.4, y: -15.0 }, { x: -0.5, y: -15.0 }]} />
    <trace from="U1.VCC1" to="C1.pin1" maxLength="3mm" pcbPathRelativeTo="U1.VCC1" pcbPath={[u(-5.49, 14.9)]} />
    <trace from="U1.VCC2" to="C2.pin1" maxLength="3mm" pcbPathRelativeTo="U1.VCC2" pcbPath={[u(-3.6, 10.7), u(-3.91, 10.3)]} />
    <trace from="U1.VCC3" to="C3.pin1" maxLength="3mm" pcbPathRelativeTo="U1.VCC3" pcbPath={[u(-0.5, 14.71)]} />
    <trace from="U1.PU22" to="J1.V3V3" pcbPathRelativeTo="U1.PU22" pcbPath={[u(-0.35, 13.6), u(0.0, 13.0), u(1.4, 13.0), u(1.4, 16.2), ...V3.slice().reverse().map((p) => u(p.x, p.y))]} />
    <trace from="U1.GND2" to="C2.pin2" maxLength="3mm" pcbPathRelativeTo="U1.GND2" pcbPath={[u(-3.2, 10.7), u(-2.89, 10.3)]} />
    <trace from="U1.GND3" to="C3.pin2" maxLength="3mm" pcbPathRelativeTo="U1.GND3" pcbPath={[u(-0.5, 14.0)]} />
    <trace from="C1.pin2" to="net.GND" maxLength="10mm" />

    {/* STEMMA QT / Qwiic: 1 GND, 2 V+, 3 SDA, 4 SCL. Signal pads inboard, opening flush toward the non-USB end (as on Adafruit's boards). Breakouts carry their
        own pull-ups. SDA/SCL drop to the bottom beside their header pins and come back up under the plug. */}
    <SM04B_SRSS_TB_LF__SN_ name="J2" pcbX={0} pcbY={-21} />
    <trace from="J1.GP4" to="J2.pin3" pcbPathRelativeTo="J1.GP4"
      pcbPath={[via(-7.75, 10.7, "bottom"), { x: -7.2, y: 10.15 }, { x: -7.2, y: -17.6 }, via(0.5, -17.6, "top")]} />
    <trace from="J1.GP5" to="J2.pin4" pcbPathRelativeTo="J1.GP5"
      pcbPath={[via(-7.75, 8.2, "bottom"), { x: -7.75, y: -21.0 }, { x: 1.5, y: -21.0 }, via(1.5, -20.5, "top")]} />
    <trace from="J2.pin1" to="net.GND" />
    <trace from="J1.GND1" to="net.GND" />
    <trace from="J1.GND8" to="net.GND" />

    <silkscreentext text="USB" pcbX={0} pcbY={24} fontSize={1} />
    <silkscreentext text="tropic-hat v0.1" pcbX={4.5} pcbY={-12} fontSize={0.8} pcbRotation={90} />
  </board>
)
