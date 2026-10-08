# How we use the OPTIGA Trust M: review

Date: 2026-10-08. Read only: no source project was changed.

Reference used: Infineon/optiga-trust-m main `03a3ebe` (v5.8.3), its develop and support/m1 branches
for the certificates, and the Solution Reference Manual (SRM) in Infineon/optiga-trust-m-overview `a45b86b`.

Our chip: an Adafruit 4351, firmware build 0809. That is a **Trust M V1** (wedgie-dev
`public/trustm.md:52-55`). That matters: V1 has no on-chip PIN (`Auto` / AUTOREF is V3 only).

## Short version

- Six projects talk to the chip. Two drivers do it: `trustm.py` (four copies, almost the same) and wedgie's
  `optiga.py`.
- On a clean bus the wire protocol is right: CRC, frame numbers, NACK retries, guard time and APDU layout
  all match Infineon.
- Error recovery is thin. The drivers never send a NAK or RESYNC, and they don't check ACK numbers or
  duplicate frames. `trustm.py` has no frame chaining and no last-error read.
- The big risks are in how the chip is set up, not in the driver:
  1. Every key we use is set to **Execute: always**. Any code on the Pico, or a clip on the I2C wires, can sign.
  2. There is no Shielded Connection.
  3. The Safe key (wedgie-safe) is never locked.
  4. The factory key E0F0 signs any 32-byte hash a relay sends.
  5. picowallet's lock would freeze "Execute: always" forever.
- Contract: TrustMAttest is sound for CA 101. The README's "swap in the CA 300 key" advice is wrong:
  CA 300 and CA 306 are **P-384** keys. `isChipSignature` has no replay protection and accepts both s and N−s.

## 1. Inventory

| Project (path) | What for | Slots / OIDs | Commands |
|---|---|---|---|
| clawd-trust-m (`~/clawd/clawd-trust-m`, **stale clone**, 2 commits; current is `~/clawd/clawd-harness/projects/clawd-trust-m` @1fd53ee) | Prove on chain that a real Trust M signed a hash. The current version also runs a network agent: the Pico polls a relay, shows the text and hash, and signs on the A button. | E0E0 cert read, E0F0 CalcSign, E0C2 UID | OpenApplication 0x70, GetDataObject 0x01 (data and metadata), CalcSign 0x31/0x11, GetRandom 0x0C |
| clawd-crops (`~/clawd/clawd-harness/projects/clawd-crops`) | Each attested chip mints 5 CROPS every 5 h (`Crops.sol`). It also keeps the raw "sign" mode. | E0F0 | same as above |
| picowallet (`~/picowallet`), TrustMSigner is **uncommitted** (`git status`: signer.py and trustm.py modified) | Vault key for the smart-account wallet | E0F1 key, F1D1 holds its public key, E0C2 UID | above plus GenKeyPair 0x38/0x03 (usage 0x10), SetDataObject 0x02/0x40 (write F1D1), SetDataObject 0x02/0x01 (metadata `C0=07, D0=FF` on both, `signer.py:118`) |
| picowallet `factory/probe.py:122-160` | Factory test: is a Trust M there, and what is its UID | E0C2 | Hard-coded datasheet frames: OpenApplication, then GetDataObject |
| picowallet `app/packages/foundry/contracts/TrustMAttest.sol` | A copy of the old constructor version. **Not wired to anything.** | none | none |
| wedgie firmware (`~/clawd/clawd-harness/projects/wedgie-dev/firmware/`) | `wedgie.py:165-223` runs the chip check: 2× GetRandom, read E0E0, E0F0 signs sha256(random). `wedgie.py:226-299` is `rand()`, the TRNG source for apps. `optiga.py` is the full API for apps. | E0F0, E0E0, everything in `optiga.py:19-40` | `optiga.py` covers the lot: chaining, last error, GenKeyPair (including export), sign and verify, ECDH, derive, AES, counters, hibernate, set_metadata |
| wedgie-safe (`~/clawd/wedgie-safe`, **stale**: local 20cb4b1, remote 6b81635; key code unchanged) | Safe owner key through Safe's WebAuthn passkey signer | E0F1 (`KEY2`) | `optiga.Chip().genkey(KEY2)` and `.sign(KEY2, …)`, at `safe.py:222-239` (remote: 437, 470) |
| wedgie-starter `hilo/hilo.py:14,65` | Fair shuffle from the chip's TRNG | none | GetRandom, through `wedgie.rand_below` |

