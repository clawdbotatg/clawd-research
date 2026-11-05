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

**X gotcha:** the MP4 needs a `colr` (nclx) box, not just tags in the H.264 stream.
Without it X re-encodes the video as plain SDR and it looks dull (Macs still play it as HDR from the
stream tags, which hides the bug). `encode.sh` writes it with `-movflags +write_colr`.
Check: `python3 -c "d=open('f.mp4','rb').read();print(d[d.find(b'colr'):][:15])"` → `colrnclx\0\t\0\x12\0\t`.

**Matching the viral file exactly** (1920x1080, 60 fps, silent AAC track, colr box): render `PAGE=best.html QS="?w=1920&h=1080"`
(serve.py `1920 1080 60`), then add audio without losing the tags:
`ffmpeg -i hdr_h264.mp4 -f lavfi -i anullsrc=r=48000:cl=stereo -map 0:v -map 1:a -c:v copy -bsf:v h264_metadata=colour_primaries=9:transfer_characteristics=18:matrix_coefficients=9 -color_primaries bt2020 -color_trc arib-std-b67 -colorspace bt2020nc -color_range tv -c:a aac -shortest -movflags +write_colr+faststart out.mp4`
(a plain `-c:v copy` remux writes colr as 2/2/9 = unspecified). As of 2026-11-03 X still stripped HDR on
our posts; it looks gated per account.

**2026-11-04 scan of X:** searched recent native videos, pulled X's copies. HDR kept on small accounts
(13, 101, 946 followers), so it is not account-gated. Every kept one is 1920x1080 or 1080x1920; all our
failed posts were 1080x1080. Recipe from github.com/ericqian77/x-hdr-video-lab (same as ours: H.264
High 8-bit HLG BT.2020, tags in stream + container, upload from desktop browser; iPhone album upload
drops HDR). Brightness is not the gate (a kept post had median luma 0.24). Next test: 16:9 file.
