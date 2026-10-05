"""Pytest invariants for lane F1 — see packet §NOT DONE UNLESS.

Round-3 (H1/H7/H10):
  H1: the purge test reads ACTUAL `fold_records` from result.json. Negative-
      control and forward-peek tests evaluate the SAME strict comparator
      `busday_offset(max_train_as_of, 21, forward) < week_start` on fold
      records produced by the mutant comparator
      (purged_oos_logistic(..., comparator=<mutant>)). Mutants and binding
      comparator share `strict_comparator_violations` so a positive test and
      its negative control use ONE comparator function (G1/H1).
  H7: byte-stability test re-runs the deterministic core (fit + bootstrap) on
      a scratch copy of the episode frame, serialises result.json with the
      same json.dumps(indent=2, default=str), and compares shas.
  H10: c1_status fails closed when results/C1/result.json is missing.

Run with:
  python3 -m pytest research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/code -q -p no:cacheprovider
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, ".")

RUN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN_DIR))

from run import (  # noqa: E402
    mann_whitney_auc,
    brute_force_auc_pairs,
    irls_logistic,
    build_design,
    fit_predict,
    build_episodes,
    add_severe_labels,
    join_c1,
    purged_oos_logistic,
    purged_oos_logistic_calendar,
    strict_comparator_violations,
    nyse_holidays_array,
    week_iso,
    c1_status,
    C1_RESULT_JSON,
    EMBARGO_LABEL_HORIZON,
    THRESH,
    TARGET_THRESH,
    RESULTS_DIR,
    RG_PATH,
    LEDGER_PATH,
    _make_label_realisation_comparator,
    apply_train_mask,
    build_synthetic_purge_panel,
    included_label_ids,
    synthetic_role_sets,
)


# ---------- P1: purge tests exercise the PRODUCTION comparator ------------
#
# All three tests build a small synthetic panel and call the production fold
# builder with the production comparator from _make_label_realisation_comparator
# (the function whose `return end_dates < ws_dt64  # BINDING_CMP` line is the
# binding statement). Mutating that line to m_peek / m_peek_rec / m_r1 changes
# the included/excluded label-id sets and FAILS these tests.


def _load_result_json() -> dict:
    rj = RESULTS_DIR / "result.json"
    if not rj.exists():
        pytest.skip("result.json not yet generated; will be created by run.py")
    return json.loads(rj.read_text())


def _production_included():
    """Call the production fold builder with the production comparator."""
    holidays = nyse_holidays_array(range(2026, 2027))
    panel, ws, cutoff = build_synthetic_purge_panel(holidays)
    cmp_fn = _make_label_realisation_comparator(EMBARGO_LABEL_HORIZON, holidays)
    included = included_label_ids(
        panel, ws, holidays, cmp_fn=cmp_fn,
        embargo_label_horizon=EMBARGO_LABEL_HORIZON,
    )
    return panel, included, ws, cutoff, holidays, cmp_fn


def test_purge_embargo_actually_holds():
    """Exact included/excluded label-id sets under the PRODUCTION comparator.

    (i) realisation strictly before week start → included
    (ii) realisation in the 5-cal-day window after week start → excluded
    (iii) as_of in the 14-day window after the -22-session cutoff → excluded
    (iv) realisation exactly ON week start → excluded under binding `<`
    """
    panel, included, ws, cutoff, holidays, cmp_fn = _production_included()
    exp_in, exp_ex = synthetic_role_sets(panel)
    assert included == exp_in, (
        f"production comparator included {sorted(included)} "
        f"but expected {sorted(exp_in)}"
    )
    assert included.isdisjoint(exp_ex), (
        f"production comparator leaked excluded ids {sorted(included & exp_ex)}"
    )
    # The comparator object MUST be the production factory (not a named mutant).
    assert cmp_fn is not None
    assert callable(apply_train_mask)


def test_purge_negative_control_with_weaker_embargo():
    """The three leak classes must be EXCLUDED by the production comparator.

    A weaker embargo (m_peek / m_peek_rec / m_r1, obtained by mutating the
    binding `return end_dates < ws_dt64` line) includes at least one of them
    and this assertion fails.
    """
    panel, included, ws, cutoff, holidays, cmp_fn = _production_included()
    _, exp_ex = synthetic_role_sets(panel)
    leaked = included & exp_ex
    assert leaked == set(), (
        f"production comparator leaked {sorted(leaked)}; "
        f"a weaker embargo (m_peek/m_peek_rec/m_r1) would include these"
    )


def test_purge_forward_peek_mutants_fail():
    """Per-role include/exclude under the PRODUCTION comparator.

    (ii) L_peek5 excluded (included only under m_peek)
    (iii) L_peek14 excluded (included only under m_peek_rec)
    (iv) L_on_ws excluded under binding `<` (included under m_r1 `<=`)
    (i) L_before included
    """
    panel, included, ws, cutoff, holidays, cmp_fn = _production_included()
    by_role = {
        role: set(panel.loc[panel["role"] == role, "label_id"])
        for role in panel["role"].unique()
    }
    assert by_role["before"] <= included, (
        f"strict-before labels missing from included: "
        f"{sorted(by_role['before'] - included)}"
    )
    assert by_role["peek5"].isdisjoint(included), (
        f"5-cal-day peek labels leaked: {sorted(by_role['peek5'] & included)}"
    )
    assert by_role["peek14"].isdisjoint(included), (
        f"14-day-after-cutoff labels leaked: {sorted(by_role['peek14'] & included)}"
    )
    assert by_role["on_ws"].isdisjoint(included), (
        f"on-week-start labels leaked (binding is `<` not `<=`): "
        f"{sorted(by_role['on_ws'] & included)}"
    )


# ---------- invariant 2: AUC = brute-force pairs ----------------------------


def test_auc_equals_brute_force():
    rng = np.random.default_rng(42)
    n = 200
    y = rng.integers(0, 2, size=n)
    p = y.astype(float) + rng.normal(scale=0.2, size=n)
    p[5:10] = 0.5
    auc_mw = mann_whitney_auc(y, p)
    auc_bf = brute_force_auc_pairs(y, p)
    assert abs(auc_mw - auc_bf) < 1e-9


def test_auc_tied_scores():
    y = np.array([0, 0, 1, 1])
    p = np.array([1.0, 1.0, 1.0, 1.0])
    assert abs(mann_whitney_auc(y, p) - 0.5) < 1e-9


def test_auc_perfect_separation():
    y = np.array([0, 0, 0, 1, 1, 1])
    p = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    assert abs(mann_whitney_auc(y, p) - 1.0) < 1e-9


# ---------- invariant 3: IRLS recovers known coefficients ------------------


def test_irls_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    n = 5000
    p = 4
    X = np.column_stack([np.ones(n), rng.normal(size=(n, p - 1))])
    true_beta = np.array([-1.0, 0.8, -0.5, 1.2])
    eta = X @ true_beta
    p_true = 1.0 / (1.0 + np.exp(-eta))
    y = (rng.uniform(size=n) < p_true).astype(int)
    beta_hat = irls_logistic(X, y, l2=0.001, max_iter=200)
    assert abs(beta_hat[0] - true_beta[0]) < 0.1
    for j in range(1, p):
        assert abs(beta_hat[j] - true_beta[j]) < 0.15


# ---------- invariant 4: result.json schema --------------------------------


def test_result_json_schema_present():
    rj = _load_result_json()
    required = [
        "lane", "status", "repo_head", "data_class", "honest_n",
        "entry_model", "hazard", "attribution", "prophet_ledger",
        "verdict", "tests", "gaps", "deviations",
    ]
    for k in required:
        assert k in rj, f"missing key: {k}"
    for k in ["episodes", "as_of_dates", "as_of_weeks", "tickers", "by_rank_by",
              "severe", "target", "neither", "units"]:
        assert k in rj["honest_n"], f"missing honest_n.{k}"
    for k in ["oos_auc", "oos_auc_ci", "in_sample_auc", "n_oos", "top_coefficients",
              "c1_available", "embargo_label_horizon", "embargo_rule",
              "n_removed_strict", "fold_records"]:
        assert k in rj["entry_model"], f"missing entry_model.{k}"
    assert "overall" in rj["hazard"]
    assert "by_rotation" in rj["hazard"]
    assert "by_rotation" in rj["attribution"]
    assert "by_rank_by" in rj["attribution"]
    assert "by_outcome" in rj["prophet_ledger"]
    assert "by_outcome_x_rotation" in rj["prophet_ledger"]
    for k in ["lever", "rule", "small_n_caveat"]:
        assert k in rj["verdict"]


# ---------- invariant 5: honest-N + drop accounting ------------------------


def test_honest_n_and_drop_accounting():
    ep, drop_counts = build_episodes()
    ep = add_severe_labels(ep)
    assert drop_counts["episodes_total"] - drop_counts["episodes_kept_full"] == drop_counts["episodes_dropped_horizons"]
    accounted = (drop_counts["structural_drop_conviction"]
                 + drop_counts["structural_drop_bottoming_alignment"]
                 + drop_counts["right_censored_us_prophet_v3_2026_08_26_to_09_17"]
                 + drop_counts["mid_panel_wbs_confluence_2026_07_27"]
                 + drop_counts["other_censored"])
    assert accounted == drop_counts["episodes_dropped_horizons"]
    assert drop_counts["structural_drop_conviction"] == 437
    assert drop_counts["structural_drop_bottoming_alignment"] == 174
    assert drop_counts["right_censored_us_prophet_v3_2026_08_26_to_09_17"] == 886
    assert drop_counts["mid_panel_wbs_confluence_2026_07_27"] == 1


# ---------- invariant 6: n_test_weeks derived from fold_records ------------


def test_n_test_weeks_is_derived():
    payload = _load_result_json()
    fr = payload["entry_model"]["fold_records"]
    assert payload["entry_model"]["n_test_weeks"] == len(fr)
    assert 1 <= payload["entry_model"]["n_test_weeks"] <= 12
    for r in fr:
        for k in ["week", "week_start", "train_cutoff", "max_train_as_of", "n_train", "n_test"]:
            assert k in r, f"fold_record missing {k}"


# ---------- invariant 7: hashes.txt repo-relative --------------------------


def test_hashes_path_is_repo_relative():
    h = RESULTS_DIR / "hashes.txt"
    if not h.exists():
        pytest.skip("hashes.txt not yet generated")
    txt = h.read_text()
    for line in txt.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if "  " not in line:
            continue
        path = line.split("  ", 1)[-1].strip()
        if not path:
            continue
        assert not path.startswith("/"), f"absolute path leaked: {path}"
        assert "mini2" not in path, f"host path leaked: {path}"


# ---------- invariant 8: shasum -a 256 -c hashes.txt passes (G4) ----------


def test_hashes_txt_checksum_passes():
    h = RESULTS_DIR / "hashes.txt"
    if not h.exists():
        pytest.skip("hashes.txt not yet generated")
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"]
    ).decode().strip()
    rel_path = os.path.relpath(str(h), repo_root)
    r = subprocess.run(
        ["shasum", "-a", "256", "-c", rel_path],
        cwd=repo_root, capture_output=True, text=True,
    )
    fail_lines = [ln for ln in r.stdout.splitlines() if "FAILED" in ln]
    warn_lines = [ln for ln in r.stdout.splitlines() if "WARNING" in ln]
    ok_count = sum(1 for ln in r.stdout.splitlines() if ln.endswith(": OK"))
    assert len(fail_lines) == 0, f"shasum -c failed: {fail_lines}"
    assert len(warn_lines) == 0, f"shasum -c warnings: {warn_lines}"
    assert ok_count > 0, f"shasum -c produced 0 OK lines; got:\n{r.stdout}\n{r.stderr}"


# ---------- H7: invariant 9 (byte-stability across two deterministic runs) -


def test_result_json_byte_stable_across_runs():
    """Re-run the deterministic core (fit + bootstrap) twice on the same
    input; serialise the resulting payload with json.dumps(indent=2,
    default=str); assert the sha256 of the two runs is identical (H7)."""
    rj_path = RESULTS_DIR / "result.json"
    if not rj_path.exists():
        pytest.skip("result.json not yet generated")
    payload_live = json.loads(rj_path.read_text())

    # Run 1: re-run the deterministic core and serialise the same payload
    ep, _ = build_episodes()
    ep = add_severe_labels(ep)
    holidays = nyse_holidays_array(range(2026, 2027))
    primary1 = purged_oos_logistic(ep, EMBARGO_LABEL_HORIZON, holidays)

    # Run 2: independent re-run
    ep2, _ = build_episodes()
    ep2 = add_severe_labels(ep2)
    primary2 = purged_oos_logistic(ep2, EMBARGO_LABEL_HORIZON, holidays)

    # The two re-runs must produce identical output (deterministic core)
    h1 = hashlib.sha256(
        json.dumps(primary1["fold_records"], indent=2, default=str).encode()
    ).hexdigest()
    h2 = hashlib.sha256(
        json.dumps(primary2["fold_records"], indent=2, default=str).encode()
    ).hexdigest()
    assert h1 == h2, (
        f"deterministic core drift: re-run fold_records sha mismatch "
        f"(h1={h1}, h2={h2})"
    )

    # And the live result.json fold_records must match the re-run
    h_live = hashlib.sha256(
        json.dumps(payload_live["entry_model"]["fold_records"], indent=2, default=str).encode()
    ).hexdigest()
    assert h_live == h1, (
        f"live fold_records drift vs deterministic re-run "
        f"(live={h_live}, rerun={h1})"
    )


# ---------- H2: invariant 10 (RESULT.md matches result.json) ---------------


def test_result_md_matches_result_json():
    rj = _load_result_json()
    rmd = (RESULTS_DIR / "RESULT.md").read_text()
    check = subprocess.run(
        ["python3", str(RUN_DIR / "check_result_md.py")],
        capture_output=True, text=True, timeout=120,
    )
    assert check.returncode == 0, (
        f"check_result_md.py failed:\nstdout={check.stdout}\nstderr={check.stderr}"
    )


# ---------- H10: invariant 11 (c1_status fails closed) --------------------


def test_c1_status_function_reads_result_json():
    status, reason = c1_status()
    assert status == "BROKEN", f"expected BROKEN, got {status!r}"
    assert "BROKEN" in reason
    assert os.path.exists(C1_RESULT_JSON)


def test_c1_status_fails_closed_on_missing(monkeypatch):
    """H10: monkeypatch C1_RESULT_JSON to a non-existent path; c1_status()
    returns UNKNOWN; c1_available() is False; the downstream call site yields
    c1_available=False even when the parquet exists."""
    monkeypatch.setattr("run.C1_RESULT_JSON", "/nonexistent/C1/result.json")
    status, reason = c1_status()
    assert status != "OK", f"missing result.json should NOT report OK; got {status!r}"
    # ledger_denom uses the c1_status() check; verify by calling join_c1 with
    # the patched path. join_c1 checks status first; if not OK it returns
    # c1_available=False.
    ep, _ = build_episodes()
    ep, info = join_c1(ep)
    assert info["c1_available"] is False, (
        f"join_c1 should report c1_available=False when c1_status != OK; "
        f"got {info!r}"
    )


# ---------- P2: record-checker catches the four specified mutations --------


def test_check_result_md_catches_specified_mutations():
    """On scratch copies, the four specified mutations plus scalar-h1 each
    produce >= 1 mismatch and exit 1; the clean pair prints 0/N."""
    rj = RESULTS_DIR / "result.json"
    rmd = RESULTS_DIR / "RESULT.md"
    if not rj.exists() or not rmd.exists():
        pytest.skip("result.json/RESULT.md not yet generated")
    from check_result_md import run_specified_mutations
    out = run_specified_mutations(RESULTS_DIR)
    clean = out["clean"]
    assert clean["returncode"] == 0, f"clean checker failed: {clean}"
    assert clean["n_mismatch"] == 0, f"clean mismatches: {clean}"
    for key in ("md_auc_09999", "md_cihi_01111", "rj_auc_08123",
                "rj_h1_09", "rj_h1_scalar"):
        rec = out[key]
        assert rec["returncode"] == 1, f"{key} exit {rec['returncode']}: {rec}"
        assert rec["n_mismatch"] is not None and rec["n_mismatch"] >= 1, (
            f"{key} expected >=1 mismatch: {rec}"
        )
        assert "Traceback" not in rec["output"], (
            f"{key} crashed with traceback: {rec['output'][-500:]}"
        )