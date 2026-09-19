from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from scripts import official_release_parsers
from scripts import watch_release_publications as wrp


CLAIMS_SEPTEMBER_10_LISTING = b"""
<div class="view-content"><div class="dol-feed-block">
  <div data-history-node-id="fixture"
       about="/newsroom/releases/eta/eta20260910">
    <p class="dol-date-text">September 10, 2026</p>
    <a href="/newsroom/releases/eta/eta20260910">
      <h3><span>Unemployment Insurance Weekly Claims Report</span></h3>
    </a>
    <div class="field--name-field-press-body">
      <p>In the week ending September 5, the advance figure for seasonally adjusted
      initial claims was 206,000, a decrease of 1,000 from the previous week's
      revised level. The 4-week moving average was 206,000.</p>
    </div>
  </div>
</div></div>
"""

FOMC_SEPTEMBER_16_STATEMENT = b"""
<html><body>
<p>September 16, 2026</p>
<p>The Federal Open Market Committee approved the following statement for release
by a 12 - 0 vote:</p>
<p>The Committee decided to raise the target range for the federal funds rate by
1/4 percentage point to 3-3/4 to 4 percent, in support of the Federal Reserve's
dual mandate.</p>
</body></html>
"""


def _http_result(body: bytes) -> dict[str, object]:
    return {
        "status": 200,
        "body": body,
        "fingerprint": hashlib.sha256(body).hexdigest(),
        "etag": '"fixture"',
        "last_modified": "Thu, 10 Sep 2026 12:30:00 GMT",
        "content_type": "text/html; charset=UTF-8",
    }


def _claims_event() -> dict[str, object]:
    return {
        "event_id": "claims:2026-09-10",
        "type": "CLAIMS",
        "date": "2026-09-10",
        "time_et": "08:30",
        "scheduled_at": "2026-09-10T08:30:00-04:00",
        "label": "Initial jobless claims",
        "label_zh": "初请失业金人数",
        "schedule_source": "computed",
        "is_context_only": True,
    }


def _fomc_event() -> dict[str, object]:
    return {
        "event_id": "fomc:2026-09-16",
        "type": "FOMC",
        "date": "2026-09-16",
        "time_et": "14:00",
        "scheduled_at": "2026-09-16T14:00:00-04:00",
        "label": "FOMC rate decision",
        "label_zh": "美联储议息会议",
        "schedule_source": "federal_reserve",
        "is_context_only": True,
    }


def _claims_state() -> dict[str, object]:
    return {
        "schema": "release_publication_state.v2",
        "coverage_started_at_by_type": {
            "CLAIMS": "2026-09-10T12:00:00+00:00",
        },
        "sources": {},
        "publications": {},
    }


def test_fomc_parser_accepts_explicit_change_size_before_target_range() -> None:
    actual = wrp.parse_fomc_actual(FOMC_SEPTEMBER_16_STATEMENT)

    assert actual is not None
    assert actual["action"] == "hike"
    assert actual["target_low"] == 3.75
    assert actual["target_high"] == 4.0
    assert actual["vote_for"] == 12
    assert actual["vote_against"] == 0


def test_fomc_change_size_statement_publishes_with_parser_v2(monkeypatch) -> None:
    event = _fomc_event()
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])

    def fetcher(spec, prior, timeout):
        assert spec.source_id == "fed_fomc"
        return _http_result(FOMC_SEPTEMBER_16_STATEMENT)

    _, payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 3, tzinfo=timezone.utc),
        state={},
        fetcher=fetcher,
    )

    publication = payload["publications"][0]
    assert publication["status"] == "published"
    assert publication["actual"]["action"] == "hike"
    assert publication["parser"] == {"name": "fomc", "version": 2}


