"""Rotation Core v2 confirmation machinery (R16-R20). Synthetic fixtures only: no market outcome is computed on real
data by any test here."""
import io, json, contextlib, subprocess, re, os, sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from engine import rotation_core_evaluation as rc
from engine import rotation_core_v2 as v2
from tests.rotation_core_v2_fixture import make_fixture, make_fund_fixture, fixture_texts

ORIG_SELECTION = v2.ROOT / "research/rotation_core/results_v2_selection.json"
IND, FAC = "49_Industry_Portfolios_Daily.csv", "F-F_Research_Data_Factors_daily.csv"


@pytest.fixture(autouse=True)
def _sel(monkeypatch):
    monkeypatch.setattr(v2, "SELECTION_RESULT", ORIG_SELECTION)


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    d = tmp_path_factory.mktemp("conf")
    return make_fixture(d / "fx")


def _s1(led, ind, fac, engine="E1", release_sha="r1", release=None, **k):
    import scripts.run_rotation_core_v2 as run
    lines, buf, err = [], io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        e = run.stage1_command(led, release or {}, release_sha, engine, ind, fac, {"industries": "x"}, B_=k.pop("B_", 20),
                               out=lambda s: (lines.append(s), print(s)), **k)
    return e, lines, buf.getvalue() + err.getvalue()


@pytest.fixture(scope="module")
def stage1(fx, tmp_path_factory):
    v2.SELECTION_RESULT = ORIG_SELECTION
    d = tmp_path_factory.mktemp("s1")
    led = v2.MemoryLedger()
    e, lines, captured = _s1(led, fx / IND, fx / FAC, publish_path=d / "published.json")
    return d, e, lines, captured, led


@pytest.fixture(scope="module")
def pre(fx):
    import scripts.run_rotation_core_v2 as run
    v2.SELECTION_RESULT = ORIG_SELECTION
    return run.pre1998_report(fx / IND, fx / FAC, B_=20)


# ------------------------------------------------------------------ R18 strict run, O1(i)
def test_R18_strict_book_never_above_base_and_strict_mix_never_below(pre):
    import scripts.run_rotation_core_v2 as run
    assert pre["violations"] == 0
    a, z = run.PRE_START, v2.PRE_END
    for reading in run.READINGS:
        bb, Lb = pre["runs"][(reading, "base")]; bs, Ls = pre["runs"][(reading, "strict")]
        for k in bb:
            _, rb, Wb, Lb_ = v2.window_arrays(bb[k], Lb, pre["rf"], a, z)
            _, rs, Ws, Ls_ = v2.window_arrays(bs[k], Ls, pre["rf"], a, z)
            assert np.all(rs <= rb + 1e-12)
            assert np.all(v2.mix_series(Ws, Ls_) >= v2.mix_series(Wb, Lb_) - 1e-12)
        # the strict book pays strictly more somewhere (re-formation at 2x is real, not a no-op)
        assert (bs["H1"].returns.loc[a:z] < bb["H1"].returns.loc[a:z] - 1e-12).sum() > 100


def test_R18_violation_counter_detects_a_breach(pre):
    import scripts.run_rotation_core_v2 as run
    runs = dict(pre["runs"])
    bs, Ls = runs[("eq", "strict")]
    bad = dict(bs); h = bad["H1"]
    r2 = h.returns.copy(); r2.iloc[-5] += 0.01
    bad["H1"] = rc.Book(h.name, r2, h.risky_weight, h.equity_weight, h.holdings, h.traded, h.costs, h.meta, h.post_holdings)
    runs[("eq", "strict")] = (bad, Ls)
    assert run.strict_inequality_violations(runs, pre["rf"], run.PRE_START, v2.PRE_END) == 1


def test_R18_base_view_identities():
    s = pd.bdate_range("2001-01-01", periods=3)
    lr = pd.DataFrame({"OFF": [0.01, 0.02, 0.0], "DEF": [0.0, 0.0, 0.0], "BASE": [0.0, 0.0, 0.0],
                       "OFF_TURN": [0.5, 0.0, 0.0], "DEF_TURN": [0.0, 0.0, 0.0], "BASE_TURN": [0.0, 0.0, 0.0]}, index=s)
    g = v2.base_view(lr, kind="gross", formed_fee_bp=10)
    assert g.loc[s[0], "OFF"] == pytest.approx(1.01 * (1 + 0.5 * 0.001) - 1)
    bk = v2.base_view(lr, kind="book", formed_fee_bp=10, book_fee_bp=20)
    assert bk.loc[s[0], "OFF"] == pytest.approx(1.01 * (1 + 0.5 * 0.001) / (1 + 0.5 * 0.002) - 1)
    assert (bk <= v2.base_view(lr) + 1e-15).all().all() and (g >= v2.base_view(lr) - 1e-15).all().all()


def test_O1_states_identical_at_10_and_20bp_signal_line_computed_once(fx, pre):
    import scripts.run_rotation_core_v2 as run
    assert run.states_identical_across_costs(pre["runs"])
    for reading in run.READINGS:                       # identical start-of-day holdings in both cost runs
        bb, _ = pre["runs"][(reading, "base")]; bs, _ = pre["runs"][(reading, "strict")]
        for k in bb:
            pd.testing.assert_frame_equal(bb[k].holdings.round(12), bs[k].holdings.round(12))
    # the state functions take no cost argument: the 10 bp net relative line is the only signal input
    import inspect
    for f in (v2.h1_states, v2.h3_states, v2.relative_line):
        assert "fee" not in str(inspect.signature(f))


# ------------------------------------------------------------------ S6 blind stage 1, O5
def _no_magnitude(text):
    """No decimal number outside the library-version lines (versions are not magnitudes)."""
    body = "\n".join(ln for ln in text.splitlines() if " version " not in ln)
    return not re.search(r"\d\.\d", body)


def test_S6_stage1_prints_only_signs_counts_and_hex(stage1):
    d, e, lines, captured, led = stage1
    assert _no_magnitude(captured), "a decimal number reached stdout/stderr"
    signs = [ln for ln in lines if ln.startswith("GATE_SIGN")]
    assert len(signs) == 16
    assert all(ln.split()[-1] in {"+", "-", "NaN"} for ln in signs)
    assert not any("H2" in ln and ln.startswith("GATE_SIGN") for ln in lines)          # S1c: H2 signs not printed
    ents = led.entries()
    assert [x["kind"] for x in ents] == ["START", "PHASE_A_CLEAN", "GATE"]
    assert "H2_signs" not in json.dumps(ents) and not any(k.startswith("H2|") for k in e["gate_signs"])
    assert not list(d.glob("sealed*")), "S6: no magnitudes file"


