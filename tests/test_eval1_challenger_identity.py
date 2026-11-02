"""EVAL-1 challenger trial identity checker tests."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "research" / "alpha_intelligence" / "expectation_market_dynamics"
CHECKER = HERE / "check_eval1_challenger_identity.py"
IDENTITY = HERE / "eval1_challenger_trial_identity.v1.json"
_SPEC = importlib.util.spec_from_file_location("check", CHECKER)
check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check)


@pytest.fixture(scope="module")
def doc() -> dict:
    return json.loads(IDENTITY.read_text(encoding="utf-8"))


def test_committed_identity_passes(doc):
    assert check.check_identity(doc, ROOT) == []


def test_main_cli_on_repo_root():
    assert check.main(["--repo-root", str(ROOT)]) == 0


def test_missing_seed_policy(doc):
    d = copy.deepcopy(doc)
    del d["elements"]["seed_policy"]
    errs = check.check_identity(d, ROOT)
    assert "missing element: seed_policy" in errs


def test_uncited_horizon(doc):
    d = copy.deepcopy(doc)
    d["elements"]["horizon"]["citations"] = []
    errs = check.check_identity(d, ROOT)
    assert "uncited element: horizon" in errs


def test_unresolvable_citation(doc):
    d = copy.deepcopy(doc)
    c = d["elements"]["target"]["citations"][0]
    c["quote"] = "ZZ-NOT-IN-FILE-ZZ"
    c["blob"] = check.git_blob_sha1((ROOT / c["path"]).read_bytes())
    errs = check.check_identity(d, ROOT)
    assert any(e.startswith("unresolvable citation: ") for e in errs)


def test_feature_not_in_emitted_set(doc):
    d = copy.deepcopy(doc)
    f = copy.deepcopy(d["elements"]["feature_set"]["value"]["features"][0])
    f["name"] = "price_return_21d"
    f["source_field"] = "price.return_21d"
    d["elements"]["feature_set"]["value"]["features"].append(f)
    errs = check.check_identity(d, ROOT)
    assert "feature not in EXP-1 emitted set: price_return_21d" in errs


def test_bound_universe_feature_missing(doc):
    d = copy.deepcopy(doc)
    feats = d["elements"]["feature_set"]["value"]["features"]
    d["elements"]["feature_set"]["value"]["features"] = [
        f for f in feats if f.get("name") != "invalid_or_inconsistent_excluded_share"
    ]
    errs = check.check_identity(d, ROOT)
    assert "bound universe feature missing: invalid_or_inconsistent_excluded_share" in errs


def test_tunable_l2_lambda_list(doc):
    d = copy.deepcopy(doc)
    d["elements"]["hyperparameters"]["value"]["l2_lambda"] = [0.1, 1.0, 10.0]
    errs = check.check_identity(d, ROOT)
    assert "tunable hyperparameter: l2_lambda" in errs


def test_tunable_tuning_grid(doc):
    d = copy.deepcopy(doc)
    d["elements"]["hyperparameters"]["value"]["tuning"] = "GRID"
    errs = check.check_identity(d, ROOT)
    assert "tunable hyperparameter: tuning" in errs


def test_fit_scope_not_f_dev(doc):
    d = copy.deepcopy(doc)
    for s in d["elements"]["preprocessing"]["value"]["steps"]:
        if s["name"] == "standardize":
            s["fit_scope"] = "F_DEV+F_VAL"
    errs = check.check_identity(d, ROOT)
    assert "fit scope other than F_DEV: standardize" in errs


def test_seed_mismatch_and_rng_used(doc):
    d = copy.deepcopy(doc)
    d["elements"]["seed_policy"]["value"]["seed"] = 1
    errs = check.check_identity(d, ROOT)
    assert "seed mismatch" in errs
    d2 = copy.deepcopy(doc)
    d2["elements"]["seed_policy"]["value"]["rng_used"] = True
    errs2 = check.check_identity(d2, ROOT)
    assert "rng used" in errs2


def test_malformed_identity_does_not_raise():
    assert check.check_identity({}, ROOT)
    assert check.check_identity([], ROOT)


def test_checker_stdlib_only_imports():
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    allowed = {"__future__", "argparse", "hashlib", "json", "os", "subprocess", "sys", "pathlib"}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed
        elif isinstance(node, ast.ImportFrom):
            assert node.module in allowed


def test_cli_exit_codes(tmp_path):
    d = copy.deepcopy(json.loads(IDENTITY.read_text(encoding="utf-8")))
    del d["elements"]["seed_policy"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(d), encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(CHECKER), "--identity", str(bad), "--repo-root", str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 1
    assert "ERROR: missing element: seed_policy" in p.stdout
    p2 = subprocess.run(
        [sys.executable, str(CHECKER), "--identity", str(IDENTITY), "--repo-root", str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert p2.returncode == 0
    assert "OK: EVAL-1 challenger trial identity" in p2.stdout


def test_unreadable_identity_main(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("not json", encoding="utf-8")
    assert check.main(["--identity", str(p), "--repo-root", str(ROOT)]) == 1
