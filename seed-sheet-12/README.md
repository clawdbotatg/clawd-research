# seed-sheet-12

Printable 2-of-3 backup sheet for a **12-word** BIP39 seed phrase. Three
cut-apart cards, each holds 8 of the 12 words. Any two cards restore the
phrase, one card alone does not.

Inspired by [Opsek/seed-phrase-sheet](https://github.com/Opsek/seed-phrase-sheet)
(24 words). This is an original layout, not a copy.

| Card | Words |
|------|-------|
| A | 1–8 |
| B | 5–12 |
| C | 1–4, 9–12 |

Files: `index.html` (the sheet, print CSS), `render.mjs` (HTML → PDF),
`seed-sheet-12.pdf` (US Letter landscape, page 1 fronts, page 2 backs),
`analysis.py` (the crack-cost table below).

Print: Letter, landscape, duplex **flip on short edge**, scale 100%. The back
page's column order is mirrored so each card's instructions land behind it.

Rebuild: `node render.mjs` (uses the harness's `playwright-core` + cached
headless Chromium; `PLAYWRIGHT_CORE=` / `CHROMIUM=` override paths).

## How bad is word splitting?

The whole scheme is "print a subset of the words on each card". A card is a
partial leak: whoever holds it knows those words and their positions, and
only has to brute-force the rest. Each BIP39 word is 11 bits. The checksum
(4 bits for 12 words, 8 for 24) is a cheap SHA256 filter, so the expensive
step (PBKDF2 ×2048 + BIP32 + secp256k1) runs on 1/16 or 1/256 of candidates.

Assumptions: attacker holds `j` cards, knows a target address, and runs
1,000,000 full derivations/s per GPU. That is generous to the attacker.
"1000 GPUs" is a serious but not nation-state budget.

General k-of-n construction: for every (k-1)-subset of cards, one group of
words is left off exactly those cards. A holder of `j` cards is missing
`W · C(n-j, k-1-j) / C(n, k-1)` words. `python3 analysis.py` prints this.

### 12 words

| scheme | words per card | attacker holds | must guess | bits | 1 GPU | 1000 GPUs |
|--------|---------------|----------------|-----------|------|-------|-----------|
| 2-of-2 | 6 | 1 | 6 | 62 | 150,000 y | 146 y |
| **2-of-3 (this sheet)** | 8 | 1 | 4 | **40** | **13 d** | **18 min** |
| 2-of-4 | 9 | 1 | 3 | 29 | 9 min | instant |
| 3-of-3 | 4 | 1 | 8 | 84 | 6e11 y | 6e8 y |
| 3-of-3 | 4 | 2 | 4 | 40 | 13 d | 18 min |
| 3-of-4 | 6 | 1 | 6 | 62 | 150,000 y | 146 y |
| 3-of-4 | 6 | 2 | 2 | 18 | instant | instant |
| 4-of-4 | 3 | 1 | 9 | 95 | 1e15 y | 1e12 y |
| 4-of-4 | 3 | 2 | 6 | 62 | 150,000 y | 146 y |
| 4-of-4 | 3 | 3 | 3 | 29 | 9 min | instant |

### 24 words (the original sheet)

| scheme | words per card | attacker holds | must guess | bits | 1 GPU | 1000 GPUs |
|--------|---------------|----------------|-----------|------|-------|-----------|
| 2-of-2 | 12 | 1 | 12 | 124 | 7e23 y | 7e20 y |
| **2-of-3 (Opsek)** | 16 | 1 | 8 | **80** | 4e10 y | 4e7 y |
| 2-of-4 | 18 | 1 | 6 | 58 | 9,100 y | 9 y |
| 3-of-4 | 12 | 1 | 12 | 124 | 7e23 y | 7e20 y |
| 3-of-4 | 12 | 2 | 4 | 36 | 19 h | 1 min |
| 4-of-4 | 6 | 3 | 6 | 58 | 9,100 y | 9 y |

### Real secret sharing (SLIP-39 / Shamir)

| words | shares an attacker holds | bits | 1 GPU | 1000 GPUs |
|-------|-------------------------|------|-------|-----------|
| 12 | any k-1 | 128 | 1e25 y | 1e22 y |
| 24 | any k-1 | 256 | 4e63 y | 4e60 y |

### Takeaways

- **12-word 2-of-3 is cracked in about two weeks on one GPU, 18 minutes on a
  farm.** 40 bits is not a secret. The sheet says so on the back of each card.
- **24-word 2-of-3 is fine in practice.** 80 bits of remaining work is out of
  reach for anyone short of a nation state, and even then only barely. This
  is why the original only works for 24 words.
- Pattern: what matters is the worst case, an attacker holding `k-1` cards.
  Raising `n` with fixed `k` (2-of-4) makes it worse, not better, since each
  card must carry more words. Raising `k` with `n` (3-of-3, 4-of-4) protects
  against one card but leaks fast once an attacker has `k-1`, and you lose
  the phrase if you lose one card.
- Word splitting trades off confidentiality against availability with a bad
  exchange rate. Shamir (SLIP-39) gives you both: any k-1 shares reveal
  nothing at all. Trezor Model T/Safe does SLIP-39 natively, and there are
  offline tools for it.
- If you still want paper 2-of-3 for 12 words: add a BIP39 passphrase (the
  cards then protect nothing without it), or move to 24 words.
