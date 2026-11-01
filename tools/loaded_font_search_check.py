"""Strict online-font homepage check. A font/network failure is NOT a fallback pass.

The before CSS is reconstructed byte-for-byte from this narrow patch's prefix,
then checked against the base commit's digest. No production font hosting changes.
"""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import hashlib,json,os
ROOT=Path(__file__).resolve().parents[1]
BASE_CSS_SHA='bded3ba53eb2986fca6fccf98c297ae25ace8856a56fe7febe78a9332c5ba416'
MARKER='\n/* Allow the search grid item to shrink at 320px, with real web fonts too. */'

def main():
    from playwright.sync_api import sync_playwright
    out=Path('/tmp/dfb-preview');out.mkdir(exist_ok=True)
    css=(ROOT/'bureau.css').read_text()
    before=css.split(MARKER)[0]
    assert hashlib.sha256(before.encode()).hexdigest()==BASE_CSS_SHA, 'Baseline CSS must remain byte-exact; explicitly rebase this regression if typography changes.'
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    report={'base':'a1f9a0df769f828e438188798511855bb0a73d16','baseline_css_sha256':BASE_CSS_SHA,'status':'not completed','runs':[]}
    try:
        with sync_playwright() as p:
            options={'headless':True}
            if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
            browser=p.chromium.launch(**options)
            for variant in ('before','after'):
                context=browser.new_context(viewport={'width':320,'height':900})
                page=context.new_page();network=[]
                page.on('response',lambda r:network.append({'url':r.url,'status':r.status}) if 'fonts.' in r.url else None)
                page.on('requestfailed',lambda r:network.append({'url':r.url,'failure':r.failure}) if 'fonts.' in r.url else None)
                if variant=='before':
                    page.route('**/bureau.css',lambda route:route.fulfill(status=200,content_type='text/css',body=before))
                try:
                    page.goto(f'http://127.0.0.1:{server.server_port}/index.html',wait_until='load')
                    fonts=page.evaluate('''async () => {
                        const faces=await Promise.all([document.fonts.load('400 16px Inter','Search'),document.fonts.load('400 39px "EB Garamond"','Find your next insight.')]);
                        await document.fonts.ready;
                        await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                        return faces.map(group=>group.map(f=>({family:f.family,status:f.status})));
                    }''')
                    assert all(group and all(f['status']=='loaded' for f in group) for group in fonts), 'Required online font face did not load; fallback is not verification.'
                    session=context.new_cdp_session(page);session.send('DOM.enable');session.send('CSS.enable')
                    doc=session.send('DOM.getDocument')['root']['nodeId'];used={}
                    for selector,family in (('.home-library-search label','Inter'),('.bureau-discovery h2','EB Garamond')):
                        node=session.send('DOM.querySelector',{'nodeId':doc,'selector':selector})['nodeId']
                        used[selector]=session.send('CSS.getPlatformFontsForNode',{'nodeId':node})['fonts']
                        assert any(f['isCustomFont'] and family.lower() in f['familyName'].lower() and f['glyphCount']>0 for f in used[selector]), ('Expected actual custom-font glyphs',selector,used)
                    metrics=page.evaluate('''() => {
                        const box=s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,fontSize:getComputedStyle(e).fontSize,paddingLeft:parseFloat(getComputedStyle(e).paddingLeft),paddingRight:parseFloat(getComputedStyle(e).paddingRight),borderLeft:parseFloat(getComputedStyle(e).borderLeftWidth),borderRight:parseFloat(getComputedStyle(e).borderRightWidth)}};
                        return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,grid:box('.bureau-discovery'),form:box('.home-library-search'),input:box('#home-topic'),button:box('.home-library-search button')};
                    }''')
                    report['runs'].append({'variant':variant,'fonts':fonts,'actualGlyphFonts':used,'metrics':metrics,'fontNetwork':network})
                    page.locator('.bureau-discovery').screenshot(path=str(out/f'home-search-loaded-font-{variant}-320.png'))
                    if variant=='after':
                        assert metrics['documentWidth']<=320, metrics
                        for name in ('form','input','button'):
                            box=metrics[name]
                            assert box['left']>=0 and box['right']<=320 and box['width']>0, (name,metrics)
                        assert metrics['form']['scrollWidth']<=metrics['form']['clientWidth'], metrics
                        assert metrics['button']['right']<=metrics['form']['right'], metrics
                        grid=metrics['grid'];form=metrics['form']
                        assert form['width']<=grid['clientWidth']-grid['paddingLeft']-grid['paddingRight'], metrics
                        assert form['left']>=grid['left']+grid['borderLeft']+grid['paddingLeft'], metrics
                        assert form['right']<=grid['right']-grid['borderRight']-grid['paddingRight'], metrics
                        assert float(metrics['input']['fontSize'].removesuffix('px'))>=16, metrics
                except Exception:
                    report['fontNetworkOnFailure']=network
                    page.screenshot(path=str(out/f'home-search-loaded-font-failure-{variant}.png'),full_page=True)
                    raise
                finally:context.close()
            browser.close()
        report['baselineOverflowReproduced']=report['runs'][0]['metrics']['documentWidth']>320
        report['status']='passed with verified web-font glyphs'
    except Exception as error:
        report['status']='failed or unverified; no fallback acceptance';report['error']=str(error)
        raise
    finally:
        (out/'home-search-loaded-font-report.json').write_text(json.dumps(report,indent=2))
        server.shutdown();server.server_close()
    print('PASS: actual Inter/EB Garamond glyphs and strict320px search containment; baseline measurements saved.')
if __name__=='__main__':main()
