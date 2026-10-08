# OPTIGA Trust M deep dive (2026-10-08)

Infineon's I2C secure element, in clawd-trust-m, picowallet, wedgie firmware, wedgie-safe, hilo, clawd-crops.

- [SPECS.md](SPECS.md): variants, crypto, speed, slots, certs, supply
- [SECURITY.md](SECURITY.md): EUCLEAK, certification, threat model, other chips compared
- [ECOSYSTEM.md](ECOSYSTEM.md): libraries, boards, who else uses it
- [OUR-USAGE.md](OUR-USAGE.md): review of our code, risks, to-do list

## Short version

- **No post-quantum. No secp256k1. No Ed25519.** Signs ECDSA (P-256/384, V3 adds P-521 + Brainpool) and RSA-2048.
- Beyond signing: ECDH, signature verify, SHA-256, TRNG, TLS-PRF. V3 adds AES (ECB/CBC/CMAC), HMAC-SHA256/384/512, HKDF.
- PQ angle: chip can't sign PQ, but a V3 can hold the seed for host-side hash signatures (HMAC-derived WOTS/LMS keys, monotonic counter to stop index reuse, PIN gate). EthereumPhone PQ1 does this with SPHINCS+.
- **V1 (our Adafruit 4351 boards, CA 101) is end of life.** Buy V3: `SLS32AIA010MK…` / `…ML…`. V3 certs are P-384 (CA 300/306), so our on-chain attest contract can't verify them as written.
- **EUCLEAK** reaches Trust M ECDSA: physical access, EM probe, ~40 signatures, ~€10k gear. No field fix. Require a button/PIN per signature.
- Throttle: ~1 private-key op per 5 s sustained after ~130 in a burst.
- Our biggest risks: every key is "execute: always" (anyone on the bus can sign), no Shielded Connection, picowallet + wedgie-safe both use slot E0F1, picowallet's lock code would freeze the open rule forever.
