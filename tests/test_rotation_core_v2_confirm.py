"""Rotation Core v2 confirmation machinery (R16 S1/S5/S6, R17, R18, O1/O5-O8). Synthetic fixtures only: no market
outcome is computed on real data by any test here."""
import io, json, contextlib, subprocess, re
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from engine import rotation_core_evaluation as rc
from engine import rotation_core_v2 as v2
from tests.rotation_core_v2_fixture import make_fixture, make_fund_fixture, write_manifest

ORIG_SELECTION = v2.ROOT / "research/rotation_core/results_v2_selection.json"
IND, FAC = "49_Industry_Portfolios_Daily.csv", "F-F_Research_Data_Factors_daily.csv"


@pytest.fixture(autouse=True)
def _sel(monkeypatch):
    monkeypatch.setattr(v2, "SELECTION_RESULT", ORIG_SELECTION)


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    d = tmp_path_factory.mktemp("conf")
    return make_fixture(d / "fx")


@pytest.fixture(scope="module")
def stage1(fx, tmp_path_factory):
    import scripts.run_rotation_core_v2 as run
    v2.SELECTION_RESULT = ORIG_SELECTION
    d = tmp_path_factory.mktemp("s1")
    lines, buf, err = [], io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        e = run.blind_stage1(fx / IND, fx / FAC, d / "gate.json", B_=20, engine_commit="fixture",
                             publish_path=d / "published.json", out=lambda s: (lines.append(s), print(s)))
    return d, e, lines, buf.getvalue() + err.getvalue()


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
def test_S6_stage1_prints_only_signs_counts_and_hex(stage1):
    d, e, lines, captured = stage1
    assert not re.search(r"\d\.\d", captured), "a decimal number reached stdout/stderr"
    signs = [ln for ln in lines if ln.startswith("GATE_SIGN")]
    assert len(signs) == 16
    assert all(ln.split()[-1] in {"+", "-", "NaN"} for ln in signs)
    assert not any("H2" in ln and ln.startswith("GATE_SIGN") for ln in lines)          # S1c: H2 signs not printed
    gate = json.loads((d / "gate.json").read_text())
    assert "H2_signs" not in json.dumps(gate) and not any(k.startswith("H2|") for k in e["gate_signs"])
    assert set(gate) == {"schema", "header_sha256", "opening_hypotheses", "gate_history", "gate_open_all_runs"}
    assert gate["opening_hypotheses"] == ["H1", "H3"]
    assert not list(d.glob("sealed*")), "S6: no magnitudes file"


def test_S6_magnitudes_hash_reproduced_and_changes_with_input(fx, stage1, tmp_path):
    import scripts.run_rotation_core_v2 as run
    d, e, lines, _ = stage1
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
    d, e, lines, _ = stage1
    if e["gate_open"]:
        assert not (d / "published.json").exists()
    else:
        pub = json.loads((d / "published.json").read_text())
        assert pub["magnitudes_sha256"] == e["magnitudes_sha256"]


