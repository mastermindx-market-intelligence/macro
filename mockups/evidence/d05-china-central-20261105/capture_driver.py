from pathlib import Path
import base64, hashlib, json, mimetypes, os, sys, time, traceback
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import capture_page_evidence as cpe
FIXTURE=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104/.pytest_cache/d05-ci-recovery-82c377/china-archive')
SITE=FIXTURE/'site-candidate-history'
OUT=ROOT/'mockups/evidence/d05-china-central-20261105'
BASE='http://localhost:3100'
CHILD='http://localhost:8765'
LEDGER=[]
USER={'id':'e2e-user-default','email':'responsive@example.com','aud':'authenticated','app_metadata':{},'user_metadata':{}}
SESSION={'access_token':'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlMmUtdXNlci1kZWZhdWx0In0.fixture-only','refresh_token':'d05-fixture-only','expires_in':3600,'expires_at':int(time.time())+3600,'token_type':'bearer','user':USER}
COOKIE='base64-'+base64.urlsafe_b64encode(json.dumps(SESSION,separators=(',',':')).encode()).decode().rstrip('=')

class ChinaFrameDriver:
    def __init__(self, *, headless, user_agent, observer_config, settle_ms):
        self.manager=sync_playwright().start()
        self.browser=self.manager.chromium.launch(headless=headless,chromium_sandbox=True)
        self.user_agent=user_agent
        self.observer_config=dict(observer_config)
        self.settle_ms=settle_ms

    def capture(self, *, url, cell, timeout_s):
        state={'theme':cell.theme,'locale':cell.locale}
        case={'cell_id':cell.cell_id,'url':url,'viewport':[cell.width,cell.height],
              'requested':state,'force_state':None if cell.force_state is None else cell.force_state.as_payload(),
              'intercepted':[],'continued_child_requests':[],'page_errors':[],
              'auth_scope':'fixture-only synthetic identity; no live authenticated request'}
        errors=[]; failed=[]; counters={'requests':0,'bytes':0}
        context=self.browser.new_context(viewport={'width':cell.width,'height':cell.height},
            user_agent=self.user_agent,locale='zh-CN' if cell.locale=='zh' else 'en-US',
            color_scheme=cell.theme,device_scale_factor=1,reduced_motion='reduce',has_touch=cell.width<1024)
        context.add_init_script(cpe.state_seed_source(state))
        context.add_init_script(cpe.timing_init_source())
        context.add_init_script("""(({theme,locale})=>{localStorage.setItem('theme',theme);localStorage.setItem('lang',locale);localStorage.setItem('mm.theme',theme);localStorage.setItem('mm.lang',locale);if(location.port==='8765'){window.MM_TERMINAL_BASE='https://app.mastermind-x.com/terminal';window.SUPABASE_CFG={url:'http://localhost:8765/fixture-auth',anonKey:'d05-fixture-only',ref:'d05-native-fixture'};}})("""+json.dumps(state)+");")
        context.add_cookies([{'name':'sb-d05-native-fixture-auth-token','value':COOKIE,'url':CHILD},{'name':'mm_e2e_rs30','value':'1','url':BASE}])
        def route(r):
            request_url=r.request.url
            if request_url.startswith(CHILD+'/fixture-auth/auth/v1/user'):
                r.fulfill(status=200,content_type='application/json',body=json.dumps(USER));return
            if request_url.startswith(CHILD+'/'):
                rel=urlsplit(request_url).path.lstrip('/')
                candidate=(SITE/rel).resolve()
                if SITE.resolve() in candidate.parents and candidate.is_file():
                    case['intercepted'].append(rel)
                    r.fulfill(status=200,content_type=mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream',body=candidate.read_bytes());return
                case['continued_child_requests'].append(rel)
                r.continue_();return
            if request_url.startswith(BASE+'/'):
                r.continue_();return
            r.abort()
        context.route('**/*',route)
        page=context.new_page()
        def console(msg):
            if msg.type=='error':
                errors.append({'text':msg.text,'source_url':(msg.location or {}).get('url') or None})
        def pageerror(error):
            case['page_errors'].append(str(error))
            errors.append({'text':'pageerror: '+str(error),'source_url':None})
        def response(res):
            if res.status>=400:
                failed.append({'url':res.url,'status':res.status})
        def finished(req):
            try:counters['bytes']+=int(req.sizes().get('responseBodySize') or 0)
            except Exception:pass
        page.on('console',console);page.on('pageerror',pageerror);page.on('response',response)
        page.on('request',lambda req:counters.__setitem__('requests',counters['requests']+1))
        page.on('requestfinished',finished)
        try:
            res=page.goto(url,wait_until='domcontentloaded',timeout=int(timeout_s*1000))
            assert res and res.ok, 'top-level load failed'
            page.wait_for_function("document.querySelector('main[data-shared-shell-phase]')?.dataset.sharedShellPhase==='ready'",timeout=45000)
            child=page.locator('iframe[data-shared-shell-frame]').element_handle().content_frame()
            assert child
            child.wait_for_function("typeof SectorCyclesEvidence==='function' && SectorCyclesEvidence().status==='verified'",timeout=40000)
            child.wait_for_function("SectorCyclesCapture()?.focus==='801010' && document.querySelector('.si-view[data-view=map]')?.classList.contains('on')",timeout=20000)
            actual=page.evaluate("({theme:document.documentElement.dataset.theme,locale:document.documentElement.dataset.lang})")
            if actual['theme']!=cell.theme:
                expected=('浅色主题' if cell.theme=='light' else '深色主题') if actual['locale']=='zh' else ('Light theme' if cell.theme=='light' else 'Dark theme')
                case['theme_control']=expected
                page.get_by_role('button',name=expected,exact=True).filter(visible=True).click()
            page.wait_for_function("(s)=>document.documentElement.dataset.theme===s.theme&&document.documentElement.dataset.lang===s.locale",arg=state,timeout=15000)
            child.wait_for_function("(s)=>document.documentElement.dataset.theme===s.theme&&document.documentElement.dataset.lang===s.locale",arg=state,timeout=15000)
            child.evaluate(cpe._APPLY_STATE_SCRIPT.strip(),state)
            cpe._wait_transient_fx_gone(child)
            child.evaluate("document.fonts.ready")
            page.wait_for_timeout(self.settle_ms)
            if cell.width>=881:
                child.locator('#sc-detail').evaluate("el=>el.scrollIntoView({block:'start',inline:'nearest'})")
            else:
                child.locator('#sc-chart').scroll_into_view_if_needed()
            applied_force=None
            if cell.force_state is not None:
                applied_force=cpe._apply_interaction_force(child,cell.force_state,timeout_ms=5000)
                assert applied_force==cell.force_state.name, 'hover was not applied'
                page.wait_for_timeout(self.settle_ms)
            facts=child.evaluate("""()=>({meta:{region:SECTOR_CYCLES.meta.region,asOf:SECTOR_CYCLES.meta.asOf,benchmark:SECTOR_CYCLES.meta.benchmark},
                publication:SectorCyclesEvidence(),capture:SectorCyclesCapture(),sectorCount:SECTOR_CYCLES.sectors.length,basketCount:SECTOR_CYCLES.baskets.length,
                mapVisible:document.querySelector('.si-view[data-view=map]').classList.contains('on'),
                theme:document.documentElement.dataset.theme,locale:document.documentElement.dataset.lang,
                sheetClass:document.querySelector('#sc-detail').className,
                sheetBackground:getComputedStyle(document.querySelector('#sc-detail')).backgroundColor,
                railBackground:getComputedStyle(document.querySelector('.si-side')).backgroundColor,
                closeHidden:!!document.querySelector('.sc-sheet-x')?.closest('[aria-hidden="true"]')})""")
            assert facts['meta']=={'region':'china','asOf':'2026-11-03','benchmark':'SHCOMP'}
            assert facts['capture']['focus']=='801010' and facts['mapVisible']
            assert facts['sectorCount']==31 and facts['basketCount']==22
            assert facts['theme']==cell.theme and facts['locale']==cell.locale
            if cell.width<881:assert not facts['closeHidden'],'close button hidden from accessibility tree'
            if cell.width>=881:
                case['detail_rect']=child.locator('#sc-detail').evaluate("el=>({top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom,viewport:innerHeight})")
                assert case['detail_rect']['top']>=-2 and case['detail_rect']['top']<case['detail_rect']['viewport']-100,'selected detail is outside the evidence viewport'
            case['child']=facts
            case['host']=page.evaluate("({theme:document.documentElement.dataset.theme,locale:document.documentElement.dataset.lang,width:innerWidth,documentWidth:document.documentElement.scrollWidth})")
            observed=child.evaluate(cpe._OBSERVER_SCRIPT.strip(),self.observer_config) or {}
            timing=child.evaluate(cpe._TIMING_SNAPSHOT_SCRIPT.strip()) or None
            screenshot=page.screenshot(full_page=True)
            case['screenshot_sha256']=hashlib.sha256(screenshot).hexdigest()
            case['loaded']=True;case['applied_force_state']=applied_force
            return cpe.CellObservation(cell_id=cell.cell_id,loaded=True,screenshot_png=screenshot,
                observed=observed,console_errors=tuple(errors),failed_responses=tuple(failed),
                request_count=counters['requests'],payload_bytes_total=counters['bytes'],
                applied_theme=facts['theme'],applied_locale=facts['locale'],
                applied_force_state=applied_force,timing=timing)
        except Exception as exc:
            case['loaded']=False;case['error']=type(exc).__name__+': '+str(exc)
            case['trace']=traceback.format_exc()
            return cpe.CellObservation(cell_id=cell.cell_id,loaded=False,error=case['error'],
                console_errors=tuple(errors),failed_responses=tuple(failed),
                request_count=counters['requests'],payload_bytes_total=counters['bytes'])
        finally:
            case['console_errors']=errors;case['failed_responses']=failed;case['counts']=counters
            LEDGER.append(case)
            (OUT/'driver_observations.json').write_text(json.dumps(LEDGER,indent=2,ensure_ascii=False)+'\n')
            print(json.dumps({'cell':cell.cell_id,'loaded':case.get('loaded'),'error':case.get('error'),'page_errors':case['page_errors'],'failed_responses':len(failed)}),flush=True)
            context.close()

    def close(self):
        self.browser.close()
        self.manager.stop()

if __name__=='__main__':
    os.chdir(ROOT)
    code=cpe.main(['--base-url',BASE,'--routes','/sector_central_china.html#801010',
        '--viewports','desktop,mobile','--locales','en,zh','--themes','dark,light','--max-pages','1',
        '--settle-ms','700','--timeout-s','60',
        '--force-state','rail_hover:hover(.si-view-btn[data-view="overview"])',
        '--output-dir','mockups/evidence/d05-china-central-20261105',
        '--manifest','mockups/evidence/d05-china-central-20261105/manifest.json',
        '--smells','mockups/evidence/d05-china-central-20261105/smells.json',
        '--emit-md','mockups/evidence/d05-china-central-20261105/smells.md'],
        driver_factory=ChinaFrameDriver)
    raise SystemExit(code)
