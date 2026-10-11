// Pure simulation: no rendering, no wall-clock, no presentation state.
// Runs the whole match first and returns a record (positions every physics step + events in
// simulation time). Camera, slow-motion and effects only ever READ this record, so changing the
// look cannot change who wins. Works in the browser and in node (node sim-check.mjs).
//
// Fixed for a given (PHYS_VER, entries count, seed, scenario):
//   initial state  — slot shuffle (n-1 rnd calls), then per entry: position slot on a circle of R0*0.62, velocity (2 rnd calls),
//                    plus the intro bob offset the p5 engine applied during the 72 intro frames
//   rule version   — PHYS_VER below; bump it whenever anything in this file changes outcomes
//   rng order      — one physics rng (mulberry32 on a hashed seed), used only at initialisation, in the order above
//   time step      — DTF = 1/120 s, fixed; slow-motion never changes it
export const PHYS_VER='p6-detmath-shuffledslots-120hz';
// Math.sin/cos are NOT bit-identical across JS engines (node 22 and Chromium 141 differ in the last
// bits), and the match is chaotic, so a 1e-16 difference flips the winner. Physics therefore uses only
// + - * / and sqrt (IEEE-754 exact on every engine) through these functions.
const TAU=6.283185307179586;
export function dsin(x){let r=x-Math.round(x/TAU)*TAU;            /* [-pi, pi] */
  if(r>Math.PI/2)r=Math.PI-r;else if(r<-Math.PI/2)r=-Math.PI-r;    /* [-pi/2, pi/2] */
  const z=r*r;return r*(1+z*(-1/6+z*(1/120+z*(-1/5040+z*(1/362880+z*(-1/39916800+z*(1/6227020800+z*(-1/1307674368000+z*(1/355687428096000)))))))));}
export const dcos=x=>dsin(x+Math.PI/2);
function datan(x){let s=1;if(x<0){x=-x;s=-1;}let y=0;          /* cephes atan, arithmetic only */
  if(x>2.414213562373095){y=Math.PI/2;x=-1/x;}else if(x>0.66){y=Math.PI/4;x=(x-1)/(x+1);}
  const z=x*x,p=(((-8.750608600031904122785e-1*z-1.615753718733365076637e1)*z-7.500855792314704667340e1)*z-1.228866684490136173410e2)*z-6.485021904942025371773e1,
    q=((((z+2.485846490142306297962e1)*z+1.650270098316988542046e2)*z+4.328810604912902668951e2)*z+4.853903996359136964868e2)*z+1.945506571482613964425e2;
  return s*(y+x+x*z*p/q);}
export function datan2(y,x){if(x>0)return datan(y/x);if(x<0)return datan(y/x)+(y>=0?Math.PI:-Math.PI);return y>0?Math.PI/2:y<0?-Math.PI/2:0;}
const dhyp=(x,y)=>Math.sqrt(x*x+y*y);
export const FPS=30, FDT=1/FPS, DTF=FDT/4, INTRO=2.4;
export const mixSeed=x=>{x=Math.imul((x^(x>>>16))>>>0,0x45d9f3b);x=Math.imul((x^(x>>>16))>>>0,0x45d9f3b);return (x^(x>>>16))>>>0;};
export const mb32=seed=>{let t=seed>>>0;return()=>{t=(t+0x6D2B79F5)>>>0;let r=Math.imul(t^(t>>>15),1|t);r=(r+Math.imul(r^(r>>>7),61|r))^r;return((r^(r>>>14))>>>0)/4294967296;};};
export const arenaFor=n=>({BR:n>12?0.5:0.6,R0:4.6,RMIN:n>12?1.75:1.7,G:13,SD:30});

