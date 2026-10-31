from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path

import pytest

from engine.release_actuals import (
    canonical_actual,
    is_scoring_truth_eligible,
    load_actual_ledger,
    normalize_publication,
    receipt_integrity_errors,
    receipts_from_payload,
    reconcile_receipts,
)
from scripts.reconcile_release_actuals import reconcile
from scripts.official_release_parsers import parse_cpi_actual
import scripts.watch_release_publications as watcher

_CASES = {
    "CPI": {
        "date": "2026-07-14",
        "reference_period": "June 2026",
        "publisher": "U.S. Bureau of Labor Statistics",
        "source_id": "bls_cpi",
        "source_url": "https://www.bls.gov/news.release/archives/cpi_07142026.htm",
        "parser": "cpi",
        "actual": {
            "headline_mom": -0.4,
            "core_mom": 0.0,
            "unit": "percent",
        },
    },
    "PPI": {
        "date": "2026-07-15",
        "reference_period": "June 2026",
        "publisher": "U.S. Bureau of Labor Statistics",
        "source_id": "bls_ppi",
        "source_url": "https://www.bls.gov/news.release/archives/ppi_07152026.htm",
        "parser": "ppi",
        "actual": {"headline_mom": 0.2, "unit": "percent"},
    },
    "NFP": {
        "date": "2026-08-07",
        "reference_period": "July 2026",
        "publisher": "U.S. Bureau of Labor Statistics",
        "source_id": "bls_employment",
        "source_url": "https://www.bls.gov/news.release/archives/empsit_08072026.htm",
        "parser": "nfp",
        "actual": {"payroll_change": 57_000, "unit": "persons"},
    },
    "PCE": {
        "date": "2026-07-30",
        "reference_period": "June 2026",
        "publisher": "U.S. Bureau of Economic Analysis",
        "source_id": "bea_pce",
        "source_url": "https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026",
        "parser": "pce",
        "actual": {"headline_mom": -0.1, "core_mom": 0.1, "unit": "percent"},
    },
    "CLAIMS": {
        "date": "2026-08-06",
        "reference_period": "August 1, 2026",
        "publisher": "U.S. Department of Labor",
        "source_id": "dol_claims",
        "source_url": "https://www.dol.gov/newsroom/releases/eta/eta20260806",
        "parser": "claims",
        "actual": {"initial_claims": 199_000, "unit": "persons"},
    },
}


# Named disclosure set: the two PCE 2026-06 receipts whose source URL was bound
# to a shared RSS digest (SHA 29ae0bad…) after a 304. The committed defects
# sidecar quarantines exactly these ids. Do not grow this set from the live
# ledger's current cardinality — later bound prints are keep-first actuals, not
# members of the defect set.
_QUARANTINED_PCE_RECEIPT_IDS = frozenset(
    {
        "official_actual:0492229833dc679fdb39494f",
        "official_actual:3af69117d78be4d9ea46b002",
    }
)
_KNOWN_PCE_BINDING_DEFECT_SHA256 = (
    "29ae0bad7d568ca7ea59be2f74461b5dcf5da4393ff816544254cd47507f13e1"
)


def _committed_official_actuals() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "release_forecast"
        / "official_actuals.jsonl"
    )


def _named_quarantined_pce_receipts() -> list[dict]:
    """The two known binding-defect PCE receipts, and nothing the nightly added later.

    ``official_actuals.jsonl`` is a live keep-first ledger. The 2026-08-13 regime
    update (``44c90f8f547``) wrote scoring-eligible bound PCE 2026-06 prints
    (SHA ``62e09584…``) next to the quarantined pair. Passing the whole file as
    ``existing`` turns a fresh bound replay into ``correction_candidate`` —
    keep-first working, not a regression. This named disclosure set is the
    census the yield contract actually needs.
    """
    rows = [
        row
        for row in load_actual_ledger(_committed_official_actuals())
        if row.get("receipt_id") in _QUARANTINED_PCE_RECEIPT_IDS
    ]
    assert {row["receipt_id"] for row in rows} == _QUARANTINED_PCE_RECEIPT_IDS
    assert all(not is_scoring_truth_eligible(row) for row in rows)
    return rows


