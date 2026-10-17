"""CPI publication hotfix regression: real production parser and watcher helpers.

Uses retained official BLS prose excerpts (not a production-network replay).
"""
from __future__ import annotations

from datetime import datetime, timezone
from copy import deepcopy
from types import SimpleNamespace

import pytest

from scripts.official_release_parsers import parse_cpi_actual
import scripts.watch_release_publications as watcher


OFFICIAL = b"""CONSUMER PRICE INDEX - SEPTEMBER 2026
The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.6 percent
on a seasonally adjusted basis in September after rising 0.4 percent in August.
Over the last 12 months, the all items index increased 3.7 percent before seasonal adjustment.
The index for all items less food and energy rose 0.3 percent in September, as it did in August.
The all items index rose 3.7 percent for the 12 months ending September.
The all items less food and energy index rose 2.6 percent over the year,
following a 2.4-percent increase over the 12 months ending August.
The index for all items less food and energy rose 2.6 percent over the past 12 months.
Not seasonally adjusted CPI measures.
For the month, the index rose 0.6 percent prior to seasonal adjustment.
"""


def _sample():
    actual = parse_cpi_actual(OFFICIAL)
    assert actual is not None
    event = {"event_id": "cpi:2026-10-14", "type": "CPI", "date": "2026-10-14"}
    document = {
        "source_url": "https://www.bls.gov/news.release/archives/cpi_10142026.htm",
        "binding_kind": "detail_document",
        "reference_period": "September 2026",
    }
    return actual, event, document


def test_september_cpi_four_typed_values_and_source_period():
    actual, _, _ = _sample()
    assert {k: actual[k] for k in ("headline_mom", "headline_yoy", "core_mom", "core_yoy")} == {
        "headline_mom": 0.6,
        "headline_yoy": 3.7,
        "core_mom": 0.3,
        "core_yoy": 2.6,
    }
    assert actual["reference_period"] == "September 2026"
    assert len(actual["metrics"]) == 4
    assert all(row["period"] == "September 2026" for row in actual["metrics"])


@pytest.mark.parametrize("mutation", [
    lambda s: s.replace("rose 2.6 percent over the past 12 months.", ""),
    lambda s: s.replace("rose 0.3 percent in September", "rose 0.3 percent in August"),
    lambda s: s.replace("on a seasonally adjusted basis", "on a not seasonally adjusted basis"),
    lambda s: s + " Reference period: August 2026",
    lambda s: s + " The all items less food and energy index rose 9.9 percent over the year.",
])
def test_bad_or_conflicting_cpi_prose_not_promoted(mutation):
    assert parse_cpi_actual(mutation(OFFICIAL.decode()).encode()) is None


def test_old_feed_shorthand_still_supported():
    text = (
        "Consumer Price Index for All Urban Consumers (CPI-U) rose 0.1 percent in July (SA); "
        "the index for all items increased 3.4 percent over the last 12 months, not seasonally adjusted. "
        "The index for all items less food and energy rose 0.2 percent in July (SA); "
        "the index for all items less food and energy was up 2.5 percent over the year (NSA). "
        "Reference period: July 2026"
    )
    actual = parse_cpi_actual(text.encode())
    assert actual is not None
    assert (actual["headline_mom"], actual["core_mom"], actual["headline_yoy"], actual["core_yoy"]) == (
        .1, .2, 3.4, 2.5
    )


def test_dated_document_bound_to_release():
    actual, event, document = _sample()
    assert watcher._cpi_detail_matches_release(actual, event, document)


@pytest.mark.parametrize("field,value", [
    ("source_url", "https://www.bls.gov/news.release/archives/cpi_09112026.htm"),
    ("source_url", "https://www.bls.gov.evil.test/news.release/archives/cpi_10142026.htm"),
    ("source_url", "https://u:p@www.bls.gov/news.release/archives/cpi_10142026.htm"),
    ("reference_period", "August 2026"),
    ("binding_kind", "feed_entry"),
])
def test_cpi_dated_document_mismatch_is_rejected(field, value):
    actual, event, document = _sample()
    document[field] = value
    assert not watcher._cpi_detail_matches_release(actual, event, document)


