#!/usr/bin/env bash
# Usage: ./queue.sh "configs/food.json:14" "configs/weekday.json:22" ...   (config:seed)
# Waits for any running render, then renders each in order and writes a preview copy.
cd "$(dirname "$0")"
while pgrep -f "^node render\.js" >/dev/null; do sleep 15; done
for item in "$@"; do
  cfg=${item%%:*}; seed=${item##*:}; name=$(basename "$cfg" .json)-s$seed
  echo "[$(date -u +%H:%M)] rendering $name"
  if node render.js "$cfg" --seeds "$seed" > "render-q-$name.log" 2>&1 && [ -f "out/$name/$name.mp4" ]; then
    ffmpeg -y -loglevel error -i "out/$name/$name.mp4" -c:v libx264 -preset slow -crf 27 -maxrate 5M -bufsize 10M -c:a copy -movflags +faststart "out/$name/$name-preview.mp4"
    echo "done $name: $(grep '^결과' "out/$name/meta.txt")"
  else echo "failed $name"; fi
done
echo "queue finished"
