"""Education behavior QA: real local HTTP, no external forms or account actions."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
from threading import Thread
import json,os,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from education import TOOLS
from curriculum import LEVELS

def main():
    out=ROOT/'.qa';out.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    requests=[];errors=[]
    with sync_playwright() as p:
        options={'headless':True}
        if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
        browser=p.chromium.launch(**options)
        context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        context.route('https://fonts.googleapis.com/**',lambda route:route.abort())
        context.route('https://fonts.gstatic.com/**',lambda route:route.abort())
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.goto(base+'/learn.html');page.locator('#lesson-search').fill('AFFO')
        assert 0<page.locator('[data-lesson]:visible').count()<36
        page.locator('#lesson-category').select_option('Start here')
        page.locator('#lesson-search').fill('zzzz-no-result')
        assert page.locator('#lesson-empty').is_visible()
        page.locator('#lesson-reset').click();assert page.locator('[data-lesson]:visible').count()==36
        page.locator('#lesson-level').select_option('Expert')
        assert page.locator('[data-lesson]:visible').count()==4
        page.locator('#lesson-reset').click()
        for level in LEVELS:
            page.goto(base+'/course-'+level['key']+'.html')
            for i,question in enumerate(level['quiz']):
                page.locator(f'input[name="question-{i}"][value="{question[2]}"]').check()
            page.get_by_role('button',name='Check my answers').click()
            assert '3 of 3 correct' in page.locator('.quiz-score').inner_text()
            assert page.locator('.quiz-feedback:visible').count()==3
            wrong=(level['quiz'][0][2]+1)%3
            page.locator(f'input[name="question-0"][value="{wrong}"]').check()
            assert page.locator('.quiz-feedback:visible').count()==0
            page.get_by_role('button',name='Check my answers').click()
            assert '2 of 3 correct' in page.locator('.quiz-score').inner_text()
        page.goto(base+'/glossary.html');page.locator('#glossary-search').fill('triple-net')
        assert page.locator('[data-term]:visible').count()==1
        for tool in TOOLS:
            page.goto(base+'/'+tool['slug']+'.html')
            page.wait_for_selector('.result-metrics',timeout=10000)
            assert page.locator('.result-metrics dd').count()>=3, (tool['slug'],page.locator('[data-result]').inner_text(),page.locator('.calculator-error').inner_text(),errors)
            assert not page.locator('.calculator-error').is_visible()
            with page.expect_download() as download:
                page.get_by_role('button',name='Download this scenario (CSV)').click()
            artifact=download.value
            assert artifact.suggested_filename.endswith('.csv')
            assert Path(artifact.path()).read_text(encoding='utf-8-sig').startswith('"Educational scenario')
            first=page.locator('.calculator-fields input').first
            original=first.input_value();first.fill('')
            assert 'Inputs changed' in page.locator('[data-result]').inner_text()
            page.get_by_role('button',name='Calculate',exact=False).first.click()
            assert not first.evaluate('(e)=>e.validity.valid')
            page.get_by_role('button',name='Reset example').click()
            page.wait_for_selector('.result-metrics')
            assert first.input_value()==original
        page.goto(base+'/calculator-dividend-income.html')
        page.locator('#input-tax').fill('100');page.get_by_role('button',name='Calculate',exact=False).first.click()
        assert 'Not defined' in page.locator('[data-result]').inner_text()
        page.goto(base+'/calculator-payout-ratio.html');page.locator('#input-decline').fill('100')
        page.get_by_role('button',name='Calculate',exact=False).first.click()
        assert 'Not defined' in page.locator('[data-result]').inner_text()
        assert '-3.00' in page.locator('[data-result]').inner_text()
        for affo in ('0','-1'):
            page.locator('#input-affo').fill(affo)
            page.get_by_role('button',name='Calculate',exact=False).first.click()
            assert page.locator('.result-metrics dd').all_inner_texts()[:3]==['Not defined']*3
            assert not page.locator('.calculator-error').is_visible()
            assert 'not meaningful' in page.locator('[data-result]').inner_text()
        with page.expect_download() as download:
            page.get_by_role('button',name='Download this scenario (CSV)').click()
        csv=Path(download.value.path()).read_text(encoding='utf-8-sig')
        assert '"Current payout","Not defined"' in csv
        page.goto(base+'/calculator-total-return.html');page.locator('#input-buyFees').fill('2')
        page.get_by_role('button',name='Calculate',exact=False).first.click()
        assert '-5.88%' in page.locator('[data-result]').inner_text()
        for width in (390,1440):
            page.set_viewport_size({'width':width,'height':1000})
            for name in ('index','learn','learn-affo','course-beginner','course-intermediate','course-advanced','course-expert','learn-expert-jv-nav','tools','calculator-payout-ratio','calculator-reinvestment','glossary'):
                page.goto(base+'/'+name+'.html')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(name,width)
                page.locator('img').evaluate_all('(images)=>images.forEach(i=>i.loading="eager")')
                page.evaluate('Promise.all([...document.images].map(i=>i.decode().catch(()=>null)))')
                assert page.locator('img').evaluate_all('(images)=>images.every(i=>i.naturalWidth>0)')
                page.screenshot(path=str(out/f'{name}-{width}.png'),full_page=True)
        offline=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        np=offline.new_page();np.goto(base+'/learn.html')
        assert np.locator('[data-lesson]:visible').count()==36
        assert not np.locator('[data-library-controls]').is_visible()
        np.goto(base+'/calculator-nav.html');assert np.locator('#formula').is_visible()
        offline.close();context.close();browser.close()
    server.shutdown()
    assert not errors,errors
    assert not any('adsbygoogle' in url or 'google-analytics' in url for url in requests)
    (out/'education-browser-report.json').write_text(json.dumps({'status':'passed','calculators':len(TOOLS),'checks':['library search/filter/reset/empty','glossary filter','seven calculators default results','CSV downloads','invalid input and reset','zero net yield','zero stressed AFFO','purchase fees denominator','mobile and desktop screenshots','no-JavaScript reading','no ad or analytics requests'],'errors':errors},indent=2),encoding='utf-8')
    print('PASS: four course quizzes, level filters, seven calculators, CSV, edge cases, images, no-JS and responsive screenshots.')

if __name__=='__main__':main()
