from pathlib import Path
import hashlib,json,mimetypes,os,socket,subprocess,tempfile,time,urllib.request
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/news-cockpit-rebuild-20261018-astra-01')
OUT=Path('/tmp/news-9612-browser-assets-8128');OUT.mkdir(exist_ok=True)
pages={n:(ROOT/'site'/n).read_text() for n in ('news.html','plans.html')}
report={'scope':'committed generated pages with controlled local API fixtures; not production authentication','page_sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in pages.items()},'states':[]}
with tempfile.TemporaryDirectory(prefix='news9612-asset-preview-') as td:
    s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close();base=f'http://127.0.0.1:{port}'
    env=os.environ.copy();env['NEWS_DESK_PREVIEW_DIR']=td
    with open(Path(td)/'server.log','w+') as log:
        server=subprocess.Popen(['/opt/homebrew/bin/uvicorn','scripts.news_desk_preview:app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            for attempt in range(80):
                if server.poll() is not None:raise RuntimeError('fixture server exited')
                try:
                    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(base+'/news.html',timeout=.7) as response:
                        if response.status==200:break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('fixture startup deadline')
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args=['--disable-dev-shm-usage'])
                for width,height in [(1440,900),(390,844)]:
                    for theme in ['dark','light']:
                        for lang in ['en','zh']:
                            context=browser.new_context(viewport={'width':width,'height':height},locale='en-US',is_mobile=width<=760,has_touch=width<=760)
                            context.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
                            page=context.new_page();errors=[];bad_assets=[]
                            page.on('pageerror',lambda err:errors.append(str(err)[:180]))
                            page.on('response',lambda r:bad_assets.append({'url':r.url,'status':r.status}) if r.status>=400 and '/assets/' in r.url else None)
                            def route(r):
                                url=r.request.url
                                for name,html in pages.items():
                                    if url==base+'/'+name:r.fulfill(status=200,content_type='text/html',body=html);return
                                if not url.startswith(base+'/'):r.abort();return
                                relative=unquote(urlsplit(url).path).lstrip('/')
                                target=(ROOT/'site'/relative).resolve()
                                if target.is_relative_to((ROOT/'site').resolve()) and target.is_file() and target.suffix in {'.css','.js','.woff2','.png','.svg','.ico'}:
                                    r.fulfill(status=200,content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream',body=target.read_bytes());return
                                r.continue_()
                            page.route('**/*',route)
                            page.goto(base+'/news.html',wait_until='load',timeout=18000);page.wait_for_timeout(500)
                            print('INITIAL_AUTH_STATE',page.evaluate('''()=>({connection:document.querySelector('#ndConnection')?.textContent,historyDisabled:document.querySelector('#ndHistorySearch')?.disabled})'''),flush=True)
                            # Exercise the existing sign-in event with an explicitly synthetic reader.
                            # The local API already has the fixture-only identity override; this is not live login proof.
                            page.evaluate('''()=>window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{event:'SIGNED_IN',user:{id:'loopback-visual-test'}}}))''')
                            page.wait_for_timeout(500)
                            state=page.evaluate('''()=>({viewport:innerWidth,document_width:document.documentElement.scrollWidth,theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,feed_rows:document.querySelectorAll('#ndFeed .nd-row').length,connection:document.querySelector('#ndConnection')?.textContent,desk_width:document.querySelector('.news-desk')?.getBoundingClientRect().width,grid:getComputedStyle(document.querySelector('.nd-layout')||document.querySelector('.news-desk')).display,linked_styles:[...document.querySelectorAll('link[rel=stylesheet]')].map(n=>({href:n.getAttribute('href'),loaded:!!n.sheet}))})''')
                            assert state['document_width']==width,state
                            assert state['theme']==theme and state['lang']==lang,state
                            assert all(n['loaded'] for n in state['linked_styles']),state
                            if width==1440 and theme=='dark' and lang=='en':
                                page.locator('#ndHistoryOpen').click();page.locator('#ndHistoryQuery').fill('shipping');page.locator('#ndHistorySearch').click();page.wait_for_timeout(300)
                                state['history_status']=page.locator('#ndHistoryStatus').inner_text();state['older_retained_match']='Earlier energy reporting' in page.locator('#ndHistoryResults').inner_text();assert state['older_retained_match'],state
                                page.locator('#ndHistory [data-close-dialog]').click()
                            if width==390:
                                page.locator('#ndFeed .nd-title').first.click();state['modal']=page.locator('#ndDetail').get_attribute('aria-modal');assert state['modal']=='true'
                                candidates='[...p.querySelectorAll("button,a[href]")].filter(n=>n.tabIndex>=0&&!n.matches(":disabled")&&!n.hidden&&!n.closest("[hidden],[inert],[aria-hidden=true]"))'
                                page.locator('#ndDetail').evaluate('p=>{const n='+candidates+';n.at(-1).focus()}');page.keyboard.press('Tab')
                                state['tab_wrap']=page.locator('#ndDetail').evaluate('p=>{const n='+candidates+';return document.activeElement===n[0]}');assert state['tab_wrap']
                                page.keyboard.press('Shift+Tab');state['reverse_tab_wrap']=page.locator('#ndDetail').evaluate('p=>{const n='+candidates+';return document.activeElement===n.at(-1)}');assert state['reverse_tab_wrap']
                                page.locator('#ndDetailClose').click()
                            page.wait_for_timeout(500)
                            state['open_dialogs']=page.evaluate('''()=>[...document.querySelectorAll('dialog[open],[role=dialog]')].filter(n=>{const s=getComputedStyle(n);return !n.hidden&&n.getAttribute('aria-hidden')!=='true'&&s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>0.01}).map(n=>({id:n.id,opacity:getComputedStyle(n).opacity,rect:{width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height}}))''')
                            state['touch_emulation']=width<=760
                            state['fine_pointer']=page.evaluate("matchMedia('(hover:hover) and (pointer:fine)').matches")
                            assert not state['open_dialogs'],state['open_dialogs']
                            if (width,theme,lang) in [(1440,'dark','en'),(390,'light','zh')]:
                                file=OUT/f'news-{width}-{theme}-{lang}.png';page.screenshot(path=str(file),full_page=False);state['screenshot_sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
                            state['page_errors']=errors;state['bad_assets']=bad_assets;assert not errors and not bad_assets,state
                            report['states'].append(state);print('STATE_OK',width,theme,lang,flush=True)
                            context.close()
                report['plans_states']=[]
                for width,height,lang in [(1440,900,'en'),(1440,900,'zh'),(390,844,'en'),(390,844,'zh')]:
                    context=browser.new_context(viewport={'width':width,'height':height},locale='en-US',is_mobile=width<=760,has_touch=width<=760)
                    context.add_init_script('localStorage.setItem("theme","light");localStorage.setItem("lang",'+json.dumps(lang)+');')
                    page=context.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)[:180]));page.route('**/*',route)
                    page.goto(base+'/plans.html',wait_until='load',timeout=18000);page.wait_for_timeout(500)
                    state=page.evaluate('''()=>({viewport:innerWidth,document_width:document.documentElement.scrollWidth,lang:document.documentElement.dataset.lang,has_ecb:document.body.textContent.includes('ECB'),has_rba:document.body.textContent.includes('RBA'),local_assets:[...document.querySelectorAll('script[src],link[rel=stylesheet]')].map(n=>({url:n.getAttribute('src')||n.getAttribute('href'),loaded:n.tagName==='LINK'?!!n.sheet:true}))})''')
                    assert state['document_width']==width and state['lang']==lang and state['has_ecb'] and state['has_rba'],state
                    assert all(a['loaded'] and ('?v=' in a['url'] or a['url'].startswith('http')) for a in state['local_assets']),state
                    state['page_errors']=errors;assert not errors,errors
                    report['plans_states'].append(state);context.close();print('PLANS_OK',width,lang,flush=True)
                browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
            report['temporary_server_stopped']=server.returncode is not None
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('BROWSER_MATRIX_PASS',len(report['states']),str(OUT/'report.json'),flush=True)
