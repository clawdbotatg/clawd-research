# Prior Art: Fake-Budget / Real-Hardware Tycoon Game

## The headline answer

**Nothing found does "fake budget, real live hardware catalog."** The pieces all exist separately:

- **Real licensed parts, fake static prices**: PC Building Simulator 1/2 (real SKUs, real benchmark-derived numbers, but a hand-curated catalog frozen at ship time).
- **Fake budget, real *live* assets**: fantasy sports salary caps and fantasy stock games (MarketDraft, Visionrare, Fantasy Funds) — but the assets are players/securities, never hardware.
- **Fake parody parts, live crypto prices**: PC Creator 2 ("INTOL", "ASOS" knockoff parts with live coin price feeds).
- **Real hardware → real output economics, no game**: NiceHash/WhatToMine-style profitability calculators are exactly the "this GPU produces X hashes worth $Y/day" data layer, presented as a spreadsheet instead of a game.

The combination — scraping the actual retail catalog (a 5090 at today's Newegg price, a DGX Spark at $4,699) into a salary-cap draft where the parts then *produce* at benchmark-realistic rates — appears to be an open lane.

---

## PC building sims (the hardware-fidelity model)

**PC Building Simulator 1/2** — Career mode: repair shop, customer orders, buy parts, assemble, benchmark, get paid. 40+ brands, 1,200+ licensed real components; the in-game 3DMark scores (Time Spy, Port Royal, Speed Way) are modeled from **real 3DMark input values**, with real interaction effects (RAM feeds the CPU score only). *Steal:* real benchmark numbers as the production function — players' real-world knowledge ("the 9800X3D punches above its price") becomes game skill, which is the entire fantasy-sports magic. *Avoid:* licensing 40 brands is a huge BD lift; PCBS's catalog is static and ages out — a scraper-driven catalog dodges both, and nominative use of part names/prices (PCPartPicker-style, no logos/3D models) likely avoids the licensing problem entirely. ([Epic support on simulated benchmarks](https://www.epicgames.com/help/c-202300000001624/c-Trending_0/which-benchmarks-are-simulated-in-pc-building-simulator-2-a202300000015796), [3DMark bundle](https://benchmarks.ul.com/news/introducing-the-build-benchmark-bundle-3dmark-pc-building-simulator), [Steam](https://store.steampowered.com/app/621060/))

**PC Creator 2** (mobile) — Build PCs from 3,000+ *parody* parts, fulfill orders, run a mining farm with **live coin prices**. Proof there's mobile appetite for the exact fantasy (build rig → rig mines → number goes up), and proof the live-data hook works; its weakness is the fake parts drain the fantasy. ([App Store](https://apps.apple.com/us/app/pc-creator-2-computer-tycoon/id1604170642), [wiki mining page](https://pc-creator.fandom.com/wiki/Bitcoin_mining))

## Crypto-mining idle games (the tick-production loop)

**RollerCoin** — The closest loop shape to the concept: buy virtual miners → arrange them in rooms → every ~10 min a "block reward" pool is **split pro-rata by your share of total network hashpower**. Sticky because rewards are relative, not absolute: the shared pool makes it inherently competitive and **self-deflating** — as everyone's hashrate inflates, your share doesn't, so the exponential arms race cancels out at the payout layer. Mini-games grant *temporary* hashrate, giving active players an edge over pure idlers. *Steal:* pro-rata shared-pool payouts as the inflation valve + the temporary-boost active layer. *Avoid:* real-crypto payouts (regulatory mess, attracts botters not gamers). ([Bitrue review](https://www.bitrue.com/blog/rollercoin-game-review), [Coingape](https://coingape.com/rollercoin-cryptocurrency-mining-game-review/))

**CryptoTab / browser miners** — Not really games; loop is "leave it on." Lesson is negative: when output is real money, the "game" collapses into an extraction calculus and retention is mercenary. Keep the budget AND payouts fake. ([Cointelegraph via TradingView](https://tr.tradingview.com/news/cointelegraph:9b3729c2f094b:0-browser-based-crypto-mining-in-2025-still-viable-or-virtually-dead))

**Roblox Bitcoin Miner / Miners World** — Kid-tier loop: place miners, earn, **prestige resets** (wipe cash/gear for permanent tokens/multipliers), constant seasonal events + promo codes as re-engagement pings. *Steal:* event cadence; prestige-token meta-currency that survives round resets. ([Miners World prestige wiki](https://roblox-miners-world.fandom.com/wiki/Prestige), [namu overview](https://en.namu.wiki/w/Bitcoin%20Miner))

## Business/tycoon sims (what depth to add, what to skip)

**Game Dev Tycoon** — Loop: pick topic+platform combo, allocate dev sliders, ship, get scored. Works because of *hidden combo knowledge* the community mines and shares — same energy as "which GPU is the value pick this week." Small decision surface, big meta-game.

**Software Inc** — Deep everything-sim (buildings, HR, market). Reviews consistently say it's overwhelming; its market sim (a good product fails if launched against a bigger competitor) is a nice timing mechanic. *Avoid:* the sprawl — a competitive round-based game wants a tight decision surface. ([Steam](https://store.steampowered.com/app/362620/Software_Inc/), [reviews](https://steamcommunity.com/app/362620/reviews/?browsefilter=toprated))

**Startup Company** — Produce "components" via employees, combine into features, sell — a crafting-tree framing of production that maps well to "machine produces spreadsheets/inference."

**Computer Tycoon / Hardware Tycoon** — Design-your-own-hardware through computing *history* (invent CPUs from 1970s onward; the Steam Hardware Tycoon goes full ISA/pipeline design). Mixed reviews; niche. Relevant mostly as confirmation that the *history/catalog* fantasy has fans but "design fake chips" is the crowded lane — "shop real chips" is not. ([Computer Tycoon](https://store.steampowered.com/app/686680/Computer_Tycoon/), [Hardware Tycoon](https://store.steampowered.com/app/4490710/Hardware_Tycoon/), [itch original](https://haxor1337.itch.io/hardware-tycoon))

## Idle/incremental design (making ticks and resets feel good)

- **Prestige math**: reset trades current progress for a permanent multiplier; it works because each reset is an *investment*, not a loss. For a competitive seasonal game, translate "permanent multiplier" into cosmetic/reputation meta-progression (titles, hall-of-fame, unlocked catalog tiers) — never a power multiplier, or season 5 newcomers can't compete. ([Incremental game — Wikipedia](https://en.wikipedia.org/wiki/Incremental_game), [Universal Paperclips — Wikipedia](https://en.wikipedia.org/wiki/Universal_Paperclips))
- **Universal Paperclips' real trick** isn't prestige — it's **phase shifts**: the game reinvents its verbs three times (clip shop → algorithmic trading → space swarm). A season could do this: early = shopping/assembly, mid = market optimization, late = who pivots fastest when the event drops.
- **Inflation control**: idle games pair exponential *costs* with linear-ish *production* and softcaps (e.g. `100+x → 100+√x`) to kill runaways. But the cleaner tools for a competitive game are RollerCoin's pro-rata pool and hard round resets — a 2-week round simply never lives long enough to inflate. ([Math of Idle Games](https://www.gamedeveloper.com/design/the-math-of-idle-games-part-i), [Balancing Idle Idol](https://www.gamedeveloper.com/design/balancing-tips-how-we-managed-math-on-idle-idol))

## Seasons & competitive economies

- **PoE / D2 ladder model**: ~13-week leagues, everyone starts broke in a fresh economy, each league ships one new mechanic, and good mechanics get folded into the core game — **the season is also the dev cycle**. This is the strongest template for rounds: fresh economy = the great equalizer, new mechanic = the retention hook, end-of-league merge = your progress isn't "deleted," it's archived. ([league cycle explainer](https://www.arpgseasons.com/en/guides/poe-league-cycle), [ResetEra thread](https://www.resetera.com/threads/thoughts-on-seasons-leagues-in-arpgs-diablo-path-of-exile-etc.363881/))
- **Pirate Nation** — Multi-axis leaderboards per season (skill / collection / social) so more player types can "win"; points as soulbound onchain tokens. *Steal:* multiple leaderboard lanes (raw income vs. efficiency-per-dollar vs. weirdest viable build). ([GamesBeat](https://gamesbeat.com/proof-of-play-launches-pirate-nation-season-3/), [ChainPlay](https://chainplay.gg/blog/pirate-nation-season-3-launch/))
- **Wolf Game** — Its "risk protocol" (wolves tax sheep's yield, can steal newly minted assets; each side's value depends on the other side's behavior) is the best example of *player-vs-player yield interference* in an idle economy — a possible PvP spice: rival machines competing for the same contract pool, or "botnet" attack roles. ([nftnow guide](https://nftnow.com/guides/wolf-game-nfts-a-guide-to-gameplay-wool-and-more/), [Woolpaper](https://wolf.game/woolpaper))
- **Dope Wars** — Community revival of a classic arbitrage loop with seasonal "hustle" leaderboards; evidence that simple buy-low-sell-high + leaderboard still retains onchain. ([dopewars.gg](https://dopewars.gg/), [HN](https://news.ycombinator.com/item?id=42199418))
- **EVE Online** — Two portable principles: sinks players *choose* (perceived-value sinks beat forced taxes), and CCP's factory-speculation fix (upkeep costs as a land-value tax to punish hoarding productive assets) — directly applicable if players can corner "inventory" of a hot GPU. ([player-driven economy overview](https://timesaver.gg/blog/best-games-player-driven-economies-2026), [economy design guide](https://www.numberanalytics.com/blog/ultimate-guide-economy-design-game-production))

## Fantasy-market games (the structural core)

- **DFS salary cap (DraftKings $50k)** — The exact skeleton: fixed fake budget, real assets priced by projected output, and the whole skill is finding *mispriced* assets ("value plays"). The critical design detail: DFS **re-prices players continuously** based on form/matchup. The hardware analog is free — retail prices already move, and MSRP-vs-street-price gaps, sales, and stock-outs create the mispricing drama automatically. ([Stokastic DFS 101](https://www.stokastic.com/articles/dfs-strategy/dfs-101-beginner-guide), [Bleacher Nation on salary caps](https://www.bleachernation.com/daily-fantasy/2026/04/27/what-is-a-salary-cap-contest/))
- **Visionrare** (fantasy startup equity, TechCrunch 2021) and **MarketDraft / Fantasy Funds** (fantasy stock/crypto portfolios) — fake budget on real live-priced assets, competitive leaderboard. Closest structural relatives; none touch hardware. ([TechCrunch on Visionrare](https://techcrunch.com/2021/10/06/fantasy-equity-nft-game-wants-you-to-spend-real-money-buying-fake-shares-of-real-startups/), [MarketDraft](https://marketdraft.com/))
- **"Fantasy PC building" existence check**: only informal Reddit/forum "best build for $500 on PCPartPicker" competitions — humans already play this game manually with no scoring engine. That's demand evidence, not competition. ([example thread](https://pcpartpicker.com/forums/topic/472468-budget-gaming-pc-build), [PCMR build guides](https://pcmasterrace.org/builds))

---

## Synthesis for the concept

1. **The open lane is real**: live-scraped retail catalog + benchmark-derived production rates + DFS salary cap + RollerCoin pro-rata payouts + PoE season resets. Each piece is proven somewhere; nobody has composed them.
2. **Differentiation vs. PCBS**: don't license — *reference*. PCPartPicker references every SKU and price with no licenses; parts are data rows with real names, not 3D models.
3. **Inflation plan**: short rounds + shared reward pools (relative payout) beat softcap math; keep cross-season progression cosmetic/reputational so every round is winnable by a newcomer.
4. **The killer hook none of the prior art has**: the meta shifts *because reality shifts* — a GPU price drop, a new chip launch, a DGX restock mid-round is a live balance patch you didn't have to write. DFS proves players love hunting mispriced assets; here the mispricing is generated by Newegg.
5. **Watch out for**: PC Creator 2's fake-parts trap (kills the fantasy), Software Inc's sprawl (keep decisions to shop/assemble/allocate), real-money payouts (CryptoTab lesson), and permanent power carryover across seasons (kills round freshness).
