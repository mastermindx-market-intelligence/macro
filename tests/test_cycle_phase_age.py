"""Tests for engine.cycle_phase_age — the B05 measured phase-age reader.

Acceptance criteria (SIC-D-B05 r2 frozen spec — review RB05 findings 1–5):

  1. load_phase_history: ok (four columns only; missing basis → "tr"), absent
     (no file AND no directory created), read_error (corrupt parquet bytes).
  2. measure_phase_age: measured run; transition on the current session;
     lower_bound at start-of-history and at a 6-business-day hole; basis change
     stops the walk at the change; same-date (keep-first) and future rows
     ignored; insufficient_history (no rows / stale latest row / asof None);
     source_unavailable (None history); unknown_phase (falsy current phase).
     R1: non-session rows (weekend restamps; a weekday the benchmark panel
     did not trade) never count — with a `sessions` list and without (weekday
     rule).  R2: a contiguous pair spanning an unobserved session (missed run +
     flip; Thanksgiving without the holiday excluded) reads lower_bound, never
     a false measured.
  3. _stamp_phase_age: daily measured → bars == sessions; lower_bound → bars
     None; monthly record → bars None; amalgam/not_logged; passes `sessions`
     through to the reader (R1).
  4. record_series provenance stamps: "ontology" / "legacy_fallback" (classifier
     raises) / "legacy_pos_fallback" (canonical position unavailable); the
     single-bar call always ships phase_v2_age_bars None; legacy fields stay
     byte-identical across the fallback.
  5. SEMANTIC_FAMILIES v2 (R4): legacy/ontology/method_independent pairwise
     disjoint; their union equals the now-block keys of a fully stamped
     synthetic record; every listed key exists on a stamped record.

All frames are synthetic (no site/ or data/ reads).  I/O tests patch
`lib.config.data_dir` via monkeypatch, matching tests/test_cycle_forward_log.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

try:  # engine deps may be absent in a minimal venv — skip, never fail, then
    from engine import cycle_phase_age as cpa
    from engine import sector_cycles as sc
except Exception:  # noqa: BLE001
    cpa = None
    sc = None

requires_engine = pytest.mark.skipif(
    cpa is None, reason="cycle_phase_age unavailable (engine deps not installed)")


# ── helpers ──────────────────────────────────────────────────────────────────

def _hist(rows, entity="xlk"):
    """Synthetic forward-log frame: rows = [(date, phase_v2, basis), ...]."""
    return pd.DataFrame(
        [{"date": d, "id": entity, "phase_v2": p, "basis": b} for d, p, b in rows])


def _measure(rows=None, *, current_phase, asof, basis="tr", entity="xlk", history=None):
    hist = history if history is not None else (
        _hist(rows, entity) if rows is not None else None)
    return cpa.measure_phase_age(
        hist, entity_id=entity, current_phase=current_phase, current_asof=asof,
        basis=basis)


def _make_sector_close(n: int = 600, seed: int = 42) -> pd.Series:
    """Synthetic daily sector close (the W1.6 integration-test pattern)."""
    rng = np.random.default_rng(seed)
    log_ret = rng.normal(0.0002, 0.012, n)
    prices = 100.0 * np.exp(np.cumsum(log_ret))
    idx = pd.date_range("2019-01-02", periods=n, freq="B")
    return pd.Series(prices, index=idx)


def _record_with_synthetic() -> dict | None:
    """One record_series call on a synthetic close; None if deps unavailable."""
    try:
        close = _make_sector_close()
        last_ts = close.index[-1]
        return sc.record_series(close, win_start=last_ts - pd.DateOffset(years=7),
                                last_ts=last_ts)
    except Exception:  # noqa: BLE001 — network-free CI guard
        return None


_KERNEL_REC = _record_with_synthetic()
requires_kernel = pytest.mark.skipif(
    _KERNEL_REC is None, reason="record_series unavailable (engine deps not installed)")


# ── 1. load_phase_history ────────────────────────────────────────────────────

@requires_engine
def test_load_ok_reduces_to_four_columns(tmp_path, monkeypatch):
    import lib.config as config_mod
    d = tmp_path / "sector_cycles"
    d.mkdir()
    pd.DataFrame([{"date": "2025-10-08", "id": "xlk", "phase_v2": "Peak",
                   "basis": "price", "pos_v2": 61.2, "hazard_1m_p": 0.4}]
                 ).to_parquet(d / "forward_log.parquet")
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)
    df, status = cpa.load_phase_history()
    assert status == "ok"
    assert list(df.columns) == ["date", "id", "phase_v2", "basis"]
    assert df["basis"].iloc[0] == "price"


@requires_engine
def test_load_tolerates_missing_basis_column(tmp_path, monkeypatch):
    import lib.config as config_mod
    d = tmp_path / "sector_cycles"
    d.mkdir()
    pd.DataFrame([{"date": "2025-10-08", "id": "xlk", "phase_v2": "Peak"}]
                 ).to_parquet(d / "forward_log.parquet")
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)
    df, status = cpa.load_phase_history()
    assert status == "ok"
    assert (df["basis"] == "tr").all()


@requires_engine
def test_load_absent_creates_nothing(tmp_path, monkeypatch):
    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)
    df, status = cpa.load_phase_history()
    assert (df, status) == (None, "absent")
    assert not (tmp_path / "sector_cycles").exists(), "reader must never create a directory"


@requires_engine
def test_load_corrupt_parquet_is_read_error(tmp_path, monkeypatch):
    import lib.config as config_mod
    d = tmp_path / "sector_cycles"
    d.mkdir()
    (d / "forward_log.parquet").write_bytes(b"definitely not parquet bytes")
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)
    df, status = cpa.load_phase_history()
    assert (df, status) == (None, "read_error")


# ── 2. measure_phase_age ─────────────────────────────────────────────────────

@requires_engine
def test_measured_run_counts_contiguous_same_phase_sessions():
    """3 Trough then 4 Recovery sessions, current Recovery → sessions 5 measured."""
    rows = [("2025-10-06", "Trough", "tr"), ("2025-10-07", "Trough", "tr"),
            ("2025-10-08", "Trough", "tr"), ("2025-10-09", "Recovery", "tr"),
            ("2025-10-10", "Recovery", "tr"), ("2025-10-13", "Recovery", "tr"),
            ("2025-10-14", "Recovery", "tr")]
    out = _measure(rows, current_phase="Recovery", asof="2025-10-15")
    assert out["status"] == "measured"
    assert out["sessions"] == 5
    assert out["run_start"] == "2025-10-09"          # first Recovery date
    assert out["observed_from"] == "2025-10-08"      # transition row
    assert out["history_rows"] == 7
    assert out["method"] == "forward_log_replay.v2"
    assert "error" not in out


@requires_engine
def test_transition_on_current_session_is_measured_sessions_one():
    """Latest prior row differs from the live phase → the run starts today."""
    rows = [("2025-10-13", "Recovery", "tr"), ("2025-10-14", "Recovery", "tr")]
    out = _measure(rows, current_phase="Downturn", asof="2025-10-15")
    assert out["status"] == "measured"
    assert out["sessions"] == 1
    assert out["run_start"] == "2025-10-15"          # the current session


@requires_engine
def test_history_starting_inside_run_is_lower_bound():
    """Usable history begins mid-run → the count is a minimum."""
    rows = [("2025-10-09", "Recovery", "tr"), ("2025-10-10", "Recovery", "tr"),
            ("2025-10-13", "Recovery", "tr"), ("2025-10-14", "Recovery", "tr")]
    out = _measure(rows, current_phase="Recovery", asof="2025-10-15")
    assert out["status"] == "lower_bound"
    assert out["sessions"] == 5                      # 4 prior + current, minimum
    assert out["run_start"] is None
    assert out["observed_from"] == "2025-10-09"      # earliest date counted


@requires_engine
def test_six_busday_hole_inside_run_is_lower_bound_at_the_hole():
    """A 6-business-day hole stops the walk; sessions above the hole count."""
    rows = [("2025-09-18", "Peak", "tr"), ("2025-09-19", "Peak", "tr"),   # below hole
            ("2025-09-29", "Peak", "tr"), ("2025-09-30", "Peak", "tr")]  # above hole
    out = _measure(rows, current_phase="Peak", asof="2025-10-01")
    assert out["status"] == "lower_bound"
    assert out["sessions"] == 3                      # 2 above the hole + current
    assert out["observed_from"] == "2025-09-29"
    assert out["history_rows"] == 4


@requires_engine
def test_thanksgiving_week_counts_contiguous():
    """2025-11-26 → 2025-11-28 spans the holiday (busday_count 2) and stays
    contiguous — the tolerance is unchanged.  R2 changed the EXPECTATION: the
    session the holiday occupied has no usable row, so without a session list
    the walk cannot claim the boundary was observed → lower_bound (was
    `measured` pre-r2 — a contiguous-but-bridged pair is no longer measured).
    With `sessions` excluding the holiday the same fixture stays `measured`."""
    rows = [("2025-11-25", "Downturn", "tr"), ("2025-11-26", "Peak", "tr"),
            ("2025-11-28", "Peak", "tr")]
    out = _measure(rows, current_phase="Peak", asof="2025-12-01")
    assert out["status"] == "lower_bound"            # 11-27 unobserved → minimum
    assert out["sessions"] == 3                      # 11-28 + 11-26 + current
    assert out["run_start"] is None
    assert out["observed_from"] == "2025-11-26"      # earliest date counted
    # the benchmark panel marks Thursday 2025-11-27 closed → nothing unobserved
    sessions = ["2025-11-25", "2025-11-26", "2025-11-28", "2025-12-01"]
    out2 = cpa.measure_phase_age(
        _hist(rows), entity_id="xlk", current_phase="Peak",
        current_asof="2025-12-01", basis="tr", sessions=sessions)
    assert out2["status"] == "measured"
    assert out2["sessions"] == 3
    assert out2["run_start"] == "2025-11-26"
    assert out2["observed_from"] == "2025-11-25"


@requires_engine
def test_weekend_restamps_count_fri_and_mon_once():
    """R1 (RB05-1): pre-#7211 the log restamped the prior session onto Sat/Sun
    calendar-union tips — a weekend crossing tripled one session into three.
    Rows Fri/Sat/Sun/Mon same phase, transition Thu, asof Tue → Fri and Mon
    count once each (= 3 with the asof session), `measured`; the weekday rule
    and an explicit `sessions` list agree."""
    rows = [("2025-10-09", "Downturn", "tr"), ("2025-10-10", "Peak", "tr"),
            ("2025-10-11", "Peak", "tr"), ("2025-10-12", "Peak", "tr"),
            ("2025-10-13", "Peak", "tr")]
    sessions = ["2025-10-09", "2025-10-10", "2025-10-13", "2025-10-14"]
    out = _measure(rows, current_phase="Peak", asof="2025-10-14")
    assert out["status"] == "measured"
    assert out["sessions"] == 3                      # Fri + Mon + asof, not 5
    assert out["run_start"] == "2025-10-10"
    assert out["observed_from"] == "2025-10-09"
    assert out["history_rows"] == 3                  # Sat/Sun never reach the walk
    out2 = cpa.measure_phase_age(
        _hist(rows), entity_id="xlk", current_phase="Peak",
        current_asof="2025-10-14", basis="tr", sessions=sessions)
    for k in ("status", "sessions", "run_start", "observed_from", "history_rows"):
        assert out2[k] == out[k], k


@requires_engine
def test_non_session_weekday_dropped_only_with_sessions():
    """R1: a WEEKDAY the benchmark did not trade (holiday) is dropped only when
    the session list says so — the weekday rule alone cannot see it."""
    rows = [("2025-10-06", "Downturn", "tr"), ("2025-10-07", "Peak", "tr"),
            ("2025-10-08", "Peak", "tr"), ("2025-10-09", "Peak", "tr")]
    sessions = ["2025-10-06", "2025-10-07", "2025-10-09", "2025-10-10"]  # no Wed
    out = cpa.measure_phase_age(
        _hist(rows), entity_id="xlk", current_phase="Peak",
        current_asof="2025-10-10", basis="tr", sessions=sessions)
    assert out["status"] == "measured"               # Wed not a session → nothing unobserved
    assert out["sessions"] == 3                      # Tue + Thu + current
    assert out["history_rows"] == 3
    plain = _measure(rows, current_phase="Peak", asof="2025-10-10")
    assert plain["sessions"] == 4                    # weekday rule counts Wed


@requires_engine
def test_missed_run_then_flip_is_lower_bound_not_measured():
    """R2 (RB05 finding 2): Mon(Trough), Wed/Thu(Recovery), asof Fri, sessions
    Mon..Fri — Tuesday ran unlogged, so the Trough→Recovery transition is known
    only to the (Mon, Wed) window: lower_bound, run_start None, minimum count."""
    rows = [("2025-10-06", "Trough", "tr"), ("2025-10-08", "Recovery", "tr"),
            ("2025-10-09", "Recovery", "tr")]
    sessions = ["2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09",
                "2025-10-10"]
    out = cpa.measure_phase_age(
        _hist(rows), entity_id="xlk", current_phase="Recovery",
        current_asof="2025-10-10", basis="tr", sessions=sessions)
    assert out["status"] == "lower_bound"            # was `measured` pre-r2
    assert out["sessions"] == 3                      # Wed + Thu + current, minimum
    assert out["run_start"] is None
    assert out["observed_from"] == "2025-10-08"      # earliest date counted


@requires_engine
def test_row_dated_exactly_asof_with_other_phase_is_ignored():
    """R3: a row dated exactly `current_asof` with a DIFFERENT phase is ignored
    (the live read stands for the current session).  Mutation-proved: with the
    reader's `dates < asof` relaxed to `dates <= asof` this test fails."""
    rows = [("2025-10-08", "Recovery", "tr"),
            ("2025-10-09", "Downturn", "tr")]       # dated exactly on asof
    out = _measure(rows, current_phase="Recovery", asof="2025-10-09")
    assert out["history_rows"] == 1                  # the asof row never enters
    assert out["status"] == "lower_bound"            # history starts mid-run
    assert out["sessions"] == 2
    assert out["run_start"] is None


