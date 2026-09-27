"""T02 round-2 adversarial probes — Healthcare D1, PR #7930 @8d858bba.

Every probe is self-contained, tmp_path-based, network-free, uses no real
molecule names, drives the sweep through its supplied-clock seam, and asserts
only through the public seams collect_shortage_sweep / save_shortage_observation
/ read_shortage_observation / format_observation_receipt / load_shortages_cache.

All six FAIL at 8d858bba and pass once the collector honours the D1 law.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

UTC = timezone.utc


def _t02r2_clock(*ticks):
    """Deterministic supplied clock: returns each tick, then repeats the last."""
    calls = {"n": 0}

    def tick():
        index = min(calls["n"], len(ticks) - 1)
        calls["n"] += 1
        return ticks[index]

    return tick


def _t02r2_record(ndc="T02R2-A", name="Synthetic Alpha", status="Current",
                  availability="Available", posted="2026-03-02"):
    return {
        "package_ndc": ndc,
        "generic_name": name,
        "status": status,
        "availability": availability,
        "initial_posting_date": posted,
        "company_name": "Synthetic Works",
    }


def _t02r2_page(generation, records, total=None):
    meta = {"results": {"total": len(records) if total is None else total}}
    if generation is not None:
        meta["last_updated"] = generation
    return {"meta": meta, "results": list(records)}


def _t02r2_sweep(generation, records, *, start, finish, total=None, max_pages=4):
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        return _t02r2_page(generation, records[skip:skip + limit], total=total)

    return collect_shortage_sweep(
        fetch_page, clock=_t02r2_clock(start, finish),
        page_size=100, max_pages=max_pages,
    )


def _t02r2_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def test_t02r2_drip_receipt_names_the_failure_code_of_a_failed_refresh(tmp_path):
    """B1 (GLM-B1). Law: complete-empty != failed != stale != unrecognized.

    format_observation_receipt reads capture['failure_code'], but the capture
    dict built by collect_shortage_sweep has no such key — the code lives at the
    result top level and is persisted under last_refresh.failure_code. The drip
    line in scripts/build_foresight.py therefore prints failure_code=none for a
    FIRST_PAGE_OUTAGE, i.e. a total upstream outage reads identically to a clean
    refresh.
    """
    from collectors.fda_shortages import (
        collect_shortage_sweep, format_observation_receipt,
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    good = _t02r2_sweep(
        "2026-09-23", [_t02r2_record()],
        start=datetime(2026, 9, 23, 12, tzinfo=UTC),
        finish=datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC),
    )
    assert save_shortage_observation(
        good, path=path, expected_predecessor=None)["promoted"] is True

    def outage(skip, limit):
        raise OSError("synthetic outage")

    failed = collect_shortage_sweep(
        outage,
        clock=_t02r2_clock(datetime(2026, 9, 24, 12, tzinfo=UTC),
                           datetime(2026, 9, 24, 12, 0, 3, tzinfo=UTC)),
        page_size=100, max_pages=3,
    )
    assert failed["failure_code"] == "FIRST_PAGE_OUTAGE"
    sidecar = path.with_suffix(".observation.json")
    save_shortage_observation(
        failed, path=path, expected_predecessor=_t02r2_digest(sidecar))

    state = read_shortage_observation(path=path)
    assert state["last_refresh"]["failure_code"] == "FIRST_PAGE_OUTAGE"
    line = format_observation_receipt(state)
    assert "failure_code=FIRST_PAGE_OUTAGE" in line, line
    assert "failure_code=none" not in line, line


def test_t02r2_failed_sidecar_write_keeps_the_last_qualified_observation(tmp_path):
    """B2 (GLM-M1, upgraded). Law: the last qualified observation survives a
    failed refresh; retention keeps absent rows 90 generations.

    _write_staged(path, write_parquet) promotes the NEW parquet before the
    sidecar is serialised and staged. When the sidecar write fails, the caller
    gets METADATA_WRITE_FAILED but the old digest now fences a new parquet:
    read_shortage_observation reports inconsistent and hands back rows=None, so
    the previously selected observation AND all of its absence history are gone
    until some later sweep qualifies.
    """
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    first = _t02r2_sweep(
        "2026-09-23", [_t02r2_record()],
        start=datetime(2026, 9, 23, 12, tzinfo=UTC),
        finish=datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC),
    )
    assert save_shortage_observation(
        first, path=path, expected_predecessor=None)["promoted"] is True
    sidecar = path.with_suffix(".observation.json")
    before = read_shortage_observation(path=path)
    assert before["rows"] is not None and len(before["rows"]) == 1

    # Make the sidecar's staged target unwritable without touching the parquet's.
    (sidecar.parent / f".{sidecar.name}.{os.getpid()}.tmp").mkdir()

    second = _t02r2_sweep(
        "2026-09-24", [_t02r2_record(), _t02r2_record(ndc="T02R2-B", name="Synthetic Beta")],
        start=datetime(2026, 9, 24, 12, tzinfo=UTC),
        finish=datetime(2026, 9, 24, 12, 0, 6, tzinfo=UTC),
    )
    outcome = save_shortage_observation(
        second, path=path, expected_predecessor=_t02r2_digest(sidecar))
    assert outcome["promoted"] is False
    assert outcome["reason"] == "METADATA_WRITE_FAILED"

    after = read_shortage_observation(path=path)
    assert after["rows"] is not None, (
        "an unpromoted metadata write destroyed the selected observation: "
        f"inconsistent={after['inconsistent']}"
    )
    assert len(after["rows"]) == 1
    assert after["capture"] is not None
    assert after["capture"]["source_generation"] == "2026-09-23"


def test_t02r2_non_dict_openfda_is_malformed_not_an_exception(tmp_path):
    """M1 (GLM-m1, re-scoped). Law: the sweep never raises; a bad upstream value
    yields a failure code.

    _parse_record type-checks exactly six text fields, then calls
    `openfda.get(...)` on whatever `rec['openfda']` holds. A truthy non-dict
    raises AttributeError, which the sweep's `except (TypeError, ValueError)`
    does not catch, so collect_shortage_sweep raises instead of reporting
    MALFORMED_ROW — and the caller writes no last_refresh receipt at all.
    """
    from collectors.fda_shortages import collect_shortage_sweep

    for bad in (["SYN-1"], "SYN-1", 7):
        record = dict(_t02r2_record(), openfda=bad)

        def fetch_page(skip, limit, _rec=record):
            return {"meta": {"last_updated": "2026-09-23", "results": {"total": 1}},
                    "results": [_rec]}

        result = collect_shortage_sweep(
            fetch_page,
            clock=_t02r2_clock(datetime(2026, 9, 23, 12, tzinfo=UTC),
                               datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC)),
            page_size=100, max_pages=2,
        )
        assert result["failure_code"] == "MALFORMED_ROW", bad
        assert result["qualified"] is False, bad
        assert result["rows"] == [], bad


def test_t02r2_unreadable_legacy_parquet_reads_as_state_not_an_exception(tmp_path):
    """M2. Law: a torn pair never raises; nothing raises into the build.

    _selected_state guards pd.read_parquet with try/except only on the
    sidecar-fenced branch. The legacy branch (parquet present, sidecar absent —
    exactly the pre-T02 cache this PR must absorb, and exactly what a sparse
    worktree truncates) reads the parquet bare, so a corrupt file raises out of
    read_shortage_observation and load_shortages_cache.
    """
    from collectors.fda_shortages import read_shortage_observation

    path = tmp_path / "shortages.parquet"
    path.write_bytes(b"PAR1-not-a-parquet-file")
    assert not path.with_suffix(".observation.json").exists()

    state = read_shortage_observation(path=path)
    assert state["rows"] is None or len(state["rows"]) == 0
    assert state["inconsistent"] is True


def test_t02r2_failed_refresh_over_a_corrupt_sidecar_does_not_raise(tmp_path):
    """M3. Law: a failed refresh writes only last_refresh and never raises.

    The unqualified branch of save_shortage_observation calls
    json.loads(sidecar.read_text()) with no guard, so a corrupt sidecar turns a
    routine upstream outage into a JSONDecodeError out of the collector.
    _selected_state already handles this shape; the writer does not.
    """
    from collectors.fda_shortages import (
        collect_shortage_sweep, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    sidecar = path.with_suffix(".observation.json")
    sidecar.write_text("{not json at all", encoding="utf-8")

    def outage(skip, limit):
        raise OSError("synthetic outage")

    failed = collect_shortage_sweep(
        outage,
        clock=_t02r2_clock(datetime(2026, 9, 24, 12, tzinfo=UTC),
                           datetime(2026, 9, 24, 12, 0, 3, tzinfo=UTC)),
        page_size=100, max_pages=3,
    )
    outcome = save_shortage_observation(
        failed, path=path, expected_predecessor=_t02r2_digest(sidecar))
    assert outcome["promoted"] is False
    assert outcome["reason"] in ("FIRST_PAGE_OUTAGE", "METADATA_WRITE_FAILED")
    assert json.loads(sidecar.read_text())["last_refresh"]["failure_code"] \
        == "FIRST_PAGE_OUTAGE"


def test_t02r2_capture_without_a_source_generation_cannot_hide_an_absence(tmp_path):
    """M4. Law: absence != resolution; source generation != acquisition time;
    retention keys on distinct generations.

    SEAT AMENDMENT (2026-09-24, ruling R-T02R4-02): the original precondition
    asserted the DEFECT state (a page without meta.last_updated "still
    qualifies"). Under R-T02R3-06/R-T02R4-02 such a sweep is UNQUALIFIED with
    NO_SOURCE_GENERATION at the public seam, so it can never promote and never
    stamps a disappeared row. The intent of the probe is unchanged: a
    generation-less page cannot hide an absence.
    """
    from collectors.fda_shortages import (
        read_shortage_observation, save_shortage_observation,
    )

    path = tmp_path / "shortages.parquet"
    both = [_t02r2_record(),
            _t02r2_record(ndc="T02R2-B", name="Synthetic Beta")]
    first = _t02r2_sweep(
        "2026-09-23", both,
        start=datetime(2026, 9, 23, 12, tzinfo=UTC),
        finish=datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC),
    )
    assert first["qualified"] is True
    save_shortage_observation(first, path=path, expected_predecessor=None)
    sidecar = path.with_suffix(".observation.json")

    second = _t02r2_sweep(
        None, [_t02r2_record()],
        start=datetime(2026, 9, 24, 12, tzinfo=UTC),
        finish=datetime(2026, 9, 24, 12, 0, 6, tzinfo=UTC),
    )
    assert second["qualified"] is False, second
    assert second["failure_code"] == "NO_SOURCE_GENERATION", second["failure_code"]
    outcome = save_shortage_observation(
        second, path=path, expected_predecessor=_t02r2_digest(sidecar))
    assert outcome["promoted"] is False, outcome

    state = read_shortage_observation(path=path)
    rows = state["rows"]
    assert rows is not None
    marks = {row["package_ndc"]: row["absent_since_generation"]
             for _, row in rows.iterrows()}
    assert "T02R2-B" in marks
    assert marks["T02R2-B"] is None, (
        "an unqualified, generation-less sweep stamped the disappeared row as "
        f"absent: {marks}"
    )
    assert json.loads(sidecar.read_text())["last_refresh"]["failure_code"] \
        == "NO_SOURCE_GENERATION"
