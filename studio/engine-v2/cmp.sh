#!/bin/bash
# comparison set: same entries and placement for every look (see scenarios.mjs)
cd "$(dirname "$0")"
for scn in ${SCNS:-still3 clash crowd12}; do for look in ${LOOKS:-legacy v25 v3d}; do
  node render.js configs/food.json --seeds ${SEED:-13} --look $look --scn $scn 2>&1 | grep -E "^done|Error|error" ; done; done
echo ALLDONE