@requires_engine
def test_none_asof_is_insufficient_history_not_source_unavailable():
    """R5: `current_asof=None` has no comparable session boundary — the status
    is insufficient_history, and the asof guard fires BEFORE the unknown_phase
    branch (a falsy phase cannot answer first).  Mutation-proved: deleting the
    `if asof is None` guard makes the comparison `dates < None` degrade to
    all-False in pandas (no raise), so the falsy-phase leg falls through to
    unknown_phase and fails this test.  (This pandas never reaches the
    source_unavailable catch the guard also protects against.)"""
    rows = [("2025-10-14", "Recovery", "tr")]
    out = _measure(rows, current_phase="Recovery", asof=None)
    assert out["status"] == "insufficient_history"
    assert out["sessions"] is None
    assert "error" not in out
    out2 = _measure(rows, current_phase=None, asof=None)
    assert out2["status"] == "insufficient_history"  # asof guard has precedence
    assert out2["sessions"] is None


@requires_engine
def test_basis_change_stops_walk_at_the_change():
    """Only same-basis rows are usable: tr rows never count toward a price run."""
    rows = [("2025-10-06", "Recovery", "tr"), ("2025-10-07", "Recovery", "tr"),
            ("2025-10-08", "Recovery", "price"), ("2025-10-09", "Recovery", "price")]
    out = _measure(rows, current_phase="Recovery", asof="2025-10-10", basis="price")
    assert out["status"] == "lower_bound"            # tr epoch invisible → minimum
    assert out["sessions"] == 3                      # 2 price rows + current
    assert out["observed_from"] == "2025-10-08"
    assert out["history_rows"] == 2
    assert out["basis"] == "price"


