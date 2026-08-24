# Real-Hardware Database for a Game — Data Source Research (2026-08)

Goal: live-ish database of real parts (CPU/GPU/RAM/mobo/SSD/PSU/case/monitor/laptops/whole
systems like DGX Spark, Mac Studio) with **name + specs + street price + performance numbers**
that drive in-game production rates. Player money is fake; the data pipeline must be cheap,
hobby-legal, and hard to break.

---

## TL;DR — the recommended stack (ranked)

| # | Source | Role | Access | Refresh |
|---|--------|------|--------|---------|
| 1 | **Best Buy Products API** | Live US street prices + specs + images for new retail gear | Free API key, official, open registration | Daily (near-real-time capable) |
| 2 | **dbgpu / RightNow-GPU-Database** (TechPowerUp-derived, open source) | GPU spec + relative-perf backbone (2,800+ GPUs) | `pip install dbgpu` / GitHub JSON | Monthly re-pull |
| 3 | **PassMark CPU Mark / G3D Mark** | The one universal perf scalar per CPU/GPU | Scrape (personal-use gray) or paid CSV license | Monthly |
| 4 | **WhatToMine + hashrate.no + minerstat APIs** | GPU/ASIC hashrate per algorithm + watts | Free API keys, real JSON APIs | Daily |
| 5 | **llama.cpp community benches + MLPerf GitHub CSVs** | tokens/sec for AI hardware (DGX Spark, Mac Studio, GPUs) | Open GitHub data, manual curation | Quarterly |
| 6 | **Geekbench Browser JSON** | CPU scores incl. Apple Silicon / laptops | Free but behind Cloudflare — needs headless browser | Monthly |
| 7 | **eBay sold-listing scrape** | Used-market prices (older GPUs, servers) | Scraper (ebayMarketAnalyzer); official Buy APIs are partner-gated | Weekly |
| 8 | **Keepa API** | Amazon price history/live for RAM/SSD/PSU/case breadth | €49/mo, no free tier | If budget allows |
| 9 | **PCPartPicker** | Taxonomy/compat reference only — NOT the price feed | robots.txt: crawl-delay 60, AI bots blocked | One-time + occasional |

Skip: Amazon PA-API (dead — endpoint shut down 2026-05-15, successor Creators API needs
10 affiliate sales/30 days), Newegg (no public catalog API; seller marketplace API only),
Intel ARK OData (closed to new users), UserBenchmark (methodology garbage).

---

## 1. Price sources

### Best Buy Products API — the sleeper winner ⭐
- https://developer.bestbuy.com/ (portal live, verified 200 on 2026-08-24) · docs: https://bestbuyapis.github.io/api-documentation/
- Official, free, open registration (email → API key). REST/JSON over the **entire catalog
  (~1M+ current + historical products)**: price, sale price, availability, full spec
  attributes, images, categories, open-box prices. Pricing updated near-real-time.
- Covers exactly the game's shelf: GPUs, CPUs, RAM, SSDs, PSUs, cases, monitors, laptops,
  prebuilts, Mac Studio/MacBook. Query Builder on the portal for prototyping.
- This is the only major US electronics retailer with a genuinely public API in 2026. Make it
  the primary live price feed; everything else is enrichment.
- Gotcha: catalog is retail-shaped — matching "ASUS TUF RTX 4070 Ti Super" SKUs to a canonical
  part (TechPowerUp entry) needs a fuzzy-matching layer (model-number regex + GPU chip name).

### PCPartPicker — reference, not feed
- No official API. `robots.txt` (fetched 2026-08-24): **Crawl-delay: 60**, disallows `/search/`,
  `/api/`, `/accounts/` etc., and explicitly blocks ClaudeBot/GPTBot/CCBot/Bytespider + a
  content signal `ai-train=no, ai-input=no`. Product pages themselves are allowed to generic
  crawlers at 1 req/min. Cloudflare fronted; aggressive scraping gets you challenged.
