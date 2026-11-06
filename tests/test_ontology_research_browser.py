"""Synthetic browser checks for the explicit captured-event research read."""
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from tests.test_ontology_explorer_brain_browser import browser

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'Content-Type': 'application/json', 'Cache-Control': 'private, no-store',
           'Vary': 'Authorization, Cookie'}


def packet():
    identity = {'date': '2026-01-02', 'ticker': 'TEST', 'side': 'down'}
    stamp = '2026-01-03T10:00:00Z'
    return {'schema': 'ontology_drl_research.v1', 'capture': {
        'schema': 'price_pressure.captured_event.v1', 'native_identity': identity,
        'source': {'artifact': 'data/price_pressure/latest.json', 'schema': 'price_pressure.v1',
                   'snapshot_sha256': 'a'*64, 'generated_utc': '2026-01-03T09:00:00Z'},
        'capture': {'captured_at': stamp, 'clock_class': 'system_recorded',
                    'historical_availability': 'unknown', 'scope': 'retrospective_captured_read'},
        'native': {'ret': .003, 'peer_ret': .013, 'resid': -.01, 'resid_z': -3,
                   'peer_basis': 'market', 'edgar_covered': False, 'family': 'filing-coverage-unknown'},
        'authority': dict.fromkeys(['can_rank','can_size','can_gate','can_originate_signal','can_escalate'], False)},
        'case': {'schema': 'opportunity_case.research.v1', 'case_id': 'opc_'+'b'*64,
                 'content_sha256': 'c'*64, 'research_state': 'partial',
                 'evidence_binding': {'state': 'exact_owner_native_event', 'scope': 'single_owner_event'},
                 'asof': {'value': stamp, 'grain':'datetime', 't0_source':'drl_captured_read',
                          't0_mode':'retrospective_research', 't0_evidence_ref': {
                              'owner_store':'price_pressure.event', 'native_identity':identity,
                              'native_digest':{'state':'known','sha256':'a'*64},
                              'recorded_clock':{'value':stamp}}},
                 'calibrated':{'state':'unavailable', 'opportunity_score':None,'confidence':None,'probability':None,'impact':None},
                 **{k:{'state':'unavailable'} for k in ['transmission','company_context','valuation_context','path_timing','portfolio_intersection']},
                 'authority':dict.fromkeys(['can_rank','can_gate','can_size','can_originate','can_open_entry'],False)}}


