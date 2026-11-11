"""Rotation Core v2: seal refusal and state-machine precedence (synthetic; no market outcome)."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from engine import rotation_core_v2 as v2

SEALED = "/home/ubuntu2/tmp/rotation-core/data/french/sealed_post2019/49_Industry_Portfolios_Daily.csv"


def test_sealed_path_refused_without_release(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.seal_guard(SEALED, release=tmp_path / "HOLDOUT_RELEASE_v2.json")


def test_loader_refuses_sealed_path_before_reading():
    with pytest.raises(v2.SealedRefusal):
        v2.load_french_industries(SEALED, "2019-12-31")


def test_window_after_2019_refused_without_release(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.assert_window("2020-01-02", release=tmp_path / "HOLDOUT_RELEASE_v2.json")
    v2.assert_window("2019-12-31", release=tmp_path / "x.json")       # D window allowed


def test_uncommitted_release_file_does_not_unlock(tmp_path):
    rel = tmp_path / "HOLDOUT_RELEASE_v2.json"; rel.write_text("{}")
    with pytest.raises(Exception):     # not inside the repo -> not committed -> refused
        v2.seal_guard(SEALED, release=rel)


def _setup(n=420, drop_at=None, wash=None, start="2010-01-04"):
    """rel flat at 1.0 (always near its high); optional drop to 0.9 at index drop_at (crosses below SMA50).
    Breadth: 0.5 with 126-day max 1.0 (armed when breadth key used). wash=(first, length): breadth <= 25% for
    `length` closes from `first`, then 0.5."""
    s = pd.bdate_range(start, periods=n)
    rel = np.ones(n)
    if drop_at is not None:
        rel[drop_at:] = 0.9
    br = np.full(n, 0.5); runp = np.zeros(n)
    if wash:
        f, L = wash
        br[f:f + L] = 0.2
        runp[f + L] = L
    bd = {"br": pd.Series(br, index=s), "bmax": pd.Series(1.0, index=s), "wash_run_prev": pd.Series(runp, index=s)}
    return s, pd.Series(rel, index=s), bd


def test_same_day_defend_and_attack_defend_wins_and_counted():
    s, rel, bd = _setup(drop_at=300, wash=(290, 10))
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert st.iloc[300] == v2.DEFEND and log["conflicts"] == 1


def test_washout_clock_from_first_close_and_expiry():
    s, rel, bd = _setup(wash=(250, 20))
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert st.iloc[270] == v2.ATTACK and log["wash_fired"] == 1
    s, rel, bd = _setup(wash=(250, 21))
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert (st.dropna() != v2.ATTACK).all() and log["wash_expired"] == 1


def test_attack_exits_at_first_month_end_63_sessions_after_entry():
    s, rel, bd = _setup(wash=(150, 5))
    st = v2.h1_states(rel, bd, 5, 25)
    e = s[155]
    out = st[st.index > e]
    first_neutral = out[out == v2.NEUTRAL].index[0]
    me = pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s
    assert me[first_neutral] and s.get_loc(first_neutral) - 155 >= 63
    assert s.get_loc(first_neutral) - 155 < 63 + 23


def test_defend_set_on_month_end_is_not_exited_that_day_and_exits_on_a_later_month_end_above_sma():
    s = pd.bdate_range("2010-01-04", periods=420)
    me_idx = [i for i in range(300, 330) if (s[i] + pd.offsets.BDay(1)).month != s[i].month][0]
    _, rel, bd = _setup(drop_at=me_idx)
    rel.iloc[me_idx + 30:] = 1.2             # back above its SMA later
    st = v2.h1_states(rel, bd, 5, 25)
    assert st.iloc[me_idx] == v2.DEFEND
    later = st.iloc[me_idx + 1:]
    exit_day = later[later == v2.NEUTRAL].index[0]
    me = pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s
    assert me[exit_day] and exit_day > s[me_idx]


def test_price_only_control_ignores_breadth_key():
    s, rel, bd = _setup(drop_at=300)
    bd["br"][:] = 0.99                    # breadth never fallen: H1 not armed
    assert (v2.h1_states(rel, bd, 5, 25).dropna() != v2.DEFEND).all()
    assert v2.h1_states(rel, bd, 5, 25, use_breadth=False).iloc[300] == v2.DEFEND


def test_matched_mix_rebuilt_per_resample():
    rng = np.random.default_rng(0)
    r = rng.normal(0, 0.01, (2, 50)); L = rng.normal(0, 0.01, (2, 50, 4))
    W = np.zeros((2, 50, 4)); W[0, :25, 0] = 1; W[0, 25:, 3] = 1; W[1, :, 0] = 1
    st = v2.matched_mix_stat(r, W, L)
    ref0 = (W[0].mean(axis=0) * L[0]).sum(axis=1)
    assert st[0] == pytest.approx((r[0] - ref0).mean() * 252)
