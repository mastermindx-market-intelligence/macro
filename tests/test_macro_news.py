"""Pure-function tests for the macro-news annotation layer — no network.
Validates the deterministic 'useful vs useless' filter, the catalyst calendar,
and that the LLM path stays off by default.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import macro_news as mn  # noqa: E402


def test_classify_theme_buckets():
    assert mn.classify_theme("Fed holds rates steady as inflation cools") == "inflation"
    assert mn.classify_theme("Jobs report shows payrolls surged") == "labor"
    assert mn.classify_theme("Recession fears grow as GDP slows") == "growth"
    assert mn.classify_theme("FOMC signals a rate cut") == "monetary"
    assert mn.classify_theme("Apple unveils a new iPhone") is None      # off-topic -> dropped


def test_filter_headlines_pipeline():
    # Two-tier contract: a tier-1 NEWS outlet is kept on source alone (the GDELT
    # query already matched macro terms in the body) and tagged 'macro' when the
    # title carries no keyword; a finance AGGREGATOR must clear the title theme
    # gate; an off-allowlist junk source is always dropped; dupes collapse.
    arts = [
        {"title": "Fed holds rates as inflation cools", "domain": "reuters.com",
         "seendate": "2026-06-14T10:00:00+00:00"},                       # theme + tier-1
        {"title": "Local village fair returns this weekend", "domain": "burytimes.co.uk",
         "seendate": "2026-06-14T09:30:00+00:00"},                       # junk source -> dropped
        {"title": "Trump weighs new China strategy", "domain": "cnbc.com",
         "seendate": "2026-06-14T09:00:00+00:00"},                       # tier-1, no title kw -> kept as 'macro'
        {"title": "3 reasons to sell this stock", "domain": "yahoo.com",
         "seendate": "2026-06-14T08:30:00+00:00"},                       # aggregator, non-macro -> dropped
        {"title": "Jobs report shows payrolls surged", "domain": "bloomberg.com",
         "seendate": "2026-06-13T08:00:00+00:00"},                       # theme + tier-1
        {"title": "Fed holds rates as inflation cools", "domain": "wsj.com",
         "seendate": "2026-06-12T08:00:00+00:00"},                       # duplicate title -> dropped
    ]
    kept = mn.filter_headlines(arts, {"max_show": 10})
    assert len(kept) == 3                                                # junk + aggregator-noise + dup removed
    assert {h["theme"] for h in kept} == {"inflation", "labor", "macro"}
    assert kept[0]["importance_score"] >= kept[-1]["importance_score"]    # intelligence-ranked, not newest-first
    assert all("theme" in h and h["url"] is not None for h in kept)


def test_filter_respects_custom_sources_and_cap():
    arts = [
        {"title": "Inflation rises again", "domain": "example-blog.com", "seendate": "2026-06-14T10:00:00Z"},
        {"title": "CPI surprises to the upside", "domain": "example-blog.com", "seendate": "2026-06-14T09:00:00Z"},
        {"title": "Treasury yield jumps on jobs data", "domain": "example-blog.com", "seendate": "2026-06-14T08:00:00Z"},
    ]
    kept = mn.filter_headlines(arts, {"sources": ["example-blog.com"], "max_show": 2})
    assert len(kept) == 2                                                # allowlisted + capped


def test_enriched_headline_importance_channels_and_tickers():
    arts = [{
        "title": "Federal Reserve rate decision lifts Treasury yields and bank stocks",
        "domain": "federalreserve.gov",
        "source": "official",
        "source_name": "Federal Reserve",
        "source_tier": "official",
        "seendate": "2026-06-18T10:00:00+00:00",
        "url": "https://example.com",
    }]
    kept = mn.filter_headlines(arts, {"max_show": 5})
    h = kept[0]
    assert h["importance"] == "high"
    assert h["importance_score"] >= 70
    assert "rates" in h["channels"]
    assert "IEF" in h["tickers"] or "XLF" in h["tickers"]
    assert h["related_tickers"]
    assert h["source_tier"] == "official"


def test_sec_regulatory_noise_is_deboosted():
    arts = [{
        "title": "SEC announces administrative proceeding and settles charges against issuer",
        "domain": "sec.gov",
        "source": "official",
        "source_name": "SEC - Press Releases",
        "source_tier": "official",
        "seendate": "2026-06-18T10:00:00+00:00",
        "url": "https://example.com",
    }, {
        "title": "CPI inflation report lifts Treasury yields",
        "domain": "bls.gov",
        "source": "official",
        "source_name": "BLS - CPI",
        "source_tier": "official",
        "seendate": "2026-06-18T09:00:00+00:00",
        "url": "https://example.com/cpi",
    }]
    kept = mn.filter_headlines(arts, {"max_show": 5})
    assert [h["source_name"] for h in kept] == ["BLS - CPI"]


def test_macro_synthesis_summarizes_channels_and_tickers():
    heads = mn.filter_headlines([{
        "title": "Federal Reserve rate decision lifts Treasury yields and bank stocks",
        "domain": "federalreserve.gov",
        "source": "official",
        "source_name": "Federal Reserve",
        "source_tier": "official",
        "seendate": "2026-06-18T10:00:00+00:00",
        "url": "https://example.com",
    }], {"max_show": 5})
    syn = mn._synthesis(heads)
    assert syn["high_impact_count"] == 1
    assert syn["top_channels"]
    assert syn["top_tickers"]


def test_stock_wire_qualitative_news_outranks_macro_prints():
    arts = [{
        "title": "Micron earnings are a must-watch event as profit growth accelerates",
        "domain": "marketwatch.com",
        "source": "news_rss",
        "source_name": "MarketWatch - Top Stories",
        "source_tier": "stock_wire",
        "theme": "earnings",         # feed declares earnings
        "seendate": "2026-06-18T09:00:00+00:00",
        "url": "https://example.com/mu",
    }, {
        "title": "CPI for all items rises 0.5% in May",
        "domain": "bls.gov",
        "source": "official",
        "source_name": "BLS - CPI",
        "source_tier": "official",
        "theme": "inflation",
        "seendate": "2026-06-18T10:00:00+00:00",
        "url": "https://example.com/cpi",
    }]
    kept = mn.filter_headlines(arts, {"max_show": 5})
    # After W1C fix 2, classify_theme runs first on the title. The growth bucket
    # deliberately carries NO bare "growth" token (only macro compounds like
    # "gdp growth"), so "profit growth accelerates" does NOT hijack this
    # earnings headline into the macro 'growth' theme — 'earnings' hits on the
    # "earnings" keyword and must win.
    micron = next((h for h in kept if "MU" in h.get("tickers", [])), None)
    assert micron is not None, "Micron item should be kept regardless of theme"
    assert micron["theme"] == "earnings", (
        f"earnings headline mislabeled as {micron['theme']!r} — bare 'growth' "
        "keyword collision regressed (see MACRO_THEMES growth-bucket note)")


def test_classify_theme_growth_vs_earnings_collision():
    """Bare 'growth' was removed from the growth bucket: corporate growth
    phrasings must classify 'earnings' (or fall to the declared theme), while
    genuine macro-growth phrasings still classify 'growth'."""
    assert mn.classify_theme("Micron profit growth accelerates on AI demand") == "earnings"
    assert mn.classify_theme("Netflix subscriber revenue growth beats estimates") == "earnings"
    # macro phrasings retained by the compound tokens
    assert mn.classify_theme("China's GDP growth slows to 4.2%") == "growth"
    assert mn.classify_theme("Global growth outlook dims, IMF warns") == "growth"
    assert mn.classify_theme("US economy shows signs of slowdown") == "growth"


def test_official_pages_drop_dateless_treasury_nav_chrome(monkeypatch):
    """Treasury list pages are scraped anchor-by-anchor; nav / section chrome
    ('Internal Revenue Service (IRS)', 'Revenue Proposals' from the Green Book
    sidebar) carries no date and must be dropped even though 'revenue' hands it an
    'earnings' theme — while a dated real release survives."""
    import requests
    html = (
        "<html><body><ul>"
        "<li><a href='/news/press-releases/jy9999'>Treasury Sanctions Network "
        "Financing Illicit Trade</a> 06/20/2026</li>"
        "<li><a href='/policy-issues/tax-policy/revenue-proposals'>Revenue Proposals</a></li>"
        "<li><a href='/about/internal-revenue-service'>Internal Revenue Service (IRS)</a></li>"
        "</ul></body></html>")

    class _Resp:
        status_code = 200
        text = html

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())
    items, _ = mn._fetch_official_pages({
        "official_pages": [{"name": "Treasury - Press Releases",
                            "url": "https://home.treasury.gov/news/press-releases",
                            "theme": "fiscal", "tier": "official"}],
        "official_window_days": 3650,
    }, date(2026, 6, 22))
    titles = [i["title"] for i in items]
    assert any("Treasury Sanctions" in t for t in titles)               # dated release kept
    assert "Revenue Proposals" not in titles                            # nav chrome dropped
    assert "Internal Revenue Service (IRS)" not in titles


def test_upcoming_catalysts_shape():
    cats = mn.upcoming_catalysts(date(2026, 6, 14), horizon_days=21)
    types = {c["type"] for c in cats}
    assert "FOMC" in types                                              # 2026-06-17 decision
    assert any(c["date"] == "2026-06-17" for c in cats)
    assert all(c["is_context_only"] for c in cats)
    assert all({"type", "date", "label"} <= set(c) for c in cats)
    assert cats == sorted(cats, key=lambda c: c["date"])               # sorted


def test_first_friday():
    assert mn._first_friday(2026, 7) == date(2026, 7, 3)
    assert mn._first_friday(2026, 5) == date(2026, 5, 1)


def test_queries_well_formed():
    qs = mn._queries({})
    assert qs, "_queries must emit at least one sub-query"
    for q in qs:
        assert q.startswith("(")
        assert "sourcecountry:US" in q and "sourcelang:eng" in q
    assert "federal reserve" in " ".join(qs).lower()


def test_llm_brief_off_by_default():
    # The keyless GDELT headline fetch ships ON (macro_news.enabled: true), but the
    # OPTIONAL LLM brief stays OFF unless llm_brief is set AND a key is present.
    assert mn.enabled() is True
    # brief never runs without headlines, and is gated off by default anyway
    assert mn.macro_brief([], "Goldilocks", "optimistic") is None
    assert mn.macro_brief([{"title": "x", "domain": "reuters.com", "theme": "monetary"}],
                          "Goldilocks", "optimistic (z=+1.0)") is None


# --------------------------------------------------------------------------- #
# W1C fix 2: theme priority inversion
# --------------------------------------------------------------------------- #
def test_theme_priority_content_beats_declared_feed_theme():
    """A title with inflation keywords from a feed declared theme='stocks' must
    be classified as 'inflation', not 'stocks'.
    (W1C fix 2: classify_theme runs first; declared_theme is fallback only)"""
    arts = [{
        "title": "France inflation drops to 1.8% in June, lowest since 2021",
        "domain": "seekingalpha.com",
        "seendate": "2026-06-14T10:00:00+00:00",
        "theme": "stocks",      # feed declares stocks
        "source": "news_rss",
        "source_tier": "stock_wire",
        "url": "https://seekingalpha.com/x",
    }]
    kept = mn.filter_headlines(arts, {"sources": ["seekingalpha.com"], "max_show": 5})
    assert len(kept) == 1, "inflation headline from stock-wire feed should be kept"
    assert kept[0]["theme"] == "inflation", (
        f"expected 'inflation' theme, got {kept[0]['theme']!r}")


def test_theme_fallback_to_declared_when_title_has_no_macro_keyword():
    """When the title has no macro keyword, the feed's declared theme is used as
    a fallback (if it is a valid macro theme). No regression on existing behavior."""
    arts = [{
        "title": "Federal Reserve holds benchmark rate steady",  # has keyword → monetary
        "domain": "reuters.com",
        "seendate": "2026-06-14T10:00:00+00:00",
        "theme": "credit",  # declared, but content wins
        "source": "news_rss",
        "source_tier": "tier1",
        "url": "https://reuters.com/x",
    }]
    kept = mn.filter_headlines(arts, {"max_show": 5})
    assert len(kept) == 1
    # "federal reserve" hits the monetary bucket → monetary wins over declared credit
    assert kept[0]["theme"] == "monetary"


# --------------------------------------------------------------------------- #
# W1C fix 3: RSS encoding
# --------------------------------------------------------------------------- #
def test_fetch_news_feeds_preserves_utf8_when_charset_header_missing(monkeypatch, tmp_path):
    """END-TO-END pin of W1C fix 3: drive _fetch_news_feeds through a fake
    requests.get whose response mirrors real requests semantics — UTF-8 bytes,
    encoding=None (no charset header), .text decodes with ISO-8859-1 unless the
    engine patches r.encoding first. Deleting the engine's encoding block makes
    this test fail with a mangled title ('Europeâ€™s...')."""
    import requests

    title_with_curly = "Europe’s economy faces headwinds"  # U+2019 right single quote
    rss_bytes = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        f'<item><title>{title_with_curly}</title>'
        '<link>https://economist.com/x</link>'
        '<pubDate>Thu, 09 Jul 2026 10:00:00 GMT</pubDate></item>'
        '</channel></rss>'
    ).encode("utf-8")

    class _Resp:
        status_code = 200
        apparent_encoding = "utf-8"
        headers = {}  # no Content-Type → no charset declared

        def __init__(self):
            self.encoding = None  # what requests sets when header lacks charset

        @property
        def text(self):
            # exact requests behavior: fall back to ISO-8859-1 when encoding unset
            return rss_bytes.decode(self.encoding or "iso-8859-1")

    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp())
    cfg = {
        "news_feeds": [{"name": "The Economist", "url": "https://economist.com/rss.xml",
                        "domain": "economist.com", "theme": "macro",
                        "source": "news_rss", "tier": "tier1"}],
        "news_cache_dir": str(tmp_path),  # keep cache writes out of data/
    }
    articles, reason = mn._fetch_news_feeds(cfg, today=date(2026, 7, 10))
    assert reason is None
    assert len(articles) == 1
    assert articles[0]["title"] == title_with_curly, (
        f"UTF-8 curly apostrophe mangled: {articles[0]['title']!r}")


# --------------------------------------------------------------------------- #
# W1C fix 4: subject map
# --------------------------------------------------------------------------- #
def test_macro_theme_to_qbus_map_exists_and_covers_all_macro_themes():
    """_MACRO_THEME_TO_QBUS must cover every key in MACRO_THEMES."""
    missing = set(mn.MACRO_THEMES.keys()) - set(mn._MACRO_THEME_TO_QBUS.keys())
    assert not missing, f"_MACRO_THEME_TO_QBUS is missing entries for: {missing}"


def test_macro_theme_to_qbus_stocks_maps_to_none():
    """'stocks' has no semantically honest qbus counterpart → maps to None (skip call).
    (W1C fix 4: earnings/guidance/analyst/deals/capital_return/stocks/macro → None)"""
    assert mn._MACRO_THEME_TO_QBUS["stocks"] is None
    assert mn._MACRO_THEME_TO_QBUS["earnings"] is None
    assert mn._MACRO_THEME_TO_QBUS["macro"] is None


def test_macro_theme_to_qbus_core_macro_themes_have_mappings():
    """Core macro themes that DO have qbus counterparts must map to a string."""
    assert mn._MACRO_THEME_TO_QBUS["monetary"] == "monetary"
    assert mn._MACRO_THEME_TO_QBUS["inflation"] == "inflation"
    assert mn._MACRO_THEME_TO_QBUS["growth"] == "growth"
    assert mn._MACRO_THEME_TO_QBUS["labor"] == "labor"
    assert mn._MACRO_THEME_TO_QBUS["credit"] == "credit"
    assert mn._MACRO_THEME_TO_QBUS["fiscal"] == "fiscal"


# --------------------------------------------------------------------------- #
# W1C fix 5: gdelt wiring to shared client
# --------------------------------------------------------------------------- #
def test_fetch_gdelt_calls_gdelt_client_get_articles(monkeypatch, tmp_path):
    """_fetch_gdelt must call gdelt_client.get_articles and preserve return shape.
    (W1C fix 5: HTTP layer replaced with shared throttle client)"""
    import engine.gdelt_client as gc

    captured = {}

    def _mock_get_articles(params, *, timeout=30, cache_path=None, cache_ttl_s=None,
                           min_interval=None):
        captured["params"] = params
        captured["timeout"] = timeout
        return (
            [{"title": "Fed holds rates", "url": "https://reuters.com/x",
              "domain": "reuters.com", "seendate": "2026-07-10T12:00:00+00:00",
              "language": "English", "sourcecountry": "US"}],
            None,
        )

    monkeypatch.setattr(gc, "get_articles", _mock_get_articles)
    # Redirect cache to tmp_path so we don't touch tracked paths
    monkeypatch.setattr(mn, "_cache_path",
                        lambda cfg, d: tmp_path / f"macro_v2_{d.isoformat()}.json")

    articles, reason = mn._fetch_gdelt({}, date(2026, 7, 10))

    assert captured.get("params") is not None, "gdelt_client.get_articles was not called"
    assert "query" in captured["params"]
    assert reason is None
    assert len(articles) == 1
    assert articles[0]["title"] == "Fed holds rates"
    assert articles[0]["domain"] == "reuters.com"
    assert articles[0]["seendate"] == "2026-07-10T12:00:00+00:00"


def test_fetch_gdelt_maps_no_articles_to_no_headlines(monkeypatch, tmp_path):
    """gdelt_client reason 'no_articles' must be mapped to 'no_headlines'.
    (W1C fix 5: reason token normalisation matching news_vector.py pattern)"""
    import engine.gdelt_client as gc

    monkeypatch.setattr(gc, "get_articles",
                        lambda *a, **k: ([], "no_articles"))
    monkeypatch.setattr(mn, "_cache_path",
                        lambda cfg, d: tmp_path / f"macro_v2_{d.isoformat()}.json")

    articles, reason = mn._fetch_gdelt({}, date(2026, 7, 10))
    assert articles == []
    assert reason == "no_headlines"


def test_fetch_gdelt_maps_rate_limited(monkeypatch, tmp_path):
    """gdelt_client reason 'rate_limited' is preserved as-is."""
    import engine.gdelt_client as gc

    monkeypatch.setattr(gc, "get_articles",
                        lambda *a, **k: (None, "rate_limited"))
    monkeypatch.setattr(mn, "_cache_path",
                        lambda cfg, d: tmp_path / f"macro_v2_{d.isoformat()}.json")

    articles, reason = mn._fetch_gdelt({}, date(2026, 7, 10))
    assert articles == []
    assert reason == "rate_limited"


def test_macro_synthesis_read_is_bilingual_and_deslugged():
    """read/read_zh are plain-word bilingual twins — no raw channel/tier slugs
    (doctrine Law 2: no untranslated slugs on user-facing surfaces)."""
    heads = mn.filter_headlines([{
        "title": "Federal Reserve rate decision lifts Treasury yields and bank stocks",
        "domain": "federalreserve.gov",
        "source": "official",
        "source_name": "Federal Reserve",
        "source_tier": "official",
        "seendate": "2026-06-18T10:00:00+00:00",
        "url": "https://example.com",
    }], {"max_show": 5})
    syn = mn._synthesis(heads)
    assert syn["read"] and "_" not in syn["read"]
    assert syn["read_zh"] and "_" not in syn["read_zh"]
    assert any("一" <= c <= "鿿" for c in syn["read_zh"])
    # structured fields keep raw slugs for machine consumers — unchanged contract
    assert syn["dominant_channel"] in mn.CHANNEL_LABEL
    # empty tape is bilingual too
    empty = mn._synthesis([])
    assert empty["read"] and empty["read_zh"]


def test_macro_synthesis_top_channels_carry_bilingual_labels():
    """top_channels entries ship {name, count, label_en, label_zh} so channel
    chips render plain words in both languages (doctrine Law 2 — no raw slugs);
    `name` stays the raw slug for machine consumers."""
    heads = mn.filter_headlines([{
        "title": "Federal Reserve rate decision lifts Treasury yields and bank stocks",
        "domain": "federalreserve.gov",
        "source": "official",
        "source_name": "Federal Reserve",
        "source_tier": "official",
        "seendate": "2026-06-18T10:00:00+00:00",
        "url": "https://example.com",
    }], {"max_show": 5})
    syn = mn._synthesis(heads)
    assert syn["top_channels"]
    for ch in syn["top_channels"]:
        assert ch["name"]  # machine slug retained
        assert ch["count"] >= 1
        assert ch["label_en"] and "_" not in ch["label_en"]
        assert ch["label_zh"]
    # mapped slugs get a true ZH twin, not just de-underscored EN
    mapped = [ch for ch in syn["top_channels"] if ch["name"] in mn.CHANNEL_LABEL]
    assert mapped
    assert all(any("一" <= c <= "鿿" for c in ch["label_zh"]) for ch in mapped)
    # unmapped slugs de-underscore instead of leaking raw
    en, zh = mn._slug_label("some_new_channel", mn.CHANNEL_LABEL)
    assert en == "some new channel" and zh == "some new channel"


def test_channel_label_has_zh_twins_for_all_21():
    assert len(mn.CHANNEL_LABEL) == 21
    for slug, (en, zh) in mn.CHANNEL_LABEL.items():
        assert en and "_" not in en, f"{slug} EN leaked underscore: {en!r}"
        assert any("\u4e00" <= c <= "\u9fff" for c in zh), f"{slug} ZH is not Chinese: {zh!r}"
    empty_en, empty_zh = mn._slug_label("", mn.CHANNEL_LABEL)
    assert empty_en == "" and empty_zh == ""


def test_load_upcoming_catalysts_failed_fetch_is_none(monkeypatch):
    def _boom(**_kw):
        raise OSError("calendar feed down")
    monkeypatch.setattr(mn, "upcoming_catalysts", _boom)
    assert mn.load_upcoming_catalysts(horizon_days=14) is None


def test_load_upcoming_catalysts_empty_is_list(monkeypatch):
    monkeypatch.setattr(mn, "upcoming_catalysts", lambda **_kw: [])
    got = mn.load_upcoming_catalysts(horizon_days=14)
    assert got == []
    assert got is not None


# --------------------------------------------------------------------------- #
# W2 qbus read-back — echo must actually attach to macro headlines
# (audit W2-PARTIAL: the item_id join never matched because macro headlines
# carried no _id; now _id shares the wire desks' basis + a title fallback)
# --------------------------------------------------------------------------- #
def _qbus_fixture_df():
    """Two crawls of the SAME Fed story from two desks/sources, clustered into
    one event_key — the minimal 'confirmed elsewhere' store."""
    import pandas as pd
    from engine import qbus
    rows = [
        {"desk": "news_vector", "source": "reuters.com",
         "url": "https://reuters.com/markets/fed-holds-rates",
         "title": "Fed holds interest rates steady",
         "seendate": "2026-06-19T12:00:00+00:00",
         "_crawled_at": "2026-06-19T12:05:00+00:00",
         "entities": [], "themes": ["monetary"], "lang": "en"},
        {"desk": "financial_news", "source": "cnbc.com",
         "url": "https://cnbc.com/2026/06/19/fed-decision.html",
         "title": "Fed holds interest rates steady in June",
         "seendate": "2026-06-19T13:00:00+00:00",
         "_crawled_at": "2026-06-19T13:02:00+00:00",
         "entities": [], "themes": ["monetary"], "lang": "en"},
    ]
    clustered = qbus.assign_event_keys(rows, thresh=0.4, window_days=3)
    assert clustered[0]["event_key"] == clustered[1]["event_key"]
    return pd.DataFrame(clustered, columns=list(qbus.COLUMNS))


def test_enrich_headline_populates_wire_desk_id():
    from engine import qkernel
    h = mn.enrich_headline({"title": "Fed holds interest rates steady",
                            "url": "https://reuters.com/markets/fed-holds-rates",
                            "domain": "reuters.com", "theme": "monetary",
                            "seendate": "2026-06-19T12:00:00+00:00"})
    assert h["_id"] == qkernel.item_id("reuters.com",
                                       "https://reuters.com/markets/fed-holds-rates",
                                       "Fed holds interest rates steady", "en")


def test_macro_headline_gets_echo_via_exact_item_id_join():
    df = _qbus_fixture_df()
    # same title + same host as the stored news_vector crawl → _id joins exactly
    h = mn.enrich_headline({"title": "Fed holds interest rates steady",
                            "url": "https://reuters.com/markets/fed-holds-rates",
                            "domain": "reuters.com", "theme": "monetary",
                            "seendate": "2026-06-19T12:00:00+00:00"})
    assert (df["item_id"] == h["_id"]).any()   # the join key really matches
    mn._attach_qbus_readback([h], date(2026, 6, 19), df)
    assert h.get("echo") == {"n_sources": 2, "n_desks": 2}


def test_macro_headline_gets_echo_via_title_fallback():
    df = _qbus_fixture_df()
    # different host (FT) → item_id can NOT match any stored row; the shingled
    # title fallback must still find the story's cluster.
    h = mn.enrich_headline({"title": "Fed holds interest rates steady",
                            "url": "https://www.ft.com/content/fed-holds",
                            "domain": "ft.com", "theme": "monetary",
                            "seendate": "2026-06-19T14:00:00+00:00"})
    assert not (df["item_id"] == h["_id"]).any()
    mn._attach_qbus_readback([h], date(2026, 6, 19), df)
    assert h.get("echo") == {"n_sources": 2, "n_desks": 2}


def test_macro_headline_unrelated_title_gets_no_echo():
    df = _qbus_fixture_df()
    h = mn.enrich_headline({"title": "Eurozone PMI slides to a nine-month low",
                            "url": "https://www.ft.com/content/pmi",
                            "domain": "ft.com", "theme": "growth",
                            "seendate": "2026-06-19T14:00:00+00:00"})
    mn._attach_qbus_readback([h], date(2026, 6, 19), df)
    assert "echo" not in h

# --------------------------------------------------------------------------- #
# F1: staleness decay — 29-day-old official item must rank below fresh 65
# --------------------------------------------------------------------------- #
def test_staleness_penalty_past_168h():
    """_freshness_points returns a negative penalty past 7 days, so a month-old
    official statement (base importance 68) sinks below a fresh item at 65."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    # 29 days ago → extra_weeks = (696-168)//168 = 3 → penalty = -6
    iso_29d = (now - timedelta(days=29)).isoformat()
    fp_old = mn._freshness_points(iso_29d)
    assert fp_old < 0, f"expected negative penalty for 29d-old item, got {fp_old}"
    # A fresh item (< 1h old)
    iso_fresh = (now - timedelta(minutes=30)).isoformat()
    fp_fresh = mn._freshness_points(iso_fresh)
    assert fp_fresh > 0
    # The exact live ordering: FOMC-style (base 68) vs fresh 65-scorer
    old_intel = 68 + fp_old
    fresh_65_intel = 65 + fp_fresh
    assert old_intel < fresh_65_intel, (
        f"29d official intel {old_intel} should be < fresh-65 intel {fresh_65_intel}")


