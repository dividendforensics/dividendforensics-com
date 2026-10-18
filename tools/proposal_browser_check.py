"""Mock-only proposal regression: never sends to FormSubmit or an email service."""
from pathlib import Path
import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--browser',default=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    args=parser.parse_args()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
        def log_message(self,*a): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,**({'executable_path':args.browser} if Path(args.browser).is_file() else {}))
            page=browser.new_page();page.set_default_timeout(7000)
            calls=[];pending=[];errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            def route_request(route):
                url=route.request.url
                if url.startswith(f'http://127.0.0.1:{server.server_port}/'):
                    route.continue_()
                elif url.startswith('https://formsubmit.co/'):
                    assert '/ajax/' in url,'Unexpected non-AJAX form submission'
                    calls.append(route.request);pending.append(route)
                else:
                    route.abort() # Includes third-party fonts: zero external networking.
            page.route('**/*',route_request)
            page.goto(f'http://127.0.0.1:{server.server_port}/research-desk.html',wait_until='domcontentloaded')
            page.wait_for_function("document.querySelector('[data-proposal-terms]').hidden")
            assert not page.locator('#rd-privacy').is_checked()
            page.locator('button[type=submit]').click()
            assert len(calls)==0
            checks.append('Empty form and unchecked privacy block requests')
            page.locator('#rd-n').fill('Regression tester')
            page.locator('#rd-e').fill('local-test@example.invalid')
            page.locator('#rd-m').fill('Mock-only inquiry. No real email is sent.')
            page.locator('#rd-privacy').check()
            project_types=['Paid article or column','Commissioned REIT/BDC research','Content licensing','Written-content collaboration']
            for project in project_types:
                page.locator('#rd-t').select_option(project)
                assert page.locator('[data-proposal-terms]').is_visible()
                assert page.locator('#rd-scope').evaluate('(e)=>e.required&&!e.disabled')
                assert page.locator('#rd-budget').evaluate('(e)=>e.required&&!e.disabled')
                page.locator('button[type=submit]').click()
                assert len(calls)==0
            checks.append('All 4 project types require project terms and specified fee/currency')
            page.locator('#rd-budget-state').select_option('discussion')
            assert page.locator('#rd-budget').is_disabled()
            assert page.locator('#rd-currency').is_disabled()
            page.locator('#rd-scope').fill('One original written research article')
            for field in ['#rd-deadline','#rd-payment','#rd-revisions','#rd-usage']:
                page.locator(field).fill('Open to discussion')
            page.locator('#rd-exclusivity').select_option('Open to discussion')
            assert page.locator('#proposal-form').evaluate('(e)=>e.checkValidity()')
            checks.append('Open to discussion is explicit; budget/currency excluded rather than zero')
            page.locator('#rd-budget-state').select_option('specified')
            page.locator('#rd-currency').select_option('USD')
            for value in ['0','-1','1,500','500-100','1e3','NaN','Infinity','100-0']:
                page.locator('#rd-budget').fill(value)
                assert not page.locator('#rd-budget').evaluate('(e)=>e.checkValidity()'),value
            for value in ['1500','1500-2500','1500.50','1500.50-2500.99']:
                page.locator('#rd-budget').fill(value)
                assert page.locator('#rd-budget').evaluate('(e)=>e.checkValidity()'),value
            checks.append('Fee syntax rejects invalid/zero/reversed ranges and accepts valid decimal ranges')
            page.locator('button[type=submit]').click()
            page.wait_for_timeout(100)
            assert len(calls)==1
            assert page.locator('button[type=submit]').is_disabled()
            assert page.locator('#proposal-form').get_attribute('aria-busy')=='true'
            page.locator('#proposal-form').evaluate("e=>{e.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));e.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}")
            page.wait_for_timeout(80)
            assert len(calls)==1
            assert 'Fee status' in calls[0].post_data
            assert 'specified' in calls[0].post_data
            assert 'Submission reference' in calls[0].post_data
            pending.pop(0).fulfill(status=200,content_type='application/json',body=json.dumps({'success':True}))
            page.wait_for_function("!document.querySelector('#proposal-form').hasAttribute('aria-busy')")
            status=page.locator('.proposal-status').inner_text()
            assert 'accepted your submission' in status and 'does not confirm email delivery' in status
            assert page.locator('#rd-m').input_value()=='Mock-only inquiry. No real email is sent.'
            assert page.locator('#rd-budget').input_value()=='1500.50-2500.99'
            checks.append('Pending duplicates blocked; mocked service success retains values and never claims inbox delivery')
            page.locator('#rd-t').select_option('Question or correction')
            assert page.locator('[data-proposal-terms]').is_hidden()
            assert page.locator('#rd-scope').is_disabled()
            page.locator('#rd-url').fill('https://example.invalid/source')
            assert page.locator('#proposal-form').evaluate('(e)=>e.checkValidity()')
            page.locator('button[type=submit]').click();page.wait_for_timeout(100)
            assert len(calls)==2
            body=calls[-1].post_data
            for excluded in ['Scope and deliverables','Offered fee or budget','Currency','Usage and distribution rights']:
                assert 'name="'+excluded+'"' not in body
            pending.pop(0).fulfill(status=503,content_type='application/json',body=json.dumps({'success':False}))
            page.wait_for_function("!document.querySelector('#proposal-form').hasAttribute('aria-busy')")
            assert 'could not confirm' in page.locator('.proposal-status').inner_text()
            assert page.locator('#rd-url').input_value()=='https://example.invalid/source'
            assert page.locator('#rd-m').input_value()=='Mock-only inquiry. No real email is sent.'
            assert page.locator('button[type=submit]').is_enabled()
            checks.append('Question mode omits disabled project fields; 503 failure retains input and re-enables retry')
            page.locator('button[type=submit]').click();page.wait_for_timeout(80)
            pending.pop(0).abort('failed')
            page.wait_for_function("!document.querySelector('#proposal-form').hasAttribute('aria-busy')")
            assert 'could not confirm' in page.locator('.proposal-status').inner_text()
            assert page.locator('#rd-n').input_value()=='Regression tester'
            checks.append('Network failure is not reported as success; inputs preserved')
            page.locator('#rd-t').select_option('Other')
            assert page.locator('[data-proposal-terms]').is_hidden()
            page.locator('#rd-e').fill('not-an-email')
            assert not page.locator('#proposal-form').evaluate('(e)=>e.checkValidity()')
            assert not errors,errors
            checks.append('Other mode and email validation checked; JavaScript errors: 0')
            for width in [360,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
            checks.append('Current question-mode layout has no page overflow at 360/768/1440')
            browser.close()
        print(json.dumps({'result':'PASS','checks':checks,'mocked_submissions':len(calls),'real_external_requests':0,'actual_inbox_delivery':'NOT RUN'},ensure_ascii=False,indent=2))
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':run()
