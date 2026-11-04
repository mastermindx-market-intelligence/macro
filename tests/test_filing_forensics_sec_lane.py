"""The Filing Forensics SEC lane runs OFF the render path, and the engine only restores.

Moved 2026-08-08.  daily.yml's engine step "restore, acquire, project, and snapshot
Filing Forensics SEC sources (hard gate)" grew 7.4m -> 11.4m -> 15.2m -> 23.3m -> 23.8m
across the 08-05..08-08 engine executions while the SEC bytes it downloads stayed flat
(127.96MB -> 127.93MB).  The cost was the immutable source store, not the source: the
store mints ~121-165 files/night on a FIXED 12-ticker universe, restore does one
sequential R2 GET per manifest entry, sync one conditional PUT plus a readback per file,
and `actions/checkout` clean:true wipes the gitignored store every run, so it was always
a cold full restore (561 -> 1883 restored files, 729 -> 2048 synced, in three days).

What this module pins, and why each pin can actually fail:

1.  **Placement.**  Acquire/project/sync live in `filing-forensics-sec.yml`, and the
    engine step carries neither `--acquire` nor `--sync`.  A re-added flag puts the
    growth straight back onto the render's critical path.
2.  **The gate survived the move.**  The engine step keeps its four R2_RESEARCH secrets
    and no `continue-on-error`: a restore failure must still stop the job before the
    broad build rather than silently rendering an empty private state.
3.  **Ordering is real, not assumed.**  Strict acquisition (`--require-complete-acquisition`)
    must precede `--build-projections`, and the bundle publish must precede its restore
    self-check; a reordered lane could publish projections built from a partial universe.
4.  **One universe, one file.**  Both workflows name the SAME pinned target list, and
    that file still carries exactly the twelve (ticker, CIK) pairs that used to be
    inline in daily.yml.  A drift between producer and consumer is what the bundle's
    ticker-set equality check turns into a red nightly.
5.  **The contract lane is pinned, not exempt.**  The D13 contract acquire (step id
    `contract_acquire`) is a deliberate THIRD wave-2 invocation over
    `$CONTRACT_TARGETS`, so pins 3-4 scope to the incumbent steps BY ID; the contract
    step's own shape — universe derived from the same pinned target file, no inline
    list, no strict-acquisition/projection/restore flags, continue-on-error — is
    pinned here and, end to end, by
    tests/test_fif_publication_workflow_shape.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / ".github/workflows/daily.yml"
LANE = ROOT / ".github/workflows/filing-forensics-sec.yml"
TARGETS_PATH = "config/fundamental_forensics/wave2_targets.v1.json"

ENGINE_STEP = "restore Filing Forensics disclosure projections (hard gate)"
BUNDLE_MODULE = "scripts.fundamental_forensics_disclosure_bundle"
WAVE2_MODULE = "scripts.run_fundamental_forensics_wave2"
#: The D13 contract-acquire step, a deliberate third wave-2 invocation over
#: $CONTRACT_TARGETS. Pins 3-4 were written for the incumbent producer chain, so they
#: exclude this step BY ID (see _incumbent_steps) and its own shape is pinned by
#: test_contract_lane_derives_its_universe_from_the_pinned_target_file.
CONTRACT_STEP_ID = "contract_acquire"
R2_RESEARCH_KEYS = {
    "R2_RESEARCH_ENDPOINT",
    "R2_RESEARCH_ACCESS_KEY_ID",
    "R2_RESEARCH_SECRET_ACCESS_KEY",
    "R2_RESEARCH_BUCKET",
}

#: The twelve pairs that were inline in daily.yml before the move, hardcoded here so
#: the config file cannot quietly change the universe the engine gate expects.
EXPECTED_TARGETS = [
    ("SMCI", "0001375365"),
    ("NVDA", "0001045810"),
    ("AAPL", "0000320193"),
    ("MSFT", "0000789019"),
    ("GOOGL", "0001652044"),
    ("AMZN", "0001018724"),
    ("META", "0001326801"),
    ("TSLA", "0001318605"),
    ("AVGO", "0001730168"),
    ("PLTR", "0001321655"),
    ("AMD", "0000002488"),
    ("ORCL", "0001341439"),
]


@pytest.fixture(scope="module")
def daily() -> dict:
    return yaml.safe_load(DAILY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lane() -> dict:
    return yaml.safe_load(LANE.read_text(encoding="utf-8"))


def _steps(workflow: dict, job: str) -> list[dict]:
    return list(workflow["jobs"][job]["steps"])


def _step(workflow: dict, job: str, name: str) -> dict:
    for step in _steps(workflow, job):
        if step.get("name") == name:
            return step
    raise AssertionError(f"step {name!r} not found in {job}")


def _incumbent_steps(workflow: dict, job: str) -> list[dict]:
    """The job's steps minus the D13 contract lane (pin 5's BY-ID exclusion).

    The contract step is pinned separately, so the at-most-one guard here keeps the
    exclusion from ever widening: a SECOND step carrying the id would silently dodge
    pins 3-4, which is exactly the drift this file exists to catch.
    """
    steps = _steps(workflow, job)
    contract = [step for step in steps if step.get("id") == CONTRACT_STEP_ID]
    assert len(contract) <= 1, (
        f"at most one step may carry id {CONTRACT_STEP_ID!r}, found {len(contract)}"
    )
    return [step for step in steps if step.get("id") != CONTRACT_STEP_ID]


def test_engine_restores_the_bundle_and_no_longer_acquires_or_syncs(daily: dict) -> None:
    step = _step(daily, "engine", ENGINE_STEP)
    run = step["run"]

    assert BUNDLE_MODULE in run
    assert "--restore" in run
    assert TARGETS_PATH in run
    # Scoped to this step's own body: the growth lived in --acquire/--sync.
    assert "--acquire" not in run
    assert "--sync" not in run
    assert WAVE2_MODULE not in run
    assert set(step["env"]) == R2_RESEARCH_KEYS
    assert "continue-on-error" not in step


def test_no_engine_step_runs_the_wave2_flow_any_more(daily: dict) -> None:
    offenders = [
        step.get("name", "(unnamed)")
        for step in _steps(daily, "engine")
        if WAVE2_MODULE in str(step.get("run", ""))
    ]
    assert offenders == []


def test_sec_lane_is_scheduled_off_the_render_path_and_never_cancelled(lane: dict) -> None:
    triggers = lane[True] if True in lane else lane["on"]

    assert triggers["schedule"] == [{"cron": "30 2 * * *"}]
    assert "workflow_dispatch" in triggers
    assert lane["concurrency"]["cancel-in-progress"] is False
    job = lane["jobs"]["acquire_project_sync"]
    assert "macstudio-light" in job["runs-on"]
    assert job["timeout-minutes"] <= 90


def test_sec_lane_keeps_the_fixed_restore_acquire_project_sync_order(lane: dict) -> None:
    body = "\n".join(str(step.get("run", "")) for step in _incumbent_steps(lane, "acquire_project_sync"))

    strict_acquire = body.index("--require-complete-acquisition")
    projections = body.index("--build-projections")
    assert strict_acquire < projections, "projections must never precede strict acquisition"
    assert "--verify-local-restore" in body
    assert "--incremental-sync" in body
    assert body.count(f"python -m {WAVE2_MODULE}") == 2


def test_sec_lane_reuses_the_warm_archive_only_on_the_acquire_invocation(lane: dict) -> None:
    """Reuse belongs to the acquire leg, and the runner refuses it anywhere else.

    The lane re-downloaded a flat ~128MB of already-retained primary documents every
    night (127.96MB -> 127.93MB across 08-05..08-08, zero new filings).  Arming the
    flag on the projection/sync call would fail that call outright.
    """
    body = next(
        str(step.get("run", ""))
        for step in _steps(lane, "acquire_project_sync")
        if WAVE2_MODULE in str(step.get("run", ""))
    )
    first, second = body.split(f"python -m {WAVE2_MODULE}")[1:3]

    assert "--acquire" in first
    assert "--reuse-local-archive" in first
    assert "--reuse-local-archive" not in second
    # Count argument lines only: the step's comment block names the flag too, and a
    # raw substring count would read the rationale as a second arming.
    armed = [
        line
        for line in body.splitlines()
        if "--reuse-local-archive" in line and not line.strip().startswith("#")
    ]
    assert len(armed) == 1


def test_sec_lane_publishes_the_bundle_and_proves_it_restores(lane: dict) -> None:
    names = [step.get("name", "") for step in _steps(lane, "acquire_project_sync")]
    publish = next(index for index, name in enumerate(names) if "publish disclosure-projection bundle" in name)
    selfcheck = next(index for index, name in enumerate(names) if "restore self-check" in name)
    assert publish < selfcheck

    publish_step = _steps(lane, "acquire_project_sync")[publish]
    selfcheck_step = _steps(lane, "acquire_project_sync")[selfcheck]
    assert "--publish" in publish_step["run"]
    assert "--restore" in selfcheck_step["run"]
    for step in (publish_step, selfcheck_step):
        assert set(step["env"]) == R2_RESEARCH_KEYS
        assert "continue-on-error" not in step


def test_every_lane_invocation_uses_the_pinned_target_file(lane: dict) -> None:
    for step in _incumbent_steps(lane, "acquire_project_sync"):
        run = str(step.get("run", ""))
        if WAVE2_MODULE not in run and BUNDLE_MODULE not in run:
            continue
        assert "--target " not in run, "the inline 12-ticker list is the drift this file prevents"
        assert run.count("--targets-file") == run.count("python -m scripts.")
        assert TARGETS_PATH in run


def test_contract_lane_derives_its_universe_from_the_pinned_target_file(lane: dict) -> None:
    """Pin 4 for the contract step: its universe comes FROM the one pinned file.

    The derive subcommand reads the pinned target file to compute the non-incumbent
    extras, and the acquire then runs on that derived list — so a drift between the
    file and the contract universe has the same failure class as pin 4's incumbents.
    """
    contract = [
        step for step in _steps(lane, "acquire_project_sync")
        if step.get("id") == CONTRACT_STEP_ID
    ]
    assert len(contract) == 1, "exactly one contract_acquire step"
    step = contract[0]
    run = str(step["run"])

    assert TARGETS_PATH in run
    assert run.count("--targets-file") == 1
    assert "--target " not in run, "the inline list is derived, never hand-written"
    assert run.count(f"python -m {WAVE2_MODULE}") == 1
    assert "--require-complete-acquisition" not in run
    assert "--build-projections" not in run
    assert "--restore" not in run
    assert step["continue-on-error"] is True


def test_both_workflows_name_the_identical_target_file() -> None:
    assert TARGETS_PATH in DAILY.read_text(encoding="utf-8")
    assert TARGETS_PATH in LANE.read_text(encoding="utf-8")


def test_pinned_target_file_still_carries_the_twelve_inline_pairs() -> None:
    payload = json.loads((ROOT / TARGETS_PATH).read_text(encoding="utf-8"))

    assert payload["schema"] == "fundamental_forensics.wave2_targets/v1"
    pairs = [(item["ticker"], item["cik"]) for item in payload["targets"]]
    assert pairs == EXPECTED_TARGETS
    assert len({ticker for ticker, _ in pairs}) == 12
    assert all(len(cik) == 10 and cik.isdigit() for _, cik in pairs)
