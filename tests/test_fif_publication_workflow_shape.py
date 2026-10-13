"""FIF C0-b: filing-forensics-sec workflow shape + CI wiring guards (A7).

The two publication lane steps are HARD gates and the schedule stays the only
proof path: ``set -euo pipefail``, zero ``|| true``, secrets referenced by
name only, no ticker or CIK literal, and no new ``workflow_dispatch`` input
surface. D13 adds the ISOLATED, non-gating contract acquire step: its
``continue-on-error`` is the isolation mechanism, so it is the one lawful
exception. The three new suites run in fif-kernel-guards (the #9014 generator's
FIF suite list; never also in engine-render-guards' rot sweep), that job's path
filter starts it on every producer path and suite, and the new producer paths
stay in the owning curated job.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "filing-forensics-sec.yml"
LEGACY_JOBS_PATH = ROOT / ".github" / "ci" / "legacy-jobs.yml"
FKG_JOB = "fif-kernel-guards"
FKG_SUITE_STEP = "FIF kernel suites (class A, hermetic)"
ERG_JOB = "engine-render-guards"

INCUMBENT_STEP = "restore, acquire, project, and sync Filing Forensics SEC sources (hard gate)"
BUNDLE_STEP = "publish disclosure-projection bundle (the engine's render input)"
SELFCHECK_STEP = "restore self-check (byte-verified roundtrip of the published bundle)"
CONTRACT_ACQUIRE_STEP = "acquire contract-issuer filings (isolated, non-gating)"
CONTRACT_CRASH_STEP = "fail on contract-acquire crash"
CAPTURE_STEP = "capture FIF filing packages (contract issuers)"
PUBLISH_STEP = "publish FIF production datasets (hard gate)"
NEW_STEPS = (CAPTURE_STEP, PUBLISH_STEP)
CONTRACT_RESULT_PATH = "fif-contract-acquire-result-${GITHUB_RUN_ID}.json"
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
    # No step anywhere in the lane may soften failures EXCEPT the D13 contract
    # acquire step, whose continue-on-error IS the isolation mechanism (a
    # contract crash must never mark the incumbent steps' job outcome red; the
    # final crash step turns it into a job failure instead).
    for step in steps:
        if step.get("name") == CONTRACT_ACQUIRE_STEP:
            continue
        assert "continue-on-error" not in step, step.get("name")
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


def test_d13_t1_hard_gated_incumbent_step_keeps_mains_semantics() -> None:
    """D13 T1: the hard-gated incumbent invocation is MAIN's semantics exactly —
    the incumbent pinned targets file, both calls at ``--max-tickers 12``, the
    strict-acquisition gate kept, and NO contract derivation anywhere near it."""
    workflow = _workflow()
    steps = _steps(workflow)
    acquire = next(step for step in steps if step.get("name") == INCUMBENT_STEP)
    run = acquire["run"]
    assert "CONTRACT_TARGETS" not in run
    assert "MAX_TICKERS" not in run
    assert "publish_fif_production_datasets" not in run  # no targets derivation
    assert "--require-complete-acquisition" in run
    assert "--targets-file config/fundamental_forensics/wave2_targets.v1.json" in run
    assert run.count("--max-tickers 12") == 2  # both calls at main's value
    assert not re.search(r"--max-tickers\s+(?!12\b)", run)
    # The bundle publish + restore self-check stay incumbent-universe only.
    bundle = next(step for step in steps if step.get("name") == BUNDLE_STEP)
    selfcheck = next(step for step in steps if step.get("name") == SELFCHECK_STEP)
    for step in (bundle, selfcheck):
        assert "--targets-file config/fundamental_forensics/wave2_targets.v1.json" in step["run"]
        assert "$CONTRACT_TARGETS" not in step["run"]
        assert re.search(r"--target\b", step["run"]) is None  # no per-issuer extras


def test_d13_t2_ticker_cap_fifteen_only_on_the_derivation() -> None:
    """D13 T2 (cap half): ``--max-tickers 15`` appears EXACTLY once in the
    workflow — on the contract step's ``targets`` derivation line, where the
    union bound is checked — and every acquire invocation (both incumbent
    calls and the contract call) runs at main's 12. No cap variable exists."""
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    cap_lines = [
        line
        for line in text.splitlines()
        if "--max-tickers 15" in line and not line.lstrip().startswith("#")
    ]
    assert len(cap_lines) == 1, cap_lines
    uses = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue  # prose mentions are not call sites
        uses.extend(re.findall(r"--max-tickers\s+[0-9]+", line))
    assert sorted(uses) == [
        "--max-tickers 12",
        "--max-tickers 12",
        "--max-tickers 12",
        "--max-tickers 15",
    ], uses
    assert "MAX_TICKERS" not in text  # the D13 shape has no cap variable


