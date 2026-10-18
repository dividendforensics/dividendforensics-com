"""Focused localhost regression for decimal display, CSV chooser roundtrip and recovery."""
from decimal import Decimal
from functools import partial
from pathlib import Path
from threading import Thread
import csv
import io
import json
import os

from playwright.sync_api import sync_playwright
from resources_browser_check import Server, Handler

ROOT = Path(__file__).resolve().parents[1]


def main():
    server = Server(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    output = ROOT / '.qa'
    output.mkdir(exist_ok=True)
    errors, console_errors, expected_blocked_errors, checks, requests = [], [], [], [], []
    blocked_external = set()
    try:
        with sync_playwright() as p:
            executable = os.environ.get('CHROMIUM_PATH')
            fallback = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
            if not executable and fallback.exists():
                executable = str(fallback)
            browser = p.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
            context = browser.new_context(accept_downloads=True, viewport={'width': 390, 'height': 950})
            def local_only(route):
                if route.request.url.startswith(base + '/'):
                    route.continue_()
                else:
                    blocked_external.add(route.request.url)
                    route.abort()
            context.route('**/*', local_only)
            context.on('request', lambda r: requests.append(r.url) if r.method != 'GET' else None)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            def console_message(message):
                if message.type != 'error':
                    return
                entry = {'text': message.text, 'url': message.location.get('url', '')}
                # The harness intentionally blocks external fonts. Exempt only an
                # exact URL blocked by this route, not arbitrary network errors.
                if entry['url'] in blocked_external and message.text == 'Failed to load resource: net::ERR_FAILED':
                    expected_blocked_errors.append(entry)
                else:
                    console_errors.append(entry)
            page.on('console', console_message)
            try:
                page.goto(base + '/calculator-ffo-affo.html')
                form = page.locator('[data-calculator]')
                for field in form.locator('input').all():
                    field.fill('0.004')
                form.locator('[type=submit]').click()
                result = page.locator('[data-result]')
                displayed = result.locator('tbody tr td').all_inner_texts()
                assert displayed == ['0.004', '0.004', '-0.004', '0.004', '0.008', '-0.004', '-0.004', '0.004', '0.004']
                assert sum(map(Decimal, displayed[:4])) == Decimal(displayed[4])
                assert Decimal(displayed[4]) + sum(map(Decimal, displayed[5:8])) == Decimal(displayed[8])
                assert result.locator('dd').all_inner_texts() == ['0.008', '0.004', '-0.004']
                assert result.locator('[data-bridge-subtotal] strong').count() == 4
                assert result.locator('tbody th[scope=row]').count() == 9
                assert 'without cent rounding' in result.inner_text()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                result.screenshot(path=str(output / 'ffo-bridge-small-values-390.png'))
                with page.expect_download() as downloaded:
                    result.get_by_role('button', name='Download this scenario (CSV)').click()
                bridge_csv = list(csv.reader(io.StringIO(Path(downloaded.value.path()).read_text(encoding='utf-8-sig'))))
                assert ['Simplified FFO', '0.008'] in bridge_csv
                assert ['Net FFO-to-AFFO adjustment', '-0.004'] in bridge_csv
                checks.append('FFO bridge 0.004 inputs reconcile visibly to 0.008 FFO and 0.004 AFFO; subtotals, metrics and CSV agree')

                for name in ['nii-pik', 'pik-ratios']:
                    page.goto(base + f'/calculator-bdc-{name}.html')
                    intro = page.locator('[data-pik-introduction]')
                    assert 'PIK means payment-in-kind' in intro.inner_text()
                    assert intro.evaluate("e => Boolean(e.compareDocumentPosition(document.querySelector('form[data-bdc-tool]')) & Node.DOCUMENT_POSITION_FOLLOWING)")
                    form = page.locator('[data-bdc-tool]')
                    for key, value in [('nii', '0.00003'), ('pik', '0.00004'), ('tii', '1')]:
                        form.locator(f'[data-bdc-input][name={key}]').fill(value)
                    form.locator('[type=submit]').click()
                    result = page.locator('[data-bdc-result]')
                    assert result.get_by_role('row').filter(has=page.get_by_role('rowheader', name='PIK / total investment income', exact=True)).locator('td').inner_text() == '0.0040%'
                    if name == 'nii-pik':
                        assert result.get_by_role('row').filter(has=page.get_by_role('rowheader', name='Simple sensitivity: 100% PIK deduction', exact=True)).locator('td').inner_text() == '-0.00001'
                    assert '24 fractional places' in result.inner_text()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    checks.append(f'BDC {name}: PIK expands before inputs; small signed decimal results and percent scale are retained')

                page.goto(base + '/calculator-preferred-common.html')
                form = page.locator('[data-capital-tool]')
                for name, value in [('earnings', '0.00001'), ('preferred', '0'), ('common', '0.00002')]:
                    form.locator(f'[name={name}]').fill(value)
                form.locator('[type=submit]').focus()
                page.keyboard.press('Enter')
                result = page.locator('[data-capital-result]')
                def metric(label):
                    return result.get_by_role('row').filter(has=page.get_by_role('rowheader', name=label, exact=True)).locator('td').inner_text()
                assert metric('Common-attributed measure') == '0.00001'
                assert metric('Common measure less common distributions') == '-0.00001'
                assert metric('Preferred distributions') == '0'
                result.screenshot(path=str(output / 'capital-small-values-390.png'))
                with page.expect_download() as downloaded:
                    page.locator('[data-capital-export]').click()
                rows = list(csv.reader(io.StringIO(Path(downloaded.value.path()).read_text(encoding='utf-8-sig'))))
                assert rows[0] == ['DFB user scenario / synthetic default', 'capital-1.0.3']
                assert ['Common-attributed measure', '0.00001'] in rows
                assert ['Common measure less common distributions', '-0.00001'] in rows
                for name, value in [('earnings', '0.3'), ('preferred', '0.1'), ('common', '0.2')]:
                    form.locator(f'[name={name}]').fill(value)
                form.locator('[type=submit]').click()
                assert metric('Common measure less common distributions') == '0'
                checks.append('Tiny positive and negative values stay nonzero; actual cancellation stays zero; CSV retains exact decimals')

                page.goto(base + '/calculator-debt-ladder.html')
                form = page.locator('[data-capital-tool]')
                contents = ('\ufeffdate,amount,scope,asOf\r'
                            '2027-03-31,+0.00001,"Bond, ""A""\nSecond line",2026-09-30\r'
                            '2027-04-30,,"  =SUM(1,2)",2026-09-30\r')
                with page.expect_file_chooser() as chooser:
                    form.locator('[data-maturity-file]').click()
                chooser.value.set_files({'name': 'maturities.csv', 'mimeType': 'text/csv', 'buffer': contents.encode('utf-8')})
                page.wait_for_function("document.querySelector('[data-capital-result] table') !== null")
                assert not form.locator('[role=alert]').is_visible()
                result = page.locator('[data-capital-result]')
                assert metric('Known maturity subtotal') == '0.00001'
                assert metric('Complete supplied maturity subtotal') == 'Not defined / incomplete'
                assert metric('Residual after maturities') == 'Not defined / incomplete'
                with page.expect_download() as downloaded:
                    form.locator('[data-maturity-export]').click()
                imported_path = Path(downloaded.value.path())
                exported = list(csv.reader(io.StringIO(imported_path.read_text(encoding='utf-8-sig'))))
                assert exported == [['date', 'amount', 'scope', 'asOf'],
                                    ['2027-03-31', '0.00001', 'Bond, "A"\nSecond line', '2026-09-30'],
                                    ['2027-04-30', '', "'  =SUM(1,2)", '2026-09-30']]
                form.locator('[name=rows]').fill('invalid')
                with page.expect_file_chooser() as chooser:
                    form.locator('[data-maturity-file]').click()
                chooser.value.set_files({'name': 'invalid.csv', 'mimeType': 'text/csv', 'buffer': b'wrong,header\n'})
                page.wait_for_function("document.querySelector('[data-capital-result]').textContent === 'Import rejected. No current result.'")
                assert form.locator('[role=alert]').is_visible()
                with page.expect_file_chooser() as chooser:
                    form.locator('[data-maturity-file]').click()
                chooser.value.set_files(str(imported_path))
                page.wait_for_function("document.querySelector('[data-capital-result] table') !== null")
                assert not form.locator('[role=alert]').is_visible()
                assert metric('Known maturity subtotal') == '0.00001'
                checks.append('CSV chooser import/export/reimport preserves CR rows, quoted newlines, unknown amounts and neutralized formula text; malformed import clears results and valid reimport recovers')

                for locale in ['de', 'ja', 'zh-hant']:
                    page.goto(base + f'/{locale}/income.html')
                    form = page.locator('[data-international-calculator]')
                    field = form.locator('[name=capital]')
                    field.fill('10.000' if locale == 'de' else '1,000')
                    form.locator('[type=submit]').focus()
                    page.keyboard.press('Enter')
                    error = form.locator('[role=alert]')
                    assert error.is_visible()
                    assert field.evaluate('e => e === document.activeElement')
                    assert field.get_attribute('aria-invalid') == 'true'
                    assert page.locator('[data-international-result]').inner_text() == error.inner_text()
                    page.locator('.calculator-layout').screenshot(path=str(output / f'calculator-{locale}-error-recovery-390.png'))
                    field.fill('10000')
                    assert not error.is_visible()
                    assert field.get_attribute('aria-invalid') is None
                    page.keyboard.press('Enter')
                    assert page.locator('[data-international-result] dd').count() == 4
                    form.locator('[type=reset]').click()
                    assert page.locator('[data-international-result] dd').count() == 0
                    assert page.locator('[data-international-result]').inner_text().strip()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    checks.append(f'{locale}: keyboard errors have visible output and field focus; editing and reset recover')
                assert not errors, errors
                assert not console_errors, console_errors
                assert not requests, requests
            finally:
                context.close()
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {'passed': True, 'checks': checks, 'javascript_errors': errors, 'console_errors': console_errors,
              'expected_blocked_external_errors': expected_blocked_errors,
              'blocked_external_requests': sorted(blocked_external), 'real_form_submissions': len(requests)}
    (output / 'calculator-quality-browser.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
