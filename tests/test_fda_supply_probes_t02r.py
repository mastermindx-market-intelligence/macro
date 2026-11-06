"""Frozen acceptance probes for Healthcare D1 T02 — red-team round R1 (2026-09-24).

Authored by the independent Opus red-team reviewer child of seat 1172846f against
carrier head ab640a6a606b (PR #7930); extracted verbatim by the seat and committed
RED. Covers review findings T02-B1..B5, T02-M1, T02-M2, T02-N1 (retention cap,
live-row deletion, torn-parquet read, selected-capture nulling on inconsistent
pair, malformed key values, clock purity, cold-start inconsistency, retention
counter). Synthetic data only; writes confined to tmp_path. Build lanes MUST NOT
edit this file — they make it green by repairing collectors/fda_shortages.py.
"""
from __future__ import annotations


def _t02r_clock(start, finish):
    calls = {"n": 0}
    def tick():
        calls["n"] += 1
        return start if calls["n"] == 1 else finish
    return tick


def _t02r_sweep(generation, records, start=None):
    from datetime import datetime, timezone
    from collectors.fda_shortages import collect_shortage_sweep
    start = start or datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    finish = start.replace(second=6)
    def fetch_page(skip, limit):
        return {"meta": {"last_updated": generation,
                         "results": {"total": len(records)}},
                "results": list(records[skip:skip + limit])}
    return collect_shortage_sweep(fetch_page, clock=_t02r_clock(start, finish),
                                  page_size=100, max_pages=5)


def _t02r_record(ndc="A", status="Current", posted="2026-03-02"):
    return {"package_ndc": ndc, "generic_name": "Synthetic", "status": status,
            "availability": "Available", "initial_posting_date": posted}


def _t02r_digest(path):
    import hashlib
    sidecar = path.with_suffix(".observation.json")
    return hashlib.sha256(sidecar.read_bytes()).hexdigest() if sidecar.exists() else None


def test_t02r_absent_row_keeps_its_original_absence_generation(tmp_path):
    """T02-B1: absent_since_generation is the generation the row WENT absent."""
    from datetime import datetime, timezone
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    predecessor = None
    for index in range(5):
        generation = f"2026-G{index:03d}"
        start = datetime(2026, 1, 1 + index, 12, tzinfo=timezone.utc)
        records = [_t02r_record("A"), _t02r_record("B")] if index == 0 else [_t02r_record("B")]
        outcome = save_shortage_observation(
            _t02r_sweep(generation, records, start=start),
            path=path, expected_predecessor=predecessor,
        )
        assert outcome["promoted"] is True, outcome
        predecessor = outcome["predecessor"]
    rows = read_shortage_observation(path=path)["rows"].set_index("package_ndc")
    assert rows.loc["A", "absent_since_generation"] == "2026-G001"
    assert rows.loc["A", "last_observed_generation"] == "2026-G000"
    assert rows.loc["A", "status"] == "Current"


def test_t02r_retention_drops_absent_rows_only_after_ninety_generations(tmp_path):
    """T02-B1/B2: the cap fires, counts, and never deletes a present row."""
    import json
    from datetime import datetime, timezone
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    predecessor = None
    for index in range(95):
        generation = f"2026-G{index:03d}"
        start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc).replace(
            minute=index % 60) + __import__("datetime").timedelta(days=index)
        records = [_t02r_record("A"), _t02r_record("B")] if index == 0 else [_t02r_record("B")]
        outcome = save_shortage_observation(
            _t02r_sweep(generation, records, start=start),
            path=path, expected_predecessor=predecessor,
        )
        assert outcome["promoted"] is True, (index, outcome)
        predecessor = outcome["predecessor"]
    state = read_shortage_observation(path=path)
    present = state["rows"]["package_ndc"].tolist()
    receipt = json.loads(path.with_suffix(".observation.json").read_text())
    assert "B" in present, "the continuously observed row must never be dropped"
    assert "A" not in present, "absent for 94 generations, past the 90-generation cap"
    assert receipt["retention"]["absent_generations_kept"] == 90
    assert receipt["retention"]["dropped_absent_rows"] >= 1


def test_t02r_torn_parquet_reads_as_inconsistent_not_an_exception(tmp_path):
    """T02-B3: a half-written parquet must return the inconsistent dict."""
    from collectors.fda_shortages import (
        load_shortages_cache, read_shortage_observation, save_shortage_observation,
    )
    import collectors.fda_shortages as module
    path = tmp_path / "shortages.parquet"
    save_shortage_observation(
        _t02r_sweep("2026-09-23", [_t02r_record()]),
        path=path, expected_predecessor=None,
    )
    path.write_bytes(path.read_bytes()[:-40])
    state = read_shortage_observation(path=path)
    assert state["inconsistent"] is True
    assert state["rows"] is None
    assert state["capture"] is None
    assert state["last_refresh"] is not None
    original = module._shortages_path
    module._shortages_path = lambda: path
    try:
        assert load_shortages_cache() is None
    finally:
        module._shortages_path = original


