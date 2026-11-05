"""Tests for scripts.leadership_rotation_p0 (T11 P0 synthetic grid)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
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


def _run_p0_summary(tmp_path: Path, records: list[dict]) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "in.jsonl"
    _write_jsonl(p, records)
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
    assert proc.returncode == 0, proc.stderr
    return jout, mout


def _null_cell_records(
    cell_id: int,
    n_ok: int,
    h1_passes: int,
) -> list[dict]:
    recs: list[dict] = []
    for k in range(n_ok):
        paths = (
            {("defensive_sector", "H1")}
            if k < h1_passes
            else None
        )
        recs.append(_sim_record(cell_id, k, pass_paths=paths))
    return recs


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


# MUTATION: scripts/leadership_rotation_p0.py:787 use wilson_lower >= alpha in part_i_ok
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
    assert bad["sized"] is False
    assert ok["sized"] is True
    bad_row = next(r for r in bad["rows"] if r["row"] == "defensive_sector/H1")
    assert bad_row["flag"] == "SIZE_VIOLATION"
    assert bad_row["part_i_ok"] is False
    assert bad_row["part_ii_ok"] is False
    assert bad_row["m"] == n_ok
    ok_row = next(r for r in ok["rows"] if r["row"] == "defensive_sector/H1")
    assert ok_row["flag"] == "SIZED"
    assert ok_row["part_i_ok"] is True
    assert ok_row["part_ii_ok"] is True


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


# MUTATION: scripts/leadership_rotation_p0.py:791 test part_ii_ok against alpha, not the envelope
def test_size_two_part_mild_row_is_sized_and_harsh_row_violates():
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
    assert "exceeds_point" not in mild
    assert mild["exceeds_point_retired"] is True
    assert mild["rule"] == "V2_SEC3_TWO_PART"
    assert mild["violations"] == [] and mild["not_executable"] == []
    mild_row = next(r for r in mild["rows"] if r["row"] == "defensive_sector/H1")
    assert mild_row["flag"] == "SIZED"
    assert mild_row["part_i_ok"] is True
    assert mild_row["part_ii_ok"] is True
    # 3/100 is above α but inside the M = 100 noise envelope, so it is sized.
    assert mild_row["pass_rate_ok"] > mild["alpha"]
    assert mild_row["pass_rate_ok"] <= mild_row["envelope"]

    harsh = size_check([_cell(10)])
    assert not harsh["sized"]
    assert any(x["flag"] == "SIZE_VIOLATION" for x in harsh["violations"])
    harsh_row = next(r for r in harsh["rows"] if r["row"] == "defensive_sector/H1")
    assert harsh_row["part_i_ok"] is False
    assert harsh_row["part_ii_ok"] is False


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


# MUTATION: scripts/leadership_rotation_p0.py:933 use "|---|" * n_cols for table 1 separator
def test_summary_md_table_separators_valid(tmp_path: Path):
    recs = _null_cell_records(0, 4, 0) + [_sim_record(6, 0)]
    _, mout = _run_p0_summary(tmp_path, recs)
    md = mout.read_text()
    sep_re = re.compile(r"^\|(?:---\|)+$")
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if not line or set(line) - set("|- "):
            continue
        if "-" not in line:
            continue
        assert sep_re.match(line), line
        if i > 0 and lines[i - 1].startswith("|"):
            n_cols = lines[i - 1].count("|") - 1
            assert line.count("---") == n_cols


# MUTATION: scripts/leadership_rotation_p0.py:884 return f"{v:.3f}" in _md_pts (log not points)
def test_summary_md_sigma_delta_in_points(tmp_path: Path):
    recs = _null_cell_records(0, 2, 0) + [_sim_record(6, 0)]
    _, mout = _run_p0_summary(tmp_path, recs)
    md = mout.read_text()
    assert "σ (pts)" in md and "δ (pts)" in md
    power = md.split("## Table 2 Power (δ > 0)")[1].split("##")[0]
    assert re.search(r"\|\s*6\s*\|\s*0\.70\s*\|\s*0\.25\s*\|", power)


# MUTATION: scripts/leadership_rotation_p0.py:1015 append only _md_rate(rate) in table 2 columns
def test_summary_md_power_table_includes_pass_counts(tmp_path: Path):
    recs = _null_cell_records(0, 2, 0) + [
        _sim_record(6, 0, pass_paths={("defensive_sector", "H1")}),
        _sim_record(6, 1),
    ]
    _, mout = _run_p0_summary(tmp_path, recs)
    md = mout.read_text()
    power = md.split("## Table 2 Power (δ > 0)")[1].split("##")[0]
    assert re.search(r"1/2\s*\(\s*0\.500\s*\)", power)


# MUTATION: scripts/leadership_rotation_p0.py:1070 iterate violations only, skip the rest
def test_summary_md_size_verdict_locates_violations_and_exceeds(tmp_path: Path):
    expected_header = [
        "cell",
        "σ",
        "ρ",
        "N",
        "row",
        "passes / M",
        "point",
        "Wilson lower",
        "envelope",
        "(i) lower ≤ α",
        "(ii) point ≤ envelope",
        "flag",
    ]
    retirement_line = (
        "Size rule: prereg V2 §3 two-part rule (i) Wilson 95 % lower ≤ α AND "
        "(ii) point ≤ α + 2·√(α(1−α)/M). The former advisory label "
        "SIZE_EXCEEDS_POINT is retired (V2 §3.3); a point exceedance is now gated."
    )

    harsh = _null_cell_records(0, 100, 10)
    _, mout_bad = _run_p0_summary(tmp_path / "harsh", harsh)
    bad = mout_bad.read_text()
    bad_lines = bad.splitlines()
    table1 = bad.split("## Table 1 Size (δ = 0)")[1].split("## Table 2 Power")[0]
    hdr = next(ln for ln in table1.splitlines() if ln.startswith("| cell |"))
    assert [c.strip() for c in hdr.strip().strip("|").split("|")] == expected_header
    assert hdr in table1
    # the retirement line sits directly under the table
    rule_idx = bad_lines.index(retirement_line)
    assert bad_lines[rule_idx - 1].startswith("|")
    assert bad.count("SIZE_EXCEEDS_POINT") == 1
    assert "Size verdict: NOT SIZED" in bad
    assert re.search(
        r"\|\s*10/100\s*\|\s*0\.100\s*\|\s*0\.055\s*\|\s*0\.056\s*\|"
        r"\s*no\s*\|\s*no\s*\|\s*SIZE_VIOLATION\s*\|",
        bad,
    )
    bullet = next(
        ln
        for ln in bad_lines
        if ln.startswith("- cell 0") and "defensive_sector/H1" in ln
    )
    for fragment in (
        "10/100",
        "point 0.100",
        "Wilson 95 % lower 0.055",
        "envelope 0.056",
        "SIZE_VIOLATION",
    ):
        assert fragment in bullet, fragment

    mild = _null_cell_records(0, 100, 3)
    _, mout_mild = _run_p0_summary(tmp_path / "mild", mild)
    mild_md = mout_mild.read_text()
    assert retirement_line in mild_md.splitlines()
    assert mild_md.count("SIZE_EXCEEDS_POINT") == 1
    assert "Size verdict: SIZED" in mild_md
    assert "Size verdict: NOT SIZED" not in mild_md
    assert re.search(
        r"\|\s*3/100\s*\|\s*0\.030\s*\|\s*0\.010\s*\|\s*0\.056\s*\|"
        r"\s*yes\s*\|\s*yes\s*\|\s*SIZED\s*\|",
        mild_md,
    )


# MUTATION: scripts/leadership_rotation_p0.py:911 use f"numpy {np.__version__}" for host line
def test_summary_md_summary_host_line(tmp_path: Path):
    recs = _null_cell_records(0, 2, 0)
    _, mout = _run_p0_summary(tmp_path, recs)
    md = mout.read_text()
    host_line = next(ln for ln in md.splitlines() if "numpy" in ln and "summary host" in ln)
    assert host_line.startswith("summary host: numpy ")


# MUTATION: scripts/leadership_rotation_p0.py:601 allow unknown cell_id
def test_load_sim_records_unknown_cell_id(tmp_path: Path):
    bad = {"cell_id": 999, "k": 0, "status": "UNREACHED"}
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="unknown cell_id"):
        load_sim_records([p])


# --- prereg V2 harness repair: exact cached honest-N search (speed only) ---


# MUTATION: scripts/leadership_rotation_p0.py _fast_honest_n_group drop ep.merge_within_pair
# MUTATION: scripts/leadership_rotation_p0.py _PairPre.s0 replace max(int(start), self.fe) with int(start)
def test_fast_honest_n_and_window_identical_to_slow():
    from scripts import leadership_rotation_p0 as p0

    groups, truth = simulate_family(
        0.007, 0.0, 0.5, 252 * 2, np.random.SeedSequence([7, 7, 1])
    )
    pre = p0._family_pre(groups)
    last = truth["n"] - TAIL - 1
    ends = sorted(set(np.linspace(st.WARMUP, last, 3).astype(int).tolist()))
    for e in ends:
        for g in ("defensive_sector", "broadening_proxy"):
            for h in ("H1", "H2", "H3"):
                slow = p0._honest_n_group(groups[g], h, st.WARMUP, e)
                fast = p0._honest_n_group(groups[g], h, st.WARMUP, e, pres=pre[g])
                assert slow == fast, (e, g, h, slow, fast)
    for h in ("H1", "H2", "H3"):
        assert window_for_target(groups, 3, h) == window_for_target(groups, 3, h, pre)


# MUTATION: scripts/leadership_rotation_p0.py _pick_formation return ends from a re-simulated path with seed+1
def test_pick_formation_reuses_identical_groups_and_ends():
    from scripts import leadership_rotation_p0 as p0

    seed = np.random.SeedSequence([7, 7, 2])

    def groups_fn(nf):
        return simulate_family(0.007, 0.0, 0.5, nf, seed)

    nf, groups, truth, ends = p0._pick_formation(groups_fn, 3)
    again, _ = simulate_family(0.007, 0.0, 0.5, nf, seed)
    assert np.array_equal(
        groups["defensive_sector"][0].num, again["defensive_sector"][0].num
    )
    pre = p0._family_pre(again)
    for h in ("H1", "H2", "H3"):
        assert ends[h] == window_for_target(again, 3, h, pre)
    assert p0._pick_n_formation(groups_fn, 3) == nf


def test_formation_years_extension_preserves_v1_prefix():
    from scripts import leadership_rotation_p0 as p0

    assert p0._FORMATION_YEARS[:7] == (4, 8, 12, 16, 24, 32, 48)
    assert max(p0._FORMATION_YEARS) >= 64
    assert list(p0._FORMATION_YEARS) == sorted(set(p0._FORMATION_YEARS))


# --- prereg V2 §3.3 two-part size rule: new coverage ------------------------


def _size_cell(
    cell_id: int,
    m: int,
    passes: int,
    *,
    row: str = "defensive_sector/H1",
    stored_rate: float | None = None,
    stored_lower: float | None = None,
    sigma: float = 0.007,
    rho: float = 0.5,
    n_target: int = 20,
    include_family: bool = False,
    family: tuple[int, int] = (0, 100),
) -> dict:
    """Hand-built δ = 0 cell in the shape `_summarize_cell` emits."""
    rate = stored_rate if stored_rate is not None else (
        passes / m if m else float("nan")
    )
    lower = stored_lower if stored_lower is not None else (
        wilson_interval(passes, m)[0] if m else float("nan")
    )
    summary: dict = {
        "by_group_hypothesis": {
            row: {
                "passes": passes,
                "n_ok": m,
                "pass_rate_ok": rate,
                "wilson_95_ok": {"lower": lower, "upper": 1.0},
            }
        }
    }
    if include_family:
        fam_passes, fam_m = family
        summary["family_any"] = {
            "passes": fam_passes,
            "n_ok": fam_m,
            "pass_rate_ok": fam_passes / fam_m if fam_m else float("nan"),
            "wilson_95_ok": {
                "lower": (
                    wilson_interval(fam_passes, fam_m)[0] if fam_m else float("nan")
                ),
                "upper": 1.0,
            },
        }
    return {
        "delta": 0.0,
        "cell_id": cell_id,
        "sigma": sigma,
        "rho": rho,
        "n_target": n_target,
        "n_sims": m,
        "n_ok": m,
        "summary": summary,
    }


def _size_row(result: dict, name: str = "defensive_sector/H1") -> dict:
    return next(r for r in result["rows"] if r["row"] == name)


# MUTATION: scripts/leadership_rotation_p0.py:788 drop the part_ii_ok conjunct (T11 gate)
def test_size_two_part_rejects_constructed_row_the_t11_gate_accepted():
    # CONSTRUCTED: stored Wilson lower deliberately inconsistent with the counts; a
    # real count-consistent row cannot separate the gates (see T12R)
    cells = [_size_cell(0, 400, 17, stored_rate=0.0425, stored_lower=0.024)]

    def _t11_gate_sized(cell_summaries: list[dict], alpha: float = 0.025) -> bool:
        """The retired T11 rule verbatim: violation iff the STORED lower bound > α."""
        for cell in cell_summaries:
            if float(cell.get("delta", float("nan"))) != 0.0:
                continue
            summary = cell.get("summary", {})
            entries = list(summary.get("by_group_hypothesis", {}).items())
            fam = summary.get("family_any")
            if isinstance(fam, dict):
                entries.append(("family_any", fam))
            for _name, row in entries:
                stored = row.get("wilson_95_ok", {}).get("lower", float("nan"))
                if float(stored) > alpha:
                    return False
        return True

    assert _t11_gate_sized(cells) is True

    result = size_check(cells)
    row = _size_row(result)
    assert row["flag"] == "SIZE_VIOLATION"
    assert row["part_i_ok"] is True
    assert row["part_ii_ok"] is False
    assert result["sized"] is False
    assert [v["row"] for v in result["violations"]] == ["defensive_sector/H1"]


def _t11_gate_sized_verbatim(cell_summaries: list[dict], alpha: float = 0.025) -> bool:
    """The retired T11 rule: violation iff a δ = 0 row's STORED Wilson lower > α."""
    for cell in cell_summaries:
        if float(cell.get("delta", float("nan"))) != 0.0:
            continue
        summary = cell.get("summary", {})
        entries = list(summary.get("by_group_hypothesis", {}).items())
        fam = summary.get("family_any")
        if isinstance(fam, dict):
            entries.append(("family_any", fam))
        for _name, row in entries:
            stored = row.get("wilson_95_ok", {}).get("lower", float("nan"))
            if float(stored) > alpha:
                return False
    return True


