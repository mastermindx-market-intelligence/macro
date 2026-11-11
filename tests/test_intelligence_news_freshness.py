"""News producer provenance through the existing unified intelligence builder."""
from datetime import date

import pytest

from engine import intelligence as intel

_TODAY = date(2026, 6, 20)


def _news(ticker):
    return {"n_recent": 3, "sentiment_lean": "pos",
            "top": [{"title": f"{ticker} headline", "url": f"https://example.test/{ticker}"}]}


def _scored_signal(ticker, score):
    return {"ticker": ticker, "signal_score": score, "action": "WATCH"}


def test_load_and_build_keeps_news_clock_separate_from_bundle_clock(tmp_path, monkeypatch):
    """The actual reader carries the metadata from the same file as its news rows."""
    import json

    news_path = tmp_path / "site/news/by_ticker.json"
    news_path.parent.mkdir(parents=True)
    metadata = {
        "source_asof": "2026-10-29T21:00:00+00:00",
        "source_asof_basis": "financial_news.fetched_at",
        "retained_from_previous_build": True,
        "retained_reason": "candidate_darker_than_existing",
    }
    news_path.write_text(json.dumps({"asof": "2026-10-31", **metadata,
                                     "tickers": {"NVDA": _news("NVDA")}}))
    monkeypatch.setattr(intel.config, "ROOT", tmp_path)
    result = intel.load_and_build(today=date(2026, 11, 8))
    assert result["news_freshness"] == metadata
    assert result["as_of"] == "2026-11-08"
    assert result["generated_utc"] != metadata["source_asof"]
    assert result["tickers"]["NVDA"]["news"] == _news("NVDA")


def test_news_metadata_is_additive_and_does_not_change_the_four_facet_read():
    from copy import deepcopy

    news = {"NVDA": _news("NVDA")}
    original = deepcopy(news)
    args = (news, [_scored_signal("NVDA", 80)], {},
            [{"ticker": "NVDA", "state": "POSITIVE_DIVERGENCE", "edge_score": 75}],
            [{"ticker": "NVDA", "label": "BUY ZONE", "conviction": 0.8}])
    legacy = intel.build(*args, today=_TODAY)
    retained = intel.build(*args, today=_TODAY, news_metadata={
        "source_asof": "2026-06-18T10:00:00+00:00",
        "source_asof_basis": "financial_news.fetched_at",
        "retained_from_previous_build": True, "retained_reason": "weaker_candidate"})
    assert legacy["news_freshness"] == {
        "source_asof": None, "source_asof_basis": None,
        "retained_from_previous_build": None, "retained_reason": None}
    assert {k: v for k, v in legacy.items() if k not in {"news_freshness", "generated_utc"}} == {
        k: v for k, v in retained.items() if k not in {"news_freshness", "generated_utc"}}
    assert news == original


@pytest.mark.parametrize("metadata", [None, {}, [], "bad", {
    "source_asof": 123, "source_asof_basis": [],
    "retained_from_previous_build": "false", "retained_reason": {"reason": "old"}}, {
    "source_asof": " ", "source_asof_basis": "", "retained_from_previous_build": 0}])
def test_unstated_or_malformed_news_metadata_stays_unknown(metadata):
    result = intel.build({"NVDA": _news("NVDA")}, None, None,
                         today=_TODAY, news_metadata=metadata)
    assert result["news_freshness"] == {
        "source_asof": None, "source_asof_basis": None,
        "retained_from_previous_build": None, "retained_reason": None}


def test_known_false_news_retention_stays_false():
    result = intel.build({"NVDA": _news("NVDA")}, None, None, news_metadata={
        "source_asof": "2026-10-31T05:00:00+00:00",
        "source_asof_basis": "financial_news.fetched_at", "retained_from_previous_build": False})
    assert result["news_freshness"] == {
        "source_asof": "2026-10-31T05:00:00+00:00",
        "source_asof_basis": "financial_news.fetched_at",
        "retained_from_previous_build": False, "retained_reason": None}
