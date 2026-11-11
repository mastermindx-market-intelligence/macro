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


def _setup(n=420, drop_at=None, wash=None, start="2010-01-04", rel_low=None):
    """rel flat at 1.0 (always near its high); optional drop to 0.9 at index drop_at (crosses below SMA50).
    Breadth: 0.5 with 126-day max 1.0 (armed when breadth key used). wash=(first, length): breadth <= 25% for
    `length` closes from `first`, then 0.5."""
    s = pd.bdate_range(start, periods=n)
    rel = np.ones(n)
    if drop_at is not None:
        rel[drop_at:] = 0.9
    if rel_low is not None:                      # rel_low = (index, value): rel near its 126-session low there
        rel[:] = 1.5
        rel[rel_low[0]:] = rel_low[1]
    br = np.full(n, 0.5)
    if wash:
        f, L = wash[:2]
        br[f:f + L] = 0.2
        if len(wash) > 2:
            br[f + wash[2]] = 0.1                 # the spell's low
    rl, fl = v2.washout_spells(br)
    bd = {"br": pd.Series(br, index=s), "bmax": pd.Series(1.0, index=s), "wash_run_prev": pd.Series(rl, index=s),
          "wash_from_low": pd.Series(fl, index=s)}
    return s, pd.Series(rel, index=s), bd


def test_same_day_defend_and_attack_defend_wins_and_counted():
    s, rel, bd = _setup(drop_at=300, wash=(290, 10))
    rel.iloc[290:300] = rel.iloc[290:300].values      # flat line = at its 126-session low and high: qualifies
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert st.iloc[300] == v2.DEFEND and log["conflicts"] == 1


def test_washout_trough_clock():
    # long spell (60 closes) whose low is 10 closes before recovery: fires
    s, rel, bd = _setup(wash=(250, 60, 50), rel_low=(240, 1.0))
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert st.iloc[310] == v2.ATTACK and log["wash_fired"] == 1
    # same spell with its low 40 closes before recovery: slow crawl back, no ATTACK
    s, rel, bd = _setup(wash=(250, 60, 20), rel_low=(240, 1.0))
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert (st.dropna() != v2.ATTACK).all() and log["wash_expired"] == 1 and log["wash_qualified"] == 1


def test_washout_spells_tie_uses_earliest_low_and_only_past_closes():
    sh = np.array([0.5, 0.2, 0.1, 0.1, 0.2, 0.3, 0.5])
    rl, fl = v2.washout_spells(sh)
    assert rl[5] == 4 and fl[5] == 3            # low at index 2 (earliest tie), recovery at 5
    assert np.isnan(rl[:5]).all() and np.isnan(rl[6])


def test_attack_exits_at_first_month_end_63_sessions_after_entry():
    s, rel, bd = _setup(wash=(150, 5), rel_low=(140, 1.0))
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


# ------------------------------------------------------------------ R12: relative line near its 126-session low
def _r12(qual_at=None, spell=(250, 10), low_offset=None, n=420):
    """Relative line at 1.5 (far above its low) except closes listed in qual_at, which drop to its 126-low level.
    Breadth washout spell = (first, length); optional extra-low breadth close at first+low_offset."""
    s = pd.bdate_range("2010-01-04", periods=n)
    rel = np.full(n, 1.5); rel[:130] = 1.0                       # sets a 126-session low of 1.0 before the spell
    rel[130:] = np.linspace(1.5, 3.0, n - 130)                   # rising: never near its own 126-session low
    lo_val = 1.0
    if qual_at:
        for q in qual_at:
            rel[q] = lo_val
        rel[:130] = 1.0
    br = np.full(n, 0.5); f, L = spell; br[f:f + L] = 0.2
    if low_offset is not None:
        br[f + low_offset] = 0.1
    rl, fl = v2.washout_spells(br)
    bd = {"br": pd.Series(br, index=s), "bmax": pd.Series(1.0, index=s), "wash_run_prev": pd.Series(rl, index=s),
          "wash_from_low": pd.Series(fl, index=s)}
    return s, pd.Series(rel, index=s), bd


def test_R12_qualifying_spell_fires_and_non_qualifying_does_not():
    s, rel, bd = _r12(qual_at=[255])
    # 126-session low over 130..255 window: rel at 255 equals 1.0 and earlier 1.0 values fall out of window -> low
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert log["wash_qualified"] == 1 and st.iloc[260] == v2.ATTACK
    s, rel, bd = _r12(qual_at=None)
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert log["wash_qualified"] == 0 and (st.dropna() != v2.ATTACK).all()


def test_R12_qualifies_on_first_and_on_last_close_of_spell_not_only_the_low_close():
    for q in (250, 259):            # first and last close of the spell (spell = 250..259); breadth low at 253
        s, rel, bd = _r12(qual_at=[q], low_offset=3)
        st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
        assert log["wash_qualified"] == 1 and st.iloc[260] == v2.ATTACK, q


def test_R12_close_outside_spell_does_not_qualify():
    s, rel, bd = _r12(qual_at=[249])            # the close just before the spell starts
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert log["wash_qualified"] == 0


def test_R12_twenty_session_limit_still_measured_from_breadth_low():
    s, rel, bd = _r12(qual_at=[252], spell=(250, 40), low_offset=2)    # low 38 sessions before recovery
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert log["wash_qualified"] == 1 and log["wash_fired"] == 0
    s, rel, bd = _r12(qual_at=[252], spell=(250, 40), low_offset=30)   # low 10 sessions before recovery
    st, log = v2.h1_states(rel, bd, 5, 25, return_log=True)
    assert log["wash_fired"] == 1 and st.iloc[290] == v2.ATTACK


def test_R12_near_low_formula_is_the_literal_mirror():
    import inspect
    src = inspect.getsource(v2.h1_states)
    assert "near = (rel >= (1 - h / 100) * hi)" in src
    assert "near_low = (rel <= (1 + h / 100) * lo126)" in src and "rolling(126, min_periods=126).min()" in src
