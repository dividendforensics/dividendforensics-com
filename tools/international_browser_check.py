"""Local-only multilingual rendering, decimal input and no-JS checks."""
from functools import partial
from pathlib import Path
from threading import Thread
import json
import os
import sys
from playwright.sync_api import sync_playwright
from resources_browser_check import Server, Handler
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from international import LOCALES,PAGES,path_for

def main():
    server=Server(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    out=ROOT/'.qa';out.mkdir(exist_ok=True)
    errors=[];renders=0
    try:
        with sync_playwright() as p:
            exe=os.environ.get('CHROMIUM_PATH')
            fallback=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
            if not exe and fallback.exists():exe=str(fallback)
            browser=p.chromium.launch(headless=True,**({'executable_path':exe} if exe else {}))
            ctx=browser.new_context()
            ctx.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            for width in (320,390,1440):
                page.set_viewport_size({'width':width,'height':950})
                for locale in LOCALES:
                    for key in PAGES:
                        path=path_for(locale,key);page.goto(base+'/'+path)
                        assert page.locator('html').get_attribute('lang')==locale
                        assert page.locator('h1').count()==1
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(path,width)
                        if key=='reit':
                            page.locator('details summary').click();assert page.locator('details[open]').count()==1
                            page.locator('.lesson-jump-menu a').first.focus();page.keyboard.press('Enter');assert page.url.endswith('#section-1')
                        if key in ('index','income') and width==390:
                            page.screenshot(path=str(out/f'international-{locale}-{key}.png'),full_page=True)
                        renders+=1
            page.set_viewport_size({'width':390,'height':950})
            for locale in LOCALES:
                page.goto(base+'/'+path_for(locale,'income'))
                assert not page.locator('[data-calculator-loading]').is_visible()
                form=page.locator('form');form.locator('[name=tax]').fill('15');form.locator('[type=submit]').click()
                expected=['500,00','425,00','35,42','141.176,47'] if locale=='de' else ['500.00','425.00','35.42','141,176.47']
                assert page.locator('[data-international-result] dd').all_text_contents()==expected
                page.screenshot(path=str(out/f'international-{locale}-calculated.png'),full_page=True)
                form.locator('[name=capital]').fill('1024,59999999999999999999' if locale=='de' else '1024.59999999999999999999')
                form.locator('[name=yield]').fill('7,5' if locale=='de' else '7.5');form.locator('[name=tax]').fill('0')
                form.locator('[type=submit]').click()
                assert page.locator('[data-international-result] dd').first.inner_text()==('76,84' if locale=='de' else '76.84')
                if locale=='de':
                    form.locator('[name=capital]').fill('10.000');form.locator('[type=submit]').click()
                    assert form.locator('[name=capital]').get_attribute('aria-invalid')=='true'
                    assert form.locator('[name=capital]').get_attribute('aria-describedby')=='calculator-input-error'
                    assert page.locator('[data-international-result] dd').count()==0
                    assert 'Dezimalkomma' in form.locator('[role=alert]').inner_text()
                    assert page.locator('[data-international-result]').inner_text()==form.locator('[role=alert]').inner_text()
                    assert form.locator('[name=capital]').evaluate('e=>e===document.activeElement')
                    style=form.locator('[role=alert]').evaluate('e=>({color:getComputedStyle(e).color,weight:getComputedStyle(e).fontWeight,background:getComputedStyle(e).backgroundColor})')
                    assert style=={'color':'rgb(121, 27, 39)','weight':'700','background':'rgb(255, 240, 241)'},style
                    assert form.locator('[name=capital]').evaluate('e=>getComputedStyle(e).borderTopWidth')=='2px'
                    page.screenshot(path=str(out/'international-de-error-390.png'),full_page=True)
                    page.set_viewport_size({'width':1024,'height':950})
                    assert abs(form.locator('[name=capital]').bounding_box()['y']-form.locator('[name=yield]').bounding_box()['y'])<1
                    page.screenshot(path=str(out/'international-de-alignment-1024.png'),full_page=True)
                    page.set_viewport_size({'width':390,'height':950})
                    form.locator('[name=capital]').fill('-1');form.locator('[type=submit]').click()
                    assert 'zwischen 0' in form.locator('[role=alert]').inner_text()
                    form.locator('[name=capital]').fill('10000')
                assert float(form.locator('[name=capital]').evaluate("e=>getComputedStyle(e).fontSize").replace('px',''))>=16
                form.locator('[name=tax]').fill('100');form.locator('[type=submit]').click()
                assert page.locator('[data-international-result] dd').last.inner_text() in ['Nicht definiert','定義できません','未定義']
                form.locator('[name=capital]').fill('1.000,00');form.locator('[type=submit]').click()
                assert form.locator('[role=alert]').is_visible()
                assert page.locator('[data-international-result] dd').count()==0
                assert page.locator('[data-international-result]').inner_text().strip()
                form.locator('[type=reset]').click();assert form.locator('[name=capital]').input_value()=='10000'
                form.locator('[type=submit]').click();assert page.locator('[data-international-result] dd').count()==4
            nojs=browser.new_context(java_script_enabled=False)
            nojs.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            static=nojs.new_page()
            for locale in LOCALES:
                for key in PAGES:
                    static.goto(base+'/'+path_for(locale,key))
                    assert static.locator('h1').is_visible()
                    if key in ('reit','bdc','coverage','comparison'):
                        assert static.locator('#example').is_visible()
                        static.locator('summary').click();assert static.locator('details[open]').count()==1
                    if key=='income':assert static.locator('noscript').is_visible()
            assert not errors,errors
            browser.close()
    finally:server.shutdown()
    result=dict(passed=True,pages=18,renders=renders,no_js_pages=18,locale_calculators=3,javascript_errors=errors)
    (out/'international-browser.json').write_text(json.dumps(result),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
