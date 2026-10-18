"""Exercise local calculator failure modes; never submit production/contact forms."""
from functools import partial
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import json, os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from resources_browser_check import Server, Handler
ROOT=Path(__file__).resolve().parents[1]

def main():
    pages=[]
    for path in ROOT.rglob('*.html'):
        if any(part.startswith('.') for part in path.relative_to(ROOT).parts):continue
        soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
        form=soup.select_one('form.calculator-form')
        if not form:continue
        assert form.select_one('fieldset[data-calculator-controls][disabled]'),path
        pages.append((path.relative_to(ROOT).as_posix(),[urlsplit(x['src']).path for x in soup.select('script[src]') if 'calculators.js' in x['src']]))
    assert len(pages)==21,len(pages)
    server=Server(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';cases=[]
    try:
        with sync_playwright() as p:
            exe=os.environ.get('CHROMIUM_PATH')
            fallback=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
            if not exe and fallback.exists():exe=str(fallback)
            browser=p.chromium.launch(headless=True,**({'executable_path':exe} if exe else {}))
            for path,scripts in pages:
                for blocked in [None,'/vendor/decimal.js/decimal.js',*scripts]:
                    context=browser.new_context(java_script_enabled=blocked is not None)
                    context.route('**/*',lambda r:r.abort() if not r.request.url.startswith(base) or (blocked and urlsplit(r.request.url).path==blocked) else r.continue_())
                    page=context.new_page();requests=[];errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.on('request',lambda r:requests.append((r.method,r.url)))
                    page.goto(base+'/'+path, wait_until='networkidle')
                    form=page.locator('form.calculator-form')
                    assert form.locator('input').first.is_disabled(),(path,blocked)
                    assert form.locator('[data-calculator-loading]').is_visible(),(path,blocked)
                    assert form.locator('input,select,textarea,button').evaluate_all("controls=>controls.every(c=>c.matches(':disabled'))"),(path,blocked)
                    assert not errors,(path,blocked,errors)
                    button=form.locator('[type=submit]');assert button.is_disabled(),(path,blocked)
                    requests.clear();before=page.url
                    # Real pointer and keyboard actions: disabled controls must not activate.
                    button.scroll_into_view_if_needed()
                    box=button.bounding_box();page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
                    form.locator('input').first.scroll_into_view_if_needed()
                    box=form.locator('input').first.bounding_box();page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
                    page.keyboard.type('928371');page.keyboard.press('Enter');page.wait_for_timeout(80)
                    assert page.url==before,(path,blocked,page.url)
                    assert not requests,(path,blocked,requests)
                    cases.append(dict(path=path,blocked=blocked or 'javascript-disabled',requests_after_actions=0))
                    context.close()
            browser.close()
    finally:server.shutdown()
    report=dict(passed=True,calculators=len(pages),cases=cases)
    (ROOT/'.qa/calculator-safety.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,calculators=len(pages),failure_cases=len(cases),requests_after_actions=0)))

if __name__=='__main__':main()