def test_S6_exception_text_carries_no_value(fx, tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    def boom(*a, **k):
        raise ValueError("excess 0.0123 leaked")
    monkeypatch.setattr(run, "pre1998_report", boom)
    with pytest.raises(SystemExit) as ei:
        run.blind_stage1(fx / IND, fx / FAC, tmp_path / "g.json", B_=20, out=lambda s: None)
    assert "0.0123" not in str(ei.value) and "withheld" in str(ei.value)


def test_O5_nan_is_neither_sign_and_fails_closed():
    import scripts.run_rotation_core_v2 as run
    assert v2.sign(float("nan")) == "NaN" and v2.sign(0.0) == "-" and v2.sign(1e-9) == "+"
    signs = {f"{h}|{e}|{r}|{c}": "+" for h in ("H1", "H3") for e in run.ERAS for r in run.READINGS for c in run.COST_RUNS}
    nan0 = {k: 0 for k in signs}
    assert run.gate_decision(signs, nan0, 0)[0] is True
    s2 = dict(signs); s2["H1|E1_1928_1945|eq|base"] = "NaN"; s2["H3|E2_1946_1997|drift|strict"] = "-"
    assert run.gate_decision(s2, nan0, 0)[0] is False
    n2 = dict(nan0); n2["H3|E1_1928_1945|eq|base"] = 1
    assert run.gate_decision(signs, n2, 0) == (False, {"H1": True, "H3": True}, False)   # integrity failure closes
    assert run.gate_decision(signs, nan0, 1)[0] is False                                # strict-run violation closes


def test_gate_needs_all_eight_signs_of_one_hypothesis():
    import scripts.run_rotation_core_v2 as run
    keys = [f"{h}|{e}|{r}|{c}" for h in ("H1", "H3") for e in run.ERAS for r in run.READINGS for c in run.COST_RUNS]
    nan0 = {k: 0 for k in keys}
    for k in keys:                      # every single '-' in H1 with H3 all '-' closes the gate
        s = {x: ("+" if x.startswith("H1") else "-") for x in keys}
        if k.startswith("H1"):
            s[k] = "-"
            assert run.gate_decision(s, nan0, 0)[0] is False


# ------------------------------------------------------------------ R17 gate history, O8
def test_R17_gate_history_appends_chains_and_refuses_rewrites(tmp_path):
    g = tmp_path / "gate.json"
    e = lambda o: {"engine_commit": "c", "gate_open": o}
    d1 = v2.append_gate_entry(g, e(True), None)
    d2 = v2.append_gate_entry(g, e(True), d1["gate_history"])
    assert [x["run_index"] for x in d2["gate_history"]] == [0, 1] and d2["gate_open_all_runs"]
    v2.verify_chain(d2["gate_history"])
    tampered = json.loads(g.read_text()); tampered["gate_history"][0]["gate_open"] = False
    with pytest.raises(v2.SealedRefusal):
        v2.verify_chain(tampered["gate_history"])
    g.write_text(json.dumps(tampered))
    with pytest.raises(v2.SealedRefusal):          # local history does not extend the remote one
        v2.append_gate_entry(g, e(True), d2["gate_history"])


def test_O8_deleted_local_gate_cannot_restart_history(tmp_path):
    g = tmp_path / "gate.json"
    d1 = v2.append_gate_entry(g, {"engine_commit": "c", "gate_open": False}, None)
    g.unlink()                                      # the local marker is deleted
    with pytest.raises(v2.SealedRefusal):
        v2.append_gate_entry(g, {"engine_commit": "c2", "gate_open": True}, d1["gate_history"])


def test_O8_run_once_guard_uses_the_remote_branch(tmp_path, monkeypatch):
    import scripts.run_rotation_core_v2 as run
    monkeypatch.setattr(v2, "fetch_remote", lambda: None)
    p = tmp_path / "x.json"
    monkeypatch.setattr(run, "_exists_on_remote", lambda q: True)       # deleted locally, present on the remote
    with pytest.raises(SystemExit):
        run.run_once_guard(p, "x")
    monkeypatch.setattr(run, "_exists_on_remote", lambda q: False)
    run.run_once_guard(p, "x")
    p.write_text("{}")
    with pytest.raises(SystemExit):
        run.run_once_guard(p, "x")


def _r2(tmp_path, gate_doc, **over):
    g = tmp_path / "gate.json"; g.write_text(json.dumps(gate_doc))
    import hashlib
    body = {"windows_released": [v2.W_H], "protocol_header_sha256": v2.FROZEN_V2_SHA256, "engine_commit": "E",
            "stage1_gate_sha256": hashlib.sha256(g.read_bytes()).hexdigest()}
    body.update(over)
    r = tmp_path / "r2.json"; r.write_text(json.dumps(body))
    return r, g


def _hist(*opens, commit="E"):
    h = []
    for o in opens:
        h.append({"engine_commit": commit, "gate_open": o, "magnitudes_sha256": "m",
                  "run_index": len(h), "prev_chain_sha256": v2.chain_hash(h) if h else None})
    return {"gate_history": h}


def test_R17_stage2_refuses_if_any_run_was_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "_committed_clean", lambda p: True)
    monkeypatch.setattr(v2, "check_engine_commit", lambda c: None)
    r, g = _r2(tmp_path, _hist(True, True))
    assert v2.stage2_release(r, g, check_remote=False)["_gate_latest"]["run_index"] == 1
    for h in (_hist(False, True), _hist(True, False), _hist()):
        r, g = _r2(tmp_path, h)
        with pytest.raises(v2.SealedRefusal):
            v2.stage2_release(r, g, check_remote=False)


def test_S1c_stage2_release_cannot_name_the_opening_list_and_pins_engine_and_gate_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "_committed_clean", lambda p: True)
    monkeypatch.setattr(v2, "check_engine_commit", lambda c: None)
    for over in ({"opening_condition_hypotheses": ["H1", "H3", "H2"]}, {"engine_commit": "OTHER"},
                 {"stage1_gate_sha256": "0" * 64}, {"protocol_header_sha256": "0" * 64}, {"windows_released": [v2.W_PRE]}):
        r, g = _r2(tmp_path, _hist(True), **over)
        with pytest.raises(v2.SealedRefusal):
            v2.stage2_release(r, g, check_remote=False)


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


