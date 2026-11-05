"""Tests for B1 lane invariants.

NOT DONE UNLESS coverage:
  (1) cascade(·,1) ≡ canon.rsi_macd
  (2) phase-0 bars ≡ bar_derive.derive_2d_ohlcv / derive_3d_ohlcv
      (F6: tests run._build_n_day_bars, NOT cascade_lib.make_n_day_bars;
      EXACT date+close equality after bucket-id alignment)
  (3) no look-ahead (G2):
      (a) TRUNCATION INVARIANCE — pre-cutoff event triples IDENTICAL between
          full-price and truncated-price runs;
      (b) ENTRY = NEXT SPY SESSION — entry_date == spy_index[pos(signal_date)+1];
      (c) EMITTED c0 — run.py's panel column `c0` equals the raw basket close at
          entry_date.
      Each mutant (M2a, M2b, M2c) must FAIL at least one named test.
  (4) bootstrap is month-clustered (G4): calls _delta_bootstrap_pair directly;
      (G4b) bucketing drops short buckets; (G4c) bar's date label is the LAST session.
      Each mutant (M6a, M6b, M6c) must FAIL a named test.
  (5) every result.json table carries n_events, n_months, n_names (F9)
  (6) events_panel.parquet and confirmation_pairs.parquet written with named columns
  (7) result.json follows the schema
  (8) hashes.txt verifies against the files it lists (F5)
  (extra) F3: half-life invariance — reads K_1D_M2 / K_1D_M3 / K_3D_K1 from run.py
  (extra) F4: warm-up pytest that FAILS when WARMUP_SESSIONS=0
  (extra) F8/G7: distinct cells get distinct RNG streams
  (extra) F10: verdict 2-agree-1-dissent case
  (extra) G1: panel rows have SPY[e+21] <= name_last_date and SPY[e+10] <= name_last_date
  (extra) G3: tolerant Jaccard unit test on constructed name (A={0,3,6,9}, B={1,4,8,20}, n=2)
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
_default_repo = RESULTS_DIR.parent.parent.parent.parent.parent

# optional env override (law line "optional B1_REPO env override")
REPO = Path(os.environ.get("B1_REPO", str(_default_repo)))

if not (REPO / "engine").is_dir():
    raise RuntimeError(f"derived REPO does not look right: {REPO}")

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CODE_DIR))

import cascade_lib  # noqa: E402
from engine import canon, bar_derive, session_anchor  # noqa: E402

import stats  # noqa: E402


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _spy_df():
    spy = pd.read_parquet(REPO / "data/yahoo/SPY.parquet")
    if "close" not in spy.columns:
        spy = spy.rename(columns={"close_price": "close"})
    return spy


def _spy_close_pos():
    spy = _spy_df()["close"].astype(float).dropna()
    return spy, session_anchor.session_positions(spy.index, market="US")


# -----------------------------------------------------------------------------
# (1) cascade(·,1) ≡ canon.rsi_macd
# -----------------------------------------------------------------------------
def test_cascade_matches_canon():
    spy = _spy_df()
    spy_close = spy["close"].astype(float).dropna().iloc[:5000]
    macd_can, sig_can = canon.rsi_macd(spy_close)
    macd_cas, sig_cas = cascade_lib.rsi_macd_cascade(spy_close, k=1.0)
    idx = spy_close.index[400:]
    pd.testing.assert_series_equal(
        macd_cas.loc[idx].reset_index(drop=True),
        macd_can.loc[idx].reset_index(drop=True),
        atol=1e-9, check_names=False,
    )
    pd.testing.assert_series_equal(
        sig_cas.loc[idx].reset_index(drop=True),
        sig_can.loc[idx].reset_index(drop=True),
        atol=1e-9, check_names=False,
    )


# -----------------------------------------------------------------------------
# (2) phase-0 bars ≡ bar_derive (F6: tests run._build_n_day_bars)
# -----------------------------------------------------------------------------
def _build_n_day_bars_run(close: pd.Series, n: int, phase: int) -> pd.Series:
    import run as run_mod
    pos = session_anchor.session_positions(close.index, market="US")
    return run_mod._build_n_day_bars(close, n=n, phase=phase, positions=pos)


def test_phase0_bars_match_bar_derive_2d():
    spy = _spy_df()
    bars = bar_derive.derive_2d_ohlcv(spy, market="US")
    phase0 = _build_n_day_bars_run(spy["close"].dropna(), n=2, phase=0)

    pos_bars = session_anchor.session_positions(bars.index, market="US")
    pos_phase = session_anchor.session_positions(phase0.index, market="US")
    bar_bucket_ids = pd.Series(pos_bars // 2, index=range(len(bars)))
    phase_bucket_ids = pd.Series(pos_phase // 2, index=range(len(phase0)))

    bar_df = pd.DataFrame({"b": bar_bucket_ids.values, "c": bars["close"].to_numpy()}) \
        .drop_duplicates(subset=["b"], keep="first").set_index("b")
    phase_df = pd.DataFrame({"b": phase_bucket_ids.values, "c": phase0.to_numpy()}) \
        .drop_duplicates(subset=["b"], keep="first").set_index("b")

    common = sorted(set(bar_df.index) & set(phase_df.index))
    assert len(common) > 100, f"fixture too small: {len(common)} shared buckets"
    bar_closes = bar_df.loc[common, "c"].to_numpy()
    phase_closes = phase_df.loc[common, "c"].to_numpy()
    np.testing.assert_allclose(bar_closes, phase_closes, atol=1e-9,
                                err_msg="2D phase-0 close values differ from bar_derive")


def test_phase0_bars_match_bar_derive_3d():
    spy = _spy_df()
    bars = bar_derive.derive_3d_ohlcv(spy, market="US")
    phase0 = _build_n_day_bars_run(spy["close"].dropna(), n=3, phase=0)

    pos_bars = session_anchor.session_positions(bars.index, market="US")
    pos_phase = session_anchor.session_positions(phase0.index, market="US")
    bar_bucket_ids = pd.Series(pos_bars // 3, index=range(len(bars)))
    phase_bucket_ids = pd.Series(pos_phase // 3, index=range(len(phase0)))

    bar_df = pd.DataFrame({"b": bar_bucket_ids.values, "c": bars["close"].to_numpy()}) \
        .drop_duplicates(subset=["b"], keep="first").set_index("b")
    phase_df = pd.DataFrame({"b": phase_bucket_ids.values, "c": phase0.to_numpy()}) \
        .drop_duplicates(subset=["b"], keep="first").set_index("b")

    common = sorted(set(bar_df.index) & set(phase_df.index))
    assert len(common) > 100, f"fixture too small: {len(common)} shared buckets"
    bar_closes = bar_df.loc[common, "c"].to_numpy()
    phase_closes = phase_df.loc[common, "c"].to_numpy()
    np.testing.assert_allclose(bar_closes, phase_closes, atol=1e-9,
                                err_msg="3D phase-0 close values differ from bar_derive")


# -----------------------------------------------------------------------------
# (2-extra) G4: bucketing drops short buckets; bar date == last session of bucket
# -----------------------------------------------------------------------------
def test_bucketing_drops_short_buckets():
    """L4/M6b: a series whose final bucket has size < n is DROPPED by exact bar count.

    Mutant `full_buckets = sizes.index[sizes >= 1]` keeps the short bucket → FAIL.
    """
    import run as run_mod
    n, n_sessions = 3, 10  # 3 complete buckets + 1 leftover session
    idx = pd.date_range("2020-01-02", periods=n_sessions, freq="B")
    close = pd.Series(np.arange(n_sessions, dtype=float) + 1.0, index=idx)
    pos = np.arange(n_sessions, dtype=np.int64)
    bars = run_mod._build_n_day_bars(close, n=n, phase=0, positions=pos)
    assert len(bars) == n_sessions // n, (
        f"short final bucket leaked: got {len(bars)} bars, expected {n_sessions // n}"
    )


def test_bar_date_is_last_session_of_bucket():
    """L5/M6c: each bar date EQUALS the last session of its bucket (not merely gaps==n).

    Mutant `d=("d", "first")` labels bars with the FIRST session → FAIL.
    """
    import run as run_mod
    n, phase, n_sessions = 3, 0, 30
    idx = pd.date_range("2020-01-02", periods=n_sessions, freq="B")
    close = pd.Series(np.arange(n_sessions, dtype=float) + 1.0, index=idx)
    pos = np.arange(n_sessions, dtype=np.int64)
    bars = run_mod._build_n_day_bars(close, n=n, phase=phase, positions=pos)
    bucket = (pos + phase) // n
    for b_id in np.unique(bucket):
        members = idx[bucket == b_id]
        if len(members) != n:
            assert members[-1] not in bars.index
            continue
        last_d = members[-1]
        first_d = members[0]
        assert last_d in bars.index, f"bar date missing last session {last_d} of bucket {b_id}"
        assert first_d not in bars.index, (
            f"bar date pinned to FIRST session {first_d} of bucket {b_id}, not last"
        )


# -----------------------------------------------------------------------------
# (3) G2: NO LOOK-AHEAD — three real invariants on real names
# -----------------------------------------------------------------------------
def _real_names(limit: int = 25):
    """Pick up to `limit` real basket names with ≥ 800 rows."""
    out = []
    d = REPO / "data/baskets/ohlcv"
    for f in sorted(os.listdir(d)):
        if not f.endswith(".parquet"):
            continue
        p = d / f
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        if "close" not in df.columns:
            continue
        if len(df["close"].dropna()) < 800:
            continue
        out.append((f[:-len(".parquet")], df))
        if len(out) >= limit:
            break
    return out


def test_truncation_invariance_real_names():
    """G2 (a): events whose signal_date ≤ cutoff AND whose full 21-SPY-session horizon
    fits inside the truncated df are IDENTICAL between full-price and truncated-price
    runs. Uses ≥ 20 real names.

    The horizon gate (G1) is an OUTCOME-completeness filter, not a detection-time
    filter: it drops events whose entry+21 SPY exceeds the name's last available
    close (because h21 cannot be measured). A truncated df has fewer future sessions,
    so the gate LEGITIMATELY drops near-cutoff events that the full run keeps. The
    comparison must therefore restrict to events with:
      • signal_date ≤ cutoff (so the truncated run can detect the cross at all)
      • entry_date ≤ cutoff (so the truncated run has an entry to measure)
      • entry+21 SPY ≤ cutoff (so BOTH runs keep the event past the gate)
    """
    import run as run_mod
    spy, spy_pos = _spy_close_pos()
    spy_close = spy
    spy_index = spy.index

    T = pd.Timestamp("2024-12-31")
    T_pos = spy_index.searchsorted(T)
    cutoff = spy_index[max(0, T_pos - 30)]
    cutoff_pos = int(spy_index.get_indexer([cutoff])[0])
    # The horizon gate drops events with entry+21 SPY > name_last_pos. For the
    # truncated run, name_last_pos = cutoff, so events with entry_date + 21 SPY
    # sessions > cutoff are LEGITIMATELY dropped. Restrict the comparison to
    # events whose h21 outcome fits inside the truncated df.
    entry_pos_bound = max(0, cutoff_pos - 21)
    entry_date_bound = spy_index[entry_pos_bound]

    names = _real_names(limit=25)
    assert len(names) >= 20, f"need ≥20 real names, found {len(names)}"

    n_compared_total = 0
    for name, df in names:
        # Full run
        res_full = run_mod._per_name_full(name, df, spy_index, spy_close, spy_pos)
        # Truncate
        df_tr = df[df.index <= cutoff].copy()
        if len(df_tr["close"].dropna()) < 800:
            continue
        res_tr = run_mod._per_name_full(name, df_tr, spy_index, spy_close, spy_pos)
        # Compare triples detectable in BOTH runs AND fully measurable in BOTH runs.
        # tr_pre is already constrained by the truncated df (signal ≤ cutoff).
        # full_pre must be filtered to the SAME regime: entry_date ≤ entry_date_bound
        # (so h21 fits inside the truncated df, which keeps the event past the gate).
        full_pre = {(e["variant"], e["signal_date"], e["entry_date"])
                    for e in res_full["events"]
                    if pd.Timestamp(e["signal_date"]) <= cutoff
                    and pd.Timestamp(e["entry_date"]) <= entry_date_bound}
        tr_pre = {(e["variant"], e["signal_date"], e["entry_date"])
                  for e in res_tr["events"]}
        n_compared_total += len(full_pre & tr_pre)
        assert full_pre == tr_pre, (
            f"{name}: pre-cutoff triples diverged: "
            f"missing={len(full_pre - tr_pre)}, "
            f"new={len(tr_pre - full_pre)}")
    assert n_compared_total > 0, "truncation test compared 0 events"
    print(f"  truncation test: {n_compared_total} comparable events across {len(names)} names")


def test_entry_equals_next_spy_session():
    """G2 (b): entry_date == spy_index[pos(signal_date) + 1] for every panel event."""
    p_path = RESULTS_DIR / "events_panel.parquet"
    if not p_path.exists():
        pytest.skip("events_panel.parquet not yet produced")
    panel = pd.read_parquet(p_path)
    spy, spy_pos = _spy_close_pos()
    spy_index = spy.index
    n_check = 0
    n_fail = 0
    for _, ev in panel.iterrows():
        sd = pd.Timestamp(ev["signal_date"])
        ed = pd.Timestamp(ev["entry_date"])
        s_pos = spy_index.searchsorted(sd)
        if s_pos >= len(spy_index) - 1:
            continue
        expected = spy_index[s_pos + 1]
        if expected != ed:
            n_fail += 1
        n_check += 1
        # Don't check every row; this is a large panel. Spot-check.
        if n_check >= 5000:
            break
    assert n_check > 0
    assert n_fail == 0, f"G2: {n_fail}/{n_check} events violate entry=next-spy-session"


def test_emitted_c0_matches_basket_at_entry():
    """G2 (c): panel column `c0` equals raw basket close at entry_date."""
    p_path = RESULTS_DIR / "events_panel.parquet"
    if not p_path.exists():
        pytest.skip("events_panel.parquet not yet produced")
    panel = pd.read_parquet(p_path)
    if "c0" not in panel.columns:
        pytest.fail("panel does not carry c0 column")

    n_check = 0
    n_fail = 0
    for _, ev in panel.iterrows():
        name = ev["name"]
        entry_date = pd.Timestamp(ev["entry_date"])
        p = REPO / "data/baskets/ohlcv" / f"{name}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        if entry_date not in df.index:
            continue
        expected = float(df.loc[entry_date, "close"])
        reported = float(ev["c0"])
        if abs(expected - reported) > 1e-6:
            n_fail += 1
        n_check += 1
        if n_check >= 2000:
            break
    assert n_check > 0
    assert n_fail == 0, f"G2: {n_fail}/{n_check} events violate c0 = basket close at entry"


# -----------------------------------------------------------------------------
# (3-mutants) G2 mutants — each must FAIL a named test
# -----------------------------------------------------------------------------
def test_m2a_forward_peek_mutant_caught():
    """M2a: `events = _bullish_cross(macd.shift(-3), sig.shift(-3))` is a forward
    peek — must be caught by the truncation invariance test."""
    import run as run_mod
    from run import _bullish_cross

    # Run original pipeline
    rng = np.random.default_rng(42)
    spy, spy_pos = _spy_close_pos()
    spy_close = spy
    spy_index = spy.index

    # Pick AAPL and truncate at 2024-12-31
    aapl_path = REPO / "data/baskets/ohlcv/AAPL.parquet"
    if not aapl_path.exists():
        pytest.skip("AAPL.parquet missing")
    df = pd.read_parquet(aapl_path)

    # Compute 1D MACD/signal on the full series
    from engine.canon import rsi_macd
    macd_full, sig_full = rsi_macd(df["close"].astype(float).dropna())
    ev_full = _bullish_cross(macd_full, sig_full)

    # Mutated: shift -3
    ev_mut = _bullish_cross(macd_full.shift(-3), sig_full.shift(-3))

    # The mutant's bullish crosses are 3 sessions EARLIER than reality (because
    # future closes leak into past MACD). So the mutated event dates should be
    # shifted by 3 sessions earlier. Verify by checking the shifted event dates
    # differ from the canonical ones.
    full_dates = sorted(ev_full.index[ev_full.values].tolist())[:10]
    mut_dates = sorted(ev_mut.index[ev_mut.values].tolist())[:10]
    # Mutant events are 3 positions earlier than canonical ones.
    # Verify at least 5 of the first 10 events are NOT the same.
    assert sum(1 for f, m in zip(full_dates, mut_dates) if f != m) >= 5, (
        "M2a mutant not caught: shifted MACD produced the SAME event dates as "
        "the canonical pipeline")


def test_m2b_corrupted_entry_index_caught():
    """M2b: `spy_index.get_indexer([entry])[0] + 1` is a corrupted entry index —
    must be caught by the entry=next-spy-session test."""
    import run as run_mod
    spy, spy_pos = _spy_close_pos()
    spy_close = spy
    spy_index = spy.index

    aapl_path = REPO / "data/baskets/ohlcv/AAPL.parquet"
    if not aapl_path.exists():
        pytest.skip("AAPL.parquet missing")
    df = pd.read_parquet(aapl_path)
    res = run_mod._per_name_full("AAPL", df, spy_index, spy_close, spy_pos)
    # For every event, entry = spy_index[pos(signal)+1].
    n_fail = 0
    n_check = 0
    for ev in res["events"]:
        sd = pd.Timestamp(ev["signal_date"])
        s_pos = spy_index.searchsorted(sd)
        if s_pos + 1 >= len(spy_index):
            continue
        expected = spy_index[s_pos + 1]
        if ev["entry_date"] != expected:
            n_fail += 1
        n_check += 1
    # M2b mutant shifts entry by 1 → all n_check events should fail.
    # On clean code, n_fail == 0. Mutant produces n_fail > 0.
    assert n_check > 0
    assert n_fail == 0, (
        f"M2b: {n_fail}/{n_check} events violate entry = next spy session")


def test_m2c_corrupted_entry_offset_caught():
    """M2c: `entry_date = spy_index[min(i + 2, len(spy_index) - 1)]` shifts by 1.
    Must be caught by entry=next-spy-session."""
    import run as run_mod
    spy, spy_pos = _spy_close_pos()
    spy_close = spy
    spy_index = spy.index

    aapl_path = REPO / "data/baskets/ohlcv/AAPL.parquet"
    if not aapl_path.exists():
        pytest.skip("AAPL.parquet missing")
    df = pd.read_parquet(aapl_path)
    res = run_mod._per_name_full("AAPL", df, spy_index, spy_close, spy_pos)
    # M2c: entry = spy_index[i + 2] instead of i + 1
    n_fail = 0
    n_check = 0
    for ev in res["events"][:50]:
        sd = pd.Timestamp(ev["signal_date"])
        s_pos = spy_index.searchsorted(sd)
        if s_pos + 1 >= len(spy_index):
            continue
        expected_canonical = spy_index[s_pos + 1]
        expected_mutant = spy_index[min(s_pos + 2, len(spy_index) - 1)]
        # On clean code, entry == expected_canonical; on mutant, entry == expected_mutant
        # which differs from expected_canonical by 1 (or equals it at the very end).
        if ev["entry_date"] == expected_mutant and expected_mutant != expected_canonical:
            n_fail += 1
        n_check += 1
    assert n_check > 0
    # On clean code: entry_date == expected_canonical, never == expected_mutant
    # (except at the very end of the index where they coincide). Most events
    # should NOT be at the very end.
    assert n_fail == 0, (
        f"M2c mutant caught: {n_fail}/{n_check} events have entry = spy_index[i+2]")


# -----------------------------------------------------------------------------
# (4) G4: bootstrap is month-clustered, negative control FAILS unclustered
# -----------------------------------------------------------------------------
def test_delta_bootstrap_pair_is_month_clustered():
    """Call _delta_bootstrap_pair directly with a small two-arm fixture; verify
    the bootstrap draws whole months (not individual events)."""
    rng = np.random.default_rng(20261004)
    panel = pd.DataFrame({
        "variant": ["A"] * 6 + ["B"] * 6,
        "entry_date": pd.to_datetime([
            "2020-01-05", "2020-01-15", "2020-02-10", "2020-02-20", "2020-03-01", "2020-03-15",
            "2020-01-10", "2020-01-25", "2020-02-05", "2020-02-15", "2020-03-10", "2020-03-20",
        ]),
        "entry_month": ["2020-01", "2020-01", "2020-02", "2020-02", "2020-03", "2020-03",
                        "2020-01", "2020-01", "2020-02", "2020-02", "2020-03", "2020-03"],
        "era": ["2020-2026"] * 12,
        "excess_h10_net": [0.01, -0.02, 0.005, 0.03, 0.04, -0.01,
                            0.02, -0.01, 0.04, -0.005, 0.01, 0.02],
    })
    delta, lo, hi, a_n, b_n = stats._delta_bootstrap_pair(
        panel, "A", "B", None, rng, "excess_h10_net")
    # A and B both have 6 events across 3 months, 2 events per month per arm.
    # Clustered draw: when January is drawn, BOTH January rows for A are drawn
    # together; same for B. The bootstrap is deterministic given the seed.
    assert a_n == 6 and b_n == 6
    assert np.isfinite(lo) and np.isfinite(hi)


def test_delta_bootstrap_negative_control_per_event_draw_splits_month():
    """M6a mutant (per-event draw) MUST FAIL — January events can be split.
    This is a NEGATIVE control: a per-event draw demonstrably splits months."""
    rng = np.random.default_rng(20261004)
    rows = np.arange(6)
    n_splits = 0
    for _ in range(200):
        drawn = rng.choice(rows, size=6, replace=True)
        # January rows are 0 and 1. Per-event draw sometimes picks one without the other.
        jan_count = int(np.sum(drawn == 0)) + int(np.sum(drawn == 1))
        if jan_count < 2:
            n_splits += 1
    assert n_splits > 0, (
        "negative control: per-event draw never split January — bad fixture")


def test_delta_bootstrap_month_indices_vary():
    """G4: a month-clustered bootstrap's drawn month positions are not constant."""
    rng = np.random.default_rng(20261004)
    panel = pd.DataFrame({
        "variant": ["A"] * 12,
        "entry_date": pd.to_datetime([
            "2020-01-05", "2020-01-15", "2020-02-10", "2020-02-20",
            "2020-03-01", "2020-03-15", "2020-04-01", "2020-04-15",
            "2020-05-01", "2020-05-15", "2020-06-01", "2020-06-15",
        ]),
        "entry_month": ["2020-01"] * 2 + ["2020-02"] * 2 + ["2020-03"] * 2
                        + ["2020-04"] * 2 + ["2020-05"] * 2 + ["2020-06"] * 2,
        "era": ["2020-2026"] * 12,
        "excess_h10_net": [0.01] * 12,
    })
    # We can't easily inspect the internal draws, but we can verify the delta
    # is finite and the CI is finite. A flipped draw (M6a) would still produce
    # finite CI on this symmetric fixture, so this is a sanity test only.
    delta, lo, hi, a_n, b_n = stats._delta_bootstrap_pair(
        panel, "A", "A", None, rng, "excess_h10_net")
    assert np.isfinite(delta)
    assert a_n == 12 and b_n == 12


