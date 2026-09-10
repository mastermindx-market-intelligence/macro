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
    assert not hero.select('.ent-line')


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
