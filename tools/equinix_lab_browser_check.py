"""Read-only mobile, keyboard, no-JS and directory checks for the Equinix lesson."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import os
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SLUG='filing-lab-equinix-2025.html'

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    output=ROOT/'.qa';output.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    errors=[];writes=[];renders=[]
    try:
        with sync_playwright() as p:
            executable=os.environ.get('CHROMIUM_PATH')
            browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
            context=browser.new_context()
            context.route('https://**/*',lambda route:route.abort())
            context.on('request',lambda req:writes.append(req.url) if req.method!='GET' else None)
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width in (320,390,768,1440):
                page.set_viewport_size({'width':width,'height':900})
                for name in ('index.html',SLUG,'filing-labs.html'):
                    page.goto(base+'/'+name,wait_until='networkidle')
                    assert page.locator('h1').count()==1
                    content=page.evaluate('document.documentElement.scrollWidth')
                    assert content<=width+1,(name,width,content)
                    renders.append({'page':name,'width':width,'content':content})
                    if name in ('index.html',SLUG) and width in (390,1440):
                        page.screenshot(path=str(output/f'equinix-{name}-{width}.png'),full_page=True)
            page.goto(base+'/'+SLUG,wait_until='networkidle')
            summary=page.locator('details.workshop-answer summary').first
            summary.focus();page.keyboard.press('Enter')
            assert summary.locator('..').get_attribute('open') is not None
            assert '1,455' in summary.locator('..').inner_text()
            page.keyboard.press('Enter')
            assert summary.locator('..').get_attribute('open') is None
            page.locator('.article-toc a[href="#reconciliation"]').click()
            assert page.url.endswith('#reconciliation')
            page.go_back();assert not page.url.endswith('#reconciliation')
            page.goto(base+'/learning-search.html?q=Equinix',wait_until='networkidle')
            results=page.locator('[data-learning-result]:visible')
            assert results.count()==1
            results.locator('a').click();assert page.url.endswith('/'+SLUG)
            nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':900})
            nojs.route('https://**/*',lambda route:route.abort())
            plain=nojs.new_page();plain.goto(base+'/'+SLUG,wait_until='networkidle')
            assert plain.locator('article table').count()==2
            assert plain.locator('article table').nth(1).locator('tbody tr').count()==19
            plain.locator('details.workshop-answer summary').first.click()
            assert '1,455' in plain.locator('details[open]').inner_text()
            assert not errors and not writes,(errors,writes)
            browser.close()
    finally:server.shutdown();server.server_close()
    report={'passed':True,'renders':renders,'console_errors':errors,'write_requests':writes,
            'checks':['responsive layout','native keyboard answer toggle','anchor and back','search discovery','no-JavaScript reading']}
    (output/'equinix-lab-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
