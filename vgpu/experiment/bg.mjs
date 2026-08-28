// vgpu experiment: audio-reactive animated background for the morning show.
// Renders work/bg.mp4 — the layer that replaces the show's pure-black base.
// Reads NOTHING from and writes NOTHING to clawd-morning-show.
import { execFileSync, spawn } from "node:child_process";
import { init, effect, target } from "vgpu/node";

const W = 1280, H = 720, FPS = 30;
const TOTAL = 24.372;          // end of story card 0 in the real plan.json
const VOICE_DELAY = 2.0;       // show delays audio by INTRO_S=2
const PIP_AT = 6.493;          // full -> PIP cut

// ---- per-frame voice levels from the real voice track ----
const pcm = execFileSync("ffmpeg", [
  "-v", "quiet", "-i", "work/voice.norm.wav",
  "-ac", "1", "-ar", "48000", "-f", "f32le", "-",
], { maxBuffer: 1 << 28 });
const samples = new Float32Array(pcm.buffer, pcm.byteOffset, pcm.byteLength / 4);
const frames = Math.ceil(TOTAL * FPS);
const win = Math.floor(48000 / FPS);
const raw = new Float32Array(frames);
for (let f = 0; f < frames; f++) {
  const t = f / FPS - VOICE_DELAY;          // audio starts at t=2 in the comp
  if (t < 0) continue;
  const s0 = Math.floor(t * 48000);
  let acc = 0;
  for (let i = s0; i < Math.min(s0 + win, samples.length); i++) acc += samples[i] * samples[i];
  raw[f] = Math.sqrt(acc / win);
}
const peak = [...raw].sort((a, b) => b - a)[Math.floor(frames * 0.02)] || 1; // 98th pct
const levels = new Float32Array(frames);
let sm = 0;
for (let f = 0; f < frames; f++) {
  const v = Math.min(raw[f] / peak, 1);
  sm = v > sm ? sm + (v - sm) * 0.55 : sm + (v - sm) * 0.12; // fast attack slow decay
  levels[f] = sm;
}

// ---- avatar stage panel rects (normalized), matching show.filter overlays ----
const rectFull = [360 / W, 160 / H, 560 / W, 560 / H];
const rectPip = [940 / W, 360 / H, 300 / W, 300 / H];

