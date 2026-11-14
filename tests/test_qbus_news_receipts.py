"""Fail-closed source-rights and runtime-health receipt tests for ticker news."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os

import pytest


UTC = timezone.utc
NOW = datetime(2026, 10, 5, 22, 0, tzinfo=UTC)


def _rights(**overrides):
    payload = {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "rights-2026-10-05-a",
        "owner_ref": "source-rights/BENZINGA-COMMERCIAL-001",
        "status": "approved",
        "source": "benzinga",
        "product_id": "benzinga-newsfeed-commercial",
        "audiences": ["site_full"],
        "effective_at": "2026-10-05T00:00:00+00:00",
        "expires_at": "2026-11-05T00:00:00+00:00",
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": True,
            "teaser_display": False,
            "body_display": False,
            "image_display": False,
            "derivative_processing": False,
        },
    }
    payload.update(overrides)
    return payload


def _health(**overrides):
    payload = {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": "live",
        "observed_at": "2026-10-05T21:59:55+00:00",
        "last_successful_catchup": "2026-10-05T21:59:50+00:00",
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 2,
        "disconnects": 1,
        "catchups_failed": 0,
    }
    payload.update(overrides)
    return payload


def test_approved_site_full_rights_map_only_explicit_display_fields():
    from engine import qbus_news_receipts as m

    receipt = m.parse_rights_receipt(_rights(), now=NOW, audience="site_full")

    assert receipt.receipt_id == "rights-2026-10-05-a"
    assert receipt.product_id == "benzinga-newsfeed-commercial"
    assert receipt.rights.allowed_sources == frozenset({"benzinga"})
    assert receipt.rights.allow_title is True
    assert receipt.rights.allow_url is True
    assert receipt.rights.allow_teaser is False


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "denied"},
        {"source": "massive"},
        {"audiences": ["internal_only"]},
        {"effective_at": "2026-10-06T00:00:00+00:00"},
        {"expires_at": "2026-10-05T21:59:59+00:00"},
    ],
)
def test_rights_refuse_wrong_status_source_audience_or_time(mutation):
    from engine import qbus_news_receipts as m

    with pytest.raises(m.NewsReceiptError):
        m.parse_rights_receipt(_rights(**mutation), now=NOW, audience="site_full")


@pytest.mark.parametrize("capability", ["internal_ingestion", "historical_retention", "headline_display"])
def test_rights_refuse_when_current_store_or_core_headline_use_is_not_licensed(capability):
    from engine import qbus_news_receipts as m

    payload = _rights()
    payload["capabilities"][capability] = False

    with pytest.raises(m.NewsReceiptError) as exc:
        m.parse_rights_receipt(payload, now=NOW, audience="site_full")
    assert capability in exc.value.code


def test_rights_never_infer_teaser_or_source_link_permission():
    from engine import qbus_news_receipts as m

    payload = _rights()
    payload["capabilities"].pop("teaser_display")
    payload["capabilities"].pop("source_link_display")

    parsed = m.parse_rights_receipt(payload, now=NOW, audience="site_full")

    assert parsed.rights.allow_teaser is False
    assert parsed.rights.allow_url is False


def test_rights_reject_naive_timestamps_and_unknown_schema():
    from engine import qbus_news_receipts as m

    with pytest.raises(m.NewsReceiptError):
        m.parse_rights_receipt(_rights(effective_at="2026-10-05T00:00:00"), now=NOW)
    with pytest.raises(m.NewsReceiptError):
        m.parse_rights_receipt(_rights(schema="future.v9"), now=NOW)


def test_rights_file_loader_missing_invalid_or_expired_is_none(tmp_path):
    from engine import qbus_news_receipts as m

    missing = tmp_path / "missing.json"
    assert m.load_rights_receipt(missing, now=NOW, audience="site_full") is None

    path = tmp_path / "rights.json"
    path.write_text("{bad", encoding="utf-8")
    assert m.load_rights_receipt(path, now=NOW, audience="site_full") is None

    path.write_text(json.dumps(_rights(expires_at="2026-10-05T21:00:00+00:00")), encoding="utf-8")
    assert m.load_rights_receipt(path, now=NOW, audience="site_full") is None


def test_fresh_health_can_be_live_without_recent_story_when_catchup_is_fresh():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(_health(), now=NOW)

    assert parsed["state"] == "live"
    assert parsed["last_stream_event_at"] is None
    assert parsed["gap_unresolved"] is False


def test_connected_but_stale_catchup_is_degraded_not_live():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(
        _health(last_successful_catchup="2026-10-05T21:50:00+00:00"),
        now=NOW,
        max_catchup_age_seconds=120,
    )

    assert parsed["state"] == "degraded"
    assert parsed["reason"] == "catchup_stale"


def test_stale_observation_receipt_is_unavailable():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(
        _health(observed_at="2026-10-05T21:50:00+00:00", last_successful_catchup="2026-10-05T21:49:50+00:00"),
        now=NOW,
        max_observation_age_seconds=120,
    )

    assert parsed["state"] == "unavailable"
    assert parsed["reason"] == "receipt_stale"


def test_gap_forces_degraded_even_when_socket_and_catchup_are_fresh():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(_health(gap_unresolved=True), now=NOW)

    assert parsed["state"] == "degraded"
    assert parsed["reason"] == "gap_unresolved"


def test_missing_catchup_never_claims_live():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(_health(last_successful_catchup=None), now=NOW)

    assert parsed["state"] == "catching_up"
    assert parsed["reason"] == "catchup_pending"


def test_health_file_loader_is_unavailable_on_missing_or_malformed(tmp_path):
    from engine import qbus_news_receipts as m

    assert m.load_health_receipt(tmp_path / "missing.json", now=NOW)["state"] == "unavailable"
    path = tmp_path / "health.json"
    path.write_text("[]", encoding="utf-8")
    loaded = m.load_health_receipt(path, now=NOW)
    assert loaded["state"] == "unavailable"
    assert loaded["reason"] == "receipt_invalid"


def test_atomic_health_writer_replaces_file_and_uses_private_mode(tmp_path):
    from engine import qbus_news_receipts as m

    path = tmp_path / "runtime" / "news-health.json"
    payload = _health()
    m.write_health_receipt(path, payload)

    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == "qbus.news_health.v1"
    assert (os.stat(path).st_mode & 0o077) == 0
    assert list(path.parent.glob(".news-health.json.*.tmp")) == []


def test_health_rejects_future_observation_and_counter_booleans():
    from engine import qbus_news_receipts as m

    with pytest.raises(m.NewsReceiptError):
        m.parse_health_receipt(_health(observed_at="2026-10-06T00:00:00+00:00"), now=NOW)
    with pytest.raises(m.NewsReceiptError):
        m.parse_health_receipt(_health(connect_attempts=True), now=NOW)


def test_health_projects_diagnostic_error_codes_when_well_formed():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(
        _health(last_catchup_error="http_401", last_stream_error="stream_auth_error_406"),
        now=NOW,
    )

    assert parsed["last_catchup_error"] == "http_401"
    assert parsed["last_stream_error"] == "stream_auth_error_406"
    assert parsed["state"] == "live"
    assert parsed["reason"] == "fresh"


@pytest.mark.parametrize(
    "bad",
    ["Bearer abc/def", "HTTP 401 Bearer abc", 406, True, "", "a" * 65, ["http_401"]],
)
def test_health_invalid_diagnostic_codes_parse_as_none_and_never_gate(bad):
    from engine import qbus_news_receipts as m

    without_keys = m.parse_health_receipt(_health(), now=NOW)

    parsed = m.parse_health_receipt(
        _health(last_catchup_error=bad, last_stream_error=bad), now=NOW
    )

    assert parsed["last_catchup_error"] is None
    assert parsed["last_stream_error"] is None
    assert parsed["state"] == without_keys["state"]
    assert parsed["reason"] == without_keys["reason"]


def test_health_receipt_without_diagnostic_codes_parses_both_as_none():
    from engine import qbus_news_receipts as m

    parsed = m.parse_health_receipt(_health(), now=NOW)

    assert parsed["last_catchup_error"] is None
    assert parsed["last_stream_error"] is None


def test_health_base_carries_both_diagnostic_codes_as_none():
    from engine import qbus_news_receipts as m

    base = m._health_base("receipt_missing")

    assert base["last_catchup_error"] is None
    assert base["last_stream_error"] is None


def test_additional_health_reports_observations_without_inventing_upstream_recency():
    from engine.qbus_news_receipts import parse_health_receipt

    extra = {
        "provider": "massive", "state": "available",
        "last_successful_poll": "2026-10-05T21:59:50+00:00",
        "publishers": ["zacks.com", "fool.com"],
        "accepted_reports": 37, "last_error": None,
        "upstream_recency": "hourly",
    }
    health = parse_health_receipt(_health(additional_sources=[extra]), now=NOW)
    projected = health["additional_sources"][0]
    assert projected["state"] == "available"
    assert projected["delivery"] == "polled"
    assert projected["configured_publishers"] == ["fool.com", "zacks.com"]
    assert projected["accepted_reports_since_start"] == 37
    assert "upstream_recency" not in projected


@pytest.mark.parametrize("publishers,count", [
    (["https://zacks.com"], True), (["zacks.com"] * 65, -1), ("zacks.com", "37"),
])
def test_invalid_additional_health_diagnostics_do_not_become_coverage(publishers, count):
    from engine.qbus_news_receipts import parse_health_receipt

    extra = {
        "provider": "massive", "state": "available",
        "last_successful_poll": "2026-10-05T21:59:50+00:00",
        "publishers": publishers, "accepted_reports": count,
    }
    projected = parse_health_receipt(_health(additional_sources=[extra]), now=NOW)["additional_sources"][0]
    assert projected["state"] == "available"
    assert "configured_publishers" not in projected
    assert "accepted_reports_since_start" not in projected

# V7-P7: delivery observation must reach the real evidence and prompt consumers
# without becoming a new source revision or a grant to use restricted text.
@pytest.fixture
def news_evidence_health_fixture(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore, RoutedRevision

    database = tmp_path / "evidence.sqlite3"
    rights_path = tmp_path / "rights.json"
    health_path = tmp_path / "health.json"
    universe_path = tmp_path / "universe.json"
    rights = _rights(audiences=["site_full", "internal_research", "blog_draft"])
    rights["capabilities"]["derivative_processing"] = True
    rights_path.write_text(json.dumps(rights), encoding="utf-8")
    health_path.write_text(json.dumps(_health()), encoding="utf-8")
    monkeypatch.setenv("MM_TICKER_NEWS_HEALTH", str(health_path))
    universe_path.write_text(json.dumps({
        "owner": "fixture.security_reference", "revision": "fixture-universe-r1",
        "complete": True, "truncated": False,
        "effective_at": (NOW - timedelta(days=1)).isoformat(),
        "known_at": (NOW - timedelta(hours=1)).isoformat(),
        "fresh_until": (NOW + timedelta(days=1)).isoformat(),
        "securities": [{
            "security_id": "sec-NVDA", "ticker": "NVDA", "aliases": ["NVDA"],
            "valid_from": (NOW - timedelta(days=100)).isoformat(), "valid_to": None,
            "known_at": (NOW - timedelta(days=2)).isoformat(),
        }],
    }), encoding="utf-8")

    def commit(title="Nvidia launches new AI accelerator", minute=0, cursor=None):
        clock = NOW - timedelta(minutes=20) + timedelta(minutes=minute)
        revision = normalize_news({
            "id": "health-case", "title": title,
            "url": "https://benzinga.com/news/health-case",
            "teaser": "Unlicensed teaser must remain absent.",
            "created": (NOW - timedelta(hours=1)).isoformat(),
            "updated": clock.isoformat(), "stocks": ["NVDA"],
        }, transport="benzinga_rest", received_at=clock + timedelta(seconds=1))
        with NewsStore(database, source_key="fixture-writer") as store:
            store.commit([RoutedRevision(revision, ("sec-NVDA",), "fixture-universe-r1")],
                         expected_cursor=cursor, next_cursor=str(minute))
        return revision

    with NewsStore(database, source_key="fixture-writer"):
        pass
    return SimpleNamespace(
        database=database, rights_path=rights_path, health_path=health_path,
        universe_path=universe_path, rights=rights, commit=commit,
        args=dict(database=database, security_id="sec-NVDA",
                  receipt_paths=(rights_path,), audience="internal_research", now=NOW),
        slot={"id": "fixture-original", "desk": "research_note",
              "as_of": NOW.date().isoformat(),
              "story": {"kind": "company_update", "tickers": ["NVDA"]}},
    )


@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("mutation,expected,reason", [
    ({}, "live", "fresh"),
    ({"observed_at": (NOW - timedelta(minutes=3)).isoformat(),
      "last_successful_catchup": (NOW - timedelta(minutes=3)).isoformat()},
     "unavailable", "receipt_stale"),
    ({"last_successful_catchup": (NOW - timedelta(minutes=3)).isoformat()},
     "degraded", "catchup_stale"),
    ({"gap_unresolved": True}, "degraded", "gap_unresolved"),
    ({"last_successful_catchup": None}, "catching_up", "catchup_pending"),
    ({"state": "unavailable"}, "unavailable", "source_unavailable"),
    ({"observed_at": (NOW + timedelta(seconds=1)).isoformat()},
     "unavailable", "receipt_invalid"),
])
def test_news_evidence_exposes_actual_delivery_health(
    news_evidence_health_fixture, populated, mutation, expected, reason,
):
    from engine.qbus_news_context import news_evidence_bundle

    fixture = news_evidence_health_fixture
    if populated:
        fixture.commit()
    fixture.health_path.write_text(json.dumps(_health(**mutation)), encoding="utf-8")
    bundle = news_evidence_bundle(**fixture.args)

    # Readable retained evidence and current delivery are different claims.
    assert bundle["state"] == "available"
    assert bundle["delivery_state"] == ("quiet" if expected == "live" and not populated else expected)
    assert bundle["health"]["reason"] == reason
    assert bool(bundle["stories"]) is populated
    assert bundle["publication_authorized"] is False
    if populated:
        assert bundle["stories"][0]["reports"][0]["teaser"] == ""


def test_missing_or_bad_health_does_not_claim_quiet_or_rewrite_evidence(
    news_evidence_health_fixture, monkeypatch,
):
    from engine.qbus_news_context import news_evidence_bundle

    fixture = news_evidence_health_fixture
    fixture.commit()
    before = news_evidence_bundle(**fixture.args)
    for value in ("not-json", json.dumps({"schema": "future.v99"})):
        fixture.health_path.write_text(value, encoding="utf-8")
        changed = news_evidence_bundle(**fixture.args)
        assert changed["delivery_state"] == "unavailable"
        assert changed["evidence_sha256"] == before["evidence_sha256"]
        assert changed["stories"] == before["stories"]
    fixture.health_path.unlink()
    assert news_evidence_bundle(**fixture.args)["health"]["reason"] == "receipt_missing"
    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH")
    missing = news_evidence_bundle(**fixture.args)
    assert missing["delivery_state"] == "unavailable"
    assert missing["health"]["reason"] == "receipt_path_unset"
    assert missing["evidence_sha256"] == before["evidence_sha256"]


def test_delivery_health_cannot_grant_derivative_or_field_rights(news_evidence_health_fixture):
    from engine.qbus_news_context import news_evidence_bundle

    fixture = news_evidence_health_fixture
    fixture.commit()
    fixture.rights["capabilities"]["derivative_processing"] = False
    fixture.rights_path.write_text(json.dumps(fixture.rights), encoding="utf-8")
    restricted = news_evidence_bundle(**fixture.args)
    assert restricted["state"] == restricted["delivery_state"] == "restricted"
    assert restricted["health"] is None
    assert restricted["stories"] == []
    assert restricted["evidence_sha256"] is None


def test_health_projection_keeps_only_permitted_publisher_scope():
    from engine.qbus_news_receipts import parse_health_receipt, scope_news_health
    from engine.qbus_news_store import NewsReadRights

    raw = parse_health_receipt(_health(additional_sources=[{
        "provider": "massive", "state": "available",
        "last_successful_poll": NOW.isoformat(),
        "publishers": ["reuters.com", "excluded.example"], "accepted_reports": 99,
    }], observed_at=NOW.isoformat()), now=NOW)
    scoped = scope_news_health(raw, NewsReadRights(frozenset({"massive:reuters.com"})))
    assert scoped["state"] == "unavailable"  # primary Benzinga is not entitled
    assert scoped["reason"] == "no_curated_primary_source"
    assert scoped["additional_sources"][0]["configured_publishers"] == ["reuters.com"]
    assert "accepted_reports_since_start" not in scoped["additional_sources"][0]
    assert "excluded.example" not in json.dumps(scoped)


def test_heartbeat_keeps_saved_basis_but_source_correction_changes_it(news_evidence_health_fixture):
    from engine.qbus_news_context import news_evidence_bundle

    fixture = news_evidence_health_fixture
    first = fixture.commit()
    before = news_evidence_bundle(**fixture.args)
    saved_bytes = json.dumps(before, sort_keys=True)
    fixture.health_path.write_text(json.dumps(_health(
        observed_at=NOW.isoformat(), last_successful_catchup=NOW.isoformat(),
    )), encoding="utf-8")
    heartbeat = news_evidence_bundle(**fixture.args)
    assert heartbeat["health"] != before["health"]
    assert heartbeat["evidence_sha256"] == before["evidence_sha256"]
    corrected = fixture.commit("Nvidia delays new AI accelerator", minute=1, cursor="0")
    after = news_evidence_bundle(**fixture.args)
    assert after["evidence_sha256"] != before["evidence_sha256"]
    assert after["stories"][0]["reports"][0]["revision_id"] == corrected.revision_id
    assert before["stories"][0]["reports"][0]["revision_id"] == first.revision_id
    assert json.dumps(before, sort_keys=True) == saved_bytes


def test_actual_press_prompt_carries_delivery_limit_and_rechecks_before_call(
    news_evidence_health_fixture, monkeypatch,
):
    from engine.press import qbus_news as consumer
    from engine.press.writer import build_prompt

    fixture = news_evidence_health_fixture
    fixture.commit()
    monkeypatch.setattr(consumer, "_utcnow", lambda: NOW)
    args = dict(database=fixture.database, universe_path=fixture.universe_path,
                receipt_paths=(fixture.rights_path,))
    prepared = consumer.prepare_slot(fixture.slot, **args)
    _, prompt = build_prompt(prepared, {})
    assert "News delivery is live" in prompt
    assert "individual report dates still apply" in prompt
    assert prepared["publication_authorized"] is False
    assert prepared["qbus_news_evidence"]["publication_authorized"] is False
    consumer.verify_slot(prepared, universe_path=fixture.universe_path,
                         receipt_paths=(fixture.rights_path,))

    # A fresh heartbeat does not strand the prepared evidence.
    fixture.health_path.write_text(json.dumps(_health(
        observed_at=NOW.isoformat(), last_successful_catchup=NOW.isoformat(),
    )), encoding="utf-8")
    consumer.verify_slot(prepared, universe_path=fixture.universe_path,
                         receipt_paths=(fixture.rights_path,))

    fixture.health_path.write_text(json.dumps(_health(gap_unresolved=True)), encoding="utf-8")
    with pytest.raises(consumer.PrivateNewsUnavailable, match="qbus_draft_delivery_changed"):
        consumer.verify_slot(prepared, universe_path=fixture.universe_path,
                             receipt_paths=(fixture.rights_path,))
    degraded = consumer.prepare_slot(fixture.slot, **args)
    _, prompt = build_prompt(degraded, {})
    assert "News delivery is degraded" in prompt
    assert "retained reports do not establish current or complete coverage" in prompt
    assert degraded["qbus_news_evidence"]["evidence_sha256"] == prepared["qbus_news_evidence"]["evidence_sha256"]
    consumer.verify_slot(degraded, universe_path=fixture.universe_path,
                         receipt_paths=(fixture.rights_path,))


def test_press_pre_call_observation_ages_even_without_receipt_write(
    news_evidence_health_fixture, monkeypatch,
):
    from engine.press import qbus_news as consumer

    fixture = news_evidence_health_fixture
    fixture.commit()
    monkeypatch.setattr(consumer, "_utcnow", lambda: NOW)
    prepared = consumer.prepare_slot(
        fixture.slot, database=fixture.database, universe_path=fixture.universe_path,
        receipt_paths=(fixture.rights_path,),
    )
    monkeypatch.setattr(consumer, "_utcnow", lambda: NOW + timedelta(minutes=3))
    with pytest.raises(consumer.PrivateNewsUnavailable, match="qbus_draft_delivery_changed"):
        consumer.verify_slot(prepared, universe_path=fixture.universe_path,
                             receipt_paths=(fixture.rights_path,))
