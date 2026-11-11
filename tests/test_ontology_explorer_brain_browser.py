"""Browser contract for the R23/R24 selected-path Brain handoff.

Every owner value in this test is synthetic. The test exercises the current
``templates/ontology.js`` and ``templates/ontology.css`` against a snapshot
composed by the real read-only ontology composer, then uses a tiny local Brain
loader stub only to observe the page-owned handoff. The shared Brain bundle's
close/fallback behavior is pinned separately in ``test_mm_brain_asset.py``.

The DOM-measured test skips cleanly when Playwright/Chromium is unavailable.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engine.ontology_explorer import compose_snapshot
from tests.ontology_explorer_fixtures import build_root, chain_state

# Invented observations exercise an admitted product identity, never a live read.
SLUG = 'oil_inflation_duration_derate'


def _scenario_browser(browser, *, qualified=False, mutate=None, status=200):
    """Actual pure evaluator + synthetic, intercepted private transport only."""
    from engine.ontology_scenario import evaluate_scenario, parse_assumption
    from tests.test_ontology_explorer_contract import x2_inputs
    snapshot, chain, baseline, _ = x2_inputs.__wrapped__()
    reading = {**snapshot['source'], 'owner_id': 'owner-a', 'composer_method': 'ontology_explorer.v1'}
    snapshot['source']['composer_method'] = reading['composer_method']
    ctx = browser.new_context()
    page = ctx.new_page()
    seen, errors = [], []
    shell = '''<!doctype html><html data-lang="en"><body>
    <section id="ox-scenario"><form data-scenario-form></form><div data-scenario-result></div></section>
    <script>
    window.owner='owner-a';window.token='fixture-token';window.callbacks=[];window.calls=0;
    window.sdk={auth:{getSession:async()=>window.sessionHook?sessionHook():({data:{session:{user:{id:owner},access_token:token}}}),
      onAuthStateChange:fn=>{callbacks.push(fn);return{data:{subscription:{unsubscribe(){}}}};}}};
    window.MDXAuth={user:()=>owner?({id:owner}):null,client:async()=>sdk};
    const nativeFetch=window.fetch;window.fetch=(...args)=>{calls++;return nativeFetch(...args);};
    </script><script type="module">import * as scenario from '/ontology-scenario.js';window.scenario=scenario;</script>
    </body></html>'''
    def route(r):
        path = r.request.url.split('macro.example')[-1]
        if path == '/ontology.html': r.fulfill(status=200, content_type='text/html', body=shell)
        elif path == '/ontology-scenario.js':
            r.fulfill(status=200, content_type='text/javascript', body=(ROOT/'templates/ontology-scenario.js').read_text())
        elif path == '/api/ontology/explorer/scenario/v1':
            payload = json.loads(r.request.post_data); seen.append({'payload': payload, 'url': r.request.url, 'method': r.request.method})
            assumption = parse_assumption(json.dumps(payload['assumption']).encode())
            refusal = None
            if not qualified:
                from engine.ontology_scenario_runtime import _load_native_baseline, NativeScenarioInputsUnavailable
                try: _load_native_baseline(ROOT, snapshot, assumption)
                except NativeScenarioInputsUnavailable as exc:
                    refusal = {'reason': exc.reason, 'missing_owner_inputs': list(exc.missing)}
            value = evaluate_scenario(assumption, snapshot=snapshot, chain=chain,
              baseline=baseline if qualified else None, evaluated_at=baseline.knowledge_cutoff,
              owner_refusal=refusal)
            if mutate: value = mutate(value)
            if status != 200: value = {'detail': {'schema':'ontology_explorer_error.v1','code':'source_changed' if status == 409 else 'source_unavailable'}}
            r.fulfill(status=status, headers={'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'},body=json.dumps(value))
        else: r.fulfill(status=204)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/*', route); page.goto('https://macro.example/ontology.html')
    page.wait_for_function('!!window.scenario')
    page.evaluate("r=>document.getElementById('ox-scenario').dispatchEvent(new CustomEvent('ontology-reading',{detail:r}))", reading)
    page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='idle'")
    return ctx, page, seen, errors, reading


def _scenario_submit(page, magnitude=30, shape='terminal_only'):
    page.locator('[name=magnitude]').fill(str(magnitude)); page.locator('[name=shape]').select_option(shape)
    page.locator('[type=submit]').click()


@pytest.mark.parametrize('qualified,magnitude,shape,expected', [
    (False, 30, 'linear_sessions', 'Evaluation unavailable'),
    (True, 20, 'terminal_only', 'Root threshold is not armed'),
    (True, 30, 'terminal_only', 'Endpoint condition met; path condition unknown'),
    (True, 30, 'linear_sessions', 'Assumed root threshold met'),
    (True, 30, 'step_at_start', 'Root threshold is not armed'),
])
def test_x2_browser_explicit_native_threshold_and_truthful_unavailable(browser, qualified, magnitude, shape, expected):
    ctx, page, seen, errors, _ = _scenario_browser(browser, qualified=qualified)
    try:
        assert seen == [] and page.evaluate('calls') == 0
        _scenario_submit(page, magnitude, shape)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='ready'")
        output = page.locator('[data-scenario-result]').inner_text()
        assert expected in output and 'Downstream effects remain unknown' in output
        assert len(seen) == 1 and seen[0]['method'] == 'POST' and '?' not in seen[0]['url']
        assert set(seen[0]['payload']) == {'schema', 'source_manifest_hash', 'assumption'}
        assert page.evaluate('[localStorage.length, sessionStorage.length]') == [0, 0]
        assert not errors
        page.locator('[name=magnitude]').fill('31')
        assert page.locator('[data-scenario-result]').get_attribute('data-state') == 'idle'
        assert 'Downstream effects' not in page.locator('[data-scenario-result]').inner_text()
        assert len(seen) == 1
    finally: ctx.close()


@pytest.mark.parametrize('change', [
    "owner=null;window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}));",
    "owner='owner-b';window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner}}}));",
    "document.querySelector('[name=magnitude]').value='31';document.querySelector('[name=magnitude]').dispatchEvent(new Event('input',{bubbles:true}));",
    "document.getElementById('ox-scenario').dispatchEvent(new CustomEvent('ontology-source-changed'));",
    "window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));",
    "Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));",
    "token='changed';callbacks.forEach(fn=>fn('TOKEN_REFRESHED',{user:{id:owner}}));",
])
def test_x2_browser_late_response_cannot_publish_after_input_auth_or_lifecycle_change(browser, change):
    ctx, page, seen, errors, _ = _scenario_browser(browser, qualified=True)
    try:
        page.evaluate("""()=>{const original=fetch;fetch=(...a)=>original(...a).then(response=>new Promise(resolve=>window.finishScenario=()=>resolve(response)));}""")
        _scenario_submit(page)
        page.wait_for_function('typeof finishScenario === "function"')
        page.evaluate(change); page.evaluate('finishScenario()')
        page.evaluate('()=>new Promise(r=>setTimeout(r,20))')
        assert page.locator('[data-scenario-result]').get_attribute('data-state') != 'ready'
        assert 'Endpoint condition' not in page.locator('[data-scenario-result]').inner_text()
        assert len(seen) == 1 and not errors
    finally: ctx.close()


@pytest.mark.parametrize('path,value', [
    (['schema'], 'wrong'), (['assumption','magnitude'], 999), (['assumption','node_ref'], 'wrong'),
    (['assumption','path_shape'], 'wrong'), (['assumption','baseline_effective_at'], '1900-01-01'),
    (['assumption','baseline_knowledge_cutoff'], '1900-01-01T00:00:00Z'),
    (['authority','can_trade'], True), (['combined_estimate'], 42), (['snapshot_id'], 'sha256:'+'f'*64),
    (['side_effect_receipt','owner_writes'], 1),
    (['method_versions'], None),
])
def test_x2_browser_refuses_unbound_echo_authority_and_combined_response(browser, path, value):
    def mutate(reply):
        cursor = reply
        for key in path[:-1]: cursor = cursor[key]
        cursor[path[-1]] = value
        return reply
    ctx, page, seen, errors, _ = _scenario_browser(browser, qualified=True, mutate=mutate)
    try:
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='unavailable'")
        assert 'Endpoint condition' not in page.locator('[data-scenario-result]').inner_text()
        assert len(seen) == 1 and not errors
    finally: ctx.close()


def test_x2_browser_source_change_is_closed_and_missed_signout_event_stays_closed(browser):
    ctx, page, seen, errors, reading = _scenario_browser(browser, status=409)
    try:
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='changed'")
        assert page.locator('[name=magnitude]').input_value() == ''
        assert page.locator('[type=submit]').is_disabled()
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
        # Canonical event says signed out even if stale SDK and user() still say A.
        page.evaluate("r=>document.getElementById('ox-scenario').dispatchEvent(new CustomEvent('ontology-reading',{detail:r}))", reading)
        assert page.locator('[type=submit]').is_disabled() and len(seen) == 1 and not errors
    finally: ctx.close()


def test_x2_browser_final_session_is_checked(browser):
    ctx, page, seen, errors, _ = _scenario_browser(browser, qualified=True)
    try:
        page.evaluate("""()=>{const original=fetch;fetch=async(...a)=>{const r=await original(...a);window.replied=true;return r;};
          sessionHook=async()=>{if(window.replied)owner=null;return{data:{session:{user:{id:'owner-a'},access_token:token}}};};}""")
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='signed_out'")
        assert 'Endpoint condition' not in page.locator('[data-scenario-result]').inner_text() and not errors
        assert page.locator('[name=magnitude]').input_value() == '' and page.locator('[type=submit]').is_disabled()
    finally: ctx.close()


@pytest.mark.parametrize('phase', ['digest', 'body'])
def test_x2_browser_late_digest_and_body_continuations_remain_private(browser, phase):
    ctx, page, seen, errors, _ = _scenario_browser(browser, qualified=True)
    try:
        if phase == 'digest':
            page.evaluate("""()=>{const digest=crypto.subtle.digest.bind(crypto.subtle);
              crypto.subtle.digest=(...a)=>digest(...a).then(value=>new Promise(resolve=>window.finishPrivate=()=>resolve(value)));}""")
        else:
            page.evaluate("""()=>{const original=fetch;fetch=async(...a)=>{const r=await original(...a);const reader=r.body.getReader();
              return{status:r.status,headers:r.headers,redirected:false,body:{getReader:()=>({
                read:()=>reader.read().then(value=>new Promise(resolve=>window.finishPrivate=()=>resolve(value))),
                cancel:()=>Promise.resolve(),releaseLock:()=>{}})}};};}""")
        _scenario_submit(page)
        page.wait_for_function('typeof finishPrivate === "function"')
        page.evaluate("owner=null;window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}));finishPrivate();")
        page.evaluate('()=>new Promise(r=>setTimeout(r,20))')
        assert page.locator('[data-scenario-result]').get_attribute('data-state') != 'ready'
        assert page.locator('[name=magnitude]').input_value() == '' and not errors
        assert len(seen) == (0 if phase == 'digest' else 1)
    finally: ctx.close()


def test_x2_browser_response_byte_budget_is_checked(browser):
    ctx, page, seen, errors, _ = _scenario_browser(browser)
    try:
        page.evaluate("""()=>{fetch=async()=>new Response(new Uint8Array(262145),{status:200,headers:{'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'}});}""")
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='unavailable'")
        assert not errors
    finally: ctx.close()


def test_x2_browser_node_unit_change_requires_new_input_and_reports_actual_rates_gap(browser):
    ctx, page, seen, errors, _ = _scenario_browser(browser)
    try:
        page.locator('[name=magnitude]').fill('30')
        page.locator('[name=node]').select_option('transmission:real10y_chg63')
        assert page.locator('[name=magnitude]').input_value() == ''
        assert page.locator('[name=shape]').is_disabled()
        page.locator('[name=magnitude]').fill('50'); page.locator('[type=submit]').click()
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='ready'")
        assert 'estimation span, sample counts' in page.locator('[data-scenario-result]').inner_text()
        assumption = seen[0]['payload']['assumption']
        assert (assumption['unit'], assumption['horizon'], assumption['path_shape']) == ('bp', '63d', 'terminal_only')
        assert not errors
    finally: ctx.close()


def test_x2_browser_hanging_body_is_cancelled_at_operation_deadline(browser):
    ctx, page, seen, errors, _ = _scenario_browser(browser)
    try:
        page.evaluate("""()=>{const timer=setTimeout;window.setTimeout=(fn,ms,...a)=>timer(fn,ms===15000?20:ms,...a);
          fetch=async()=>new Response(new ReadableStream({cancel(){window.bodyCancelled=true;}}),{status:200,
            headers:{'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'}});}""")
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='unavailable'")
        assert page.evaluate('bodyCancelled') is True and not errors
    finally: ctx.close()


@pytest.mark.parametrize('change,state', [('other', 'signed_out'), ('token', 'idle')])
def test_x2_browser_sdk_only_account_or_token_change_clears_assumption(browser, change, state):
    ctx, page, seen, errors, _ = _scenario_browser(browser, qualified=True)
    try:
        page.evaluate("""change=>{const original=fetch;fetch=async(...a)=>{const r=await original(...a);window.replied=true;return r;};
          sessionHook=async()=>({data:{session:{user:{id:window.replied&&change==='other'?'owner-b':'owner-a'},
            access_token:window.replied&&change==='token'?'rotated':token}}});}""", change)
        _scenario_submit(page)
        page.wait_for_function("s=>document.querySelector('[data-scenario-result]').dataset.state===s", arg=state)
        assert page.locator('[name=magnitude]').input_value() == '' and not errors
        assert 'Endpoint condition' not in page.locator('[data-scenario-result]').inner_text()
        assert len(seen) == 1
    finally: ctx.close()

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JS = ROOT / "templates" / "ontology.js"
ONTOLOGY_CSS = ROOT / "templates" / "ontology.css"
THEME_CSS = ROOT / "site" / "theme.css"

SHELL = """<!doctype html>
<html lang="en" data-lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
  --bg:#F7F8FA;--panel:#FFFFFF;--panel-2:#EEF1F6;--text:#1C2430;
  --muted:#5D6B7E;--line:#C9CCD1;--up:#1F9A55;--down:#CF4040;
  --warn:#B9791A;--act:#C43D3D;--ok:#2F8A52;--info:#285FFF;
  --ink-link:#2758E6;--ink-info:#2758E6;--ink-warn:#7D5922;
  --font-ui:Inter,Arial,sans-serif;--font-mono:Menlo,monospace;
  --fs-micro:10px;--fs-label:11px;--fs-sm:12.5px;--fs-body:14px;
  --fs-h2:17px;--fs-h1:28px;--r-ctl:8px;--r-btn:10px;
  --card-shadow:0 8px 24px rgba(28,36,48,.08);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-ui)}
