// edge-map alignment: tune camera + layout so my render's edges sit on the video's
const TW = 370, TH = 223;
const tc = document.createElement('canvas'); tc.width = TW; tc.height = TH;
const tg = tc.getContext('2d', { willReadFrequently: true });
function edges(src) {
  tg.drawImage(src, 0, 0, TW, TH);
  const d = tg.getImageData(0, 0, TW, TH).data, L = new Float32Array(TW * TH), E = new Float32Array(TW * TH);
  for (let i = 0; i < TW * TH; i++) L[i] = 0.3 * d[i * 4] + 0.59 * d[i * 4 + 1] + 0.11 * d[i * 4 + 2];
  for (let y = 1; y < TH - 1; y++) for (let x = 1; x < TW - 1; x++) {
    const i = y * TW + x;
    const gx = L[i + 1] - L[i - 1], gy = L[i + TW] - L[i - TW];
    E[i] = Math.min(60, Math.hypot(gx, gy));
  }
  // blur twice
  for (let k = 0; k < 2; k++) {
    const B = new Float32Array(TW * TH);
    for (let y = 1; y < TH - 1; y++) for (let x = 1; x < TW - 1; x++) {
      let s = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) s += E[(y + dy) * TW + x + dx];
      B[y * TW + x] = s / 9;
    }
    E.set(B);
  }
  return E;
}
window.tune = async (times, P, steps, rounds = 3) => {
  const fw = document.getElementById('f').contentWindow;
  const refs = [];
  for (const t of times) { await seek(t); refs.push(edges(v)); }
  const toParams = p => ({ cam: [p[0], p[1], p[2]], tgt: [p[3], 0, p[4]], fov: p[5], roll: p[6], lanes: [p[7], p[8], p[9]], clockZ: p[10], cap: p[11], narrow: p[12], pitch: p[13], floorOff: p[14], seam: p[15], lead: p[16] });
  const score = p => {
    fw.setParams(toParams(p)); let s = 0;
    times.forEach((t, k) => { const E = edges(fw.clockAt(clockTime(t))); const R = refs[k]; for (let i = 0; i < E.length; i++) { const d = E[i] - R[i]; s += d * d; } });
    return s;
  };
  let best = score(P), st = steps.slice();
  for (let r = 0; r < rounds; r++) {
    for (let k = 0; k < P.length; k++) {
      if (!st[k]) continue;
      for (const dir of [1, -1]) {
        let improved = true;
        while (improved) {
          const q = P.slice(); q[k] += dir * st[k]; const s = score(q);
          improved = s < best; if (improved) { best = s; P = q; }
        }
      }
    }
    st = st.map(s => s / 2);
  }
  fw.setParams(toParams(P));
  return { P: P.map(x => +x.toFixed(4)), best };
};
