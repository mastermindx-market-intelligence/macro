"""Exercise the existing lazy-owner failure boundary; no remote HTTP or message."""
from pathlib import Path
import http.server,json,socketserver,threading,hashlib,sys
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
SITE=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/r15_actual')

def main():
    proof_root=HERE/'final' if '--final' in sys.argv else HERE
    target=proof_root/'assistant_failure.json'
    if target.exists():raise RuntimeError('Failure-proof target already exists; reconcile first')
    rows=[]
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(SITE),**kw)
        def log_message(self,*a):pass
    with socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_address[1]}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
                for width in [390,1440]:
                    for lang in ['en','zh']:
                        page=browser.new_page(viewport={'width':width,'height':900});events=[]
                        def intercept(route):
                            url=route.request.url
                            if 'mm_brain.js' in url:events.append('blocked_assistant_script');route.abort()
                            elif url.startswith(base+'/'):route.continue_()
                            else:route.abort()
                        page.route('**/*',intercept)
                        page.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','dark');")
                        page.goto(base+'/crypto.html',wait_until='networkidle');button=page.locator('[data-crypto-brain]')
                        button.focus();page.keyboard.press('Enter')
                        page.wait_for_selector('.desk-brain-status:not([hidden])',timeout=6000)
                        assert not button.is_disabled() and button.get_attribute('aria-busy') is None
                        status=page.locator('.desk-brain-status').inner_text()
                        assert ('Market research remains available.' if lang=='en' else '您仍可查看市场研究') in status
                        assert page.locator('[data-desk-budget-value]').inner_text()=='60%'
                        assert not page.locator('#mmb-launch').is_visible()
                        link=page.locator('.desk-budget-cta');link.focus();page.keyboard.press('Enter')
                        assert page.url.endswith('#allocation')
                        assert page.locator('[data-shelf]').count()==8
                        rows.append({'width':width,'language':lang,'status':status,'button_reenabled':True,'budget_preserved':True,'allocation_link_works':True,'blocked_script_requests':len(events)})
                        page.close()
                browser.close()
        finally:server.shutdown();thread.join(timeout=2)
    out={'classification':'CONTROLLED_ASSET_FAILURE_NOT_PROVIDER_OUTAGE','html_sha256':hashlib.sha256((SITE/'crypto.html').read_bytes()).hexdigest(),'cases':rows,
         'limits':'Existing shared owner script intentionally blocked; no chat message, backend request or live customer session.'}
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('ASSISTANT_FAILURE_PROOF',len(rows),'cases passed; existing market/budget navigation stays usable.')

if __name__=='__main__':main()