def test_size_gate_refuses_count_consistent_t12_shape_the_t11_gate_accepted():
    # COUNT-CONSISTENT (no stored-field tampering): the T12 run shape — thin M per
    # δ = 0 cell and cell 2 UNREACHED (n_ok = 0). The T11 rule calls this SIZED
    # (a NaN lower bound is never > α); the V2 §3 gate refuses it as not executable.
    cells = [
        _size_cell(0, 100, 2),
        _size_cell(1, 100, 2, n_target=40),
        _size_cell(2, 0, 0, n_target=80),
        _size_cell(3, 42, 1, rho=0.8),
        _size_cell(4, 42, 1, rho=0.8, n_target=40),
        _size_cell(48, 79, 1, sigma=0.014),
    ]
    assert _t11_gate_sized_verbatim(cells) is True

    result = size_check(cells, min_m=400, required_cells=[0, 1, 2, 3, 4, 48])
    assert result["sized"] is False
    assert result["violations"] == []
    assert result["missing_cells"] == []
    flagged = {r["cell_id"]: r["flag"] for r in result["rows"]}
    assert set(flagged) == {0, 1, 2, 3, 4, 48}
    assert set(flagged.values()) == {"SIZE_NOT_EXECUTABLE"}
    # without the M floor, cell 2's zero OK sims alone still refuse the set (V2.1 §5 F2)
    assert size_check(cells)["sized"] is False


# MUTATION: scripts/leadership_rotation_p0.py:784 envelope as alpha + 1/sqrt(m) (R-H1-3)
def test_size_envelope_values():
    at_400 = _size_row(size_check([_size_cell(0, 400, 0)]))["envelope"]
    at_100 = _size_row(size_check([_size_cell(1, 100, 0)]))["envelope"]
    assert abs(at_400 - 0.040612) < 5e-5
    assert abs(at_100 - 0.056225) < 5e-5


