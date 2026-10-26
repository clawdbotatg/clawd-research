// opentype -> three.js typeface JSON (digits only), with contour winding normalised:
// outer contours one way, holes the other (by nesting depth), the way three's toShapes expects
import opentype from 'opentype.js';
import fs from 'fs';
const [src, out, refFile] = process.argv.slice(2);
const font = opentype.loadSync(src), res = font.unitsPerEm;

// split a path into contours: [{start:[x,y], segs:[{t,pts:[[x,y]...], to:[x,y]}]}]
function contours(cmds) {
  const cs = []; let cur = null, pen = null;
  for (const c of cmds) {
    if (c.type === 'M') { cur = { start: [c.x, c.y], segs: [] }; cs.push(cur); pen = [c.x, c.y]; }
    else if (c.type === 'L') { cur.segs.push({ t: 'L', pts: [], to: [c.x, c.y] }); pen = [c.x, c.y]; }
    else if (c.type === 'Q') { cur.segs.push({ t: 'Q', pts: [[c.x1, c.y1]], to: [c.x, c.y] }); }
    else if (c.type === 'C') { cur.segs.push({ t: 'C', pts: [[c.x1, c.y1], [c.x2, c.y2]], to: [c.x, c.y] }); }
  }
  return cs;
}
const poly = c => [c.start, ...c.segs.flatMap(s => [...s.pts, s.to])];
const area = P => { let a = 0; for (let i = 0; i < P.length; i++) { const [x1, y1] = P[i], [x2, y2] = P[(i + 1) % P.length]; a += x1 * y2 - x2 * y1; } return a / 2; };
const inside = ([x, y], P) => { let r = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const [xi, yi] = P[i], [xj, yj] = P[j]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) r = !r; } return r; };
function reverse(c) {
  const pts = [c.start, ...c.segs.map(s => s.to)];
  const segs = [];
  for (let i = c.segs.length - 1; i >= 0; i--) {
    const s = c.segs[i];
    segs.push({ t: s.t, pts: s.pts.slice().reverse(), to: pts[i] });
  }
  return { start: pts[pts.length - 1], segs };
}
// which sign does three want for outers? read it off a known-good typeface ('0' outer)
let outerSign = 1;
if (refFile) {
  const ref = JSON.parse(fs.readFileSync(refFile)).glyphs['0'].o.trim().split(/\s+/);
  const P = []; for (let i = 0; i < ref.length;) { const k = ref[i++]; const n = { m: 2, l: 2, q: 4, b: 6 }[k]; const v = ref.slice(i, i + n).map(Number); i += n; P.push([v[0], v[1]]); if (k === 'm' && P.length > 1) break; }
  outerSign = Math.sign(area(P.slice(0, -1)));
}
const glyphs = {};
for (const ch of '0123456789') {
  const g = font.charToGlyph(ch);
  let cs = contours(g.path.commands);
  const polys = cs.map(poly);
  cs = cs.map((c, i) => {
    const depth = polys.filter((P, j) => j !== i && inside(polys[i][0], P)).length;
    const want = depth % 2 === 0 ? outerSign : -outerSign;
    return Math.sign(area(polys[i])) === want ? c : reverse(c);
  });
  const f = v => Math.round(v);
  const o = cs.map(c => [`m ${f(c.start[0])} ${f(c.start[1])}`, ...c.segs.map(s =>
    s.t === 'L' ? `l ${f(s.to[0])} ${f(s.to[1])}` :
    s.t === 'Q' ? `q ${f(s.to[0])} ${f(s.to[1])} ${f(s.pts[0][0])} ${f(s.pts[0][1])}` :
    `b ${f(s.to[0])} ${f(s.to[1])} ${f(s.pts[0][0])} ${f(s.pts[0][1])} ${f(s.pts[1][0])} ${f(s.pts[1][1])}`)].join(' ')).join(' ');
  glyphs[ch] = { ha: Math.round(g.advanceWidth), x_min: g.xMin ?? 0, x_max: g.xMax ?? 0, o };
}
fs.writeFileSync(out, JSON.stringify({ glyphs, familyName: font.names.fontFamily.en, ascender: font.ascender, descender: font.descender, resolution: res,
  boundingBox: { xMin: font.tables.head.xMin, yMin: font.tables.head.yMin, xMax: font.tables.head.xMax, yMax: font.tables.head.yMax }, underlinePosition: 0, underlineThickness: 0, cssFontWeight: 'normal', cssFontStyle: 'normal' }));
console.log(out, 'outerSign', outerSign);
