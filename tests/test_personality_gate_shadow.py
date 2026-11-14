"""PSS-W3 — Prophet tailored-gate shadow (pure accrual, never a gate).

Synthetic-store tests mirroring test_mag7_washout_shadow's root=tmp convention.
The nightly-sole-advancer sentinel is exercised via COLLECT_LANE (ledger_lane).

Fixture strategy: a wobbly-down tape (down-down-up steps) prints Stoch-RSI<20
crosses repeatedly; truncating the DAILY series to end exactly on a chosen rung's
fire bar-date makes that rung fire on its LATEST bar — the condition the nightly
lane logs. seed=0 yields a stable 3D fire and a stable 2W fire at deterministic
lengths, so the four disagreement classes are all reproducible without mocking the
derived K/D. Both gates reuse the pinned engine stoch (bars_for + tool_dates(·,"S")
→ engine.mag7_washout.stoch_rsi/cross_up); nothing is re-implemented here.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import personality_gate_shadow as pgs
from engine.personality_gate_shadow import LEDGER_SCHEMA, STATE_SCHEMA, UNIFORM_RUNG
from scripts.research.ptt_w1_persistence_of_fit import bars_for, tool_dates


# ── fixtures ────────────────────────────────────────────────────────────────
def _wobbly(n: int = 600, seed: int = 0) -> pd.Series:
    """down-down-up sawtooth into oversold — S-family Stoch-RSI crosses print
    repeatedly, so a fire can be landed on any rung's terminal bar by truncation."""
    rng = np.random.default_rng(seed)
    px = [100.0]
    for _ in range(1, n):
        px.append(px[-1] * (1 + rng.choice([-0.03, -0.03, 0.025])))
    return pd.Series(px, index=pd.bdate_range("2019-01-01", periods=n))



def _calendar_wobbly(n: int = 700, seed: int = 0) -> pd.Series:
    """Older synthetic warm-up; capture and maturity stay in verified 2026."""
    from lib.market_session import is_session_date
    dates = [d for d in pd.bdate_range(end="2026-12-30", periods=n + 60)
             if is_session_date("us", d.date())][-n:]
    assert len(dates) == n
    return pd.Series(_wobbly(n, seed).to_numpy(), index=pd.DatetimeIndex(dates))


def _after_day(day) -> str:
    return str((pd.Timestamp(day) + pd.Timedelta(days=1)).date())


def _trunc_to_fire(s: pd.Series, rung: str, min_fwd: int = 0) -> pd.Series | None:
    """Trim `s` so its last DAILY bar == a `rung` fire bar-date. With min_fwd>0,
    choose a fire that still leaves ≥min_fwd daily bars ahead in the full tape (for
    the maturity/grading tests)."""
    bars = bars_for(s, rung)
    dates = tool_dates(bars, "S")
    if not dates:
        return None
    if min_fwd <= 0:
        return s[s.index <= dates[-1]]
    for cand in dates[::-1]:
        if int((s.index > cand).sum()) >= min_fwd:
            return s[s.index <= cand]
    return None


def _write_close(root: Path, sym: str, ser: pd.Series) -> None:
    d = root / "baskets" / "ohlcv"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"open": ser, "high": ser * 1.01, "low": ser * 0.99,
                  "close": ser, "volume": 1e6}).to_parquet(d / f"{sym}.parquet")


def _write_codex(root: Path, rows: list[dict], as_of: str = "2026-07-25") -> None:
    d = root / "personality_timing"
    d.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{"as_of": as_of, **r} for r in rows])
    df.to_parquet(d / "codex.parquet")


