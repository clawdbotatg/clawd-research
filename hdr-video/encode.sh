#!/bin/sh
# encode.sh DIR — master.mkv (rgb48, HLG/BT.2020 signal) -> hdr_h264.mp4 + hdr_hevc10.mp4
set -e; D=$1
TAGS="-color_primaries bt2020 -color_trc arib-std-b67 -colorspace bt2020nc -color_range tv"
VF="scale=out_color_matrix=bt2020nc:out_range=tv:flags=accurate_rnd"
X="colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc"
# H.264 8-bit HLG: same format as the viral posts (X keeps the tags)
ffmpeg -y -v error -i $D/master.mkv -vf "$VF,format=yuv420p" -c:v libx264 -profile:v high -crf 15 -preset slow \
  -x264-params $X $TAGS -movflags +write_colr+faststart $D/hdr_h264.mp4
# HEVC 10-bit HLG: smoother gradients; plays HDR in iPhone Photos
ffmpeg -y -v error -i $D/master.mkv -vf "$VF,format=yuv420p10le" -c:v libx265 -crf 15 -preset medium -tag:v hvc1 \
  -x265-params "$X:range=limited:log-level=error" $TAGS -movflags +write_colr+faststart $D/hdr_hevc10.mp4
