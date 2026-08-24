# Realtime video+voice AI APIs for a "sees what I see" wearable — research findings (2026-08-24)

*Raw research-agent report. Synthesis in [STACK.md](STACK.md).*

Legend: **[V]** = verified against official docs/announcements this session · **[L]** = likely but from secondary sources or small-model summarization of docs (spot-check before building) · **[E]** = estimate/calculation.

---

## 1. Google Gemini Live API — the only major *native video-in* realtime API

**Status: Preview (still not GA), WebSocket-based.** [V]

**Models** (from Google's live pricing/docs pages) [V]:
- `gemini-2.5-flash-native-audio-preview-12-2025` — native audio, 128k context
- `gemini-3.1-flash-live-preview` — **newer generation live model** (the one to build on; note per-minute pricing option below)
- `gemini-3.5-live-translate-preview` — speech translation specialty model
- (Older half-cascade `gemini-2.5-flash-live` models: 32k context)

**Video input mechanics** [V]:
- Frames sent as **individual JPEG/PNG images over the WebSocket** (`realtimeInput` with a Blob + mimeType) — there is no video codec stream; "video" = you sample the camera and push stills.
- **Max ~1 frame per second**; recommended 768×768 @ 1 FPS.
- `mediaResolution` knob: default ≈ **258 tokens/frame**, `MEDIA_RESOLUTION_LOW` ≈ **66 tokens/frame** (≈300 vs ≈100 tokens per second of video). Audio input tokenizes at **32 tokens/sec**. [V — Google tokens doc]

**Audio** [V]: input raw 16-bit PCM @ 16 kHz LE (`audio/pcm;rate=16000`); output always 24 kHz PCM.

**Session limits** [V]:
- Defaults: **15 min audio-only, 2 min audio+video** — BUT enabling `contextWindowCompression` (sliding window) makes duration **unlimited**. Mandatory for a wearable.
- The WebSocket connection itself dies ~every 10 min → use `sessionResumption` (server sends resumption tokens, valid 2 h; `GoAway` message with `timeLeft` warns before disconnect). The wearable client must implement reconnect-with-handle.

**VAD / proactive audio** [V]:
- Automatic server VAD on by default, tunable (`startOfSpeechSensitivity`, `endOfSpeechSensitivity`, `prefixPaddingMs`, `silenceDurationMs`), or manual `activityStart`/`activityEnd`.
- **Proactive audio** ("model can decide NOT to respond when content isn't relevant" — i.e., it can watch silently and speak up when useful, exactly the wearable behavior) — docs say supported on 2.5 Flash native audio via `v1beta`; whether 3.1-flash-live supports it wasn't confirmed. **[L — verify on the capabilities page for 3.1]**
- Affective dialog (tone-matching) also available. [V]

**Auth for on-device clients** [V]: ephemeral tokens are the recommended pattern (don't ship the API key on the wearable).

**Pricing** [V from Google pricing page]:
| Model | Input | Output |
|---|---|---|
| 2.5-flash-native-audio | $0.50/1M text; **$3.00/1M audio & video** | $2.00/1M text; $12.00/1M audio |
| **3.1-flash-live-preview** | $0.75/1M text; $3.00/1M **or $0.005/min** audio; **$1.00/1M or $0.002/min image/video** | $4.50/1M text; $12.00/1M **or $0.018/min** audio |

The per-minute billing option on 3.1-flash-live is the headline for this use case — flat, predictable continuous-streaming cost.

**Ecosystem** [V]: official partner integrations — LiveKit Agents, Pipecat (Daily), Vision Agents (Stream), Fishjam, Voximplant, Agora.

Sources: [Live API capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities) · [Session management](https://ai.google.dev/gemini-api/docs/live-api/session-management) · [Firebase limits & specs](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs) · [Pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Tokens doc](https://ai.google.dev/gemini-api/docs/tokens) · [Live API overview](https://ai.google.dev/gemini-api/docs/live-api)

---

## 2. OpenAI Realtime API (gpt-realtime family) — audio-native, images yes, "video" = frames-as-images

**Image input: YES, native since gpt-realtime GA (Aug 2025).** [V] Mechanics: `conversation.item.create` with content type **`input_image`** (base64 data-URL or file ID), `detail: high|low|auto|original`. The model grounds the spoken conversation in the image. [V — OpenAI API reference]

**Video input: NOT a native stream.** No video track ingestion in the API itself; the pattern (implemented by LiveKit Agents) is **sampling camera/screen frames and sending each as an image message**. LiveKit's OpenAI plugin: `video_input=True`, default sampler = **1 frame/sec while user speaks, 1 frame per 3 sec otherwise**, custom `video_sampler` supported (Python only currently). [V — LiveKit docs] So OpenAI is architecture (b) by construction.

**Transport** [V]: WebRTC (since Dec 2024), WebSocket, and SIP (dedicated SIP ranges + GeoIP routing added Jan 2026). The Realtime **Beta interface was removed May 12, 2026** — GA interface only.

**Models** [V names / L dates]:
- `gpt-realtime` (GA Aug 2025), `gpt-realtime-mini`
- **`gpt-realtime-2`** — configurable reasoning speech-to-speech (≈May 2026)
- **`gpt-realtime-2.1` + `gpt-realtime-2.1-mini`** — July 2026: better alphanumerics, noise/silence handling, interruption behavior; mini is a distilled cheaper reasoning model. [V — MarkTechPost July 2026 + changelog]
- Also `gpt-realtime-translate`, `gpt-realtime-whisper` (streaming STT).

**Pricing** (per 1M tokens, OpenAI pricing page) [V]:
| | Audio in | Audio in cached | Audio out | Text in | Image in | Image cached |
|---|---|---|---|---|---|---|
| gpt-realtime-2.1 / -2 / gpt-realtime | $32 | $0.40 | $64 | $4 | **$5** | $0.50 |
| gpt-realtime-2.1-mini | **$10** | $0.30 | **$20** | $0.60 | **$0.80** | $0.08 |

Token rates: user audio ≈ **10 tokens/sec** (600/min), assistant audio ≈ **20 tokens/sec** (1,200/min). [V]

**The cost trap** [V, measured by third parties]: Realtime bills the *accumulated conversation context on every response*, so raw per-minute list price balloons with turn count. Real-world measurements (4,000 sessions, HackerNoon 2026): **$0.18–0.46/min uncached, $0.05–0.10/min with prompt caching** for voice-only. Images sitting in context get re-billed too unless you truncate/expire old items — for a wearable you MUST aggressively delete stale frame items from the conversation.

Sources: [gpt-realtime announcement](https://openai.com/index/introducing-gpt-realtime/) · [OpenAI pricing](https://developers.openai.com/api/docs/pricing) · [Changelog](https://developers.openai.com/api/docs/changelog) · [LiveKit OpenAI realtime plugin](https://docs.livekit.io/agents/models/realtime/plugins/openai/) · [conversation.item.create ref](https://platform.openai.com/docs/api-reference/realtime-client-events/conversation/item/create) · [webrtcHacks on gpt-realtime WebRTC](https://webrtchacks.com/how-openai-does-webrtc-in-the-new-gpt-realtime/) · [HackerNoon measured pricing](https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions)

---

## 3. Anthropic — no realtime API, confirmed

- **The Claude API has no audio input**: "audio input is not supported; it will be ignored and stripped" (OpenAI-SDK-compat docs). No streaming voice endpoint, no video/frame-stream endpoint. Text + static images only. [V]
- Voice exists only in **products**: Claude app voice mode (updated July 2026 — model choice Opus/Sonnet/Haiku) and Claude Code voice mode (~March 2026). Not exposed as a developer API. [V — TechCrunch]
- For a wearable, Anthropic today can only play the VLM role in architecture (b) with images over the normal Messages API + your own STT/TTS (e.g., via Pipecat/LiveKit). Rumored roadmap items (offline voice packs, voice cloning) are **[L/uncertain — single blog source]**.

Sources: [OpenAI SDK compat — Claude docs](https://platform.claude.com/docs/en/api/openai-sdk) · [TechCrunch July 2026](https://techcrunch.com/2026/07/23/anthropic-updates-claude-voice-mode-with-more-capable-models/) · [TechCrunch March 2026](https://techcrunch.com/2026/03/03/claude-code-rolls-out-a-voice-mode-capability/)

---

## 4. xAI / Grok and the rest of the field

**xAI** [V]:
- **Consumer app**: Grok voice mode "can see" via live camera — **app-only, not exposed in the API**.
- **Grok Voice Agent API** (launched ~Dec 2025/2026, expanded July 2026 with 21 new voices): OpenAI Realtime-API-compatible at `wss://api.x.ai/v1/realtime`, in-house VAD/audio stack, sub-second latency, LiveKit + Pipecat plugins exist. Models: `grok-voice-latest`, `grok-voice-think-fast-2.0/1.0`. **Audio + text only — docs list no image/video input.** You'd bolt `grok-4`/`grok-2-vision` frame calls onto the voice session yourself.
- Sources: [x.ai voice agent announcement](https://x.ai/news/grok-voice-agent-api) · [docs.x.ai voice agent](https://docs.x.ai/developers/model-capabilities/audio/voice-agent) · [LiveKit xAI plugin](https://docs.livekit.io/agents/models/realtime/plugins/xai/) · [Pipecat Grok Realtime](https://docs.pipecat.ai/api-reference/server/services/s2s/grok)

**Qwen-Omni Realtime (Alibaba Model Studio)** — the sleeper option, closest to Gemini Live [V]:
- Models: `qwen3.5-omni-plus-realtime`, `qwen3.5-omni-flash-realtime`, `qwen3-omni-flash-realtime`. WebSocket **and WebRTC**; audio+**image frames** in (recommended **1 FPS**, JPG ≤256 KB, 480p/720p rec, 1080p max, "must send audio before images"), text+speech out. PCM 16 kHz in / 24 kHz out — same as Gemini.
- Session: WebSocket up to **120 min**; video context retention limited (plus: 50 turns / 240 s of video; flash: 50 turns / 120 s).
- Pricing lives in the Model Studio console; intl new accounts get 1M in + 1M out tokens free for 90 days. **[L on price]**
- **Qwen3-Omni weights are open (Apache-2)** — the same architecture is the local option (see §5c).
- Sources: [Alibaba Cloud Qwen-Omni-Realtime doc](https://www.alibabacloud.com/help/en/model-studio/realtime) · [Qwen3-Omni GitHub](https://github.com/QwenLM/Qwen3-Omni)

**Moondream (local/edge VLM)** [V]:
- Moondream 3.1 (small MoE VLM) + **"Photon"** runtime: real-time inference on video streams, runs on **Apple Silicon Macs, NVIDIA GPUs, Jetson**; ~2× faster than same-size models on vLLM; marketed explicitly for continuous live-video analysis. No voice — the "eyes" component you pair with STT/TTS.
- Sources: [Photon announcement](https://moondream.ai/blog/photon-real-time-vision-ai-is-finally-here) · [Live video solutions](https://moondream.ai/solutions/analyze-live-video)

**Frameworks that stitch it together** [V]:
- **LiveKit Agents** — first-class plugins for Gemini Live, OpenAI Realtime (with the video→frames sampler), and xAI voice. Strongest "wearable backend" story: WebRTC transport from device, server agent does the sampling.
- **Pipecat (Daily)** — vendor-neutral, 100+ integrations incl. Gemini Live multimodal, Grok realtime, local Ollama; vision agents pass video frames to a VLM or CV models (YOLO/Roboflow).
- **Vision Agents by Stream** — newest, purpose-built "voice agent that also sees": VLMs, YOLO, pose detection on a standard voice pipeline; has a Moondream plugin. ([visionagents.ai](https://visionagents.ai/integrations/vision/moondream), [Stream comparison post](https://getstream.io/blog/voice-chatbot-platforms/))

---

## 5. Architecture comparison

**(a) Native video-in realtime API — Gemini Live (or Qwen-Omni Realtime)**
- One socket, one model: audio + 1 FPS frames in, speech out. Model natively correlates what it hears with what it sees; proactive-audio can keep it silent until useful.
- Latency: speech-to-speech well under ~1 s typical; frames are already in context, so "what am I looking at" has zero extra round-trip. **[L on exact ms]**
- Engineering burden: session resumption every ~10 min + context compression config; 1 FPS ceiling means fast action is missed.
- Cost: cheapest by an order of magnitude with 3.1-flash-live per-minute billing.

**(b) Audio-realtime + frame injection — gpt-realtime(+images), Grok voice(+grok-vision), or Pipecat/LiveKit with any VLM (incl. Claude)**
- Best voice quality/tool-calling ecosystems, any VLM for the eyes.
- Latency: voice loop fast (~300–800 ms), but vision-grounded answers pay either (i) nothing extra if frames are pre-injected (then you pay for every frame in every turn's context), or (ii) an extra VLM round-trip (~0.5–2 s) on-demand (cheaper).
- Engineering burden: frame sampler + context hygiene, or a tool-call bridge to the VLM.
- Cost: dominated by realtime-audio context re-billing; caching mandatory.

**(c) Local — Mac Studio / DGX Spark running an omni model**
- **Qwen3-Omni-30B-A3B** (open weights, audio+video in, speech out) is the real candidate; Moondream+Photon on Apple Silicon/Jetson is the lighter "eyes-only" path (pair with Whisper-streaming + local TTS).
- Latency: expect ~1–3 s speech response on consumer hardware, not sub-second **[E]**; Moondream frame analysis is genuinely real-time on GPU.
- Cost: $0 marginal, hardware amortized; fully private — relevant for an always-on face camera.
- Burden: highest.

---

## 6. Cost math — 1 hour/day continuous video+voice, 30 hrs/month

**Gemini Live, `gemini-3.1-flash-live-preview`, per-minute billing** [E from verified rates]:
- Input: 60 min × ($0.005 audio + $0.002 video) = **$0.42/hr**
- Output: assistant speaks 15 min/hr × $0.018 = $0.27 (30 min → $0.54)
- **≈ $0.69–0.96/hour → ≈ $21–29/month.** (Token-billed alternative: audio 115k tok = $0.35 + video at LOW res 66 tok/frame × 3,600 = 238k tok = $0.24 → similar; default-res frames triple the video line.)

**Gemini Live, `gemini-2.5-flash-native-audio`** [E]: **≈ $1.4–3.5/hr → $42–105/month.** The 3.1 per-minute SKU clearly wins.

**GPT Realtime frame-sampled (gpt-realtime-2.1 + LiveKit sampler ~1 frame/3s idle)** [E, wide error bars]:
- Naive list-price floor ~$3–4/hr *if context were never re-billed — it is.*
- With measured real-world multipliers (context re-billing, caching on): voice alone **$3–6/hr cached**; add frames living in context → realistically **$5–15/hr → $150–450/month**. Uncached worst case $11–28/hr voice alone.
- **gpt-realtime-2.1-mini** cuts every line ~3–6×: plausibly **$1.5–5/hr → $45–150/month** with good context hygiene. [E]
- Cheaper variant of (b): keep frames OUT of the realtime context; on demand, tool-call a snapshot to `gpt-5-mini`/Claude Haiku/Moondream — vision drops to per-question pennies, voice-only realtime dominates.

**Local (c)**: ~$0/month marginal + hardware.

**Bottom line** [E]: for continuous "AI sees what I see," **Gemini Live on 3.1-flash-live is ~10–20× cheaper than frame-stuffed GPT Realtime** (~$25/mo vs $150–450/mo at 1 hr/day), is the only true native video-in socket among US providers, and has the proactive-audio behavior a wearable wants. Qwen-Omni Realtime is the architectural twin (with WebRTC) as second source or the same model locally later. OpenAI is the play only if you want its voice/tool-calling quality with disciplined frame eviction (or mini). Anthropic and xAI's camera mode are not API options today.

**Key open items to verify before building**: proactive audio on `gemini-3.1-flash-live-preview` specifically; exact image-token count per frame in gpt-realtime; Qwen realtime per-token pricing (console-only); GPT-Realtime-2/2.1 release dates (changelog year ambiguity — 2.1 confirmed July 2026 via MarkTechPost).