def test_staleness_penalty_is_floored_at_minus_12():
    """penalty never drops below -12 regardless of age."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    # 2 years old → extra_weeks >> 6 → floor at -12
    iso_very_old = (now - timedelta(days=730)).isoformat()
    fp = mn._freshness_points(iso_very_old)
    assert fp == -12, f"expected floor -12 for 2y-old item, got {fp}"


def test_staleness_bonus_curve_unchanged():
    """The 0-168h bonus curve must be unchanged: 7/5/3/1 for <=8/24/72/168h.
    Uses offsets relative to 'now' so the test is time-independent."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    def _iso(h_ago: float) -> str:
        return (now - timedelta(hours=h_ago)).isoformat()
    assert mn._freshness_points(_iso(2)) == 7     # 2h ago -> <=8h bucket
    assert mn._freshness_points(_iso(12)) == 5    # 12h ago -> <=24h bucket
    assert mn._freshness_points(_iso(48)) == 3    # 48h ago -> <=72h bucket
    assert mn._freshness_points(_iso(100)) == 1   # 100h ago -> <=168h bucket


# --------------------------------------------------------------------------- #
# F2/MN-03: official same-event dedup
# --------------------------------------------------------------------------- #
def test_official_same_event_dedup_collapses_fomc_pair():
    """The 2026-06-17 FOMC pair (statement + projections) from federalreserve.gov
    on the same seendate must collapse to a single item in filter_headlines."""
    arts = [
        {
            "title": "Federal Reserve issues FOMC statement",
            "domain": "federalreserve.gov",
            "source": "official",
            "source_name": "Federal Reserve - Monetary Policy",
            "source_tier": "official",
            "seendate": "2026-06-17T18:00:00",
            "url": "https://federalreserve.gov/a",
        },
        {
            "title": "Federal Reserve Board and Federal Open Market Committee release economic projections",
            "domain": "federalreserve.gov",
            "source": "official",
            "source_name": "Federal Reserve - Monetary Policy",
            "source_tier": "official",
            "seendate": "2026-06-17T18:00:00",
            "url": "https://federalreserve.gov/b",
        },
    ]
    kept = mn.filter_headlines(arts, {"max_show": 10, "min_importance_score": 0})
    assert len(kept) == 1, (
        f"expected 1 item after official same-event dedup, got {len(kept)}: "
        + str([h["title"] for h in kept]))


