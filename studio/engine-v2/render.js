// Usage: node render.js configs/mbti.json [configs/zodiac.json ...] [--seeds 7,8,9] [--keep] [--max 70]
//   --look legacy|v25|v3d   renderer (legacy = p5 visuals on the same simulation record)
//   --scn still3|clash|crowd12|game   comparison scene (see scenarios.mjs); non-game scenes render video only
const {chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const {execFileSync,spawnSync}=require('child_process');
const ROOT=__dirname, MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff'};
const argv=process.argv.slice(2), opt=k=>{const i=argv.indexOf(k);return i>=0?argv[i+1]:null;};
const cfgs=argv.filter((a,i)=>a.endsWith('.json')&&!['--seeds','--shots','--fonts','--look','--scn'].includes(argv[i-1]));
const look=opt('--look')||'v3d', scn=opt('--scn')||'game';
const seedsArg=opt('--seeds'), keep=argv.includes('--keep'), maxSec=+(opt('--max')||70);
// --shots 45,200,600: quick look — simulate every frame but only render/save these, no audio/video
const fontsArg=opt('--fonts'); // e.g. --fonts bungee,black-han-sans
const hudTest=argv.includes('--hudtest'); // layout self-test, prints worst-case margins
const simOnly=argv.includes('--sim'); // simulate only: print the winner per seed, write nothing
const shots=opt('--shots')?new Set(opt('--shots').split(',').map(Number)):null;
function serve(){return new Promise(res=>{const srv=http.createServer((q,r)=>{
  const f=path.join(ROOT,decodeURIComponent(q.url.split('?')[0]));
  if(!f.startsWith(ROOT)||!fs.existsSync(f)||fs.statSync(f).isDirectory()){r.writeHead(404);return r.end();}
  r.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(r);});
  srv.listen(0,'127.0.0.1',()=>res(srv));});}
(async()=>{
  const srv=await serve(), port=srv.address().port;
  const browser=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  for(const cfgPath of cfgs){
    const cfg=JSON.parse(fs.readFileSync(path.join(ROOT,cfgPath)));
    const seeds=seedsArg?seedsArg.split(',').map(Number):[cfg.seed||1];
    for(const seed of seeds){
      const name=path.basename(cfgPath,'.json')+'-s'+seed+(scn!=='game'?'-'+scn:'')+'-'+look, out=path.join(ROOT,'out',(shots||simOnly||hudTest)?'_scratch':'',name), fdir=path.join(out,'frames'); // previews never touch real render output
      if(!simOnly){fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(fdir,{recursive:true});}
      const page=await browser.newPage({viewport:{width:1080,height:1920}});
      page.on('pageerror',e=>console.error('[page]',e.message));
      page.on('console',m=>{if(m.type()==='error'&&!/404/.test(m.text()))console.error('[console]',m.text());else if(/^(fonts|icon pictures|assets):/.test(m.text()))console.log('  '+m.text());});
      await page.goto(`http://127.0.0.1:${port}/${look==='legacy'?'legacy':'scene'}.html?look=${look}&scn=${scn}&cfg=${encodeURIComponent(cfgPath)}&seed=${seed}${argv.includes('--noslow')?'&noslow=1':''}${fontsArg?'&fonts='+encodeURIComponent(fontsArg):''}`);
      await page.waitForFunction('window.ready===true',null,{timeout:120000});
      if(hudTest){const cases=[];for(const rank of [1,12,100])for(const [name,icon] of [['치킨','🍗'],['김치찌개','🍲'],['아주아주아주긴음식이름입니다',''],['ENTP','']])cases.push({rank,name,icon});
        const res=await page.evaluate(c=>window.__hudTest(c),cases);await page.close();
        for(const x of res)console.log(`hudtest ${String(x.rank).padStart(3)}위 | ${x.name.padEnd(14)} | min margin ${Math.round(x.minMargin)}px ${x.minMargin<30?'  <-- TOO TIGHT':''}`);continue;}
      if(simOnly){let q;do{q=await page.evaluate(()=>window.frame(false));}while(!q.done&&q.t<maxSec);const L=await page.evaluate(()=>window.getLog());await page.close();console.log(`sim ${name} winner ${L.winner}`);continue;}
      const info=await page.evaluate(()=>window.info||{});const fromF=Math.round((info.from||0)*30),toF=info.to!=null?Math.round(info.to*30):1e9;
      const t0=Date.now();let i=0,r,saved=0;
      do{const want=shots?shots.has(i):(i>=fromF&&i<toF);
        const res=await page.evaluate(w=>{const r=window.frame(w);return{r,d:w?document.getElementById('out').toDataURL('image/jpeg',0.92).split(',')[1]:null};},want);
        r=res.r;if(res.d)fs.writeFileSync(path.join(fdir,String(shots?i:saved++).padStart(5,'0')+'.jpg'),Buffer.from(res.d,'base64'));i++;
        if(i>=toF)break;
        if(shots&&i>Math.max(...shots))break;
        if(i%150===0)console.log(`  ${name}: ${i} frames, ${r.alive} alive, ${((Date.now()-t0)/Math.max(1,saved)).toFixed(0)}ms/saved frame`);
      }while(!r.done&&i<maxSec*30);
      if(shots){await page.close();console.log(`shots ${name}: ${[...shots].join(',')} -> ${fdir} (${((Date.now()-t0)/1000).toFixed(0)}s)`);continue;}
      const log=await page.evaluate(()=>window.getLog());await page.close();
      fs.writeFileSync(path.join(out,'log.json'),JSON.stringify(log));
      if(scn!=='game'){const mp4=path.join(out,name+'.mp4');   // comparison clip: picture only
        if(saved>1)execFileSync('ffmpeg',['-y','-loglevel','error','-framerate','30','-i',path.join(fdir,'%05d.jpg'),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',mp4]);
        else fs.copyFileSync(path.join(fdir,'00000.jpg'),path.join(out,name+'.jpg'));
        console.log(`done ${name}: ${saved} frames, ${((Date.now()-t0)/1000).toFixed(0)}s render (${((Date.now()-t0)/Math.max(1,saved)/1000).toFixed(2)}s/frame incl. skipped)`);continue;}
      execFileSync('python3',[path.join(ROOT,'audio.py'),out],{stdio:'inherit'});
      const mp4=path.join(out,name+'.mp4');
      execFileSync('ffmpeg',['-y','-loglevel','error','-framerate','30','-i',path.join(fdir,'%05d.jpg'),'-i',path.join(out,'audio.wav'),
        '-c:v','libx264','-preset','medium','-crf','22','-maxrate','12M','-bufsize','24M','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',mp4]);
      // loudness/true-peak of the encoded file, not the WAV: AAC can overshoot the source peak
      const meas=f=>{const e=spawnSync('ffmpeg',['-hide_banner','-nostats','-i',f,'-map','0:a','-af','ebur128=peak=true','-f','null','-'],{encoding:'utf8'}).stderr;
        const tp=[...e.matchAll(/Peak:\s+(-?[\d.]+|-inf) dBFS/g)].pop(),I=[...e.matchAll(/I:\s+(-?[\d.]+) LUFS/g)].pop();return{tp:tp?parseFloat(tp[1]):NaN,I:I?parseFloat(I[1]):NaN};};
      let am=meas(mp4);
      if(!(am.tp<=-1)){const fix=path.join(out,'fix.mp4'),g=(-(am.tp+1.5)).toFixed(2);
        execFileSync('ffmpeg',['-y','-loglevel','error','-i',mp4,'-c:v','copy','-af',`volume=${g}dB`,'-c:a','aac','-b:a','192k','-movflags','+faststart',fix]);fs.renameSync(fix,mp4);am=meas(mp4);}
      console.log(`  audio check (final mp4): true peak ${am.tp} dBTP, integrated ${am.I} LUFS ${am.tp<=-1?'OK':'STILL HOT'}`);
      const up=cfg.upload||{};
      fs.writeFileSync(path.join(out,'meta.txt'),[`제목: ${up.title||cfg.title.join(' ')}`,'',
        `설명: ${up.description||''}`,'',`해시태그: ${(up.hashtags||[]).join(' ')}`,'',
        `결과 (seed ${seed}, 물리 ${log.phys}): 1위 ${log.winner}`,`오디오(최종 MP4 측정): true peak ${am.tp} dBTP, ${am.I} LUFS`,...log.ranks.map(r=>`${r.rank}위 ${r.name} (${r.t}초)`)].join('\n'));
      if(!keep)fs.rmSync(fdir,{recursive:true,force:true});
      fs.rmSync(path.join(out,'audio.wav'),{force:true});
      console.log(`done ${name}: ${(i/30).toFixed(1)}s video, winner ${log.winner}, ${((Date.now()-t0)/1000).toFixed(0)}s render`);
    }
  }
  await browser.close();srv.close();
})().catch(e=>{console.error(e);process.exit(1);});
