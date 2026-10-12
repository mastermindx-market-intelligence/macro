"""Narrow structural discriminators; not a substitute for product or browser review."""
from pathlib import Path
from bs4 import BeautifulSoup
import re

ROOT = Path(__file__).resolve().parents[1]

def load():
    return BeautifulSoup((ROOT / 'prototype.html').read_text(encoding='utf-8'), 'html.parser')

def test_flagship_is_visible_in_the_hero_not_just_anywhere():
    s = load(); hero = s.select_one('header.hero')
    assert hero is not None, 'A visible flagship-first hero is required'
    identity = hero.select_one('.eyebrow')
    assert identity and 'prophet' in identity.get_text().lower(), 'Identify the flagship in the hero hierarchy, not merely a CTA'
    assert not identity.has_attr('hidden')
    assert hero.select_one('h1') and 'signals' in hero.h1.get_text().lower()
    assert 'intelligence' in hero.h1.get_text().lower()

def test_primary_navigation_and_cta_reach_existing_prophet_route():
    s = load(); first = s.select_one('nav .product-link'); cta = s.select_one('#primary-cta')
    assert first and first.get('href') == 'https://www.mastermind-x.com/us_stocks.html'
    assert first.get_text(strip=True) == 'Prophet'
    assert cta and cta.get('href') == first['href']

def test_delivered_example_is_not_behind_a_closed_disclosure_or_research_work():
    s = load(); card = s.select_one('#signal-example'); explanation = s.select_one('#prepared-read')
    assert card and explanation, 'Provide a prepared signal and explanation, not research homework'
    assert not card.find_parent('details'), 'Flagship proof must not be hidden in a disclosure'
    assert not card.has_attr('hidden') and not explanation.has_attr('hidden')
    before = str(s).split('id="signal-example"')[0]
    assert '<input' not in before and '<textarea' not in before, 'No setup before first value'
    assert 'Inspect the valuation' not in before, 'Research cannot replace first value'

def test_historical_and_winner_selection_disclosures_are_explicit():
    s = load(); notice = s.select_one('#sample-disclosure')
    assert notice and '2026-08-21' in notice.get_text()
    assert 'selected for winners' in notice.get_text().lower()
    assert 'not current' in notice.get_text().lower()
    assert not notice.find_parent('details') and not notice.has_attr('hidden')

def test_example_fields_preserve_the_public_source_without_probability_claims():
    s = load()
    for selector, expected in [('#signal-ticker','HOOD'),('#signal-label','BUY'),
                              ('#signal-price','$108.13'),('#zone-low','$103.00'),
                              ('#zone-high','$108.10'),('#edge-grade','61')]:
        e=s.select_one(selector)
        assert e and e.get_text(strip=True)==expected, f'Incorrect source field: {selector}'
    grade_note=s.select_one('#grade-note')
    assert grade_note and 'not a win probability' in grade_note.get_text().lower()
    raw=(ROOT/'prototype.html').read_text(encoding='utf-8')
    assert not re.search(r'Math\.random|setInterval|since_pct|win.?rate', raw, re.I)

def test_cautions_are_not_recast_as_bullish_confirmation():
    s=load(); text=s.select_one('#prepared-read')
    assert text and 'accounting-quality concerns' in text.get_text().lower()
    assert 'weakening financials basket' in text.get_text().lower()
    bilingual = ' '.join(e.get('data-zh', '') for e in text.select('[data-zh]'))
    assert '财务质量需复核' in bilingual and '金融板块篮子走弱' in bilingual
    assert s.select_one('#entry-note') and 'not a current entry' in s.select_one('#entry-note').get_text().lower()

def test_language_and_degraded_states_are_explicit():
    s=load()
    assert s.select_one('button[data-lang="zh"]') and s.select_one('button[data-lang="en"]')
    assert s.select_one('#empty-state') and s.select_one('#unavailable-state')
    assert 'No setups in this example' in s.select_one('#empty-state').get_text()
    assert 'unavailable' in s.select_one('#unavailable-state').get_text().lower()
    assert s.select_one('meta[name="robots"]')['content']=='noindex,nofollow'
