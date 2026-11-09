NP=dict(zip(range(2,18),[56,57,56,60,60,63,64,63,60,66,60,65,70,60,64,68]))
def pm(t): return 24*t+8*t*t+NP[t]*(2*t+2)
for t in [3,4,6,7,8,10,17]: print('t',t,'muls',pm(t))
OVH=1.05  # adds/loads
fixed=63*9+300; generic=251*9+63*10+300
print('fixedbase M',fixed,'generic',generic)
cores={'RP2040 asm':(133e6,4000,3.59e6,50e3,0.4e6),'RP2040 C':(133e6,8200,4.07e6,50e3,0.5e6),
       'RP2350 asm':(150e6,450,0.411e6,15e3,0.05e6),'RP2350 C':(150e6,1030,0.9e6,15e3,0.1e6)}
for n,(hz,mc,x,bl,dec) in cores.items():
  ms=lambda c: c/hz*1e3
  P=lambda t: pm(t)*mc*OVH
  eddsa=(fixed+pm(6)+10)*mc*OVH+bl
  enc=3*x+2*dec+20e3
  tx=2*P(3)+3*P(3)+3*P(4)+P(8)+eddsa+3*enc
  print(f"{n}: mul {mc/hz*1e6:.1f}us P4 {ms(P(4)):.1f} P7 {ms(P(7)):.1f} P17 {ms(P(17)):.1f} P8 {ms(P(8)):.1f} eddsa {ms(eddsa):.1f} (generic {ms((generic+pm(6))*mc*OVH+bl):.1f}) x25519 {ms(x):.1f} enc/out {ms(enc):.1f} tx {ms(tx):.0f} poseidon-part {ms(tx-3*enc-eddsa):.0f}")