def test_official_dedup_different_domains_not_collapsed():
    """Items from different official domains on the same date must NOT collapse."""
    arts = [
        {
            "title": "Federal Reserve issues FOMC statement",
            "domain": "federalreserve.gov",
            "source": "official",
            "source_name": "Federal Reserve",
            "source_tier": "official",
            "seendate": "2026-06-17T18:00:00",
            "url": "https://federalreserve.gov/a",
        },
        {
            "title": "BLS reports CPI rose 0.3% in May",
            "domain": "bls.gov",
            "source": "official",
            "source_name": "BLS - CPI",
            "source_tier": "official",
            "seendate": "2026-06-17T08:00:00",
            "url": "https://bls.gov/b",
        },
    ]
    kept = mn.filter_headlines(arts, {"max_show": 10, "min_importance_score": 0})
    assert len(kept) == 2, (
        f"items from different official domains must not collapse, got {len(kept)}")


def test_official_dedup_non_official_items_unaffected():
    """Non-official items sharing the same domain and date are NOT collapsed."""
    arts = [
        {
            "title": "Fed raises rates by 25bp in June meeting",
            "domain": "reuters.com",
            "source": "news_rss",
            "source_tier": "tier1",
            "seendate": "2026-06-17T18:00:00",
            "url": "https://reuters.com/a",
        },
        {
            "title": "Federal Open Market Committee signals rate pause into Q3",
            "domain": "reuters.com",
            "source": "news_rss",
            "source_tier": "tier1",
            "seendate": "2026-06-17T19:00:00",
            "url": "https://reuters.com/b",
        },
    ]
    kept = mn.filter_headlines(arts, {"max_show": 10, "min_importance_score": 0})
    # Both are tier1 (non-official); dedup is title-prefix only; both should survive
    assert len(kept) == 2, (
        f"non-official items from same domain on same date must not be collapsed, "
        f"got {len(kept)}")


