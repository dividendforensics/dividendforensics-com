"""Focused local Chrome regression for exact decimal display, tables and CSV."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import csv
import argparse
import io
import json
import os

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CASES=[
    ('below','1024.59999999999999999999','76.84499999999999999999925','76.84','76,84'),
    ('half','1024.6','76.845','76.85','76,85'),
    ('above','1024.60000000000000000001','76.84500000000000000000075','76.85','76,85'),
]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class QAServer(ThreadingHTTPServer):
    # CSS and deferred scripts share this local-only server under concurrent QA.
    request_queue_size=128
    daemon_threads=True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-queue-size',type=int,choices=[5,128],default=128,
                        help='Local server backlog; 5 is available for a diagnostic comparison.')
    args=parser.parse_args()
    QAServer.request_queue_size=args.request_queue_size
    server=QAServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    out=ROOT/'.qa';out.mkdir(exist_ok=True)
    errors=[];blocked=[];results=[];responses=[];failed=[];engines=[]
    def report(passed,failure=None):
        return {'passed':passed,'cases':results,'checks':['English and Spanish half-cent boundaries','exact input and output in actual downloaded CSV','numeric scenario table rounds decimal strings','FFO exact zero and true negative1e-21 preserved'],'javascript_errors':errors,'blocked_external_requests':blocked,'failed_requests':failed,'responses':responses,'engine_checks':engines,'failure':failure,'request_queue_size':args.request_queue_size,'real_form_submissions':0,'precision_significant_digits':80,'unlimited_precision_claim':False}
    try:
        with sync_playwright() as p:
            executable=os.environ.get('CHROMIUM_PATH')
            fallback=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
            if not executable and fallback.is_file():executable=str(fallback)
            browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
            context=browser.new_context(accept_downloads=True,viewport={'width':390,'height':1000})
            def local_only(route):
                if route.request.url.startswith(base+'/'):route.continue_()
                else:blocked.append(route.request.url);route.abort()
            context.route('**/*',local_only)
            try:
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.set_default_timeout(10000)
                page.on('response',lambda response:responses.append({'url':response.url,'status':response.status,'content_length':response.headers.get('content-length')}))
                page.on('requestfailed',lambda request:failed.append({'url':request.url,'failure':request.failure}))
                def require_engine(spanish=False):
                    state=page.evaluate('''() => ({url:location.href,readyState:document.readyState,
                        decimal:typeof window.Decimal,engine:typeof window.DFBOriginal,
                        calculate:typeof window.DFBOriginal?.calculate,
                        disabled:document.querySelector('button[type=submit]')?.disabled,
                        guard:document.querySelector('[data-result],[data-es-result]')?.textContent,
                        scripts:Array.from(document.scripts).filter(s=>s.src).map(s=>s.src)})''')
                    engines.append(state)
                    assert state['readyState']=='complete',state
                    assert state['decimal']=='function' and state['calculate']=='function' and state['disabled'] is False,state
                    if spanish:
                        assert page.locator('[data-es-calculator]').count()==1
                for name,capital,exact,en,es in CASES:
                    page.goto(base+'/calculator-dividend-income.html')
                    require_engine()
                    form=page.locator('[data-calculator=income]')
                    for key,value in [('capital',capital),('yield','7.5'),('tax','0'),('target','0')]:form.locator(f'input[name="{key}"]').fill(value)
                    form.locator('button[type=submit]').click()
                    assert form.locator('[name=capital]').input_value()==capital
                    assert page.locator('.result-metrics dd').first.inner_text()==en
                    assert page.locator('.table-scroll tbody tr').nth(1).locator('td').nth(1).inner_text()==en
                    with page.expect_download() as download:page.get_by_role('button',name='Download this scenario (CSV)').click()
                    data=Path(download.value.path()).read_text(encoding='utf-8-sig')
                    rows=list(csv.reader(io.StringIO(data)))
                    assert ['capital',capital] in rows
                    assert ['Annual gross distributions',exact] in rows
                    assert ['Annual after-withholding income',exact] in rows
                    assert ['7.50%',exact,exact] in rows
                    (out/f'precision-{name}.csv').write_text(data,encoding='utf-8')
                    page.goto(base+'/es/calculadora-dividendos.html')
                    require_engine(spanish=True)
                    form=page.locator('[data-es-calculator=income]')
                    for key,value in [('capital',capital),('yield','7.5'),('tax','0'),('target','0')]:form.locator(f'input[name="{key}"]').fill(value)
                    form.locator('button[type=submit]').click()
                    assert form.locator('[name=capital]').input_value()==capital
                    assert page.locator('[data-es-result] dd').first.inner_text()==es
                    results.append({'case':name,'input':capital,'exact_csv':exact,'english_display':en,'spanish_display':es})
                # Tiny genuine differences remain signed; only actual cancellation is zero.
                page.goto(base+'/calculator-ffo-affo.html')
                require_engine()
                form=page.locator('[data-calculator=bridge]')
                for key,value in [('net','0.1'),('depreciation','0.2'),('gains','0.3'),('ffoOther','0'),('capex','0'),('rent','0'),('affoOther','0')]:form.locator(f'input[name="{key}"]').fill(value)
                form.locator('button[type=submit]').click()
                assert page.locator('.result-metrics dd').first.inner_text()=='0.00'
                form.locator('[name=affoOther]').fill('-0.000000000000000000001')
                form.locator('button[type=submit]').click()
                assert page.locator('.result-metrics dd').nth(1).inner_text()=='-1.000e-21'
                with page.expect_download() as download:page.get_by_role('button',name='Download this scenario (CSV)').click()
                rows=list(csv.reader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))))
                assert ['Modeled AFFO','-1e-21'] in rows
                assert not errors,errors
            finally:
                context.close()
                browser.close()
    except Exception as error:
        failure_report=report(False,str(error))
        (out/'precision-browser-report.json').write_text(json.dumps(failure_report,indent=2),encoding='utf-8')
        print(json.dumps(failure_report,indent=2))
        raise
    finally:
        server.shutdown();server.server_close()
    result=report(True)
    (out/'precision-browser-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'cases':results,'javascript_errors':errors,'failed_local_requests':[r for r in failed if r['url'].startswith(base+'/')],'request_queue_size':args.request_queue_size,'engine_checks':len(engines)},indent=2))


if __name__=='__main__':main()
