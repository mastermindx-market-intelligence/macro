"""Fail-closed K3E EVAL-1 admission inspection over accepted Git source.

This module does not grade outcomes, register trials, activate a protocol, or replace
Eval OS / QLedger. It answers one narrower question before any K3E EVAL-1 outcome
reader is allowed to start: do the accepted-main source records establish an
admitted, versioned successor to immutable EVAL-0?

The default source is refs/remotes/origin/main. Working-tree bytes never grant
admission. Missing or malformed records refuse.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from lib.nyse_calendar import ET, is_session


MAIN_REF = "refs/remotes/origin/main"
BASE = "research/alpha_intelligence/expectation_market_dynamics"
EVAL0_PATH = f"{BASE}/eval0_preregistration.v1.json"
EVAL1_PATH = f"{BASE}/eval1_preregistration.v1.json"
OWNER_ACCEPTANCE_PATH = f"{BASE}/eval1_owner_acceptance.v1.json"
ACTIVATION_PATH = f"{BASE}/eval1_activation_receipt.v1.json"

EVAL0_REGISTRATION_ID = "K3E-EVAL-0-V1"
EVAL0_CANONICAL_DIGEST = "986ec117e8517b77e8dece565fd9d9dc169e758beb9d1619acc443e061ef87fd"
EVAL1_REGISTRATION_ID = "K3E-EVAL-1-V1"
EVAL_OWNER = "WS:EVAL-OS-MEASUREMENT-LAW"
FREEZE_BOUNDARY_RULE = "first_nyse_session_open_strictly_after_origin_main_commit_containing_exact_registration_digest/v1"
_NYSE_OPEN = time(9, 30)
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _canonical_json_digest(raw: bytes) -> str:
    payload = json.loads(raw.decode("utf-8"))
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_NO_LAZY_FETCH"] = "1"
    return env


def _git_show(repo: Path, ref: str, path: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        env=_git_env(),
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _rev_parse(repo: Path, ref: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
        env=_git_env(),
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value if _HEX40.fullmatch(value) is not None else None


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        env=_git_env(),
    )
    return proc.returncode == 0


def _commit_time(repo: Path, commit: str) -> datetime | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", "-s", "--format=%cI", commit],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
        env=_git_env(),
    )
    if proc.returncode != 0:
        return None
    try:
        parsed = datetime.fromisoformat(proc.stdout.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _first_nyse_session_open_strictly_after(moment: datetime) -> date | None:
    cursor = moment.astimezone(ET).date()
    moment_utc = moment.astimezone(timezone.utc)
    for _ in range(30):
        if is_session(cursor):
            session_open = datetime.combine(cursor, _NYSE_OPEN, tzinfo=ET)
            if session_open.astimezone(timezone.utc) > moment_utc:
                return cursor
        cursor += timedelta(days=1)
    return None


def _load_json(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _result(
    *,
    reasons: list[str],
    eval0_preserved: bool,
    source_main_commit: str | None,
) -> dict[str, Any]:
    return {
        "schema": "k3e.eval1_source_admission/v1",
        "admitted": False,
        "outcome_access_allowed": False,
        "reasons": reasons,
        "source_main_commit": source_main_commit,
        "eval0": {
            "registration_id": EVAL0_REGISTRATION_ID,
            "canonical_digest": EVAL0_CANONICAL_DIGEST,
            "preserved": eval0_preserved,
        },
    }


def _admitted_result(
    *,
    registration_digest: str,
    source_commit: str,
    boundary: str,
    source_main_commit: str,
) -> dict[str, Any]:
    return {
        "schema": "k3e.eval1_source_admission/v1",
        "admitted": True,
        "outcome_access_allowed": True,
        "reasons": [],
        "source_main_commit": source_main_commit,
        "registration_digest": registration_digest,
        "registration_source_commit": source_commit,
        "resolved_first_eligible_session": boundary,
        "eval0": {
            "registration_id": EVAL0_REGISTRATION_ID,
            "canonical_digest": EVAL0_CANONICAL_DIGEST,
            "preserved": True,
        },
    }


def _registration_reason(registration: dict[str, Any]) -> str | None:
    if registration.get("schema") != "k3e.eval1_preregistration/v1":
        return "EVAL1_REGISTRATION_SCHEMA_INVALID"
    if registration.get("registration_id") != EVAL1_REGISTRATION_ID:
        return "EVAL1_REGISTRATION_ID_INVALID"
    if registration.get("status") != "FROZEN_BEFORE_OUTCOME_ACCESS":
        return "EVAL1_REGISTRATION_NOT_FROZEN"
    predecessor = registration.get("predecessor")
    if not isinstance(predecessor, dict):
        return "EVAL1_PREDECESSOR_INVALID"
    if (
        predecessor.get("registration_id") != EVAL0_REGISTRATION_ID
        or predecessor.get("canonical_digest_sha256") != EVAL0_CANONICAL_DIGEST
        or predecessor.get("prior_trial_budget_reset") is not False
    ):
        return "EVAL1_PREDECESSOR_INVALID"
    experiments = registration.get("admitted_experiments")
    freeze = registration.get("scientific_freeze")
    if (
        not isinstance(experiments, list)
        or not experiments
        or any(not isinstance(item, str) or not item.strip() for item in experiments)
        or len(set(experiments)) != len(experiments)
        or not isinstance(freeze, dict)
    ):
        return "EVAL1_SCIENTIFIC_FREEZE_INCOMPLETE"

    string_fields = (
        "primary_endpoint",
        "primary_loss",
        "strongest_baseline_rule",
        "effective_n_rule",
        "coverage_rule",
        "dependence_rule",
        "censoring_rule",
        "forward_partitions",
    )
    if any(not isinstance(freeze.get(key), str) or not freeze[key].strip() for key in string_fields):
        return "EVAL1_SCIENTIFIC_FREEZE_INCOMPLETE"

    horizon = freeze.get("primary_horizon_sessions")
    budget = freeze.get("total_search_budget")
    effect = freeze.get("effect_size_threshold")
    if (
        isinstance(horizon, bool)
        or not isinstance(horizon, int)
        or horizon <= 0
        or isinstance(budget, bool)
        or not isinstance(budget, int)
        or budget <= 0
        or isinstance(effect, bool)
        or not isinstance(effect, (int, float))
        or not math.isfinite(float(effect))
        or float(effect) <= 0
    ):
        return "EVAL1_SCIENTIFIC_FREEZE_INCOMPLETE"
    return None


def inspect_eval1_admission(repo_root: str | Path, *, as_of_date: date) -> dict[str, Any]:
    """Inspect one immutable accepted-main K3E EVAL source snapshot without outcomes."""
    repo = Path(repo_root)
    source_main_commit = _rev_parse(repo, MAIN_REF)
    if source_main_commit is None:
        return _result(
            reasons=["SOURCE_MAIN_UNAVAILABLE"],
            eval0_preserved=False,
            source_main_commit=None,
        )

    def refuse(reason: str, *, eval0_preserved: bool) -> dict[str, Any]:
        return _result(
            reasons=[reason],
            eval0_preserved=eval0_preserved,
            source_main_commit=source_main_commit,
        )

    eval0_raw = _git_show(repo, source_main_commit, EVAL0_PATH)
    eval0 = _load_json(eval0_raw)
    if eval0_raw is None:
        return refuse("EVAL0_REGISTRATION_MISSING", eval0_preserved=False)
    if eval0 is None:
        return refuse("EVAL0_REGISTRATION_INVALID", eval0_preserved=False)
    try:
        eval0_digest = _canonical_json_digest(eval0_raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return refuse("EVAL0_REGISTRATION_INVALID", eval0_preserved=False)
    if eval0.get("registration_id") != EVAL0_REGISTRATION_ID or eval0_digest != EVAL0_CANONICAL_DIGEST:
        return refuse("EVAL0_REGISTRATION_CHANGED", eval0_preserved=False)

    eval1_raw = _git_show(repo, source_main_commit, EVAL1_PATH)
    if eval1_raw is None:
        return refuse("EVAL1_REGISTRATION_MISSING", eval0_preserved=True)
    registration = _load_json(eval1_raw)
    if registration is None:
        return refuse("EVAL1_REGISTRATION_INVALID", eval0_preserved=True)
    registration_reason = _registration_reason(registration)
    if registration_reason is not None:
        return refuse(registration_reason, eval0_preserved=True)
    try:
        registration_digest = _canonical_json_digest(eval1_raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return refuse("EVAL1_REGISTRATION_INVALID", eval0_preserved=True)

    owner_raw = _git_show(repo, source_main_commit, OWNER_ACCEPTANCE_PATH)
    owner = _load_json(owner_raw)
    if owner_raw is None:
        return refuse("OWNER_ACCEPTANCE_MISSING", eval0_preserved=True)
    if owner is None:
        return refuse("OWNER_ACCEPTANCE_INVALID", eval0_preserved=True)
    source_commit = owner.get("registration_source_commit")
    if (
        owner.get("schema") != "k3e.eval1_owner_acceptance/v1"
        or owner.get("registration_id") != EVAL1_REGISTRATION_ID
        or owner.get("accepted") is not True
        or owner.get("owner_workstream") != EVAL_OWNER
        or not isinstance(source_commit, str)
        or _HEX40.fullmatch(source_commit) is None
    ):
        return refuse("OWNER_ACCEPTANCE_INVALID", eval0_preserved=True)
    if owner.get("registration_digest_sha256") != registration_digest:
        return refuse("OWNER_ACCEPTANCE_DIGEST_MISMATCH", eval0_preserved=True)

    if not _is_ancestor(repo, source_commit, source_main_commit):
        return refuse("OWNER_ACCEPTANCE_SOURCE_UNBOUND", eval0_preserved=True)
    source_registration = _git_show(repo, source_commit, EVAL1_PATH)
    try:
        source_digest = (
            _canonical_json_digest(source_registration)
            if source_registration is not None
            else None
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        source_digest = None
    if source_digest != registration_digest:
        return refuse("OWNER_ACCEPTANCE_SOURCE_UNBOUND", eval0_preserved=True)

    activation_raw = _git_show(repo, source_main_commit, ACTIVATION_PATH)
    if activation_raw is None:
        return refuse("EVAL1_ACTIVATION_MISSING", eval0_preserved=True)
    activation = _load_json(activation_raw)
    if activation is None:
        return refuse("EVAL1_ACTIVATION_INVALID", eval0_preserved=True)
    if (
        activation.get("schema") != "k3e.eval1_activation_receipt/v1"
        or activation.get("registration_id") != EVAL1_REGISTRATION_ID
        or activation.get("canonical_registration_digest_sha256") != registration_digest
        or activation.get("registration_source_commit") != source_commit
        or activation.get("freeze_boundary_rule") != FREEZE_BOUNDARY_RULE
    ):
        return refuse("EVAL1_ACTIVATION_INVALID", eval0_preserved=True)

    boundary = activation.get("resolved_first_eligible_session")
    if not isinstance(boundary, str):
        return refuse("EVAL1_ACTIVATION_INVALID", eval0_preserved=True)
    try:
        boundary_date = date.fromisoformat(boundary)
    except ValueError:
        return refuse("EVAL1_ACTIVATION_INVALID", eval0_preserved=True)

    source_time = _commit_time(repo, source_commit)
    expected_boundary = (
        _first_nyse_session_open_strictly_after(source_time)
        if source_time is not None
        else None
    )
    if expected_boundary is None or boundary_date != expected_boundary:
        return refuse("EVAL1_ACTIVATION_BOUNDARY_INVALID", eval0_preserved=True)
    if as_of_date < boundary_date:
        return refuse("FORWARD_BOUNDARY_NOT_REACHED", eval0_preserved=True)

    return _admitted_result(
        registration_digest=registration_digest,
        source_commit=source_commit,
        boundary=boundary,
        source_main_commit=source_main_commit,
    )