def _nightly(monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")


def _ledger_rows(root: Path) -> list[dict]:
    p = root / "personality_timing" / "gate_shadow.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if not l.startswith("#")]


# ── disagreement classification ─────────────────────────────────────────────
def test_four_disagreement_classes(tmp_path, monkeypatch):
    """All four classes populate; only fires are stored; 'neither' is census-only."""
    _nightly(monkeypatch)
    tail3d = _trunc_to_fire(_wobbly(), "3D")     # 3D fires, 2W does not on its terminal
    uni2w = _trunc_to_fire(_wobbly(), "2W")      # 2W fires; a 3D-rung name → uniform_only
    flat = pd.Series(100.0 + np.zeros(400),
                     index=pd.bdate_range("2019-01-01", periods=400))  # never fires
    assert tail3d is not None and uni2w is not None

    _write_close(tmp_path, "TAIL3D", tail3d)     # rung 3D → fired_tailored_only
    _write_close(tmp_path, "UNI2W", uni2w)       # rung 3D → fired_uniform_only
    _write_close(tmp_path, "AGREE2W", uni2w)     # rung 2W → both (agree_by_construction)
    _write_close(tmp_path, "QUIET", flat)        # rung 1W → neither
    _write_codex(tmp_path, [
        {"sym": "TAIL3D", "rung_derived": "3D"},
        {"sym": "UNI2W", "rung_derived": "3D"},
        {"sym": "AGREE2W", "rung_derived": "2W"},
        {"sym": "QUIET", "rung_derived": "1W"},
    ])

    st = pgs.update(root=tmp_path, as_of="2026-07-25")
    assert st is not None and st["schema"] == STATE_SCHEMA
    c = st["coverage_census"]
    assert c["codex_names"] == 4 and c["covered"] == 4
    assert c["classes"] == {"both": 1, "fired_uniform_only": 1,
                            "fired_tailored_only": 1, "neither": 1}
    assert c["disagreements"] == 2          # the two *_only classes
    assert c["agree_by_construction"] == 1  # AGREE2W (rung == uniform 2W)

    rows = {r["sym"]: r for r in _ledger_rows(tmp_path)}
    assert set(rows) == {"TAIL3D", "UNI2W", "AGREE2W"}   # QUIET (neither) not stored
    assert rows["TAIL3D"]["disagreement_class"] == "fired_tailored_only"
    assert rows["TAIL3D"]["fired_tailored"] and not rows["TAIL3D"]["fired_uniform"]
    assert rows["UNI2W"]["disagreement_class"] == "fired_uniform_only"
    assert rows["UNI2W"]["fired_uniform"] and not rows["UNI2W"]["fired_tailored"]
    assert rows["AGREE2W"]["disagreement_class"] == "both"
    assert rows["AGREE2W"]["agree_by_construction"] is True
    for r in rows.values():
        assert r["schema"] == LEDGER_SCHEMA
        assert r["uniform_rung"] == UNIFORM_RUNG == "2W"
        assert r["graded"] is False          # fire on terminal bar — no forward tape yet


# ── ledger append idempotency (same-day rerun) ──────────────────────────────
def test_same_day_rerun_appends_nothing(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    s = _trunc_to_fire(_wobbly(), "3D")
    _write_close(tmp_path, "TAIL3D", s)
    _write_codex(tmp_path, [{"sym": "TAIL3D", "rung_derived": "3D"}])

    st1 = pgs.update(root=tmp_path, as_of="2026-07-25")
    n1 = len(_ledger_rows(tmp_path))
    assert n1 == 1 and st1["ledger"]["appended_today"] == 1

    st2 = pgs.update(root=tmp_path, as_of="2026-07-25")   # same as_of key
    assert len(_ledger_rows(tmp_path)) == n1              # no duplicate row
    assert st2["ledger"]["appended_today"] == 0
    assert st2["ledger"]["fire_rows"] == 1


# ── nightly-sole-advancer sentinel ──────────────────────────────────────────
def test_sentinel_off_appends_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    s = _trunc_to_fire(_wobbly(), "3D")
    _write_close(tmp_path, "TAIL3D", s)
    _write_codex(tmp_path, [{"sym": "TAIL3D", "rung_derived": "3D"}])

    st = pgs.update(root=tmp_path, as_of="2026-07-25")
    assert st is not None and st["gate_open"] is False
    # census still computed (measurement runs any lane); ledger append is gated off
    assert st["coverage_census"]["classes"]["fired_tailored_only"] == 1
    assert not (tmp_path / "personality_timing" / "gate_shadow.jsonl").exists()


# ── PIT rung join (the tailored rung comes from the codex, not re-derived) ───
def test_pit_rung_join_from_codex(tmp_path, monkeypatch):
    """The tailored gate fires on the rung the CODEX assigns the name. Same tape,
    two codex rungs → different tailored-gate outcomes; the join is PIT (the codex
    as_of is carried onto the fire row)."""
    _nightly(monkeypatch)
    s3 = _trunc_to_fire(_wobbly(), "3D")   # 3D fires on terminal, 2W does not
    _write_close(tmp_path, "NAME3D", s3)
    _write_close(tmp_path, "NAME2W", s3)   # identical tape…
    _write_codex(tmp_path, [
        {"sym": "NAME3D", "rung_derived": "3D"},   # …but codex says 3D → tailored fires
        {"sym": "NAME2W", "rung_derived": "2W"},   # …codex says 2W → tailored is the 2W read
    ], as_of="2026-07-25")

    pgs.update(root=tmp_path, as_of="2026-07-25")
    rows = {r["sym"]: r for r in _ledger_rows(tmp_path)}
    assert rows["NAME3D"]["tailored_rung"] == "3D"
    assert rows["NAME3D"]["fired_tailored"] is True
    assert rows["NAME3D"]["codex_asof"] == "2026-07-25"   # PIT stamp carried
    # NAME2W: tailored rung == uniform rung → agree_by_construction; on this tape the
    # 2W terminal bar is NOT a fire, so it lands in 'neither' and is not stored.
    assert "NAME2W" not in rows
    assert pgs.update(root=tmp_path, as_of="2026-07-25")  # idempotent, no crash


def test_bad_rung_and_missing_prices_are_census_dropped(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    s = _trunc_to_fire(_wobbly(), "3D")
    _write_close(tmp_path, "GOOD", s)
    # BADRUNG has an unknown rung; NOPRICE has a codex row but no ohlcv file
    _write_codex(tmp_path, [
        {"sym": "GOOD", "rung_derived": "3D"},
        {"sym": "BADRUNG", "rung_derived": "1M"},
        {"sym": "NOPRICE", "rung_derived": "1W"},
    ])
    st = pgs.update(root=tmp_path, as_of="2026-07-25")
    c = st["coverage_census"]
    assert c["codex_names"] == 3
    assert c["covered"] == 1          # only GOOD
    assert c["bad_rung"] == 1         # BADRUNG
    assert c["no_prices"] == 1        # NOPRICE


# ── deferred DUAL-ruler grading (frozen-until-matured, nightly-gated) ────────
def test_dual_ruler_grade_defers_then_advances(tmp_path, monkeypatch):
    """A fire on the terminal bar stays ungraded (no forward tape); once ≥63td of
    forward tape accrues the grade advances under BOTH rulers, then is idempotent."""
    _nightly(monkeypatch)
    full = _calendar_wobbly(600, 0)
    s = _trunc_to_fire(full, "3D", min_fwd=70)   # fire with ≥70 daily bars ahead in `full`
    assert s is not None and s.index[-1].year == 2026
    _write_close(tmp_path, "TAIL3D", s)
    first = str(s.index[-1].date())
    _write_codex(tmp_path, [{"sym": "TAIL3D", "rung_derived": "3D"}], as_of=first)

    st1 = pgs.update(root=tmp_path, as_of=first)
    assert st1["ledger"]["graded"] == 0
    r1 = _ledger_rows(tmp_path)[0]
    assert r1["tailored_grade"] is None and r1["graded"] is False

    # A separate nightly captures the first post-publication daily close.
    next_session = full.iloc[:len(s) + 1]
    _write_close(tmp_path, "TAIL3D", next_session)
    sampled = pgs.update(root=tmp_path, as_of=_after_day(next_session.index[-1]))
    assert sampled["ledger"]["graded_prospective"] == 0
    execution = _ledger_rows(tmp_path)[0]["tailored_execution"]
    assert execution["entry_date"] == str(next_session.index[-1].date())
    assert execution["entry_px"] == round(float(next_session.iloc[-1]), 4)

    # Only later can 63 FULL sessions of outcome mature.
    _write_close(tmp_path, "TAIL3D", full)
    st2 = pgs.update(root=tmp_path, as_of=_after_day(full.index[-1]))
    assert st2["ledger"]["grades_advanced_today"] == 1
    assert st2["ledger"]["graded"] == 1
    r2 = _ledger_rows(tmp_path)[0]
    g = r2["tailored_grade"]
    assert g is not None
    assert {"fwd63", "mae63", "prox", "td_to_trough", "timing_label"}.issubset(g)
    assert g["grade_basis"] == pgs.FORWARD_BASIS
    assert g["execution_date"] > first
    assert isinstance(g["fwd63"], float)         # legacy ruler
    assert g["mae63"] <= 0                        # timing ruler: adverse excursion ≤0
    assert g["prox"] >= 0                         # entry premium over the ±31td low
    assert g["timing_label"] in ("confirmed_reset", "called_low", "early")
    assert r2["graded"] is True and r2["graded_asof"] == _after_day(full.index[-1])

    # idempotent: a later nightly does not re-advance an already-graded fire
    st3 = pgs.update(root=tmp_path, as_of=str(full.index[-1].date()))
    assert st3["ledger"]["grades_advanced_today"] == 0


def test_grade_gated_off_non_nightly(tmp_path, monkeypatch):
    """Grades never advance outside the nightly lane (sentinel off)."""
    _nightly(monkeypatch)
    full = _wobbly(600, 0)
    s = _trunc_to_fire(full, "3D", min_fwd=70)
    _write_close(tmp_path, "TAIL3D", s)
    _write_codex(tmp_path, [{"sym": "TAIL3D", "rung_derived": "3D"}])
    pgs.update(root=tmp_path, as_of="2026-07-25")     # nightly: fire appended, ungraded
    _write_close(tmp_path, "TAIL3D", full)            # forward tape now exists

    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    st = pgs.update(root=tmp_path, as_of="2026-08-01")  # non-nightly
    assert st["gate_open"] is False
    assert st["ledger"]["grades_advanced_today"] == 0
    assert _ledger_rows(tmp_path)[0]["graded"] is False


# ── flat-RSI NaN edge (reuse engine stoch — must not crash) ──────────────────
def test_flat_rsi_window_does_not_crash(tmp_path, monkeypatch):
    """A long flat-RSI stretch (hi==lo → NaN, not pd.NA) must not crash the scan.
    Reuses the shared engine stoch machinery via bars_for/tool_dates — the same
    NaN-not-crash guard as test_stoch_rsi_flat_rsi_window_is_nan_not_crash."""
    _nightly(monkeypatch)
    n = 240
    vals = [100.0 + (i % 2) for i in range(40)] + [100.5] * (n - 40)  # flat-RSI vector
    px = pd.Series(vals, index=pd.bdate_range("2019-01-01", periods=n))
    _write_close(tmp_path, "FLAT", px)
    _write_codex(tmp_path, [{"sym": "FLAT", "rung_derived": "1W"}])

    st = pgs.update(root=tmp_path, as_of="2026-07-25")   # must not raise
    assert st is not None
    assert st["coverage_census"]["covered"] == 1
    # flat RSI → no S-cross → 'neither'; nothing stored, no crash
    assert st["coverage_census"]["classes"]["neither"] == 1
    assert _ledger_rows(tmp_path) == []


# ── W-FRI tail edge: a 1W bar-date past the last daily close is not a fire ────
def test_wfri_tail_bar_never_stored_with_null_entry(tmp_path, monkeypatch):
    """The 1W (W-FRI) resample can label the last bar with a Friday that is past the
    last daily close (a Thursday-anchored week tail). Such a bar must NOT be reported
    as a fire — mirroring sig_metrics' `i >= len(idx): continue` — so no fire row is
    ever stored with an unresolvable (null) entry. Verified structurally: the scan
    completes and any stored fire carries a resolvable, in-bounds entry."""
    _nightly(monkeypatch)
    s = _trunc_to_fire(_wobbly(), "1W")
    assert s is not None
    # trim off the final Friday so the last 1W label lands past the last daily bar
    while s.index[-1].weekday() == 4:  # Friday
        s = s.iloc[:-1]
    _write_close(tmp_path, "WK", s)
    _write_codex(tmp_path, [{"sym": "WK", "rung_derived": "1W"}])

    st = pgs.update(root=tmp_path, as_of="2026-07-25")   # must not raise
    assert st is not None
    for r in _ledger_rows(tmp_path):
        for side in ("uniform", "tailored"):
            entry = r.get(f"{side}_entry")
            if entry is not None:  # every stored entry is resolvable + in-bounds
                assert isinstance(entry["entry_idx"], int)
                assert entry["entry_idx"] < len(s)


# ── fail-open without stores ─────────────────────────────────────────────────
def test_fail_open_without_codex(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    st = pgs.update(root=tmp_path, as_of="2026-07-25")
    assert st is not None
    assert st["coverage_census"]["codex_names"] == 0
    assert st["ledger"]["fire_rows"] == 0
    assert st["display_only"] is True and st["is_context_only"] is True


# ── W3 new source identity + prospective observation contract, issue #8718 ──
def test_second_publication_day_same_bar_does_not_append(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    s = _trunc_to_fire(_wobbly(), "3D")
    assert s is not None
    _write_close(tmp_path, "REPEAT", s)
    first = str(s.index[-1].date())
    _write_codex(tmp_path, [{"sym": "REPEAT", "rung_derived": "3D"}], as_of=first)
    assert pgs.update(root=tmp_path, as_of=first)["ledger"]["appended_today"] == 1
    second = str((pd.Timestamp(first) + pd.Timedelta(days=1)).date())
    assert pgs.update(root=tmp_path, as_of=second)["ledger"]["appended_today"] == 0
    assert len(_ledger_rows(tmp_path)) == 1
    assert _ledger_rows(tmp_path)[0]["grade_basis"] == pgs.FORWARD_BASIS


def test_genuine_second_completed_cross_is_new_source_identity(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    full = _wobbly(900)
    dates = tool_dates(bars_for(full, "3D"), "S")
    assert len(dates) >= 2
    s1 = full[full.index <= dates[-2]]
    s2 = full[full.index <= dates[-1]]
    _write_close(tmp_path, "TWOCROSSES", s1)
    first = str(s1.index[-1].date())
    _write_codex(tmp_path, [{"sym": "TWOCROSSES", "rung_derived": "3D"}], as_of=first)
    assert pgs.update(root=tmp_path, as_of=first)["ledger"]["appended_today"] == 1
    _write_close(tmp_path, "TWOCROSSES", s2)
    assert pgs.update(root=tmp_path, as_of=str(s2.index[-1].date()))[
        "ledger"]["appended_today"] == 1
    keys = [pgs._source_event_key(r, "tailored") for r in _ledger_rows(tmp_path)]
    assert len(keys) == 2 and len(set(keys)) == 2


def test_missed_first_close_capture_abstains_instead_of_backfill(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    full = _calendar_wobbly(700)
    s = _trunc_to_fire(full, "3D", min_fwd=75)
    assert s is not None and s.index[-1].year == 2026
    first = str(s.index[-1].date())
    _write_codex(tmp_path, [{"sym": "LATE", "rung_derived": "3D"}], as_of=first)
    _write_close(tmp_path, "LATE", s)
    pgs.update(root=tmp_path, as_of=first)
    _write_close(tmp_path, "LATE", full)
    state = pgs.update(root=tmp_path, as_of=str(full.index[-1].date()))
    row = _ledger_rows(tmp_path)[0]
    assert row["tailored_execution_skip"] == "missed_first_close_observation"
    assert row.get("tailored_execution") is None
    assert row["tailored_grade"] is None and not row["graded"]
    assert state["ledger"]["graded_prospective"] == 0


def test_codex_stamp_in_future_abstains(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    s = _trunc_to_fire(_wobbly(), "3D")
    _write_close(tmp_path, "FUTURE", s)
    now = str(s.index[-1].date())
    future = str((pd.Timestamp(now) + pd.Timedelta(days=5)).date())
    _write_codex(tmp_path, [{"sym": "FUTURE", "rung_derived": "3D"}], as_of=future)
    result = pgs.update(root=tmp_path, as_of=now)
    assert result["coverage_census"]["future_codex"] == 1
    assert result["ledger"]["appended_today"] == 0
    assert _ledger_rows(tmp_path) == []


def test_existing_v1_row_stays_byte_unchanged_and_excluded(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    folder = tmp_path / "personality_timing"
    folder.mkdir(parents=True)
    old = {"schema": LEDGER_SCHEMA, "as_of": "2026-07-26",
           "sym": "OLD", "codex_asof": "2026-07-25",
           "uniform_rung": "2W", "tailored_rung": "3D",
           "fired_uniform": False, "fired_tailored": True,
           "uniform_entry": None,
           "tailored_entry": {"entry_date": "2019-03-01", "entry_idx": 42, "entry_px": 90.0},
           "graded": False, "tailored_grade": None, "uniform_grade": None}
    path = folder / "gate_shadow.jsonl"
    path.write_text(json.dumps(old) + "\n")
    before = path.read_text()
    state = pgs.update(root=tmp_path, as_of="2026-10-09")
    assert path.read_text() == before
    assert state["ledger"]["legacy_rows"] == 1
    assert state["ledger"]["graded_prospective"] == 0
    assert state["timing"]["tailored"]["n_graded"] == 0


def test_recorded_next_close_price_is_not_rebased_at_grade(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    full = _calendar_wobbly(700)
    s = _trunc_to_fire(full, "3D", min_fwd=75)
    assert s is not None and s.index[-1].year == 2026
    first = str(s.index[-1].date())
    _write_codex(tmp_path, [{"sym": "FREEZE", "rung_derived": "3D"}], as_of=first)
    _write_close(tmp_path, "FREEZE", s)
    pgs.update(root=tmp_path, as_of=first)
    next_day = full.iloc[:len(s) + 1]
    _write_close(tmp_path, "FREEZE", next_day)
    pgs.update(root=tmp_path, as_of=_after_day(next_day.index[-1]))
    frozen = _ledger_rows(tmp_path)[0]["tailored_execution"]
    revised = full.copy()
    revised.iloc[len(s)] *= 1.10
    _write_close(tmp_path, "FREEZE", revised)
    state = pgs.update(root=tmp_path, as_of=_after_day(full.index[-1]))
    row = _ledger_rows(tmp_path)[0]
    assert row["tailored_execution"] == frozen
    assert row["tailored_grade"]["execution_price"] == frozen["entry_px"]
    assert state["ledger"]["graded_prospective"] == 1


# Exact observation/calendar regressions use synthetic stores only.
def _capture_row(sym="TEST", known="2026-08-03", source="2026-07-31"):
    return {
        "schema": LEDGER_SCHEMA, "as_of": known, "first_seen_asof": known,
        "grade_basis": pgs.FORWARD_BASIS, "sym": sym, "codex_asof": known,
        "uniform_rung": "2W", "tailored_rung": "3D",
        "fired_uniform": False, "fired_tailored": True,
        "uniform_entry": None,
        "tailored_entry": {"entry_date": source, "entry_idx": 0, "entry_px": 100.0},
        "graded": False, "graded_asof": None,
        "uniform_grade": None, "tailored_grade": None,
    }


def test_observation_future_tail_cannot_change_either_scanned_gate(tmp_path):
    full = _wobbly(700)
    prefix = _trunc_to_fire(full, "3D", min_fwd=80)
    assert prefix is not None
    observed = str(prefix.index[-1].date())
    future = full[full.index > prefix.index[-1]].copy()
    future.iloc[:] = np.where(np.arange(len(future)) % 2, 0.01, 1_000_000.0)
    for folder, prices in (("prefix", prefix), ("future", pd.concat([prefix, future]))):
        root = tmp_path / folder
        _write_close(root, "TEST", prices)
        _write_codex(root, [{"sym": "TEST", "rung_derived": "3D"}], as_of=observed)
    before = pgs._scan(tmp_path / "prefix", observed)
    after = pgs._scan(tmp_path / "future", observed)
    assert before[0] and before[1]["covered"] == 1
    assert after == before
    assert all(r["tailored_entry"]["entry_date"] <= observed for r in after[0]
               if r["tailored_entry"])


def test_observation_all_future_prices_are_not_covered(tmp_path):
    _write_close(tmp_path, "TEST", pd.Series([100.0, 101.0],
                  index=pd.to_datetime(["2026-08-04", "2026-08-05"])))
    _write_codex(tmp_path, [{"sym": "TEST", "rung_derived": "3D"}],
                 as_of="2026-08-03")
    fires, census = pgs._scan(tmp_path, "2026-08-03")
    assert fires == [] and census["covered"] == 0 and census["no_prices"] == 1


@pytest.mark.parametrize("kind", ["missing", "null"])
def test_expected_session_gap_never_slides_to_later_price(tmp_path, kind):
    prices = pd.Series([100.0, np.nan, 105.0],
                       index=pd.to_datetime(["2026-08-03", "2026-08-04", "2026-08-05"]))
    if kind == "missing":
        prices = prices.drop(pd.Timestamp("2026-08-04"))
    _write_close(tmp_path, "TEST", prices)
    row = _capture_row()
    pgs._grade_one(tmp_path, row, as_of="2026-08-06")
    assert row.get("tailored_execution") is None
    assert row.get("tailored_execution_skip") is None
    assert row["tailored_grade"] is None


def test_same_day_close_waits_for_observation_lower_bound(tmp_path):
    _write_close(tmp_path, "TEST", pd.Series([100.0, 101.0],
                 index=pd.to_datetime(["2026-08-03", "2026-08-04"])))
    row = _capture_row()
    assert not pgs._grade_one(tmp_path, row, as_of="2026-08-04")
    assert row.get("tailored_execution") is None
    assert pgs._grade_one(tmp_path, row, as_of="2026-08-05")
    mark = row["tailored_execution"]
    assert mark["entry_date"] == "2026-08-04"
    assert mark["captured_asof"] == "2026-08-05"
    assert mark["completed_through"] == "2026-08-04"
    assert mark["observation_clock"] == "as_of_date_utc_midnight_lower_bound/v1"
    assert row["graded"] is False and row["graded_asof"] is None


def test_actual_holiday_is_skipped_even_if_a_price_row_exists(tmp_path):
    # US Memorial Day 2026 is Monday May25, independently of observed rows.
    row = _capture_row(known="2026-05-22", source="2026-05-22")
    _write_close(tmp_path, "TEST", pd.Series([1.0, 101.0],
                 index=pd.to_datetime(["2026-05-25", "2026-05-26"])))
    assert pgs._grade_one(tmp_path, row, as_of="2026-05-27")
    assert row["tailored_execution"]["entry_date"] == "2026-05-26"
    assert row["tailored_execution"]["entry_px"] == 101.0


@pytest.mark.parametrize("sym,market", [
    ("TEST", "us"), ("0700.HK", "hk"), ("600000.SS", "cn"), ("SHOP.TO", "ca"),
])
def test_capture_uses_the_existing_symbol_calendar(tmp_path, sym, market):
    row = _capture_row(sym=sym)
    _write_close(tmp_path, sym, pd.Series([101.0], index=pd.to_datetime(["2026-08-04"])))
    assert pgs._grade_one(tmp_path, row, as_of="2026-08-05")
    assert row["tailored_execution"]["market"] == market
    assert row["tailored_execution"]["entry_date"] == "2026-08-04"


@pytest.mark.parametrize("sym,known,now,reason", [
    ("VOD.L", "2026-08-03", "2026-08-05", "unsupported_cash_market"),
    ("BTC-USD", "2026-08-03", "2026-08-05", "unsupported_cash_market"),
    ("TEST", "2028-01-03", "2028-01-05", "unverified_cash_calendar"),
    ("SHOP.TO", "2026-12-31", "2027-01-05", "unverified_cash_calendar"),
])
def test_unknown_market_or_calendar_coverage_abstains(tmp_path, sym, known, now, reason):
    row = _capture_row(sym=sym, known=known, source=known)
    _write_close(tmp_path, sym, pd.Series([101.0], index=pd.to_datetime([_after_day(known)])))
    assert pgs._grade_one(tmp_path, row, as_of=now)
    assert row["tailored_execution_skip"] == reason
    assert row.get("tailored_execution") is None and row["tailored_grade"] is None


def test_verified_year_transition_uses_actual_new_year_holiday(tmp_path):
    row = _capture_row(known="2026-12-31", source="2026-12-31")
    _write_close(tmp_path, "TEST", pd.Series([1.0, 101.0],
                 index=pd.to_datetime(["2027-01-01", "2027-01-04"])))
    pgs._grade_one(tmp_path, row, as_of="2027-01-05")
    assert row["tailored_execution"]["entry_date"] == "2027-01-04"


@pytest.mark.parametrize("observed,accepted", [("2026-08-11", True), ("2026-08-12", False)])
def test_capture_deadline_records_actual_late_observation(tmp_path, observed, accepted):
    row = _capture_row()
    _write_close(tmp_path, "TEST", pd.Series([101.0], index=pd.to_datetime(["2026-08-04"])))
    assert pgs._grade_one(tmp_path, row, as_of=observed)
    if accepted:
        mark = row["tailored_execution"]
        assert mark["entry_date"] == "2026-08-04"
        assert mark["first_seen_asof"] == "2026-08-03"
        assert mark["captured_asof"] == observed
    else:
        assert row["tailored_execution_skip"] == "missed_first_close_observation"
        assert row.get("tailored_execution") is None


@pytest.mark.parametrize("no_prices", [False, True])
def test_missing_expected_row_cannot_extend_capture_deadline(tmp_path, no_prices):
    row = _capture_row()
    if not no_prices:
        _write_close(tmp_path, "TEST", pd.Series([105.0],
                     index=pd.to_datetime(["2026-08-10"])))
    pgs._grade_one(tmp_path, row, as_of="2026-08-12")
    assert row["tailored_execution_skip"] == "missed_first_close_observation"
    assert row.get("tailored_execution") is None


def test_capture_respects_latest_known_codex_and_marker(tmp_path):
    row = _capture_row(known="2026-08-03", source="2026-08-04")
    row["codex_asof"] = "2026-08-06"
    _write_close(tmp_path, "TEST", pd.Series([1.0, 2.0, 107.0],
                 index=pd.to_datetime(["2026-08-04", "2026-08-05", "2026-08-07"])))
    pgs._grade_one(tmp_path, row, as_of="2026-08-08")
    assert row["tailored_execution"]["entry_date"] == "2026-08-07"


def _grading_fixture():
    from lib.us_cash_calendar import sessions_between
    from datetime import date
    idx = pd.DatetimeIndex(sessions_between(date(2026, 6, 1), date(2026, 12, 30)))
    e = idx.get_loc(pd.Timestamp("2026-08-04"))
    prices = pd.Series(100.0, index=idx[:e + 65])
    prices.iloc[e + 3] = 80.0
    prices.iloc[e + 63] = 125.0
    prices.iloc[e + 64] = 999.0  # a later row must never replace the horizon
    row = _capture_row()
    row["tailored_execution"] = {
        "basis": pgs.FORWARD_BASIS, "first_seen_asof": "2026-08-03",
        "source_entry_date": "2026-07-31", "entry_date": "2026-08-04",
        "entry_idx": e, "entry_px": 100.0, "captured_asof": "2026-08-05",
        "market": "us", "observation_clock": "as_of_date_utc_midnight_lower_bound/v1",
        "completed_through": "2026-08-04",
    }
    return prices, row, e


def test_exact_completed_horizon_has_hand_computable_rulers(tmp_path):
    prices, row, e = _grading_fixture()
    _write_close(tmp_path, "TEST", prices)
    horizon = prices.index[e + 63]
    assert not pgs._grade_one(tmp_path, row, as_of=str(horizon.date()))
    assert pgs._grade_one(tmp_path, row, as_of=_after_day(horizon))
    grade = row["tailored_grade"]
    assert grade["fwd63"] == 25.0 and grade["mae63"] == -20.0
    assert grade["prox"] == 25.0 and grade["td_to_trough"] == 3
    assert grade["timing_label"] == "called_low"
    assert grade["execution_price"] == 100.0 and row["graded"] is True


@pytest.mark.parametrize("kind", ["missing", "null", "infinite", "endpoint_missing"])
def test_missing_horizon_session_never_shifts_to_available_row(tmp_path, kind):
    prices, row, e = _grading_fixture()
    when = prices.index[e + (63 if kind == "endpoint_missing" else 10)]
    if kind in {"missing", "endpoint_missing"}:
        prices = prices.drop(when)
    else:
        prices.loc[when] = np.nan if kind == "null" else np.inf
    _write_close(tmp_path, "TEST", prices)
    pgs._grade_one(tmp_path, row, as_of=_after_day(prices.index[-1]))
    assert row["tailored_grade"] is None and row["graded"] is False


def test_mixed_legacy_and_uncertified_values_survive_real_capture_rewrite(tmp_path, monkeypatch):
    _nightly(monkeypatch)
    legacy = _capture_row(sym="LEGACY")
    legacy.pop("grade_basis")
    legacy["graded"] = True
    legacy["tailored_grade"] = {"fwd63": 444.0, "timing_label": "early"}
    legacy["retained_payload"] = {"original": ["value", 1.0, None]}
    old_v1 = copy.deepcopy(legacy)
    old_v1["sym"] = "VONE"
    old_v1["grade_basis"] = "first_seen_next_session_close/v1"
    current = _capture_row()
    originals = copy.deepcopy([legacy, old_v1])
    path = pgs.ledger_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"))
                              for r in [legacy, old_v1, current]) + "\n")
    _write_close(tmp_path, "TEST", pd.Series([101.0], index=pd.to_datetime(["2026-08-04"])))
    state = pgs.update(root=tmp_path, as_of="2026-08-05")
    rows = _ledger_rows(tmp_path)
    assert rows[:2] == originals  # parsed values; incumbent writer may reformat
    assert rows[2]["tailored_execution"]["entry_date"] == "2026-08-04"
    assert rows[2]["graded_asof"] is None
    assert state["ledger"]["legacy_rows"] == 2
    assert state["ledger"]["legacy_graded_excluded"] == 2
    assert state["ledger"]["prospective_rows"] == 1
    assert state["ledger"]["graded_prospective"] == 0
    assert state["ledger"]["grades_advanced_today"] == 0
    assert state["timing"]["tailored"]["n_graded"] == 0


def test_legacy_event_identity_remains_reserved_for_each_side():
    old = _capture_row()
    old["grade_basis"] = "first_seen_next_session_close/v1"
    old["fired_uniform"], old["fired_tailored"] = True, False
    old["uniform_entry"] = old.pop("tailored_entry")
    old["tailored_entry"] = None
    new = _capture_row(known="2026-08-04", source="2026-08-03")
    new["fired_uniform"] = True
    new["uniform_entry"] = copy.deepcopy(old["uniform_entry"])
    fresh = pgs._unique_new_fires([new], [old])
    assert len(fresh) == 1 and fresh[0]["fired_tailored"]
    assert not fresh[0]["fired_uniform"] and fresh[0]["uniform_entry"] is None
    assert fresh[0]["disagreement_class"] == "fired_tailored_only"
    assert pgs._unique_new_fires([new], [old, *fresh]) == []


def test_same_day_second_comparator_is_deferred_with_truthful_first_seen():
    first = _capture_row()
    second = copy.deepcopy(first)
    second["fired_tailored"] = False
    second["tailored_entry"] = None
    second["fired_uniform"] = True
    second["uniform_entry"] = {"entry_date": "2026-08-03", "entry_idx": 1, "entry_px": 100.0}
    assert pgs._unique_new_fires([second], [first]) == []
    second["as_of"] = "2026-08-04"
    fresh = pgs._unique_new_fires([second], [first])
    assert len(fresh) == 1 and fresh[0]["first_seen_asof"] == "2026-08-04"
    assert fresh[0]["fired_uniform"] and not fresh[0]["fired_tailored"]


def test_non_nightly_blocks_an_otherwise_eligible_grade(tmp_path, monkeypatch):
    prices, row, _ = _grading_fixture()
    _write_close(tmp_path, "TEST", prices)
    path = pgs.ledger_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(row) + "\n")
    before = path.read_bytes()
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    observed = _after_day(prices.index[-1])
    state = pgs.update(root=tmp_path, as_of=observed)
    assert state["ledger"]["grades_advanced_today"] == 0
    assert path.read_bytes() == before
    _nightly(monkeypatch)
    state = pgs.update(root=tmp_path, as_of=observed)
    assert state["ledger"]["grades_advanced_today"] == 1
    assert _ledger_rows(tmp_path)[0]["tailored_grade"]["fwd63"] == 25.0


def test_actual_terminality_consumer_keeps_its_own_mixed_version_policy(tmp_path, monkeypatch):
    """Exercise actual ingestion/identity/I/O; frozen model scoring is a fixture."""
    from engine import personality_terminality_shadow as pts
    _nightly(monkeypatch)
    idx = pd.bdate_range(end="2026-08-07", periods=180)
    prices = pd.Series(100.0 + np.arange(len(idx)) / 10, index=idx)
    sources = [
        _capture_row(sym="LEGACY", known="2026-08-06", source="2026-08-03"),
        _capture_row(sym="VONE", known="2026-08-06", source="2026-08-04"),
        _capture_row(sym="VNEW", known="2026-08-06", source="2026-08-05"),
    ]
    sources[0].pop("grade_basis")
    sources[1]["grade_basis"] = "first_seen_next_session_close/v1"
    for row in sources:
        row["tailored_grade"] = {"fwd63": 999999.0}  # never consumer grade authority
        _write_close(tmp_path, row["sym"], prices)
    context = tmp_path / "yahoo"
    context.mkdir()
    pd.DataFrame({"close": prices}, index=idx).to_parquet(context / "SPY.parquet")
    artifact = {"manifest": {"train_end": "2022-12-31", "threshold": 0.5,
                             "target_coverage": 0.2}, "models": {}}
    monkeypatch.setattr(pts, "load_artifact", lambda root=None: artifact)
    monkeypatch.setattr(pts, "score_locator", lambda artifact, values: (0.1, 0.1, 0.1))
    path = pgs.ledger_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(sources[0]) + "\n")
    first = pts.update(root=tmp_path, as_of="2026-08-07")
    assert first["ledger"]["appended_today"] == 1
    uniform_only = _capture_row(sym="UNIONLY")
    uniform_only.update(fired_tailored=False, tailored_entry=None, fired_uniform=True,
                        uniform_entry={"entry_date": "2026-08-05", "entry_px": 100.0})
    path.write_text("\n".join(json.dumps(r) for r in
                    [*sources, copy.deepcopy(sources[2]), uniform_only]) + "\n")
    before = path.read_bytes()
    state = pts.update(root=tmp_path, as_of="2026-08-08")
    rows = pts._load_jsonl(pts.ledger_path(tmp_path))
    assert state["ledger"]["appended_today"] == 2
    assert state["ledger"]["incumbent_events"] == 3
    assert len({pts._event_key(r) for r in rows}) == 3
    assert {r["sym"] for r in rows} == {"LEGACY", "VONE", "VNEW"}
    for row in rows:
        assert row["model_id"] == pts.MODEL_ID
        assert row["authority"] == "shadow_only" and row["display_only"]
        assert row["source_as_of"] == "2026-08-06"
        assert row["prospective_from"] == "2026-08-07"
        assert row["observed_as_of"] == ("2026-08-07" if row["sym"] == "LEGACY" else "2026-08-08")
        assert row["incumbent_grade"] is None
    assert path.read_bytes() == before
    assert not state["may_rank"] and not state["may_size"] and not state["may_alert"]
    assert pts.update(root=tmp_path, as_of="2026-08-08")["ledger"]["appended_today"] == 0