#mmb-boot{position:fixed;right:12px;bottom:12px;width:48px;height:48px}
</style>
</head>
<body>
  <script>
  window.currentOwner={id:'first'};
  window.MDXAuth={user:()=>window.currentOwner,client:async()=>({auth:{getSession:async()=>({data:{session:{user:window.currentOwner,access_token:'fixture-first'}}})}})};
  </script>
  <button id="mmb-boot" type="button">Brain</button>
  <main class="ox-wrap"><div id="ox-root" aria-busy="true"></div></main>
  <div id="mock-brain" tabindex="-1"></div>
</body>
</html>
"""


def _browser_unavailable(reason: str) -> None:
    if os.environ.get("MM_REQUIRE_BROWSER") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="module")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _browser_unavailable("Playwright not installed")
    manager = sync_playwright()
    try:
        playwright = manager.__enter__()
    except Exception as exc:  # pragma: no cover - runtime-specific
        _browser_unavailable(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            launched = playwright.chromium.launch(headless=True, channel="chrome")
        except Exception:
            launched = playwright.chromium.launch(headless=True)
    except Exception as exc:  # pragma: no cover - runtime-specific
        manager.__exit__(None, None, None)
        _browser_unavailable(f"Chromium unavailable: {exc}")
    yield launched
    launched.close()
    manager.__exit__(None, None, None)


@pytest.fixture()
def synthetic_snapshot(tmp_path: Path) -> dict:
    source_root = build_root(
        tmp_path,
        slug=SLUG,
        state_doc=chain_state(SLUG, confirmed=(False, False, True, True)),
    )
    return compose_snapshot(
        source_root,
        chain=SLUG,
        now=datetime(2026, 1, 4, tzinfo=UTC),
    )


def _open(
    browser,
    snapshot: dict,
    *,
    width: int,
    height: int,
    responses: list[dict] | None = None,
    reading_expected: bool = True,
    query: str = "",
):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        reduced_motion="reduce",
    )
    page = context.new_page()
    # Hermetic fixture: static source assets are local, never a network fallback.
    page.route("http://ontology.test/**", lambda route: route.abort())
    page.route("http://ontology.test/fonts/*", lambda route: route.fulfill(
        status=200, content_type="font/woff2",
        path=str(ROOT / "templates/fonts" / route.request.url.rsplit("/",1)[-1])))
    # The canonical theme imports the shared navigation-icon stylesheet.
    # Serve that real paired asset locally: an unresolved import causes Chromium
    # to reject add_style_tag before any product assertion can execute.
    page.route(
        "http://ontology.test/product-nav-icons.css*",
        lambda route: route.fulfill(
            status=200,
            content_type="text/css",
            path=str(ROOT / "site" / "product-nav-icons.css"),
        ),
    )
    page.route(
        "http://ontology.test/ontology.html*",
        lambda route: route.fulfill(status=200, content_type="text/html", body=SHELL),
    )
    page.goto("http://ontology.test/ontology.html" + query, wait_until="load")
    page.add_style_tag(path=str(THEME_CSS))
    page.add_style_tag(path=str(ONTOLOGY_CSS))
    page.evaluate(
        """config => {
          window.__brainBoots = 0;
          window.__brainOpens = 0;
          window.__fetchCount = 0;
          const queue = (config.responses || [{status: 200, body: config.snapshot}]).slice();
          window.__requestURLs = [];
          window.fetch = (url) => {
            window.__requestURLs.push(url);
            const item = queue[Math.min(window.__fetchCount, queue.length - 1)];
            window.__fetchCount += 1;
            return Promise.resolve({
              ok: item.status >= 200 && item.status < 300,
              status: item.status,
              json: () => Promise.resolve(item.body)
            });
          };
          document.getElementById('mmb-boot').addEventListener('click', () => {
            window.__brainBoots += 1;
            window.MMBrain = {
              mounted: true,
              open: () => { window.__brainOpens += 1; }
            };
            window.MMBrain.open();
          });
        }""",
        {"snapshot": snapshot, "responses": responses},
    )
    page.add_script_tag(path=str(ONTOLOGY_JS))
    if reading_expected and (responses is None or (responses and responses[0].get("status") == 200)):
        page.wait_for_selector("#ox-steps .ox-leg", state="attached")
        page.evaluate("document.getElementById('ox-steps').open = true")
        page.wait_for_selector("#ox-steps .ox-brain-action", state="visible")
    return context, page


@pytest.mark.parametrize('query',['?chain=', '?chain=unadmitted', '?chain=dollar_spike_em_multinational&chain=oil_inflation_duration_derate'])
def test_path_selection_refuses_invalid_queries_without_a_default_request(browser,synthetic_snapshot,query):
    ctx,page=_open(browser,synthetic_snapshot,width=390,height=844,query=query,reading_expected=False)
    try:
        assert 'This path is not available here' in page.locator('#ox-root').inner_text()
        assert page.evaluate('__requestURLs')==[]
        assert page.locator('#ox-steps').count()==0
    finally:ctx.close()


def test_explicit_dollar_selection_refuses_a_successful_reply_from_another_path(browser,synthetic_snapshot):
    ctx,page=_open(browser,synthetic_snapshot,width=390,height=844,query='?chain=dollar_spike_em_multinational',reading_expected=False)
    try:
        page.wait_for_function("document.querySelector('#ox-root').getAttribute('aria-busy')!=='true'")
        assert page.evaluate('__requestURLs')==['/api/ontology/explorer/v1?chain=dollar_spike_em_multinational']
        assert page.locator('#ox-steps').count()==0
    finally:ctx.close()


def test_default_oil_selection_refuses_a_successful_dollar_reply(browser,tmp_path):
    from tests.ontology_explorer_fixtures import dollar_root
    snapshot=compose_snapshot(dollar_root(tmp_path),chain='dollar_spike_em_multinational')
    ctx,page=_open(browser,snapshot,width=390,height=844,reading_expected=False)
    try:
        page.wait_for_function("document.querySelector('#ox-root').getAttribute('aria-busy')!=='true'")
        assert page.evaluate('__requestURLs')==['/api/ontology/explorer/v1']
        assert page.locator('#ox-steps').count()==0
    finally:ctx.close()


@pytest.mark.parametrize('language',['en','zh'])
def test_native_transition_references_keep_policy_limits_visible(browser,tmp_path,language):
    from tests.test_ontology_explorer_contract import _native_k1_transition
    root = build_root(tmp_path,slug=SLUG)
    (root/'data/transmission/chain_episodes.jsonl').write_text(json.dumps(_native_k1_transition(chain=SLUG,episode_id=SLUG+'@r2:2026-01-01'))+'\n')
    snapshot = compose_snapshot(root, chain=SLUG, now=datetime(2026,1,4,tzinfo=UTC))
    assert snapshot['evidence']['k1']['status']=='partial'
    context,page=_open(browser,snapshot,width=390,height=844)
    try:
        page.evaluate("lang=>document.documentElement.dataset.lang=lang",language)
        page.locator('#ox-root details').evaluate_all("nodes=>nodes.forEach(n=>n.open=true)")
        text=page.locator('#ox-root').inner_text()
        assert ('Bound transition references: 1' if language=='en' else '已绑定状态转换引用：1') in text
        assert ('not independent market evidence' if language=='en' else '并非独立市场证据') in text
        assert ('historical replay remain unavailable' if language=='en' else '历史回放仍不可用') in text
        assert snapshot['evidence']['k1']['refs'][0]['reference_id'] in text
        assert 'PRIVATE_BODY' not in text
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:context.close()


@pytest.mark.parametrize("size", ((1440, 900), (390, 844)))
def test_selected_leg_opens_existing_brain_with_bounded_context_and_exact_return(
    browser,
    synthetic_snapshot: dict,
    size: tuple[int, int],
) -> None:
    context, page = _open(
        browser,
        synthetic_snapshot,
        width=size[0],
        height=size[1],
    )
    try:
        asks = page.locator("#ox-steps .ox-brain-action")
        assert asks.count() == 4
        first = asks.first
        first.scroll_into_view_if_needed()
        box = first.bounding_box()
        assert box is not None and box["height"] >= 44
        if size[0] == 390:
            assert box["width"] >= 300

        first.click()
        handoff = page.evaluate(
            """() => ({
              boots: window.__brainBoots,
              opens: window.__brainOpens,
              hash: location.hash,
              ctx: window.MM_BRAIN_CFG.getAiContext()
            })"""
        )
        assert handoff["boots"] == 1
        assert handoff["opens"] == 1
        assert handoff["hash"] == "#ox-leg-n1"
        assert handoff["ctx"]["schema"] == "ai_context_client.v1"
        assert handoff["ctx"]["ambient"] == {
            "symbol": None,
            "timeframe": None,
            "page": "ontology",
            "panel": "n1",
        }
        assert handoff["ctx"]["pinned"] == []
        assert handoff["ctx"]["active"] is None

        return_scroll = page.evaluate("window.scrollY")
        returned = page.evaluate(
            """returnScroll => {
              window.scrollTo(0, 0);
              document.getElementById('mock-brain').focus();
              const ok = window.MM_BRAIN_CFG.onClose();
              return {
                ok,
                focused: document.activeElement.classList.contains('ox-brain-action'),
                scrollY: window.scrollY,
                cleared: window.MM_BRAIN_CFG.getAiContext().ambient
              };
            }""",
            return_scroll,
        )
        assert returned["ok"] is True
        assert returned["focused"] is True
        assert abs(returned["scrollY"] - return_scroll) <= 1
        assert returned["cleared"] == {
            "symbol": None,
            "timeframe": None,
            "page": "ontology",
            "panel": None,
        }

        metrics = page.evaluate(
            """() => ({
              scrollWidth: document.documentElement.scrollWidth,
              clientWidth: document.documentElement.clientWidth,
              ontologyStorageKeys: Object.keys(localStorage)
                .concat(Object.keys(sessionStorage))
                .filter(key => key.toLowerCase().includes('ontology'))
            })"""
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"]
        assert metrics["ontologyStorageKeys"] == []
    finally:
        context.close()


def test_mounted_brain_is_reused_without_clicking_the_lazy_loader(
    browser,
    synthetic_snapshot: dict,
) -> None:
    context, page = _open(browser, synthetic_snapshot, width=390, height=844)
    try:
        page.evaluate(
            """() => {
              window.__brainBoots = 0;
              window.__brainOpens = 0;
              window.MMBrain = {
                mounted: true,
                open: () => { window.__brainOpens += 1; }
              };
            }"""
        )
        first = page.locator("#ox-steps .ox-brain-action").first
        first.scroll_into_view_if_needed()
        first.click()
        counts = page.evaluate(
            "() => ({boots: window.__brainBoots, opens: window.__brainOpens})"
        )
        assert counts == {"boots": 0, "opens": 1}
    finally:
        context.close()


def test_answer_first_summary_and_primary_blocker_action(
    browser,
    synthetic_snapshot: dict,
) -> None:
    """R23/R24 put the answer, coverage and exact first blocker before depth."""
    for width, height in ((1440, 900), (390, 844)):
        context, page = _open(
            browser,
            synthetic_snapshot,
            width=width,
            height=height,
        )
        try:
            summary = page.locator(".ox-answer-summary")
            assert summary.is_visible()
            assert summary.locator(".ox-answer-count").inner_text().strip() == "2 / 4"
            assert "Node one" in summary.locator(".ox-answer-blocker").inner_text()
            assert "Downstream contradiction" in summary.locator(
                '[data-kind="contradiction"]'
            ).inner_text()
            assert "Comparison unavailable" in summary.locator(
                '[data-kind="comparison"]'
            ).inner_text()
            assert "Verification unavailable" in summary.locator(
                '[data-kind="verification"]'
            ).inner_text()

            action = page.locator(".ox-hero-action")
            action_box = action.bounding_box()
            assert action_box is not None and action_box["height"] >= 44
            if width == 390:
                assert action_box["width"] >= 300
            action.click()
            page.wait_for_function(
                "document.activeElement && document.activeElement.id === 'ox-leg-n1'"
            )
            assert page.locator("#ox-steps").get_attribute("open") is not None
            assert page.evaluate("location.hash") == "#ox-leg-n1"

            page.evaluate("document.documentElement.setAttribute('data-lang', 'zh')")
            assert "节点一" in summary.locator(".ox-answer-blocker").inner_text()
            metrics = page.evaluate(
                """() => ({
                  scrollWidth: document.documentElement.scrollWidth,
                  clientWidth: document.documentElement.clientWidth
                })"""
            )
            assert metrics["scrollWidth"] <= metrics["clientWidth"]
        finally:
            context.close()


@pytest.mark.parametrize(
    ("code", "expected"),
    (
        ("source_unavailable", "required owner source is unavailable"),
        ("source_incoherent", "current sources disagree"),
        ("internal_error", "cannot be safely shown"),
    ),
)
def test_typed_503_states_remain_distinct_and_retry_on_the_same_route(
    browser,
    synthetic_snapshot: dict,
    code: str,
    expected: str,
) -> None:
    context, page = _open(
        browser,
        synthetic_snapshot,
        width=390,
        height=844,
        responses=[
            {"status": 503, "body": {"detail": {"code": code, "reason": "fixture"}}},
            {"status": 200, "body": synthetic_snapshot},
        ],
    )
    try:
        gate = page.locator(f'.ox-gate[data-gate-code="{code}"]')
        gate.wait_for(state="visible")
        assert expected in gate.inner_text().lower()
        retry = gate.locator("button.ox-cta")
        box = retry.bounding_box()
        assert box is not None and box["height"] >= 44
        retry.click()
        page.wait_for_selector(".ox-answer-summary", state="visible")
        assert page.evaluate("window.__fetchCount") == 2
        assert page.locator(".ox-gate").count() == 0
    finally:
        context.close()


def test_unreadable_leg_is_not_collapsed_to_unresolved(
    browser,
    synthetic_snapshot: dict,
) -> None:
    import copy

    snapshot = copy.deepcopy(synthetic_snapshot)
    snapshot["path"]["legs"][1]["observation"] = "unreadable"
    snapshot["path"]["legs"][1]["confirmed"] = None
    context, page = _open(browser, snapshot, width=390, height=844)
    try:
        station = page.locator('.station[data-leg="unreadable"]')
        assert station.count() == 1
        assert "Reading unreadable" in station.locator(".st-verdict").inner_text()
    finally:
        context.close()


@pytest.mark.parametrize(
    ("width", "height", "zoom_contract"),
    (
        (1440, 900, "desktop"),
        (768, 1024, "tablet"),
        (390, 844, "mobile"),
        # A 1440px desktop at 200% browser zoom exposes roughly a 720 CSS-pixel
        # layout viewport. Reflow—not magnified horizontal scroll—is the contract.
        (720, 900, "desktop-200-percent"),
    ),
)
@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("lang", ("en", "zh"))
def test_r23_r24_cross_device_language_theme_and_focus_matrix(
    browser,
    synthetic_snapshot: dict,
    width: int,
    height: int,
    zoom_contract: str,
    theme: str,
    lang: str,
) -> None:
    """Accepted R23/R24 meaning survives reflow, locale, theme and keyboard use."""
    context, page = _open(browser, synthetic_snapshot, width=width, height=height)
    try:
        page.evaluate(
            """({theme, lang}) => {
              document.documentElement.setAttribute('data-theme', theme);
              document.documentElement.setAttribute('data-lang', lang);
            }""",
            {"theme": theme, "lang": lang},
        )
        summary = page.locator(".ox-answer-summary")
        action = page.locator(".ox-hero-action")
        assert summary.is_visible()
        assert action.is_visible()
        assert page.locator("#ox-root").get_attribute("aria-busy") == "false"

        expected_blocker = "节点一" if lang == "zh" else "Node one"
        assert expected_blocker in summary.locator(".ox-answer-blocker").inner_text()
        assert summary.locator(".ox-answer-count").inner_text().strip() == "2 / 4"

        metrics = page.evaluate(
            """() => {
              const action = document.querySelector('.ox-hero-action');
              const summary = document.querySelector('.ox-answer-summary');
              const actionBox = action.getBoundingClientRect();
              const summaryBox = summary.getBoundingClientRect();
              const pageStyle = getComputedStyle(document.body);
              return {
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
                actionHeight: actionBox.height,
                actionRight: actionBox.right,
                summaryRight: summaryBox.right,
                bodyBackground: pageStyle.backgroundColor,
                visibleEn: [...document.querySelectorAll('.l-en')]
                  .some(el => getComputedStyle(el).display !== 'none'),
                visibleZh: [...document.querySelectorAll('.l-zh')]
                  .some(el => getComputedStyle(el).display !== 'none')
              };
            }"""
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"]
        assert metrics["actionHeight"] >= 44
        assert metrics["actionRight"] <= metrics["clientWidth"] + 1
        assert metrics["summaryRight"] <= metrics["clientWidth"] + 1
        assert metrics["bodyBackground"] not in {"rgba(0, 0, 0, 0)", "transparent"}
        assert metrics["visibleZh"] is (lang == "zh")
        assert metrics["visibleEn"] is (lang == "en")

        action.focus()
        focus_style = action.evaluate(
            """el => {
              const style = getComputedStyle(el);
              return {outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth};
            }"""
        )
        assert focus_style["outlineStyle"] != "none"
        assert focus_style["outlineWidth"] != "0px"
        page.keyboard.press("Enter")
        page.wait_for_function(
            "document.activeElement && document.activeElement.id === 'ox-leg-n1'"
        )
        assert page.evaluate("location.hash") == "#ox-leg-n1"
        assert zoom_contract in {"desktop", "tablet", "mobile", "desktop-200-percent"}
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_primary_blocker_action_keeps_its_fill_and_contrast(browser, synthetic_snapshot, theme):
    """The generic action rule must not erase the Paper primary-action treatment."""
    context, page = _open(browser, synthetic_snapshot, width=390, height=844)
    try:
        page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
        action = page.locator(".ox-hero-action")
        for hover in (False, True):
            if hover:
                action.hover()
            measured = action.evaluate("""el => {
                const style = getComputedStyle(el);
                const sample = document.createElement('span');
                sample.style.backgroundColor = 'var(--info)';
                sample.style.color = 'var(--bg)';
                el.appendChild(sample);
                const expected = getComputedStyle(sample);
                const result = {
                    fill: style.backgroundColor, ink: style.color,
                    expectedFill: expected.backgroundColor, expectedInk: expected.color,
                    height: el.getBoundingClientRect().height
                };
                sample.remove();
                return result;
            }""")
            assert measured["fill"] == measured["expectedFill"]
            assert measured["ink"] == measured["expectedInk"]
            assert measured["height"] >= 44
    finally:
        context.close()


@pytest.mark.parametrize("body", (None, [], {}, {"schema": "unreviewed_snapshot.v9"}))
def test_invalid_success_body_settles_and_can_recover(browser, synthetic_snapshot, body):
    """HTTP 200 alone is not a readable snapshot or permission to keep loading."""
    context, page = _open(
        browser, synthetic_snapshot, width=390, height=844,
        responses=[{"status": 200, "body": body},
                   {"status": 200, "body": synthetic_snapshot}],
        reading_expected=False,
    )
    try:
        gate = page.locator('.ox-gate[data-gate-code="invalid_snapshot"]')
        gate.wait_for(state="visible", timeout=2500)
        assert page.locator("#ox-root").get_attribute("aria-busy") == "false"
        assert page.locator(".ox-answer-summary").count() == 0
        gate.locator("button.ox-cta").click()
        page.locator(".ox-answer-summary").wait_for(state="visible")
        assert page.evaluate("window.__fetchCount") == 2
        assert page.locator("#ox-root").get_attribute("aria-busy") == "false"
    finally:
        context.close()


@pytest.mark.parametrize("width", (1440, 390))
@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("lang", ("en", "zh"))
def test_answer_heading_leads_the_owner_summary(browser, synthetic_snapshot, width, theme, lang):
    """R23/R24 lead with the explanation, not an unexplained lifecycle label."""
    context, page = _open(browser, synthetic_snapshot, width=width, height=900)
    try:
        page.evaluate("v => {document.documentElement.dataset.theme=v.theme;document.documentElement.dataset.lang=v.lang}", {"theme": theme, "lang": lang})
        title = page.locator("h1.ox-answer-title")
        assert title.count() == 1
        assert title.is_visible()
        assert ("Node one" if lang == "en" else "节点一") in title.inner_text()
        layout = page.evaluate("""() => {
            const title = document.querySelector('.ox-answer-title');
            const state = document.querySelector('.ox-state-word');
            const lead = document.querySelector('.ox-hero-lead').getBoundingClientRect();
            const summary = document.querySelector('.ox-answer-summary').getBoundingClientRect();
            return {
                titleSize: parseFloat(getComputedStyle(title).fontSize),
                stateSize: parseFloat(getComputedStyle(state).fontSize),
                leadRight: lead.right, leadBottom: lead.bottom,
                summaryLeft: summary.left, summaryTop: summary.top,
                overflow: document.documentElement.scrollWidth > innerWidth
            };
        }""")
        assert layout["titleSize"] > layout["stateSize"]
        assert not layout["overflow"]
        if width == 1440:
            assert layout["leadRight"] <= layout["summaryLeft"]
        else:
            assert layout["leadBottom"] <= layout["summaryTop"]
    finally:
        context.close()


def test_shared_brain_turn_preserves_selected_revision_then_clears_it(browser, synthetic_snapshot):
    """Execute the real shared turn builder, not a consumer-only hand-authored context."""
    source = (ROOT / "templates" / "mm_brain.js").read_text(encoding="utf-8")
    start = source.index("  function buildTurnContext() {")
    end = source.index("\n  /* Review repair (NB-1)", start)
    turn_builder = source[start:end]
    context, page = _open(browser, synthetic_snapshot, width=390, height=844)
    try:
        page.locator("#ox-steps .ox-brain-action").first.click()
        run_builder = """() => {
            const CFG = window.MM_BRAIN_CFG;
            const ANCHOR = 'bottom';
            const ctxSymbol = null;
            const explainPanel = null;
            const zh = () => false;
            const buildAiContext = () => CFG.getAiContext();
        """ + turn_builder + "\nreturn buildTurnContext();}"
        payload = page.evaluate(run_builder)
        assert payload["page"] == "ontology"
        assert payload["panel"] == "n1"
        assert payload.get("timeframe") is None
        assert payload["ontology_selection"]["revision"] == 2
        assert payload["ontology_selection"]["manifest_hash"] == synthetic_snapshot["source"]["source_manifest_hash"]
        assert payload.get("timeframe") == payload["ai_context"]["ambient"]["timeframe"]
        page.evaluate("window.MM_BRAIN_CFG.onClose()")
        cleared = page.evaluate(run_builder)
        assert not cleared.get("panel")
        assert not cleared.get("timeframe")
    finally:
        context.close()


@pytest.mark.parametrize(
    "metric,value,threshold,passed,unit,verdict",
    [
        ("ret_pct", 6, 10, False, "%", "Not met"),
        ("ret_pct", 10, 10, False, "%", "Not met"),
        ("ret_bp", 0, 15, False, " bp", "Not met"),
        ("rs_pp", -3, 0, True, " pp", "Met"),
    ],
)
def test_receipt_separates_observation_requirement_and_owner_result(
    browser, synthetic_snapshot, metric, value, threshold, passed, unit, verdict
):
    """Never print a failed test as a true mathematical assertion like '6 > 10'."""
    import copy

    snapshot = copy.deepcopy(synthetic_snapshot)
    receipt = {"series": "SYN-N1", "metric": metric, "window": 60,
               "value": value, "op": "lt" if metric == "rs_pp" else "gt",
               "threshold": threshold, "passed": passed}
    snapshot["path"]["legs"][0]["receipts"] = [receipt]
    context, page = _open(browser, snapshot, width=390, height=844)
    try:
        text = page.locator("#ox-leg-n1 .ox-kv dd").inner_text()
        glyph = "<" if metric == "rs_pp" else ">"
        assert "Observed: " + str(value) + unit in text
        assert "Requires: " + glyph + " " + str(threshold) + unit in text
        assert verdict in text
        assert str(value) + " " + glyph + " " + str(threshold) not in text
        page.evaluate("document.documentElement.dataset.lang='zh'")
        chinese = page.locator("#ox-leg-n1 .ox-kv dd").inner_text()
        assert "读数：" in chinese and "要求：" in chinese
        assert ("已满足" if passed else "未满足") in chinese
    finally:
        context.close()


def test_required_browser_cannot_report_a_skip(monkeypatch):
    """The hosted ontology job must fail if its browser cannot actually run."""
    monkeypatch.setenv("MM_REQUIRE_BROWSER", "1")
    with pytest.raises(pytest.fail.Exception, match="Chromium unavailable"):
        _browser_unavailable("Chromium unavailable")
    monkeypatch.delenv("MM_REQUIRE_BROWSER")
    with pytest.raises(pytest.skip.Exception, match="Chromium unavailable"):
        _browser_unavailable("Chromium unavailable")


def test_selected_path_forwards_exact_evidence_reference_and_clears(browser, synthetic_snapshot):
    """No node-id rewriting, market bytes, or revision masquerading as timeframe."""
    import copy
    snapshot = copy.deepcopy(synthetic_snapshot)
    exact_node = "Oil-shock_long_name_01234567890123456789"
    snapshot["path"]["legs"][0]["node_id"] = exact_node
    context, page = _open(browser, snapshot, width=390, height=844)
    try:
        page.locator("#ox-steps .ox-brain-action").first.click()
        ref = page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()")
        assert ref == {"chain": snapshot["source"]["chain"],
                       "revision": snapshot["source"]["rev"],
                       "asof": snapshot["source"]["asof"],
                       "manifest_hash": snapshot["source"]["source_manifest_hash"],
                       "node_id": exact_node}
        assert page.evaluate("window.MM_BRAIN_CFG.getAiContext().ambient.timeframe") is None
        page.evaluate("window.MM_BRAIN_CFG.onClose()")
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is None
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "zh"))
def test_first_glance_is_short_without_losing_causal_warning(browser, synthetic_snapshot, lang):
    context, page = _open(browser, synthetic_snapshot, width=390, height=844)
    try:
        page.evaluate("lang => document.documentElement.dataset.lang=lang", lang)
        title = page.locator("h1.ox-answer-title").inner_text()
        assert title == ("Not running. First unmet condition: Node one." if lang == "en"
                         else "未运行。首个未满足条件：节点一。")
        # The causal caveat remains in the explanation, not deleted to shorten the heading.
        assert ("its own causes" if lang == "en" else "自身") in page.locator(".ox-answers").inner_text()
        metrics = page.locator(".ox-answer-metric")
        count_box, blocker_box = metrics.nth(0).bounding_box(), metrics.nth(1).bounding_box()
        assert abs(count_box["y"] - blocker_box["y"]) < 2
        assert count_box["x"] + count_box["width"] <= blocker_box["x"]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        context.close()


def test_chinese_first_blocker_name_does_not_split_at_the_heading_edge(browser, synthetic_snapshot):
    context, page = _open(browser, synthetic_snapshot, width=1440, height=900)
    try:
        page.evaluate("document.documentElement.dataset.lang='zh'")
        rects = page.locator('h1.ox-answer-title .l-zh').nth(1).evaluate('''node => {
            const range=document.createRange();range.selectNodeContents(node);
            return Array.from(range.getClientRects()).filter(rect=>rect.width>0).map(rect=>rect.top);
        }''')
        assert len(set(rects)) == 1
    finally:
        context.close()


def test_x2_same_owner_refresh_keeps_selected_reading_but_clears_private_assumption(browser):
    ctx,page,seen,errors,_ = _scenario_browser(browser,qualified=True)
    try:
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='ready'")
        page.evaluate("token='rotated';window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner},event:'TOKEN_REFRESHED'}}))")
        assert page.locator('[data-scenario-result]').get_attribute('data-state')=='idle'
        assert page.locator('[name=magnitude]').input_value()=='' and len(seen)==1
        assert page.locator('[type=submit]').is_enabled()
        _scenario_submit(page)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='ready'")
        assert len(seen)==2 and errors==[]
    finally:ctx.close()


def _numeric_browser_client(monkeypatch, tmp_path):
    from tests.test_ontology_explorer_contract import x2_inputs
    from tests.test_ontology_explorer_transport import _rates_scenario_client
    from tests.test_rate_inflation_transmission import _native_scenario_calibration
    import pandas as pd
    inputs = x2_inputs.__wrapped__()
    client, root, path, _ = _rates_scenario_client(monkeypatch, tmp_path, inputs)
    earlier = (pd.Timestamp(inputs[2].effective_at) - pd.offsets.BDay(1)).date().isoformat()
    cal, _ = _native_scenario_calibration(monkeypatch, asof=earlier)
    path.write_text(json.dumps(cal))
    return client, cal


def test_x2_numeric_native_http_to_browser_keeps_method_samples_and_separate_clocks(browser, monkeypatch, tmp_path):
    client, cal = _numeric_browser_client(monkeypatch, tmp_path)
    ctx, page, seen, errors, _ = _scenario_browser(browser)
    delivered = []
    try:
        with client:
            snapshot = client.get('/api/ontology/explorer/v1').json()
            reading = {**snapshot['source'], 'owner_id': 'owner-a'}
            def numeric(r):
                response = client.post('/api/ontology/explorer/scenario/v1', content=r.request.post_data,
                  headers={'Content-Type': 'application/json'})
                assert response.status_code == 200
                delivered.append(response.json())
                r.fulfill(status=response.status_code, headers=dict(response.headers), body=response.text)
            page.route('**/api/ontology/explorer/scenario/v1', numeric)
            page.evaluate("r=>document.getElementById('ox-scenario').dispatchEvent(new CustomEvent('ontology-reading',{detail:r}))", reading)
            page.locator('[name=node]').select_option('transmission:real10y_chg63')
            assert page.locator('[name=shape]').is_disabled()
            page.locator('[name=magnitude]').fill('50'); page.locator('[type=submit]').click()
            page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='ready'")
        output = page.locator('[data-scenario-result]').inner_text()
        assert len(delivered) == 1 and delivered[0]['root_evaluation']['status'] == 'NUMERIC_ILLUSTRATION'
        assert 'Historical same-window illustration' in output and 'not forecasts or causal estimates' in output
        assert '637 overlapping paired observations' in output and 'effective independent sample size are not provided' in output
        assert '2 of 2 calibrated assets shown' in output and 'SPY' in output and 'TLT' in output
        assert cal['scenario_beta_metadata']['generated_at'] in output and snapshot['source']['built'] in output
        assert cal['meta']['asof'] != snapshot['source']['asof']
        assert 'moving-average path' not in output and 'Assumed root threshold met' not in output
        assert '历史同窗示意' in output and '重叠观测不等同于独立事件' in output
        page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
        assert page.locator('[name=node] option:checked').inner_text() == '10年期实际收益率变化'
        assert page.evaluate('[localStorage.length,sessionStorage.length]') == [0, 0] and not errors and seen == []
        page.locator('[name=magnitude]').fill('51')
        assert page.locator('[data-scenario-result]').get_attribute('data-state') == 'idle'
        assert 'SPY' not in page.locator('[data-scenario-result]').inner_text()
    finally: ctx.close()


def test_x2_numeric_decoder_refuses_cross_owner_clock_coverage_and_measurement_claims(browser, monkeypatch, tmp_path):
    import copy
    from tests.test_ontology_explorer_transport import _rates_payload
    client, _ = _numeric_browser_client(monkeypatch, tmp_path)
    with client:
        snapshot = client.get('/api/ontology/explorer/v1').json()
        response = client.post('/api/ontology/explorer/scenario/v1', json=_rates_payload(snapshot))
    assert response.status_code == 200 and response.json()['root_evaluation']['status'] == 'NUMERIC_ILLUSTRATION'
    value = response.json(); reading = {**snapshot['source'], 'owner_id': 'owner-a'}
    assumption = _rates_payload(snapshot)['assumption']
    ctx, page, _, errors, _ = _scenario_browser(browser)
    try:
        def decode(v):
            return page.evaluate("([v,a,r])=>{try{scenario.decodeEvaluation(v,a,v.snapshot_id,r);return true;}catch(_){return false;}}", [v, assumption, reading])
        assert decode(value)
        for path, replacement in [
            (['root_evaluation','confirmed'], True),
            (['root_evaluation','method_class'], 'CAUSAL_RESPONSE'),
            (['root_evaluation','scenario','shock_bp'], 51),
            (['root_evaluation','horizon','unit'], 'calendar_days'),
            (['root_evaluation','calibration','generated_at'], '2099-01-01T00:00:00Z'),
            (['root_evaluation','samples','SPY','n'], True),
            (['root_evaluation','samples','SPY','effective_n'], 637),
            (['root_evaluation','samples','SPY','end'], '2099-01-01'),
            (['root_evaluation','coverage','displayed_assets'], ['SPY']),
            (['root_evaluation','coverage','not_displayed'], [{'asset':'TLT','reason':'hidden'}]),
            (['root_evaluation','uncertainty'], 'CONFIDENT'),
            (['owner_receipt','source_manifest_hash'], 'sha256:'+'f'*64),
            (['owner_receipt','generation'], 'sha256:'+'f'*64),
            (['owner_receipt','selected_knowledge_cutoff'], '2099-01-01T00:00:00Z'),
            (['owner_receipt','knowledge_cutoff'], reading['built']),
            (['owner_receipt','historical_vintage_claim'], True),
            (['owner_receipt','publication_contract'], 'can_trade'),
        ]:
            changed = copy.deepcopy(value); cursor = changed
            for key in path[:-1]: cursor = cursor[key]
            cursor[path[-1]] = replacement
            assert not decode(changed), path
        assert not errors
    finally: ctx.close()


# Native TXI -> Macro Gap view, using recorded owner transitions rather than UI verdict fixtures.
def native_gap_snapshot(tmp_path, *, state='waiting_inside_window'):
    from tests.test_ontology_explorer_contract import _native_gap_root
    from tests import ontology_explorer_fixtures as fx
    options={
        'waiting_inside_window': {}, 'stalled': {'stall':True},
        'contradicted': {'readings':{'n2':True}}, 'condition_stopped': {'kill':True},
        'owner_expired': {'asof':'2026-01-12'}, 'source_unavailable': {},
    }
    root,doc,chain,ledger=_native_gap_root(tmp_path/'native',**options[state])
    # This is still a wholly synthetic native owner fixture. Use the page's
    # admitted chain identity before composing, rather than patching the response.
    slug='oil_inflation_duration_derate';chain['chain']=slug;doc['chains'][0]['chain']=slug
    for row in ledger:row['chain']=slug
    if state=='source_unavailable':ledger=[]
    root=fx.build_root(tmp_path/'selected',yaml_doc=chain,state_doc=doc,slug=slug)
    (root/'data/transmission/chain_episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in ledger))
    result=compose_snapshot(root,chain=slug,now=datetime(2026,2,1,tzinfo=UTC))
    assert result['transmission_gap']['state']==state
    return json.loads(json.dumps(result))

@pytest.mark.parametrize('state',['waiting_inside_window','stalled','contradicted','condition_stopped','owner_expired','source_unavailable'])
@pytest.mark.parametrize('language',['en','zh'])
def test_native_gap_states_are_distinct_on_assembled_macro(browser,tmp_path,state,language):
    from tests.test_ontology_exposure_company_browser import portfolio_start
    snapshot=native_gap_snapshot(tmp_path,state=state)
    ctx,page,seen,errors=portfolio_start(browser,snapshot,width=390,theme='light',language=language,full_shell=True)
    try:
        gap=page.locator('[data-transmission-gap]')
        assert gap.get_attribute('data-gap-state')==state
        if state!='source_unavailable':
            gap.locator('summary').click();text=gap.inner_text()
            assert '2026-01-01' in text and snapshot['source']['source_manifest_hash'] in text
            assert ('Applicability assumption' if language=='en' else '适用前提') in text
            assert ('Expected target condition' if language=='en' else '预期目标条件') in text
            assert ('calendar days' if language=='en' else '日历日') in text
            assert ('not historical point-in-time evidence' if language=='en' else '不是历史时点证据') in text
            gap.locator('button').click()
            assert page.locator('#ox-steps').get_attribute('open') is not None
            # The shared focus action waits for the newly opened details layout.
            page.wait_for_function('(id) => document.activeElement.id === id', arg='ox-leg-'+snapshot['transmission_gap']['pending_hop']['to'])
        else:
            assert ('Missing data is not failed transmission' if language=='en' else '缺失数据不代表传导失败') in gap.inner_text()
            assert gap.locator('button').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert seen==[] and not errors and page.evaluate('pCalls.queries')==0
    finally:ctx.close()

@pytest.mark.parametrize('mutation',[
    ('identity.chain','foreign'),('identity.rev',999),('identity.episode_id','foreign'),
    ('observation.asof','2026-01-06'),('ledger.sha256','0'*64),
    ('pending_hop.elapsed_calendar_days',99),('pending_hop.lag_d',[0,1]),
    ('pending_hop.target_observation.confirmed',True),('market_thesis_verdict','false'),
    ('pending_hop.expected_target.test.op','is_false'),('pending_hop.expected_target.src','foreign'),
    ('pending_hop.applicability_assumption',{'en':'Invented assumption','zh':'虚构前提'}),
    ('state','stalled'),('current_contradiction',{'invented':True}),
])
def test_gap_view_withholds_foreign_generations_and_reinterpreted_conditions(browser,tmp_path,mutation):
    from tests.test_ontology_exposure_company_browser import portfolio_start
    snapshot=native_gap_snapshot(tmp_path);value=snapshot['transmission_gap'];path,replacement=mutation
    parts=path.split('.')
    for key in parts[:-1]:value=value[key]
    value[parts[-1]]=replacement
    ctx,page,seen,errors=portfolio_start(browser,snapshot,full_shell=True)
    try:
        gap=page.locator('[data-transmission-gap]')
        assert gap.get_attribute('data-gap-state')=='source_unavailable'
        assert gap.locator('button, details').count()==0 and not errors
    finally:ctx.close()


@pytest.mark.parametrize("width,language", [(1440,"en"),(1440,"zh"),(390,"en"),(390,"zh")])
def test_research_continuation_uses_existing_theme_owner_and_abstains(browser,synthetic_snapshot,width,language):
    context,page=_open(browser,synthetic_snapshot,width=width,height=900)
    try:
        page.evaluate("lang=>document.documentElement.dataset.lang=lang",language)
        disclosure=page.locator('#ox-research-reading')
        disclosure.locator('summary').click()
        text=disclosure.inner_text()
        assert ('Calibrated opportunity estimates are unavailable' if language=='en' else '经校准的机会估计尚不可用') in text
        assert ('dates are separate' if language=='en' else '日期与本路径读数分开') in text
        link=disclosure.locator('a')
        assert link.get_attribute('href')=='state_of_themes.html#research-reading-order'
        assert page.evaluate('window.__fetchCount')==1
        assert page.evaluate('[localStorage.length,sessionStorage.length]')==[0,0]
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # The actual emitted landing is used; this test creates no new theme population.
        landing=(ROOT/'site/state_of_themes.html').read_text()
        assert landing.count('id="research-reading-order"')==1
        assert 'id="research-reading-order"' in (ROOT/'templates/state_of_themes.html.j2').read_text()
        page.route('http://ontology.test/state_of_themes.html',lambda route: route.fulfill(status=200,content_type='text/html',body=landing))
        page.route('**/*',lambda route: route.fallback() if route.request.url.split('#')[0]=='http://ontology.test/state_of_themes.html' else route.fulfill(status=204))
        link.click()
        page.wait_for_url('**/state_of_themes.html#research-reading-order')
        assert page.locator('#research-reading-order').count()==1
    finally:context.close()


@pytest.mark.parametrize('chain,selected', [
    ('oil_inflation_duration_derate', None),
    ('dollar_spike_em_multinational', 'dollar_spike_em_multinational'),
])
def test_native_transmission_return_keeps_selected_path_revision_and_step(browser, chain, selected):
    """Execute the existing landing script, including URL encoding, in a browser."""
    from urllib.parse import urlencode, urlparse, parse_qs, unquote
    source = (ROOT / 'templates/transmission.html.j2').read_text()
    script = source[source.index('id="tx-from"'):].split('<script>', 1)[1].split('</script>', 1)[0]
    ctx = browser.new_context(); page = ctx.new_page()
    try:
        focus, revision = 'em_derate', 'r3+fixture'
        page.route('**/*', lambda route: route.fulfill(status=200, content_type='text/html',
            body='<p id="tx-from" hidden>Return to the selected step <a id="tx-from-back">Back</a></p>'))
        page.goto('https://macro.example/transmission.html?' + urlencode({'from': chain, 'focus': focus, 'rev': revision}))
        page.evaluate(script)
        href = urlparse(page.locator('#tx-from-back').get_attribute('href'))
        query = parse_qs(href.query)
        assert href.path == 'ontology.html'
        assert query == ({'chain': [selected], 'rev': [revision]} if selected else {'rev': [revision]})
        assert unquote(href.fragment) == 'ox-leg-' + focus
        assert page.locator('#tx-from').is_visible()
        assert focus not in page.locator('#tx-from').inner_text()
    finally:
        ctx.close()



@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('language',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_gap_target_predicate_and_assumption_remain_distinct_in_existing_themes(browser,tmp_path,theme,language,width):
    snapshot=native_gap_snapshot(tmp_path)
    pending=snapshot['transmission_gap']['pending_hop']
    pending['applicability_assumption']={'en':'Synthetic applicability only','zh':'仅为合成适用前提'}
    snapshot['path']['hops'][0]['condition']=pending['applicability_assumption']
    ctx,page=_open(browser,snapshot,width=width,height=900)
    try:
        page.evaluate("([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;}",[theme,language])
        gap=page.locator('[data-transmission-gap]')
        assert gap.get_attribute('data-gap-state')=='waiting_inside_window'
        assumption=gap.locator('[data-gap-applicability]')
        assert ('Synthetic applicability only' if language=='en' else '仅为合成适用前提') in assumption.inner_text()
        gap.locator('summary').click()
        target=gap.locator('[data-gap-target-predicate]')
        assert ('Expected target condition' if language=='en' else '预期目标条件') in target.inner_text()
        assert ('must be true' if language=='en' else '须为真') in target.inner_text()
        assert 'n1' in target.inner_text() and 'Synthetic applicability only' not in target.inner_text()
        assert ('not a verdict on the market thesis' if language=='en' else '不是对市场论点的裁定') in gap.inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>[e.tagName,e.className,e.textContent.slice(0,100),e.getBoundingClientRect().width]).slice(0,10)")
        assert page.evaluate('window.__fetchCount')==1
    finally:ctx.close()


@pytest.mark.parametrize('mutation',['src','predicate','assumption','nested_body','mixed_group'])
def test_gap_target_predicate_refuses_misbinding_and_non_native_payloads(browser,tmp_path,mutation):
    import copy
    snapshot=native_gap_snapshot(tmp_path);pending=snapshot['transmission_gap']['pending_hop']
    if mutation=='src':pending['expected_target']['src']='foreign'
    elif mutation=='predicate':pending['expected_target']['test']['op']='is_false'
    elif mutation=='assumption':pending['applicability_assumption']={'en':'Invented','zh':'虚构'}
    else:
        test={'path':'n1','op':'is_true','private_body':'DO_NOT_EXPORT'} if mutation=='nested_body' else {'all':[{'path':'n1','op':'is_true'}],'any':[{'path':'n1','op':'is_true'}]}
        pending['expected_target']['test']=test
        snapshot['path']['legs'][1]['declared_predicate']=copy.deepcopy(pending['expected_target'])
    ctx,page=_open(browser,snapshot,width=390,height=900)
    try:
        gap=page.locator('[data-transmission-gap]')
        assert gap.get_attribute('data-gap-state')=='source_unavailable'
        assert gap.locator('button, details').count()==0 and 'DO_NOT_EXPORT' not in gap.inner_text()
    finally:ctx.close()


@pytest.mark.parametrize('language',['en','zh'])
def test_gap_target_predicate_renders_boolean_structure_and_zero_threshold(browser,tmp_path,language):
    import copy
    snapshot=native_gap_snapshot(tmp_path);target=snapshot['path']['legs'][1]
    # Explicitly synthetic renderer vector; never a new production declaration.
    target['src']='forex_state'
    target['declared_predicate']={'node_id':target['node_id'],'src':target['src'],'test':{'all':[
        {'path':'dollar_desk.trend','op':'eq','value':'up'},
        {'any':[{'series':'FXI','vs':'SPY','metric':'rs','window':63,'op':'lt','value':0},
                {'path':'transmission.headwind_for','op':'in_contains','value':'EM equities'}]}]}}
    snapshot['transmission_gap']['pending_hop']['expected_target']=copy.deepcopy(target['declared_predicate'])
    ctx,page=_open(browser,snapshot,width=390,height=900)
    try:
        page.evaluate("lang=>document.documentElement.dataset.lang=lang",language)
        gap=page.locator('[data-transmission-gap]');gap.locator('summary').click()
        predicate=gap.locator('[data-gap-target-predicate]');text=predicate.inner_text()
        assert ('All conditions must hold' if language=='en' else '条件须全部满足') in text
        assert ('At least one condition must hold' if language=='en' else '条件至少须满足一项') in text
        assert 'FXI vs SPY' in text and '< 0' in text and '63' in text
        assert ('relative return' if language=='en' else '相对回报') in text
        assert ('must include' if language=='en' else '须包含') in text
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:ctx.close()
