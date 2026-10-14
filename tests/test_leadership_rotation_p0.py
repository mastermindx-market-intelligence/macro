"""Tests for scripts.leadership_rotation_p0 (T11 P0 synthetic grid)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts import leadership_rotation_study as st
from scripts.leadership_rotation_p0 import (
    REGIME_MAX,
    REGIME_MIN,
    TAIL,
    load_sim_records,
    size_check,
    simulate_family,
    run_cell,
    summarize_records,
    window_for_target,
    wilson_interval,
)


def _base_groups(
    *,
    pass_paths: set[tuple[str, str]] | None = None,
    iut_overrides: dict[tuple[str, str], dict] | None = None,
) -> dict:
    pass_paths = pass_paths or set()
    iut_overrides = iut_overrides or {}
    groups: dict = {}
    for g in ("defensive_sector", "broadening_proxy"):
        groups[g] = {}
        for h in ("H1", "H2", "H3"):
            verdict = (
                "DEVELOPMENT_PASS"
                if (g, h) in pass_paths
                else "DEVELOPMENT_FAIL"
            )
            row: dict = {
                "verdict": verdict,
                "honest_n": 20,
                "window_years": 4.0,
                "point": 0.01,
                "raw_p": 0.5,
                "holm_p": 0.9,
            }
            if h == "H1":
                iut = {
                    "cond_a": False,
                    "cond_b": False,
                    "p_h1": 0.5,
                    "delay_reduction": 0.01,
                    "burden_cut_b": 0.02,
                }
                iut.update(iut_overrides.get((g, h), {}))
                row["iut"] = iut
            groups[g][h] = row
    return groups


def _sim_record(
    cell_id: int,
    k: int,
    *,
    status: str = "OK",
    pass_paths: set[tuple[str, str]] | None = None,
    iut_overrides: dict | None = None,
    extra: dict | None = None,
) -> dict:
    rec: dict = {
        "cell_id": cell_id,
        "k": k,
        "status": status,
        "n_formation": 1008,
    }
    if status == "OK":
        rec["truth_n"] = 5000
        rec["ends"] = {"H1": 2000, "H2": 2000, "H3": 2000}
        rec["groups"] = _base_groups(
            pass_paths=pass_paths, iut_overrides=iut_overrides
        )
    if extra:
        rec.update(extra)
    return rec


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


# MUTATION: scripts/leadership_rotation_p0.py:118 replace seed_seq with np.random.SeedSequence([0])
def test_simulate_family_deterministic_and_varies_by_k():
    ss0 = np.random.SeedSequence([1, 2, 0])
    ss1 = np.random.SeedSequence([1, 2, 1])
    g0a, _ = simulate_family(0.01, 0.0, 0.5, 504, ss0)
    g0b, _ = simulate_family(0.01, 0.0, 0.5, 504, ss0)
    g1, _ = simulate_family(0.01, 0.0, 0.5, 504, ss1)
    assert np.allclose(g0a["defensive_sector"][0].num, g0b["defensive_sector"][0].num)
    assert not np.allclose(g0a["defensive_sector"][0].num, g1["defensive_sector"][0].num)


# MUTATION: scripts/leadership_rotation_p0.py:88 replace max(...) with sigma alone
def test_null_relative_return_sd_matches_sigma():
    sigma = 0.010
    n_form = 20_000 - st.WARMUP - TAIL
    groups, _ = simulate_family(sigma, 0.0, 0.5, n_form, np.random.SeedSequence(99))
    ps = groups["defensive_sector"][0]
    m = np.log(ps.num[1:] / ps.num[:-1]) - np.log(ps.den[1:] / ps.den[:-1])
    sd = float(np.std(m, ddof=1))
    assert abs(sd - sigma) / sigma < 0.05


# MUTATION: scripts/leadership_rotation_p0.py:134 replace delta / 20.0 with delta
def test_regime_drift_mean_relative_return():
    n_form = 8000
    groups, truth = simulate_family(1e-6, 0.01, 0.0, n_form, np.random.SeedSequence(7))
    g = "defensive_sector"
    regime = np.asarray(truth["regime_mask"][g], dtype=bool)
    ps = groups[g][0]
    rel = np.log(ps.num[1:] / ps.num[:-1]) - np.log(ps.den[1:] / ps.den[:-1])
    on = rel[regime[1:]]
    off = rel[~regime[1:]]
    assert float(np.mean(on)) == pytest.approx(0.01 / 20.0, rel=0.15, abs=0.0002)
    assert abs(float(np.mean(off))) < 0.0001


# MUTATION: scripts/leadership_rotation_p0.py:108 append onset at warmup - 1
def test_onsets_regime_length_no_overlap():
    n_form = 3000
    groups, truth = simulate_family(0.01, 0.005, 0.5, n_form, np.random.SeedSequence(3))
    for g in groups:
        onsets = truth["onsets"][g]
        regime = truth["regime_mask"][g]
        for t in onsets:
            assert st.WARMUP <= t < st.WARMUP + n_form
        active_end = -1
        lengths = []
        for t in sorted(onsets):
            assert t > active_end
            run = 0
            while t + run < st.WARMUP + n_form and regime[t + run]:
                run += 1
            lengths.append(run)
            active_end = t + run - 1
        assert lengths
        assert all(REGIME_MIN <= L <= REGIME_MAX for L in lengths)


# MUTATION: scripts/leadership_rotation_p0.py:131 use sqrt_rho for both legs of u
def test_within_group_u_correlation():
    n_form = 15_000
    rho = 0.5
    groups, _ = simulate_family(0.01, 0.0, rho, n_form, np.random.SeedSequence(11))
    spy = groups["defensive_sector"][0].spy

    def _u_hat(ps):
        m = np.diff(np.log(spy))
        rel = np.log(ps.num[1:] / ps.num[:-1]) - np.log(ps.den[1:] / ps.den[:-1])
        return rel + 0.3 * m

    g = groups["defensive_sector"]
    c_within = float(np.corrcoef(_u_hat(g[0]), _u_hat(g[1]))[0, 1])
    c_across = float(np.corrcoef(_u_hat(g[0]), _u_hat(groups["broadening_proxy"][0]))[0, 1])
    assert abs(c_within - rho) < 0.05
    assert abs(c_across) < 0.05


# MUTATION: scripts/leadership_rotation_p0.py:201 reverse range(st.WARMUP, last_e + 1)
def test_window_for_target_monotone_in_n_target():
    groups, _ = simulate_family(0.01, 0.005, 0.5, 252 * 12, np.random.SeedSequence(5))
    w20 = window_for_target(groups, 20, "H2")
    w40 = window_for_target(groups, 40, "H2")
    assert w20 is not None and w40 is not None
    assert w20 <= w40


# MUTATION: scripts/leadership_rotation_p0.py:348 skip done sims when appending
def test_run_cell_resumable(tmp_path: Path):
    out = tmp_path / "sims.jsonl"
    run_cell(0.01, 0.0, 0.5, 20, 1, cell_id=99, workers=1, out=out)
    n1 = sum(1 for _ in out.read_text().splitlines() if _)
    run_cell(0.01, 0.0, 0.5, 20, 1, cell_id=99, workers=1, out=out)
    n2 = sum(1 for _ in out.read_text().splitlines() if _)
    assert n1 == 1 and n2 == 1


# MUTATION: scripts/leadership_rotation_p0.py:218 replace z with 1.0 in wilson_interval
def test_wilson_interval_known_values():
    lo, hi = wilson_interval(0, 200)
    assert lo < 1e-9
    assert hi == pytest.approx(0.0188, abs=1e-3)
    lo5, hi5 = wilson_interval(5, 200)
    assert lo5 == pytest.approx(0.0107, abs=1e-3)
    assert hi5 == pytest.approx(0.0572, abs=1e-3)


# MUTATION: scripts/leadership_rotation_p0.py:733 use lo < alpha instead of lo > alpha
def test_size_check_flags_high_null_pass_rate():
    passes = 20
    n_ok = 200
    lo_ok, _ = wilson_interval(passes, n_ok)
    cell_bad = {
        "delta": 0.0,
        "cell_id": 0,
        "sigma": 0.007,
        "rho": 0.5,
        "n_target": 20,
        "n_sims": n_ok,
        "n_ok": n_ok,
        "summary": {
            "by_group_hypothesis": {
                "defensive_sector/H1": {
                    "passes": passes,
                    "n_ok": n_ok,
                    "pass_rate_ok": passes / n_ok,
                    "wilson_95_ok": {"lower": lo_ok, "upper": 1.0},
                }
            },
            "family_any": {
                "passes": 0,
                "n_ok": n_ok,
                "pass_rate_ok": 0.0,
                "wilson_95_ok": {"lower": 0.0, "upper": 1.0},
            },
        },
    }
    lo2, _ = wilson_interval(2, n_ok)
    cell_ok = {
        "delta": 0.0,
        "cell_id": 1,
        "sigma": 0.007,
        "rho": 0.5,
        "n_target": 40,
        "n_sims": n_ok,
        "n_ok": n_ok,
        "summary": {
            "by_group_hypothesis": {
                "defensive_sector/H1": {
                    "passes": 2,
                    "n_ok": n_ok,
                    "pass_rate_ok": 2 / n_ok,
                    "wilson_95_ok": {"lower": lo2, "upper": 1.0},
                }
            },
            "family_any": {
                "passes": 0,
                "n_ok": n_ok,
                "pass_rate_ok": 0.0,
                "wilson_95_ok": {"lower": 0.0, "upper": 1.0},
            },
        },
    }
    bad = size_check([cell_bad])
    ok = size_check([cell_ok])
    assert bad["violations"]
    assert not ok["violations"]


# MUTATION: scripts/leadership_rotation_p0.py:710 return 0 from _cmd_size when not sized
def test_size_cli_fail_closed_on_null_passes(tmp_path: Path):
    import subprocess
    import sys

    recs = [
        _sim_record(
            0,
            k,
            pass_paths={("defensive_sector", "H1")} if k < 6 else None,
        )
        for k in range(20)
    ]
    p = tmp_path / "sims.jsonl"
    _write_jsonl(p, recs)
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.leadership_rotation_p0", "size", "--in", str(p)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    out = json.loads(proc.stdout)
    assert proc.returncode == 1
    assert any(v["flag"] == "SIZE_VIOLATION" for v in out["violations"])
    assert any(v["row"] == "defensive_sector/H1" for v in out["violations"])


# MUTATION: scripts/leadership_rotation_p0.py:707 skip raise ValueError for no null cells
def test_size_cli_exit_2_when_no_delta_zero(tmp_path: Path):
    import subprocess
    import sys

    recs = [_sim_record(30, k) for k in range(5)]
    p = tmp_path / "alt.jsonl"
    _write_jsonl(p, recs)
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.leadership_rotation_p0", "size", "--in", str(p)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert proc.returncode == 2
    assert "no delta=0 cells" in proc.stderr


# MUTATION: scripts/leadership_rotation_p0.py:459 use n_ok instead of n for pass_rate
def test_ok_denominator_pass_rates():
    recs = []
    for k in range(10):
        if k < 4:
            recs.append(_sim_record(0, k, status="UNREACHED"))
        elif k == 4:
            recs.append(
                _sim_record(0, k, pass_paths={("defensive_sector", "H1")})
            )
        else:
            recs.append(_sim_record(0, k))
    summ = summarize_records({0: recs})[0]["summary"]
    row = summ["by_group_hypothesis"]["defensive_sector/H1"]
    assert row["pass_rate"] == 0.1
    assert row["pass_rate_ok"] == pytest.approx(1 / 6)


# MUTATION: scripts/leadership_rotation_p0.py:642 skip duplicate counting
def test_load_sim_records_identical_and_conflicting_duplicates(tmp_path: Path):
    r0 = _sim_record(0, 0)
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write_jsonl(a, [r0])
    _write_jsonl(b, [r0])
    by_cell, stats = load_sim_records([a, b])
    assert stats["duplicates"] == 1
    assert len(by_cell[0]) == 1
    r1 = dict(r0)
    r1["truth_n"] = 9999
    c = tmp_path / "c.jsonl"
    _write_jsonl(c, [r1])
    with pytest.raises(ValueError, match="conflicting duplicate"):
        load_sim_records([a, c])


# MUTATION: scripts/leadership_rotation_p0.py:631 continue on middle malformed line
def test_load_sim_records_partial_last_and_middle_error(tmp_path: Path):
    r0 = _sim_record(0, 0)
    p = tmp_path / "partial.jsonl"
    text = json.dumps(r0) + "\nnot json\n"
    p.write_text(text)
    by_cell, stats = load_sim_records([p])
    assert stats["skipped_partial"] == 1
    assert len(by_cell[0]) == 1
    p2 = tmp_path / "bad.jsonl"
    p2.write_text(json.dumps(r0) + "\n{broken\n" + json.dumps(_sim_record(0, 1)) + "\n")
    with pytest.raises(ValueError, match="bad.jsonl:2"):
        load_sim_records([p2])


# MUTATION: scripts/leadership_rotation_p0.py:493 replace family_passes += 1 with += 2
def test_family_any_counts_sim_once_with_two_passes():
    recs = [
        _sim_record(
            0,
            0,
            pass_paths={("defensive_sector", "H1"), ("broadening_proxy", "H2")},
        )
    ]
    fam = summarize_records({0: recs})[0]["summary"]["family_any"]
    assert fam["passes"] == 1
    assert fam["pass_rate_ok"] == 1.0


# MUTATION: scripts/leadership_rotation_p0.py:760 use lo < alpha for SIZE_VIOLATION
def test_size_boundary_exceeds_point_vs_violation():
    n_ok = 100

    def _cell(passes: int) -> dict:
        lo, _ = wilson_interval(passes, n_ok)
        return {
            "delta": 0.0,
            "cell_id": 0,
            "sigma": 0.007,
            "rho": 0.5,
            "n_target": 20,
            "n_sims": n_ok,
            "n_ok": n_ok,
            "summary": {
                "by_group_hypothesis": {
                    "defensive_sector/H1": {
                        "passes": passes,
                        "n_ok": n_ok,
                        "pass_rate_ok": passes / n_ok,
                        "wilson_95_ok": {"lower": lo, "upper": 1.0},
                    }
                },
                "family_any": {
                    "passes": 0,
                    "n_ok": n_ok,
                    "pass_rate_ok": 0.0,
                    "wilson_95_ok": {"lower": 0.0, "upper": 1.0},
                },
            },
        }

    mild = size_check([_cell(3)])
    assert mild["sized"]
    assert any(x["flag"] == "SIZE_EXCEEDS_POINT" for x in mild["exceeds_point"])
    harsh = size_check([_cell(10)])
    assert not harsh["sized"]
    assert any(x["flag"] == "SIZE_VIOLATION" for x in harsh["violations"])


# MUTATION: scripts/leadership_rotation_p0.py:668 read delta from records not catalog
def test_summarize_records_uses_catalog_metadata():
    rec = _sim_record(
        30,
        0,
        extra={"sigma": 9.99, "delta": 9.99, "rho": 9.99, "n_target": 999},
    )
    row = summarize_records({30: [rec]})[0]
    assert row["sigma"] == 0.010
    assert row["delta"] == 0.0025
    assert row["rho"] == 0.5
    assert row["n_target"] == 20


# MUTATION: scripts/leadership_rotation_p0.py:441 invert cond_a_true increment
def test_h1_iut_component_counts():
    recs = [
        _sim_record(
            0,
            0,
            iut_overrides={
                ("defensive_sector", "H1"): {"cond_a": True, "cond_b": False},
            },
        ),
        _sim_record(
            0,
            1,
            iut_overrides={
                ("defensive_sector", "H1"): {"cond_a": True, "cond_b": True},
                ("broadening_proxy", "H1"): {"cond_a": False, "cond_b": True},
            },
        ),
    ]
    summ = summarize_records({0: recs})[0]["summary"]["by_group_hypothesis"]
    ds = summ["defensive_sector/H1"]
    bp = summ["broadening_proxy/H1"]
    assert ds["cond_a_true"] == 2
    assert ds["cond_b_true"] == 1
    assert bp["cond_a_true"] == 0
    assert bp["cond_b_true"] == 1


# MUTATION: scripts/leadership_rotation_p0.py:1020 skip writing md file
def test_summary_cli_writes_json_and_md(tmp_path: Path):
    import subprocess
    import sys

    recs = [_sim_record(0, 0), _sim_record(30, 0)]
    p = tmp_path / "mix.jsonl"
    _write_jsonl(p, recs)
    jout = tmp_path / "out.json"
    mout = tmp_path / "out.md"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.leadership_rotation_p0",
            "summary",
            "--in",
            str(p),
            "--json",
            str(jout),
            "--md",
            str(mout),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert proc.returncode == 0
    assert jout.is_file() and mout.is_file()
    md = mout.read_text()
    assert "Size (δ = 0)" in md
    assert "| 0 |" in md
    assert "| 30 |" in md


# MUTATION: scripts/leadership_rotation_p0.py:601 allow unknown cell_id
def test_load_sim_records_unknown_cell_id(tmp_path: Path):
    bad = {"cell_id": 999, "k": 0, "status": "UNREACHED"}
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="unknown cell_id"):
        load_sim_records([p])
