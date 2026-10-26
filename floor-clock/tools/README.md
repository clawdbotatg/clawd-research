# Matching the original

- `compare.html` + `tune.js`: put `src.mp4` (the original, via `yt-dlp`) and a link to `../index.html` next to them, serve with a range-capable server (`npx http-server`), open `compare.html`.
  `sheet([times])` = video | mine | 50% overlay rows. `over(t)` = one big overlay. `tune(times, P, steps)` = edge-map fit of camera + layout.
- `fit-camera.mjs`: camera fit from hand-picked floor-grid corners in frame 0.
- The video's seconds run 0.5% fast: 19:45:41 lands at 0.62 s, one tick every 0.9945 s.
