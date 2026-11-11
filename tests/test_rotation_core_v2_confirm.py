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
import scripts.run_rotation_core_v2  # noqa: E402,F401  (registers the Phase A digest before any fixture runs)

ORIG_SELECTION = v2.ROOT / "research/rotation_core/results_v2_selection.json"
IND, FAC = "49_Industry_Portfolios_Daily.csv", "F-F_Research_Data_Factors_daily.csv"


@pytest.fixture(autouse=True)
def _sel(monkeypatch):
    monkeypatch.setattr(v2, "SELECTION_RESULT", ORIG_SELECTION)
    for k in list(os.environ):                             # R26.4: the runner refuses inherited GIT_/GH_/proxy vars
        if k.startswith(("GIT_", "GH_")) or k.lower() in v2.PROXY_VARS:
            monkeypatch.delenv(k)
    import scripts.run_rotation_core_v2 as run
    def hard_exit(msg):                                    # R25.1(b): in-process tests observe the exit as SystemExit;
        raise SystemExit(msg)                              # the real os._exit is tested in a subprocess
    monkeypatch.setattr(run, "_hard_exit", hard_exit)


PY = sys.executable
RUN_FLAGS = ("-E", "-P", "-B", "-X", "pycache_prefix=/dev/shm/rotation_core_v2_pycache")       # R29.3, R31.6


def _clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith(("GIT_", "GH_", "PYTHON", "PYTEST_")) or k.lower() in v2.PROXY_VARS)}
    env.update(extra)
    return env


def _py(args, cfg=None, tmp=None, flags=RUN_FLAGS, env=None, stdin=None):
    """Run the runner (or the test driver) in a real interpreter, as the command line does."""
    if cfg is not None:
        cp = Path(tmp) / f"cfg_{abs(hash(json.dumps(cfg, default=str)))}.json"
        cp.write_text(json.dumps(cfg, default=str))
        args = [str(v2.ROOT / "tests/rotation_core_v2_driver.py"), str(cp)]
    return subprocess.run([PY, *flags, *args], cwd=str(v2.ROOT), capture_output=True, text=True,
                          env=env or _clean_env(), stdin=stdin if stdin is not None else subprocess.DEVNULL)


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    d = tmp_path_factory.mktemp("conf")
    return make_fixture(d / "fx")


def _s1(led, ind, fac, engine="E1", release_sha="r1", release=None, **k):
    import scripts.run_rotation_core_v2 as run
    lines, buf, err = [], io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        e = run.stage1_command(led, release or {}, release_sha, engine, ind, fac, {"industries": "x"}, B_=k.pop("B_", 20),
                               out=lambda s: (lines.append(s), print(s)), **k, selection=ORIG_SELECTION)
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
    return run.pre1998_report(fx / IND, fx / FAC, B_=20, selection=ORIG_SELECTION)


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
    body = re.sub(r"\b[RSOF]\d+(\.\d+)*(\([^)]*\))?", "", body)        # rule references such as R25.1(b)
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
    again = run.pre1998_report(fx / IND, fx / FAC, B_=20, selection=ORIG_SELECTION)
    v2.verify_reproduction(again["magnitudes"], e["magnitudes_sha256"])
    fx2 = make_fixture(tmp_path / "fx2")
    t = (fx2 / IND).read_text().splitlines()
    i = next(j for j, ln in enumerate(t) if ln.startswith("19500103,"))
    p = t[i].split(","); p[5] = f"{float(p[5]) + 0.01:.2f}"; t[i] = ",".join(p)
    (fx2 / IND).write_text("\n".join(t) + "\n")
    other = run.pre1998_report(fx2 / IND, fx2 / FAC, B_=20, selection=ORIG_SELECTION)
    with pytest.raises(v2.SealedRefusal):
        v2.verify_reproduction(other["magnitudes"], e["magnitudes_sha256"])


def test_S6_closed_gate_publishes_at_once(stage1, open_stage1, tmp_path):
    d, e, lines, _, led = stage1
    assert e["gate_open"] is False                                    # precondition: the seed-7 fixture's gate closes
    pub = json.loads((d / "published.json").read_text())
    assert pub["magnitudes_sha256"] == e["magnitudes_sha256"]
    import scripts.run_rotation_core_v2 as run                       # and an open gate publishes nothing
    pre = open_stage1[0]
    g = run.stage1_command(v2.MemoryLedger(), {}, "r1", "E1", pre / IND, pre / FAC, {"x": "1"}, B_=20,
                           publish_path=tmp_path / "pub.json", out=lambda x: None, selection=ORIG_SELECTION)
    assert g["gate_open"] is True and not (tmp_path / "pub.json").exists()


def test_S6_exception_text_carries_no_value(fx, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    def boom(*a, **k):
        raise ValueError("excess 0.0123 leaked")
    for fn, kinds in (("prepare_pre1998", ["START"]), ("pre1998_stats", ["START", "PHASE_A_CLEAN", "GATE"])):
        led = v2.MemoryLedger()
        with monkeypatch.context() as m:
            m.setattr(run, fn, boom)
            with pytest.raises(SystemExit) as ei:
                _s1(led, fx / IND, fx / FAC)
            assert "0.0123" not in str(ei.value)
            assert ("withheld" in str(ei.value)) if fn == "prepare_pre1998" else ("ValueError" in str(ei.value))
        assert [x["kind"] for x in led.entries()] == kinds     # R20.11: a sign-phase failure is never an abort
        assert "0.0123" not in json.dumps(led.entries())
    assert led.entries()[-1]["closed_by"] == "phase_b_exception"          # R21.1


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
    h1 = [k for k in keys if k.startswith("H1")]
    assert len(h1) == 8                                               # precondition: eight H1 keys
    for k in h1:                        # every single '-' in H1 with H3 all '-' closes the gate
        s = {x: ("+" if x.startswith("H1") else "-") for x in keys}
        s[k] = "-"
        assert run.gate_decision(s)[0] is False



def test_S1c_stage1_release_opening_list_is_the_constant(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "_committed_clean", lambda p, root=None: True)
    monkeypatch.setattr(v2, "check_engine_commit", lambda c: None)
    import hashlib
    body = {"windows_released": [v2.W_PRE], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
            "selected_grid_point": {"h_near_high_pct": 3, "b_breadth_drop_pp": 25}, "engine_commit": "X",
            "selection_results_commit": "HEAD",
            "selection_results_sha256": hashlib.sha256(ORIG_SELECTION.read_bytes()).hexdigest()}
    p = tmp_path / "r1.json"; p.write_text(json.dumps(dict(body, opening_condition_hypotheses=["H1", "H3", "H2"])))
    with pytest.raises(v2.SealedRefusal):
        v2.stage1_release(p, selection=ORIG_SELECTION, root=v2.ROOT)
    p.write_text(json.dumps(dict(body, selection_results_sha256="0" * 64)))
    with pytest.raises(v2.SealedRefusal):                                   # S5: selection pinned by sha256
        v2.stage1_release(p, selection=ORIG_SELECTION, root=v2.ROOT)
    p.write_text(json.dumps(body))
    assert v2.stage1_release(p, selection=ORIG_SELECTION, root=v2.ROOT)


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
        v2.on_remote(v2.RELEASE, "f" * 40, v2.ROOT)
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
    assert run.SEED_BASE == 20261113 and "SeedSequence" in s["pooled_pre1998"]["block21"]


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
    assert i_clean < i_sign and all(ln.startswith(("PHASE_A", "WITNESS start_commit")) for ln in lines[:i_clean + 1])
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


PHASE_A_CALLS = {"Timestamp", "abs", "any", "append", "count_nonzero", "equals", "int", "isfinite", "items",
                 "phase_a_strict", "phase_a_window", "reindex", "sorted", "states_identical_across_costs", "to_numpy"}
PHASE_A_COMPARES = {   # finite checks, strict-book <= base-book, legs >= legs, weight equality, index masks, counts
    "V_all[m] == 0", "W_all[m] > TOL", "bb[k].traded > 0", "bs[k].traded > 0", "ib <= pd.Timestamp(z)",
    "ib >= pd.Timestamp(a)", "idx <= pd.Timestamp(wz)", "idx <= pd.Timestamp(z)", "idx >= pd.Timestamp(a)",
    "idx >= pd.Timestamp(wa)", "idx[0] < pd.Timestamp(wa)", "ls >= lb - TOL", "np.abs(Ws - Wb) > 1e-09",
    "np.count_nonzero(m) == 0", "np.count_nonzero(m) > 0", "rs <= rb + TOL", "v != 0"}
PHASE_A_ARITH = {"rb + TOL", "lb - TOL", "Ws - Wb"}     # tolerance shifts and the same-book weight difference
PHASE_A_ASSIGNS = {
"C_all = rf.reindex(idx).to_numpy(dtype=float)",
"L_all = LR.reindex(idx)[LEG_COLS_R].to_numpy(dtype=float)",
"V_all = valid.reindex(idx).to_numpy()",
"W_all = bk.holdings[LEG_COLS_R].to_numpy(dtype=float)",
"Wb = bb[k].holdings[LEG_COLS_R].to_numpy(dtype=float)[m]",
"Ws = bs[k].holdings.reindex(idx)[LEG_COLS_R].to_numpy(dtype=float)[m]",
"bb, Lb = runs[reading, 'base']",
"bb, _ = runs[reading, 'base']",
"bs, Ls = runs[reading, 'strict']",
"bs, _ = runs[reading, 'strict']",
"cash_only = ~np.any(held, axis=1)",
"held = W_all[m] > TOL",
"ib = Lb.index",
"idx = bb[k].returns.index",
"idx = bk.returns.index",
"key = f'{k}|{w}|{reading}|{cost}'",
"lb = Lb[LEG_COLS_R].to_numpy(dtype=float)[mb]",
"ls = Ls.reindex(ib)[LEG_COLS_R].to_numpy(dtype=float)[mb]",
"m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))",
"m = (idx >= pd.Timestamp(wa)) & (idx <= pd.Timestamp(wz))",
"mb = (ib >= pd.Timestamp(a)) & (ib <= pd.Timestamp(z))",
"n += int(np.count_nonzero(np.abs(Ws - Wb) > 1e-09))",
"n += int(np.count_nonzero(ok & ~(ls >= lb - TOL)))",
"n += int(np.count_nonzero(~(rs <= rb + TOL)))",
"n = 0",
"nan, unobs, warm = ({}, {}, {})",
"nan[key] = np.count_nonzero(~np.isfinite(r_all[m])) + np.count_nonzero(~np.isfinite(W_all[m])) + np.count_nonzero(held & ~np.isfinite(L_all[m])) + np.count_nonzero(cash_only & ~np.isfinite(C_all[m])) + int(np.count_nonzero(m) == 0)",
"nonzero = sorted((f'{name}|{kind}|{k}' for name, w in out['windows'].items() for kind, d in w.items() for k, v in d.items() if v != 0))",
"ok = np.isfinite(lb) & np.isfinite(ls)",
"out = {'windows': {}, 'strict_inequality_violations': 0, 'executions_identical_across_cost_runs': True}",
"out['clean'] = not nonzero",
"out['executions_identical_across_cost_runs'] &= states_identical_across_costs(p['runs'])",
"out['nonzero'] = nonzero",
"out['strict_inequality_violations'] += phase_a_strict(p['runs'], p['a'], p['z'])",
"out['windows'][name] = w",
"r_all = bk.returns.to_numpy(dtype=float)",
"rb = bb[k].returns.to_numpy(dtype=float)[m]",
"rs = bs[k].returns.reindex(idx).to_numpy(dtype=float)[m]",
"st = states[ST_OF_BOOK[k]].reindex(idx).to_numpy(dtype=float)",
"unobs[key] = int(np.count_nonzero(held & (V_all[m] == 0)))",
"valid = legs.valid[LEG_COLS_R]",
"w = phase_a_window(p['runs'], p['legs'], p['states'], p['rf'], p['a'], p['z'], p['windows'])",
"warm[key] = int(np.count_nonzero(~np.isfinite(st[m]))) + int(not (np.count_nonzero(m) > 0 and idx[0] < pd.Timestamp(wa)))"
}   # R25.2/R26.6
REDUCTIONS = {"sum", "mean", "prod", "cumsum", "cumprod", "max", "min", "std", "nansum", "nanmean", "average", "var",
              "median", "quantile"}


def _is_count(n) -> bool:
    """A sum of counts: every leaf is np.count_nonzero(...) or int(...)."""
    import ast
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        return _is_count(n.left) and _is_count(n.right)
    return isinstance(n, ast.Call) and ((isinstance(n.func, ast.Attribute) and n.func.attr == "count_nonzero")
                                        or (isinstance(n.func, ast.Name) and n.func.id == "int"))


def phase_a_violations(src: str) -> list:
    """R23.5: an ALLOWLIST. Every call must be a permitted name (never an arithmetic reduction); every comparison
    must be one of the reviewed forms present today; arithmetic is limited to boolean masks (&), sums of counts and
    the three reviewed tolerance/weight expressions."""
    import ast
    bad = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "?"
            if name in REDUCTIONS or name not in PHASE_A_CALLS:
                bad.append(f"call {name}")
        elif isinstance(n, (ast.Assign, ast.AugAssign)) and ast.unparse(n) not in PHASE_A_ASSIGNS:
            bad.append(f"assign {ast.unparse(n)}")               # rebinding a trusted name (R25.2 cases)
        elif isinstance(n, ast.Compare) and ast.unparse(n) not in PHASE_A_COMPARES:
            bad.append(f"compare {ast.unparse(n)}")
        elif isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.BitAnd) or _is_count(n) or ast.unparse(n) in PHASE_A_ARITH:
                continue
            bad.append(f"arith {ast.unparse(n)}")
    return bad


def test_R19_R23_5_phase_a_is_an_allowlist():
    import inspect, textwrap
    import scripts.run_rotation_core_v2 as run
    assert set(run.PHASE_A_FUNCTIONS) == {"phase_a_window", "phase_a_strict", "phase_a", "states_identical_across_costs"}
    for name in run.PHASE_A_FUNCTIONS:
        assert phase_a_violations(textwrap.dedent(inspect.getsource(getattr(run, name)))) == [], name


@pytest.mark.parametrize("src", [
    "def f(r):\n    return np.count_nonzero(r > 0)",                 # a return compared with a constant
    "def f(r):\n    return np.count_nonzero(r)  + r.sum()",           # a reduction
    "def f(r, mix):\n    return np.count_nonzero(r - mix > 0)",       # book against mix
    "def f(r):\n    return np.mean(r)",
    "def f(r):\n    return np.cumprod(1 + r)",
    "def f(r):\n    return max(r)"])
def test_R23_5_checker_rejects_sign_revealing_forms(src):
    assert phase_a_violations(src)


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
                             out=lines.append, selection=ORIG_SELECTION)
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
                            "gate_open": v2.gate_decision(rec)[0], "magnitudes_sha256": "d" * 64})
    return led.entries()


def test_R20_case1_rewritten_or_rechained_ledger_refused(tmp_path):
    """Through a real temporary remote: a closed run then an open run are pushed; the ledger file is rewritten to
    drop the closed run and re-chain the open one as run 0, committed and pushed as an ordinary commit. The
    committed versions come from the remote's history, not from the test."""
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin)
    led.fetch()
    for e in _ledger(("stage1", "r1", "E1", "clean", _closed()), ("stage1", "r2", "E2", "clean", _all_plus())):
        led.append({k: v for k, v in e.items() if k not in ("index", "prev_chain_sha256")})
    hist = led.entries()
    rew = v2.MemoryLedger()
    for e in hist[3:]:
        rew.append({k: v for k, v in e.items() if k not in ("index", "prev_chain_sha256")} |
                   ({"start_index": 0} if e["kind"] != "START" else {}))
    (work / "ledger.json").write_bytes(v2.ledger_doc(rew.entries()))
    g("commit", "-q", "-am", "rechain", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    with pytest.raises(v2.SealedRefusal, match="does not extend the ledger read earlier"):
        led.fetch(); led.entries()                                    # R29.1(b): the same invocation
    fresh = _gled(work, origin); fresh.fetch()                         # a new invocation: the committed versions
    with pytest.raises(v2.SealedRefusal, match="not a prefix|does not extend its predecessor"):
        v2.validate_ledger(fresh.entries(), fresh.version_entries(), {"r1": {}, "r2": {}})


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
        def append(self, entry, precheck=None):
            order.append(("ledger", entry["kind"])); return super().append(entry, precheck)
    led = Spy()
    import scripts.run_rotation_core_v2 as run
    run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20,
                       out=lambda s: order.append(("out", s.split()[0])), selection=ORIG_SELECTION)
    first_sign = order.index(("out", "GATE_SIGN"))
    assert order.index(("ledger", "GATE")) < first_sign
    assert order.index(("ledger", "PHASE_A_CLEAN")) < order.index(("ledger", "GATE"))
    assert order[0] == ("ledger", "START")


def test_R20_case4_fixture_dry_run_takes_no_path():
    import scripts.run_rotation_core_v2 as run, inspect
    assert list(inspect.signature(run.fixture_dry_run).parameters) == ["out", "B_", "selection"]   # no path
    r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture",
             str(v2.REAL_DATA_ROOT / "french" / "le2019")])
    assert r.returncode != 0 and "unrecognized arguments" in r.stderr                  # the flag takes no argument
    r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"])
    assert r.returncode == 0, r.stderr[-400:]
    out = r.stdout.strip().splitlines()
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
    with pytest.raises(v2.SealedRefusal):                                    # R21.2(ii): same release refused
        v2.start_allowed(led, _start(), {"ledger_records_cited": [0]})
    with pytest.raises(v2.SealedRefusal):                                    # new release, START not cited
        v2.start_allowed(led, _start(rel="r1b"), {})
    v2.start_allowed(led, _start(rel="r1b"), {"ledger_records_cited": [0]})   # same commit, new release citing it
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


def test_R20_2_ledger_version_prefix_and_chain(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin)
    led.fetch()
    for e in _ledger(("stage1", "r1", "E1", "clean", _all_plus())):
        led.append({k: v for k, v in e.items() if k not in ("index", "prev_chain_sha256")})
    vs = led.version_entries()
    assert [len(v) for v in vs] == [1, 2, 3]                      # one committed version per pushed entry
    v2.validate_ledger(led.entries(), vs, {"r1": {}})
    (work / "ledger.json").write_bytes(v2.ledger_doc(led.entries()[:1]))         # drop two entries, ordinary commit
    g("commit", "-q", "-am", "drop", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    fresh = _gled(work, origin); fresh.fetch()
    with pytest.raises(v2.SealedRefusal, match="not a prefix|does not extend its predecessor"):
        v2.validate_ledger(fresh.entries(), fresh.version_entries(), {"r1": {}})
    bad = [dict(vs[-1][0]), dict(vs[-1][1], prev_chain_sha256="0" * 64)]
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


def _gled(work, origin, branch="b"):
    return v2.GitLedger(root=work, path=work / "ledger.json", branch=branch, remote_url=str(origin), code_root=v2.ROOT)


def test_R20_1_git_ledger_pushes_each_entry_and_refuses_on_push_failure(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin)
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
    led = _gled(work, origin)
    led.fetch()
    (work / "x").write_text("y"); g("add", "x", cwd=work); g("commit", "-q", "-m", "local only", cwd=work)
    with pytest.raises(v2.SealedRefusal):
        led.require_local_equals_remote()
    g("remote", "set-url", "origin", str(tmp_path / "nowhere.git"), cwd=work)
    with pytest.raises(v2.SealedRefusal, match="fetching the remote branch failed"):
        _gled(work, tmp_path / "nowhere.git").fetch()
    with pytest.raises(v2.SealedRefusal):
        _gled(work, origin).entries()                                            # no read before a fetch


def _closed_run_on_remote(tmp_path):
    origin, work, g = _git_env(tmp_path)
    head_at_release = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    led = _gled(work, origin)
    led.fetch()
    s = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s["index"]})
    led.append({"kind": "GATE", "start_index": s["index"], "gate_signs": _closed(), "gate_open": False,
                "magnitudes_sha256": "d" * 64})
    return origin, work, g, led, head_at_release


