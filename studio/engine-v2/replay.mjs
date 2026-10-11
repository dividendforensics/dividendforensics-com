// Presentation layer over a finished simulation record (sim.mjs).
// Everything here reads the record; nothing writes back, so slow-motion and camera cannot change results.
import {FDT,INTRO} from './sim.mjs';

// video frame -> simulation time. Slow-motion windows are chosen from the record:
//   near miss (hp 1, close to a spike): 0.45x for ~0.35 sim-s, at most one per 3.5 sim-s
//   final kill: eases to 0.25x for the last 0.4 sim-s before the deciding hit
// pace: base playback speed of the match (0.8 = 80%); presentation only, the record is unchanged
// gaps: [{t, g}] per elimination (sim time t, video seconds g it needs on screen). If the next elimination
// would arrive sooner, the stretch between them plays slower so every elimination gets its g seconds.
export function timeline(rec,{noslow=false,outro=5.8,maxFrames=120*30,pace=1,gaps=null}={}){
  const wins=[];
  if(gaps)for(let k=0;k+1<gaps.length;k++){const a=gaps[k].t,b=gaps[k+1].t,r=(b-a)/gaps[k].g;if(r<pace)wins.push({a:a-0.06*r/pace,b,s:Math.max(0.015,r*0.92)});}   // starts a hair early so the ease-down is done by the elimination
  if(!noslow){let cool=-1e9;for(const e of rec.events)if(e.type==='near'&&e.t>cool){cool=e.t+3.5;wins.push({a:e.t-0.04,b:e.t+0.32,s:0.45,e});}
    if(rec.winner!=null)wins.push({a:rec.endT-0.4,b:1e9,s:0.25,win:true});}
  const sim=[],ts=[];let s=0,k=pace,endF=null;
  for(let f=0;f<maxFrames;f++){const tv=f*FDT;
    if(tv>=INTRO){let tgt=pace;for(const w of wins)if(s>=w.a&&s<w.b)tgt=Math.min(tgt,w.s);
      k+=(tgt-k)*(tgt<k?0.65:0.18);s=Math.min(rec.endT,s+FDT*k);}
    sim.push(s);ts.push(k);
    if(endF===null&&s>=rec.endT-1e-9)endF=f;
    if(endF!==null&&(f-endF)*FDT>=outro)break;}
  return {sim,ts,frames:sim.length,endF,near:new Set(wins.filter(w=>w.e).map(w=>w.e))};
}

// walks the event list as sim time advances; keeps hp / alive / last impact per entry
export function replayer(rec){
  const n=rec.n,st={hp:new Array(n).fill(3),alive:new Array(n).fill(true),imp:new Array(n).fill(null),duel:false,winner:null,dead:[],cur:0};
  st.advance=(s0,s1,tv0,tv1,h)=>{const E=rec.events;
    while(st.cur<E.length&&E[st.cur].t<=s1+1e-12){const e=E[st.cur++];
      const tvE=s1>s0?tv0+(e.t-s0)/(s1-s0)*(tv1-tv0):tv1;
      if(e.type==='hit')st.hp[e.i]=e.hp;
      else if(e.type==='die'){st.alive[e.i]=false;st.dead.push({i:e.i,rank:e.rank,t:e.t});}
      else if(e.type==='final'){st.duel=true;for(let i=0;i<n;i++)if(st.alive[i])st.hp[i]=2;}
      else if(e.type==='win')st.winner=e.i;
      else if(e.type==='imp')st.imp[e.i]={t:e.t,v:e.v,nx:e.nx,ny:e.ny,wall:!!e.wall};
      if(h[e.type])h[e.type](e,tvE);}};
  return st;
}

// collision squash, visual only: flatten toward the contact, spring back with one small overshoot.
// returns {s, nx, ny}: s>0 = compressed along (nx,ny) by s*r; the caller keeps the contact side fixed.
export function squash(imp,simT){if(!imp)return {s:0,nx:1,ny:0};const dt=simT-imp.t;if(dt<0||dt>0.4)return {s:0,nx:imp.nx,ny:imp.ny};
  const A=Math.min(0.13,imp.v*0.0085);return {s:A*Math.exp(-dt/0.075)*Math.cos(dt*2*Math.PI/0.19),nx:imp.nx,ny:imp.ny};}
