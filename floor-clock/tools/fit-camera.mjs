const P0 = [[0,0,110,210],[1,0,345,393],[2,0,585,580],[3,0,835,780],[1,1,845,165],[2,1,1090,340],[3,1,1350,520],[3,-1,270,1067],[4,-1,535,1302],[5,-1,815,1562],[5,1,1925,927],[6,1,2255,1152],[7,1,2600,1402],[6,0,1720,1482],[3,2,1810,285],[5,2,2405,655]];
const MAP = (process.argv[2] || '1,1').split(',').map(Number), N = +(process.argv[3] || 10);
const P = P0.slice(0, N).map(([j, i, u, v]) => [j * MAP[0], i * MAP[1], u, v]);
const W = 2960, H = 1784;
// params: camera pos (cx,cy,cz), look-at floor point (tx,tz), vertical fov (rad)
function proj([cx, cy, cz, tx, tz, fov, roll], x, z) {
  let fx = tx - cx, fy = -cy, fz = tz - cz; const fl = Math.hypot(fx, fy, fz); fx /= fl; fy /= fl; fz /= fl;
  let rx = -fz, rz = fx; const rl = Math.hypot(rx, rz); rx /= rl; rz /= rl; // right = f x up(0,1,0)
  const ux = -rz * fy, uy = rz * fx - rx * fz, uz = rx * fy;               // up = r x f
  const dx = x - cx, dy = -cy, dz = z - cz;
  const X = dx * rx + dz * rz, Y = dx * ux + dy * uy + dz * uz, Z = dx * fx + dy * fy + dz * fz;
  if (Z <= 0) return [1e6, 1e6];
  const f = (H / 2) / Math.tan(fov / 2);
  const a = f * X / Z, b = f * Y / Z, c = Math.cos(roll), s = Math.sin(roll);
  return [W / 2 + a * c - b * s, H / 2 - (a * s + b * c)];
}
const err = p => p[5] <= 0.08 || p[5] > 2 || p[1] <= 0 ? 1e15 : P.reduce((s, [j, i, u, v]) => { const [a, b] = proj(p, j, i); return s + (a - u) ** 2 + (b - v) ** 2; }, 0);
function nm(x0, scale, iters = 4000) {
  const n = x0.length; let S = [x0];
  for (let i = 0; i < n; i++) { const x = x0.slice(); x[i] += scale[i]; S.push(x); }
  let F = S.map(err);
  for (let it = 0; it < iters; it++) {
    const idx = F.map((f, i) => i).sort((a, b) => F[a] - F[b]); S = idx.map(i => S[i]); F = idx.map(i => F[i]);
    const c = Array(n).fill(0); for (let i = 0; i < n; i++) for (let k = 0; k < n; k++) c[k] += S[i][k] / n;
    const w = S[n], r = c.map((v, k) => v + (v - w[k])), fr = err(r);
    if (fr < F[0]) { const e = c.map((v, k) => v + 2 * (v - w[k])), fe = err(e); if (fe < fr) { S[n] = e; F[n] = fe; } else { S[n] = r; F[n] = fr; } }
    else if (fr < F[n - 1]) { S[n] = r; F[n] = fr; }
    else { const k2 = c.map((v, k) => v + 0.5 * (w[k] - v)), fk = err(k2);
      if (fk < F[n]) { S[n] = k2; F[n] = fk; } else { for (let i = 1; i <= n; i++) { S[i] = S[i].map((v, k) => S[0][k] + 0.5 * (v - S[0][k])); F[i] = err(S[i]); } } }
  }
  return { p: S[0], e: F[0] };
}
let best = null;
for (let t = 0; t < 400; t++) {
  const x0 = [Math.random() * 60 - 30, 1 + Math.random() * 30, Math.random() * 60 - 30, Math.random() * 6 - 1, Math.random() * 6 - 3, 0.09 + Math.random() * 0.6, (Math.random() - 0.5) * 6.28];
  let r = nm(x0, [1, 1, 1, 1, 1, 0.1, 0.2]); r = nm(r.p, [0.3, 0.3, 0.3, 0.3, 0.3, 0.03, 0.05]);
  if (!best || r.e < best.e) best = r;
}
console.log('rms px', Math.sqrt(best.e / P.length).toFixed(2), 'params', best.p.map(v => +v.toFixed(3)), 'fovDeg', (best.p[5] * 57.296).toFixed(2), 'rollDeg', (best.p[6] * 57.296).toFixed(2));
if (process.argv[4]) for (const [j, i, u, v] of P) console.log(j, i, [u, v], proj(best.p, j, i).map(Math.round));
