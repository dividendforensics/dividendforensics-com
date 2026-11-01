"""Education behavior QA: real local HTTP, no external forms or account actions."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
from threading import Thread
import json,os,sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from education import TOOLS
from curriculum import LEVELS

def wait_for_library_query(page, query, errors, responses, failed_requests, output):
    """Require both the correct document and its enhancement; expose load failures."""
    try:
        page.wait_for_load_state('domcontentloaded')
        page.wait_for_function('''query => {
            const search=document.querySelector('#lesson-search');
            const controls=document.querySelector('[data-library-controls]');
            return !!search && !!controls && !controls.hidden && search.value===query;
        }''',arg=query,timeout=30000)
    except PlaywrightTimeoutError as error:
        state=page.evaluate('''() => ({url:location.href,readyState:document.readyState,
            value:document.querySelector('#lesson-search')?.value,
            controlsHidden:document.querySelector('[data-library-controls]')?.hidden,
            scripts:Array.from(document.scripts).map(s=>({src:s.src,defer:s.defer}))})''')
        diagnostic={'state':state,'javascript_errors':errors,'responses':responses,
                    'failed_requests':failed_requests,'expected_query':query}
        (output/'education-search-failure.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
        raise AssertionError('Learning-room query did not initialize: '+json.dumps(diagnostic)) from error


def check_learning_search(page, base):
    page.goto(base+'/index.html')
    page.locator('#home-topic').fill('ticker')
    page.get_by_role('button',name='Search guides').click()
    page.wait_for_url('**/learning-search.html?q=ticker#search-results')
    page.wait_for_function("document.activeElement === document.getElementById('learning-query')")
    expected = {'ticker':'market-labels', 'market cap':'stock-classification', 'S&P500':'market-labels',
                'buyback':'dividends-buybacks-guide', 'free cash flow':'dividends-buybacks-guide',
                'EPS':'market-labels', 'PIK':'learn-bdc-pik-income'}
    for query, slug in expected.items():
        page.locator('#learning-query').fill(query)
        assert page.locator('[data-learning-result]:visible a[href="/'+slug+'.html"]').count() == 1, query
    page.locator('#learning-topic').select_option('REIT')
    assert page.locator('#learning-empty').is_visible()
    page.locator('#learning-query').focus()
    page.keyboard.press('Tab')
    assert page.locator('#learning-topic').evaluate('(e)=>e===document.activeElement')
    page.keyboard.press('Tab')
    assert page.locator('#learning-reset').evaluate('(e)=>e===document.activeElement')
    page.keyboard.press('Enter')
    total=page.locator('[data-learning-result]:visible').count()
    assert total > 52
    assert page.locator('#learning-query').evaluate('(e)=>e===document.activeElement')
    for query in ('zzzz-unmatched-query', '없는검색어', '<script>alert(1)</script>'):
        page.locator('#learning-query').fill(query)
        assert page.locator('#learning-empty').is_visible()
        assert page.locator('#learning-empty a').count() >= 4
    page.goto(base+'/learning-search.html?q=PIK&room=BDC&source=qa#search-results')
    page.wait_for_function("document.querySelector('#learning-query').value==='PIK'")
    assert page.locator('#learning-topic').input_value()=='BDC'
    initial_history=page.evaluate('history.length')
    page.locator('#learning-query').fill('NII')
    page.reload()
    page.wait_for_function("document.querySelector('#learning-query').value==='NII'")
    assert page.locator('#learning-topic').input_value()=='BDC'
    assert page.evaluate("new URL(location.href).searchParams.get('source')")=='qa'
    assert page.evaluate('location.hash')=='#search-results'
    assert page.evaluate('history.length')==initial_history
    page.locator('[data-learning-result]:visible a').first.click()
    page.go_back()
    page.wait_for_function("document.querySelector('#learning-query').value==='NII'")
    assert page.locator('[data-learning-result]:visible').count()>0
    page.locator('#learning-reset').click()
    assert page.locator('[data-learning-result]:visible').count()==total
    assert page.evaluate("new URL(location.href).searchParams.has('q')") is False
    assert page.evaluate("new URL(location.href).searchParams.has('room')") is False
    for width in (320,390,768,1188,1440):
        page.set_viewport_size({'width':width,'height':1000})
        page.evaluate('document.fonts.ready')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), width
    page.set_viewport_size({'width':1440,'height':1000})


def main(library_only=False):
    out=ROOT/'.qa';out.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    requests=[];errors=[];responses=[];failed_requests=[]
    with sync_playwright() as p:
        options={'headless':True}
        if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
        browser=p.chromium.launch(**options)
        context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        context.route('https://fonts.googleapis.com/**',lambda route:route.abort())
        context.route('https://fonts.gstatic.com/**',lambda route:route.abort())
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.on('response',lambda r:responses.append({'url':r.url,'status':r.status}))
        page.on('requestfailed',lambda r:failed_requests.append({'url':r.url,'failure':r.failure}))
        check_learning_search(page, base)
        # Legacy links retain the original REIT-only q/filter contract.
        page.goto(base+'/learn.html?q=AFFO#library')
        wait_for_library_query(page,'AFFO',errors,responses,failed_requests,out)
        assert 0<page.locator('[data-lesson]:visible').count()<36
        page.wait_for_function("document.activeElement === document.getElementById('lesson-search')")
        assert page.locator('#library').evaluate('(el) => { const r=el.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; }')
        page.locator('#lesson-category').select_option('Start here')
        page.locator('#lesson-search').fill('zzzz-no-result')
        assert page.locator('#lesson-empty').is_visible()
        page.locator('#lesson-reset').click();assert page.locator('[data-lesson]:visible').count()==36
        page.locator('#lesson-level').select_option('Expert')
        assert page.locator('[data-lesson]:visible').count()==4
        page.locator('#lesson-reset').click()
        # Query edits and clearing must survive reload without accumulating
        # history entries or discarding unrelated parameters and the anchor.
        page.goto(base+'/learn.html?q=AFFO&source=qa#library')
        wait_for_library_query(page,'AFFO',errors,responses,failed_requests,out)
        history_length = page.evaluate('history.length')
        page.locator('#lesson-search').fill('zzzxq0')
        assert page.evaluate("new URL(location.href).searchParams.get('q')") == 'zzzxq0'
        assert page.evaluate('history.length') == history_length
        page.reload()
        wait_for_library_query(page,'zzzxq0',errors,responses,failed_requests,out)
        assert page.locator('#lesson-empty').is_visible()
        page.locator('#lesson-reset').click()
        assert page.evaluate("new URL(location.href).searchParams.has('q')") is False
        assert page.evaluate("new URL(location.href).searchParams.get('source')") == 'qa'
        assert page.evaluate('location.hash') == '#library'
        page.reload()
        wait_for_library_query(page,'',errors,responses,failed_requests,out)
        assert page.locator('[data-lesson]:visible').count() == 36
        if library_only:
            assert not errors,errors
            context.close();browser.close();server.shutdown();server.server_close()
            (out/'education-library-report.json').write_text(json.dumps({'status':'passed','scope':'unified directory and legacy REIT library filters only','checks':['homepage ticker query reaches unified directory; legacy AFFO query initializes','AFFO results are a nonempty subset','category/empty/reset','four expert guides','36 guides restored','edited query and cleared query survive reload','replaceState preserves unrelated parameters/hash without history spam'],'errors':errors},indent=2),encoding='utf-8')
            print('PASS: unified learning search and legacy REIT filters; broader education checks were not run.')
            return
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
        for filename, anchor, legacy, hidden_anchor in (('glossary.html','ffo','term-8','affo'), ('glossary-bdc.html','nii','term-0','pik')):
            for fragment in (anchor, legacy):
                page.goto(base+'/'+filename+'#'+fragment)
                page.wait_for_function("id => document.activeElement?.id===id",arg=anchor)
            page.locator('#glossary-search').fill('zzzz-no-result')
            assert page.locator('[data-term]:visible').count()==0
            page.evaluate("id => location.hash=id",hidden_anchor)
            page.wait_for_function("id => document.activeElement?.id===id",arg=hidden_anchor)
            assert page.locator('#'+hidden_anchor).is_visible()
            assert page.locator('#glossary-search').input_value()==''
            page.evaluate("location.hash='%E0%A4%A'")
            page.locator('#glossary-search').fill('zzzz-no-result')
            assert page.locator('#glossary-empty').is_visible()
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
        page.locator('#input-affo').fill('-4');page.locator('#input-dividend').fill('3');page.locator('#input-decline').fill('25')
        page.get_by_role('button',name='Calculate',exact=False).first.click()
        assert page.locator('.result-metrics dd').all_inner_texts()[-1]=='-8.00'
        assert '-5.00' in page.locator('.table-scroll').inner_text()
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
        np.goto(base+'/learning-search.html?q=ticker#search-results')
        assert np.locator('[data-learning-result]:visible').count()>52
        assert not np.locator('[data-learning-controls]').is_visible()
        assert np.locator('a[href="/market-labels.html"]').count()>0
        np.goto(base+'/calculator-nav.html');assert np.locator('#formula').is_visible()
        offline.close();context.close();browser.close()
    server.shutdown()
    assert not errors,errors
    assert not any('adsbygoogle' in url or 'google-analytics' in url for url in requests)
    (out/'education-browser-report.json').write_text(json.dumps({'status':'passed','calculators':len(TOOLS),'checks':['unified search required topics, room filter, empty/reset, keyboard, URL reload/Back','stable and legacy glossary anchors reveal hidden definitions','library search/filter/reset/empty','glossary filter','seven calculators default results','CSV downloads','invalid input and reset','zero net yield','zero stressed AFFO','purchase fees denominator','mobile and desktop screenshots','no-JavaScript reading','no ad or analytics requests'],'errors':errors},indent=2),encoding='utf-8')
    print('PASS: four course quizzes, level filters, seven calculators, CSV, edge cases, images, no-JS and responsive screenshots.')

if __name__=='__main__':main(library_only='--library-only' in sys.argv)