const shader = /* wgsl */ `
  struct Params {
    time: f32, level: f32, aspect: f32, pipmix: f32,
    rect: vec4f,
    hist: array<vec4f, 16>,
  }
  @group(0) @binding(0) var<uniform> params: Params;

  fn hash(p: vec2f) -> f32 {
    return fract(sin(dot(p, vec2f(127.1, 311.7))) * 43758.5453);
  }

  fn sdRoundRect(p: vec2f, half: vec2f, r: f32) -> f32 {
    let q = abs(p) - half + vec2f(r);
    return length(max(q, vec2f(0.0))) + min(max(q.x, q.y), 0.0) - r;
  }

  @fragment fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
    let px = vec2f(uv.x * params.aspect, uv.y);   // aspect-corrected
    let lvl = params.level;

    // deep navy base with slow drift
    var col = mix(vec3f(0.010, 0.016, 0.028), vec3f(0.020, 0.034, 0.052),
                  uv.y + 0.06 * sin(params.time * 0.13 + uv.x * 2.0));

    // perspective floor grid below the horizon, scrolling toward viewer
    let hy = 0.585;
    if (uv.y > hy) {
      let d = (uv.y - hy) + 0.0001;
      let persp = 0.055 / d;
      let gx = abs(fract((uv.x - 0.5) * persp * 2.4) - 0.5);
      let gz = abs(fract(persp * 1.4 - params.time * 0.55) - 0.5);
      let lw = 0.03 + d * 0.05;
      let line = smoothstep(lw, lw * 0.2, min(gx, gz)) * smoothstep(0.0, 0.10, d);
      col += vec3f(0.05, 0.26, 0.15) * line * (0.5 + 0.6 * lvl);
      // thin bright horizon line + narrow glow, breathing with the voice
      col += vec3f(0.10, 0.45, 0.25) * exp(-d * 220.0) * (0.6 + 1.2 * lvl);
      col += vec3f(0.04, 0.20, 0.11) * exp(-d * 40.0) * (0.3 + 0.7 * lvl);
    } else {
      // sparse dim stars in the sky (point within cell, radial falloff)
      let sp = uv * vec2f(96.0, 54.0);
      let cell = floor(sp);
      let star = step(0.992, hash(cell));
      let pos = vec2f(hash(cell + 1.3), hash(cell + 2.7));
      let dd = length((fract(sp) - pos) * vec2f(1.0, 0.5625));
      let tw = 0.5 + 0.5 * sin(params.time * 1.7 + hash(cell + 7.0) * 40.0);
      col += vec3f(0.35, 0.5, 0.45) * star * tw * smoothstep(0.12, 0.0, dd) * 0.6 * smoothstep(hy, 0.1, uv.y);
    }

    // voice waveform ribbon across the top band (history right -> left)
    let wy = 0.085;
    let idx = clamp(i32(uv.x * 63.0), 0, 63);
    let h = params.hist[idx / 4][idx % 4];
    let amp = 0.003 + h * 0.075;
    let dy = abs(uv.y - wy);
    let wave = smoothstep(amp, amp * 0.15, dy);
    col += vec3f(0.10, 0.42, 0.24) * wave * (0.15 + 0.85 * h);
    col += vec3f(0.05, 0.20, 0.12) * smoothstep(0.09, 0.0, dy) * (0.05 + 0.25 * h);

    // avatar stage panel: pure black interior + glowing border
    let rc = params.rect;
    let cpx = vec2f((rc.x + rc.z * 0.5) * params.aspect, rc.y + rc.w * 0.5);
    let half = vec2f(rc.z * 0.5 * params.aspect, rc.w * 0.5);
    let sd = sdRoundRect(px - cpx, half, 0.02);
    let border = exp(-abs(sd) * 130.0) * (0.35 + 0.65 * lvl);
    col += vec3f(0.07, 0.34, 0.19) * border;
    col = mix(col, vec3f(0.0), smoothstep(0.004, -0.002, sd)); // hard black inside

    // scanlines + vignette
    col *= 0.94 + 0.06 * sin(uv.y * 720.0 * 3.14159);
    let v = uv - 0.5;
    col *= 1.0 - dot(v, v) * 0.55;

    return vec4f(col, 1.0);
  }
`;

const gpu = await init({ adapter: "hardware" });
const t = target(gpu, { size: [W, H] });
const hist = new Float32Array(64);
const histVecs = () => Array.from({ length: 16 }, (_, i) => [hist[i * 4], hist[i * 4 + 1], hist[i * 4 + 2], hist[i * 4 + 3]]);
const fx = effect(gpu, shader, {
  set: { params: { time: 0, level: 0, aspect: W / H, pipmix: 0, rect: rectFull, hist: histVecs() } },
});

const ff = spawn("ffmpeg", [
  "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", `${W}x${H}`,
  "-r", String(FPS), "-i", "-",
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "work/bg.mp4",
], { stdio: ["pipe", "ignore", "pipe"] });
let ffErr = "";
ff.stderr.on("data", (d) => (ffErr += d));

const t0 = Date.now();
for (let f = 0; f < frames; f++) {
  const time = f / FPS;
  hist.copyWithin(0, 1);
  hist[63] = levels[f];
  const rect = time < PIP_AT ? rectFull : rectPip;
  fx.set({ params: { time, level: levels[f], rect, hist: histVecs() } });
  fx.draw(t);
  const pixels = await t.read();
  if (!ff.stdin.write(Buffer.from(pixels))) {
    await new Promise((r) => ff.stdin.once("drain", r));
  }
}
ff.stdin.end();
const code = await new Promise((r) => ff.on("close", r));
await gpu.settled();
gpu.dispose();
if (code !== 0) { console.error(ffErr.split("\n").slice(-8).join("\n")); process.exit(1); }
const dt = (Date.now() - t0) / 1000;
console.log(`bg: ${frames} frames in ${dt.toFixed(1)}s (${(frames / dt).toFixed(0)} fps) -> work/bg.mp4`);
