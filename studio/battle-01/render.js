const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
 const out=path.join(__dirname,'frames');fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
 const p=await b.newPage({viewport:{width:1080,height:1920}});
 await p.goto('file://'+path.join(__dirname,'scene.html'));await p.waitForFunction('window.ready===true');
 let i=0,r;
 do{ r=await p.evaluate(()=>window.frame());
  {const d=await p.evaluate(()=>document.getElementById('c').toDataURL('image/jpeg',0.92).split(',')[1]);
   fs.writeFileSync(path.join(out,String(i).padStart(5,'0')+'.jpg'),Buffer.from(d,'base64'));}
  i++; if(i>60*60)break; }while(!r.done);
 const ev=await p.evaluate(()=>window.events);fs.writeFileSync(path.join(__dirname,'events.json'),JSON.stringify({dur:r.t,events:ev}));
 await b.close();console.log('frames',i,'dur',r.t.toFixed(2),'events',ev.length);
})().catch(e=>{console.error(e);process.exit(1)});
