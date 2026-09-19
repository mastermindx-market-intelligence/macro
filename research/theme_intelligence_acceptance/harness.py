#!/usr/bin/env python3
"""Deterministic independent acceptance harness for Theme Intelligence Lane F.

The harness evaluates one immutable Git subject. It imports the real committed
production functions after byte-matching the checkout to that subject, reads all
published artifacts with ``git show``, and never writes product data or production
source. A rejected product verdict can therefore be a successful evaluator result.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping

import yaml


SCHEMA = "theme_intelligence.acceptance_result.v1"
OPERATION_KEY = "theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001"

INPUT_PATHS = (
    "scripts/build_state_of_themes.py",
    "engine/neuralweb/theme_thesis.py",
    "config/theme_thesis_registry.yml",
    "site/basketdata/foresight_cascade.json",
    "site/neuralwebdata/theme_thesis.json",
    "site/basketdata/theme_lanes.json",
    "site/state_of_themes.html",
    "data/neuralweb/theme_state.json",
)

_LOCAL_MODULE_PATHS = (
    "scripts/build_state_of_themes.py",
    "engine/neuralweb/theme_thesis.py",
)

_TEMPORAL_CHECK_KEYS = frozenset(
    {
        "from_stage",
        "prior_stage",
        "previous_stage",
        "from_field",
        "prior_field",
        "previous_field",
        "transition_field",
        "history_field",
        "prior_source_artifact",
        "history_source_artifact",
        "transition_evidence",
    }
)


class AcceptanceHarnessError(RuntimeError):
    """Raised when immutable input or harness integrity cannot be established."""


def _git(root: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AcceptanceHarnessError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout


def _resolve_subject(root: Path, subject: str) -> tuple[str, str]:
    commit = _git(root, "rev-parse", f"{subject}^{{commit}}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise AcceptanceHarnessError(f"subject did not resolve to a full commit: {commit!r}")
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    return commit, tree


def _git_bytes(root: Path, commit: str, path: str) -> bytes:
    return _git(root, "show", f"{commit}:{path}")


def _blob_id(root: Path, commit: str, path: str) -> str:
    return _git(root, "rev-parse", f"{commit}:{path}").decode().strip()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(raw: bytes, path: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcceptanceHarnessError(f"invalid JSON at {path}: {exc}") from exc


def _yaml_bytes(raw: bytes, path: str) -> Any:
    try:
        return yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AcceptanceHarnessError(f"invalid YAML at {path}: {exc}") from exc


def _load_cases(cases_path: Path, commit: str) -> dict[str, Any]:
    try:
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceHarnessError(f"could not load cases {cases_path}: {exc}") from exc
    if cases.get("schema") != "theme_intelligence.acceptance_cases.v1":
        raise AcceptanceHarnessError(f"unsupported cases schema: {cases.get('schema')!r}")
    if cases.get("operation_key") != OPERATION_KEY:
        raise AcceptanceHarnessError("case operation key does not match Lane F")
    if cases.get("frozen_subject") != commit:
        raise AcceptanceHarnessError(
            f"case subject {cases.get('frozen_subject')} does not match evaluated commit {commit}"
        )
    return cases


def _input_manifest(root: Path, commit: str) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    manifest: dict[str, dict[str, Any]] = {}
    raw_by_path: dict[str, bytes] = {}
    for path in INPUT_PATHS:
        raw = _git_bytes(root, commit, path)
        raw_by_path[path] = raw
        row: dict[str, Any] = {
            "git_blob": _blob_id(root, commit, path),
            "sha256": _sha256(raw),
            "bytes": len(raw),
        }
        local = root / path
        if path in _LOCAL_MODULE_PATHS:
            if not local.is_file():
                raise AcceptanceHarnessError(f"required production source is not materialized: {path}")
            local_raw = local.read_bytes()
            row["checkout_matches_subject"] = local_raw == raw
            if local_raw != raw:
                raise AcceptanceHarnessError(
                    f"checkout source {path} does not match immutable subject {commit}"
                )
        manifest[path] = row
    return manifest, raw_by_path


def _load_module(root: Path, relative_path: str, commit: str) -> ModuleType:
    path = root / relative_path
    module_name = (
        "lane_f_"
        + relative_path.replace("/", "_").replace(".", "_")
        + "_"
        + commit[:12]
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AcceptanceHarnessError(f"could not load production module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _find_dict(rows: Any, key: str, value: str, label: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise AcceptanceHarnessError(f"{label} is not a list")
    matches = [row for row in rows if isinstance(row, dict) and row.get(key) == value]
    if len(matches) != 1:
        raise AcceptanceHarnessError(
            f"expected exactly one {label} row with {key}={value!r}; found {len(matches)}"
        )
    return matches[0]


def _theme_thesis_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise AcceptanceHarnessError("theme thesis projection is not an object")
    for key in ("theses", "records", "themes"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return rows
    raise AcceptanceHarnessError("theme thesis projection has no supported row list")


def _transition_contract_present(check: Mapping[str, Any]) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    for key in sorted(_TEMPORAL_CHECK_KEYS):
        value = check.get(key)
        if value not in (None, "", [], {}):
            evidence.append(key)
    field = str(check.get("field") or "").lower()
    kind = str(check.get("kind") or "").lower()
    if "transition" in field or "history" in field:
        evidence.append("field_semantics")
    if kind in {"stage_transition", "transition"}:
        evidence.append("kind_semantics")
    return bool(evidence), sorted(set(evidence))


def _extract_html_lane(html: str, theme_id: str) -> str:
    article = re.search(
        rf'<article\b(?=[^>]*\bdata-theme-id="{re.escape(theme_id)}")[^>]*>.*?</article>',
        html,
        flags=re.DOTALL,
    )
    if article is None:
        # Current template places attributes over several lines; use a broader bounded match.
        article = re.search(
            rf'<article\b.*?\bdata-theme-id="{re.escape(theme_id)}".*?</article>',
            html,
            flags=re.DOTALL,
        )
    if article is None:
        raise AcceptanceHarnessError(f"served card for {theme_id!r} not found")
    lane = re.search(r'\bdata-lane="([^"]+)"', article.group(0))
    if lane is None:
        raise AcceptanceHarnessError(f"served card for {theme_id!r} has no data-lane")
    return lane.group(1)


def _lane_legs(crowding_band: Any) -> dict[str, Any]:
    return {"crowding_hazard": {"band": crowding_band}}


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _copy_mutation(mutation: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(mutation or {}))


def evaluate(
    repo_root: Path | str,
    subject: str,
    cases_path: Path | str,
    *,
    mutation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one immutable subject and return a deterministic result object.

    ``mutation`` is used only by the executable adversarial specification. It changes
    in-memory evaluator observations; it never changes repository bytes.
    """
    root = Path(repo_root).resolve()
    cases_file = Path(cases_path).resolve()
    commit, tree = _resolve_subject(root, subject)
    cases = _load_cases(cases_file, commit)
    inputs, raw = _input_manifest(root, commit)
    mut = _copy_mutation(mutation)

    tracker = _load_module(root, "scripts/build_state_of_themes.py", commit)
    thesis_engine = _load_module(root, "engine/neuralweb/theme_thesis.py", commit)
    lane_classifier: Callable[[str, bool, dict[str, Any], str | None], str] = getattr(
        tracker, "_classify_lane"
    )
    eval_falsifier = getattr(thesis_engine, "_eval_falsifier")

    registry = _yaml_bytes(raw["config/theme_thesis_registry.yml"], "config/theme_thesis_registry.yml")
    if not isinstance(registry, dict):
        raise AcceptanceHarnessError("theme thesis registry is not an object")
    watch_case = cases["watch_invalidation"]
    theme_id = str(watch_case["theme_id"])
    falsifier_id = str(watch_case["falsifier_id"])
    thesis = _find_dict(registry.get("theses"), "theme_id", theme_id, "registry thesis")
    falsifier = _find_dict(thesis.get("falsifiers"), "id", falsifier_id, "registry falsifier")
    check = falsifier.get("check")
    if not isinstance(check, dict):
        raise AcceptanceHarnessError(f"{falsifier_id} has no machine-checkable check")

    foresight_payload = _json_bytes(
        raw["site/basketdata/foresight_cascade.json"], "site/basketdata/foresight_cascade.json"
    )
    state_payload = _json_bytes(raw["data/neuralweb/theme_state.json"], "data/neuralweb/theme_state.json")
    thesis_payload = _json_bytes(
        raw["site/neuralwebdata/theme_thesis.json"], "site/neuralwebdata/theme_thesis.json"
    )
    lanes_payload = _json_bytes(
        raw["site/basketdata/theme_lanes.json"], "site/basketdata/theme_lanes.json"
    )
    html = raw["site/state_of_themes.html"].decode("utf-8")

    if not isinstance(foresight_payload, dict) or not isinstance(foresight_payload.get("themes"), list):
        raise AcceptanceHarnessError("foresight projection has no themes list")
    if not isinstance(state_payload, dict) or not isinstance(state_payload.get("themes"), list):
        raise AcceptanceHarnessError("theme state artifact has no themes list")
    foresight_rows = foresight_payload["themes"]
    state_rows = state_payload["themes"]
    foresight_row = _find_dict(foresight_rows, "theme", theme_id, "foresight theme")
    state_row = _find_dict(state_rows, "theme_id", theme_id, "theme state")
    foresight_index = {
        str(row["theme"]): row
        for row in foresight_rows
        if isinstance(row, dict) and row.get("theme")
    }
    state_index = {
        str(row["theme_id"]): row
        for row in state_rows
        if isinstance(row, dict) and row.get("theme_id")
    }

    production_watch = eval_falsifier(falsifier, foresight_index, state_index, theme_id)
    actual_watch_fired = bool(
        mut.get("watch_actual_fired_override", production_watch.get("fired", False))
    )
    transition_present, transition_evidence = _transition_contract_present(check)
    if "transition_contract_override" in mut:
        transition_present = bool(mut["transition_contract_override"])
        transition_evidence = ["mutation_override"] if transition_present else []
    expected_watch_fired = bool(watch_case["expected_fired"])
    watch_reasons: list[str] = []
    if actual_watch_fired != expected_watch_fired:
        watch_reasons.append("WATCH_WITHOUT_TRANSITION_WAS_INVALIDATED")
    if not transition_present:
        watch_reasons.append("STAGE_REGRESSION_HAS_NO_TEMPORAL_INPUT")
    watch_ok = not watch_reasons

    lane_overrides = dict(mut.get("lane_overrides") or {})
    lane_rows: list[dict[str, Any]] = []
    failed_case_ids: list[str] = []
    for case in cases["lane_matrix"]:
        case_id = str(case["id"])
        actual = lane_classifier(
            str(case["stage"]),
            bool(case["any_fired"]),
            _lane_legs(case.get("crowding_band")),
            case.get("divergence"),
        )
        if case_id in lane_overrides:
            actual = str(lane_overrides[case_id])
        expected = str(case["expected_lane"])
        passed = actual == expected
        if not passed:
            failed_case_ids.append(case_id)
        lane_rows.append(
            {
                "id": case_id,
                "stage": case["stage"],
                "any_fired": bool(case["any_fired"]),
                "crowding_band": case.get("crowding_band"),
                "divergence": case.get("divergence"),
                "expected_lane": expected,
                "actual_lane": actual,
                "status": _status(passed),
            }
        )

    published_thesis = _find_dict(
        _theme_thesis_rows(thesis_payload), "theme_id", theme_id, "published thesis"
    )
    published_falsifier = _find_dict(
        published_thesis.get("falsifiers"), "id", falsifier_id, "published falsifier"
    )
    published_fired = bool(mut.get("published_fired_override", published_falsifier.get("fired")))
    published_state = str(
        mut.get("published_state_override", published_falsifier.get("state"))
    )
    published_lane = str(
        mut.get(
            "published_lane_override",
            (lanes_payload.get("lanes") or {}).get(theme_id),
        )
    )
    html_lane = str(mut.get("html_lane_override", _extract_html_lane(html, theme_id)))
    current_stage = str(foresight_row.get("stage"))
    divergence = None
    divergence_row = state_row.get("divergence_board")
    if isinstance(divergence_row, dict):
        divergence = divergence_row.get("quadrant")
    source_lane = lane_classifier(current_stage, published_fired, {}, divergence)
    if "current_source_lane_override" in mut:
        source_lane = str(mut["current_source_lane_override"])

    path_assertions = {
        "foresight_stage_matches_case": current_stage == watch_case["current_stage"],
        "production_matches_published_fired": actual_watch_fired == published_fired,
        "published_state_matches_fired": published_state == ("FIRED" if published_fired else "ARMED"),
        "classifier_matches_lane_artifact": source_lane == published_lane,
        "lane_artifact_matches_served_card": published_lane == html_lane,
    }
    path_ok = all(path_assertions.values())

    authority_expected = dict(cases["authority_expected"])
    source_authority = deepcopy(getattr(thesis_engine, "AUTHORITY_BLOCK"))
    published_authority = deepcopy(published_thesis.get("authority") or {})
    for key, value in dict(mut.get("authority_overrides") or {}).items():
        source_authority[key] = value
        published_authority[key] = value
    authority_assertions = {
        f"source.{key}": source_authority.get(key) == expected
        for key, expected in authority_expected.items()
    }
    authority_assertions.update(
        {
            f"published.{key}": published_authority.get(key) == expected
            for key, expected in authority_expected.items()
        }
    )
    authority_ok = all(authority_assertions.values())

    checks: dict[str, dict[str, Any]] = {
        "watch_invalidation": {
            "status": _status(watch_ok),
            "theme_id": theme_id,
            "falsifier_id": falsifier_id,
            "check_kind": check.get("kind"),
            "check_field": check.get("field"),
            "current_stage": current_stage,
            "prior_stage": watch_case.get("prior_stage"),
            "expected_fired": expected_watch_fired,
            "actual_fired": actual_watch_fired,
            "production_result": production_watch,
            "transition_contract_present": transition_present,
            "transition_contract_evidence": transition_evidence,
            "reason_codes": watch_reasons,
        },
        "lane_matrix": {
            "status": _status(not failed_case_ids),
            "n_cases": len(lane_rows),
            "n_passed": len(lane_rows) - len(failed_case_ids),
            "n_failed": len(failed_case_ids),
            "failed_case_ids": failed_case_ids,
            "cases": lane_rows,
        },
        "published_path_consistency": {
            "status": _status(path_ok),
            "assertions": path_assertions,
            "foresight_stage": current_stage,
            "production_fired": actual_watch_fired,
            "published_fired": published_fired,
            "published_falsifier_state": published_state,
            "classifier_lane": source_lane,
            "artifact_lane": published_lane,
            "served_card_lane": html_lane,
            "artifact_as_of": {
                "theme_thesis": published_thesis.get("as_of"),
                "foresight": foresight_payload.get("as_of") or foresight_payload.get("generated_at"),
                "theme_state": state_payload.get("as_of") or state_payload.get("generated_at"),
            },
        },
        "authority_invariance": {
            "status": _status(authority_ok),
            "assertions": authority_assertions,
            "expected": authority_expected,
            "source": {key: source_authority.get(key) for key in authority_expected},
            "published": {key: published_authority.get(key) for key in authority_expected},
        },
    }
    failed_checks = [name for name, row in checks.items() if row["status"] != "PASS"]
    product_verdict = "ACCEPTABLE_SOURCE_SEMANTICS" if not failed_checks else "REJECTED_CURRENT_SOURCE"

    return {
        "schema": SCHEMA,
        "operation_key": OPERATION_KEY,
        "subject": {"commit": commit, "tree": tree},
        "inputs": inputs,
        "checks": checks,
        "failed_checks": failed_checks,
        "product_verdict": product_verdict,
        "release_state": "HOLD_FOR_LANE_A_AND_LAWFUL_RELEASE_OWNER",
        "production_proof": "NOT_PROVEN",
        "browser_deployment_parity": "NOT_PROVEN",
        "prospective_outcomes": "UNKNOWN_NOT_MATURED",
    }


