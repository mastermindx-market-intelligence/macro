"""P3 falsifier: backtest gate + forward-outcome ledger + radar auto-demote.

Run: .venv/bin/python -m tests.test_btc_impulse_falsifier
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import btc_impulse_radar_backtest as BT  # noqa: E402
from engine import btc_impulse_ledger as LED  # noqa: E402
from engine import btc_impulse_radar as R  # noqa: E402


def _sig_with_drops(n=480, seed=3):
    """Synthetic daily close with single-bar ~-8% drops at RANDOM (seeded)
    intervals. Single-bar (not 3-bar) so each crosses the label's -5% floor; and
    NON-periodic so a circular-shift permutation gives a clean p (a periodic
    schedule would re-align under shift and inflate the null)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    px = [60000.0]
    cooldown = 0
    while len(px) < n:
        if cooldown == 0 and rng.random() < 0.05:     # a single -8% shock bar
            px.append(px[-1] * 0.92); cooldown = 4
        else:
            px.append(px[-1] * 1.001); cooldown = max(0, cooldown - 1)
    return pd.DataFrame({"close": pd.Series(px[:n], index=idx)}, index=idx)


def _patch_fire_series(frame):
    """Patch the backtest's view of radar.fire_series to return `frame`."""
    orig = BT.radar.fire_series
    BT.radar.fire_series = lambda s=None: frame
    return orig


def test_labels_are_strictly_forward_provable_by_hand():
    """The label at t must be the min/max of closes STRICTLY in (t, t+H], provable
    on a handcrafted monotone series — NOT the old shift(-1).rolling(H) which
    reached back to close[t-1]/close[t]. This validates the label CONSTRUCTION
    directly, so it cannot be satisfied by the same contamination it guards."""
    H = BT.LABEL_H
    assert H == 3
    # Monotone-descending closes so every forward window has an unambiguous min.
    close = pd.Series(
        [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0],
        index=pd.date_range("2024-01-01", periods=8),
    )
    down, up = BT._labels(close)
    # Reconstruct fwd_min / fwd_max independently from the definition (t, t+H].
    for i in range(len(close)):
        window = close.iloc[i + 1: i + 1 + H]           # strictly forward, H bars
        if len(window) < H:                              # last H rows: no full future
            assert pd.isna(down.iloc[i]) and pd.isna(up.iloc[i]), (
                f"row {i} must be unknown, not a negative outcome")
            continue
        exp_down = (window.min() / close.iloc[i] - 1.0) <= -BT.LABEL_THR
        exp_up = (window.max() / close.iloc[i] - 1.0) >= BT.LABEL_THR
        assert bool(down.iloc[i]) == bool(exp_down), f"down mismatch at row {i}"
        assert bool(up.iloc[i]) == bool(exp_up), f"up mismatch at row {i}"


def test_labels_invariant_to_prior_bars():
    """Anti-overlap invariant: perturbing ONLY the prior bar close[t-1] must NOT
    change the label at t. The label legitimately depends on close[t] as the
    entry/reference base (forward return is measured from it) and on the closes
    in (t, t+H] — but it must never look BACKWARD. The OLD construction FAILS
    this because its shift(-1).rolling(H) window reached back to close[t-1]."""
    H = BT.LABEL_H
    rng = np.random.default_rng(11)
    base = pd.Series(
        60000.0 * np.cumprod(1 + rng.normal(0, 0.02, 200)),
        index=pd.date_range("2024-01-01", periods=200),
    )
    down0, up0 = BT._labels(base)
    # Only labels at rows t in [1, N-H-1] are testable: they have both a prior bar
    # and a full forward window.
    for t in range(1, len(base) - H):
        pert = base.copy()
        pert.iloc[t - 1] = base.iloc[t - 1] * 2.0     # slam ONLY the prior bar
        downp, upp = BT._labels(pert)
        assert bool(downp.iloc[t]) == bool(down0.iloc[t]), (
            f"down label at {t} changed when close[t-1] moved — backward leak!")
        assert bool(upp.iloc[t]) == bool(up0.iloc[t]), (
            f"up label at {t} changed when close[t-1] moved — backward leak!")


