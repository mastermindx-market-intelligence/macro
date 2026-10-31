"""Discriminating tests for the T11 prereg harness (scripts/leadership_rotation_study.py).

Every test names the single one-line source mutation that makes it FAIL (the
``# MUTATION:`` comment above it) and is proven by applying that mutation,
seeing the test FAIL, and reverting. Synthetic numpy arrays and ``tmp_path``
only -- no market data is read or evaluated here (prereg section 12,
invalidator 6).
"""

from __future__ import annotations

import math
import subprocess

import numpy as np
import pandas as pd
import pytest

from scripts import leadership_rotation_study as study
from scripts.leadership_rotation_study import (
    PartitionSealed,
    PreregChanged,
    PreregNotLanded,
    SourceInvalid,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check
    )


# ---------------------------------------------------------------------------
# 1. truncation invariance (no look-ahead)
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py zscore shift the sigma window to
# `sliding_window_view(changes, SIGMA_CHANGES)[1 : n - SIGMA_CHANGES + 1]` (the
# vectorized form of `changes[t - SIGMA_CHANGES + 1 : t + 1]`, a 1-day look-ahead) -- the z at the
# last kept index then differs between the full and truncated series and this
# test FAILS.
def test_truncation_invariance_no_lookahead():
    rng = np.random.default_rng(study.SEED)
    R = np.cumsum(rng.normal(0.0, 0.01, 400))
    m = rng.normal(0.0, 0.01, 400)
    x = 0.8 * m

    for k in (150, 300, 390):
        # A1: state/entries/exits on R[:k] equal the full-series results
        # restricted to indices < k.
        st_f, en_f, ex_f = study.arm_a1(R)
        st_t, en_t, ex_t = study.arm_a1(R[:k])
        np.testing.assert_array_equal(st_f[:k], st_t[:k])
        assert [e for e in en_f if e < k] == en_t
        assert [e for e in ex_f if e < k] == ex_t
        # the z itself must be identical on the kept prefix
        np.testing.assert_array_equal(study.zscore(R)[:k], study.zscore(R[:k])[:k])

        # A0
        raw_f, on_f = study.arm_a0(R)
        raw_t, on_t = study.arm_a0(R[:k])
        assert [t for t in raw_f if t < k] == raw_t
        assert [t for t in on_f if t < k] == on_t

        # B2
        b2_f = study.arm_b2(R)
        b2_t = study.arm_b2(R[:k])
        assert [t for t in b2_f if t < k] == b2_t

        # rolling beta (B4 helper)
        np.testing.assert_array_equal(
            study.rolling_beta(x, m)[:k], study.rolling_beta(x[:k], m[:k])[:k]
        )

    # smoke: B3 shape, B5 descriptive table, B7 abstain (no alarm ever)
    spy = np.cumsum(rng.normal(0.0, 0.01, 400))
    b3_state, b3_entries, b3_exits = study.arm_b3(R, spy)
    assert len(b3_state) == len(R)
    assert study.arm_b7() == []
    table = study.arm_b5_table(R, np.zeros(len(R)), np.zeros(len(R), dtype=bool))
    assert table["n_formations"] > 0
    assert len(b3_entries) >= 0 and len(b3_exits) >= 0


# ---------------------------------------------------------------------------
# 2. hand-computed z at one t
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py zscore change `win[ok].std(axis=1, ddof=1)`
# to `win[ok].std(axis=1, ddof=0)` -- sigma becomes sqrt(62/63) instead of 1 and the
# hand-computed value FAILS.
def test_zscore_hand_computed_at_one_index():
    # 63 changes: 31 of +1, 31 of -1, one 0 -> mean 0,
    # sigma_t = sqrt((62 * 1^2) / (63 - 1)) = sqrt(62/62) = 1 exactly.
    d = np.array([1.0, -1.0] * 31 + [0.0])
    assert len(d) == study.SIGMA_CHANGES
    R = np.concatenate([[0.0], np.cumsum(d)])
    # numerator R_t - R_{t-20} = sum of the 20 changes ending at t
    # = sum(d[43:63]) = -1 (the alternating tail cancels, the last change is 0)
    assert float(np.sum(d[43:63])) == -1.0
    z = study.zscore(R)
    # z_63 = (R_63 - R_43) / (sigma_63 * sqrt(20)) = -1 / (1 * sqrt(20))
    assert z[63] == pytest.approx(-1.0 / np.sqrt(20.0), abs=1e-12)
    assert np.isnan(z[62])  # t too early: the 63-change window is not complete


