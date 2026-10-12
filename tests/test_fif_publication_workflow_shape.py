"""FIF C0-b: filing-forensics-sec workflow shape + CI wiring guards (A7).

The two new lane steps are HARD gates and the schedule stays the only proof
path: ``set -euo pipefail``, zero ``continue-on-error``, zero ``|| true``,
secrets referenced by name only, no ticker or CIK literal, and no new
``workflow_dispatch`` input surface. The three new suites must be wired into
engine-render-guards' rot sweep, and the new producer paths into the owning
curated job.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "filing-forensics-sec.yml"
LEGACY_JOBS_PATH = ROOT / ".github" / "ci" / "legacy-jobs.yml"

CAPTURE_STEP = "capture FIF filing packages (contract issuers)"
PUBLISH_STEP = "publish FIF production datasets (hard gate)"
NEW_STEPS = (CAPTURE_STEP, PUBLISH_STEP)
NEW_TEST_SUITES = (
    "tests/test_fundamental_forensics_member_capture.py",
    "tests/test_fundamental_forensics_production_publisher.py",
    "tests/test_fif_publication_workflow_shape.py",
)
NEW_PRODUCER_PATHS = (
    "engine/fundamental_forensics/fif_member_capture.py",
    "scripts/publish_fif_production_datasets.py",
)


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _steps(workflow: dict) -> list[dict]:
    jobs = workflow["jobs"]
    assert list(jobs) == ["acquire_project_sync"]
    return list(jobs["acquire_project_sync"]["steps"])


def test_triggers_unchanged_schedule_stays_the_only_proof_path() -> None:
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "30 2 * * *"}]
    # No new dispatch input surface for the proof rung.
    assert triggers["workflow_dispatch"] == {}


def test_new_steps_exist_and_are_hard_gates() -> None:
    workflow = _workflow()
    steps = _steps(workflow)
    by_name = {step.get("name"): step for step in steps if step.get("name")}
    for name in NEW_STEPS:
        assert name in by_name, name
        step = by_name[name]
        assert "continue-on-error" not in step
        assert "set -euo pipefail" in step["run"]
        assert "|| true" not in step["run"]
        assert step["run"].count("publish_fif_production_datasets") >= 1
    # No step anywhere in the lane may soften failures.
    for step in steps:
        assert "continue-on-error" not in step
    assert "|| true" not in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_secrets_referenced_by_name_only() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    expressions = re.findall(r"\$\{\{\s*([^}]+?)\s*\}\}", text)
    assert expressions
    for expression in expressions:
        assert re.fullmatch(r"secrets\.[A-Z0-9_]+", expression), expression


def test_no_ticker_or_cik_literal_in_the_workflow() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    # No CIK-shaped literal anywhere in the lane YAML.
    assert re.findall(r"\b\d{10}\b", text) == []
    contract = json.loads(
        (
            ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
        ).read_text(encoding="utf-8")
    )
    for issuer in contract["issuers"]:
        assert issuer["ticker"] not in text
        assert issuer["cik"] not in text
        for accession in issuer.get("accessions", []):
            assert accession["accession"] not in text


def test_first_wave2_invocation_consumes_derived_targets() -> None:
    workflow = _workflow()
    steps = _steps(workflow)
    acquire = next(
        step
        for step in steps
        if step.get("name", "").startswith("restore, acquire, project, and sync")
    )
    run = acquire["run"]
    assert "publish_fif_production_datasets targets" in run
    assert "--coverage-file config/fundamental_forensics/coverage/five_issuer_v1.json" in run
    assert "$CONTRACT_TARGETS" in run
    assert "--max-tickers 15" in run
    # The bundle publish step keeps the incumbent pinned file ALONE, so the
    # render bundle stays at the incumbent universe.
    bundle = next(
        step
        for step in steps
        if step.get("name", "").startswith("publish disclosure-projection bundle")
    )
    assert "--targets-file" in bundle["run"]
    assert "$CONTRACT_TARGETS" not in bundle["run"]
    assert re.search(r"--target\b", bundle["run"]) is None  # no per-issuer extras


def test_capture_step_uses_the_contract_coverage_file() -> None:
    workflow = _workflow()
    steps = _steps(workflow)
    capture = next(step for step in steps if step.get("name") == CAPTURE_STEP)
    assert "--coverage-file config/fundamental_forensics/coverage/five_issuer_v1.json" in capture["run"]
    assert "--recorded-at" in capture["run"]


def test_publish_step_publishes_then_verifies() -> None:
    workflow = _workflow()
    steps = _steps(workflow)
    publish = next(step for step in steps if step.get("name") == PUBLISH_STEP)
    run = publish["run"]
    assert "publish_fif_production_datasets publish" in run
    assert "publish_fif_production_datasets verify" in run
    assert "--recorded-at" in run
    # The R2 store family rides the four dedicated research env names.
    env = publish.get("env", {})
    assert set(env) == {
        "R2_RESEARCH_ENDPOINT",
        "R2_RESEARCH_ACCESS_KEY_ID",
        "R2_RESEARCH_SECRET_ACCESS_KEY",
        "R2_RESEARCH_BUCKET",
    }


def test_new_suites_wired_into_engine_render_guards_rot_sweep() -> None:
    text = LEGACY_JOBS_PATH.read_text(encoding="utf-8")
    for suite in NEW_TEST_SUITES:
        assert suite in text, suite
    manifest = yaml.safe_load(text)["jobs"]
    guards = manifest["engine-render-guards"]
    sweep = next(
        step
        for step in guards["steps"]
        if "render-guard + engine-contract tests" in str(step.get("name", ""))
    )
    run = sweep["run"]
    for suite in NEW_TEST_SUITES:
        assert suite in run, suite


def test_new_producer_paths_wired_into_owning_curated_job() -> None:
    manifest = yaml.safe_load(LEGACY_JOBS_PATH.read_text(encoding="utf-8"))["jobs"]
    owner = manifest["ticker-news-qbus"]
    paths = owner["paths"]
    for path in NEW_PRODUCER_PATHS:
        assert path in paths, path
