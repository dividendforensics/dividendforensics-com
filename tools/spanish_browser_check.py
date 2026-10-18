"""Local-only Spanish edition QA; never submit a real form or fetch external data."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from localized import PAIRS


class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def screenshot(page,path):
    # Full-page capture should start at the top even after a scrolled submit.
    page.evaluate('window.scrollTo(0,0)')
    page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>resolve()))')
    page.screenshot(path=str(path),full_page=True)


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    output=ROOT/'.qa';output.mkdir(exist_ok=True)
    errors=[];requests=[];blocked=[];renders=[];screenshots=[]
    try:
        with sync_playwright() as p:
            executable=os.environ.get('CHROMIUM_PATH')
            fallback=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
            if not executable and fallback.is_file():executable=str(fallback)
            browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
            def configure(context):
                def route(request):
                    if request.request.url.startswith(base+'/'):request.continue_()
                    else:blocked.append(request.request.url);request.abort()
                context.route('**/*',route)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            configure(context)
            page=context.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request:requests.append(request.url))
            for width in [320,390,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for path in PAIRS.values():
                    page.goto(base+'/'+path,wait_until='load')
                    assert page.locator('html').get_attribute('lang')=='es',path
                    assert page.locator('h1').count()==1,path
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(path,width)
                    renders.append({'path':path,'width':width})
                    if path=='es/index.html' and width in [390,1440]:
                        artifact=output/f'es-hub-{width}.png'
                        screenshot(page,artifact);screenshots.append(artifact.name)

            page.set_viewport_size({'width':390,'height':1000})
            page.goto(base+'/es/calculadora-dividendos.html')
            form=page.locator('[data-es-calculator=income]')
            for name,value in [('capital','10000'),('yield','5'),('tax','15'),('target','500')]:form.locator(f'[name="{name}"]').fill(value)
            form.locator('button[type=submit]').click()
            values=page.locator('[data-es-result] dd').all_text_contents()
            assert values[:3]==['500,00','425,00','35,42'],values
            assert values[3].replace('.','').replace('\u00a0','').replace('\u202f','').replace(' ','')=='141176,47',values
            artifact=output/'es-income-390.png';screenshot(page,artifact);screenshots.append(artifact.name)
            form.locator('[name=tax]').fill('100')
            assert page.locator('[data-es-result] dd').count()==0
            assert 'han cambiado' in page.locator('[data-es-result]').inner_text()
            form.locator('button[type=submit]').click()
            assert page.locator('[data-es-result] dd').last.inner_text()=='No definido'
            form.locator('[name=capital]').fill('')
            form.locator('button[type=submit]').click()
            assert not form.locator('[name=capital]').evaluate('(e)=>e.validity.valid')
            form.locator('button[type=reset]').click()
            page.wait_for_function('document.querySelector("[data-es-result]").textContent.includes("restablecido")')
            assert form.locator('[name=capital]').input_value()=='10000'
            assert form.locator('[name=tax]').input_value()=='0'
            assert page.locator('[data-es-result] dd').count()==0
            form.locator('button[type=submit]').click()
            assert page.locator('[data-es-result] dd').nth(1).inner_text()=='500,00'

            page.goto(base+'/es/calculadora-cobertura-affo.html')
            form=page.locator('[data-es-calculator=payout]')
            for name,value in [('affo','-4'),('dividend','3'),('decline','25')]:form.locator(f'[name={name}]').fill(value)
            form.locator('button[type=submit]').click()
            assert page.locator('[data-es-result] dd').all_text_contents()==['No definido','No definido','No definido','-8,00']
            assert not page.locator('.calculator-error').is_visible()
            artifact=output/'es-affo-390.png';screenshot(page,artifact);screenshots.append(artifact.name)
            form.locator('[name=affo]').fill('4')
            assert page.locator('[data-es-result] dd').count()==0
            form.locator('button[type=reset]').click()
            page.wait_for_function('document.querySelector("[data-es-result]").textContent.includes("restablecido")')
            form.locator('button[type=submit]').click()
            assert page.locator('[data-es-result] dd').all_text_contents()[:2]==['75,00 %','1,33 ×']
            assert not errors,errors
            context.close()

            offline=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})
            configure(offline)
            static=offline.new_page()
            for path in PAIRS.values():
                if path=='es/index.html':continue
                static.goto(base+'/'+path)
                if 'calculadora-' in path:
                    assert static.get_by_role('heading',name='Fórmula y base').is_visible(),path
                    assert static.get_by_role('heading',name='Ejemplo hipotético',exact=True).is_visible(),path
                    assert static.locator('noscript').is_visible(),path
                else:
                    assert static.locator('.lesson-body').inner_text().count(' ' )>200,path
                    answer=static.locator('.lesson-body details')
                    answer.locator('summary').click()
                    assert answer.locator('p').is_visible(),path
                assert static.evaluate('document.documentElement.scrollWidth<=innerWidth'),path
            offline.close();browser.close()
    finally:
        server.shutdown();server.server_close()
    assert not blocked,blocked
    assert all(url.startswith(base+'/') for url in requests)
    report={'passed':True,'renders':len(renders),'pages':7,'widths':[320,390,1440],
            'checks':['Spanish income:425,00 /35,42 /141.176,47','negative AFFO margin-8,00 and undefined ratios','input changes clear stale results','reset restores examples and requires recalculation','four guides and two formulas without JavaScript','USD scope and decimal point input / comma output'],
            'screenshots':screenshots,'javascript_errors':errors,'external_requests':len(blocked),'real_form_submissions':0}
    (output/'spanish-browser-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