# ---------------------------------------------------------------------------
# 3. hysteresis state machine
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:320 change `zt >= Z_ENTER` to
# `zt > Z_ENTER` -- the entries at exactly z = +1.0 never fire and this
# test FAILS.
def test_hysteresis_entry_exit_and_nan_forces_off():
    z = np.array([np.nan, 1.0, 0.5, 2.0, -0.5, 0.5, 1.0, np.nan, 1.0, 0.0])
    state, entries, exits = study.hysteresis(z)
    assert entries == [1, 6, 8]
    assert exits == [4, 9]
    assert state.astype(int).tolist() == [0, 1, 1, 1, 0, 0, 1, 0, 1, 0]
    # entry only from OFF at z >= +1 (t=3 is ON, z=2.0 -> no re-entry);
    # no re-entry below the band while OFF (t=5, z=0.5 -> stays OFF);
    # NaN forces OFF with NO exit signal (t=7 records nothing) and the next
    # entry needs z >= +1 again (t=8 fires).


# ---------------------------------------------------------------------------
# 4. A2 delayed confirmation
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:348 change
# `alarms.append(e + C)` to `alarms.append(e + C - 1)` -- the alarm date moves
# off e+5 and this test FAILS.
def test_a2_confirmation_alarm_pending_and_drop():
    n = 30
    state = np.ones(n, dtype=bool)
    state[13] = False  # the e=10 entry drops at e+3
    entries = [2, 10, 27]
    alarms, pending = study.arm_a2(state, entries)
    # e=2 stays ON at 3..7 -> alarm at e+5 = 7
    assert alarms == [7]
    # e=10 drops at 13 -> never alarms, and the calendar continues (not pending)
    # e=27: e+5 = 32 >= n -> PENDING, counted, never an alarm
    assert pending == [27]
    assert 10 not in alarms and 10 not in pending


# ---------------------------------------------------------------------------
# 5. A0 onset needs the full quiet run
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:369 change
# `range(t - A0_QUIET, t)` to `range(t - A0_QUIET + 1, t)` (only 4 quiet days
# required) -- the positive-day-then-quiet-run series D fires a false onset
# and this test FAILS.
def test_a0_onset_requires_five_quiet_days_and_unmeasured_breaks_run():
    # A: five non-positive 2s days then a positive day -> raw AND onset at 8
    Ra = np.array([100.0, 100.0, 100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 100.0])
    raw, onsets = study.arm_a0(Ra)
    assert raw == [8] and onsets == [8]
    # B: an unmeasured day inside the run breaks it -> raw fires, onset does not
    Rb = np.array([100.0, 100.0, 100.0, 99.0, 98.0, np.nan, 96.0, 95.0, 100.0])
    raw, onsets = study.arm_a0(Rb)
    assert raw == [8] and onsets == []
    # D: day t-5 is positive, t-4..t-1 quiet -> NO onset (needs all five)
    Rd = np.array([100.0, 100.0, 101.0, 100.0, 99.0, 98.0, 97.0, 101.0])
    raw, onsets = study.arm_a0(Rd)
    assert raw == [2, 7] and onsets == []


# ---------------------------------------------------------------------------
# 6. B2 fires on the crossing, not on every positive day
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:396 change `prev <= 0.0` to
# `prev < 0.0` -- the crossing whose previous value is EXACTLY 0 no longer
# fires and this test FAILS.
def test_b2_crosses_once_then_stays_silent():
    R = np.full(70, 100.0)
    R[64] = 101.0  # cur = 1 > 0, prev = 0 <= 0 -> the single crossing
    R[65] = 102.0  # cur = 2 > 0, prev = 1 > 0 -> silent
    assert study.arm_b2(R) == [64]


