"""Pins the three metric-validity invariants of the Universal Scoreboard.

Each test states the reading it forbids and why that reading is silent. The
negative controls matter as much as the positives: an auditor that flags
everything is as useless as one that flags nothing, and only the negative
controls prove this one discriminates.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from engine.k3e_eval_admission import (
    EVAL0_CANONICAL_DIGEST,
    _canonical_json_digest,
    _registration_reason,
    inspect_eval1_admission,
)
import engine.k3e_eval1_forward as k3e_fwd
from engine.qledger_validity import (
    SEVERITY_INVALID,
    SEVERITY_NOTE,
    Finding,
    audit,
    may_pool_signed_excess,
    may_report_hit_rate,
    profile_families,
)


def _claim(family: str, cid: str, direction: int, horizon: int = 5, **extra):
    return {
        "claim_family": family,
        "claim_id": cid,
        "direction": direction,
        "horizon_d": horizon,
        **extra,
    }


def _grade(cid: str, horizon: int):
    return {"claim_id": cid, "horizon_d": horizon}


# --------------------------------------------------------------------------- #
# V1 — signed excess may not be pooled across directions
# --------------------------------------------------------------------------- #
def test_mixed_direction_family_may_not_pool_signed_excess():
    """grades.excess is RAW, so a correct bearish call contributes negative excess."""
    claims = [_claim("m", "a", 1), _claim("m", "b", -1)]
    grades = [_grade("a", 5), _grade("b", 5)]
    codes = {f.code for f in audit(claims, grades)}
    assert "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" in codes


def test_single_direction_family_may_pool_signed_excess():
    """Negative control: one sign means the pooled mean is interpretable."""
    claims = [_claim("h", "c", 1), _claim("h", "d", 1)]
    grades = [_grade("c", 5), _grade("d", 5)]
    codes = {f.code for f in audit(claims, grades)}
    assert "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes


def test_placebo_rows_do_not_decide_a_real_familys_direction_profile():
    """A synthetic control row must never flip a real family's reporting rights."""
    claims = [
        _claim("h", "c", 1),
        _claim("h", "d", 1),
        _claim("h", "p", -1, is_placebo=True),
    ]
    grades = [_grade("c", 5), _grade("d", 5)]
    codes = {f.code for f in audit(claims, grades)}
    assert "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes


# --------------------------------------------------------------------------- #
# V2 — a salience family has no hit rate
# --------------------------------------------------------------------------- #
def test_salience_family_may_not_report_a_hit_rate():
    """direction==0 asserts importance, not direction, so `hit` is undefined."""
    claims = [_claim("s", "e", 0), _claim("s", "f", 0)]
    grades = [_grade("e", 5), _grade("f", 5)]
    findings = audit(claims, grades)
    hits = [f for f in findings if f.code == "HIT_RATE_ON_A_SALIENCE_FAMILY"]
    assert hits and hits[0].severity == SEVERITY_INVALID


def test_salience_family_may_still_pool_excess():
    """With no directional claims there is no sign convention to violate."""
    claims = [_claim("s", "e", 0), _claim("s", "f", 0)]
    grades = [_grade("e", 5), _grade("f", 5)]
    codes = {f.code for f in audit(claims, grades)}
    assert "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes


# --------------------------------------------------------------------------- #
# V3 — a verdict may only be read at the family's declared ruler
# --------------------------------------------------------------------------- #
def test_grades_short_of_the_declared_horizon_are_accruing_not_a_verdict():
    """DNR:KILL-OFFHORIZON-VERDICTS — a 63d claim read at 5d is not a record."""
    claims = [_claim("l", "g", 1, horizon=63)]
    grades = [_grade("g", 5), _grade("g", 21)]
    findings = [f for f in audit(claims, grades) if f.code == "OFF_HORIZON_VERDICT"]
    assert findings and findings[0].severity == SEVERITY_NOTE
    assert "63" in findings[0].detail


def test_off_horizon_finding_clears_once_the_declared_ruler_matures():
    """Negative control: this must be a maturity statement, not a permanent brand."""
    claims = [_claim("l", "g", 1, horizon=63)]
    grades = [_grade("g", 5), _grade("g", 21), _grade("g", 63)]
    codes = {f.code for f in audit(claims, grades)}
    assert "OFF_HORIZON_VERDICT" not in codes


def test_family_declaring_several_horizons_is_ruled_by_its_longest():
    """us_importance_v0 declares {5,21}; its ruler is 21, and 21 is present."""
    claims = [_claim("multi", "x", 1, horizon=5), _claim("multi", "y", 1, horizon=21)]
    grades = [_grade("x", 5), _grade("y", 21)]
    codes = {f.code for f in audit(claims, grades)}
    assert "OFF_HORIZON_VERDICT" not in codes

    grades_short = [_grade("x", 5), _grade("y", 5)]
    codes = {f.code for f in audit(claims, grades_short)}
    assert "OFF_HORIZON_VERDICT" in codes


# --------------------------------------------------------------------------- #
# Profile + schema mechanics
# --------------------------------------------------------------------------- #
def test_direction_and_horizon_are_read_from_strings_too():
    """The live store holds direction as a string ('1'/'-1'); coercion is load-bearing."""
    claims = [_claim("m", "a", "1"), _claim("m", "b", "-1")]
    profiles = profile_families(claims)
    assert profiles["m"].directions == {1, -1}
    assert not may_pool_signed_excess(profiles["m"])


def test_booleans_are_never_read_as_a_direction():
    """bool is an int subclass; a stray True must not become direction==1."""
    profiles = profile_families([_claim("b", "a", True)])
    assert profiles["b"].directions == set()


def test_reported_metrics_narrows_the_audit_to_what_a_caller_publishes():
    claims = [_claim("m", "a", 1), _claim("m", "b", -1)]
    grades = [_grade("a", 5), _grade("b", 5)]
    codes = {f.code for f in audit(claims, grades, reported_metrics={"m": {"hit_rate"}})}
    assert "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes


def test_empty_corpus_yields_no_findings():
    assert audit([], []) == []


def test_finding_rejects_an_unknown_code_or_severity():
    with pytest.raises(ValueError):
        Finding(code="NOPE", family="f", severity=SEVERITY_INVALID, detail="")
    with pytest.raises(ValueError):
        Finding(code="OFF_HORIZON_VERDICT", family="f", severity="critical", detail="")


def test_may_report_hit_rate_requires_a_directional_claim():
    profiles = profile_families([_claim("s", "e", 0)])
    assert not may_report_hit_rate(profiles["s"])
    profiles = profile_families([_claim("d", "e", -1)])
    assert may_report_hit_rate(profiles["d"])