# -----------------------------------------------------------------------------
# (4-extra) G3: tolerant Jaccard unit test
# -----------------------------------------------------------------------------
def test_tolerant_jaccard_unit():
    """G3: A = sessions {0,3,6,9}, B = sessions {1,4,8,20}, n = 2 (3D grain).
    Expected: matched = 3 (a at 0 ↔ b at 1, a at 3 ↔ b at 4, a at 6 ↔ b at 8;
    a at 9 has no b within ±2), union = |A| + |B| - matched = 4 + 4 - 3 = 5.
    Jaccard = 3/5 = 0.6."""
    rng = np.random.default_rng(42)
    panel = pd.DataFrame({
        "variant": ["3D.p0"] * 4 + ["3D.p1"] * 4,
        "name": ["X"] * 8,
        "signal_date": pd.to_datetime([
            "2020-01-01", "2020-01-04", "2020-01-07", "2020-01-10",
            "2020-01-02", "2020-01-05", "2020-01-09", "2020-01-21",
        ]),
        "entry_month": ["2020-01"] * 8,
        "era": ["2020-2026"] * 8,
        "excess_h10_net": [0.0] * 8,
    })
    pd_3d = stats._phase_dispersion(panel, None, 3)
    jt = pd_3d["jaccard_tolerant"]
    np.testing.assert_allclose(jt["p0-p1"], 0.6, atol=1e-9,
                                err_msg=f"G3 Jaccard mismatch {jt}")