# ---------------------------------------------------------------------------
# 7. outcome precedence and origin o = t+1
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:511 change
# `o = t + origin_offset` to `o = t` -- the free earlier execution moves every
# y and this test FAILS.
def test_outcome_precedence_and_origin_t_plus_one():
    R = np.array([0.0, 5.0, 7.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 100.0, 101.0, 102.0])
    invalid = np.zeros(len(R), dtype=bool)

    # MATURED with origin o = t+1: y = R[o+h] - R[o] = R[6] - R[3] = 3
    state, y = study.outcome(R, invalid, 2, 3)
    assert state == "MATURED" and y == pytest.approx(3.0)
    # a mutation to o = t would give R[5] - R[2] = 35 instead

    # SOURCE_INVALID beats UNPRICEABLE: the invalid endpoint also has NaN R
    invalid_si = invalid.copy()
    R_si = R.copy()
    R_si[3] = np.nan
    invalid_si[3] = True
    state, y = study.outcome(R_si, invalid_si, 2, 3)
    assert state == "SOURCE_INVALID" and np.isnan(y)

    # UNPRICEABLE: an existing endpoint with NaN R (not flagged invalid)
    R_un = R.copy()
    R_un[3] = np.nan
    state, y = study.outcome(R_un, invalid, 2, 3)
    assert state == "UNPRICEABLE" and np.isnan(y)

    # IMMATURE: the endpoint is beyond the calendar end
    state, y = study.outcome(R, invalid, 9, 3)  # o=10 ok, end=13 >= 12
    assert state == "IMMATURE" and np.isnan(y)

    # NaN beats beyond-end: o exists and is NaN while o+h is past the end
    R_nan = R.copy()
    R_nan[10] = np.nan
    state, y = study.outcome(R_nan, invalid, 9, 3)
    assert state == "UNPRICEABLE"


# ---------------------------------------------------------------------------
# 8. policy origin o_c = t+6 and cost_of_delay over both-MATURED entries
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:527 change
# `origin_offset=1 + C` to `origin_offset=1 + C - 1` -- the policy origin moves
# off t+c+1, the policy-path y changes and this test FAILS.
def test_policy_origin_is_t_plus_c_plus_one_and_cost_of_delay_uses_both():
    R = np.array(
        [0.0, 5.0, 7.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 100.0, 101.0, 150.0, 103.0, 104.0, 105.0, 106.0]
    )
    invalid = np.zeros(len(R), dtype=bool)

    # policy origin: o_c = t + c + 1 = t + 6 (t=2 -> o=8, end=11)
    assert study.policy_outcome(R, invalid, 2, 3) == study.outcome(
        R, invalid, 2, 3, origin_offset=6
    )
    assert study.policy_outcome(R, invalid, 2, 3)[1] == pytest.approx(150.0 - 45.0)

    # cost_of_delay: entry 2 is MATURED on BOTH paths; entry 7 is MATURED on o
    # but IMMATURE on o_c (end = 16 beyond the calendar) -> excluded from the
    # difference and from n_both.
    report = study.cost_of_delay(R, invalid, [2, 7], h=3)
    assert report["states_o"]["MATURED"] == 2
    assert report["states_oc"]["MATURED"] == 1
    assert report["states_oc"]["IMMATURE"] == 1
    assert report["n_both"] == 1
    assert report["mean_y_o"] == pytest.approx((3.0 + 105.0) / 2)
    assert report["mean_y_oc"] == pytest.approx(150.0 - 45.0)
    assert report["difference"] == pytest.approx(3.0 - (150.0 - 45.0))


# ---------------------------------------------------------------------------
# 9. B6 carry / zero-new-return placebo
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:483 change
# `carry_R = np.concatenate(([np.nan], R[:-1]))` to
# `carry_R = np.asarray(R, dtype=float)` -- day t's own move is no longer
# removed, the day-move-only entry wrongly counts as carry and this test FAILS.
def test_b6_carry_placebo():
    d = np.zeros(199)
    d[79] = 1.0  # a single one-session jump: the entry at 80 is day-t's own move
    d[97:159] = 0.01  # a sustained ramp; d[159] = 0 so the 159 entry needs no fresh return
    R = np.concatenate([[0.0], np.cumsum(d)])
    z = study.zscore(R)
    assert z[80] >= study.Z_ENTER  # a genuine A1 entry
    assert z[159] >= study.Z_ENTER  # a genuine A1 entry

    flags, share = study.arm_b6_carry(R, [80, 159])
    assert flags == [False, True]  # jump entry is NOT carry; ramp entry IS
    assert 0.0 <= share <= 1.0
    assert share == pytest.approx(0.5)  # the share is printed beside the flags


