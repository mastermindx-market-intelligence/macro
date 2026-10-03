from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd
import pytest


UTC = timezone.utc
LEGACY_COLUMNS = [
    "package_ndc", "generic_name", "brand_name", "substance_name", "status",
    "availability", "initial_posting_date", "update_date", "discontinued_date",
    "therapeutic_category", "company_name", "related_info", "fetched_utc",
]


def _record(ndc="TEST-A", name="Synthetic A", status="Current",
            availability="Available", posted="2026-03-02"):
    return {
        "package_ndc": ndc,
        "generic_name": name,
        "status": status,
        "availability": availability,
        "initial_posting_date": posted,
        "company_name": "Synthetic Pharma Works",
    }


def _page(generation, records, total):
    return {
        "meta": {"last_updated": generation, "results": {"total": total}},
        "results": list(records),
    }


def _clock(start, finish=None):
    calls = 0

    def tick():
        nonlocal calls
        calls += 1
        return start if calls == 1 else (start if finish is None else finish)

    return tick


def _sweep(generation, records, start=datetime(2026, 9, 23, 12, tzinfo=UTC),
           finish=datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC), page_size=100,
           max_pages=5):
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        return _page(generation, records[skip:skip + limit], len(records))

    return collect_shortage_sweep(
        fetch_page, clock=_clock(start, finish), page_size=page_size,
        max_pages=max_pages,
    )


def _sidecar_digest(path):
    sidecar = path.with_suffix(".observation.json")
    if not sidecar.exists():
        return None
    return hashlib.sha256(sidecar.read_bytes()).hexdigest()


def test_late_page_failure_is_not_a_current_sweep():
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        if skip:
            raise OSError("synthetic second page failure")
        return {"meta": {"last_updated": "2026-09-23", "results": {"total": 2}},
                "results": [{"package_ndc": "TEST-A", "generic_name": "Synthetic A",
                             "status": "Current", "initial_posting_date": "2026-03-02"}]}

    result = collect_shortage_sweep(
        fetch_page,
        clock=lambda: datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
        page_size=1, max_pages=2,
    )
    assert result["qualified"] is False
    assert result["failure_code"] == "PAGE_FAILED"


def test_complete_single_page_is_qualified_with_observed_generation():
    result = _sweep("2026-09-23", [_record()])
    assert result["qualified"] is True
    assert result["failure_code"] is None
    assert len(result["rows"]) == 1
    assert result["rows"][0]["observed_generation"] == "2026-09-23"
    assert result["capture"]["pages"] == 1
    assert result["capture"]["raw_count"] == 1
    assert result["capture"]["unique_count"] == 1
    assert result["capture"]["reported_total"] == 1
    assert result["capture"]["complete"] is True


def test_complete_empty_is_qualified(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    result = _sweep("2026-09-20", [])
    assert result["qualified"] is True
    assert result["rows"] == []
    assert result["capture"]["raw_count"] == 0
    assert result["capture"]["unique_count"] == 0
    assert result["capture"]["reported_total"] == 0
    assert result["capture"]["complete"] is True

    path = tmp_path / "shortages.parquet"
    outcome = save_shortage_observation(
        result, path=path, expected_predecessor=None,
    )
    assert outcome["promoted"] is True
    state = read_shortage_observation(path=path)
    assert len(state["rows"]) == 0
    assert state["capture"]["source_generation"] == "2026-09-20"
    assert state["legacy"] is False


def test_first_page_outage_has_no_rows():
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        raise OSError("synthetic first page outage")

    result = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=100, max_pages=5,
    )
    assert result["qualified"] is False
    assert result["failure_code"] == "FIRST_PAGE_OUTAGE"
    assert result["rows"] == []


@pytest.mark.parametrize(
    ("pages", "expected_code"),
    [
        (
            [
                _page("2026-09-23", [_record()], 2),
                _page("2026-09-23", [], 1),
            ],
            "COUNT_DRIFT",
        ),
        (
            [
                _page("2026-09-23", [_record()], 2),
                _page("2026-09-24", [_record(ndc="TEST-B", name="Synthetic B")], 2),
            ],
            "GENERATION_DRIFT",
        ),
        (
            [
                _page("2026-09-23", [_record()], 2),
                _page("2026-09-23", [_record()], 2),
            ],
            "REPEATED_PAGE",
        ),
    ],
    ids=["count", "generation", "repeated"],
)
def test_page_consistency_failures_are_never_qualified(pages, expected_code):
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        return pages[skip // limit]

    result = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=1, max_pages=5,
    )
    assert result["qualified"] is False
    assert result["failure_code"] == expected_code


def test_non_dict_row_is_malformed():
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        return _page("2026-09-23", ["not-a-dict"], 1)

    result = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=100, max_pages=1,
    )
    assert result["failure_code"] == "MALFORMED_ROW"
    assert result["qualified"] is False