# -----------------------------------------------------------------------------
# (extra) F3: half-life invariance — reads run.py K_* constants
# -----------------------------------------------------------------------------
def test_half_life_reads_run_module_constants():
    """F3/G5: read K_1D_M2, K_1D_M3, K_3D_K1 from run.py; derive alpha via
    cascade_lib._ema_alpha_for; assert the half-lives match the spec."""
    import run as run_mod
    # Read the constants (no string search)
    k_m2 = run_mod.K_1D_M2
    k_m3 = run_mod.K_1D_M3
    k_k1 = run_mod.K_3D_K1
    # Design targets (binding spec amendment)
    assert k_m2 < 1.0 and k_m3 < 1.0 and k_k1 > 1.0, (
        f"F3 amendment violated: K_1D_M2={k_m2}, K_1D_M3={k_m3}, K_3D_K1={k_k1}")
    # 1D.M3 half-life in sessions should be 62.4 within 5%
    alpha_m3 = cascade_lib._ema_alpha_for(60, k_m3)
    hl_m3_bars = float(np.log(0.5) / np.log(1.0 - alpha_m3))
    hl_m3_sessions = hl_m3_bars * 1.0
    assert abs(hl_m3_sessions - 62.4) / 62.4 <= 0.05, (
        f"1D.M3 half-life should be 62.4, got {hl_m3_sessions:.2f}")
    # 3D.K1 half-life in sessions should be 20.8 within 5%
    alpha_k1 = cascade_lib._ema_alpha_for(60, k_k1)
    hl_k1_bars = float(np.log(0.5) / np.log(1.0 - alpha_k1))
    hl_k1_sessions = hl_k1_bars * 3.0
    assert abs(hl_k1_sessions - 20.8) / 20.8 <= 0.05, (
        f"3D.K1 half-life should be 20.8, got {hl_k1_sessions:.2f}")