@requires_engine
def test_same_date_and_future_rows_are_ignored():
    """A row dated on the current session and later are dropped; a same-date
    duplicate keeps the FIRST row (the writer's keep-FIRST invariant)."""
    rows = [("2025-10-07", "Downturn", "tr"),
            ("2025-10-08", "Downturn", "tr"), ("2025-10-08", "Recovery", "tr"),  # dup
            ("2025-10-10", "Recovery", "tr")]                                      # future
    out = _measure(rows, current_phase="Recovery", asof="2025-10-09")
    assert out["history_rows"] == 2                 # dup + future dropped
    assert out["status"] == "measured"              # kept-first 10-08 is Downturn
    assert out["sessions"] == 1                     # → transition at 10-08, not a run
    assert out["run_start"] == "2025-10-09"


@requires_engine
def test_no_rows_and_stale_latest_row_are_insufficient_history():
    """No usable prior row, or the latest one not contiguous with asof."""
    empty = pd.DataFrame({"date": [], "id": [], "phase_v2": [], "basis": []})
    out = _measure(history=empty, current_phase="Recovery", asof="2025-10-15")
    assert out["status"] == "insufficient_history"
    assert out["sessions"] is None
    stale = [("2025-09-01", "Peak", "tr"), ("2025-09-02", "Peak", "tr")]
    out2 = _measure(stale, current_phase="Peak", asof="2025-10-15")
    assert out2["status"] == "insufficient_history"
    assert out2["sessions"] is None


