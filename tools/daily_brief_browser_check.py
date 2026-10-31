"""Filing-brief release QA: local Chromium only, no source-site requests or submissions."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import os
import sys
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from daily_briefs import load, calculations, publication_label

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


def main():
    records=load(ROOT)
    assert records, 'Release QA requires at least one real independently approved brief.'
    out=Path('/tmp/dfb-preview/daily-briefs');out.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    errors=[];external=[];failed=[];checks=[]
    try:
        with sync_playwright() as p:
            opts={'headless':True}
            if os.environ.get('CHROMIUM_PATH'):opts['executable_path']=os.environ['CHROMIUM_PATH']
            browser=p.chromium.launch(**opts)
            context=browser.new_context()
            def local_only(route):
                url=route.request.url
                if url.startswith(base+'/'):route.continue_()
                else:external.append({'url':url,'type':route.request.resource_type});route.abort()
            context.route('**/*',local_only)
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda response:failed.append([response.url,response.status]) if response.url.startswith(base) and response.status>=400 else None)
            page.set_default_timeout(15000)
            for width in (320,390,768,1440):
                page.set_viewport_size({'width':width,'height':1000})
                for landing in ('index.html','research.html'):
                    page.goto(base+'/'+landing,wait_until='networkidle')
                    section=page.locator('section[aria-labelledby="brief-title"]')
                    assert section.count()==1 and section.is_visible()
                    assert section.get_by_role('link',name=records[0]['title'],exact=True).count()==1
                    assert 'Unpublished' not in section.inner_text()
                    category=section.locator('.lesson-card .kicker').first
                    category_state=category.evaluate('''el => ({source:el.textContent.trim(),
                        rendered:el.innerText.trim(),transform:getComputedStyle(el).textTransform})''')
                    category_state.update(url=page.url,width=width,expected=records[0]['category'])
                    # Shared dfb.css intentionally renders .kicker in uppercase.
                    # Verify the exact data AND visible text, accounting only for that CSS transform.
                    expected_category=records[0]['category']
                    expected_visible=(expected_category.upper() if category_state['transform']=='uppercase'
                                      else expected_category)
                    assert category.is_visible(),category_state
                    assert category_state['source']==expected_category,category_state
                    assert category_state['rendered']==expected_visible,category_state
                    if landing=='index.html':
                        assert 'Latest external publication:' in page.locator('main').inner_text()
                    section.get_by_role('link',name='All filing briefs',exact=False).click()
                    assert urlsplit(page.url).path=='/daily-briefs.html'
                    assert page.locator('h1').inner_text()=='Filing briefs'
                    assert page.locator('main a[href^="/brief-"]').count()==len(records)
                for b in records:
                    path='/brief-'+b['slug']+'.html'
                    page.goto(base+path+'?qa=archive-link',wait_until='networkidle')
                    assert page.locator('h1').inner_text()==b['title']
                    body=page.locator('main').inner_text()
                    assert publication_label(b) in body
                    assert b['event_date'] in body and b['reporting_period']['end'] in body
                    assert 'Recalculation ledger' in body and 'Structural research, not investment advice.' in body
                    assert not any(x in body for x in ['Unpublished review preview','{{daily_briefs}}'])
                    for fact in b['facts'].values():
                        assert fact['value'] in body and fact['unit'] in body
                        assert fact['period']['start'] in body and fact['period']['end'] in body
                    for value in calculations(b).values():assert value in body
                    for source in b['sources'].values():
                        assert page.locator('main a').evaluate_all('(els,url)=>els.some(a=>a.href===url)',source['url'])
                    assert page.locator('main table tbody tr').count()==len(b['facts'])
                    # Wide ledgers may scroll inside their wrapper, never the entire page.
                    dimensions=page.evaluate('''() => ({viewport:innerWidth, document:document.documentElement.scrollWidth, body:document.body.scrollWidth})''')
                    assert dimensions['document']<=width+2 and dimensions['body']<=width+2,dimensions
                    page.screenshot(path=str(out/f'{b["slug"]}-{width}.png'),full_page=True)
                    page.get_by_role('link',name='All filing briefs',exact=True).click()
                    assert urlsplit(page.url).path=='/daily-briefs.html'
                    page.get_by_role('link',name=b['title'],exact=True).click()
                    assert urlsplit(page.url).path==path
                    page.keyboard.press('Tab')
                    assert page.evaluate('document.activeElement.tagName') in ('A','BUTTON','INPUT')
                    checks.append({'width':width,'slug':b['slug'],'overflow':False,'source_links':len(b['sources']),'facts':len(b['facts'])})
            # Existing shared Google Fonts may be blocked; the feature must not request third-party data/APIs.
            unexpected=[x for x in external if urlsplit(x['url']).hostname not in ('fonts.googleapis.com','fonts.gstatic.com')]
            assert not unexpected,unexpected
            assert not errors,errors
            assert not failed,failed
            context.close();browser.close()
        (out/'result.json').write_text(json.dumps({'passed':True,'checks':checks,'javascript_errors':errors,'local_http_failures':failed,'blocked_shared_font_requests':external,'external_source_requests':0,'real_submissions':0},indent=2))
        print(f'PASS: filing briefs at 320/390/768/1440; {len(checks)} detail checks; no offsite API requests.')
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
