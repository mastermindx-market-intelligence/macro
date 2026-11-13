"""Tests for the S&P index-change announcement leg — collector parse + engine cohort/context."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import pytest

from collectors import sp_index_changes as C  # noqa: E402
from engine import index_changes as IC  # noqa: E402


# --------------------------------------------------------------------------- #
# collector parsing (pure)
# --------------------------------------------------------------------------- #
_RSS = """<rss><channel>
<item><title>First Advantage Set to Join S&amp;P SmallCap 600</title>
<link>https://press.spglobal.com/2026-06-11-First-Advantage-Set-to-Join-S-P-SmallCap-600</link>
<pubDate>Thu, 11 Jun 2026 18:41:00 -0400</pubDate></item>
<item><title>S&amp;P Dow Jones Indices Announces Q2 Earnings</title>
<link>https://press.spglobal.com/2026-06-10-earnings</link>
<pubDate>Wed, 10 Jun 2026 09:00:00 -0400</pubDate></item>
</channel></rss>"""

_PAGE = """<html><body><table><tr><td>Effective Date</td><td>Index Name</td><td>Action</td>
<td>Company Name</td><td>Ticker</td><td>GICS Sector</td></tr>
<tr><td>June 16, 2026</td><td>S&amp;P SmallCap 600</td><td>Addition</td>
<td>First Advantage</td><td>FA</td><td>Industrials</td></tr>
<tr><td>June 16, 2026</td><td>S&amp;P SmallCap 600</td><td>Deletion</td>
<td>Kennedy-Wilson Holdings</td><td>KW</td><td>Real Estate</td></tr></table></body></html>"""


def test_parse_rss_keeps_only_join_items():
    items = C.parse_rss(_RSS)
    assert len(items) == 1
    assert items[0]["announce_date"] == "2026-06-11"
    assert "First-Advantage" in items[0]["url"]


def test_parse_changes_page_extracts_table():
    rows = C.parse_changes_page(_PAGE, "http://x/fa", "2026-06-11")
    by_t = {r["ticker"]: r for r in rows}
    assert by_t["FA"]["action"] == "addition" and by_t["FA"]["index"] == "sp600"
    assert by_t["FA"]["effective_date"] == "2026-06-16"
    assert by_t["KW"]["action"] == "deletion"
    assert all(r["announce_date"] == "2026-06-11" for r in rows)


# --------------------------------------------------------------------------- #
# engine cohort classification (pure)
# --------------------------------------------------------------------------- #
def _pit(rows):
    df = pd.DataFrame(rows)
    df["sd"] = pd.to_datetime(df["start_date"])
    df["ed"] = pd.to_datetime(df["end_date"])
    return {t: g for t, g in df.groupby("ticker")}


def test_classify_pure_when_no_prior_membership():
    assert IC.classify_cohort("NEW", "2026-06-16", "sp600", {}) == "pure"


def test_classify_migration_when_prior_other_index():
    # was active in sp400 until ~the add date, now joining sp500 → forced seller in sp400
    pit = _pit([{"ticker": "MIG", "start_date": "2024-01-01", "end_date": "2026-06-15", "src": "sp400"}])
    assert IC.classify_cohort("MIG", "2026-06-16", "sp500", pit) == "migration"


def test_classify_readd_when_prior_same_index():
    pit = _pit([{"ticker": "RE", "start_date": "2020-01-01", "end_date": "2023-01-01", "src": "sp600"}])
    assert IC.classify_cohort("RE", "2026-06-16", "sp600", pit) == "readd"


# --------------------------------------------------------------------------- #
# engine context snapshot
# --------------------------------------------------------------------------- #
def _changes():
    return pd.DataFrame([
        {"ticker": "FA", "index": "sp600", "action": "addition",
         "effective_date": "2026-06-16", "announce_date": "2026-06-11", "company": "First Advantage"},
        {"ticker": "MIG", "index": "sp500", "action": "addition",
         "effective_date": "2026-06-18", "announce_date": "2026-06-12", "company": "Migrator"},
        {"ticker": "OLD", "index": "sp600", "action": "addition",
         "effective_date": "2026-01-01", "announce_date": "2025-12-20", "company": "Stale"},  # too old
        {"ticker": "KW", "index": "sp600", "action": "deletion",
         "effective_date": "2026-06-16", "announce_date": "2026-06-11", "company": "Target"},  # deletion ignored
    ])


def test_build_snapshot_context_only_and_splits_cohorts(monkeypatch):
    pit = _pit([{"ticker": "MIG", "start_date": "2024-01-01", "end_date": "2026-06-17", "src": "sp400"}])
    monkeypatch.setattr(IC, "pit_history", lambda: pit)
    monkeypatch.setattr(IC, "load_gate", lambda: {"announce_gross_scored": True,
                                                  "announce_net_scored": False,
                                                  "announce_tiers": {"sp600": True, "sp500": True}})
    snap = IC.build_snapshot(today=date(2026, 6, 21), changes=_changes())
    assert snap["is_context_only"] is True and snap["scored"] is False
    assert snap["gate"]["gross_scored"] is True and snap["gate"]["net_scored"] is False
    pure = [r["ticker"] for r in snap["pure_additions"]]
    other = [r["ticker"] for r in snap["other_additions"]]
    assert "FA" in pure and "MIG" in other            # FA pure, MIG migration
    assert "OLD" not in pure + other                  # stale (>10d past) dropped
    assert "KW" not in pure + other                   # deletion ignored
    fa = next(r for r in snap["pure_additions"] if r["ticker"] == "FA")
    assert fa["days_to_effective"] == -5 and fa["run_up_window_open"] is True


def test_build_snapshot_degrades_empty():
    snap = IC.build_snapshot(today=date(2026, 6, 21), changes=pd.DataFrame())
    assert snap["n_pure"] == 0 and snap["scored"] is False and snap["schema"] == IC.SCHEMA


# --------------------------------------------------------------------------- #
# validator regression — thin windows (>=10 events, <8 distinct months) must NOT crash
# (newey_west_tstat returns t/p=None there; _window must fail closed, not float(None))
# --------------------------------------------------------------------------- #
def test_window_thin_months_fails_closed_not_crash(monkeypatch):
    import scripts.validate_index_reconstitution as R
    monkeypatch.setattr(R, "_abn", lambda prices, t, d, a, b: 0.01)
    ev = pd.DataFrame({"ticker": [f"T{i}" for i in range(12)],
                       "d": pd.to_datetime(["2026-01-05", "2026-01-12", "2026-02-03", "2026-02-10",
                                            "2026-03-02", "2026-03-09", "2026-04-06", "2026-04-13",
                                            "2026-01-20", "2026-02-17", "2026-03-16", "2026-04-20"])})
    w = R._window(ev, None, -5, 0)               # 12 events / 4 months → no HAC-t
    assert w["n"] == 12 and w["n_months"] == 4
    assert "hac_t" not in w                       # omitted, not None → consumers .get('hac_t',0)
    assert w.get("hac_t", 0) == 0                  # fail-closed: not scored, no crash


@pytest.mark.parametrize('encoding', ['&amp;', '&#38;', '&#x26;', '&#160;', '&nbsp;', '&', '\u00a0'])
@pytest.mark.parametrize('warm', [False, True])
def test_raw_encoded_http_to_native_cache_and_snapshot(monkeypatch, tmp_path, encoding, warm):
    import json
    import requests
    from types import SimpleNamespace
    from lib import config
    from scripts import build_index_changes as B

    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path / 'data')
    monkeypatch.setattr(config, 'load', lambda: {'storage': {'site_dir': 'site'}})
    class Clock(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 21)
    monkeypatch.setattr(IC, 'date', Clock)
    literal = _PAGE.replace('&amp;', '&')
    if encoding in ['&#160;', '&nbsp;', '\u00a0']:
        page = literal.replace('S&P SmallCap', 'S&P' + encoding + 'SmallCap')
    else:
        page = literal.replace('S&P', 'S' + encoding + 'P')
    expected = C.parse_changes_page(literal, 'http://x/fa', '2026-06-11')
    assert C.parse_changes_page(page, 'http://x/fa', '2026-06-11') == expected
    cache = C._cache_path()
    if warm:
        old = {**expected[0], 'ticker': 'OLD', 'announce_url': 'http://old',
               'effective_date': '2020-01-01', '_seen': 'old'}
        pd.DataFrame([old]).to_parquet(cache)
    calls = []
    class Session:
        def __init__(self):
            self.headers = {}
        def get(self, url, timeout):
            calls.append(url)
            return SimpleNamespace(status_code=200, text=_RSS if url == C._RSS else page)
    monkeypatch.setattr(requests, 'Session', Session)
    assert B.main() == 0
    payload = json.loads((tmp_path / 'site/index_changes/latest.json').read_text())
    assert payload['n_pure'] == 1 and payload['pure_additions'][0]['ticker'] == 'FA'
    assert payload['scored'] is False and payload['is_context_only'] is True
    stored = pd.read_parquet(cache)
    assert set(stored.ticker) == ({'FA', 'KW', 'OLD'} if warm else {'FA', 'KW'})
    before = cache.read_bytes()
    assert B.main() == 0
    assert cache.read_bytes() == before  # already-seen announcement is not appended again
    assert len(calls) == 3  # RSS + new page, then RSS only


@pytest.mark.parametrize('has_announcement', [False, True])
@pytest.mark.parametrize('warm', [False, True])
def test_unparseable_announcement_warns_but_empty_feed_does_not(monkeypatch, tmp_path, caplog,
                                                              has_announcement, warm):
    import requests
    from types import SimpleNamespace
    from lib import config
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    cache = C._cache_path()
    if warm:
        pd.DataFrame([{'announce_url': 'http://old', 'ticker': 'OLD', 'action': 'addition'}]).to_parquet(cache)
    before = cache.read_bytes() if warm else None
    class Session:
        def __init__(self):
            self.headers = {}
        def get(self, url, timeout):
            rss = _RSS if has_announcement else '<rss><channel></channel></rss>'
            return SimpleNamespace(status_code=200, text=rss if url == C._RSS else '<html>unrecognized table</html>')
    monkeypatch.setattr(requests, 'Session', Session)
    result = C.fetch_index_changes()
    assert len(result) == (1 if warm else 0)
    assert ('not a verified no-change feed' in caplog.text) is has_announcement
    assert (cache.read_bytes() if cache.exists() else None) == before


def test_encoded_angle_brackets_are_text_not_markup():
    page = _PAGE.replace('First Advantage', 'First &lt;Advantage&gt; &amp; Co')
    rows = C.parse_changes_page(page, 'http://x/fa', '2026-06-11')
    assert rows[0]['company'] == 'First <Advantage> & Co'


@pytest.mark.parametrize('phrase', ['Set to Join', 'to join the', 'join'])
@pytest.mark.parametrize('amp', ['&amp;', '&#38;', '&#x26;'])
@pytest.mark.parametrize('mode', ['plain', 'escaped', 'cdata'])
@pytest.mark.parametrize('namespace', ['', 'urn:rss-test'])
def test_rss_xml_identity_before_filtering(phrase, amp, mode, namespace):
    url = 'https://press.spglobal.com/a?s=2429&item=999'
    wire = 'https://press.spglobal.com/a' if mode == 'plain' else (
        url.replace('&', '&amp;') if mode == 'escaped' else '<![CDATA[' + url + ']]>')
    expected = 'https://press.spglobal.com/a' if mode == 'plain' else url
    ns = ' xmlns="' + namespace + '"' if namespace else ''
    rss = f'<rss{ns}><channel><item><title>A {phrase} S{amp}P 500</title><link>{wire}</link></item></channel></rss>'
    assert C.parse_rss(rss) == [{'title': f'A {phrase} S&P 500', 'url': expected, 'announce_date': None}]


@pytest.mark.parametrize('bad', [
    '<rss><channel><item>', '<rss/>', '<html/>',
    '<rss><channel><item><title>Join S&bogus;P</title></item></channel></rss>',
    '<!DOCTYPE rss [<!ENTITY a "Join S&amp;P">]><rss><channel/></rss>',
])
def test_rss_invalid_document_preserves_cache(monkeypatch, tmp_path, caplog, bad):
    import requests
    from types import SimpleNamespace
    from lib import config
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    cache = C._cache_path()
    pd.DataFrame([{'announce_url': 'old', 'ticker': 'OLD'}]).to_parquet(cache)
    before = cache.read_bytes()
    calls = []
    class Session:
        def __init__(self): self.headers = {}
        def get(self, url, timeout):
            calls.append(url)
            return SimpleNamespace(status_code=200, text=bad)
    monkeypatch.setattr(requests, 'Session', Session)
    assert C.fetch_index_changes().ticker.tolist() == ['OLD']
    assert cache.read_bytes() == before
    assert calls == [C._RSS]
    assert 'RSS fetch failed' in caplog.text


def test_rss_cdata_decodes_once_and_ignores_nonitems():
    text = '<rss><channel><title>Join S&amp;P</title><link>wrong</link><item><title><![CDATA[A join S&P]]></title><link><![CDATA[https://x/?a=1&amp;b=2]]></link></item><item><title>Join S&amp;P</title><link> </link></item></channel></rss>'
    assert C.parse_rss(text) == [{'title':'A join S&P','url':'https://x/?a=1&amp;b=2','announce_date':None}]
    assert C.parse_rss('<rss><channel/></rss>') == []


@pytest.mark.parametrize('phrase', ['Set to Join', 'to join the', 'join'])
@pytest.mark.parametrize('amp', ['&amp;', '&#38;', '&#x26;'])
@pytest.mark.parametrize('mode', ['plain', 'escaped', 'cdata'])
@pytest.mark.parametrize('warm', [False, True])
def test_rss_xml_to_native_writer(monkeypatch, tmp_path, phrase, amp, mode, warm):
    import json
    import requests
    from types import SimpleNamespace
    from lib import config
    from scripts import build_index_changes as B
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path / 'data')
    monkeypatch.setattr(config, 'load', lambda: {'storage': {'site_dir': 'site'}})
    class Clock(date):
        @classmethod
        def today(cls): return cls(2026, 6, 21)
    monkeypatch.setattr(IC, 'date', Clock)
    url = 'https://press.spglobal.com/a' if mode == 'plain' else 'https://press.spglobal.com/a?s=2429&item=999'
    wire = '<![CDATA[' + url + ']]>' if mode == 'cdata' else url.replace('&', '&amp;')
    rss = f'<rss><channel><item><title>A {phrase} S{amp}P SmallCap 600</title><link>{wire}</link><pubDate>Thu, 11 Jun 2026 18:41:00 -0400</pubDate></item></channel></rss>'
    cache = C._cache_path()
    if warm:
        pd.DataFrame([{'ticker':'OLD','index':'sp600','action':'addition','effective_date':'2020-01-01','announce_date':'2019-12-20','company':'Old','announce_url':'https://old','_seen':'old'}]).to_parquet(cache)
    calls = []
    class Session:
        def __init__(self): self.headers = {}
        def get(self, target, timeout):
            calls.append(target)
            assert target in (C._RSS, url), 'XML-encoded request identity escaped boundary'
            return SimpleNamespace(status_code=200, text=rss if target == C._RSS else _PAGE)
    monkeypatch.setattr(requests, 'Session', Session)
    assert B.main() == 0
    payload = json.loads((tmp_path/'site/index_changes/latest.json').read_text())
    assert payload['n_pure'] == 1 and payload['pure_additions'][0]['ticker'] == 'FA'
    assert payload['scored'] is False and payload['is_context_only'] is True
    rows = pd.read_parquet(cache)
    assert set(rows[rows.announce_url == url].ticker) == {'FA', 'KW'}
    assert len(rows) == 2 + int(warm)
    before = cache.read_bytes()
    assert B.main() == 0
    assert cache.read_bytes() == before
    assert calls == [C._RSS, url, C._RSS]