def test_S6_magnitudes_hash_reproduced_and_changes_with_input(fx, stage1, tmp_path):
    import scripts.run_rotation_core_v2 as run
    d, e, lines, _, led = stage1
    again = run.pre1998_report(fx / IND, fx / FAC, B_=20)
    v2.verify_reproduction(again["magnitudes"], e["magnitudes_sha256"])
    fx2 = make_fixture(tmp_path / "fx2")
    t = (fx2 / IND).read_text().splitlines()
    i = next(j for j, ln in enumerate(t) if ln.startswith("19500103,"))
    p = t[i].split(","); p[5] = f"{float(p[5]) + 0.01:.2f}"; t[i] = ",".join(p)
    (fx2 / IND).write_text("\n".join(t) + "\n")
    other = run.pre1998_report(fx2 / IND, fx2 / FAC, B_=20)
    with pytest.raises(v2.SealedRefusal):
        v2.verify_reproduction(other["magnitudes"], e["magnitudes_sha256"])


def test_S6_closed_gate_publishes_at_once(stage1):
    d, e, lines, _, led = stage1
    if e["gate_open"]:
        assert not (d / "published.json").exists()
    else:
        pub = json.loads((d / "published.json").read_text())
        assert pub["magnitudes_sha256"] == e["magnitudes_sha256"]