# --------------------------------------------------------------------------- #
# The --json contract (pins a defect found while testing the documented
# reproduce command: --json emitted ::notice lines, not JSON, when the store was
# absent — which is exactly the sparse-worktree and CI case).
# --------------------------------------------------------------------------- #
def _load_cli():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "check_qledger_metric_validity.py"
    spec = importlib.util.spec_from_file_location("_qmv_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_json_payload_is_always_an_object_with_the_same_keys():
    cli = _load_cli()
    absent = json.loads(cli._json_payload(None, store_absent=True, missing=["a", "b"]))
    present = json.loads(cli._json_payload([], store_absent=False, n_claims=3, n_grades=4))
    assert absent.keys() == present.keys()
    for payload in (absent, present):
        assert isinstance(payload, dict)


def test_absent_store_reports_null_findings_not_an_empty_list():
    """"Could not look" must never be encodable as "looked and clean" (§9.2)."""
    cli = _load_cli()
    absent = json.loads(cli._json_payload(None, store_absent=True, missing=["x"]))
    assert absent["store_absent"] is True
    assert absent["findings"] is None
    assert absent["missing"] == ["x"]

    clean = json.loads(cli._json_payload([], store_absent=False, n_claims=0, n_grades=0))
    assert clean["store_absent"] is False
    assert clean["findings"] == []


@pytest.mark.parametrize(
    "claims,grades,expected_code,strict_exit",
    [
        ([_claim("mixed", "a", 1), _claim("mixed", "b", -1)],
         [_grade("a", 5), _grade("b", 5)],
         "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS", 1),
        ([_claim("salience", "a", 0)], [_grade("a", 5)],
         "HIT_RATE_ON_A_SALIENCE_FAMILY", 1),
        ([_claim("long", "a", 1, horizon=63)], [_grade("a", 21)],
         "OFF_HORIZON_VERDICT", 0),
        ([_claim("legal", "a", -1)], [_grade("a", 5)], None, 0),
        ([], [], None, 0),
    ],
    ids=["mixed-direction", "salience-hit-rate", "immature-note", "legal-short", "empty"],
)
def test_metric_gate_strict_scope_preserves_owner_severity_and_warn_default(
    tmp_path, monkeypatch, capsys, claims, grades, expected_code, strict_exit
):
    """Exercise the real CLI on synthetic stores, without activating fleet strictness.

    An illegal metric is a strict failure; immature evidence retains the owner's
    NOTE severity. Neither a clean store nor a lawful negative direction fails.
    Both modes must audit identical inputs and leave the owner stores untouched.
    """
    import sys

    cli = _load_cli()
    store = tmp_path / "data" / "qledger"
    store.mkdir(parents=True)
    for name, rows in (("claims", claims), ("grades", grades)):
        (store / f"{name}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
    before = {p.name: p.read_bytes() for p in store.iterdir()}
    outputs = []
    for strict in (False, True):
        argv = ["check_qledger_metric_validity", "--root", str(tmp_path), "--json"]
        monkeypatch.setattr(sys, "argv", argv + (["--strict"] if strict else []))
        assert cli.main() == (strict_exit if strict else 0)
        outputs.append(json.loads(capsys.readouterr().out))
    assert outputs[0] == outputs[1]
    assert outputs[0]["store_absent"] is False
    assert outputs[0]["claims"] == len(claims)
    assert outputs[0]["grades"] == len(grades)
    codes = {finding["code"] for finding in outputs[0]["findings"]}
    assert codes == ({expected_code} if expected_code else set())
    assert {p.name: p.read_bytes() for p in store.iterdir()} == before


def test_descriptive_no_metric_scope_does_not_invent_a_hit_rate():
    """The existing auditor supports an explicit no-metric owner projection."""
    claims = [_claim("description", "a", 0)]
    assert audit(claims, [], reported_metrics={"description": set()}) == []


# --------------------------------------------------------------------------- #
# K3E EVAL-1 — accepted-main source admission fence
# --------------------------------------------------------------------------- #
_K3E_ROOT = Path(__file__).resolve().parents[1]
_K3E_BASE = Path("research/alpha_intelligence/expectation_market_dynamics")
_K3E_EVAL0 = _K3E_BASE / "eval0_preregistration.v1.json"
_K3E_EVAL1 = _K3E_BASE / "eval1_preregistration.v1.json"
_K3E_OWNER = _K3E_BASE / "eval1_owner_acceptance.v1.json"
_K3E_ACTIVATION = _K3E_BASE / "eval1_activation_receipt.v1.json"


_K3E_DEFAULT_WHEN = "2026-10-04T12:00:00-04:00"
_K3E_AT_BOUNDARY = "2026-10-05T09:30:00-04:00"
_K3E_EVAL1_COMMITTED_DIGEST = "1ca158a213fca3f90c5c4fdc1359d40bf9146f2400cb10d8caa202b18f293bd4"


def _k3e_git(repo: Path, *args: str, when: str | None = None) -> str:
    env = dict(os.environ)
    stamp = when or _K3E_DEFAULT_WHEN
    env["GIT_AUTHOR_DATE"] = stamp
    env["GIT_COMMITTER_DATE"] = stamp
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        stderr=subprocess.STDOUT,
        env=env,
    ).strip()


def _k3e_source_repo(tmp_path: Path) -> Path:
    bare = tmp_path / "origin.git"
    subprocess.check_call(["git", "init", "--bare", "-q", str(bare)])
    repo = tmp_path / "repo"
    repo.mkdir()
    _k3e_git(repo, "init", "-b", "main")
    _k3e_git(repo, "config", "user.name", "K3E Test")
    _k3e_git(repo, "config", "user.email", "k3e-test@example.invalid")
    _k3e_git(repo, "config", "commit.gpgsign", "false")
    _k3e_git(repo, "remote", "add", "origin", str(bare))
    target = repo / _K3E_EVAL0
    target.parent.mkdir(parents=True)
    target.write_bytes((_K3E_ROOT / _K3E_EVAL0).read_bytes())
    _k3e_git(repo, "add", ".")
    _k3e_git(repo, "commit", "-m", "seed accepted eval0")
    head = _k3e_git(repo, "rev-parse", "HEAD")
    _k3e_git(repo, "push", "-q", "origin", "HEAD:refs/heads/main")
    _k3e_git(repo, "update-ref", "refs/remotes/origin/main", head)
    return repo


def _k3e_write_json(repo: Path, path: Path, payload: dict) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _k3e_commit_main(
    repo: Path,
    message: str,
    *,
    when: str | None = None,
    push: bool = True,
) -> str:
    _k3e_git(repo, "add", ".", when=when)
    _k3e_git(repo, "commit", "-m", message, when=when)
    head = _k3e_git(repo, "rev-parse", "HEAD")
    if push:
        _k3e_git(repo, "push", "-q", "origin", "HEAD:refs/heads/main", when=when)
    _k3e_git(repo, "update-ref", "refs/remotes/origin/main", head)
    return head


def _k3e_digest(payload: dict) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _k3e_frozen_registration(*, status: str = "FROZEN_BEFORE_OUTCOME_ACCESS") -> dict:
    return {
        "schema": "k3e.eval1_preregistration/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "status": status,
        "predecessor": {
            "registration_id": "K3E-EVAL-0-V1",
            "canonical_digest_sha256": EVAL0_CANONICAL_DIGEST,
            "prior_trial_budget_reset": False,
        },
        "admitted_experiments": ["SYNTHETIC_PROTOCOL_TEST_ONLY"],
        "scientific_freeze": {
            "primary_endpoint": "SYNTHETIC_ENDPOINT",
            "primary_horizon_sessions": 21,
            "primary_loss": "synthetic_loss",
            "strongest_baseline_rule": "strongest_eligible_matched_information_baseline",
            "total_search_budget": 1,
            "effect_size_threshold": 0.05,
            "effective_n_rule": "distinct_issuer_episodes",
            "coverage_rule": "print_abstentions_no_imputation",
            "dependence_rule": "issuer_episode_cluster_plus_date_block",
            "censoring_rule": "preserve_censoring",
            "forward_partitions": "new_forward_only_no_relabel",
        },
    }


def _k3e_publish_valid_receipts(
    repo: Path,
    registration: dict,
    source_commit: str,
    *,
    when: str | None = None,
    resolved_session: str = "2026-10-05",
    push: bool = True,
) -> str:
    digest = _k3e_digest(registration)
    _k3e_write_json(repo, _K3E_OWNER, {
        "schema": "k3e.eval1_owner_acceptance/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "registration_digest_sha256": digest,
        "registration_source_commit": source_commit,
        "owner_workstream": "WS:EVAL-OS-MEASUREMENT-LAW",
        "accepted": True,
    })
    _k3e_write_json(repo, _K3E_ACTIVATION, {
        "schema": "k3e.eval1_activation_receipt/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "canonical_registration_digest_sha256": digest,
        "registration_source_commit": source_commit,
        "freeze_boundary_rule": "first_nyse_session_open_strictly_after_origin_main_commit_containing_exact_registration_digest/v1",
        "resolved_first_eligible_session": resolved_session,
    })
    return _k3e_commit_main(
        repo,
        "publish valid eval1 owner and activation receipts",
        when=when,
        push=push,
    )


def _k3e_ready_admission(repo: Path) -> dict:
    """Registration on the default Sunday; receipts introduced at the Monday open."""
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    introduction = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, introduction, when=_K3E_AT_BOUNDARY)
    return {
        "registration": registration,
        "introduction": introduction,
        "boundary": "2026-10-05",
    }


def _k3e_snapshot(repo: Path) -> str:
    status = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
        text=True,
    )
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    )
    digest = hashlib.sha256()
    for path in sorted(p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts):
        digest.update(str(path.relative_to(repo)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return status + "\n" + head + "\n" + digest.hexdigest()


def test_k3e_eval1_missing_registration_refuses_and_preserves_eval0(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 4))
    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["EVAL1_REGISTRATION_MISSING"]
    assert result["eval0"] == {
        "registration_id": "K3E-EVAL-0-V1",
        "canonical_digest": EVAL0_CANONICAL_DIGEST,
        "preserved": True,
    }


def test_k3e_eval1_unsigned_registration_on_main_still_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    _k3e_write_json(repo, _K3E_EVAL1, _k3e_frozen_registration(status="UNSIGNED_OWNER_REVIEW"))
    _k3e_commit_main(repo, "publish unsigned review draft")
    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 4))
    assert result["reasons"] == ["EVAL1_REGISTRATION_NOT_FROZEN"]
    assert result["outcome_access_allowed"] is False


