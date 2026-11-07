"""Hermetic production-order bootstrap of the selected-reading consumers."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader
import pytest

from tests.test_ontology_explorer_brain_browser import browser, synthetic_snapshot

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JS = ROOT / 'templates' / 'ontology.js'


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