def test_R20_2_git_ledger_ordinary_rewrite_on_the_remote_is_refused(tmp_path):
    origin, work, g, led, h0 = _closed_run_on_remote(tmp_path)
    ents = led.entries()
    (work / "ledger.json").write_bytes(v2.ledger_doc(ents[:2]))       # drop the closed gate record and push
    g("commit", "-q", "-am", "rewrite", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    led.fetch()
    with pytest.raises(v2.SealedRefusal):
        v2.validate_ledger(led.entries(), led.version_entries(), {"r1": {}})


def test_R22_force_push_back_before_start_is_refused_without_the_activity_check(tmp_path):
    origin, work, g, led, h0 = _closed_run_on_remote(tmp_path)
    other = tmp_path / "other"
    g("clone", "-q", "-b", "b", str(origin), str(other), cwd=tmp_path)
    g("push", "-q", "-f", "origin", f"{h0}:refs/heads/b", cwd=other)          # rewind to before START
    with pytest.raises(v2.SealedRefusal, match="not a fast-forward"):          # the existing clone: no forced fetch
        led.fetch()
    fresh = tmp_path / "fresh"
    g("clone", "-q", "-b", "b", str(origin), str(fresh), cwd=tmp_path)
    fl = _gled(fresh, origin); sha = fl.fetch()
    assert fl.entries() == []                                                 # the record is gone from this view
    # a release pinned at a later head (e.g. a stage-2 release after the gate) refuses on the ancestry pin
    gate_head = led.last_commit
    with pytest.raises(v2.SealedRefusal, match="branch_head_at_release"):
        v2.check_release_pins({"branch_head_at_release": gate_head}, sha, fresh)
    # rewound exactly to the stage-1 release head on a fresh clone: only the host record catches it (R22.1, R23.2)
    v2.check_release_pins({"branch_head_at_release": h0}, sha, fresh)
    log = [{"id": 1, "activity_type": "branch_creation", "before": v2.ZERO_SHA, "after": h0, "ref": "refs/heads/b",
            "timestamp": "t1"},
           {"id": 2, "activity_type": "push", "before": h0, "after": gate_head, "ref": "refs/heads/b", "timestamp": "t2"},
           {"id": 3, "activity_type": "force_push", "before": gate_head, "after": h0, "ref": "refs/heads/b",
            "timestamp": "t3"}]
    real_isanc = lambda a, b: v2._git("merge-base", "--is-ancestor", a, b, check=False, root=fresh).returncode == 0
    with pytest.raises(v2.SealedRefusal, match="force_push"):      # R26.6: real ancestry on the real fresh clone
        v2.check_activity(log, sha, h0, real_isanc, "refs/heads/b")
    with pytest.raises(v2.SealedRefusal):                         # even without the force_push label: the gate
        v2.check_activity(log[:2] + [dict(log[2], activity_type="push")], sha, h0, real_isanc, "refs/heads/b")


def test_R22_delete_and_recreate_is_refused_without_the_activity_check(tmp_path):
    origin, work, g, led, h0 = _closed_run_on_remote(tmp_path)
    other = tmp_path / "other"
    g("clone", "-q", "-b", "b", str(origin), str(other), cwd=tmp_path)
    g("push", "-q", "origin", ":refs/heads/b", cwd=other)                      # delete
    g("push", "-q", "origin", f"{h0}:refs/heads/b", cwd=other)                 # re-create before START
    with pytest.raises(v2.SealedRefusal, match="not a fast-forward"):
        led.fetch()


# ------------------------------------------------------------------ R22.1 / R23.2 host record on recorded JSON
PROBE = json.loads((Path(__file__).parent / "data/rotation_core_activity_probe_20261111.json").read_text())


def _chain(n=4, ref="refs/heads/b"):
    shas = [f"{i:040x}" for i in range(1, n + 1)]
    log = [{"id": 1, "activity_type": "branch_creation", "before": v2.ZERO_SHA, "after": shas[0], "ref": ref,
            "timestamp": "2026-11-11T00:00:01Z"}]
    for i in range(1, n):
        log.append({"id": i + 1, "activity_type": "push", "before": shas[i - 1], "after": shas[i], "ref": ref,
                    "timestamp": f"2026-11-11T00:00:{i + 1:02d}Z"})
    order = {s_: i for i, s_ in enumerate(shas)}
    return log, shas, (lambda a, b: a in order and b in order and order[a] <= order[b])


def test_R22_1_activity_clean_chain_passes_and_is_recorded():
    log, shas, anc = _chain()
    rec = v2.check_activity(log, shas[-1], shas[1], anc, "refs/heads/b")
    assert rec["activity_entries"] == 4 and re.fullmatch(r"[0-9a-f]{64}", rec["activity_sha256"])


def test_R22_1_activity_refusals():
    log, shas, anc = _chain()
    cases = {
        "force_push": [dict(e, activity_type="force_push") if e["id"] == 3 else e for e in log],
        "deletion": log + [{"id": 9, "activity_type": "branch_deletion", "before": shas[-1], "after": v2.ZERO_SHA,
                            "ref": "refs/heads/b", "timestamp": "2026-11-11T00:01:00Z"}],
        "broken": [dict(e, before="f" * 40) if e["id"] == 3 else e for e in log],
        "truncated": log[2:],                                   # does not reach the anchor / the creation
        "not_head": log[:-1],
        "other_ref": [dict(e, ref="refs/heads/x") if e["id"] == 2 else e for e in log],
        "empty": []}
    for name, lg in cases.items():
        with pytest.raises(v2.SealedRefusal):
            v2.check_activity(lg, shas[-1], shas[1], anc, "refs/heads/b")
    with pytest.raises(v2.SealedRefusal, match="anchor"):        # a full chain that does not contain the anchor
        v2.check_activity(log, shas[-1], "a" * 40, anc, "refs/heads/b")


def test_R22_1_recorded_probe_log_with_force_push_deletion_and_recreation_refuses():
    kinds = [e["activity_type"] for e in PROBE]
    assert kinds == ["branch_creation", "push", "force_push", "branch_deletion", "branch_creation"]
    with pytest.raises(v2.SealedRefusal, match="force_push"):
        v2.check_activity(PROBE, PROBE[-1]["after"], PROBE[0]["after"], lambda a, b: True, PROBE[0]["ref"])
    with pytest.raises(v2.SealedRefusal, match="force_push"):    # the clean-looking prefix up to the force push
        v2.check_activity(PROBE[:3], PROBE[2]["after"], PROBE[0]["after"], lambda a, b: True, PROBE[0]["ref"])
    v2.check_activity(PROBE[:2], PROBE[1]["after"], PROBE[0]["after"], lambda a, b: True, PROBE[0]["ref"])


def test_R22_1_api_failure_and_unparsable_body_refuse(monkeypatch):
    class R:
        def __init__(self, code, out): self.returncode, self.stdout = code, out
    monkeypatch.setattr(v2.subprocess, "run", lambda *a, **k: R(1, b""))
    with pytest.raises(v2.SealedRefusal, match="API call failed"):
        v2.gh_api("/x")
    monkeypatch.setattr(v2.subprocess, "run", lambda *a, **k: R(0, b"not json"))
    with pytest.raises(v2.SealedRefusal, match="did not parse"):
        v2.gh_api("/x")
    def raising(path, paginate=False):
        raise v2.SealedRefusal("refused: the GitHub API call failed")
    with pytest.raises(v2.SealedRefusal):
        v2.host_checks("0" * 40, v2.ROOT, raising, v2.BRANCH, v2.ANCHOR_COMMIT)


def test_R23_2_rules_and_ruleset_checked():
    good_rules = [{"type": "non_fast_forward"}, {"type": "deletion"}]
    good_rs = {"id": v2.RULESET_ID, "enforcement": "active", "bypass_actors": [], "updated_at": "u"}
    assert v2.check_rules(good_rules, good_rs) == {"ruleset_id": v2.RULESET_ID, "ruleset_updated_at": "u"}
    for rules, rs in (([{"type": "deletion"}], good_rs), ([], good_rs),
                      (good_rules, dict(good_rs, enforcement="evaluate")),
                      (good_rules, dict(good_rs, bypass_actors=[{"actor_id": 1}])),
                      (good_rules, {k: v for k, v in good_rs.items() if k != "bypass_actors"}),
                      (good_rules, dict(good_rs, id=1))):
        with pytest.raises(v2.SealedRefusal):
            v2.check_rules(rules, rs)


def test_R22_1_host_record_is_copied_into_every_ledger_entry(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    led.host_record = {"activity_entries": 7, "activity_sha256": "a" * 64, "ruleset_id": v2.RULESET_ID,
                       "ruleset_updated_at": "u"}
    s_ = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    assert all(e["host"] == led.host_record for e in led.entries())


# ------------------------------------------------------------------ R22.2 release pins
def test_R22_2_gate_commit_must_contain_the_gate_record(tmp_path):
    origin, work, g, led, h0 = _closed_run_on_remote(tmp_path)
    ents = led.entries()
    gate = ents[-1]
    r = {"branch_head_at_release": h0, "gate_commit": led.last_commit, "_gate_latest": gate}
    v2.check_release_pins(r, led.remote_sha, work, led)
    with pytest.raises(v2.SealedRefusal, match="does not contain"):
        v2.check_release_pins(dict(r, gate_commit=h0), led.remote_sha, work, led)
    with pytest.raises(v2.SealedRefusal, match="anchor"):
        v2.check_release_pins(dict(r, activity_anchor_commit="b" * 40), led.remote_sha, work, led)
    with pytest.raises(v2.SealedRefusal):
        v2.check_release_pins({k: v for k, v in r.items() if k != "branch_head_at_release"}, led.remote_sha, work, led)


# ------------------------------------------------------------------ R23.1 identical rerun binds permanently (D1, D2)
def test_R23_1_d1_killed_identical_rerun_cannot_unlock_a_new_commit():
    L = v2.MemoryLedger()
    s0 = L.append(_start(rel="R1"))
    L.append({"kind": "PHASE_A_CLEAN", "start_index": s0["index"]})
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(L.entries(), _start(eng="E2", rel="R2"), {"ledger_records_cited": [0]})
    v2.start_allowed(L.entries(), _start(rel="R1"), {})
    L.append(_start(rel="R1"))                                                  # killed before Phase A
    with pytest.raises(v2.SealedRefusal, match="permanently"):
        v2.start_allowed(L.entries(), _start(eng="E2", rel="R2"), {"ledger_records_cited": [0, 2]})
    with pytest.raises(v2.SealedRefusal):
        L2 = v2.MemoryLedger(L.entries() + [dict(_start(eng="E2", rel="R2"), index=3,
                                                 prev_chain_sha256=v2.chain_hash(L.entries()))])
        v2.validate_ledger(L2.entries(), [], {"R1": {}, "R2": {"ledger_records_cited": [0, 2]}})
    v2.start_allowed(L.entries(), _start(rel="R1"), {})                          # the identical rerun stays allowed
    L.append(_start(rel="R1")); s3 = L.entries()[-1]
    L.append({"kind": "PHASE_A_CLEAN", "start_index": s3["index"]})
    L.append({"kind": "GATE", "start_index": s3["index"], "gate_signs": _all_plus(), "gate_open": True,
              "magnitudes_sha256": "d" * 64})
    v2.start_allowed(L.entries(), _start(eng="E2", rel="R2"), {"ledger_records_cited": [0, 2]})   # completed: free


def test_R23_1_d2_failed_gate_push_leaves_only_the_identical_rerun(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    s_ = led.append(_start(rel="R1")); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    hook = origin / "hooks" / "pre-receive"; hook.write_text("#!/bin/sh\nexit 1\n"); hook.chmod(0o755)
    with pytest.raises(v2.LedgerPushFailed, match="UNKNOWN"):
        led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _closed(), "gate_open": False,
                    "magnitudes_sha256": "d" * 64})
    hook.unlink()
    led.fetch()
    ents = led.entries()
    assert [e["kind"] for e in ents] == ["START", "PHASE_A_CLEAN"]
    led.append(_start(rel="R1"))                                                 # identical rerun, killed after START
    for st, rel in ((_start(eng="E2", rel="R2"), {"ledger_records_cited": [0, 2]}), (_start(rel="R9"), {})):
        with pytest.raises(v2.SealedRefusal):
            v2.start_allowed(led.entries(), st, rel)


def test_R23_1_n2_start_rules_rechecked_on_fresh_entries_inside_append(tmp_path):
    origin, work, g = _git_env(tmp_path)
    a = _gled(work, origin); a.fetch()
    other = tmp_path / "w2"; g("clone", "-q", "-b", "b", str(origin), str(other), cwd=tmp_path)
    b = _gled(other, origin); b.fetch()
    stale = b.entries()                                                           # [] when B checked
    new = _start(eng="E2", rel="R2")
    v2.start_allowed(stale, new, {})
    s_ = a.append(_start()); a.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    a.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _closed(), "gate_open": False,
              "magnitudes_sha256": "d" * 64})
    with pytest.raises(v2.SealedRefusal, match="closed"):
        b.append(new, precheck=lambda cur: v2.start_allowed(cur, new, {}))
    b.fetch()
    assert [e["kind"] for e in b.entries()] == ["START", "PHASE_A_CLEAN", "GATE"]


# ------------------------------------------------------------------ R23.3 remote identity
def test_R23_3_remote_identity(tmp_path, monkeypatch):
    origin, work, g = _git_env(tmp_path)
    url = str(origin)
    v2.check_remote_identity(work, url)
    with pytest.raises(v2.SealedRefusal, match="pinned repository"):
        v2.check_remote_identity(work, v2.REMOTE_URL)
    g("config", "remote.origin.pushurl", str(tmp_path / "elsewhere.git"), cwd=work)
    with pytest.raises(v2.SealedRefusal, match="pinned repository"):
        v2.check_remote_identity(work, url)
    g("config", "--unset", "remote.origin.pushurl", cwd=work)
    g("config", "url./tmp/fake.git.insteadOf", url, cwd=work)
    with pytest.raises(v2.SealedRefusal, match="insteadOf"):
        v2.check_remote_identity(work, url)
    g("config", "--remove-section", "url./tmp/fake.git", cwd=work)
    g("config", "url./tmp/fake.git.pushInsteadOf", url, cwd=work)
    with pytest.raises(v2.SealedRefusal, match="insteadOf"):
        v2.check_remote_identity(work, url)
    g("config", "--remove-section", "url./tmp/fake.git", cwd=work)
    v2.check_remote_identity(work, url)
    for var in ("GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_GLOBAL"):
        monkeypatch.setenv(var, "1")
        with pytest.raises(v2.SealedRefusal, match="GIT_CONFIG"):
            v2.check_remote_identity(work, url)
        monkeypatch.delenv(var)


def test_R23_3_real_checkout_has_the_pinned_identity():
    v2.check_remote_identity(v2.ROOT, v2.REMOTE_URL)


# ------------------------------------------------------------------ R23.4 interpreter environment (real paths)
def test_R23_4_startup_and_home_variables_refused(monkeypatch):
    for var in ("PYTHONSTARTUP", "PYTHONHOME"):
        monkeypatch.setenv(var, "/tmp/x")
        with pytest.raises(v2.SealedRefusal, match=var):
            v2.check_import_environment()
        monkeypatch.delenv(var)


def test_R23_4_location_test_follows_symlinks(monkeypatch, tmp_path):
    import types, sysconfig
    lib = tmp_path / "lib"; lib.mkdir(); elsewhere = tmp_path / "elsewhere"; elsewhere.mkdir()
    (elsewhere / "evil.py").write_text("x = 1\n"); (lib / "evil.py").symlink_to(elsewhere / "evil.py")
    (lib / "fine.py").write_text("x = 1\n")
    real = sysconfig.get_paths()
    monkeypatch.setattr(sysconfig, "get_paths", lambda *a, **k: dict(real, platstdlib=str(lib)))
    m = types.ModuleType("fine_mod"); m.__file__ = str(lib / "fine.py")
    monkeypatch.setitem(sys.modules, "fine_mod", m)
    v2.check_import_environment()                                            # a real file inside an allowed root
    m2 = types.ModuleType("evil_mod"); m2.__file__ = str(lib / "evil.py")     # link inside, real file outside
    monkeypatch.setitem(sys.modules, "evil_mod", m2)
    with pytest.raises(v2.SealedRefusal, match="evil_mod"):
        v2.check_import_environment()


def test_R22_4_every_loaded_module_lies_under_the_interpreter_or_the_repository(monkeypatch, tmp_path):
    import types
    v2.check_import_environment()
    m = types.ModuleType("stray"); m.__file__ = str(tmp_path / "stray.py")
    monkeypatch.setitem(sys.modules, "stray", m)
    with pytest.raises(v2.SealedRefusal, match="stray"):
        v2.check_import_environment()


# ------------------------------------------------------------------ R23.7 fund veto fails closed
def test_R23_7_fund_veto_fires_on_nan_and_negative_only_finite_nonnegative_passes():
    assert v2.tradable_veto({"a": 0.01, "b": 0.0}) is False
    assert v2.tradable_veto({"a": 0.01, "b": float("nan")}) is True
    assert v2.tradable_veto({"a": float("inf"), "b": 0.1}) is True
    assert v2.tradable_veto({"a": -1e-9}) is True


# ------------------------------------------------------------------ R22.3 witness lines
def test_R22_3_witness_lines_start_and_gate_before_any_sign(stage1):
    d, e, lines, _, led = stage1
    i_start = next(i for i, ln in enumerate(lines) if ln.startswith("WITNESS start_commit "))
    i_gate = next(i for i, ln in enumerate(lines) if ln.startswith("WITNESS gate_commit "))
    i_sign = min(i for i, ln in enumerate(lines) if ln.startswith("GATE_SIGN"))
    assert i_start < i_gate < i_sign and lines[i_gate].endswith(f"ledger_index {e['index']}")


# ------------------------------------------------------------------ R20.3 / R20.6 final run trusts nothing recorded
def test_R20_6_reproduction_hash_and_signs_are_required(tmp_path):
    import scripts.run_rotation_core_v2 as run, inspect
    p = inspect.signature(run.final_evaluation).parameters
    assert p["expected_sha"].default is inspect.Parameter.empty and p["expected_signs"].default is inspect.Parameter.empty
    for sha, signs in ((None, _all_plus()), ("x", _all_plus()), ("a" * 64, _closed()), ("a" * 64, {})):
        with pytest.raises(v2.SealedRefusal):
            run.final_evaluation("p", "f", "c", "d", sha, signs, v2.MemoryLedger(), 0, selection=ORIG_SELECTION)


def _stage2_ledger(signs, sha):
    led = v2.MemoryLedger()
    s_ = led.append(_start(eng="E1", rel="r1")); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": signs, "gate_open": v2.gate_decision(signs)[0],
                "magnitudes_sha256": sha})
    ents = led.entries()
    r2 = v2.verify_release2({"windows_released": [v2.W_H], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
                             "engine_commit": "E1", "ledger_prefix_len": len(ents),
                             "ledger_prefix_chain_sha256": v2.chain_hash(ents)}, ents)
    return led, r2


@pytest.fixture(scope="module")
def stage2_dirs(tmp_path_factory):
    d = tmp_path_factory.mktemp("s2")
    return make_fixture(d / "full", extra_after="2025-12-31"), make_fund_fixture(d / "funds")