def test_t02r_failed_refresh_never_erases_the_selected_capture(tmp_path):
    """T02-B4: an unqualified sweep on an inconsistent pair keeps the record."""
    import json
    from datetime import datetime, timezone
    import pandas as pd
    from collectors.fda_shortages import (
        collect_shortage_sweep, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    save_shortage_observation(
        _t02r_sweep("2026-09-23", [_t02r_record()]),
        path=path, expected_predecessor=None,
    )
    sidecar = path.with_suffix(".observation.json")
    before = json.loads(sidecar.read_text())["selected_capture"]
    pd.read_parquet(path).assign(generic_name="TAMPERED").to_parquet(path, engine="pyarrow")
    def outage(skip, limit):
        raise OSError("synthetic outage")
    failed = collect_shortage_sweep(
        outage,
        clock=_t02r_clock(datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                          datetime(2026, 9, 25, 12, 0, 5, tzinfo=timezone.utc)),
        page_size=100, max_pages=3,
    )
    save_shortage_observation(failed, path=path, expected_predecessor=_t02r_digest(path))
    receipt = json.loads(sidecar.read_text())
    assert receipt["selected_capture"] == before
    assert receipt["last_refresh"]["qualified"] is False
    assert receipt["last_refresh"]["attempted_at"] == "2026-09-25T12:00:05+00:00"


def test_t02r_malformed_field_values_are_rejected_not_raised(tmp_path):
    """T02-B5: bad value TYPES yield MALFORMED_ROW; the sweep never raises."""
    from datetime import datetime, timezone
    from collectors.fda_shortages import collect_shortage_sweep
    for bad in (
        {"package_ndc": ["A", "B"], "initial_posting_date": "2026-03-02", "status": "Current"},
        {"package_ndc": "A", "initial_posting_date": {"x": 1}, "status": "Current"},
        {"package_ndc": 12345, "initial_posting_date": "2026-03-02", "status": "Current"},
    ):
        def fetch_page(skip, limit, _bad=bad):
            return {"meta": {"last_updated": "2026-09-23", "results": {"total": 1}},
                    "results": [_bad]}
        result = collect_shortage_sweep(
            fetch_page,
            clock=_t02r_clock(datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
                              datetime(2026, 9, 23, 12, 0, 6, tzinfo=timezone.utc)),
            page_size=100, max_pages=2,
        )
        assert result["failure_code"] == "MALFORMED_ROW", bad
        assert result["qualified"] is False
        assert result["rows"] == []


def test_t02r_sweep_is_deterministic_under_a_supplied_clock():
    """T02-M1: no wall clock inside the pure function."""
    import inspect
    from datetime import datetime, timezone
    import collectors.fda_shortages as module
    source = inspect.getsource(module._parse_record)
    assert "datetime.now" not in source, (
        "_parse_record stamps fetched_utc from the wall clock inside collect_shortage_sweep"
    )
    start = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    first = _t02r_sweep("2026-09-23", [_t02r_record()], start=start)
    second = _t02r_sweep("2026-09-23", [_t02r_record()], start=start)
    assert first["rows"] == second["rows"]
    assert first["capture"] == second["capture"]


def test_t02r_cold_start_failure_is_not_an_integrity_alarm(tmp_path):
    """T02-M2: never-observed is not the same state as a torn pair."""
    from datetime import datetime, timezone
    from collectors.fda_shortages import (
        collect_shortage_sweep, read_shortage_observation, save_shortage_observation,
    )
    path = tmp_path / "shortages.parquet"
    def outage(skip, limit):
        raise OSError("synthetic outage")
    failed = collect_shortage_sweep(
        outage,
        clock=_t02r_clock(datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                          datetime(2026, 9, 25, 12, 0, 5, tzinfo=timezone.utc)),
        page_size=100, max_pages=3,
    )
    save_shortage_observation(failed, path=path, expected_predecessor=None)
    state = read_shortage_observation(path=path)
    assert state["inconsistent"] is False
    assert state["capture"] is None
    assert state["last_refresh"]["failure_code"] == "FIRST_PAGE_OUTAGE"


def test_t02r_dropped_absent_rows_survives_a_failed_refresh(tmp_path):
    """T02-N1: the retention counter is read from the sidecar's own block."""
    import hashlib, json
    from datetime import datetime, timezone
    import pandas as pd
    from collectors.fda_shortages import collect_shortage_sweep, save_shortage_observation
    path = tmp_path / "shortages.parquet"
    pd.DataFrame([{
        "package_ndc": "A", "initial_posting_date": "2026-03-02", "status": "Current",
        "first_observed_generation": "g", "last_observed_generation": "g",
        "absent_since_generation": None, "previous_status": None,
        "status_changed_generation": None, "capture_known": True,
    }]).to_parquet(path, engine="pyarrow")
    capture = {"started_at": "2026-01-01T00:00:00+00:00",
               "finished_at": "2026-01-01T00:00:06+00:00", "source_generation": "g",
               "pages": 1, "page_size": 100, "max_pages": 5, "raw_count": 1,
               "unique_count": 1, "reported_total": 1, "complete": True,
               "atomic_snapshot_proven": False, "acquisition_interval_s": 6.0}
    receipt = {
        "schema": "fda_shortages_observation.v1", "selected_capture": capture,
        "last_refresh": {"attempted_at": capture["finished_at"], "qualified": True,
                         "failure_code": None, "partial_rows_observed": 0},
        "history_coverage": {"earliest_qualified_generation": "g",
                             "legacy_rows_capture_unknown": False,
                             "forward_retention_started_at": capture["finished_at"]},
        "retention": {"absent_generations_kept": 90, "dropped_absent_rows": 7},
        "predecessor": None,
        "parquet_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    sidecar = path.with_suffix(".observation.json")
    sidecar.write_text(json.dumps(receipt, sort_keys=True, indent=2))
    def outage(skip, limit):
        raise OSError("synthetic outage")
    failed = collect_shortage_sweep(
        outage,
        clock=_t02r_clock(datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                          datetime(2026, 9, 25, 12, 0, 5, tzinfo=timezone.utc)),
        page_size=100, max_pages=3,
    )
    save_shortage_observation(failed, path=path, expected_predecessor=_t02r_digest(path))
    assert json.loads(sidecar.read_text())["retention"]["dropped_absent_rows"] == 7
