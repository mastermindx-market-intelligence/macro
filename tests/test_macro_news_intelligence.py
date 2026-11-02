"""News rendering contracts: source honesty, safe links, malformed input resilience."""
from pathlib import Path
import re
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(loader=FileSystemLoader(ROOT / 'templates'), undefined=StrictUndefined)

def render(**values):
    data = dict(alerts=[], macro_news={'headlines': []}, latest={})
    data.update(values)
    return BeautifulSoup(ENV.get_template('_macro_news_intelligence.html.j2').render(**data), 'html.parser')

def test_one_population_and_calendar_is_not_an_action_signal():
    alerts = [{'rule':'gex_flip', 'tier':'watch', 'plain_en':'Gamma flipped', 'message':'4 sessions; crossing unobserved'},
              {'rule':'event_risk', 'tier':'context', 'plain_en':'Event ahead', 'message':'Jobs in 5 days'},
              {'rule':'fund_move', 'tier':'context', 'message':'ARKK cut GOOG'},
              {'rule':'legacy', 'message':'Legacy alert'}]
    soup = render(alerts=alerts, latest={'dislocation': {'dislocation_active':True, 'fed_put':None}})
    assert len(soup.select('[data-al-row]')) == len(alerts) + 1
    assert len(soup.select('[data-news-item="priority"]')) == 4
    event = soup.select_one('[data-news-event-alert]')
    assert event.select_one('.ni-status .l-en').text == 'Event'
    assert 'Jobs in 5 days' in event.select_one('[data-news-observation]').text
    assert '4 sessions; crossing unobserved' in soup.select_one('[data-news-observation]').text
    assert not soup.select('time')  # no invented observation timestamp

@pytest.mark.parametrize('alerts,news', [(None,None), ('bad', {'headlines':'bad'}), ({}, {}), ([None, 42], {'headlines':[None, {'title':''}]})])
def test_malformed_inputs_render_partial_state(alerts, news):
    soup = render(alerts=alerts, macro_news=news)
    assert soup.select_one('.ni-notice')
    assert soup.select_one('.ni-empty')
    assert not soup.select('[data-news-item]')

def test_unavailable_is_distinct_from_empty_and_failed_search():
    soup = render()
    assert not soup.select_one('.ni-notice')
    assert 'No developments' in soup.select_one('.ni-empty').text
    assert soup.select_one('[data-news-no-matches]').has_attr('hidden')
    assert soup.select_one('[data-news-toolbar]').has_attr('hidden')

def test_headline_escaping_protocols_dedup_and_no_ten_item_truncation():
    rows = [{'title':f'Report {n}', 'url':f'https://example.org/{n}', 'seendate':'2026-10-30'} for n in range(12)]
    rows += [dict(rows[0]), {'title':'<img src=x onerror=alert(1)>', 'url':'javascript:alert(1)'}, {'title':'Unsafe', 'url':'data:text/html,<script>x</script>'}]
    soup = render(macro_news={'headlines':rows})
    assert len(soup.select('[data-news-item="headlines"]')) == 14
    assert not soup.select('img, script')
    assert all(a['href'].startswith(('https://','http://')) for a in soup.select('.ni-title a'))
    assert all('noreferrer' in a['rel'] for a in soup.select('.ni-title a'))
    assert '<img' in soup.select('[data-news-item="headlines"]')[-2].text

def test_caveat_not_hidden_in_disclosure():
    soup = render(alerts=[{'rule':'gex', 'message':'Snapshot gaps: crossing point unobserved', 'edge_en':'Volatility backdrop, not direction.', 'what_en':'Long explanation'}])
    row = soup.select_one('[data-al-row]')
    assert row.select_one('.ni-limit').text.startswith('Volatility')
    assert not row.select_one('.ni-limit').find_parent('details')
    assert 'Long explanation' in row.select_one('details').text
    assert not row.select_one('details').has_attr('open')

def test_parent_integration_and_build_asset_contract():
    parent = (ROOT/'templates/dashboard.html.j2').read_text()
    ENV.parse(parent)
    block = parent.split('{# dlg-news:')[1].split('{# dlg-deep-context:')[0]
    assert block.count("{% include '_macro_news_intelligence.html.j2' %}") == 1
    assert 'aria-labelledby="ni-dialog-title"' in block
    assert 'onclick="mx5CloseDlg()"' in block
    builder = (ROOT/'scripts/build_site.py').read_text()
    for asset in ['macro_news_intelligence.css','macro_news_intelligence.js','release_publications_live.js']:
        assert asset in parent and asset in builder
        assert (ROOT/'templates'/asset).read_bytes() == (ROOT/'site'/asset).read_bytes()