def test_old_buggy_construction_would_fail_the_invariant():
    """Guard-the-guard: the *old* shift(-1).rolling(H).min() construction MUST
    violate the prior-bar anti-overlap invariant (so we know the new test has
    teeth and isn't vacuously passing on any construction)."""
    H = BT.LABEL_H
    rng = np.random.default_rng(5)
    base = pd.Series(
        60000.0 * np.cumprod(1 + rng.normal(0, 0.03, 150)),
        index=pd.date_range("2024-01-01", periods=150),
    )

    def _old_labels(close):
        fwd_min = close.shift(-1).rolling(H).min()
        fwd_max = close.shift(-1).rolling(H).max()
        return (fwd_min / close - 1.0) <= -BT.LABEL_THR, (fwd_max / close - 1.0) >= BT.LABEL_THR

    down0, up0 = _old_labels(base)
    violated = False
    for t in range(1, len(base) - H):
        pert = base.copy()
        pert.iloc[t - 1] = base.iloc[t - 1] * 2.0     # slam ONLY the prior bar
        downp, upp = _old_labels(pert)
        if (bool(downp.iloc[t]) != bool(down0.iloc[t])
                or bool(upp.iloc[t]) != bool(up0.iloc[t])):
            violated = True
            break
    assert violated, "old construction should leak the prior bar — invariant has no teeth otherwise"


def test_validate_passes_when_leg_leads():
    sig = _sig_with_drops()
    close = sig["close"]
    down, _ = BT._labels(close)
    # d2 fires exactly on the pre-drop down-event bars (a perfect leader)
    d2 = down.fillna(False).copy()
    fires = pd.DataFrame({"d2": d2}, index=sig.index)
    orig = _patch_fire_series(fires)
    try:
        v = BT.validate(sig)
    finally:
        BT.radar.fire_series = orig
    assert v["ok"] and v["legs"]["d2"]["status"] == "leading"
    assert v["legs"]["d2"]["lift_holdout"] >= 1.5
    assert v["legs"]["d2"]["perm_p"] <= 0.05


def test_validate_fails_when_leg_stops_leading():
    sig = _sig_with_drops()
    rng = np.random.default_rng(7)
    # fires RANDOM / independent of the drops -> lift ~1 < floor -> demoted
    d2 = pd.Series(rng.random(len(sig)) < 0.12, index=sig.index)
    fires = pd.DataFrame({"d2": d2}, index=sig.index)
    orig = _patch_fire_series(fires)
    try:
        v = BT.validate(sig)
    finally:
        BT.radar.fire_series = orig
    assert v["ok"] and v["all_pass"] is False
    assert v["legs"]["d2"]["status"] == "demoted"


def test_validate_marks_thin_but_leading_leg_insufficient_n():
    """A leg whose edge clears its floor+p but has < MIN_HOLDOUT_N holdout fires
    must be 'insufficient_n' (watch), NOT 'leading' — u1 (14 fires) is exactly
    this case. It is a non-pass and the radar zeroes its act points."""
    sig = _sig_with_drops()
    down, _ = BT._labels(sig["close"])
    # Perfect leader (fires on the down-event bars) but THINNED to < MIN_HOLDOUT_N
    # holdout fires so the edge is real yet the sample is inadequate.
    holdout_mask = sig.index >= pd.Timestamp(BT.HOLDOUT_START)
    d2 = down.fillna(False).copy()
    fire_pos = [i for i in range(len(d2)) if bool(d2.iloc[i]) and holdout_mask[i]]
    keep = set(fire_pos[: max(0, BT.MIN_HOLDOUT_N - 5)])   # keep only a few holdout fires
    thin = d2.copy()
    for i in fire_pos:
        if i not in keep:
            thin.iloc[i] = False
    fires = pd.DataFrame({"d2": thin}, index=sig.index)
    orig = _patch_fire_series(fires)
    try:
        v = BT.validate(sig)
    finally:
        BT.radar.fire_series = orig
    leg = v["legs"]["d2"]
    assert leg["n_fires_holdout"] < BT.MIN_HOLDOUT_N
    assert leg["status"] == "insufficient_n"
    assert leg["pass"] is False
    assert v["all_pass"] is False