@requires_engine
def test_none_history_is_source_unavailable():
    out = _measure(history=None, current_phase="Peak", asof="2025-10-15")
    assert out["status"] == "source_unavailable"
    assert out["sessions"] is None
    assert "error" not in out


@requires_engine
def test_falsy_current_phase_is_unknown_phase():
    rows = [("2025-10-14", "Recovery", "tr")]
    for bad in (None, ""):
        out = _measure(rows, current_phase=bad, asof="2025-10-15")
        assert out["status"] == "unknown_phase"
        assert out["sessions"] is None


@requires_engine
def test_internal_exception_never_raises():
    """A history lacking the phase_v2 column degrades to source_unavailable."""
    bogus = pd.DataFrame({"date": ["2025-10-14"], "id": ["xlk"]})
    out = cpa.measure_phase_age(bogus, entity_id="xlk", current_phase="Peak",
                                current_asof="2025-10-15", basis="tr")
    assert out["status"] == "source_unavailable"
    assert out["sessions"] is None
    assert "error" in out


# ── 3. _stamp_phase_age ──────────────────────────────────────────────────────

@requires_engine
def test_stamp_daily_measured_bars_equal_sessions():
    hist = _hist([("2025-10-06", "Trough", "tr"), ("2025-10-07", "Trough", "tr"),
                  ("2025-10-08", "Trough", "tr"), ("2025-10-09", "Recovery", "tr"),
                  ("2025-10-10", "Recovery", "tr"), ("2025-10-13", "Recovery", "tr"),
                  ("2025-10-14", "Recovery", "tr")])
    recs = [{"id": "xlk", "basis": "tr",
             "now": {"phase_v2": "Recovery", "basis": "tr"}}]   # no freq key → daily
    sc._stamp_phase_age(recs, asof="2025-10-15", history=hist, history_status="ok")
    nw = recs[0]["now"]
    assert nw["phase_v2_age_status"] == "measured"
    assert nw["phase_v2_age_sessions"] == 5
    assert nw["phase_v2_age_bars"] == 5              # daily measured → bars == sessions
    assert nw["phase_v2_age"]["run_start"] == "2025-10-09"