def test_S6_exception_text_carries_no_value(fx, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    def boom(*a, **k):
        raise ValueError("excess 0.0123 leaked")
    for fn, kinds in (("prepare_pre1998", ["START"]), ("pre1998_stats", ["START", "PHASE_A_CLEAN"])):
        led = v2.MemoryLedger()
        with monkeypatch.context() as m:
            m.setattr(run, fn, boom)
            with pytest.raises(SystemExit) as ei:
                _s1(led, fx / IND, fx / FAC)
            assert "0.0123" not in str(ei.value) and "withheld" in str(ei.value)
        assert [x["kind"] for x in led.entries()] == kinds     # R20.11: a sign-phase failure is never an abort


def test_O5_nan_is_neither_sign_and_fails_closed():
    import scripts.run_rotation_core_v2 as run
    assert v2.sign(float("nan")) == "NaN" and v2.sign(0.0) == "-" and v2.sign(1e-9) == "+"
    signs = {f"{h}|{e}|{r}|{c}": "+" for h in ("H1", "H3") for e in run.ERAS for r in run.READINGS for c in run.COST_RUNS}
    assert run.gate_decision(signs)[0] is True
    s2 = dict(signs); s2["H1|E1_1928_1945|eq|base"] = "NaN"; s2["H3|E2_1946_1997|drift|strict"] = "-"
    assert run.gate_decision(s2) == (False, {"H1": False, "H3": False})


def test_gate_needs_all_eight_signs_of_one_hypothesis():
    import scripts.run_rotation_core_v2 as run
    keys = [f"{h}|{e}|{r}|{c}" for h in ("H1", "H3") for e in run.ERAS for r in run.READINGS for c in run.COST_RUNS]
    nan0 = {k: 0 for k in keys}
    for k in keys:                      # every single '-' in H1 with H3 all '-' closes the gate
        s = {x: ("+" if x.startswith("H1") else "-") for x in keys}
        if k.startswith("H1"):
            s[k] = "-"
            assert run.gate_decision(s)[0] is False



def test_S1c_stage1_release_opening_list_is_the_constant(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "_committed_clean", lambda p: True)
    monkeypatch.setattr(v2, "check_engine_commit", lambda c: None)
    import hashlib
    body = {"windows_released": [v2.W_PRE], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
            "selected_grid_point": {"h_near_high_pct": 3, "b_breadth_drop_pp": 25}, "engine_commit": "X",
            "selection_results_commit": "HEAD",
            "selection_results_sha256": hashlib.sha256(ORIG_SELECTION.read_bytes()).hexdigest()}
    p = tmp_path / "r1.json"; p.write_text(json.dumps(dict(body, opening_condition_hypotheses=["H1", "H3", "H2"])))
    with pytest.raises(v2.SealedRefusal):
        v2.stage1_release(p)
    p.write_text(json.dumps(dict(body, selection_results_sha256="0" * 64)))
    with pytest.raises(v2.SealedRefusal):                                   # S5: selection pinned by sha256
        v2.stage1_release(p)
    p.write_text(json.dumps(body))
    assert v2.stage1_release(p)


# ------------------------------------------------------------------ S5 remote containment
def test_S5_local_only_commit_is_not_a_release(monkeypatch):
    calls = []
    def fake_git(*a, check=True, root=None, env=None, input=None):
        calls.append(a)
        if a[0] == "log":
            return subprocess.CompletedProcess(a, 0, b"deadbeef\n", b"")
        return subprocess.CompletedProcess(a, 1, b"", b"")         # merge-base --is-ancestor: not contained
    monkeypatch.setattr(v2, "_git", fake_git)
    with pytest.raises(v2.SealedRefusal):
        v2.on_remote(v2.RELEASE, "f" * 40)
    assert any(c[0] == "merge-base" and c[-1] == "f" * 40 for c in calls)


def test_S5_engine_commit_pins_header_and_runner_inputs():
    assert "research/rotation_core/protocol_header_v2.json" in v2.PINNED_PATHS
    assert {"engine", "scripts", "tests"} <= set(v2.PINNED_PATHS)


# ------------------------------------------------------------------ O6 manifest
def test_O6_manifest_refuses_changed_input_or_versions(fx):
    ins = {"industries": fx / IND, "factors": fx / FAC}
    good = {"inputs_sha256": {k: v2.sha256_file(p) for k, p in ins.items()}, "versions": v2.versions()}
    assert v2.check_manifest(good, ins) == good["inputs_sha256"]
    with pytest.raises(v2.SealedRefusal):
        v2.check_manifest(dict(good, inputs_sha256=dict(good["inputs_sha256"], factors="0" * 64)), ins)
    with pytest.raises(v2.SealedRefusal):
        v2.check_manifest(dict(good, versions=dict(good["versions"], numpy="0.0")), ins)


# ------------------------------------------------------------------ S1: final conjunction
def _passing_inputs():
    import scripts.run_rotation_core_v2 as run
    rcs = [f"{r}|{c}" for r in run.READINGS for c in run.COST_RUNS]
    holm = {f"{k}|{cv}": {h: {"reject_h0": True} for h in run.HYPS} for k in rcs for cv in run.CONVENTIONS}
    point = {k: {h: {"pre1998": 0.01, "E1_1928_1945": 0.01, "E2_1946_1997": 0.01, "h2020_2025": 0.01} for h in run.HYPS}
             for k in rcs}
    dd = {k: {h: {"pre1998": (-0.2, -0.3), "h2020_2025": (-0.2, -0.3)} for h in run.HYPS} for k in rcs}
    return {"holm": holm, "point": point, "drawdown": dd, "integrity_ok": True}


def test_S1_conjunction_pass_case_and_veto_case():
    import scripts.run_rotation_core_v2 as run
    R = _passing_inputs()
    for h in run.HYPS:
        lg = run.conjunction_legs(h, R)
        assert len(lg) == 1 + 4 * (2 + 4 + 2) and all(lg.values())
        assert v2.verdict(lg, False) == "survives falsification on history"
        assert v2.verdict(lg, run.fund_veto({"eq|base": 0.01, "eq|strict": -0.001})) == "signal not shown to be tradable"


def test_S1_each_single_leg_fail_case_fails():
    import scripts.run_rotation_core_v2 as run, copy
    base = _passing_inputs()
    names = list(run.conjunction_legs("H1", base))
    hit = set()
    for rc_ in base["point"]:
        for w in base["point"][rc_]["H1"]:
            for bad in (0.0, -0.01, float("nan")):
                R = copy.deepcopy(base); R["point"][rc_]["H1"][w] = bad
                lg = run.conjunction_legs("H1", R)
                assert v2.verdict(lg, False) == "FAIL"; hit |= {k for k, v in lg.items() if not v}
                assert all(run.conjunction_legs("H3", R).values())          # other hypotheses unaffected
        for w in ("pre1998", "h2020_2025"):
            for bad in ((-0.31, -0.3), (float("nan"), -0.3)):
                R = copy.deepcopy(base); R["drawdown"][rc_]["H1"][w] = bad
                lg = run.conjunction_legs("H1", R); assert v2.verdict(lg, False) == "FAIL"; hit |= {k for k, v in lg.items() if not v}
    for k in base["holm"]:
        R = copy.deepcopy(base); R["holm"][k]["H1"]["reject_h0"] = False
        lg = run.conjunction_legs("H1", R); assert v2.verdict(lg, False) == "FAIL"; hit |= {k_ for k_, v in lg.items() if not v}
    R = copy.deepcopy(base); R["integrity_ok"] = False
    lg = run.conjunction_legs("H1", R); assert v2.verdict(lg, False) == "FAIL"; hit |= {k for k, v in lg.items() if not v}
    assert hit == set(names), "every leg is exercised by a single-leg fail case"


def test_S1_pooled_weights_are_years_weighted_mean_of_annualised_window_statistics():
    a = pd.DatetimeIndex(list(pd.bdate_range("1940-01-01", periods=300)) + list(pd.date_range("1940-01-06", periods=40, freq="7D")))
    b = pd.bdate_range("2020-01-02", periods=100)
    m = np.array([0.001, -0.0005])
    for conv in ("weekday", "fixed252"):
        c = v2.pooled_weights([a, b], conv)
        ann = [v2.ann_factor(a), v2.ann_factor(b)] if conv == "weekday" else [252.0, 252.0]
        yrs = [len(a) / ann[0], len(b) / ann[1]]
        want = (yrs[0] * ann[0] * m[0] + yrs[1] * ann[1] * m[1]) / sum(yrs)
        assert c @ m == pytest.approx(want)
    assert not np.allclose(v2.pooled_weights([a, b], "weekday"), v2.pooled_weights([a, b], "fixed252"))


def test_S1_shared_resample_indices_and_raw_statistic_matches_matched_mix_stat():
    rng = np.random.default_rng(0)
    n = 400
    r = rng.normal(0, 0.01, n); W = rng.dirichlet(np.ones(4), n); L = rng.normal(0, 0.01, (n, 4))
    assert v2.raw_mix_excess(r, W, L) * 252 == pytest.approx(float(v2.matched_mix_stat(r[None], W[None], L[None])[0]))
    ser = {"a": ("mix", r, W, L), "b": ("mix", r, W, L), "d": ("paired", r)}
    dr = v2.bootstrap_draws(ser, 40, 21, 5, chunk=15)
    assert np.array_equal(dr["a"], dr["b"])
    ii = np.concatenate([rc.stationary_bootstrap_indices(n, b_, 21, 5 + c) for c, b_ in enumerate((15, 15, 10))])
    assert np.allclose(dr["d"], r[ii].mean(axis=1))
    m = r[ii].mean(axis=1) - sum(W[:, j][ii].mean(axis=1) * L[:, j][ii].mean(axis=1) for j in range(4))
    assert np.allclose(dr["a"], m)


def test_S1_holm_one_sided_governs_two_sided_labelled():
    d = np.array([0.0, 0.1, -0.1, 0.2, -0.2, 0.05])
    assert v2.two_sided_p(d, 0.1) >= rc.centred_p(d, 0.1)


def test_S1_warm_state_2020_equals_continuous_run_not_a_restart(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    monkeypatch.setattr(v2, "assert_window", lambda *a, **k: None)
    monkeypatch.setattr(v2, "seal_guard", lambda *a, **k: None)
    full = make_fixture(tmp_path / "full", start="2010-01-01", end="2021-12-31", extra_after="2021-12-31")
    D = run.build(full / IND, full / FAC, "2021-12-31", 3.0, 25.0)
    st = D["states"]["H1"]
    cold = run.build(full / IND, full / FAC, "2021-12-31", 3.0, 25.0)        # same input -> same warm series
    assert st.equals(cold["states"]["H1"])
    bks, LR = run.run_books(D["legs"], D["states"], D["rf"], pd.Timestamp("2021-12-31"), "eq", "base")
    assert bks["H1"].returns.index[0] < v2.H_START                            # held from first formation, sliced later


def test_S11_seed_record_lists_every_stream():
    import scripts.run_rotation_core_v2 as run
    s = run.seeds_record()
    assert {"stage1_standalone_pre1998", "stage2_standalone_2020_2025", "pooled_pre1998", "pooled_2020_2025",
            "shared_indices"} <= set(s)
    assert run.SEEDS == {"stage1": 20261113, "stage2": 20261114, "pooled": 20261115}


# ------------------------------------------------------------------ R19.1 Phase A / INTEGRITY_ABORT
def _damage(fx_dir, dates, cols=range(24, 49)):
    """All of the top-beta industries (fixture betas rise with the index) missing on the given dates, both
    sections: the offence leg has no observed close on those days."""
    p = Path(fx_dir) / IND
    out = []
    for ln in p.read_text().splitlines():
        k = ln.split(",", 1)[0]
        if k in dates:
            x = ln.split(",")
            for c in cols:
                x[1 + c] = "-99.99"
            ln = ",".join(x)
        out.append(ln)
    p.write_text("\n".join(out) + "\n")


DAMAGE_DATES = {d.strftime("%Y%m%d") for d in pd.bdate_range("1950-01-02", "1990-12-31")[::900]}


def _run_capture(fn, *a, **k):
    lines, buf = [], io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*a, **k, out=lambda s: (lines.append(s), print(s)))
    return r, lines, buf.getvalue()


def test_R19_nan_in_one_leg_aborts_with_no_sign_anywhere(tmp_path):
    fx = make_fixture(tmp_path / "fx"); _damage(fx, DAMAGE_DATES)
    led = v2.MemoryLedger()
    e, lines, text = _s1(led, fx / IND, fx / FAC, engine="E0")
    assert e["integrity_abort"] is True
    assert not any(ln.startswith(("GATE_SIGN", "gate_open", "magnitudes_sha256", "status")) for ln in lines)
    assert "PHASE_A INTEGRITY_ABORT" in lines and _no_magnitude(text)
    ents = led.entries()
    assert [x["kind"] for x in ents] == ["START", "INTEGRITY_ABORT"]
    nz = ents[1]["nonzero_counts"]
    assert any("|nan|" in k for k in nz) and any("|leg_unobserved|" in k for k in nz)
    assert "gate_signs" not in ents[1] and all(isinstance(v, int) for v in nz.values())


def test_R19_strict_inequality_violation_aborts_the_same_way(fx, monkeypatch):
    orig = v2.base_view
    def bad(legs_r, base="eq", kind="net", formed_fee_bp=v2.FEE_INDUSTRY_BP, book_fee_bp=None):
        x = orig(legs_r, base, kind, formed_fee_bp, book_fee_bp)
        if kind == "book":
            x = x.copy(); x.loc[pd.Timestamp("1960-06-01"):pd.Timestamp("1960-06-30")] += 0.01
        return x
    monkeypatch.setattr(v2, "base_view", bad)
    led = v2.MemoryLedger()
    e, lines, _ = _s1(led, fx / IND, fx / FAC, engine="E0")
    assert e["integrity_abort"] is True and "strict_inequality_violations" in e["nonzero_counts"]
    assert not any(ln.startswith("GATE_SIGN") for ln in lines)
    assert [x["kind"] for x in led.entries()] == ["START", "INTEGRITY_ABORT"]


def test_R19_clean_fixture_proceeds_and_phase_a_is_printed_before_any_sign(stage1):
    d, e, lines, _, led = stage1
    i_clean = lines.index("PHASE_A CLEAN")
    i_sign = min(i for i, ln in enumerate(lines) if ln.startswith("GATE_SIGN"))
    assert i_clean < i_sign and all(ln.startswith("PHASE_A") for ln in lines[:i_clean + 1])
    assert sum(ln.startswith("GATE_SIGN") for ln in lines) == 16


def test_R19_abort_is_not_a_gate_result_and_a_fix_needs_a_new_commit_and_citation(fx, tmp_path):
    bad = make_fixture(tmp_path / "bad"); _damage(bad, DAMAGE_DATES)
    led = v2.MemoryLedger()
    _s1(led, bad / IND, bad / FAC, engine="E0", release_sha="r0")
    with pytest.raises(v2.SealedRefusal):                       # same commit after an abort
        _s1(led, fx / IND, fx / FAC, engine="E0", release_sha="r1")
    with pytest.raises(v2.SealedRefusal):                       # new commit without citing the abort
        _s1(led, fx / IND, fx / FAC, engine="E1", release_sha="r1")
    e, lines, _ = _s1(led, fx / IND, fx / FAC, engine="E1", release_sha="r1", release={"ledger_records_cited": [0]})
    kinds = [x["kind"] for x in led.entries()]
    assert kinds == ["START", "INTEGRITY_ABORT", "START", "PHASE_A_CLEAN", "GATE"] and e["kind"] == "GATE"


def test_R19_phase_a_calls_no_gate_statistic_function():
    import ast, inspect, textwrap
    import scripts.run_rotation_core_v2 as run
    forbidden = {"window_excess", "matched_contrast", "matched_mix_stat", "mix_series", "raw_mix_excess", "max_drawdown",
                 "bootstrap_draws", "standalone", "window_block", "paired_h2", "observed_raw", "window_series", "_cagr",
                 "pre1998_stats", "fund_stats", "sign", "gate_decision", "centred_p", "two_sided_p", "holm", "ci95",
                 "ann_factor", "pooled_weights", "find_episode", "pivot_table", "mean", "nanmean", "sum", "nansum",
                 "cumsum", "cumprod", "prod", "average", "base_view", "simulate_states", "run_books"}
    called = set()
    for name in run.PHASE_A_FUNCTIONS:
        tree = ast.parse(textwrap.dedent(inspect.getsource(getattr(run, name))))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                called.add(f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "")
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                src = ast.unparse(n)
                assert "mix" not in src.lower(), src                       # nothing book-vs-mix
    assert not (called & forbidden), called & forbidden





def test_R19_stage2_final_run_aborts_before_any_2020_2025_number(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    pre = make_fixture(tmp_path / "pre")
    full = make_fixture(tmp_path / "full", extra_after="2025-12-31")
    _damage(full, {d.strftime("%Y%m%d") for d in pd.bdate_range("2020-02-03", "2025-11-28")[::120]})
    funds = make_fund_fixture(tmp_path / "funds")
    def boom(*a, **k):
        raise AssertionError("a statistic was computed after an integrity failure")
    for f in ("pre1998_stats", "window_block", "paired_h2", "standalone", "fund_stats", "window_series"):
        monkeypatch.setattr(run, f, boom)
    led = v2.MemoryLedger(); s = led.append(run.start_entry("stage2", "r2", "E1", {}))
    lines = []
    with v2.stage2_opened([], recorded={}), pytest.raises(run.IntegrityAbort) as ei:
        run.final_evaluation(pre / IND, full / IND, full / FAC, funds, "a" * 64, _all_plus(), led, s["index"], B_=20,
                             out=lines.append)
    assert any(k.startswith("h2020_2025|") for k in ei.value.phase_a["nonzero"])
    assert "PHASE_A INTEGRITY_ABORT" in lines and _no_magnitude("\n".join(lines))
    assert [x["kind"] for x in led.entries()] == ["START", "INTEGRITY_ABORT"]


# ------------------------------------------------------------------ R20: the reviewer's bypasses, now refused
def _all_plus(minus=()):
    return {k: ("-" if k in minus else "+") for h in ("H1", "H3") for k in v2.gate_keys(h)}


def _closed():
    return {k: "-" for h in ("H1", "H3") for k in v2.gate_keys(h)}


def _start(stage="stage1", rel="r1", eng="E1", ins=None):
    return {"kind": "START", "stage": stage, "release_sha256": rel, "engine_commit": eng, "inputs_sha256": ins or {"a": "1"},
            "versions": {}, "utc": "t"}


def _ledger(*runs):
    """runs: tuples (stage, release, engine, outcome('abort'|'clean'|None), record(signs dict|'final'|None))."""
    led = v2.MemoryLedger()
    for stage, rel, eng, outcome, rec in runs:
        s = led.append(_start(stage, rel, eng))
        if outcome == "abort":
            led.append({"kind": "INTEGRITY_ABORT", "start_index": s["index"], "nonzero_counts": {"x": 1}})
        elif outcome == "clean":
            led.append({"kind": "PHASE_A_CLEAN", "start_index": s["index"]})
            if rec == "final":
                led.append({"kind": "FINAL", "start_index": s["index"], "verdicts": {}})
            elif rec is not None:
                led.append({"kind": "GATE", "start_index": s["index"], "gate_signs": rec,
                            "gate_open": v2.gate_decision(rec)[0], "magnitudes_sha256": "m" * 64})
    return led.entries()


def test_R20_case1_rewritten_or_rechained_ledger_refused():
    hist = _ledger(("stage1", "r1", "E1", "clean", _closed()), ("stage1", "r2", "E2", "clean", _all_plus()))
    v1 = hist[:3]
    # the closed run removed and the open run re-chained as the first run
    rew = v2.MemoryLedger()
    for e in hist[3:]:
        rew.append({k: v for k, v in e.items() if k not in ("index", "prev_chain_sha256")} | (
            {"start_index": 0} if e["kind"] != "START" else {}))
    docs = {"r1": {}, "r2": {}}
    with pytest.raises(v2.SealedRefusal):                       # R20.2: an earlier committed version is not a prefix
        v2.validate_ledger(rew.entries(), [v1, rew.entries()], docs)
    with pytest.raises(v2.SealedRefusal):                       # and the full history itself: closed is final
        v2.validate_ledger(hist, [v1, hist], docs)


def test_R20_case2_flipped_gate_open_refused():
    hist = _ledger(("stage1", "r1", "E1", "clean", _closed()))
    hist[2]["gate_open"] = True
    led = v2.MemoryLedger()
    for e in hist:
        led.append({k: v for k, v in e.items() if k not in ("index", "prev_chain_sha256")})
    with pytest.raises(v2.SealedRefusal):
        v2.validate_ledger(led.entries(), [led.entries()], {"r1": {}})
    r2 = {"windows_released": [v2.W_H], "protocol_header_sha256": v2.FROZEN_V2_SHA256, "engine_commit": "E1",
          "ledger_prefix_len": 3, "ledger_prefix_chain_sha256": v2.chain_hash(led.entries())}
    with pytest.raises(v2.SealedRefusal):
        v2.verify_release2(r2, led.entries())


def test_R20_case3_gate_record_pushed_before_any_sign_and_failed_push_prints_nothing(fx):
    led = v2.MemoryLedger(fail_on={"GATE"})
    with pytest.raises(SystemExit) as ei:
        e, lines, text = _s1(led, fx / IND, fx / FAC)
    assert "nothing about signs" in str(ei.value)
    assert [x["kind"] for x in led.entries()] == ["START", "PHASE_A_CLEAN"]
    # the lost record: only the identical rerun is permitted; any other commit or release refused permanently
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(led.entries(), _start(eng="E2", ins={"industries": "x"}), {"ledger_records_cited": [0]})
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(led.entries(), _start(rel="r9", ins={"industries": "x"}), {})
    v2.start_allowed(led.entries(), _start(eng="E1", ins={"industries": "x"}), {})


def test_R20_case3_signs_reach_the_ledger_before_stdout(fx):
    order = []
    class Spy(v2.MemoryLedger):
        def append(self, entry):
            order.append(("ledger", entry["kind"])); return super().append(entry)
    led = Spy()
    import scripts.run_rotation_core_v2 as run
    run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20,
                       out=lambda s: order.append(("out", s.split()[0])))
    first_sign = order.index(("out", "GATE_SIGN"))
    assert order.index(("ledger", "GATE")) < first_sign
    assert order.index(("ledger", "PHASE_A_CLEAN")) < order.index(("ledger", "GATE"))
    assert order[0] == ("ledger", "START")


def test_R20_case4_fixture_dry_run_takes_no_path(monkeypatch, capsys):
    import scripts.run_rotation_core_v2 as run, inspect
    assert list(inspect.signature(run.fixture_dry_run).parameters) == ["out", "B_"]
    monkeypatch.setattr(sys, "argv", ["run", "--dry-run-stage1-fixture", "/home/ubuntu2/tmp/rotation-core/data/french/le2019"])
    with pytest.raises(SystemExit):                                         # argparse: the flag takes no argument
        run.main()
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", ["run", "--dry-run-stage1-fixture"])
    assert run.main() == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) > 40 and all(ln.startswith("FIXTURE ") for ln in out)
    assert _no_magnitude("\n".join(out)) and any("PHASE_A CLEAN" in ln for ln in out)