def _repaired_baseline_mutation() -> dict[str, Any]:
    return {
        "watch_actual_fired_override": False,
        "published_fired_override": False,
        "published_state_override": "ARMED",
        "transition_contract_override": True,
        "published_lane_override": "early",
        "html_lane_override": "early",
        "lane_overrides": {"clean_precipice_is_early": "early"},
    }


def run_mutation_suite(
    repo_root: Path | str,
    subject: str,
    cases_path: Path | str,
) -> dict[str, Any]:
    """Run deterministic in-memory false-green mutations and positive controls."""
    rows: list[dict[str, Any]] = []

    mutation = _repaired_baseline_mutation()
    mutation["transition_contract_override"] = False
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "false_watch_green_without_transition",
            "expected_effect": "watch check must remain rejected",
            "observed_product_verdict": result["product_verdict"],
            "killed": result["checks"]["watch_invalidation"]["status"] == "FAIL",
        }
    )

    mutation = _repaired_baseline_mutation()
    mutation["lane_overrides"]["fired_dominates_precipice"] = "early"
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "fired_priority_removed",
            "expected_effect": "fired priority mutation must fail the lane matrix",
            "observed_failed_case_ids": result["checks"]["lane_matrix"]["failed_case_ids"],
            "killed": "fired_dominates_precipice"
            in result["checks"]["lane_matrix"]["failed_case_ids"],
        }
    )

    mutation = _repaired_baseline_mutation()
    mutation["lane_overrides"]["high_crowding_dominates_precipice"] = "early"
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "high_crowding_priority_removed",
            "expected_effect": "crowding priority mutation must fail the lane matrix",
            "observed_failed_case_ids": result["checks"]["lane_matrix"]["failed_case_ids"],
            "killed": "high_crowding_dominates_precipice"
            in result["checks"]["lane_matrix"]["failed_case_ids"],
        }
    )

    mutation = _repaired_baseline_mutation()
    mutation["html_lane_override"] = "review"
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "published_card_lane_mismatch",
            "expected_effect": "artifact/card mismatch must fail path consistency",
            "observed_status": result["checks"]["published_path_consistency"]["status"],
            "killed": result["checks"]["published_path_consistency"]["status"] == "FAIL",
        }
    )

    mutation = {}
    mutation["published_state_override"] = "ARMED"
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "published_falsifier_state_mismatch",
            "expected_effect": "published state/fired mismatch must fail path consistency",
            "observed_status": result["checks"]["published_path_consistency"]["status"],
            "killed": result["checks"]["published_path_consistency"]["status"] == "FAIL",
        }
    )

    mutation = _repaired_baseline_mutation()
    mutation["authority_overrides"] = {"may_rank": True}
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "rank_authority_enabled",
            "expected_effect": "authority escalation must fail invariance",
            "observed_status": result["checks"]["authority_invariance"]["status"],
            "killed": result["checks"]["authority_invariance"]["status"] == "FAIL",
        }
    )

    mutation = _repaired_baseline_mutation()
    result = evaluate(repo_root, subject, cases_path, mutation=mutation)
    rows.append(
        {
            "id": "clean_precipice_repair_discriminator",
            "expected_effect": "the preregistered bounded semantic repair must clear all source checks",
            "observed_product_verdict": result["product_verdict"],
            "killed": result["product_verdict"] == "ACCEPTABLE_SOURCE_SEMANTICS",
        }
    )

    return {
        "schema": "theme_intelligence.acceptance_mutations.v1",
        "operation_key": OPERATION_KEY,
        "subject": _resolve_subject(Path(repo_root).resolve(), subject)[0],
        "mutations": rows,
        "n_mutations": len(rows),
        "n_killed": sum(1 for row in rows if row["killed"]),
        "status": "PASS" if all(row["killed"] for row in rows) else "FAIL",
    }


def _write_json(path: Path | None, payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    default_cases = Path(__file__).with_name("incident_cases.v1.json")
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--subject", default=None)
    parser.add_argument("--cases", type=Path, default=default_cases)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mutations", action="store_true")
    parser.add_argument("--require-product-pass", action="store_true")
    args = parser.parse_args(argv)

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    subject = args.subject or cases["frozen_subject"]
    if args.mutations:
        payload = run_mutation_suite(args.repo_root, subject, args.cases)
        _write_json(args.output, payload)
        return 0 if payload["status"] == "PASS" else 1

    payload = evaluate(args.repo_root, subject, args.cases)
    _write_json(args.output, payload)
    if args.require_product_pass and payload["product_verdict"] != "ACCEPTABLE_SOURCE_SEMANTICS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