def test_R20_3_R24_1a_stage1_not_reproduced_is_an_integrity_abort_with_no_final(stage1, fx, stage2_dirs, monkeypatch):
    """R24.1(a): the reproduction runs as Phase A2, before any 2020-2025 statistic. Hash reproduced but the gate
    re-derived differs from the record, and a plain hash mismatch: each ends INTEGRITY_ABORT, reason only, no FINAL."""
    import scripts.run_rotation_core_v2 as run
    d, e, lines0, _, led0 = stage1
    full, funds = stage2_dirs
    def boom(*a, **k):
        raise AssertionError("a 2020-2025 statistic was computed")
    monkeypatch.setattr(run, "_final_phase_b", boom)
    for sha in (e["magnitudes_sha256"], "a" * 64):
        led, r2 = _stage2_ledger(_all_plus(), sha)
        lines = []
        with v2.stage2_opened([], recorded={}):
            res = run.confirm_command(led, r2, "q1", "E1", fx / IND, full / IND, full / FAC, funds, {"x": "1"}, B_=20,
                                      out=lines.append, selection=ORIG_SELECTION)
        assert res == {"integrity_abort": True, "reason": "stage1_not_reproduced"}
        ents = led.entries()
        assert [x["kind"] for x in ents][-3:] == ["START", "PHASE_A_CLEAN", "INTEGRITY_ABORT"]
        assert ents[-1]["reason"] == "stage1_not_reproduced" and not any(x["kind"] == "FINAL" for x in ents)
        assert lines[-1] == "INTEGRITY_ABORT stage1_not_reproduced"
        v2.validate_ledger(ents, [], {"r1": {}, "q1": {}})
        # governed by R19: the same release refused; a new release citing the run may retry (the reference is fixed)
        with pytest.raises(v2.SealedRefusal):
            v2.start_allowed(ents, _start("stage2", "q1", "E1"), {"ledger_records_cited": [3]})
        with pytest.raises(v2.SealedRefusal):
            v2.start_allowed(ents, _start("stage2", "q2", "E1"), {})
        v2.start_allowed(ents, _start("stage2", "q2", "E1"), {"ledger_records_cited": [3]})


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


def test_R20_8_sitecustomize_hash_is_pinned_in_versions(fx):
    sc = getattr(sys.modules.get("sitecustomize"), "__file__", None)
    v = v2.versions()
    assert v["sitecustomize_sha256"] == (v2.sha256_file(sc) if sc else None)
    ins = {"industries": fx / IND}
    good = {"inputs_sha256": {k: v2.sha256_file(p) for k, p in ins.items()}, "versions": v}
    v2.check_manifest(good, ins)
    with pytest.raises(v2.SealedRefusal, match="library versions"):
        v2.check_manifest(dict(good, versions=dict(v, sitecustomize_sha256="0" * 64)), ins)
    with pytest.raises(v2.SealedRefusal, match="library versions"):
        v2.check_manifest(dict(good, versions=dict(v, pth_sha256="0" * 64)), ins)


# ------------------------------------------------------------------ R20.9 selection rerun on the remote
def test_R20_9_stage1_checks_selection_commit_and_file_against_the_remote(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "_committed_clean", lambda p, root=None: True)
    import hashlib
    body = {"windows_released": [v2.W_PRE], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
            "selected_grid_point": {"h_near_high_pct": 3, "b_breadth_drop_pp": 25}, "engine_commit": "X",
            "selection_results_commit": "HEAD",
            "selection_results_sha256": hashlib.sha256(ORIG_SELECTION.read_bytes()).hexdigest()}
    p = tmp_path / "r1.json"; p.write_text(json.dumps(body))
    old = v2._git("rev-list", "--max-parents=0", "HEAD").stdout.decode().split()[0]   # a remote that lacks HEAD
    with pytest.raises(v2.SealedRefusal, match="is not contained in the remote branch"):     # the remote check
        v2.stage1_release(p, remote_sha=old, engine_check=lambda c: None, selection=ORIG_SELECTION, root=v2.ROOT)


# ------------------------------------------------------------------ R20.10 planted-edge end to end, verdicts exact
def _slow(t, amp=0.0015):
    return amp if (t.year // 2) % 2 == 0 else -amp


def _edge_pass(t):
    return _slow(t)


def _edge_late_fail(t):
    if t.year >= 2020:
        return 0.0004 if ((t.year * 12 + t.month) // 2) % 2 == 0 else -0.0004
    return _slow(t)


def _commit_push(g, work, name, doc):
    (work / name).write_text(json.dumps(doc, indent=1))
    g("add", name, cwd=work); g("commit", "-q", "-m", name, cwd=work); g("push", "-q", "origin", "b", cwd=work)
    return g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()


def _e2e_setup(d, edge=None, fund_sign=1.0, B_=200):
    """A temporary bare remote and clone with the selection file and a pushed stage-1 release; fixtures outside it."""
    import shutil, hashlib
    d = Path(d)
    origin, work, g = _git_env(d)
    shutil.copy(ORIG_SELECTION, work / "sel.json")
    g("add", "sel.json", cwd=work); g("commit", "-q", "-m", "selection", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    sel_commit = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    pre = make_fixture(d / "pre", edge=edge)
    full = make_fixture(d / "full", extra_after="2025-12-31", edge=edge)
    funds = make_fund_fixture(d / "funds", edge=edge, edge_sign=fund_sign)
    s1_in = {"industries_le2019": pre / IND, "factors": full / FAC}
    s2_in = {"industries_full": full / IND, "industries_le2019": pre / IND, "factors": full / FAC,
             **{f"yahoo_{t}": funds / f"{t}.parquet" for t in ["SPY", "RSP"] + v2.FUNDS}}
    ctx = {"root": work, "ledger_path": work / "ledger.json", "branch": "b", "remote_url": str(origin),
           "release1": work / "r1.json", "release2": work / "r2.json", "selection": work / "sel.json",
           "ind_d": pre / IND, "ind_full": full / IND, "fact": full / FAC, "fund_dir": funds,
           "stage1_inputs": s1_in, "stage2_inputs": s2_in, "anchor": sel_commit, "B": B_,
           "final_j": d / "final.json", "final_m": d / "final.md", "stage1_published": d / "published.json",
           "ledger_status_j": d / "status.json", "ledger_status_m": d / "status.md",
           "selection_rerun_j": d / "selrerun.json", "selection_rerun_m": d / "selrerun.md",
           "sealed_paths": [], "sealed_recorded": {}, "host_stub": True, "engine_stub": True}
    r1_commit = _commit_push(g, work, "r1.json", {
        "windows_released": [v2.W_PRE], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
        "selected_grid_point": {"h_near_high_pct": 3, "b_breadth_drop_pp": 25}, "engine_commit": "E1",
        "selection_results_commit": sel_commit,
        "selection_results_sha256": hashlib.sha256((work / "sel.json").read_bytes()).hexdigest(),
        "inputs_sha256": {k: v2.sha256_file(p) for k, p in s1_in.items()}, "versions": v2.versions(),
        "branch_head_at_release": sel_commit})
    return {"d": d, "origin": origin, "work": work, "g": g, "ctx": ctx, "r1_commit": r1_commit, "s2_in": s2_in}


def _e2e(d, edge, fund_sign=1.0, B_=200, capture=None):
    """R23.6/R25.1(a): through the real entry point main() in a real `python -E` subprocess (the test driver), with
    the real GitLedger on a temporary bare remote. Only the host API and the engine-commit check are stubbed."""
    S = _e2e_setup(d, edge, fund_sign, B_)
    d, work, g, ctx = S["d"], S["work"], S["g"], S["ctx"]
    r = _py([], {"argv": ["--stage", "pre1998"], "ctx": ctx}, d)
    assert r.returncode == 0, r.stderr[-800:]
    out1 = r.stdout.splitlines()
    w1 = next(ln.split() for ln in out1 if ln.startswith("WITNESS start_commit"))
    gate_commit = next(ln.split()[2] for ln in out1 if ln.startswith("WITNESS gate_commit"))
    assert w1[3:] == ["branch", "b"]
    ents = json.loads((work / "ledger.json").read_text())["entries"]
    head = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    _commit_push(g, work, "r2.json", {
        "windows_released": [v2.W_H], "protocol_header_sha256": v2.FROZEN_V2_SHA256, "engine_commit": "E1",
        "ledger_prefix_len": len(ents), "ledger_prefix_chain_sha256": v2.chain_hash(ents),
        "branch_head_at_release": head, "gate_commit": gate_commit,
        "inputs_sha256": {k: v2.sha256_file(p) for k, p in S["s2_in"].items()}, "versions": v2.versions(),
        "witnessed": {"branch": "b", "release_commit": S["r1_commit"], "start_commit": w1[2],
                      "gate_commit": gate_commit, "witness_utc": "2026-11-11T16:00Z", "acknowledged_at": "test"},
        "witness_confirmation_utc": (__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                                     + __import__("datetime").timedelta(minutes=2)).isoformat()})
    cfg = {"argv": ["--stage", "confirm"], "ctx": ctx}
    if capture is not None:
        cfg["capture_keys"] = str(d / "keys.json")
    r = _py([], cfg, d)
    assert r.returncode == 0, r.stderr[-800:]
    if capture is not None:
        capture.extend(tuple(k) for k in json.loads((d / "keys.json").read_text()))
    res = json.loads((d / "final.json").read_text())
    led_entries = json.loads((work / "ledger.json").read_text())["entries"]
    gate = next(e for e in led_entries if e["kind"] == "GATE")
    return gate, res, led_entries, out1


SIGN_2020 = sorted(f"sign|h2020_2025|{r}|{c}" for r in ("eq", "drift") for c in ("base", "strict"))


E2E_KEYS = []


@pytest.fixture(scope="module")
def e2e_pass(tmp_path_factory):
    return _e2e(tmp_path_factory.mktemp("e2e_pass"), _edge_pass, capture=E2E_KEYS)


def test_R20_10_planted_edge_must_pass(e2e_pass):
    g, res, ents, out1 = e2e_pass
    assert g["gate_open"] is True
    assert {h: v["verdict"] for h, v in res["verdicts"].items()} == {
        "H1": "FAIL", "H2": "FAIL", "H3": "survives falsification on history"}
    assert res["verdicts"]["H3"]["failed_legs"] == [] and res["verdicts"]["H3"]["fund_veto_fired"] is False
    assert [x["kind"] for x in ents] == ["START", "PHASE_A_CLEAN", "GATE", "START", "PHASE_A_CLEAN", "REPRODUCTION_OK",
                                        "FINAL"]
    assert ents[-1]["verdicts"]["H3"] == "survives falsification on history"
    assert all(e["host"]["ruleset_id"] == v2.RULESET_ID for e in ents)              # R22.1/R23.2 recorded
    assert res["witnessed"]["acknowledged_at"] == "test" and res["witnessed"]["branch"] == "b"


def test_R20_10_planted_edge_fails_only_on_the_2020_2025_sign_legs(tmp_path):
    g, res, ents, out1 = _e2e(tmp_path, _edge_late_fail)
    assert g["gate_open"] is True
    assert res["verdicts"]["H3"]["verdict"] == "FAIL"
    assert res["verdicts"]["H3"]["failed_legs"] == SIGN_2020


def test_R20_10_planted_edge_trips_the_fund_veto(tmp_path):
    g, res, ents, out1 = _e2e(tmp_path, _edge_pass, fund_sign=-1.0)
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


# ------------------------------------------------------------------ R21
def test_R21_0_R22_4_pth_files_pinned_in_versions(tmp_path, monkeypatch):
    v = v2.versions()
    assert isinstance(v["pth_count"], int) and re.fullmatch(r"[0-9a-f]{64}", v["pth_sha256"])
    d = tmp_path / "site-packages"; d.mkdir()
    monkeypatch.setattr(v2, "site_dirs", lambda: [str(d)])
    empty = v2.pth_digest()
    (d / "x.pth").write_text("import os\n")
    one = v2.pth_digest()
    assert one[0] == 1 and one[1] != empty[1]
    (d / "x.pth").write_text("import sys\n")
    assert v2.pth_digest()[1] != one[1]


def test_R21_1_phase_b_exception_records_a_closed_gate_on_the_remote(fx, tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    led = run.temporary_remote(tmp_path)
    orig, n = v2.window_excess, [0]
    def after_first(*a, **k):
        n[0] += 1
        if n[0] > 1:                                      # the first era excess exists, then a failure
            raise ValueError("value 0.0123 inside")
        return orig(*a, **k)
    monkeypatch.setattr(v2, "window_excess", after_first)
    lines = []
    with pytest.raises(SystemExit) as ei:
        run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20, out=lines.append, selection=ORIG_SELECTION)
    assert "ValueError" in str(ei.value) and "0.0123" not in str(ei.value)
    led.fetch()
    ents = led.entries()
    assert [x["kind"] for x in ents] == ["START", "PHASE_A_CLEAN", "GATE"]
    g = ents[-1]
    assert g["gate_open"] is False and g["closed_by"] == "phase_b_exception" and g["exception_type"] == "ValueError"
    assert "gate_signs" not in g and "magnitudes_sha256" not in g and "0.0123" not in json.dumps(ents)
    assert not any(ln.startswith("GATE_SIGN") for ln in lines) and _no_magnitude("\n".join(lines))
    v2.validate_ledger(ents, led.version_entries(), {"r1": {}})               # a consistent record
    for st in (_start(eng="E2", rel="r2", ins={"a": "1"}), _start(ins={"a": "1"}), _start("stage2", "q", "E1")):
        with pytest.raises(v2.SealedRefusal):                                    # closed: final at any commit
            v2.start_allowed(ents, st, {"ledger_records_cited": []})


def test_R21_1_memory_error_leaves_phase_a_clean_and_the_identical_rerun_completes(fx, tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    led = run.temporary_remote(tmp_path)
    def oom(*a, **k):
        raise MemoryError()
    with monkeypatch.context() as m:
        m.setattr(v2, "window_excess", oom)
        with pytest.raises(SystemExit):
            run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20, out=lambda x: None, selection=ORIG_SELECTION)
    led.fetch()
    assert [x["kind"] for x in led.entries()] == ["START", "PHASE_A_CLEAN"]
    with pytest.raises(v2.SealedRefusal):                                    # anything but the identical rerun
        run.stage1_command(led, {}, "r1", "E2", fx / IND, fx / FAC, {"a": "1"}, B_=20, out=lambda x: None, selection=ORIG_SELECTION)
    g = run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20, out=lambda x: None, selection=ORIG_SELECTION)
    led.fetch()
    assert g["kind"] == "GATE" and "gate_signs" in g
    assert [x["kind"] for x in led.entries()] == ["START", "PHASE_A_CLEAN", "START", "PHASE_A_CLEAN", "GATE"]


@pytest.fixture(scope="module")
def open_stage1(tmp_path_factory):
    """A planted-edge stage 1 whose gate is open, recorded in an in-memory ledger (B = 20)."""
    import scripts.run_rotation_core_v2 as run
    v2.SELECTION_RESULT = ORIG_SELECTION
    d = tmp_path_factory.mktemp("open_s1")
    pre = make_fixture(d / "pre", edge=_edge_pass)
    full = make_fixture(d / "full", extra_after="2025-12-31", edge=_edge_pass)
    funds = make_fund_fixture(d / "funds", edge=_edge_pass)
    led = v2.MemoryLedger()
    g = run.stage1_command(led, {}, "r1", "E1", pre / IND, pre / FAC, {"x": "1"}, B_=20, out=lambda x: None, selection=ORIG_SELECTION)
    assert g["gate_open"] is True
    return pre, full, funds, led.entries()


def _confirm_with_planted(open_stage1, monkeypatch, target, exc):
    import scripts.run_rotation_core_v2 as run
    pre, full, funds, ents = open_stage1
    led = v2.MemoryLedger(); [led.append({k: v for k, v in e.items() if k not in ("index", "prev_chain_sha256")}) for e in ents]
    r2 = v2.verify_release2({"windows_released": [v2.W_H], "protocol_header_sha256": v2.FROZEN_V2_SHA256,
                             "engine_commit": "E1", "ledger_prefix_len": len(ents),
                             "ledger_prefix_chain_sha256": v2.chain_hash(led.entries())}, led.entries())
    def boom(*a, **k):
        raise exc
    monkeypatch.setattr(run, target, boom)
    lines = []
    with v2.stage2_opened([], recorded={}), pytest.raises(SystemExit) as ei:     # R25.1(b): ends in the hard exit
        run.confirm_command(led, r2, "q1", "E1", pre / IND, full / IND, full / FAC, funds, {"x": "1"}, B_=20,
                            out=lines.append, selection=ORIG_SELECTION)
    return str(ei.value), led.entries(), lines


def test_R21_1_stage2_phase_b_exception_records_final_all_fail(open_stage1, monkeypatch):
    res, ents, lines = _confirm_with_planted(open_stage1, monkeypatch, "fund_stats", ZeroDivisionError())
    f = ents[-1]
    assert [x["kind"] for x in ents][-4:] == ["START", "PHASE_A_CLEAN", "REPRODUCTION_OK", "FINAL"]
    assert f["closed_by"] == "phase_b_exception" and f["exception_type"] == "ZeroDivisionError"
    assert f["verdicts"] == {"H1": "FAIL", "H2": "FAIL", "H3": "FAIL"} and "ZeroDivisionError" in res
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(ents, _start("stage2", "q2", "E1"), {})


def test_R24_1b_stage2_refusal_in_phase_b_records_final_all_fail(open_stage1, monkeypatch):
    res, ents, lines = _confirm_with_planted(open_stage1, monkeypatch, "fund_stats",
                                             v2.SealedRefusal("refused: planted"))
    f = ents[-1]
    assert f["kind"] == "FINAL" and f["closed_by"] == "phase_b_refusal" and f["exception_type"] == "SealedRefusal"
    assert f["verdicts"] == {"H1": "FAIL", "H2": "FAIL", "H3": "FAIL"} and "planted" not in json.dumps(ents)
    v2.validate_ledger(ents, [], {"r1": {}, "q1": {}})


def test_R24_1b_stage1_refusal_in_phase_b_records_a_closed_gate_on_the_remote(fx, tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    led = run.temporary_remote(tmp_path)
    orig, n = v2.window_excess, [0]
    def after_first(*a, **k):
        n[0] += 1
        if n[0] > 1:
            raise v2.SealedRefusal("refused: planted 0.0123")
        return orig(*a, **k)
    monkeypatch.setattr(v2, "window_excess", after_first)
    lines = []
    with pytest.raises(SystemExit) as ei:
        run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20, out=lines.append, selection=ORIG_SELECTION)
    assert "SealedRefusal" in str(ei.value) and "0.0123" not in str(ei.value)
    led.fetch()
    ents = led.entries()
    assert [x["kind"] for x in ents] == ["START", "PHASE_A_CLEAN", "GATE"]
    g = ents[-1]
    assert g["gate_open"] is False and g["closed_by"] == "phase_b_refusal" and g["exception_type"] == "SealedRefusal"
    assert "gate_signs" not in g and "0.0123" not in json.dumps(ents) and not any("GATE_SIGN" in x for x in lines)
    v2.validate_ledger(ents, led.version_entries(), {"r1": {}})
    with pytest.raises(v2.SealedRefusal):
        v2.start_allowed(ents, _start(eng="E2", rel="r2", ins={"a": "1"}), {})


def test_R24_1_ledger_order_a2_before_final():
    led = v2.MemoryLedger()
    s_ = led.append(_start("stage2", "q1", "E1")); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    bad = v2.MemoryLedger(led.entries())
    bad.append({"kind": "FINAL", "start_index": s_["index"], "verdicts": {}})            # FINAL without A2
    with pytest.raises(v2.SealedRefusal, match="out of order"):
        v2._runs(bad.entries())
    led.append({"kind": "REPRODUCTION_OK", "start_index": s_["index"]})
    led.append({"kind": "FINAL", "start_index": s_["index"], "verdicts": {}})
    assert v2._runs(led.entries())[0]["record"]["kind"] == "FINAL"


# ------------------------------------------------------------------ R24.5 the command line runs the real checks
def test_R24_5_R26_2_real_hooks_with_an_absent_release_path(tmp_path):
    """R26.2: the context's release path is an absent path; the host check (real `gh`, network) and the engine-commit
    check are the real ones. Runs in a real `python -E` subprocess."""
    out = tmp_path / "calls.json"
    r = _py([], {"mode": "real_hooks", "out": str(out)}, tmp_path)
    assert r.returncode == 0, r.stderr[-600:]
    calls = json.loads(out.read_text())
    assert calls["host_api_is_none"] is True and calls["ruleset_id"] == v2.RULESET_ID
    assert calls["engine_check_is_real"] is True
    assert "__absent_release_for_tests__.json" in calls["refusal"]
    assert calls["input_reads"] == 0                                   # R31.4: no input file was opened


def test_R26_2_no_context_sealed_stage_under_pytest_refuses_even_with_a_release(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    origin, work, g = _git_env(tmp_path)
    rel = work / "HOLDOUT_RELEASE_v2.json"; rel.write_text(json.dumps({"windows_released": [v2.W_PRE]}))
    g("add", rel.name, cwd=work); g("commit", "-q", "-m", "release", cwd=work)
    monkeypatch.setattr(v2, "RELEASE", rel)                       # a release EXISTS (temporary repository only)
    for stage in ("pre1998", "confirm"):
        with pytest.raises(SystemExit, match="pytest"):
            run.main(["--stage", stage])


def test_R24_5_no_option_or_environment_variable_sets_the_test_context():
    import inspect, scripts.run_rotation_core_v2 as run
    r = _py(["scripts/run_rotation_core_v2.py", "--help"])
    assert r.returncode == 0
    assert not re.search(r"ctx|host|engine.check|stub|anchor", r.stdout, re.I)
    for f in (run.main, run.Ctx, run.verified_ledger, run.run_once_guard, run.start_checks):
        src = inspect.getsource(f)
        assert "os.environ" not in src and "getenv" not in src and "environ[" not in src
    assert inspect.signature(run.main).parameters["_ctx"].default is None


def test_R21_3_nonfinite_pooled_p_is_counted_never_rejected_and_fails_its_hypothesis():
    import scripts.run_rotation_core_v2 as run, copy
    h, bad = run.holm_safe({"H1": float("nan"), "H2": 0.5, "H3": 0.001})
    assert bad == ["H1"] and h["H1"]["reject_h0"] is False and h["H3"]["reject_h0"] is True
    R = _passing_inputs()
    point = copy.deepcopy(R["point"]); dd = copy.deepcopy(R["drawdown"])
    pooled = {"block21": {"eq|base|weekday": {hy: {"observed_ann_CONDITIONAL_ON_GATE": 0.01, "p_one_sided_centred": 0.001}
                                              for hy in run.HYPS}}}
    pooled["block21"]["eq|base|weekday"]["H1"]["p_one_sided_centred"] = float("nan")
    funds = {"eq|base": {hy: 0.01 for hy in run.HYPS}}
    stand = {"block21": {f"eq|base|{hy}": {"observed_ann": 0.01, "p_one_sided_centred": 0.2} for hy in run.HYPS}}
    n = run.nonfinite_by_hypothesis(pooled, point, dd, funds, stand)
    assert n == {"H1": 1, "H2": 0, "H3": 0}
    R["integrity_ok"] = {hy: n[hy] == 0 for hy in run.HYPS}
    assert run.conjunction_legs("H1", R)["integrity"] is False
    assert all(run.conjunction_legs("H3", R).values())
    funds["eq|base"]["H3"] = float("nan"); point["eq|base"]["H2"]["h2020_2025"] = float("inf")
    assert run.nonfinite_by_hypothesis(pooled, point, dd, funds, stand) == {"H1": 1, "H2": 1, "H3": 1}


def test_R21_3_stage1_counts_nonfinite_gate_statistics(stage1):
    d, e, lines, _, led = stage1
    assert "count nonfinite_gate_statistics 0" in lines
    assert any(ln.startswith("count dropped_industry_days_unique_eligible_industries_only") for ln in lines)


def test_R21_4_every_stream_key_distinct_and_the_final_run_uses_exactly_them(e2e_pass):
    import scripts.run_rotation_core_v2 as run
    keys = run.stream_keys()                                             # B = 10,000: 20 chunks
    assert len(keys) == len(set(keys)) == 4 * 2 * 20
    states = {tuple(np.random.SeedSequence(run.SEED_BASE, spawn_key=k).generate_state(4)) for k in keys}
    assert len(states) == len(keys)
    assert all(isinstance(k, tuple) for k in E2E_KEYS)                   # no integer seed reaches the bootstrap
    assert len(E2E_KEYS) == len(set(E2E_KEYS)) and set(E2E_KEYS) == set(run.stream_keys(200))


def test_R21_5_fund_drawdowns_and_provenance(e2e_pass, tmp_path):
    res = e2e_pass[1]
    fd = res["funds"]["fund_drawdown_DESCRIPTIVE_not_a_leg_of_the_veto"]
    assert len(fd) == 8 and all(set(v) == {"book", "matched_mix"} and v["book"] <= 0 for v in fd.values())
    assert "through-2019 French file" in res["data_provenance"]


def test_R21_6_rehearsal_on_synthetic_open_window(tmp_path):
    import scripts.run_rotation_core_v2 as run
    ind, fac = fixture_texts(start="1996-01-02", end="2019-12-31")
    lines = []
    e = run.rehearsal_command(io.StringIO(ind), io.StringIO(fac), out=lines.append, B_=20, engine_commit="E", selection=ORIG_SELECTION)
    assert e["kind"] == "GATE" and e["window"] == "rehearsal_1998_2019"
    assert set(k.split("|")[1] for k in e["gate_signs"]) == {"P1_1998_2008", "P2_2009_2019"} and len(e["gate_signs"]) == 16
    assert lines and all(ln.startswith("REHEARSAL ") for ln in lines)
    assert "REHEARSAL ledger START PHASE_A_CLEAN GATE" in lines


def test_R21_6_rehearsal_refuses_inputs_outside_1996_2019():
    import scripts.run_rotation_core_v2 as run
    for start, end in (("1995-12-01", "2019-12-31"), ("1996-01-02", "2020-01-10")):
        ind, fac = fixture_texts(start=start, end=end, n_ind=12)
        with pytest.raises(v2.SealedRefusal):
            run.rehearsal_command(io.StringIO(ind), io.StringIO(fac), out=lambda x: None, B_=20, engine_commit="E", selection=ORIG_SELECTION)


def test_R21_6_window_text_keeps_only_dated_lines_in_range():
    import scripts.run_rotation_core_v2 as run
    ind, _ = fixture_texts(start="1994-01-03", end="2020-03-31", n_ind=6)
    w = run.window_text(io.StringIO(ind))
    run.check_rehearsal_input(w)
    vw, _ = v2.load_french_industries(w, "2019-12-31")
    assert vw.index.min() >= pd.Timestamp("1996-01-02") and vw.index.max() <= pd.Timestamp("2019-12-31")


# ------------------------------------------------------------------ R25.1(a) -E enforced
def test_R25_1a_the_runner_refuses_without_E_or_when_interactive():
    for flags, env in ((("-P",), None), (RUN_FLAGS + ("-i",), None), (("-P",), _clean_env(PYTHONINSPECT="1"))):
        r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"], flags=flags, env=env)
        assert "R25.1(a)" in (r.stdout + r.stderr) and "GATE_SIGN" not in r.stdout, (flags, r.stderr[-300:])
    r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"])
    assert r.returncode == 0


# ------------------------------------------------------------------ R25.1(b) + R26.1 through main() in a real process
def _assert_no_leak(work, lines_out, err):
    assert "Traceback" not in err and "GATE_SIGN" not in lines_out and _no_magnitude(lines_out + err)
    unreachable = subprocess.run([v2.tool("git"), "-C", str(work), "fsck", "--unreachable", "--no-reflogs"],
                                 capture_output=True, text=True).stdout.split()
    for o in (x for x in unreachable if len(x) == 40):
        body = subprocess.run([v2.tool("git"), "-C", str(work), "cat-file", "-p", o], capture_output=True).stdout
        assert b"gate_open" not in body, "a GATE blob reached the real object store"
    import glob
    assert not glob.glob(str(Path(v2.OBJ_BASE) / (v2.OBJ_DIR_PREFIX + "*")))


@pytest.mark.parametrize("plant", ["fetch_fail_before_gate", "reject_push_before_gate"])
def test_R25_1b_R26_1_failed_record_push_after_clean_phase_b_exits_with_type_only_and_leaves_nothing(tmp_path, plant):
    S = _e2e_setup(tmp_path, None, 1.0, 20)
    r = _py([], {"argv": ["--stage", "pre1998"], "ctx": S["ctx"], "plant": plant, "origin": str(S["origin"])}, tmp_path)
    assert r.returncode == 5, (r.returncode, r.stderr[-500:])
    err = r.stderr.strip().splitlines()
    assert len(err) == 1 and ("SealedRefusal" in err[0] or "LedgerPushFailed" in err[0]) and "push" in err[0]
    _assert_no_leak(S["work"], r.stdout, r.stderr)
    gone = S["origin"].with_name(S["origin"].name + ".gone")
    if gone.exists():
        gone.rename(S["origin"])
    led = _gled(S["work"], S["origin"]); led.fetch()
    assert [e["kind"] for e in led.entries()] == ["START", "PHASE_A_CLEAN"]


def test_R26_1_in_process_failed_push_leaves_no_gate_blob_and_no_object_dir(fx, tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    led = run.temporary_remote(tmp_path)
    origin = tmp_path / "origin.git"
    orig = run.pre1998_stats
    def planted(*a, **k):
        res = orig(*a, **k)
        h = origin / "hooks" / "pre-receive"; h.write_text("#!/bin/sh\nexit 1\n"); h.chmod(0o755)
        return res
    monkeypatch.setattr(run, "pre1998_stats", planted)
    with pytest.raises(SystemExit, match="push did not complete"):
        run.stage1_command(led, {}, "r1", "E1", fx / IND, fx / FAC, {"a": "1"}, B_=20, out=lambda x: None, selection=ORIG_SELECTION)
    _assert_no_leak(tmp_path / "work", "", "")


def test_R26_1_leftover_object_dirs_removed_unread(tmp_path):
    import tempfile
    d = Path(tempfile.mkdtemp(prefix=v2.OBJ_DIR_PREFIX, dir=v2.OBJ_BASE)); (d / "x").write_text("never read")
    assert v2.cleanup_leftover_object_dirs() >= 1 and not d.exists()


# ------------------------------------------------------------------ R25.1(c) default closed, and published
def _status_ledger(stage1_record=None, stage2=False):
    led = v2.MemoryLedger()
    s_ = led.append(_start(rel="r1")); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    if stage1_record is not None:
        led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": stage1_record,
                    "gate_open": v2.gate_decision(stage1_record)[0], "magnitudes_sha256": "d" * 64})
    if stage2:
        q = led.append(_start("stage2", "q1", "E1")); led.append({"kind": "PHASE_A_CLEAN", "start_index": q["index"]})
        led.append({"kind": "REPRODUCTION_OK", "start_index": q["index"]})
    return led.entries()


def test_R25_1c_phase_a_clean_without_record_is_closed_in_the_report(tmp_path):
    import scripts.run_rotation_core_v2 as run
    from scripts.rotation_core_v2_report import write_ledger_status_md
    st = run.ledger_status(_status_ledger())
    assert st["headline"] == "historical tier FAIL, " + run.R25_CLOSED
    st2 = run.ledger_status(_status_ledger(_all_plus(), stage2=True))
    assert st2["headline"] == "every hypothesis FAIL, " + run.R25_CLOSED
    with pytest.raises(v2.SealedRefusal):                           # stage 2 can never start on a clean-no-record
        v2.start_allowed(_status_ledger(), _start("stage2", "q1", "E1"), {})
    write_ledger_status_md(st, tmp_path / "s.md")
    assert run.R25_CLOSED in (tmp_path / "s.md").read_text()
    # the identical rerun is the only thing that changes it
    ents = _status_ledger()
    led = v2.MemoryLedger(ents); s_ = led.append(_start(rel="r1"))
    led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _all_plus(), "gate_open": True,
                "magnitudes_sha256": "d" * 64})
    assert run.ledger_status(led.entries())["headline"] == "gate OPEN"


