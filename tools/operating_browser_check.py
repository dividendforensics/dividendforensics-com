"""Exercise the operating-company journey on localhost; never submit external forms."""
from functools import partial
from pathlib import Path
from threading import Thread
import csv
import io
import json
import os
from playwright.sync_api import sync_playwright, expect
from resources_browser_check import Server, Handler

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['operating-companies.html', 'operating-cash-flow-guide.html',
         'dividends-buybacks-guide.html', 'cash-flow-workbench.html', 'filing-lab-apple-2024.html']


def main():
    output = ROOT / '.qa'
    output.mkdir(exist_ok=True)
    server = Server(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors, submissions, renders, checks = [], [], [], []
    try:
        with sync_playwright() as p:
            exe = os.environ.get('CHROMIUM_PATH')
            fallback = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
            if not exe and fallback.exists(): exe = str(fallback)
            browser = p.chromium.launch(headless=True, **({'executable_path': exe} if exe else {}))
            context = browser.new_context(accept_downloads=True)
            context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base+'/') else r.abort())
            context.on('request', lambda r: submissions.append(r.url) if r.method != 'GET' else None)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            for width in (320, 390, 768, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 950})
                for name in PAGES:
                    page.goto(base+'/'+name, wait_until='networkidle')
                    assert page.locator('h1').count() == 1, name
                    size = page.evaluate('({width:innerWidth, content:document.documentElement.scrollWidth})')
                    assert size['content'] <= width+1, (name, size)
                    renders.append(dict(page=name, **size))
                    assert page.locator('main').inner_text().strip(), name
                    if width in (390, 1440):
                        page.screenshot(path=str(output/f'operating-{name}-{width}.png'))
            page.goto(base+'/filing-lab-apple-2024.html', wait_until='networkidle')
            first = page.locator('main details summary').first
            first.focus(); page.keyboard.press('Enter')
            assert first.locator('..').get_attribute('open') is not None
            page.locator('a[href="/cash-flow-workbench.html?example=apple-2024"]').first.click()
            form = page.locator('[data-operating-workbench]')
            result = page.locator('[data-operating-result]')
            expect(form.locator('[name=netIncome]')).to_have_value('93736')
            expect(result).to_contain_text('118254')
            text = result.inner_text()
            assert all(n in text for n in ('118254', '108807', '-1376', '29943')), text
            assert text.count('Matches entered totals (gap 0)') == 2
            source = form.locator('[data-operating-source]').inner_text()
            assert '2024-11-01' in source and 'convention' in source
            checks.append('Native answer key → Apple preset; OCF, FCF, residual and two independent reconciliations')
            page.locator('[data-operating-baseline]').click()
            form.locator('[name=capex]').fill('10447')
            assert '-2376' in result.inner_text()
            comparison = page.locator('[data-operating-comparison]').inner_text()
            assert '-1000' in comparison and 'Apple FY2024' in comparison
            assert 'gap 0' in result.inner_text()
            checks.append('Retained baseline and edited capex: residual delta -1000; reported cash balance unchanged')
            with page.expect_download() as download:
                page.locator('[data-operating-export]').click()
            target = output/'operating-comparison.csv'
            download.value.save_as(str(target))
            raw = target.read_text(encoding='utf-8-sig')
            rows = list(csv.reader(io.StringIO(raw)))
            assert '-1000' in raw and '108807' in raw and '107807' in raw
            assert 'convention' in raw and '2024-11-01' in raw, 'Export must preserve source dates and FX convention'
            assert any('Baseline' in row[0] for row in rows)
            checks.append('Actual CSV download contains baseline, current inputs, exact deltas and source caveats')
            bad = form.locator('[name=capex]')
            bad.fill('-1'); bad.press('Enter')
            assert form.locator('[data-operating-error]').is_visible()
            assert bad.get_attribute('aria-invalid') == 'true'
            assert page.locator('[data-operating-export]').is_disabled()
            assert 'Results cleared' in result.inner_text()
            bad.fill('9447')
            assert not form.locator('[data-operating-error]').is_visible()
            assert bad.get_attribute('aria-invalid') is None
            assert not page.locator('[data-operating-export]').is_disabled()
            checks.append('Negative payment → keyboard error focus/ARIA and stale-output clearing → correction')
            form.locator('[name=reportedOCF]').fill('')
            assert 'Not checked' in result.inner_text() and 'Not calculated' in result.inner_text()
            form.locator('[name=reportedOCF]').fill('118255')
            assert 'Unreconciled' in result.inner_text()
            checks.append('Missing OCF remains unknown; mismatched total is visibly unreconciled')
            payload = '=SUM(1,2) <script>window.injected=true</script>'
            form.locator('[name=scenarioLabel]').fill(payload)
            assert payload in result.inner_text()
            assert page.evaluate('window.injected === undefined')
            with page.expect_download() as download:
                page.locator('[data-operating-export]').click()
            unsafe = output/'operating-safe-label.csv'; download.value.save_as(str(unsafe))
            assert "'=SUM(1,2)" in unsafe.read_text(encoding='utf-8-sig')
            checks.append('User labels render as text; spreadsheet formulas are escaped in CSV')
            assert page.evaluate('localStorage.length === 0 && sessionStorage.length === 0')
            assert not context.cookies()
            page.reload(wait_until='networkidle')
            assert 'No baseline retained' in page.locator('[data-operating-comparison]').inner_text()
            checks.append('Reload discards edited values and retained baseline; no browser storage/cookies')
            context.close()
            nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 950})
            nojs.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base+'/') else r.abort())
            page = nojs.new_page()
            for name in PAGES:
                page.goto(base+'/'+name)
                assert len(page.locator('main').inner_text()) > 1000
                if name == 'cash-flow-workbench.html':
                    assert page.locator('form input').first.is_disabled()
                    assert page.locator('[data-operating-loading]').is_visible()
                elif page.locator('main details summary').count():
                    summary = page.locator('main details summary').first
                    summary.focus(); page.keyboard.press('Enter')
                    assert summary.locator('..').get_attribute('open') is not None
            checks.append('Actual JavaScript-disabled browser: five pages readable, native answers usable, tool disabled')
            nojs.close(); browser.close()
    finally:
        server.shutdown()
    assert not errors, errors
    assert not submissions, submissions
    report = dict(passed=True, renders=renders, checks=checks, javascript_errors=errors, real_form_submissions=len(submissions))
    (output/'operating-browser.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(passed=True, renders=len(renders), checks=checks, javascript_errors=errors, real_form_submissions=0)))


if __name__ == '__main__': main()
