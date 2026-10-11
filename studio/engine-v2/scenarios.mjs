// Comparison scenes. Same entries and placement for every look, so stills and clips compare 1:1.
//   game     — a normal match (the default)
//   still3   — three beads standing still (material / volume / shadow check)
//   clash    — three beads, no spike damage: approach → bead-bead hit (sim 1.10 s, 19.5 u/s) → wall hit (1.14 s) → separation
//   crowd12  — the real seed-N match, first seconds after GO (small-size readability and clutter)
export function scenario(name,cfg){
  const pick=slugs=>slugs.map(s=>cfg.entries.find(e=>e.slug===s)||cfg.entries[0]);
  switch(name){
    case 'still3':return {entries:pick(['tteokbokki','gimbap','chicken']),hud:false,from:3.0,to:3.0+1/30,
      sim:{frozen:true,fixedRing:true,maxT:2,init:[{x:-1.55,y:-0.45},{x:0.05,y:-1.35},{x:1.6,y:-0.4}]}};
    case 'clash':return {entries:pick(['tteokbokki','gimbap','chicken']),hud:false,from:2.4,to:7.4,
      sim:{noDamage:true,fixedRing:true,maxT:5.2,init:[{x:1.37,y:-0.24,vx:7.11,vy:3.58},{x:0.22,y:2.58,vx:3.96,vy:1.83},{x:-1.45,y:-0.98,vx:0.69,vy:5.93}]}};
    case 'crowd12':return {entries:cfg.entries,hud:true,from:2.0,to:7.0,sim:{}};
    default:return {entries:cfg.entries,hud:true,sim:{}};
  }
}