# --------------------------------------------------------------------------- #
# F5/MN-07: Fed enforcement de-boost
# --------------------------------------------------------------------------- #
def test_fed_enforcement_action_is_deboosted():
    """'Federal Reserve Board issues enforcement action with TS Banking Group'
    must score below a genuine macro story — the regulatory_plumbing_noise check
    now covers federalreserve.gov enforcement items, not just SEC."""
    arts = [
        {
            "title": "Federal Reserve Board issues enforcement action with TS Banking Group",
            "domain": "federalreserve.gov",
            "source": "official",
            "source_name": "Federal Reserve - All Press",
            "source_tier": "official",
            "seendate": "2026-07-16T12:00:00+00:00",
            "url": "https://federalreserve.gov/enforce/x",
        },
        {
            "title": "Federal Reserve holds rates steady, signals caution on inflation",
            "domain": "federalreserve.gov",
            "source": "official",
            "source_name": "Federal Reserve - Monetary Policy",
            "source_tier": "official",
            "seendate": "2026-07-16T14:00:00+00:00",
            "url": "https://federalreserve.gov/fomc/x",
        },
    ]
    kept = mn.filter_headlines(arts, {"max_show": 10, "min_importance_score": 0})
    # The monetary policy release must rank above the enforcement action
    if len(kept) >= 2:
        titles = [h["title"] for h in kept]
        enforce_idx = next(i for i, t in enumerate(titles) if "enforcement" in t.lower())
        fomc_idx = next(i for i, t in enumerate(titles) if "holds rates" in t.lower())
        assert enforce_idx > fomc_idx, (
            f"enforcement action ranked above FOMC release: {titles}")
    # With MN-03 dedup both collapse to 1 (same domain, same date, same theme=monetary).
    # The surviving item should NOT be the enforcement action.
    assert len(kept) >= 1
    assert "enforcement" not in kept[0]["title"].lower(), (
        f"enforcement action should not win after de-boost: {kept[0]['title']}")


