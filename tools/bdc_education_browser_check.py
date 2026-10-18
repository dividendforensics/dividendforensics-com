"""BDC curriculum search, self-checks, no-JS and responsive smoke checks; localhost only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import bdc_education


class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    executable=os.environ.get('CHROMIUM_PATH')
    if not executable and Path('C:/Program Files/Google/Chrome/Application/chrome.exe').exists():
        executable='C:/Program Files/Google/Chrome/Application/chrome.exe'
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
        context=browser.new_context()
        context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'/learn-bdc.html')
        assert page.locator('[data-lesson]:visible').count()==16
        page.locator('#lesson-level').select_option('Expert')
        assert page.locator('[data-lesson]:visible').count()==4
        page.locator('#lesson-search').fill('PIK')
        assert 0<page.locator('[data-lesson]:visible').count()<=4
        page.locator('#lesson-reset').click()
        assert page.locator('[data-lesson]:visible').count()==16
        for level in bdc_education.LEVELS:
            page.goto(base+'/course-bdc-'+level['key']+'.html')
            assert page.locator('.course-lessons>li').count()==4
            for field in page.locator('fieldset').all():
                answer=int(field.get_attribute('data-answer'))
                field.locator('input').nth((answer+1)%3).check()
            page.locator('[data-quiz] button[type=submit]').click()
            assert '0 of 4' in page.locator('.quiz-score').inner_text()
            for field in page.locator('fieldset').all():
                field.locator('input').nth(int(field.get_attribute('data-answer'))).check()
            page.locator('[data-quiz] button[type=submit]').click()
            assert '4 of 4' in page.locator('.quiz-score').inner_text()
        renders=0
        for name in [path.name for path in bdc_education.outputs(ROOT)]:
            for width in (320,390,1440):
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/'+name)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(name,width)
                renders+=1
        nojs=browser.new_context(java_script_enabled=False)
        nojs.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
        np=nojs.new_page();np.goto(base+'/learn-bdc.html')
        assert np.locator('[data-lesson]:visible').count()==16
        np.goto(base+'/learn-bdc-pik-income.html')
        assert np.locator('#worked-example').is_visible()
        assert np.locator('#source-notes a').count()>=2
        assert not errors,errors
        browser.close()
    server.shutdown()
    report={'passed':True,'new_page_renders':renders,'levels':4,'guides':16,'javascript_errors':errors,'external_requests_allowed':False,'real_form_submissions':0}
    (ROOT/'.qa').mkdir(exist_ok=True)
    (ROOT/'.qa/bdc-education-browser.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
