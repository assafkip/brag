#!/bin/bash
# Mux rendered frames and a soundtrack into the final mp4, normalise loudness in two passes, bake the poster into frame 0.
#   mux.sh <frames-dir> <audio.wav> <out.mp4> [poster-at-seconds=11.0] [fps=30]
# Settings are the owner's (Claudemy Sonos cut rebuild, 2026-10-23): h264 crf 17, yuv420p, AAC 192k 48 kHz,
# loudnorm I=-16 TP=-1.5 LRA=11. The first pass measures the soundtrack, the second applies the measured values with
# linear=true, so the result lands on -16 LUFS (a single pass landed at -17.2 on a product explainer cut).
# Writes <out>-poster.jpg next to the video; frame 0 of the video is that poster.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FRAMES="$1"; WAV="$2"; OUT="$3"; POSTER_AT="${4:-11.0}"; FPS="${5:-30}"
STEM="${OUT%.mp4}"; POSTER="${STEM}-poster.jpg"; TMP="${STEM}.tmp.mp4"
TARGET="I=-16:TP=-1.5:LRA=11"
MEAS=$(ffmpeg -hide_banner -i "$WAV" -af "loudnorm=${TARGET}:print_format=json" -vn -f null - 2>&1 | python3 "$HERE/loudnorm_args.py")
ffmpeg -v error -y -framerate "$FPS" -i "$FRAMES/%05d.png" -i "$WAV" -c:v libx264 -crf 17 -preset slow \
  -pix_fmt yuv420p -af "loudnorm=${TARGET}:${MEAS}:linear=true" -c:a aac -b:a 192k -ar 48000 -shortest \
  -movflags +faststart "$TMP"
ffmpeg -v error -y -ss "$POSTER_AT" -i "$TMP" -frames:v 1 -q:v 2 "$POSTER"
ffmpeg -v error -y -i "$TMP" -i "$POSTER" \
  -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]" -map "[v]" -map 0:a -c:v libx264 -crf 17 \
  -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT"
rm -f "$TMP"
echo "built $OUT (poster $POSTER at ${POSTER_AT}s)"