def test_radar_zeroes_insufficient_n_leg():
    """The radar must zero act points for an 'insufficient_n' leg, same as
    'demoted' — a thin sample cannot award act-tier weight."""
    import engine.btc_impulse_radar_backtest as bt
    orig = bt.load_gate
    bt.load_gate = lambda: {"legs": {"d2": {"status": "leading"},
                                     "d3": {"status": "leading"},
                                     "u1": {"status": "insufficient_n"}}}
    try:
        out = R.compute()
    finally:
        bt.load_gate = orig
    if not out.get("ok"):
        return
    u1 = next(l for l in out["up"]["legs"] if l["key"] == "u1_sopr")
    assert u1["demoted"] is True and u1["points"] == 0.0


def test_main_exit_code_reflects_pass(monkeypatch_free=True):
    """main() returns 1 when an act leg fails, 0 when all lead (smoke)."""
    sig = _sig_with_drops()
    rng = np.random.default_rng(1)
    fires = pd.DataFrame({"d2": pd.Series(rng.random(len(sig)) < 0.12, index=sig.index)})
    orig_fs = _patch_fire_series(fires)
    orig_read = BT.store.read
    BT.store.read = lambda ns, nm: sig if (ns, nm) == ("vector", "signals") else orig_read(ns, nm)
    tmp = Path(tempfile.mkdtemp()) / "gate.json"
    orig_path = BT.gate_path
    BT.gate_path = lambda: tmp
    try:
        rc = BT.main()
    finally:
        BT.radar.fire_series = orig_fs
        BT.store.read = orig_read
        BT.gate_path = orig_path
    assert rc == 1                      # a random (non-leading) leg fails the gate


def test_radar_auto_demotes_on_gate():
    """The radar zeroes an act leg's points when the gate marks it demoted."""
    import engine.btc_impulse_radar_backtest as bt
    orig = bt.load_gate
    bt.load_gate = lambda: {"legs": {"d2": {"status": "demoted"},
                                     "d3": {"status": "leading"},
                                     "u1": {"status": "leading"}}}
    try:
        out = R.compute()              # real data
    finally:
        bt.load_gate = orig
    if not out.get("ok"):
        return                          # stores absent -> skip
    d2 = next(l for l in out["down"]["legs"] if l["key"] == "d2_dvol")
    assert d2["demoted"] is True and d2["points"] == 0.0
    assert "DEMOTED" in d2["honesty"]


def test_ledger_stamp_and_grade_roundtrip():
    tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    orig = LED._path
    LED._path = lambda: tmp
    try:
        idx = pd.date_range("2024-01-01", periods=10, freq="D")
        # a fired DOWN leg followed by a real -6% move -> should grade down_hit=True
        close = pd.Series([100, 100, 100, 100, 100, 94, 93, 93, 93, 93.0], index=idx)
        sig = pd.DataFrame({"close": close}, index=idx)
        radar = {"ok": True, "asof": "2024-01-05",
                 "down": {"score": 70, "ladder": "trigger", "act_live": True,
                          "legs": [{"key": "d2_dvol", "fired_today": True}]},
                 "up": {"score": 0, "ladder": "quiet", "act_live": False, "legs": []}}
        LED.stamp(radar, sig.loc[:"2024-01-05"])
        assert len(LED.load()) == 1
        LED.stamp(radar, sig.loc[:"2024-01-05"])      # idempotent on asof
        assert len(LED.load()) == 1
        summ = LED.grade(sig)                          # now the row matures (3d fwd)
        rows = LED.load()
        assert rows[0]["outcome"]["matured"] is True
        assert rows[0]["outcome"]["down_hit"] is True  # -6% within 3d after a down fire
        assert summ["down"]["hit_rate"] == 1.0
    finally:
        LED._path = orig


def test_ledger_grade_skips_a_bad_row():
    """Audit MEDIUM: one corrupt/hand-edited asof must NOT abort grading of every
    other matured row (the live hit-rate display must keep filling)."""
    tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    orig = LED._path
    LED._path = lambda: tmp
    try:
        idx = pd.date_range("2024-01-01", periods=12, freq="D")
        close = pd.Series(100.0, index=idx)
        sig = pd.DataFrame({"close": close}, index=idx)
        LED._write([
            {"asof": "2024-01-02", "fires": {"d2": True, "d3": False, "u1": False}, "outcome": None},
            {"asof": "not-a-date", "fires": {"d2": True, "d3": False, "u1": False}, "outcome": None},
            {"asof": "2024-01-03", "fires": {"d2": True, "d3": False, "u1": False}, "outcome": None},
        ])
        summ = LED.grade(sig)
        rows = LED.load()
        assert summ["ok"] is True
        assert rows[0]["outcome"] is not None and rows[2]["outcome"] is not None   # valid rows graded
        assert rows[1]["outcome"] is None                                          # bad row skipped, not fatal
    finally:
        LED._path = orig