@requires_engine
def test_stamp_lower_bound_and_monthly_leave_bars_none():
    lb = _hist([("2025-10-09", "Recovery", "tr"), ("2025-10-10", "Recovery", "tr"),
                ("2025-10-13", "Recovery", "tr"), ("2025-10-14", "Recovery", "tr")])
    recs = [{"id": "xlk", "basis": "tr",
             "now": {"phase_v2": "Recovery", "basis": "tr"}},
            {"id": "monthly", "basis": "tr",
             "now": {"phase_v2": "Recovery", "basis": "tr", "freq": "M"}}]
    sc._stamp_phase_age(recs, asof="2025-10-15", history=lb, history_status="ok")
    nw0, nw1 = recs[0]["now"], recs[1]["now"]
    assert nw0["phase_v2_age_status"] == "lower_bound"
    assert nw0["phase_v2_age_sessions"] == 5
    assert nw0["phase_v2_age_bars"] is None           # minimum ≠ measurement
    assert nw1["phase_v2_age_bars"] is None           # monthly bar ≠ session


@requires_engine
def test_stamp_amalgam_records_not_logged():
    recs = [{"id": "ndx-semis", "kind": "ndx",
             "now": {"phase_v2": "Recovery", "basis": "tr", "freq": "D"}}]
    sc._stamp_phase_age(recs, asof="2025-10-15", history=None,
                        history_status="not_logged")
    nw = recs[0]["now"]
    assert nw["phase_v2_age_status"] == "not_logged"
    assert nw["phase_v2_age_sessions"] is None
    assert nw["phase_v2_age_bars"] is None
    assert nw["phase_v2_age"]["method"] == "forward_log_replay.v2"