- Known unofficial scrapers (all break periodically):
  - https://github.com/soeltjen/PCPartPicker-API (Py3, all regions/product lists)
  - https://github.com/JonathanVusich/pcpartpicker-scraper (full parts-DB snapshots)
  - https://github.com/dbeley/pcpartpicker-scraper (BS4/Selenium)
  - https://github.com/thefirebanks (see topic index: https://github.com/topics/pcpartpicker)
  - https://github.com/N-O-U-R/PcPartPicker-Scraping (Node + ZenRows — i.e. needs a paid
    anti-bot proxy, which tells you how hostile the site is now)
- Practical use: one slow snapshot for the **compatibility taxonomy** (socket ↔ mobo ↔ RAM type,
  PSU wattage, case form factors) and the part-name universe, then never again. Don't build a
  daily price crawler on it — their lowest-price number is aggregated from retailers you can hit
  directly (Best Buy) or via Keepa anyway.

### Amazon: PA-API is dead; Keepa is the real product
- PA-API 5 deprecated 2026-04-30, endpoint **shut down 2026-05-15**
  (https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation).
  Successor **Creators API**: OAuth2, requires accepted Associates account with **10 qualifying
  sales in the last 30 days** — a hobby game can't sustain that. Not viable.
- **Keepa API** (https://keepa.com/#!api): REST/JSON over 6B+ tracked Amazon products, full price
  history (Amazon/3P new/used/Warehouse), refreshes stale data on request. **€49/mo minimum
  (20 tokens/min), no free tier**; €49 tier is plenty for a nightly sweep of a few thousand ASINs.
  This is the correct paid option if you want Amazon breadth + historical price curves (great for
  an in-game "market price wiggles like reality" mechanic).

### eBay (used market)
- Official **Buy/Browse APIs in production are partner-gated**: need eBay Partner Network account
  + Buy API application + contract (https://developer.ebay.com/api-docs/buy/buy-requirements.html).
  Sandbox is open; production approval is a business-model review. Marketplace Insights (sold
  prices) is even more restricted. Don't count on it.
- Practical路: scrape **sold listings** pages — battle-tested tool:
  https://github.com/driscoll42/ebayMarketAnalyzer (CPUs/GPUs/consoles/mobos, median/avg sold
  price, trend plots). Also https://github.com/v-hill/gpu-price-tracker (Selenium, sold GPUs → JSON).
- Weekly cadence is enough; used prices move slowly. Gives the game a plausible second-hand
  economy (RTX 3090s, old Xeons, Threadrippers).

### Geizhals / skinflint (EU) — optional
- No public API. The app's private API was reverse-engineered
  (https://github.com/Vernoxvernax/geizhals-api — bearer token, SSL-pinned app) — fragile.
  Apify rents scrapers (https://apify.com/shahidirfan/geizhals-scraper). Only bother if you want
  EU street prices; for a US-centric game, Best Buy + Keepa + eBay covers it.

### Newegg
- developer.newegg.com is the **marketplace seller API** (feeds for listing your own products) —
  there is no public catalog/price API. Options: their affiliate program's product feeds via
  CJ/Impact networks (application required), or light scraping of search pages
  (e.g. https://github.com/WorleyG/GPUscraper). Low value given Best Buy exists — skip initially.

---

## 2. Performance / benchmark sources

### PassMark (cpubenchmark.net / videocardbenchmark.net) — best "one number per part"
- **Licensing is explicit and real**: they sell CSV data dumps —
  https://www.passmark.com/services/market-analysis.php — model-level averages (~3k rows per
  CPU/GPU/HDD table, updated **daily**) plus a 1M+ row raw-results dump (weekly). Pricing on
  request. If the game ever goes commercial, this is the clean path.
- For hobby use: scrapers exist and the mega-tables are trivially parseable —
  https://github.com/ading2210/passmark-scraper (Python lib, CPU+GPU+HDD, sortable),
  https://github.com/tskubicki/passmark-cpu-scraper (mega page → CSV). Their stance: data is
  **personal use only** — so scrape monthly, cache locally, attribute, and don't republish the
  raw table as a table. Transforming scores into "spreadsheets/tick" inside a game is exactly
  the kind of derived use that has never drawn fire, but it's a ToS-gray zone, not a right.
- Why it wins: single coherent scale across 4,000+ CPUs and 2,000+ GPUs, laptops included
  (separate laptop charts), plus a **price-performance column** they compute themselves.

### Geekbench Browser — the Apple Silicon / laptop gap-filler
- Undocumented JSON API: `https://browser.geekbench.com/processor-benchmarks.json`,
  `/mac-benchmarks.json`, `/search?q=<cpu>` + header `Accept: application/json`, and
  `/v6/cpu/singlecore|multicore` charts. (Write-up:
  https://dev.to/0012303/geekbench-has-a-free-api-benchmark-any-cpu-without-running-tests-yourself-1hb7)
- **Verified 2026-08-24: plain curl now gets a Cloudflare "Just a moment" 403.** Needs a real
  browser context (Playwright headless with cookies) or cloudscraper; once past the challenge
  the JSON is clean. Monthly pull of the two chart JSONs is ~2 requests — trivially polite.
- Essential for M-series Macs (Mac Studio M3 Ultra etc.) and phone/laptop chips PassMark covers
  poorly.

### TechPowerUp GPU Database
- **Official licensing now exists**: https://www.techpowerup.com/database-licensing/ — CPU, GPU
  and SSD DBs, REST API + even an MCP server, "rate limits sized to your usage", custom schema
  free. Enterprise-priced (contact). The site itself 403s non-browser fetchers.
- **Open-source escape hatch (use this):**
  - https://github.com/painebenjamin/dbgpu — pip-installable DB of 2,000+ GPUs (specs, arch,
    process, TDP, **relative performance**), data bundled as JSON.
  - https://github.com/RightNow-AI/RightNow-GPU-Database — 2,824 GPUs across NVIDIA/AMD/Intel,
    prebuilt from dbgpu.
  - https://github.com/dxhibou/Techpowerup_API — scraper if you need live lookups.
- TPU's "Relative Performance" % is a great in-game GPU scalar where PassMark G3D is missing
  (workstation/datacenter cards).

### Tom's Hardware hierarchy charts — real-fps garnish
- GPU: https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html ·
  CPU: https://www.tomshardware.com/reviews/cpu-hierarchy,4312.html
- Editorial tables with average fps at 1080p/1440p/4K across a fixed suite, updated with each
  launch. One page, scrape monthly. Perfect for a "gaming rig produces X fps-hours" mechanic.
  Pure copyright-of-a-table territory — use as calibration, don't mirror.

### Hashrates (mining production rates) — genuinely good APIs
- **WhatToMine**: https://whattomine.com/api-docs — `GET /api/v1/gpus` returns every GPU with
  per-algorithm hashrate + power draw; `/api/v1/asics` same for ASICs; `/api/v1/coins` (legacy
  `/coins.json` still public, verified 200) for difficulty/price context. v1 endpoints need a
  (free-tier) API key; monthly rate limits via `X-RateLimit-*` headers; history endpoints are paid.
- **hashrate.no**: https://api.hashrate.no/docs/cpuEstimates — `/v1/gpuEstimates?apiKey=…`
  (free key on login), even has **CPU mining estimates**.
- **minerstat**: https://api.minerstat.com/ — open JSON for hundreds of ASICs+GPUs: hashrate and
  power per algorithm + hardware specs.
- These are the easiest of all the perf feeds: real JSON, per-part, per-algorithm, watts included
  (→ in-game electricity cost!). Pull daily.

### AI inference tokens/sec (for DGX Spark, Mac Studio, big GPUs)
- **MLPerf Inference**: every round is a GitHub repo of raw results —
  https://github.com/mlcommons/inference_results_v5.1 (…v6.0 etc.) + summary CSVs
  (e.g. https://github.com/mlcommons/mlperf_inference_test_submissions/blob/main/summary.csv).
  Datacenter-class systems (DGX, H100/B200 boxes) with tokens/sec per model. Free, versioned,
  perfect for the exotic top shelf of the in-game store. Also **MLPerf Client**
  (https://github.com/mlcommons/mlperf_client) for consumer laptops/NPUs.
- **llama.cpp community numbers** (curate by hand into a YAML, quarterly):
  - Apple/NVIDIA head-to-head: https://github.com/XiongjieDai/GPU-Benchmarks-on-LLM-Inference
    (M1 Air → M2 Ultra Mac Studio → 4090, LLaMA-3 pp/tg t/s)
  - **DGX Spark measured**: https://github.com/ggml-org/llama.cpp/discussions/16578
  - Maintainer's perf page: https://johannesgaessler.github.io/llamacpp_performance
  - Methodology cheat-sheet + bandwidth heuristics: https://llm-tracker.info/howto/LLM-Inference-Benchmarking-Cheat%E2%80%91Sheet-for-Hardware-Reviewers
- Gap-filling formula for any GPU not in the tables (standard community heuristic):
  `tg tokens/sec ≈ mem_bandwidth_GB/s ÷ model_size_GB × 0.6–0.8` for a fixed reference model
  (say Llama-3-8B Q4_K_M ≈ 4.9 GB). Bandwidth comes free from dbgpu. This lets every GPU in the
  game have an inference rate from two spec numbers + a few measured anchors.

### Spec databases (backbone)
- **TechPowerUp via dbgpu** — see above; the GPU backbone.
- **Intel ARK**: the OData API (https://odata.intel.com/) is **closed to new users** (migrate-to
  "Intel Product Data microservice" for existing users only). Unofficial:
  https://github.com/issy/intel-ark-api (Go REST wrapper). ARK pages themselves are stable and
  parseable if you need per-CPU spec detail beyond name/cores/clock.
- **WikiChip** — MediaWiki-based, so `api.php` gives you wikitext, but the data is
  semi-structured infoboxes; treat as manual reference, not a pipeline.
- **openbenchmarking.org / Phoronix Test Suite** — results exportable as JSON
  (`result-file-to-json`), and there's a Zenodo dump of ~400 test profiles' data
  (https://zenodo.org/record/5535465). Rich but noisy (per-system results, not per-part
  canon) — skip for v1.

---

## 3. Legal / ToS quick table

| Source | Official API? | Hobby-scrape risk | Notes |
|--------|--------------|-------------------|-------|
| Best Buy | ✅ free | none | The clean one. Attribution per their terms. |
| PCPartPicker | ❌ | Medium (Cloudflare, crawl-delay 60, AI-bots blocked) | One-time taxonomy snapshot only. |
| Amazon | Creators API (10 sales/30d) | High (Amazon sues scrapers) | Use Keepa instead. |
| Keepa | ✅ €49/mo | — | Their whole business is selling you this. |
| eBay | Partner-gated | Low (sold-listing scrapes are ubiquitous) | Weekly, gentle. |
| PassMark | Paid CSV license | Low, but data marked "personal use only" | License if commercial. |
| Geekbench | Undocumented JSON | Low (2 pages/month) | Cloudflare challenge — headless browser. |
| TechPowerUp | Paid REST/MCP | — (use open dbgpu dataset instead) | Site 403s bots hard. |
| WhatToMine / hashrate.no / minerstat | ✅ free keys | none | Best-behaved perf APIs of the lot. |
| MLPerf / llama.cpp | ✅ open GitHub | none | Apache/CC-ish, cite rounds. |
| Tom's Hardware | ❌ | Low (1 page/month) | Calibration only, don't republish tables. |

Blanket rules that keep a hobby project unblocked: identify honestly in User-Agent, respect
robots.txt, ≤1 req/min against any non-API site, cache everything locally (SQLite), and never
re-serve a scraped table verbatim — always ship the *derived* game stat.

---

## 4. Mapping benchmarks → in-game production rates

Design principle: **each part class gets one canonical scalar, normalized to a reference part
(= 1.0), then multiplied into a per-job base rate.** Keep the raw benchmark in the DB, compute
game rates at load — rebalancing then never touches the data pipeline.

| Game output | Source metric | Mapping | Reference anchor |
|-------------|--------------|---------|------------------|
| Spreadsheets/tick (office work) | PassMark **single-thread** rating | linear: `rate = base × ST/ST_ref` | Ryzen 5 7600 = 1.0 |
| Renders & compiles/tick | PassMark **CPU Mark** (multi) | `base × (CPUMark/ref)^0.9` (mild sublinear so 96-core Epycs don't trivialize) | same |
| Frames/tick (game streaming rig) | Tom's GPU hierarchy avg fps @1440p, fallback TPU relative-% | linear | RTX 4060 = 1.0 |
| Hashes/tick (mining) | WhatToMine per-algo MH/s **verbatim** | 1 MH/s = N hashes/tick; power draw (W) drives in-game electricity bill | direct physical units — no normalization needed |
| Inference tokens/tick (AI farm) | llama.cpp tg t/s (measured) else `bandwidth/model_size × 0.7` | linear; batchable jobs can use pp t/s | RTX 3090 ≈ 1.0; DGX Spark/Mac Studio from measured threads |
| Storage IO jobs/tick | SSD seq/random specs (TPU SSD DB / Best Buy attrs) | linear on random IOPS | — |
| **Non-producing parts** | specs only | **gates, not rates**: PSU wattage ≥ Σ TDP, mobo socket/RAM type match, case form factor, monitor adds a small "comfort" multiplier | PCPartPicker taxonomy snapshot |

Two balance tricks worth stealing: (a) log-compress any scalar spanning >100× (a B200 vs a
Celeron) — `rate = base × (1 + ln(score/ref))` above the reference — or the endgame collapses;
(b) electricity cost from real TDP/measured watts (mining APIs + dbgpu carry both) makes
"efficiency" an emergent strategy for free, since perf/W is real data.

Whole systems (DGX Spark, Mac Studio, laptops): treat as pre-assembled bundles — price from
Best Buy/street, CPU rate from Geekbench, GPU/AI rate from the llama.cpp/MLPerf anchors.
DGX Spark specifically: ~$3,999–4,699 street, measured llama.cpp numbers in discussion #16578.

---

## 5. Suggested pipeline (v1, one box, cron)

```
nightly : bestbuy_sync.py      (categories: GPU/CPU/RAM/SSD/PSU/case/monitor/laptop → sqlite)
nightly : mining_sync.py       (whattomine /gpus + /asics, hashrate.no fallback)
weekly  : ebay_used.py         (sold-listing medians for a watchlist of ~200 legacy parts)
monthly : passmark_pull.py     (mega tables → cpu_mark, single_thread, g3d)
monthly : geekbench_pull.mjs   (playwright: processor-benchmarks.json + mac-benchmarks.json)
monthly : dbgpu refresh + toms_hierarchy.py (calibration constants)
quarterly (manual): curate ai_tokens.yaml from MLPerf round + llama.cpp discussions
```
Matching layer (the real work): canonical `part_id` keyed on chip/model, fuzzy-match retail SKU
titles → part_id (regex for model numbers gets ~90%; hand-map the rest once).

---

*Researched 2026-08-24. Live checks done: pcpartpicker robots.txt (fetched), Best Buy portal
(200), Geekbench JSON (Cloudflare 403 via curl), whattomine /api/v1/gpus (401 — key needed) and
legacy /coins.json (200, open).*