def test_R25_1c_ledger_report_through_main_on_a_ledger_ending_in_phase_a_clean(tmp_path):
    S = _e2e_setup(tmp_path, None, 1.0, 20)
    led = _gled(S["work"], S["origin"]); led.fetch()
    rsha = v2.sha256_file(S["work"] / "r1.json")
    s_ = led.append(dict(_start(rel=rsha))); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    r = _py([], {"argv": ["--ledger-report"], "ctx": S["ctx"]}, tmp_path)
    assert r.returncode == 0, r.stderr[-500:]
    assert "R25.1" in r.stdout
    st = json.loads((tmp_path / "status.json").read_text())
    assert st["headline"].startswith("historical tier FAIL") and "R25.1" in (tmp_path / "status.md").read_text()


# ------------------------------------------------------------------ R25.2 Phase A pinned by syntax-tree hash
PHASE_A_AST_SHA256 = {
 "phase_a_window": "14469b40ce70b96fc0bf742a6aa83dcdc3bda8bf04ad847810222f20e55c3139",
 "phase_a_strict": "9bb8090404b6377d9b2745f7f8960a2b2412b78734e364168fb3864f493567b7",
 "phase_a": "886092b6ceae491b20d87d7e9a4ee0805d04a74a64f0f8f5d0310823e40a576e",
 "states_identical_across_costs": "0825b22238947827140f0ddc3f252e8e6b54b005d8d11b4445d5f7cfe414686e"
}


def test_R25_2_phase_a_syntax_tree_hashes_are_pinned_and_recorded():
    import scripts.run_rotation_core_v2 as run
    assert run.phase_a_ast_digest() == PHASE_A_AST_SHA256
    assert v2.versions()["phase_a_ast_sha256"] == PHASE_A_AST_SHA256
    led = v2.MemoryLedger(); e = led.append(_start())
    assert e["phase_a_ast_sha256"] == PHASE_A_AST_SHA256


@pytest.mark.parametrize("src", [
    'def f(bb, LR, m):\n    rb = LR["OFF"].to_numpy()[m]\n    rs = bb.returns.to_numpy()[m]\n'
    '    return np.count_nonzero(~(rs <= rb + TOL))',
    "def f(r_all, m):\n    W_all = r_all\n    return np.count_nonzero(W_all[m] > TOL)"])
def test_R25_2_reader_rebinding_cases_fail_the_guard(src):
    assert any(v.startswith("assign") for v in phase_a_violations(src))


# ------------------------------------------------------------------ R25.3 git and gh by absolute path
def test_R25_3_tools_resolved_once_by_absolute_path_and_recorded(tmp_path, monkeypatch):
    assert v2.tool("git") == "/usr/bin/git" and v2.tool("gh") == "/usr/bin/gh"
    t = v2.versions()["tools"]
    assert t["git"]["path"] == "/usr/bin/git" and t["git"]["version"].startswith("git version")
    assert t["gh"]["path"] == "/usr/bin/gh" and t["gh"]["version"].startswith("gh version")
    d = tmp_path / "bin"; d.mkdir(); f = d / "faketool"; f.write_text("#!/bin/sh\n"); f.chmod(0o775)
    monkeypatch.setattr(v2, "TOOL_DIRS", (str(d),)); monkeypatch.setattr(v2, "_TOOLS", {})
    with pytest.raises(v2.SealedRefusal, match="writable"):
        v2.tool("faketool")
    with pytest.raises(v2.SealedRefusal, match="not found"):
        v2.tool("absent")


# ------------------------------------------------------------------ R25.5 an object body fails closed
def test_R25_5_object_body_is_a_plain_refusal():
    for bad in ({"message": "Not Found"}, ["Not Found"], [1, 2], None):
        with pytest.raises(v2.SealedRefusal, match="unexpected"):
            v2.check_activity(bad, "a" * 40, "a" * 40, lambda a, b: True, "refs/heads/b")
    with pytest.raises(v2.SealedRefusal, match="unexpected"):
        v2.host_checks("a" * 40, v2.ROOT, lambda path, paginate=False: {"message": "Not Found"} if "activity" in path
                       else [], v2.BRANCH, v2.ANCHOR_COMMIT)


# ------------------------------------------------------------------ R26.3 untracked / ignored code, re-checked at the record
def test_R26_3_untracked_py_at_the_repository_root_refuses_through_main():
    probe = v2.ROOT / f"zz_r26_probe_{os.getpid()}.py"
    probe.write_text("x = 1\n")
    try:
        r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"])
        assert r.returncode != 0 and probe.name in r.stderr and "untracked or ignored code file" in r.stderr
    finally:
        probe.unlink()


def test_R26_3_record_push_rechecks_the_worktree(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = v2.GitLedger(root=work, path=work / "ledger.json", branch="b", remote_url=str(origin), code_root=work)
    led.fetch(); s_ = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    (work / ".gitignore").write_text("*.so\n"); (work / "evil.so").write_text("x")
    with pytest.raises(v2.SealedRefusal, match="evil.so"):
        led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _closed(), "gate_open": False,
                    "magnitudes_sha256": "d" * 64})
    (work / "evil.so").unlink(); (work / "__pycache__").mkdir(); (work / "__pycache__" / "ok.pyc").write_text("x")
    led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _closed(), "gate_open": False,
                "magnitudes_sha256": "d" * 64})


# ------------------------------------------------------------------ R26.4 git / gh redirection
def test_R26_4_inherited_variables_refused(monkeypatch):
    v2.check_env_vars()
    for k in ("GIT_EDITOR", "GIT_SSH_COMMAND", "GH_TOKEN", "GH_HOST", "https_proxy", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy"):
        monkeypatch.setenv(k, "x")
        with pytest.raises(v2.SealedRefusal, match=k):
            v2.check_env_vars()
        monkeypatch.delenv(k)


def test_R26_4_git_config_redirections_refused(tmp_path):
    origin, work, g = _git_env(tmp_path)
    v2.check_remote_identity(work, str(origin))
    for key, val in (("http.proxy", "http://p:1"), ("https.proxy", "http://p:1"), ("core.gitProxy", "x"),
                     ("core.sshCommand", "ssh -v"), ("http.sslVerify", "false"),
                     ("http.https://github.com.sslVerify", "false"), ("http.https://github.com.proxy", "http://p")):
        g("config", key, val, cwd=work)
        with pytest.raises(v2.SealedRefusal):
            v2.check_remote_identity(work, str(origin))
        g("config", "--unset", key, cwd=work)
    g("config", "http.sslVerify", "true", cwd=work)
    v2.check_remote_identity(work, str(origin))


def test_R26_4_gh_called_with_hostname(monkeypatch):
    seen = {}
    class R:
        returncode, stdout = 0, b"[]"
    def fake(cmd, **k):
        seen["cmd"] = cmd; return R()
    monkeypatch.setattr(v2.subprocess, "run", fake)
    v2.gh_api("/x")
    assert seen["cmd"][:4] == ["/usr/bin/gh", "api", "--hostname", "github.com"]


# ------------------------------------------------------------------ R26.5 witness checked
def test_R26_5_witness_block_is_checked_against_the_ledger_and_the_release_history(tmp_path):
    import scripts.run_rotation_core_v2 as run
    origin, work, g = _git_env(tmp_path)
    r1 = _commit_push(g, work, "r1.json", {"windows_released": [v2.W_PRE]})
    led = _gled(work, origin); led.fetch()
    rsha = v2.sha256_file(work / "r1.json")
    s_ = led.append(_start(rel=rsha)); start_commit = led.last_commit
    led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _all_plus(), "gate_open": True,
                "magnitudes_sha256": "d" * 64, "utc": "2026-11-11T17:00Z"})
    gate_commit = led.last_commit
    ctx = _tctx(tmp_path, root=work, branch="b", release1=work / "r1.json")
    good = {"branch": "b", "release_commit": r1, "start_commit": start_commit, "gate_commit": gate_commit,
            "witness_utc": "t"}
    r2 = {"gate_commit": gate_commit, "_gate_latest": led.entries()[-1], "witnessed": good,
          "witness_confirmation_utc": "2026-11-11T17:05Z"}
    run.check_witness(r2, led, ctx)
    for conf in (None, "", "2026-11-11T16:59Z", "2026-11-11T17:00Z", "not a time", "2026-11-11T17:05",
                 "2099-01-01T00:00Z", 12345):                                             # R27.5, R29.6
        with pytest.raises(v2.SealedRefusal, match="witness_confirmation_utc"):
            run.check_witness(dict(r2, witness_confirmation_utc=conf), led, ctx)
    for k, bad in (("branch", "other"), ("release_commit", start_commit), ("start_commit", gate_commit),
                   ("gate_commit", start_commit), ("witness_utc", "")):
        with pytest.raises(v2.SealedRefusal):
            run.check_witness(dict(r2, witnessed=dict(good, **{k: bad})), led, ctx)
    with pytest.raises(v2.SealedRefusal):
        run.check_witness({k: v for k, v in r2.items() if k != "witnessed"}, led, ctx)


