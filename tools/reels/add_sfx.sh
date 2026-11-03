#!/bin/bash
# add_sfx.sh <in.mp4> <out.mp4> — 장면 시간에 맞춰 효과음 입히기 (카드 6장 기본 타이밍)
set -e
IN=$1; OUT=$2; S="$(cd "$(dirname "$0")" && pwd)/sfx"
EV="impact:0.00:0.9 whoosh:2.25:0.5 whoosh:5.35:0.5 whoosh:8.45:0.5 whoosh:11.75:0.5 pop:12.50:0.6 pop:13.20:0.6 pop:13.90:0.6 pop:14.60:0.6 whoosh:15.85:0.5 ding:16.05:0.45"
ARGS=""; F=""; i=1; L=""
for e in $EV; do IFS=: read n t v <<< "$e"; ARGS="$ARGS -i $S/$n.wav"; ms=$(python3 -c "print(int($t*1000))")
  F="$F[$i:a]adelay=${ms}|${ms},volume=$v[a$i];"; L="$L[a$i]"; i=$((i+1)); done
cnt=$((i-1))
ffmpeg -loglevel error -y -i $IN $ARGS -filter_complex "${F}${L}amix=inputs=$cnt:normalize=0:duration=longest,apad,alimiter=limit=0.9[aout]" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart $OUT
ffprobe -v error -show_entries stream=codec_type,duration -of csv=p=0 $OUT