def test_k3e_eval1_owner_acceptance_wrong_digest_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    source_commit = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_write_json(repo, _K3E_OWNER, {
        "schema": "k3e.eval1_owner_acceptance/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "registration_digest_sha256": "0" * 64,
        "registration_source_commit": source_commit,
        "owner_workstream": "WS:EVAL-OS-MEASUREMENT-LAW",
        "accepted": True,
    })
    _k3e_write_json(repo, _K3E_ACTIVATION, {
        "schema": "k3e.eval1_activation_receipt/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "canonical_registration_digest_sha256": _k3e_digest(registration),
        "registration_source_commit": source_commit,
        "resolved_first_eligible_session": "2026-10-05",
    })
    _k3e_commit_main(repo, "publish mismatched owner receipt")
    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))
    assert result["reasons"] == ["OWNER_ACCEPTANCE_DIGEST_MISMATCH"]
    assert result["outcome_access_allowed"] is False


def test_k3e_eval1_owner_source_commit_must_bind_main_lineage(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, "f" * 40)
    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))
    assert result["reasons"] == ["OWNER_ACCEPTANCE_SOURCE_NOT_INTRODUCTION"]
    assert result["detail"]["registration_source_commit"] == "f" * 40
    assert result["outcome_access_allowed"] is False


def test_k3e_eval1_valid_lineage_waits_for_new_forward_boundary(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    source_commit = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, source_commit, when=_K3E_AT_BOUNDARY)

    before = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 4))
    after = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 5))

    assert before["reasons"] == ["FORWARD_BOUNDARY_NOT_REACHED"]
    assert before["outcome_access_allowed"] is False
    assert after["admitted"] is True
    assert after["outcome_access_allowed"] is True
    assert after["reasons"] == []
    assert after["registration_digest"] == _k3e_digest(registration)
    assert after["registration_source_commit"] == source_commit
    assert after["resolved_first_eligible_session"] == "2026-10-05"


def test_k3e_eval1_backdated_activation_boundary_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    source_commit = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, source_commit)
    _k3e_write_json(repo, _K3E_ACTIVATION, {
        "schema": "k3e.eval1_activation_receipt/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "canonical_registration_digest_sha256": _k3e_digest(registration),
        "registration_source_commit": source_commit,
        "freeze_boundary_rule": "first_nyse_session_open_strictly_after_origin_main_commit_containing_exact_registration_digest/v1",
        "resolved_first_eligible_session": "2000-01-03",
    })
    _k3e_commit_main(repo, "attempt backdated activation")

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["EVAL1_ACTIVATION_BOUNDARY_INVALID"]


def test_k3e_eval1_boolean_trial_budget_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    registration["scientific_freeze"]["total_search_budget"] = True
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    source_commit = _k3e_commit_main(repo, "freeze malformed eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, source_commit)

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["EVAL1_SCIENTIFIC_FREEZE_INCOMPLETE"]


def test_k3e_eval1_admission_binds_one_main_commit(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    source_commit = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, source_commit, when=_K3E_AT_BOUNDARY)
    expected_main = _k3e_git(repo, "rev-parse", "refs/remotes/origin/main")

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 5))

    assert result["admitted"] is True
    assert result["source_main_commit"] == expected_main


def test_k3e_eval1_t1_owner_source_ancestor_not_introduction(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    parent = _k3e_git(repo, "rev-parse", "HEAD")
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    introduction = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, parent)

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["OWNER_ACCEPTANCE_SOURCE_NOT_INTRODUCTION"]
    assert result["detail"]["registration_source_commit"] == parent
    assert result["detail"]["introduction_commit"] == introduction

    digest = _k3e_digest(registration)
    _k3e_write_json(repo, _K3E_OWNER, {
        "schema": "k3e.eval1_owner_acceptance/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "registration_digest_sha256": digest,
        "registration_source_commit": introduction,
        "owner_workstream": "WS:EVAL-OS-MEASUREMENT-LAW",
        "accepted": True,
    })
    _k3e_write_json(repo, _K3E_ACTIVATION, {
        "schema": "k3e.eval1_activation_receipt/v1",
        "registration_id": "K3E-EVAL-1-V1",
        "canonical_registration_digest_sha256": digest,
        "registration_source_commit": parent,
        "freeze_boundary_rule": "first_nyse_session_open_strictly_after_origin_main_commit_containing_exact_registration_digest/v1",
        "resolved_first_eligible_session": "2026-10-05",
    })
    _k3e_commit_main(repo, "activation names an ancestor instead of the introduction")
    activation = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))
    assert activation["reasons"] == ["OWNER_ACCEPTANCE_SOURCE_NOT_INTRODUCTION"]
    assert activation["detail"]["registration_source_commit"] == parent
    assert activation["detail"]["introduction_commit"] == introduction


def test_k3e_eval1_t2_side_branch_merge_is_the_introduction(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    side_when = "2026-09-30T12:00:00-04:00"
    merge_when = "2026-10-06T15:00:00-04:00"
    _k3e_git(repo, "checkout", "-b", "side")
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    _k3e_git(repo, "add", ".", when=side_when)
    _k3e_git(repo, "commit", "-m", "side lands the registration", when=side_when)
    side = _k3e_git(repo, "rev-parse", "HEAD")
    _k3e_git(repo, "checkout", "main")
    _k3e_git(repo, "merge", "--no-ff", "-m", "merge side onto main", "side", when=merge_when)
    merge = _k3e_git(repo, "rev-parse", "HEAD")
    parents = set(_k3e_git(repo, "rev-parse", "HEAD^1", "HEAD^2").split())
    assert side in parents and side != merge
    _k3e_git(repo, "update-ref", "refs/remotes/origin/main", merge)
    _k3e_git(repo, "push", "-q", "origin", "HEAD:refs/heads/main")

    _k3e_publish_valid_receipts(
        repo,
        registration,
        side,
        resolved_session="2026-10-01",
    )
    refused = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 8))
    assert refused["admitted"] is False
    assert refused["outcome_access_allowed"] is False
    assert refused["reasons"] == ["OWNER_ACCEPTANCE_SOURCE_NOT_INTRODUCTION"]
    assert refused["detail"]["registration_source_commit"] == side
    assert refused["detail"]["introduction_commit"] == merge

    _k3e_publish_valid_receipts(
        repo,
        registration,
        merge,
        when="2026-10-07T09:30:00-04:00",
        resolved_session="2026-10-07",
    )
    admitted = inspect_eval1_admission(repo)
    assert admitted["admitted"] is True
    assert admitted["outcome_access_allowed"] is True
    assert admitted["introduction_commit"] == merge
    assert admitted["boundary"] == "2026-10-07"
    assert admitted["registration_source_commit"] == merge
    assert admitted["main_freshness"]["proven"] is True


def test_k3e_eval1_t3_local_main_ahead_of_bare_remote_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    _k3e_ready_admission(repo)
    (repo / "local-only.txt").write_text("not pushed\n", encoding="utf-8")
    _k3e_commit_main(repo, "advance local main without pushing", push=False)

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["MAIN_REF_FRESHNESS_UNPROVEN"]
    assert result["main_freshness"]["proven"] is False
    assert result["main_freshness"]["remote"] is not None
    assert result["main_freshness"]["local"] != result["main_freshness"]["remote"]
    assert result["detail"]["freshness_reason"]


def test_k3e_eval1_t4_missing_origin_remote_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    _k3e_ready_admission(repo)
    local_main = _k3e_git(repo, "rev-parse", "refs/remotes/origin/main")
    _k3e_git(repo, "remote", "remove", "origin")
    # remote remove deletes the tracking ref; the local main commit must remain
    # so the refusal is freshness, not a missing source ref.
    _k3e_git(repo, "update-ref", "refs/remotes/origin/main", local_main)

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 6))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["MAIN_REF_FRESHNESS_UNPROVEN"]
    assert result["main_freshness"] == {
        "local": result["main_freshness"]["local"],
        "remote": None,
        "proven": False,
    }
    assert result["main_freshness"]["proven"] is False
    assert result["detail"]["freshness_reason"]