# ------------------------------------------------------------------ R26.6 activity ancestry, raw-line loaders
def test_R26_6_activity_push_must_be_a_fast_forward_in_local_history(tmp_path):
    origin, work, g = _git_env(tmp_path)
    c0 = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    (work / "a").write_text("1"); g("add", "a", cwd=work); g("commit", "-q", "-m", "a", cwd=work)
    c1 = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    g("checkout", "-q", "--orphan", "z", cwd=work); (work / "z").write_text("z"); g("add", "z", cwd=work)
    g("commit", "-q", "-m", "z", cwd=work)
    cz = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    isanc = lambda a, b: v2._git("merge-base", "--is-ancestor", a, b, check=False, root=work).returncode == 0
    ok = [{"id": 1, "activity_type": "branch_creation", "before": v2.ZERO_SHA, "after": c0, "ref": "refs/heads/b",
           "timestamp": "t1"},
          {"id": 2, "activity_type": "push", "before": c0, "after": c1, "ref": "refs/heads/b", "timestamp": "t2"}]
    v2.check_activity(ok, c1, c0, isanc, "refs/heads/b")
    bad = ok + [{"id": 3, "activity_type": "push", "before": c1, "after": cz, "ref": "refs/heads/b", "timestamp": "t3"}]
    with pytest.raises(v2.SealedRefusal, match="fast-forward"):
        v2.check_activity(bad, cz, c0, isanc, "refs/heads/b")


def test_R26_6_market_loader_drops_lines_after_the_end_before_any_parse(tmp_path):
    ind, fac = fixture_texts(start="1996-01-02", end="1997-12-31", n_ind=6)
    p = tmp_path / "f.csv"; p.write_text(fac + "19980102,NOT,A,NUMBER,AT_ALL\n")
    mkt, rf = v2.load_french_market(p, "1997-12-31")
    assert mkt.index.max() <= pd.Timestamp("1997-12-31") and len(mkt) > 400


def _tctx(tmp, **over):
    """A wholly temporary context: every field explicit, every path under tmp."""
    import scripts.run_rotation_core_v2 as run
    t = Path(tmp)
    kw = {k: t / k for k in run.CTX_PATH_FIELDS}
    kw.update(stage1_inputs={"industries_le2019": t / "i.csv", "factors": t / "f.csv"},
              stage2_inputs={"industries_full": t / "full.csv"}, sealed_paths=[], branch="b",
              remote_url=str(t / "origin.git"), sealed_recorded={}, host_api=lambda *a, **k: [], anchor="a" * 40,
              engine_check=lambda c: None, B=20)
    kw.update(over)
    return run.Ctx(**kw)


def _rctx(**over):
    """A wholly REAL supplied context: the builder's fields (paths only; nothing is opened)."""
    import scripts.run_rotation_core_v2 as run
    real = run._real_ctx()
    kw = {k: getattr(real, k) for k in run.CTX_FIELDS}
    kw.update(over)
    return run.Ctx(**kw)


# ------------------------------------------------------------------ R27.1 a supplied context touching anything real
def test_R27_1_is_real_predicate_on_real_values(tmp_path):
    import scripts.run_rotation_core_v2 as run
    assert run.is_real(_rctx()) is True
    assert run.is_real(_tctx(tmp_path)) is False
    for over in ({"root": v2.ROOT}, {"ledger_path": v2.LEDGER}, {"release1": v2.RELEASE}, {"release2": v2.RELEASE2},
                 {"remote_url": v2.REMOTE_URL}, {"release1": v2.ROOT / "research"}):
        assert run.is_real(_tctx(tmp_path, **over)) is True, over
    link = tmp_path / "link"; link.symlink_to(v2.ROOT)                       # real path, not the link path
    assert run.is_real(_tctx(tmp_path, root=link)) is True
    assert run.is_real(_tctx(tmp_path, branch=v2.BRANCH)) is False           # branch alone, on a local remote


def test_R27_1_reader_config_real_root_with_stubs_refused(tmp_path):
    """The gate main() applies after parse_args (in-process the pytest interpreter lacks -E, so the gate itself is
    called; the subprocess tests below go through main())."""
    import scripts.run_rotation_core_v2 as run
    stub = lambda path, paginate=False: []
    for stage in ("pre1998", "confirm"):
        for kw in ({"host_api": stub}, {"engine_check": lambda c: None}, {"host_api": stub, "engine_check": lambda c: None}):
            ctx = _rctx(**kw)
            with pytest.raises(v2.SealedRefusal, match="real host and engine checks"):
                run.sealed_stage_gate(stage, ctx, ctx)
        key = "release1" if stage == "pre1998" else "release2"
        ctx = _rctx(**{key: v2.ROOT / "research/rotation_core/__absent__.json"})
        run.sealed_stage_gate(stage, ctx, ctx)
        assert run.check_supplied_ctx(ctx, stage) == "supplied_real"


def test_R27_1_real_context_with_a_file_at_the_release_path_refuses_before_reading(monkeypatch):
    import scripts.run_rotation_core_v2 as run
    read = []
    monkeypatch.setattr(v2, "_load_release", lambda *a, **k: read.append(a) or {})
    existing = v2.HEADER_V2                                    # an existing file inside the real repository, not written
    for stage, key in (("pre1998", "release1"), ("confirm", "release2")):
        ctx = _rctx(**{key: existing})
        with pytest.raises(v2.SealedRefusal, match="refused before reading it"):
            run.sealed_stage_gate(stage, ctx, ctx)
    assert read == []


def test_R27_1_reader_exact_config_through_the_driver_is_refused_before_import(tmp_path):
    cfg = {"argv": ["--stage", "pre1998"], "ctx": {"root": str(v2.ROOT), "branch": v2.BRANCH,
                                                   "remote_url": v2.REMOTE_URL}, "host_stub": True}
    cfg["ctx"].update({"host_stub": True, "engine_stub": True})
    r = _py([], cfg, tmp_path)
    assert r.returncode != 0 and "R28.5" in r.stderr and "WITNESS" not in r.stdout


def test_R27_1_R28_2_test_context_must_be_wholly_under_tmp_with_a_local_remote_there(tmp_path):
    import scripts.run_rotation_core_v2 as run
    other = Path("/srv/rc_not_tmp")                                          # neither the repository nor /tmp
    for over in ({"root": other}, {"final_j": other / "x"}, {"stage1_inputs": {"i": other / "x"}},
                 {"sealed_paths": [other / "x"]}):
        with pytest.raises(v2.SealedRefusal, match="system temporary"):
            run.check_supplied_ctx(_tctx(tmp_path, **over), "pre1998")
    for url in ("https://example.com/x.git", "git@example.com:x.git", "relative/o.git", str(other / "o.git")):
        with pytest.raises(v2.SealedRefusal, match="local filesystem path under"):
            run.check_supplied_ctx(_tctx(tmp_path, remote_url=url), "pre1998")
    assert run.check_supplied_ctx(_tctx(tmp_path), "pre1998") == "test"


@pytest.mark.parametrize("args,env_extra,flags,needle", [
    (["-c", "import sys; sys.path.insert(0, '.'); import scripts.run_rotation_core_v2 as r; "
            "r.main(['--stage', 'pre1998'])"], {}, RUN_FLAGS, "runs only as"),
    (["scripts/run_rotation_core_v2.py", "--stage", "pre1998"], {"PYTEST_CURRENT_TEST": "x"}, RUN_FLAGS, "pytest"),
    (["scripts/run_rotation_core_v2.py", "--stage=pre1998"], {}, RUN_FLAGS + ("-O",), "-O")])
def test_R27_1_real_run_requires_the_script_no_pytest_no_optimize(args, env_extra, flags, needle):
    r = _py(args, flags=flags, env=_clean_env(**env_extra))
    assert r.returncode != 0 and needle in r.stderr, r.stderr[-400:]
    assert "WITNESS" not in r.stdout


def test_R27_1b_real_validation_refuses_stub_or_missing_host_records():
    good = {"ruleset_id": v2.RULESET_ID, "ruleset_updated_at": "2026-11-11T07:21:36.088-08:00"}
    e = lambda h: [dict(_start(), index=0, **({"host": h} if h is not None else {}))]
    v2.check_real_host_records(e(good))
    for h in (None, dict(good, stub=True), dict(good, ruleset_id=1), dict(good, ruleset_updated_at="stub"), "x"):
        with pytest.raises(v2.SealedRefusal):
            v2.check_real_host_records(e(h))
    led = v2.MemoryLedger(); led.append(_start())
    v2.validate_ledger(led.entries(), [], {"r1": {}})                          # test ledgers: not REAL
    with pytest.raises(v2.SealedRefusal, match="host record"):
        v2.validate_ledger(led.entries(), [], {"r1": {}}, real=True)


# ------------------------------------------------------------------ R27.2 children's environment and config
def test_R27_2_git_and_gh_children_get_a_constructed_environment(monkeypatch):
    seen = []
    class R:
        returncode, stdout, stderr = 0, b"[]", b""
    def spy(cmd, **k):
        seen.append((cmd, k.get("env"))); return R()
    monkeypatch.setenv("SECRET_THING", "x")
    monkeypatch.setattr(v2.subprocess, "run", spy)
    v2._git("status"); v2.gh_api("/x"); v2._git("hash-object", env={"GIT_OBJECT_DIRECTORY": "/dev/shm/x"})
    for cmd, env in seen:
        assert set(env) <= {"PATH", "HOME", "LANG", "LC_ALL", "GIT_OBJECT_DIRECTORY", "GIT_NO_LAZY_FETCH"}
        assert env["PATH"] == "/usr/bin:/bin" and env["GIT_NO_LAZY_FETCH"] == "1"
        assert env["LANG"] == env["LC_ALL"] == "C" and "SECRET_THING" not in env
    assert seen[0][0][1:7] == v2.GIT_FIXED and seen[1][0][:4] == ["/usr/bin/gh", "api", "--hostname", "github.com"]


def test_R27_2_hash_object_no_filters_push_to_url_and_private_store_in_dev_shm(tmp_path, monkeypatch):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    calls, orig = [], v2._git
    def spy(*a, **k):
        calls.append((a, k.get("env"))); return orig(*a, **k)
    monkeypatch.setattr(v2, "_git", spy)
    led.append(_start())
    h = next(a for a, e in calls if a[0] == "hash-object")
    assert "--no-filters" in h
    push = next((a, e) for a, e in calls if a[0] == "push")
    assert push[0][2] == str(origin) and push[1]["GIT_OBJECT_DIRECTORY"].startswith(v2.OBJ_BASE + "/")


def test_R27_2_repository_config_allowlist(tmp_path):
    origin, work, g = _git_env(tmp_path)
    v2.check_repo_config(work, str(origin), test_repo=True)
    for key, val in (("core.editor", "vi"), ("core.pager", "less"), ("alias.x", "!sh"), ("diff.external", "x"),
                     ("filter.f.clean", "x"), ("remote.origin.pushurl", "x"), ("include.path", "/x")):
        g("config", key, val, cwd=work)
        with pytest.raises(v2.SealedRefusal, match="repository-scope"):
            v2.check_repo_config(work, str(origin), test_repo=True)
        g("config", "--unset", key, cwd=work)
    v2.check_repo_config(work, str(origin), test_repo=True)
    v2.check_repo_config(v2.ROOT, v2.REMOTE_URL)                                       # this repository today


def test_R27_2_runtime_overrides_refused(monkeypatch):
    v2.check_runtime_env()
    for k in v2.RUNTIME_REFUSED:
        monkeypatch.setenv(k, "/x")
        with pytest.raises(v2.SealedRefusal, match=k):
            v2.check_runtime_env()
        monkeypatch.delenv(k)


def test_R27_2_gh_unix_socket_refused(monkeypatch):
    class R:
        def __init__(self, out): self.returncode, self.stdout = 0, out
    monkeypatch.setattr(v2.subprocess, "run", lambda *a, **k: R(b""))
    v2.check_gh_socket()
    monkeypatch.setattr(v2.subprocess, "run", lambda *a, **k: R(b"/run/x.sock\n"))
    with pytest.raises(v2.SealedRefusal, match="http_unix_socket"):
        v2.check_gh_socket()


# ------------------------------------------------------------------ R27.3 one invocation at a time
def test_R27_3_second_invocation_refuses_without_touching_anything():
    with v2.RunLock():
        with pytest.raises(v2.SealedRefusal, match="another invocation"):
            with v2.RunLock():
                pass
        r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"])
        assert r.returncode != 0 and "another invocation" in r.stderr and "FIXTURE" not in r.stdout
        r = _py(["scripts/run_rotation_core_v2.py", "--preflight"])
        assert "PREFLIGHT REFUSED" in r.stdout and "another invocation" in r.stdout
    with v2.RunLock():
        pass


# ------------------------------------------------------------------ R27.4 notes
def test_R27_4_record_push_checks_blob_equality_at_the_engine_commit(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = v2.GitLedger(root=work, path=work / "ledger.json", branch="b", remote_url=str(origin), code_root=work)
    led.fetch(); s_ = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    led.engine_commit = "48c4d9dd4bc50f43b61051972710ab0141f7ce97"          # an old engine: the loaded code differs
    with pytest.raises(v2.SealedRefusal, match="differs from the engine commit"):
        led.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _closed(), "gate_open": False,
                    "magnitudes_sha256": "d" * 64})


@pytest.mark.parametrize("name", ["x.pyd", "x.dylib", "x.zip", "x.egg-link", "a b.py", "sub/dir/n.so"])
def test_R27_4_worktree_check_more_suffixes_and_z_parsing(tmp_path, name):
    origin, work, g = _git_env(tmp_path)
    f = work / name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text("x")
    with pytest.raises(v2.SealedRefusal, match="untracked or ignored code file"):
        v2.check_worktree_code(work)


def test_R27_4_stage1_also_binds_versions(fx):
    ins = {"industries": fx / IND}
    good = {"inputs_sha256": {k: v2.sha256_file(p) for k, p in ins.items()}, "versions": v2.versions()}
    for k in ("tools", "pth_sha256", "sitecustomize_sha256", "phase_a_ast_sha256"):
        with pytest.raises(v2.SealedRefusal, match=k):
            v2.check_manifest(dict(good, versions=dict(good["versions"], **{k: "x"})), ins)


def test_R27_4_preflight_reads_no_release_writes_nothing_and_refuses_on_an_inherited_variable():
    before = subprocess.run([v2.tool("git"), "status", "--porcelain", "--ignored"], cwd=v2.ROOT,
                            capture_output=True).stdout
    r = _py(["scripts/run_rotation_core_v2.py", "--preflight"])
    lines = r.stdout.strip().splitlines()
    # the expected line is derived from the stated state of this checkout, then asserted exactly
    dirty = subprocess.run([v2.tool("git"), "status", "--porcelain", "--", *v2.PINNED_PATHS], cwd=v2.ROOT,
                           capture_output=True, env=v2.child_env()).stdout.strip() != b""
    head = subprocess.run([v2.tool("git"), "rev-parse", "HEAD"], cwd=v2.ROOT, capture_output=True,
                          env=v2.child_env()).stdout.decode().strip()
    remote = subprocess.run([v2.tool("git"), "ls-remote", v2.REMOTE_URL, f"refs/heads/{v2.BRANCH}"], cwd=v2.ROOT,
                            capture_output=True, env=v2.child_env()).stdout.decode().split()[0]
    assert len(lines) == 1
    if not dirty and head == remote:
        assert lines[0].startswith(f"PREFLIGHT PASS head {head} ")
    elif head != remote:
        assert lines[0] == ("PREFLIGHT REFUSED: refused: the local branch is not the fetched remote head (unpushed "
                            "or stale commits)")
    else:
        assert lines[0] == "PREFLIGHT REFUSED: refused: modified or untracked files under the pinned paths"
    r2 = _py(["scripts/run_rotation_core_v2.py", "--preflight"], env=_clean_env(GIT_EDITOR="vi"))
    assert r2.stdout.strip() == "PREFLIGHT REFUSED: refused: the environment variable GIT_EDITOR is set"
    after = subprocess.run([v2.tool("git"), "status", "--porcelain", "--ignored"], cwd=v2.ROOT,
                           capture_output=True).stdout
    assert before == after


# ------------------------------------------------------------------ R27.6 no core, R27.7 more refused git config
def test_R27_6_no_core_in_force_inside_a_python_E_subprocess(tmp_path):
    code = ("import sys, resource, ctypes; sys.path.insert(0, '.'); from engine import rotation_core_v2 as v2; "
            "v2.no_core(); print(resource.getrlimit(resource.RLIMIT_CORE), ctypes.CDLL(None).prctl(3, 0, 0, 0, 0)); "
            "import subprocess; print(subprocess.run(['/bin/sh', '-c', 'ulimit -c'], capture_output=True, "
            "text=True).stdout.strip())")
    r = _py(["-c", code])
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\n")[:2] == ["(0, 0) 0", "0"]
    r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"])     # main() applies it first
    assert r.returncode == 0
    import scripts.run_rotation_core_v2 as run, inspect
    src = inspect.getsource(run._main_guarded)
    assert src.index("v2.no_core()") < src.index("pre_lock_checks(")
    main_src = inspect.getsource(run.main)                     # main only takes the root off the path first (R32.8)
    assert main_src.index("_root_off_path()") < main_src.index("_main_guarded(") and "no_core" not in main_src


def test_R27_6_no_core_refuses_if_the_call_fails(monkeypatch):
    import resource
    def bad(*a):
        raise ValueError("no")
    monkeypatch.setattr(resource, "setrlimit", bad)
    with pytest.raises(v2.SealedRefusal, match="core dumps"):
        v2.no_core()


def test_R27_7_more_redirecting_git_config_refused(tmp_path):
    origin, work, g = _git_env(tmp_path)
    v2.check_remote_identity(work, str(origin))
    for key, val in (("remote.origin.proxy", "http://p:1"), ("http.curloptResolve", "github.com:443:1.2.3.4"),
                     ("http.https://github.com.curloptResolve", "x"), ("http.sslCAInfo", "/x"),
                     ("http.sslCAPath", "/x"), ("http.https://github.com.sslCAInfo", "/x"),
                     ("http.https://github.com.sslCAPath", "/x"), ("http.sslBackend", "gnutls"),
                     ("http.extraHeader", "X: 1"), ("http.https://github.com.extraHeader", "X: 1"),
                     ("credential.helper", "store"), ("credential.https://github.com.helper", "!/tmp/evil"),
                     ("credential.https://github.com.username", "x")):
        g("config", "--add", key, val, cwd=work)
        with pytest.raises(v2.SealedRefusal):
            v2.check_remote_identity(work, str(origin))
        g("config", "--unset-all", key, cwd=work)
    g("config", "--add", "credential.https://github.com.helper", "", cwd=work)
    g("config", "--add", "credential.https://github.com.helper", "!/usr/bin/gh auth git-credential", cwd=work)
    v2.check_remote_identity(work, str(origin))
    v2.check_remote_identity(v2.ROOT, v2.REMOTE_URL)                                         # this host as configured today