// opts: n, seed, spikes=10, shrink=26, maxT (sim seconds), and for comparison scenes:
//   init:[{x,y,vx,vy}] overrides the start state, noDamage (spikes never hurt), frozen (nothing moves),
//   fixedRing (ring stays at R0), G override
export function simulate(opts){
  const n=opts.n, seed=opts.seed>>>0, NS=opts.spikes||10, SHRINK=opts.shrink||26, maxT=opts.maxT||90;
  const A=arenaFor(n), BR=A.BR, R0=A.R0, RMIN=A.RMIN, G=opts.G??A.G, SD=A.SD;
  const rnd=mb32(mixSeed(seed+0x9e3779b9));
  const balls=[];
  // start slots are shuffled per seed: a fixed slot per entry made some entries lose more often (slot 8: 29/600 wins vs ~50)
  const slot=[...Array(n).keys()];for(let i=n-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[slot[i],slot[j]]=[slot[j],slot[i]];}
  for(let i=0;i<n;i++){const a=slot[i]/n*Math.PI*2, r=R0*0.62, sa=rnd()*Math.PI*2, sp=7+rnd()*3;
    balls.push({i,x:dcos(a)*r,y:dsin(a)*r,vx:dcos(sa)*sp,vy:dsin(sa)*sp,r:BR,hp:3,alive:true,inv:0});}
  // the p5 engine nudged y during the intro frames; it is part of the fixed initial state
  for(let f=0;;f++){const tv=f*FDT;if(tv>=INTRO)break;for(const b of balls)b.y+=dsin(tv*4+b.i)*0.004;}
  if(opts.init)opts.init.forEach((s,i)=>Object.assign(balls[i],s));
  const steps=Math.ceil(maxT/DTF)+2;
  const pos=new Float64Array(steps*n*2), ringA=new Float64Array(steps), spinA=new Float64Array(steps);
  const events=[], deaths=[];
  let simT=0, ring=R0, spin=0, spinV=0.6, duel=false, winner=null, k=0;
  const alive=()=>balls.filter(b=>b.alive);
  const tension=()=>1-(alive().length-1)/(n-1);
  const ev=(type,o)=>events.push({t:simT,type,...o});
  const save=()=>{ringA[k]=ring;spinA[k]=spin;for(const b of balls){pos[(k*n+b.i)*2]=b.x;pos[(k*n+b.i)*2+1]=b.y;}k++;};
  function die(b){const rank=alive().length;b.alive=false;deaths.push({i:b.i,rank,t:simT});ev('die',{i:b.i,rank});
    const left=alive().length;
    if(left===2){duel=true;ev('final',{});for(const a of alive()){a.hp=2;a.inv=1.2;}}
    if(left===1){winner=alive()[0];ev('win',{i:winner.i});}}
  function hit(b,nx,ny){b.hp--;b.inv=0.35;b.vx-=nx*3;b.vy-=ny*3;ev('hit',{i:b.i,nx,ny,hp:b.hp});if(b.hp<=0)die(b);}
  function step(dt){
    simT+=dt;const rT=duel?2.5:Math.max(RMIN,R0-(R0-RMIN)*Math.min(1,simT/SHRINK));
    if(!opts.fixedRing)ring+=(rT-ring)*Math.min(1,dt*2.5);
    spinV=Math.min(2.4,0.6+0.05*simT);spin+=spinV*dt;
    const hitW=duel?0.05:0.075+0.06*Math.max(0,1-simT/9)+Math.max(0,simT-SD)*0.012, T=tension();
    for(const b of balls){if(!b.alive)continue;b.inv-=dt;b.vy-=G*dt;b.x+=b.vx*dt;b.y+=b.vy*dt;
      const d=dhyp(b.x,b.y)||1e-6;
      if(d+b.r>ring){const nx=b.x/d,ny=b.y/d;b.x=nx*(ring-b.r);b.y=ny*(ring-b.r);const vn=b.vx*nx+b.vy*ny;
        if(vn>0){ev('imp',{i:b.i,v:vn,nx,ny,wall:1});b.vx-=2*vn*nx;b.vy-=2*vn*ny;const push=spinV*ring*0.16;b.vx+=-ny*push;b.vy+=nx*push;
          const sp=dhyp(b.vx,b.vy),lo=7+3*T,hi=15;if(sp<lo){b.vx*=lo/sp;b.vy*=lo/sp;}else if(sp>hi){b.vx*=hi/sp;b.vy*=hi/sp;}
          const a=datan2(ny,nx)-spin,kk=((a/(2*Math.PI)*NS)%1+1)%1,dist=Math.abs(kk-0.5);
          if(dist<hitW&&b.inv<=0&&!opts.noDamage)hit(b,nx,ny);
          else{if(dist<0.17&&b.hp===1&&b.inv<=0)ev('near',{i:b.i});ev('bounce',{i:b.i,v:vn});}}}}
    const L=alive();
    for(let i=0;i<L.length;i++)for(let j=i+1;j<L.length;j++){const a=L[i],b=L[j],dx=b.x-a.x,dy=b.y-a.y,d=dhyp(dx,dy)||1e-6,md=a.r+b.r;
      if(d<md){const nx=dx/d,ny=dy/d,ov=(md-d)/2;a.x-=nx*ov;a.y-=ny*ov;b.x+=nx*ov;b.y+=ny*ov;
        const rv=(b.vx-a.vx)*nx+(b.vy-a.vy)*ny;if(rv<0){a.vx+=rv*nx;a.vy+=rv*ny;b.vx-=rv*nx;b.vy-=rv*ny;
          ev('imp',{i:a.i,v:-rv,nx,ny});ev('imp',{i:b.i,v:-rv,nx:-nx,ny:-ny});
          if(-rv>6)ev('clack',{i:a.i,j:b.i});}}}
  }
  save();
  while(!winner&&simT<maxT-1e-9&&k<steps){if(!opts.frozen)step(DTF);else simT+=DTF;save();}
  const ranks=deaths.slice().sort((a,b)=>a.rank-b.rank);
  return {phys:PHYS_VER,seed,n,BR,R0,NS,dtf:DTF,steps:k,pos,ring:ringA,spin:spinA,events,deaths,
    winner:winner?winner.i:null,endT:simT,ranks};
}

// position of ball i at simulation time t (linear between fixed steps)
export function sample(rec,i,t){const u=Math.max(0,Math.min(rec.steps-1,t/rec.dtf)),k0=Math.floor(u),k1=Math.min(rec.steps-1,k0+1),w=u-k0,n=rec.n;
  return [rec.pos[(k0*n+i)*2]*(1-w)+rec.pos[(k1*n+i)*2]*w, rec.pos[(k0*n+i)*2+1]*(1-w)+rec.pos[(k1*n+i)*2+1]*w];}
export function sampleArr(arr,rec,t){const u=Math.max(0,Math.min(rec.steps-1,t/rec.dtf)),k0=Math.floor(u),k1=Math.min(rec.steps-1,k0+1),w=u-k0;return arr[k0]*(1-w)+arr[k1]*w;}
