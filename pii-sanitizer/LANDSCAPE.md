# PHI sanitizer in front of frontier LLMs — landscape

2026-10-26. Web research only. Goal: strip PHI from medical text, send placeholders to a
frontier model, swap them back on return, and somehow *know* the outbound text is clean
(idea: Levanto Sage as an exit check).

Not legal advice. Items marked **(unverified)** came from secondary sources only.

---

## 1. HIPAA de-identification rules

Rule text: 45 CFR 164.514(a)–(c)
(https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514).
HHS guidance: https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html
(blocked our fetcher; the content below is from the rule text plus memory of the guidance).

Data that is properly de-identified is **not PHI**. HIPAA stops applying to it. There are
two ways to get there.

### 1a. Safe Harbor — 164.514(b)(2)

Remove these 18 identifiers for the patient **and their relatives, employers, and household
members**:

| # | Identifier | Notes |
|---|---|---|
| A | Names | |
| B | Geography smaller than a state | Street, city, county, precinct, ZIP, geocodes. First 3 ZIP digits may stay **only if** all ZIPs with those 3 digits hold >20,000 people (current Census); otherwise use `000`. HHS lists 17 restricted ZIP3s (2000 Census). |
| C | All date elements except year | Birth, admission, discharge, death dates. **All ages over 89**, and any date element (incl. year) that reveals such an age. Ages can be grouped as "90 or older". |
| D | Phone numbers | |
| E | Fax numbers | |
| F | Email addresses | |
| G | Social Security numbers | |
| H | Medical record numbers | |
| I | Health plan beneficiary numbers | |
| J | Account numbers | |
| K | Certificate/license numbers | |
| L | Vehicle IDs and serials, incl. plates | |
| M | Device IDs and serial numbers | |
| N | URLs | |
| O | IP addresses | |
| P | Biometric IDs (finger, voice prints) | |
| Q | Full-face photos and comparable images | |
| R | Any other unique identifying number, characteristic, or code | Except a re-identification code allowed under 164.514(c). |

**Plus the "no actual knowledge" clause, 164.514(b)(2)(ii):** the covered entity must not
actually know that what remains could identify the person, alone or combined with other
info. Example from HHS guidance: a note that says "the patient is the current mayor" or
names a rare job title. Removing the 18 is not enough if you *know* the rest still points
to someone.

Safe Harbor applies to free text too. Narrative names, places and dates count.

### 1b. Expert Determination — 164.514(b)(1)

- **Who:** "a person with appropriate knowledge of and experience with generally accepted
  statistical and scientific methods" for making data not identifiable. No license or
  certification exists. Usually a statistician or privacy firm.
- **What they produce:** a written determination that the risk of re-identification by the
  expected recipient is "very small", with documented methods and results. It is tied to a
  dataset, a recipient, and a use. HHS says experts may set an expiry date.
- **Allows things Safe Harbor doesn't:** e.g. date shifting, 3-digit ZIPs, keeping some
  dates, as long as measured risk is very small.