# ------------------------------------------------------------------ R28 a supplied context is wholly real or wholly temporary
# The machine-readable twin of the ruling's field table: field -> (kind, purpose).
CTX_FIELD_TABLE = {
    "root": ("path", "repository checkout the ledger and releases live in"),
    "ledger_path": ("path", "run ledger file"),
    "release1": ("path", "stage-1 release file"),
    "release2": ("path", "stage-2 release file"),
    "selection": ("path", "committed selection result"),
    "ind_d": ("path", "through-2019 industry file"),
    "ind_full": ("path", "full (sealed) industry file"),
    "fact": ("path", "factor file"),
    "fund_dir": ("path", "fund parquet directory"),
    "final_j": ("path", "final results JSON (write)"),
    "final_m": ("path", "final results Markdown (write)"),
    "stage1_published": ("path", "closed-gate publication (write)"),
    "selection_rerun_j": ("path", "selection rerun JSON (write)"),
    "selection_rerun_m": ("path", "selection rerun Markdown (write)"),
    "ledger_status_j": ("path", "ledger status JSON (write)"),
    "ledger_status_m": ("path", "ledger status Markdown (write)"),
    "stage1_inputs": ("path_map", "stage-1 manifest inputs"),
    "stage2_inputs": ("path_map", "stage-2 manifest inputs"),
    "sealed_paths": ("path_list", "files unsealed by stage 2"),
    "branch": ("other", "ledger branch"),
    "remote_url": ("remote", "ledger remote"),
    "sealed_recorded": ("other", "recorded sealed hashes (None = the committed record)"),
    "host_api": ("hook", "host-record API (None = real gh)"),
    "anchor": ("other", "activity-log anchor commit"),
    "engine_check": ("hook", "engine-commit check"),
    "B": ("other", "bootstrap resamples")}


def test_R28_4_every_context_field_is_classified():
    import inspect, scripts.run_rotation_core_v2 as run
    params = inspect.signature(run.Ctx.__init__).parameters
    fields = {n for n, p in params.items() if p.kind is p.KEYWORD_ONLY}
    assert fields == set(CTX_FIELD_TABLE) == set(run.CTX_FIELDS)
    assert all(p.default is p.empty for n, p in params.items() if n in fields)          # no defaults
    kinds = lambda k: {f for f, (kk, _) in CTX_FIELD_TABLE.items() if kk == k}
    assert kinds("path") == set(run.CTX_PATH_FIELDS)
    assert kinds("path_map") == set(run.CTX_PATH_MAP_FIELDS) and kinds("path_list") == set(run.CTX_PATH_LIST_FIELDS)
    ruling = (v2.ROOT / "research/rotation_core/HOLDOUT_RELEASE_RULING_v2.md").read_text()
    assert all(f"| `{f}` |" in ruling for f in CTX_FIELD_TABLE)                         # the ruling's table


@pytest.mark.parametrize("field", sorted(CTX_FIELD_TABLE))
def test_R28_1_omitting_any_field_raises(tmp_path, field):
    import scripts.run_rotation_core_v2 as run
    full = _tctx(tmp_path)
    kw = {k: getattr(full, k) for k in run.CTX_FIELDS if k != field}
    with pytest.raises(TypeError):
        run.Ctx(**kw)


PATH_LIKE = sorted(f for f, (k, _) in CTX_FIELD_TABLE.items() if k in ("path", "path_map", "path_list", "remote"))


@pytest.mark.parametrize("how", ["direct", "symlink", "dotdot"])
@pytest.mark.parametrize("target", ["repo", "data"])
@pytest.mark.parametrize("field", PATH_LIKE)
def test_R28_4_pointing_any_path_field_at_real_makes_it_real(tmp_path, field, target, how):
    """Paths and predicates only: no real file is opened."""
    import scripts.run_rotation_core_v2 as run
    base = v2.ROOT if target == "repo" else v2.REAL_DATA_ROOT
    if how == "direct":
        p = base / "x"
    elif how == "symlink":
        link = tmp_path / "lnk"; link.symlink_to(base); p = link / "x"
    else:
        p = Path("/tmp") / os.path.relpath(base, "/tmp") / "x"                  # /tmp/../home/... by '..'
    val = {"path": p, "path_map": {"k": p}, "path_list": [p], "remote": str(p)}[CTX_FIELD_TABLE[field][0]]
    ctx = _tctx(tmp_path, **{field: val})
    assert run.is_real(ctx) is True
    with pytest.raises(v2.SealedRefusal):                                       # stubs + real -> refused
        run.check_supplied_ctx(ctx, "pre1998")


def test_R28_4_reader_b1_config_refused_by_the_driver_and_by_the_constructor(tmp_path):
    work = tmp_path / "work"; origin = tmp_path / "origin.git"
    ctx = {"root": str(work), "ledger_path": str(work / "ledger.json"), "release1": str(work / "r1.json"),
           "release2": str(work / "r2.json"), "selection": str(work / "sel.json"), "branch": "b",
           "remote_url": str(origin), "host_stub": True, "engine_stub": True}
    r = _py([], {"argv": ["--stage", "pre1998"], "ctx": ctx}, tmp_path)
    assert r.returncode != 0 and "must name every context key" in r.stderr and "WITNESS" not in r.stdout
    sys.path.insert(0, str(v2.ROOT / "tests"))
    import rotation_core_v2_driver as drv                               # the driver check bypassed in-process:
    with pytest.raises((TypeError, KeyError)):                          # the constructor refuses the omitted keys
        drv.build_ctx(ctx)
    import scripts.run_rotation_core_v2 as run
    with pytest.raises(TypeError):
        run.Ctx(root=work, ledger_path=work / "l", release1=work / "r1", release2=work / "r2", selection=work / "s",
                branch="b", remote_url=str(origin), host_api=None, engine_check=None)
    cfg2 = {"argv": ["--stage", "confirm"], "ctx": dict(_tctx_cfg(tmp_path), sealed_paths=[str(v2.ROOT / "x")])}
    r = _py([], cfg2, tmp_path)
    assert r.returncode != 0 and "only paths under" in r.stderr                  # a sealed path checked too


def _tctx_cfg(tmp):
    t = Path(tmp)
    import scripts.run_rotation_core_v2 as run
    c = {k: str(t / k) for k in run.CTX_PATH_FIELDS}
    c.update(stage1_inputs={"i": str(t / "i")}, stage2_inputs={"j": str(t / "j")}, sealed_paths=[], branch="b",
             remote_url=str(t / "o.git"), sealed_recorded={}, anchor="a" * 40, B=20, host_stub=True, engine_stub=True)
    return c


@pytest.mark.parametrize("key", ["root", "fact", "stage1_inputs", "sealed_paths", "B", "host_stub"])
def test_R28_5_driver_refuses_a_config_omitting_any_key_before_import(tmp_path, key):
    c = _tctx_cfg(tmp_path); c.pop(key)
    r = _py([], {"argv": ["--stage", "pre1998"], "ctx": c}, tmp_path)
    assert r.returncode != 0 and "must name every context key" in r.stderr


def test_R28_3_choke_point_refuses_real_paths_real_hashes_and_chmod_in_a_test_context(tmp_path):
    """No real file is opened: the real hashes come from the committed records."""
    import io as _io
    try:
        v2.set_io_mode("test")
        for p in (v2.ROOT / "x", v2.REAL_DATA_ROOT / "french" / "x", Path("/srv/rc_not_tmp/x")):
            with pytest.raises(v2.SealedRefusal, match="only under the system temporary"):
                v2.io_check(p, "read")
            with pytest.raises(v2.SealedRefusal):
                v2.write_text(p, "x")
        real = next(iter(v2.recorded_real_hashes()))
        f = tmp_path / "copy.csv"; f.write_text("not real")
        v2.io_check(f, "read")
        import unittest.mock as um
        with um.patch.object(v2, "sha256_file", lambda p: real):           # a byte-identical copy of a real input
            with pytest.raises(v2.SealedRefusal, match="equals a recorded real input"):
                v2.io_check(f, "read")
        with pytest.raises(v2.SealedRefusal, match="unsealed only by the real run"):
            v2.io_check(tmp_path / "sealed_post2019" / "x.csv", "chmod")
        with pytest.raises(v2.SealedRefusal, match="real run"):
            with v2.stage2_opened([tmp_path / "x.csv"], recorded={}):
                pass
        with pytest.raises(v2.SealedRefusal):                              # the loaders pass through it
            v2.load_french_market(v2.ROOT / "nope.csv", "1997-12-31")
        v2.io_check(_io.StringIO("synthetic"), "read")
        v2.set_io_mode("supplied_real")
        with pytest.raises(v2.SealedRefusal, match="reads and writes no data"):
            v2.io_check(tmp_path / "x", "read")
    finally:
        v2.set_io_mode(None)
    assert len(v2.recorded_real_hashes()) >= 15


def test_R28_6_pinned_blobs_flags_and_presence(tmp_path):
    origin, work, g = _git_env(tmp_path)
    (work / "engine").mkdir(); (work / "engine" / "a.py").write_text("x = 1\n"); (work / "data.txt").write_text("d\n")
    g("add", ".", cwd=work); g("commit", "-q", "-m", "c", cwd=work)
    head = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    assert v2.check_pinned_blobs(head, work, ["engine", "data.txt"]) == 2
    for flag in ("--assume-unchanged", "--skip-worktree"):
        g("update-index", flag, "data.txt", cwd=work)
        (work / "data.txt").write_text("edited\n")                     # hidden from status by the flag
        assert g("status", "--porcelain", cwd=work).stdout.strip() == b""
        with pytest.raises(v2.SealedRefusal, match="skip-worktree or assume-unchanged"):
            v2.check_pinned_blobs(head, work, ["engine", "data.txt"])
        g("update-index", flag.replace("--", "--no-"), "data.txt", cwd=work)
        with pytest.raises(v2.SealedRefusal, match="differs from the engine commit"):
            v2.check_pinned_blobs(head, work, ["engine", "data.txt"])
        (work / "data.txt").write_text("d\n")
    (work / "engine" / "a.py").unlink()
    with pytest.raises(v2.SealedRefusal, match="not present"):
        v2.check_pinned_blobs(head, work, ["engine", "data.txt"])


def test_R28_6_this_checkout_pinned_paths_are_unflagged_and_present():
    flags = v2._git("ls-files", "-v", "-z", "--", *v2.PINNED_PATHS).stdout.decode(errors="replace").split("\0")
    assert flags and not any(f and (f[0] == "S" or f[0].islower()) for f in flags)


# ------------------------------------------------------------------ R29.1 a failed read is never absence
def _partial_env(tmp_path):
    """A real blob-less partial clone of a temporary local remote (uploadpack.allowFilter)."""
    def g(*a, cwd):
        return subprocess.run([v2.tool("git"), *a], cwd=cwd, capture_output=True, check=True, env=v2.child_env(
            {"GIT_NO_LAZY_FETCH": None}))
    origin = tmp_path / "origin.git"; seed = tmp_path / "seed"; work = tmp_path / "work"
    g("init", "-q", "--bare", str(origin), cwd=tmp_path)
    g("config", "uploadpack.allowFilter", "true", cwd=origin)
    g("config", "uploadpack.allowAnySHA1InWant", "true", cwd=origin)
    g("clone", "-q", str(origin), str(seed), cwd=tmp_path)
    g("checkout", "-q", "-b", "b", cwd=seed); (seed / "README").write_text("x\n")
    g("add", "README", cwd=seed); g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "i", cwd=seed)
    g("push", "-q", "origin", "b", cwd=seed)
    g("clone", "-q", "--no-local", "--filter=blob:none", "-b", "b", str(origin), str(work), cwd=tmp_path)
    g("config", "user.email", "t@t", cwd=work); g("config", "user.name", "t", cwd=work)
    assert g("config", "remote.origin.promisor", cwd=work).stdout.strip() == b"true"
    return origin, work, g


def test_R29_1d_partial_clone_unreachable_promisor_between_appends_refuses_and_pushes_nothing(tmp_path, monkeypatch):
    origin, work, g = _partial_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    s_ = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    # a fresh blob-less partial clone (it holds no ledger blob)
    fresh = tmp_path / "fresh"
    g("clone", "-q", "--no-local", "--filter=blob:none", "-b", "b", str(origin), str(fresh), cwd=tmp_path)
    g("config", "user.email", "t@t", cwd=fresh); g("config", "user.name", "t", cwd=fresh)
    remote_before = v2._git("ls-remote", str(origin), "refs/heads/b", root=work).stdout
    real_fetch = v2.fetch_remote
    gone = origin.with_name("origin.gone")
    def fetch_then_drop(*a, **k):                    # the promisor becomes unreachable right after the fetch
        sha = real_fetch(*a, **k)
        if origin.exists():
            origin.rename(gone)
        return sha
    monkeypatch.setattr(v2, "fetch_remote", fetch_then_drop)
    led2 = _gled(fresh, origin)
    with pytest.raises(v2.SealedRefusal, match="could not be brought into the object store"):
        led2.append({"kind": "GATE", "start_index": s_["index"], "gate_signs": _closed(), "gate_open": False,
                     "magnitudes_sha256": "d" * 64})
    gone.rename(origin)
    monkeypatch.setattr(v2, "fetch_remote", real_fetch)
    assert v2._git("ls-remote", str(origin), "refs/heads/b", root=work).stdout == remote_before   # nothing pushed
    led3 = _gled(work, origin); led3.fetch()
    assert [e["kind"] for e in led3.entries()] == ["START", "PHASE_A_CLEAN"]                      # no 1-entry ledger


def test_R29_1a_missing_blob_is_a_refusal_not_absence(tmp_path):
    """R30.1: the blob is REALLY unreadable: a fresh blob-less clone that has not materialised it, with the promisor
    unreachable; lazy fetching off (GIT_NO_LAZY_FETCH=1, as in every runner child)."""
    origin, work, g = _partial_env(tmp_path)
    led = _gled(work, origin); led.fetch(); led.append(_start())
    fresh = tmp_path / "fresh"
    g("clone", "-q", "--no-local", "--no-checkout", "--filter=blob:none", "-b", "b", str(origin), str(fresh),
      cwd=tmp_path)                                                  # no checkout: no blob was fetched
    origin.rename(origin.with_name("origin.gone"))                   # the promisor is unreachable
    sha = v2._git("rev-parse", "HEAD", root=fresh).stdout.decode().strip()
    oid = v2._git("rev-parse", f"{sha}:ledger.json", root=fresh).stdout.decode().strip()
    has = subprocess.run([v2.tool("git"), "-C", str(fresh), "cat-file", "-e", oid], capture_output=True,
                         env=v2.child_env()).returncode == 0
    assert not has
    led2 = _gled(fresh, origin); led2.remote_sha = sha
    with pytest.raises(v2.SealedRefusal, match="not absence"):
        led2._entries_at(sha)
    with pytest.raises(v2.SealedRefusal, match="not absence"):
        v2.file_versions("ledger.json", sha, fresh)
    assert v2.blob_at(sha, "no/such/file", fresh) is None and v2.path_in_tree(sha, "ledger.json", fresh)
    with pytest.raises(v2.SealedRefusal):
        v2.blob_at("0" * 40, "ledger.json", fresh)                    # an unreadable tree is not absence