def test_dol_overdue_release_retries_through_retention_and_self_heals(monkeypatch) -> None:
    event = _claims_event()
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])
    calls = []

    def fetcher(spec, prior, timeout):
        calls.append(spec.url)
        assert spec.source_id == "dol_claims"
        assert spec.url == "https://www.dol.gov/index.php/newsroom/releases/eta"
        return _http_result(CLAIMS_SEPTEMBER_10_LISTING)

    new_state, payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 15, tzinfo=timezone.utc),
        state=_claims_state(),
        fetcher=fetcher,
    )

    assert calls == ["https://www.dol.gov/index.php/newsroom/releases/eta"]
    publication = next(
        row for row in payload["publications"]
        if row["event_id"] == "claims:2026-09-10"
    )
    assert publication["status"] == "published"
    assert publication["data_ready"] is True
    assert publication["actual"]["initial_claims"] == 206_000
    assert publication["actual"]["change"] == -1_000
    assert publication["source_url"] == (
        "https://www.dol.gov/index.php/newsroom/releases/eta/eta20260910"
    )

    source = new_state["sources"]["dol_claims:claims:2026-09-10"]
    assert source["attempt_count"] == 1
    assert source["first_attempt_at"] == "2026-09-16T18:15:00+00:00"
    assert source["last_attempt_at"] == "2026-09-16T18:15:00+00:00"
    assert source["last_attempt_status"] == "ok"
    assert source["last_success_at"] == "2026-09-16T18:15:00+00:00"


def test_overdue_source_failure_lineage_survives_then_recovers(monkeypatch) -> None:
    event = _claims_event()
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])
    first_tick = datetime(2026, 9, 16, 18, 15, tzinfo=timezone.utc)

    def failing_fetcher(spec, prior, timeout):
        raise TimeoutError("official source timed out")

    failed_state, failed_payload = wrp.detect(
        now=first_tick,
        state=_claims_state(),
        fetcher=failing_fetcher,
    )

    key = "dol_claims:claims:2026-09-10"
    failed = failed_state["sources"][key]
    assert failed["attempt_count"] == 1
    assert failed["first_attempt_at"] == first_tick.isoformat()
    assert failed["last_attempt_at"] == first_tick.isoformat()
    assert failed["last_attempt_status"] == "error"
    assert failed["last_error"] == "TimeoutError"
    assert failed["last_error_at"] == first_tick.isoformat()
    assert failed_payload["source_health"] == [
        {
            "source_id": "dol_claims",
            "event_id": "claims:2026-09-10",
            "status": "error",
            "error": "TimeoutError",
        }
    ]

    def unexpected_fetcher(spec, prior, timeout):
        raise AssertionError("non-periodic ticks must not hot-loop an overdue source")

    retained_state, retained_payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 16, tzinfo=timezone.utc),
        state=failed_state,
        fetcher=unexpected_fetcher,
    )
    assert retained_state["sources"][key] == failed
    assert retained_payload["source_health"] == []

    def recovering_fetcher(spec, prior, timeout):
        return _http_result(CLAIMS_SEPTEMBER_10_LISTING)

    recovered_state, recovered_payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 30, tzinfo=timezone.utc),
        state=retained_state,
        fetcher=recovering_fetcher,
    )
    recovered = recovered_state["sources"][key]
    assert recovered["attempt_count"] == 2
    assert recovered["last_attempt_status"] == "ok"
    assert recovered["last_success_at"] == "2026-09-16T18:30:00+00:00"
    assert recovered["last_error"] == "TimeoutError"
    assert recovered["last_error_at"] == first_tick.isoformat()
    publication = next(
        row for row in recovered_payload["publications"]
        if row["event_id"] == "claims:2026-09-10"
    )
    assert publication["status"] == "published"


def test_dol_entry_source_url_uses_accessible_first_party_path() -> None:
    entry = official_release_parsers.extract_feed_entry(
        "dol_claims",
        CLAIMS_SEPTEMBER_10_LISTING,
        "2026-09-10",
    )

    assert entry is not None
    assert entry["source_url"] == (
        "https://www.dol.gov/index.php/newsroom/releases/eta/eta20260910"
    )
