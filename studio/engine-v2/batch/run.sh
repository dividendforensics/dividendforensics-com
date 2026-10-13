#!/bin/bash
# Batch: connection-independence check first, then every upload candidate in order (real 3D, nebula, with audio).
cd "$(dirname "$0")/.."
echo "== verify $(date +%T)"
node verify.cjs configs/food.json 13,22 2>&1 | grep -v "^\["
for f in batch/[0-9][0-9]-*.json; do
  echo "== render $f $(date +%T)"
  node render.js "$f" --look v3d --bg nebula 2>&1 | grep -E "^done|audio check|rror"
done
echo "== ALLDONE $(date +%T)"