def test_R29_1b_the_ledger_never_shrinks(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    s_ = led.append(_start()); led.append({"kind": "PHASE_A_CLEAN", "start_index": s_["index"]})
    led.entries()
    (work / "ledger.json").write_bytes(v2.ledger_doc(led.entries()[:1]))           # a shrink, ordinary commit
    g("commit", "-q", "-am", "shrink", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    led.remote_sha = v2.fetch_remote(work, "b", str(origin))
    with pytest.raises(v2.SealedRefusal, match="does not extend the ledger read earlier"):
        led.entries()                                                               # within one invocation
    fresh = _gled(work, origin); fresh.fetch()
    with pytest.raises(v2.SealedRefusal, match="does not extend its predecessor"):
        fresh.version_entries()                                                     # across commits
    (work / "ledger.json").unlink()
    g("commit", "-q", "-am", "delete", cwd=work); g("push", "-q", "origin", "b", cwd=work)
    fresh2 = _gled(work, origin); fresh2.fetch()
    with pytest.raises(v2.SealedRefusal):
        fresh2.version_entries()


def test_R29_1c_materialise_counts_versions_and_disables_lazy_fetch_elsewhere(tmp_path):
    origin, work, g = _partial_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    for _ in range(3):
        led.append(_start(rel=f"r{_}") if _ == 0 else {"kind": "PHASE_A_CLEAN", "start_index": 0} if _ == 1 else
                   {"kind": "GATE", "start_index": 0, "gate_signs": _all_plus(), "gate_open": True,
                    "magnitudes_sha256": "d" * 64})
    assert v2.materialise(work, led.remote_sha, ["ledger.json"]) == 3            # every committed version
    assert v2.child_env()["GIT_NO_LAZY_FETCH"] == "1"


# ------------------------------------------------------------------ R29.2 reads are blobs; flags refuse
def test_R29_2_release_read_as_the_committed_blob_and_a_flag_refuses(tmp_path):
    origin, work, g = _git_env(tmp_path)
    _commit_push(g, work, "r1.json", {"windows_released": ["committed"]})
    sha = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    (work / "r1.json").write_text(json.dumps({"windows_released": ["EDITED"]}))
    g("update-index", "--skip-worktree", "r1.json", cwd=work)
    assert g("status", "--porcelain", cwd=work).stdout.strip() == b""             # the edit is hidden from status
    try:
        v2.set_read_head(work, sha)
        with pytest.raises(v2.SealedRefusal, match="skip-worktree or assume-unchanged"):
            v2._load_release(work / "r1.json", work)
        g("update-index", "--no-skip-worktree", "r1.json", cwd=work)
        doc = v2._load_release(work / "r1.json", work)                 # the blob, not the edit
        committed = v2._git("show", f"{sha}:r1.json", root=work).stdout
        assert doc == {"windows_released": ["committed"], "_blob_sha256": v2.sha256_bytes(committed)}
        g("update-index", "--assume-unchanged", "r1.json", cwd=work)
        with pytest.raises(v2.SealedRefusal):
            v2._load_release(work / "r1.json", work)
    finally:
        v2.set_read_head(None, None)


def test_R29_2_records_read_as_code_blobs():
    assert "49_Industry_Portfolios_Daily.csv" in v2.sealed_record()
    assert len(v2.recorded_real_hashes()) >= 15


# ------------------------------------------------------------------ R29.3 bytecode
def test_R29_3_crafted_pyc_is_ignored_under_the_runner_flags(tmp_path):
    """A temporary copy of the package (the real engine/__pycache__ is never touched)."""
    import shutil, py_compile, importlib.util
    pkg = tmp_path / "pkg"; (pkg / "probe").mkdir(parents=True)
    src = pkg / "probe" / "mod.py"; (pkg / "probe" / "__init__.py").write_text("")
    src.write_text("WHO = 'source!'\n")
    st = src.stat()
    evil = tmp_path / "evil.py"; evil.write_text("WHO = 'crafted'\n")         # same size as the source
    assert evil.stat().st_size == st.st_size
    cache = importlib.util.cache_from_source(str(src))
    py_compile.compile(str(evil), cfile=cache, dfile=str(src))
    data = bytearray(Path(cache).read_bytes())                               # header: source mtime and size
    import struct
    data[8:16] = struct.pack("<II", int(st.st_mtime) & 0xFFFFFFFF, st.st_size & 0xFFFFFFFF)
    Path(cache).write_bytes(bytes(data))
    code = "import sys; sys.path.append('.'); import probe.mod as m; print(m.WHO)"       # -P adds no '' entry
    plain = subprocess.run([PY, "-E", "-c", code], cwd=pkg, capture_output=True, text=True, env=_clean_env())
    assert plain.stdout.strip() == "crafted"                                 # the trap is real without the flags
    flagged = subprocess.run([PY, *RUN_FLAGS, "-c", code], cwd=pkg, capture_output=True, text=True, env=_clean_env())
    assert flagged.stdout.strip() == "source!"


@pytest.mark.parametrize("flags", [("-E", "-P"), ("-E", "-P", "-B"),
                                   ("-E", "-P", "-X", "pycache_prefix=/dev/shm/rotation_core_v2_pycache"),
                                   ("-E", "-P", "-B", "-X", "pycache_prefix=/dev/shm/other")])
def test_R29_3_runner_refuses_without_the_bytecode_flags(flags):
    import shutil
    try:
        r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"], flags=flags)
        assert r.returncode != 0 and "R29.3" in (r.stdout + r.stderr) and "FIXTURE" not in r.stdout
    finally:                                         # without -B, Python writes bytecode into the prefix: remove it
        shutil.rmtree(v2.PYCACHE_PREFIX, ignore_errors=True)


def test_R29_3_runner_refuses_a_non_empty_pycache_prefix():
    d = Path(v2.PYCACHE_PREFIX); d.mkdir(exist_ok=True); f = d / "planted"; f.write_text("x")
    try:
        r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"])
        assert r.returncode != 0 and "is not empty" in r.stderr
    finally:
        f.unlink()


def test_R29_3_bytecode_module_check(monkeypatch, tmp_path):
    import types, importlib.machinery as m
    mod = types.ModuleType("engine.fake_pyc"); mod.__file__ = str(v2.ROOT / "engine" / "fake.pyc")
    monkeypatch.setitem(sys.modules, "engine.fake_pyc", mod)
    with pytest.raises(v2.SealedRefusal, match="bytecode"):
        v2.check_no_bytecode_modules(v2.ROOT)


# ------------------------------------------------------------------ R29.4 fetch and config values
def test_R29_4_fetch_with_empty_refmap_refuses_a_rewrite_and_leaves_the_tracking_ref(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch(); led.append(_start())
    led.fetch()
    before = g("rev-parse", "refs/remotes/origin/b", cwd=work).stdout
    other = tmp_path / "other"; g("clone", "-q", "-b", "b", str(origin), str(other), cwd=tmp_path)
    g("reset", "-q", "--hard", "HEAD~1", cwd=other); (other / "z").write_text("z"); g("add", "z", cwd=other)
    g("commit", "-q", "-m", "rewrite", cwd=other); g("push", "-q", "-f", "origin", "b", cwd=other)
    g("config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*", cwd=work)
    with pytest.raises(v2.SealedRefusal, match="not a fast-forward"):
        v2.fetch_remote(work, "b", str(origin))
    assert g("rev-parse", "refs/remotes/origin/b", cwd=work).stdout == before


def test_R29_4_repository_config_values_pinned(tmp_path):
    origin, work, g = _git_env(tmp_path)
    v2.check_repo_config(work, str(origin), test_repo=True)
    for key, val in (("remote.origin.fetch", "+refs/heads/b:refs/remotes/origin/other"),
                     ("extensions.partialclone", "elsewhere"), ("remote.origin.promisor", "false"),
                     ("remote.origin.partialclonefilter", "tree:0")):
        old = g("config", "--get", key, cwd=work).stdout if key == "remote.origin.fetch" else None
        g("config", key, val, cwd=work)
        with pytest.raises(v2.SealedRefusal, match="repository-scope"):
            v2.check_repo_config(work, str(origin), test_repo=True)
        if old:
            g("config", key, old.decode().strip(), cwd=work)
        else:
            g("config", "--unset", key, cwd=work)
    g("config", "extensions.partialclone", "origin", cwd=work)
    v2.check_repo_config(work, str(origin), test_repo=True)
    v2.check_repo_config(v2.ROOT, v2.REMOTE_URL)


def test_R29_4_preflight_help_wording():
    r = _py(["scripts/run_rotation_core_v2.py", "--help"])
    assert "writes nothing in the working tree" in " ".join(r.stdout.split())


# ------------------------------------------------------------------ R29.5 real-path constants only in the builder
FORBIDDEN_RUN = {"IND_D", "IND_FULL", "FACT", "FR", "YAHOO", "FUND_DIR", "OUT_J", "OUT_M", "FINAL_J", "FINAL_M",
                 "STAGE1_PUBLISHED", "SELECTION_RERUN_J", "SELECTION_RERUN_M", "STAGE1_INPUTS"}
FORBIDDEN_V2 = {"RELEASE", "RELEASE2", "LEDGER", "SELECTION_RESULT", "REAL_DATA_ROOT"}
CONSTANT_ALLOWED = {("run", "_real_ctx"), ("run", "_touches_real"), ("v2", "io_check")}


def _alias_and_module_level_violations(path, mod) -> list:
    """R30.5 (a lint, not the boundary): import aliases of a forbidden name, getattr with a forbidden literal, and
    module-level statements that use a forbidden name other than to define a constant."""
    import ast
    names = FORBIDDEN_RUN | FORBIDDEN_V2
    tree = ast.parse((v2.ROOT / path).read_text())
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and any(a.name in names for a in n.names):
            bad.append(("import", [a.name for a in n.names if a.name in names]))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2 \
                and isinstance(n.args[1], ast.Constant) and n.args[1].value in names:
            bad.append(("getattr", n.args[1].value))
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        used = {x.id for x in ast.walk(st) if isinstance(x, ast.Name) and x.id in names} | \
               {x.attr for x in ast.walk(st) if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name)
                and x.value.id == "v2" and x.attr in FORBIDDEN_V2}
        targets = {t.id for t in getattr(st, "targets", []) if isinstance(t, ast.Name)}
        if used and not (isinstance(st, ast.Assign) and targets and targets <= (names | {"STAGE1_INPUTS"})
                         | {"IND_D", "IND_FULL", "FACT", "FUND_DIR"}):
            bad.append(("module-level", ast.unparse(st)[:60]))
    return bad


def test_R30_5_lint_aliases_getattr_and_module_level():
    for mod, path in (("run", "scripts/run_rotation_core_v2.py"), ("v2", "engine/rotation_core_v2.py"),
                      ("run", "scripts/rotation_core_v2_report.py"), ("run", "tests/rotation_core_v2_driver.py")):
        assert _alias_and_module_level_violations(path, mod) == [], path


def test_R30_5_the_lint_catches_its_cheap_alias_cases(tmp_path, monkeypatch):
    src = ("from scripts.run_rotation_core_v2 import IND_D as X\n"
           "y = getattr(v2, 'RELEASE')\n"
           "print(FACT)\n")
    f = v2.ROOT / "tests" / f"_tmp_lint_probe_{os.getpid()}.py"
    f.write_text(src)
    try:
        kinds = {k for k, _ in _alias_and_module_level_violations(str(f.relative_to(v2.ROOT)), "run")}
        assert kinds == {"import", "getattr", "module-level"}
    finally:
        f.unlink()


def test_R29_5_no_function_references_a_real_path_constant_outside_the_builder():
    import ast
    bad = []
    for mod, path in (("run", "scripts/run_rotation_core_v2.py"), ("v2", "engine/rotation_core_v2.py"),
                      ("run", "scripts/rotation_core_v2_report.py")):
        names = FORBIDDEN_RUN | (FORBIDDEN_V2 if mod == "v2" else set())
        tree = ast.parse((v2.ROOT / path).read_text())
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if (mod, getattr(fn, "name", "")) in CONSTANT_ALLOWED:
                continue
            for n in ast.walk(fn):
                if isinstance(n, ast.Name) and n.id in names:
                    bad.append((path, getattr(fn, "name", "lambda"), n.id))
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "v2" \
                        and n.attr in FORBIDDEN_V2:
                    bad.append((path, getattr(fn, "name", "lambda"), "v2." + n.attr))
    assert bad == []


# ------------------------------------------------------------------ R29.6
def test_R29_6_a_second_worktree_of_the_real_repository_is_real(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    origin, work, g = _git_env(tmp_path)
    wt = tmp_path / "wt"; g("worktree", "add", "-q", "-b", "w2", str(wt), cwd=work)
    monkeypatch.setattr(run, "ROOT", work)                       # the temporary repository stands in for the real one
    ctx = _tctx(tmp_path, root=wt)
    assert run._common_dir(wt) == run._common_dir(work) and run.is_real(ctx) is True
    other = tmp_path / "other"; g("init", "-q", str(other), cwd=tmp_path)
    assert run.is_real(_tctx(tmp_path, root=other)) is False


def test_R29_6_lock_file_that_cannot_be_opened_is_a_plain_refusal():
    with pytest.raises(v2.SealedRefusal, match="cannot be opened"):
        with v2.RunLock("/proc/no/such/dir/lock"):
            pass


def test_R29_6_abort_after_the_startup_settings_leaves_no_crash_file_and_no_core(tmp_path):
    before = set(os.listdir("/var/crash"))
    code = ("import sys, os; sys.path.insert(0, %r); from engine import rotation_core_v2 as v2; v2.no_core(); "
            "os.abort()" % str(v2.ROOT))
    r = subprocess.run([PY, *RUN_FLAGS, "-c", code], cwd=tmp_path, capture_output=True, env=_clean_env())
    assert r.returncode == -6
    import time; time.sleep(2)
    assert set(os.listdir("/var/crash")) == before and not any(p.name.startswith("core") for p in tmp_path.iterdir())


# ------------------------------------------------------------------ R30.2 every return code; is_ancestor three-valued
def test_R30_2_is_ancestor_is_three_valued(tmp_path):
    origin, work, g = _git_env(tmp_path)
    c0 = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    (work / "a").write_text("1"); g("add", "a", cwd=work); g("commit", "-q", "-m", "a", cwd=work)
    c1 = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    assert v2.is_ancestor(c0, c1, work) is True and v2.is_ancestor(c1, c0, work) is False
    with pytest.raises(v2.SealedRefusal, match="ancestry check failed"):
        v2.is_ancestor("f" * 40, c1, work)                           # an unknown object is an error, not "no"
    with pytest.raises(v2.SealedRefusal, match="ancestry check failed"):
        v2.check_release_pins({"branch_head_at_release": "f" * 40}, c1, work)


def test_R30_2_materialise_refuses_a_failed_batch_check(tmp_path, monkeypatch):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch(); led.append(_start())
    real = v2._git
    def failing(*a, **k):
        if a[:2] == ("cat-file", "--batch-check"):
            return subprocess.CompletedProcess(a, 128, b"", b"fatal")
        return real(*a, **k)
    monkeypatch.setattr(v2, "_git", failing)
    with pytest.raises(v2.SealedRefusal, match="checking the object store failed"):
        v2.materialise(work, led.remote_sha, ["ledger.json"])


def test_R30_2_other_failed_reads_refuse(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    origin, work, g = _git_env(tmp_path)
    real = v2._git
    def fail(cmd):
        def f(*a, **k):
            if a and a[0] == cmd:
                return subprocess.CompletedProcess(a, 128, b"", b"fatal")
            return real(*a, **k)
        return f
    with monkeypatch.context() as m:
        m.setattr(v2, "_git", fail("status"))
        with pytest.raises(v2.SealedRefusal, match="git status failed"):
            v2._committed_clean(work / "README", work)
    with monkeypatch.context() as m:
        m.setattr(v2, "_git", fail("remote"))
        with pytest.raises(v2.SealedRefusal, match="pinned repository"):
            v2.check_remote_identity(work, str(origin))
    with monkeypatch.context() as m:
        m.setattr(v2, "_git", fail("rev-parse"))
        with pytest.raises(v2.SealedRefusal, match="common directory"):
            run._common_dir(work)
    with monkeypatch.context() as m:
        m.setattr(v2, "_git", fail("log"))
        with pytest.raises(v2.SealedRefusal, match="history"):
            v2.on_remote(work / "README", "a" * 40, work)
    with monkeypatch.context() as m:
        def bad_version(cmd, **k):
            return subprocess.CompletedProcess(cmd, 1, b"", b"")
        m.setattr(v2, "_TOOL_VERSIONS", {})
        m.setattr(v2.subprocess, "run", bad_version)
        with pytest.raises(v2.SealedRefusal, match="--version failed"):
            v2.tool_versions()


# ------------------------------------------------------------------ R30.3 history walks agree; merges refused
def test_R30_3_a_merge_touching_the_ledger_is_refused_and_linear_history_passes(tmp_path):
    origin, work, g = _git_env(tmp_path)
    created = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    led = _gled(work, origin); led.fetch(); led.append(_start())
    head = v2._git("rev-parse", "HEAD", root=work).stdout.decode().strip()
    v2.check_no_merges(work, head, created, ["ledger.json"])
    g("checkout", "-q", "-b", "side", created, cwd=work)
    (work / "ledger.json").write_text("{}"); g("add", "ledger.json", cwd=work); g("commit", "-q", "-m", "side", cwd=work)
    g("checkout", "-q", "b", cwd=work)
    g("merge", "-q", "--no-ff", "-s", "ours", "-m", "merge", "side", cwd=work)
    m = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    with pytest.raises(v2.SealedRefusal, match="merge commit"):
        v2.check_no_merges(work, m, created, ["ledger.json"])
    v2.check_no_merges(work, m, created, ["unrelated.txt"])               # a merge not touching them passes


def test_R30_3_commit_adding_entry_walks_first_parents(tmp_path):
    origin, work, g = _git_env(tmp_path)
    led = _gled(work, origin); led.fetch()
    led.append(_start()); c0 = led.last_commit
    led.append({"kind": "PHASE_A_CLEAN", "start_index": 0}); c1 = led.last_commit
    assert led.commit_adding_entry(0) == c0 and led.commit_adding_entry(1) == c1 and led.commit_adding_entry(2) is None


# ------------------------------------------------------------------ R30.4 config values pinned
def test_R30_4_config_values_pinned(tmp_path):
    origin, work, g = _git_env(tmp_path)
    for key, val in (("core.bare", "true"), ("core.filemode", "false"), ("core.ignorecase", "true"),
                     ("core.sparsecheckout", "false"), ("user.name", "!sh -c x"), ("user.email", "-x"),
                     ("branch.b.remote", "a\nb"), ("branch.b.merge", "-refs")):
        old = v2._git("config", "--get", key, root=work, check=False)
        g("config", key, val, cwd=work)
        with pytest.raises(v2.SealedRefusal, match="not allowed with that value"):
            v2.check_repo_config(work, str(origin), test_repo=True)
        if old.returncode == 0:
            g("config", key, old.stdout.decode().strip(), cwd=work)
        else:
            g("config", "--unset", key, cwd=work)
    v2.check_repo_config(work, str(origin), test_repo=True)


# ------------------------------------------------------------------ R30.6 the hash alone decides
def test_R30_6_a_recorded_hash_at_a_different_path_is_still_refused(tmp_path, monkeypatch):
    f = tmp_path / "anything.csv"; f.write_text("bytes that are, for this test, a recorded real input\n")
    h = v2.sha256_file(f)
    real_code_text = v2.code_text
    def records(path):
        if Path(path).name == "REAL_INPUT_SHA256.txt":
            return f"# test record\n{h}  some/other/place/entirely.csv\n"
        return real_code_text(path)
    monkeypatch.setattr(v2, "code_text", records)
    try:
        v2.set_io_mode("test")
        with pytest.raises(v2.SealedRefusal, match="equals a recorded real input"):
            v2.io_check(f, "read")
    finally:
        v2.set_io_mode(None)


def test_R30_6_the_committed_records_carry_no_absolute_home_path():
    for rel in ("research/rotation_core/v2_power/REAL_INPUT_SHA256.txt",):
        assert "/home/" not in (v2.ROOT / rel).read_text()
    for ln in (v2.ROOT / "research/rotation_core/v2_power/REAL_INPUT_SHA256.txt").read_text().splitlines():
        if not ln.startswith("#"):
            assert not ln.split(None, 1)[1].startswith("/")


# ------------------------------------------------------------------ R31.1 one read of a release file
def _ledger_kinds(S):
    led = _gled(S["work"], S["origin"]); led.fetch()
    return [e["kind"] for e in led.entries()], led


@pytest.mark.parametrize("resave", ["trailing_newline", "crlf"])
def test_R31_1c_a_resaved_release_refuses_before_start(tmp_path, resave):
    S = _e2e_setup(tmp_path, None, 1.0, 20)
    p = S["work"] / "r1.json"
    b = p.read_bytes()
    p.write_bytes(b + b"\n" if resave == "trailing_newline" else b.replace(b"\n", b"\r\n"))
    flags = v2._git("ls-files", "-v", "r1.json", root=S["work"]).stdout.decode()
    assert flags.startswith("H ")                                       # no index flag hides it
    r = _py([], {"argv": ["--stage", "pre1998"], "ctx": S["ctx"]}, tmp_path)
    assert r.returncode != 0 and "working-tree copy of r1.json differs" in r.stderr
    assert "WITNESS" not in r.stdout
    assert _ledger_kinds(S)[0] == []                                    # nothing spent: no START


def test_R31_1ab_start_carries_the_committed_blob_hash_and_the_next_invocation_accepts_it(tmp_path):
    import hashlib
    S = _e2e_setup(tmp_path, None, 1.0, 20)
    p = S["work"] / "r1.json"
    committed = v2._git("show", "HEAD:r1.json", root=S["work"]).stdout
    p.write_bytes(committed + b"\n")                                    # the working tree differs by one byte
    r = _py([], {"argv": ["--stage", "pre1998"], "ctx": S["ctx"], "plant": "bypass_worktree_check"}, tmp_path)
    assert r.returncode == 0, r.stderr[-600:]
    kinds, led = _ledger_kinds(S)
    start = led.entries()[0]
    assert kinds[:3] == ["START", "PHASE_A_CLEAN", "GATE"]
    assert start["release_sha256"] == hashlib.sha256(committed).hexdigest() != hashlib.sha256(p.read_bytes()).hexdigest()
    r2 = _py([], {"argv": ["--ledger-report"], "ctx": S["ctx"], "plant": "bypass_worktree_check"}, tmp_path)
    assert r2.returncode == 0, r2.stderr[-600:]                          # verified_ledger accepts the record


def test_R31_1b_append_refuses_a_start_naming_an_uncommitted_release(tmp_path):
    origin, work, g = _git_env(tmp_path)
    _commit_push(g, work, "r1.json", {"windows_released": ["x"]})
    led = v2.GitLedger(root=work, path=work / "ledger.json", branch="b", remote_url=str(origin), code_root=v2.ROOT,
                       release_paths=[work / "r1.json"])
    led.fetch()
    before = v2._git("ls-remote", str(origin), "refs/heads/b", root=work).stdout
    with pytest.raises(v2.SealedRefusal, match="not a committed version"):
        led.append(_start(rel="a" * 64))
    assert v2._git("ls-remote", str(origin), "refs/heads/b", root=work).stdout == before        # nothing pushed
    good = v2.sha256_bytes(v2._git("show", "HEAD:r1.json", root=work).stdout)
    led.append(_start(rel=good))                                         # the committed blob's hash is accepted
    docs = v2.release_docs({"r1.json": v2.file_versions("r1.json", led.remote_sha, work)})
    assert good in docs                                                  # the same mapping validate_ledger uses


def test_R31_1a_no_working_tree_hash_of_a_release_or_selection_on_the_run_path():
    import ast
    src = (v2.ROOT / "scripts/run_rotation_core_v2.py").read_text()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sha256_file":
            arg = ast.unparse(n.args[0]) if n.args else ""
            assert not any(x in arg for x in ("release", "selection")), arg


# ------------------------------------------------------------------ R31.2 --manifest passes the choke point
def test_R31_2_manifest_checks_each_input_before_hashing_it(tmp_path):
    S = _e2e_setup(tmp_path, None, 1.0, 20)
    log = tmp_path / "io.log"
    r = _py([], {"argv": ["--manifest", "stage1"], "ctx": S["ctx"], "plant": "spy_io", "out": str(log)}, tmp_path)
    assert r.returncode == 0, r.stderr[-400:]
    lines = log.read_text().splitlines()
    for p in S["ctx"]["stage1_inputs"].values():
        i_io = lines.index(f"io read {p}")
        i_sha = lines.index(f"sha {p}")
        assert i_io < i_sha


# ------------------------------------------------------------------ R31.3 supplied-real: no release in the fetched tree
def test_R31_3_supplied_real_refuses_a_release_present_in_the_fetched_tree(tmp_path):
    import scripts.run_rotation_core_v2 as run
    origin, work, g = _git_env(tmp_path)
    _commit_push(g, work, "r1.json", {"windows_released": ["x"]})
    sha = g("rev-parse", "HEAD", cwd=work).stdout.decode().strip()
    (work / "r1.json").unlink()                                          # absent from the working tree only
    ctx = _tctx(tmp_path, root=work, release1=work / "r1.json")
    try:
        v2.set_io_mode("supplied_real")
        with pytest.raises(v2.SealedRefusal, match="exists in the tree at the fetched head"):
            run._check_supplied_real_release_absent(ctx, sha, "pre1998")
        run._check_supplied_real_release_absent(_tctx(tmp_path, root=work, release1=work / "absent.json"), sha,
                                                "pre1998")
    finally:
        v2.set_io_mode(None)


# ------------------------------------------------------------------ R31.4 remaining defaults removed
def test_R31_4_ledger_functions_have_no_real_defaults():
    import inspect
    for f, names in ((v2.fetch_remote, ("root", "branch", "url")),
                     (v2.host_checks, ("root", "api", "branch", "anchor")),
                     (v2.check_remote_identity, ("root", "url")), (v2.on_remote, ("root",)),
                     (v2.commit_on_remote, ("root",)), (v2.file_versions, ("root",)),
                     (v2.check_release_pins, ("root",)), (v2.check_repo_config, ("root", "remote_url")),
                     (v2.GitLedger.__init__, ("code_root",))):
        ps = inspect.signature(f).parameters
        assert all(ps[n].default is inspect.Parameter.empty for n in names), f.__name__
    with pytest.raises(v2.SealedRefusal, match="root is required"):
        v2.stage1_release(v2.ROOT / "x.json", selection=ORIG_SELECTION)


# ------------------------------------------------------------------ R31.5 rehearsal statistics on 1998+ sessions only
def test_R31_5_every_rehearsal_statistic_is_on_sessions_from_1998(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    starts = []
    def spy(fn, pos):
        def f(*a, **k):
            starts.append((fn.__name__, pd.Timestamp(a[pos])))
            return fn(*a, **k)
        return f
    monkeypatch.setattr(run, "window_block", spy(run.window_block, 3))
    monkeypatch.setattr(run, "paired_h2", spy(run.paired_h2, 1))
    monkeypatch.setattr(run, "window_series", spy(run.window_series, 2))
    monkeypatch.setattr(v2, "window_excess", spy(v2.window_excess, 3))
    real_standalone = run.standalone
    def standalone_spy(ser, ii, *a, **k):
        starts.append(("standalone", pd.DatetimeIndex(ii).min()))
        return real_standalone(ser, ii, *a, **k)
    monkeypatch.setattr(run, "standalone", standalone_spy)
    ind, fac = fixture_texts(start="1996-01-02", end="2019-12-31")
    e = run.rehearsal_command(io.StringIO(ind), io.StringIO(fac), out=lambda x: None, B_=20, engine_commit="E",
                              selection=ORIG_SELECTION)
    assert e["kind"] == "GATE" and {x[0] for x in starts} >= {"window_block", "paired_h2", "window_series",
                                                               "window_excess", "standalone"}
    assert all(t >= run.REH_START for _, t in starts), [x for x in starts if x[1] < run.REH_START][:3]
    assert min(a for a, _ in run.REH_SPEC["eras"].values()) == run.REH_START


def test_R31_5_printed_counts_including_warm_up_are_named():
    import scripts.run_rotation_core_v2 as run, inspect
    src = inspect.getsource(run.pre1998_stats)
    for k in WARMUP_INCLUSIVE_COUNTS:
        assert k in src
    ruling = (v2.ROOT / "research/rotation_core/HOLDOUT_RELEASE_RULING_v2.md").read_text()
    assert all(f"`{k}`" in ruling for k in WARMUP_INCLUSIVE_COUNTS)


WARMUP_INCLUSIVE_COUNTS = ("deferred_executions_total_incl_warmup", "days_holding_after_last_close_total",
                           "dropped_industry_days_unique_eligible_industries_only")


# ------------------------------------------------------------------ R31.6 nothing in the repository runs before the checks
SHADOW = "print('SHADOW-MODULE-RAN')\n"


def _plant(rel):
    p = v2.ROOT / rel
    assert not p.exists()
    p.write_text(SHADOW)
    return p


@pytest.mark.parametrize("rel,flags", [("scripts/argparse.py", RUN_FLAGS), ("scripts/argparse.py", ("-E", "-B")),
                                       ("json.py", RUN_FLAGS), ("engine/ctypes.py", RUN_FLAGS),
                                       ("engine/fcntl.py", RUN_FLAGS)])
def test_R31_6_a_planted_shadow_is_never_imported_and_the_run_refuses(rel, flags):
    p = _plant(rel)
    try:
        r = _py(["scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"], flags=flags)
        assert "SHADOW-MODULE-RAN" not in r.stdout + r.stderr                 # never imported
        assert r.returncode != 0 and "FIXTURE" not in r.stdout                # and the run refuses
        assert ("R31.6" in r.stderr) if "-P" not in flags else ("untracked or ignored code file" in r.stderr)
    finally:
        p.unlink()


def test_R31_6_without_P_the_runner_refuses_before_importing_anything_else():
    r = _py(["scripts/run_rotation_core_v2.py", "--preflight"], flags=("-E", "-B", "-X",
                                                                       "pycache_prefix=/dev/shm/rotation_core_v2_pycache"))
    assert r.returncode != 0 and "R31.6" in r.stderr and "PREFLIGHT" not in r.stdout


def test_R31_6_c_a_stdlib_name_loaded_from_the_repository_is_refused(monkeypatch):
    import types, scripts.run_rotation_core_v2 as run
    run.refuse_shadowed_modules(); v2.refuse_shadowed_modules(v2.ROOT)
    m = types.ModuleType("json"); m.__file__ = str(v2.ROOT / "json.py")
    monkeypatch.setitem(sys.modules, "json", m)
    with pytest.raises(SystemExit, match="R31.6"):
        run.refuse_shadowed_modules()
    with pytest.raises(v2.SealedRefusal, match="R31.6"):
        v2.refuse_shadowed_modules(v2.ROOT)


def test_R31_6_b_root_is_appended_and_repo_packages_still_resolve_from_the_root():
    code = ("import sys, os; sys.argv = ['x']; import runpy\n"
            "sys.path.append(%r)\n"
            "import scripts.run_rotation_core_v2 as run\n"
            "root = os.path.realpath(%r)\n"
            "assert sys.path.index(%r) > 0\n"
            "bad = [n for n, m in sys.modules.items() if n.split('.')[0] in ('engine', 'scripts') and "
            "getattr(m, '__file__', None) and not os.path.realpath(m.__file__).startswith(root + os.sep)]\n"
            "print('BAD', bad)\n"
            "import json, subprocess, ctypes; print('STDLIB', all(not os.path.realpath(x.__file__).startswith(root) "
            "for x in (json, subprocess, ctypes)))\n") % (str(v2.ROOT), str(v2.ROOT), str(v2.ROOT))
    r = _py(["-c", code])
    assert r.returncode == 0, r.stderr[-400:]
    assert "BAD []" in r.stdout and "STDLIB True" in r.stdout
    src = (v2.ROOT / "scripts/run_rotation_core_v2.py").read_text()
    assert "sys.path.insert(0" not in src and "run_rotation_core_v1" not in src.split('"""', 2)[2]


def test_R31_6_episode_tables_equal_v1s():
    import scripts.run_rotation_core_v2 as run, scripts.run_rotation_core_v1 as v1
    assert run.DPEAK == v1.DPEAK and run.LPEAK == v1.LPEAK


# ------------------------------------------------------------------ R32
R31_6E_FILES = ("scripts/run_rotation_core_v2.py", "engine/rotation_core_v2.py", "engine/rotation_core_evaluation.py",
                "engine/validation.py", "scripts/rotation_core_v2_report.py", "tests/rotation_core_v2_fixture.py")


def test_R32_1_no_file_on_the_run_path_inserts_into_sys_path_first():
    import ast
    for rel in R31_6E_FILES:
        tree = ast.parse((v2.ROOT / rel).read_text())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "insert":
                assert "path" not in ast.unparse(n.func.value), (rel, ast.unparse(n))
            if isinstance(n, ast.Attribute) and n.attr in ("meta_path", "path_hooks"):
                raise AssertionError((rel, ast.unparse(n)))


def test_R32_1_after_each_report_import_site_the_root_is_not_first():
    code = ("import sys, os; sys.path.append(%r)\n"
            "import scripts.run_rotation_core_v2 as run\n"
            "root = os.path.realpath(%r)\n"
            "first = lambda: os.path.realpath(sys.path[0] or '.') == root\n"
            "out = [first()]\n"
            "from scripts.rotation_core_v2_report import write_ledger_status_md; out.append(first())\n"
            "from scripts.rotation_core_v2_report import write_final_md; out.append(first())\n"
            "from scripts.rotation_core_v2_report import write_selection_md; out.append(first())\n"
            "print('FIRST', out)\n") % (str(v2.ROOT), str(v2.ROOT))
    r = _py(["-c", code])
    assert r.returncode == 0, r.stderr[-400:]
    assert "FIRST [False, False, False, False]" in r.stdout
    src = (v2.ROOT / "scripts/run_rotation_core_v2.py").read_text()
    assert src.count("from scripts.rotation_core_v2_report import") == 3


def test_R32_2_a_top_level_package_from_elsewhere_is_refused(monkeypatch, tmp_path):
    import types
    v2.check_import_environment(v2.ROOT)
    with monkeypatch.context() as m:
        fake = types.ModuleType("engine"); fake.__file__ = str(tmp_path / "site-packages" / "engine" / "__init__.py")
        m.setitem(sys.modules, "engine", fake)
        with pytest.raises(v2.SealedRefusal, match="package engine is not the repository's own"):
            v2.check_import_environment(v2.ROOT)
    with monkeypatch.context() as m:
        ns = types.ModuleType("tests"); ns.__path__ = [str(tmp_path / "elsewhere")]
        m.setitem(sys.modules, "tests", ns)
        with pytest.raises(v2.SealedRefusal, match="package tests is not the repository's own"):
            v2.check_import_environment(v2.ROOT)
    v2.check_import_environment(v2.ROOT)


def test_R32_3_unreadable_package_metadata_refuses(monkeypatch):
    import importlib.metadata as md, scripts.run_rotation_core_v2 as run
    def boom():
        raise OSError("metadata")
    monkeypatch.setattr(md, "packages_distributions", boom)
    with pytest.raises(SystemExit, match="R32.3"):
        run._protected_names()


def test_R32_4_format_0_only_in_a_test_repository(tmp_path):
    origin, work, g = _git_env(tmp_path)
    assert v2._git("config", "--get", "core.repositoryformatversion", root=work).stdout.strip() == b"0"
    v2.check_repo_config(work, str(origin), test_repo=True)
    with pytest.raises(v2.SealedRefusal, match="core.repositoryformatversion"):
        v2.check_repo_config(work, str(origin))                        # the real-context rule: 1 only
    g("config", "core.repositoryformatversion", "1", cwd=work)
    v2.check_repo_config(work, str(origin))
    v2.check_repo_config(v2.ROOT, v2.REMOTE_URL)


def test_R32_5_driver_refuses_a_url_remote_on_its_own(tmp_path):
    c = _tctx_cfg(tmp_path)
    for url in ("file:///tmp/o.git", "https://github.com/x/y.git", "ssh://h/tmp/o.git"):
        r = _py([], {"argv": ["--stage", "pre1998"], "ctx": dict(c, remote_url=url)}, tmp_path)
        assert r.returncode != 0 and "R32.5" in r.stderr


def test_R32_6_header_is_read_after_the_pin_check_in_the_sealed_stages():
    import ast, inspect, scripts.run_rotation_core_v2 as run
    src = inspect.getsource(run._main_body)
    pre = src[src.index('if a.stage == "pre1998":'):src.index('if a.stage == "confirm":')]
    conf = src[src.index('if a.stage == "confirm":'):src.index('if a.stage == "select":')]
    assert pre.index("stage1_release(") < pre.index("verify_header_v2(FROZEN)")
    assert conf.index("ctx.engine_check(") < conf.index("verify_header_v2(FROZEN)")


def test_R32_7_every_printed_or_recorded_rehearsal_figure_is_windowed_or_declared(tmp_path, monkeypatch):
    """Mechanical over what the rehearsal prints and records: every `count` line printed (the integrity block) is a
    declared warm-up-inclusive count or computed on the window's sessions (its source expression uses the window
    index, the window's eras or the window's episodes); the Phase A lines are taken on the spec's window masks
    (both pseudo-eras start 1998-01-02); signs and magnitudes come from statistics shown windowed by
    test_R31_5_every_rehearsal_statistic_is_on_sessions_from_1998."""
    import ast, inspect, scripts.run_rotation_core_v2 as run
    ind, fac = fixture_texts(start="1996-01-02", end="2019-12-31")
    lines = []
    e = run.rehearsal_command(io.StringIO(ind), io.StringIO(fac), out=lines.append, B_=20, engine_commit="E",
                              selection=ORIG_SELECTION)
    printed = {ln.split()[2] for ln in lines if ln.startswith("REHEARSAL count ")}
    recorded = {k for k, _ in run._flat(e["integrity"])}
    assert printed == recorded and printed
    src = textwrap_dedent(inspect.getsource(run.pre1998_stats))
    tree = ast.parse(src)
    integ = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "integrity" for t in n.targets))
    windowed = {"idx", "ERAS_", "eps", "era_values"}
    for k, v in zip(integ.keys, integ.values):
        key = k.value
        names = {x.id for x in ast.walk(v) if isinstance(x, ast.Name)}
        if key in WARMUP_INCLUSIVE_COUNTS:
            continue
        assert names & windowed, (key, ast.unparse(v))
    top = {k.split(".")[0] for k in printed}
    assert top <= {k.value for k in integ.keys}
    phase = [ln for ln in lines if ln.startswith("REHEARSAL PHASE_A ") and " rehearsal_1998_2019 " in ln]
    assert phase and all((" P1_1998_2008 " in ln) or (" P2_2009_2019 " in ln) for ln in phase)
    assert all(a >= run.REH_START for a, _ in run.REH_SPEC["eras"].values())


def textwrap_dedent(s):
    import textwrap
    return textwrap.dedent(s)


# ------------------------------------------------------------------ R32.8 only engine, scripts and tests load from the root
CODE_COPY = ("engine/__init__.py", "engine/rotation_core_v2.py", "engine/rotation_core_evaluation.py",
             "engine/validation.py", "scripts/__init__.py", "scripts/run_rotation_core_v2.py",
             "scripts/rotation_core_v2_report.py", "tests/__init__.py", "tests/rotation_core_v2_fixture.py",
             "research/rotation_core/protocol_header_v2.json", "research/rotation_core/results_v2_selection.json")


def _code_repo(tmp_path, planted: dict):
    """A temporary repository holding a copy of the run's code with `planted` files COMMITTED at its root."""
    import shutil
    root = tmp_path / "repo"
    for rel in CODE_COPY:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(v2.ROOT / rel, root / rel)
    for name, body in planted.items():
        (root / name).write_text(body)
    def g(*a):
        return subprocess.run([v2.tool("git"), *a], cwd=root, capture_output=True, check=True, env=v2.child_env())
    g("init", "-q"); g("config", "core.repositoryformatversion", "1")
    g("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "copy")
    return root


def _marker_body(marker):
    return f"open({str(marker)!r}, 'w').write('RAN')\nraise ImportError('planted')\n"


@pytest.mark.parametrize("name", ["cython.py", "bottleneck.py", "numexpr.py"])
def test_R32_8_a_committed_optional_name_at_the_root_refuses_before_start_and_never_runs(tmp_path, name):
    marker = tmp_path / "marker"
    root = _code_repo(tmp_path, {name: _marker_body(marker)})
    r = subprocess.run([PY, *RUN_FLAGS, "scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"], cwd=root,
                       capture_output=True, text=True, env=_clean_env())
    assert r.returncode != 0 and "shadows an optional import (R32.8)" in r.stderr
    assert "WITNESS" not in r.stdout and not marker.exists()               # refused before START, never ran


def test_R32_8_a_an_arbitrary_root_module_is_never_found_and_a_loaded_one_is_refused(tmp_path):
    marker = tmp_path / "marker"
    root = _code_repo(tmp_path, {"zz_anything.py": _marker_body(marker)})
    r = subprocess.run([PY, *RUN_FLAGS, "scripts/run_rotation_core_v2.py", "--dry-run-stage1-fixture"], cwd=root,
                       capture_output=True, text=True, env=_clean_env())
    assert r.returncode == 0, r.stderr[-400:]
    assert not marker.exists()                                             # nothing imports it; it never ran
    # a root module that IS loaded (here forced, as a probe would) is refused by the strict check before main
    code = ("import sys; sys.path.append(%r)\n"
            "try:\n    import zz_anything\nexcept ImportError:\n    pass\n"
            "sys.modules['zz_anything'] = type(sys)('zz_anything'); sys.modules['zz_anything'].__file__ = %r\n"
            "import scripts.run_rotation_core_v2\n") % (str(root), str(root / "zz_anything.py"))
    r2 = subprocess.run([PY, *RUN_FLAGS, "-c", code], cwd=root, capture_output=True, text=True, env=_clean_env())
    assert r2.returncode != 0 and "zz_anything was loaded from the repository directory" in r2.stderr


def test_R32_8_root_is_off_the_import_path_during_main_and_restored_after():
    code = ("import sys, os; sys.path.append(%r)\n"
            "import scripts.run_rotation_core_v2 as run\n"
            "seen = {}\n"
            "def probe(*a, **k):\n"
            "    seen['root_on_path'] = any(os.path.realpath(p or '.') == os.path.realpath(%r) for p in sys.path)\n"
            "    import engine.validation, scripts.rotation_core_v2_report, tests.rotation_core_v2_fixture\n"
            "    seen['submodules'] = True\n"
            "    return 0\n"
            "run._main_guarded = probe\n"
            "run.main(['--dry-run-stage1-fixture'])\n"
            "print('SEEN', seen, any(os.path.realpath(p) == os.path.realpath(%r) for p in sys.path))\n"
            ) % (str(v2.ROOT), str(v2.ROOT), str(v2.ROOT))
    r = _py(["-c", code])
    assert r.returncode == 0, r.stderr[-400:]
    assert "SEEN {'root_on_path': False, 'submodules': True} True" in r.stdout


def test_R32_8_in_process_strict_and_names_only(monkeypatch):
    import types, scripts.run_rotation_core_v2 as run
    run.refuse_shadowed_modules()                                         # under pytest: names-only, passes
    m = types.ModuleType("zz_any"); m.__file__ = str(v2.ROOT / "zz_any.py")
    monkeypatch.setitem(sys.modules, "zz_any", m)
    run.refuse_shadowed_modules()                                         # not a protected name: names-only passes
    with pytest.raises(SystemExit, match="R32.8"):
        run.refuse_shadowed_modules(strict=True)                         # the real run's rule refuses it
