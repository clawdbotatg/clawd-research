export default () => (
  <board width="20mm" height="20mm">
    <voltagesource name="V1" voltage="5V" waveShape="square" frequency="1kHz" dutyCycle={0.5} />
    <resistor name="R1" resistance="1k" footprint="0402" />
    <capacitor name="C1" capacitance="100nF" footprint="0402" />
    <trace from=".V1 > .pin1" to=".R1 > .pin1" />
    <trace from=".R1 > .pin2" to=".C1 > .pin1" />
    <trace from=".C1 > .pin2" to=".V1 > .pin2" />
    <voltageprobe name="VP1" connectsTo=".C1 > .pin1" />
    <analogsimulation duration="5ms" />
  </board>
)