def _publication(event_type: str = "CPI") -> dict:
    case = _CASES[event_type]
    day = case["date"]
    actual = {**case["actual"], "reference_period": case["reference_period"]}
    return {
        "event_id": f"{event_type.lower()}:{day}",
        "type": event_type,
        "date": day,
        "reference_period": case["reference_period"],
        "data_ready": True,
        "publisher": case["publisher"],
        "source_id": case["source_id"],
        "source_url": case["source_url"],
        "source_sha256": "a" * 64,
        "first_seen_at": f"{day}T12:30:01+00:00",
        "observed_at": f"{day}T12:30:01+00:00",
        "source_released_at": f"{day}T12:30:00+00:00",
        "verified_at": f"{day}T12:31:00+00:00",
        "parser": {"name": case["parser"], "version": 1},
        "actual": actual,
    }


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        ("CPI", [("cpi_headline", "2026-06", -0.4), ("cpi_core", "2026-06", 0.0)]),
        ("PPI", [("ppi_finaldemand", "2026-06", 0.2)]),
        ("NFP", [("nfp", "2026-07", 57.0)]),
        ("PCE", [("pce_headline", "2026-06", -0.1), ("pce_core", "2026-06", 0.1)]),
        ("CLAIMS", [("claims", "2026-08-06", 199.0)]),
    ],
)
def test_each_target_normalizes_only_from_compatible_official_source(
    event_type: str,
    expected: list[tuple[str, str, float]],
) -> None:
    rows = normalize_publication(_publication(event_type))
    assert [(row["release"], row["period"], row["actual"]) for row in rows] == expected
    assert all(row["actual_basis"] == "official_published_metric" for row in rows)
    assert all(row["automatic_scoring_eligible"] is True for row in rows)
    assert all(receipt_integrity_errors(row) == [] for row in rows)


@pytest.mark.parametrize("event_type", list(_CASES))
def test_agency_source_id_and_parser_contracts_fail_closed(event_type: str) -> None:
    bad = _publication(event_type)
    bad["source_url"] = "https://www.federalreserve.gov/not-the-publisher"
    assert normalize_publication(bad) == []

    bad = _publication(event_type)
    bad["publisher"] = "Wrong agency"
    assert normalize_publication(bad) == []

    bad = _publication(event_type)
    bad["source_id"] = "wrong_source"
    assert normalize_publication(bad) == []

    bad = _publication(event_type)
    bad["parser"]["name"] = "wrong_parser"
    assert normalize_publication(bad) == []

    bad = _publication(event_type)
    bad["parser"]["version"] = 3 if event_type == "CPI" else 2
    assert normalize_publication(bad) == []



def test_cpi_v2_current_receipts_accept_without_invalidating_v1_history() -> None:
    """The repaired watcher may emit v2; keep-first CPI v1 truth stays readable."""
    historical = normalize_publication(_publication("CPI"))
    assert len(historical) == 2
    assert all(row["parser_version"] == 1 for row in historical)

    current = _publication("CPI")
    current["parser"]["version"] = 2
    repaired = normalize_publication(current)
    assert len(repaired) == 2
    assert all(row["parser_version"] == 2 for row in repaired)
    assert all(receipt_integrity_errors(row) == [] for row in repaired)
    # The metric identity and source digest, not parser generation, determine
    # keep-first receipt identity; a parser upgrade cannot create a duplicate.
    assert [row["receipt_id"] for row in repaired] == [
        row["receipt_id"] for row in historical
    ]


def test_unofficial_domain_or_missing_hash_fails_closed() -> None:
    bad = _publication("CPI")
    bad["source_url"] = "https://example.com/cpi"
    assert normalize_publication(bad) == []
    bad = _publication("CPI")
    bad["source_sha256"] = None
    assert normalize_publication(bad) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_seen_at", "2026-08-07 12:30:01"),
        ("observed_at", "2026-08-07"),
        ("source_released_at", "not-a-time"),
        ("verified_at", "2026-08-07T12:31:00"),
    ],
)
def test_timestamps_require_full_timezone_aware_iso(field: str, value: str) -> None:
    bad = _publication("NFP")
    bad[field] = value
    assert normalize_publication(bad) == []


