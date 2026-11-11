"""Rotation Core v2: seal refusal and state-machine precedence (synthetic; no market outcome)."""
from pathlib import Path
import numpy as np
import pandas as pd
import json as _json
import pytest
from engine import rotation_core_v2 as v2

SEALED = "/home/ubuntu2/tmp/rotation-core/data/french/sealed_post2019/49_Industry_Portfolios_Daily.csv"


def test_sealed_path_refused_outside_the_verified_stage2_run(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.seal_guard(SEALED)
    with v2.stage2_opened([], recorded={}):            # the runner's verified context opens the loaders
        v2.seal_guard(SEALED)
    with pytest.raises(v2.SealedRefusal):              # and closes them on exit
        v2.seal_guard(SEALED)


def test_loader_refuses_sealed_path_before_reading():
    with pytest.raises(v2.SealedRefusal):
        v2.load_french_industries(SEALED, "2019-12-31")


def test_window_after_2019_refused_without_release(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.assert_window("2020-01-02")
    v2.assert_window("2019-12-31")   # D window allowed


def test_uncommitted_release_file_does_not_unlock(tmp_path):
    rel = tmp_path / "HOLDOUT_RELEASE_v2_stage2.json"; rel.write_text(_json.dumps({"windows_released": ["2020-01-02..2025-12-31"]}))
    assert v2._load_release(rel) is None     # not inside the repo -> not committed -> never a release
    with pytest.raises(v2.SealedRefusal):
        v2.seal_guard(SEALED)


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


def test_frozen_v2_header_accepted_and_one_byte_change_refused(tmp_path):
    from engine import rotation_core_evaluation as rc
    h = v2.verify_header_v2()
    assert h["status"].startswith("FROZEN")
    raw = bytearray(v2.HEADER_V2.read_bytes()); raw[-2] = ord(" ") if raw[-2] != ord(" ") else ord("\t")
    bad = tmp_path / "h.json"; bad.write_bytes(bytes(raw))
    with pytest.raises(rc.HeaderMismatch):
        v2.verify_header_v2(bad)


# ------------------------------------------------------------------ R13 staged release
import json as _json
from tests.rotation_core_v2_fixture import make_fixture


def _rel(tmp_path, name, windows, **kw):
    p = tmp_path / name; p.write_text(_json.dumps({"windows_released": windows, **kw})); return p


ORIG_SELECTION = v2.ROOT / "research/rotation_core/results_v2_selection.json"


@pytest.fixture(autouse=True)
def _selection_points_at_committed_original(monkeypatch):
    # until the R15 rerun exists, tests read the committed 1ca5228b3c selection file
    monkeypatch.setattr(v2, "SELECTION_RESULT", ORIG_SELECTION)


def _good_release(tmp_path, name="r1.json", **over):
    body = {"windows_released": [v2.W_PRE], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
            "selected_grid_point": {"h_near_high_pct": 3, "b_breadth_drop_pp": 25}, "engine_commit": "X",
            "selection_results_commit": "HEAD",
            "selection_results_sha256": __import__("hashlib").sha256(ORIG_SELECTION.read_bytes()).hexdigest()}
    body.update(over)
    p = tmp_path / name; p.write_text(_json.dumps(body)); return p


def test_stage1_release_checks_window_header_config_and_engine_commit(tmp_path, monkeypatch):
    with pytest.raises(v2.SealedRefusal):
        v2.stage1_release(tmp_path / "missing.json", selection=ORIG_SELECTION)
    monkeypatch.setattr(v2, "_committed_clean", lambda p, root=None: True)
    monkeypatch.setattr(v2, "check_engine_commit", lambda c: None)
    assert v2.stage1_release(_good_release(tmp_path), selection=ORIG_SELECTION)
    with pytest.raises(v2.SealedRefusal):         # selection file differs at the named commit
        v2.stage1_release(_good_release(tmp_path, "badsel.json", selection_results_commit="4d49b23a8f"), selection=ORIG_SELECTION)
    for over in ({"windows_released": [v2.W_PRE, v2.W_H]}, {"windows_released": [v2.W_H]},
                 {"protocol_header_sha256": "0" * 64}, {"selected_grid_point": {"h_near_high_pct": 5, "b_breadth_drop_pp": 25}}):
        with pytest.raises(v2.SealedRefusal):
            v2.stage1_release(_good_release(tmp_path, "bad.json", **over), selection=ORIG_SELECTION)


def test_engine_commit_check_refuses_other_commit():
    with pytest.raises(v2.SealedRefusal):
        v2.check_engine_commit("4d49b23a8f0246718fd48a24b4124c35129a1cfe")      # v1 data pin: engine differs


def test_selected_setting_read_from_committed_selection():
    assert v2.selected_setting(ORIG_SELECTION) == (3.0, 25.0)


def test_uncommitted_release_never_counts(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.stage1_release(_good_release(tmp_path), selection=ORIG_SELECTION)          # exists but not committed in the repo


def test_stage1_cannot_read_1998_or_the_sealed_path(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.assert_stage1_window("1998-01-02")
    v2.assert_stage1_window("1997-12-31")
    with pytest.raises(v2.SealedRefusal):
        v2.seal_guard(SEALED)


def test_stage1_loader_truncates_at_1997(tmp_path):
    fx = make_fixture(tmp_path / "fx", extra_after="1999-06-30")
    vw, _ = v2.load_french_industries(fx / "49_Industry_Portfolios_Daily.csv", v2.PRE_END)
    assert vw.index.max() <= v2.PRE_END


def test_stage2_refused_without_second_release(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.verify_release2(v2._load_release(tmp_path / "none.json"), [])


def test_stage2_release_with_wrong_window_refused(tmp_path):
    with pytest.raises(v2.SealedRefusal):
        v2.verify_release2({"windows_released": [v2.W_PRE]}, [])


def test_gate_statistic_is_the_same_function_as_the_era_point_estimate(tmp_path):
    """R13-g.3: window_excess (gate, conjunction) equals matched_contrast's era point estimate."""
    import scripts.run_rotation_core_v2 as run
    fx = make_fixture(tmp_path / "fx", start="1940-01-01")
    D = run.build(fx / "49_Industry_Portfolios_Daily.csv", fx / "F-F_Research_Data_Factors_daily.csv", v2.PRE_END, 3.0, 25.0)
    for reading in ("eq", "drift"):
        for cost in ("base", "strict"):
            bks, LR = run.run_books(D["legs"], D["states"], D["rf"], v2.PRE_END, reading, cost)
            for k in ("H1", "H3"):
                idx = bks[k].returns.index
                for a_, z in (("1950-01-03", "1969-12-31"), ("1970-01-02", "1997-12-31")):
                    m = pd.Series((idx >= a_) & (idx <= z), index=idx)
                    mc = v2.matched_contrast(bks[k], LR, D["rf"], m, B=5)
                    assert v2.window_excess(bks[k], LR, D["rf"], a_, z) == pytest.approx(mc["observed"], abs=1e-15)


def test_R14_drift_base_hand_example():
    s_ = pd.bdate_range("2001-01-01", periods=600)
    rng = np.random.default_rng(2)
    vw = pd.DataFrame(rng.normal(0, 0.01, (600, 6)), index=s_, columns=list("ABCDEF"))
    mkt = vw.mean(axis=1)
    legs = v2.form_legs(vw, mkt, min_valid=100, min_pairs=60)
    t = sorted(legs.formed)[3]
    nxt = sorted(legs.formed)[4]
    days = s_[(s_ > t) & (s_ <= nxt)]
    mem = legs.formed[t][2]
    x = vw.loc[days, mem].to_numpy()
    w = np.full(len(mem), 1 / len(mem)); exp = []
    for row in x:
        exp.append(float(w @ row)); w = w * (1 + row); w = w / w.sum()
    got = legs.returns.loc[days, "BASE_DRIFT"].to_numpy()
    assert got[1:] == pytest.approx(exp[1:])                      # day 0 also carries the re-formation cost
    assert legs.returns.loc[days[1:], "BASE"].to_numpy() == pytest.approx(x[1:].mean(axis=1))


def test_F1_yahoo_loader_filters_before_any_frame_and_refuses_after_2019(tmp_path):
    s_ = pd.bdate_range("2019-12-20", "2020-01-10")
    df = pd.DataFrame({"Adj Close": np.arange(len(s_), dtype=float) + 1}, index=pd.DatetimeIndex(s_, name="Date"))
    p = tmp_path / "X.parquet"; df.to_parquet(p)
    x = v2.load_yahoo_tr(p, "2019-12-31")
    assert x.index.max() <= pd.Timestamp("2019-12-31")
    with pytest.raises(v2.SealedRefusal):
        v2.load_yahoo_tr(p, "2020-01-03")


def test_F3_false_pivot_uses_held_state_not_decided_state():
    import scripts.run_rotation_core_v2 as run
    from engine import rotation_core_evaluation as rc
    s_ = pd.bdate_range("2005-01-03", periods=6)
    R = pd.DataFrame(0.0, index=s_, columns=["OFF", "DEF", "BASE"])
    tgt = pd.DataFrame({"OFF": [0, 0, 0, 0, 0, 0.], "DEF": [0, 0, 1, 1, 1, 1.], "BASE": [1, 1, 0, 0, 0, 0.]}, index=s_)
    bk = rc.simulate(tgt, R, pd.Series(0.0, index=s_), 0.0, "f3", equity_cols=("OFF", "DEF", "BASE"))
    w = run.held_risk_on(bk)
    assert w.round(9).tolist() == [0.0, 1.0, 1.0, 0.0, 0.0, 0.0]   # DEFEND decided day 2 is held from day 3's close


# ------------------------------------------------------------------ R16 S2-S4, S9, S10
def test_S2_no_trivial_arming_or_trigger_right_after_first_formation():
    s_ = pd.bdate_range("2001-01-01", periods=300)
    R = pd.DataFrame(np.nan, index=s_, columns=["OFF", "DEF", "BASE"])
    R.iloc[272:] = 0.0
    R.iloc[273, 0] = -0.01                            # their reproduction: 1% dip two sessions after formation
    legs = v2.Legs({s_[271]: (["A"], ["B"], ["A", "B"])}, R, R.notna().astype(int), 0)
    rel = v2.relative_line(legs)
    assert rel.iloc[:272].isna().all()
    bd = {"br": pd.Series(0.5, index=s_), "bmax": pd.Series(1.0, index=s_),
          "wash_run_prev": pd.Series(np.nan, index=s_), "wash_from_low": pd.Series(np.nan, index=s_)}
    st, log = v2.h1_states(rel, bd, 3, 25, return_log=True)
    assert (st.dropna() == v2.NEUTRAL).all() and st.iloc[273] == v2.NEUTRAL
    assert st.iloc[:272].isna().all() and st.iloc[272] == v2.NEUTRAL


def test_S2_h3_momentum_needs_126_formed_sessions():
    s_ = pd.bdate_range("2001-01-01", periods=420)
    R = pd.DataFrame(np.nan, index=s_, columns=["OFF", "DEF", "BASE"]); R.iloc[272:] = 0.001
    legs = v2.Legs({s_[271]: (["A"], ["B"], ["A", "B"])}, R, R.notna().astype(int), 0)
    st = v2.h3_states(legs)
    assert st.iloc[: 272 + 126].isna().all()


def test_S3_sma_over_last_50_observed_closes_and_missing_day_excluded():
    s_ = pd.bdate_range("2001-01-01", periods=80)
    x = pd.Series(0.01, index=s_); x.iloc[60] = np.nan
    lvl, sma = v2.observed_level_sma(x.to_frame("A"), 50)
    obs = (1 + x.dropna()).cumprod()
    assert np.isnan(lvl.iloc[60, 0]) and np.isnan(sma.iloc[60, 0])
    assert sma.iloc[79, 0] == pytest.approx(obs.iloc[-50:].mean())
    assert lvl.iloc[61, 0] == pytest.approx(1.01 ** 61)          # carries: 61 observed returns, no 0% close


def test_S4_held_leg_hand_example():
    blk = np.array([[1.0, -0.5], [-0.5, 1.0]])
    eq = np.prod(1 + blk.mean(axis=1)) - 1
    held = np.prod(1 + v2.held_leg_returns(blk)) - 1
    assert eq == pytest.approx(0.5625) and held == pytest.approx(0.0)


def test_S4_drift_reading_replaces_all_three_legs():
    R = pd.DataFrame({c: [0.1 * i] for i, c in enumerate(["OFF", "DEF", "BASE", "OFF_DRIFT", "DEF_DRIFT", "BASE_DRIFT"])})
    d = v2.base_view(R, "drift")
    assert d.iloc[0].tolist() == pytest.approx([0.3, 0.4, 0.5]) and list(d.columns) == ["OFF", "DEF", "BASE"]


def test_S9_arming_memory_boundary_21_sessions():
    n = 200; s_ = pd.bdate_range("2001-01-01", periods=n)
    for age, expect in ((21, v2.DEFEND), (22, v2.NEUTRAL)):
        rel = pd.Series(1.0, index=s_); rel.iloc[180:] = 0.9          # cross-down at 180
        br = pd.Series(1.0, index=s_); br.iloc[180 - age] = 0.5         # breadth key armed only at 180-age
        bd = {"br": br, "bmax": pd.Series(1.0, index=s_), "wash_run_prev": pd.Series(np.nan, index=s_),
              "wash_from_low": pd.Series(np.nan, index=s_)}
        assert v2.h1_states(rel, bd, 5, 25).iloc[180] == expect, age


def test_S10_leg_observed_if_any_member_has_a_close_simulate_states_defers_otherwise():
    s_ = pd.bdate_range("2001-01-01", periods=5)
    R = pd.DataFrame(0.0, index=s_, columns=["OFF", "DEF", "BASE", "OFF_DRIFT", "DEF_DRIFT", "BASE_DRIFT"])
    V = pd.DataFrame(1, index=s_, columns=R.columns); V.loc[s_[2], "DEF"] = 0      # no DEF member closed on day 2
    legs = v2.Legs({}, R, V, 0)
    st = pd.Series([0, 1, np.nan, np.nan, np.nan], index=s_, dtype=float)
    bk = v2.simulate_states(st, legs, pd.Series(0.0, index=s_), s_[0], s_[-1])
    assert bk.meta["deferred_executions"] == 1 and bk.traded.iloc[2] == 0 and bk.traded.iloc[3] > 0