def test_R20_4_loaders_read_in_memory_text_identically(tmp_path):
    ind, fac = fixture_texts(seed=7)
    d = make_fixture(tmp_path / "f", seed=7)
    a = v2.load_french_industries(io.StringIO(ind), v2.PRE_END)[0]
    b = v2.load_french_industries(d / IND, v2.PRE_END)[0]
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_series_equal(v2.load_french_market(io.StringIO(fac), v2.PRE_END)[0],
                                   v2.load_french_market(d / FAC, v2.PRE_END)[0])


def test_R20_case5_gate_decision_needs_exactly_eight_signs_per_hypothesis():
    assert v2.gate_decision({}) == (False, {"H1": False, "H3": False})
    full = _all_plus()
    assert v2.gate_decision(full)[0] is True
    short = dict(full); short.pop(next(iter(v2.gate_keys("H1"))))
    assert v2.gate_decision(short)[0] is False
    extra = dict(full, **{"H1|E3|eq|base": "+"})
    assert v2.gate_decision(extra)[0] is False
    only_h3 = {k: "+" for k in v2.gate_keys("H3")}
    assert v2.gate_decision(only_h3)[0] is False


# ------------------------------------------------------------------ R20.1 state rules
def test_R20_1_closed_gate_is_final_for_every_later_invocation():
    led = _ledger(("stage1", "r1", "E1", "clean", _closed()))
    for st in (_start(eng="E2", rel="r2"), _start(eng="E1", rel="r1"), _start("stage2", "r3", "E1")):
        with pytest.raises(v2.SealedRefusal):
            v2.start_allowed(led, st, {"ledger_records_cited": []})


