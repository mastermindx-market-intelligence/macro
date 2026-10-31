"""News JSON builder preserves other feeds when China has stored tone only."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import build_news


def _forbid_external_call(*args, **kwargs):
    raise AssertionError("offline news builder test reached an external boundary")


@pytest.mark.parametrize("china_has_headlines", [False, True], ids=["tone-only", "headlines"])
def test_build_keeps_other_headlines_with_nullable_china_news(monkeypatch, china_has_headlines):
    from engine import china_news, financial_news, macro_news, news_ai_feed
    from engine import news_llm, news_rss, news_vector

    now = datetime.now(timezone.utc).isoformat()
    macro = {"headlines": [{"title": "Macro observation", "domain": "reuters.com",
                            "quality": 60, "seendate": now}]}
    financial = {"market": [{"title": "Issuer observation", "domain": "reuters.com",
                              "quality": 60, "seendate": now}],
                 "mag7": {}, "sectors": {}, "baskets": {}}
    tone = {"label_en": "cautious", "z": -0.53, "n_days": 120}
    china_headlines = [{"title": "China observation", "domain": "reuters.com",
                        "quality": 60, "seendate": now}]
    china_feed = {"headlines": china_headlines} if china_has_headlines else None

    monkeypatch.setattr(build_news.config, "load", lambda: {})
    monkeypatch.setattr(macro_news, "macro_headlines", lambda: macro)
    monkeypatch.setattr(macro_news, "upcoming_catalysts", lambda **kwargs: [])
    monkeypatch.setattr(financial_news, "feed", lambda: financial)
    monkeypatch.setattr(news_rss, "start_reject_log", lambda: ([], None))
    monkeypatch.setattr(news_rss, "stop_reject_log", lambda token: None)
    monkeypatch.setattr(news_ai_feed, "enabled", lambda: False)
    monkeypatch.setattr(news_ai_feed, "fetch", _forbid_external_call)
    monkeypatch.setattr(china_news, "policy_tone", lambda asof: tone)
    monkeypatch.setattr(china_news, "enabled", lambda: china_has_headlines)
    monkeypatch.setattr(china_news, "flash_headlines", lambda: china_feed)
    monkeypatch.setattr(china_news, "news_brief", lambda *args: None)
    monkeypatch.setattr(news_vector, "enabled", lambda: False)
    monkeypatch.setattr(news_vector, "ingest", _forbid_external_call)
    monkeypatch.setattr(news_vector, "ingest_to_qbus", _forbid_external_call)
    monkeypatch.setattr(news_vector, "recent_panel", lambda: None)
    monkeypatch.setattr(news_llm, "annotate", lambda rows: None)
    monkeypatch.setattr(news_llm, "provider_label", lambda: "")

    # Exercise the real builder, China panel and deterministic enrichment. With
    # write=False no side-artifact or event/reject ledger writer can run.
    result = build_news.build(write=False)

    assert result["china"]["tone"] == tone
    assert result["china"]["news"] == china_feed
    assert [row["title"] for row in result["macro"]["headlines"]] == ["Macro observation"]
    assert [row["title"] for row in result["fin"]["market"]] == ["Issuer observation"]
    assert result["macro"]["headlines"][0]["rank_score"] > 0
    assert result["fin"]["market"][0]["rank_score"] > 0
    if china_has_headlines:
        assert result["china"]["news"]["headlines"][0]["title"] == "China observation"
        assert result["china"]["news"]["headlines"][0]["rank_score"] > 0


# --------------------------------------------------------------------------- #
# Freshness honesty: by_ticker.json must say WHEN its news was fetched and
# WHETHER it was retained from a previous build by the never-darken guard.
# --------------------------------------------------------------------------- #
def _offline_fin_build(monkeypatch, tmp_path, fin_feed):
    """Patch every external boundary of build_news.build(write=True): the feed
    stubs from the test above, plus macro-surprise cards, the news event ledger
    and the entity map — nothing may reach the network or the repo's data/.
    config ROOT + site_dir point at tmp_path."""
    from engine import china_news, financial_news, macro_news, news_ai_feed
    from engine import macro_surprise, news_common, news_event_ledger
    from engine import news_llm, news_rss, news_vector

    now = datetime.now(timezone.utc).isoformat()
    macro = {"headlines": [{"title": "Macro observation", "domain": "reuters.com",
                            "quality": 60, "seendate": now}]}
    tone = {"label_en": "cautious", "z": -0.53, "n_days": 120}

    monkeypatch.setattr(build_news.config, "ROOT", tmp_path)
    monkeypatch.setattr(build_news.config, "load",
                        lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(macro_news, "macro_headlines", lambda: macro)
    monkeypatch.setattr(macro_news, "upcoming_catalysts", lambda **kwargs: [])
    monkeypatch.setattr(financial_news, "feed", lambda: fin_feed)
    monkeypatch.setattr(news_rss, "start_reject_log", lambda: ([], None))
    monkeypatch.setattr(news_rss, "stop_reject_log", lambda token: None)
    monkeypatch.setattr(news_ai_feed, "enabled", lambda: False)
    monkeypatch.setattr(news_ai_feed, "fetch", _forbid_external_call)
    monkeypatch.setattr(china_news, "policy_tone", lambda asof: tone)
    monkeypatch.setattr(china_news, "enabled", lambda: False)
    monkeypatch.setattr(china_news, "flash_headlines", lambda: None)
    monkeypatch.setattr(china_news, "news_brief", lambda *args: None)
    monkeypatch.setattr(news_vector, "enabled", lambda: False)
    monkeypatch.setattr(news_vector, "ingest", _forbid_external_call)
    monkeypatch.setattr(news_vector, "ingest_to_qbus", _forbid_external_call)
    monkeypatch.setattr(news_vector, "recent_panel", lambda: None)
    monkeypatch.setattr(news_llm, "annotate", lambda rows: None)
    monkeypatch.setattr(news_llm, "provider_label", lambda: "")
    # write=True-only boundaries: release cards, the event/reject ledger, entities
    monkeypatch.setattr(macro_surprise, "build_release_cards", lambda **k: None)
    monkeypatch.setattr(news_event_ledger, "persist_kept_events", lambda *a, **k: 0)
    monkeypatch.setattr(news_event_ledger, "persist_reject_sample", lambda *a, **k: 0)
    monkeypatch.setattr(news_common, "build_entity_map", lambda: {"tickers": {}})


def test_by_ticker_retained_path_stamps_source_asof_from_retained_file(monkeypatch, tmp_path):
    """T1: when the never-darken guard keeps the previous build's financial.json,
    by_ticker.json must say so — source_asof is the RETAINED file's fetched_at
    (never the build date), retained_from_previous_build is True and
    retained_reason matches the refresh_skipped_reason stamped into financial.json."""
    now = datetime.now(timezone.utc)
    retained_fetched_at = (now - timedelta(hours=2)).isoformat()
    candidate = {
        "schema": "financial_news.v1", "is_context_only": True,
        "fetched_at": now.isoformat(),
        "providers": {"polygon": False, "finnhub": False, "quiver": False,
                      "gdelt": True},
        "counts": {"raw": 1, "tagged": 1, "tickers_covered": 1},
        "market": [{"title": "Issuer observation", "domain": "reuters.com",
                    "quality": 60, "seendate": now.isoformat()}],
        "mag7": {}, "sectors": {}, "baskets": {},
        "by_ticker": {"AMD": [{"title": "AMD observation",
                               "url": "https://example.com/a", "source": "Example",
                               "seendate": now.isoformat(), "sentiment": None,
                               "summary": ""}]},
        "rejected": [],
    }
    _offline_fin_build(monkeypatch, tmp_path, candidate)

    # Pre-existing artifact that is FRESH (<36 h) and strictly HEALTHIER (3 live
    # providers vs the candidate's 1) — exactly the guard's keep condition.
    healthier = {
        "schema": "financial_news.v1", "is_context_only": True,
        "fetched_at": retained_fetched_at,
        "providers": {"polygon": True, "finnhub": True, "quiver": False,
                      "gdelt": True},
        "counts": {"raw": 3, "tagged": 3, "tickers_covered": 5},
        "by_ticker": {"NVDA": [{"title": "NVDA retained headline",
                                "url": "https://www.reuters.com/nvda",
                                "source": "Reuters",
                                "seendate": retained_fetched_at,
                                "sentiment": "pos", "summary": ""}]},
    }
    news_dir = tmp_path / "site" / "news"
    news_dir.mkdir(parents=True)
    (news_dir / "financial.json").write_text(json.dumps(healthier))

    vm = build_news.build(write=True)

    payload = json.loads((news_dir / "by_ticker.json").read_text())
    fin_disk = json.loads((news_dir / "financial.json").read_text())
    assert payload["source_asof"] == retained_fetched_at
    assert payload["retained_from_previous_build"] is True
    assert payload["retained_reason"] == fin_disk["refresh_skipped_reason"]
    assert payload["source_asof_basis"] == "financial_news.fetched_at"
    # `asof` keeps its meaning: the build date, not the fetch stamp.
    assert payload["asof"] == vm["built_date"]
    assert payload["asof"] == datetime.now(timezone.utc).date().isoformat()
    assert payload["schema"] == "news_flow.v1"
    assert payload["is_context_only"] is True
    assert "NVDA" in payload["tickers"]


def test_by_ticker_fresh_path_is_not_retained(monkeypatch, tmp_path):
    """T2: with no previous financial.json the fresh feed is written —
    source_asof is the candidate's fetched_at, retained_from_previous_build is
    False and retained_reason is omitted entirely."""
    fetched_at = "2026-10-31T05:00:00+00:00"
    candidate = {
        "schema": "financial_news.v1", "is_context_only": True,
        "fetched_at": fetched_at,
        "providers": {"polygon": True, "finnhub": False, "quiver": False,
                      "gdelt": True},
        "counts": {"raw": 1, "tagged": 1, "tickers_covered": 1},
        "market": [{"title": "Issuer observation", "domain": "reuters.com",
                    "quality": 60, "seendate": fetched_at}],
        "mag7": {}, "sectors": {}, "baskets": {},
        "by_ticker": {"NVDA": [{"title": "NVDA fresh headline",
                                "url": "https://www.reuters.com/nvda",
                                "source": "Reuters", "seendate": fetched_at,
                                "sentiment": None, "summary": ""}]},
        "rejected": [],
    }
    _offline_fin_build(monkeypatch, tmp_path, candidate)

    build_news.build(write=True)

    payload = json.loads((tmp_path / "site" / "news" / "by_ticker.json").read_text())
    assert payload["source_asof"] == fetched_at
    assert payload["retained_from_previous_build"] is False
    assert "retained_reason" not in payload
    assert payload["source_asof_basis"] == "financial_news.fetched_at"
    assert "NVDA" in payload["tickers"]