# MUTATION: scripts/leadership_rotation_p0.py:787 use strict < in part_i_ok
def test_size_count_consistent_boundaries():
    cases = [
        (400, 16, "SIZED", True, True),
        (400, 17, "SIZE_VIOLATION", False, False),
        (100, 5, "SIZED", True, True),
        (100, 6, "SIZE_VIOLATION", False, False),
    ]
    for m, passes, flag, part_i, part_ii in cases:
        result = size_check([_size_cell(0, m, passes)])
        row = _size_row(result)
        assert row["flag"] == flag, (m, passes, row)
        assert row["part_i_ok"] is part_i, (m, passes, row)
        assert row["part_ii_ok"] is part_ii, (m, passes, row)
        assert row["wilson_lower"] == pytest.approx(wilson_interval(passes, m)[0])
        assert row["pass_rate_ok"] == pytest.approx(passes / m)
        assert result["sized"] is (flag == "SIZED"), (m, passes, result)


# MUTATION: scripts/leadership_rotation_p0.py:803 drop the family_any flag branch
def test_size_family_row_flag():
    result = size_check(
        [_size_cell(0, 100, 0, include_family=True, family=(10, 100))]
    )
    fam = _size_row(result, "family_any")
    assert fam["flag"] == "FAMILY_SIZE_VIOLATION"
    assert fam["passes"] == 10 and fam["m"] == 100
    assert fam["part_i_ok"] is False and fam["part_ii_ok"] is False
    assert result["sized"] is False
    assert result["max_family_point_rate_ok"] == pytest.approx(0.10)
    assert result["max_point_rate_ok"] == pytest.approx(0.0)
    assert _size_row(result)["flag"] == "SIZED"


# MUTATION: scripts/leadership_rotation_p0.py:799 ignore min_m and the m == 0 branch
def test_size_not_executable_zero_ok_and_min_m():
    zero = size_check([_size_cell(2, 0, 0)])
    zero_row = _size_row(zero)
    assert zero_row["flag"] == "SIZE_NOT_EXECUTABLE"
    assert zero["sized"] is False
    assert zero["violations"] == []
    assert [r["row"] for r in zero["not_executable"]] == ["defensive_sector/H1"]
    assert zero_row["m"] == 0
    assert zero_row["pass_rate_ok"] is None
    assert zero_row["wilson_lower"] is None
    assert zero_row["envelope"] is None
    assert zero_row["part_i_ok"] is None
    assert zero_row["part_ii_ok"] is None

    thin = size_check([_size_cell(0, 100, 2)], min_m=400)
    thin_row = _size_row(thin)
    assert thin_row["flag"] == "SIZE_NOT_EXECUTABLE"
    assert thin["sized"] is False
    assert thin["violations"] == []
    assert thin["min_m"] == 400
    assert [r["row"] for r in thin["not_executable"]] == ["defensive_sector/H1"]
    # both parts pass on the counts; only the sim budget makes it non-executable
    assert thin_row["part_i_ok"] is True and thin_row["part_ii_ok"] is True
    assert size_check([_size_cell(0, 100, 2)])["sized"] is True


# MUTATION: scripts/leadership_rotation_p0.py:834 always return missing_cells = []
def test_size_required_cells_missing():
    result = size_check([_size_cell(0, 100, 1)], required_cells=[0, 2])
    assert result["missing_cells"] == [2]
    assert result["required_cells"] == [0, 2]
    assert result["sized"] is False
    assert result["violations"] == []
    assert result["not_executable"] == []

    complete = size_check(
        [_size_cell(0, 100, 1), _size_cell(2, 100, 1, n_target=80)],
        required_cells=[2, 0],
    )
    assert complete["missing_cells"] == []
    assert complete["required_cells"] == [0, 2]
    assert complete["sized"] is True
    assert size_check([_size_cell(0, 100, 1)])["required_cells"] is None


# MUTATION: scripts/leadership_rotation_p0.py:815 emit the retired n_ok key, drop envelope
def test_size_rows_carry_both_parts_and_m():
    cells = [
        _size_cell(0, 100, 3),
        _size_cell(1, 400, 17, n_target=40, include_family=True, family=(9, 400)),
    ]
    result = size_check(cells, required_cells=[0, 1])
    expected_keys = {
        "cell_id",
        "sigma",
        "rho",
        "n_target",
        "n_sims",
        "row",
        "passes",
        "m",
        "pass_rate_ok",
        "wilson_lower",
        "envelope",
        "part_i_ok",
        "part_ii_ok",
        "flag",
    }
    assert len(expected_keys) == 14
    assert len(result["rows"]) == 3
    assert result["n_null_cells"] == 2
    assert result["n_null_sims"] == 500
    assert result["n_null_ok"] == 500
    by_id = {c["cell_id"]: c for c in cells}

    def _source_row(cell: dict, name: str) -> dict:
        if name == "family_any":
            return cell["summary"]["family_any"]
        return cell["summary"]["by_group_hypothesis"][name]

    for row in result["rows"]:
        assert set(row) == expected_keys, sorted(set(row) ^ expected_keys)
        src_row = _source_row(by_id[row["cell_id"]], row["row"])
        assert row["m"] == src_row["n_ok"]
        assert row["passes"] == src_row["passes"]
        assert row["n_sims"] == by_id[row["cell_id"]]["n_sims"]

    assert _size_row(result)["flag"] == "SIZED"
    assert _size_row(result, "defensive_sector/H1")["cell_id"] == 0
    cell1 = [r for r in result["rows"] if r["cell_id"] == 1]
    assert {r["row"]: r["flag"] for r in cell1} == {
        "defensive_sector/H1": "SIZE_VIOLATION",
        "family_any": "SIZED",
    }


_PER_ARM_KEYS = (
    "A0_raw_burden",
    "A0_burden",
    "A1_burden",
    "A1_median_delay",
    "A1_detection",
    "A2_median_delay",
)
_C2_STRATA = ("both_up", "both_down", "mixed", "unmeasured")


def _c2_block(hyp: str, *, n: int, status: str, point: float | None,
              reason: str | None = None) -> dict:
    """One frozen-shape c2_strata[stratum] entry (structure owned by the C2 lane)."""
    entry: dict = {"n_items": n + 1, "n": n, "status": status, "reason": reason}
    if hyp == "H1":
        entry["delay_reduction"] = point
        entry["burden_cut_b"] = point
    else:
        entry["point"] = point
        entry["comparator_basis"] = "B2"
    return entry


def _c2_strata(hyp: str, *, n: int, status: str, point: float | None) -> dict:
    return {
        s: _c2_block(hyp, n=n, status=status, point=point) for s in _C2_STRATA
    }


# MUTATION: scripts/leadership_rotation_p0.py:_extract_sim_metrics read A0_raw_burden
# from h1["A0"] (or pass a non-finite per-arm value through, or drop c2_strata).
def test_extract_sim_metrics_per_arm_and_c2_carried():
    from scripts.leadership_rotation_p0 import (
        _GROUPS,
        _HYPOTHESES,
        _extract_sim_metrics,
    )

    ends = {"H1": 2000, "H2": 2000, "H3": 2000}
    order = [(g, h) for g in _GROUPS for h in _HYPOTHESES]
    fam: dict = {
        "holm": {"order": order, "raw": [0.5] * len(order), "adjusted": [0.9] * len(order)},
        "groups": {},
        "verdicts": {},
    }

    g0, g1 = _GROUPS[0], _GROUPS[1]
    c2_g0 = {h: _c2_strata(h, n=9, status="COMPUTED", point=0.1) for h in _HYPOTHESES}
    fam["groups"][g0] = {
        "honest_n": {h: 20 for h in _HYPOTHESES},
        "c2_strata": c2_g0,
        "H1": {
            "delay_reduction": 0.01,
            "p": 0.4,
            "burden_cut_b": 0.2,
            "decision": {"cond_a": False, "cond_b": True, "p_h1": 0.4},
            "A0_raw": {"burden": 11.25},
            "A0": {"burden": 5.0},
            "A1": {"burden": float("nan"), "median_delay": 3.0, "detection": 0.75},
            "A2": {"median_delay": 8.0},
        },
        "H2": {"point": 0.02, "p": 0.3},
        "H3": {"point": 0.03, "p": 0.2},
    }
    fam["groups"][g1] = {
        "honest_n": {h: 10 for h in _HYPOTHESES},
        "H1": {
            "delay_reduction": 0.0,
            "p": 0.5,
            "burden_cut_b": 0.0,
            "decision": {"cond_a": False, "cond_b": False, "p_h1": 0.5},
        },
        "H2": {"point": 0.0, "p": 0.5},
        "H3": {"point": 0.0, "p": 0.5},
    }
    for g in _GROUPS:
        fam["verdicts"][g] = {h: "DEVELOPMENT_FAIL" for h in _HYPOTHESES}

    out = _extract_sim_metrics(fam, ends)

    per_arm = out[g0]["H1"]["per_arm"]
    assert tuple(per_arm) == _PER_ARM_KEYS
    assert per_arm["A0_raw_burden"] == 11.25
    assert per_arm["A0_burden"] == 5.0
    assert per_arm["A1_burden"] is None  # NaN -> None, never a filled fake value
    assert per_arm["A1_median_delay"] == 3.0
    assert per_arm["A1_detection"] == 0.75
    assert per_arm["A2_median_delay"] == 8.0

    assert "per_arm" not in out[g0]["H2"] and "per_arm" not in out[g0]["H3"]

    # missing arm metric dicts -> keys present, every value None (unmeasured != zero)
    bare = out[g1]["H1"]["per_arm"]
    assert tuple(bare) == _PER_ARM_KEYS
    assert all(v is None for v in bare.values())

    # C2 carried VERBATIM (identical object) for every (g, h); None when absent
    for h in _HYPOTHESES:
        assert out[g0][h]["c2_strata"] is c2_g0[h]
        assert out[g1][h]["c2_strata"] is None


