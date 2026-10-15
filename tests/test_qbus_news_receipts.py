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