@requires_engine
def test_stamp_never_raises_on_broken_record():
    recs = [{"id": "xlk", "now": {"phase_v2": "Recovery"}}, "not-a-record"]
    sc._stamp_phase_age(recs, asof="2025-10-15", history=None,
                        history_status="ok")          # None history → source_unavailable
    assert recs[0]["now"]["phase_v2_age_status"] == "source_unavailable"
    assert recs[1] == "not-a-record"                 # left unchanged


@requires_engine
def test_stamp_passes_sessions_through_to_the_reader():
    """R1 (packet test 5): `_stamp_phase_age` forwards `sessions` — the same
    record measures 3 with the holiday excluded from the panel and 4 without."""
    rows = [("2025-10-06", "Downturn", "tr"), ("2025-10-07", "Peak", "tr"),
            ("2025-10-08", "Peak", "tr"), ("2025-10-09", "Peak", "tr")]
    sessions = ["2025-10-06", "2025-10-07", "2025-10-09", "2025-10-10"]  # no Wed
    with_s = [{"id": "xlk", "basis": "tr",
               "now": {"phase_v2": "Peak", "basis": "tr"}}]
    sc._stamp_phase_age(with_s, asof="2025-10-10", history=_hist(rows),
                        history_status="ok", sessions=sessions)
    without_s = [{"id": "xlk", "basis": "tr",
                  "now": {"phase_v2": "Peak", "basis": "tr"}}]
    sc._stamp_phase_age(without_s, asof="2025-10-10", history=_hist(rows),
                        history_status="ok")
    nw_s, nw_p = with_s[0]["now"], without_s[0]["now"]
    assert nw_s["phase_v2_age_status"] == "measured"
    assert nw_s["phase_v2_age_sessions"] == 3        # Wed excluded by the panel
    assert nw_s["phase_v2_age"]["history_rows"] == 3
    assert nw_p["phase_v2_age_sessions"] == 4        # weekday rule counts Wed
    assert nw_p["phase_v2_age"]["history_rows"] == 4


# ── 4. record_series provenance stamps ───────────────────────────────────────

@requires_kernel
def test_record_series_default_path_stamps_ontology():
    rec = _KERNEL_REC
    nw = rec["now"]
    assert nw["phase_v2_source"] == "ontology"
    assert nw["phase_v2_position_input"] == "pos_v2"
    assert nw["phase_v2_age_bars"] is None           # single-bar call cannot measure


@requires_kernel
def test_record_series_classifier_failure_stamps_legacy_fallback(monkeypatch):
    """onto.classify_phase raising → phase_v2 falls back to the legacy phase and
    the fallback is stamped, never silent."""
    def boom(*args, **kwargs):
        raise RuntimeError("synthetic classifier failure")
    monkeypatch.setattr(sc.onto, "classify_phase", boom)
    close = _make_sector_close()
    last_ts = close.index[-1]
    rec = sc.record_series(close, win_start=last_ts - pd.DateOffset(years=7),
                           last_ts=last_ts)
    nw = rec["now"]
    assert nw["phase_v2_source"] == "legacy_fallback"
    assert nw["phase_v2"] == nw["phase"]             # the silent fallback, now visible
    assert nw["phase_v2_age_bars"] is None
    # legacy vocabulary is untouched by the fallback
    for key in ("phase", "phaseLabel", "pos", "signal", "timing_state", "action"):
        assert nw[key] == _KERNEL_REC["now"][key], key