# MUTATION: scripts/leadership_rotation_p0.py:_summarize_cell average per_arm /
# c2_strata over all sims instead of OK sims only, or flatten the strata dict.
def test_summarize_cell_per_arm_medians_and_c2_summary():
    from scripts.leadership_rotation_p0 import _GROUPS, _HYPOTHESES, _summarize_cell

    def _ok_rec(k: int) -> dict:
        groups: dict = {}
        for g in _GROUPS:
            groups[g] = {}
            for h in _HYPOTHESES:
                row: dict = {
                    "verdict": "DEVELOPMENT_FAIL",
                    "honest_n": 20,
                    "window_years": 4.0,
                    "point": 0.01,
                    "raw_p": 0.5,
                    "holm_p": 0.9,
                }
                if h == "H1":
                    row["iut"] = {
                        "cond_a": False,
                        "cond_b": False,
                        "p_h1": 0.5,
                        "delay_reduction": 0.01,
                        "burden_cut_b": 0.02,
                    }
                    row["per_arm"] = {
                        "A0_raw_burden": 1.0 + 2.0 * k,  # 1, 3, 5 -> 3
                        "A0_burden": 2.0,
                        "A1_burden": None if k == 1 else 4.0,  # 4, 4 -> 4
                        "A1_median_delay": float(k),  # 0, 1, 2 -> 1
                        "A1_detection": 0.5,
                        "A2_median_delay": float("nan"),  # non-finite -> None
                    }
                    strata = _c2_strata("H1", n=9, status="COMPUTED", point=0.1)
                    strata["both_up"]["n"] = 4 + 2 * k  # 4, 6, 8 -> 6
                    strata["both_up"]["delay_reduction"] = 0.1 * (k + 1)  # -> 0.2
                    strata["both_up"]["burden_cut_b"] = 0.25
                    strata["both_down"]["status"] = "SOURCE_LIMITED" if k == 2 else "COMPUTED"
                    strata["unmeasured"] = _c2_block(
                        "H1", n=0, status="UNMEASURED", point=None, reason="no items"
                    )
                else:
                    strata = _c2_strata(h, n=7, status="COMPUTED", point=0.5)
                row["c2_strata"] = strata
                groups[g][h] = row
        return {"cell_id": 0, "k": k, "status": "OK", "groups": groups}

    sims = [_ok_rec(0), _ok_rec(1), _ok_rec(2), {"cell_id": 0, "k": 3, "status": "UNREACHED"}]
    summary = _summarize_cell(sims)
    row_h1 = summary["by_group_hypothesis"]["defensive_sector/H1"]

    assert row_h1["per_arm_n"] == 3  # the UNREACHED sim carries no per_arm
    med = row_h1["per_arm_median"]
    assert tuple(med) == _PER_ARM_KEYS
    assert med["A0_raw_burden"] == 3.0
    assert med["A0_burden"] == 2.0
    assert med["A1_burden"] == 4.0
    assert med["A1_median_delay"] == 1.0
    assert med["A1_detection"] == 0.5
    assert med["A2_median_delay"] is None

    c2 = row_h1["c2_summary"]
    assert tuple(c2) == _C2_STRATA
    both_up = c2["both_up"]
    assert both_up["status_counts"] == {"COMPUTED": 3}
    assert both_up["median_n"] == 6.0
    assert both_up["median_delay_reduction"] == pytest.approx(0.2)
    assert both_up["median_burden_cut_b"] == 0.25
    assert both_up["n_sims"] == 3
    assert c2["both_down"]["status_counts"] == {"COMPUTED": 2, "SOURCE_LIMITED": 1}
    assert c2["unmeasured"]["status_counts"] == {"UNMEASURED": 3}
    assert c2["unmeasured"]["median_n"] == 0.0
    assert c2["unmeasured"]["median_delay_reduction"] is None

    row_h2 = summary["by_group_hypothesis"]["defensive_sector/H2"]
    assert "per_arm_median" not in row_h2 and "per_arm_n" not in row_h2
    assert row_h2["c2_summary"]["both_up"]["median_point"] == 0.5

    # no OK sim carries c2 -> c2_summary is None on every row (never a zero-filled dict)
    bare = [{
        "cell_id": 0,
        "k": 0,
        "status": "OK",
        "groups": {
            g: {h: {"verdict": "DEVELOPMENT_FAIL", "honest_n": 5, "window_years": 4.0,
                    "point": 0.0, "raw_p": 0.5, "holm_p": 0.9} for h in _HYPOTHESES}
            for g in _GROUPS
        },
    }]
    bare_summary = _summarize_cell(bare)
    for rk, row in bare_summary["by_group_hypothesis"].items():
        assert row["c2_summary"] is None, rk


# MUTATION: scripts/leadership_rotation_p0.py:_write_summary_md omit Table 5/Table 6,
# or print the Table 6 grid when every c2_summary is None.
def test_summary_md_tables_5_and_6(tmp_path: Path):
    from scripts.leadership_rotation_p0 import _GROUPS, _HYPOTHESES

    t5_head = "## Table 5 Per-arm metrics (prereg V2 §3.4)"
    t6_head = "## Table 6 C2 direction strata (prereg V2 §6)"
    t5_note = (
        'Medians over OK sims. "A0 raw" = A0 fires before the 5-quiet-session '
        "suppression, through the same window filter, merge and classifier as A0 "
        '("suppressed"); burden = REPEATED + LATE + FALSE_START per measured pair-year.'
    )
    t6_note = (
        "Prereg V2 §6 direction stratification (CHAL GATES #2); NOT the sealed "
        "Trend-Persistence-era study also called 'C2', which stays closed."
    )
    absent = "_C2 strata absent from the input records (producer predates prereg V2 §6)._"

    # ---- records WITH c2_strata + per_arm -------------------------------
    recs = _null_cell_records(0, 3, 0) + _null_cell_records(6, 2, 0)
    for rec in recs:
        if rec.get("status") != "OK":
            continue
        for g in _GROUPS:
            for h in _HYPOTHESES:
                rec["groups"][g][h]["c2_strata"] = _c2_strata(
                    h, n=9, status="COMPUTED", point=0.1
                )
            rec["groups"][g]["H1"]["per_arm"] = {
                "A0_raw_burden": 11.25,
                "A0_burden": 5.0,
                "A1_burden": 4.0,
                "A1_median_delay": 3.0,
                "A1_detection": 0.75,
                "A2_median_delay": 8.0,
            }
    _, mout = _run_p0_summary(tmp_path / "with_c2", recs)
    md = mout.read_text()

    assert t5_head in md and t5_note in md
    t5 = md.split(t5_head)[1].split(t6_head)[0]
    data_rows = [ln for ln in t5.splitlines() if re.match(r"^\| \d+ \|", ln)]
    assert len(data_rows) == 2 * len(_GROUPS)  # one row per (cell, group), δ = 0 and δ > 0
    assert "| 6 | 0.007 | 0.003 | 0.500 | 20 | defensive_sector | 11.250 | 5.000 | 4.000 | 3.000 | 0.750 | 8.000 | 2 |" in t5

    assert t6_head in md and t6_note in md
    t6 = md.split(t6_head)[1]
    assert absent not in t6
    assert "| cell | row | stratum | sims | status counts | median n | median point(s) |" in t6
    t6_rows = [ln for ln in t6.splitlines() if re.match(r"^\| \d+ \|", ln)]
    assert len(t6_rows) == 2 * len(_GROUPS) * len(_HYPOTHESES) * len(_C2_STRATA)
    assert "| defensive_sector/H1 | both_up | 3 | COMPUTED: 3 | 9.000 | 0.100 / 0.100 |" in t6
    assert "| defensive_sector/H2 | both_up | 3 | COMPUTED: 3 | 9.000 | 0.100 |" in t6

    # ---- records WITHOUT c2 (producer predates §6) ----------------------
    plain = _null_cell_records(0, 2, 0)
    _, mout2 = _run_p0_summary(tmp_path / "no_c2", plain)
    md2 = mout2.read_text()
    assert t5_head in md2  # Table 5 is printed for every input, em-dashes when unmeasured
    t5_2 = md2.split(t5_head)[1].split(t6_head)[0]
    assert len([ln for ln in t5_2.splitlines() if re.match(r"^\| \d+ \|", ln)]) == len(_GROUPS)
    assert "| 0 | 0.007 | 0.000 | 0.500 | 20 | broadening_proxy | — | — | — | — | — | — | 0 |" in t5_2
    assert t6_head in md2 and absent in md2
    t6_2 = md2.split(t6_head)[1]
    assert "| cell | row | stratum |" not in t6_2