# --------------------------------------------------------------------------- #
# F6: future-date guard in _fetch_official_pages
# --------------------------------------------------------------------------- #
def test_official_pages_drops_future_dated_nav_anchors(monkeypatch):
    """Items dated > today + 30d must be dropped — they are scheduled-meeting
    nav links, not real releases."""
    import requests
    html = (
        "<html><body><ul>"
        "<li><a href='/news/1'>Treasury Sanctions Network</a> 06/20/2026</li>"
        "<li><a href='/future/1'>FOMC Meeting Schedule</a> 08/17/2026</li>"
        "</ul></body></html>"
    )

    class _Resp:
        status_code = 200
        text = html

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())
    items, _ = mn._fetch_official_pages({
        "official_pages": [{"name": "Treasury - Press Releases",
                            "url": "https://home.treasury.gov/news/press-releases",
                            "theme": "fiscal", "tier": "official"}],
        "official_window_days": 3650,
    }, date(2026, 7, 16))
    titles = [i["title"] for i in items]
    assert any("Treasury Sanctions" in t for t in titles), "dated release should be kept"
    # 08/17/2026 is > 2026-07-16 + 30d → should be dropped
    assert not any("FOMC Meeting Schedule" in t for t in titles), (
        "future-dated nav anchor should be dropped")


# --------------------------------------------------------------------------- #
# W0: rejected rows carry 'feed' field
# --------------------------------------------------------------------------- #
def test_filter_headlines_rejected_rows_carry_feed_field():
    """Rejected items appended to the _rejected list must include a 'feed' key."""
    arts = [{
        "title": "Analyst Report: AAPL",
        "domain": "yahoo.com",
        "source": "yahoo_finance",
        "source_tier": "quality",
        "seendate": "2026-07-16T12:00:00+00:00",
        "url": "https://yahoo.com/x",
    }]
    rejected: list[dict] = []
    mn.filter_headlines(arts, {"max_show": 5, "min_importance_score": 0},
                        _rejected=rejected)
    assert len(rejected) == 1, "analyst_report_stub should be rejected"
    assert "feed" in rejected[0], f"rejected row missing 'feed' key: {rejected[0]}"
    assert rejected[0]["feed"] == "yahoo_finance"


# --------------------------------------------------------------------------- #
# F5 unit: _regulatory_plumbing_noise helper
# --------------------------------------------------------------------------- #
def test_regulatory_plumbing_noise_sec_still_fires():
    """Original SEC enforcement detection must still work after rename/widening."""
    assert mn._regulatory_plumbing_noise(
        "SEC announces administrative proceeding", "SEC - Press Releases", "sec.gov")
    assert not mn._regulatory_plumbing_noise(
        "Federal Reserve cuts rates by 25bp", "", "federalreserve.gov")


def test_official_cache_success_records_fetched_at_not_publication_time(monkeypatch, tmp_path):
    import json
    from datetime import datetime, timezone

    rss = (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        "<item><title>Federal Reserve issues FOMC statement</title>"
        "<link>https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm</link>"
        "<pubDate>Wed, 29 Jul 2026 18:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )

    class _Resp:
        status_code = 200
        encoding = "utf-8"
        apparent_encoding = "utf-8"
        headers = {"Content-Type": "application/rss+xml; charset=utf-8"}
        text = rss

    monkeypatch.setattr("requests.get", lambda *a, **k: _Resp())
    before = datetime.now(timezone.utc)
    cfg = {
        "official_feeds": [{"name": "Federal Reserve - Monetary Policy",
                            "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
                            "theme": "monetary", "tier": "official"}],
        "official_cache_dir": str(tmp_path),
        "use_official_pages": False,
        "official_window_days": 3650,
    }
    articles, reason = mn._fetch_official_feeds(cfg, today=date(2026, 9, 8))
    after = datetime.now(timezone.utc)
    assert reason is None
    assert articles and articles[0]["seendate"].startswith("2026-07-29")
    cache = tmp_path / "official_v3_2026-09-08.json"
    blob = json.loads(cache.read_text(encoding="utf-8"))
    fetched = datetime.fromisoformat(blob["fetched_at"].replace("Z", "+00:00"))
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    assert before <= fetched <= after
    assert blob["feed_status"] == "ok"
    assert blob["feeds"][0]["status"] == "ok"
    assert blob["feed_status"] != "live"


def test_official_cache_failed_feed_is_not_success(monkeypatch, tmp_path):
    import json

    rss = (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        "<item><title>Warsh speech</title>"
        "<link>https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm</link>"
        "<pubDate>Fri, 28 Aug 2026 14:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )

    class _Ok:
        status_code = 200
        encoding = "utf-8"
        apparent_encoding = "utf-8"
        headers = {"Content-Type": "application/rss+xml; charset=utf-8"}
        text = rss

    class _Fail:
        status_code = 503
        encoding = "utf-8"
        apparent_encoding = "utf-8"
        headers = {}
        text = ""

    def _get(url, **_k):
        if "speeches" in url:
            return _Fail()
        return _Ok()

    monkeypatch.setattr("requests.get", _get)
    cfg = {
        "official_feeds": [
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
             "theme": "monetary", "tier": "official"},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml",
             "theme": "monetary", "tier": "official"},
        ],
        "official_cache_dir": str(tmp_path),
        "use_official_pages": False,
        "official_window_days": 3650,
    }
    articles, reason = mn._fetch_official_feeds(cfg, today=date(2026, 9, 8))
    blob = json.loads((tmp_path / "official_v3_2026-09-08.json").read_text(encoding="utf-8"))
    assert blob["feed_status"] == "mixed"
    assert blob["feed_status"] != "live"
    statuses = {row["name"]: row["status"] for row in blob["feeds"]}
    assert statuses["Federal Reserve - Monetary Policy"] == "ok"
    assert statuses["Federal Reserve - Speeches"] == "fail"
    assert articles
    assert articles[0]["seendate"].startswith("2026-08-28")


def test_official_legacy_cache_without_fetched_at_still_reads(monkeypatch, tmp_path):
    import json

    cache = tmp_path / "official_v3_2026-09-08.json"
    cache.write_text(json.dumps({
        "articles": [{"title": "legacy", "url": "https://www.federalreserve.gov/x",
                      "seendate": "2026-07-29T18:00:00+00:00"}],
        "degraded_reason": None,
    }), encoding="utf-8")
    cfg = {
        "official_feeds": [{"name": "x", "url": "https://example.test/feed",
                            "theme": "monetary", "tier": "official"}],
        "official_cache_dir": str(tmp_path),
        "use_official_pages": False,
        "official_cache_ttl_hours": 24,
    }

    def boom(*_a, **_k):
        raise AssertionError("legacy cache must not refetch")

    monkeypatch.setattr("requests.get", boom)
    articles, reason = mn._fetch_official_feeds(cfg, today=date(2026, 9, 8))
    assert reason is None
    assert articles[0]["title"] == "legacy"
    assert articles[0]["seendate"].startswith("2026-07-29")


