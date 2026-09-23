import { Fragment } from "react"
import { RaspberryPiHatBoard } from "@tscircuit/common"
import { ATECC608B_SSHDA_T } from "./imports/ATECC608B_SSHDA_T"

// CELL reader-kit driver HAT (toolchain test, 2026-09-23).
// Replaces the breadboard in cell/BOM.csv: ATECC608B on I2C, three 2N7002
// low-side switches for the 650nm laser module + white LED + 940nm IR LED,
// and a 4-pin pass-through header for the AS7341 breakout.
export default () => (
  <RaspberryPiHatBoard name="PI">
    {/* secure element, I2C @ 3V3 */}
    <ATECC608B_SSHDA_T name="U1" pcbX={-18} pcbY={-14} />
    <resistor name="R1" resistance="4.7k" footprint="0603" pcbX={-10} pcbY={-8} />
    <resistor name="R2" resistance="4.7k" footprint="0603" pcbX={-10} pcbY={-12} />
    <trace from="U1.VCC" to="net.V3_3" />
    <trace from="U1.GND" to="net.GND" />
    <trace from="U1.SDA" to="net.SDA" />
    <trace from="U1.SCL" to="net.SCL" />
    <trace from="R1.pin1" to="net.SDA" />
    <trace from="R1.pin2" to="net.V3_3" />
    <trace from="R2.pin1" to="net.SCL" />
    <trace from="R2.pin2" to="net.V3_3" />
    <trace from="PI.GPIO_2" to="net.SDA" />
    <trace from="PI.GPIO_3" to="net.SCL" />
    <trace from="PI.V3_3_1" to="net.V3_3" />
    <trace from="PI.V5_1" to="net.V5" />
    <trace from="PI.GND_1" to="net.GND" />

    {/* AS7341 breakout pass-through: 3V3 GND SDA SCL */}
    <pinheader name="J1" pinCount={4} pitch="2.54mm" pcbX={-24} pcbY={0} pcbRotation={90}
      pinLabels={["V3_3", "GND", "SDA", "SCL"]} />
    <trace from="J1.pin1" to="net.V3_3" />
    <trace from="J1.pin2" to="net.GND" />
    <trace from="J1.pin3" to="net.SDA" />
    <trace from="J1.pin4" to="net.SCL" />

    {/* three low-side switches: laser (GPIO17), white LED (GPIO27), IR LED (GPIO22) */}
    {[
      { n: 1, gpio: "GPIO_17", x: -2, load: "LASER", rs: null },
      { n: 2, gpio: "GPIO_27", x: 7, load: "WHITE", rs: "68" },
      { n: 3, gpio: "GPIO_22", x: 22, load: "IR", rs: "47" },
    ].map(({ n, gpio, x, load, rs }) => (
      <Fragment key={n}>
        <mosfet name={`Q${n}`} channelType="n" mosfetMode="enhancement" footprint="sot23"
          supplierPartNumbers={{ jlcpcb: ["C414015"] }} manufacturerPartNumber="2N7002K"
          pcbX={x} pcbY={-14} />
        <resistor name={`RG${n}`} resistance="100" footprint="0603" pcbX={x - 3} pcbY={-8} />
        <resistor name={`RP${n}`} resistance="10k" footprint="0603" pcbX={x + 3} pcbY={-8} />
        <pinheader name={`J${n + 1}`} pinCount={2} pitch="2.54mm" pcbX={x} pcbY={-24}
          pinLabels={["V5", `${load}_N`]} />
        <trace from={`PI.${gpio}`} to={`RG${n}.pin1`} />
        <trace from={`RG${n}.pin2`} to={`Q${n}.gate`} />
        <trace from={`RP${n}.pin1`} to={`Q${n}.gate`} />
        <trace from={`RP${n}.pin2`} to="net.GND" />
        <trace from={`Q${n}.source`} to="net.GND" />
        <trace from={`J${n + 1}.pin1`} to="net.V5" />
        {rs ? (
          <>
            <resistor name={`RS${n}`} resistance={rs} footprint="1206" pcbX={x} pcbY={-19} pcbRotation={180} />
            <trace from={`J${n + 1}.pin2`} to={`RS${n}.pin1`} />
            <trace from={`RS${n}.pin2`} to={`Q${n}.drain`} />
          </>
        ) : (
          <trace from={`J${n + 1}.pin2`} to={`Q${n}.drain`} />
        )}
      </Fragment>
    ))}
  </RaspberryPiHatBoard>
)
