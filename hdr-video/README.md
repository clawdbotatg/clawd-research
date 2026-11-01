# hdr-video

HDR (HLG / BT.2020) videos for X, like the ones going around on 2026-10-31.
The viral posts are plain 8-bit H.264 tagged HLG + BT.2020; X keeps the tags,
so anything above SDR white (HLG signal 0.75) shows brighter than the rest of the
timeline on HDR phones.

`wedgie/` renders the real wedgie case (geometry from wedgie-dev `public/3d/`)
flying at the camera in three.js, float HDR, encoded to HLG in a shader.

```sh
cd <dir with node_modules/three + playwright-core>        # npm i three@0.186.1 playwright-core
python3 wedgie/serve.py <wedgie-dev>/public . OUT &       # serves page, pipes frames to ffmpeg
node wedgie/drive.mjs preview 150,300                     # SDR previews at half exposure
node wedgie/drive.mjs all                                 # 420 frames -> OUT/master.mkv (~2.5 min)
./encode.sh OUT                                           # -> hdr_h264.mp4 (post this) + hdr_hevc10.mp4
```

Scene linear 1.0 = SDR white = HLG 0.75; soft knee to peak at ~3.8x.
