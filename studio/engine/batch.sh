#!/usr/bin/env bash
# Renders series in rotation with fresh seeds until a UTC deadline (default 13:00 UTC = 22:00 KST).
# Waits for any render already running, then keeps queuing one video at a time.
set -u
DEADLINE=$(date -u -d "${1:-2026-10-10 13:00:00}" +%s)
cd "$(dirname "$0")"
while pgrep -f "node render.js" >/dev/null; do sleep 15; done
SERIES=(configs/food.json configs/weekday.json configs/mbti.json configs/zodiac.json configs/month.json)
seed=100
i=0
while :; do
  now=$(date -u +%s)
  # one video takes ~9 min on this box; don't start one that would end after the deadline
  if (( now + 600 > DEADLINE )); then echo "deadline reached, stopping at $(date -u)"; break; fi
  cfg=${SERIES[$((i % ${#SERIES[@]}))]}; i=$((i+1)); seed=$((seed+1))
  echo "[$(date -u +%H:%M)] rendering $cfg seed $seed"
  node render.js "$cfg" --seeds "$seed" > "batch-$(basename "$cfg" .json)-$seed.log" 2>&1 || { echo "render failed: $cfg $seed"; continue; }
  name=$(basename "$cfg" .json)-s$seed
  ffmpeg -y -loglevel error -i "out/$name/$name.mp4" -c:v libx264 -preset slow -crf 27 -maxrate 5M -bufsize 10M -c:a copy -movflags +faststart "out/$name/$name-preview.mp4"
  echo "[$(date -u +%H:%M)] done $name: $(head -1 "out/$name/meta.txt" >/dev/null; grep '^결과' "out/$name/meta.txt")"
done
