// Presentation-independence check.
// For each seed, replays the match in the browser under different presentation settings
// (look legacy / v25 / v3d, slow-motion on / off) and compares, against node's own simulation:
//   winner, full elimination order, and the order of 'die' events the presentation layer emitted.
// usage: node verify.cjs configs/food.json 13,22,31
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const ROOT=__dirname, MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.css':'text/css','.woff2':'font/woff2'};
const [cfgPath,seedsArg]=process.argv.slice(2);
const cfg=JSON.parse(fs.readFileSync(path.join(ROOT,cfgPath)));
const srv=http.createServer((q,r)=>{const f=path.join(ROOT,decodeURIComponent(q.url.split('?')[0]));
  if(!f.startsWith(ROOT)||!fs.existsSync(f)||fs.statSync(f).isDirectory()){r.writeHead(404);return r.end();}
  r.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(r);});
srv.listen(0,'127.0.0.1',async()=>{
  const {simulate,PHYS_VER}=await import('./sim.mjs');
  const browser=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  let bad=0;
  for(const seed of seedsArg.split(',').map(Number)){
    const rec=simulate({n:cfg.entries.length,seed,spikes:cfg.spikes,shrink:cfg.shrink});
    const want=rec.ranks.map(d=>cfg.entries[d.i].name).join(',')+'|'+cfg.entries[rec.winner].name;
    const rows=[];
    for(const [look,noslow] of [['legacy',0],['v25',0],['v25',1],['v3d',0]]){
      const page=await browser.newPage({viewport:{width:1080,height:1920}});
      await page.goto(`http://127.0.0.1:${srv.address().port}/${look==='legacy'?'legacy':'scene'}.html?look=${look}&cfg=${encodeURIComponent(cfgPath)}&seed=${seed}${noslow?'&noslow=1':''}`);
      await page.waitForFunction('window.ready===true',null,{timeout:120000});
      const L=await page.evaluate(()=>{let q;do{q=window.frame(false);}while(!q.done);return window.getLog();});await page.close();
      const dieOrder=L.events.filter(e=>e.type==='die').sort((a,b)=>b.rank-a.rank).map(e=>cfg.entries[e.i].name).reverse();
      const got=L.ranks.map(r=>r.name).join(',')+'|'+L.winner, ok=got===want&&dieOrder.join(',')===rec.ranks.map(d=>cfg.entries[d.i].name).join(',')&&L.phys===PHYS_VER;
      if(!ok)bad++;
      rows.push(`${look}${noslow?'/noslow':'/slow'}: ${ok?'same':'DIFFERENT'} (video ${L.dur.toFixed(1)}s)`);}
    console.log(`seed ${seed} [${PHYS_VER}] node winner ${cfg.entries[rec.winner].name} :: ${rows.join(' | ')}`);
  }
  console.log(bad?`FAILED: ${bad} mismatches`:'all presentation variants give the same elimination order and winner');
  await browser.close();srv.close();});
