# "AI sees exactly what I'm seeing" — stack research

*Researched 2026-08-24 (three parallel web-research passes: hardware, realtime APIs, prior art). Austin's framing: "Meta Ray-Bans + Gemini Live + GPT Realtime voice will kill the screen."*

## TLDR — the recommended stack

**Meta Ray-Ban Gen 2 ($379) + Meta's official Wearables Device Access Toolkit (DAT) + Gemini Live API (`gemini-3.1-flash-live-preview`) ≈ $25/month at 1 hr/day.** This exact stack already exists as working open source: **[VisionClaw](https://github.com/Intent-Lab/VisionClaw)** (2.5k stars, active this week) — Ray-Bans camera at ~1fps JPEG + 16kHz mic over WebSocket into Gemini Live, with tool calls routed to an agent on a Mac. That last part is the hook for us: the tool-call router is where the clawd harness / PM plugs in.

The intuition in the prompt was right, with one correction: **GPT Realtime is the wrong voice layer for this** — it has no native video, frames must be stuffed into context as images and get re-billed every turn (~$150–450/mo realistic vs ~$25/mo on Gemini Live). Gemini Live is the only major API with a native video-in socket, and it has "proactive audio" (the model can watch silently and only speak when useful — the wearable behavior you actually want).

## Why this is suddenly possible (the Dec 2025 unlock)