Docs only: picowallet `CRYPTO-CHIPS.md`, `DIY-WALLET-PARTS.md:43,52,65-69,177-189`, and `pcb/PARTS.md:23` (Trust M is not on the PCB).

**Slot collision.** picowallet and wedgie-safe both use **E0F1**:
- If one breakout moves between them, wedgie's "make key" destroys a picowallet vault key that isn't locked yet.
- If picowallet already locked the slot, wedgie's genkey fails instead.
- clawd-trust-m `SKILL.md:24-25` calls E0F1–E0F3 "free".

No secrets found in any of this code. The 64-hex strings are Safe typehashes, the curve order, and the
public cert and signature values in the tests. `picowallet/firmware/secrets.py` is gitignored.

## 2. Protocol review: our drivers vs Infineon

Files: `~/clawd/clawd-trust-m/firmware/trustm.py` (T). The picowallet copy is the same plus
genkey/write/set_metadata (`picowallet/firmware/trustm.py:178-201`). `wedgie-dev/firmware/optiga.py` is (O).

**Right:**
- **CRC.** CRC-16, poly 0x8408 (reflected CCITT), init 0, high byte first, over FCTR + LEN + payload (T:114-120). Matches `ifx_i2c_data_link_layer.c:224-248, 302-304`, and the datasheet sample frames check out.
- **Frame numbers.** First frame is FRNR 0, ACKNR 3 (T:128-129). The reference starts both counters at 3 (DL L181-182). The ACKNR we send is the last received FRNR (T:141). Our ACK control frame is `0x80|acknr` (T:142).
- **NACK retry.** 200 tries at 1 ms (T:26-45) = `PL_POLLING_MAX_CNT`. Guard time: we wait 100 µs, the reference 50 µs.
- **Response read.** Read I2C_STATE, test RESP_RDY (0x40), read DATA for the given length, poll every 5 ms (T:62-76). Same as the reference (PL L495-530).
- **Soft reset.** Write 0x88, then wait 25 ms (T:57-59). That is longer than tSTARTUP (15 ms).
- **APDU layout.** Matches `optiga_cmd.c`: OpenApplication AID, GetDataObject offset/len, CalcSign tags 01/03, GenKeyPair tags 01/02, response tag 02, usage 0x10 = Sign. The response header (Sta, UnDef, Len) is parsed right.
- **Chaining in O.** PCTR 0x01/0x02/0x04 and 271-byte fragments (O:73, 129-152) match the transport layer (TL L33-40, L89).
- **Errors in O.** O reads F1C2 on an error (O:162-166), as the reference does (cmd L1777-1868).

**Missing or weak:**
1. **No NAK, no resend, no RESYNC (T and O).** The reference does all three:
   - On a bad FCS it NAKs (DL L429-438).
   - It resends up to 3× (`DL_TRANS_REPEAT`), then sends RESYNC 0xC0 (DL L311-336).
   - We raise an error and leave the session dead (T:139-140, O:145-146).
   - Callers mostly open a fresh `Session()`/`Chip()` per job, which soft-resets. So the cost is failed calls, not wrong data. But it isn't robust.
2. **The receive path checks only the CRC.** `_recv` (T:137-144, O:141-152) does not check:
   - that it got a data frame and not a control frame (bit 7)
   - that the chip's ACKNR acknowledges our frame
   - a repeated FRNR (the chip resends when our ACK is lost; we would take the duplicate as the next answer)
   - that LEN matches the bytes read

   `read_frame` drops any 5-byte frame with LEN 0 (T:79-85), so a NAK or RESYNC from the chip is dropped silently and we time out.