def test_R20_1_start_only_and_abort_rules():
    led = _ledger(("stage1", "r1", "E1", None, None))
    v2.start_allowed(led, _start(), {})                                      # identical rerun: no sign existed
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(led, _start(eng="E2", rel="r2"), {})                # new commit without citing
    v2.start_allowed(led, _start(eng="E2", rel="r2"), {"ledger_records_cited": [0]})
    led = _ledger(("stage1", "r1", "E1", "abort", None))
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(led, _start(), {})                                  # a fix is a new commit (R19)
    v2.start_allowed(led, _start(eng="E2", rel="r2"), {"ledger_records_cited": [0]})


def test_R20_1_open_gate_rerun_needs_a_new_commit_and_stage2_follows_the_latest_gate():
    led = _ledger(("stage1", "r1", "E1", "clean", _all_plus()))
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(led, _start(rel="r2"), {})                          # same commit after a gate record
    v2.start_allowed(led, _start(eng="E2", rel="r2"), {})
    v2.start_allowed(led, _start("stage2", "q1", "E1"), {})
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(led, _start("stage2", "q1", "E9"), {})
    fin = _ledger(("stage1", "r1", "E1", "clean", _all_plus()), ("stage2", "q1", "E1", "clean", "final"))
    for st in (_start("stage2", "q2", "E1"), _start(eng="E2", rel="r2")):
        with pytest.raises(v2.SealedRefusal):
            v2.start_allowed(fin, st, {})


