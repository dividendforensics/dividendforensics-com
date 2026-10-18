"""Check practical guides and local-only note export; never submit external forms."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import os
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PAGES=['reit-vs-bdc.html','dividend-dates.html','dividend-research-worksheet.html',
       'filing-labs.html','filing-lab-realty-income-2024.html','filing-lab-ares-capital-2024.html']

class Server(ThreadingHTTPServer):
    request_queue_size=128
    daemon_threads=True

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    output=ROOT/'.qa';output.mkdir(exist_ok=True)
    server=Server(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    errors=[];posts=[];renders=[]
    report={'passed':False,'renders':renders,'errors':errors,'post_requests':posts}
    try:
        with sync_playwright() as p:
            exe=os.environ.get('CHROMIUM_PATH')
            if not exe and Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe').is_file():exe=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
            browser=p.chromium.launch(headless=True,**({'executable_path':exe} if exe else {}))
            context=browser.new_context(accept_downloads=True)
            context.route('https://**/*',lambda route:route.abort())
            context.on('request',lambda req:posts.append(req.url) if req.method!='GET' else None)
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width in (320,390,1440):
                page.set_viewport_size({'width':width,'height':900})
                for name in PAGES:
                    page.goto(base+'/'+name,wait_until='networkidle')
                    assert page.locator('h1').count()==1
                    size=page.evaluate('({width:innerWidth,content:document.documentElement.scrollWidth})')
                    assert size['content']<=width+1,(name,size)
                    assert page.locator('main').inner_text().strip()
                    renders.append({'page':name,**size})
                    if width in (390,1440):
                        page.screenshot(path=str(output/f'resource-{name}-{width}.png'),full_page=True)
                        page.screenshot(path=str(output/f'resource-top-{name}-{width}.png'))
            page.goto(base+'/filing-lab-ares-capital-2024.html',wait_until='networkidle')
            input_values=page.locator('[data-lab-input]').evaluate_all('(els)=>Object.fromEntries(els.map(el=>[el.dataset.labInput,el.textContent]))')
            assert input_values=={'nii':'1403','pik':'463','tii':'2990','regular':'1219'}
            page.goto(base+'/calculator-bdc-nii-pik.html',wait_until='networkidle')
            form=page.locator('[data-bdc-tool]')
            for key,value in {**input_values,'supplemental':'0','special':'0','periodStart':'2024-01-01','periodEnd':'2024-12-31','asOf':'2026-10-18'}.items():
                form.locator(f'[name="{key}"]').fill(value)
            form.locator('[type=submit]').click()
            assert not form.locator('[data-bdc-error]').is_visible()
            result=page.locator('[data-bdc-result]').inner_text()
            assert '1.1509' in result and '0.7711' in result
            page.goto(base+'/dividend-research-worksheet.html',wait_until='networkidle')
            payload='Fictional issuer <script>alert(1)</script> & "quoted"'
            details='https://example.test/filing\nTable 4: USD millions; not found ≠ zero.'
            page.locator('#note-issuer').fill(payload)
            page.locator('#note-model').select_option(label='BDC')
            page.locator('#note-period').fill('Year ended 2026-09-30')
            page.locator('#note-asof').fill('2026-10-18')
            page.locator('#note-sources').fill(details)
            long_note='An unresolved disclosure remains an open question.\n'*80
            page.locator('#note-unknowns').fill(long_note)
            with page.expect_download() as download:
                page.locator('[data-download-note]').click()
            downloaded=download.value
            assert downloaded.suggested_filename=='dfb-dividend-research-note.txt'
            text=Path(downloaded.path()).read_text(encoding='utf-8-sig')
            assert payload in text and details in text and long_note.strip() in text
            assert 'BDC' in text and '[Not recorded]' in text
            page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
            page.emulate_media(media='print')
            assert page.locator('#research-worksheet').is_hidden()
            assert page.locator('#worksheet-print').is_visible()
            assert long_note.strip() in page.locator('#worksheet-print').inner_text()
            assert page.locator('#worksheet-print script').count()==0
            page.pdf(path=str(output/'research-note-print.pdf'),format='A4',print_background=True)
            page.emulate_media(media='screen')
            assert page.evaluate('localStorage.length')==0 and page.evaluate('sessionStorage.length')==0
            assert not context.cookies()
            page.reload(wait_until='networkidle')
            assert page.locator('#note-issuer').input_value()==''
            # Confirm keyboard access to native fields, without executing print dialogs.
            page.locator('#note-issuer').focus();page.keyboard.press('Tab')
            assert page.locator('#note-model').evaluate('(el)=>el===document.activeElement')
            nojs=browser.new_context(java_script_enabled=False)
            nojs.route('https://**/*',lambda route:route.abort())
            plain=nojs.new_page();plain.goto(base+'/dividend-research-worksheet.html',wait_until='networkidle')
            assert plain.locator('fieldset').count()==3
            assert 'Where to find dividend-analysis inputs' in plain.locator('main').inner_text()
            assert plain.locator('.worksheet-actions').is_hidden()
            plain.locator('#note-issuer').fill('No-JS private draft')
            plain.locator('#note-issuer').press('Enter')
            assert plain.url==base+'/dividend-research-worksheet.html'
            assert plain.locator('#note-issuer').input_value()=='No-JS private draft'
            assert plain.locator('form#research-worksheet').count()==0
            for name in PAGES[3:]:
                plain.goto(base+'/'+name,wait_until='networkidle')
                assert plain.locator('main').inner_text().strip()
                assert plain.locator('h1').count()==1
                if name.startswith('filing-lab-'):
                    assert plain.locator('a[href="/content/filing-labs.json"]').count()==1
                    assert plain.locator('main table').count()>=3
                    answer=plain.locator('details.workshop-answer').first
                    assert answer.count()==1
                    summary=answer.locator('summary')
                    summary.focus();plain.keyboard.press('Enter')
                    assert answer.evaluate('(el)=>el.open')
                    plain.keyboard.press('Enter')
                    assert not answer.evaluate('(el)=>el.open')
                    assert '2024' in plain.locator('main').inner_text()
            nojs.close();context.close();browser.close()
            assert not errors and not posts
            report.update(passed=True,checks=[f'{len(renders)} responsive renders','actual UTF-8 text download','literal HTML-like input stays text','long-note print expansion and PDF','blank values stay missing','no storage/cookies or non-GET requests','reload clears entries','keyboard field navigation','no-JS worksheet','3 filing pages without JS; source ledger links and keyboard answer keys','copy-ready lab values reproduce BDC worksheet coverage'])
    finally:
        server.shutdown();server.server_close()
        (output/'resources-browser-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
