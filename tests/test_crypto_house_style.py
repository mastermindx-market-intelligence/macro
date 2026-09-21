from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PARTIAL = ROOT / "templates" / "_crypto_house_style.html.j2"


def test_both_crypto_dashboards_use_one_house_style_partial():
    for template in ("crypto.html.j2", "vector.html.j2"):
        source = (ROOT / "templates" / template).read_text(encoding="utf-8")
        assert '{% include "_crypto_house_style.html.j2" %}' in source


def test_house_style_uses_sf_display_and_inter_ui_data():
    source = PARTIAL.read_text(encoding="utf-8")
    assert '"SF Pro Display"' in source
    assert '"SF Pro Text"' in source
    assert "--font-data: Inter" in source
    assert "--font-mono: var(--font-data)" in source
    assert "--num: var(--font-data)" in source


def test_house_style_inherits_macro_and_commodities_tokens():
    source = PARTIAL.read_text(encoding="utf-8")
    for token in (
        "var(--info)",
        "var(--panel)",
        "var(--panel2)",
        "var(--line)",
        "var(--text)",
        "var(--muted)",
    ):
        assert token in source
    assert "--crypto: var(--info)" in source
    assert "border-radius: 16px" in source
    assert "backdrop-filter: saturate(165%) blur(18px)" in source


# The main Crypto board is a static table with live quote hooks, not a new feed.
def test_crypto_market_board_has_accessible_table_relationships():
    source = (ROOT / "templates/crypto.html.j2").read_text()
    for marker in ('id="crypto-market-title"', 'role="table" aria-labelledby="crypto-market-title"',
                   'role="columnheader"', 'role="rowheader"', 'role="cell"'):
        assert marker in source
    assert 'data-sym="{{ a.live_symbol }}"' in source
    assert 'market-value nb-px' in source and 'market-change nb-chg' in source


def test_crypto_narrow_rows_keep_identity_and_numbers_in_bounds():
    source = (ROOT / "templates/crypto.html.j2").read_text()
    assert '#market-board .market-row{grid-template-columns:minmax(0,1fr) 100px 66px}' in source
    assert '#market-board .market-row>div{padding:10px 8px}' in source
    assert '#market-board .asset{grid-template-columns:20px minmax(0,1fr)' in source
    assert '#market-board .asset small{grid-column:2' in source
    assert '#market-board .market-value,#market-board .market-change{white-space:nowrap}' in source


def test_crypto_more_assets_remains_native_and_has_a_focus_target():
    source = (ROOT / "templates/crypto.html.j2").read_text()
    assert "t('More assets','更多资产')" in source
    assert 'Expand ranks 21–50' not in source
    assert '#market-board .more-market summary{min-height:40px' in source
    assert '#market-board .more-market summary:focus-visible' in source
    assert '<details class="more-market"><summary>' in source


def test_crypto_snapshot_and_market_headers_are_bilingual():
    source = (ROOT / "templates/crypto.html.j2").read_text()
    assert "t('Daily snapshot','每日快照')" in source
    assert "t('assets tracked','项资产已跟踪')" in source
    assert "t('24h change','24小时涨跌')" in source
    assert 'Daily class read' not in source


def test_crypto_published_market_table_keeps_all_live_quote_pairs():
    import re
    page = (ROOT / "site/crypto.html").read_text()
    start = page.index('role="table" aria-labelledby="crypto-market-title"')
    end = page.index('<details class="more-market">', start)
    board = page[start:end]
    prices = re.findall(r'class="market-value nb-px"[^>]+data-sym="([^"]+)"', board)
    changes = re.findall(r'class="market-change nb-chg"[^>]+data-sym="([^"]+)"', board)
    assert prices and prices == changes
    assert board.count('role="rowheader"') == len(prices)
    assert board.count('role="columnheader"') == 5
    assert page.count('id="crypto-market-title"') == 1


def test_crypto_canonical_control_css_matches_published_asset():
    import hashlib, re
    from jinja2 import Environment, FileSystemLoader
    source = (ROOT / "templates/crypto.html.j2").read_text()
    css_source = re.search(r'<style>(.*?)</style>', source, re.S).group(1)
    rendered = Environment(loader=FileSystemLoader(str(ROOT / "templates"))).from_string(css_source).render()
    page = (ROOT / "site/crypto.html").read_text()
    refs = re.findall(r'assets/css/([0-9a-f]{8})\.css\?v=\1', page)
    assets = [ROOT / "site" / "assets" / "css" / (ref + ".css") for ref in refs]
    matching = [p for p in assets if p.exists() and '#market-board .asset small' in p.read_text()]
    assert len(matching) == 1
    css = matching[0]
    assert hashlib.sha256(css.read_bytes()).hexdigest()[:8] == css.stem
    assert rendered.strip() in css.read_text()


def test_crypto_wide_symbols_do_not_overlap_names():
    source = (ROOT / "templates/crypto.html.j2").read_text()
    assert 'grid-template-columns:30px minmax(64px,max-content) minmax(0,1fr)' in source
    assert '<small title="{{ a.name }}">{{ a.name }}</small>' in source
