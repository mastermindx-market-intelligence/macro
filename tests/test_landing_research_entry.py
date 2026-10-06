"""The homepage's first research example must be useful, dated and navigable."""
from pathlib import Path
import json
import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_outcome_hero_and_free_entry_are_unambiguous(surface):
    page = BeautifulSoup((ROOT / surface / 'index.html').read_text(), 'html.parser')
    hero = page.select_one('.cov-copy')
    assert 'See what changed.' in hero.h1.get_text(' ', strip=True)
    assert 'Understand why it matters.' in hero.h1.get_text(' ', strip=True)
    assert 'MastermindX' in hero.h1.get_text()
    assert hero.select_one('a[href="#research-example"]')
    assert 'No credit card' in hero.select_one('.micro').get_text()
    assert 'TRIAL' not in hero.select_one('.micro').get_text().upper()
    assert hero.select_one('.sub'), 'Keep a visible explanation of the research product'


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_example_is_static_dated_and_not_a_live_model_answer(surface):
    page = BeautifulSoup((ROOT / surface / 'index.html').read_text(), 'html.parser')
    example = page.select_one('#research-example')
    assert example, 'A useful example must exist in authored HTML, before animation'
    text = example.get_text(' ', strip=True)
    for phrase in ['AAPL', '9 Sep 2026', 'FY2025', '$416.2B', '$98.8B', '47.63', 'not a live quote']:
        assert phrase in text
    assert example.select_one('[data-zh]')
    assert len(example.select('.re-step')) == 3
    for link in example.select('a.re-source'):
        path, anchor = link['href'].split('#')
        target = BeautifulSoup((ROOT / 'site' / path).read_text(), 'html.parser')
        assert target.find(id=anchor), f'Destination must preserve a real AAPL section: {link}'
    assert {a['href'] for a in example.select('a.re-source')} == {
        'stocks/AAPL.html#financials', 'stocks/AAPL.html#valuation', 'stocks/AAPL.html#why'
    }


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_demo_and_institutional_relationships_are_not_overclaimed(surface):
    page = BeautifulSoup((ROOT / surface / 'index.html').read_text(), 'html.parser')
    disclosure = page.select_one('details.hero-demos')
    assert disclosure and disclosure.find('summary')
    assert 'not current market data' in disclosure.get_text(' ', strip=True)
    assert disclosure.select_one('#pyr'), 'Retain existing demonstration IDs until composition'
    assert not page.select('.tlogos'), 'Unsubstantiated institutional-use assertion must not remain'
    assert 'PROPHET · TODAY' not in disclosure.get_text()
    assert 'TECHNOLOGY — TODAY' not in disclosure.get_text()


def test_new_copy_has_a_fresh_shadow_identity_not_a_relabelled_experiment():
    page = BeautifulSoup((ROOT / 'templates/index.html').read_text(), 'html.parser')
    config = json.loads(page.select_one('#mm-adtest').string)
    assert config['arena_id'] == 'hero-connected-research-20260910'
    assert config['status'] == 'planned' and config['mode'] == 'shadow'
    assert len(config['arms']) == 2
    assert not {'adc-a929e26ce95c', 'adc-67661666832f'} & {a['id'] for a in config['arms']}


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_counterpoint_shows_a_comparable_sector_reference(surface):
    page = BeautifulSoup((ROOT / surface / 'index.html').read_text(), 'html.parser')
    step = page.select('#research-example .re-step')[1]
    assert '47.63' in step.get_text() and '28.77' in step.get_text()
    assert 'Sector median' in step.get_text(), 'A bare multiple does not demonstrate the counterpoint'
    assert any('行业中位数' in node.get('data-zh', '') for node in step.select('[data-zh]'))


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_hero_has_one_authoritative_type_scale(surface):
    import re
    css = (ROOT / surface / 'landing.css').read_text()
    rules = re.findall(r'(?<![\w.])\.cov-copy h1\s*\{([^}]+)\}', css)
    assert len([rule for rule in rules if 'font-size:' in rule]) == 1, 'Edit the canonical hero rule, not a remote override'


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_all_demo_heading_labels_are_explicitly_noncurrent(surface):
    page = BeautifulSoup((ROOT / surface / 'index.html').read_text(), 'html.parser')
    disclosure = page.select_one('details.hero-demos')
    text = disclosure.get_text(' ', strip=True)
    assert "TODAY'S READ" not in text and 'WHAT TO ACT ON NOW' not in text
    assert all(not any(label in node.get('data-zh', '') for label in ['今日研判', '现在该做什么']) for node in disclosure.select('[data-zh]'))


@pytest.mark.parametrize('surface', ['templates', 'site'])
def test_mobile_demo_centres_on_actual_disclosure_toggle(surface):
    import re
    import subprocess
    source = (ROOT / surface / 'index.html').read_text()
    match = re.search(r'/\* — pyramid on mobile:.*?\*/\s*(\(function\(\)\{.*?\}\)\(\);)', source, re.S)
    assert match, 'The existing mobile positioning owner must remain present'
    harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const events = {}, globalEvents = {};
const details = {open:false,addEventListener:(name,fn)=>events[name]=fn};
const pyr = {scrollLeft:0,clientWidth:0,closest:()=>details};
const card = {offsetLeft:0,offsetWidth:0};
const context = {document:{getElementById:id=>id==='pyr'?pyr:card,querySelector:()=>details},
 getComputedStyle:()=>({display:'flex'}),requestAnimationFrame:fn=>fn(),
 addEventListener:(name,fn)=>globalEvents[name]=fn};
vm.runInNewContext(SOURCE, context);
assert.equal(pyr.scrollLeft,0);
assert.equal(typeof globalEvents.resize,'function');
assert.equal(typeof events.toggle,'function','Opening details must activate the existing centre routine');
details.open=true;pyr.clientWidth=390;card.offsetLeft=550;card.offsetWidth=280;
events.toggle();assert.equal(pyr.scrollLeft,495,'The front card must centre after the hidden strip gets dimensions');
pyr.clientWidth=320;globalEvents.resize();assert.equal(pyr.scrollLeft,530);
""".replace('SOURCE', json.dumps(match[1]))
    result = subprocess.run(['node','-e',harness],capture_output=True,text=True,timeout=15)
    assert result.returncode == 0, result.stderr
