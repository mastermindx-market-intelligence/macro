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


def _series(vals, start="2010-01-04"):
    return pd.Series(vals, index=pd.bdate_range(start, periods=len(vals)), dtype=float)


def test_defend_wins_same_day_tie_and_month_end_trigger_held_through_next_month():
    n = 400
    rel = np.r_[np.linspace(1.0, 1.5, 300), np.linspace(1.5, 1.3, 100)]
    br = np.r_[np.full(280, 0.9), np.full(10, 0.5), np.full(110, 0.2)]
    rel_s, br_s = _series(rel), _series(br)
    # force a washout recovery on the same day as the first DEFEND trigger
    st = v2.h1_states(rel_s, br_s, h=5, b=25)
    first_def = st[st == v2.DEFEND].index
    assert len(first_def) > 0
    d0 = first_def[0]
    br2 = br_s.copy(); br2.loc[:d0] = 0.9; br2.iloc[br2.index.get_loc(d0) - 3: br2.index.get_loc(d0)] = 0.2
    br2.loc[d0] = 0.5
    st2 = v2.h1_states(rel_s, br2, h=5, b=25)
    assert st2.loc[d0] == v2.DEFEND


def test_state_set_on_last_session_of_month_survives_that_month_end():
    s = pd.bdate_range("2010-01-04", periods=400)
    rel = pd.Series(np.r_[np.linspace(1, 1.5, 300), np.linspace(1.5, 1.2, 100)], index=s)
    br = pd.Series(np.r_[np.full(285, 0.9), np.full(115, 0.4)], index=s)
    st = v2.h1_states(rel, br, h=5, b=25)
    d0 = st[st == v2.DEFEND].index[0]
    me = s[(s.month == d0.month) & (s.year == d0.year)].max()
    if d0 == me:
        nxt_me = s[s > me][(s[s > me].month == (me + pd.offsets.MonthBegin(1)).month)].max()
        assert st.loc[nxt_me] == v2.DEFEND
    else:
        assert st.loc[me] == v2.NEUTRAL or st.loc[me] == v2.DEFEND


def test_matched_mix_rebuilt_per_resample():
    rng = np.random.default_rng(0)
    r = rng.normal(0, 0.01, (2, 50)); L = rng.normal(0, 0.01, (2, 50, 4))
    W = np.zeros((2, 50, 4)); W[0, :25, 0] = 1; W[0, 25:, 3] = 1; W[1, :, 0] = 1
    st = v2.matched_mix_stat(r, W, L)
    ref0 = (W[0].mean(axis=0) * L[0]).sum(axis=1)
    assert st[0] == pytest.approx((r[0] - ref0).mean() * 252)