# ---------------------------------------------------------------------------
# 10. exact betas and the beta-only residual
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:434 change
# `(sxm - sx * sm / window)` to `(sxm - sx * sm / (window - 1))` -- the slope
# leaves 0.8/1.1 far beyond 1e-12 and this test FAILS.
def test_rolling_beta_exact_and_beta_only_residual():
    rng = np.random.default_rng(study.SEED + 2)
    m = rng.normal(0.0, 0.01, 400)
    x = 0.8 * m
    w = 1.1 * m + 0.0002  # an intercept never moves the slope

    beta_x = study.rolling_beta(x, m)
    beta_w = study.rolling_beta(w, m)
    assert beta_x[300] == pytest.approx(0.8, abs=1e-12)
    assert beta_w[300] == pytest.approx(1.1, abs=1e-12)
    assert np.isnan(beta_x[: study.BETA_WINDOW - 1]).all()

    # one NaN pair in the window poisons the beta
    m_nan = m.copy()
    m_nan[250] = np.nan
    assert np.isnan(study.rolling_beta(0.8 * m_nan, m_nan)[300])

    # beta-only Y has residual exactly 0 (betas are the caller's, at t = o-1)
    log_spy = np.cumsum(rng.normal(0.0, 0.01, 40)) + 5.0
    o, h = 10, 5
    y = (0.8 - 1.1) * (log_spy[o + h] - log_spy[o])
    assert study.residual_outcome(y, 0.8, 1.1, log_spy, o, h) == pytest.approx(
        0.0, abs=1e-12
    )
    assert np.isnan(study.residual_outcome(y, np.nan, 1.1, log_spy, o, h))


# ---------------------------------------------------------------------------
# 11. all-event coverage keeps UNMEASURED days in the denominator
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:625 change
# `denominator += 1` to `if not np.isnan(R[t]): denominator += 1` -- UNMEASURED
# days drop out, coverage rises and this test FAILS.
def test_all_event_coverage_keeps_unmeasured_days_in_denominator():
    R = np.arange(30, dtype=float)
    R[12] = np.nan
    R[13] = np.nan
    invalid = np.zeros(len(R), dtype=bool)
    cov = study.all_event_coverage(R, invalid, first_eligible_idx=5, last_formation=20, h=2)
    assert cov["denominator"] == 16  # every calendar index in [5, 20]
    assert cov["counts"]["UNMEASURED"] == 2  # never reclassified as zero
    # t=12,13 are UNMEASURED; t=9,10,11 have an endpoint on the NaN days and
    # are UNPRICEABLE; the remaining 11 days are MATURED with finite y.
    assert cov["numerator"] == 11
    assert cov["counts"]["UNPRICEABLE"] == 3
    assert cov["counts"]["MATURED"] == 11
    assert cov["coverage"] == pytest.approx(11.0 / 16.0)


# ---------------------------------------------------------------------------
# 12. relative units: y is a LOG difference, not a percentage
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:249 change
# `np.log(num) - np.log(den)` to `(num - den) / den` -- y becomes the 0.1
# simple difference instead of log(1.1) and this test FAILS.
def test_relative_units_are_log_not_pct():
    num = np.full(6, 100.0)
    den = np.full(6, 100.0)
    num[5] = 110.0  # receiver +10%, donor flat
    R, invalid = study.log_ratio(num, den)
    state, y = study.outcome(R, invalid, 1, 3)  # o = 2, end = 5
    assert state == "MATURED"
    assert y == pytest.approx(math.log(1.1), abs=1e-12)
    assert abs(y - 0.1) > 1e-3  # 0.0953..., NOT the 0.1 simple difference
    # the H2 margin lives on the same log scale: +0.50 points = +0.0050
    assert study.MARGIN_H2 == 0.0050
    assert study.MARGIN_H3 == 0.0025


