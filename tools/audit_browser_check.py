"""Regression checks for the October independent review; localhost only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import argparse
import json
import os
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

CONTRAST = r'''selector => {
 const placeholder=selector.endsWith('::placeholder');
 const e=document.querySelector(placeholder?selector.slice(0,-13):selector);
 const rgb=s=>{const n=s.match(/[\d.]+/g).map(Number);return [n[0],n[1],n[2],n.length>3?n[3]:1]};
 const over=(f,b)=>f.slice(0,3).map((v,i)=>v*f[3]+b[i]*(1-f[3]));
 const chain=[];for(let p=e;p;p=p.parentElement)chain.unshift(p);
 let bg=[255,255,255];for(const p of chain)bg=over(rgb(getComputedStyle(p).backgroundColor),bg);
 const style=getComputedStyle(e,placeholder?'::placeholder':null),fg=over(rgb(style.color),bg);
 const lum=c=>c.map(v=>v/255).map(v=>v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[0.2126,0.7152,0.0722][i],0);
 const a=lum(fg),b=lum(bg);return {selector,ratio:(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05),foreground:style.color,background:bg};
}'''


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bdc-only', action='store_true', help='Only check five BDC date validation UIs')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    output = ROOT / '.qa'
    output.mkdir(exist_ok=True)
    checks, errors, contrast = [], [], []
    try:
        with sync_playwright() as p:
            executable = os.environ.get('CHROMIUM_PATH')
            fallback = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
            if not executable and fallback.is_file():
                executable = str(fallback)
            browser = p.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
            context = None
            try:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
                page = context.new_page()
                page.set_default_timeout(15000)
                page.set_default_navigation_timeout(20000)
                page.on('pageerror', lambda error: errors.append(str(error)))
                if not args.bdc_only:
                    print('Home learning CTA contrast check', flush=True)
                    page.goto(base + '/', wait_until='domcontentloaded')
                    for width in [320, 390, 1440]:
                        page.set_viewport_size({'width': width, 'height': 1000})
                        for selector in ['.education-home .btn-s[href="/learn-bdc.html"]', '.education-home .bureau-hero-copy .btn-p[href="/learn.html"]']:
                            button = page.locator(selector)
                            page.mouse.move(0, 0)
                            button.evaluate('(e)=>e.blur()')
                            page.wait_for_timeout(250)
                            measured = page.evaluate(CONTRAST, selector)
                            measured.update(state='default', viewport=width)
                            contrast.append(measured)
                            assert measured['ratio'] >= 4.5, measured
                            button.hover()
                            page.wait_for_timeout(250)
                            measured = page.evaluate(CONTRAST, selector)
                            measured.update(state='hover', viewport=width)
                            contrast.append(measured)
                            assert measured['ratio'] >= 4.5, measured
                            page.mouse.move(0, 0)
                            page.wait_for_timeout(250)
                            button.focus()
                            page.keyboard.press('Tab')
                            page.keyboard.press('Shift+Tab')
                            assert button.evaluate('(e)=>e===document.activeElement&&e.matches(":focus-visible")')
                            focus = button.evaluate('(e)=>({style:getComputedStyle(e).outlineStyle,width:parseFloat(getComputedStyle(e).outlineWidth),color:getComputedStyle(e).outlineColor,offset:parseFloat(getComputedStyle(e).outlineOffset)})')
                            assert focus['style'] != 'none' and focus['width'] >= 2 and focus['offset'] >= 2, focus
                            measured = page.evaluate(CONTRAST, selector)
                            measured.update(state='keyboard focus', viewport=width, outline=focus)
                            contrast.append(measured)
                            assert measured['ratio'] >= 4.5, measured
                        caption=page.evaluate(CONTRAST, '.paper-plate figcaption')
                        caption.update(viewport=width,state='report-cover caption')
                        contrast.append(caption)
                        assert caption['ratio'] >= 4.5, caption
                        labels=page.locator('.masthead-note,.directory-label,.directory-note,.home-page .section-heading .kicker').evaluate_all("els=>els.filter(e=>e.getClientRects().length).map(e=>({text:e.textContent.trim(),size:parseFloat(getComputedStyle(e).fontSize)}))")
                        assert all(label['size'] >= 12 for label in labels), labels
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                        page.locator('.bureau-hero-copy').screenshot(path=str(output / f'home-learning-cta-reviewed-{width}.png'))
                    checks.append('Home Study BDCs and Study REITs CTAs meet 4.5:1 in default/hover/keyboard focus at 320/390/1440px with visible outlines')
                for slug in ['nii-pik', 'pik-ratios', 'non-accrual', 'nav-discount', 'leverage']:
                    print('BDC date check: ' + slug, flush=True)
                    page.goto(base + '/calculator-bdc-' + slug + '.html', wait_until='domcontentloaded')
                    page.wait_for_function("!!window.DFBBdc && !!document.querySelector('[data-bdc-result] table')")
                    form = page.locator('[data-bdc-tool]')
                    form.locator('[name=asOf]').fill('2026-06-30')
                    assert form.evaluate('(e)=>e.checkValidity()'), {'slug':slug,'invalid':form.locator(':invalid').evaluate_all('(els)=>els.map(e=>({name:e.name,value:e.value,message:e.validationMessage}))')}
                    form.locator('button[type=submit]').click()
                    form.locator('[data-bdc-error]').wait_for(state='visible')
                    assert form.locator('[data-bdc-error]').is_visible(), slug
                    assert 'period end' in form.locator('[data-bdc-error]').inner_text().lower(), slug
                    form.locator('[name=asOf]').fill('2026-09-30')
                    form.locator('button[type=submit]').click()
                    form.locator('[data-bdc-error]').wait_for(state='hidden')
                    page.locator('[data-bdc-result] table').wait_for(state='visible')
                    assert not form.locator('[data-bdc-error]').is_visible(), slug
                    assert page.locator('[data-bdc-result] table').count() > 0, slug
                    assert form.locator('[data-bdc-status]').count() == form.locator('[data-bdc-input]').count()
                    assert form.locator('[data-bdc-status]').evaluate_all('els=>els.every(e=>e.getClientRects().length && !e.closest("details"))')
                    if slug != 'nav-discount':
                        amount=form.locator('[data-bdc-input]').first
                        original=amount.input_value()
                        amount.fill('not-a-number')
                        form.locator('button[type=submit]').click()
                        assert amount.get_attribute('aria-invalid') == 'true'
                        assert 'bdc-input-error' in amount.get_attribute('aria-describedby').split()
                        label=page.locator('label[for="'+amount.get_attribute('id')+'"]').inner_text()
                        assert form.locator('[data-bdc-error]').inner_text().startswith(label+':')
                        amount.fill(original)
                        assert amount.get_attribute('aria-invalid') is None
                        assert 'bdc-input-error' not in amount.get_attribute('aria-describedby').split()
                        form.locator('button[type=submit]').click()
                        assert not form.locator('[data-bdc-error]').is_visible()
                    if slug == 'nav-discount':
                        assert form.locator('[name=incomeBasis], [name=distributionBasis]').count() == 0
                        for price, expected in [('18','0.9'), ('22','1.1'), ('18','0.9')]:
                            form.locator('[name=price]').fill(price)
                            form.locator('button[type=submit]').click()
                            audit = json.loads(page.locator('[data-bdc-result] pre').text_content())
                            assert audit['context']['incomeBasis'] == 'not_applicable'
                            assert audit['context']['distributionBasis'] == 'not_applicable'
                            assert audit['inputs']['price']['value'] == price
                            assert page.evaluate("([price]) => DFBBdc.calculate('nav',{price,nav:'20'},{datasetMode:'scenario',currency:'USD',scale:'one',unit:'per-share',periodStart:'2026-07-01',periodEnd:'2026-09-30',asOf:'2026-09-30',scope:'common'}).rows[0].value", [price]) == expected
                            assert 'null NII' not in page.locator('[data-bdc-result]').inner_text()
                        form.locator('button[type=reset]').click()
                        page.wait_for_function("(() => {const record=document.querySelector('[data-bdc-result] pre');return record && JSON.parse(record.textContent).context.datasetMode === 'synthetic';})()")
                        reset_audit = json.loads(page.locator('[data-bdc-result] pre').text_content())
                        assert reset_audit['inputs']['price']['value'] == form.locator('[name=price]').input_value()
                        # A Playwright click is a trusted browser input, not dispatchEvent.
                        # Stub only the OS print boundary; do not claim dialog verification.
                        page.evaluate("window.__printCalls=0; window.__printClicks=[]; window.print=()=>{window.__printCalls++}; document.querySelector('[data-bdc-print]').addEventListener('click', e=>window.__printClicks.push(e.isTrusted))")
                        for expected_calls in (1,2,3):
                            form.locator('[data-bdc-print]').click()
                            assert page.evaluate('window.__printCalls') == expected_calls
                            assert page.evaluate('window.__printClicks.every(Boolean)')
                        checks.append('NAV print button: one trusted click makes one print call; three separate clicks make exactly three calls (OS dialog stubbed)')
                        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
                        assert page.locator('[data-bdc-result] details').evaluate('(e)=>e.open')
                        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
                        price_input=form.locator('[name=price]');nav_input=form.locator('[name=nav]')
                        def submit_nav():
                            form.locator('button[type=submit]').click()
                            assert not form.locator('[data-bdc-error]').is_visible()
                            return json.loads(page.locator('[data-bdc-result] pre').text_content())
                        def choose_availability(name,status):
                            field=form.locator('[name="'+name+'"]').locator('xpath=..')
                            field.locator('summary').click()
                            field.locator('[name="'+name+'Availability"]').select_option(status)
                            field.locator('summary').click()
                            assert field.locator('[data-bdc-status]').is_visible()
                        for status,label in [('not_applicable','Not applicable'),('not_disclosed','Not disclosed'),('not_found','Not found')]:
                            choose_availability('price',status)
                            assert label in form.locator('#price-status').inner_text()
                            assert price_input.input_value() == '18'
                            excluded=submit_nav()
                            assert excluded['inputs']['price']['rawValue'] == '18'
                            assert excluded['inputs']['price']['value'] is None
                            assert excluded['inputs']['price']['availability'] == status
                            assert excluded['inputs']['price']['reviewedBy'] is None
                            rendered=page.locator('[data-bdc-result]').inner_text()
                            assert 'market price per common share excluded' in rendered and label in rendered
                            assert 'must be positive for a ratio' not in rendered
                            choose_availability('price','scenario');submit_nav()
                            assert '0.9000×' in page.locator('[data-bdc-result] table').inner_text()
                        for bad_price in ('abc','1,234.5'):
                            price_input.fill(bad_price);form.locator('button[type=submit]').click()
                            assert price_input.input_value() == bad_price
                            assert price_input.get_attribute('aria-invalid') == 'true'
                            assert 'User-entered market price per common share:' in form.locator('[data-bdc-error]').inner_text()
                            assert 'price-status' in price_input.get_attribute('aria-describedby').split()
                            assert 'bdc-input-error' in price_input.get_attribute('aria-describedby').split()
                            price_input.fill('18');submit_nav()
                            assert price_input.get_attribute('aria-invalid') is None
                        for nav_value,difference in [('0','18.0000'),('-20','38.0000')]:
                            nav_input.fill(nav_value);submit_nav()
                            assert 'NAV per share must be positive for a ratio' in page.locator('[data-bdc-result]').inner_text()
                            assert difference in page.locator('[data-bdc-result] table').inner_text()
                            assert nav_input.get_attribute('aria-invalid') is None
                        nav_input.fill('20');submit_nav()
                        page.evaluate("const note=document.createElement('span');note.id='persistent-nav-help';note.textContent='Test helper';document.body.append(note);document.querySelector('[name=nav]').setAttribute('aria-describedby','nav-status persistent-nav-help')")
                        nav_input.fill('twenty');form.locator('button[type=submit]').click()
                        assert 'Disclosed common NAV per share:' in form.locator('[data-bdc-error]').inner_text()
                        assert nav_input.get_attribute('aria-invalid') == 'true'
                        assert set(nav_input.get_attribute('aria-describedby').split()) == {'nav-status','persistent-nav-help','bdc-input-error'}
                        assert 'Needs correction' in form.locator('#nav-status').inner_text()
                        assert nav_input.evaluate('e=>e===document.activeElement')
                        nav_input.fill('20')
                        assert nav_input.get_attribute('aria-invalid') is None
                        assert set(nav_input.get_attribute('aria-describedby').split()) == {'nav-status','persistent-nav-help'}
                        submit_nav()
                        for repeat in range(2):
                            nav_input.fill('bad');form.locator('button[type=submit]').click()
                            form.locator('button[type=reset]').click()
                            page.wait_for_function("(() => {const record=document.querySelector('[data-bdc-result] pre');return record && JSON.parse(record.textContent).context.datasetMode === 'synthetic';})()")
                            assert not form.locator('[data-bdc-error]').is_visible()
                            assert nav_input.get_attribute('aria-invalid') is None
                            assert set(nav_input.get_attribute('aria-describedby').split()) == {'nav-status','persistent-nav-help'}
                            form.locator('[data-bdc-clear]').click()
                            assert price_input.input_value() == '' and nav_input.input_value() == ''
                            assert 'No value entered' in form.locator('#price-status').inner_text()
                            cleared=json.loads(page.locator('[data-bdc-result] pre').text_content())
                            assert all(item['value'] is None for item in cleared['inputs'].values())
                            assert all(item['rawValue'] == '' for item in cleared['inputs'].values())
                            form.locator('[data-bdc-clear]').click()
                        form.locator('button[type=reset]').click()
                        page.wait_for_function("(() => {const record=document.querySelector('[data-bdc-result] pre');return record && JSON.parse(record.textContent).context.datasetMode === 'synthetic';})()")
                        assert '0.9000×' in page.locator('[data-bdc-result] table').inner_text()
                        assert page.locator('.bdc-nav-notes').count() == 2
                        for notes_width in (320,390,1188,1440):
                            page.set_viewport_size({'width':notes_width,'height':1000})
                            notes=page.evaluate("""async () => {
                                await document.fonts.ready;
                                await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                                return {viewport:innerWidth,content:document.documentElement.scrollWidth,
                                    paragraphs:[...document.querySelectorAll('.bdc-nav-notes>p')].map(e=>({width:e.getBoundingClientRect().width,maxWidth:parseFloat(getComputedStyle(e).maxWidth)})),
                                    headings:[...document.querySelectorAll('.bdc-nav-notes>h2')].map(e=>({gap:parseFloat(getComputedStyle(e).marginBottom),font:parseFloat(getComputedStyle(e).fontSize)}))};
                            }""")
                            assert notes['content'] <= notes_width+1, notes
                            assert all(item['maxWidth'] > 0 and item['width'] <= item['maxWidth']+1 for item in notes['paragraphs']), notes
                            assert all(item['gap'] >= .49*item['font'] for item in notes['headings']), notes

                        checks.append('NAV availability: exclusions name price/status, raw inputs survive, scenarios restore, nonpositive NAV stays undefined only for ratios, malformed inputs have labeled ARIA errors; repeated reset/clear preserve unrelated descriptions')
                        checks.append('NAV context: applicable fields only; repeated calculate/reset and printable JSON record preserve inputs and not-applicable income/distribution metadata')
                checks.append('All five BDC tools reject an early analysis date and accept period-end equality')
                if args.bdc_only:
                    assert not errors, errors
                    report = {'passed':True,'checks':checks,'javascript_errors':errors,'real_form_submissions':0,'external_requests':0,'scope':'five BDC date UIs only'}
                    (output / 'audit-bdc-readiness-report.json').write_text(json.dumps(report, indent=2),encoding='utf-8')
                    print(json.dumps(report,indent=2),flush=True)
                    return

                page.goto(base + '/calculator-preferred-common.html')
                assert page.locator('form [name=basis]').count() == 0
                assert page.locator('[name=earningsDefinition]').count() == 1
                checks.append('Preferred form presents earnings definition without debt basis')

                page.goto(base + '/calculator-debt-ladder.html')
                form = page.locator('[data-capital-tool]')
                form.locator('[name=maturityBasis]').select_option('fiscal')
                assert form.locator('[name=horizonEnd]').is_disabled()
                assert not form.locator('[name=horizonEnd]').is_visible()
                assert form.locator('[name=resourceDate]').is_visible()
                form.locator('[name=rows]').fill('2027,+90,Consolidated principal,2026-09-30\n2028,100,Consolidated principal,2026-09-30')
                form.locator('button[type=submit]').click()
                result = page.locator('[data-capital-result]')
                assert '190' in result.get_by_role('row', name=re.compile('^Complete supplied maturity subtotal')).inner_text()
                assert 'Not defined' in result.get_by_role('row', name=re.compile('^Residual after supplied fiscal buckets\\s+Not')).inner_text()
                with page.expect_download() as maturity_download:
                    form.locator('[data-maturity-export]').click()
                maturity_path = Path(maturity_download.value.path())
                maturity_csv = maturity_path.read_text(encoding='utf-8-sig')
                assert '"2027","90"' in maturity_csv and '+90' not in maturity_csv
                form.locator('[data-maturity-file]').set_input_files(str(maturity_path))
                page.wait_for_function("!document.querySelector('[data-capital-tool] [role=alert]').textContent")
                assert not form.locator('[role=alert]').is_visible()
                with page.expect_download() as download:
                    page.locator('[data-capital-export]').click()
                exported = Path(download.value.path()).read_text(encoding='utf-8-sig')
                assert 'resourceDate' in exported and 'horizonEnd' not in exported
                assert 'Residual after supplied fiscal buckets' in exported
                form.locator('button[type=reset]').click()
                page.wait_for_function("document.querySelector('[name=resourceDate]').disabled")
                assert form.locator('[name=horizonEnd]').is_visible()
                checks.append('Fiscal mode withholds complete funding/residuals, round-trips +90 as 90, and resets to a dated cutoff')

                legacy = (ROOT / 'calculator-debt-ladder.html').read_text(encoding='utf-8').replace('name="resourceDate"', 'name="legacyResourceDate"')
                page.route(base + '/calculator-debt-ladder.html?legacy=1', lambda route: route.fulfill(status=200, content_type='text/html', body=legacy))
                page.goto(base + '/calculator-debt-ladder.html?legacy=1')
                assert 'cached worksheet' in page.locator('[data-capital-tool] [role=alert]').inner_text()
                assert page.locator('[data-capital-tool] button[type=submit]').is_disabled()
                checks.append('An old cached layout is blocked rather than mixed silently with the new calculator script')

                page.goto(base + '/research-desk.html')
                # Measure the actual CSS cascade at the leading inquiry CTA, including hover and keyboard focus.
                hero_selector = '.rd-hero .btn-p'
                hero_button = page.locator(hero_selector)
                for width in [320, 390, 1440]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    page.mouse.move(0, 0)
                    hero_button.evaluate('(e)=>e.blur()')
                    page.wait_for_timeout(250)
                    measured = page.evaluate(CONTRAST, hero_selector)
                    measured['state'] = 'default'
                    measured['viewport'] = width
                    contrast.append(measured)
                    assert measured['ratio'] >= 4.5, measured
                    hero_button.hover()
                    page.wait_for_timeout(200)
                    measured = page.evaluate(CONTRAST, hero_selector)
                    measured['state'] = 'hover'
                    measured['viewport'] = width
                    contrast.append(measured)
                    assert measured['ratio'] >= 4.5, measured
                    page.mouse.move(0, 0)
                    page.wait_for_timeout(250)
                    hero_button.focus()
                    page.keyboard.press('Tab')
                    page.keyboard.press('Shift+Tab')
                    assert hero_button.evaluate('(e)=>e===document.activeElement&&e.matches(":focus-visible")')
                    focus = hero_button.evaluate('(e)=>({style:getComputedStyle(e).outlineStyle,width:parseFloat(getComputedStyle(e).outlineWidth),color:getComputedStyle(e).outlineColor,offset:parseFloat(getComputedStyle(e).outlineOffset)})')
                    assert focus['style'] != 'none' and focus['width'] >= 2 and focus['offset'] >= 2, focus
                    measured = page.evaluate(CONTRAST, hero_selector)
                    measured['state'] = 'keyboard focus'
                    measured['viewport'] = width
                    measured['outline'] = focus
                    contrast.append(measured)
                    assert measured['ratio'] >= 4.5, measured
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                    page.locator('.rd-hero').screenshot(path=str(output / f'research-hero-reviewed-{width}.png'))
                checks.append('Research Desk hero CTA has actual default/hover/focus text contrast >=4.5 and a visible keyboard outline at 320/390/1440px')
                assert page.locator('.rd-tk .rd-tick').count() == 3
                assert page.locator('s').count() == 0
                assert not page.locator('#inquiries').evaluate("e=>!!e.closest('s')")
                page.locator('#rd-t').select_option('Paid article or column')
                for selector in ['#inquiries .rd-h2', '#inquiries .rd-sub', '#inquiries .rd-note',
                                 '#inquiries .proposal-terms .small-note', '#inquiries label[for=rd-n]',
                                 '#inquiries label[for=rd-scope]', '#inquiries .rd-form small',
                                 '#rd-m::placeholder', '#rd-scope::placeholder']:
                    measured = page.evaluate(CONTRAST, selector)
                    contrast.append(measured)
                    assert measured['ratio'] >= 4.5, measured
                for selector in ['#rd-n', '#rd-scope']:
                    page.locator(selector).focus()
                    outline = page.locator(selector).evaluate('(e)=>({style:getComputedStyle(e).outlineStyle,width:parseFloat(getComputedStyle(e).outlineWidth)})')
                    assert outline['style'] != 'none' and outline['width'] >= 2, (selector, outline)
                for width in [390, 1440]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                    page.locator('#inquiries').screenshot(path=str(output / f'proposal-reviewed-{width}.png'))
                checks.append('Decorative spans cannot spread strike-through; selected proposal text meets 4.5:1 and inputs show focus')
                page.goto(base + '/calculator-jv-debt.html')
                page.locator('[data-capital-tool] button[type=submit]').click()
                page.wait_for_selector('.calculator-output .small-note')
                measured = page.evaluate(CONTRAST, '.calculator-output .small-note')
                contrast.append(measured)
                assert measured['ratio'] >= 4.5, measured
                checks.append('Small result notes meet 4.5:1 on their actual dark background')

                page.goto(base + '/course-beginner.html')
                for width in [320, 390, 1440]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    route = page.locator('.course-lessons')
                    assert route.evaluate('(e)=>getComputedStyle(e).listStyleType') == 'none'
                    assert page.locator('.course-lessons > li > span').all_text_contents() == ['01', '02', '03', '04', '05', '06']
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                    if width in [390, 1440]:
                        route.screenshot(path=str(output / f'beginner-route-{width}.png'))
                checks.append('Beginner route shows six designed step labels without native list markers at 320/390/1440px')
                assert not errors, errors
            except Exception as error:
                print(json.dumps({'passed':False,'failure':str(error),'javascript_errors':errors,'checks_completed':checks},indent=2),flush=True)
                raise
            finally:
                if context is not None:
                    context.close()
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {'passed': True, 'checks': checks, 'contrast_samples': contrast, 'javascript_errors': errors,
              'real_form_submissions': 0, 'external_requests': 0}
    (output / 'audit-browser-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
