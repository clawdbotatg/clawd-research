// Headless WGSL -> mp4: vgpu (Dawn/Metal) renders frames, ffmpeg encodes.
import { spawn } from "node:child_process";
import { init, effect, target } from "vgpu/node";

const W = 1280, H = 720, FPS = 30, SECONDS = 4;

const shader = /* wgsl */ `
  struct Params { time: f32, aspect: f32 }
  @group(0) @binding(0) var<uniform> params: Params;

  fn palette(t: f32) -> vec3f {
    return 0.5 + 0.5 * cos(6.28318 * (vec3f(0.0, 0.33, 0.67) + t));
  }

  @fragment fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
    var p = (uv - 0.5) * vec2f(params.aspect, 1.0) * 2.0;
    let p0 = p;
    var col = vec3f(0.0);
    for (var i = 0; i < 4; i++) {
      p = fract(p * 1.5) - 0.5;
      var d = length(p) * exp(-length(p0));
      let c = palette(length(p0) + f32(i) * 0.4 + params.time * 0.4);
      d = sin(d * 8.0 + params.time) / 8.0;
      d = abs(d);
      d = pow(0.01 / d, 1.2);
      col += c * d;
    }
    return vec4f(col, 1.0);
  }
`;

const gpu = await init({ adapter: "hardware" });
const t = target(gpu, { size: [W, H] });
const fx = effect(gpu, shader, { set: { params: { time: 0, aspect: W / H } } });

const ff = spawn("ffmpeg", [
  "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", `${W}x${H}`,
  "-r", String(FPS), "-i", "-",
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "out.mp4",
], { stdio: ["pipe", "ignore", "pipe"] });
let ffErr = "";
ff.stderr.on("data", (d) => (ffErr += d));

const t0 = Date.now();
const frames = FPS * SECONDS;
for (let i = 0; i < frames; i++) {
  fx.set({ params: { time: i / FPS } });
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

if (code !== 0) {
  console.error(ffErr.split("\n").slice(-10).join("\n"));
  process.exit(1);
}
const dt = (Date.now() - t0) / 1000;
console.log(`${frames} frames @ ${W}x${H} in ${dt.toFixed(1)}s (${(frames / dt).toFixed(1)} fps) -> out.mp4`);