# ---------------------------------------------------------------------------
# LR-REP-5 — prereg V2 §4 G2 positive-control catalog, §3.2 k-range split, the
# §3.6 size-gate artifact and the §4.3/§4.4 power disposition. Synthetic records
# and throw-away tmp_path git repos only; no test here runs a real simulation.
# ---------------------------------------------------------------------------

_ALL_PASS_PATHS = {
    (g, h)
    for g in ("defensive_sector", "broadening_proxy")
    for h in ("H1", "H2", "H3")
}
# prereg V2 §4.3 slot set: G2 cells with δ ≤ 4.0 % AND N ≤ 40
_G2_ELIGIBLE = (100, 101, 103, 104, 106, 107)
_H1_POWER_LABEL = (
    "H1: same arithmetic as V2 §4.3, reported for information; "
    "the §4.3 rule is written for H2/H3"
)
_ARTIFACT_KEYS = {
    "schema",
    "rule",
    "alpha",
    "sized",
    "min_m",
    "required_cells",
    "cells",
    "rows",
    "violations",
    "not_executable",
    "missing_cells",
    "h1_null_method",
    "h1_null_k",
    "prereg",
    "harness",
    "inputs",
    "generated_utc",
}
_SIZE_ROW_KEYS = {
    "cell_id",
    "sigma",
    "rho",
    "n_target",
    "n_sims",
    "row",
    "passes",
    "m",
    "pass_rate_ok",
    "wilson_lower",
    "envelope",
    "part_i_ok",
    "part_ii_ok",
    "flag",
}
_CURVE_KEYS = {
    "generator",
    "cell_id",
    "sigma",
    "delta",
    "rho",
    "n_target",
    "row",
    "passes",
    "m",
    "pass_rate_ok",
    "wilson_lower",
    "wilson_upper",
    "below_min_m",
}


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _tmp_harness_repo(root: Path) -> Path:
    """Throw-away git repo holding byte copies of the real HARNESS_MODULES."""
    from scripts.leadership_rotation_run import HARNESS_MODULES

    real_root = Path(__file__).resolve().parents[1]
    repo = root / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", str(repo)], check=True, capture_output=True, text=True
    )
    for rel in HARNESS_MODULES:
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((real_root / rel).read_bytes())
    _git(repo, "add", "--", *HARNESS_MODULES)
    _git(repo, "commit", "-q", "-m", "harness bytes under test")
    return repo


def _stamped(records: list[dict], harness_id: str) -> list[dict]:
    for rec in records:
        rec["harness_id"] = harness_id
    return records


def _power_cell(cell_id: int, rows: dict[str, tuple[int, int]]) -> dict:
    """Hand-built cell in the shape `_summarize_cell` emits (params from catalog)."""
    from scripts.leadership_rotation_p0 import _catalog_map

    sigma, delta, rho, n_target = _catalog_map()[cell_id]
    by_gh: dict = {}
    family: dict | None = None
    for name, (passes, m) in rows.items():
        lo, hi = wilson_interval(passes, m) if m else (None, None)
        row = {
            "passes": passes,
            "n_ok": m,
            "pass_rate_ok": passes / m if m else float("nan"),
            "wilson_95_ok": {"lower": lo, "upper": hi},
        }
        if name == "family_any":
            family = row
        else:
            by_gh[name] = row
    summary: dict = {"by_group_hypothesis": by_gh}
    if family is not None:
        summary["family_any"] = family
    n_sims = max([m for _, m in rows.values()], default=0)
    return {
        "cell_id": cell_id,
        "sigma": sigma,
        "delta": delta,
        "rho": rho,
        "n_target": n_target,
        "n_sims": n_sims,
        "n_ok": n_sims,
        "summary": summary,
    }


# MUTATION: scripts/leadership_rotation_p0.py:_iter_g2_cells use cid = G2_CELL_ID_BASE + n_idx * len(G2_DELTAS) + d_idx (transposed id grid)
def test_g2_catalog_ids_params_and_validation():
    from scripts.leadership_rotation_p0 import (
        G2_CELL_ID_BASE,
        G2_CELL_IDS,
        G2_DELTAS,
        G2_N_TARGETS,
        G2_RHO,
        G2_SIGMA,
        _catalog_map,
        _iter_g2_cells,
        _iter_grid_cells,
        _validate_sim_record,
    )

    g1 = _iter_grid_cells()
    g2 = _iter_g2_cells()
    catalog = _catalog_map()

    assert [c[0] for c in g1] == list(range(72))
    assert G2_CELL_ID_BASE == 100
    assert G2_SIGMA == 0.007 and G2_RHO == 0.5
    assert G2_DELTAS == (0.01, 0.02, 0.04, 0.08)
    assert G2_N_TARGETS == (20, 40, 80)
    assert G2_CELL_IDS == tuple(range(100, 112))
    assert [c[0] for c in g2] == list(G2_CELL_IDS)
    # ids are disjoint from G1 and the union is the whole catalog
    assert set(catalog) == set(range(72)) | set(range(100, 112))
    assert len(catalog) == 84
    for cid, sigma, delta, rho, n_target in g1:
        assert catalog[cid] == (sigma, delta, rho, n_target)
    for cid, sigma, delta, rho, n_target in g2:
        assert catalog[cid] == (sigma, delta, rho, n_target)
    assert catalog[100] == (0.007, 0.01, 0.5, 20)
    assert catalog[104] == (0.007, 0.02, 0.5, 40)
    assert catalog[111] == (0.007, 0.08, 0.5, 80)

    _validate_sim_record({"cell_id": 105, "k": 0, "status": "OK"}, catalog)
    _validate_sim_record(
        {
            "cell_id": 105,
            "k": 3,
            "status": "UNREACHED",
            "harness_id": "a" * 64,
            "h1_null_method": "V2_OPTION_A",
        },
        catalog,
    )
    for bad_k in (0, -1, True, 1.5, "1000"):
        with pytest.raises(ValueError, match="invalid h1_null_k"):
            _validate_sim_record({"cell_id": 105, "k": 0, "status": "OK", "h1_null_k": bad_k}, catalog)
    with pytest.raises(ValueError, match="unknown cell_id 72"):
        _validate_sim_record({"cell_id": 72, "k": 0, "status": "OK"}, catalog)
    with pytest.raises(ValueError, match="unknown cell_id 112"):
        _validate_sim_record({"cell_id": 112, "k": 0, "status": "OK"}, catalog)
    with pytest.raises(ValueError, match="invalid harness_id"):
        _validate_sim_record(
            {"cell_id": 105, "k": 0, "status": "OK", "harness_id": "xyz"}, catalog
        )
    with pytest.raises(ValueError, match="invalid harness_id"):
        _validate_sim_record(
            {"cell_id": 105, "k": 0, "status": "OK", "harness_id": "A" * 64}, catalog
        )
    with pytest.raises(ValueError, match="invalid h1_null_method"):
        _validate_sim_record(
            {"cell_id": 105, "k": 0, "status": "OK", "h1_null_method": ""}, catalog
        )


