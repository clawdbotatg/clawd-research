# AI vs elliptic curves: the "bunker mode" scare (2026-10-07/08)

Researched 2026-10-08. Question: is there any real sign that AI can break ECDSA / ECDLP
(secp256k1, P-256) without a quantum computer? Who is saying it, why, and what to do.

Tags: **[confirmed]** = checked against a primary source (paper, repo, the post itself).
**[claim]** = someone said it; we could not check it. **[spec]** = speculation or opinion,
including ours. All times UTC. Tweet text was pulled from the posts themselves (fxtwitter API
and the logged-in X page), not from news paraphrase.

> ## What's actually known (as of 2026-10-08 16:00 UTC)
>
> - **No AI or classical attack on secp256k1 or P-256 has been published.** None. Not in the
>   OpenAI drop, not on ePrint, not on arXiv. Best known classical attack is still generic
>   Pollard rho, about 2^128 work. [confirmed: searched ePrint/arXiv + read the OpenAI catalog]
> - **The trigger was general AI math, not crypto.** On 2026-10-06 OpenAI dumped 719
>   manuscripts (372 result families) from an unreleased model. We grepped the catalog: **zero**
>   results on discrete log, ECDLP, factoring, lattices or cryptanalysis. Three papers were
>   already withdrawn on 10-07 for a sign error. ~42% of headline results have Lean proofs.
>   [confirmed]
> - **AI has broken real crypto assumptions, just not ECC:**
>   - Anthropic (07-28): Claude broke **HAWK**, a lattice signature in NIST round 3. Key
>     recovery for HAWK-256 went from 2^64 to 2^38. HAWK was withdrawn next day. Also a
>     200-800x speedup on **7-round** AES (still 2^89 work, not practical). [confirmed]
>   - Claude (paper 10-05): **3SUM, APSP and Zero-Weight k-Clique hypotheses refuted.** Found
>     while Claude was told to analyze *cryptographic constructions* built on Zero-k-Clique
>     hardness. That is a broken crypto assumption, but a niche "fine-grained" one nobody
>     deploys. [confirmed]
>   - OpenAI: integer multiplication below n log n, matrix-mult exponent <= 9/4, deterministic
>     polynomial factoring over F_p. Big theory results, no effect on key sizes. [confirmed]
> - **Quantum estimates keep falling.** Google (03-30): ECDLP-256 in ~1,200 logical qubits,
>   <500k physical, minutes per key. IonQ (09-10): 19,397 trapped-ion qubits, ~26 days.
>   ecdsa.fail open "autoresearch" (humans + AI agents) cut the point-addition circuit cost 86%.
>   [confirmed]
> - **Drake's "months not years" is his opinion.** He gives no attack, no paper, no leak. He
>   calls it a worst case. [confirmed that it's opinion; the risk itself is spec]
> - **Moving to a never-signed address is cheap, old advice.** Everyone, skeptics included,
>   agrees on "don't reuse addresses". The fight is over "mass migration" and the timeline.

---

## 1. Timeline

| When (UTC) | What | Status |
|---|---|---|
| 2026-03-25 | Google sets 2029 as its full PQ migration date (Adkins + Schmieg). | confirmed |
| 2026-03-30/31 | Google Quantum AI ECDLP-256 paper (Drake is a late co-author). Circuit details hidden behind a ZK proof. Oratomic neutral-atom paper same day. | confirmed |
| 2026-05-20 | OpenAI model disproves Erdős unit distance conjecture. Checked by Alon, Gowers, Sawin et al. ([arXiv 2605.20695](https://arxiv.org/abs/2605.20695)). Drake calls this "our warning shot". | confirmed |
| 2026-06-02 | André Schrottenloher publishes the hidden Google optimization. ecdsa.fail launches. | confirmed (per Drake + ePrint 2026/1128) |
| 2026-07-28 | Anthropic: Claude breaks HAWK, speeds up 7-round AES. | confirmed |
| 2026-07-29 | HAWK withdrawn from NIST. Matthew Green blog post. | confirmed |
| 2026-08-01 | OpenAI "Ten Advances" incl. NP-hardness of poly-approx CVP (a *hardness* result, good news for lattices). | confirmed |
| 2026-09-10 | IonQ: secp256k1 in ~26 days on 19,397 trapped-ion qubits (ePrint 2026/1916). | confirmed |
| 2026-10-05 | Alman + Vassilevska Williams: 3SUM in O(n^1.9992), algorithm found by Claude (arXiv 2610.06783). | confirmed |
| 2026-10-06 | OpenAI dumps 719 math manuscripts (github.com/openai/math). | confirmed |
| 2026-10-07 14:14 | **Drake "bunker mode" post.** ~4M views. | confirmed |
| 2026-10-07 23:28 | Vitalik: don't scramble, but lattices are the new worry. | confirmed |
| 2026-10-08 00:31 | **Green: "I think we might lose public key cryptography."** Then: "Well, encryption specifically." | confirmed |
| 2026-10-08 01:01 | Lindell (Coinbase): "the very definition of FUD". | confirmed |
| 2026-10-09..12 | EF post-quantum research retreat (Cambridge UK). Expect statements after. | claim (CryptoSlate) |

---

## 2. What triggered it

### 2.1 The OpenAI drop (2026-10-06) [confirmed]

- Repo: [github.com/openai/math](https://github.com/openai/math). README: "719 manuscripts
  organized into 372 families". News says 722; the repo now says 719.
- About 4,000 problems posed, about 3 hours of "ChatGPT Pro thinking" per result.
- README: "Some of the unformalized results could have issues." ~42% of headline results
  have Lean proofs.
- [history.md](https://github.com/openai/math/blob/main/history.md), 10-07: three Hodge/K3
  papers withdrawn ("a sign error invalidates a stabilization-trace cancellation argument"),
  14 more patched.
- **We cloned it and grepped `CONTENTS.md`.** Hits for "discrete logarithm", "cryptograph",
  "learning with errors", "shortest vector": **0**. Closest things:
  - #109 integer multiplication in O(n (log n)^(1-2^-182)). Disproves n log n optimality.
  - #107 matrix multiplication exponent <= 9/4.
  - #142 deterministic poly-time factoring of *polynomials* over F_p (not integers).
    Chris Peikert: closes "an annoying gap in crypto: unconditional DPT square roots modulo a
    prime = 1 mod 16" ([Bluesky, 10-07](https://bsky.app/profile/chrispeikert.bsky.social/post/3mxcrpv524c2n)).
  - #279 exact quantum factoring circuit (a theory result, not a cheaper Shor).
  - #102 claims a proof of Khot's Unique Games Conjecture.
  - Elliptic curve *number theory* (BSD, modularity, Goldfeld). That is about curves over Q,
    not discrete logs over finite fields.
- Drake himself noted the gap: "striking under-representation of cryptographic breakthroughs
  among the 722 mathematical results". He reads that as possible censorship. That is
  **[spec]**.

### 2.2 The Claude 3SUM result (2026-10-05) [confirmed]

[arXiv 2610.06783](https://arxiv.org/abs/2610.06783), Josh Alman (Columbia) + Virginia
Vassilevska Williams (MIT). From the paper's methodology section:

> "An Anthropic employee used an internal research model to investigate open problems in the
> theory of cryptography. One of them was about cryptographic constructions based on the
> average-case hardness of Zero-k-Clique ... Claude was tasked with verifying and improving
> the constructions, but instead developed this algorithm ... The session used 16M output
> tokens with no human input."

Why it matters: this is the clearest case of an AI knocking out a hardness assumption that
someone had built crypto on. Why it is not ECC news: the saving is tiny (n^2 to n^1.9992),
and fine-grained crypto is not deployed anywhere. Lean proofs at
[anthropics/formal-math](https://github.com/anthropics/formal-math/tree/main/3sum-apsp).

### 2.3 The Anthropic cryptanalysis post (2026-07-28) [confirmed]

[anthropic.com/research/discovering-cryptographic-weaknesses](https://www.anthropic.com/research/discovering-cryptographic-weaknesses)

- HAWK-256 key recovery: thought 2^64, shown 2^38. "about 60 hours in total."
- 7-round AES: 200-800x faster. Full AES has 10+ rounds.
- "Each of the results cost roughly $100,000 in API cost."
- "they do not currently affect any production systems."
- Small (<10x) gains on reduced Salsa20, Poseidon, SHA-1. 6-round Serpent key recovery.
- No mention of ECDLP or RSA attacks.
- NIST's PQC page now says HAWK was withdrawn and "This finding does not affect any of NIST's
  finalized PQC standards, such as ML-KEM and ML-DSA" ([nist.gov/pqc](https://www.nist.gov/pqc)).
- One report says a separate team hit HAWK independently with GPT-5.6. [claim]

### 2.4 Things people cite that are not real or not checked

- "OpenAI used 10,000 agents to solve Navier-Stokes in 88 hours." Repeated by several crypto
  news sites. **Not in Drake's post.** No primary source found. [rumor]
- "OpenAI already has a (log p)^k discrete log algorithm and is hiding it" (popular X post,
  @testinprodcap). Joke/rumor. [rumor]
- Drake (08-13): HAWK and isogeny-based SQIsign "have suffered blows. Sources I trust say more
  blood is coming." HAWK is confirmed. **We found no public SQIsign break.** [claim]
- "The AI Lab says quantum threat is 2 years away." A product press release. Ignore.

---

## 3. The posts, word for word

### Justin Drake (EF), 2026-10-07 14:14 [confirmed, full text]

[x.com/drakefjustin/status/2107837081313505768](https://x.com/drakefjustin/status/2107837081313505768)

> Today I call upon the blockchain industry to calmly begin planning for "bunker mode". My
> personal recommendation is to set in motion a controlled mass migration of assets to fresh
> addresses, i.e. addresses whose pubkeys remain hidden behind a hash.
>
> Holders, starting with large and sophisticated ones, should consider moving the bulk of
> their funds to addresses that have never signed a transaction. And when they do sign one,
> they should also move remaining funds to a new address (possibly generated from the same
> seed phrase).
>
> Don't rush. While I believe there is cause for action a rushed migration would do more harm
> than good. Don't panic either. Moving assets to protected addresses is a simple, preventative
> step which does not require new cryptography or new wallets.
>
> IMO it is now reasonable to brace for the possibility that ECDSA breaks before qday, in the
> worst case in months not years. By "break" I mean fast private key recovery (e.g. in one
> week) on available hardware (e.g. a large GPU cluster).
>
> Recent days have been humbling for human mathematical intuition. Long-held, unquestioned
> hypotheses have fallen. This includes the n log(n) bound for integer multiplication and the
> 3SUM conjecture. In hindsight, May's unexpected disproof of the Erdős unit distance
> conjecture was our warning shot.
>
> Yesterday's OpenAI drop made it clear that mathematical superintelligence is upon us. [...]
> Could our magic 64-byte ECDSA signatures be too good to be true? Was it just security
> through obscurity all this time?
>
> Elliptic curves feel especially vulnerable to superintelligence. Curves carry rich
> structure, with room for fancy tricks like Schoof, Frobenius, pairings. (By contrast, hashes
> are designed to minimise algebraic structure.)
>
> Separately, as Ewin Tang can attest, an efficient quantum algorithm sometimes foreshadows an
> efficient classical one. We should be open to the possibility of a classical counterpart to
> Shor that breaks elliptic curves and RSA at once.
>
> Also noteworthy is the striking under-representation of cryptographic breakthroughs among
> the 722 mathematical results OpenAI published. I've witnessed first-hand the US government
> censoring academic quantum cryptanalysis results. Backroom interventionism is my base case.
>
> I urge large, sophisticated actors to lead by example. Project11's "risq list" [...] is a
> great tracker of exposed BTC pubkeys. Binance, Bitbank, Robinhood, Bitfinex, and Tether have
> an opportunity to harden their cold storage. [...]
>
> Again, please do not rush. Wallets holding under 50 BTC enjoy partial cover from "Satoshi's
> shield", i.e. his 20K exposed addresses that hold 50 BTC each. Load-bearing signers like
> oracles and L2 security councils should consider rotating ECDSA pubkeys with every signed
> message and/or multi-signing with a hash-based schemes like SPHINCS.
>
> Exiting bunker mode safely will require post-AI cryptography. My inclination is to go all-in
> on hash-based cryptography and avoid structured mathematical assumptions entirely, whether
> from curves, lattices, or isogenies. A single battle-tested hash (e.g. from the SHA or BLAKE
> families) yields plausible post-AI security.
>
> The Ethereum roadmap on strawmap[.]org fully embraces hash-based cryptography [...]. Those
> timelines must now be revisited and accelerated in light of mathematical superintelligence.
> I'll be pushing for maximum defensive acceleration.

Check on his evidence:
- n log n multiplication: real (OpenAI #109). 3SUM: real (Claude, 2610.06783). Unit distance:
  real (May). None touch ECDLP. Craig Gidney (Google) on these: the n log n result is
  "irrelevant to practice"; "Odds on most asymptotic complexities ending up with finicky
  complicated inelegant constants just shot up" ([10-07](https://x.com/CraigGidney/status/2107849355780567426)).
- "US government censoring": what's public is that Google hid its 03-30 circuit behind a ZK
  proof after it "engaged with the U.S. government", and Gidney said he sat on one
  optimization for a year. "Censorship" is Drake's word. Drake is a co-author and says he
  can't say more ([06-02 post](https://x.com/drakefjustin/status/2061793725299224676)). [confirmed facts, spec framing]
- Drake's own quantum odds (06-02): "50%" chance of qday by 2032, "10% by 2030".

### Matthew Green (JHU), 2026-10-08 00:31 [confirmed]

Replying to Kevin Madura, who asked "how many novel attacks on cryptography do we think exist
now but are unreleased?" ([x.com/kmad/status/2107971206208995605](https://x.com/kmad/status/2107971206208995605)):

- "I think we might lose public key cryptography."
  [x.com/matthew_d_green/status/2107992246360649879](https://x.com/matthew_d_green/status/2107992246360649879) (~1M views)
- 16 seconds later: "Well, encryption specifically."
  [x.com/matthew_d_green/status/2107992310177022307](https://x.com/matthew_d_green/status/2107992310177022307)

Read with care: it's two lines, not a thread. "Encryption specifically" points at public-key
*encryption* (KEMs: ML-KEM, ECDH, RSA-OAEP), where hash-only fallbacks don't exist. Signatures
can fall back to hashes. He did not say ECDSA is about to break.

His longer view is in the 07-29 blog post
([Some thoughts about Anthropic's new cryptanalysis results](https://blog.cryptographyengineering.com/2026/07/29/some-notes-about-anthropics-new-results/)):
- "Public-key cryptography is messier." Too few people have studied ECDLP, RSA, lattices,
  codes to rule out better attacks. "there's a lot of fertile ground for AIs to make real progress."
- Good news: we are mid-migration anyway. "If there was ever a perfect time for a massive new
  public cryptanalysis capability to come on line, we're in it."
- Symmetric crypto looks robust.
- Models also produce "result slop" that takes experts hours to debunk.

Bluesky (his main account, matthewdgreen.bsky.social) on 08-02: "I feel like we're going to
look back at that time in summer 2026 when we thought it was so surprising that models could
find new mathematical results". No ECC post there this week.

### Vitalik Buterin, 2026-10-07 23:28 [confirmed, key lines]

[x.com/VitalikButerin/status/2107976296320106851](https://x.com/VitalikButerin/status/2107976296320106851)

> I don't recommend anyone scramble to move their funds to new wallets today. But we should
> take the risks to cryptography from AI-accelerated math seriously, and minimize our exposure
> to not just quantum-vulnerable cryptography, but also potentially AI-vulnerable cryptography.
>
> The core new area of risk from this viewpoint is, unfortunately, ML-DSA / FHE / lattices.
>
> (and it's also another reason, along with quantum, why ECDSA might fall even faster than
> expected, hence the "fresh address" recommendation)
>
> [...] there is a good chance that the concrete security of lattices will take serious hits
> from the next two years of AI math.
>
> [...] What if there are skeletons in the closet like that [naive factoring -> GNFS], both for
> elliptic curves and lattices, that we are simply not smart enough to discover - but bots
> soon will be?
>
> [...] one reasonable inference is that if you want to make something plausibly long-term
> secure, multiply the key sizes by 10.
>
> [...] it's much more likely that a mathematical object has exactly no exploitable structure
> (like hashes are intended to), than that a mathematical object has exactly ~3 forms of
> exploitable structure (for elliptic curves: associativity, Schoof, pairings) and not some
> secret fourth form [...]
>
> * Hash-based > lattice-based, in those situations where hash-based is possible at all
> * For anything lattice-based, be much more paranoid on param sizes. [...]
> * For privacy protocols, strongly favor NOT putting encrypted notes onchain. [...]
> * If it's not difficult for you, keeping your funds in addresses which have not yet been
>   used to make a transaction is a good idea. [...] **But be careful about migrations; I
>   personally have lost more money in botched migrations than I have lost in all hacks
>   combined**.
> * For multisig wallets, doing confirmations offchain is better than onchain [...] so if
>   ECDSA falls to AI much faster than expected, at least the multisig "gracefully degrades"
>   to a 1-of-1 where the 1 is whoever was gathering the signatures

Follow-up, 10-08 04:07 ([link](https://x.com/VitalikButerin/status/2108046549020557482)):
"for multisigs the ideal "safe" rule is that you want each signer to change their key after
each operation. [...] it's very easy to lose funds from a misconfigured rushed upgrade, so
... don't rush anything."

### Others

| Who | When | Stance | Quote / link |
|---|---|---|---|
| **Yehuda Lindell** (Coinbase head of crypto) | 10-08 01:01 | Skeptic | "there is no evidence whatsoever pointing to a break of decades old hardness assumptions like elliptic curve cryptography." "The fact that AI can prove theorems that have been hard does not indicate in any way that problems assumed to be hard are not." "historically hash functions have been more broken than elliptic curves." "It is the very definition of FUD." [thread](https://x.com/LindellYehuda/status/2107999859219587309) |
| **Charles Guillemet** (Ledger CTO) | 10-07 17:02 | Skeptic | "treating a classical ECDSA break in months as a planning baseline still looks like FUD." A real break "would compromise TLS, code signing, most banking systems". "the same loss of mathematical intuition that motivates caution on curves also applies to hashes ;-)". "calling for a "mass migration" would create operational mistakes that lose funds with higher probability than the scenario being mitigated." [link](https://x.com/P3b7_/status/2107879248765874659). Also: "today's biggest risk is on operational security, not on cryptography." [link](https://x.com/P3b7_/status/2107881070637265356) |
| **Adam Back** (Blockstream) | 10-08 06:04 | Skeptic | To Green: "Dubious. Do you think P=NP? [...] even if all algebraic were hardness problems lost, we have hash-based SHRINCS." [link](https://x.com/adam3us/status/2108076121895969011) |
| **Dankrad Feist** (EF alum) | 10-08 02:29 | Skeptic of the plan | "If elliptic curves are broken so that any exposed public key leads to compromise, and it's not by white hat hackers who save everyone's assets first, your coins are going to zero. Having them in bunker mode is not going to help you." [link](https://x.com/dankrad/status/2108021904028438591). Agreed with Dan Robinson that stablecoins "would probably be OK". |
| **Bas Westerbaan** (Cloudflare) | 10-08 10:40 | Calm | "No reason to panic yet." (standalone post; context not stated) [link](https://x.com/bwesterb/status/2108145508795793680) |
| **Deirdre Connolly** (PQ standards) | 10-08 14:29/14:45 | Mixed | "ill put 15 dollars on rsa going bust (from a non-quantum attack)" and "im more skeptical about a classical curves break/weakening but they're vulnerable to shor anyway" ([1](https://bsky.app/profile/durumcrustulum.com/post/3mxeob3qfyk2z), [2](https://bsky.app/profile/durumcrustulum.com/post/3mxep65v5oc2z)) |
| **Antonio Sanso** (EF crypto) | 10-08 09:34 | Constructive | Lists where a lab should aim: 1024-bit Micali–Schnorr factoring, Poseidon over small fields, class numbers, pairing inversion, **ECDLP over binary fields**. Prime-field curves (ours) are not on the list. [link](https://x.com/asanso/status/2108128919387820278) |
| **Haseeb Qureshi** (Dragonfly) | 10-07 16:26 | Alarmed | "I think this is a very sober call. [...] The risk is not quantum, but just conventional mathematics overturning unproven cryptographic hardness assumptions." [link](https://x.com/hosseeb/status/2107870281599762683) |
| **Samson Mow** (Jan3) | 10-08 05:51 | Dismissive | "Don't reuse addresses as a best practice. There's no need to panic because an Ethereum researcher is saying silly things." [link](https://x.com/Excellion/status/2108072761738551781) |
| **Jacob Creech** (Solana Fdn) | 10-08 03:51 | Chain pitch | Ed25519 keys come from a hashed seed, so owners can later prove seed knowledge with a hash proof and migrate. PoC: anza-xyz/cryptography `ed25519-pokos`. [link](https://x.com/jacobvcreech/status/2108042644819427521) |
| **Safe** (official) | 10-08 13:02 | Marketing | Quote-posted "Bunker Mode = @safe mode". No technical statement. [link](https://x.com/safe/status/2108181362406719727) |
| **BitGo** | 10-07 | Marketing | "We've been offering 'bunker mode' since 2013." |

**Searched, found nothing this week:** Dan Boneh, Nadia Heninger, Tanja Lange, Daniel J.
Bernstein (latest blog post 08-14, "NSA and IETF, part 9"; his 06-30 post "Understanding
lattice risks" predates this), Sophie Schmieg, Filippo Valsorda, Martin Albrecht, Luca De Feo,
Jameson Lopp, Jonas Nick. Checked X search and Bluesky feeds. Hacker News API was blocked for
us; no HN thread checked.

**Scoreboard:** working cryptographers who spoke are mostly skeptical of a near-term ECC break
(Lindell, Guillemet, Connolly, Westerbaan, Back). Green worries about public-key *encryption*
over years, not ECDSA in months. Alarm comes mainly from Ethereum researchers (Drake, partly
Vitalik) and crypto investors.

---

## 4. Real cryptanalysis progress on 256-bit curves, 2025-2026

### Classical [confirmed]
- Nothing new that matters. Records for prime-field ECDLP sit around 112-117 bits. 256-bit
  needs ~2^128 group operations (Pollard rho).
- [arXiv 2607.09814](https://arxiv.org/abs/2607.09814) (Mahalanobis, "guess and determine"):
  a zero-minor approach. Earlier versions of this line only reached ~2^50 groups. Not a threat.
- secp256k1 has a known speedup from its efficient endomorphism (GLV) plus negation map: a
  small constant factor (about sqrt(6)), known for 20+ years.

### Quantum [confirmed]
| Source | Date | Logical qubits | Gates | Physical | Time |
|---|---|---|---|---|---|
| Google Quantum AI, Babbush et al. ([ePrint 2026/625](https://eprint.iacr.org/2026/625), PRX Quantum) | 03-30 | ~1,200 (or ~1,450 with fewer gates) | 70-90M Toffoli | <500k superconducting | minutes |
| Oratomic ([arXiv 2603.28627](https://arxiv.org/abs/2603.28627)) | 03-31 | builds on Google | | ~10-26k neutral atoms | ~10 days |
| Schrottenloher ([ePrint 2026/1128](https://eprint.iacr.org/2026/1128)) | 06-02 | ~Google +1.5% | 6.5-10% fewer | | |
| IonQ, Häner/Naehrig/Roetteler et al. ([ePrint 2026/1916](https://eprint.iacr.org/2026/1916)) | 09-10 | ~1,450 | 40M Toffoli | 19,397 trapped ions | ~25.7 days, 63% success |
| ecdsa.fail open autoresearch, Eigen Labs, 36 authors ([arXiv 2609.09582](https://arxiv.org/abs/2609.09582)) | 09-09 | 1,151 (813 low-width variant) | ~1.3M Toffoli per point add | | point-add cost Q×T down 86% |

- Google withheld its circuit and published a ZK proof instead. First time that's been done.
- AI is now used to optimize Shor circuits (ecdsa.fail, arXiv 2609.28882). That's AI speeding
  up the *quantum* attack, which is the more grounded version of "AI shortens the timeline".
- Timelines: Google, Cloudflare and the EF target 2029 for migration. Global Risk Institute
  survey: 28-49% chance of a cryptographically relevant QC within 10 years. NIST: deprecate
  P-256-class after 2030, disallow after 2035.

---

## 5. What the ecosystem is doing

Protocol detail is in [PQ-WALLET-LANDSCAPE.md](PQ-WALLET-LANDSCAPE.md). Short version:

- **Ethereum.** Hash-only plan (WOTS / SPHINCS-style, leanVM, no lattices). EF PQ team since
  2026-01, [pq.ethereum.org](https://pq.ethereum.org/) since 03-25, L1 PQ target ~2029. EF
  dropped Poseidon for SHA/BLAKE on 08-13. EIP-8141 frame transactions SFI'd for Hegotá.
  Vitalik's [quantum emergency fork plan](https://ethresear.ch/t/how-to-hard-fork-to-save-most-users-funds-in-a-quantum-emergency/18901)
  (roll back, freeze ECDSA, prove BIP-32 seed with a STARK) is the standing break-glass plan.
  No official EF statement on AI yet; PQ retreat is 10-09..12. Drake says he'll push to
  accelerate.
- **Bitcoin.** BIP-360 (now P2MR, Pay-to-Merkle-Root, bc1z) merged as Draft 2026-02-11, not
  activated. BIP-361 (Lopp et al.) proposes sunsetting legacy sigs, needs 360 first. SHRINCS
  hash-based sig BIP draft 08-27 (Blockstream), running on Liquid since 03. No soft fork
  scheduled. Bitcoin devs mostly dismissed the AI claim.
- **Safe.** No post-quantum module of its own. Stock Safe can swap owners, which is the escape
  hatch. Third-party PQ setups exist (Qanary, RivaLabs, our hashsig-safe).
- **Hardware wallets.** Trezor Safe 7 uses SLH-DSA for firmware verify and ML-DSA for
  attestation; transaction signing is still ECDSA. Ledger has ML-KEM in its SDK; CTO is
  publicly skeptical of the AI scare. No vendor ships PQ transaction signing for ETH/BTC.
- **NIST.** HAWK withdrawn. NIST says ML-KEM / ML-DSA unaffected. No AI-specific guidance.
  NSA CNSA 2.0 bars new non-PQ national security systems from 2027-01-01. OMB M-26-15 (06-24).
- **Solana.** Points to Ed25519 seed-hash migration path.
- **Markets.** BTC fell under $83k on 10-08 (CoinDesk also blames rates). "Quantum-safe" tokens
  pumped (ALGO +9%).

---

## 6. Who is exposed, and what to do

### What "exposed" means
Your public key is on chain, or anywhere public. A future ECDLP break (AI or quantum) turns a
public key into a private key. A hash of a key (an address) stays safe as long as the hash
holds.

| Thing | Pubkey public? |
|---|---|
| ETH EOA that has never signed anything | No. Only the address (keccak hash) is public. |
| ETH EOA that sent any tx | **Yes**, recoverable from the signature. |
| ETH EOA that signed **off-chain** (SIWE login, EIP-712 permit, Permit2, NFT listing, 7702 authorization) | **Yes**, to whoever saw that signature. Easy to forget. |
| BTC P2PKH / P2WPKH, never spent | No. |
| BTC Taproot (P2TR) | **Yes**, the key is in the address itself. |
| BTC P2PK (Satoshi era), reused addresses | **Yes**. |
| Any wallet whose xpub you gave to a service | **Yes**, to that service, for every address. |
| Safe with ECDSA owners | Owner pubkeys go public the first time each owner's signature lands in `execTransaction` calldata (or they send any tx). Off-chain collection only delays this until execution. |
| **Safe with a P-256 passkey / chip owner** (our wedgie-safe, picowallet) | **Yes, from setup.** Safe's WebAuthn signer proxy is deployed with x,y in its code/args (usually at setup, at the latest at first use), before or with the first signature. Unlike an EOA there is no hash hiding the key. |
| Our Trust M attest contracts (clawd-trust-m, clawd-crops) | **Yes.** The chip pubkey and CA 101 key are on chain by design. Fine for attestation, not for holding funds. |

### Guidance being given (and our take)
1. **Don't reuse addresses. Keep the bulk in never-signed addresses.** Everyone agrees. Cheap.
   Do it as normal hygiene, not as an emergency. [consensus]
2. **Don't rush a mass migration.** Vitalik, Guillemet, Drake himself. Botched moves lose more
   money than this threat has so far. [consensus]
3. **Rotate keys after each signature** for multisig signers / oracles / councils (Drake,
   Vitalik). Real but costly ops work. Worth it only for high-value signers. [opinion]
4. **Add a hash-based co-signer** (SPHINCS / WOTS) to important multisigs (Drake). This is
   what hashsig-safe does. [opinion, matches our direction]
5. **Prefer hashes over lattices** for long-term signatures (Drake, Vitalik). Supported by the
   HAWK break. Lattice *standards* (ML-DSA, ML-KEM) are not broken. [opinion]
6. **Watch the right signal.** A real break would show up first as a published reduced-size
   ECDLP record far below 2^n/2 work, or a sudden drain of old exposed BTC (Satoshi coins,
   P2PK). Neither has happened.

### For our stack specifically [spec, our call]
- **P-256 chip keys as Safe owners are fully exposed** the day they are registered. Same risk
  class as an ETH key that has signed. A classical or quantum ECDLP break hits them first.
  This doesn't change the plan; it confirms it: P-256 owner for convenience, WOTS owner
  (hashsig-safe) as the real authority for anything that matters.
- **Trust M V1 can't help with this directly.** It signs ECDSA only. Its use in a post-ECC
  wallet is as a locked PRF/seed holder for hash-based one-time keys (tested today, see
  [V1-DERIVEKEY-TEST.md](V1-DERIVEKEY-TEST.md)).
- **Watch P-256 vs secp256k1.** If a structural ECC attack ever appears, it could hit one curve
  family harder than the other (secp256k1 has extra structure from its endomorphism; P-256
  doesn't). Pure speculation; no such attack is known.
- **Don't panic-move anything** because of this news. Move dev/test funds out of reused
  addresses when convenient.

---

## Sources

Primary:
- Drake post: https://x.com/drakefjustin/status/2107837081313505768
- Drake 03-31 (Google paper): https://x.com/drakefjustin/status/2038847732152996108
- Drake 06-02 (censorship, ecdsa.fail): https://x.com/drakefjustin/status/2061793725299224676
- Drake 08-13 (Poseidon dropped): https://x.com/drakefjustin/status/2087905684180418733
- Green: https://x.com/matthew_d_green/status/2107992246360649879 and .../2107992310177022307
- Green blog 07-29: https://blog.cryptographyengineering.com/2026/07/29/some-notes-about-anthropics-new-results/
- Vitalik: https://x.com/VitalikButerin/status/2107976296320106851 and .../2108046549020557482
- Lindell: https://x.com/LindellYehuda/status/2107999859219587309
- Guillemet: https://x.com/P3b7_/status/2107879248765874659
- Dankrad: https://x.com/dankrad/status/2108021904028438591
- Adam Back: https://x.com/adam3us/status/2108076121895969011
- Sanso: https://x.com/asanso/status/2108128919387820278
- Gidney: https://x.com/CraigGidney/status/2107849355780567426
- Westerbaan: https://x.com/bwesterb/status/2108145508795793680
- Connolly: https://bsky.app/profile/durumcrustulum.com/post/3mxeob3qfyk2z
- Peikert: https://bsky.app/profile/chrispeikert.bsky.social/post/3mxcrpv524c2n
- OpenAI math repo: https://github.com/openai/math
- OpenAI Ten Advances (CVP hardness): https://cdn.openai.com/pdf/ten-proofs-oai.pdf
- Anthropic crypto post: https://www.anthropic.com/research/discovering-cryptographic-weaknesses
- 3SUM paper: https://arxiv.org/abs/2610.06783
- NIST PQC page: https://www.nist.gov/pqc
- Google ECDLP paper: https://eprint.iacr.org/2026/625
- IonQ: https://eprint.iacr.org/2026/1916
- Schrottenloher: https://eprint.iacr.org/2026/1128
- ecdsa.fail: https://arxiv.org/abs/2609.09582
- Unit distance remarks: https://arxiv.org/abs/2605.20695

News / secondary:
- CoinDesk 10-08: https://www.coindesk.com/markets/2026/10/08/bitcoin-slips-below-usd83-000-as-ethereum-researcher-s-bunker-mode-call-divides-crypto
- The Block 10-08: https://www.theblock.co/news/defi/2026-10-08-crypto-industry-split-over-justin-drakes-ai-warning-418021
- Bitcoin.com: https://news.bitcoin.com/crypto-news/bunker-mode-crypto-experts-argue-ai-threat-bitcoin-ethereum
- Decrypt: https://decrypt.co/380363/ethereum-researcher-ai-break-encryption-before-quantum
- CryptoSlate: https://cryptoslate.com/openais-math-breakthrough-raises-fears-ai-could-break-bitcoin-and-ethereum-security-within-months/
- Quantum Insider (Google estimate): https://thequantuminsider.com/2026/03/31/google-suggests-quantum-attacks-on-cryptocurrency-encryption-may-require-fewer-resources/
- BIP-360 merge: https://blockspace.media/insight/bitcoin-developers-merge-bip-360-in-first-move-to-address-quantum-computing-risks/
- Trezor quantum-ready: https://trezor.io/guides/trezor-devices/trezor-safe-7/the-first-quantum-ready-hardware-wallet
