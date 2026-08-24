# Prior art: wiring wearable/phone cameras into realtime AI assistants

*Raw research-agent report, 2026-08-24. Stars/activity pulled live from the GitHub API. Synthesis in [STACK.md](STACK.md).*

---

## 1. Open-source projects (glasses-first)

### Meta Ray-Ban bridge projects (the hottest lane right now)

**Intent-Lab/VisionClaw** — https://github.com/Intent-Lab/VisionClaw
- **2,525 stars, last push 2026-08-19 — active, working code.** The closest existing thing to "AI sees exactly what I'm seeing" with real agent hooks.
- Mechanism: uses Meta's official **Wearables Device Access Toolkit (DAT) SDK** (iOS + Android) to pull the glasses camera at 24fps, throttles to **~1fps JPEG (50% quality) + 16kHz PCM audio over WebSocket to the Gemini Live API**. Tool calls route through a `ToolCallRouter` to **OpenClaw** running on a Mac (messaging, web search, smart home — "agentic actions").
- Requirements: Ray-Ban Metas with Developer Mode enabled in the Meta AI app, Gemini API key, iOS 17+/Android 14+. Has a phone-camera fallback mode for testing without glasses.
- Known limits: entirely dependent on Meta's proprietary DAT SDK; can't run WebRTC restream and Gemini Live simultaneously (audio device conflict).
- Smaller sibling: **DarlingtonDeveloper/OpenGlass** (13 stars, Feb 2026) — same Ray-Bans + Gemini Live + OpenClaw shape.

**przemek-nowicki/meta-lens-ai** — https://github.com/przemek-nowicki/meta-lens-ai
- 112 stars, push 2026-08-14. Android app (sideloaded APK) on the DAT SDK: talk to ChatGPT/Gemini about what the glasses see, livestream to YouTube/Twitch/Kick, capture + analyze. Early/beta; iOS in progress.

**jasondukes/SpecBridge** — https://github.com/jasondukes/SpecBridge
- 43 stars, push 2026-01. Open-source iOS bridge: **DAT SDK video frames → standard RTMP** (Twitch etc.). The generic "get the glasses feed out of Meta's walled garden into anything that speaks RTMP" piece — useful for ingesting on a Mac and running your own model loop.

**dcrebbin/meta-glasses-api** (a.k.a. meta-vision-api) — https://github.com/dcrebbin/meta-glasses-api
- 689 stars, last push 2025-06 — **the original pre-SDK hack, now mostly superseded.** Browser extension abusing **Messenger**: rename a group chat "ChatGPT", say "Hey Meta, send a message to ChatGPT", the extension monitors the chat on an alt account and forwards to OpenAI/Claude/Perplexity/DeepSeek, replies back into Messenger (Minimax TTS optional). Video path = screenshotting a Messenger video call. Fragile by design — historically important, don't build on it.

**Instagram-live-scrape pattern**: **ghsaboias/glasses-ai** — https://github.com/ghsaboias/glasses-ai (44 stars, Feb 2025). Glasses → Instagram livestream → capture on an M1 Mac → YOLOv8. Proof the "public livestream as camera API" bridge works; latency and ToS make it a dead end vs the DAT SDK.

**affaan-m/JARVIS** — https://github.com/affaan-m/JARVIS (350 stars, push 2026-06). Ray-Ban frames → MediaPipe/ArcFace face ID → OSINT scraping agents → Claude/Gemini synthesis. The "creepy demo" that shows the full agentic loop off a glasses feed.

### OpenGlass / Omi (BasedHardware)

- **BasedHardware/OpenGlass** — https://github.com/BasedHardware/OpenGlass — 4,134 stars but **archived-in-spirit: README says "no longer supported, moved to Omi"; last push 2025-09.** The original <$25 ESP32-S3 (XIAO Sense) DIY glasses: periodic photo capture over BLE → app → Groq/OpenAI/Ollama.
- **BasedHardware/omi** — https://github.com/BasedHardware/omi — **13,255 stars, pushed 2026-08-24 — very active.** OpenGlass lives on as the **`omiGlass` subfolder** (https://github.com/BasedHardware/omi/tree/main/omiGlass): XIAO ESP32-S3 Sense camera board, **photo every few seconds** feeding the Omi app for all-day context/memory; video/audio recording possible with firmware mods. Dev kit: https://www.omi.me/products/omi-glass-dev-kit. Note: **periodic stills + always-on memory**, not realtime video conversation — complementary to the Gemini-Live pattern; the Omi pendant itself is audio-first.

