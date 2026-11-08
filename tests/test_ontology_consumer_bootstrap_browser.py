"""Hermetic production-order bootstrap of the selected-reading consumers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader
import pytest

from tests.test_ontology_explorer_brain_browser import browser, synthetic_snapshot

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JS = ROOT / 'templates' / 'ontology.js'

RESEARCH_CONSUMERS = {
    'company': ('ox-company', 'mountCompanyResearch', 'company'),
    'theme': ('ox-theme', 'mountTheme', 'theme'),
    'research': ('ox-research', 'mountResearch', 'research'),
    'radar-research': ('ox-radar-research', 'mountRadarResearch', 'radar'),
}


def _research_shell(browser, language='en'):
    """Actual static shell, with offline module imports controlled by the test."""
    env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True)
    shell = env.get_template('ontology.html.j2').render(nav_prefix='')
    shell = re.sub(r'<script\b[^>]*>.*?</script>', '', shell, flags=re.S)
    context = browser.new_context()
    page = context.new_page()
    requests, errors = [], []
    page.add_init_script("""window.MDXAuth={user:()=>({id:'fixture-owner'}),client:async()=>({auth:{
      onAuthStateChange:()=>({data:{subscription:{unsubscribe(){}}}}),
      getSession:async()=>({data:{session:null}})
    }})};""")

    def route(r):
        requests.append(r.request.url)
        path = urlsplit(r.request.url).path
        if path == '/ontology.html':
            r.fulfill(status=200, content_type='text/html', body=shell)
        elif path.startswith('/ontology-') and path.endswith('.js'):
            r.fulfill(status=200, content_type='text/javascript',
                      body=(ROOT / 'templates' / path[1:]).read_text())
        else:
            r.fulfill(status=200, body='')

    page.route('**/*', route)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('https://ontology.test/ontology.html')
    page.add_style_tag(content='.l-en,.l-zh{display:none}.l-' + language + '{display:inline}')
    page.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
    return context, page, requests, errors


def _mount_research_consumers(page):
    # Prevent the modules' automatic mount, then retain their real lifecycle handles.
    page.evaluate("""async consumers => {
      const roots=Object.fromEntries(Object.entries(consumers).map(([key,[id]])=>[key,document.getElementById(id)]));
      for(const root of Object.values(roots))root.id+='-fixture';
      const modules={};
      for(const key of Object.keys(consumers))modules[key]=await import('/ontology-'+key+'.js');
      for(const [key,[id]] of Object.entries(consumers))roots[key].id=id;
      window.consumerHandles={};
      for(const [key,[id,mount]] of Object.entries(consumers))consumerHandles[key]=modules[key][mount](roots[key]);
    }""", RESEARCH_CONSUMERS)


@pytest.mark.parametrize('language', ['en', 'zh'])
@pytest.mark.parametrize('disposed', [False, True])
def test_research_consumer_lifecycle_fallback_is_visible_and_non_submitting(browser, language, disposed):
    context, page, requests, errors = _research_shell(browser, language)
    try:
        if disposed:
            _mount_research_consumers(page)
            page.evaluate("Object.values(consumerHandles).forEach(h=>h.dispose())")
        for _, (root, _, result) in RESEARCH_CONSUMERS.items():
            output = page.locator(f'#{root} [data-{result}-result]')
            assert output.get_attribute('data-state') == 'module_unavailable'
            assert output.get_attribute('aria-busy') == 'false'
            assert output.locator('.l-' + language).is_visible()
            assert ('not initialized' if language == 'en' else '尚未初始化') in output.inner_text()
            assert page.locator(f'#{root} input:enabled, #{root} select:enabled, #{root} button:enabled').count() == 0
        # Disabled named fields cannot be serialized, even if a prior view filled them.
        page.evaluate("""() => {
          const f=document.querySelector('#ox-research form');
          f.elements.date.value='2026-11-06'; f.elements.ticker.value='PRIVATE-FIXTURE';
          document.querySelector('#ox-company-query').value='PRIVATE-FIXTURE';
        }""")
        assert page.evaluate("Array.from(new FormData(document.querySelector('#ox-research form'))) ") == []
        before = list(requests)
        page.evaluate("document.querySelectorAll('#ox-company button[type=submit], #ox-research button[type=submit]').forEach(b=>b.click())")
        page.keyboard.press('Enter')
        assert page.url == 'https://ontology.test/ontology.html'
        assert requests == before
        assert page.locator('#ox-research a').get_attribute('href') == 'stocks/index.html#pressure'
        assert page.locator('#ox-research a').is_visible()
        assert not errors
    finally:
        context.close()


def test_research_consumer_late_mount_and_disposal_keep_other_consumers_usable(browser):
    context, page, requests, errors = _research_shell(browser)
    try:
        _mount_research_consumers(page)
        for key, (root, _, result) in RESEARCH_CONSUMERS.items():
            assert page.locator(f'#{root} [data-{result}-result]').get_attribute('data-state') == ('no_reading' if key == 'theme' else 'idle')
            assert page.locator(f'#{root} [data-{result}-clear]').is_enabled()
        assert page.locator('#ox-company-query').is_enabled()
        assert page.locator('#ox-research input[name=ticker]').is_enabled()
        assert page.locator('[data-theme-read]').is_disabled()
        page.evaluate("""document.getElementById('ox-theme').dispatchEvent(new CustomEvent('ontology-reading',{detail:{
          chain:'dollar_spike_em_multinational',source_manifest_hash:'sha256:'+'a'.repeat(64),
          asof:'2026-11-06',built:'2026-11-06T12:00:00Z',owner_id:'fixture-owner'
        }}))""")
        assert page.locator('[data-theme-result]').get_attribute('data-state') == 'no_company'
        assert page.locator('[data-theme-read]').is_disabled()
        # Lifecycle changes remain local; another mounted consumer still has its handler.
        page.evaluate("consumerHandles.company.dispose()")
        assert page.locator('#ox-research button[type=submit]').is_enabled()
        page.locator('#ox-research input[name=ticker]').fill('KEPT')
        page.locator('[data-research-clear]').click()
        assert page.locator('#ox-research input[name=ticker]').input_value() == 'KEPT'
        page.locator('[data-radar-clear]').click()
        page.locator('[data-theme-clear]').click()
        assert page.locator('[data-radar-result]').get_attribute('data-state') == 'idle'
        assert page.locator('[data-theme-result]').get_attribute('data-state') == 'no_company'
        assert not any('/api/' in url or urlsplit(url).path == '/ontology.html' and urlsplit(url).query for url in requests)
        assert not errors
    finally:
        context.close()


def test_research_consumer_mounted_forms_intercept_submit_without_native_navigation(browser):
    context, page, requests, errors = _research_shell(browser)
    try:
        _mount_research_consumers(page)
        page.locator('#ox-company-query').fill('FIXTURE')
        page.locator('#ox-company button[type=submit]').click()
        page.wait_for_function("document.querySelector('[data-company-result]').dataset.state==='signed_out'")
        page.locator('#ox-research input[name=date]').fill('2026-11-06')
        page.locator('#ox-research input[name=ticker]').fill('FIXTURE')
        page.locator('#ox-research button[type=submit]').click()
        page.wait_for_function("document.querySelector('[data-research-result]').dataset.state==='unavailable'")
        assert page.url == 'https://ontology.test/ontology.html'
        assert sum(urlsplit(url).path == '/ontology.html' for url in requests) == 1
        assert not any('/api/' in url for url in requests)  # synthetic session is signed out
        assert not errors
    finally:
        context.close()


def test_research_consumer_disposal_during_session_wait_cannot_reenable_or_fetch(browser):
    context, page, requests, errors = _research_shell(browser)
    try:
        page.evaluate("""() => {
          window.sessionReturns=[];
          MDXAuth.client=async()=>({auth:{
            onAuthStateChange:()=>({data:{subscription:{unsubscribe(){}}}}),
            getSession:()=>new Promise(resolve=>sessionReturns.push(resolve))
          }});
        }""")
        _mount_research_consumers(page)
        page.locator('#ox-company-query').fill('FIXTURE')
        page.locator('#ox-company button[type=submit]').click()
        page.locator('#ox-research input[name=date]').fill('2026-11-06')
        page.locator('#ox-research input[name=ticker]').fill('FIXTURE')
        page.locator('#ox-research button[type=submit]').click()
        page.locator('[data-radar-read]').click()
        page.evaluate("""() => {
          document.getElementById('ox-theme').dispatchEvent(new CustomEvent('ontology-reading',{detail:{
            chain:'dollar_spike_em_multinational',source_manifest_hash:'sha256:'+'a'.repeat(64),
            asof:'2026-11-06',built:'2026-11-06T12:00:00Z',owner_id:'fixture-owner'
          }}));
          document.getElementById('ox-company').dispatchEvent(new CustomEvent('ontology-company-identity',{detail:{
            identity_kind:'security',identity_id:'SEC:US-XNAS-FIXTURE',symbol:'FIXTURE',owner_id:'fixture-owner'
          }}));
        }""")
        page.locator('[data-theme-read]').click()
        page.wait_for_function('sessionReturns.length===4')
        for _, (_, _, result) in RESEARCH_CONSUMERS.items():
            assert page.locator(f'[data-{result}-result]').get_attribute('aria-busy') == 'true'
        page.evaluate("""async () => {
          Object.values(consumerHandles).forEach(h=>h.dispose());
          sessionReturns.forEach(resolve=>resolve({data:{session:{user:{id:'fixture-owner'},access_token:'fixture-token'}}}));
          await new Promise(resolve=>setTimeout(resolve,0));
        }""")
        for _, (root, _, result) in RESEARCH_CONSUMERS.items():
            assert page.locator(f'[data-{result}-result]').get_attribute('data-state') == 'module_unavailable'
            assert page.locator(f'#{root} input:enabled, #{root} select:enabled, #{root} button:enabled').count() == 0
        assert not any('/api/' in url for url in requests)
        assert not errors
    finally:
        context.close()


def _open(browser, snapshot, *, blocked=(), late=False, language='en'):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    shell = env.get_template("ontology.html.j2").render(nav_prefix="")
    if late:
        for name in ['portfolio', 'scenario']:
            shell = shell.replace(f'<script type="module" src="ontology-{name}.js"></script>', '')
    context = browser.new_context()
    page = context.new_page()
    errors, requests = [], []
    page.add_init_script("""window.owner='fixture-owner';window.callbacks=[];
      window.MDXAuth={user:()=>owner?{id:owner}:null,client:async()=>({auth:{
        getSession:async()=>({data:{session:{user:{id:owner},access_token:'fixture-token'}}}),
        onAuthStateChange:fn=>{callbacks.push(fn);return {data:{subscription:{unsubscribe(){}}}};}
      }})};""")
    page.add_init_script(f"localStorage.setItem('lang', {json.dumps(language)});")

    def route(r):
        path = urlsplit(r.request.url).path
        requests.append(path)
        if path == '/ontology.html':
            r.fulfill(status=200, content_type='text/html', body=shell)
        elif path == '/api/ontology/explorer/v1':
            r.fulfill(status=200, content_type='application/json', body=json.dumps(snapshot))
        elif path in ['/ontology.js', '/ontology-scenario.js', '/ontology-portfolio.js']:
            if path in blocked:
                r.fulfill(status=503, content_type='text/javascript', body='// fixture asset unavailable')
            else:
                asset = ONTOLOGY_JS if path == '/ontology.js' else ROOT / 'templates' / path[1:]
                r.fulfill(status=200, content_type='text/javascript', body=asset.read_text())
        else:
            r.fulfill(status=200, content_type='text/javascript', body='')

    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/*', route)
    page.goto('https://ontology.test/ontology.html')
    page.wait_for_selector('#ox-root .ox-leg', state='attached')
    return context, page, errors, requests


@pytest.mark.parametrize('missing_membership_clock', [False, True])
def test_production_order_mounts_scenario_and_delivers_portfolio_reading(browser, synthetic_snapshot, missing_membership_clock):
    if missing_membership_clock:
        synthetic_snapshot['company_exposure']['asof'] = None
    context, page, errors, requests = _open(browser, synthetic_snapshot)
    try:
        assert page.locator('[data-scenario-form] select').count() == 3
        assert page.locator('[data-scenario-form] input').count() == 1
        assert page.locator('[data-scenario-result]').get_attribute('data-state') == 'idle'
        assert page.locator('[data-portfolio-result]').get_attribute('data-state') == ('reading_unavailable' if missing_membership_clock else 'idle')
        assert page.locator('[data-portfolio-read]').is_enabled() is not missing_membership_clock
        if missing_membership_clock:
            assert 'dated screen membership is unavailable' in page.locator('[data-portfolio-result]').inner_text()
        assert requests.count('/api/ontology/explorer/v1') == 1
        assert not any('scenario/v1' in p or 'portfolio/v1' in p for p in requests)
        assert not errors
    finally:
        context.close()


@pytest.mark.parametrize('late', [False, True])
def test_unavailable_or_late_modules_keep_visible_disabled_shell_without_private_reads(browser, synthetic_snapshot, late):
    context, page, errors, requests = _open(browser, synthetic_snapshot,
        blocked=() if late else ('/ontology-scenario.js', '/ontology-portfolio.js'), late=late)
    try:
        assert page.locator('[data-scenario-form] select').count() == 3
        assert page.locator('[data-scenario-form] input').count() == 1
        assert page.locator('[name=node] option').first.text_content() == 'WTI oil / WTI 原油'
        assert page.locator('[data-scenario-form] :enabled').count() == 0
        assert page.locator('[data-scenario-result]').get_attribute('data-state') == 'module_unavailable'
        assert 'controls have not initialized' in page.locator('[data-scenario-result]').inner_text()
        assert page.locator('[data-portfolio-result]').get_attribute('data-state') == 'module_unavailable'
        assert page.locator('[data-portfolio-read]').is_disabled()
        if late:
            page.add_script_tag(url='https://ontology.test/ontology-scenario.js', type='module')
            page.add_script_tag(url='https://ontology.test/ontology-portfolio.js', type='module')
            page.wait_for_function("document.querySelector('[data-portfolio-result]').dataset.state==='idle'")
            assert page.locator('[data-scenario-result]').get_attribute('data-state') == 'idle'
            assert page.locator('[data-scenario-form] select').count() == 3
            assert page.locator('[data-scenario-form] input').count() == 1
            assert page.locator('[data-scenario-form] button').count() == 2
            assert page.locator('[data-portfolio-read]').is_enabled()
        assert requests.count('/api/ontology/explorer/v1') == 1
        assert not any('scenario/v1' in p or 'portfolio/v1' in p for p in requests)
        assert not errors
    finally:
        context.close()


def test_server_options_are_plain_text_and_module_initializes_chinese_locale(browser, synthetic_snapshot):
    import re
    env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True)
    shell = env.get_template('ontology.html.j2').render(nav_prefix='')
    options = re.findall(r'<option\b[^>]*>(.*?)</option>', shell, re.S)
    assert options and all('<' not in text for text in options)
    context, page, errors, _ = _open(browser, synthetic_snapshot, language='zh')
    try:
        assert page.locator('[name=node] option').first.text_content() == 'WTI 原油'
        assert page.locator('[name=shape] option').first.text_content() == '仅指定期末值'
        assert not errors
    finally:
        context.close()


def test_unqualified_membership_state_survives_clear_but_not_owner_change(browser, synthetic_snapshot):
    synthetic_snapshot['company_exposure']['asof'] = None
    context, page, errors, requests = _open(browser, synthetic_snapshot)
    try:
        assert page.locator('[data-portfolio-result]').get_attribute('data-state') == 'reading_unavailable'
        page.locator('[data-portfolio-clear]').click()
        page.locator('[data-private-kind=watchlist]').click()
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner},event:'TOKEN_REFRESHED'}}))")
        assert page.locator('[data-portfolio-result]').get_attribute('data-state') == 'reading_unavailable'
        assert page.locator('[data-portfolio-read]').is_disabled()
        page.evaluate("owner=null;window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
        assert page.locator('[data-portfolio-result]').get_attribute('data-state') == 'no_reading'
        assert page.locator('[data-portfolio-read]').is_disabled()
        assert not any('scenario/v1' in p or 'portfolio/v1' in p for p in requests)
        assert not errors
    finally:
        context.close()
