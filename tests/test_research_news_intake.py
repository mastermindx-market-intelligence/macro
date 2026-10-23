"""Acceptance/recovery/rights tests for research RSS in the incumbent owners."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pytest
from engine import news_rss
from engine.marketing.intelligence_desk import IntelligenceStore, build_research_packet

NOW = datetime(2026, 10, 18, 4, 0, tzinfo=timezone.utc)
SPEC = dict(id="policy", enabled=True, publisher="Test policy office", url="https://example.gov/feed",
            allowed_hosts=["example.gov"], category="geopolitics", language="en",
            content_use="attributed_feed_excerpt", terms_url="https://example.gov/terms", poll_seconds=60)
SOURCE_HEALTH = [dict(id="policy", enabled=True, status="observed",
                      content_use="attributed_feed_excerpt", hold_reason="")]


def rss(title="Policy update", date="Sun, 18 Oct 2026 03:00:00 GMT", guid="id-1", summary="Source summary", url="https://example.gov/story"):
    return (f'<rss version="2.0"><channel><item><guid>{guid}</guid><title>{title}</title><link>{url}</link>'
            f'<pubDate>{date}</pubDate><description>{summary}</description></item></channel></rss>').encode()


def parse(raw=None):
    return news_rss._research_parse(raw or rss(), SPEC, now=NOW)


def test_future_gdelt_index_clock_is_not_presented_as_fresh_reporting(monkeypatch):
    monkeypatch.setattr(news_rss.nc, "source_tier", lambda domain: 1)
    row = news_rss._research_gdelt([{"url": "https://example.com/report", "title": "Example report", "seendate": "20300101T123400Z", "language": "Chinese"}], SPEC, now=NOW)[0]
    assert row["provider_indexed_at"] == ""
    assert row["published_at"] == ""
    assert row["timestamp_quality"] == "future_index_stamp"
    assert row["language"] == "zh"


def test_stable_item_amendment_and_revert_keep_identity():
    a, b, again = parse()[0], parse(rss(title="Amended policy update"))[0], parse()[0]
    assert a["id"] == b["id"] == again["id"]
    assert a["source_revision"] != b["source_revision"]
    assert a["source_revision"] == again["source_revision"]
    assert parse(rss(url="https://example.gov/new-url"))[0]["id"] == a["id"]


def test_atom_original_published_updated_and_alternate_link_separate():
    raw = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>source-1</id><title>Policy</title>
    <updated>2026-10-18T03:30:00Z</updated><published>2026-10-17T03:00:00Z</published>
    <link rel="self" href="https://example.gov/api"/><link rel="alternate" href="https://example.gov/article"/>
    <summary>Details</summary></entry></feed>'''
    item = parse(raw)[0]
    assert item["url"] == "https://example.gov/article"
    assert item["published_at"].startswith("2026-10-17")
    assert item["source_updated_at"].startswith("2026-10-18T03:30")


def test_namespaced_rss_one_feed_is_not_misreported_as_empty():
    raw = b'''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
        <item rdf:about="https://example.gov/policy"><title>Policy release</title>
        <link>https://example.gov/policy</link><dc:date>2026-10-18T03:00:00Z</dc:date>
        <description>Institutional notice</description></item></rdf:RDF>'''
    stats = {}
    rows = news_rss._research_parse(raw, SPEC, now=NOW, diagnostics=stats)
    assert len(rows) == 1 and rows[0]["headline"] == "Policy release"
    assert rows[0]["published_at"].startswith("2026-10-18T03:00")
    assert stats == {"observed_item_count": 1, "eligible_item_count": 1,
                     "filtered_item_count": 0, "duplicate_item_count": 0}


def test_feed_diagnostics_distinguish_eligible_filtered_and_duplicate_entries():
    items = [rss().split(b"<channel>")[1].split(b"</channel>")[0],
             rss().split(b"<channel>")[1].split(b"</channel>")[0],
             rss(guid="unsafe", url="javascript:alert(1)").split(b"<channel>")[1].split(b"</channel>")[0],
             rss(guid="old", date="Thu, 01 Oct 2026 03:00:00 GMT").split(b"<channel>")[1].split(b"</channel>")[0]]
    stats = {}
    rows = news_rss._research_parse(b"<rss><channel>" + b"".join(items) + b"</channel></rss>", SPEC, now=NOW, diagnostics=stats)
    assert len(rows) == 1
    assert stats == {"observed_item_count": 4, "eligible_item_count": 1,
                     "filtered_item_count": 2, "duplicate_item_count": 1}


def test_source_outcomes_distinguish_empty_filtered_unchanged_and_eligible():
    responses = {"empty": {"status": 200, "body": b"<rss><channel/></rss>"},
                 "filtered": {"status": 200, "body": rss(url="javascript:alert(1)")},
                 "unchanged": {"status": 304}, "eligible": {"status": 200, "body": rss()}}
    results = news_rss.poll_research_feeds([dict(SPEC, id=key) for key in responses], {}, now=NOW,
                                         fetcher=lambda spec, state: responses[spec["id"]])
    by_id = {row["feed_id"]: row for row in results}
    assert {key: row["outcome"] for key, row in by_id.items()} == {key: key for key in responses}
    assert by_id["empty"]["observed_item_count"] == 0
    assert by_id["filtered"]["observed_item_count"] == by_id["filtered"]["filtered_item_count"] == 1
    assert by_id["unchanged"]["observed_item_count"] is None
    assert by_id["eligible"]["eligible_item_count"] == 1
    for row in results:
        assert row["attempt_duration_ms"] >= 0
        assert datetime.fromisoformat(row["attempt_completed_at"]) >= datetime.fromisoformat(row["attempt_started_at"])


@pytest.mark.parametrize("failure, code, kind", [
    (OSError("rate_limited"), "rate_limited", "fetch_failed"),
    (OSError("query_rejected"), "query_rejected", "rejected"),
    (TimeoutError("private URL and secret should not escape"), "deadline_exceeded", "fetch_failed"),
    (ValueError("ambiguous source revisions"), "revision_rejected", "rejected"),
    (OSError("private URL and secret should not escape"), "fetch_error", "fetch_failed"),
])
def test_failure_reasons_are_bounded_categories_not_raw_exception_text(failure, code, kind):
    def fetch(spec, state):
        raise failure
    result = news_rss.poll_research_feeds([SPEC], {}, now=NOW, fetcher=fetch)[0]
    assert result["error_code"] == code and result["outcome"] == kind
    assert "private URL" not in json.dumps(result)
    assert result["items"] == [] and result["http_status"] is None


def test_http_failure_keeps_observed_status_without_accepting_content():
    result = news_rss.poll_research_feeds([SPEC], {}, now=NOW,
                                         fetcher=lambda *a: {"status": 429, "body": rss()})[0]
    assert result["http_status"] == 429 and result["status"] == 0
    assert result["error_code"] == "http_error" and result["items"] == []


def test_gdelt_diagnostics_deduplicate_and_reject_ambiguous_source_revisions(monkeypatch):
    monkeypatch.setattr(news_rss.nc, "source_tier", lambda domain: 1 if domain == "example.com" else 0)
    row = {"url": "https://example.com/report", "title": "Example report", "language": "Chinese"}
    stats = {}
    items = news_rss._research_gdelt([row, dict(row), {"url": "https://other.com/report", "title": "Other"}], SPEC, now=NOW, diagnostics=stats)
    assert len(items) == 1 and items[0]["language"] == "zh"
    assert stats == {"observed_item_count": 3, "eligible_item_count": 1,
                     "filtered_item_count": 1, "duplicate_item_count": 1}
    with pytest.raises(ValueError, match="ambiguous source revisions"):
        news_rss._research_gdelt([row, dict(row, title="Conflicting report")], SPEC, now=NOW)


@pytest.mark.parametrize("date", ["", "not a date", "Mon, 19 Oct 2026 03:00:00 GMT"])
def test_unknown_or_future_time_never_becomes_publication_now(date):
    item = parse(rss(date=date))[0]
    packet = build_research_packet(item, now=NOW)
    assert packet["published_at"] == ""
    assert packet["first_seen"] == NOW.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_parser_rejects_bounded_document_failures_and_skips_unsafe_links():
    for raw in [b"<html>error</html>", b"<!DOCTYPE rss><rss/>", b"x" * (news_rss._RESEARCH_MAX_BYTES + 1)]:
        with pytest.raises((ValueError, news_rss.ET.ParseError)):
            parse(raw)
    assert parse(rss(url="javascript:alert(1)")) == []


def test_institutional_release_boundary_excludes_authored_and_foreign_material():
    spec = dict(SPEC, allowed_path_prefixes=["/press/pr/", "/press/govcdec/"])
    for url in ["https://example.gov/press/key/date/speech.html",
                "https://example.gov/press/blog/opinion.html?next=/press/pr/",
                "https://unapproved.example/press/pr/release.html"]:
        assert news_rss._research_parse(rss(url=url), spec, now=NOW) == []
    rows = news_rss._research_parse(rss(url="https://example.gov//press/pr/date/release.html"), spec, now=NOW)
    assert len(rows) == 1
    assert rows[0]["content_use"] == "attributed_feed_excerpt"


def test_held_source_is_never_fetched_and_failure_is_isolated():
    calls = []
    def fetch(spec, state):
        calls.append(spec["id"])
        if spec["id"] == "broken":
            raise TimeoutError()
        return {"status": 200, "body": rss(), "etag": "v1"}
    specs = [SPEC, dict(SPEC, id="broken"), dict(SPEC, id="held", enabled=False),
             dict(SPEC, id="held_enabled", enabled=True, hold_reason="Source review pending")]
    out = news_rss.poll_research_feeds(specs, {}, now=NOW, fetcher=fetch)
    assert set(calls) == {"policy", "broken"}
    assert len(next(r for r in out if r["feed_id"] == "policy")["items"]) == 1
    assert next(r for r in out if r["feed_id"] == "broken")["error"] == "TimeoutError"


def test_unchanged_replay_preserves_clocks_and_amendment_does_not_add_source(tmp_path):
    store = IntelligenceStore(tmp_path / "news.db")
    store.set_source_health(SOURCE_HEALTH)
    try:
        first = build_research_packet(parse()[0], now=NOW)
        store.upsert([first], now=NOW)
        store.upsert([build_research_packet(parse()[0], now=NOW + timedelta(minutes=20))], now=NOW + timedelta(minutes=20))
        snap = store.snapshot(now=NOW + timedelta(minutes=20))
        assert snap["health"]["state"] == "quiet"
        assert "sources_online" not in snap["health"]
        unchanged = snap["stories"][0]
        assert unchanged["updated_at"] == unchanged["accepted_revision_at"] == NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
        amended = build_research_packet(parse(rss(title="Amended policy update", summary=""))[0], now=NOW + timedelta(minutes=21))
        store.upsert([amended], now=NOW + timedelta(minutes=21))
        current = store.snapshot(now=NOW + timedelta(minutes=21))["stories"][0]
        assert current["first_seen"] == NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert current["brief"] == ""
        assert current["source_count"] == 1 and len(current["evidence"]) == 1
        assert current["status"] == "amended" and len(current["revision_history"]) == 1
        assert current["drafts"] == current["content_routes"] == []
    finally:
        store.close()


def test_research_reservation_survives_a_saturated_editorial_snapshot(tmp_path):
    store = IntelligenceStore(tmp_path / "news.db")
    store.set_source_health(SOURCE_HEALTH)
    try:
        for i in range(6):
            p = build_research_packet(parse(rss(guid=str(i)))[0], now=NOW)
            p.pop("purpose")
            p["stage"] = "confirmed"
            store.upsert([p], now=NOW)
        store.upsert([build_research_packet(parse()[0], now=NOW)], now=NOW)
        snapshot = store.snapshot(now=NOW, max_items=3, research_max=1)
        assert len(snapshot["stories"]) == 3
        assert sum(p.get("purpose") == "research" for p in snapshot["stories"]) == 1
    finally:
        store.close()


def test_purpose_collision_rolls_back_the_whole_batch(tmp_path):
    store = IntelligenceStore(tmp_path / "news.db")
    store.set_source_health(SOURCE_HEALTH)
    try:
        p = build_research_packet(parse()[0], now=NOW)
        store.upsert([p], now=NOW)
        collision = dict(p); collision.pop("purpose")
        with pytest.raises(ValueError, match="collision"):
            store.upsert([collision], now=NOW)
        assert store.snapshot(now=NOW)["stories"][0]["purpose"] == "research"
    finally:
        store.close()


def _tick_setup(monkeypatch, tmp_path):
    from scripts import marketing_fastlane_daemon as daemon
    monkeypatch.setattr(daemon, "ROOT", tmp_path)
    monkeypatch.setattr(daemon, "_PRESS_STATE_PATH", tmp_path / "state.json")
    cfg = {"research_rss": {"enabled": True, "feeds": [SPEC]}, "wire": {"intelligence": {
        "db_paths": [str(tmp_path / "desk.db")], "snapshot_paths": [str(tmp_path / "desk.json")],
        "history_snapshot_path": str(tmp_path / "intelligence-history.json"), "snapshot_research_max": 10}}}
    return daemon, cfg


def test_failed_acceptance_keeps_applied_validators_and_recovers_same_revision(monkeypatch, tmp_path):
    from engine.marketing import intelligence_desk
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    seen = []
    def fetch(spec, state):
        seen.append(state.get("applied_etag"))
        return {"status": 200, "body": rss(), "etag": "new"}
    monkeypatch.setattr(news_rss, "_research_fetch", fetch)
    real_atomic = intelligence_desk._atomic_json
    def fail(*a, **k): raise OSError("simulated export failure after SQLite commit")
    monkeypatch.setattr(intelligence_desk, "_atomic_json", fail)
    state = {"research_rss": {"policy": {"applied_etag": "old"}}}
    assert daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)["accepted"] is False
    assert state["research_rss"]["policy"]["applied_etag"] == "old"
    assert state["research_rss"]["policy"]["last_outcome"] == "acceptance_failed"
    assert state["research_rss"]["policy"]["last_acceptance_error"] == "OSError"
    assert "latest_applied_revision_by_item" not in state["research_rss"]["policy"]
    monkeypatch.setattr(intelligence_desk, "_atomic_json", real_atomic)
    result = daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW + timedelta(minutes=2))
    assert result["accepted"] and seen == ["old", "old"]
    packet = json.loads((tmp_path / "desk.json").read_text())["stories"][0]
    assert packet["first_seen"] == packet["accepted_revision_at"] == NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert state["research_rss"]["policy"]["applied_etag"] == "new"
    # Republication acknowledges the original stored revision, not a new change.
    assert state["research_rss"]["policy"]["last_outcome"] == "unchanged"
    assert state["research_rss"]["policy"]["last_changed_item_count"] == 0
    assert result["revisions"] == 0
    assert state["research_rss"]["policy"]["last_acceptance_error"] == ""
    assert state["research_rss"]["policy"]["last_applied_at"] == packet["accepted_revision_at"]
    health = json.loads((tmp_path / "desk.json").read_text())["source_health"][0]
    assert health["last_accepted_at"] == packet["accepted_revision_at"]


@pytest.mark.parametrize("withdrawal", ["disabled_feed", "held_feed", "disabled_lane", "removed_feed"])
def test_idle_scope_withdrawal_survives_later_editorial_export(monkeypatch, tmp_path, withdrawal):
    from engine.marketing import intelligence_desk
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    calls = []
    def fetch(*args):
        calls.append(1)
        return {"status": 200, "body": rss(), "etag": "accepted-v1"}
    monkeypatch.setattr(news_rss, "_research_fetch", fetch)
    state = {}
    assert daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)["accepted"]
    first = json.loads((tmp_path / "desk.json").read_text())
    assert len(first["stories"]) == 1
    before = dict(state["research_rss"]["policy"])
    if withdrawal == "disabled_feed":
        cfg["research_rss"]["feeds"] = [dict(SPEC, enabled=False)]
    elif withdrawal == "held_feed":
        cfg["research_rss"]["feeds"] = [dict(SPEC, enabled=True, hold_reason="Display grant withdrawn")]
    elif withdrawal == "disabled_lane":
        cfg["research_rss"]["enabled"] = False
    else:
        cfg["research_rss"]["feeds"] = []
    result = daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW + timedelta(seconds=30))
    assert result["accepted"] and result["due"] == 0 and result["revisions"] == 0
    assert calls == [1]
    assert state["research_rss"]["policy"] == before
    # The later incumbent editorial turn supplies no source_health override.
    intelligence_desk.update_intelligence_desk([], root=tmp_path, now=NOW + timedelta(minutes=1),
                                               cfg=cfg["wire"]["intelligence"])
    assert json.loads((tmp_path / "desk.json").read_text())["stories"] == []
    assert json.loads((tmp_path / "intelligence-history.json").read_text())["stories"] == []


def test_superseded_daemon_revision_preserves_acceptance_clock_and_applied_ledger(monkeypatch, tmp_path):
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    current = atom([atom_entry("Current revision", "2026-10-18T03:00:00Z")])
    older = atom([atom_entry("Older revision", "2026-10-18T02:00:00Z")])
    responses = iter([{"status": 200, "body": current, "etag": "r2"},
                      {"status": 200, "body": older, "etag": "old-response-r1"}])
    monkeypatch.setattr(news_rss, "_research_fetch", lambda *args: next(responses))
    state = {}
    assert daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)["revisions"] == 1
    first = json.loads((tmp_path / "desk.json").read_text())
    first_state = dict(state["research_rss"]["policy"])
    result = daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW + timedelta(minutes=2))
    assert result["accepted"] and result["revisions"] == 0
    latest = json.loads((tmp_path / "desk.json").read_text())
    entry = state["research_rss"]["policy"]
    assert latest["stories"][0]["headline"] == "Current revision"
    assert latest["stories"][0]["accepted_revision_at"] == first["stories"][0]["accepted_revision_at"]
    assert entry["latest_applied_revision_by_item"] == first_state["latest_applied_revision_by_item"]
    assert entry["last_applied_at"] == first_state["last_applied_at"]
    assert entry["last_changed_item_count"] == 0 and entry["last_outcome"] == "unchanged"
    assert entry["applied_etag"] == "old-response-r1"  # Successfully observed transport validator.
    health = latest["source_health"][0]
    assert health["last_accepted_at"] == first["source_health"][0]["last_accepted_at"]
    assert health["last_changed_item_count"] == 0 and health["last_outcome"] == "unchanged"
    assert "acceptance_receipt" not in json.dumps(latest)


def test_oversized_gdelt_response_records_actual_count_without_advancing_validator(monkeypatch, tmp_path):
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    cfg["research_rss"]["feeds"] = [dict(SPEC, transport="gdelt", content_use="attributed_headline_link")]
    rows = [{"url": "https://example.com/" + str(i), "title": "Report " + str(i)} for i in range(101)]
    monkeypatch.setattr(news_rss, "_research_fetch", lambda *args: {"status": 200, "articles": rows, "etag": "oversized"})
    state = {"research_rss": {"policy": {"applied_etag": "prior", "last_applied_at": "2026-10-17T03:00:00Z"}}}
    result = daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)
    assert result["revisions"] == 0
    entry = state["research_rss"]["policy"]
    assert entry["applied_etag"] == "prior" and entry["last_applied_at"] == "2026-10-17T03:00:00Z"
    assert entry["last_outcome"] == "rejected" and entry["last_error_code"] == "batch_too_large"
    assert entry["last_observed_item_count"] == 101 and entry["last_eligible_item_count"] == 0
    assert entry["last_http_status"] == 200 and "latest_applied_revision_by_item" not in entry
    assert json.loads((tmp_path / "desk.json").read_text())["stories"] == []


def test_304_updates_fetch_health_without_new_news(monkeypatch, tmp_path):
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    state = {"research_rss": {"policy": {"applied_etag": "v1", "last_applied_at": "2026-10-17T03:00:00+00:00"}}}
    monkeypatch.setattr(news_rss, "_research_fetch", lambda *args: {"status": 304})
    result = daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)
    assert result["revisions"] == 0
    assert state["research_rss"]["policy"]["last_applied_at"].startswith("2026-10-17")
    assert state["research_rss"]["policy"]["last_fetch_success_at"] == NOW.isoformat()
    health = json.loads((tmp_path / "desk.json").read_text())["source_health"][0]
    assert health["last_outcome"] == "unchanged" and health["last_http_status"] == 304
    assert health["last_observed_item_count"] is None and health["last_changed_item_count"] == 0
    assert health["last_attempt_duration_ms"] >= 0


def test_source_health_distinguishes_first_acceptance_and_unchanged_replay(monkeypatch, tmp_path):
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    state = {}
    monkeypatch.setattr(news_rss, "_research_fetch", lambda *a: {"status": 200, "body": rss()})
    daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)
    first = json.loads((tmp_path / "desk.json").read_text())["source_health"][0]
    assert first["last_outcome"] == "accepted" and first["last_changed_item_count"] == 1
    assert first["content_use"] == "attributed_feed_excerpt"
    daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW + timedelta(minutes=2))
    second = json.loads((tmp_path / "desk.json").read_text())["source_health"][0]
    assert second["last_outcome"] == "unchanged" and second["last_changed_item_count"] == 0
    assert second["last_eligible_item_count"] == 1
    assert second["last_accepted_at"] == first["last_accepted_at"]


@pytest.mark.parametrize("loss", ["validator_eviction", "state_loss"])
def test_replayed_stored_revision_acknowledges_without_inventing_changed_items(monkeypatch, tmp_path, loss):
    daemon, cfg = _tick_setup(monkeypatch, tmp_path)
    attempts = []
    def fetch(*args):
        attempts.append(True)
        return {"status": 200, "body": rss(), "etag": f"observed-{len(attempts)}"}
    monkeypatch.setattr(news_rss, "_research_fetch", fetch)
    state = {}
    assert daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW)["revisions"] == 1
    first = json.loads((tmp_path / "desk.json").read_text())["source_health"][0]
    versions = dict(state["research_rss"]["policy"]["latest_applied_revision_by_item"])
    if loss == "validator_eviction":
        state["research_rss"]["policy"]["latest_applied_revision_by_item"].clear()
    else:
        state.clear()
    result = daemon._run_research_rss_tick(state=state, press_cfg=cfg, now=NOW + timedelta(minutes=2))
    entry = state["research_rss"]["policy"]
    health = json.loads((tmp_path / "desk.json").read_text())["source_health"][0]
    assert result["accepted"] is True
    assert health["last_changed_item_count"] == 0
    assert entry["last_changed_item_count"] == 0 and result["revisions"] == 0
    assert health["last_outcome"] == entry["last_outcome"] == "unchanged"
    assert health["last_accepted_at"] == first["last_accepted_at"]
    assert entry["applied_etag"] == "observed-2"
    assert entry["latest_applied_revision_by_item"] == versions


def test_research_cannot_enter_editorial_drafting_or_approval(monkeypatch, tmp_path):
    from engine.marketing.intelligence_llm import eligible_packets
    from admin import marketing
    packet = build_research_packet(parse()[0], now=NOW)
    packet.update(stage="high_impact", drafts=[{"id": "forged", "status": "review", "text": "Do not publish"}])
    assert eligible_packets([packet], max_per_tick=10) == []
    monkeypatch.setattr(marketing, "_intelligence_snapshot", lambda *a, **k: {"stories": [packet]})
    result = marketing.intelligence_approve(packet["id"], "forged", root=tmp_path, now=NOW)
    assert result["ok"] is False and "research_only" in json.dumps(result)


def test_research_publication_precedes_optional_editorial_enrichment():
    from scripts import marketing_fastlane_daemon as daemon
    import inspect
    body = inspect.getsource(daemon._run_press_tick)
    assert body.index("_run_research_rss_tick(") < body.index("_attach_desk_llm(")
    assert body.index("_attach_desk_llm(") < body.index("_attach_desk_zh(") < body.index("snapshot = update_intelligence_desk(")


def atom_entry(title, updated, published="2026-09-01T03:00:00Z", identity="a"):
    return f'<entry><id>{identity}</id><title>{title}</title><published>{published}</published><updated>{updated}</updated><link href="https://example.gov/{identity}"/></entry>'


def atom(entries):
    return ('<feed xmlns="http://www.w3.org/2005/Atom">' + ''.join(entries) + '</feed>').encode()


def test_old_publication_with_current_amendment_is_not_dropped():
    item = parse(atom([atom_entry("Amended policy", "2026-10-18T03:30:00Z")]))[0]
    assert item["published_at"].startswith("2026-09-01")
    assert item["source_updated_at"].startswith("2026-10-18")


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_source_versions_resolve_by_declared_update_not_xml_order(reverse):
    entries = [atom_entry("Older version", "2026-10-18T02:00:00Z"), atom_entry("Newer version", "2026-10-18T03:00:00Z")]
    assert parse(atom(entries[::-1] if reverse else entries))[0]["headline"] == "Newer version"
    with pytest.raises(ValueError, match="ambiguous"):
        parse(atom([entries[0], atom_entry("Conflicting version", "2026-10-18T02:00:00Z")]))


def test_stale_declared_revision_cannot_replace_current_or_advance_acceptance(tmp_path):
    old = build_research_packet(parse(atom([atom_entry("Older", "2026-10-18T02:00:00Z")]))[0], now=NOW)
    new = build_research_packet(parse(atom([atom_entry("Newer", "2026-10-18T03:00:00Z")]))[0], now=NOW)
    store = IntelligenceStore(tmp_path / "desk.db")
    store.set_source_health(SOURCE_HEALTH)
    try:
        store.upsert([new], now=NOW)
        store.upsert([old], now=NOW + timedelta(minutes=1))
        current = store.snapshot(now=NOW + timedelta(minutes=1))["stories"][0]
        assert current["headline"] == "Newer"
        assert current["accepted_revision_at"] == new["accepted_revision_at"]
    finally:
        store.close()


def test_overflow_is_failed_before_conditional_validator_can_be_applied():
    raw = atom([atom_entry(str(i), "2026-10-18T03:00:00Z", identity=str(i)) for i in range(151)])
    outcome = news_rss.poll_research_feeds([SPEC], {}, now=NOW, fetcher=lambda *args: {"status": 200, "body": raw, "etag": "overflow"})[0]
    assert outcome["status"] == 0 and not outcome["items"]


def test_gdelt_due_feeds_share_one_fair_turn_without_delaying_rss():
    a, b = dict(SPEC, id="a", transport="gdelt"), dict(SPEC, id="b", transport="gdelt")
    fetched = []
    def fetch(spec, state):
        fetched.append(spec["id"])
        return {"status": 200, "body": rss(), "articles": []}
    news_rss.poll_research_feeds([a, b, SPEC], {}, now=NOW, fetcher=fetch)
    assert set(fetched) == {"a", "policy"}
    fetched.clear()
    news_rss.poll_research_feeds([a, b, SPEC], {"a": {"last_attempt_at": (NOW-timedelta(minutes=10)).isoformat()}}, now=NOW, fetcher=fetch)
    assert set(fetched) == {"b", "policy"}


@pytest.mark.parametrize("mode", ["lock", "trickle"])
def test_gdelt_total_deadline_kills_and_reaps_actual_blocked_child(monkeypatch, tmp_path, mode):
    import fcntl
    import subprocess
    import time
    from engine import gdelt_client
    real_popen = subprocess.Popen
    children = []
    marker, stamp = tmp_path / "http_attempt", tmp_path / "stamp"
    stamp.write_text("0")
    held = stamp.open("a+")
    if mode == "lock":
        fcntl.flock(held, fcntl.LOCK_EX)
    prefix = ("from pathlib import Path; import engine.gdelt_client as g; import requests,time; "
              f"g._stamp_path=lambda:Path({str(stamp)!r}); "
              "g._penalty_active=lambda:False; "
              f"marker=Path({str(marker)!r}); ")
    if mode == "lock":
        prefix += "requests.get=lambda *a,**k:marker.write_text('unexpected request'); "
    else:
        prefix += ("g._throttle=lambda interval:None; "
                   "R=type('R',(),{'iter_content':lambda self,**k: ((time.sleep(.15) or b'x') for i in range(200)), 'close':lambda self:None}); "
                   "requests.get=lambda *a,**k:(marker.write_text('started') and R()); ")
    def launch(args, **kwargs):
        args = list(args)
        args[2] = prefix + args[2]
        child = real_popen(args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(subprocess, "Popen", launch)
    start = time.monotonic()
    try:
        articles, reason = gdelt_client.get_articles({"query": "economy", "mode": "artlist"}, total_timeout_s=1.5, max_attempts=1, max_response_bytes=1024)
    finally:
        fcntl.flock(held, fcntl.LOCK_UN)
        held.close()
    assert articles is None and reason == "deadline_exceeded"
    assert time.monotonic() - start < 2.7
    assert children and all(p.poll() is not None for p in children)
    assert marker.exists() is (mode == "trickle")


def test_rss_trickling_transport_has_a_total_deadline_and_no_orphan(monkeypatch):
    import subprocess
    import sys
    import time
    real_popen = subprocess.Popen
    children = []
    def launch(args, **kwargs):
        code = "import sys,time; [(sys.stdout.write('x'),sys.stdout.flush(),time.sleep(.1)) for _ in range(200)]"
        child = real_popen([sys.executable, "-u", "-c", code], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(subprocess, "Popen", launch)
    monkeypatch.setattr(news_rss, "_RESEARCH_FETCH_SECONDS", .4)
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        news_rss._research_fetch(SPEC, {})
    assert time.monotonic() - start < 1.6
    assert children and all(p.poll() is not None for p in children)