def test_R20_1_every_release_version_maps_to_the_ledger_or_is_superseded_as_unused():
    import hashlib
    b1, b2 = b'{"engine_commit": "E1"}', b'{"engine_commit": "E2"}'
    s1 = hashlib.sha256(b1).hexdigest()
    with pytest.raises(v2.SealedRefusal):
        v2.check_release_history({"HOLDOUT_RELEASE_v2.json": [("c1", b1), ("c2", b2)]}, [])
    b2s = json.dumps({"engine_commit": "E2", "supersedes_unused_releases": [s1]}).encode()
    docs = v2.check_release_history({"HOLDOUT_RELEASE_v2.json": [("c1", b1), ("c2", b2s)]}, [])
    assert s1 in docs
    used = _ledger(("stage1", s1, "E1", None, None))
    v2.check_release_history({"HOLDOUT_RELEASE_v2.json": [("c1", b1), ("c2", b2)]}, used)


def test_R20_2_ledger_version_prefix_and_chain():
    hist = _ledger(("stage1", "r1", "E1", "clean", _all_plus()))
    v2.validate_ledger(hist, [hist[:1], hist[:2], hist], {"r1": {}})
    dropped = [hist[0]]
    with pytest.raises(v2.SealedRefusal):
        v2.validate_ledger(dropped, [hist[:2], dropped], {"r1": {}})
    bad = [dict(hist[0]), dict(hist[1], prev_chain_sha256="0" * 64)]
    with pytest.raises(v2.SealedRefusal):
        v2.verify_chain(bad)


# ------------------------------------------------------------------ R20.1/R20.5 GitLedger against a real bare remote
def _git_env(tmp_path):
    def g(*a, cwd):
        return subprocess.run(["git", *a], cwd=cwd, capture_output=True, check=True)
    origin = tmp_path / "origin.git"; work = tmp_path / "work"
    g("init", "-q", "--bare", str(origin), cwd=tmp_path)
    g("clone", "-q", str(origin), str(work), cwd=tmp_path)
    g("checkout", "-q", "-b", "b", cwd=work)
    (work / "README").write_text("x\n")
    g("-c", "user.email=t@t", "-c", "user.name=t", "add", "README", cwd=work)
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init", cwd=work)
    g("push", "-q", "origin", "b", cwd=work)
    g("config", "user.email", "t@t", cwd=work); g("config", "user.name", "t", cwd=work)
    return origin, work, g


