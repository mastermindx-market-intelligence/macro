"""Recovered release-result browser regression; independent of repository production.

Authored after the interrupted run: this is not a reconstruction/claim of its
unrecovered 68-case file. Uses the actual adapter, template and candidate assets.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import pytest
# Keep ordinary repository test collection independent of optional browser tooling.
# The recorded browser proof installs Playwright and runs these tests without skips.
_pw = pytest.importorskip("playwright.sync_api", reason="optional browser proof requires Playwright")
sync_playwright, expect = _pw.sync_playwright, _pw.expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))
from events_news_release_fixture import historical_data
from events_news_release_browser_support import fixture_page
from engine.events_news_release_evidence import attach_event_actual_evidence, attach_event_expectation_context
from test_events_news_release_expectations import ASOF as EXPECT_ASOF, cpi_event, forecast_payload

SIZES = [(1440,900),(768,1024),(390,844),(320,740),(844,390),(720,450)]
APPEARANCES = [('dark','en'),('light','en'),('dark','zh'),('light','zh')]
NOW = datetime(2026,8,12,13,tzinfo=timezone.utc)


def result_data(state='available'):
    if state in ('reference_drift','precision_withheld'):
        data = historical_data()
        if state == 'reference_drift':
            data['macro_catalysts'][0]['reference_period'] = 'June 2026'
        else:
            rows = json.loads((ROOT/'tests/fixtures/events_news_official_receipts.json').read_text())['rows']
            for row in rows:
                if row['release'] == 'cpi_headline': row['published_precision'] = 0
            data['macro_catalysts'] = attach_event_actual_evidence(
                data['macro_catalysts'], rows, as_of=data['generated_utc'],
                defects_path=ROOT/'tests/fixtures/events_news_actual_defects.json')
        return data
    return historical_data(state)


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
        b = p.chromium.launch(headless=True, **({'executable_path':executable} if executable else {}))
        yield b
        b.close()


def load(browser, state='available', theme='light', lang='en', size=(1440,900), js=True):
    p = browser.new_page(viewport=dict(width=size[0],height=size[1]))
    p.clock.set_fixed_time(NOW)
    p.set_content(fixture_page(result_data(state),theme,lang,include_js=js),wait_until='domcontentloaded')
    if js: expect(p.locator('#dlg-news')).to_have_attribute('data-nd-ready','true')
    return p


def enter_detail(p):
    p.locator('[data-nd-mode="releases"]').click()
    p.locator('[data-nd-item="calendar"]').evaluate('(n)=>window.originalResultRow=n')
    p.locator('[data-nd-inspect]:visible').first.click()
    assert p.locator('[data-nd-detail-record] [data-nd-item]').evaluate('(n)=>n===window.originalResultRow')


def assert_fit(p, size):
    box=p.locator('.nd-panel').bounding_box()
    assert box and box['x']>=0 and box['y']>=0
    assert box['x']+box['width']<=size[0]+1 and box['y']+box['height']<=size[1]+1
    body=p.locator('.nd-body').evaluate('(n)=>({w:n.clientWidth,s:n.scrollWidth,h:n.clientHeight})')
    assert body['s']<=body['w']+1 and body['h']>=100, body
    close=p.locator('.nd-close').bounding_box()
    assert close['height']>=44 and close['width']>=44


@pytest.mark.parametrize('size',SIZES)
@pytest.mark.parametrize('theme,lang',APPEARANCES)
def test_available_result_disclosure_and_return(browser,size,theme,lang):
    p=load(browser,theme=theme,lang=lang,size=size)
    try:
        errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        assert not p.locator('.nd-official-evidence').evaluate('(n)=>n.open')
        enter_detail(p)
        assert p.locator('.nd-official-value').all_text_contents()==['0.1%','0.2%']
        assert p.locator('.nd-official-evidence').evaluate('(n)=>n.open')
        assert p.locator('[data-nd-provenance][open]').count()==0
        assert_fit(p,size)
        summary=p.locator('[data-nd-provenance] > summary').first
        summary.focus();p.keyboard.press('Enter')
        expect(p.locator('[data-nd-provenance]').first).to_have_attribute('open','')
        assert '2026-07' in p.locator('.nd-official-period').first.inner_text()
        assert '2026-08-12T12:30:48.228052+00:00' in p.locator('[data-nd-provenance]').first.inner_text()
        assert_fit(p,size)
        p.locator('[data-nd-back]').click()
        assert p.locator('[data-nd-item="calendar"]').evaluate('(n)=>n===window.originalResultRow')
        assert p.locator('[data-nd-item]').count()==1 and p.locator('[data-al-row]').count()==0
        assert p.locator('[data-nd-provenance][open]').count()==0
        assert not p.locator('.nd-official-evidence').evaluate('(n)=>n.open')
        assert p.locator('[data-nd-inspect]').evaluate('(n)=>n===document.activeElement')
        assert not errors,errors
    finally: p.close()


@pytest.mark.parametrize('state,count',[
    ('partial',1),('withheld',0),('repaired',2),('quarantine_missing',0),
    ('mismatch',0),('unsupported',0),('binding_mismatch',0),
    ('precision_withheld',1),('reference_drift',0),
])
@pytest.mark.parametrize('theme,lang,size',[
    ('dark','en',(1440,900)),('light','zh',(390,844)),
])
def test_result_gaps_and_partial_state(browser,state,count,theme,lang,size):
    p=load(browser,state,theme,lang,size)
    try:
        enter_detail(p)
        assert p.locator('.nd-official-value').count()==count
        assert p.locator('[data-nd-official-count]').get_attribute('data-nd-official-count')==str(count)
        if count==0: assert p.locator('.nd-official-missing:visible').count()>0
        assert_fit(p,size)
        p.keyboard.press('Escape')
        assert not p.locator('.nd-detail').is_visible()
        assert p.locator('[data-nd-item="calendar"]').evaluate('(n)=>n===window.originalResultRow')
    finally: p.close()


@pytest.mark.parametrize('lang',['en','zh'])
def test_no_js_keeps_native_result_and_source_disclosures(browser,lang):
    p=load(browser,lang=lang,js=False,size=(390,844))
    try:
        p.locator('.nd-official-evidence > summary').click()
        assert p.locator('.nd-official-value:visible').count()==2
        p.locator('[data-nd-provenance] > summary').first.click()
        assert p.locator('[data-nd-provenance][open]').count()==1
        assert p.locator('[data-nd-provenance] a').first.get_attribute('href').startswith('https://www.bls.gov/')
        assert_fit(p,(390,844))
    finally: p.close()


def test_detail_language_change_preserves_evidence_and_no_storage(browser):
    p=load(browser)
    try:
        requests=[];p.on('request',lambda r:requests.append(r.url))
        p.evaluate("() => { Storage.prototype.setItem=function(){throw new Error('unexpected persistence')}; }")
        enter_detail(p)
        p.locator('[data-nd-provenance] > summary').first.click()
        p.evaluate("document.documentElement.dataset.lang='zh'")
        expect(p.locator('[data-nd-detail-kind]')).to_have_text('数据公布 / 官方结果')
        assert p.locator('[data-nd-provenance][open]').count()==1
        assert p.locator('.nd-official-value').all_text_contents()==['0.1%','0.2%']
        p.locator('[data-nd-back]').click()
        p.locator('[data-nd-mode="following"]').click()
        assert p.locator('.nd-following button').is_disabled()
        assert not requests
    finally: p.close()


def test_reinitialization_retains_one_result_and_identity(browser):
    p=load(browser)
    try:
        enter_detail(p)
        p.evaluate((ROOT/'templates/macro-events-news.js').read_text())
        assert p.locator('[data-nd-item]').count()==1
        assert p.locator('.nd-official-value').count()==2
        p.locator('[data-nd-back]').click()
        assert p.locator('[data-nd-item="calendar"]').evaluate('(n)=>n===window.originalResultRow')
    finally: p.close()


def test_repaired_result_does_not_relabel_later_verification(browser):
    p=load(browser,state='repaired')
    try:
        enter_detail(p);p.locator('[data-nd-provenance] > summary').first.click()
        text=p.locator('[data-nd-provenance]').first.inner_text()
        assert '2026-07-30T12:30:56.032836+00:00' in text
        assert '2026-08-11T08:24:15.196500+00:00' in text
        assert p.locator('.nd-official-value').first.inner_text()=='-0.1%'
    finally: p.close()


def test_expectation_detail_opens_summary_but_keeps_methodology_progressive(browser):
    event = cpi_event()
    event.update(time_et='08:30', impact='high', label='CPI · fixture release')
    event = attach_event_expectation_context(
        [event], forecast_payload(), as_of=EXPECT_ASOF)[0]
    data = {
        'alerts': [], 'latest': None, 'macro_news': {'headlines': []},
        'macro_catalysts': [event], 'generated_utc': EXPECT_ASOF,
    }
    p = browser.new_page(viewport=dict(width=1440, height=900))
    p.clock.set_fixed_time(datetime(2026,10,1,21,tzinfo=timezone.utc))
    try:
        p.set_content(
            fixture_page(data, 'light', 'en', include_js=True),
            wait_until='domcontentloaded')
        expect(p.locator('#dlg-news')).to_have_attribute('data-nd-ready','true')
        outer = p.locator('.nd-expectation-context')
        assert not outer.evaluate('(n)=>n.open')
        p.locator('[data-nd-mode="releases"]').click()
        p.locator('[data-nd-inspect]:visible').first.click()
        assert outer.evaluate('(n)=>n.open')
        assert p.locator('.nd-expectation-method[open]').count() == 0
        text = outer.inner_text()
        assert 'Street survey' in text and 'Not connected' in text
        assert 'Mastermind blended benchmark' in text
        p.locator('.nd-expectation-method > summary').first.click()
        assert p.locator('.nd-expectation-method[open]').count() == 1
        assert 'Accuracy claim' in p.locator('.nd-expectation-method').first.inner_text()
        p.locator('[data-nd-back]').click()
        assert not outer.evaluate('(n)=>n.open')
        assert p.locator('.nd-expectation-method[open]').count() == 0
    finally:
        p.close()
