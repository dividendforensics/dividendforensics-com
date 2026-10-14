#!/bin/bash
# usage: batch/run-chunk.sh START END   (1-based indexes into batch/[0-9][0-9]-*.json)
# Run as a foreground command of a background task: a detached nohup child was killed when its launcher task ended.
cd "$(dirname "$0")/.."
i=0
for f in batch/[0-9][0-9]-*.json; do
  i=$((i+1))
  if [ "$i" -lt "$1" ] || [ "$i" -gt "$2" ]; then continue; fi
  if python3 batch/is_done.py "$f"; then echo "== [$i/18] skip (already finished and checked) $f"; continue; fi
  echo "== [$i/18] render $f $(date +%F_%T)"
  node render.js "$f" --look v3d --bg nebula 2>&1 | grep -E "^done|audio check|rror"
done
echo "== CHUNK DONE $1-$2 $(date +%F_%T)"
