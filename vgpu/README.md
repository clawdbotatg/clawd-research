# vgpu (vgpu.sh) — headless WebGPU, verified working

**What it is:** `vgpu` is a TypeScript WebGPU library from Vercel Labs (MIT).
Write a WGSL shader once, run the exact same code in a browser canvas, in
headless Node (Dawn native bindings — Metal on this Mac), or in a deterministic
mock for tests. Docs: https://vgpu.sh/docs · repo: github.com/vercel-labs/vgpu

**Verified on this machine (2026-08-28):**
- `npx vgpu doctor` → healthy, real Metal adapter, renders a test frame.
- `spike/render-video.mjs` → 120 frames of an animated fractal shader at
  1280×720, piped as raw RGBA into ffmpeg → `out.mp4`.
  **0.7s total, ~183 fps.** No browser, no window, no Xvfb.

## Why this matters for us

1. **Morning-show video pipeline.** The missing render engine. A WGSL shader +
   ffmpeg gives broadcast-quality animated backgrounds, title cards, and
   transitions from a plain Node script — faster than realtime. Compose data
   (headlines, charts) as textures/uniforms.
2. **Agents can do graphics with proof, not vibes.** The whole project is
   agent-first: `llms.txt`, `agents.md`, an MCP server
   (`claude mcp add --transport http vgpu https://vgpu.sh/api/mcp`), a CLI
   (`npx vgpu docs grep …`, `npx vgpu examples pull …`), and `doctor` emits a
   JSON verdict. The loop is render → `target.read()` → assert on pixels.
   A session in the harness can write a shader, render it, read the PNG back
   with vision, and iterate — fully headless.
3. **Live visuals.** Same shader file drives a browser canvas for anything
   live (agent-esports overlays, show graphics) and the headless renderer for
   recorded output. One codebase, both worlds.
4. **ML post-processing.** It does NOT run models; it shares a `GPUDevice`
   with onnxruntime-web etc. so model outputs (tensors are just `GPUBuffer`s)
   get post-processed on-GPU with zero CPU roundtrip. Niche for us today.

## API in 10 lines (the part I got wrong first)

```ts
import { init, effect, target } from "vgpu/node";
const gpu = await init();                       // or { adapter: "hardware" | "software" }
const t = target(gpu, { size: [1280, 720] });
const fx = effect(gpu, WGSL, { set: { params: { time: 0 } } }); // bindings by WGSL name
fx.set({ params: { time: 1.5 } });              // writes immediately
fx.draw(t);
const pixels = await t.read();                  // RGBA bytes
gpu.dispose();                                  // stops Dawn polling so node exits
```

No global uniforms — you declare a `struct Params` in WGSL and `set()` it by
name. Time in browser loops comes from `clock(gpu)`. Missing binding =
`VGPU-R1-BINDING-NEVER-SET` at draw.

## Gotchas

- Bundle claim: complete effects ~25 KB gzipped. Node side pulls a Dawn
  binary (cached under `~/.cache`); CPU fallback via
  `npx vgpu install-software-renderer` for GPU-less CI.
- `effect()` = fullscreen fragment shader; `draw()` = real geometry/vertex
  work; `frame()`/`frameLoop()` batch passes; there's also `compute()`.
- PNG/video encoding is yours (pngjs, ffmpeg) — vgpu just hands you bytes.

## Files

- `spike/render-video.mjs` — WGSL → ffmpeg mp4 pipeline (the 183 fps run).
- `spike/frame.png` / `spike/out.mp4` — gitignored outputs; rerun to regenerate.

## Experiment: morning show over a live shader (2026-08-28)

`experiment/` re-composites the first 24s of the REAL 2026-08-21 show with the
black background replaced by a vgpu-rendered set: scrolling perspective grid,
voice-reactive waveform + horizon glow (per-frame RMS from voice.norm.wav),
and a black stage panel with a glowing border that tracks the avatar's
full→PIP move (the avatar clips are on pure black, so the panel makes the
square read as design). **clawd-morning-show was not modified** — inputs are
copies, coordinates cribbed from its show.filter.

- `experiment/bg.mjs` — levels extraction + shader render → `work/bg.mp4`
  (732 frames of 720p in ~1.7s; a full 2:20 show ≈ 10s).
- `experiment/comp.sh` — ffmpeg-full comp: bg + avatar concat + story card +
  ticker + captions.ass + delayed audio → `experiment.mp4`.
- To regenerate: copy the listed inputs from a show's `out/work-<date>/` into
  `experiment/work/`, then `node bg.mjs && ./comp.sh`.
- Integration shape if adopted: one new stage writes `bg.mp4`; 05-render's
  base layer becomes that file instead of black. Nothing else changes.
- Watch: https://claude.ai/code/artifact/a4f8f3de-9eac-432e-9cd9-613d91d04963