def test_cap_before_total_uses_live_reported_total():
    from collectors.fda_shortages import collect_shortage_sweep

    rows = [
        _record(), _record(ndc="TEST-B", name="Synthetic B"),
        _record(ndc="TEST-C", name="Synthetic C"),
    ]

    def fetch_page(skip, limit):
        return _page("2026-09-23", rows[skip:skip + limit], 3)

    result = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=1, max_pages=2,
    )
    assert result["failure_code"] == "CAP_BEFORE_TOTAL"
    assert result["capture"]["pages"] == 2
    assert result["capture"]["reported_total"] == 3


@pytest.mark.parametrize(
    "record",
    [
        {"generic_name": "Synthetic A", "initial_posting_date": "2026-03-02"},
        {"package_ndc": "", "initial_posting_date": "2026-03-02"},
        {"package_ndc": "TEST-A", "initial_posting_date": None},
    ],
    ids=["missing-ndc", "empty-ndc", "empty-date"],
)
def test_absent_stable_key_disqualifies_without_collapsing_rows(record):
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        return _page("2026-09-23", [record], 1)

    result = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=100, max_pages=1,
    )
    assert result["failure_code"] == "KEY_ABSENT"
    assert result["qualified"] is False
    assert result["capture"]["raw_count"] == 1


