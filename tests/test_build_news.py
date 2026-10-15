"""News JSON builder preserves other feeds when China has stored tone only."""
from datetime import datetime, timezone

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