def test_labels_keep_tail_unknown_and_denominator_mature_only():
    close = pd.Series([100., 100., 100., 94., 94., 94., 94., 94.],
                      index=pd.date_range("2026-01-01", periods=8))
    down, up = BT._labels(close)
    assert str(down.dtype) == "boolean" and str(up.dtype) == "boolean"
    assert down.notna().sum() == 5 and down.tail(3).isna().all()
    assert down.iloc[:5].tolist() == [True, True, True, False, False]
    fires = pd.Series(False, index=close.index)
    fires.iloc[-3:] = True
    base, lift, n = BT._lift(fires, down, pd.Series(True, index=close.index))
    assert np.isclose(base, 0.6) and np.isnan(lift) and n == 0


def test_labels_preserve_invalid_reference_and_future_as_unknown():
    base = pd.Series(np.linspace(100., 130., 12), index=pd.date_range("2026-01-01", periods=12))
    for invalid in [np.nan, np.inf, -np.inf, 0., -1.]:
        close = base.copy()
        close.iloc[4] = invalid
        down, up = BT._labels(close)
        assert down.iloc[1:5].isna().all() and up.iloc[1:5].isna().all()
        assert pd.notna(down.iloc[0]) and pd.notna(down.iloc[5])


def test_labels_do_not_treat_three_observations_as_three_days_across_gaps():
    close = pd.Series(np.arange(100., 112.), index=pd.date_range("2026-01-01", periods=12))
    close = close.drop(close.index[2])
    down, up = BT._labels(close)
    assert down.iloc[:2].isna().all() and up.iloc[:2].isna().all()
    assert pd.notna(down.iloc[2])