def test_k3e_eval1_t5_activation_before_boundary_cannot_be_unlocked(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    registration = _k3e_frozen_registration()
    _k3e_write_json(repo, _K3E_EVAL1, registration)
    introduction = _k3e_commit_main(repo, "freeze eval1 registration")
    _k3e_publish_valid_receipts(repo, registration, introduction)

    result = inspect_eval1_admission(repo, as_of_date=date(2099, 1, 4))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["FORWARD_BOUNDARY_NOT_REACHED"]
    assert result["detail"]["activation_introduced_at"].startswith("2026-10-04T12:00:00")
    assert result["detail"]["boundary_at"].startswith("2026-10-05T09:30:00")


def test_k3e_eval1_t6_admits_without_caller_clock_when_main_is_fresh(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    ready = _k3e_ready_admission(repo)

    result = inspect_eval1_admission(repo)

    assert result["admitted"] is True
    assert result["outcome_access_allowed"] is True
    assert result["reasons"] == []
    assert result["introduction_commit"] == ready["introduction"]
    assert result["boundary"] == ready["boundary"]
    assert result["resolved_first_eligible_session"] == ready["boundary"]
    assert result["registration_digest"] == _k3e_digest(ready["registration"])
    assert result["main_freshness"]["proven"] is True
    assert result["main_freshness"]["local"] == result["main_freshness"]["remote"]
    assert result["main_freshness"]["local"] == result["source_main_commit"]


def test_k3e_eval1_t7_caller_clock_before_boundary_still_refuses(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    ready = _k3e_ready_admission(repo)

    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 4))

    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["FORWARD_BOUNDARY_NOT_REACHED"]
    assert result["detail"]["as_of_date"] == "2026-10-04"
    assert result["detail"]["boundary_date"] == ready["boundary"]


def test_k3e_eval1_t8_eval0_runs_first_and_calls_do_not_write(tmp_path: Path):
    repo = _k3e_source_repo(tmp_path)
    before_refuse = _k3e_snapshot(repo)
    refused = inspect_eval1_admission(repo)
    after_refuse = _k3e_snapshot(repo)
    assert before_refuse == after_refuse
    assert refused["reasons"] == ["EVAL1_REGISTRATION_MISSING"]
    assert refused["eval0"]["registration_id"] == "K3E-EVAL-0-V1"
    assert refused["eval0"]["canonical_digest"] == EVAL0_CANONICAL_DIGEST
    assert refused["eval0"]["preserved"] is True

    payload = json.loads((repo / _K3E_EVAL0).read_text(encoding="utf-8"))
    payload["registration_id"] = "K3E-EVAL-0-TAMPERED"
    _k3e_write_json(repo, _K3E_EVAL0, payload)
    _k3e_commit_main(repo, "tamper eval0")
    tampered = inspect_eval1_admission(repo, as_of_date=date(2099, 1, 4))
    assert tampered["reasons"] == ["EVAL0_REGISTRATION_CHANGED"]
    assert tampered["eval0"]["preserved"] is False

    admitted_root = tmp_path / "admitted"
    admitted_root.mkdir()
    admitted_repo = _k3e_source_repo(admitted_root)
    _k3e_ready_admission(admitted_repo)
    before_admit = _k3e_snapshot(admitted_repo)
    admitted = inspect_eval1_admission(admitted_repo)
    after_admit = _k3e_snapshot(admitted_repo)
    assert admitted["admitted"] is True
    assert before_admit == after_admit


def test_k3e_eval1_committed_preregistration_is_schema_valid_and_waits_for_owner_acceptance(
    tmp_path: Path,
):
    raw = (_K3E_ROOT / _K3E_EVAL1).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    assert payload["registration_id"] == "K3E-EVAL-1-V1"
    assert _registration_reason(payload) is None
    assert _canonical_json_digest(raw) == _K3E_EVAL1_COMMITTED_DIGEST
    assert payload["predecessor"]["canonical_digest_sha256"] == EVAL0_CANONICAL_DIGEST
    assert payload["predecessor"]["prior_trial_budget_reset"] is False

    repo = _k3e_source_repo(tmp_path)
    target = repo / _K3E_EVAL1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    _k3e_commit_main(repo, "freeze committed EVAL-1 preregistration bytes")
    result = inspect_eval1_admission(repo, as_of_date=date(2026, 10, 4))
    assert result["admitted"] is False
    assert result["outcome_access_allowed"] is False
    assert result["reasons"] == ["OWNER_ACCEPTANCE_MISSING"]
    assert result["eval0"] == {
        "registration_id": "K3E-EVAL-0-V1",
        "canonical_digest": EVAL0_CANONICAL_DIGEST,
        "preserved": True,
    }


def test_k3e_eval1_forward_t1_constants_match_registration():
    assert k3e_fwd.BOOTSTRAP_SEED == int(k3e_fwd.REGISTRATION_DIGEST[:8], 16) == 480336034
    assert k3e_fwd.BOOTSTRAP_REPLICATES == 19999
    assert k3e_fwd.REGISTRATION_DIGEST == _K3E_EVAL1_COMMITTED_DIGEST
    raw = (_K3E_ROOT / _K3E_EVAL1).read_bytes()
    assert _canonical_json_digest(raw) == k3e_fwd.REGISTRATION_DIGEST
    harmonic = sum(1.0 / i for i in range(1, 65))
    assert (1.0 / (k3e_fwd.BOOTSTRAP_REPLICATES + 1)) < 0.10 / (64 * harmonic)


def test_k3e_eval1_forward_t2_frozen_term_mismatches():
    import copy

    raw = (_K3E_ROOT / _K3E_EVAL1).read_bytes()
    registration = json.loads(raw.decode("utf-8"))
    assert k3e_fwd.frozen_term_mismatches(registration) == []
    bad_h = copy.deepcopy(registration)
    bad_h["scientific_freeze"]["primary_horizon_sessions"] = 22
    assert "primary_horizon_sessions" in k3e_fwd.frozen_term_mismatches(bad_h)
    bad_q = copy.deepcopy(registration)
    bad_q["multiple_testing"]["q"] = 0.05
    assert "by_q" in k3e_fwd.frozen_term_mismatches(bad_q)


def test_k3e_eval1_forward_t3_t1_label():
    cv = 1.0
    cs = 100
    assert k3e_fwd.t1_label(cs, cv, [(105, 1.0, True), (110, 1.2, True)], 200) == (
        "UP",
        None,
    )
    assert k3e_fwd.t1_label(cs, cv, [(110, 0.9, True)], 200) == ("DOWN", None)
    assert k3e_fwd.t1_label(cs, cv, [(121, 1.0, True)], 200) == ("FLAT", None)
    assert k3e_fwd.t1_label(cs, cv, [(130, 1.0, True)], 200) == ("FLAT", None)
    assert k3e_fwd.t1_label(cs, cv, [(130, 1.1, True)], 200) == (
        "CENSORED",
        "change_after_horizon_before_unchanged_snapshot",
    )
    assert k3e_fwd.t1_label(cs, cv, [(130, None, False), (140, None, False)], 200) == (
        "CENSORED",
        "no_successful_snapshot_in_flat_window",
    )
    assert k3e_fwd.t1_label(cs, cv, [(110, 1.2, True)], 105) == (
        "PENDING",
        "horizon_not_reached",
    )
    assert k3e_fwd.t1_label(cs, cv, [], 130) == ("PENDING", "flat_window_open")
    assert k3e_fwd.t1_label(cs, cv, [(90, 2.0, True), (100, 2.0, True)], 200) == (
        "CENSORED",
        "no_successful_snapshot_in_flat_window",
    )
    assert k3e_fwd.t1_label(cs, cv, [(164, 1.0, True)], 200) == (
        "CENSORED",
        "no_successful_snapshot_in_flat_window",
    )
    assert k3e_fwd.t1_label(cs, cv, [(163, 1.0, True)], 200) == ("FLAT", None)
    with pytest.raises(ValueError):
        k3e_fwd.t1_label(cs, float("nan"), [], 200)


def test_k3e_eval1_forward_t4_loss_metrics():
    import math

    row = [(0.5, 0.25, 0.25)]
    assert k3e_fwd.row_log_losses(row, ["UP"])[0] == pytest.approx(math.log(2))
    assert k3e_fwd.row_log_losses([(0.0, 0.5, 0.5)], ["UP"])[0] == math.inf
    with pytest.raises(ValueError):
        k3e_fwd.row_log_losses([(0.5, 0.2, 0.2)], ["UP"])
    with pytest.raises(ValueError):
        k3e_fwd.row_log_losses(row, ["SIDEWAYS"])
    assert k3e_fwd.brier_score([(1.0, 0.0, 0.0)], ["UP"]) == 0.0
    assert k3e_fwd.brier_score(row, ["UP"]) == pytest.approx(0.375)


def test_k3e_eval1_forward_t5_baselines():
    assert k3e_fwd.fit_b0_no_change(["UP", "DOWN", "FLAT", "FLAT"]) == pytest.approx(
        (0.25, 0.25, 0.5)
    )
    assert k3e_fwd.fit_b0_no_change(["FLAT", "FLAT"]) is None
    assert k3e_fwd.fit_b0_no_change(["UP", "DOWN"]) is None
    assert k3e_fwd.fit_b0_no_change([]) is None
    rows = [
        ("eps", "UP"),
        ("eps", "DOWN"),
        ("eps", "FLAT"),
        ("rev", "UP"),
        ("rev", "DOWN"),
        ("rev", "FLAT"),
        ("rev", "FLAT"),
    ]
    model = k3e_fwd.fit_b6_base_rate(rows)
    assert model is not None
    assert model["eps"] == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert model["rev"] == pytest.approx((0.25, 0.25, 0.5))
    assert k3e_fwd.fit_b6_base_rate([("m", "UP"), ("m", "UP")]) is None
    assert k3e_fwd.score_b6(model, [("missing", "UP")]) is None


def test_k3e_eval1_forward_t6_strongest_baseline_and_relative_improvement():
    import math

    assert k3e_fwd.strongest_baseline(
        {"B0_NO_CHANGE": 0.9, "B6_HISTORICAL_BASE_RATE": 0.8}
    ) == ("B6_HISTORICAL_BASE_RATE", 0.8)
    assert k3e_fwd.strongest_baseline(
        {"B0_NO_CHANGE": None, "B6_HISTORICAL_BASE_RATE": None}
    ) == (None, None)
    with pytest.raises(ValueError):
        k3e_fwd.strongest_baseline({"B1": 0.5})
    assert k3e_fwd.relative_improvement(1.0, 0.95) == pytest.approx(0.05)
    assert k3e_fwd.relative_improvement(None, 0.5) is None
    assert k3e_fwd.relative_improvement(1.0, math.inf) == -math.inf


def test_k3e_eval1_forward_t7_cluster_bootstrap():
    import math

    diffs: list[float] = []
    clusters: list[str] = []
    for i in range(40):
        key = f"c{i:02d}"
        for row in range(3):
            diffs.append(0.1 + 0.01 * (i % 5) + 0.001 * row)
            clusters.append(key)
    a = k3e_fwd.cluster_bootstrap(diffs, clusters)
    b = k3e_fwd.cluster_bootstrap(diffs, clusters)
    assert a == b
    assert a["p_value"] == pytest.approx(1 / 20000)
    assert a["excludes_zero"] is True
    assert a["replicates"] == 19999
    assert a["seed"] == 480336034

    sym_diffs: list[float] = []
    sym_clusters: list[str] = []
    for i in range(40):
        sign = 0.2 if i % 2 == 0 else -0.2
        key = f"s{i:02d}"
        for _ in range(3):
            sym_diffs.append(sign)
            sym_clusters.append(key)
    sym = k3e_fwd.cluster_bootstrap(sym_diffs, sym_clusters, replicates=1999)
    assert sym["excludes_zero"] is False
    assert sym["p_value"] > 0.05

    one = k3e_fwd.cluster_bootstrap([0.1, 0.2], ["a", "a"])
    assert one["ci_low"] == one["ci_high"] == one["mean"]

    with pytest.raises(ValueError):
        k3e_fwd.cluster_bootstrap([0.1], ["a", "b"])
    with pytest.raises(ValueError):
        k3e_fwd.cluster_bootstrap([math.inf], ["a"])


def test_k3e_eval1_forward_t8_cluster_helpers():
    assert k3e_fwd.cluster_key("AAPL", None, None) == "issuer:AAPL"
    assert k3e_fwd.cluster_key("AAPL", "e1", None) == "issuer:AAPL|episode:e1|event:"
    with pytest.raises(ValueError):
        k3e_fwd.cluster_key("", None, None)
    assert k3e_fwd.date_block_keys([10, 72, 73, 140]) == [
        "block:0",
        "block:0",
        "block:1",
        "block:2",
    ]
    expected = hashlib.sha256(
        json.dumps(
            ["AAPL", "eps", "2026Q3", "2026-10-08"],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert (
        k3e_fwd.episode_id("AAPL", "eps", "2026Q3", "2026-10-08") == expected
    )
    assert (
        k3e_fwd.episode_id("AAPL", "eps", "2026Q3", "2026-10-09")
        != expected
    )


def test_k3e_eval1_forward_t9_by_family_decision():
    assert k3e_fwd.by_family_decision([5e-5] + [0.5] * 63)["rejected"][0] is True
    assert k3e_fwd.by_family_decision([4e-4] + [0.9] * 63)["rejected"][0] is False


def test_k3e_eval1_forward_t10_assign_partitions():
    boundary = 1000

    def _rows_dev_100():
        return [(s, f"ep{s}", s) for s in range(1000, 1100)]

    full = _rows_dev_100()
    out = k3e_fwd.assign_partitions(full, boundary)
    assert out["closes"]["F_DEV"] == 1099
    assert out["status"]["F_DEV"] == "CLOSED"

    with_purge = full + [(1100, "x", 1100), (1162, "y", 1162), (1163, "z", 1163)]
    p = k3e_fwd.assign_partitions(with_purge, boundary)
    assert p["partitions"][-3:] == ["PURGE_1", "PURGE_1", "F_VAL"]

    pre = k3e_fwd.assign_partitions([(999, "e", 999)], boundary)
    assert pre["partitions"] == [k3e_fwd.PRE_BOUNDARY]

    val_rows = _rows_dev_100() + [(1100, "p1", 1100)]
    val_rows += [(1163 + i, f"v{i}", 1163 + i) for i in range(100)]
    val_rows.append((1200, "old", 1150))
    p2 = k3e_fwd.assign_partitions(val_rows, boundary)
    idx_old = val_rows.index((1200, "old", 1150))
    assert p2["excluded"][idx_old] == "episode_started_before_partition"

    short = [(1000 + i, f"s{i}", 1000 + i) for i in range(99)]
    ps = k3e_fwd.assign_partitions(short, boundary)
    assert ps["status"]["F_DEV"] == "OPEN"
    assert ps["status"]["F_VAL"] == "NOT_STARTED"

    chain: list[tuple[int, str | None, int | None]] = []
    for start in (1000, 1163, 1326):
        chain.extend((start + i, f"e{start}_{i}", start + i) for i in range(100))
    chain.append((1426, "shadow", 1426))
    pc = k3e_fwd.assign_partitions(chain, boundary)
    assert pc["closes"]["F_VAL"] == 1262
    assert pc["closes"]["F_HOLD"] == 1425
    assert pc["partitions"][-1] == "PROSPECTIVE_SHADOW"

    dup = [(1000, "same", 1000), (1001, "same", 1001)]
    dup += [(1000 + i, f"u{i}", 1000 + i) for i in range(2, 100)]
    pd = k3e_fwd.assign_partitions(dup, boundary)
    assert pd["episode_counts"]["F_DEV"] == 99

    shuffled = list(reversed(_rows_dev_100()))
    psf = k3e_fwd.assign_partitions(shuffled, boundary)
    full_map = dict(zip(full, out["partitions"]))
    for row, part in zip(shuffled, psf["partitions"]):
        assert part == full_map[row]


def test_k3e_eval1_forward_t11_coverage():
    statuses = ["SCORED"] * 6 + ["CENSORED:x"] * 4
    ok = k3e_fwd.coverage_summary(statuses, challenger_abstained=4)
    assert ok["unestimable"] is False
    bad_abs = k3e_fwd.coverage_summary(statuses, challenger_abstained=5)
    assert bad_abs["unestimable"] is True
    half = k3e_fwd.coverage_summary(["SCORED"] * 5 + ["X"] * 5, challenger_abstained=0)
    assert half["unestimable"] is True
    empty = k3e_fwd.coverage_summary([], challenger_abstained=0)
    assert empty["unestimable"] is True
    assert empty["scored_fraction"] is None
    assert k3e_fwd.case_coverage(3)["met"] is True
    assert k3e_fwd.case_coverage(2)["met"] is False
    with pytest.raises(ValueError):
        k3e_fwd.case_coverage(5)


def test_k3e_eval1_forward_t12_static_io_guard():
    source = (_K3E_ROOT / "engine/k3e_eval1_forward.py").read_text(encoding="utf-8")
    forbidden = (
        "data/",
        "site/",
        "read_parquet",
        "read_csv",
        "open(",
        "subprocess",
        "import os",
        "pathlib",
        "pandas",
    )
    for needle in forbidden:
        assert needle not in source


def test_k3e_eval1_forward_t7b_cluster_sum_is_exact_fsum():
    out = k3e_fwd.cluster_bootstrap([1e16, 1.0, -1e16], ["a", "a", "a"], replicates=99)
    assert out["mean"] == 1.0 / 3.0
    assert out["ci_low"] == out["ci_high"] == 1.0 / 3.0


def test_k3e_eval1_forward_t2b_one_try_per_check():
    import copy

    raw = (_K3E_ROOT / _K3E_EVAL1).read_bytes()
    registration = json.loads(raw.decode("utf-8"))
    bad_q = copy.deepcopy(registration)
    del bad_q["multiple_testing"]["q"]
    assert k3e_fwd.frozen_term_mismatches(bad_q) == ["by_q"]
    bad_outer = copy.deepcopy(registration)
    del bad_outer["scientific_freeze"]["censoring_rule"]
    assert k3e_fwd.frozen_term_mismatches(bad_outer) == ["outer_window"]
    bad_cov = copy.deepcopy(registration)
    del bad_cov["scientific_freeze"]["coverage_rule"]
    assert k3e_fwd.frozen_term_mismatches(bad_cov) == [
        "case_coverage_floor",
        "max_challenger_abstention",
        "scored_fraction_floor",
    ]


# T12 exposes the existing metric owner to the existing Agent OS boundary.
def _research_registry(*families):
    return {"schema": "intelligence_registry.v1", "engines": [
        {"engine_id": f"engine/{f}.py::owner-{f}", "producer": f"engine/{f}.py",
         "owner_program": f"owner-{f}", "ledger": f"qledger:{f}",
         "ledger_evidence": {"rule": 2, "desk": f}}
        for f in families], "excluded": []}


def test_research_findings_project_two_explicit_metric_owner_findings():
    from engine.qledger_validity import project_research_findings
    claims = [_claim("mixed", "a", 1), _claim("mixed", "b", -1), _claim("salience", "c", 0)]
    metrics = {"mixed": {"excess_mean"}, "salience": {"hit_rate"}}
    registry = _research_registry("mixed", "salience")
    before = json.dumps([claims, registry], sort_keys=True)
    result = project_research_findings(claims, [], reported_metrics=metrics, registry=registry, evidence_link="research/evidence/synthetic-audit.json")
    assert result["evaluation_status"] == "not_assessed"
    assert not result["unresolved"]
    assert [(x["segment"], x["metric"], x["suggested_tier"]) for x in result["issues"]] == [("mixed", "excess_mean", "T0"), ("salience", "hit_rate", "T0")]
    for issue, owner in zip(result["issues"], audit(claims, [], reported_metrics=metrics)):
        assert set(issue) == {"engine", "metric", "observed_change", "segment", "evidence_link", "suggested_tier"}
        assert issue["observed_change"] == "Snapshot of intended-report metric validity: " + owner.detail
        assert issue["engine"] == f"engine/{owner.family}.py::owner-{owner.family}"
    assert json.dumps([claims, registry], sort_keys=True) == before


@pytest.mark.parametrize("metrics", [None, {}, {"m": None}, {"m": ["excess_mean"]}])
def test_research_findings_require_explicit_per_family_metric_scope(metrics):
    from engine.qledger_validity import project_research_findings
    with pytest.raises(ValueError):
        project_research_findings([_claim("m", "a", 1), _claim("m", "b", -1)], [], reported_metrics=metrics, registry=_research_registry("m"), evidence_link="research/evidence/x.json")


def test_research_findings_empty_descriptive_scope_emits_no_issue():
    from engine.qledger_validity import project_research_findings
    result = project_research_findings([_claim("m", "a", 1), _claim("m", "b", -1)], [], reported_metrics={"m": set()}, registry=_research_registry("m"), evidence_link="research/evidence/x.json")
    assert result["issues"] == [] and result["unresolved"] == []


@pytest.mark.parametrize("damage", ["missing", "ambiguous", "excluded", "wrong_id", "weak_binding"])
def test_research_findings_do_not_guess_engine_binding(damage):
    from copy import deepcopy
    from engine.qledger_validity import project_research_findings
    registry = _research_registry("m")
    row = registry["engines"][0]
    if damage == "missing": registry["engines"] = []
    if damage == "ambiguous": registry["engines"].append(deepcopy(row))
    if damage == "excluded":
        registry["excluded"] = [{"engine_id": row["engine_id"], "would_be_ledger": "qledger:m"}]
        registry["engines"] = []
    if damage == "wrong_id": row["engine_id"] = "invented"
    if damage == "weak_binding": row["ledger_evidence"]["rule"] = 1
    result = project_research_findings([_claim("m", "a", 1), _claim("m", "b", -1)], [], reported_metrics={"m": {"excess_mean"}}, registry=registry, evidence_link="research/evidence/x.json")
    assert result["issues"] == [] and result["unresolved"]


def test_research_findings_preserve_off_horizon_as_unsupported_note():
    from engine.qledger_validity import project_research_findings
    result = project_research_findings([_claim("m", "a", 1, horizon=63)], [_grade("a", 5)], reported_metrics={"m": {"hit_rate"}}, registry=_research_registry("m"), evidence_link="research/evidence/x.json")
    assert result["issues"] == []
    assert result["unresolved"][0]["code"] == "OFF_HORIZON_VERDICT"
    assert result["unresolved"][0]["reason"] == "unsupported_owner_finding"


@pytest.mark.parametrize("link", [None, "", "x" * 2049, "\ud800"])
def test_research_findings_require_bounded_evidence_locator(link):
    from engine.qledger_validity import project_research_findings
    with pytest.raises(ValueError):
        project_research_findings([], [], reported_metrics={}, registry=_research_registry(), evidence_link=link)



def test_research_findings_real_registry_to_existing_discovery_consumer(monkeypatch):
    import socket
    from scripts import agentos
    from engine.intelligence_registry import build_registry, DeskScan
    from engine.qledger_validity import project_research_findings
    producer = "engine/synthetic_owner.py"
    registry = build_registry(synapse={"meta": {"schema_version": 1}, "artifacts": {"example": {
        "path": "data/synthetic-output.json", "format": "json", "producer": producer,
        "owner_program": "synthetic-owner", "cadence": "daily-engine", "storage": "git",
        "asof_field": "asof", "freshness_sla_hours": 24, "schema": "example",
        "tier": "display", "horizon_role": "context", "consumers": []}}},
        desk_scans={producer: DeskScan(imports_qledger=True, desks=("mixed",), unresolved=False)})
    def refuse_io(*args, **kwargs):
        raise AssertionError("pure finding projection must not do I/O")
    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", refuse_io)
        patch.setattr(socket, "socket", refuse_io)
        result = project_research_findings([_claim("mixed", "a", 1), _claim("mixed", "b", -1)], [], reported_metrics={"mixed": {"excess_mean"}}, registry=registry, evidence_link="research/evidence/synthetic-owner.json")
        assert len(result["issues"]) == 1 and not result["unresolved"]
        finding = result["issues"][0]
        payload = {"key": "SYNTHETIC-METRIC-FINDING", "claim": "The synthetic mixed-direction family cannot report pooled signed excess.", "falsifier": "pytest tests/test_qledger_validity.py -k research_findings", "so_what": "Use a legal metric for this synthetic report.", "kind": "data", "verified_at": "2026-10-14", "verified_by": "tests/test_qledger_validity.py:1", "scope": ["synthetic-owner"], "confidence": "verified", "evaluation_finding": finding}
        text = agentos.draft_discovery(payload)
        record = agentos.yaml.safe_load(text.split("---", 2)[1])
        assert record["evaluation_finding"] == finding
        assert not [p for p in agentos.check_discovery(record, Path("DSC-SYNTHETIC-METRIC-FINDING.md")) if p.hard]
        payload.pop("falsifier")
        with pytest.raises(SystemExit):
            agentos.draft_discovery(payload)


def test_research_findings_unassessed_scope_cannot_look_clear():
    from engine.qledger_validity import project_research_findings
    result = project_research_findings([_claim("m", "a", 1)], [], reported_metrics={"m": {"accuracy"}, "absent": {"hit_rate"}}, registry=_research_registry("m"), evidence_link="research/evidence/x.json")
    assert result["issues"] == []
    assert {x["reason"] for x in result["unresolved"]} == {"unsupported_metric", "family_has_no_claims"}


def test_research_findings_metric_integrity_does_not_depend_on_engine_authority():
    from engine.qledger_validity import project_research_findings
    registry = _research_registry("m")
    registry["engines"][0]["authority"] = "gate_size"
    result = project_research_findings([_claim("m", "a", 1), _claim("m", "b", -1)], [], reported_metrics={"m": {"excess_mean"}}, registry=registry, evidence_link="research/evidence/x.json")
    assert result["issues"][0]["suggested_tier"] == "T0"


# --------------------------------------------------------------------------- #
# T12 CLI consumer — `check_qledger_metric_validity.py --project-findings`.
#
# The pure producer above had no bounded caller route. The mode reads ONE
# caller-supplied regular JSON file, delegates every semantic to the pure
# owner, and prints a snapshot. It must never touch the live claim/grade
# stores, fetch registry inputs or dereference evidence_link — the tests wire
# I/O refusals in to prove the absence rather than trusting the output. A
# refused input exits 2 with a null result: "could not look" must never render
# as "looked and clean" (§9.2), and never as a traceback or echoed input.
# --------------------------------------------------------------------------- #
_PROJECT_FINDINGS_MAX_BYTES = 16 * 1024 * 1024


def _research_input(
    *,
    claims=None,
    grades=None,
    metrics=None,
    registry="default",
    evidence_link="research/evidence/synthetic-cli.json",
    schema="qledger.research_findings_input.v1",
    extra=None,
    drop=(),
):
    document = {
        "schema": schema,
        "claims": [_claim("mixed", "a", 1), _claim("mixed", "b", -1)] if claims is None else claims,
        "grades": [] if grades is None else grades,
        "reported_metrics": {"mixed": ["excess_mean"]} if metrics is None else metrics,
        "registry": _research_registry("mixed") if registry == "default" else registry,
        "evidence_link": evidence_link,
    }
    document.update(extra or {})
    for key in drop:
        del document[key]
    return document


def _run_project_findings(monkeypatch, capsys, extra_argv):
    import sys

    cli = _load_cli()
    monkeypatch.setattr(sys, "argv", ["check_qledger_metric_validity", *extra_argv])
    code = cli.main()
    out = capsys.readouterr().out
    return code, (json.loads(out) if out.strip() else None), out


def _malformed_cases():
    def raw(document):
        return json.dumps(document).encode("utf-8")

    return {
        # JSON layer refusals — a document that cannot be parsed as bounded
        # strict JSON is unknown, never an empty projection.
        "not_json": (b"TELLTALE-NOT-JSON {{{", "input_not_json"),
        "bad_utf8": (b"{\xff not utf-8 \xfe}", "input_not_utf8"),
        "duplicate_key": (b'{"evidence_link": "a", "evidence_link": "b"}', "duplicate_json_key"),
        "non_finite_constant": (
            json.dumps(_research_input(claims=[], grades=[])).replace('"claims": []', '"claims": [NaN]').encode("utf-8"),
            "non_finite_json_constant",
        ),
        # Schema/shape refusals — decided before the pure owner is called.
        "document_not_object": (b"[1, 2]", "input_schema_invalid"),
        "wrong_schema": (raw(_research_input(schema="not.the.schema.v1")), "input_schema_invalid"),
        "extra_key": (raw(_research_input(extra={"surprise": 1})), "input_schema_invalid"),
        "missing_key": (raw(_research_input(drop=("grades",))), "input_schema_invalid"),
        "claims_not_list": (raw(_research_input(claims={"mixed": _claim("mixed", "a", 1)})), "input_schema_invalid"),
        "claim_not_object": (raw(_research_input(claims=[42])), "input_schema_invalid"),
        "grades_not_list": (raw(_research_input(grades={"a": 5})), "input_schema_invalid"),
        "grade_not_object": (raw(_research_input(grades=["a"])), "input_schema_invalid"),
        "metrics_not_object": (raw(_research_input(metrics=["mixed"])), "input_schema_invalid"),
        "metrics_value_not_list": (raw(_research_input(metrics={"mixed": "excess_mean"})), "input_schema_invalid"),
        "metric_not_string": (raw(_research_input(metrics={"mixed": [7]})), "input_schema_invalid"),
        "registry_not_object": (raw(_research_input(registry=[])), "input_schema_invalid"),
        "evidence_link_not_string": (raw(_research_input(evidence_link=17)), "input_schema_invalid"),
    }


def test_project_findings_valid_input_returns_the_unchanged_pure_result(tmp_path, monkeypatch, capsys):
    """Arrays become sets at the boundary; the result is the owner's, byte for byte."""
    from engine.qledger_validity import project_research_findings as pure

    raw = json.dumps(_research_input()).encode("utf-8")
    source = tmp_path / "findings-input.json"
    source.write_bytes(raw)
    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 0
    assert set(out) == {"schema", "input", "result", "error"}
    assert out["schema"] == "qledger.research_findings_cli.v1"
    assert out["input"]["bytes"] == len(raw)
    assert out["input"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert out["error"] is None
    expected = pure(
        _research_input()["claims"],
        [],
        reported_metrics={"mixed": {"excess_mean"}},
        registry=_research_input()["registry"],
        evidence_link="research/evidence/synthetic-cli.json",
    )
    assert out["result"] == expected
    assert [(i["segment"], i["metric"], i["suggested_tier"]) for i in out["result"]["issues"]] == [
        ("mixed", "excess_mean", "T0")
    ]


def test_project_findings_issue_reaches_the_existing_discovery_draft_and_validator(
    tmp_path, monkeypatch, capsys
):
    """The CLI issue is the same typed payload the existing draft/validator consume."""
    import socket
    import sys

    from scripts import agentos

    source = tmp_path / "findings-input.json"
    source.write_bytes(json.dumps(_research_input()).encode("utf-8"))
    # --json is redundant in this mode, not a conflict: the mode only speaks JSON.
    code, out, _ = _run_project_findings(
        monkeypatch, capsys, ["--project-findings", str(source), "--json"]
    )
    assert code == 0
    finding = out["result"]["issues"][0]
    payload = {
        "key": "SYNTHETIC-CLI-FINDING",
        "claim": "The synthetic mixed-direction family cannot report pooled signed excess.",
        "falsifier": "pytest tests/test_qledger_validity.py -k project_findings",
        "so_what": "Use a legal metric for this synthetic report.",
        "kind": "data",
        "verified_at": "2026-10-14",
        "verified_by": "tests/test_qledger_validity.py:1",
        "scope": ["synthetic-cli"],
        "confidence": "verified",
        "evaluation_finding": finding,
    }

    def refuse_io(*args, **kwargs):
        raise AssertionError("snapshot emission must not do I/O")

    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", refuse_io)
        patch.setattr(socket, "socket", refuse_io)
        text = agentos.draft_discovery(payload)
        record = agentos.yaml.safe_load(text.split("---", 2)[1])
        assert record["evaluation_finding"] == finding
        assert not [p for p in agentos.check_discovery(record, Path("DSC-SYNTHETIC-CLI-FINDING.md")) if p.hard]


@pytest.mark.parametrize("case", sorted(_malformed_cases()))
def test_project_findings_refuses_malformed_input_as_unknown(tmp_path, monkeypatch, capsys, case):
    import sys

    raw, expected_code = _malformed_cases()[case]
    source = tmp_path / "bad.json"
    source.write_bytes(raw)
    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 2
    assert out["schema"] == "qledger.research_findings_cli.v1"
    assert out["result"] is None  # unknown — never an empty clean finding set
    assert out["error"]["code"] == expected_code
    assert out["error"]["message"]


def test_project_findings_failure_never_echoes_the_input(tmp_path, monkeypatch, capsys):
    import sys

    source = tmp_path / "tell.json"
    source.write_bytes(b"TELLTALE-INPUT-CONTENT { not json")
    code, out, text = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 2 and out["result"] is None
    assert "TELLTALE-INPUT-CONTENT" not in text


def test_project_findings_surrogate_locator_is_owner_refused_not_crashed(tmp_path, monkeypatch, capsys):
    """A JSON-escaped lone surrogate is valid JSON and a str; the owner refuses it.

    The mode must surface the pure owner's refusal as the same bounded exit-2
    shape rather than letting it become a traceback.
    """
    source = tmp_path / "surrogate.json"
    source.write_bytes(json.dumps(_research_input(evidence_link="\ud800")).encode("utf-8"))
    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 2
    assert out["result"] is None
    assert out["error"]["code"] == "engine_refused_input"


def test_project_findings_absent_input_is_unknown_not_clean(tmp_path, monkeypatch, capsys):
    code, out, _ = _run_project_findings(
        monkeypatch, capsys, ["--project-findings", str(tmp_path / "absent.json")]
    )
    assert code == 2
    assert out["result"] is None
    assert out["error"]["code"] == "input_missing"


def test_project_findings_refuses_oversized_and_non_regular_input(tmp_path, monkeypatch, capsys):
    over = tmp_path / "over.json"
    over.write_bytes(b" " * (_PROJECT_FINDINGS_MAX_BYTES + 1))
    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(over)])
    assert code == 2 and out["result"] is None
    assert out["error"]["code"] == "input_too_large"

    # The bound is inclusive: a valid document padded to exactly 16 MiB projects.
    raw = json.dumps(_research_input()).encode("utf-8")
    at_bound = tmp_path / "at-bound.json"
    at_bound.write_bytes(raw + b" " * (_PROJECT_FINDINGS_MAX_BYTES - len(raw)))
    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(at_bound)])
    assert code == 0
    assert out["input"]["bytes"] == _PROJECT_FINDINGS_MAX_BYTES

    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(tmp_path)])
    assert code == 2 and out["result"] is None
    assert out["error"]["code"] == "input_not_regular_file"

    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", "/dev/null"])
    assert code == 2 and out["result"] is None
    assert out["error"]["code"] == "input_not_regular_file"