### MentraOS (Mentra Community)

- https://github.com/Mentra-Community/MentraOS — **2,325 stars, pushed 2026-08-24 — very active. MIT-licensed, fully open** (clients, cloud, SDKs, example apps). Cross-vendor smart-glasses OS (Mentra Live camera glasses, Even Realities, Vuzix…).
- Camera API for apps (camera-equipped glasses only, i.e. Mentra Live): photo capture, **managed streaming with restream fan-out to arbitrary RTMP destinations, or unmanaged streaming for full control / local-network ingestion** — docs: https://docs.mentra.glass/camera. The most open "glasses feed → your own server → your own model" path that doesn't depend on Meta.
- Also: **Mentra-Community/Edge_AI_SmartGlasses** — fully **offline** STT/TTS/LLM/VLM assistant on MentraOS.

### Brilliant Labs (Frame / Halo, Noa)

- Org: https://github.com/brilliantlabsAR — hardware + firmware genuinely open source.
- **frame-codebase** (509 stars, complete Frame hardware/firmware), **noa-assistant** (200 stars, but stale — last push Oct 2024; the cloud agent backend), **halo-firmware** (30 stars, pushed 2026-08-23 — new Halo glasses, active), **brilliant_sdk** (88 stars, pushed 2026-08-21).
- Most relevant demo: **frame_realtime_gemini_voicevision** (83 stars, push 2026-02) — Flutter app streaming Frame photos + audio to **Gemini Live** in realtime. Working code for the exact pattern on non-Meta hardware.
- Caveat: Frame/Halo cameras are low-power sensors (Halo: "low-power optical sensor"), not Ray-Ban-class video. Halo (~$299, ~40g) ships with **Noa**, a private cloud agent with memory. https://brilliant.xyz/products/halo

### Standalone/Chinese-ecosystem open hardware

- **Iam5tillLearning/OpenSource-Ai-Glasses** — https://github.com/Iam5tillLearning/OpenSource-Ai-Glasses — 245 stars, push 2026-07. Embedded-Linux standalone glasses platform with C/C++ SDK and **native RTSP video streaming**, BLE, audio, optional display. RTSP-out means any local pipeline can subscribe directly.

---

## 2. Phone-first: what consumer apps do, and where they stop

**Gemini Live camera share (Android + iOS)** — free, all users since ~mid-2025.
- Does: realtime voice conversation about live camera / screen share; works well as "point phone at thing, talk".
- **Falls short of always-on by design**: camera **auto-stops when you leave the Gemini app, put Live on hold, or the screen locks, and doesn't auto-resume** (https://support.google.com/gemini/answer/15274899). No background operation. No custom tools, no custom memory/agent hooks, session length + battery limits.