# MUTATION: scripts/leadership_rotation_p0.py:grid keep filtering an explicit id list against _iter_grid_cells() only, so G2 ids silently select nothing
def test_grid_selects_g2_and_rejects_unknown_ids(monkeypatch):
    from scripts import leadership_rotation_p0 as p0

    calls: list[tuple] = []

    def _fake_run_cell(sigma, delta, rho, n_target, sims, **kw):
        calls.append((sigma, delta, rho, n_target, sims, kw))
        return {"cell_id": kw["cell_id"], "sims": sims}

    monkeypatch.setattr(p0, "run_cell", _fake_run_cell)

    p0.grid(cells="g2", sims_null=7, sims_alt=3, k_start=5)
    assert [c[5]["cell_id"] for c in calls] == list(range(100, 112))
    assert all(c[4] == 3 for c in calls)  # every G2 cell has δ > 0 → sims_alt
    assert all(c[5]["k_start"] == 5 for c in calls)
    assert calls[0][:4] == (0.007, 0.01, 0.5, 20)
    assert calls[4][:4] == (0.007, 0.02, 0.5, 40)
    assert calls[-1][:4] == (0.007, 0.08, 0.5, 80)

    calls.clear()
    p0.grid(cells="all", sims_null=7, sims_alt=3)
    assert [c[5]["cell_id"] for c in calls] == list(range(72))
    assert all(c[5]["k_start"] == 0 for c in calls)
    # G1 ids 0–5 are the δ = 0 cells at σ 0.70 %; id 6 is the first δ > 0 cell
    assert calls[0][4] == 7 and calls[5][4] == 7
    assert calls[6][4] == 3 and calls[71][4] == 3

    calls.clear()
    p0.grid(cells=[104, 0, 104], sims_null=2, sims_alt=1, k_start=400)
    assert [c[5]["cell_id"] for c in calls] == [0, 104]  # ascending, de-duplicated
    assert calls[0][4] == 2 and calls[1][4] == 1
    assert all(c[5]["k_start"] == 400 for c in calls)

    calls.clear()
    with pytest.raises(ValueError, match="unknown cell id 999"):
        p0.grid(cells=[999])
    with pytest.raises(ValueError, match="unknown cell id 72"):
        p0.grid(cells=[0, 72])
    assert calls == []  # selection is validated before any cell is run


# MUTATION: scripts/leadership_rotation_p0.py:run_cell keep pending = range(sims) and read back every record of the cell regardless of k_start
def test_run_cell_k_start_range_and_harness_stamp(tmp_path: Path, monkeypatch):
    from scripts import leadership_rotation_p0 as p0

    def _stub(sigma, delta, rho, n_target, cell_id, k):
        return {
            "cell_id": cell_id,
            "k": k,
            "status": "UNREACHED",
            "n_formation": None,
        }

    monkeypatch.setattr(p0, "_run_one_sim", _stub)
    out = tmp_path / "sims.jsonl"

    first = p0.run_cell(0.007, 0.0, 0.5, 20, 3, cell_id=0, workers=1, out=out, k_start=5)
    assert [r["k"] for r in first["sim_records"]] == [5, 6, 7]

    second = p0.run_cell(0.007, 0.0, 0.5, 20, 2, cell_id=0, workers=1, out=out, k_start=0)
    assert [r["k"] for r in second["sim_records"]] == [0, 1]

    written = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert sorted(r["k"] for r in written) == [0, 1, 5, 6, 7]
    assert len(written) == 5  # the second call re-ran nothing already on disk

    runtime_id = p0._runtime_harness_id()
    assert re.fullmatch(r"[0-9a-f]{64}", runtime_id)
    assert all(r["harness_id"] == runtime_id for r in written)
    assert p0._runtime_harness_id() == runtime_id  # lru_cached for the process

    # a sibling cell in the same file is neither read back nor returned
    other = p0.run_cell(0.007, 0.0, 0.5, 20, 1, cell_id=1, workers=1, out=out, k_start=5)
    assert [r["k"] for r in other["sim_records"]] == [5]
    assert all(r["cell_id"] == 1 for r in other["sim_records"])

    with pytest.raises(ValueError, match="k_start"):
        p0.run_cell(0.007, 0.0, 0.5, 20, 1, cell_id=0, k_start=-1)