@pytest.mark.skipif(os.geteuid() == 0, reason="mode-000 does not block root")
def test_project_findings_refuses_unreadable_input(tmp_path, monkeypatch, capsys):
    source = tmp_path / "locked.json"
    source.write_bytes(json.dumps(_research_input()).encode("utf-8"))
    source.chmod(0o000)
    code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 2 and out["result"] is None
    assert out["error"]["code"] == "input_unreadable"


@pytest.mark.parametrize("extra", [["--strict"], ["--selftest"], ["--root", "/tmp"], ["--strict", "--json"]])
def test_project_findings_mode_conflicts_fail_before_any_read(tmp_path, monkeypatch, capsys, extra):
    """The path is deliberately absent: a conflict is diagnosed BEFORE the read.

    If the mode opened the file first, this would surface as input_missing;
    mode_conflict proves the refusal happened first.
    """
    absent = tmp_path / "never-read.json"
    code, out, _ = _run_project_findings(
        monkeypatch, capsys, ["--project-findings", str(absent), *extra]
    )
    assert code == 2
    assert out["result"] is None
    assert out["error"]["code"] == "mode_conflict"


def test_project_findings_refuses_input_that_moves_while_reading(tmp_path, monkeypatch, capsys):
    """The post-read fstat must refuse a moved input — and claim no atomicity."""
    from types import SimpleNamespace

    source = tmp_path / "moving.json"
    source.write_bytes(json.dumps(_research_input()).encode("utf-8"))
    cli = _load_cli()
    real_fstat = os.fstat
    seen = []

    def fstat(fd):
        st = real_fstat(fd)
        seen.append(1)
        if len(seen) == 2:  # the post-read re-check sees a different size
            return SimpleNamespace(
                st_mode=st.st_mode,
                st_ino=st.st_ino,
                st_dev=st.st_dev,
                st_size=st.st_size + 1,
                st_mtime_ns=st.st_mtime_ns,
                st_ctime_ns=st.st_ctime_ns,
            )
        return st

    with monkeypatch.context() as patch:
        patch.setattr(cli.os, "fstat", fstat)
        code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 2
    assert out["result"] is None
    assert out["error"]["code"] == "input_changed_during_read"