# --------------------------------------------------------------------------- #
# GDELT bounded sub-query contract
# --------------------------------------------------------------------------- #
# This module shipped ONE 400-char OR-query. GDELT answers an over-long query
# with HTTP 200 + text/html "Your query was too short or too long." — a
# STRUCTURAL rejection no retry can heal — so the global-wire leg contributed
# ZERO articles on every nightly fetch while the official/RSS legs kept the
# board looking full. Production log:
#   "GDELT REJECTED the query (len=400) — STRUCTURAL, not retried"
# Re-probed live against api.gdeltproject.org on 2026-09-18: still rejected.
# The sibling engine/news_vector.py hit the same server-side tightening in
# 2026-06 and already answers it with bounded sub-queries; these tests pin the
# same contract here.
#
# The fake below is a FIDELITY provider: it is installed at the `requests.get`
# boundary, so every assertion runs through the REAL engine.gdelt_client —
# its content-type guard, its _REJECTED_MARKERS classification, its
# _parse_articles normalisation, its rate-limit breaker and its cache rules.
# --------------------------------------------------------------------------- #

# GDELT's real server-side ceiling sits between 246 (accepted) and 288
# (rejected), probed 2026-07-10. The fake rejects above 260 so that a regression
# to the old single query is caught even though _MAX_QUERY_LEN leaves headroom.
_FAKE_SERVER_LIMIT = 260


class _FakeGdeltResponse:
    """Minimal requests.Response stand-in."""

    def __init__(self, status, *, body=None, json_body=None, content_type):
        self.status_code = status
        self.text = body if body is not None else ""
        self.headers = {"Content-Type": content_type}
        self._json = json_body

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def _fake_gdelt_server(*, limit=_FAKE_SERVER_LIMIT, catalogue=None, calls=None,
                       status_for=None, reject_if=None, verdicts=None):
    """Build a requests.get replacement that answers like the live GDELT doc API.

    * query longer than `limit`  -> 200 + text/html + the real rejection body
    * otherwise                  -> 200 + application/json artlist containing
                                    every catalogue article whose `terms` appear
                                    in the sub-query (so coverage is observable)
    `status_for(query)` may override with an HTTP status (e.g. 429) to exercise
    the transient path; `reject_if(query)` rejects a NAMED sub-query regardless
    of its length, so partial-failure mixes can be built deterministically.
    `verdicts` collects "accepted"/"rejected" per request so a test can assert the
    PROVIDER's answer instead of re-reading the constant it is supposed to guard.
    """
    catalogue = catalogue if catalogue is not None else []

    def _get(url, params=None, timeout=None, headers=None):
        q = (params or {}).get("query", "")
        if calls is not None:
            calls.append(q)
        if status_for is not None:
            forced = status_for(q)
            if forced is not None:
                return _FakeGdeltResponse(forced, body="rate limited",
                                          content_type="text/html; charset=utf-8")
        if len(q) > limit or (reject_if is not None and reject_if(q)):
            if verdicts is not None:
                verdicts.append("rejected")
            # byte-for-byte the live body (probed 2026-09-18)
            return _FakeGdeltResponse(
                200, body="Your query was too short or too long.\n",
                content_type="text/html; charset=utf-8")
        if verdicts is not None:
            verdicts.append("accepted")
        arts = [a for a in catalogue if a["term"] in q]
        return _FakeGdeltResponse(
            200, content_type="application/json",
            json_body={"articles": [
                {"title": a["title"], "url": a["url"], "domain": a["domain"],
                 "seendate": "20260918T120000Z"} for a in arts]})

    return _get


def _isolate_gdelt(monkeypatch, tmp_path):
    """Point the shared client's throttle stamp AND its rate-limit breaker at
    tmp_path (gdelt_client derives the breaker path from the stamp path), and
    point macro_news's day-cache there too. Hermetic: no tracked path touched.

    The pacing floor is neutralised at gdelt_client's OWN resolver rather than by
    a config key, because macro_news deliberately passes no min_interval — the
    shared floor is the only pacing policy over this budget."""
    import engine.gdelt_client as gc
    monkeypatch.setattr(gc, "_stamp_path",
                        lambda: tmp_path / "gdelt" / "last_request")
    monkeypatch.setattr(gc, "_min_interval", lambda: 0.0)
    (tmp_path / "gdelt").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mn, "_cache_path",
                        lambda cfg, d: tmp_path / f"macro_v2_{d.isoformat()}.json")
    return gc


_CFG = {"window_days": 2, "max_records": 50, "cache_ttl_hours": 12}


def test_prefix_the_bug_single_query_over_whole_term_set_is_rejected(monkeypatch, tmp_path):
    """THE REGRESSION. Building ONE OR-query over the whole term set — what this
    module did until now — is rejected by the provider as STRUCTURAL."""
    import engine.gdelt_client as gc
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    monkeypatch.setattr(requests, "get", _fake_gdelt_server())

    legacy = ("(" + " OR ".join(mn._QUERY_CORE) + ")"
              + " sourcecountry:US sourcelang:eng")
    # (it was exactly 400 chars when the bug was found; the SUBJECT of this test is
    # the rejection, so the assertion is on the verdict, not on that number)
    arts, reason = gc.get_articles(
        {"query": legacy, "mode": "artlist", "format": "json"}, min_interval=0)
    assert arts is None
    assert reason == "query_rejected", (
        f"the pre-fix single query ({len(legacy)} chars) must be classified "
        "STRUCTURAL, not retried")


def test_every_emitted_request_satisfies_the_bounded_query_contract(monkeypatch, tmp_path):
    """Every query macro_news puts on the wire is ACCEPTED by a provider that
    enforces the real server limit. The judge is the provider's verdict, never
    `_MAX_QUERY_LEN` — comparing the emitted length to the very constant under
    test would pass just as happily with the bound reverted to a huge value."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    calls: list[str] = []
    verdicts: list[str] = []
    monkeypatch.setattr(requests, "get",
                        _fake_gdelt_server(calls=calls, verdicts=verdicts))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert calls, "no request reached the transport"
    assert verdicts == ["accepted"] * len(calls), (
        f"the provider rejected {verdicts.count('rejected')} of {len(calls)} "
        f"emitted queries; lengths were {[len(q) for q in calls]} against a "
        f"{_FAKE_SERVER_LIMIT}-char server limit")
    assert reason != "query_rejected"
    # secondary: the module's own bound must be at least as strict as the server's
    assert mn._MAX_QUERY_LEN <= _FAKE_SERVER_LIMIT


def test_subqueries_cover_the_term_set_exactly(monkeypatch, tmp_path):
    """Source coverage is EXACT: splitting must not drop, duplicate or reorder a
    term. An OR-query partitions losslessly, so the union of the sub-queries asks
    for precisely what the single query asked for."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    calls: list[str] = []
    verdicts: list[str] = []
    monkeypatch.setattr(requests, "get",
                        _fake_gdelt_server(calls=calls, verdicts=verdicts))

    mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert "rejected" not in verdicts, (
        "coverage counted from queries the provider refused is not coverage")
    emitted: list[str] = []
    for q in calls:
        inner = q[1:q.index(")")]
        emitted += [t.strip() for t in inner.split(" OR ")]
    assert emitted == mn._QUERY_CORE, (
        "sub-queries must cover the term set exactly, in order\n"
        f"  missing: {[t for t in mn._QUERY_CORE if t not in emitted]}\n"
        f"  extra:   {[t for t in emitted if t not in mn._QUERY_CORE]}")


def test_term_set_is_ascii_so_the_character_bound_is_the_wire_length():
    """_MAX_QUERY_LEN counts CHARACTERS. GDELT's limit applies to what goes on the
    wire, so a non-ASCII term would make the two diverge (one CJK char = 3 UTF-8
    bytes = 9 percent-encoded characters) and the splitter would pack queries that
    look bounded here and get rejected there."""
    for t in mn._QUERY_CORE:
        assert t.isascii(), f"non-ASCII term breaks the length bound: {t!r}"
    for q in mn._queries({}):
        assert len(q) == len(q.encode("utf-8")), f"query is not 1 byte/char: {q!r}"


def test_no_single_term_can_bust_the_budget():
    """The splitter's contract is only satisfiable while every term FITS. A term
    longer than one group's budget would be emitted alone and still be rejected —
    fail here, in CI, rather than silently darkening the wire in production."""
    suffix = " sourcecountry:US sourcelang:eng"
    budget = mn._MAX_QUERY_LEN - len(suffix) - 2
    too_long = [t for t in mn._QUERY_CORE if len(t) > budget]
    assert not too_long, f"terms that cannot fit a sub-query: {too_long}"