# ---------------------------------------------------------------------------
# 13. entry_context: both-down is relative resilience, recovery never claimed
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:715 swap the contract
# arguments: `pair_interpretation(r_receiver=den_ret, r_donor=num_ret)` -- the
# roles reverse, the label becomes relative_weakness and this test FAILS.
def test_entry_context_both_down_is_relative_resilience():
    num = pd.Series([100.0, 100.0, 100.0, 100.0, 95.0])  # receiver -5%
    den = pd.Series([100.0, 100.0, 100.0, 100.0, 90.0])  # donor -10%
    ctx = study.entry_context(num, den, t=4, lookback=2)
    assert ctx["absolute_direction"] == "both_down"
    assert ctx["interpretation"] == "relative_resilience"
    assert "absolute_recovery" in ctx["not_claimed"]
    assert ctx["receiver_return"] == pytest.approx(-0.05)
    assert ctx["donor_return"] == pytest.approx(-0.10)


# ---------------------------------------------------------------------------
# 14. the loader reads COMMITTED bytes only
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:198 replace the cat-file read
# with a working-tree read:
# `raw = subprocess.CompletedProcess([], 0, io.open(f"{repo}/{path}", "rb").read(), b"")`
# -- the loader returns the overwritten working-tree value (99.0) and this
# test FAILS.
def test_loader_reads_committed_bytes_not_working_tree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "lane@example.com")
    _git(repo, "config", "user.name", "lane")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "empty root")
    empty_commit = _git(repo, "rev-parse", "HEAD").stdout.strip()

    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    parquet_dir = repo / "data" / "yahoo"
    parquet_dir.mkdir(parents=True)
    pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0, 14.0]}, index=dates).to_parquet(
        parquet_dir / "AAA.parquet"
    )
    pd.DataFrame({"px": [1.0, 2.0, 3.0, 4.0, 5.0]}, index=dates).to_parquet(
        parquet_dir / "BBB.parquet"  # missing the required close column
    )
    _git(repo, "add", "data/yahoo/AAA.parquet", "data/yahoo/BBB.parquet")
    _git(repo, "commit", "-q", "-m", "add parquet")
    full_commit = _git(repo, "rev-parse", "HEAD").stdout.strip()

    # overwrite the working-tree copy AFTER the commit
    pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0, 99.0]}, index=dates).to_parquet(
        parquet_dir / "AAA.parquet"
    )

    closes, identity = study.load_closes_from_git(str(repo), full_commit, ["AAA"])
    assert closes["AAA"].iloc[-1] == 14.0  # the COMMITTED value, not 99.0
    expected_blob = _git(
        repo, "rev-parse", f"{full_commit}:data/yahoo/AAA.parquet"
    ).stdout.strip()
    assert identity["AAA"] == {
        "path": "data/yahoo/AAA.parquet",
        "blob_sha": expected_blob,
        "commit": full_commit,
    }
    assert str(closes["AAA"].index[0])[:10] == "2020-01-01"

    with pytest.raises(SourceInvalid, match="BBB"):  # missing column
        study.load_closes_from_git(str(repo), full_commit, ["BBB"])
    with pytest.raises(SourceInvalid, match="AAA"):  # path absent at commit
        study.load_closes_from_git(str(repo), empty_commit, ["AAA"])

    # duplicate dates are a source defect, never silently sorted away
    dup = pd.DataFrame(
        {"close": [1.0, 2.0, 3.0]},
        index=pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"]),
    )
    dup.to_parquet(parquet_dir / "DDD.parquet")
    _git(repo, "add", "data/yahoo/DDD.parquet")
    _git(repo, "commit", "-q", "-m", "dup dates")
    with pytest.raises(SourceInvalid, match="DDD"):
        study.load_closes_from_git(str(repo), "HEAD", ["DDD"])