def test_project_findings_reads_only_the_supplied_file(tmp_path, monkeypatch, capsys):
    """Wire refusals into every live-store/provider path the default mode uses.

    The patches, not the disk, decide the outcome here — so a pass proves the
    mode never reached a claim store, grade store, registry builder or socket.
    """
    import socket
    import urllib.request

    import engine.intelligence_registry
    import engine.qledger_store

    source = tmp_path / "findings-input.json"
    source.write_bytes(json.dumps(_research_input()).encode("utf-8"))

    def refuse(what):
        def _refuse(*args, **kwargs):
            raise AssertionError(f"--project-findings must not {what}")

        return _refuse

    with monkeypatch.context() as patch:
        patch.setattr(engine.qledger_store, "uses_native_claims", refuse("read the live claim store"))
        patch.setattr(engine.qledger_store, "open_raw_lines", refuse("read the live claim store"))
        patch.setattr(engine.intelligence_registry, "build_registry", refuse("derive registry inputs"))
        patch.setattr(socket, "socket", refuse("open a network socket"))
        patch.setattr(urllib.request, "urlopen", refuse("fetch registry inputs"))
        code, out, _ = _run_project_findings(monkeypatch, capsys, ["--project-findings", str(source)])
    assert code == 0
    assert out["result"]["schema"] == "qledger.research_findings.v1"
    assert [(i["segment"], i["metric"]) for i in out["result"]["issues"]] == [("mixed", "excess_mean")]