def test_observation_cannot_precede_source_release() -> None:
    bad = _publication("NFP")
    bad["source_released_at"] = "2026-08-07T14:30:46+00:00"
    assert normalize_publication(bad) == []

    bad = _publication("NFP")
    bad["verified_at"] = "2026-08-07T12:29:59+00:00"
    assert normalize_publication(bad) == []


def test_malformed_or_mismatched_nfp_reference_period_fails_closed() -> None:
    malformed = _publication("NFP")
    malformed["actual"]["reference_period"] = "The"
    assert normalize_publication(malformed) == []

    mismatched = _publication("NFP")
    mismatched["actual"]["reference_period"] = "June 2026"
    assert normalize_publication(mismatched) == []


def test_explicit_source_period_avoids_mechanical_month_minus_one() -> None:
    delayed = _publication("PCE")
    delayed["date"] = "2026-08-31"
    delayed["event_id"] = "pce:2026-08-31"
    delayed["first_seen_at"] = "2026-08-31T12:30:01+00:00"
    delayed["observed_at"] = "2026-08-31T12:30:01+00:00"
    delayed["source_released_at"] = "2026-08-31T12:30:00+00:00"
    delayed["verified_at"] = "2026-08-31T12:31:00+00:00"
    rows = normalize_publication(delayed)
    assert {row["period"] for row in rows} == {"2026-06"}
    assert all(
        row["period_resolution"] == "validated_parser_and_source_reference_period"
        for row in rows
    )


def test_claims_reference_week_must_match_source_and_schedule() -> None:
    bad = _publication("CLAIMS")
    bad["actual"]["reference_period"] = "August 8, 2026"
    bad["reference_period"] = "August 8, 2026"
    assert normalize_publication(bad) == []


def test_canonical_actual_revalidates_persisted_truth() -> None:
    valid = normalize_publication(_publication("NFP"))[0]
    assert canonical_actual([valid], "nfp", "2026-07") == valid

    malformed_period = {**valid, "official_reference_period": "The"}
    assert "reference_period_invalid" in receipt_integrity_errors(malformed_period)
    assert canonical_actual([malformed_period], "nfp", "2026-07") is None

    early = {
        **valid,
        "source_released_at": "2026-08-07T14:30:46+00:00",
    }
    assert "observed_before_source_release" in receipt_integrity_errors(early)
    assert canonical_actual([early], "nfp", "2026-07") is None

    wrong_agency = {**valid, "source_id": "bea_pce"}
    assert "source_id_mismatch" in receipt_integrity_errors(wrong_agency)
    assert canonical_actual([wrong_agency], "nfp", "2026-07") is None