# ---------------------------------------------------------------------------
# 15. the prereg guard: landed, not descended, edited, never on main
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:689 swap the ancestry
# arguments: `_git(repo, "merge-base", "--is-ancestor", head, add)` -- the
# landed case then raises PreregNotLanded and this test FAILS.
def test_prereg_guard_states(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "lane@example.com")
    _git(repo, "config", "user.name", "lane")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "root")
    root = _git(repo, "rev-parse", "HEAD").stdout.strip()

    prereg = repo / study.PREREG_PATH
    prereg.parent.mkdir(parents=True)
    prereg.write_text("prereg v1\n", encoding="utf-8")
    _git(repo, "add", study.PREREG_PATH)
    _git(repo, "commit", "-q", "-m", "land prereg")
    landed = _git(repo, "rev-parse", "HEAD").stdout.strip()
    blob = _git(repo, "rev-parse", f"{landed}:{study.PREREG_PATH}").stdout.strip()

    _git(repo, "commit", "--allow-empty", "-q", "-m", "descendant")
    descendant = _git(repo, "rev-parse", "HEAD").stdout.strip()

    # fake the remote main ref exactly as the envelope prescribes
    _git(repo, "update-ref", "refs/remotes/origin/main", landed)

    # landed: passes and names the oldest add commit + the frozen blob
    result = study.assert_prereg_landed(
        str(repo), head=descendant, main_ref="origin/main", blob_sha=blob
    )
    assert result == {"add_commit": landed, "blob_sha": blob, "head": descendant}

    # not descended from the add commit
    _git(repo, "switch", "-q", "-c", "side", root)
    _git(repo, "commit", "--allow-empty", "-q", "-m", "sibling")
    sibling = _git(repo, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(PreregNotLanded):
        study.assert_prereg_landed(
            str(repo), head=sibling, main_ref="origin/main", blob_sha=blob
        )

    # descended but the file was edited at the head
    _git(repo, "switch", "-q", "main")
    prereg.write_text("prereg v2\n", encoding="utf-8")
    _git(repo, "commit", "-aqm", "edit prereg")
    edited = _git(repo, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(PreregChanged):
        study.assert_prereg_landed(
            str(repo), head=edited, main_ref="origin/main", blob_sha=blob
        )

    # the file is not on the main ref at all
    _git(repo, "update-ref", "refs/remotes/origin/main", root)
    with pytest.raises(PreregNotLanded):
        study.assert_prereg_landed(
            str(repo), head=descendant, main_ref="origin/main", blob_sha=blob
        )


# ---------------------------------------------------------------------------
# 16. partition guard: the seal is a seat act; P1 is inclusive at both ends
# ---------------------------------------------------------------------------


# MUTATION: scripts/leadership_rotation_study.py:658 change `idx <= end` to
# `idx < end` -- the P1_END date drops out of the mask and this test FAILS.
def test_partition_guard_seals_p2_p3_and_p1_is_inclusive():
    cal = pd.to_datetime(
        ["2015-01-01", "2015-01-02", "2026-10-11", "2026-10-12", "2026-10-13"]
    )
    mask = study.partition_mask(cal, "P1")
    # inclusive at BOTH ends: P1_START (2015-01-02) and P1_END (2026-10-12)
    assert mask.tolist() == [False, True, True, True, False]

    with pytest.raises(ValueError):  # P0 is synthetic: no calendar mask
        study.partition_mask(cal, "P0")
    with pytest.raises(PartitionSealed):  # the seal is a seat act
        study.partition_mask(cal, "P2")
    with pytest.raises(PartitionSealed):
        study.partition_mask(cal, "P3")


# V2 amendment (research/LEADERSHIP_ROTATION_PREREG_V2.md section 6): the read
# guard pins V1 AND V2. MUTATION: drop the second assert_prereg_landed call in
# assert_protocol_landed -- the "V2 edited" case below then passes and FAILS this.
def test_protocol_guard_requires_both_versions(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "lane@example.com")
    _git(repo, "config", "user.name", "lane")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "root")

    v1 = repo / study.PREREG_PATH
    v1.parent.mkdir(parents=True)
    v1.write_text("prereg v1\n", encoding="utf-8")
    _git(repo, "add", study.PREREG_PATH)
    _git(repo, "commit", "-q", "-m", "land v1")
    v1_landed = _git(repo, "rev-parse", "HEAD").stdout.strip()
    v1_blob = _git(repo, "rev-parse", f"{v1_landed}:{study.PREREG_PATH}").stdout.strip()

    v2 = repo / study.PREREG_V2_PATH
    v2.write_text("prereg v2\n", encoding="utf-8")
    _git(repo, "add", study.PREREG_V2_PATH)
    _git(repo, "commit", "-q", "-m", "land v2")
    v2_landed = _git(repo, "rev-parse", "HEAD").stdout.strip()
    v2_blob = _git(repo, "rev-parse", f"{v2_landed}:{study.PREREG_V2_PATH}").stdout.strip()
    monkeypatch.setattr(study, "PREREG_BLOB_SHA", v1_blob)
    monkeypatch.setattr(study, "PREREG_V2_BLOB_SHA", v2_blob)

    # a head between the two landings has V1 but not V2: refused
    _git(repo, "update-ref", "refs/remotes/origin/main", v2_landed)
    with pytest.raises(PreregNotLanded):
        study.assert_protocol_landed(str(repo), head=v1_landed, main_ref="origin/main")

    # a descendant of both landings passes and names both landing commits
    _git(repo, "commit", "--allow-empty", "-q", "-m", "descendant")
    descendant = _git(repo, "rev-parse", "HEAD").stdout.strip()
    result = study.assert_protocol_landed(str(repo), head=descendant, main_ref="origin/main")
    assert result["v1"]["add_commit"] == v1_landed
    assert result["v2"]["add_commit"] == v2_landed
    assert result["head"] == descendant

    # V2 edited after landing (V2 section 7 invalidator 9): refused
    v2.write_text("prereg v2 edited\n", encoding="utf-8")
    _git(repo, "commit", "-aqm", "edit v2")
    edited = _git(repo, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(PreregChanged):
        study.assert_protocol_landed(str(repo), head=edited, main_ref="origin/main")


def _zscore_v1_loop(R):
    """Verbatim V1 per-t loop (blob fafdaf09 era) kept as the identity oracle."""
    R = np.asarray(R, dtype=float)
    n = len(R)
    z = np.full(n, np.nan)
    if n <= study.SIGMA_CHANGES:
        return z
    changes = np.diff(R)
    scale = np.sqrt(study.H_PRIMARY)
    for t in range(study.SIGMA_CHANGES, n):
        if np.isnan(R[t]) or np.isnan(R[t - study.Z_LOOKBACK]):
            continue
        window = changes[t - study.SIGMA_CHANGES : t]
        if np.isnan(window).any():
            continue
        sigma = window.std(ddof=1)
        if not np.isfinite(sigma) or sigma == 0.0:
            continue
        z[t] = (R[t] - R[t - study.Z_LOOKBACK]) / (sigma * scale)
    return z


# MUTATION: scripts/leadership_rotation_study.py zscore drop np.isnan(win).any(axis=1) from ok
# MUTATION: scripts/leadership_rotation_study.py zscore slice sliding_window_view[1:] (off-by-one window)
def test_zscore_vectorized_is_bitwise_identical_to_v1_loop():
    rng = np.random.default_rng(20261014)
    for k in range(120):
        n = int(rng.integers(10, 900))
        R = np.cumsum(rng.normal(0.0, [1e-3, 7e-3, 3e-2][k % 3], n))
        if k % 3 == 0:
            R[rng.integers(0, n, size=int(rng.integers(1, 12)))] = np.nan
        if k % 5 == 0 and n > 200:
            a = int(rng.integers(0, n - 100))
            R[a : a + 80] = R[a]  # flat stretch -> sigma == 0 windows
        if k % 7 == 0:
            R[: int(rng.integers(0, n))] = np.nan
        assert np.array_equal(study.zscore(R), _zscore_v1_loop(R), equal_nan=True), k


def test_prereg_pins_match_the_committed_documents():
    """Every prereg blob pin equals the git blob of the document it names (V1, V2,
    V2.1 §0), so a doc edit without a re-pin — or a re-pin without the doc — fails."""
    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for path, pin in (
        (study.PREREG_PATH, study.PREREG_BLOB_SHA),
        (study.PREREG_V2_PATH, study.PREREG_V2_BLOB_SHA),
        (study.PREREG_V2_1_PATH, study.PREREG_V2_1_BLOB_SHA),
    ):
        data = (root / path).read_bytes()
        blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        assert blob == pin, f"{path}: blob {blob} != pin {pin}"
    assert study.PREREG_V2_1_BLOB_SHA != "0" * 40