def test_labels_reject_duplicate_reversed_or_intraday_dates():
    close = pd.Series([100., 101., 102., 103., 104.], index=pd.date_range("2026-01-01", periods=5))
    cases = [close.iloc[::-1], pd.concat([close.iloc[:2], close.iloc[1:]])]
    intraday = close.copy()
    intraday.index = intraday.index + pd.Timedelta(hours=1)
    cases.append(intraday)
    for invalid in cases:
        try:
            BT._labels(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Malformed daily dates must not become scored outcomes")


def test_lift_and_permutation_have_no_evidence_when_no_outcome_matured():
    close = pd.Series([100., 90.], index=pd.date_range("2026-01-01", periods=2))
    down, up = BT._labels(close)
    assert down.isna().all() and up.isna().all()
    fire = pd.Series(True, index=close.index)
    mask = pd.Series(True, index=close.index)
    base, lift, n = BT._lift(fire, down, mask)
    assert np.isnan(base) and np.isnan(lift) and n == 0
    assert np.isnan(BT._perm_p(fire, down, mask, lift, np.random.default_rng(0)))
    assert all(s.empty for s in BT._labels(close.iloc[:0]))


def test_validate_does_not_count_immature_tail_fires():
    sig = _sig_with_drops()
    fire = pd.Series(False, index=sig.index)
    fire.iloc[-BT.LABEL_H:] = True
    original = _patch_fire_series(pd.DataFrame({"d2": fire}))
    try:
        result = BT.validate(sig)
    finally:
        BT.radar.fire_series = original
    assert result["ok"] is True
    assert result["legs"]["d2"]["n_fires_full"] == 0
    assert result["legs"]["d2"]["n_fires_holdout"] == 0
    assert result["legs"]["d2"]["pass"] is False


def test_r3_episode_selection_requires_observed_onsets_and_no_future_labels():
    from research.crypto_science.r3_cohort_study import episode_starts
    idx = pd.date_range("2026-01-01", periods=12)
    fire = pd.Series([pd.NA, True, False, True, True, False, True, False, False, True, False, False],
                     index=idx, dtype="boolean")
    # Jan2 is already positive when it first becomes observed: no invented onset.
    assert list(episode_starts(fire, separation_days=3)) == [idx[3], idx[9]]
    assert list(episode_starts(fire, separation_days=7)) == [idx[3]]
    sparse = fire.drop(idx[2])
    assert idx[3] not in episode_starts(sparse, separation_days=3)


def test_r3_delay_uses_calendar_days_and_preserves_unknown():
    from research.crypto_science.r3_cohort_study import delayed_observations
    idx = pd.date_range("2026-01-01", periods=6)
    fire = pd.Series([False, True], index=idx[[0, 2]], dtype="boolean")
    shifted = delayed_observations(fire, idx, 1)
    assert pd.isna(shifted.loc[idx[0]])
    assert not bool(shifted.loc[idx[1]])
    assert pd.isna(shifted.loc[idx[2]])
    assert bool(shifted.loc[idx[3]])
    assert shifted.iloc[4:].isna().all()


def test_r3_episode_interval_abstains_with_one_event_block():
    from research.crypto_science.r3_cohort_study import block_hit_interval
    assert block_hit_interval(np.array([1, 0, 0]), np.array([1, 0, 0])) is None
    got = block_hit_interval(np.array([1, 1, 0]), np.array([1, 1, 0]))
    assert got == [1.0, 1.0]


def _r4_bars(n=120, freq="h"):
    idx = pd.date_range("2020-01-01", periods=n, freq=freq)
    close = 100 + np.sin(np.arange(n) / 3)
    return pd.DataFrame({"open": close, "high": close + 1,
                         "low": close - 1, "close": close}, index=idx)


def test_r4_hourly_features_use_completed_past_only_and_reject_gaps():
    from research.crypto_science.r4_sequence_study import hourly_conditions
    bars = _r4_bars()
    bars.loc[bars.index[95], ["open", "high", "low", "close"]] = [100, 100, 90, 91]
    full = hourly_conditions(bars)
    assert full.iloc[:73].isna().all().all()
    assert bool(full.d0.iloc[95]) and bool(full.d1.iloc[95])
    for stop in [80, 96, 109, 120]:
        pd.testing.assert_frame_equal(hourly_conditions(bars.iloc[:stop]), full.iloc[:stop])
    broken = hourly_conditions(bars.drop(bars.index[85]))
    assert broken.loc[bars.index[85]:].isna().all().all()
    bad = bars.copy(); bad.loc[bad.index[99], "high"] = np.inf
    assert hourly_conditions(bad).iloc[99:].isna().all().all()
    for invalid in [bars.iloc[::-1], pd.concat([bars.iloc[:3], bars.iloc[2:]])]:
        try:
            hourly_conditions(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Malformed indices must not be silently sorted/deduplicated")


def test_r4_onsets_do_not_invent_start_after_missing_observations():
    from research.crypto_science.r4_sequence_study import onsets, execution_time
    idx = pd.date_range("2020-01-01", periods=8, freq="h")
    s = pd.Series([pd.NA, True, False, True, True, False, True, False], index=idx, dtype="boolean")
    assert list(onsets(s, step="1h", separation="3h")) == [idx[3]]
    assert execution_time(idx[3], bar_hours=1, delay_hours=1) == idx[5]
    assert execution_time(idx[3], bar_hours=24, delay_hours=6) == idx[3] + pd.Timedelta(hours=30)


def test_r4_barriers_distinguish_unknown_order_opening_gap_and_censoring():
    from research.crypto_science.r4_sequence_study import barrier_label
    b = _r4_bars(4); b.loc[:, :] = [100, 101, 99, 100]
    b.loc[b.index[1], ["high", "low"]] = [104, 94]
    assert barrier_label(b, b.index[0], hours=3, lower=-.05, upper=.03)["category"] == "ambiguous"
    b.loc[b.index[1], "open"] = 94
    assert barrier_label(b, b.index[0], hours=3, lower=-.05, upper=.03)["category"] == "lower_first"
    b.loc[b.index[1], "open"] = 104
    assert barrier_label(b, b.index[0], hours=3, lower=-.05, upper=.03)["category"] == "upper_first"
    assert barrier_label(b.iloc[:-1], b.index[0], hours=3, lower=-.05, upper=.03)["category"] == "censored"
    b.loc[b.index[1], :] = [100, 101, 99, 100]
    assert barrier_label(b, b.index[0], hours=3, lower=-.05, upper=.03)["category"] == "neither"
    assert barrier_label(b.drop(b.index[1]), b.index[0], hours=3, lower=-.05, upper=.03)["category"] == "censored"


def test_r4_reclaim_is_first_observable_date_not_future_best_entry():
    from research.crypto_science.r4_sequence_study import first_reclaim
    b = _r4_bars(20, "D"); b.loc[:, :] = [100, 101, 99, 100]
    b.loc[b.index[10], :] = [100, 101, 79, 80]
    b.loc[b.index[11], :] = [80, 90, 79, 89]
    b.loc[b.index[12], :] = [89, 101, 80, 100]
    assert first_reclaim(b, b.index[10]) == ("confirmed", b.index[12])
    assert first_reclaim(b.iloc[:13], b.index[10]) == ("confirmed", b.index[12])
    status, when = first_reclaim(b.drop(b.index[11]), b.index[10])
    assert status == "unknown" and when is None
    flat = _r4_bars(20, "D"); flat.loc[:, :] = [100, 101, 99, 100]
    assert first_reclaim(flat, flat.index[10]) == ("no_entry", None)


def test_r4_account_holds_drifting_weights_and_charges_actual_changes():
    from research.crypto_science.r4_sequence_study import account_path
    assert np.isclose(account_path([100, 110, 99], [1, 1], cost_bps=0)["wealth"], .99)
    assert np.isclose(account_path([100, 110, 99], [.5, .5], cost_bps=0)["wealth"], .995)
    assert np.isclose(account_path([100, 100, 100], [.5, .5], cost_bps=100)["wealth"], .995**2)
    assert account_path([100, 90, 80], [0, 0], cost_bps=25)["wealth"] == 1
    cash = account_path([100, 90], [0], initial_weight=1, terminal_weight=1, cost_bps=10)
    assert np.isclose(cash["wealth"], .999**2)
    for bad in [[100, np.nan, 90], [100, 0, 90]]:
        try:
            account_path(bad, [1, 1], cost_bps=0)
        except ValueError:
            pass
        else:
            raise AssertionError("Unknown prices must not disappear from accounting")


def test_r4_incumbent_target_appears_after_daily_close_and_explicit_delay():
    from research.crypto_science.r4_sequence_study import incumbent_targets
    day = pd.Timestamp("2020-01-01")
    s = pd.Series([.6, np.nan, 0.], index=pd.date_range(day, periods=3))
    idx = pd.date_range(day, periods=100, freq="h")
    t = incumbent_targets(s, idx, delay_hours=1)
    assert t.loc[:day + pd.Timedelta(hours=24)].isna().all()
    assert t.loc[day + pd.Timedelta(hours=25)] == .6
    assert t.loc[day + pd.Timedelta(hours=48)] == .6
    assert pd.isna(t.loc[day + pd.Timedelta(hours=49)])
    assert t.loc[day + pd.Timedelta(hours=73)] == 0


def test_r4_block_interval_supports_signed_differences_without_fake_certainty():
    from research.crypto_science.r4_sequence_study import interval90
    frame = pd.DataFrame({'anchor':['2020-01-01','2020-07-01'], 'difference':[-.1,-.1]})
    assert np.allclose(interval90(frame,'difference'),[-.1,-.1])
    assert interval90(frame.iloc[:1],'difference') is None


def test_r4_preentry_shock_is_not_credited_as_future_prediction():
    from research.crypto_science.r4_sequence_study import barrier_label
    bars = _r4_bars(5); bars.loc[:, :] = [100,101,99,100]
    bars.loc[bars.index[0], :] = [130,130,80,100]
    got = barrier_label(bars,bars.index[1],hours=3,lower=-.05,upper=.03)
    assert got['category']=='neither' and np.isclose(got['worst_excursion'], -.01, rtol=0, atol=1e-12)


def test_r4_terminal_open_does_not_require_future_terminal_bar_extrema():
    from research.crypto_science.r4_sequence_study import barrier_label
    bars = _r4_bars(4); bars.loc[:, :] = [100, 101, 99, 100]
    bars.loc[bars.index[-1], ['high','low','close']] = np.nan
    got = barrier_label(bars, bars.index[0], hours=3, lower=-.05, upper=.03)
    assert got['category']=='neither' and got['terminal_return']==0
    bars.loc[bars.index[-1], 'open'] = np.nan
    assert barrier_label(bars, bars.index[0], hours=3, lower=-.05, upper=.03)['category']=='censored'


def _r5_bars(n=300):
    idx = pd.date_range('2020-01-01', periods=n, freq='h')
    return pd.DataFrame({'open':100.,'high':101.,'low':99.,'close':100.,'volume':10.}, index=idx)


def test_r5_landmark_uses_only_completed_followup_and_prior_volume():
    from research.crypto_science.r5_participation_study import downside_observation
    b = _r5_bars(); a = b.index[90]
    b.loc[a,'volume'] = 99999.
    for k in range(1,7):
        b.loc[a+pd.Timedelta(hours=k),:] = [96-k,97-k,94-k,95-k,20.]
    got = downside_observation(b,a)
    assert got['state']=='persistent' and got['volume_ratio']==2.
    assert got == downside_observation(b.loc[:a+pd.Timedelta(hours=6)],a)
    changed=b.copy();changed.loc[a+pd.Timedelta(hours=7):,:] = [1000,1001,999,1000,99999]
    assert got == downside_observation(changed,a)
    assert got['issue']==a+pd.Timedelta(hours=7)
    b.loc[a+pd.Timedelta(hours=6),['open','high','low','close']] = [100,103,99,102]
    assert downside_observation(b,a)['state']=='reclaimed'


def test_r5_volume_missing_is_not_a_negative_but_zero_is_observed():
    from research.crypto_science.r5_participation_study import downside_observation
    b=_r5_bars();a=b.index[90]
    for k in range(1,7):b.loc[a+pd.Timedelta(hours=k),:] = [96-k,97-k,94-k,95-k,0.]
    assert downside_observation(b,a)['volume_ratio']==0.
    b.loc[a+pd.Timedelta(hours=3),'volume']=np.nan
    got=downside_observation(b,a)
    assert got['state']=='persistent' and got['volume_ratio'] is None
    b.loc[a+pd.Timedelta(hours=3),'volume']=-1.
    assert downside_observation(b,a)['volume_ratio'] is None
    b.loc[:a-pd.Timedelta(hours=1),'volume']=0.
    assert downside_observation(b,a)['volume_ratio'] is None
    assert downside_observation(b.drop(a+pd.Timedelta(hours=2)),a)['state']=='unknown'


def test_r5_reclaim_volume_gate_never_searches_a_later_prettier_entry():
    from research.crypto_science.r5_participation_study import early_reclaim
    b=_r5_bars();anchor=b.index[72];t=anchor+pd.Timedelta(hours=30)
    b.loc[t,['open','high','low','close']]=[100,103,100,102]
    b.loc[t-pd.Timedelta(hours=2):t,'volume']=5.
    b.loc[t+pd.Timedelta(hours=1),:]=[102,110,101,109,10000]
    got=early_reclaim(b,anchor)
    assert got['price_status']=='confirmed' and got['signal_start']==t
    assert got['volume_ratio']==.5 and got['volume_status']=='rejected'
    assert got==early_reclaim(b.loc[:t],anchor)
    b.loc[t-pd.Timedelta(hours=10),'volume']=np.nan
    got=early_reclaim(b,anchor)
    assert got['price_status']=='confirmed' and got['volume_status']=='unknown'


def test_r5_no_entry_differs_from_missing_price_and_bad_index():
    from research.crypto_science.r5_participation_study import early_reclaim, downside_observation
    b=_r5_bars();anchor=b.index[72]
    assert early_reclaim(b,anchor)['price_status']=='no_entry'
    assert early_reclaim(b.drop(anchor+pd.Timedelta(hours=28)),anchor)['price_status']=='unknown'
    for f in [b.iloc[::-1],pd.concat([b,b.iloc[-1:]])]:
        try:downside_observation(f,b.index[90])
        except ValueError:pass
        else:raise AssertionError('Malformed chronology must not be silently repaired')


def test_r5_cash_overlay_cannot_exit_before_the_landmark():
    from research.crypto_science.r5_participation_study import cash_after
    idx=pd.date_range('2020-01-01',periods=24,freq='h')
    t=pd.Series(.6,index=idx)
    out=cash_after(t,idx[6])
    assert (out.iloc[:6]==.6).all() and (out.iloc[6:]==0).all()
    assert (t==.6).all(), 'Do not mutate the incumbent target array'


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