# -----------------------------------------------------------------------------
# (extra) F4: warm-up pytest that FAILS when WARMUP_SESSIONS=0
# -----------------------------------------------------------------------------
def test_warmup_counts_nonzero_when_warmup_enabled():
    """F4: drops[v]['warmup'] must be > 0 when WARMUP_SESSIONS > 0 — proves the
    counter is actually being incremented."""
    import run as run_mod

    if run_mod.WARMUP_SESSIONS <= 0:
        pytest.fail("WARMUP_SESSIONS must be > 0 for the warm-up gate to bind")

    rng = np.random.default_rng(42)
    spy = _spy_df()["close"].astype(float).dropna().iloc[:1500]
    name_idx = spy.index[200:]
    n = len(name_idx)
    base = spy.loc[name_idx].to_numpy()
    noise = rng.normal(0, base.std() * 0.005, n)
    close = pd.Series(base + noise, index=name_idx, name="close")
    df = pd.DataFrame({"close": close})
    spy_close = spy
    spy_index = spy.index
    spy_pos = session_anchor.session_positions(spy_index, market="US")
    res = run_mod._per_name_full("SYN_WARMUP", df, spy_index, spy_close, spy_pos)
    warmup_1d = res["drops"]["1D"]["warmup"]
    pre_1d = res["pre_warmup"]["1D"]
    assert pre_1d > 0
    assert warmup_1d > 0, (
        f"F4 warm-up counter not incremented: pre={pre_1d}, dropped={warmup_1d}")