3. **The chained send in O doesn't check the chip's reply (O:135-139).** It waits for any control frame. It doesn't check ACK vs NAK or the CRC.
4. **No chaining in T.** T ignores PCTR on receive and always sends PCTR 0. Any answer longer than one frame comes back garbled with no error. `get_all(step=200)` avoids this today (T:178-184). A bare `get(oid)` on a big object would not.
5. **No last-error read in T.** On Sta≠0 it prints `r[4:]`, which is empty (T:149-150). It should read F1C2.
6. **Command bytes are sent without the 0x80 bit** (T and O). The reference ORs in 0x80 ("clear last error") on every command except the F1C2 read. Harmless today, but F1C2 can then report an older error.
7. **DATA_REG_LEN (0x81) is never negotiated.** O assumes 277-byte frames (O:73). That is the chip's default, so it works, but the reference writes and reads back the value (PL L434-456).
8. **Fixed 1 s wait for a response (T:62).** Fine for ECC. An RSA genkey would time out. O uses 60 s.
9. **A soft reset kills any other session on the bus.** Every `Session()` resets the chip. wedgie's `rand()` keeps a Session open (`wedgie.py:231-274`) and recovers by re-finding it. picowallet runs an ATECC on the same bus and the host tool has to stop it (projects/clawd-trust-m `tools/chip.py` `run`).
10. **No length checks.** No limit on `random(n)` (the SRM allows 8..256), and none on the CalcSign reply (T:166-173). A bad reply gives an IndexError, not a clean error.
11. **Four copies of T plus O, slowly drifting apart.** Keep one driver.
12. **No reset pin.** Cold or warm reset needs the RST line; the breakout wiring only allows a soft reset. The chip can't be recovered from a hung state without a power cycle.

## 3. Risks

**R1 (high): every key we use can be run by anyone who reaches the bus.**
- What the defaults are:
  - E0F0's default metadata is `Change NEV, Execute ALW`, usage Auth (SRM dump `200fc00101d001ffd30100e00103e10101`).
  - Our E0F1 reads `D3=00`, i.e. Execute ALW (`wedgie-dev/public/trustm.md:217`).
  - CalcSign accepts Auth-usage keys.
- What that means:
  - Malicious code on the Pico (no secure boot on the RP2040), or a clip on SDA/SCL, can sign with any slot. No button, no PIN.
  - picowallet's vault key is "the only thing that can spend the vault" (`picowallet/README.md:224`). A stolen picowallet is a signing oracle, limited only by the vault's own rules.
  - wedgie-dev's own `docs/PLAN-TRUST.md:19-24` already admits this for wedgies.
- **Can E0F0 be used freely? Yes, and it can never be fenced.** Its metadata is frozen (Change NEV), so nobody can add a gate. Any "the chip signed X" claim from E0F0 only proves that someone with access to that chip asked for it.

**R2 (high): picowallet's lock would make R1 permanent.**
- `LOCK = C0 01 07, D0 01 FF` (`picowallet/firmware/signer.py:118`) raises LcsO to operational.
- Once LcsO is operational, D3 (Execute) can never change (SRM Table 49).
- So locking E0F1 as written fixes "Execute: always" forever: no Shielded Connection gate can be added later.
- Fix: set `D3` to `Conf(E140)` (`D3 03 20 E1 40`) in the same metadata write, **before** C0=07. First provision and lock E0F1 itself, with its Read set to NEV or Conf.

**R3 (high): no Shielded Connection.**
- E140 is unused (`wedgie-dev/public/trustm.md:77`). Neither driver has the presentation layer (PCTR bit 0x08, AES-128-CCM, keys from TLS-PRF(secret, "Platform Binding", random): PresL L285-351, L450-600).
- So someone on the wire can:
  - read and send any command
  - fake replies: random bytes, metadata that says "locked" (`signer.py:140-142`), public keys
  - swap the chip
- Chip swap in practice:
  - picowallet reads its own public key back from F1D1 on the chip (`signer.py:126-131`). A swapped chip supplies the swapper's key and the device shows it.
  - wedgie-safe caches the key in flash. That is better, but a swapped chip then signs nothing valid. That is denial of service, not theft.
- Shielded Connection only helps if the host can keep the binding secret. On an RP2040 it can't: flash can be read out.
- The only real fix is wedgie's phase 4 (`PLAN-TRUST.md:74-93`): RP2350 OTP holds the secret and only signed firmware can read it. That plus R2's `Conf(E140)` gate is the whole fix.

**R4 (high, wedgie-safe): the Safe key is never locked.**
- `make_key` runs GenKeyPair on E0F1 and stops (`safe.py:222-231`). E0F1 keeps `Change: LcsO<op`.
- Any app, any host after a "full control" yes, or the user pressing A after the key file is lost (`safe.py:396-400`) can re-key the slot.
- That destroys the Safe owner key for good. If the wedgie is the only owner, the Safe is locked out.
- Also: wedgie-safe never checks whether the slot already holds a key. See the E0F1 collision above.

