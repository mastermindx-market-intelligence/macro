"""Prophet opens the existing symbol research tool without claiming an episode match."""
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
import pytest

from engine.prophet_opportunity_presentation import present_us_candidate
from tests.test_prophet_opportunity_integration import _render, _source
from tests.test_prophet_table_opportunity_parity import _render as render_table


def check_links(body, ticker):
    links = body.select('.pvs-memory-link')
    assert len(links) == 2
    for link, lang in zip(links, ('en', 'zh')):
        url = urlsplit(link['href'])
        assert not url.scheme and not url.netloc and not url.fragment
        assert url.path == '/market_memory.html'
        assert parse_qs(url.query) == {'mm_issuer_input': [ticker], 'view': ['memory'], 'mm_lang': [lang]}
        assert link['target'] == '_blank'
        assert 'noopener' in link['rel']
    assert 'recomputed history' in links[0].get_text().lower()
    assert 'new tab' in links[0].get_text().lower()
    assert '重算历史' in links[1].get_text()
    assert '新标签页' in links[1].get_text()
    assert body.select_one('[data-plan-exact]')['data-plan-exact'] == 'unavailable'


@pytest.mark.parametrize('prefix', ['today', 'screener', 'today-paid', 'screener-paid'])
def test_native_card_handoff_contains_only_this_symbol_not_an_assessment(prefix):
    source = _source(ticker='BRK.B', theme={'id': 'financials', 'name': 'Financials'})
    body = _render([source], prefix).select_one('.pv-setup-body')
    check_links(body, 'BRK.B')
    assert body.select_one('.pvs-context-link')['href'] == '/baskets.html#theme-financials'


@pytest.mark.parametrize('surface', ['shell', 'paid'])
def test_handoff_stays_inside_existing_public_paid_row_split(tmp_path, surface):
    html, shell, paid = render_table(tmp_path)
    row = (shell if surface == 'shell' else paid['rows'])[0]
    body = BeautifulSoup(row['setup_detail'], 'html.parser').select_one('.pv-setup-body')
    body = BeautifulSoup(str(body), 'html.parser')
    check_links(body, row['ticker'])
    assert 'PVTABLELOCKED' not in html


@pytest.mark.parametrize('ticker', ['', None, 'a/b', 'A?mm_gen=wrong', 'A#private', 'A%2FB', '<script>', 'X'*21])
def test_unusable_identity_has_no_research_link(ticker):
    display = present_us_candidate(_source(ticker=ticker), occurrence_id='source')
    assert display.get('memory_href') is None