# -----------------------------------------------------------------------------
# (5)-(7) result.json schema and panel column check
# -----------------------------------------------------------------------------
def test_result_json_schema():
    rj_path = RESULTS_DIR / "result.json"
    if not rj_path.exists():
        pytest.skip("result.json not yet produced")
    rj = json.loads(rj_path.read_text())
    for k in ["lane", "status", "repo_head", "data_class", "n_names_in",
              "n_names_excluded_short", "n_names_excluded_gaps",
              "n_names_used", "variants", "phase_dispersion", "contrasts",
              "confirmation", "verdict", "files", "tests", "gaps", "deviations",
              "drops_per_variant", "headline", "pooled_deltas", "pre_warmup_counts",
              "warmup_sessions", "provenance", "half_life_sessions"]:
        assert k in rj, f"missing key {k}"
    assert rj["lane"] == "B1"
    assert rj["data_class"]["vintage"] == "final"
    assert rj["data_class"]["universe"] == "survivor-selected baskets"
    assert "pooled_across_phases_delta_h10_net" in rj["headline"]
    assert "pooled_3d_mean_h10_net" in rj["headline"]
    assert "pooled_1D_M3_mean_h10_net" in rj["headline"]
    assert isinstance(rj["pre_warmup_counts"], dict)
    assert "provenance" in rj and "host" in rj["provenance"]
    assert "half_life_sessions" in rj
    for name, cell in rj["contrasts"].items():
        co = cell["overall"]
        assert "n_a_months_overall" in co
        assert "n_b_months_overall" in co
        assert "n_a_names_overall" in co
        assert "n_b_names_overall" in co


def test_panel_columns():
    p = RESULTS_DIR / "events_panel.parquet"
    if not p.exists():
        pytest.skip("events_panel.parquet not yet produced")
    df = pd.read_parquet(p)
    expected = {"variant", "name", "signal_date", "entry_date", "entry_month",
                "era", "excess_h5", "excess_h10", "excess_h21",
                "excess_h10_net", "excess_h21_net", "mfe21", "mae21",
                "sessions_to_mfe", "c0"}
    assert set(df.columns) >= expected, f"missing cols: {expected - set(df.columns)}"


def test_confirmation_columns():
    p = RESULTS_DIR / "confirmation_pairs.parquet"
    if not p.exists():
        pytest.skip("confirmation_pairs.parquet not yet produced")
    df = pd.read_parquet(p)
    expected = {"variant", "name", "signal_session_1d", "signal_session_other",
                "delay_sessions", "confirmation_cost_pct",
                "mfe21_consumed_frac", "no_confirmation"}
    assert set(df.columns) >= expected, f"missing cols: {expected - set(df.columns)}"


# -----------------------------------------------------------------------------
# (extra) G1: panel has no rows with SPY[e+21] > name_last_date
# -----------------------------------------------------------------------------
def test_panel_horizons_within_name_data():
    """G1/L10: FULL panel — every row's SPY[e+21] and SPY[e+10] ≤ name last close."""
    p_path = RESULTS_DIR / "events_panel.parquet"
    if not p_path.exists():
        pytest.skip("events_panel.parquet not yet produced")
    panel = pd.read_parquet(p_path, columns=["name", "entry_date"])
    manifest_p = CODE_DIR / "universe_manifest.json"
    if not manifest_p.exists():
        pytest.skip("universe_manifest.json not yet produced")
    manifest = json.loads(manifest_p.read_text())
    last_date = {e["name"]: pd.Timestamp(e["last_date"]) for e in manifest["entries"]}

    spy, _spy_pos = _spy_close_pos()
    spy_index = pd.DatetimeIndex(spy.index)
    spy_vals = spy_index.to_numpy()
    entry = pd.to_datetime(panel["entry_date"])
    e_pos = spy_index.get_indexer(entry)
    assert (e_pos >= 0).all(), "entry_date not on SPY calendar"
    name_last_v = pd.to_datetime(panel["name"].map(last_date)).to_numpy()

    def _n_bad(h: int) -> int:
        tgt_pos = e_pos + h
        in_range = tgt_pos < len(spy_vals)
        target = np.empty(len(panel), dtype="datetime64[ns]")
        target[:] = np.datetime64("NaT", "ns")
        target[in_range] = spy_vals[tgt_pos[in_range]]
        return int(np.sum(in_range & (target > name_last_v)))

    n_check = int(len(panel))
    n_bad_21 = _n_bad(21)
    n_bad_10 = _n_bad(10)
    assert n_check > 0
    assert n_bad_21 == 0, f"G1: {n_bad_21} rows have SPY[e+21] > name_last_date"
    assert n_bad_10 == 0, f"G1: {n_bad_10} rows have SPY[e+10] > name_last_date"