def start(browser, *, value=None, status=200, headers=None, search=''):
    context = browser.new_context()
    page = context.new_page()
    seen, errors = [], []
    shell = (ROOT/'site/ontology.html').read_text()
    # The actual public shell and module; existing siblings are not under test.
    auth = '''<script>window.owner='owner-a';window.token='fixture-token';window.callbacks=[];
    window.sdk={auth:{getSession:async()=>({data:{session:{user:{id:owner},access_token:token}}}),
    onAuthStateChange:fn=>{callbacks.push(fn);return{data:{subscription:{unsubscribe(){}}}};}}};
    window.MDXAuth={user:()=>owner?({id:owner}):null,client:async()=>sdk};</script>'''
    shell = shell.replace('<head>', '<head>'+auth)
    def route(r):
        path=urlsplit(r.request.url).path
        if path=='/ontology.html': r.fulfill(status=200,content_type='text/html',body=shell)
        elif path=='/api/ontology/explorer/research/v1':
            seen.append({'payload':json.loads(r.request.post_data),'headers':r.request.headers})
            r.fulfill(status=status,headers=headers or HEADERS,body=json.dumps(value if value is not None else packet()))
        elif path=='/ontology-research.js' or path.endswith('.css') or '/fonts/' in path:
            source=ROOT/'site'/path.lstrip('/')
            if source.is_file(): r.fulfill(status=200,body=source.read_bytes(),content_type='text/javascript' if path.endswith('.js') else 'text/css' if path.endswith('.css') else 'font/woff2')
            else:r.fulfill(status=404)
        else:r.fulfill(status=204)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/*',route);page.goto('https://macro.example/ontology.html'+search)
    if not page.locator('#ox-research').evaluate('(root)=>root.open'):
        page.locator('#ox-research summary').click()
    page.wait_for_function("document.querySelector('[data-research-result]').dataset.state==='idle'")
    return context,page,seen,errors


def inspect(page):
    page.locator('#ox-research [name=date]').fill('2026-01-02')
    page.locator('#ox-research [name=ticker]').fill('test')
    page.locator('#ox-research button[type=submit]').click()


def settled(page,state):
    page.wait_for_function("s=>document.querySelector('[data-research-result]').dataset.state===s",arg=state)


def test_pressure_watch_handoff_prefills_only_until_explicit_submit(browser):
    from engine.stocks_hub import pressure_band
    row = {'date':'2026-01-02','ticker':'TEST','side':'down'}
    band = pressure_band({'asof':'2026-01-03','open_events':[row]})
    href = band['open'][0]['research_href']
    assert band['open'][0]['href'] == 'TEST.html'
    context,page,seen,errors=start(browser,search='?'+urlsplit(href).query+'#ox-research')
    try:
        assert page.locator('[name=date]').input_value() == row['date']
        assert page.locator('[name=ticker]').input_value() == row['ticker']
        assert page.locator('[name=side]').input_value() == row['side']
        assert seen == []
        page.locator('#ox-research button[type=submit]').click()
        settled(page,'ready')
        assert len(seen) == 1
        assert seen[0]['payload'] == {'schema':'ontology_drl_research_request.v1',**row}
        assert 'historical availability' in page.locator('[data-research-result]').inner_text().lower()
        assert not errors
    finally:context.close()


@pytest.mark.parametrize('query',[
    'research_date=2026-01-02&research_ticker=TEST',
    'research_ticker=TEST&research_side=down',
    'research_date=2026-01-02&research_side=down',
    'research_date=2026-02-30&research_ticker=TEST&research_side=down',
    'research_date=0000-01-02&research_ticker=TEST&research_side=down',
    'research_date=2026-01-02&research_ticker=test&research_side=down',
    'research_date=2026-01-02&research_ticker=TEST&research_side=unknown',
    *['research_date=2026-01-02&research_ticker=TEST&research_side=down&'+extra
      for extra in ['research_date=2026-01-03','research_ticker=OTHER','research_side=up',
                    'research_generation=claimed','research_asof=2026-01-02']],
    'research_date=2026-01-02&research_ticker=%ZZ&research_side=down',
])
def test_pressure_watch_invalid_handoff_never_prefills_or_requests(browser,query):
    context,page,seen,errors=start(browser,search='?'+query+'#ox-research')
    try:
        assert page.locator('[name=date]').input_value() == ''
        assert page.locator('[name=ticker]').input_value() == ''
        assert seen == [] and not errors
    finally:context.close()


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('lang',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_research_case_private_native_read_and_clear(browser,theme,lang,width):
    context,page,seen,errors=start(browser)
    try:
        page.set_viewport_size({'width':width,'height':900})
        page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l;document.dispatchEvent(new Event('langchange'))}",[theme,lang])
        assert seen==[]
        assert page.locator('[name=side] option:checked').inner_text()==('负残差' if lang=='zh' else 'Negative residual')
        inspect(page);settled(page,'ready')
        assert len(seen)==1 and seen[0]['headers']['authorization']=='Bearer fixture-token'
        assert seen[0]['payload']=={'schema':'ontology_drl_research_request.v1','date':'2026-01-02','ticker':'TEST','side':'down'}
        text=page.locator('[data-research-result]').inner_text()
        assert '+0.30%' in text and '+1.30%' in text and '-1.00%' in text
        assert ('the market' if lang=='en' else '市场') in text
        assert ('historical availability' in text.lower()) if lang=='en' else '历史可用性' in text
        assert page.evaluate('[localStorage.length,sessionStorage.length]')==[0,0]
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.evaluate("window.owner=null;callbacks.forEach(f=>f('SIGNED_OUT',null));window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null}}))")
        settled(page,'idle');assert '0.30%' not in page.locator('[data-research-result]').inner_text()
        assert len(seen)==1 and not errors
    finally:context.close()


@pytest.mark.parametrize('status,state',[(401,'signed_out'),(403,'forbidden'),(404,'not_found'),(503,'unavailable')])
def test_research_refusals_never_keep_a_value(browser,status,state):
    context,page,seen,errors=start(browser,status=status,value={'detail':{'code':'unavailable'}})
    try:inspect(page);settled(page,state);assert not page.locator('[data-research-result] dl').count();assert len(seen)==1
    finally:context.close()


@pytest.mark.parametrize('mutation',['selection','snapshot','clock','authority','context','headers'])
def test_research_mismatched_receipts_are_refused(browser,mutation):
    value=deepcopy(packet());headers=dict(HEADERS)
    if mutation=='selection':value['capture']['native_identity']['ticker']='OTHER'
    elif mutation=='snapshot':value['case']['asof']['t0_evidence_ref']['native_digest']['sha256']='d'*64
    elif mutation=='clock':value['capture']['capture']['historical_availability']='known'
    elif mutation=='authority':value['case']['authority']['can_open_entry']=True
    elif mutation=='context':value['case']['company_context']['state']='available'
    else:headers['Cache-Control']='public'
    context,page,seen,errors=start(browser,value=value,headers=headers)
    try:inspect(page);settled(page,'unavailable');assert not page.locator('[data-research-result] dl').count()
    finally:context.close()


def test_research_delayed_read_is_discarded_when_selection_changes(browser):
    context,page,seen,errors=start(browser)
    try:
        page.evaluate("() => {window.savedFetch=window.fetch;window.fetch=(...args)=>new Promise((resolve,reject)=>{window.deliver=()=>{void savedFetch(...args).then(resolve,reject);};});}")
        inspect(page);settled(page,'loading')
        page.wait_for_function('typeof deliver===\"function\"')
        page.locator('#ox-research [name=ticker]').fill('OTHER');settled(page,'idle')
        page.evaluate('() => { deliver(); }');page.wait_for_timeout(100)
        assert page.locator('[data-research-result]').get_attribute('data-state')=='idle'
        assert '0.30%' not in page.locator('[data-research-result]').inner_text()
    finally:context.close()


@pytest.mark.parametrize('status,final_call', [(200, 3), (404, 2)])
def test_research_final_session_switch_cannot_render(browser, status, final_call):
    context, page, seen, errors = start(browser, status=status)
    try:
        page.evaluate("""last => {
          let calls=0;
          sdk.auth.getSession=()=>{
            const result={data:{session:{user:{id:owner},access_token:token}}};
            if(++calls===last)return new Promise(resolve=>{
              resolve(result);queueMicrotask(()=>queueMicrotask(()=>{
                window.owner='owner-b';callbacks.forEach(f=>f('SIGNED_IN',{user:{id:owner}}));
                window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner}}}));
              }));
            });return Promise.resolve(result);
          };
        }""", final_call)
        inspect(page)
        page.wait_for_function("window.owner==='owner-b'")
        settled(page, 'idle')
        assert '0.30%' not in page.locator('[data-research-result]').inner_text()
        assert not page.locator('[data-research-result] dl').count()
        assert len(seen)==1 and not errors
    finally: context.close()


@pytest.mark.parametrize('width', [390, 1440])
@pytest.mark.parametrize('theme', ['dark', 'light'])
@pytest.mark.parametrize('language', ['en', 'zh'])
def test_pressure_watch_research_action_uses_full_row_measure(browser, width, theme, language):
    """The continuation must not inherit the ticker's 56px grid track."""
    import re
    from jinja2 import Environment

    template = (ROOT/'templates/ticker_index.html.j2').read_text()
    macro = template[:template.index('{% set nav_prefix')]
    section = template[template.index('{%- if P.open %}'):template.index('{#- One footnote')]
    pressure = Environment(autoescape=True).from_string(macro + section).render(P={
        'open': [{'href': 'CZR.html', 't': 'CZR', 'move_en': 'fell 0.2%',
                  'move_zh': '下跌 0.2%', 'cmp_en': '', 'fam_en': '', 'state_en': '',
                  'research_href': '../ontology.html?research_date=2026-10-15&research_ticker=CZR&research_side=down#ox-research'}],
        'count_en': 'one event', 'count_zh': '一个事件', 'demoted': False,
    })
    css = re.search(r'<style>(.*?)</style>', template, re.S).group(1)
    context = browser.new_context(viewport={'width': width, 'height': 900})
    page = context.new_page()
    requests = []
    page.route('**/*', lambda route: (requests.append(route.request.url), route.abort()))
    try:
        page.set_content(f'<html data-theme="{theme}" data-lang="{language}"><head><style>'
                         + (ROOT/'templates/theme.css').read_text() + css
                         + '</style></head><body><section class="pw">' + pressure + '</section></body></html>')
        geometry = page.locator('.pw-research-action').evaluate('''note => {
          const row = note.previousElementSibling, grid = note.parentElement;
          const n = note.getBoundingClientRect(), r = row.getBoundingClientRect();
          const a = note.querySelector('a'), label = a.querySelector(document.documentElement.dataset.lang === 'zh' ? '.l-zh' : '.l-en');
          const rects = [...label.getClientRects()].filter(x => x.width && x.height);
          return {width:n.width, gridWidth:grid.getBoundingClientRect().width,
            below:n.top >= r.bottom, overflow:document.documentElement.scrollWidth > innerWidth,
            spans:getComputedStyle(note).gridColumn, dossier:row.getAttribute('href'),
            href:a.getAttribute('href'), nested:!!a.parentElement.closest('a'),
            fragments:rects.length, hit:rects.every(x => a.contains(document.elementFromPoint(x.x+x.width/2,x.y+x.height/2)))};
        }''')
        assert geometry['width'] > 112 and geometry['below'] and not geometry['overflow']
        assert geometry['spans'] == '1 / -1' and geometry['fragments'] <= 2 and geometry['hit']
        assert geometry['dossier'] == 'CZR.html' and not geometry['nested']
        assert geometry['href'] == '../ontology.html?research_date=2026-10-15&research_ticker=CZR&research_side=down#ox-research'
        assert all('/api/' not in url for url in requests)
    finally:
        context.close()
