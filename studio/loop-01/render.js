const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
 const out=path.join(__dirname,'frames');fs.mkdirSync(out,{recursive:true});
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-gl=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage({viewport:{width:720,height:1280}});
 await p.goto('file://'+path.join(__dirname,'scene.html'));
 await p.waitForFunction('window.ready===true');
 const FPS=30,N=8*FPS;
 for(let i=0;i<N;i++){
  await p.evaluate(t=>window.render(t),i/FPS);
  const d=await p.evaluate(()=>document.getElementById('c').toDataURL('image/png').split(',')[1]);
  fs.writeFileSync(path.join(out,String(i).padStart(4,'0')+'.png'),Buffer.from(d,'base64'));
 }
 await b.close();console.log('frames',N);
})().catch(e=>{console.error(e);process.exit(1)});