# ------------------------------------------------------------------ S5 remote containment, check_engine_commit
def test_S5_local_only_commit_is_not_a_release(monkeypatch):
    calls = []
    def fake_git(*a, check=True):
        calls.append(a)
        if a[0] == "log":
            return subprocess.CompletedProcess(a, 0, b"deadbeef\n", b"")
        return subprocess.CompletedProcess(a, 1, b"", b"")         # merge-base --is-ancestor: not contained
    monkeypatch.setattr(v2, "_git", fake_git)
    with pytest.raises(v2.SealedRefusal):
        v2.on_remote(v2.RELEASE)
    assert any(c[0] == "merge-base" and c[-1] == v2.REMOTE_REF for c in calls)


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


# ------------------------------------------------------------------ O7 fixture guard
def test_O7_fixture_dry_run_needs_a_manifest_and_refuses_real_inputs(tmp_path):
    import scripts.run_rotation_core_v2 as run
    d = make_fixture(tmp_path / "f")
    with pytest.raises(v2.SealedRefusal):
        run.check_fixture_dir(d, real_hashes=set())
    files = write_manifest(d)
    run.check_fixture_dir(d, real_hashes=set())
    with pytest.raises(v2.SealedRefusal):                                   # a listed hash equals a real input
        run.check_fixture_dir(d, real_hashes={files[IND]})
    (d / FAC).write_text((d / FAC).read_text() + "\n")
    with pytest.raises(v2.SealedRefusal):                                   # file no longer matches the manifest
        run.check_fixture_dir(d, real_hashes=set())


def test_O7_fixture_dry_run_stamps_every_line(tmp_path, monkeypatch, capsys):
    import scripts.run_rotation_core_v2 as run, sys
    d = make_fixture(tmp_path / "f2"); write_manifest(d)
    monkeypatch.setattr(run, "real_input_hashes", lambda: set())
    monkeypatch.setattr(sys, "argv", ["run", "--dry-run-stage1-fixture", str(d)])
    assert run.main() == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) > 40 and all(ln.startswith("FIXTURE ") for ln in out)
    assert not re.search(r"\d\.\d", "\n".join(out))


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


@pytest.fixture(scope="module")
def final_run(tmp_path_factory, stage1):
    import scripts.run_rotation_core_v2 as run
    v2.SELECTION_RESULT = ORIG_SELECTION
    d = tmp_path_factory.mktemp("final")
    full = make_fixture(d / "full", extra_after="2025-12-31")
    pre = make_fixture(d / "pre")                  # same seed: identical pre-1998 rows, truncated copy
    funds = make_fund_fixture(d / "funds")
    mp = pytest.MonkeyPatch()
    mp.setattr(v2, "assert_window", lambda *a, **k: None)
    mp.setattr(v2, "seal_guard", lambda *a, **k: None)
    try:
        sha = run.pre1998_report(pre / IND, pre / FAC, B_=20)["magnitudes"]
        res = run.final_evaluation(pre / IND, full / IND, full / FAC, funds, expected_sha=v2.magnitudes_sha(sha), B_=20)
        with pytest.raises(v2.SealedRefusal):
            run.final_evaluation(pre / IND, full / IND, full / FAC, funds, expected_sha="0" * 64, B_=20)
    finally:
        mp.undo()
    return res


def test_S1_final_evaluation_end_to_end_on_fixture(final_run):
    import scripts.run_rotation_core_v2 as run
    res = final_run
    assert res["strict_inequality_violations"] == 0 and res["nonfinite_statistics"] == 0
    assert set(res["verdicts"]) == {"H1", "H2", "H3"}
    for h, v in res["verdicts"].items():
        assert v["verdict"] in {"FAIL", "survives falsification on history", "signal not shown to be tradable"}
        assert v["legs_total"] == 33
        lg = run.conjunction_legs(h, res["conjunction_inputs"])
        assert sorted(k for k, x in lg.items() if not x) == v["failed_legs"]
    assert set(res["holm_m3"]) == {"block21", "block63"} and res["governing"].startswith("block 21")
    assert len(res["holm_m3"]["block21"]) == 8                       # 2 readings x 2 cost runs x 2 conventions
    assert set(res["funds"]["estimates"]) == {"eq|base", "eq|strict", "drift|base", "drift|strict"}
    assert "named_mapping_descriptive_hindsight" in res["funds"]
    st = res["standalone_2020_2025_OUT_OF_SAMPLE_EFFECT_SIZE"]
    assert set(st) == {"block21", "block63"} and len(st["block21"]) == 12
    # warm state: 2020-2025 books were held continuously (no cold NEUTRAL restart on 2020-01-02)
    w = res["h2020_2025"]["eq|base"]["books"]["H1"]["matched_mix_weights"]
    assert w["OFF"] + w["DEF"] > 0


def test_S1_final_report_writes(final_run, tmp_path):
    from scripts.rotation_core_v2_report import write_final_md
    write_final_md(json.loads(json.dumps(final_run, default=float)), tmp_path / "f.md")
    t = (tmp_path / "f.md").read_text()
    assert "conditional on the pre-1998 gate" in t and "independent bets" in t


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