@requires_kernel
def test_record_series_missing_pos_v2_stamps_legacy_pos_fallback(monkeypatch):
    """canonical_position unavailable → classify_phase reads the legacy position."""
    def boom(*args, **kwargs):
        raise RuntimeError("synthetic canonical_position failure")
    monkeypatch.setattr(sc.onto, "canonical_position", boom)
    close = _make_sector_close()
    last_ts = close.index[-1]
    rec = sc.record_series(close, win_start=last_ts - pd.DateOffset(years=7),
                           last_ts=last_ts)
    nw = rec["now"]
    assert nw["pos_v2"] is None
    assert nw["phase_v2_position_input"] == "legacy_pos_fallback"
    assert nw["phase_v2_source"] == "ontology"       # classifier itself still ran


# ── 5. SEMANTIC_FAMILIES ─────────────────────────────────────────────────────

@requires_engine
def test_semantic_families_lists_are_disjoint():
    fam = sc.SEMANTIC_FAMILIES
    assert fam["schema"] == "sector_cycles.semantic_families.v2"
    legacy = set(fam["legacy"])
    ontology = set(fam["ontology"])
    independent = set(fam["method_independent"])
    assert legacy & ontology == set()
    assert legacy & independent == set()
    assert ontology & independent == set()
    assert legacy == {"phase", "phaseLabel", "pos", "signal", "osc_slope",
                      "timing_state", "action", "read", "read_zh"}
    assert {"pos_v2", "phase_v2", "phase_v2_age_bars", "phase_v2_source",
            "phase_v2_position_input", "phase_v2_age_sessions",
            "phase_v2_age", "phase_v2_age_status"} <= ontology
    assert {"w_macd_up", "rs_63d", "above200d", "basis", "freq"} <= independent
    assert fam["legacy_position_method"] == "range_stochastic"
    assert fam["ontology_position_method"] == "canonical_zcdf"


@requires_kernel
def test_semantic_families_keys_exist_on_stamped_record():
    """Every legacy/ontology key exists on a record_series output after
    phase-age stamping (method_independent keys are basket/monthly-path only —
    the full-partition test below covers them)."""
    rec = dict(_KERNEL_REC)                          # shallow copy; stamping mutates now
    rec["now"] = dict(_KERNEL_REC["now"])
    sc._stamp_phase_age([rec], asof="2026-10-20", history=_hist(
        [("2026-10-15", "Recovery", "tr")]), history_status="ok")
    nw = rec["now"]
    for key in sc.SEMANTIC_FAMILIES["legacy"] + sc.SEMANTIC_FAMILIES["ontology"]:
        assert key in nw, f"{key} missing from a stamped record's now block"


@requires_kernel
def test_semantic_families_v2_partition_every_stamped_now_key(monkeypatch):
    """R4: on a FULLY stamped synthetic record (basket family, so the W3.1
    freq/hazard_features stamps fire; leadership, engine read, hazard score,
    RS ranks and phase age applied) the three family lists are pairwise
    disjoint and their union EQUALS the record's now-block keys.  The hazard
    artifact is stubbed — CI has no data/, and the families cover the KEY, not
    the pillar's calibration."""
    import engine.hazard_score as hz_mod
    monkeypatch.setattr(hz_mod, "score", lambda *a, **k: {"stub": True})
    close = _make_sector_close(seed=7)
    last_ts = close.index[-1]
    rec = sc.record_series(close, win_start=last_ts - pd.DateOffset(years=7),
                           last_ts=last_ts, family="basket")
    assert rec is not None
    sc._apply_leadership(rec, {"rs_21d": 1.0, "rs_63d": 2.0, "rs_126d": 0.5,
                               "rs_above_trend": True, "thin_history": False})
    sc._set_engine_read(rec)
    sc._stamp_hazard(rec, family="basket")
    sc._stamp_rs_ranks([rec])
    sc._stamp_phase_age([rec], asof=str(last_ts.date()), history=_hist(
        [(str(close.index[-2].date()), "Trough", "tr")]), history_status="ok")
    fam = sc.SEMANTIC_FAMILIES
    legacy = set(fam["legacy"])
    ontology = set(fam["ontology"])
    independent = set(fam["method_independent"])
    assert legacy & ontology == set()
    assert legacy & independent == set()
    assert ontology & independent == set()
    nw_keys = set(rec["now"])
    assert legacy | ontology | independent == nw_keys
    assert "hazard" in nw_keys and "freq" in nw_keys   # the basket path stamped them