**R5 (medium-high): E0F0 signs any hash a relay sends.**
- Where: projects/clawd-trust-m `firmware/agent.py:86` → `ui.py:143-161`, and clawd-crops `firmware/agent.py:158-160`.
- The relay picks the 32 bytes. The screen shows "relay/host-provided text" and the hex hash (`ui.py:83-93`). No person can check a hash by eye.
- Attack: a hostile relay sends a Crops harvest digest with `to` = the attacker, labeled "hello world".
  - Crops' domain separation (`Crops.sol:54-56`) doesn't help, because the device's raw mode signs it anyway.
  - The device's harvest mode rebuilds the digest itself (crops `agent.py:7-8, 129-131, 174-177`). The raw "sign" mode bypasses that.
- The same holds for any future contract that trusts `isChipSignature`.

**R6 (medium): keys in E0F1–E0F3 can't be attested.**
- TrustMAttest only covers E0F0 (the factory cert).
- picowallet's and wedgie's chip-made keys have no proof they live in a chip.
- Signing them with E0F0 proves nothing extra: the host can ask E0F0 to sign any public key (R1).
- Don't claim "proved in hardware" for those keys.

**R7 (medium): the wedgie chip check can be replayed.**
- The device picks the message (`wedgie.py:180`) and signs sha256 of it (`wedgie.py:214`). The site sends no challenge (`wedgie-dev/src/serial/chipcheck.ts:1-5`).
- Fake firmware, or a fake device, can replay one recorded (cert, msg, sig) set and pass.
- Fix: the site sends a nonce.

**R8 (medium): no backup story.**
- Chip-made keys can't be exported, which is the point.
- Recovery has to be on chain:
  - picowallet: the vault's delayed recovery wallet (`README.md:224-225`). OK.
  - wedgie-safe: depends on the Safe having other owners. Nothing in the app makes you add one.
- Public keys:
  - wedgie-safe keeps its public key only in flash (`/saves/safe/key`). If that's wiped, the key is still in the chip but we no longer know its address; we'd recover it from the passkey signer contract or a signature.
  - picowallet keeps it in F1D1, which is unprotected until the lock.
- `optiga.genkey(slot=None)` exports a private key (`optiga.py:265-272`). That's fine for sessions, but a trap if an app uses it for money.

**R9 (low): Security Event Counter.**
- Every private-key use counts as an event. The chip allows about one protected operation per 5 s, with 5 credits for bursts. Throttling starts at SEC=128 (SRM; `wedgie-dev/public/trustm.md:56-59`).
- Human-paced signing is fine.
- A relay that floods sign requests, or a loop, slows the chip to seconds per call. Our 1 s timeout (T:62) then turns that into errors.
- On V1 there is no PIN, so SEC gives no brute-force protection we can use.
- hilo's GetRandom doesn't count.

**R10 (low): drift and stale docs.**
- `~/clawd/clawd-trust-m` and `~/clawd/wedgie-safe` are behind their remotes. The old README names the old contract `0xC868…AB99`; the current one is `0xA2b5…E197`. Attestations don't carry over between them.
- picowallet `CRYPTO-CHIPS.md:50` says the wallet doesn't use the Trust M (now it does, uncommitted). `secrets.example.py:17-21` still talks only about the ATECC.

### Contract: TrustMAttest.sol (`~/clawd/clawd-trust-m/packages/foundry/contracts/TrustMAttest.sol`)

- **Pinned CA.** Only CA 101 (`DeployTrustMAttest.s.sol`; the current repo hard-codes it).
  - I checked the key against Infineon's CA 101 cert: X=`9733…d2d0`, Y=`1ea2…408b`. **It matches.**
  - CA 101 is signed by the original "Infineon OPTIGA(TM) ECC Root CA". Valid 2018-09-01 to 2043-07-25.
  - Trusting the intermediate directly is fine.
- **CA 300 / CA 306 can't be added the way the README says.**
  - README:76-80 and SKILL.md:43 say "put that CA's public key in the deploy script".
  - Both are P-384 keys whose own certs are signed with ecdsa-with-SHA512 (checked with openssl on `wedgie-dev/public/device/infineon/ca300.crt`, `ca306.crt`).
  - P-384 has no precompile, and the contract only does P-256 with sha256.
  - So newer chips can't be attested at all without a P-384 verifier in Solidity (expensive).
  - wedgie's site, by contrast, trusts ca101, ca300 and ca306 (`chipcheck.ts:52`).
