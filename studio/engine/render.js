// Usage: node render.js configs/mbti.json [configs/zodiac.json ...] [--seeds 7,8,9] [--keep] [--max 70]
const {chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const {execFileSync}=require('child_process');
const ROOT=__dirname, MIME={'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff'};
const argv=process.argv.slice(2), opt=k=>{const i=argv.indexOf(k);return i>=0?argv[i+1]:null;};
const cfgs=argv.filter((a,i)=>a.endsWith('.json')&&!['--seeds','--shots'].includes(argv[i-1]));
const seedsArg=opt('--seeds'), keep=argv.includes('--keep'), maxSec=+(opt('--max')||70);
// --shots 45,200,600: quick look — simulate every frame but only render/save these, no audio/video
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
      const name=path.basename(cfgPath,'.json')+'-s'+seed, out=path.join(ROOT,'out',name), fdir=path.join(out,'frames');
      fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(fdir,{recursive:true});
      const page=await browser.newPage({viewport:{width:1080,height:1920}});
      page.on('pageerror',e=>console.error('[page]',e.message));
      page.on('console',m=>{if(m.type()==='error')console.error('[console]',m.text());});
      await page.goto(`http://127.0.0.1:${port}/scene.html?cfg=${encodeURIComponent(cfgPath)}&seed=${seed}`);
      await page.waitForFunction('window.ready===true',null,{timeout:120000});
      const t0=Date.now();let i=0,r;
      do{const want=!shots||shots.has(i);
        const res=await page.evaluate(w=>{const r=window.frame(w);return{r,d:w?document.getElementById('out').toDataURL('image/jpeg',0.92).split(',')[1]:null};},want);
        r=res.r;if(res.d)fs.writeFileSync(path.join(fdir,String(i).padStart(5,'0')+'.jpg'),Buffer.from(res.d,'base64'));i++;
        if(shots&&i>Math.max(...shots))break;
        if(i%150===0)console.log(`  ${name}: ${i} frames, ${r.alive} alive, ${((Date.now()-t0)/i).toFixed(0)}ms/frame`);
      }while(!r.done&&i<maxSec*30);
      if(shots){await page.close();console.log(`shots ${name}: ${[...shots].join(',')} -> ${fdir} (${((Date.now()-t0)/1000).toFixed(0)}s)`);continue;}
      const log=await page.evaluate(()=>window.getLog());await page.close();
      fs.writeFileSync(path.join(out,'log.json'),JSON.stringify(log));
      execFileSync('python3',[path.join(ROOT,'audio.py'),out],{stdio:'inherit'});
      const mp4=path.join(out,name+'.mp4');
      execFileSync('ffmpeg',['-y','-loglevel','error','-framerate','30','-i',path.join(fdir,'%05d.jpg'),'-i',path.join(out,'audio.wav'),
        '-c:v','libx264','-preset','medium','-crf','22','-maxrate','12M','-bufsize','24M','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',mp4]);
      const up=cfg.upload||{};
      fs.writeFileSync(path.join(out,'meta.txt'),[`제목: ${up.title||cfg.title.join(' ')}`,'',
        `설명: ${up.description||''}`,'',`해시태그: ${(up.hashtags||[]).join(' ')}`,'',
        `결과 (seed ${seed}): 1위 ${log.winner}`,...log.ranks.map(r=>`${r.rank}위 ${r.name} (${r.t}초)`)].join('\n'));
      if(!keep)fs.rmSync(fdir,{recursive:true,force:true});
      fs.rmSync(path.join(out,'audio.wav'),{force:true});
      console.log(`done ${name}: ${(i/30).toFixed(1)}s video, winner ${log.winner}, ${((Date.now()-t0)/1000).toFixed(0)}s render`);
    }
  }
  await browser.close();srv.close();
})().catch(e=>{console.error(e);process.exit(1);});