def test_split_is_deterministic():
    """A stable fan-out is what makes the shared per-IP budget predictable."""
    assert mn._queries({}) == mn._queries({})
    assert len(mn._queries({})) >= 2, "the term set must actually split"


def test_union_dedupes_articles_matched_by_more_than_one_subquery(monkeypatch, tmp_path):
    """A story matching terms in two sub-queries is returned ONCE."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    # "inflation" is in sub-query 1, "rate cut" in sub-query 2 -> the same article
    # is served by both; "powell" is served only by sub-query 2.
    catalogue = [
        {"term": "inflation", "title": "Fed weighs a rate cut as inflation cools",
         "url": "https://reuters.com/a", "domain": "reuters.com"},
        {"term": '"rate cut"', "title": "Fed weighs a rate cut as inflation cools",
         "url": "https://reuters.com/a", "domain": "reuters.com"},
        {"term": "powell", "title": "Powell testifies on the outlook",
         "url": "https://reuters.com/b", "domain": "reuters.com"},
    ]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(catalogue=catalogue))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert reason is None
    titles = sorted(a["title"] for a in arts)
    assert titles == ["Fed weighs a rate cut as inflation cools",
                      "Powell testifies on the outlook"], titles
    keys = [(a["title"], a["domain"]) for a in arts]
    assert len(keys) == len(set(keys)), "duplicate (title, domain) survived the union"


def test_all_requests_go_through_the_one_shared_rate_limiter(monkeypatch, tmp_path):
    """macro_news must own NO transport of its own: every sub-query goes through
    engine.gdelt_client, which holds the single cross-process per-IP pace lock
    (nine uncoordinated callers caused the 2026-06-20 429 penalty-box incident).
    The fan-out must therefore spend the shared budget, never a private one."""
    import engine.gdelt_client as gc
    _isolate_gdelt(monkeypatch, tmp_path)

    seen = []
    real = gc.get_articles

    def _spy(params, **kw):
        seen.append(kw)
        return ([], "no_articles")

    monkeypatch.setattr(gc, "get_articles", _spy)
    # any direct HTTP from macro_news would bypass the shared lock entirely
    import requests

    def _boom(*a, **k):
        raise AssertionError("macro_news opened its own transport — the shared "
                             "per-IP pace lock was bypassed")

    monkeypatch.setattr(requests, "get", _boom)

    mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert len(seen) == len(mn._queries(_CFG)), "one shared-client call per sub-query"
    for kw in seen:
        assert kw.get("min_interval") is None, (
            "macro_news must NOT pass its own min_interval — the pacing floor is "
            "ONE shared global number (gdelt.min_request_interval_s), and a "
            "module-local override is a second throttle policy over one budget")
    assert real is not gc.get_articles   # spy installed (guards a silent no-op)


def test_armed_circuit_breaker_short_circuits_the_whole_fan_out(monkeypatch, tmp_path):
    """When a prior caller proved the IP is 429-boxed, the fan-out must cost ZERO
    network calls — a multi-sub-query leg must not multiply the boxed-IP stall
    the breaker exists to prevent."""
    import time
    gc = _isolate_gdelt(monkeypatch, tmp_path)
    gc._penalty_path().write_text(str(time.time() + 600))   # breaker armed
    import requests

    def _boom(*a, **k):
        raise AssertionError("hit the network while the breaker was armed")

    monkeypatch.setattr(requests, "get", _boom)

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert arts == []
    assert reason == "rate_limited"


def test_partial_success_keeps_articles_and_reports_the_worst_reason(monkeypatch, tmp_path):
    """One sub-query succeeds, one is structurally rejected: the good articles are
    KEPT (partial success) and the reason reports the WORST outcome, so a rejected
    sub-query cannot hide behind the one that worked."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    qs = mn._queries(_CFG)
    assert len(qs) >= 2, "this test needs a term set that splits"
    last = qs[-1]
    catalogue = [{"term": "inflation", "title": "Inflation cools in August",
                  "url": "https://reuters.com/a", "domain": "reuters.com"}]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(
        catalogue=catalogue, reject_if=lambda q: q == last))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert [a["title"] for a in arts] == ["Inflation cools in August"], (
        "the successful sub-query's articles must survive its sibling's rejection")
    assert reason == "query_rejected", (
        "a structurally rejected sub-query must outrank its successful siblings")
    assert not (tmp_path / "macro_v2_2026-09-18.json").exists(), (
        "a PARTIAL harvest must not be cached: replaying it would freeze the "
        "missing term groups out for the whole 12h TTL and silence the alarm")


def test_structural_rejection_is_not_retried_but_does_not_abort_siblings(monkeypatch, tmp_path):
    """Structural != transient. A rejection is issued ONCE per sub-query (no
    retry burns the shared budget) and the remaining sub-queries still run."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    calls: list[str] = []
    # limit 0 -> every sub-query is rejected
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(limit=0, calls=calls))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert arts == []
    assert reason == "query_rejected"
    assert len(calls) >= 2, "the term set must actually split for this test"
    assert len(calls) == len(set(calls)), (
        "a rejection must cost exactly ONE request per sub-query — a retry would "
        f"repeat a query; got {len(calls)} calls, {len(set(calls))} distinct")


def test_transient_rate_limit_costs_the_shared_budget_only_once(monkeypatch, tmp_path):
    """A 429 is per-IP, so the rest of the fan-out is doomed — but the SHARED
    breaker is what must stop it, not a private early-abort in this module. The
    first sub-query pays gdelt_client's bounded retry and arms the breaker; every
    later sub-query then short-circuits with ZERO network calls."""
    gc = _isolate_gdelt(monkeypatch, tmp_path)
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)    # skip the real backoff
    import requests
    calls: list[str] = []
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(
        calls=calls, status_for=lambda q: 429))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert arts == []
    assert reason == "rate_limited"
    # exactly one sub-query reached the network, three times (1 + 2 bounded retries)
    assert len(set(calls)) == 1, (
        f"a second sub-query hit the network after the 429: {len(set(calls))} distinct")
    assert len(calls) == 3, f"expected 1 call + 2 bounded retries, got {len(calls)}"
    assert gc._penalty_active(), "the terminal 429 must arm the SHARED breaker"


def test_rate_limit_does_not_abandon_coverage_when_the_breaker_is_off(monkeypatch, tmp_path):
    """gdelt.rate_limit_cooldown_s: 0 is a documented off-switch. With the shared
    breaker disabled, a 429 on one sub-query must NOT cost the others their
    coverage — the sibling engine.news_vector makes the same choice."""
    gc = _isolate_gdelt(monkeypatch, tmp_path)
    monkeypatch.setattr(gc, "_cooldown", lambda: 0.0)        # breaker OFF
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    import requests
    qs = mn._queries({})
    first = qs[0]
    catalogue = [{"term": "powell", "title": "Powell testifies on the outlook",
                  "url": "https://reuters.com/b", "domain": "reuters.com"}]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(
        catalogue=catalogue, status_for=lambda q: 429 if q == first else None))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))

    assert [a["title"] for a in arts] == ["Powell testifies on the outlook"], (
        "a later sub-query's articles were abandoned after a 429 on an earlier one")
    assert reason == "rate_limited"


def test_structural_failure_never_becomes_a_fresh_success_cache(monkeypatch, tmp_path):
    """A rejection must NOT be cached. Caching it would suppress every retry for
    the full 12h TTL — which is how a structural rejection survives its own fix."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(limit=0))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert (arts, reason) == ([], "query_rejected")
    assert not (tmp_path / "macro_v2_2026-09-18.json").exists(), \
        "a rejected fetch was written to the day cache"

    # the very next call must go BACK to the network (and now succeed)
    catalogue = [{"term": "inflation", "title": "Inflation cools",
                  "url": "https://reuters.com/a", "domain": "reuters.com"}]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(catalogue=catalogue))
    arts2, reason2 = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert [a["title"] for a in arts2] == ["Inflation cools"]
    assert reason2 is None
    assert (tmp_path / "macro_v2_2026-09-18.json").exists(), "a success must cache"


