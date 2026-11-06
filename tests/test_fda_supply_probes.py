"""Frozen acceptance probes for Healthcare D1 (FDA supply observation).

Cases pinned here: R8-A18, R8-A19, R8-A20, R8-A21, R8-A22, R8-A23, R8-A24,
R8-A25, R8-A26, R8-A27, R9-A02, R9-A07, R10-A07, R10-A11.

Authored by the independent Opus reviewer child of seat 1172846f on 2026-09-24.
Synthetic data only (no network, no real product identifiers, writes confined to
tmp_path). These probes are the acceptance gate for D1: the build lanes MUST NOT
edit this file — they make it green by repairing engine/fda_scarcity.py,
collectors/fda_shortages.py and engine/foresight_cascade.py.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

UTC = timezone.utc

LEGACY_COLUMNS = [
    "package_ndc", "generic_name", "brand_name", "substance_name", "status",
    "availability", "initial_posting_date", "update_date", "discontinued_date",
    "therapeutic_category", "company_name", "related_info", "fetched_utc",
]
BANNED_ECONOMIC_WORDS = ("glut", "tell", "all-clear", "catching up")


@pytest.fixture(autouse=True)
def _isolate_real_data_tree(tmp_path, monkeypatch):
    """Mirror tests/test_foresight_cascade.py:15-27 — the cascade lazily recomputes
    any tier not passed in straight off the real data/ tree and can append to the
    real forward ledger. Redirect lib.config so every lazy recompute degrades."""
    from lib import config as _config
    _config.load()
    monkeypatch.setattr(_config, "ROOT", tmp_path)
    monkeypatch.setattr(_config, "data_dir", lambda: tmp_path / "data")


def _rec(ndc, name, status, availability, posted):
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


def _clock(first, later=None):
    """First call returns `first`; every later call returns `later` (or `first`)."""
    state = {"n": 0}

    def _tick():
        state["n"] += 1
        return first if state["n"] == 1 else (later or first)

    return _tick


def _digest(path):
    sidecar = path.with_suffix(".observation.json")
    if not sidecar.exists():
        return None
    return hashlib.sha256(sidecar.read_bytes()).hexdigest()


def _one_page_sweep(generation, records, clock_start, clock_end):
    from collectors.fda_shortages import collect_shortage_sweep

    def fetch_page(skip, limit):
        return _page(generation, [] if skip else records, len(records))

    return collect_shortage_sweep(
        fetch_page, clock=_clock(clock_start, clock_end), page_size=100, max_pages=5
    )


# ── T01 — engine.fda_scarcity ────────────────────────────────────────────────

def test_r8_a18_current_available_stays_current():
    """R8-A18: Retain Current and Available as different observations."""
    from engine.fda_scarcity import compute_fda_scarcity

    df = pd.DataFrame([{
        "generic_name": "semaglutide injection", "package_ndc": "TEST-A",
        "status": "Current", "availability": "Available",
        "initial_posting_date": "2026-03-02",
    }])
    legacy = compute_fda_scarcity(df)["glp1_obesity"]
    assert legacy["band"] == "SHORTAGE_ACTIVE", \
        "R8-A18: a Current row presented as Available is still a reported current shortage"
    assert legacy["source_status"] == "CURRENT_REPORTED", \
        "R8-A18: the legacy chip entry point must carry the scoped source status"

    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    capture = {"qualified": True, "finished_at": now.isoformat(),
               "source_generation": "2026-09-23", "atomic_snapshot_proven": False}
    rows = [{"generic_name": "Synthetic A", "status": "Current",
             "availability": "Available", "package_ndc": "TEST-A"}]
    out = summarize_supply(rows, capture=capture, now=now,
                           max_capture_age=timedelta(days=2))
    assert out["source_status"] == "CURRENT_REPORTED", "R8-A18: Current must stay CURRENT_REPORTED"
    assert out["rows"][0]["regulator_status"] == "current", \
        "R8-A18: regulator status is the national determination"
    assert out["rows"][0]["manufacturer_availability"] == "Available", \
        "R8-A18: availability is a separate observation, preserved verbatim"
    assert out["counts"]["current"] == 1, "R8-A18: one current row observed"
    assert "glut" not in out["label"].casefold(), "R8-A18: no economic conclusion in the label"


def test_r8_a19_mixed_evidence_is_not_a_theme_all_clear():
    """R8-A19: Preserve mixed evidence; never emit a theme-wide resolution/all-clear."""
    from engine.fda_scarcity import compute_fda_scarcity

    df = pd.DataFrame([
        {"generic_name": "semaglutide injection", "package_ndc": "TEST-A",
         "status": "Current", "availability": "Available", "initial_posting_date": "2026-03-02"},
        {"generic_name": "tirzepatide injection", "package_ndc": "TEST-B",
         "status": "Resolved", "availability": "Available", "initial_posting_date": "2026-01-05"},
    ])
    legacy = compute_fda_scarcity(df)["glp1_obesity"]
    assert legacy["band"] != "SHORTAGE_RESOLVED", \
        "R8-A19: a mixture must never collapse into a theme-wide resolved band"
    assert legacy["band"] == "SHORTAGE_ACTIVE", "R8-A19: mixed evidence keeps the active legacy band"
    assert legacy["source_status"] == "MIXED_REPORTED", "R8-A19: mixture is reported as MIXED_REPORTED"
    for word in BANNED_ECONOMIC_WORDS:
        assert word not in str(legacy.get("rationale", "")).casefold(), \
            f"R8-A19: rationale must not carry the economic word {word!r}"

    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [{"generic_name": "Synthetic A", "status": "Current", "availability": "Available",
          "package_ndc": "TEST-A"},
         {"generic_name": "Synthetic B", "status": "Resolved", "availability": "Available",
          "package_ndc": "TEST-B"}],
        capture={"qualified": True, "finished_at": now.isoformat(),
                 "source_generation": "2026-09-23", "atomic_snapshot_proven": False},
        now=now, max_capture_age=timedelta(days=2))
    assert out["source_status"] == "MIXED_REPORTED", "R8-A19: both states survive as a mixture"
    assert out["counts"]["current"] == 1 and out["counts"]["resolved"] == 1, \
        "R8-A19: both observations are counted separately"
    assert "all-clear" not in out["label"].casefold(), "R8-A19: no all-clear language"


def test_r8_a20_discontinuation_is_not_resolved_supply():
    """R8-A20: Use distinct machine semantics; never treat discontinuation as resolved supply."""
    from engine.fda_scarcity import compute_fda_scarcity

    df = pd.DataFrame([{
        "generic_name": "semaglutide oral", "package_ndc": "TEST-A",
        "status": "To Be Discontinued", "availability": "Available",
        "initial_posting_date": "2026-02-11",
    }])
    legacy = compute_fda_scarcity(df)["glp1_obesity"]
    assert legacy["band"] != "SHORTAGE_RESOLVED", \
        "R8-A20: a discontinuation must not reuse the resolved machine band"
    assert legacy["band"] == "NONE", "R8-A20: discontinuation maps to no legacy shortage band"
    assert legacy["source_status"] == "DISCONTINUATION_REPORTED", \
        "R8-A20: discontinuation is its own source status"

    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [{"generic_name": "Synthetic A", "status": "To Be Discontinued",
          "availability": "Available", "package_ndc": "TEST-A"}],
        capture={"qualified": True, "finished_at": now.isoformat(),
                 "source_generation": "2026-09-23", "atomic_snapshot_proven": False},
        now=now, max_capture_age=timedelta(days=2))
    assert out["source_status"] == "DISCONTINUATION_REPORTED", "R8-A20: distinct machine status"
    assert out["counts"]["discontinued"] == 1 and out["counts"]["resolved"] == 0, \
        "R8-A20: a discontinuation is never counted as a resolution"
    assert out["rows"][0]["regulator_status"] == "to_be_discontinued", \
        "R8-A20: per-row regulator status stays discontinuation"


def test_r8_a21_unknown_status_is_observed_but_unclassified():
    """R8-A21: Show observed-but-unclassified; do not report no matching records."""
    from engine.fda_scarcity import compute_fda_scarcity

    df = pd.DataFrame([{
        "generic_name": "semaglutide injection", "package_ndc": "TEST-A",
        "status": "Under Review", "availability": "",
        "initial_posting_date": "2026-04-18",
    }])
    legacy = compute_fda_scarcity(df)["glp1_obesity"]
    assert "no shortage records" not in str(legacy.get("rationale", "")).casefold(), \
        "R8-A21: an observed unrecognized row must not be described as no records"
    assert legacy["source_status"] == "UNCLASSIFIED", "R8-A21: observed but unclassified"

    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [{"generic_name": "Synthetic A", "status": "Under Review", "availability": "",
          "package_ndc": "TEST-A"}],
        capture={"qualified": True, "finished_at": now.isoformat(),
                 "source_generation": "2026-09-23", "atomic_snapshot_proven": False},
        now=now, max_capture_age=timedelta(days=2))
    assert out["source_status"] == "UNCLASSIFIED", "R8-A21: unclassified, not NO_MATCHING_RECORDS"
    assert out["source_status"] != "NO_MATCHING_RECORDS", "R8-A21: the row was observed"
    assert out["rows"][0]["regulator_status"] == "unrecognized", "R8-A21: row-level unrecognized"
    assert out["counts"]["unrecognized"] == 1 and out["counts"]["matched"] == 1, \
        "R8-A21: the unrecognized row is counted as matched and unrecognized"
    assert out["coverage"]["unclassified_rows"] == 1, "R8-A21: coverage exposes the unclassified row"


def test_r9_a07_fresh_acquisition_does_not_prove_fresh_evidence():
    """R9-A07: Retain both freshness dimensions; fresh acquisition is not fresh evidence."""
    from engine.fda_scarcity import format_theme_feed_chip

    chip = format_theme_feed_chip(
        {"band": "SHORTAGE_ACTIVE", "n_active": 1, "n_resolved": 0, "n_discontinued": 0,
         "molecules_checked": ["semaglutide"], "details": ["Synthetic A [Current/Available]"],
         "rationale": "one current record observed"},
        "glp1_obesity")
    assert chip is not None, "R9-A07: an active row still renders a chip"
    assert "freshness" in chip, "R9-A07: the visible chip must carry the freshness dimensions"

    from engine.fda_scarcity import summarize_supply

    now = datetime(2026, 9, 23, 12, tzinfo=UTC)
    out = summarize_supply(
        [{"generic_name": "Synthetic A", "status": "Current", "availability": "Available",
          "package_ndc": "TEST-A"}],
        capture={"qualified": True, "finished_at": now.isoformat(),
                 "source_generation": "2026-07-25", "atomic_snapshot_proven": False},
        now=now, max_capture_age=timedelta(days=2))
    fresh = out["freshness"]
    assert fresh["capture_qualified"] is True, "R9-A07: the acquisition itself is qualified"
    assert fresh["capture_age_s"] <= 60, "R9-A07: the acquisition is fresh"
    assert fresh["source_generation"] == "2026-07-25", "R9-A07: source generation kept verbatim"
    assert fresh["source_generation_age_days"] >= 60, \
        "R9-A07: the underlying evidence is 60 days old and must say so"
    assert "fresh" not in out["label"].casefold(), \
        "R9-A07: a fresh fetch of old evidence may not be labelled fresh"


def test_r10_a11_chip_is_display_only_stage_unchanged():
    """R10-A11: the D1 chip is display-only — stage/entry unchanged, no economic wording."""
    from engine import foresight_cascade as fc

    bottleneck = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "band": "AWAITING_DATA"}}}
    revisions = {"themes": {"glp1_obesity": {"name": "GLP-1 / Obesity", "breadth": 0.05,
                                             "level_state": "FLAT_LOW"}}}
    freshness = {"capture_qualified": True, "capture_finished_at": "2026-09-23T12:00:00+00:00",
                 "capture_age_s": 0, "source_generation": "2026-09-23",
                 "source_generation_age_days": 0, "stale": False, "failed_refresh": False}
    current = {"glp1_obesity": {
        "source_status": "CURRENT_REPORTED", "freshness": freshness, "band": "SHORTAGE_ACTIVE",
        "n_active": 1, "n_resolved": 0, "n_discontinued": 0,
        "molecules_checked": ["semaglutide"], "details": ["Synthetic A [Current/Available]"],
        "rationale": "one current record observed"}}
    resolved = {"glp1_obesity": {
        "source_status": "RESOLVED_REPORTED", "freshness": freshness, "band": "SHORTAGE_RESOLVED",
        "n_active": 0, "n_resolved": 1, "n_discontinued": 0,
        "molecules_checked": ["semaglutide"], "details": ["Synthetic A [Resolved]"],
        "rationale": "one resolved record observed"}}

    def _run(scarcity):
        out = fc.compute_foresight_cascade(
            bottleneck=bottleneck, revisions=revisions,
            demand={"themes": {}}, glut={"themes": {}},
            fda_scarcity=scarcity, write_ledger=False)
        assert out is not None, "R10-A11: the cascade must still compute"
        return out["themes"][0]

    row_current, row_resolved = _run(current), _run(resolved)
    assert row_current["stage"] == row_resolved["stage"], \
        "R10-A11: the FDA chip is display-only and may never move the stage"
    assert row_current.get("entry") == row_resolved.get("entry"), \
        "R10-A11: entry overlay must be identical under either source status"
    chip_current = row_current["theme_feed_summary"]
    chip_resolved = row_resolved["theme_feed_summary"]
    assert chip_current is not None and chip_resolved is not None, "R10-A11: both chips render"
    assert chip_current["label"] != chip_resolved["label"], "R10-A11: only the chip differs"
    for chip in (chip_current, chip_resolved):
        text = f"{chip.get('label', '')} {chip.get('rationale', '')}".casefold()
        for word in BANNED_ECONOMIC_WORDS:
            assert word not in text, \
                f"R10-A11: chip text must carry no economic conclusion ({word!r})"


# ── T02 — collectors.fda_shortages ───────────────────────────────────────────

def test_r8_a22_partial_acquisition_is_not_promoted(tmp_path):
    """R8-A22: Do not promote partial data as the new qualified observation; expose failed refresh."""
    from collectors.fda_shortages import (collect_shortage_sweep, read_shortage_observation,
                                          save_shortage_observation)

    path = tmp_path / "shortages.parquet"
    good = _one_page_sweep("2026-09-20", [_rec("TEST-A", "Synthetic A", "Current", "Available",
                                               "2026-03-02")],
                           datetime(2026, 9, 20, 12, tzinfo=UTC),
                           datetime(2026, 9, 20, 12, 0, 5, tzinfo=UTC))
    assert good["qualified"] is True, "R8-A22: the baseline sweep is qualified"
    save_shortage_observation(good, path=path, expected_predecessor=None)

    def fetch_page(skip, limit):
        if skip:
            raise OSError("synthetic second page failure")
        return _page("2026-09-23", [_rec("TEST-B", "Synthetic B", "Resolved", "Available",
                                         "2026-05-05")], 2)

    partial = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=1, max_pages=2)
    assert partial["qualified"] is False, "R8-A22: a late page failure is not a current sweep"
    assert partial["failure_code"] == "PAGE_FAILED", "R8-A22: the failure code names the page failure"

    save_shortage_observation(partial, path=path, expected_predecessor=_digest(path))
    state = read_shortage_observation(path=path)
    ndcs = sorted(state["rows"]["package_ndc"].tolist())
    assert ndcs == ["TEST-A"], "R8-A22: the partial row must never be promoted into the artifact"
    assert state["capture"]["source_generation"] == "2026-09-20", \
        "R8-A22: the previous qualified capture is retained"
    assert state["last_refresh"]["qualified"] is False, "R8-A22: the failed refresh is exposed"
    assert state["last_refresh"]["failure_code"] == "PAGE_FAILED", \
        "R8-A22: the failed refresh records why"


def test_r8_a23_complete_empty_differs_from_failed_and_stale(tmp_path):
    """R8-A23: Distinguish complete empty observation from failed acquisition and stale cache."""
    from collectors.fda_shortages import (collect_shortage_sweep, read_shortage_observation,
                                          save_shortage_observation)

    path = tmp_path / "shortages.parquet"
    empty = _one_page_sweep("2026-09-20", [], datetime(2026, 9, 20, 12, tzinfo=UTC),
                            datetime(2026, 9, 20, 12, 0, 4, tzinfo=UTC))
    assert empty["qualified"] is True, "R8-A23: a complete empty source is a qualified observation"
    assert empty["failure_code"] is None, "R8-A23: complete empty carries no failure code"
    assert empty["rows"] == [], "R8-A23: complete empty has zero rows"
    assert empty["capture"]["complete"] is True, "R8-A23: the empty capture is complete"
    assert empty["capture"]["raw_count"] == 0 and empty["capture"]["reported_total"] == 0, \
        "R8-A23: counts agree at zero"
    save_shortage_observation(empty, path=path, expected_predecessor=None)

    def fetch_page(skip, limit):
        raise OSError("synthetic first page outage")

    outage = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC)),
        page_size=100, max_pages=5)
    assert outage["qualified"] is False, "R8-A23: a first-page outage is not an observation"
    assert outage["failure_code"] == "FIRST_PAGE_OUTAGE", \
        "R8-A23: the outage is distinguishable from a complete empty source"
    save_shortage_observation(outage, path=path, expected_predecessor=_digest(path))

    state = read_shortage_observation(path=path)
    assert state["legacy"] is False, "R8-A23: the stored observation is not legacy"
    assert state["capture"]["source_generation"] == "2026-09-20", \
        "R8-A23: the stale-but-qualified empty capture is still the selected one"
    assert state["last_refresh"]["failure_code"] == "FIRST_PAGE_OUTAGE", \
        "R8-A23: the stale cache is labelled with the failed refresh, not silently re-dated"


def test_r8_a24_capture_records_window_without_snapshot_proof():
    """R8-A24: Record the acquisition window/consistency checks; do not claim atomic snapshot proof."""
    result = _one_page_sweep(
        "2026-09-23", [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02")],
        datetime(2026, 9, 23, 12, tzinfo=UTC), datetime(2026, 9, 23, 12, 0, 8, tzinfo=UTC))
    cap = result["capture"]
    assert result["qualified"] is True, "R8-A24: the single complete page qualifies"
    assert cap["atomic_snapshot_proven"] is False, \
        "R8-A24: matching counts never prove snapshot isolation"
    assert cap["started_at"] == "2026-09-23T12:00:00+00:00", "R8-A24: acquisition start recorded"
    assert cap["finished_at"] == "2026-09-23T12:00:08+00:00", "R8-A24: acquisition finish recorded"
    assert cap["acquisition_interval_s"] == 8, "R8-A24: the acquisition window is disclosed"
    assert cap["raw_count"] == 1 and cap["unique_count"] == 1 and cap["reported_total"] == 1, \
        "R8-A24: the consistency counts are recorded"
    assert cap["complete"] is True, "R8-A24: completeness is an explicit recorded check"
    assert cap["source_generation"] == "2026-09-23", "R8-A24: the source generation is recorded"


def test_r8_a25_disappeared_row_is_retained_with_absence_basis(tmp_path):
    """R8-A25: Retain prior history and record current absence basis, not stale present-tense membership."""
    from collectors.fda_shortages import read_shortage_observation, save_shortage_observation

    path = tmp_path / "shortages.parquet"
    first = _one_page_sweep(
        "2026-09-20",
        [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02"),
         _rec("TEST-B", "Synthetic B", "Current", "Limited Availability", "2026-04-09")],
        datetime(2026, 9, 20, 12, tzinfo=UTC), datetime(2026, 9, 20, 12, 0, 6, tzinfo=UTC))
    assert first["qualified"] is True, "R8-A25: the first complete sweep qualifies"
    save_shortage_observation(first, path=path, expected_predecessor=None)

    second = _one_page_sweep(
        "2026-09-23", [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02")],
        datetime(2026, 9, 23, 12, tzinfo=UTC), datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC))
    assert second["qualified"] is True, "R8-A25: the second complete sweep qualifies"
    save_shortage_observation(second, path=path, expected_predecessor=_digest(path))

    rows = {r["package_ndc"]: r for r in read_shortage_observation(path=path)["rows"].to_dict("records")}
    assert set(rows) == {"TEST-A", "TEST-B"}, "R8-A25: the disappeared row is retained, not dropped"
    assert rows["TEST-A"]["last_observed_generation"] == "2026-09-23", \
        "R8-A25: the still-present row records the generation that observed it"
    assert rows["TEST-B"]["absent_since_generation"] == "2026-09-23", \
        "R8-A25: the absent row records the generation that stopped seeing it"
    assert rows["TEST-B"]["status"] == "Current", \
        "R8-A25: absence from a snapshot is never a status change to resolved"


def test_r8_a26_legacy_rows_get_forward_retention_not_backfill(tmp_path):
    """R8-A26: Mark historical coverage unavailable; begin truthful forward retention."""
    from collectors.fda_shortages import read_shortage_observation, save_shortage_observation

    path = tmp_path / "shortages.parquet"
    legacy_row = {c: None for c in LEGACY_COLUMNS}
    legacy_row.update({"package_ndc": "TEST-L", "generic_name": "Synthetic L",
                       "status": "Current", "availability": "Available",
                       "initial_posting_date": "2026-01-07",
                       "update_date": "2026-02-01", "company_name": "Synthetic Pharma Works",
                       "fetched_utc": "2026-02-01T00:00:00+00:00"})
    pd.DataFrame([legacy_row], columns=LEGACY_COLUMNS).to_parquet(path)

    before = read_shortage_observation(path=path)
    assert before["legacy"] is True, "R8-A26: a parquet with no sidecar is legacy"
    assert before["capture"] is None, "R8-A26: legacy rows have no known capture"
    assert before["history_coverage"]["legacy_rows_capture_unknown"] is True, \
        "R8-A26: legacy coverage is explicitly unknown"

    fresh = _one_page_sweep(
        "2026-09-23", [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02")],
        datetime(2026, 9, 23, 12, tzinfo=UTC), datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC))
    save_shortage_observation(fresh, path=path, expected_predecessor=None)

    cov = read_shortage_observation(path=path)["history_coverage"]
    assert cov["legacy_rows_capture_unknown"] is True, \
        "R8-A26: the legacy rows stay marked unknown after a qualified save"
    assert cov["earliest_qualified_generation"] == "2026-09-23", \
        "R8-A26: forward retention starts now — no hindsight backfill of an earlier generation"


def test_r8_a27_stale_capture_shows_age_and_failed_refresh(tmp_path):
    """R8-A27: Show its age and failed refresh; never replace source time with render time."""
    from collectors.fda_shortages import read_shortage_observation, save_shortage_observation

    path = tmp_path / "shortages.parquet"
    good = _one_page_sweep(
        "2026-09-20", [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02")],
        datetime(2026, 9, 20, 12, tzinfo=UTC), datetime(2026, 9, 20, 12, 0, 7, tzinfo=UTC))
    save_shortage_observation(good, path=path, expected_predecessor=None)

    def fetch_page(skip, limit):
        raise OSError("synthetic outage at refresh time")

    from collectors.fda_shortages import collect_shortage_sweep
    failed = collect_shortage_sweep(
        fetch_page, clock=_clock(datetime(2026, 9, 22, 9, tzinfo=UTC)),
        page_size=100, max_pages=5)
    assert failed["qualified"] is False, "R8-A27: the refresh failed"
    save_shortage_observation(failed, path=path, expected_predecessor=_digest(path))

    state = read_shortage_observation(path=path)
    assert state["capture"]["source_generation"] == "2026-09-20", \
        "R8-A27: the selected capture keeps its own generation"
    assert state["capture"]["finished_at"] == "2026-09-20T12:00:07+00:00", \
        "R8-A27: source/acquisition time is never replaced by render time"
    assert state["last_refresh"]["qualified"] is False, "R8-A27: the failed refresh is visible"
    assert state["last_refresh"]["attempted_at"] == "2026-09-22T09:00:00+00:00", \
        "R8-A27: the failed attempt carries its own clock, separate from the capture"


def test_r9_a02_atomic_snapshot_not_claimed_and_interval_disclosed(tmp_path):
    """R9-A02: Keep atomic_snapshot_proven=false and disclose the acquisition interval."""
    from collectors.fda_shortages import collect_shortage_sweep, save_shortage_observation

    path = tmp_path / "shortages.parquet"

    def fetch_page(skip, limit):
        rows = [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02"),
                _rec("TEST-B", "Synthetic B", "Resolved", "Available", "2026-04-09")]
        return _page("2026-09-23", rows[skip:skip + limit], 2)

    result = collect_shortage_sweep(
        fetch_page,
        clock=_clock(datetime(2026, 9, 23, 12, tzinfo=UTC),
                     datetime(2026, 9, 23, 12, 0, 30, tzinfo=UTC)),
        page_size=1, max_pages=5)
    cap = result["capture"]
    assert result["qualified"] is True, "R9-A02: a complete two-page sweep qualifies"
    assert cap["atomic_snapshot_proven"] is False, \
        "R9-A02: a multi-page interval sweep can never claim snapshot isolation"
    assert cap["acquisition_interval_s"] == 30, "R9-A02: the acquisition interval is disclosed"
    assert cap["pages"] == 2, "R9-A02: the page count is part of the disclosed window"

    save_shortage_observation(result, path=path, expected_predecessor=None)
    sidecar = json.loads(path.with_suffix(".observation.json").read_text())
    assert sidecar["selected_capture"]["atomic_snapshot_proven"] is False, \
        "R9-A02: the persisted receipt keeps the false snapshot claim"
    assert sidecar["selected_capture"]["acquisition_interval_s"] == 30, \
        "R9-A02: the persisted receipt keeps the interval"


def test_r10_a07_older_sweep_cannot_overwrite_newer_generation(tmp_path):
    """R10-A07: Existing writer fencing prevents an older sweep from overwriting a newer one."""
    from collectors.fda_shortages import read_shortage_observation, save_shortage_observation

    path = tmp_path / "shortages.parquet"
    p0 = _digest(path)
    assert p0 is None, "R10-A07: no predecessor receipt exists before the first save"

    sweep_b = _one_page_sweep(
        "2026-09-23", [_rec("TEST-B", "Synthetic B", "Current", "Available", "2026-05-05")],
        datetime(2026, 9, 23, 12, tzinfo=UTC), datetime(2026, 9, 23, 12, 0, 6, tzinfo=UTC))
    assert sweep_b["qualified"] is True, "R10-A07: the newer sweep qualifies"
    save_shortage_observation(sweep_b, path=path, expected_predecessor=p0)
    p1 = _digest(path)
    assert p1 is not None and p1 != p0, "R10-A07: the newer save minted a new receipt"

    sweep_a = _one_page_sweep(
        "2026-09-22", [_rec("TEST-A", "Synthetic A", "Current", "Available", "2026-03-02")],
        datetime(2026, 9, 22, 12, tzinfo=UTC), datetime(2026, 9, 22, 12, 0, 6, tzinfo=UTC))
    assert sweep_a["qualified"] is True, "R10-A07: the older sweep is itself qualified"
    out = save_shortage_observation(sweep_a, path=path, expected_predecessor=p0)
    assert out["promoted"] is False, "R10-A07: the older finisher must not replace the newer one"
    assert out["reason"] == "PREDECESSOR_MISMATCH", "R10-A07: the refusal names the stale predecessor"
    assert _digest(path) == p1, "R10-A07: the refused write left the receipt untouched"

    state = read_shortage_observation(path=path)
    assert state["capture"]["source_generation"] == "2026-09-23", \
        "R10-A07: the newer qualified generation is still selected"
    assert sorted(state["rows"]["package_ndc"].tolist()) == ["TEST-B"], \
        "R10-A07: the newer rows survive the stale writer"
