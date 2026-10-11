// node sim-check.mjs configs/food.json 13,22   → winner and elimination order per seed (no browser)
import {simulate,PHYS_VER} from './sim.mjs';
import fs from 'fs';
const [cfgPath,seedsArg]=process.argv.slice(2);
const cfg=JSON.parse(fs.readFileSync(cfgPath));
for(const seed of (seedsArg||String(cfg.seed||1)).split(',').map(Number)){
  const r=simulate({n:cfg.entries.length,seed,spikes:cfg.spikes,shrink:cfg.shrink});
  const nm=i=>cfg.entries[i].name;
  console.log(`seed ${seed} [${PHYS_VER}] winner ${nm(r.winner)} at ${r.endT.toFixed(2)}s | ${r.ranks.map(d=>`${d.rank}:${nm(d.i)}@${d.t.toFixed(2)}`).join(' ')}`);
}