# MUTATION: scripts/leadership_rotation_p0.py:write_size_gate_artifact default h1_null_method to SIZE_GATE_H1_NULL_METHOD instead of reading it off the records
def test_size_out_writes_v1_artifact(tmp_path: Path, capsys):
    import hashlib

    from scripts.leadership_rotation_p0 import harness_identity, main
    from scripts.leadership_rotation_run import HARNESS_MODULES

    repo = _tmp_harness_repo(tmp_path)
    ident = harness_identity(repo)
    recs = _stamped(
        [
            _sim_record(cid, k, pass_paths=_ALL_PASS_PATHS if k < 5 else None)
            for cid in (0, 1, 2, 3, 4, 48)
            for k in range(400)
        ],
        ident["id"],
    )
    src = tmp_path / "sims.jsonl"
    _write_jsonl(src, recs)
    out = tmp_path / "art" / "size_gate.json"

    argv = [
        "size",
        "--in",
        str(src),
        "--min-m",
        "400",
        "--require-cells",
        "0,1,2,3,4,48",
        "--out",
        str(out),
        "--repo-root",
        str(repo),
    ]
    assert main(argv) == 0
    artifact = json.loads(out.read_text())

    assert set(artifact) == _ARTIFACT_KEYS
    assert artifact["schema"] == "leadership_rotation.size_gate.v1"
    assert artifact["rule"] == "V2_SEC3_TWO_PART"
    assert artifact["alpha"] == 0.025
    assert artifact["sized"] is True
    assert artifact["min_m"] == 400
    assert artifact["required_cells"] == [0, 1, 2, 3, 4, 48]
    assert artifact["violations"] == []
    assert artifact["not_executable"] == []
    assert artifact["missing_cells"] == []
    assert [c["cell_id"] for c in artifact["cells"]] == [0, 1, 2, 3, 4, 48]
    for cell in artifact["cells"]:
        assert set(cell) == {
            "cell_id",
            "sigma",
            "delta",
            "rho",
            "n_target",
            "n_sims",
            "n_ok",
        }
        assert cell["delta"] == 0.0 and cell["n_sims"] == 400 and cell["n_ok"] == 400
    assert len(artifact["rows"]) == 6 * 7
    assert all(set(row) == _SIZE_ROW_KEYS for row in artifact["rows"])

    assert artifact["harness"]["head"] == _git(repo, "rev-parse", "HEAD")
    assert set(artifact["harness"]["blobs"]) == set(HARNESS_MODULES)
    for rel in HARNESS_MODULES:
        assert artifact["harness"]["blobs"][rel] == _git(repo, "rev-parse", f"HEAD:{rel}")
    assert artifact["prereg"] == {
        "v1_blob": st.PREREG_BLOB_SHA,
        "v2_blob": st.PREREG_V2_BLOB_SHA,
        "v2_1_blob": st.PREREG_V2_1_BLOB_SHA,
    }
    assert artifact["h1_null_method"] == "V1_BOOTSTRAP_SUPERSEDED"

    data = src.read_bytes()
    assert artifact["inputs"]["files"] == [
        {
            "path": str(src),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    ]
    assert artifact["inputs"]["records"] == 2400
    assert artifact["inputs"]["duplicates"] == 0
    assert artifact["inputs"]["skipped_partial"] == 0
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", artifact["generated_utc"])

    # stdout stays the size JSON exactly as before; --out adds a file, not output
    printed = json.loads(capsys.readouterr().out)
    assert printed["sized"] is True and "schema" not in printed

    # the same population under the repaired §2 null records that method verbatim
    for rec in recs:
        rec["h1_null_method"] = "V2_OPTION_A"
        rec["h1_null_k"] = 1000
    src_a = tmp_path / "sims_option_a.jsonl"
    _write_jsonl(src_a, recs)
    out_a = tmp_path / "art" / "size_gate_option_a.json"
    argv_a = [a if a != str(src) else str(src_a) for a in argv]
    argv_a = [a if a != str(out) else str(out_a) for a in argv_a]
    assert main(argv_a) == 0
    assert json.loads(out_a.read_text())["h1_null_method"] == "V2_OPTION_A"


# MUTATION: scripts/leadership_rotation_p0.py:_cmd_size write the artifact before the harness/method gates so a refused gate still leaves a file behind
def test_size_out_refuses_dirty_mismatched_or_mixed(tmp_path: Path, capsys):
    from scripts.leadership_rotation_p0 import harness_identity, main

    def _run(tag: str, recs: list[dict], repo: Path) -> tuple[int, Path]:
        src = tmp_path / f"{tag}.jsonl"
        _write_jsonl(src, recs)
        out = tmp_path / f"{tag}_gate.json"
        rc = main(
            [
                "size",
                "--in",
                str(src),
                "--out",
                str(out),
                "--repo-root",
                str(repo),
            ]
        )
        return rc, out

    def _null_recs(rid: str) -> list[dict]:
        return _stamped([_sim_record(0, k) for k in range(20)], rid)

    # (a) a harness module modified but not committed: the working bytes are not
    #     the bytes HEAD records, so nothing may be pinned to them
    repo_a = _tmp_harness_repo(tmp_path / "a")
    rid_a = harness_identity(repo_a)["id"]
    dirty = repo_a / "scripts" / "leadership_rotation_inference.py"
    dirty.write_bytes(dirty.read_bytes() + b"\n# uncommitted edit\n")
    rc, out = _run("dirty", _null_recs(rid_a), repo_a)
    assert rc == 2 and not out.exists()
    err = capsys.readouterr().err
    assert "HARNESS_DIRTY" in err
    assert "scripts/leadership_rotation_inference.py" in err

    # (b) one record stamped by different harness bytes
    repo_b = _tmp_harness_repo(tmp_path / "b")
    recs_b = _null_recs(harness_identity(repo_b)["id"])
    recs_b[7]["harness_id"] = "0" * 64
    rc, out = _run("mismatch", recs_b, repo_b)
    assert rc == 2 and not out.exists()
    err = capsys.readouterr().err
    assert "HARNESS_MISMATCH" in err and "cell=0" in err and "k=7" in err

    # (c) a δ = 0 population mixing two H1 null methods
    repo_c = _tmp_harness_repo(tmp_path / "c")
    recs_c = _null_recs(harness_identity(repo_c)["id"])
    recs_c[3]["h1_null_method"] = "V2_OPTION_A"
    rc, out = _run("mixed", recs_c, repo_c)
    assert rc == 2 and not out.exists()
    err = capsys.readouterr().err
    assert "MIXED_H1_NULL_METHOD" in err
    assert "V1_BOOTSTRAP_SUPERSEDED" in err and "V2_OPTION_A" in err

    # (d) an Option A population whose null used fewer than K = 1,000 paths
    repo_d = _tmp_harness_repo(tmp_path / "d")
    recs_d = _null_recs(harness_identity(repo_d)["id"])
    for rec in recs_d:
        rec["h1_null_method"] = "V2_OPTION_A"
        rec["h1_null_k"] = 1000
    recs_d[5]["h1_null_k"] = 50
    rc, out = _run("smallk", recs_d, repo_d)
    assert rc == 2 and not out.exists()
    err = capsys.readouterr().err
    assert "NULL_K_TOO_SMALL" in err and "50" in err


# MUTATION: scripts/leadership_rotation_p0.py:_cmd_size return 2 without the artifact when result["sized"] is False (a failing re-size hidden instead of reported)
def test_size_out_written_when_not_sized(tmp_path: Path):
    from scripts.leadership_rotation_p0 import harness_identity, main

    repo = _tmp_harness_repo(tmp_path)
    rid = harness_identity(repo)["id"]
    recs = _stamped(
        [
            _sim_record(
                0, k, pass_paths={("defensive_sector", "H1")} if k < 30 else None
            )
            for k in range(400)
        ],
        rid,
    )
    src = tmp_path / "not_sized.jsonl"
    _write_jsonl(src, recs)
    out = tmp_path / "gate.json"
    rc = main(
        [
            "size",
            "--in",
            str(src),
            "--min-m",
            "400",
            "--out",
            str(out),
            "--repo-root",
            str(repo),
        ]
    )
    assert rc == 1
    artifact = json.loads(out.read_text())
    assert artifact["sized"] is False
    row = [
        v
        for v in artifact["violations"]
        if v["cell_id"] == 0 and v["row"] == "defensive_sector/H1"
    ]
    assert len(row) == 1
    assert row[0]["passes"] == 30 and row[0]["m"] == 400
    assert row[0]["flag"] == "SIZE_VIOLATION"
    assert row[0]["part_i_ok"] is False and row[0]["part_ii_ok"] is False
    assert artifact["missing_cells"] == []
    assert artifact["h1_null_method"] == "V1_BOOTSTRAP_SUPERSEDED"


# MUTATION: scripts/leadership_rotation_p0.py:power_summary count an eligible slot with m < min_m as measured, so a 60-path 0.90 slot declares POWERED_IN_PRINCIPLE
def test_power_summary_curve_shape_and_dispositions():
    from scripts.leadership_rotation_p0 import power_summary

    # ---- (i) one eligible slot reaches 0.55 -> POWERED_IN_PRINCIPLE ----------
    res = power_summary([_power_cell(104, {"defensive_sector/H2": (55, 100)})])
    assert res["rule"] == "V2_SEC4_POWERED_IN_PRINCIPLE"
    assert res["threshold"] == 0.50
    assert res["max_delta"] == 0.04 and res["max_n"] == 40 and res["min_m"] == 100
    h2 = res["dispositions"]["H2"]
    assert h2["disposition"] == "POWERED_IN_PRINCIPLE"
    ds = h2["by_group"]["defensive_sector"]
    assert ds["disposition"] == "POWERED_IN_PRINCIPLE"
    assert ds["best"]["cell_id"] == 104
    assert ds["best"]["pass_rate_ok"] == 0.55
    assert ds["best"]["delta"] == 0.02 and ds["best"]["n_target"] == 40
    assert ds["best"]["wilson_lower"] <= 0.55 <= ds["best"]["wilson_upper"]
    assert ds["unmeasured_cells"] == [100, 101, 103, 106, 107]
    # an unmeasured group is never a failure
    bp = h2["by_group"]["broadening_proxy"]
    assert bp["disposition"] == "NOT_EVALUATED"
    assert bp["best"] is None
    assert bp["unmeasured_cells"] == list(_G2_ELIGIBLE)
    assert res["dispositions"]["H1"]["label"] == _H1_POWER_LABEL
    assert "label" not in res["dispositions"]["H2"]
    assert "label" not in res["dispositions"]["H3"]
    assert res["dispositions"]["H3"]["disposition"] == "NOT_EVALUATED"

    # ---- (ii) every eligible slot measured below 0.50; 0.90 only where §4.3
    #           does not look (δ 8 % and N 80) -> NOT_EXECUTABLE ---------------
    ds_passes = {100: 10, 101: 12, 103: 14, 104: 20, 106: 16, 107: 20}
    bp_passes = {100: 30, 101: 30, 103: 14, 104: 16, 106: 18, 107: 12}
    cells = []
    for cid in sorted(set(ds_passes) | {102, 109, 110}):
        rows = {
            "defensive_sector/H2": (ds_passes.get(cid, 90), 100),
            "defensive_sector/H3": (ds_passes.get(cid, 90), 100),
            "broadening_proxy/H2": (bp_passes.get(cid, 90), 100),
            "broadening_proxy/H3": (bp_passes.get(cid, 90), 100),
        }
        cells.append(_power_cell(cid, rows))
    res = power_summary(cells)
    for h in ("H2", "H3"):
        assert res["dispositions"][h]["disposition"] == "NOT_EXECUTABLE"
        for g in ("defensive_sector", "broadening_proxy"):
            entry = res["dispositions"][h]["by_group"][g]
            assert entry["disposition"] == "NOT_EXECUTABLE"
            assert entry["unmeasured_cells"] == []
            assert entry["best"]["cell_id"] in _G2_ELIGIBLE
    # tie at the top point rate: smaller δ wins (104 at δ 2 % beats 107 at δ 4 %)
    assert (
        res["dispositions"]["H2"]["by_group"]["defensive_sector"]["best"]["cell_id"]
        == 104
    )
    assert (
        res["dispositions"]["H2"]["by_group"]["defensive_sector"]["best"][
            "pass_rate_ok"
        ]
        == 0.20
    )
    # tie at the top rate AND equal δ: smaller N wins (100 at N 20 beats 101 at N 40)
    assert (
        res["dispositions"]["H2"]["by_group"]["broadening_proxy"]["best"]["cell_id"]
        == 100
    )
    # the ineligible cells are still on the curve; they simply cannot qualify
    off_slot = [e for e in res["curve"] if e["cell_id"] in (102, 109, 110)]
    assert len(off_slot) == 3 * 4
    assert all(e["pass_rate_ok"] == 0.90 for e in off_slot)

    # ---- (iii) one eligible slot missing -> NOT_EVALUATED, id named ----------
    res = power_summary(
        [
            _power_cell(cid, {"defensive_sector/H2": (10, 100)})
            for cid in _G2_ELIGIBLE
            if cid != 103
        ]
    )
    ds = res["dispositions"]["H2"]["by_group"]["defensive_sector"]
    assert ds["disposition"] == "NOT_EVALUATED"
    assert ds["unmeasured_cells"] == [103]
    assert ds["best"]["cell_id"] == 100

    # ---- (iv) an under-M slot never qualifies --------------------------------
    res = power_summary(
        [_power_cell(100, {"defensive_sector/H2": (54, 60)})]
        + [
            _power_cell(cid, {"defensive_sector/H2": (10, 100)})
            for cid in _G2_ELIGIBLE
            if cid != 100
        ]
    )
    ds = res["dispositions"]["H2"]["by_group"]["defensive_sector"]
    assert ds["disposition"] == "NOT_EVALUATED"
    assert ds["unmeasured_cells"] == [100]
    assert ds["best"]["cell_id"] == 101
    under = next(
        e
        for e in res["curve"]
        if e["cell_id"] == 100 and e["row"] == "defensive_sector/H2"
    )
    assert under["below_min_m"] is True
    assert under["m"] == 60 and under["pass_rate_ok"] == 0.9
    assert all(e["below_min_m"] is False for e in res["curve"] if e["m"] >= 100)

    # ---- curve shape: labels, ordering, Wilson bracketing, δ = 0 excluded ----
    res = power_summary(
        [
            _power_cell(18, {"defensive_sector/H2": (5, 100)}),
            _power_cell(111, {"defensive_sector/H2": (90, 100), "family_any": (90, 100)}),
            _power_cell(100, {"defensive_sector/H2": (10, 0)}),
            _power_cell(0, {"defensive_sector/H2": (5, 100)}),
        ]
    )
    gens = {(e["cell_id"], e["generator"]) for e in res["curve"]}
    assert (18, "G1") in gens
    assert (100, "G2") in gens and (111, "G2") in gens
    assert all(e["cell_id"] != 0 for e in res["curve"])  # δ = 0 is size, not power
    order = [
        (e["generator"], e["n_target"], e["delta"], e["cell_id"], e["row"])
        for e in res["curve"]
    ]
    assert order == sorted(order)
    for e in res["curve"]:
        assert set(e) == _CURVE_KEYS
        if e["m"] > 0:
            assert e["pass_rate_ok"] == e["passes"] / e["m"]
            assert e["wilson_lower"] <= e["pass_rate_ok"] <= e["wilson_upper"]
        else:
            assert e["pass_rate_ok"] is None
            assert e["wilson_lower"] is None and e["wilson_upper"] is None
            assert e["below_min_m"] is True
    # family_any is reported on the curve but is never a (group, hypothesis) slot
    assert any(e["row"] == "family_any" for e in res["curve"])
    assert all(
        res["dispositions"][h]["by_group"][g]["best"] is None
        for h in ("H1", "H2", "H3")
        for g in ("defensive_sector", "broadening_proxy")
    )
    assert res["dispositions"]["H2"]["disposition"] == "NOT_EVALUATED"


# MUTATION: scripts/leadership_rotation_p0.py:_write_summary_md emit the Table 2b separator with the Table 1 column count
def test_summary_md_power_curve_table(tmp_path: Path):
    recs = [
        _sim_record(18, 0),
        _sim_record(18, 1),
        _sim_record(100, 0),
        _sim_record(104, 0, pass_paths={("defensive_sector", "H2")}),
        _sim_record(104, 1),
    ]
    jout, mout = _run_p0_summary(tmp_path, recs)
    md = mout.read_text()
    head = "## Table 2b Power curve and V2 §4 disposition"
    assert head in md
    section = md.split(head)[1].split("## Table 3")[0]
    lines = section.splitlines()
    hdr = "| generator | cell | δ (pts) | N | row | passes/M | point | Wilson 95 % |"
    i = lines.index(hdr)
    sep = lines[i + 1]
    assert re.fullmatch(r"\|(?:---\|)+", sep)
    assert sep.count("---") == hdr.count("|") - 1
    assert "| G1 | 18 |" in section
    assert "| G2 | 100 |" in section
    assert re.search(
        r"\| G2 \| 104 \| 2\.00 \| 40 \| defensive_sector/H2 \| 1/2 \| 0\.500 \| \[\d\.\d+, \d\.\d+\] \|",
        section,
    )
    assert "| n/a |" not in section  # every row above has m > 0
    for h in ("H1", "H2", "H3"):
        assert re.search(rf"^- {h}: \w+ \(defensive_sector \w+; broadening_proxy \w+\)", section, re.M)
    assert _H1_POWER_LABEL in section

    payload = json.loads(jout.read_text())
    assert payload["power"]["rule"] == "V2_SEC4_POWERED_IN_PRINCIPLE"
    assert set(payload["power"]["dispositions"]) == {"H1", "H2", "H3"}
    assert payload["power"]["dispositions"]["H1"]["label"] == _H1_POWER_LABEL
    assert {(e["cell_id"], e["generator"]) for e in payload["power"]["curve"]} == {
        (18, "G1"),
        (100, "G2"),
        (104, "G2"),
    }


# MUTATION: scripts/leadership_rotation_p0.py:write_size_gate_artifact rename the row key "passes" so the P1 reader in leadership_rotation_run cannot recompute the two-part rule
def test_size_gate_artifact_round_trips_through_the_p1_reader(tmp_path: Path):
    """Writer (p0 ``size --out``) and reader (run ``assert_size_gate_passed``)
    were built by separate lanes against shared constants; this is the
    integration proof that a SIZED V2_OPTION_A population written by one is
    accepted by the other, and that the same population under the superseded
    V1 bootstrap null is refused by method, not by an accident of shape."""
    from scripts.leadership_rotation_p0 import harness_identity, main
    from scripts.leadership_rotation_run import (
        SIZE_GATE_PATH,
        SizeGateNotPassed,
        assert_size_gate_passed,
    )

    repo = _tmp_harness_repo(tmp_path)
    ident = harness_identity(repo)

    def _population(method: str) -> list[dict]:
        recs = _stamped(
            [
                _sim_record(cid, k, pass_paths=_ALL_PASS_PATHS if k < 5 else None)
                for cid in (0, 1, 2, 3, 4, 48)
                for k in range(400)
            ],
            ident["id"],
        )
        for rec in recs:
            rec["h1_null_method"] = method
            if method == "V2_OPTION_A":
                rec["h1_null_k"] = 1000
        return recs

    def _write_and_commit(method: str) -> None:
        src = tmp_path / f"sims_{method}.jsonl"
        _write_jsonl(src, _population(method))
        out = repo / SIZE_GATE_PATH
        rc = main(
            [
                "size",
                "--in",
                str(src),
                "--min-m",
                "400",
                "--require-cells",
                "0,1,2,3,4,48",
                "--out",
                str(out),
                "--repo-root",
                str(repo),
            ]
        )
        assert rc == 0
        _git(repo, "add", "--", SIZE_GATE_PATH)
        _git(repo, "commit", "-q", "-m", f"size gate {method}")

    _write_and_commit("V2_OPTION_A")
    gate = assert_size_gate_passed(str(repo), runtime_root=str(repo))
    assert gate["h1_null_method"] == "V2_OPTION_A"
    assert gate["required_cells"] == [0, 1, 2, 3, 4, 48]
    assert gate["harness_head"] == ident["head"]

    _write_and_commit("V1_BOOTSTRAP_SUPERSEDED")
    with pytest.raises(SizeGateNotPassed) as exc:
        assert_size_gate_passed(str(repo), runtime_root=str(repo))
    assert exc.value.reason == "SIZE_GATE_NULL_METHOD_MISMATCH"