@pytest.mark.parametrize("problem", ["missing", "wrong_period", "wrong_unit", "duplicate"])
def test_cpi_identity_mismatch_is_rejected(problem):
    actual, event, document = _sample()
    if problem == "missing":
        actual["metrics"].pop()
    elif problem == "wrong_period":
        actual["metrics"][0]["period"] = "August 2026"
    elif problem == "wrong_unit":
        actual["metrics"][0]["unit"] = "index_level"
    else:
        actual["metrics"][0]["metric_id"] = actual["metrics"][1]["metric_id"]
    assert not watcher._cpi_detail_matches_release(actual, event, document)


@pytest.mark.parametrize("actual,error,status", [
    ({}, None, "incomplete"),
    ({"kind": "inflation"}, None, "verified"),
    ({}, "TimeoutError", "source_unavailable"),
])
def test_extraction_records_attempt_vs_success(actual, error, status):
    now = datetime(2026, 10, 15, 2, 45, tzinfo=timezone.utc)
    before = {"status": "verified", "last_success_at": "2026-10-14T12:31:00+00:00"}
    copy = deepcopy(before)
    updated = watcher._extraction_attempt(before, actual=actual, now=now, error=error)
    assert before == copy
    assert updated["status"] == status
    assert updated["last_attempt_at"] == now.isoformat()
    assert updated["last_success_at"] == (now.isoformat() if actual else before["last_success_at"])


@pytest.mark.parametrize("ready,version,attempted,expected", [
    (False, 1, None, True),
    (False, 2, None, False),
    (True, 1, None, False),
    (False, 1, {"name": "cpi", "version": 2}, False),
    (False, 1, {"name": "cpi", "version": 1}, True),
])
def test_upgrade_is_single_catchup_not_retry_storm(monkeypatch, ready, version, attempted, expected):
    monkeypatch.setattr(
        watcher, "SOURCES",
        (SimpleNamespace(actual_parser="cpi", actual_parser_version=2, event_types=("CPI",)),),
    )
    event = {"event_id": "cpi:2026-10-14", "type": "CPI"}
    publication = {"data_ready": ready, "parser": {"name": "cpi", "version": version}}
    if attempted is not None:
        publication["extraction"] = {"attempted_parser": attempted}
    assert bool(watcher._parser_upgrade_keys([event], {event["event_id"]: publication})) == expected


def test_cpi_feed_only_never_becomes_accepted_actual():
    """An official RSS publication with unavailable detail is not verified CPI."""
    import hashlib

    released = datetime(2026, 7, 14, 12, 35, tzinfo=timezone.utc)
    rss = """<feed xmlns="http://www.w3.org/2005/Atom">
    <id>bls.gov:feed:cpi</id><title>Consumer Price Index</title><entry>
    <title>Consumer Price Index — June 2026</title>
    <id>https://www.bls.gov/news.release/archives/cpi_07142026.htm</id>
    <published>2026-07-14T08:31:00-04:00</published>
    <link href="https://www.bls.gov/news.release/archives/cpi_07142026.htm"/>
    <content type="html">Consumer Price Index for All Urban Consumers rose 0.2 percent
    in June 2026. All items index rose 2.7 percent over the last 12 months.
    Core CPI 0.3 percent monthly.</content>
    </entry></feed>""".encode()
    calls = []

    def fetcher(spec, prior, timeout):
        calls.append(spec.url)
        if spec.url.endswith("cpi_07142026.htm"):
            raise TimeoutError("detail unavailable")
        assert spec.url == "https://www.bls.gov/feed/cpi.rss"
        return {
            "status": 200,
            "body": rss,
            "fingerprint": hashlib.sha256(rss).hexdigest(),
            "etag": '"rss"',
            "last_modified": "Tue, 14 Jul 2026 12:35:00 GMT",
            "content_type": "application/atom+xml",
        }

    _, payload = watcher.detect(now=released, state={}, fetcher=fetcher)
    cpi = next(row for row in payload["publications"] if row["type"] == "CPI")
    assert cpi["status"] == "published_unparsed"
    assert cpi["data_ready"] is False
    assert not cpi.get("actual")
    assert cpi["extraction"]["status"] == "source_unavailable"
    assert cpi["extraction"]["error_code"] == "TimeoutError"
    assert calls == [
        "https://www.bls.gov/feed/cpi.rss",
        "https://www.bls.gov/news.release/archives/cpi_07142026.htm",
    ]
