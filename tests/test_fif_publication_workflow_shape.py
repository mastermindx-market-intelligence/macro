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
    # Secrets are referenced BY NAME only. Non-secret workflow contexts are
    # allowed from this narrow allowlist (the house upload-artifact pattern's
    # runner.temp / github.run_id — D5); anything else must be a secrets.NAME.
    non_secret_contexts = {"runner.temp", "github.run_id"}
    for expression in expressions:
        assert expression in non_secret_contexts or re.fullmatch(
            r"secrets\.[A-Z0-9_]+", expression
        ), expression


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
    assert '--max-tickers "$MAX_TICKERS"' in run
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


def test_ticker_cap_is_single_sourced_at_fifteen() -> None:
    """ERRATA E2-R (T6): the cap literal 15 appears EXACTLY once in the workflow
    and EVERY --max-tickers use (targets call + both wave-2 calls) reads it."""
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert text.count("MAX_TICKERS=15") == 1
    uses = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue  # prose mentions are not call sites
        uses.extend(re.findall(r'--max-tickers\s+"[^"]*"', line))
    assert len(uses) == 3, uses  # targets + first wave-2 + second wave-2
    assert all(use == '--max-tickers "$MAX_TICKERS"' for use in uses), uses
    # No bare numeric cap anywhere: the value lives only in MAX_TICKERS=15.
    assert not re.search(r"--max-tickers\s+[0-9]+", text)
    # No second definition of the variable.
    assert len(re.findall(r"^\s*MAX_TICKERS=", text, re.MULTILINE)) == 1


def test_d6_capture_report_written_and_consumed() -> None:
    """D6: the capture step writes its JSON report to RUNNER_TEMP and the
    publish step consumes the SAME path via --capture-report."""
    workflow = _workflow()
    steps = _steps(workflow)
    capture = next(step for step in steps if step.get("name") == CAPTURE_STEP)
    publish = next(step for step in steps if step.get("name") == PUBLISH_STEP)
    pattern = "fif-member-capture-report-${GITHUB_RUN_ID}.json"
    assert pattern in capture["run"]
    assert '--report-path "$CAPTURE_REPORT"' in capture["run"]
    assert pattern in publish["run"]
    assert '--capture-report "$CAPTURE_REPORT"' in publish["run"]


UPLOAD_STEP = "upload FIF publication reports (always)"
UPLOAD_ARTIFACT_PIN = (
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
)


def test_d5_reports_uploaded_as_artifact_with_always() -> None:
    """D5: spec §4 requires the run report as 'stdout + workflow artifact' —
    an upload-artifact step with `if: always()` (a red lane's reports are the
    interesting ones) pinned to the repo's existing sha, uploading BOTH the
    publish report and the D6 capture report."""
    workflow = _workflow()
    steps = _steps(workflow)
    upload = next(step for step in steps if step.get("name") == UPLOAD_STEP)
    assert upload["uses"] == UPLOAD_ARTIFACT_PIN
    assert upload["if"] == "always()"
    run_text = str(upload["with"]["path"])
    assert "fif-production-publish-report-${{ github.run_id }}.json" in run_text
    assert "fif-member-capture-report-${{ github.run_id }}.json" in run_text


def test_d7_capture_step_carries_no_secrets() -> None:
    """D7: member capture fetches from SEC through the collector and writes to
    the warm archive root — it never touches the store, so the capture step
    gets NO credentials at all, least of all the four R2_RESEARCH_* secrets it
    was previously handed."""
    workflow = _workflow()
    capture = next(step for step in _steps(workflow) if step.get("name") == CAPTURE_STEP)
    assert "env" not in capture
    assert "R2_" not in capture["run"]


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
