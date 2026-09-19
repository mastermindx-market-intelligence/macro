from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from engine.research_intelligence.store import (
    load_latest_research_intelligence,
    persist_analysis,
)
from engine.research_intelligence.zerohedge_adapter import (
    analyze_candidate,
    parse_zerohedge_feed,
    qbus_projection,
    select_candidates,
)
from engine.research_vault.r2_store import build_store


SOURCE = {
    "key": "zerohedge_feed",
    "kind": "rss",
    "url": "https://feeds.feedburner.com/zerohedge/feed",
    "source_name": "ZeroHedge",
    "tier": "wire",
}

QUOTE = "AMD server demand accelerated by 35% year over year as cloud buyers raised orders."


def _body(seed: str = QUOTE) -> str:
    filler = (
        "The report discusses cloud infrastructure spending, supply, pricing, and demand "
        "across several end markets without changing the source identity. "
    )
    return seed + " " + filler * 10


def _rss(two: bool = False, short: bool = False) -> str:
    body = "Too short." if short else _body()
    other = _body("A quiet market note contains no immediate macro catalyst.")
    second = (
        "<item><title>A quiet note on markets</title>"
        "<link>https://www.zerohedge.com/markets/quiet-note</link>"
        "<guid>quiet-guid</guid><pubDate>Fri, 18 Sep 2026 18:00:00 GMT</pubDate>"
        f"<description><![CDATA[<p>{other}</p>]]></description></item>"
        if two
        else ""
    )
    return (
        "<rss version='2.0'><channel>"
        "<item><title>AMD Server Demand Accelerates As Cloud Orders Rise</title>"
        "<link>https://www.zerohedge.com/markets/amd-server-demand</link>"
        "<guid>amd-guid</guid><pubDate>Fri, 18 Sep 2026 19:00:00 GMT</pubDate>"
        f"<description><![CDATA[<p>{body}</p>]]></description></item>"
        f"{second}</channel></rss>"
    )


def _model_call(system, user, *, model_id, max_tokens):
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split(
        "\n\nOUTPUT SHAPE:", 1
    )[0]
    shape_text = user.split("OUTPUT SHAPE:\n", 1)[1].split(
        "\n\nDOCUMENT BODY:", 1
    )[0]
    identity = json.loads(identity_text)
    output = json.loads(shape_text)
    output["document"] = identity
    output["claims"][0].update(
        {
            "statement": QUOTE,
            "evidence": [{"quote_span": QUOTE}],
            "numbers": ["35%"],
            "entities": ["AMD"],
            "horizon": "current",
            "explicit": True,
        }
    )
    output["analysis"]["thesis"].update(
        {
            "summary": "The article argues that cloud ordering is strengthening AMD server demand.",
            "direction": "bullish",
            "mechanism": ["higher cloud orders support server demand"],
            "conviction": "moderate",
            "support_claim_indices": [0],
        }
    )
    return json.dumps(output), "fixture-provider", "fixture-model"


def _candidate():
    return select_candidates(
        parse_zerohedge_feed(_rss(), SOURCE),
        now=datetime(2026, 9, 18, 19, 30, tzinfo=timezone.utc),
        breaking_cfg={"salience_threshold": 0},
        limit=1,
    )[0]


def test_parser_preserves_breaking_identity_and_recovers_full_body():
    parsed = parse_zerohedge_feed(_rss(), SOURCE)
    assert len(parsed) == 1
    article = parsed[0]
    item = article["feed_item"]
    assert item["source"] == "zerohedge_feed"
    assert item["url"] == "https://www.zerohedge.com/markets/amd-server-demand"
    assert len(item["body_snippet"]) <= 600
    assert len(article["research_body"]) > 800
    assert article["research_body"].startswith(QUOTE)
    assert article["body_state"] == "full"


def test_short_publisher_body_fails_closed():
    parsed = parse_zerohedge_feed(_rss(short=True), SOURCE)
    assert parsed[0]["body_state"] == "insufficient"
    assert parsed[0]["research_body"] == ""


def test_candidate_selection_reuses_incumbent_breaking_relevance():
    articles = parse_zerohedge_feed(_rss(two=True), SOURCE)
    chosen = select_candidates(
        articles,
        now=datetime(2026, 9, 18, 19, 30, tzinfo=timezone.utc),
        breaking_cfg={"salience_threshold": 60},
        limit=2,
    )
    assert len(chosen) == 2
    assert chosen[0]["feed_item"]["salience"] >= chosen[1]["feed_item"]["salience"]
    assert all("rank_score" in row["feed_item"] for row in chosen)


def test_analysis_uses_shared_grounded_rio_contract():
    candidate = _candidate()
    result = analyze_candidate(candidate, model_id="fixture-request", call=_model_call)
    assert result["state"] == "ok"
    assert result["rio"]["document"]["id"] == candidate["feed_item"]["id"]
    assert result["rio"]["document"]["source_type"] == "qualitative_article"
    assert result["rio"]["claims"][0]["statement"] == QUOTE


def test_zerohedge_rio_persists_through_shared_w2_store(tmp_path):
    candidate = _candidate()
    result = analyze_candidate(candidate, model_id="fixture-request", call=_model_call)
    store = build_store(local_dir=tmp_path / "vault")
    receipt = persist_analysis(store, result, source_body=candidate["research_body"])
    stored = load_latest_research_intelligence(store, candidate["feed_item"]["id"])
    assert receipt.state == "created"
    assert stored is not None
    assert stored.rio["document"]["source_type"] == "qualitative_article"
    assert stored.source_content_sha256 == result["rio"]["document"]["content_sha256"]


def test_qbus_projection_reuses_cross_source_cluster_without_quote_text():
    candidate = _candidate()
    existing = {
        "item_id": "wire-001",
        "event_key": "ev_existing_amd",
        "desk": "financial_news",
        "source": "reuters",
        "source_tier": 1,
        "lang": "en",
        "url": "https://example.test/amd-demand",
        "title": "AMD Server Demand Accelerates As Cloud Orders Rise",
        "body_sha256": "",
        "seendate": "2026-09-18T18:55:00+00:00",
        "_crawled_at": "2026-09-18T18:56:00+00:00",
        "timestamp_quality": "PUBLISHER_STATED",
        "entities": ["AMD"],
        "themes": ["technology"],
        "importance_raw": 80.0,
    }
    row = qbus_projection(
        candidate,
        observed_at="2026-09-18T19:31:00+00:00",
        existing_rows=[existing],
    )
    expected_hash = hashlib.sha256(candidate["research_body"].encode("utf-8")).hexdigest()
    assert row["item_id"] == candidate["feed_item"]["id"]
    assert row["event_key"] == "ev_existing_amd"
    assert row["source"] == "zerohedge_feed"
    assert row["body_sha256"] == expected_hash
    assert QUOTE not in json.dumps(row)