- **Cost/time (vendor source, Limina/Private AI):** a few thousand dollars for clean
  structured data, tens of thousands for complex multi-source data; 2–4 weeks typical,
  6–8+ weeks for longitudinal or multi-site data
  (https://www.getlimina.ai/en/blog/hipaa-expert-determination-cost,
  https://www.getlimina.ai/en/blog/hipaa-expert-determination-report).
- An expert determination on a *pipeline* (not a fixed dataset) is possible but needs
  ongoing measurement — the expert has to trust your recall numbers.

### 1c. Is "pseudonymize with a reversible map" de-identified?

164.514(c) lets a covered entity keep a code to re-identify data, if both hold:

1. **Derivation:** the code is not derived from or related to info about the person, and
   can't be translated back to identify them. So `[PATIENT_1]` is fine. A hash of the
   name, MRN, or SSN is **not** (HHS guidance calls out hashes of identifiers).
2. **Security:** the entity doesn't use or disclose the code for other purposes and does
   not disclose the re-identification mechanism.

**What it means for a local placeholder map:**

- Sanitized text with random, sequential placeholders + a map that never leaves our box
  **can** meet Safe Harbor — *if* all 18 identifiers were actually removed. The map is
  the allowed re-identification code.
- The map itself is full PHI. It must be protected like PHI and never sent with the text.
- The catch is recall, not the map. One missed name means the outbound text was PHI, and
  sending it to a vendor without a BAA is a disclosure (possibly a reportable breach).
- Safe Harbor also wants **dates** gone (except year). `[DATE_1]` placeholders are fine,
  but relative intervals ("day 3 after admit") and date shifting are a gray area under
  Safe Harbor and normally go through Expert Determination **(unverified for intervals)**.
- GDPR treats this same setup as *pseudonymized*, still personal data. HIPAA is kinder.

### 1d. Does HIPAA even apply?

HIPAA binds **covered entities** (providers, plans, clearinghouses) and their **business
associates**. A consumer app where patients paste their own records is usually *not* under
HIPAA, but falls under the FTC Health Breach Notification Rule and state laws (e.g.
Washington My Health My Data). If we sell to clinics, we become their business associate
and HIPAA applies fully.

---

## 2. The other route: send PHI to a vendor under a BAA

If the frontier provider signs a BAA, PHI can go out as-is. Sanitizing becomes defense in
depth, not a legal requirement.

| Provider | BAA? | Terms (as of 10-2026) |
|---|---|---|
| **OpenAI API** | Yes | Self-serve toggle in org settings for orgs with usage history; else email baa@openai.com (Paubox reports >1 month). Covers **only ZDR-eligible endpoints**. BAA and ZDR are separate approvals. Batch API not ZDR-eligible. Consumer ChatGPT never covered. (https://openai.com/api/, https://www.paubox.com/blog/how-do-i-get-a-baa-business-associate-agreement-with-openai, https://www.protecto.ai/blog/openai-hipaa-baa-what-it-actually-covers-and-what-leaves-phi-exposed/) |
| **Anthropic API** | Yes | Sales-enabled "HIPAA configuration" on an API org; **ZDR not required** for the API. Beta features and Console are out of scope. Claude Code needs ZDR (or Enterprise HIPAA config, local mode). Since 2026-06-09 "Covered Models" (Mythos 5, Fable 5) keep 30-day retention even in ZDR orgs **(secondary source)**. Free/Pro/Max/Team: no BAA. (https://support.claude.com/en/articles/15455031-covered-models-under-a-business-associate-agreement-baa, https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to) |
| **Google Vertex AI (Gemini)** | Yes | Covered by Google Cloud BAA; flag the project for HIPAA. Consumer Gemini / AI Studio not covered. Not trained on. Up to 24h caching; abuse-monitoring retention exception via support request — sources disagree on the default. (https://www.aptible.com/hipaa/hipaa-compliant-ai) |
| **Azure OpenAI** | Yes | Microsoft HIPAA BAA (in product terms). Default 30-day abuse-monitoring retention; opt-out via Modified Abuse Monitoring application (EA/MCA). Stored features (threads, files, vector stores) persist regardless. (https://www.specode.ai/blog/openai-llm-api-hipaa) |
| **AWS Bedrock** | Yes | AWS BAA self-serve via AWS Artifact. HIPAA-eligible. No prompt storage by default, not used for training. Runs Claude, Llama, etc. Easiest path. (https://gingerlabs.ai/blog/best-llm-api-providers-with-zdr-and-privacy) |

Takeaways:

- Every big provider signs a BAA for its API/cloud tier. None for consumer apps.
- A BAA is a contract, not proof. NEAR's own pitch: "Zero data retention is a contractual
  promise, not a technical one."
- For a clinic customer, "Claude on Bedrock under the AWS BAA" is the standard,
  boring, defensible answer. The sanitizer then reduces exposure, it doesn't create
  compliance.
- For a vendor with **no** BAA (open models on random hosts, Sage on NEAR), the sanitizer
  is the only thing keeping it legal, so recall matters a lot.

---

## 3. Tools people use

| Tool | Type | Reversible / re-identify? | Notes |
|---|---|---|---|
| **Microsoft Presidio** (now `data-privacy-stack/presidio`) | OSS, regex + spaCy NER | Only via AES `encrypt` → `Decrypt` deanonymizer; not format-preserving. Placeholder maps are DIY. | General PII, weak on clinical text out of the box. (https://presidio.dataprivacystack.org/anonymizer/) |
| **AWS Comprehend Medical DetectPHI** | Cloud API | No (detect only, you do the swap) | ~0.94–0.96 F1 on i2b2 samples in JSL-run tests. AWS says it may miss PHI and isn't de-id by itself. (https://docs.aws.amazon.com/comprehend-medical/latest/dev/textanalysis-phi.html) |
| **Google Sensitive Data Protection (DLP)** | Cloud API | **Yes**: `CryptoDeterministicConfig` / FPE surrogates + `content.reidentify` with your KMS key | Healthcare API de-id is for FHIR/DICOM; free text goes through DLP. (https://docs.cloud.google.com/sensitive-data-protection/docs/pseudonymization) |
| **Azure Health Data Services de-id** | Cloud API | No reverse. TAG / REDACT / SURROGATE; consistent surrogates in batch | 27 entity types incl. all 18. Recommends surrogates over redaction (hides misses). (https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/overview) |
| **Philter** (UCSF) | OSS (BSD-3), regex + blacklists + stats | No | Paper: 99.46% recall UCSF, 99.92% i2b2, precision ~78%. Independent 2025 test: recall 0.79, precision 0.35. (https://www.nature.com/articles/s41746-020-0258-y, https://pmc.ncbi.nlm.nih.gov/articles/PMC12477974/) |
| **John Snow Labs Healthcare NLP** | Commercial, local | Yes (obfuscation with consistent fakes, mapping) | Vendor claims 0.98 micro-F1 on i2b2 2014; on its own notes 0.96 vs Claude Opus 4.8 0.91, GPT-5.5 0.89 (vendor-run). (https://www.johnsnowlabs.com/clinical-de-identification-benchmarks-2026-john-snow-labs-against-openai-databricks-presidio-and-llm-apis/) |
| **Private AI → now "Limina"** | Commercial API / container | **Yes**: numbered markers + `/process/text/reidentify`; **caller holds the map** | Built for the LLM round trip. Closest to our design. (https://docs.private-ai.com/latest/reidentify-text) |
| **Skyflow** LLM Privacy Vault | Commercial vault | **Yes**: tokens, vault holds map, policy-gated detokenize | Map lives server-side at Skyflow. (https://www.skyflow.com/post/private-llms-data-protection-potential-and-limitations) |
| **Protecto** | Commercial | **Yes**: deterministic tokens + vault + `unmask` API; rescans output | Claims all 18 Safe Harbor IDs; marketing-only accuracy. (https://developer.protecto.ai/docs/unmask-a-token/) |
| **Nightfall** | Commercial DLP | Mostly redact/block | Data-loss "AI firewall" for SaaS/LLM prompts; not clinical-specialized. (no good source found) |
| **LLM Guard** (Protect AI) | OSS | **Yes**: `Anonymize(vault)` / `Deanonymize(vault)` | Presidio underneath. (https://levelup.gitconnected.com/inside-llm-guard-the-ultimate-toolkit-for-secure-language-ai-0539f4375c87) |
| **CloakLLM** (cloakllm.dev, MIT) | OSS Python lib + MCP gateway | **Yes**: reversible tokens, audit log | MCP gateway "leak-probe gate passes", pre-release. (https://cloakllm.dev/) |
| **North-StudioFr/cloakllm** | OSS TS proxy | **Yes**: `[PERSON_1]`, in-memory vault, streaming rehydrate | Local SLM/regex detection. (https://github.com/North-StudioFr/cloakllm) |
| **CloakPipe**, **Rehydra SDK**, mirage-proxy, PasteGuard | OSS proxies | **Yes** | Same pattern; Rust ones claim <5 ms. (https://github.com/rohansx/cloakpipe, https://github.com/rehydra-ai/rehydra-sdk) |
| **TIDE 2.0** (Stanford) | OSS | Keyed surrogates | i2b2 2014 recall 0.77 at precision 0.87 default config. (https://arxiv.org/html/2610.07224v1) |

The "anonymize → LLM → rehydrate" proxy is a crowded, commodity pattern. None of the OSS
proxies publish clinical recall numbers. Nobody we found ships a *separate verifier*
gate as a product feature, except Protecto's output rescan and CloakLLM's leak-probe test.

---

## 4. How "clean" gets measured

### Benchmarks

| Dataset | What | Access |
|---|---|---|
| i2b2 2006 de-id | ~900 discharge summaries, surrogate PHI | n2c2 DUA (https://portal.dbmi.hms.harvard.edu/) |
| i2b2/UTHealth 2014 Track 1 | 1,304 longitudinal notes, 296 patients, 25 PHI types | n2c2 DUA |
| CEGS N-GRID 2016 | Psychiatric notes | n2c2 DUA |
| PhysioNet deid (MIMIC nursing notes) | 2,434 notes + the `deid` Perl tool | PhysioNet |
| ASQ-PHI (2025) | 1,051 synthetic clinical *queries*, hard negatives | open (https://pmc.ncbi.nlm.nih.gov/articles/PMC12926592/) |

### Reported numbers

| System | Data | Result |
|---|---|---|
| Best 2014 shared task system (CRF + rules) | i2b2 2014 | F1 0.936 strict; 0.964 entity-level (https://www.sciencedirect.com/science/article/pii/S1532046415001173) |
| NeuroNER (LSTM-CRF) | i2b2 2014 | P 94.3 / R 93.8 / F1 94.0 (https://arxiv.org/pdf/2102.08517) |
| Philter | i2b2 2014 | R 99.92, P ~78.6 (own paper) |
| GPT-4 zero-shot (Altalla et al., Sci Rep 2025) | Real notes, Jordanian cancer center | P 0.993, **R 0.832** (https://www.nature.com/articles/s41598-025-86890-3) |
| GPT-4 one-shot (Gunay 2024, via survey) | i2b2 | ~0.97 P/R/F1 (https://arxiv.org/pdf/2509.14464) |
| DeID-GPT (2023) | i2b2 2014 | first GPT-4 de-id paper; notes human annotators' recall ranges 63–94% (https://arxiv.org/pdf/2303.11032) |
| Best LLM, institution-tuned prompt (Palacios et al., Aug 2026) | 100 pediatric oncology notes, 5,322 spans | **R 0.981**, F1 0.907; TiDE F1 0.779 (https://arxiv.org/abs/2608.17051) |
| Commercial APIs (JSL-run, 2023) | 100 i2b2 notes | F1: JSL 0.96, AWS 0.94, Azure 0.81, GCP 0.77; name recall AWS 90%, Azure 67%, GCP 42% (https://arxiv.org/pdf/2312.08495) |

### What recall is "acceptable"?

- No legal number. Safe Harbor is binary: identifiers removed or not.
- Literature target: F1 ≈ 0.95 (Stubbs 2015); field practice aims at **recall ≥ 0.95,
  ideally ≥ 0.99** on names.
- Even manual human de-id misses things: recall 63–94% depending on annotator (DeID-GPT).
  Gold standards themselves are leaky: Palacios found 227 real PHI spans the gold set
  missed.
- Experts accept residual risk and lean on **surrogates** ("hiding in plain sight",
  Carrell 2013): replace found PHI with realistic fakes so a missed real name blends in.
  ~90% of residual identifiers get concealed, ~10x lower exposure
  (https://www.semanticscholar.org/paper/c8e09840f4e86a1ce99752964b1ccc96aa9c2daf).
  Expert Determination reports routinely cite this.

### Second model as verifier — what exists

| Work | Finding |
|---|---|
| **RedactOR** (ACL 2025 Industry) | Multi-pass: mask what was found, re-run to catch misses. Helps recall, saturates fast. Second LLM pass on audio +~10% recall. (https://aclanthology.org/2025.acl-industry.36.pdf) |
| **Palacios et al. 2026** | 14 multi-agent / ensemble / verifier setups — **none beat one well-tuned prompt**. Ensembles buy a bit of recall for precision and 3x calls. Biggest win: name the institution's own PHI types in the prompt (+79% of misses). Verifiers useful for *auditing gold labels*. (https://arxiv.org/abs/2608.17051) |
| **DR-SL** (Hu et al., Sep 2026) | Local certifier checks dehydrated text before cloud send. Adversarial "is anything left?" prompts gave **many false PASSes** — the model saw residuals but didn't report them. Switching to an *enumeration* probe ("list every identifier you see") fixed much of it but never hit 1.0 on open-vocab categories (e.g. firm names); needed a deterministic hard rule + external attacker re-test + human fallback. (https://arxiv.org/abs/2609.14883) |
| **Surrogate detectability** (Aug 2026) | A post-substitution second-pass detector must still flag surrogates, or layered pipelines break. Faker surrogates are *easier* to detect than real PHI. (https://arxiv.org/html/2608.03172) |
| **Educational PII verifier** (2025) | Verifier model used for precision (cut false positives), not recall. (https://arxiv.org/html/2501.09765v1) |
| **nference / Mayo ensemble** | Ensemble of detectors + surrogates. (https://www.medrxiv.org/content/10.1101/2020.12.22.20248270.full.pdf) |
| **Protecto** | Rescans LLM output for residual PHI (marketing). |

Read: a yes/no "is this clean?" gate is the weakest form of verifier. Errors are
correlated with the first pass, and binary judges under-report. Enumeration + diverse
detectors + hard rules works better.

---

## 5. Known failure modes

| Failure | Example | Why it slips |
|---|---|---|
| Names that are common words | "Rose", "Hope", "Will", "Mark", "Bill", "Grant", "Dr. Brown", "Ms. Lake" | Whitelists of medical/common words suppress them; NER needs context. |
| Long / foreign names | Philter's only UCSF name misses: one patient with a 6-token name | Partial span capture leaves tokens behind. |
| Names in free text, quotes, signatures | "per daughter Maria", "pt states 'tell Jimmy'", "— J.K. RN", initials | Not in name-shaped positions. Relatives count under Safe Harbor. |
| Institutional / local identifiers | Hospital abbreviations, building/unit names, pager numbers, clinic codes | Biggest miss category for off-the-shelf tools (Palacios 2026). |
| Odd-format IDs | MRN `00-12345-6`, accession numbers, device serials, implant lot numbers, license #s, VINs, URLs in portal links, IPs in logs | Regex written for one format. "Any other unique number" (R) is open-ended. |
| Dates | "3/4", "last Tuesday", "Christmas Eve", "POD#2 from 10/12", "age 92", "born in '31" | Relative dates leak when anchored to one real date; age >89 is a date-class identifier. |
| Quasi-identifiers | rare disease + small town + age + occupation | ZIP+DOB+sex identifies ~87% of Americans (Sweeney 2000, https://dataprivacylab.org/projects/identifiability/paper1.pdf). This is the "actual knowledge" clause. LLM agents with web search now re-identify from quasi-IDs (https://arxiv.org/pdf/2605.30848). |
| OCR'd text | "J0hn Sm1th", split lines, table cells, headers/footers with MRN repeated on every page | Tokenization breaks NER; regex misses broken patterns. |
| Placeholder leakage via context | `[NAME_1]` + "the senator from…", "patient's husband, the town's only dentist" | Placeholder is clean, the sentence around it isn't. |
| Placeholder-map tricks | Hashed / derived tokens; `[NAME_Smith_1]`; same placeholder reused across patients | Violates 164.514(c) "not derived from". |
| Over-redaction | Drug names, eponyms ("Parkinson", "Crohn", "Bell's palsy"), "Dr." in "Dr. Martens" | Kills utility; also confuses rehydration. |
| Rehydration errors | Model rewrites `[NAME_1]` as "Name 1" or invents `[NAME_3]` | Swap-back silently fails or mixes patients. |
| Annotation drift | Gold set itself misses PHI | Your recall number is too high. |

---

## 6. NEAR AI confidential compute and Levanto Sage

### What NEAR AI Cloud is

- Private inference: models run in **Intel TDX** confidential VMs with **NVIDIA H200
  GPUs in confidential-computing mode**. TLS terminates inside the enclave; the gateway
  runs in its own CVM. OpenAI-compatible API, same per-token price as non-private.
  (https://docs.near.ai/cloud/private-inference, https://near.ai/blog/building-next-gen-near-ai-infrastructure-with-tees)
- **Attestation:** each response carries a hardware-signed quote tying code + model weights
  to genuine Intel/NVIDIA hardware; verification checks hardware evidence, compares
  measurements to the expected deployment, and binds the TLS connection. No account needed
  to fetch a report. Intel Trust Authority now co-signs attestation tokens.
  (https://near.ai/blog/assume-were-lying-how-to-verify-private-ai,
  https://near.ai/blog/near-ai-cloud-integrates-intel-trust-authority)
- Users: Brave Leo, Venice, Government of Bermuda, Abound. Member of the Confidential
  Computing Consortium. (https://near.ai/)

### The 2026-10-26 Levanto announcement

Blog: "NEAR AI and Levanto Labs Bring Verifiably Private Decision Models to Life"
(https://near.ai/blog/near-ai-levanto-verifiably-private-decision-models). The tweet
(x.com/near_ai/status/2114778299918368873) returned 402 to our fetcher; the blog is the
same announcement.

- Sage now runs on NEAR AI's confidential infrastructure.
- Main pitch: **private prompt routing** — "You can't really have private inference if the
  system making the routing decision sees the data first."
- Also named: "programmatic compliance, transaction screening, agent permissions",
  deciding whether a request should "trigger a compliance requirement" or go to a human.
- Latency chart (yes/no): Sage 238 ms, Haiku 4.5 1,175 ms, Opus 4.8 1,991 ms.
- Model id in the chart: `levanto-sage-v1`. No endpoint, pricing, or GA date. NEAR says it
  will "explore broader distribution" — reads as early.
- The post doesn't name TDX/GPU CC or describe attestation for Sage specifically. Sage is
  proprietary, while NEAR's attestation story is built around open weights; the blog
  doesn't say how weights are measured.
- Deploy configs show Sage on GPU 6 of a NEAR gpu04 box; an earlier PR ran it with
  `SAGE_CONFIDENTIAL=off`, a later one with `SAGE_CONFIDENTIAL=required`; ~216 ms there vs
  ~95 ms on a single-GPU CVM (https://github.com/nearai/cvm-compose-files/pull/371,
  https://github.com/nearai/cvm-compose-files/pull/379).
- **No mention of healthcare, HIPAA, PHI, PII, BAA, or redaction.**

### NEAR AI and HIPAA

- No HIPAA, BAA, or SOC 2 statement found on near.ai, the blog, or the Sage post. The
  only HIPAA mention is generic ("compliance programs built on GDPR, HIPAA, or SOC 2 …
  run on evidence") in the Intel Trust Authority post. Trust Center
  (https://trust.near.ai) is JS-rendered and showed nothing to our fetcher; a DPA exists
  (GDPR-style, not a BAA). **Ask them directly.**

### Does a TEE change the HIPAA picture?

- **No published HHS guidance on TEEs / confidential computing** that we could find.
- Closest is HHS 2016 cloud guidance: a cloud provider that processes or stores ePHI is a
  business associate **even if it can't see the data** (encrypted, no key). A BAA is
  still required; the "conduit" exception does not apply to processing.
  "No-view" lets the customer carry more of the Security Rule duties.
  (https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html)
- By analogy (our inference, consistent with every source): **a TEE does not remove the
  BAA requirement.** It is strong evidence for Security Rule safeguards and breach-risk
  assessment, not a substitute for the contract.
- So: if text sent to Sage-on-NEAR contains PHI, NEAR (and possibly Levanto) would need a
  BAA. The exit check reads the **pre-sanitized or post-sanitized** text — if it's the
  post-sanitized text and that text is truly de-identified, no BAA is needed. If the
  sanitizer missed something, the checker just received PHI.

---

## 7. What this means for our design

- **Decide the legal mode first.** Clinic customer → use a BAA'd frontier route (Bedrock /
  Vertex / Anthropic / OpenAI with HIPAA config) and treat the sanitizer as defense in
  depth. Non-BAA model (open models, Sage on NEAR) → sanitizer must meet Safe Harbor, and
  recall is the whole game.
- **The placeholder map is legal** under 164.514(c) if tokens are random/sequential
  (`[PATIENT_1]`), never hashes or derived from the value, and the map stays local and is
  treated as PHI.
- **Run the exit check on the *sanitized* text only**, so Sage on NEAR never sees raw PHI
  and needs no BAA in the happy path. Ask NEAR anyway whether they'd sign a BAA, since a
  miss means PHI did reach it.
- **Don't ask Sage "is this clean? yes/no".** DR-SL shows binary judges under-report.
  Ask it to *enumerate* suspected identifiers, or run per-category yes/no questions
  ("does this contain a person's name?", "a date other than a year?", "an ID number?",
  "something that singles out one person?"). Block on any hit; use Sage's null/low
  confidence as a block too.
- **Make the checker diverse from the stripper.** Correlated errors kill ensembles
  (Palacios 2026). Stack: deterministic regex + dictionary hard rules (all 18 classes,
  ages >89, ZIPs, dates) → NER/LLM stripper → Sage enumeration check → block or route to
  human. Use realistic surrogates instead of bare `[NAME_1]` where possible so misses
  hide in plain sight — but keep the map exact for rehydration.
- **Measure it ourselves.** Get n2c2 2014 + PhysioNet deid under DUA, plus an adversarial
  set of our own failure cases (common-word names, odd MRNs, OCR noise, relative dates,
  quasi-IDs). Report recall per category, especially names; target ≥ 0.99 on names and
  zero hard-rule escapes. Expect gold labels to be wrong.
- **Quasi-identifiers need a separate pass.** Safe Harbor's "actual knowledge" clause and
  LLM re-ID attacks mean the checker should also ask "could this text single out one
  person?" and generalize rare details (town, job, rare disease + age) — or go to Expert
  Determination (~$5–30k, weeks) for a defensible risk number.
- **Verify rehydration too.** Check every placeholder sent comes back exactly once and no
  new ones appear; fail closed otherwise.