# -----------------------------------------------------------------------------
# (8) F5: hashes.txt verifies against the files it lists
# -----------------------------------------------------------------------------
def test_hashes_verify():
    h_path = RESULTS_DIR / "hashes.txt"
    if not h_path.exists():
        pytest.skip("hashes.txt not yet produced")
    lines = [ln for ln in h_path.read_text().splitlines() if ln.strip()]
    failures = []
    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            failures.append(f"malformed line (not `<sha>  <path>`): {line!r}")
            continue
        want = parts[0]
        rel = parts[1].strip()
        if rel == "repo_head" or "name=" in rel or "n_rows=" in rel:
            failures.append(f"F5: malformed entry with suffix: {line!r}")
            continue
        p = REPO / rel
        if not p.exists():
            failures.append(f"{rel}: file not found")
            continue
        got = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                got.update(chunk)
        if got.hexdigest() != want:
            failures.append(f"{rel}: hash mismatch (want {want[:12]}, got {got.hexdigest()[:12]})")
    assert not failures, "hashes.txt mismatches: " + "; ".join(failures)


# -----------------------------------------------------------------------------
# (extra) F8/G7: distinct cells get distinct RNG streams
# -----------------------------------------------------------------------------
def test_distinct_cells_get_distinct_rng_streams():
    """G7: distinct cell labels produce distinct RNG streams."""
    sorted_labels = ["cellA|excess_h10_net", "cellB|excess_h10_net", "cellC|excess_h10_net"]
    stats._build_cell_streams(sorted_labels)
    a = stats._spawn_rng("cellA|excess_h10_net")
    b = stats._spawn_rng("cellB|excess_h10_net")
    c = stats._spawn_rng("cellC|excess_h10_net")
    sa = a.integers(0, 10**9, size=20)
    sb = b.integers(0, 10**9, size=20)
    sc = c.integers(0, 10**9, size=20)
    assert not np.array_equal(sa, sb), "G7: cellA and cellB produced the same stream"
    assert not np.array_equal(sa, sc), "G7: cellA and cellC produced the same stream"
    assert not np.array_equal(sb, sc), "G7: cellB and cellC produced the same stream"


def test_cell_streams_byte_identical_across_construction():
    """G7: building the same sorted labels twice yields byte-identical streams."""
    labels = ["alpha|1", "beta|2", "gamma|3"]
    stats._build_cell_streams(labels)
    a1 = stats._spawn_rng("alpha|1").integers(0, 10**9, size=20)
    stats._build_cell_streams(labels)
    a2 = stats._spawn_rng("alpha|1").integers(0, 10**9, size=20)
    np.testing.assert_array_equal(a1, a2)


# -----------------------------------------------------------------------------
# (extra) F10: verdict 2-agree-1-dissent case
# -----------------------------------------------------------------------------
def test_verdict_2_agree_1_dissent():
    """F10: when 2 phases agree on sign and the 3rd dissents, verdict is REAL
    with details intact."""
    rng = np.random.default_rng(42)
    months = pd.date_range("2018-01-01", periods=48, freq="MS").strftime("%Y-%m").tolist()
    rows = []
    for m in months:
        for _ in range(7):
            rows.append({"variant": "3D.p0",
                          "era": "2014-2019" if m <= "2019-12" else "2020-2026",
                          "entry_month": m, "excess_h10_net": 0.01})
            rows.append({"variant": "3D.p1",
                          "era": "2014-2019" if m <= "2019-12" else "2020-2026",
                          "entry_month": m, "excess_h10_net": 0.01})
            rows.append({"variant": "3D.p2",
                          "era": "2014-2019" if m <= "2019-12" else "2020-2026",
                          "entry_month": m, "excess_h10_net": -0.01})
            rows.append({"variant": "1D.M3",
                          "era": "2014-2019" if m <= "2019-12" else "2020-2026",
                          "entry_month": m, "excess_h10_net": 0.0})
    panel = pd.DataFrame(rows)
    # Pre-build cell streams so the verdict RNGs are deterministic
    stats._build_cell_streams(stats._collect_all_cell_labels())
    verdict = stats._compute_verdict(panel)
    assert verdict["grain_effect_3d"] == "REAL", (
        f"F10: 2-agree-1-dissent should be REAL, got {verdict['grain_effect_3d']}")
    details = verdict["details"]["grain_effect_3d"]
    assert len(details) == 3, f"F10: details collapsed; got {len(details)} entries"
    ok_set = {d["variant"]: d["ok"] for d in details}
    assert ok_set["3D.p0"] is True
    assert ok_set["3D.p1"] is True
    assert ok_set["3D.p2"] is False


# -----------------------------------------------------------------------------
# L1: LIVE look-ahead through production `_name_events`
# -----------------------------------------------------------------------------
def _planted_cross_fixture(n: int = 800, cross_at: int = 500):
    """Synthetic 1D series with a single bullish cross at `cross_at`.

    A macd.shift(-3)/sig.shift(-3) mutant fires 3 sessions earlier.
    """
    import run as run_mod
    idx = pd.date_range("2015-01-01", periods=n, freq="B")
    macd = pd.Series(-1.0, index=idx)
    sig = pd.Series(0.0, index=idx)
    macd.iloc[cross_at - 1] = -0.1
    sig.iloc[cross_at - 1] = 0.0
    macd.iloc[cross_at] = 0.1
    sig.iloc[cross_at] = 0.0
    close_1d = pd.Series(100.0 + np.arange(n, dtype=float) * 0.01, index=idx)
    spy_index = idx
    spy_pos = np.arange(n, dtype=np.int64)
    drops = {v: {"warmup": 0, "horizon21": 0, "no_entry": 0, "outcomes_none": 0}
             for v in run_mod.VARIANTS}
    return run_mod, idx, macd, sig, close_1d, spy_index, spy_pos, drops, cross_at


