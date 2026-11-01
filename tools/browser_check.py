#!/usr/bin/env python3
"""Browser checks + screenshots. Does not submit inquiries or visit outside links.

By default uses a local HTTP server. --inline renders source, CSS, script and
images in memory for environments in which localhost requests are restricted.
"""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit
import argparse,base64,json,mimetypes,os,sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def send_error(self,code,message=None,explain=None):
        if code==404:
            data=(ROOT/'404.html').read_bytes()
            self.send_response(404);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        else:super().send_error(code,message,explain)

def inline_source(name):
    soup=BeautifulSoup((ROOT/name).read_text(),'html.parser')
    base=soup.new_tag('base',href='https://dividendforensics.com/');soup.head.insert(0,base)
    for link in list(soup.select('link')):
        href=link.get('href','')
        if link.get('rel')==['stylesheet'] and href.startswith('/'):
            style=soup.new_tag('style');style.string=(ROOT/href.lstrip('/')).read_text();link.replace_with(style)
        elif href.startswith('https://fonts.') or link.get('rel')==['icon']:link.decompose()
    for img in soup.select('img[src]'):
        p=ROOT/img['src'].lstrip('/')
        if p.is_file():img['src']='data:'+str(mimetypes.guess_type(p.name)[0])+';base64,'+base64.b64encode(p.read_bytes()).decode()
        img['loading']='eager'
    for script in soup.select('script[src]'):
        p=ROOT/script['src'].lstrip('/')
        if p.is_file():
            del script['src'];script.attrs.pop('defer',None);script.string=p.read_text();script.extract();soup.body.append(script)
    return str(soup)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inline',action='store_true');ap.add_argument('--widths',default='320,390,768,1024,1440');ap.add_argument('--output',default='/tmp/dfb-preview');args=ap.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    pages=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*.html') if '.qa' not in p.parts and 'name="dfb-design"' in p.read_text()]
    server=None
    if not args.inline:
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
        Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    errors=[];measurements=[];screens=['three-financial-statements.html','learning-search.html','operating-companies.html','brief-microsoft-fy2027-q1-cash-capex-bridge.html','stock-classification.html','market-labels.html','index.html','research.html','research-desk.html','learn.html','about.html','tools.html','404.html','learn-bdc.html','course-bdc-beginner.html','learn-bdc-expert-income-bridge.html','es/index.html','es/calculadora-dividendos.html']
    with sync_playwright() as p:
        exe=os.environ.get('CHROMIUM_PATH')
        b=p.chromium.launch(**({'executable_path':exe} if exe else {}),headless=True,args=['--no-sandbox'])
        def load(page,name):
            page.route('https://fonts.googleapis.com/**',lambda route:route.abort())
            page.route('https://fonts.gstatic.com/**',lambda route:route.abort())
            if args.inline:page.set_content(inline_source(name),wait_until='load')
            else:
                page.goto(base+'/'+name,wait_until='networkidle')
                page.evaluate("document.querySelectorAll('img').forEach(i=>i.loading='eager')")
            page.evaluate("Promise.all([...document.images].map(i=>i.decode().catch(()=>null)))")
        # Page overflow misses text spilling into an adjacent grid track. Inspect
        # actual text-line rectangles, including the previously colliding 1188px view.
        for width in (320,390,600,768,1024,1051,1188,1440):
            page=b.new_page(viewport={'width':width,'height':900})
            load(page,'index.html')
            page.evaluate('document.fonts.ready')
            for selector in ('.brand-name','.hero-bottom-line','.site-footer h2','.home-page .education-home .kicker'):
                for element in page.locator(selector).all():
                    if element.is_visible():
                        assert element.evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)>=12'), (width,selector)
            assert page.locator('.home-curriculum .course-card').count()==4
            collisions=page.evaluate(r'''() => {
              const lines=element=>{
                const walker=document.createTreeWalker(element,NodeFilter.SHOW_TEXT), rects=[];
                while(walker.nextNode()) {
                  if(!walker.currentNode.textContent.trim()) continue;
                  const range=document.createRange();range.selectNodeContents(walker.currentNode);
                  rects.push(...[...range.getClientRects()].map(r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom})));
                }
                return rects;
              };
              return [...document.querySelectorAll('.home-curriculum .course-card')].flatMap(card=>{
                const title=card.querySelector('h3'), copy=card.querySelector('p'), bounds=card.getBoundingClientRect();
                const heading=lines(title), body=lines(copy);
                const overlap=heading.some(a=>body.some(b=>Math.max(b.left-a.right,a.left-b.right)<8 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1));
                const outside=heading.some(r=>r.left<bounds.left-1 || r.right>bounds.right+1);
                return overlap || outside ? [{title:title.textContent.trim(),overlap,outside,heading,body}] : [];
              });
            }''')
            measurements.append(dict(page='index.html',width=width,curriculumTextCollisions=collisions))
            if collisions:errors.append(f'index.html@{width}: curriculum text collision {collisions}')
            if width==1188:
                page.locator('.home-curriculum').screenshot(path=str(out/'home-curriculum-1188.png'))
            page.close()
        for width in map(int,args.widths.split(',')):
            for name in pages:
                page=b.new_page(viewport={'width':width,'height':900})
                page.on('pageerror',lambda err:errors.append(str(err)))
                if args.inline:page.route('https://**/*',lambda r:r.abort())
                load(page,name)
                metrics=page.evaluate('''() => ({viewport:innerWidth,content:document.documentElement.scrollWidth,h1:document.querySelectorAll('h1').length,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.alt)})''')
                measurements.append(dict(page=name,width=width,**metrics))
                if metrics['content']>width+1:errors.append(f'{name}@{width}: horizontal overflow {metrics["content"]}')
                if metrics['h1']!=1:errors.append(f'{name}: h1 count')
                if metrics['brokenImages']:errors.append(f'{name}: broken image {metrics["brokenImages"]}')
                if name in screens and width in (390,1440):
                    suffix='mobile' if width==390 else 'desktop'
                    page.screenshot(path=str(out/f'{name.replace('/','-')[:-5]}-{suffix}.png'),full_page=True)
                    if name in ('index.html','research-desk.html'):page.screenshot(path=str(out/f'{name.replace('/','-')[:-5]}-{suffix}-top.png'))
                page.close()
        # Search and filters operate on the complete static archive.
        page=b.new_page(viewport={'width':1440,'height':900});load(page,'research.html')
        total=page.locator('.archive-entry').count()
        page.locator('#research-search').fill('OTF')
        assert page.locator('.archive-entry:visible').count()==1,'OTF search'
        page.locator('[data-filter="REIT"]').click()
        assert page.locator('#archive-empty').is_visible(),'empty state'
        page.locator('#research-search').fill('');page.locator('[data-filter="all"]').click()
        assert page.locator('.archive-entry:visible').count()==total,'reset filters'
        page.close()
        page=b.new_page(viewport={'width':390,'height':844});load(page,'index.html')
        assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
        page.locator('.menu-toggle').click();assert page.locator('#site-links').is_visible()
        page.keyboard.press('Escape');assert not page.locator('#site-links').is_visible()
        assert page.locator('.menu-toggle').evaluate('(e)=>e===document.activeElement'),'escape returns focus'
        page.close()
        # No request is sent: browser validates form fields and target locally.
        page=b.new_page(viewport={'width':1440,'height':900});load(page,'research-desk.html')
        assert page.locator('form').get_attribute('action')=='https://formsubmit.co/ba46f1f257eba5688fcf0b5122a8b335'
        assert not page.locator('form').evaluate('(f)=>f.checkValidity()')
        for selector,value in [('#rd-n','Test reader'),('#rd-o','Test organization'),('#rd-e','reader@example.com'),('#rd-m','Local validation only; do not submit.')]:page.locator(selector).fill(value)
        page.locator('#rd-t').select_option(label='Question or correction')
        page.locator('#rd-privacy').check()
        assert page.locator('form').evaluate('(f)=>f.checkValidity()')
        page.close()
        # JavaScript is not necessary to read research or use navigation.
        ctx=b.new_context(java_script_enabled=False,viewport={'width':390,'height':844});page=ctx.new_page()
        if args.inline:page.set_content(inline_source('research.html'),wait_until='load')
        else:page.goto(base+'/research.html',wait_until='networkidle')
        assert page.locator('.archive-entry:visible').count()==total
        assert page.locator('#site-links').is_visible()
        ctx.close()
        if not args.inline:
            page=b.new_page();response=page.goto(base+'/missing/deep/research-record',wait_until='networkidle')
            assert response.status==404
            assert page.locator('h1').inner_text().startswith('This address')
            assert page.locator('a[href="/research.html"]').count()>0
            page.close()
        b.close()
    if server:server.shutdown()
    result={'pages':len(pages),'viewports':args.widths,'renders':len(measurements),'errors':errors,'functional_checks':['search','sector filters','empty state','mobile menu','Escape focus','form validation (not submitted)','no-JavaScript reading'],'measurements':measurements}
    (out/'browser-report.json').write_text(json.dumps(result,indent=2))
    if errors:
        print('\n'.join(errors));return 1
    print(f'PASS: {len(measurements)} renders, {len(pages)} pages; no overflow or broken images; all functional checks passed.')
    return 0
if __name__=='__main__':sys.exit(main())