- **Cert parsing by offsets** (L57-63) is sound:
  - The CA signature covers exactly the TBS range the caller gives.
  - The key must sit right after the fixed P-256 SPKI header, inside that range.
  - Overflow on huge offsets reverts (checked math).
- **Not checked:** validity dates, keyUsage, issuer name, signature algorithm OID. All low risk while the only CA is CA 101 and every cert it issues is a device cert.
- **Malleability.**
  - `isChipSignature` folds s to low-s (L71-77), so both (r, s) and (r, N−s) pass.
  - Any consumer that uses signature bytes as a replay key can be double-spent.
  - Crops uses a nonce, so it's safe.
  - Either reject high s in `isChipSignature` (normalize off chain, as `chip.py` already does) or document it loudly.
- **Replay.**
  - `isChipSignature(x, y, hash, r, s)` binds no domain, chain, contract or nonce. It is a raw "chip signed this hash" check.
  - Safe only for consumers that build domain-separated, single-use digests (Crops does).
  - R5 means the device side has to refuse raw hashes too.
- **No ownership.** `attest` is open to anyone, and certs are public. Attestation says "real chip", never "your chip" (the README says so too, L29-30).

## 4. To-do, in order

**Before any of this holds value**
1. **picowallet lock.**
   - Don't run `lock_config` as written (`signer.py:118`).
   - Lock with `D3 = Conf(E140)` in the same write as `C0=07, D0=FF`, after provisioning E140 with Read NEV.
   - If shielded mode isn't built yet, wait. Locking now freezes "Execute: always" forever.
2. **wedgie-safe.**
   - Lock E0F1 after `make_key` (`C0=07, D0=FF`, plus D3 as in item 1 once ready).
   - Refuse genkey on a slot that already has a key, and say so on the screen.
   - Push users to add a second Safe owner.
3. **Pick slots per project.** For example picowallet E0F2, wedgie-safe E0F1. Note it in clawd-trust-m `SKILL.md:24-25`.
4. **Stop raw-hash signing with E0F0.**
   - In projects/clawd-trust-m `agent.py` and clawd-crops `agent.py:158`, sign only digests the device builds from text it shows, with a fixed prefix (for example keccak256("\x19Trust M signed message:\n" ‖ len ‖ text)).
   - Change the page and contract use to match.

**Next**
5. **wedgie chip check:** the site sends a 32-byte nonce, and the device signs sha256("wedgie chip check" ‖ nonce).
6. **Shielded Connection in the driver.**
   - Presentation layer: Hello / Finished handshake, TLS-PRF-SHA256 key derivation, AES-128-CCM with an 8-byte tag, PCTR 0x08, SCTR 0x20|prot.
   - Then move the binding secret into RP2350 OTP (wedgie phase 4).
   - Check first that our V1 build does the handshake.
7. **Driver hardening** (one shared driver, retire the copies):
   - Check FTYPE, the ACKNR we get back, repeated FRNR, and LEN.
   - NAK a bad FCS. Resend up to 3×, then RESYNC (0xC0).
   - Read F1C2 on any error.
   - Make T fail loudly on a chained answer, or use O's chaining.
   - Set the 0x80 bit on command bytes.
   - Range-check `random(n)` to 8..256.
   - Use a per-command timeout (longer for RSA).
8. **TrustMAttest docs and contract.**
   - Fix README:76-80: CA 300/306 are P-384 and can't be dropped in.
   - Next deploy: reject high s in `isChipSignature`, or name the malleability in NatSpec. Add a NatSpec warning that it has no domain and no replay protection.

**Housekeeping**
9. Pull `~/clawd/clawd-trust-m` and `~/clawd/wedgie-safe` (both behind). Commit or drop picowallet's uncommitted TrustMSigner. Fix `CRYPTO-CHIPS.md:50` and `secrets.example.py`.
10. Delete picowallet's unused `TrustMAttest.sol` copy, or point it at the deployed one.
11. Show SEC (E0C5) in the status and chip-check output, and back off when it is high. Don't let a relay queue run sign requests back to back.
12. On a Trust M V3 board, look at `Auto(AUTOREF)` with a PIN-derived HMAC secret as an on-chip PIN gate. Not possible on our V1 chips.
