# GPT Voice — what it is, how devs use it (2026-08)

TLDR: The magic in ChatGPT's voice mode is a **native speech-to-speech model**
(no STT→LLM→TTS pipeline) plus **semantic turn detection** (it understands
*whether you sound done talking*, not just silence). Developers get the same
stack via the **Realtime API** (`gpt-realtime` family). Custom voices exist but
are **sales-gated** ("eligible customers" only) — for self-serve voice cloning
you still pair with ElevenLabs/Cartesia. ChatGPT voice: free tier gets a taste,
Plus ($20/mo) gets hours/day. API is pay-per-audio-token, roughly
**$0.06–0.11/min** full model, **$0.02–0.05/min** mini.

## Why it feels good (the pause handling)

- One model does audio-in → audio-out. Sub-300ms latency, keeps prosody/emotion,
  can hear tone. No transcription round-trip.
- **Semantic VAD**: a classifier scores "is the user actually finished?" from the
  *words*, not just silence energy. Trailing off with "ummm…" → longer wait;
  a crisp sentence → instant reply. Tunable via an `eagerness` param
  (low/medium/high). This is the specific feature that makes pauses feel human.
- Barge-in (interrupting the model mid-sentence) is handled natively — server
  VAD truncates the response when you start talking.
- Docs: https://developers.openai.com/api/docs/guides/realtime-vad

## Developer surface

- **Realtime API** — WebSocket or WebRTC session; streams audio both ways.
  Supports tool/function calling, remote MCP servers, image input, and **SIP**
  (point a phone number at it). https://openai.com/index/introducing-gpt-realtime/
- **Agents SDK** has a voice-agent layer that wires Realtime sessions to tools.
- Models (as of mid-2026): `gpt-realtime` / `gpt-realtime-2` (full),
  `gpt-realtime-mini` (cheap tier, 2025-12-15 snapshot much better at
  instruction-following + tool calls), plus translate and streaming-Whisper
  variants. Also `gpt-audio(-mini)` for speech via Chat Completions, and
  separate TTS/STT models if you *do* want a pipeline.
- **Pricing** — per audio token, not per minute. Full model ~$32/M audio in,
  $64/M out; mini ~$10/$20. Real-world: ~$0.06–0.11/min full, ~$0.02–0.05/min
  mini with prompt caching (cached audio input is ~99% discounted). Output
  dominates cost — the model talks more than you.
  https://developers.openai.com/api/docs/guides/realtime-costs

## Custom voices

- **Yes, but gated.** Custom Voices work across TTS / Realtime / Chat
  Completions audio: you provide a short reference sample and the model
  replicates it. **"Limited to eligible customers — contact sales."** Not
  self-serve as of 2026-08; OpenAI says broader BYO-voice is on the roadmap.
  https://developers.openai.com/blog/updates-audio-models
- Realtime otherwise ships ~10 preset voices (marin, cedar, alloy, echo, …);
  note some TTS voices (ash, ballad, coral, fable, onyx, nova) are NOT on
  realtime models.
- Practical alt today: keep gpt-realtime for the brain/turn-taking and swap the
  output leg to ElevenLabs/Cartesia cloned voice — costs you latency and the
  native prosody, so most people just pick a preset.

## Subscriptions (consumer, ChatGPT app)

- Voice mode is in the ChatGPT apps: **Free** = limited daily use on the mini
  model; **Plus $20/mo** = hours per day on the full model + vision-in-voice;
  Pro higher still. (Consumer voice ≠ API access — the API is billed separately
  per token with an API key.)

## Where to learn

- Realtime guide: https://developers.openai.com/api/docs/guides/realtime
- VAD/turn-taking: https://developers.openai.com/api/docs/guides/realtime-vad
- Cost guide: https://developers.openai.com/api/docs/guides/realtime-costs
- Launch post: https://openai.com/index/introducing-gpt-realtime/
- Audio model updates (Dec-2025 snapshots, custom-voice note):
  https://developers.openai.com/blog/updates-audio-models