def test_d13_t2_contract_step_is_isolated_and_non_gating() -> None:
    """D13 T2: the contract acquire step exists with the isolation mechanics —
    id ``contract_acquire``, ``continue-on-error: true``, an integer
    ``timeout-minutes`` <= 15, positioned after the restore self-check and
    before capture — and its wave-2 call carries ONLY the non-gating acquire
    shape over ``$CONTRACT_TARGETS``."""
    workflow = _workflow()
    steps = _steps(workflow)
    names = [step.get("name") for step in steps]
    contract = next(step for step in steps if step.get("name") == CONTRACT_ACQUIRE_STEP)
    assert contract["id"] == "contract_acquire"
    assert contract["continue-on-error"] is True
    timeout = contract["timeout-minutes"]
    assert type(timeout) is int and 0 < timeout <= 15, timeout
    assert names.index(SELFCHECK_STEP) < names.index(CONTRACT_ACQUIRE_STEP) < names.index(CAPTURE_STEP)
    run = contract["run"]
    assert "set -euo pipefail" in run
    assert "$CONTRACT_TARGETS" in run
    assert CONTRACT_RESULT_PATH in run  # stdout result capture
    # The forbidden flags are banned from the WAVE-2 INVOCATION (the
    # derivation line legitimately passes --targets-file to `targets`).
    wave2 = run[run.index("run_fundamental_forensics_wave2") : run.index("contract-acquire-summary")]
    assert "--acquire" in wave2
    assert "--reuse-local-archive" in wave2
    assert "--sync --incremental-sync" in wave2
    assert "--max-tickers 12" in wave2
    assert "--require-complete-acquisition" not in wave2
    assert "--restore" not in wave2.replace("--reuse-local-archive", "")
    assert "--targets-file" not in wave2
    assert not re.search(r"--max-(submissions|document|ticker|total)-bytes", wave2)
    assert "--build-projections" not in wave2  # the contract call builds no projections
    # The derivation (the ONLY place 15 appears) feeds this step's targets.
    assert "publish_fif_production_datasets targets" in run
    assert "--max-tickers 15" in run
    # ...and the wave-2 call consumes the derived targets verbatim.
    assert "$CONTRACT_TARGETS" in wave2
    # The sync needs the private store: the same four secrets the incumbent
    # step uses, and nothing else.
    env = contract.get("env", {})
    assert set(env) == {
        "R2_RESEARCH_ENDPOINT",
        "R2_RESEARCH_ACCESS_KEY_ID",
        "R2_RESEARCH_SECRET_ACCESS_KEY",
        "R2_RESEARCH_BUCKET",
    }
    # A separate observation root so incumbent observation bytes never move.
    assert "observations-contract" in run


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