def test_defect_sidecar_is_absent_open_and_matching_malformed_closed(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "absent.json"
    row = normalize_publication(
        _publication("PCE"),
        defects_path=missing,
    )[0]
    assert is_scoring_truth_eligible(row, defects_path=missing)

    unrelated = tmp_path / "unrelated.json"
    unrelated.write_text(
        json.dumps(
            {
                "schema": "official_actual_defects.v1",
                "defects_by_receipt": {"official_actual:unrelated": "malformed"},
            }
        ),
        encoding="utf-8",
    )
    assert is_scoring_truth_eligible(row, defects_path=unrelated)

    matching = tmp_path / "matching.json"
    matching.write_text(
        json.dumps(
            {
                "schema": "official_actual_defects.v1",
                "defects_by_receipt": {row["receipt_id"]: "malformed"},
            }
        ),
        encoding="utf-8",
    )
    assert receipt_integrity_errors(row, defects_path=matching)[-1] == (
        "known_source_binding_defect"
    )
    assert not is_scoring_truth_eligible(row, defects_path=matching)
    assert canonical_actual(
        [row],
        row["release"],
        row["period"],
        defects_path=matching,
    ) is None

    invalid_root = tmp_path / "invalid.json"
    invalid_root.write_text("{not-json", encoding="utf-8")
    assert "official_actual_defect_sidecar_invalid" in receipt_integrity_errors(
        row,
        defects_path=invalid_root,
    )
    assert not is_scoring_truth_eligible(row, defects_path=invalid_root)


def test_keep_first_and_correction_candidate() -> None:
    payload = {"schema": "release_publications.v2", "publications": [_publication("CPI")]}
    first = receipts_from_payload(payload)
    assert len(reconcile_receipts(payload, [])) == 2
    changed = _publication("CPI")
    changed["source_sha256"] = "b" * 64
    changed["actual"]["headline_mom"] = -0.3
    novel = reconcile_receipts(
        {"schema": "release_publications.v2", "publications": [changed]}, first
    )
    assert all(row["row_type"] == "correction_candidate" for row in novel)
    assert canonical_actual(first + novel, "cpi_headline", "2026-06")["actual"] == -0.4


def test_quarantined_pce_receipts_yield_to_fresh_bound_receipts() -> None:
    defective_replay = _publication("PCE")
    defective_replay["source_sha256"] = _KNOWN_PCE_BINDING_DEFECT_SHA256
    assert reconcile_receipts(
        {
            "schema": "release_publications.v2",
            "publications": [defective_replay],
        },
        [],
    ) == []

    existing = _named_quarantined_pce_receipts()

    corrected = _publication("PCE")
    corrected["source_sha256"] = "b" * 64
    payload = {"schema": "release_publications.v2", "publications": [corrected]}

    novel = reconcile_receipts(payload, existing)

    assert len(novel) == 2
    assert all(row["row_type"] == "actual" for row in novel)
    assert all(row["automatic_scoring_eligible"] is True for row in novel)
    assert all(is_scoring_truth_eligible(row) for row in novel)
    for release in ("pce_headline", "pce_core"):
        winner = canonical_actual(existing + novel, release, "2026-06")
        assert winner is not None
        assert winner["source_sha256"] == "b" * 64
        assert winner["receipt_id"] in {row["receipt_id"] for row in novel}


def test_file_reconciliation_is_idempotent(tmp_path: Path) -> None:
    payload_path = tmp_path / "live.json"
    out = tmp_path / "actuals.jsonl"
    payload_path.write_text(
        json.dumps({"schema": "release_publications.v2", "publications": [_publication("CPI")]}),
        encoding="utf-8",
    )
    assert len(reconcile(str(payload_path), out)) == 2
    assert reconcile(str(payload_path), out) == []
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2


def test_committed_official_actual_ledger_quarantines_known_pce_binding_defects(
    tmp_path: Path,
) -> None:
    rows = load_actual_ledger(_committed_official_actuals())
    assert rows
    missing_sidecar = tmp_path / "absent.json"
    assert all(
        receipt_integrity_errors(row, defects_path=missing_sidecar) == []
        for row in rows
    )
    quarantined = {
        row["receipt_id"]
        for row in rows
        if "known_source_binding_defect" in receipt_integrity_errors(row)
    }
    assert quarantined == _QUARANTINED_PCE_RECEIPT_IDS
    assert all(
        is_scoring_truth_eligible(row) == (row["receipt_id"] not in quarantined)
        for row in rows
    )
    assert all(row.get("official_reference_period") != "The" for row in rows)


# CPI October 2026 recovery: retained typed parser and watcher regressions.
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


def _aged_cpi_state(**overrides):
    _, event, document = _sample()
    row = {
        **event, "time_et": "08:30", "source_id": "bls_cpi",
        "status": "published_unparsed", "data_ready": False,
        "source_url": document["source_url"], "reference_period": "September 2026",
        "source_sha256": "a" * 64, "content_sha256": "a" * 64,
        "detected_at": "2026-10-14T12:31:17+00:00",
        "parser": {"name": "cpi", "version": 1}, **overrides,
    }
    return {"publications": {event["event_id"]: row}}


def test_aged_cpi_recovers_on_ordinary_tick_without_feed_or_rebuild(monkeypatch):
    import hashlib
    from datetime import timedelta

    monkeypatch.setattr(watcher, "scheduled_releases", lambda *args, **kwargs: [])
    state = _aged_cpi_state()
    event_id, before = next(iter(state["publications"].items()))
    now = datetime(2026, 10, 31, 6, 4, tzinfo=timezone.utc)
    calls = []

    def fetch(spec, prior, timeout):
        calls.append(spec.url)
        assert spec.url == before["source_url"]
        assert not prior
        if len(calls) == 1:
            raise TimeoutError("temporarily unavailable")
        return {"status": 200, "body": OFFICIAL, "url": spec.url,
                "fingerprint": hashlib.sha256(OFFICIAL).hexdigest()}

    state, _ = watcher.detect(now=now, state=state, fetcher=fetch)
    assert calls == [before["source_url"]]
    row = state["publications"][event_id]
    assert row["data_ready"] is False and row["source_url"] == before["source_url"]
    assert row["extraction"]["status"] == "source_unavailable"
    state, _ = watcher.detect(now=now + timedelta(minutes=1), state=state, fetcher=fetch)
    assert len(calls) == 1
    state, payload = watcher.detect(now=now + timedelta(hours=1), state=state, fetcher=fetch)
    row, = payload["publications"]
    assert len(calls) == 2 and row["event_id"] == event_id
    assert row["status"] == "published" and row["data_ready"] is True
    assert row["detected_at"] == before["detected_at"]
    assert row["actual"]["source_url"] == before["source_url"]
    assert row["source_sha256"] == row["content_sha256"] == hashlib.sha256(OFFICIAL).hexdigest()
    assert row["extraction"]["status"] == "verified" and len(row["actual"]["metrics"]) == 4
    watcher.detect(now=now + timedelta(days=1), state=state, fetcher=fetch)
    assert len(calls) == 2


@pytest.mark.parametrize("override", [
    {"source_url": "https://www.bls.gov/feed/cpi.rss"},
    {"source_url": "https://www.bls.gov/news.release/archives/cpi_09112026.htm"},
    {"source_url": "https://www.bls.gov.evil.test/news.release/archives/cpi_10142026.htm"},
    {"data_ready": True}, {"reference_period": ""}, {"source_id": "bls_ppi"},
])
def test_aged_cpi_replay_requires_retained_event_bound_evidence(monkeypatch, override):
    monkeypatch.setattr(watcher, "scheduled_releases", lambda *args, **kwargs: [])
    calls = []
    watcher.detect(now=datetime(2026, 10, 31, tzinfo=timezone.utc),
                   state=_aged_cpi_state(**override), fetcher=lambda *args: calls.append(args))
    assert not calls


@pytest.mark.parametrize("fault", ["wrong_period", "redirect", "malformed"])
def test_aged_cpi_rejects_unbound_document_and_exhausts_budget(monkeypatch, fault):
    import hashlib
    from datetime import timedelta

    monkeypatch.setattr(watcher, "scheduled_releases", lambda *args, **kwargs: [])
    state = _aged_cpi_state()
    key, before = next(iter(state["publications"].items()))
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    calls = []

    def fetch(spec, prior, timeout):
        calls.append(spec.url)
        body = {"wrong_period": OFFICIAL.replace(b"September", b"August").replace(b"SEPTEMBER", b"AUGUST"),
                "malformed": b"pending"}.get(fault, OFFICIAL)
        url = spec.url if fault != "redirect" else "https://www.bls.gov/news.release/cpi.htm"
        return {"status": 200, "body": body, "url": url,
                "fingerprint": hashlib.sha256(body).hexdigest()}

    for hours in [0, 1, 3, 24]:
        state, _ = watcher.detect(now=now + timedelta(hours=hours), state=state, fetcher=fetch)
        row = state["publications"][key]
        assert row["data_ready"] is False and not row.get("actual")
        assert row["source_sha256"] == before["source_sha256"]
        assert row["source_url"] == before["source_url"]
    assert len(calls) == 3
    assert state[watcher.DEFECT_REPAIR_STATE_KEY][key]["status"] == "exhausted"