**ChatGPT** — Advanced Voice with Video shipped Dec 2024 (camera + screen share, paid tiers). **Regression: the July 2026 GPT-Live rebuild (simultaneous listen/speak) currently has no camera or screen share**, no timeline for its return (https://theaicareerlab.com/blog/chatgpt-gpt-live-voice-mode-2026).

**Grok** — Voice Mode + Live Camera on iOS/Android; voice on free tier, some features gated behind SuperGrok/Premium+. Same foreground-app, no-hooks constraints.

**Why build your own** (the concrete gaps in all three):
1. No background / screen-locked operation — "always on while I walk around" is prohibited at the app level, not the API level.
2. No custom tool calls into your own agents (the VisionClaw → OpenClaw pattern; or your harness).
3. No persistent memory you control / transcripts in your own store.
4. No choice of frame rate / cost profile (the DIY pattern is ~1fps JPEG, cheap and sufficient).
5. No custom wake behavior, proactive triggers, or multi-model routing.
- The **Gemini Live API itself has none of these restrictions**: `google-gemini/live-api-web-console` (2,557 stars, React starter with webcam/screen/mic modules, push 2026-06) and `google-gemini/gemini-live-api-examples` (474 stars, push 2026-08) are the canonical build-your-own starting points. https://github.com/google-gemini/live-api-web-console

---

## 3. Bridge patterns people actually use

| Pattern | Status | Notes |
|---|---|---|
| **Meta DAT SDK → app → Live API** | The new default (VisionClaw, meta-lens-ai) | Official since Dec 2025 developer preview; video stream, photo, mic, speaker; Developer Mode required; **public publishing gated until GA "in 2026"** — personal builds fine. https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/ ; Android SDK: https://github.com/facebook/meta-wearables-dat-android (350 stars, active) |
| **DAT → RTMP restream** | Working (SpecBridge; Twitch/Streamlabs are official partners) | Glasses → phone → RTMP server → ffmpeg frame-grab → any VLM. Adds seconds of latency vs direct WebSocket. |
| **Instagram/WhatsApp/Messenger call scrape** | Legacy hack, superseded | glasses-ai (IG live + screen capture), meta-glasses-api (Messenger call screenshots). WhatsApp/Messenger video calls can source glasses camera natively (double-tap capture button mid-call) — people then pointed OBS virtual cam / screen capture at the call window. Fragile, ToS-risky, obsolete now the SDK exists. |
| **Phone as body cam → Mac ingest** | Commodity pieces, no canonical repo | Continuity Camera makes a chest/pocket-mounted iPhone a Mac camera over Wi-Fi; GoPro/Insta360 webcam mode or https://github.com/jschmid1/gopro_as_webcam_on_linux; then any local loop (ffmpeg frame sampling → VLM). |
| **Local always-on VLM watcher** | Working, active | **SharpAI/DeepCamera** — https://github.com/SharpAI/DeepCamera — agentic "watches, understands, remembers" camera platform, RTSP/ONVIF/webcam/iPhone input, local VLMs (Qwen, SmolVLM, LLaVA) or cloud, runs on a Mac mini, talks to you via Telegram/Discord/Slack. Closest open project to "a standing agent that watches a camera and messages me" — surveillance-framed, but the pipeline is exactly the walk-around build minus the wearable. |

---

## 4. Frameworks with working "watch my camera and talk to me" demos

- **LiveKit Agents**: `livekit-examples/vision-demo` (86 stars, push 2026-03) — complete open-source voice+video assistant with a camera-share checkbox; official Vision quickstart (inject latest video frame into LLM context per turn): https://docs.livekit.io/agents/quickstarts/vision/ ; `python-agents-examples` has camera examples incl. adding vision to non-vision LLMs; `agent-starter-swift` gives an iOS client (phone-in-pocket → LiveKit room → agent). Strongest framework path for own infra + tools + memory.
- **Pipecat** (Daily): `pipecat` core has `examples/vision/vision-openai.py`; `pipecat-examples` (339 stars, push 2026-08) includes **Gemini Live starters with camera/screenshare web clients**; "Describe Video" recipe = frame from live stream → model. https://github.com/pipecat-ai/pipecat-examples
- **Daily Bots**: hosted demo at https://vision.dailybots.ai/ ("bot describes your webcam", Anthropic-powered) + `daily-demos/daily-bots-web-demo`. Working, but hosted product rather than something to extend deeply.

---

## 5. Halliday / Rokid / Chinese ecosystems

- **Halliday**: **no camera at all** — G1 and the new G2 (July 2026, $599) are deliberately camera-free display glasses. Irrelevant to a vision build. https://the-gadgeteer.com/2026/07/22/halliday-g2-smart-glasses-camera-free/
- **Rokid Glasses**: camera + proprietary but documented SDKs — **CXR-M** (phone companion: AI interaction, photo capture, audio over BLE/BT socket/Wi-Fi Direct) and **CXR-S** (on-device, YodaOS-Sprite). Community reverse-engineering is where the real access is: **buildwithfenna/rokid-docs** (45 stars) and **Anezium/awesome-rokid** (111 stars, push 2026-08-18). Open platform: https://open.rokid.com/. More photo-capture-oriented than continuous streaming.
- **Chinese/standalone open lane**: OpenSource-Ai-Glasses (embedded Linux + RTSP out) is the notable fully-open entry; RayNeo/INMO are supported targets of MentraOS-style cross-vendor APIs rather than open themselves.

---

## Bottom line for a personal build

- **Working code today, glasses**: VisionClaw (Ray-Bans + DAT SDK + Gemini Live + agent tool-calls, 2.5k stars, active this week) is the reference implementation; MentraOS + Mentra Live is the fully-open alternative with first-class RTMP/unmanaged streaming; omiGlass is the cheap always-on-stills/memory angle.
- **Working code today, phone**: Google's own `live-api-web-console` + LiveKit vision-demo / Pipecat Gemini Live starters — the consumer Gemini app's foreground-only camera is the gap that justifies rolling your own (background capture, custom tools, your own memory).
- **Vapor/legacy to avoid**: Messenger/Instagram scrape hacks (superseded by the DAT SDK), noa-assistant backend (stale ~2 yrs), Halliday (no camera), ChatGPT camera (currently regressed out of GPT-Live).