def test_changed_status_retains_the_prior_generation_value(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    first = _sweep("2026-09-20", [_record(status="Current")])
    save_shortage_observation(first, path=path, expected_predecessor=None)
    second = _sweep(
        "2026-09-23",
        [_record(status="Resolved", availability="Available")],
    )
    save_shortage_observation(
        second, path=path, expected_predecessor=_sidecar_digest(path),
    )

    row = read_shortage_observation(path=path)["rows"].iloc[0]
    assert row["status"] == "Resolved"
    assert row["previous_status"] == "Current"
    assert row["status_changed_generation"] == "2026-09-23"
    assert row["first_observed_generation"] == "2026-09-20"
    assert row["last_observed_generation"] == "2026-09-23"


def test_disappeared_row_is_retained_with_absence_generation(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    first = _sweep(
        "2026-09-20",
        [_record(ndc="TEST-A"), _record(ndc="TEST-B", name="Synthetic B")],
    )
    save_shortage_observation(first, path=path, expected_predecessor=None)
    second = _sweep("2026-09-23", [_record(ndc="TEST-A")])
    save_shortage_observation(
        second, path=path, expected_predecessor=_sidecar_digest(path),
    )

    rows = read_shortage_observation(path=path)["rows"].set_index("package_ndc")
    assert rows.loc["TEST-B", "status"] == "Current"
    assert rows.loc["TEST-B", "absent_since_generation"] == "2026-09-23"
    assert rows.loc["TEST-B", "last_observed_generation"] == "2026-09-20"
    assert pd.isna(rows.loc["TEST-A", "absent_since_generation"])


def test_legacy_cache_has_unknown_capture_and_starts_forward_history(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    row = {column: None for column in LEGACY_COLUMNS}
    row.update(
        package_ndc="TEST-L", generic_name="Synthetic L", status="Current",
        availability="Available", initial_posting_date="2026-01-07",
        company_name="Synthetic Pharma Works",
        fetched_utc="2026-02-01T00:00:00+00:00",
    )
    pd.DataFrame([row], columns=LEGACY_COLUMNS).to_parquet(path)

    before = read_shortage_observation(path=path)
    assert before["legacy"] is True
    assert before["capture"] is None
    assert before["history_coverage"]["legacy_rows_capture_unknown"] is True

    fresh = _sweep("2026-09-23", [_record()])
    save_shortage_observation(fresh, path=path, expected_predecessor=None)
    state = read_shortage_observation(path=path)
    coverage = state["history_coverage"]
    assert coverage["earliest_qualified_generation"] == "2026-09-23"
    assert coverage["legacy_rows_capture_unknown"] is True
    rows = state["rows"].set_index("package_ndc")
    assert not bool(rows.loc["TEST-L", "capture_known"])
    assert rows.loc["TEST-L", "absent_since_generation"] == "2026-09-23"


def test_failed_metadata_write_is_not_advertised_as_current(tmp_path, monkeypatch):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    first = _sweep("2026-09-20", [_record()])
    save_shortage_observation(first, path=path, expected_predecessor=None)
    old_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar = path.with_suffix(".observation.json")
    old_sidecar = sidecar.read_bytes()
    second = _sweep("2026-09-23", [_record(status="Resolved")])

    def fail_json_dump(*args, **kwargs):
        raise OSError("synthetic metadata write failure")

    monkeypatch.setattr("collectors.fda_shortages._json_dumps", fail_json_dump)
    outcome = save_shortage_observation(
        second, path=path, expected_predecessor=_sidecar_digest(path),
    )
    assert outcome["promoted"] is False
    assert outcome["reason"] == "METADATA_WRITE_FAILED"
    state = read_shortage_observation(path=path)
    assert state["inconsistent"] is False
    assert state["rows"] is not None and len(state["rows"]) == 1
    assert state["capture"]["source_generation"] == "2026-09-20"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == old_digest
    assert sidecar.read_bytes() == old_sidecar
    assert json.loads(sidecar.read_text())["parquet_sha256"] == old_digest


def test_interleaved_older_writer_is_refused(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    newer = _sweep(
        "2026-09-23",
        [_record(ndc="TEST-B", name="Synthetic B")],
        finish=datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC),
    )
    assert save_shortage_observation(
        newer, path=path, expected_predecessor=None,
    )["promoted"] is True
    newer_digest = _sidecar_digest(path)

    older = _sweep(
        "2026-09-22",
        [_record()],
        start=datetime(2026, 9, 22, 12, tzinfo=UTC),
        finish=datetime(2026, 9, 22, 12, 0, 6, tzinfo=UTC),
    )
    refused = save_shortage_observation(
        older, path=path, expected_predecessor=None,
    )
    assert refused["reason"] == "PREDECESSOR_MISMATCH"
    assert refused["promoted"] is False
    assert _sidecar_digest(path) == newer_digest
    rows = read_shortage_observation(path=path)["rows"]
    assert rows["package_ndc"].tolist() == ["TEST-B"]


def test_older_qualified_generation_is_refused_after_predecessor_check(tmp_path):
    from collectors.fda_shortages import save_shortage_observation

    path = tmp_path / "shortages.parquet"
    newer = _sweep(
        "2026-09-23", [_record()],
        start=datetime(2026, 9, 23, 12, tzinfo=UTC),
    )
    save_shortage_observation(newer, path=path, expected_predecessor=None)
    older = _sweep(
        "2026-09-22", [_record()],
        start=datetime(2026, 9, 22, 12, tzinfo=UTC),
    )
    outcome = save_shortage_observation(
        older, path=path, expected_predecessor=_sidecar_digest(path),
    )
    assert outcome["reason"] == "GENERATION_REGRESSION"
    assert outcome["promoted"] is False


def test_wrapper_returns_previous_qualified_frame_after_failed_refresh(
        tmp_path, monkeypatch):
    from collectors import fda_shortages

    path = tmp_path / "shortages.parquet"
    baseline = _sweep("2026-09-20", [_record()])
    fda_shortages.save_shortage_observation(
        baseline, path=path, expected_predecessor=None,
    )
    monkeypatch.setattr(fda_shortages, "_shortages_path", lambda: path)

    def outage(skip, limit=100):
        raise OSError("synthetic refresh outage")

    monkeypatch.setattr(fda_shortages, "_fetch_page", outage)
    frame = fda_shortages.fetch_shortages()
    assert frame is not None
    assert frame["package_ndc"].tolist() == ["TEST-A"]
    assert frame.attrs["fda_observation"]["failed_refresh"] is True
    assert frame.attrs["fda_observation"]["capture"]["source_generation"] == "2026-09-20"
    state = fda_shortages.read_shortage_observation(path=path)
    assert state["capture"]["source_generation"] == "2026-09-20"


def test_failed_refresh_preserves_the_digest_of_a_torn_parquet(
        tmp_path, monkeypatch):
    from collectors import fda_shortages

    path = tmp_path / "shortages.parquet"
    fda_shortages.save_shortage_observation(
        _sweep("2026-09-20", [_record()]), path=path, expected_predecessor=None,
    )
    sidecar = path.with_suffix(".observation.json")
    before = json.loads(sidecar.read_text())
    path.write_bytes(path.read_bytes()[:-16])
    assert fda_shortages.read_shortage_observation(path=path)["inconsistent"] is True

    def outage(skip, limit=100):
        raise OSError("synthetic refresh outage")

    monkeypatch.setattr(fda_shortages, "_shortages_path", lambda: path)
    monkeypatch.setattr(fda_shortages, "_fetch_page", outage)
    fda_shortages.fetch_shortages()
    after = json.loads(sidecar.read_text())
    assert after["parquet_sha256"] == before["parquet_sha256"]
    state = fda_shortages.read_shortage_observation(path=path)
    assert state["inconsistent"] is True
    assert state["rows"] is None
    assert state["capture"] is None


def test_cache_reader_carries_observation_state(tmp_path, monkeypatch):
    from collectors import fda_shortages

    path = tmp_path / "shortages.parquet"
    fda_shortages.save_shortage_observation(
        _sweep("2026-09-23", [_record()]), path=path,
        expected_predecessor=None,
    )
    monkeypatch.setattr(fda_shortages, "_shortages_path", lambda: path)
    frame = fda_shortages.load_shortages_cache()
    observation = frame.attrs["fda_observation"]
    assert observation["capture"]["source_generation"] == "2026-09-23"
    assert observation["legacy"] is False
    assert observation["inconsistent"] is False
    assert observation["failed_refresh"] is False


def test_observation_receipt_line_is_truthful_and_neutral(tmp_path):
    from collectors import fda_shortages

    path = tmp_path / "shortages.parquet"
    fda_shortages.save_shortage_observation(
        _sweep("2026-09-23", [_record()]), path=path, expected_predecessor=None,
    )
    qualified = fda_shortages.read_shortage_observation(path=path)
    assert fda_shortages.format_observation_receipt(qualified) == (
        "fda_shortages: observation qualified=True failure_code=none "
        "source_generation=2026-09-23 last_refresh=2026-09-23T12:00:06+00:00 "
        "legacy=False inconsistent=False"
    )

    failed = fda_shortages.read_shortage_observation(path=tmp_path / "missing.parquet")
    assert fda_shortages.format_observation_receipt(failed) == (
        "fda_shortages: observation qualified=False failure_code=none "
        "source_generation=unknown last_refresh=none legacy=False inconsistent=False"
    )

    failed = fda_shortages.read_shortage_observation(path=path)
    failed["last_refresh"] = {
        "attempted_at": "2026-09-24T12:00:03+00:00", "qualified": False,
        "failure_code": "FIRST_PAGE_OUTAGE",
    }
    assert fda_shortages.format_observation_receipt(failed) == (
        "fda_shortages: observation qualified=False failure_code=FIRST_PAGE_OUTAGE "
        "source_generation=2026-09-23 last_refresh=2026-09-24T12:00:03+00:00 "
        "legacy=False inconsistent=False"
    )

    legacy = {"legacy": True}
    assert fda_shortages.format_observation_receipt(legacy) == (
        "fda_shortages: observation qualified=False failure_code=none "
        "source_generation=unknown last_refresh=none legacy=True inconsistent=False"
    )
    for banned in ("glut", "tell", "all-clear", "catching up"):
        assert banned not in fda_shortages.format_observation_receipt(qualified)


def test_every_qualified_capture_disclaims_snapshot_proof():
    single = _sweep("2026-09-23", [_record()])
    multiple = _sweep(
        "2026-09-23", [_record(), _record(ndc="TEST-B", name="Synthetic B")],
        page_size=1,
    )
    empty = _sweep("2026-09-23", [])
    for result in (single, multiple, empty):
        assert result["qualified"] is True
        assert type(result["capture"]["atomic_snapshot_proven"]) is bool
        assert result["capture"]["atomic_snapshot_proven"] is False


def test_generationless_sweep_is_unqualified_at_the_public_seam(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    result = _sweep(None, [_record()])

    assert result["qualified"] is False
    assert result["failure_code"] == "NO_SOURCE_GENERATION"
    assert result["capture"]["source_generation"] is None

    outcome = save_shortage_observation(
        result, path=path, expected_predecessor=None,
    )

    assert outcome["promoted"] is False
    assert outcome["reason"] == "NO_SOURCE_GENERATION"
    assert not path.exists()
    state = read_shortage_observation(path=path)
    assert state["capture"] is None
    assert state["rows"] is None
    assert state["history_coverage"] == {}


def test_save_path_still_demotes_a_legacy_generationless_capture(tmp_path):
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    legacy_rows = [_record(), _record(ndc="TEST-B", name="Synthetic B")]
    result = _sweep(None, legacy_rows)
    result = {**result, "qualified": True, "rows": legacy_rows}

    outcome = save_shortage_observation(
        result, path=path, expected_predecessor=None,
    )

    assert result["qualified"] is True
    assert outcome["promoted"] is False
    assert outcome["reason"] == "NO_SOURCE_GENERATION"
    sidecar_path = path.with_suffix(".observation.json")
    assert outcome["predecessor"] == hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["selected_capture"] is None
    assert sidecar["history_coverage"]["legacy_rows_capture_unknown"] is True
    state = read_shortage_observation(path=path)
    assert state["capture"] is None
    assert state["inconsistent"] is False
    assert state["rows"]["package_ndc"].tolist() == ["TEST-A", "TEST-B"]
    assert state["rows"]["absent_since_generation"].isna().all()
    assert state["rows"]["capture_known"].eq(False).all()
    assert sidecar["last_refresh"] == {
        "attempted_at": "2026-09-23T12:00:06+00:00",
        "qualified": False,
        "failure_code": "NO_SOURCE_GENERATION",
        "partial_rows_observed": 0,
    }
