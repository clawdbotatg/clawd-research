import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["VDD"],
  pin2: ["SCL"],
  pin3: ["GND"],
  pin4: ["LDR"],
  pin5: ["PGND"],
  pin6: ["GPIO"],
  pin7: ["INT"],
  pin8: ["SDA"]
} as const

const pinAttributes = {
  pin1: {requiresPower: true},
  pin3: {requiresGround: true},
  pin5: {requiresGround: true}
} as const

export const AS7341_DLGM = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      pinAttributes={pinAttributes}
      supplierPartNumbers={{
  "jlcpcb": [
    "C2649486"
  ]
}}
      manufacturerPartNumber="AS7341-DLGM"
      footprint="dfn8_p0.7998mm_w1.8511mm_pw0.488mm_pl0.575mm_pin1location(leftside,bottom)"
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2649486.obj?uuid=8be43ef4d25446068c1502e97a221060",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C2649486.step?uuid=8be43ef4d25446068c1502e97a221060",
        pcbRotationOffset: 0,
        modelOriginPosition: { x: -0.000012700000070253736, y: 0, z: -0.22 },
      }}
      {...props}
    />
  )
}