# hdr-video

HDR (HLG / BT.2020) videos for X, like the ones going around on 2026-10-31.
The viral posts are plain 8-bit H.264 tagged HLG + BT.2020; X keeps the tags,
so anything above SDR white (HLG signal 0.75) shows brighter than the rest of the
timeline on HDR phones.

`wedgie/best.html` (v4, current): square 1080, black void, red/green rims. `PAGE=best.html VW=1080 VH=1080`, serve.py args `1080 1080 60`.
`wedgie/canyon.html` (v3): v2 down a neon canyon, fireworks, sparks. `PAGE=canyon.html`. Screen always near HDR peak; copy `wedgie/undies-screen.png` to `<wedgie-dev>/public/screens/undies.png` first.
`wedgie/loop.html` (v2): 6 s seamless loop, undies → whip at your face → flip back → Safe tx, sign → flip back. Run drive.mjs with `PAGE=loop.html`.
`wedgie/index.html` (v1) renders the real wedgie case (geometry from wedgie-dev `public/3d/`)
flying at the camera in three.js, float HDR, encoded to HLG in a shader.

```sh
cd <dir with node_modules/three + playwright-core>        # npm i three@0.186.1 playwright-core
python3 wedgie/serve.py <wedgie-dev>/public . OUT &       # serves page, pipes frames to ffmpeg
node wedgie/drive.mjs preview 150,300                     # SDR previews at half exposure
node wedgie/drive.mjs all                                 # 420 frames -> OUT/master.mkv (~2.5 min)
./encode.sh OUT                                           # -> hdr_h264.mp4 (post this) + hdr_hevc10.mp4
```

Scene linear 1.0 = SDR white = HLG 0.75; soft knee to peak at ~3.8x.
