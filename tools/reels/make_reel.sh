#!/bin/bash
# make_reel.sh <layersDir> <out.mp4>  — 카드 레이어로 세로 릴스 영상 만들기
set -e
L=$1; OUT=$2; T=/tmp/reelclips; rm -rf $T; mkdir -p $T
DUR=(2.6 3.4 3.4 3.6 4.4 3.6)
ZOOM="scale=2160:3840,zoompan=z='1+0.05*on/(DUR*30)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
for n in 1 2 3 4 5 6; do
  D=${DUR[$((n-1))]}; Z=${ZOOM//DUR/$D}
  if [ -f $L/${n}_txt.png ]; then
    if [ $n = 1 ]; then TX="[1]format=rgba[t];[bg][t]overlay=0:0"
    else TX="[1]format=rgba,fade=in:st=0.15:d=0.35:alpha=1[t];[bg][t]overlay=x=0:y='40*max(0\,1-max(0\,t-0.15)/0.35)'"; fi
    ffmpeg -loglevel error -y -loop 1 -framerate 30 -t $D -i $L/${n}_bg.png -loop 1 -framerate 30 -t $D -i $L/${n}_txt.png \
      -filter_complex "[0]$Z[bg];$TX,format=yuv420p" -t $D -c:v libx264 -preset veryfast -crf 18 $T/$n.mp4
  else
    ffmpeg -loglevel error -y -loop 1 -framerate 30 -t $D -i $L/${n}_bg.png \
      -loop 1 -framerate 30 -t $D -i $L/${n}_txt0.png -loop 1 -framerate 30 -t $D -i $L/${n}_txt1.png \
      -loop 1 -framerate 30 -t $D -i $L/${n}_txt2.png -loop 1 -framerate 30 -t $D -i $L/${n}_txt3.png -loop 1 -framerate 30 -t $D -i $L/${n}_txt4.png \
      -filter_complex "[0]$Z[bg];[1]format=rgba,fade=in:st=0.1:d=0.3:alpha=1[t0];[bg][t0]overlay[a];\
[a][2]overlay=enable='between(t,0.7,1.4)'[b];[b][3]overlay=enable='between(t,1.4,2.1)'[c];[c][4]overlay=enable='between(t,2.1,2.8)'[d];[d][5]overlay=enable='gte(t,2.8)',format=yuv420p" \
      -t $D -c:v libx264 -preset veryfast -crf 18 $T/$n.mp4
  fi
done
X=0.3; IN=""; F=""; off=0; prev="0:v"
for n in 1 2 3 4 5 6; do IN="$IN -i $T/$n.mp4"; done
acc=${DUR[0]}
for n in 2 3 4 5 6; do
  i=$((n-1)); off=$(python3 -c "print(round($acc-$X*$((n-1)),3))")
  lab="v$n"; F="$F[$prev][$i:v]xfade=transition=smoothleft:duration=$X:offset=$off[$lab];"; prev=$lab
  acc=$(python3 -c "print($acc+${DUR[$((n-1))]})")
done
ffmpeg -loglevel error -y $IN -filter_complex "${F%;}" -map "[$prev]" -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p -r 30 -movflags +faststart $OUT
ffprobe -v error -show_entries format=duration -of csv=p=0 $OUT
