# OPTIGA Trust M: security track record

Researched 2026-10-08. Focus: Trust M as the signing key for a crypto wallet
(P-256 key as a Safe passkey-style signer, factory cert used for on-chain
attestation).

Tags: **[confirmed]** = a primary source says it. **[inferred]** = my reading
of sources, not stated anywhere. **[unconfirmed]** = could not verify.

## TL;DR

- Trust M **is affected by EUCLEAK**. NinjaLab measured the same leaky ECDSA
  nonce inversion on a Trust M and Infineon then patched its crypto library
  instead of denying it. [confirmed] ([paper §6.2, p.70](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf))
- Trust M firmware **cannot be updated in the field**. Chips already on boards
  stay vulnerable. [confirmed for "OS locked"; inferred for "no fix possible"]
  ([datasheet §1.3](https://www.infineon.com/dgdl/Infineon-OPTIGA_Trust_M-DataSheet-v03_70-EN.pdf?fileId=8ac78c8c818eceac01819539e0ed53e1), [paper §7.1](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf))
- Infineon has **no public Trust M advisory**. It did ship an ECDSA side-channel
  fix for its TPMs (Dec 2024). Whether newer Trust M part numbers carry the fix
  is **unconfirmed**. ([Infineon TPM update page](https://www.infineon.com/product-information/tpm-update))
- EUCLEAK needs: the device in hand, the case opened, an EM probe over the chip,
  the chip made to sign ~40 times with the target key, about 10 k€ of gear, and
  hours of offline work. Not cheap, not remote.
- The bigger everyday risks are **how it is wired**: default `E0F0` lets anyone
  on the I2C bus sign, the Shielded Connection is only as strong as the host
  MCU that holds its secret, and a hacked host can just ask the chip to sign.
- **No backup**: keys made inside the chip can't be read out. Chip dies, key is
  gone. Plan the Safe around that.

## 1. EUCLEAK (NinjaLab, Sept 2024)

**What it is.** Infineon's crypto library computes the ECDSA nonce inverse with
a non-constant-time Extended Euclidean Algorithm. The nonce was masked, but only
with a 32-bit mask. EM traces of that inversion leak enough nonce bits to
recover the private key with lattice math. The bug sat in Infineon chips ~14
years and ~80 CC evaluations at AVA_VAN.4/5. [confirmed]
([NinjaLab page](https://ninjalab.io/eucleak/), [paper p.9](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf), [ePrint 2024/1380](https://eprint.iacr.org/2024/1380))

**CVE.** CVE-2024-45678. NVD text names YubiKey 5 (<5.7) and YubiHSM 2
(<2.4.0) and says "other uses of an Infineon cryptographic library may also be
affected." No Trust M-specific CVE exists. NVD keyword search for "OPTIGA"
returns zero CVEs. [confirmed] ([NVD API](https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-45678))

### Is Trust M affected?

- NinjaLab ran ECDSA sign and verify on a Trust M (PSoC 62S2 eval kit,
  CY8CEVAL-062S2) and saw the same inversion pattern as on the broken SLE78.
  [confirmed] ([paper §6.2](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf))
- They did **not** run the full key recovery on Trust M. They said they "cannot
  fully conclude" because Infineon might have used a bigger mask. Infineon
  "neither confirmed nor denied" and then shipped a fix that grows the mask to
  full nonce size. From that, NinjaLab concluded "the Optiga Trust M is
  vulnerable." [confirmed that this is NinjaLab's reasoning] ([paper p.70](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf))
- Some news coverage said NinjaLab only "suspected" Trust M. The paper itself
  calls it vulnerable. ([Help Net Security](https://www.helpnetsecurity.com/2024/09/04/yubico-security-keys-vulnerability/), [BleepingComputer](https://www.bleepingcomputer.com/news/security/new-eucleak-attack-lets-threat-actors-clone-yubikey-fido-keys/))
- Trezor publicly said EUCLEAK affects the Trust M in Safe 3 / Safe 5, and that
  seeds are not at risk (they use Trust M for HMAC/PIN, not ECDSA on the seed).
  ([Trezor on X](https://x.com/Trezor/status/1831256973242716623), [Trezor Optiga config](https://docs.trezor.io/trezor-firmware/core/misc/optiga.html))
- Which versions: NinjaLab says "any existing version" of the Infineon
  cryptolib as of 2024. That covers Trust M V1 and V3 as shipped then.
  [confirmed for "all versions known in 2024"] ([NinjaLab page](https://ninjalab.io/eucleak/))

### Did Infineon fix it?

- Infineon told NinjaLab on 2024-07-26 it had implemented and tested a patch
  (full-size multiplicative mask). [confirmed] ([paper p.10, §7.4.1](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf))
- BSI recertified the Trust M chip family (BSI-DSZ-CC-0961-V7-2024,
  2024-11-11) adding a new asymmetric crypto library **ACL v2.09.002**, manual
  dated 2024-06-27. Timing fits the EUCLEAK patch. **Whether that is the fix,
  and whether Trust M firmware uses it, is unconfirmed.** [inferred]
  ([cert report](https://www.commoncriteriaportal.org/files/epfiles/0961V7a_pdf.pdf))
- For TPMs Infineon is explicit: Dec 2024 certified firmware where "the crypto
  library function used for ECDSA has been adapted for enhanced protection
  against advanced side channel attacks." TPMs are field-updatable. [confirmed]
  ([Infineon TPM update](https://www.infineon.com/product-information/tpm-update))
- For Trust M: no advisory, no PCN found. Infineon's KB lists new active part
  suffixes (SLS32AIA010MK…XTMB2, SLS32AIA010ML…XTMC1; old XTMA2 now NRND) with
  "latest firmware." It does not say why. Whether they include the EUCLEAK fix
  is **unconfirmed**. Ask Infineon / FAE, and read chip info (`0xE0C2`) on our
  parts. ([Infineon KB, via search snippet; page blocks bots](https://community.infineon.com/t5/Knowledge-Base-Articles/OPTIGA-Trust-M-Latest-OPN-status-and-active-variants/ta-p/1195051))

### Can Trust M firmware be updated in the field?

No. Trust M "comes with preprogrammed OS/Application code locked."
"Protected update" only updates data objects, keys and metadata, not the OS.
[confirmed] ([datasheet §1.3](https://www.infineon.com/dgdl/Infineon-OPTIGA_Trust_M-DataSheet-v03_70-EN.pdf?fileId=8ac78c8c818eceac01819539e0ed53e1), [overview repo](https://github.com/Infineon/optiga-trust-m-overview))
NinjaLab: "in the vast majority of cases, the security microcontrollers
cryptolib cannot be upgraded on the field." ([paper §7.1](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf))
The only fix is new silicon on new boards.

### What the attack needs

All from the [paper](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf) unless noted.

| Need | Detail |
|---|---|
| Physical access | Yes. Open the device, put an EM probe right over the chip package. |
| Chip must sign | Yes, with the **target key**, many times. YubiKey attack: 200 sigs for 5 recoveries, ~40 sigs average. Sig-verify traces were only used to study the leak. |
| Time with device | "few minutes" of capture; whole online phase "less than an hour" incl. opening. |
| Offline | ~24 h for them; "less than an hour" with more engineering. |
| Gear | ~10 k€ setup (PicoScope 6424E, Langer probe, microscope, PC). They used a ~30 k€ LeCroy too but think the PicoScope is enough. Can be "mobile… a laptop which fit in a case or a backpack." |
| Skill | High: custom software, side-channel and lattice expertise. ([Yubico YSA-2024-03](https://www.yubico.com/support/security-advisories/ysa-2024-03/)) |
| Per key | Capture and offline work must be redone for each key in the chip. |

Trust M slows this down a little. Its Security Monitor allows about one
private-key use per 5 s by default (configurable, can be set to 0 = off).
40 signatures is still only a few minutes. [confirmed numbers; inferred effect]
([SRM, Security Monitor](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md))

### What it means for a stolen device

- The attacker must get the chip to sign with **our** key ~40 times while
  probing it. [inferred from paper]
- If the key's execute rule is `ALW` (the factory default for `E0F0`), they
  just wire to I2C and send `CalcSign`. No PIN involved. [confirmed default;
  inferred attack path] ([SRM, key object table](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md))
- If execute is locked to `Conf(E140)` (Shielded Connection), they first need
  the platform binding secret from the host MCU. On an STM32F4-class MCU that
  has been done by voltage glitching (Donjon vs Trezor Safe 3, 2025). [inferred]
  ([The Block](https://www.theblock.co/post/346018/trezor-discloses-vulnerability-safe-3-crypto-wallet-rival-ledger), [Guillemet thread](https://x.com/P3b7_/status/1899863743036874795))
- If the host only lets the chip sign after a user PIN or on-screen confirm,
  and the binding secret can't be pulled, the attacker can't feed it 40 signs.
  That is the real defense against EUCLEAK on old chips. [inferred]
- Result if it works: a full copy of the private key. For a Safe signer that
  means the attacker signs as that owner forever, until the owner is removed.
  Theft is silent if the device is returned. [inferred]

## 2. ROCA (CVE-2017-15361)

- ROCA was a bad RSA **key generation** in Infineon RSA library v1.02.013
  (TPMs, YubiKey 4, ID cards). Public key alone revealed the private key.
  ([NVD](https://nvd.nist.gov/vuln/detail/CVE-2017-15361), [CRoCS ROCA](https://crocs.fi.muni.cz/public/papers/rsa_ccs17))
- The Trust M chip family (CC 0961) shipped with asymmetric libraries v2.06.003
  and later, never v1.02.013. [confirmed]
  ([0961 2017 report](https://www.commoncriteriaportal.org/files/epfiles/0961a_pdf.pdf), [0961-V2 report](https://www.commoncriteriaportal.org/files/epfiles/0961V2a_pdf.pdf))
- No source says Trust M was affected. [inferred: not affected]
- Irrelevant for us anyway: our keys are P-256, not RSA.
- Side note: in the 2024 recert, BSI **removed RSA key generation** from the
  certified scope of the older libraries (v2.06–v2.08), leaving it certified
  only in v2.09.002. No reason given. [confirmed fact, reason unknown]
  ([0961-V7 report p.~19](https://www.commoncriteriaportal.org/files/epfiles/0961V7a_pdf.pdf))

## 3. Other CVEs, advisories, papers

- **NVD:** zero CVEs mention OPTIGA. Infineon-wide: ROCA and EUCLEAK are the
  only crypto-chip ones. [confirmed] ([NVD search](https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=OPTIGA))
- **Infineon PSIRT:** no Trust M bulletin found. ([Infineon cybersecurity](https://www.infineon.com/about/company/cybersecurity))
- **Host library (Infineon/optiga-trust-m):** v5.8.3 (2026-09-14) added length
  checks on the `CalcSign` response and fixed a buffer overflow from an
  unvalidated wire length (in examples). So a malicious chip or bus MITM could
  feed bad lengths to older host code. Update to ≥5.8.3. No GHSA filed.
  [confirmed] ([CHANGELOG](https://github.com/Infineon/optiga-trust-m/blob/main/CHANGELOG.md))
- **TPM-Fail (2019):** timing leak in ECDSA nonce handling on ST33 TPM and
  Intel fTPM. **Not Infineon.** ([arXiv 1911.05673](https://arxiv.org/pdf/1911.05673))
- **Minerva (2019):** nonce bit-length timing leak on Athena IDProtect
  (Atmel/Inside Secure AT90SC). **Not Infineon.** ([Minerva](https://minerva.crocs.fi.muni.cz/))
- **Fault injection / laser / probing on Trust M:** no public paper found.
  [unconfirmed — absence of evidence]
- **Trezor Safe 3 (Donjon, Mar 2025):** attack hit the STM32F429 next to the
  Trust M, not the Trust M. It read MCU flash and bypassed supply-chain checks.
  ([The Block](https://www.theblock.co/post/346018/trezor-discloses-vulnerability-safe-3-crypto-wallet-rival-ledger))
- **Trezor 2019 NDA'd SE issue:** Trezor says it once tested an unnamed popular
  SE that fell short and couldn't disclose why. Not named as Optiga.
  ([Trezor TROPIC01 post](https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/tropic-01-chip-vulnerability-disclosure-what-happened))

## 4. Common Criteria

| Item | Value |
|---|---|
| Certificate | **BSI-DSZ-CC-0961-V7-2024**, issued 2024-11-11, valid to 2027-03-23 ([BSI](https://www.bsi.bund.de/SharedDocs/Zertifikate_CC/CC/SmartCards_IC_Cryptolib/0961.html)) |
| Trust M hardware ID | IFX_CCI_00000Bh (65 nm, design step G13) ([datasheet](https://www.infineon.com/dgdl/Infineon-OPTIGA_Trust_M-DataSheet-v03_70-EN.pdf?fileId=8ac78c8c818eceac01819539e0ed53e1)) |
| Level | EAL6 augmented by ALC_FLR.1. EAL6 includes AVA_VAN.5 (high attack potential). ([report](https://www.commoncriteriaportal.org/files/epfiles/0961V7a_pdf.pdf)) |
| Protection profile | BSI-CC-PP-0084-2014 (Security IC Platform PP) |
| Security target | Public ST lite rev 1.13, 2024-09-17 ([0961V7b](https://www.commoncriteriaportal.org/files/epfiles/0961V7b_pdf.pdf)); full ST is confidential |
| History | First cert 2017 (expired 2022), V2/V3 2018, V4 2019, V6 2022, V7 2024 ([CC portal](https://www.commoncriteriaportal.org/files/epfiles/0961a_pdf.pdf)) |
| Other | PSA Certified Level 3 for SLS 32AIA010MK ([PSA](https://products.psacertified.org/products/optiga-trust-m-v3-sls-32aia010mk)) |

**What's in scope:** the security IC, its firmware (BOS, flash loader) and
optional crypto libraries (RSA/EC/SCL/HSL). **Not in scope:** the Trust M
application OS that implements the OIDs, access conditions, Shielded Connection
and the I2C protocol. Infineon says Trust M is "**based on** CC EAL6+ certified
hardware," not that Trust M itself is certified. [confirmed wording; scope
boundary inferred from report contents]
([report](https://www.commoncriteriaportal.org/files/epfiles/0961V7a_pdf.pdf), [datasheet](https://www.infineon.com/dgdl/Infineon-OPTIGA_Trust_M-DataSheet-v03_70-EN.pdf?fileId=8ac78c8c818eceac01819539e0ed53e1))

**Which crypto library version** the Trust M OS links is not public.
[unconfirmed]

Lesson from EUCLEAK: AVA_VAN.5 passed ~80 times on the leaky code. A cert
means a lab didn't find a break in the time it had, not that none exists.

## 5. Weaknesses in typical use

### Plain I2C

- Default: no encryption. Commands and responses are clear text on SDA/SCL at
  address 0x30. [confirmed] ([datasheet §… I2C](https://www.infineon.com/dgdl/Infineon-OPTIGA_Trust_M-DataSheet-v03_70-EN.pdf?fileId=8ac78c8c818eceac01819539e0ed53e1))
- Sniffing signatures leaks nothing secret. The risks are: injecting sign
  requests, swapping the hash being signed (MITM), replaying, and swapping the
  whole chip. [inferred]

### Shielded Connection

- Encrypts and authenticates I2C using a pre-shared **platform binding
  secret** (PBS) in OID `E140`, also stored on the host. [confirmed] ([SRM](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md))
- Infineon's own words: "The security level of the Shielded connection is as
  high as typical microcontroller/Host side hardware security level." Pull the
  PBS from host flash and it's gone. [confirmed]
- No host nonce: "doesn't provide an option to add random challenge/nonce from
  host to provide freshness." Extra steps needed. [confirmed]
- Shielded Connection only **forces** binding if each key's `EXE` access
  condition is set to `Conf(E140)` and the key's lifecycle (LcsO) is locked to
  operational. Turning it on in the host lib alone does not stop a rogue master
  from using a key set to `ALW`. [confirmed per SRM guidance]
- The reference host code ships a placeholder PBS of `01 02 03 …` in
  `pal_os_datastore.c`, and the pairing example leaves `E140` in creation state
  "at the real time/customer side this needs to be" operational. Easy to ship
  by mistake. [confirmed] ([pal template](https://github.com/Infineon/optiga-trust-m/blob/main/extras/pal/NEW_PAL_TEMPLATE/pal_os_datastore.c), [pairing example](https://github.com/Infineon/optiga-trust-m/blob/main/examples/optiga/usecases/example_pair_host_and_optiga_using_pre_shared_secret.c))
- Trezor's config is a good model: signing keys `E0F0`/`E0F2` gated on
  `Conf(KEY_PAIRING)`, PBS never readable or writable. ([Trezor docs](https://docs.trezor.io/trezor-firmware/core/misc/optiga.html))

### Host compromise

- Trust M has no screen, button or user-presence check. It signs whatever
  digest an authorized host sends. Owning the host (malware, bad firmware
  update, glitched MCU) = signing anything, without touching the key.
  [inferred from API; no user-verification feature exists in the SRM]
- So the real security boundary for "what gets signed" is the host + its UI,
  not the SE. Safe-side guards (thresholds, timelocks, spend limits) matter
  more than SE hardness for this risk.

### Factory key `E0F0` defaults

| OID | EXE | Change | Read |
|---|---|---|---|
| `E0F0` device key 1 (factory) | **ALW** | NEV | NEV |
| `E0F1–E0F3` keys 2–4 | ALW | LcsO < op | NEV |
| `E140` PBS | ALW | LcsO < op \|\| Conf(E140) | LcsO < op |

Source: [SRM key/data object tables](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md). [confirmed]

- Out of the box, anything on the bus can sign with the factory key. [confirmed]
- "Change: NEV" means the factory key can never be regenerated. So if
  EUCLEAK extracts it, that chip's identity is cloned for good. [inferred]
- Each extra sign with `E0F0` (e.g. a public attestation endpoint) is one more
  trace for an EUCLEAK attacker. Keep `E0F0` signs rare and gated. [inferred]

### Export and backup

- Keys created in a key OID can't be read: `GetDataObject` on a key's data
  "not allowed… even if the metadata states the access rights differently."
  [confirmed] ([SRM](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md))
- Careful: `GenerateKeyPair` also has an **export-to-host** mode. A key made
  that way was in host RAM. Check our code never uses it for the signer.
  [confirmed API exists]
- No backup, no key wrapping/escrow for ECC private keys. [inferred: no such
  command in the SRM]
- Wallet consequence: chip death, a cracked board, or hitting NVM/counter
  limits = key lost. The Safe must have another owner or a recovery module that
  can replace this signer. [inferred]
- Endurance limits exist (NVM write cycles, Security Event Counter writes); see
  SRM "Overview Data and Key Store." Not a practical issue for a signer used a
  few times a day. [confirmed limits exist; exact numbers per object vary]

## 6. Supply chain: what the factory cert proves

- V3 ships an X.509 cert in `E0E0` for the P-256 key in `E0F0`, chained to
  **Infineon OPTIGA ECC Root CA 2 → CA 300** (V1: Root CA 1 → CA 101;
  Express/MTR: CA 306). [confirmed] ([overview repo](https://github.com/Infineon/optiga-trust-m-overview), [Infineon certs](https://www.infineon.com/design-resources/platforms/optiga-software-tools/optiga-tpm-and-trust-certificates))
- A fresh signature by `E0F0` over our challenge, plus a valid chain, proves:
  "the signer holds a private key that Infineon's CA certified." [confirmed
  by construction]
- It does **not** prove:
  - that the key is still only inside one chip (EUCLEAK clone, or an Infineon
    CA compromise, makes a perfect fake) [inferred];
  - anything about the host firmware or board [inferred];
  - that **another** key (our Safe signer in `E0F1`) lives in the same chip.
    Trust M has no native key attestation. If the host asks `E0F0` to sign the
    `E0F1` public key, a hacked host can feed it any public key. The binding is
    only as good as the host at provisioning time. [inferred; no key-attestation
    command found in SRM]
- Can someone fake a Trust M cert without a real chip? Not without Infineon's
  CA key or a key pulled from a real chip. With EUCLEAK on an old chip: yes,
  one chip's identity can be cloned into software. [inferred]
- Revocation: no public CRL/OCSP process for Trust M device certs found.
  [unconfirmed]
- Express/MTR variants are provisioned by a third party (docs name both
  Infineon OSTS and Kudelski keySTREAM — inconsistent). [confirmed doc
  inconsistency] ([overview repo](https://github.com/Infineon/optiga-trust-m-overview))

On-chain attestation advice [inferred]: pin CA 300 (or the root), verify a
fresh challenge signed by `E0F0`, and treat the attested identity as "an
Infineon chip was involved at enrollment," not "this key can never be copied."

## 7. Comparison

| Chip | Used in | Public key-extraction attacks | Field-updatable | Notes |
|---|---|---|---|---|
| **OPTIGA Trust M** | Trezor Safe 3/5/7 | EUCLEAK (EM side channel, ECDSA). No public fault/laser break. | No | EAL6+ hardware only |
| **ATECC608A/B** (Microchip) | Coldcard Mk3/4, many IoT | 508A: 1 laser fault reads a slot (2020). 608A: 2 laser faults (SSTIC/BlackHat 2021, Coldcard Mk3 PIN slot). 608B: 3-attack laser chain to a protected key and a wallet seed. All Ledger Donjon. ([SSTIC 2021](https://www.sstic.org/media/SSTIC2021/SSTIC-actes/defeating_a_secure_element_with_multiple_laser_fau/SSTIC2021-Article-defeating_a_secure_element_with_multiple_laser_fault_injections-heriveaux.pdf), [hardwear.io](https://hardwear.io/talks/triple-exploit-chain-with-laser-fault-injection-on-a-secure-element/)) | No | Not CC high-level. Clearly weaker. |
| **NXP SE050** | IoT, Arduino Portenta | None public found. Older NXP A700x had an ECDSA EM leak ("A Side Journey to Titan", 2021). | Applet updates possible on some; OS no [unconfirmed] | CC EAL6+ covering **HW + JCOP OS** (NSCIB-CC-180212) ([ST lite](https://commoncriteriaportal.org/files/epfiles/NSCIB-CC-180212_3-STLite.pdf)) |
| **TROPIC01** | Trezor Safe 7 | Ledger Donjon, Jan 2026 (public 2026-06-03): laser fault skips FW signature check, runs custom code, extracts secrets. Needs desolder + backside decap; redo after power-off. No fix for existing chips. ([Trezor](https://trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/tropic-01-chip-vulnerability-disclosure-what-happened)) | No (HW flaw) | Open-architecture SE, new |
| **ST33 (Ledger)** | Ledger Nano/Stax/Flex | No public key extraction from Ledger's ST33 apps found. TPM-Fail hit the ST33 **TPM firmware**, a different product. ([Ledger](https://www.ledger.com/why-secure-elements-make-a-crucial-difference-to-hardware-wallet-security), [TPM-Fail](https://arxiv.org/pdf/1911.05673)) | Yes (Ledger OS) | Vendor writes own crypto; secure screen path |

On the brief's "Kraken ATECC608A key extraction": I could not confirm a Kraken
paper extracting keys from ATECC608A. The known ATECC608A/B extractions are
Ledger Donjon's. [unconfirmed attribution]

Big difference: Ledger/Trezor Safe 5+ pair the SE with a trusted display and
button, and Trezor never puts the seed's ECDSA on the Optiga. Using Trust M as
**the** signing key, driven by a general MCU with no trusted confirm, is a
weaker pattern than either. [inferred]

## 8. Threat model

Costs are rough. [inferred unless a row cites a source]

| Attack | Stopped? | Attacker needs | Rough cost |
|---|---|---|---|
| Read private key over I2C / API | **Yes** | — | — ([SRM](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md)) |
| Remote malware on host asks chip to sign | **No** | Host compromise | Software exploit |
| Bus master on I2C signs with `ALW` key | **No** (default config) | Physical access, wires | ~$20 logic analyzer / MCU |
| Same, keys gated on `Conf(E140)` | Yes, until PBS leaks | PBS from host flash | MCU glitch: low-k$ ([Donjon/Trezor](https://www.theblock.co/post/346018/trezor-discloses-vulnerability-safe-3-crypto-wallet-rival-ledger)) |
| MITM swaps signed hash on bus | Only with Shielded Connection + host check | Interposer on bus | Low |
| Swap in attacker's chip | Only if verifier checks `E0F0` challenge + pins identity | Rework station | Low |
| Fake factory cert, no chip | **Yes** | Infineon CA key | Nation-state / insider |
| EUCLEAK on 2024-era Trust M | **No** | Device in hand <1 h, open case, chip must sign ~40× with target key, offline hours | ~10 k€ gear + expert ([paper](https://ninjalab.io/wp-content/uploads/2024/09/20240903_eucleak.pdf)) |
| EUCLEAK on patched silicon | Probably | — | Unknown; patch status unconfirmed |
| Laser fault / decap / microprobe | Probably (AVA_VAN.5, nothing public) | Lab, decap, many chips | 100 k€+ class [unconfirmed] |
| Chip death / board damage | **No** — key lost | — | Plan Safe recovery |
| Evil maid, then return device | **No** vs EUCLEAK (silent) | Same as EUCLEAK | Same |

## 9. What to do (for our design)

1. Gate every signing key's `EXE` on `Conf(E140)`; set PBS random per device,
   never readable; lock LcsO to operational. ([SRM guidance](https://github.com/Infineon/optiga-trust-m-overview/blob/main/docs/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md))
2. Require a user action (PIN, button, biometric on the host) before each sign,
   so a thief can't drive 40 signatures.
3. Use a monotonic counter as a usage limit on the key; keep the Security
   Monitor on.
4. Don't expose `E0F0` signing beyond enrollment.
5. Treat the chip as one Safe owner, never the only one. Keep a recovery path.
6. Ask Infineon which OPN/firmware has the EUCLEAK-fixed library; buy that
   part; record chip info `0xE0C2` per device.
7. Use host lib ≥ 5.8.3.
8. In on-chain attestation, say what it proves ("Infineon chip at enrollment")
   and no more.

## Open questions

- Is ACL v2.09.002 the EUCLEAK fix, and which Trust M firmware links it?
- Do XTMB2 / XTMC1 parts carry it? (Infineon KB page blocks scripted reads.)
- Does Infineon publish a CRL for Trust M CA 300?
