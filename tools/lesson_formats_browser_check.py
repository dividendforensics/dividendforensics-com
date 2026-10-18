"""Render every redesigned lesson and check static/interactive reading paths."""
from functools import partial
from pathlib import Path
from threading import Thread
import json
import os
import sys
from playwright.sync_api import sync_playwright
from resources_browser_check import Server, Handler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from education import load_articles
from bdc_education import load_articles as load_bdc


def main():
    articles = load_articles(ROOT) + load_bdc(ROOT)
    paths = [a['slug']+'.html' for a in articles]
    paths += ['es/'+a['slug']+'.html' for a in json.loads((ROOT/'content/spanish.json').read_text(encoding='utf-8'))]
    samples = ['learn-reit-basics', 'learn-net-lease', 'learn-ffo', 'learn-dividend-cuts',
               'learn-read-filings', 'learn-bdc-expert-income-bridge']
    out = ROOT/'.qa'; out.mkdir(exist_ok=True)
    server = Server(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors = []; renders = 0
    try:
        with sync_playwright() as p:
            exe = os.environ.get('CHROMIUM_PATH')
            if not exe and Path('C:/Program Files/Google/Chrome/Application/chrome.exe').is_file():
                exe = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
            browser = p.chromium.launch(headless=True, **({'executable_path': exe} if exe else {}))
            context = browser.new_context()
            context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
            for width in (320, 390, 1440):
                page.set_viewport_size({'width': width, 'height': 1000})
                for path in paths:
                    page.goto(base+'/'+path, wait_until='load')
                    assert page.locator('h1').count() == 1, path
                    assert page.locator('[data-reading-format]').count() == 1, path
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (path, width)
                    if 'expert-' in path:
                        assert page.locator('.workshop-analysis').evaluate('(e)=>e.compareDocumentPosition(document.querySelector(".worked-example")) & Node.DOCUMENT_POSITION_FOLLOWING'), path
                        for table in page.locator('.table-scroll').all():
                            assert page.locator('#'+table.get_attribute('aria-describedby')).is_visible()
                            table.focus()
                            page.keyboard.press('ArrowRight')
                            page.wait_for_timeout(100)
                            if table.evaluate('(e)=>e.scrollWidth>e.clientWidth'):
                                assert table.evaluate('(e)=>e.scrollLeft>0'), (path, width)
                                table.evaluate('(e)=>e.scrollLeft=e.scrollWidth')
                                assert table.evaluate('(e)=>Math.abs(e.scrollWidth-e.clientWidth-e.scrollLeft)<2'), path
                    page.evaluate('Array.from(document.images).forEach(i=>i.loading="eager")')
                    page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
                    if path[:-5] in samples and width in (390, 1440):
                        page.screenshot(path=str(out/f'lesson-{path[:-5]}-{width}.png'), full_page=True)
                    renders += 1
            page.goto(base+'/learn-bdc-expert-income-bridge.html')
            page.locator('.workshop-answer summary').click()
            assert page.locator('.workshop-answer[open]').count() == 1
            field = page.locator('[data-quiz] fieldset').first
            answer = int(field.get_attribute('data-answer'))
            field.locator('input').nth((answer+1)%3).check()
            page.locator('[data-quiz] button').click()
            assert '0 of' in page.locator('.quiz-score').inner_text()
            field.locator('input').nth(answer).check()
            page.locator('[data-quiz] button').click()
            assert '1 of' in page.locator('.quiz-score').inner_text()
            page.goto(base+'/learn-ffo.html')
            page.locator('.lesson-jump-menu a[href="#worked-example"]').focus()
            page.keyboard.press('Enter')
            assert page.url.endswith('#worked-example')
            nojs = browser.new_context(java_script_enabled=False)
            nojs.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            static = nojs.new_page()
            for sample in samples:
                static.goto(base+'/'+sample+'.html')
                assert static.locator('#worked-example').is_visible()
                assert static.locator('#source-notes a').count() >= 2
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
    result = dict(passed=True, pages=len(paths), renders=renders, javascript_errors=errors,
                  no_js_formats=6, quiz_retry=True, keyboard_anchor=True)
    (out/'lesson-formats-browser.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
