#include <stdint.h>
/* BN254 Fr = 21888242871839275222246405745257275088548364400416034343698204186575808495617 */
#define N16 16
static const uint16_t P16[16]={0x0001,0xf000,0xf593,0x43e1,0x7091,0x79b9,0xe848,0x2833,0x585d,0x8181,0x45b6,0xb850,0xa029,0xe131,0x4e72,0x3064};
#define NP16 0xffff /* -p^-1 mod 2^16 : p ends in 0x0001 so -1 */
/* CIOS Montgomery with 16-bit limbs, only 32-bit products: M0+ friendly */
void mont16(uint16_t *r, const uint16_t *a, const uint16_t *b){
  uint32_t t[N16+2];
#pragma GCC unroll 18
  for(int i=0;i<N16+2;i++) t[i]=0;
#pragma GCC unroll 16
  for(int i=0;i<N16;i++){
    uint32_t C=0, bi=b[i];
#pragma GCC unroll 16
    for(int j=0;j<N16;j++){ uint32_t s=t[j]+a[j]*bi+C; t[j]=s&0xffff; C=s>>16; }
    uint32_t s=t[N16]+C; t[N16]=s&0xffff; t[N16+1]=s>>16;
    uint32_t m=(t[0]*NP16)&0xffff;
    s=t[0]+m*P16[0]; C=s>>16;
#pragma GCC unroll 16
    for(int j=1;j<N16;j++){ s=t[j]+m*P16[j]+C; t[j-1]=s&0xffff; C=s>>16; }
    s=t[N16]+C; t[N16-1]=s&0xffff; t[N16]=t[N16+1]+(s>>16);
  }
  /* final conditional subtract */
  uint32_t br=0; uint16_t u[N16];
#pragma GCC unroll 16
  for(int j=0;j<N16;j++){ uint32_t d=t[j]-P16[j]-br; u[j]=d&0xffff; br=(d>>16)&1; }
  int use = (t[N16]!=0) || !br;
#pragma GCC unroll 16
  for(int j=0;j<N16;j++) r[j]= use?u[j]:t[j];
}
/* 32-bit limbs with 64-bit products: M33 (UMLAL/UMAAL) */
static const uint32_t P32[8]={0xf0000001,0x43e1f593,0x79b97091,0x2833e848,0x8181585d,0xb85045b6,0xe131a029,0x30644e72};
#define NP32 0xefffffffu
void mont32(uint32_t *r, const uint32_t *a, const uint32_t *b){
  uint32_t t[10]={0};
#pragma GCC unroll 8
  for(int i=0;i<8;i++){
    uint64_t C=0; uint32_t bi=b[i];
#pragma GCC unroll 8
    for(int j=0;j<8;j++){ uint64_t s=(uint64_t)a[j]*bi+t[j]+C; t[j]=(uint32_t)s; C=s>>32; }
    uint64_t s=(uint64_t)t[8]+C; t[8]=(uint32_t)s; t[9]=s>>32;
    uint32_t m=t[0]*NP32;
    s=(uint64_t)m*P32[0]+t[0]; C=s>>32;
#pragma GCC unroll 8
    for(int j=1;j<8;j++){ s=(uint64_t)m*P32[j]+t[j]+C; t[j-1]=(uint32_t)s; C=s>>32; }
    s=(uint64_t)t[8]+C; t[7]=(uint32_t)s; t[8]=t[9]+(uint32_t)(s>>32);
  }
  uint32_t u[8]; uint64_t br=0;
#pragma GCC unroll 8
  for(int j=0;j<8;j++){ uint64_t d=(uint64_t)t[j]-P32[j]-br; u[j]=(uint32_t)d; br=(d>>32)&1; }
  int use=(t[8]!=0)||!br;
#pragma GCC unroll 8
  for(int j=0;j<8;j++) r[j]=use?u[j]:t[j];
}
