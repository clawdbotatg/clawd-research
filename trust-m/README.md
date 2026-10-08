# OPTIGA Trust M deep dive (2026-10-08)

Infineon's I2C secure element, in clawd-trust-m, picowallet, wedgie firmware, wedgie-safe, hilo, clawd-crops.

- [SPECS.md](SPECS.md): variants, crypto, speed, slots, certs, supply
- [SECURITY.md](SECURITY.md): EUCLEAK, certification, threat model, other chips compared
- [ECOSYSTEM.md](ECOSYSTEM.md): libraries, boards, who else uses it
- [OUR-USAGE.md](OUR-USAGE.md): review of our code, risks, to-do list
- [V1-DERIVEKEY-TEST.md](V1-DERIVEKEY-TEST.md): tested on our chip: locked secret + one-time key maker, 1.8 s per call
- [AI-VS-ECC.md](AI-VS-ECC.md): the AI-breaks-ECDSA scare (Drake, Green, Vitalik, skeptics); no actual attack exists
- [PQ-WALLET-LANDSCAPE.md](PQ-WALLET-LANDSCAPE.md): Ethereum PQ status, schemes, gas, recovery
- [PQ-WALLET-DESIGN.md](PQ-WALLET-DESIGN.md): **the plan**: Trust M V1 + Pico + WOTS Safe owner

## Short version

- **No post-quantum. No secp256k1. No Ed25519.** Signs ECDSA (P-256/384, V3 adds P-521 + Brainpool) and RSA-2048.
- Beyond signing: ECDH, signature verify, SHA-256, TRNG, TLS-PRF. V3 adds AES (ECB/CBC/CMAC), HMAC-SHA256/384/512, HKDF.
- PQ angle: chip can't sign PQ, but a V3 can hold the seed for host-side hash signatures (HMAC-derived WOTS/LMS keys, monotonic counter to stop index reuse, PIN gate). EthereumPhone PQ1 does this with SPHINCS+.
- **V1 (our Adafruit 4351 boards, CA 101) is end of life.** Buy V3: `SLS32AIA010MK…` / `…ML…`. V3 certs are P-384 (CA 300/306), so our on-chain attest contract can't verify them as written.
- **EUCLEAK** reaches Trust M ECDSA: physical access, EM probe, ~40 signatures, ~€10k gear. No field fix. Require a button/PIN per signature.
- Throttle: ~1 private-key op per 5 s sustained after ~130 in a burst.
- Our biggest risks: every key is "execute: always" (anyone on the bus can sign), no Shielded Connection, picowallet + wedgie-safe both use slot E0F1, picowallet's lock code would freeze the open rule forever.

## Tested 2026-10-08 on a V1 chip (wedgie, CA 101)

V1 can hold a secret it won't reveal and turn it into one-time keys:
- Data object type PRESSEC (E8=21), use rule D3=ALW, then read rule D1=NEV.
- Read now fails (0x07). DeriveKey (0x34, TLS1.2 PRF SHA-256, export tag 07) still works.
- Output matched host TLS-PRF exactly, for two different indexes.
- Gotcha: without D3 set, DeriveKey fails with 0x07 (default use rule is never).
- Slot used: F1DA, restored to zero after (now has explicit D3=FF).
