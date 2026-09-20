#!/usr/bin/env python3
"""Independent exact-head acceptance for Theme Intelligence Lane C.

The candidate is evaluated read-only from a caller-supplied exact checkout. A PASS
from this script means the evaluator reproduced the preregistered positive controls
and repair blockers; it does not mean the candidate product is accepted.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


RESULT_SCHEMA = "theme_intelligence.lane_c_acceptance_result.v1"


class AcceptanceError(RuntimeError):
    """Raised when candidate identity or evaluator setup is not trustworthy."""


def _run(
    root: Path,
    args: Sequence[str],
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    proc = subprocess.run(
        list(args),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return {"exit_code": proc.returncode, "output": output}


def _git(root: Path, *args: str) -> str:
    result = _run(root, ["git", *args])
    if result["exit_code"] != 0:
        raise AcceptanceError(
            f"git {' '.join(args)} failed: {result['output'].strip()}"
        )
    return result["output"].strip()


def _pytest_summary(output: str) -> str | None:
    matches = re.findall(
        r"(?:^|\n)(\d+ passed(?:, \d+ skipped)?(?:, \d+ warnings?)?) in [^\n]+",
        output,
    )
    return matches[-1] if matches else None


def _json_write(path: Path | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path is None:
        sys.stdout.write(text)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _load_cases(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "theme_intelligence.lane_c_acceptance_cases.v1":
        raise AcceptanceError(f"unsupported cases schema: {payload.get('schema')!r}")
    return payload


def _bars(returns: list[float], *, volume: float = 100.0) -> pd.DataFrame:
    idx = pd.bdate_range("2026-01-02", periods=len(returns) + 1)
    close = 100.0 * np.cumprod(np.array([1.0, *[1.0 + r for r in returns]], dtype=float))
    return pd.DataFrame({"close": close, "volume": volume}, index=idx)


def _import_candidate(candidate: Path):
    candidate_s = str(candidate)
    sys.path.insert(0, candidate_s)
    importlib.invalidate_caches()
    for name in (
        "engine.neuralweb.thematic_state",
        "engine.neuralweb",
        "engine.subsector_rotation",
        "engine",
    ):
        sys.modules.pop(name, None)
    subsector_rotation = importlib.import_module("engine.subsector_rotation")
    thematic_state = importlib.import_module("engine.neuralweb.thematic_state")
    return subsector_rotation, thematic_state


def _direct_discriminators(
    sr: Any,
    ts: Any,
    authority_expected: dict[str, bool],
) -> tuple[dict[str, Any], set[str], set[str]]:
    positive: set[str] = set()
    blockers: set[str] = set()
    details: dict[str, Any] = {}

    authority_actual = dict(sr.CLOSED_SESSION_PERMISSIONS)
    authority_ok = authority_actual == authority_expected
    if authority_ok:
        positive.add("AUTHORITY_INVARIANCE")
    details["authority_invariance"] = {
        "status": "PASS" if authority_ok else "FAIL",
        "expected": authority_expected,
        "actual": authority_actual,
    }

    market = _bars([0.0] * 70)
    fast = [0.0] * 65 + [0.02] * 5
    slow = [0.0] * 65 + [-0.02] * 5
    tree = [{
        "theme": "Semiconductors",
        "subsectors": [
            {"key": "fast", "name": "Fast", "members": ["A", "B", "C"]},
            {"key": "slow", "name": "Slow", "members": ["D", "E", "F"]},
        ],
    }]
    bars = {ticker: _bars(fast) for ticker in ("A", "B", "C")}
    bars.update({ticker: _bars(slow) for ticker in ("D", "E", "F")})
    mixed = sr.compute_closed_session_leadership(
        tree,
        bars,
        market,
        asof=str(market.index[-1].date()),
        parent_keys={"Semiconductors"},
    )["themes"]["Semiconductors"]
    by_key = {row["key"]: row for row in mixed["subthemes"]}
    separation_ok = (
        len(by_key) == 2
        and by_key["fast"]["windows"]["5"]["return_pct"] > 0
        and by_key["slow"]["windows"]["5"]["return_pct"] < 0
        and mixed["parent"]["windows"]["5"]["return_pct"] is not None
    )
    if separation_ok:
        positive.add("PARENT_SUBTHEME_SEPARATION")
    details["parent_subtheme_separation"] = {
        "status": "PASS" if separation_ok else "FAIL",
        "parent_5_session_return_pct": mixed["parent"]["windows"]["5"]["return_pct"],
        "fast_5_session_return_pct": by_key["fast"]["windows"]["5"]["return_pct"],
        "slow_5_session_return_pct": by_key["slow"]["windows"]["5"]["return_pct"],
    }

    stale = _bars([0.001] * 65)
    stale_theme = sr.compute_closed_session_leadership(
        [{
            "theme": "Hardware",
            "subsectors": [{"key": "servers", "name": "Servers", "members": ["STALE"]}],
        }],
        {"STALE": stale},
        market,
        asof=str(market.index[-1].date()),
        parent_keys={"Hardware"},
    )["themes"]["Hardware"]
    stale_row = stale_theme["subthemes"][0]
    stale_reclaim_count = stale_row["volume_reclaim"]["members_with_20d_reclaim_evidence"]
    stale_reclaim_leak = bool(stale_row["coverage"]["stale_members"] and stale_reclaim_count)
    if stale_reclaim_leak:
        blockers.add("STALE_MEMBER_RECLAIM_EVIDENCE_NOT_EXCLUDED")
    details["stale_member_reclaim"] = {
        "status": "FAIL" if stale_reclaim_leak else "PASS",
        "node_status": stale_row["status"],
        "stale_members": stale_row["coverage"]["stale_members"],
        "volume_reclaim": stale_row["volume_reclaim"],
    }

    today = pd.Timestamp.now(tz="UTC").date().isoformat()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / "site/marketdata/subsector_rotation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "asof": today,
            "themes": [{
                "theme": "Semiconductors",
                "quadrant": "leading",
                "leadership_observation": {
                    "status": "MEASURED",
                    "asof": "2000-01-03",
                    "measurement_receipt": {
                        "clocks": {"observation_session": "2000-01-03"},
                        "bar_status": "CLOSED",
                    },
                },
            }],
        }), encoding="utf-8")
        rows, stale_legs = ts._read_subsector(root)
    stale_propagated = any(
        "leadership" in item.lower() and "stale" in item.lower()
        for item in stale_legs
    )
    if not stale_propagated:
        blockers.add("STALE_LEADERSHIP_OBSERVATION_NOT_PROPAGATED")
    details["consumer_stale_health"] = {
        "status": "PASS" if stale_propagated else "FAIL",
        "stale_legs": stale_legs,
        "consumer_observation": rows["Semiconductors"]["leadership_observation"],
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / "site/marketdata/subsector_rotation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "asof": today,
            "closed_session_leadership": {
                "schema": "subsector_rotation.closed_session_leadership.v1",
                "status": "UNAVAILABLE",
                "reason_codes": ["OWNER_INPUT_LOAD_FAILED"],
                "clocks": {
                    "observation_session": None,
                    "input_snapshot_asof": today,
                    "computation_utc": f"{today} 23:00",
                },
            },
            "themes": [{"theme": "Semiconductors", "quadrant": "leading"}],
        }), encoding="utf-8")
        rows, failure_stale_legs = ts._read_subsector(root)
    consumer_failure = rows["Semiconductors"]["leadership_observation"]
    unavailable_preserved = (
        isinstance(consumer_failure, dict)
        and consumer_failure.get("status") == "UNAVAILABLE"
    )
    reason_preserved = any(
        "OWNER_INPUT_LOAD_FAILED" in item for item in failure_stale_legs
    )
    if not unavailable_preserved:
        blockers.add("UNAVAILABLE_PRODUCER_RECEIPT_LOST_AT_SHARED_CONSUMER")
    if not reason_preserved:
        blockers.add("PRODUCER_FAILURE_REASON_NOT_PROPAGATED_TO_HEALTH")
    details["consumer_failure_health"] = {
        "status": "PASS" if unavailable_preserved and reason_preserved else "FAIL",
        "consumer_observation": consumer_failure,
        "stale_legs": failure_stale_legs,
    }

    return details, positive, blockers


def _repository_checks(
    candidate: Path,
    cases: dict[str, Any],
    *,
    run_suites: bool,
) -> tuple[dict[str, Any], set[str], set[str]]:
    positive: set[str] = set()
    blockers: set[str] = set()
    details: dict[str, Any] = {}
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    py_compile = _run(candidate, [
        sys.executable,
        "-m",
        "py_compile",
        "engine/subsector_rotation.py",
        "scripts/build_subsector_rotation.py",
        "engine/neuralweb/thematic_state.py",
    ], env=env)
    if py_compile["exit_code"] == 0:
        positive.add("PY_COMPILE")
    details["py_compile"] = {
        "exit_code": py_compile["exit_code"],
        "status": "PASS" if py_compile["exit_code"] == 0 else "FAIL",
    }

    trial = _run(candidate, [sys.executable, "scripts/check_trial_registration.py"], env=env)
    if trial["exit_code"] == 0:
        positive.add("TRIAL_REGISTRATION")
    details["trial_registration"] = {
        "exit_code": trial["exit_code"],
        "status": "PASS" if trial["exit_code"] == 0 else "FAIL",
        "summary": trial["output"].strip().splitlines()[-1] if trial["output"].strip() else None,
    }

    if run_suites:
        subsector_suites = [
            str(path.relative_to(candidate))
            for path in sorted((candidate / "tests").glob("test_subsector*.py"))
        ]
        suites = {
            "SUBSECTOR_REGRESSION_SUITE": [
                sys.executable, "-m", "pytest", "-q", *subsector_suites
            ],
            "THEMATIC_STATE_REGRESSION_SUITE": [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_thematic_state.py",
                "tests/test_thematic_state_leadership_receipt.py",
                "tests/test_build_subsector_closed_session_leadership.py",
            ],
            "SECTOR_PAGE_REGRESSION_SUITE": [
                sys.executable, "-m", "pytest", "-q", "tests/test_sector_intelligence_page.py"
            ],
        }
        for check_id, command in suites.items():
            result = _run(candidate, command, env=env)
            passed = result["exit_code"] == 0
            if passed:
                positive.add(check_id)
            details[check_id.lower()] = {
                "exit_code": result["exit_code"],
                "status": "PASS" if passed else "FAIL",
                "summary": _pytest_summary(result["output"]),
            }

    audit = _run(candidate, [sys.executable, "scripts/audit_unrun_tests.py"], env=env)
    dark_paths = sorted(set(re.findall(
        r"::error title=unrun-suite::(\S+)", audit["output"]
    )))
    expected_dark = sorted(cases["expected_dark_test_paths"])
    dark_failure = dark_paths == expected_dark and audit["exit_code"] != 0
    if dark_failure:
        blockers.add("NEW_TEST_SUITES_UNWIRED")
    details["unrun_test_audit"] = {
        "exit_code": audit["exit_code"],
        "status": "FAIL" if dark_failure else "PASS",
        "dark_test_paths": dark_paths,
    }

    agentos = _run(candidate, [sys.executable, "scripts/agentos.py", "validate"], env=env)
    unparseable = [
        line for line in agentos["output"].splitlines()
        if "agentos-unparseable" in line and "THEME-INTELLIGENCE-LANE-C" in line
    ]
    agentos_ok = agentos["exit_code"] == 0 and not unparseable
    if agentos_ok:
        positive.add("AGENTOS_VALIDATION")
    if agentos["exit_code"] != 0 and unparseable:
        blockers.add("AGENTOS_HANDOFF_UNPARSEABLE")
    details["agentos_validation"] = {
        "exit_code": agentos["exit_code"],
        "status": "PASS" if agentos_ok else "FAIL",
        "errors": unparseable,
        "summary": next(
            (line for line in reversed(agentos["output"].splitlines()) if line.startswith("agentos:")),
            None,
        ),
    }

    diff_check = _run(candidate, [
        "git", "diff", "--check", f"{cases['candidate_base']}..{cases['candidate_head']}"
    ])
    whitespace_issues = [
        line for line in diff_check["output"].splitlines()
        if line.endswith("trailing whitespace.")
    ]
    if diff_check["exit_code"] != 0:
        blockers.add("DIFF_CHECK_FAILURE")
    details["diff_check"] = {
        "exit_code": diff_check["exit_code"],
        "status": "FAIL" if diff_check["exit_code"] else "PASS",
        "trailing_whitespace_issue_count": len(whitespace_issues),
        "issues": whitespace_issues,
    }

    grep_result = _run(candidate, [
        "git",
        "grep",
        "-n",
        cases["price_manifest_sha256"],
        cases["candidate_head"],
        "--",
        ".",
    ])
    occurrences = [line for line in grep_result["output"].splitlines() if line.strip()]
    manifest_bytes_committed = any(
        "agentos/handoffs/" not in line for line in occurrences
    )
    if not manifest_bytes_committed:
        blockers.add("REAL_PRICE_PROOF_NOT_REPRODUCIBLE_FROM_CARRIER")
    details["real_price_proof_reproducibility"] = {
        "status": "PASS" if manifest_bytes_committed else "FAIL",
        "price_manifest_sha256": cases["price_manifest_sha256"],
        "hash_occurrences": occurrences,
        "exact_manifest_or_result_bytes_committed": manifest_bytes_committed,
    }

    return details, positive, blockers


def evaluate(
    candidate: Path,
    cases_path: Path,
    *,
    run_suites: bool,
) -> dict[str, Any]:
    candidate = candidate.resolve()
    cases = _load_cases(cases_path.resolve())
    head = _git(candidate, "rev-parse", "HEAD")
    tree = _git(candidate, "rev-parse", "HEAD^{tree}")
    base = _git(candidate, "merge-base", "HEAD", cases["candidate_base"])
    if head != cases["candidate_head"]:
        raise AcceptanceError(f"candidate HEAD {head} != frozen {cases['candidate_head']}")
    if tree != cases["candidate_tree"]:
        raise AcceptanceError(f"candidate tree {tree} != frozen {cases['candidate_tree']}")
    if base != cases["candidate_base"]:
        raise AcceptanceError(f"candidate base {base} != frozen {cases['candidate_base']}")
    if _git(candidate, "status", "--porcelain"):
        raise AcceptanceError("candidate checkout is dirty")

    sr, ts = _import_candidate(candidate)
    direct, direct_positive, direct_blockers = _direct_discriminators(
        sr,
        ts,
        dict(cases["authority_expected"]),
    )
    repository, repository_positive, repository_blockers = _repository_checks(
        candidate,
        cases,
        run_suites=run_suites,
    )

    observed_positive = direct_positive | repository_positive
    observed_blockers = direct_blockers | repository_blockers
    expected_positive = set(cases["expected_positive_checks"])
    if not run_suites:
        expected_positive -= {
            "SUBSECTOR_REGRESSION_SUITE",
            "THEMATIC_STATE_REGRESSION_SUITE",
            "SECTOR_PAGE_REGRESSION_SUITE",
        }
    expected_blockers = set(cases["expected_blockers"])
    missing_positive = sorted(expected_positive - observed_positive)
    missing_blockers = sorted(expected_blockers - observed_blockers)
    unexpected_blockers = sorted(observed_blockers - expected_blockers)
    harness_pass = not missing_positive and not missing_blockers and not unexpected_blockers

    return {
        "schema": RESULT_SCHEMA,
        "operation_key": cases["operation_key"],
        "candidate_operation_key": cases["candidate_operation_key"],
        "candidate": {
            "head": head,
            "tree": tree,
            "base": base,
            "implementation_commit": cases["implementation_commit"],
        },
        "harness_status": "PASS" if harness_pass else "FAIL",
        "candidate_acceptance_state": "REJECTED_FOR_REPAIR",
        "merge_recommendation": "HOLD",
        "positive_checks": sorted(observed_positive),
        "repair_blockers": sorted(observed_blockers),
        "missing_positive_checks": missing_positive,
        "missing_expected_blockers": missing_blockers,
        "unexpected_blockers": unexpected_blockers,
        "checks": {
            "direct_discriminators": direct,
            "repository_admission": repository,
        },
        "not_yet_proven": [
            "CORRECTION_SAFE_FIRST_SEEN_AND_FIRST_VISIBLE_HISTORY",
            "TWO_DISTINCT_OBSERVATIONS_VS_REPEAT_RENDERS",
            "DUPLICATE_EVIDENCE_FAMILY_IDENTITY_ACROSS_THEME_CONSUMERS",
            "SPLIT_DIVIDEND_CORPORATE_ACTION_BASIS",
            "DEPLOYED_BYTE_AND_BROWSER_PARITY",
            "PREDICTIVE_OR_PROSPECTIVE_OUTCOMES",
        ],
        "release_state": "DRAFT_HOLD_FOR_LANE_A_AND_INCUMBENT_OWNERS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("lane_c_cases.v1.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-suites", action="store_true")
    args = parser.parse_args(argv)
    payload = evaluate(
        args.candidate_root,
        args.cases,
        run_suites=args.run_suites,
    )
    _json_write(args.output, payload)
    return 0 if payload["harness_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