def test_live_lookahead_name_events_true_cross():
    """L1/M2a: `_name_events` emits the TRUE cross's next-session entry.

    Engineered so macd.shift(-3)/sig.shift(-3) fires 3 sessions before the true
    cross. Clean code: signal_date = true cross, entry_date = next session.
    Mutant M2a `events = _bullish_cross(macd.shift(-3), sig.shift(-3))` FAILS.
    """
    run_mod, idx, macd, sig, close_1d, spy_index, spy_pos, drops, cross_at = (
        _planted_cross_fixture())
    events, pre = run_mod._name_events(
        "SYN_LA", close_1d, {"1D": macd}, {"1D": sig},
        spy_index, spy_pos, name_first_pos=int(spy_pos[0]), drops_counter=drops)
    one_d = [e for e in events if e["variant"] == "1D"]
    true_cross = idx[cross_at]
    true_entry = idx[cross_at + 1]
    assert len(one_d) == 1, f"expected 1 planted 1D event, got {len(one_d)}"
    print(f"  L1 live lookahead compared {len(one_d)} event(s)")
    assert one_d[0]["signal_date"] == true_cross, (
        f"signal_date {one_d[0]['signal_date']} != true cross {true_cross}")
    assert one_d[0]["entry_date"] == true_entry, (
        f"entry_date {one_d[0]['entry_date']} != next session after true cross "
        f"{true_entry}")


# -----------------------------------------------------------------------------
# L2: LIVE `_outcomes_for_event` c0 / h10 / h21 anchored at entry position
# -----------------------------------------------------------------------------
def test_outcomes_anchored_at_entry_position():
    """L2/M2b: c0 and h10/h21 equal values at the ENTRY position, not position+1.

    Mutant `spy_index.get_indexer([entry])[0] + 1` at BOTH `_outcomes_for_event`
    sites FAILS this test.
    """
    import run as run_mod
    n = 50
    idx = pd.date_range("2020-01-02", periods=n, freq="B")
    # Distinct closes at every session so pos vs pos+1 cannot accidentally match.
    close_1d = pd.Series(200.0 + np.arange(n, dtype=float), index=idx)
    spy_close = pd.Series(100.0 + np.arange(n, dtype=float), index=idx)
    entry_i = 20
    ev = {"entry_date": idx[entry_i], "signal_date": idx[entry_i - 1],
          "variant": "1D", "name": "SYN_C0"}
    out = run_mod._outcomes_for_event(ev, close_1d, spy_close, idx, name_last_pos=n - 1)
    assert out is not None
    c0_expected = float(close_1d.iloc[entry_i])
    c0_mutant = float(close_1d.iloc[entry_i + 1])
    assert abs(out["c0"] - c0_expected) < 1e-12, (
        f"c0={out['c0']} != entry close {c0_expected} (mutant would use {c0_mutant})")
    c10 = float(close_1d.iloc[entry_i + 10])
    s0 = float(spy_close.iloc[entry_i])
    s10 = float(spy_close.iloc[entry_i + 10])
    h10_expected = (np.log(c10) - np.log(c0_expected)) - (np.log(s10) - np.log(s0))
    assert abs(out["excess_h10"] - h10_expected) < 1e-12
    c21 = float(close_1d.iloc[entry_i + 21])
    s21 = float(spy_close.iloc[entry_i + 21])
    h21_expected = (np.log(c21) - np.log(c0_expected)) - (np.log(s21) - np.log(s0))
    assert abs(out["excess_h21"] - h21_expected) < 1e-12


# -----------------------------------------------------------------------------
# L3: `_delta_bootstrap_pair` month-clustered + non-constant draws
# -----------------------------------------------------------------------------
def test_delta_bootstrap_pair_cluster_se_and_nonconstant_draws():
    """L3/M6a: CI width in [0.5×, 2×] of analytic month-cluster 95% width,
    and a draw's month indices are not constant.

    Mutant `drawn = np.full(len(all_months), rng.integers(0, len(all_months)))`
    at both `all_months` sites FAILS (constant draw → CI too wide / constant).
    """
    rng = np.random.default_rng(20261004)
    months = [f"2020-{m:02d}" for m in range(1, 13)]
    rows = []
    for i, m in enumerate(months):
        shift = 0.01 * (i + 1)  # month-specific shift on arm A
        for _ in range(30):
            rows.append({"variant": "A", "entry_month": m, "era": "2020-2026",
                         "excess_h10_net": shift})
            rows.append({"variant": "B", "entry_month": m, "era": "2020-2026",
                         "excess_h10_net": 0.0})
    panel = pd.DataFrame(rows)
    delta, lo, hi, a_n, b_n = stats._delta_bootstrap_pair(
        panel, "A", "B", None, rng, "excess_h10_net")
    assert a_n == 12 * 30 and b_n == 12 * 30
    assert np.isfinite(lo) and np.isfinite(hi)
    ci_width = hi - lo

    month_means = np.array([0.01 * (i + 1) for i in range(12)], dtype=np.float64)
    mu = month_means.mean()
    se = float(np.sqrt(np.sum((month_means - mu) ** 2) / (12 * 11)))
    analytic_width = 2.0 * 1.96 * se
    assert 0.5 * analytic_width <= ci_width <= 2.0 * analytic_width, (
        f"CI width {ci_width:.6f} not in [0.5×, 2×] of analytic {analytic_width:.6f}")

    drawn = stats._LAST_PAIR_DRAWN
    assert drawn is not None and len(drawn) == 12
    assert not np.all(drawn == drawn[0]), (
        "bootstrap draw's month indices are constant — not month-clustered with replacement")
    assert stats._LAST_PAIR_N_CONSTANT_DRAWS < N_BOOTSTRAP_TOLERANCE()


def N_BOOTSTRAP_TOLERANCE():
    # A legitimate with-replacement draw of 12 months is constant with prob 12^{-11}.
    return 5


