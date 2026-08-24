# Camera smart glasses for an "AI sees what I see" assistant — landscape as of 2026-08-24

*Raw research-agent report. Synthesis in [STACK.md](STACK.md).*

TLDR up front: **Mentra Live ($449, ships in 1–3 days) is the only device you can buy today with a documented, open, developer-facing live-video path** (cloud SDK → managed HLS/DASH URL or raw RTMP to your own server, plus on-demand stills as ArrayBuffers). **Meta's toolkit is real and does expose live camera streaming + photo capture to your own phone app, but it's still Developer Preview — you can build for yourself today, you just can't publish.** Brilliant Labs Halo is the open-hardware/display play but its camera is a 640×480 AI-inference sensor, not a video camera. Everything else is either consumer-locked (Xiaomi, Solos, Looktech, Loomos), display-only (Even Realities), or AliExpress spy-glasses jank (which, ironically, does RTSP).

---

## 1. Meta Ray-Ban (Gen 2 / Display / Oakley) + Wearables Device Access Toolkit (DAT)

**Hardware / price (all buyable today):**
- Ray-Ban Meta Gen 2 — from **$379**, 12MP ultra-wide camera, 5-mic array, ~8h mixed battery ([Meta newsroom](https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/), [PhoneArena](https://www.phonearena.com/news/Metas-Gen-2-Ray-Ban-smart-glasses-double-the-battery-and-raise-the-price_id174146))
- Meta Ray-Ban Display — **$799** incl. Neural Band ([Road to VR](https://roadtovr.com/meta-ray-ban-smart-glasses-display-price-release-date-specs/), [Meta blog](https://www.meta.com/blog/meta-ray-ban-display-ai-glasses-connect-2025/))
- Oakley Meta Vanguard — **$499**; Oakley Meta HSTN ~$399 ([Road to VR](https://roadtovr.com/meta-smart-glasses-ray-ban-oakley-vanguard-price-release/))
- New budget "Meta Glasses" line from **$299** (launched 2026-06-23) ([SolidAITech](https://www.solidaitech.com/2026/07/ray-ban-meta-smart-glasses.html)) — *single secondary source; treat the exact date/lineup as lightly verified.*

**What DAT actually exposes today (verified):**
- SDKs for **iOS (Swift) and Android (Kotlin)**, open on GitHub ([iOS](https://github.com/facebook/meta-wearables-dat-ios), [Android](https://github.com/facebook/meta-wearables-dat-android) — Android artifact at **v0.9.0**, Apache-licensed). Your **phone app** gets: **live camera video streaming** (with resolution/frame-rate control, "low-latency" per Meta's own partner writeups), **photo capture**, **microphone audio in**, and **open-ear speaker out**. Display access is listed for Ray-Ban Display. ([Meta FAQ](https://developers.meta.com/wearables/faq/), [DAT docs](https://wearables.developer.meta.com/docs/develop/dat/), [capabilities blog](https://developers.meta.com/blog/explore-whats-possible-with-wearables-device-access-toolkit/))
- Architecture: **glasses → your companion phone app**. There is no glasses-side app runtime and no direct-to-cloud path; your app receives the frames and does whatever it wants with them (partner demos do real-time frame processing: Aira live visual interpretation for blind users, Planta plant ID, OOrion object/text recognition). So yes — **a third-party app CAN get camera frames and mic audio**, which is exactly this use case.
- **v0.6 (April 2026)** added improved video streaming, phone-camera-based stream simulation, Mock Device Kit, and new-device support ([GitHub discussion](https://github.com/facebook/meta-wearables-dat-ios/discussions/141)). Roadmap items Meta itself lists as *not yet done*: voice invocation, Wi-Fi Direct.
- **Constraints (the catch):** still **Developer Preview** as of today. You can register an org in the Wearables Developer Center, run your unpublished app on your own glasses via developer mode, and distribute to testers via release channels — but **general publishing is closed; only hand-picked partners ship publicly**. Meta says GA publishing "in 2026," no date. Country-gated to AI-glasses-supported countries. ([FAQ](https://developers.meta.com/wearables/faq/), [intro blog](https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/))
- **Bottom line for a personal assistant: this is actually fine.** A personal "AI sees what I see" app never needs publishing — developer mode + your own glasses is enough, today.

**Hacks (if you didn't want DAT):**
- **WhatsApp/Messenger video-call bridge**: officially supported — on a WhatsApp/Messenger call, double-press the capture button to switch the call's video to the glasses camera ([WhatsApp Help](https://faq.whatsapp.com/745123461071373)). The bridge trick = call a WhatsApp account you control, capture the incoming video on the far end (WhatsApp Web + screen/tab capture, or a headless browser) and feed frames to your model. Works, but fragile — forum reports show the double-press behavior breaking/changing in updates ([Meta forums](https://communityforums.atmeta.com/discussions/ai-setup-pairing/streaming-from-meta-ray-bans-to-whatsapp-disabled/1225325)), latency is call-grade, quality is call-compressed.
- **Instagram/Facebook live restream**: glasses livestream only to IG/FB ([setup guide](https://www.vr-wave.store/blogs/virtual-reality-prescription-lenses/live-streaming-setup-guide-for-ray-ban-meta-smart-glasses-2)); you can scrape your own live's HLS feed, but latency is many seconds and it's ToS-gray. With DAT available, both hacks are now obsolete for this purpose.

**Battery under streaming:** ~**30–45 min continuous livestream** on a charge, can't charge while streaming (glasses charge in the case) ([VR Wave guide](https://www.vr-wave.store/blogs/virtual-reality-prescription-lenses/live-streaming-setup-guide-for-ray-ban-meta-smart-glasses-2)). DAT streaming to the phone should be in the same ballpark or somewhat better (no cellular uplink from phone battery's perspective, but the glasses radio is the cost either way).

---

## 2. Mentra Live / MentraOS — the developer's pick

- **Price/availability:** **$449** (glasses + charging case + "Infinity Cable" for powered wear), **ships in 1–3 days, buyable today** ([mentraglass.com/live](https://mentraglass.com/live)). Note: launched at $299 early-bird ([Engadget](https://www.engadget.com/wearables/mentras-first-smart-glasses-are-open-source-and-come-with-their-own-app-store-150021126.html), [Gizmodo](https://gizmodo.com/smart-glasses-for-onlyfans-live-streaming-have-arrived-2000710780)); current site price is $449. Shipping since ~Feb 2026 ([9to5Google](https://9to5google.com/2026/01/15/mentra-live-smart-glasses-youtube-livestream/)).
- **Hardware:** 12MP camera (stills 3264×2448), 1080p video, ~112–119° FOV, privacy LED, no display, speakers + mics, touchpad, **Wi-Fi + BLE**, 43g. YC-backed (Mentra), hardware is a Vuzix-related ODM design. ([mentraglass.com/live](https://mentraglass.com/live), [Android Police](https://www.androidpolice.com/these-ray-ban-meta-challengers-will-fulfill-all-your-livestreaming-dreams/))
- **Dev surface (verified in docs — this is the standout):** MentraOS is **MIT-licensed open source** ([GitHub](https://github.com/Mentra-Community/MentraOS)). Apps are TypeScript services using the cloud SDK; hardware arrives over a session object:
  - **Stills:** `session.camera.requestPhoto()` → photo as **ArrayBuffer** in your code — the exact primitive for a "look at what I'm seeing" assistant loop.
  - **Managed streaming:** `session.camera.startManagedStream()` → returns **HLS + DASH URLs** you can point anything at, with optional `restreamDestinations` fan-out to arbitrary **RTMP** ingests (YouTube/Twitch/your own nginx-rtmp).
  - **Unmanaged streaming:** direct RTMP to a URL you specify — lowest latency path to your own server for frame extraction (ffmpeg → frames → VLM).
  - Also mic/audio, speakers, buttons/touchpad; there's a separate **BLE starter kit** for building your own phone app against the glasses ([Mentra-Bluetooth-SDK-Starter-Kit](https://github.com/Mentra-Community/Mentra-Bluetooth-SDK-Starter-Kit)), and a MiniApp store for distribution. Docs: [camera module](https://docs.mentra.glass/camera), [hardware modules](https://cloud-docs.mentra.glass/sdk/hardware-modules).
- **Battery reality:** **livestreaming 40+ min, video recording 1+ h, mixed use 10–12 h**; the Infinity Cable exists specifically so you can run tethered power for continuous use ([mentraglass.com/live](https://mentraglass.com/live)). That cable is the honest answer to "continuous video all day": no glasses do it on internal battery.

---

## 3. Brilliant Labs Halo (and Frame)

- **Price/shipping:** **$299 preorder → $349 → $399** current ([Wareable](https://www.wareable.com/wearable-tech/brilliant-labs-halo-smart-glasses-ai-release-date-price), [Road to VR](https://roadtovr.com/brilliant-labs-halo-smart-glasses-price-release-date/)). Slipped from "late 2025" to Q1 2026 to — per the official product page — "first units rolling off the line, shipments beginning early August" ([brilliant.xyz/products/halo](https://brilliant.xyz/products/halo)). So: **orderable today, mass shipping just starting**; assume crowdfund-style risk.
- **Hardware (verified in official docs):** camera is a **PixArt PAG7982J1, 640×480 global shutter**, 81° FOV — an AI-inference/computer-vision sensor, explicitly *not* a POV video camera (no capture LED, not for social capture). Color **OLEDoS 640×480 display** (up to 120Hz), dual MEMS mics, **BLE 5.3 only — no Wi-Fi**, 2×150mAh (300mAh) battery; marketing claims ~14h all-day use ([docs.brilliant.xyz/halo/hardware](https://docs.brilliant.xyz/halo/hardware/), [Notebookcheck](https://www.notebookcheck.net/Brilliant-Labs-unveils-new-Halo-AI-smart-glasses-with-built-in-display-lightweight-design-and-14-hours-of-runtime.1073945.0.html)).
- **Dev surface:** best-in-class openness — Zephyr RTOS + **on-device Lua 5.3 VM** scriptable over BLE, with direct camera-pipeline control via libmpix (debayer/denoise/resize before encode), plus Python/Flutter host SDKs; hardware design files on GitHub ([Lua API](https://docs.brilliant.xyz/halo/halo-sdk-lua/), [Python SDK](https://docs.brilliant.xyz/halo/halo-sdk-python/), [brilliant_sdk monorepo](https://github.com/brilliantlabsAR/brilliant_sdk)).
- **Reality check for this use case:** you can pull VGA stills over BLE and script everything, and it has a **display for output** — but BLE bandwidth + VGA sensor means "periodic low-res glances," not live video. Older **Frame** ($349, 720p camera, tiny mono display, same Lua-over-BLE model) is discontinued-ish but findable used ([eBay](https://www.ebay.com/itm/156937035471)).

---

## 4. Even Realities G1 / G2 — output-only (no camera, confirmed)

- **G1** ($599 launch, still sold): green microLED HUD, **no camera, no speakers** — deliberate, for all-day wear and ~1.5-day battery ([Engadget review](https://www.engadget.com/wearables/even-realities-g1-review-limited-but-effective-smart-glasses-140059586.html), [evenrealities.com/g1](https://www.evenrealities.com/g1)).
- **G2** (from **$599**, buyable now; optional R1 smart ring $249): same display-only philosophy, refined ([Android Police review](https://www.androidpolice.com/even-realities-even-g2-review/), [store](https://www.evenrealities.com/store)).
- **Dev surface:** official [EvenDemoApp](https://github.com/even-realities/EvenDemoApp) demo/SDK plus a healthy reverse-engineered BLE-protocol scene ([G1 protocol dump](https://github.com/AGiXT/mobile/blob/main/Even%20Realities%20G1%20BLE%20Protocol.txt), [even-g2-protocol](https://github.com/i-soxi/even-g2-protocol), [awesome-even-realities-g2](https://github.com/pangoleen/awesome-even-realities-g2), [Gadgetbridge support](https://gadgetbridge.org/gadgets/others/even_realities/)). You can push arbitrary text/notification content to the HUD — i.e., a clean **output channel** to pair with a camera device or phone. Halliday and similar HUD glasses occupy the same slot.

---

## 5. Other options

| Device | Price / buy today? | Camera & dev access | Verdict |
|---|---|---|---|
| **Rokid Glasses / AI Glasses Style** | $699 (list $799); Style ~$398 w/ Rx; on Amazon US today ([Amazon](https://www.amazon.com/Rokid-Glasses-Translation-Voice-Controlled-Productivity/dp/B0FWRR787L), [Kickstarter](https://www.kickstarter.com/projects/rokid/new-rokid-glassesworlds-lighest-full-function-ai-glasses)) | 12MP IMX681; green HUD (on display model); real dev program: native phone/glasses SDKs (AARs) + JS "JSAR" on-glasses runtime + AIUI Studio agent publishing ([Extentos dev overview](https://extentos.com/docs/ecosystem/platforms/rokid)) | Most dev-open of the Chinese display+camera options, but camera-streaming API surface for third parties is not clearly documented — verify before buying |
| **Xiaomi AI Glasses** | ¥1,999 (~$275), **China only**, import via resellers ([Gizmochina](https://www.gizmochina.com/2025/06/26/xiaomi-launches-its-first-ai-glasses-with-2k-video-recording-voice-assistant-and-a-1999-yuan-price-tag/), [import guide](https://xiaomiforall.com/xiaomi-ai-glasses-usa-buy-guide/)) | 12MP, 2K30 video capped at **10 min/clip**, livestream/video-call support in Chinese apps; **no third-party SDK** | Consumer-locked. Skip |
| **Solos AirGo V2** (and AirGo Vision) | **$299**, launched CES 2026, buyable ([Android Central](https://www.androidcentral.com/wearables/solos-airgo-v2-smart-glasses-are-here-with-camera-enabled-ai-for-usd299-at-ces-2026), [solosglasses.com](https://solosglasses.com/blogs/news/solos-airgo-v2-smart-glasses-starting-at-299)) | 16MP + EIS, FHD video, low-power Wi-Fi; multimodal via their SolosChat app (GPT/Claude/Gemini) | AI-in-*their*-app; no public camera API found. Skip for dev use |
| **Looktech** | $209–299, Kickstarter (HK$9.2M raised), shipping since late 2025 ([Kickstarter](https://www.kickstarter.com/projects/looktech/looktech-smart-ai-glasses-and-hands-free-hd-camera), [New Atlas](https://newatlas.com/consumer-tech/looktech-ai-glasses/)) | 13MP, 4K photo/2K video, GPT/Gemini/Claude voice AI | **No SDK found.** Consumer toy |
| **Sharge Loomos** | $199–299, Kickstarter ($1.5M), shipped 2025 ([CNX](https://www.cnx-software.com/2025/02/24/loomos-ai-smart-glasses-integrate-gpt-4o-offer-a-16mp-camera-and-hi-fi-audio/), [VentureBeat](https://venturebeat.com/games/sharges-loomos-ai-smart-glasses-hits-1-3m-in-5-days-on-kickstarter/)) | 16MP/4K photo, 1080p video, GPT-4o assistant, 450mAh | No dev API found. Skip |
| **AliExpress/Alibaba "spy" Wi-Fi glasses** | ~$40–150, buy today ([Alibaba RTSP suppliers](https://www.alibaba.com/rtsp-glasses-camera-suppliers.html), [example RTSP DVR model](https://www.besovideo.com/en/product/detail?i=65), [Hollyland roundup](https://www.hollyland.com/blog/cameras/glasses-with-camera-and-wi-fi-live-streaming)) | 1080p, Wi-Fi AP mode, some models expose **RTSP** (one claims ~80 min streaming; ~60–120 min battery) | Ugly, janky, zero ecosystem — but **RTSP into ffmpeg/OpenCV with zero permission-begging** is the cheapest possible prototype |
| **Pendants: Limitless / Plaud NotePin / Compass** | Limitless $99 — **Meta acquired Dec 2025, sales ended** ([Layer3Labs](https://www.layer3labs.io/gear/reviews/limitless-pendant)); Plaud NotePin/NotePin S $169 ([plaud.ai](https://www.plaud.ai/products/plaud-notepin)); Compass $99 ([Gearbrain](https://www.gearbrain.com/compass-ai-wearable-productivity-2669403482.html)) | **All audio-only — Compass included** (no camera on shipping Compass models) | Not vision devices |
| **Phone chest/neck mount** | ~$20–40 | Full camera control, RTMP/WebRTC/whatever you code, unlimited compute, powerbank-extendable | Still the honest baseline: highest quality + fully open, just dorky |

---

## 6. Battery for continuous streaming — comparison

| Device | Continuous video streaming | Notes |
|---|---|---|
| Ray-Ban Meta Gen 2 | ~30–45 min | Can't charge while wearing/streaming |
| Mentra Live | 40+ min (1+ h local recording) | **Infinity Cable = tethered power while worn → effectively unlimited** — unique |
| Brilliant Labs Halo | N/A (no video streaming; BLE-only stills) | ~14h claimed mixed use on 300mAh |
| Xiaomi AI Glasses | 10-min clip cap; best-in-class standby (~8.6h mixed) | Livestream drain unpublished |
| Solos AirGo V2 / Looktech / Loomos | Not published; expect ≤1h class | All same-class 400–500mAh packs |
| AliExpress RTSP glasses | ~60–120 min | Some take swappable battery sticks |
| Phone on chest mount | Hours, powerbank-extendable | Only real all-day option besides tethered Mentra |

---

## Recommendation shape

1. **Buy today, least friction:** **Mentra Live** — `requestPhoto()` ArrayBuffers for the assistant loop, unmanaged RTMP to your own box for live video, MIT-licensed OS, tethered-power option.
2. **Best hardware, acceptable friction:** **Ray-Ban Meta Gen 2 + DAT developer mode** — live frames + mic into your own iOS/Android app today; you just can't ship it to others until GA. iOS SDK v0.6+/Android 0.9.0.
3. **Output channel:** Even Realities G1/G2 (or Halo's display) for answers in-lens rather than in-ear.
4. **$50 proof-of-concept this week:** an RTSP Wi-Fi camera-glasses unit → ffmpeg → frames → VLM.

**Verified vs rumored:** everything above marked with official docs/GitHub (Meta DAT capabilities & preview status, Mentra camera API, Halo hardware, Even SDKs) is verified from primary sources. Lightly-sourced items: the June 2026 "$299 Meta Glasses" budget line (one secondary source), Ray-Ban streaming battery figure (retailer guide, not Meta), Looktech/Loomos ship-quality (crowdfunding-class), and Halo's "shipping early August" (vendor's own page — as of today no independent confirmation units are in backers' hands).