def test_d13_t3_isolation_confinement_and_crash_gate() -> None:
    """D13 T3: ``CONTRACT_TARGETS`` lives in the contract step ALONE; no
    incumbent step is gated on the contract lane; capture + publish carry the
    known-state success gate; the job's LAST step is the crash gate with the
    exact ``if:`` and a line-start ``::error`` + ``exit 1``; and the
    always-upload carries the two contract files."""
    workflow = _workflow()
    steps = _steps(workflow)
    names = [step.get("name") for step in steps]
    for step in steps:
        run = step.get("run") or ""
        if step.get("name") == CONTRACT_ACQUIRE_STEP:
            assert "CONTRACT_TARGETS" in run
            continue
        assert "CONTRACT_TARGETS" not in run, step.get("name") or step.get("uses")
    # Incumbents are never conditioned on the contract lane.
    for step in steps:
        if step.get("name") in (INCUMBENT_STEP, BUNDLE_STEP, SELFCHECK_STEP):
            assert "contract_acquire" not in str(step.get("if", "")), step["name"]
    gate = "steps.contract_acquire.outcome == 'success'"
    capture = next(step for step in steps if step.get("name") == CAPTURE_STEP)
    publish = next(step for step in steps if step.get("name") == PUBLISH_STEP)
    assert capture["if"] == gate
    assert publish["if"] == gate
    # The capture step consumes the contract acquire summary into its report.
    assert '--contract-acquire-report "$CONTRACT_ACQUIRE_SUMMARY"' in capture["run"]
    assert "fif-contract-acquire-summary-${GITHUB_RUN_ID}.json" in capture["run"]
    # W5: the job's LAST step fails the job on a contract crash, never before.
    assert names[-1] == CONTRACT_CRASH_STEP
    crash = steps[-1]
    assert crash["if"] == "always() && steps.contract_acquire.outcome == 'failure'"
    crash_lines = crash["run"].strip().splitlines()
    assert any(
        line.lstrip().startswith('echo "::error title=fif-contract-acquire::') for line in crash_lines
    ), crash["run"]
    assert any(line.strip() == "exit 1" for line in crash_lines)


def test_d13_w4_upload_carries_the_contract_files() -> None:
    """D13 W4: the always-upload artifact gains the contract acquire result +
    summary, so a crashed contract night still leaves its evidence behind.
    MINOR-3: the acquire-contract run report rides the same always-upload."""
    workflow = _workflow()
    steps = _steps(workflow)
    upload = next(step for step in steps if step.get("name") == UPLOAD_STEP)
    run_text = str(upload["with"]["path"])
    assert "fif-contract-acquire-result-${{ github.run_id }}.json" in run_text
    assert "fif-contract-acquire-summary-${{ github.run_id }}.json" in run_text
    assert "fif-contract-acquire-acquire-report-${{ github.run_id }}.json" in run_text


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


def test_contract_sec_steps_pace_at_two_requests_per_second() -> None:
    # Seat ruling (C0-c r6): the production contract lane is held to <=2 SEC
    # requests/s, so both SEC-touching contract steps pass an explicit 0.5 s
    # minimum interval instead of inheriting the 0.12 s argparse default.
    workflow = _workflow()
    steps = _steps(workflow)
    for name in (CONTRACT_ACQUIRE_STEP, CAPTURE_STEP):
        step = next(step for step in steps if step.get("name") == name)
        assert "--min-interval-seconds 0.5" in step["run"], name


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


def _glob_matches(glob: str, path: str) -> bool:
    """The legacy-jobs path-filter semantics: ``**`` crosses directories, ``*`` does not."""
    pattern = re.escape(glob).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.fullmatch(pattern, path) is not None


def test_new_suites_wired_into_fif_kernel_guards() -> None:
    manifest = yaml.safe_load(LEGACY_JOBS_PATH.read_text(encoding="utf-8"))["jobs"]
    kernel = manifest[FKG_JOB]
    suite_step = next(step for step in kernel["steps"] if step.get("name") == FKG_SUITE_STEP)
    suites = str(suite_step["run"]).split()
    for suite in NEW_TEST_SUITES:
        assert suite in suites, suite
    # One home: a suite that also stayed in the rot sweep would run twice per pack.
    render_guards = yaml.safe_dump(manifest[ERG_JOB])
    for suite in NEW_TEST_SUITES:
        assert suite not in render_guards, suite
    # The job must also START on an edit to any of them or to a producer path.
    globs = [str(glob) for glob in kernel["paths"]]
    for path in NEW_TEST_SUITES + NEW_PRODUCER_PATHS:
        assert any(_glob_matches(glob, path) for glob in globs), path


def test_new_producer_paths_wired_into_owning_curated_job() -> None:
    manifest = yaml.safe_load(LEGACY_JOBS_PATH.read_text(encoding="utf-8"))["jobs"]
    owner = manifest["ticker-news-qbus"]
    paths = owner["paths"]
    for path in NEW_PRODUCER_PATHS:
        assert path in paths, path