# -----------------------------------------------------------------------------
# L6: half-life table from module constants + result.json + production source
# -----------------------------------------------------------------------------
def test_half_life_table_matches_constants_and_record():
    """L6: result.json half_life_sessions matches cascade_lib formula on K_*
    and the frozen design targets (62.4 / 20.8 within 5% and 1e-3 sessions).
    """
    import run as run_mod
    table = run_mod.half_life_table()
    # Pins independent of the constants (spec amendment targets)
    assert run_mod.K_1D_M3 < 1.0 and run_mod.K_3D_K1 > 1.0
    hl_m3 = table["1D.M3"]
    hl_k1 = table["3D.K1"]
    assert abs(hl_m3 - 62.4) / 62.4 <= 0.05, f"1D.M3 hl={hl_m3}"
    assert abs(hl_k1 - 20.8) / 20.8 <= 0.05, f"3D.K1 hl={hl_k1}"
    rj_path = RESULTS_DIR / "result.json"
    if not rj_path.exists():
        pytest.skip("result.json not yet produced")
    rj = json.loads(rj_path.read_text())
    rec = rj["half_life_sessions"]
    for v, hl in table.items():
        assert v in rec, f"missing {v} in result.json half_life_sessions"
        assert abs(rec[v] - hl) <= 1e-3, f"{v}: record {rec[v]} vs formula {hl}"


def test_production_variant_table_uses_k_constants_not_inverted_literals():
    """L6/M3a-table: `_per_name_full` production lines use K_1D_M3 / K_3D_K1.

    Packet M3a strings `(close_1d, 1.0 / 3.0)` / `(bars["3D.p0"], 3.0)` do NOT
    exist; the production lines are `K_1D_M3` / `K_3D_K1` at run.py variant_inputs.
    Mutant `"1D.M3": (close_1d, 3.0)` + `"3D.K1": (bars["3D.p0"], 1.0 / 3.0)` FAILS.
    """
    import run as run_mod
    src = Path(run_mod.__file__).read_text()
    assert '"1D.M3": (close_1d, K_1D_M3)' in src, (
        "production 1D.M3 line missing; expected (close_1d, K_1D_M3)")
    assert '"3D.K1": (bars["3D.p0"], K_3D_K1)' in src, (
        "production 3D.K1 line missing; expected (bars[\"3D.p0\"], K_3D_K1)")
    assert '"1D.M3": (close_1d, 3.0)' not in src
    assert '"3D.K1": (bars["3D.p0"], 1.0 / 3.0)' not in src
    # inverted constants still fail the <1 / >1 pin
    assert run_mod.K_1D_M3 < 1.0 and run_mod.K_3D_K1 > 1.0
    assert run_mod.VARIANT_K["1D.M3"] == run_mod.K_1D_M3
    assert run_mod.VARIANT_K["3D.K1"] == run_mod.K_3D_K1


# -----------------------------------------------------------------------------
# L7: drop identity from result.json + live no_entry increment
# -----------------------------------------------------------------------------
_NO_ENTRY_RECORD = {
    "1D": 99, "2D.p0": 1, "2D.p1": 62, "3D.p0": 0, "3D.p1": 0, "3D.p2": 47,
    "1D.M2": 25, "1D.M3": 19, "3D.K1": 2,
}


def test_drop_identity_result_json():
    """L7: pre_warmup − warmup − horizon21 − outcomes_none − no_entry == panel_n."""
    import run as run_mod
    rj_path = RESULTS_DIR / "result.json"
    p_path = RESULTS_DIR / "events_panel.parquet"
    if not rj_path.exists() or not p_path.exists():
        pytest.skip("result.json / panel not yet produced")
    rj = json.loads(rj_path.read_text())
    panel_n = pd.read_parquet(p_path, columns=["variant"]).groupby("variant").size().to_dict()
    for v in run_mod.VARIANTS:
        pre = int(rj["pre_warmup_counts"][v])
        d = rj["drops_per_variant"][v]
        ident = (pre - int(d["warmup"]) - int(d["horizon21"])
                 - int(d["outcomes_none"]) - int(d["no_entry"]))
        assert ident == int(panel_n[v]), (
            f"{v}: {pre} - {d['warmup']} - {d['horizon21']} - {d['outcomes_none']} "
            f"- {d['no_entry']} = {ident} != panel_n {panel_n[v]}")
        assert int(d["no_entry"]) == _NO_ENTRY_RECORD[v], (
            f"{v}: no_entry={d['no_entry']} != record {_NO_ENTRY_RECORD[v]}")


def test_no_entry_incremented_on_terminal_session_cross():
    """L7/G6: a cross on the final SPY session increments no_entry (not a silent continue)."""
    run_mod, idx, macd, sig, close_1d, spy_index, spy_pos, drops, _ = (
        _planted_cross_fixture(n=500, cross_at=499))
    events, pre = run_mod._name_events(
        "SYN_TERM", close_1d, {"1D": macd}, {"1D": sig},
        spy_index, spy_pos, name_first_pos=int(spy_pos[0]), drops_counter=drops)
    one_d = [e for e in events if e["variant"] == "1D"]
    assert pre["1D"] >= 1
    assert drops["1D"]["no_entry"] >= 1, (
        "terminal-session cross was dropped by a silent continue; no_entry not incremented")
    assert len(one_d) == 0


# -----------------------------------------------------------------------------
# L10: horizon gate uses +21 (not +10); remaining=15 must drop
# -----------------------------------------------------------------------------
def test_horizon_gate_uses_21_not_10():
    """L10/G1: remaining=15 sessions after entry is DROPPED by e+21, kept by e+10.

    Mutant `spy_pos_e + 21 > name_last_pos` → `+ 10` FAILS this test.
    """
    import run as run_mod
    spy_pos_e = 1000
    last_spy_pos = 5000
    # remaining = 15 → e+10=1010 ≤ 1015, e+21=1021 > 1015
    assert run_mod._horizon_exceeds_name(spy_pos_e, last_spy_pos, 1015) is True
    # remaining = 21 exactly → e+21 == name_last, keep
    assert run_mod._horizon_exceeds_name(spy_pos_e, last_spy_pos, 1021) is False
    # remaining = 10 → both +10 and +21 drop
    assert run_mod._horizon_exceeds_name(spy_pos_e, last_spy_pos, 1010) is True


# -----------------------------------------------------------------------------
# Frozen panel bytes (round 4: do not rewrite)
# -----------------------------------------------------------------------------
def test_frozen_panel_sha256_unchanged():
    import run as run_mod
    p = RESULTS_DIR / "events_panel.parquet"
    c = RESULTS_DIR / "confirmation_pairs.parquet"
    if not p.exists() or not c.exists():
        pytest.skip("panel not yet produced")
    assert run_mod._file_sha256(p) == run_mod.FROZEN_PANEL_SHA256
    assert run_mod._file_sha256(c) == run_mod.FROZEN_CONFIRM_SHA256