def test_R20_1_git_ledger_pushes_each_entry_and_refuses_on_push_failure(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = v2.GitLedger(root=work, path=work / "ledger.json", branch="b")
    led.fetch(); led.require_local_equals_remote()
    s = led.append(_start())
    remote = subprocess.run(["git", "ls-remote", str(origin), "refs/heads/b"], capture_output=True).stdout.split()[0].decode()
    assert remote == led.remote_sha and json.loads((work / "ledger.json").read_text())["entries"][0]["kind"] == "START"
    hook = origin / "hooks" / "pre-receive"; hook.write_text("#!/bin/sh\nexit 1\n"); hook.chmod(0o755)
    before = (work / "ledger.json").read_text()
    with pytest.raises(v2.LedgerPushFailed):
        led.append({"kind": "PHASE_A_CLEAN", "start_index": s["index"]})
    assert (work / "ledger.json").read_text() == before                # nothing written in the working tree
    assert [e["kind"] for e in led.entries()] == ["START"]


def test_R20_5_fetch_fails_closed_and_local_must_equal_remote(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = v2.GitLedger(root=work, path=work / "ledger.json", branch="b")
    led.fetch()
    (work / "x").write_text("y"); g("add", "x", cwd=work); g("commit", "-q", "-m", "local only", cwd=work)
    with pytest.raises(v2.SealedRefusal):
        led.require_local_equals_remote()
    g("remote", "set-url", "origin", str(tmp_path / "nowhere.git"), cwd=work)
    with pytest.raises(v2.SealedRefusal):
        led.fetch()
    with pytest.raises(v2.SealedRefusal):
        v2.GitLedger(root=work, path=work / "ledger.json", branch="b").entries()     # no read before a fetch


def test_R20_2_git_ledger_rewrite_on_the_remote_is_refused(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = v2.GitLedger(root=work, path=work / "ledger.json", branch="b")
    led.fetch()
    s = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s["index"]})
    led.append({"kind": "GATE", "start_index": s["index"], "gate_signs": _closed(), "gate_open": False,
                "magnitudes_sha256": "m" * 64})
    ents = led.entries()
    (work / "ledger.json").write_bytes(v2.ledger_doc(ents[:2]))       # drop the closed gate record and push
    g("commit", "-q", "-am", "rewrite", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    led.fetch()
    with pytest.raises(v2.SealedRefusal):
        v2.validate_ledger(led.entries(), led.version_entries(), {"r1": {}})


# ------------------------------------------------------------------ R20.3 / R20.6 final run trusts nothing recorded
def test_R20_6_reproduction_hash_and_signs_are_required(tmp_path):
    import scripts.run_rotation_core_v2 as run, inspect
    p = inspect.signature(run.final_evaluation).parameters
    assert p["expected_sha"].default is inspect.Parameter.empty and p["expected_signs"].default is inspect.Parameter.empty
    for sha, signs in ((None, _all_plus()), ("x", _all_plus()), ("a" * 64, _closed()), ("a" * 64, {})):
        with pytest.raises(v2.SealedRefusal):
            run.final_evaluation("p", "f", "c", "d", sha, signs, v2.MemoryLedger(), 0)


def test_R20_3_gate_rederived_from_reproduced_numbers_must_equal_the_record(stage1, fx, tmp_path):
    import scripts.run_rotation_core_v2 as run
    d, e, lines, _, led0 = stage1
    full = make_fixture(tmp_path / "full", extra_after="2025-12-31")
    funds = make_fund_fixture(tmp_path / "funds")
    led = v2.MemoryLedger(); s = led.append(run.start_entry("stage2", "r2", "E1", {}))
    with v2.stage2_opened([], recorded={}), pytest.raises(v2.SealedRefusal) as ei:
        run.final_evaluation(fx / IND, full / IND, full / FAC, funds, e["magnitudes_sha256"], _all_plus(), led,
                             s["index"], B_=20, out=lambda x: None)
    assert "re-derived" in str(ei.value)                                     # hash reproduced; the gate is not


# ------------------------------------------------------------------ R20.7 unseal inside the runner, re-seal on exit
def test_R20_7_unseal_checks_recorded_hash_and_reseals_whatever_happens(tmp_path):
    p = tmp_path / "sealed_post2019" / "49_Industry_Portfolios_Daily.csv"; p.parent.mkdir(); p.write_text("data\n")
    h = v2.sha256_file(p); os.chmod(p, 0)
    with v2.stage2_opened([p], recorded={p.name: h}):
        assert p.read_text() == "data\n"
        v2.seal_guard(p)
    assert (p.stat().st_mode & 0o777) == 0
    with pytest.raises(v2.SealedRefusal):
        v2.seal_guard(p)
    with pytest.raises(v2.SealedRefusal):
        with v2.stage2_opened([p], recorded={p.name: "0" * 64}):
            pass
    assert (p.stat().st_mode & 0o777) == 0 and not v2._STAGE2_OPEN["open"]
    with pytest.raises(RuntimeError):
        with v2.stage2_opened([p], recorded={p.name: h}):
            raise RuntimeError("crash inside the run")
    assert (p.stat().st_mode & 0o777) == 0 and not v2._STAGE2_OPEN["open"]


def test_R20_7_recorded_sealed_hashes_cover_the_full_industry_file():
    assert "49_Industry_Portfolios_Daily.csv" in v2.sealed_record()


# ------------------------------------------------------------------ R20.8 engine-commit environment
def test_R20_8_import_environment(monkeypatch, tmp_path):
    import types
    v2.check_import_environment()
    monkeypatch.setenv("PYTHONPATH", "/tmp")
    with pytest.raises(v2.SealedRefusal):
        v2.check_import_environment()
    monkeypatch.delenv("PYTHONPATH")
    m = types.ModuleType("usercustomize"); m.__file__ = str(tmp_path / "usercustomize.py")
    monkeypatch.setitem(sys.modules, "usercustomize", m)
    with pytest.raises(v2.SealedRefusal):
        v2.check_import_environment()
    monkeypatch.delitem(sys.modules, "usercustomize")
    m = types.ModuleType("sitecustomize"); m.__file__ = str(tmp_path / "sitecustomize.py")
    monkeypatch.setitem(sys.modules, "sitecustomize", m)
    with pytest.raises(v2.SealedRefusal):
        v2.check_import_environment()
    monkeypatch.undo()
    m = types.ModuleType("engine.planted"); m.__file__ = str(tmp_path / "planted.py")
    monkeypatch.setitem(sys.modules, "engine.planted", m)
    with pytest.raises(v2.SealedRefusal):
        v2.check_import_environment()


def test_R20_8_untracked_file_under_pinned_paths_refused(monkeypatch):
    def fake_git(*a, check=True, root=None, env=None, input=None):
        if a[0] == "status":
            return subprocess.CompletedProcess(a, 0, b"?? engine/shadow.py\n", b"")
        return subprocess.CompletedProcess(a, 0, b"", b"")
    monkeypatch.setattr(v2, "_git", fake_git)
    with pytest.raises(v2.SealedRefusal):
        v2.check_engine_commit("HEAD")


def test_R20_8_sitecustomize_hash_is_pinned_in_versions():
    assert "sitecustomize_sha256" in v2.versions()


# ------------------------------------------------------------------ R20.9 selection rerun on the remote
def test_R20_9_stage1_checks_selection_commit_and_file_against_the_remote(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "_committed_clean", lambda p: True)
    monkeypatch.setattr(v2, "check_engine_commit", lambda c: None)
    import hashlib
    body = {"windows_released": [v2.W_PRE], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
            "selected_grid_point": {"h_near_high_pct": 3, "b_breadth_drop_pp": 25}, "engine_commit": "X",
            "selection_results_commit": "HEAD",
            "selection_results_sha256": hashlib.sha256(ORIG_SELECTION.read_bytes()).hexdigest()}
    p = tmp_path / "r1.json"; p.write_text(json.dumps(body))
    old = v2._git("rev-list", "--max-parents=0", "HEAD").stdout.decode().split()[0]   # a remote that lacks HEAD
    with pytest.raises(v2.SealedRefusal):
        v2.stage1_release(p, remote_sha=old)


# ------------------------------------------------------------------ R20.10 planted-edge end to end, verdicts exact
def _slow(t, amp=0.0015):
    return amp if (t.year // 2) % 2 == 0 else -amp


def _edge_pass(t):
    return _slow(t)


def _edge_late_fail(t):
    if t.year >= 2020:
        return 0.0004 if ((t.year * 12 + t.month) // 2) % 2 == 0 else -0.0004
    return _slow(t)


def _e2e(d, edge, fund_sign=1.0, B_=200):
    """Through the real command path: stage1_command -> ledger GATE -> the stage-2 release verified against the
    ledger -> the runner's stage-2 context -> confirm_command -> FINAL record."""
    import scripts.run_rotation_core_v2 as run
    v2.SELECTION_RESULT = ORIG_SELECTION
    d = Path(d)
    pre = make_fixture(d / "pre", edge=edge)
    full = make_fixture(d / "full", extra_after="2025-12-31", edge=edge)
    funds = make_fund_fixture(d / "funds", edge=edge, edge_sign=fund_sign)
    led = v2.MemoryLedger()
    sink = []
    g = run.stage1_command(led, {}, "r1", "E1", pre / IND, pre / FAC, {"x": "1"}, B_=B_, out=sink.append)
    ents = led.entries()
    r2 = v2.verify_release2({"windows_released": [v2.W_H], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
                             "engine_commit": "E1", "ledger_prefix_len": len(ents),
                             "ledger_prefix_chain_sha256": v2.chain_hash(ents)}, ents)
    with v2.stage2_opened([], recorded={}):
        res = run.confirm_command(led, r2, "r2", "E1", pre / IND, full / IND, full / FAC, funds, {"x": "1"}, B_=B_,
                                  out=sink.append)
    return g, res, led


SIGN_2020 = sorted(f"sign|h2020_2025|{r}|{c}" for r in ("eq", "drift") for c in ("base", "strict"))


@pytest.fixture(scope="module")
def e2e_pass(tmp_path_factory):
    return _e2e(tmp_path_factory.mktemp("e2e_pass"), _edge_pass)


def test_R20_10_planted_edge_must_pass(e2e_pass):
    g, res, led = e2e_pass
    assert g["gate_open"] is True
    assert {h: v["verdict"] for h, v in res["verdicts"].items()} == {
        "H1": "FAIL", "H2": "FAIL", "H3": "survives falsification on history"}
    assert res["verdicts"]["H3"]["failed_legs"] == [] and res["verdicts"]["H3"]["fund_veto_fired"] is False
    assert [x["kind"] for x in led.entries()] == ["START", "PHASE_A_CLEAN", "GATE", "START", "PHASE_A_CLEAN", "FINAL"]
    assert led.entries()[-1]["verdicts"]["H3"] == "survives falsification on history"


def test_R20_10_planted_edge_fails_only_on_the_2020_2025_sign_legs(tmp_path):
    g, res, led = _e2e(tmp_path, _edge_late_fail)
    assert g["gate_open"] is True
    assert res["verdicts"]["H3"]["verdict"] == "FAIL"
    assert res["verdicts"]["H3"]["failed_legs"] == SIGN_2020


def test_R20_10_planted_edge_trips_the_fund_veto(tmp_path):
    g, res, led = _e2e(tmp_path, _edge_pass, fund_sign=-1.0)
    assert res["verdicts"]["H3"] == {"verdict": "signal not shown to be tradable", "failed_legs": [], "legs_total": 33,
                                     "fund_veto_fired": True}
    assert res["verdicts"]["H1"]["verdict"] == "FAIL" and res["verdicts"]["H2"]["verdict"] == "FAIL"


def test_S1_final_report_writes(e2e_pass, tmp_path):
    from scripts.rotation_core_v2_report import write_final_md
    write_final_md(json.loads(json.dumps(e2e_pass[1], default=float)), tmp_path / "f.md")
    t = (tmp_path / "f.md").read_text()
    assert "conditional on the pre-1998 gate" in t and "independent bets" in t and "descriptive only" in t


def test_S1_final_structure(e2e_pass):
    import scripts.run_rotation_core_v2 as run
    res = e2e_pass[1]
    for h, v in res["verdicts"].items():
        lg = run.conjunction_legs(h, res["conjunction_inputs"])
        assert sorted(k for k, x in lg.items() if not x) == v["failed_legs"] and v["legs_total"] == 33
    assert set(res["holm_m3"]) == {"block21", "block63"} and len(res["holm_m3"]["block21"]) == 8
    assert set(res["funds"]["estimates"]) == {"eq|base", "eq|strict", "drift|base", "drift|strict"}
    assert len(res["standalone_2020_2025_OUT_OF_SAMPLE_EFFECT_SIZE"]["block21"]) == 12