def test_a_stale_empty_cache_blob_is_not_served_as_a_success(monkeypatch, tmp_path):
    """Builds before this fix wrote `{"articles": [], ...}` on every rejected
    fetch. That blob must not be replayed — the wire would stay dark for the
    whole TTL after the cause was fixed."""
    _isolate_gdelt(monkeypatch, tmp_path)
    (tmp_path / "macro_v2_2026-09-18.json").write_text(
        json.dumps({"articles": [], "degraded_reason": "query_rejected"}))
    import requests
    catalogue = [{"term": "inflation", "title": "Inflation cools",
                  "url": "https://reuters.com/a", "domain": "reuters.com"}]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(catalogue=catalogue))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert [a["title"] for a in arts] == ["Inflation cools"], \
        "the poisoned empty cache was replayed instead of refetching"
    assert reason is None


def test_fidelity_provider_response_reaches_the_macro_news_result(monkeypatch, tmp_path):
    """END TO END: with a provider that behaves like the real GDELT server, the
    bounded sub-queries are ACCEPTED and their articles reach macro_headlines()'s
    output as GDELT contributions."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    catalogue = [
        {"term": "inflation", "title": "Inflation cools as CPI slows in August",
         "url": "https://reuters.com/a", "domain": "reuters.com"},
        {"term": "powell", "title": "Powell signals patience on rate cuts",
         "url": "https://bloomberg.com/b", "domain": "bloomberg.com"},
    ]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(catalogue=catalogue))
    # isolate the fetch to the GDELT leg only — the RSS legs are independent and
    # are exercised by their own tests
    monkeypatch.setattr(mn, "_cfg", lambda: dict(
        _CFG, enabled=True, use_official_feeds=False, use_news_feeds=False))

    out = mn.macro_headlines(date(2026, 9, 18))

    assert out is not None
    assert out["n_gdelt"] == 2, f"GDELT contributed {out['n_gdelt']} raw articles"
    assert out["n_kept"] >= 1, "no GDELT article survived into the result"
    assert out["leg_status"]["gdelt"]["degraded_reason"] is None
    titles = [h["title"] for h in out["headlines"]]
    assert any("Inflation cools" in t for t in titles), titles


def test_dark_global_wire_stays_visible_when_the_rss_legs_are_healthy(monkeypatch, tmp_path):
    """The failure this bug hid behind: `degraded_reason` goes None the moment ANY
    leg has headlines, so a rejected global wire reads as a healthy news suite.
    leg_status must record the absence, and the RSS legs must stay independent."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(limit=0))   # wire dark
    monkeypatch.setattr(mn, "_fetch_official_feeds", lambda cfg, today=None: ([
        {"title": "Fed holds rates steady as inflation cools",
         "url": "https://federalreserve.gov/x", "domain": "federalreserve.gov",
         "seendate": "2026-09-18T12:00:00+00:00"}], None))
    monkeypatch.setattr(mn, "_fetch_news_feeds", lambda cfg, today=None: ([], None))
    monkeypatch.setattr(mn, "_cfg", lambda: dict(_CFG, enabled=True))

    out = mn.macro_headlines(date(2026, 9, 18))

    assert out is not None
    assert out["n_kept"] >= 1, "the independent official leg must still deliver"
    assert out["n_gdelt"] == 0
    # the blended field still answers only "is the board empty" ...
    assert out["degraded_reason"] is None
    # ... so the per-leg record is what keeps the absence visible
    assert out["leg_status"]["gdelt"]["degraded_reason"] == "query_rejected", \
        "a structurally dark global wire was reported as a healthy news suite"
    assert out["leg_status"]["gdelt"]["n"] == 0
    assert out["leg_status"]["official_rss"]["degraded_reason"] is None


def test_a_transient_partial_harvest_is_retried_on_the_next_call(monkeypatch, tmp_path):
    """THE 12-HOUR FREEZE. Group 1 succeeds, group 2 is rate-limited — the normal
    state of this shared IP. Caching that partial harvest would serve a truncated
    term set for the whole TTL even though the breaker clears in ~900s, so the very
    next call must go back to the network and recover the missing groups."""
    gc = _isolate_gdelt(monkeypatch, tmp_path)
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    import requests
    qs = mn._queries({})
    last = qs[-1]
    catalogue = [
        {"term": "inflation", "title": "Inflation cools in August",
         "url": "https://reuters.com/a", "domain": "reuters.com"},
        {"term": "powell", "title": "Powell testifies on the outlook",
         "url": "https://reuters.com/b", "domain": "reuters.com"},
    ]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(
        catalogue=catalogue, status_for=lambda q: 429 if q == last else None))

    arts, reason = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert [a["title"] for a in arts] == ["Inflation cools in August"]
    assert reason == "rate_limited"
    assert not (tmp_path / "macro_v2_2026-09-18.json").exists()

    # the rate limit clears (breaker released, provider healthy) -> full recovery
    gc._clear_penalty()
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(catalogue=catalogue))
    arts2, reason2 = mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert sorted(a["title"] for a in arts2) == [
        "Inflation cools in August", "Powell testifies on the outlook"], (
        "the truncated harvest was replayed from cache instead of being recovered")
    assert reason2 is None
    assert (tmp_path / "macro_v2_2026-09-18.json").exists(), "a CLEAN harvest caches"


def test_rejection_annotation_tells_the_truth_about_the_union(monkeypatch, capsys, tmp_path):
    """The annotation is the operator's only loud signal, so it must not claim the
    wire contributed nothing when one group did deliver. It is emitted ONCE per
    fan-out, after the union is known — not per rejected sub-query."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    qs = mn._queries({})
    last = qs[-1]
    catalogue = [{"term": "inflation", "title": "Inflation cools in August",
                  "url": "https://reuters.com/a", "domain": "reuters.com"}]

    # (a) PARTIAL — one group rejected, the other delivered
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(
        catalogue=catalogue, reject_if=lambda q: q == last))
    mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    out = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("::")]
    assert len(out) == 1, f"expected exactly one annotation per fan-out, got {out}"
    assert out[0].startswith("::warning title=macro-news-gdelt-query-rejected::")
    assert "THINNED" in out[0], out[0]
    assert "NOTHING" not in out[0], (
        "a partially-degraded wire was reported as contributing nothing: " + out[0])
    assert f"1 of {len(qs)}" in out[0], out[0]

    # (b) FULLY DARK — every group rejected
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(limit=0))
    mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    out = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("::")]
    assert len(out) == 1, f"expected exactly one annotation per fan-out, got {out}"
    assert "NOTHING" in out[0], out[0]
    assert f"{len(qs)} of {len(qs)}" in out[0], out[0]


def test_no_annotation_when_the_wire_is_healthy(monkeypatch, capsys, tmp_path):
    """The alarm must stay quiet on a good night, or it stops being an alarm."""
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    catalogue = [{"term": "inflation", "title": "Inflation cools in August",
                  "url": "https://reuters.com/a", "domain": "reuters.com"}]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(catalogue=catalogue))

    mn._fetch_gdelt(dict(_CFG), date(2026, 9, 18))
    assert not [ln for ln in capsys.readouterr().out.splitlines()
                if ln.startswith("::")]


def test_a_thinned_wire_is_not_reported_as_dark(monkeypatch, caplog, tmp_path):
    """macro_headlines' operator log must distinguish a wire that answered partly
    from one that answered not at all — they are different diagnoses."""
    import logging
    _isolate_gdelt(monkeypatch, tmp_path)
    import requests
    qs = mn._queries({})
    last = qs[-1]
    catalogue = [{"term": "inflation", "title": "Inflation cools as CPI slows",
                  "url": "https://reuters.com/a", "domain": "reuters.com"}]
    monkeypatch.setattr(requests, "get", _fake_gdelt_server(
        catalogue=catalogue, reject_if=lambda q: q == last))
    monkeypatch.setattr(mn, "_cfg", lambda: dict(
        _CFG, enabled=True, use_official_feeds=False, use_news_feeds=False))

    with caplog.at_level(logging.WARNING, logger="engine.macro_news"):
        out = mn.macro_headlines(date(2026, 9, 18))

    assert out is not None and out["n_gdelt"] == 1
    assert out["leg_status"]["gdelt"]["degraded_reason"] == "query_rejected"
    msgs = [r.getMessage() for r in caplog.records]
    assert any("THINNED" in m for m in msgs), msgs
    assert not any("is DARK" in m for m in msgs), (
        "a wire that delivered an article was logged as DARK: " + repr(msgs))
