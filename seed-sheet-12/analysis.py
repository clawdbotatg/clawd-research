#!/usr/bin/env python3
"""How weak is 'word splitting' (k-of-n cards, each card a subset of the words)?

Construction: for every (k-1)-subset S of the n cards, one group of words is
left OFF exactly the cards in S (and printed on the other n-k+1). Any k cards
cover every group; any k-1 cards miss exactly one group. Groups = C(n, k-1).

An attacker holding j < k cards misses every group whose S contains all of
their cards: C(n-j, k-1-j) groups. Unknown words = W * C(n-j,k-1-j) / C(n,k-1).

Cost model: candidates = 2048^u. The BIP39 checksum (W/3 bits) is a cheap
SHA256 filter, so the expensive step (PBKDF2-HMAC-SHA512 x2048 + BIP32 path
+ secp256k1) runs on 2048^u / 2^(W/3) survivors. Assumed attacker rate:
1e6 full derivations/s per GPU (generous; hashcat PBKDF2-SHA512 on a 4090 is
in this ballpark before the EC math). Attacker knows the word positions
(they're printed) and a target address.
"""
from math import comb, log2

RATE_PER_GPU = 1e6
GPUS = 1000                     # a serious attacker
YEAR = 365.25 * 86400

def fmt_time(s):
    if s < 1: return "instant"
    if s < 60: return f"{s:.0f} s"
    if s < 3600: return f"{s/60:.0f} min"
    if s < 86400: return f"{s/3600:.1f} h"
    if s < YEAR: return f"{s/86400:.0f} d"
    y = s / YEAR
    if y < 1e3: return f"{y:.0f} y"
    return f"{y:.1e} y"

def row(W, k, n, j):
    groups = comb(n, k-1)
    if W % groups: return None
    per_group = W // groups
    on_card = W - per_group * comb(n-1, k-2)           # words printed on one card
    u = per_group * comb(n-j, k-1-j)                    # unknown to a j-card holder
    if u == 0: return None
    cs_bits = W // 3
    cands = 2048**u / 2**cs_bits
    bits = 11*u - cs_bits
    return dict(W=W, k=k, n=n, j=j, per_card=on_card, u=u, bits=bits,
                one_gpu=fmt_time(cands/RATE_PER_GPU), farm=fmt_time(cands/(RATE_PER_GPU*GPUS)))

schemes = [(2,2),(2,3),(2,4),(3,3),(3,4),(3,5),(4,4),(4,5),(4,6)]
print(f"{'words':>5} {'scheme':>7} {'per card':>8} {'holds':>5} {'unknown':>7} {'bits':>4} {'1 GPU':>10} {'1000 GPUs':>10}")
for W in (12, 24):
    for k, n in schemes:
        for j in range(1, k):
            r = row(W, k, n, j)
            if not r: continue
            print(f"{W:>5} {k}-of-{n:<3} {r['per_card']:>8} {j:>5} {r['u']:>7} {r['bits']:>4} {r['one_gpu']:>10} {r['farm']:>10}")
    print()
print("Shamir (SLIP-39) for comparison: any k-1 shares reveal 0 bits; brute force = full entropy.")
for W, bits in ((12,128),(24,256)):
    c = 2**bits
    print(f"{W:>5} SLIP-39   -        any   -   {bits:>4} {fmt_time(c/RATE_PER_GPU):>10} {fmt_time(c/(RATE_PER_GPU*GPUS)):>10}")