def test_existing_selftest_and_default_modes_are_untouched(tmp_path, monkeypatch, capsys):
    """--selftest alone and the default/--root/--strict/--json store audit keep
    their existing contracts; the new flag changes nothing about them."""
    import sys

    cli = _load_cli()
    monkeypatch.setattr(sys, "argv", ["check_qledger_metric_validity", "--selftest"])
    assert cli.main() == 0
    capsys.readouterr()

    store = tmp_path / "data" / "qledger"
    store.mkdir(parents=True)
    claims = [_claim("mixed", "a", 1), _claim("mixed", "b", -1)]
    grades = [_grade("a", 5), _grade("b", 5)]
    (store / "claims.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in claims), encoding="utf-8"
    )
    (store / "grades.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in grades), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["check_qledger_metric_validity", "--root", str(tmp_path), "--json"])
    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["store_absent"] is False
    assert [f["code"] for f in payload["findings"]] == ["SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS"]
    monkeypatch.setattr(
        sys, "argv", ["check_qledger_metric_validity", "--root", str(tmp_path), "--json", "--strict"]
    )
    assert cli.main() == 1
    capsys.readouterr()


@pytest.mark.parametrize('field,value', [('claim_family', []), ('claim_id', []), ('direction', 1e300)])
def test_project_findings_malformed_row_is_structured_unknown(tmp_path, monkeypatch, capsys, field, value):
    document = _research_input()
    document['claims'][0][field] = value
    if field == 'direction':
        # Literal numeric overflow is not handled by json.parse_constant.
        raw = json.dumps(document).replace('1e+300', '1e999').encode()
    else:
        raw = json.dumps(document).encode()
    source = tmp_path / 'malformed-row.json'
    source.write_bytes(raw)
    code, out, _ = _run_project_findings(monkeypatch, capsys, ['--project-findings', str(source)])
    assert code == 2 and out['result'] is None


def test_project_findings_duplicate_key_does_not_echo_input(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'duplicate.json'
    source.write_bytes(b'{"PRIVATE-INPUT-MARKER":1,"PRIVATE-INPUT-MARKER":2}')
    code, out, text = _run_project_findings(monkeypatch, capsys, ['--project-findings', str(source)])
    assert code == 2 and out['result'] is None
    assert 'PRIVATE-INPUT-MARKER' not in text


def test_project_findings_refusal_closes_open_descriptor(tmp_path, monkeypatch, capsys):
    cli = _load_cli()
    original = cli.os.open
    descriptors = []
    def capture(*args, **kwargs):
        fd = original(*args, **kwargs)
        descriptors.append(fd)
        return fd
    with monkeypatch.context() as patch:
        patch.setattr(cli.os, 'open', capture)
        code, out, _ = _run_project_findings(monkeypatch, capsys, ['--project-findings', str(tmp_path)])
    assert code == 2 and out['result'] is None
    assert len(descriptors) == 1
    try:
        with pytest.raises(OSError):
            os.fstat(descriptors[0])
    finally:
        try:
            os.close(descriptors[0])
        except OSError:
            pass


def test_project_findings_replaced_path_is_unknown(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'moving-path.json'
    source.write_bytes(json.dumps(_research_input()).encode())
    replacement = tmp_path / 'replacement.json'
    replacement.write_bytes(json.dumps(_research_input(claims=[])).encode())
    cli = _load_cli()
    original = cli.os.fstat
    calls = []
    def replace_path(fd):
        result = original(fd)
        calls.append(fd)
        if len(calls) == 2:
            replacement.replace(source)
        return result
    with monkeypatch.context() as patch:
        patch.setattr(cli.os, 'fstat', replace_path)
        code, out, _ = _run_project_findings(monkeypatch, capsys, ['--project-findings', str(source)])
    assert code == 2 and out['result'] is None
    assert out['error']['code'] == 'input_changed_during_read'