Meta shipped the **Wearables Device Access Toolkit** — official iOS/Swift + Android/Kotlin SDKs ([iOS](https://github.com/facebook/meta-wearables-dat-ios), [Android](https://github.com/facebook/meta-wearables-dat-android), Apache-licensed) that give **your own phone app** live camera video (resolution/framerate control), photo capture, mic in, and speaker out from the glasses. Still Developer Preview: you can't *publish* an app until GA ("in 2026"), but developer mode + your own glasses works today — which is all a personal build needs. The old hacks (Messenger-call screenshots, Instagram-live scraping) are obsolete.

Constraint that matters: **~30–45 min continuous streaming per charge** on Ray-Bans, and they only charge in the case. Continuous all-day vision is not a thing on any glasses' internal battery.

## The three layers

### 1. Eyes (hardware)

| Option | Price | Why / why not |
|---|---|---|
| **Ray-Ban Meta Gen 2 + DAT dev mode** | $379 | Best hardware (12MP, 5 mics, wearable in public). Official live-video SDK to your own app. Can't publish until GA; ~30–45 min streaming battery. **The pick.** |
| **Mentra Live** ([MentraOS](https://github.com/Mentra-Community/MentraOS), MIT) | $449 | The fully-open alternative: TypeScript cloud SDK, `requestPhoto()` → ArrayBuffer, managed HLS/DASH or **raw RTMP to your own server**, and an "Infinity Cable" for tethered power = unlimited streaming. Docs read like they were written for this exact project. No display. |
| Brilliant Labs Halo | $399 | Open hardware + Lua VM + **in-lens display**, but camera is a 640×480 CV sensor over BLE — periodic glances, not video. Shipping just starting. |
| Even Realities G1/G2 | $599 | No camera — but the best **output channel** (in-lens HUD) if we ever want answers on-eye instead of in-ear. |
| AliExpress RTSP spy glasses | ~$50–150 | Janky, but native **RTSP → ffmpeg → VLM** with zero permission-begging. Cheapest proof-of-concept. |
| Phone chest mount | ~$30 | The honest baseline: best camera, powerbank all day, fully open. Dorky. |

Skipped: Xiaomi (China-only, no SDK), Solos/Looktech/Loomos (consumer-locked), pendants (Limitless — Meta acquired it, Plaud, Compass — all audio-only).

### 2. Brain (realtime API)

| Option | Video in | Cost @ 1hr/day | Verdict |
|---|---|---|---|
| **Gemini Live** `gemini-3.1-flash-live-preview` | **Native**: ~1fps JPEG frames over WebSocket, 66–258 tok/frame | **≈ $21–29/mo** (per-minute billing: $0.005/min audio + $0.002/min video in, $0.018/min audio out) | **The pick.** Only native video socket. Proactive audio + tunable VAD + affective dialog. Needs session-resumption handling (socket dies ~10 min; `contextWindowCompression` → unlimited duration). |
| GPT Realtime 2.1 (+ frame injection) | No — images via `input_image`, sampled by e.g. LiveKit (1fps while talking) | ~$150–450/mo realistic (context re-billing; mini tier maybe $45–150) | Great voice/tools, wrong architecture for continuous vision. 10–20× the cost. |
| Qwen3.5-Omni realtime | Native (1fps frames, WebSocket + WebRTC) | TBD (console-only pricing) | Architectural twin of Gemini Live; **open weights (Apache-2)** → the future local option on a DGX Spark / Mac Studio. |
| Grok Voice Agent API | No (app's camera mode has no API) | — | Audio-only API today. |
| Anthropic | No realtime/voice/video API at all (confirmed) | — | Only usable as the VLM in a frame-sampled pipeline. |
| Local (Qwen3-Omni-30B / Moondream Photon) | Yes | $0 marginal | Private, but ~1–3s responses on consumer hardware and you own the whole pipeline. Later. |

### 3. Hands (the agent hook)

The consumer apps (Gemini Live camera share, ChatGPT, Grok) all die at the same wall: **foreground-only, screen-lock kills the camera, no custom tools, no memory you control.** That's an app-level restriction, not an API one — the Gemini Live *API* has none of it. Building your own client is what buys: background operation, tool calls into the clawd harness/PM (VisionClaw's `ToolCallRouter` → OpenClaw pattern maps 1:1 onto our PM verbs), transcripts into our own store, frame-rate/cost control, proactive triggers.

Frameworks if we don't fork VisionClaw: **LiveKit Agents** (first-class Gemini Live + OpenAI plugins, iOS starter client, vision quickstart) or **Pipecat** (Gemini Live starters with camera clients). Google's own [live-api-web-console](https://github.com/google-gemini/live-api-web-console) (2.5k stars) is the fastest desk-test harness.

## Build path

1. **Tonight, $0**: run [live-api-web-console](https://github.com/google-gemini/live-api-web-console) with a Gemini API key — laptop webcam + mic into Gemini Live. Validates the brain + the feel.
2. **This week, $0**: phone as camera (VisionClaw has a phone-camera fallback mode specifically for testing without glasses) — walk around, talk to it.
3. **Buy**: Ray-Ban Meta Gen 2, enable Developer Mode in the Meta AI app, run VisionClaw (iOS 17+/Android 14+); swap its OpenClaw tool router for the clawd harness PM endpoints.
4. **Hedge/2nd source**: Mentra Live if Meta's preview gating ever bites, or when tethered all-day streaming matters.
5. **Later, private**: Qwen3-Omni local on the DGX Spark (ties into the local-ai research).

## Gotchas to remember

- **Battery is the real limit**: ~30–45 min streaming on Ray-Bans. Design for burst sessions ("look at this with me") not always-on; Mentra + cable is the only all-day story.
- **Gemini Live session plumbing is mandatory**: `contextWindowCompression` (else 2-min audio+video limit), `sessionResumption` (socket dies ~10 min), ephemeral tokens on device.
- **If ever on GPT Realtime**: aggressively evict old frame items from context or costs explode (frames re-billed every turn).
- VisionClaw known limit: can't run WebRTC restream and Gemini Live simultaneously (audio device conflict).
- Verify before building: proactive audio on `gemini-3.1-flash-live-preview` specifically (confirmed on 2.5-flash-native-audio).

## Full agent reports

Raw findings with all sources: [hardware.md](hardware.md) · [apis.md](apis.md) · [prior-art.md](prior-art.md)
