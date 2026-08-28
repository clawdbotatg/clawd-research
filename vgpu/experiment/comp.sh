#!/bin/bash
# Composite the vgpu background under the real show layers (copies in work/).
# Coordinates/styling cribbed verbatim from the show's own show.filter.
set -euo pipefail
cd "$(dirname "$0")"
FF=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg
END=24.372
PIP=6.493

$FF -y -v error \
  -i work/bg.mp4 \
  -i work/idle_1.mp4 \
  -stream_loop -1 -i work/chatting_1.mp4 \
  -loop 1 -i work/story-0.png \
  -i work/voice.norm.wav \
  -filter_complex "
    [1:v]trim=duration=2,setpts=PTS-STARTPTS[seg0];
    [2:v]trim=duration=22.5,setpts=PTS-STARTPTS[seg1];
    [seg0][seg1]concat=n=2:v=1:a=0[avatar];
    [avatar]split[avA][avB];
    [avA]scale=560:560[full];
    [avB]scale=300:300[pip];
    [0:v][full]overlay=360:160:enable='lt(t,$PIP)'[c0];
    [c0][pip]overlay=940:360:enable='gte(t,$PIP)'[c1];
    [c1][3:v]overlay=40:140:enable='between(t,$PIP,$END)'[k0];
    [k0]drawtext=fontfile='/System/Library/Fonts/Monaco.ttf':textfile=work/lower3.txt:fontcolor=0x99DDAA:fontsize=20:x=(w-text_w)/2:y=684:box=1:boxcolor=0x081008@0.85:boxborderw=12,subtitles=work/captions.ass,trim=duration=$END,fade=t=out:st=23.87:d=0.5,format=yuv420p[v];
    [4:a]adelay=2000:all=1,atrim=duration=$END,afade=t=out:st=23.87:d=0.5[a]
  " \
  -map '[v]' -map '[a]' -c:v libx264 -crf 20 -c:a aac -b:a 128k \
  experiment.mp4
echo "-> experiment.mp4"
