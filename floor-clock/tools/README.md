# Matching the original

- `compare.html` + `tune.js`: serve next to `index.html` and a `frames/` dir
  (`ffmpeg -i src.mp4 -vf "fps=30,scale=1480:892" -q:v 3 frames/%05d.jpg`; src via `yt-dlp`).
  `crops([t])` = side-by-side crops, `over(t)` = 50% overlay, `sheet([t])` = rows,
  `tune(times, P, steps)` = edge-map fit of camera + layout.
- `fit-camera.mjs`: first camera fit from floor-grid corners in frame 0.
- `font-to-typeface.mjs`: OTF -> three.js typeface JSON (digits), winding fixed. Font = TeX Gyre Heros Bold (GUST font license).
- The video's seconds run 0.5% fast: 19:45:41 lands at 0.58 s, one tick every 0.9945 s.
