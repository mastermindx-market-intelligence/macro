"""Measured-cost planning: samples -> conservative seconds -> balanced packs.

2026-11-09 migration (Macro #6351 lane B / Mastermind #1607): the pack
planner's balancing weights moved off the mixed heuristic scale — hosted
seconds for ~30 hand-entered dominators in ``OBSERVED_COMMAND_SECONDS``,
text-shape "units" for every other job (1,412 modeled units once executed
5,038 s hosted) — onto conservative observed seconds. Samples come from the
natural-run timing artifacts (PR #10878 collection path), are ingested by
``scripts/update_measured_job_seconds.py`` into
``.github/ci/measured-job-seconds.json``, and are consumed with a freshness
window, upper-tail headroom and a conservative non-zero bound for
unobserved jobs. Per-pack setup/acquisition is modeled separately
(``PACK_SETUP_OVERHEAD_SECONDS``) because every pack pays it once
regardless of grouping: it belongs to wall-time prediction, not balancing.

These tests pin the four properties the migration had to hold:

* the estimator is conservative (max fresh sample, headroom, stale samples
  are unobserved, unobserved is never cheap);
* loading fails safe (a missing or malformed table degrades every job to
  the unobserved bound; planning never crashes on telemetry);
* the ingest tool is fail-closed about ambiguous artifacts and merges by
  run identity instead of duplicating samples;
* REPLAY PARITY — grouping the SAME selected logical workload through the
  frozen legacy estimator and the measured estimator loses no command,
  duplicates nothing, changes no semantic identity or interpreter-isolation
  surface, splits no job across packs, retains the main baseline named-pack
  partition and the baseline-replay plan fields, and does not increase the
  predicted critical-path pack wall.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"

SPEC = importlib.util.spec_from_file_location(
    "run_ci_pack", ROOT / "scripts" / "run_ci_pack.py"
)
assert SPEC and SPEC.loader
PACK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACK
SPEC.loader.exec_module(PACK)

UPDATE_TOOL = ROOT / "scripts" / "update_measured_job_seconds.py"
UPDATE_SPEC = importlib.util.spec_from_file_location(
    "update_measured_job_seconds", UPDATE_TOOL
)
assert UPDATE_SPEC and UPDATE_SPEC.loader
UPDATE = importlib.util.module_from_spec(UPDATE_SPEC)
sys.modules[UPDATE_SPEC.name] = UPDATE
UPDATE_SPEC.loader.exec_module(UPDATE)


TODAY = dt.date(2026, 11, 9)
FRESH = "2026-11-08"
STALE = (TODAY - dt.timedelta(days=PACK.MEASURED_SAMPLE_MAX_AGE_DAYS + 1)).isoformat()


def _sample(
    test_seconds: float,
    observed: str = FRESH,
    *,
    dependency_install_seconds: float = 0.0,
    run_id: str = "42559449303",
    attempt: int = 1,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "attempt": attempt,
        "observed": observed,
        "test_seconds": test_seconds,
        "dependency_install_seconds": dependency_install_seconds,
    }


def _table(
    jobs: dict[str, list[dict[str, object]]], **provenance: object
) -> dict[str, object]:
    return {
        "schema": 1,
        "provenance": {
            "description": "fixture",
            "refreshed_at": TODAY.isoformat(),
            "sources": provenance.get("sources", []),
        },
        "jobs": {
            job_id: (entry if isinstance(entry, dict) else {"samples": entry})
            for job_id, entry in jobs.items()
        },
    }


def _write_table(path: Path, table: dict[str, object]) -> Path:
    path.write_text(json.dumps(table), encoding="utf-8")
    return path


# ── estimator ───────────────────────────────────────────────────────────────

def test_estimator_takes_max_fresh_sample_plus_dependency_and_headroom(tmp_path):
    table = _write_table(tmp_path / "measured.json", _table({
        # two fresh samples: the upper tail (200 s) must win, not the mean
        "alpha": [_sample(200.0), _sample(150.0), _sample(1000.0, STALE)],
        # dependency-install seconds count toward the job's own pack cost
        "beta": [_sample(100.0, dependency_install_seconds=20.0)],
    }))
    weights = PACK.measured_job_weight_table(table, today=TODAY)
    assert weights["alpha"] == 220  # ceil(1.10 * 200), fuzz-safe rounding
    assert weights["beta"] == 132   # ceil(1.10 * 100 + 1.10 * 20 dependency)


def test_the_legacy_migration_seed_never_ages_out(tmp_path):
    """The seeded hand-entered seconds were permanent in code; keep them so.

    Without the exemption, 2026-12-13 would silently drop the ~16 data-gated
    heavyweights a code-gated natural run cannot select (engine-render-guards
    875 s et al.) from 875 s to the 150 s unobserved bound.
    """
    table = _write_table(tmp_path / "measured.json", _table({
        "seeded-heavyweight": [
            _sample(875.0, STALE, run_id=PACK.LEGACY_SEED_RUN_ID),
        ],
        "natural-stale": [_sample(400.0, STALE)],
    }))
    weights = PACK.measured_job_weight_table(table, today=TODAY)
    assert weights == {"seeded-heavyweight": 963}  # ceil(1.1 * 875), kept


def test_stale_or_malformed_samples_are_unobserved(tmp_path):
    table = _write_table(tmp_path / "measured.json", _table({
        "only-stale": [_sample(4000.0, STALE)],
        "bad-date": [{"observed": "not-a-date", "test_seconds": 10.0,
                      "dependency_install_seconds": 0.0, "run_id": "1", "attempt": 1}],
        "bad-seconds": [_sample(-5.0)],
        "not-a-list": {"samples": "nope"},
    }))
    assert PACK.measured_job_weight_table(table, today=TODAY) == {}


def test_table_loading_fails_safe_to_the_unobserved_bound(tmp_path):
    definition = {"steps": [{"run": "pytest tests/test_example.py"}]}
    for broken in (
        tmp_path / "missing.json",                      # absent
        _write_table(tmp_path / "garbage.json", {"jobs": "not json"}),  # wrong shape
        _write_table(tmp_path / "schema.json", {"schema": 99, "jobs": {}}),
        _write_table(tmp_path / "jobs.json", {"schema": 1, "jobs": [1, 2]}),
    ):
        assert PACK.measured_job_weight_table(broken, today=TODAY) == {}
        assert PACK._job_weight("never-observed", definition) == (
            PACK.UNOBSERVED_JOB_COST_SECONDS
        )


def test_unobserved_bound_stays_conservative_against_the_committed_table():
    """Unobserved work must never be cheaper than the typical measured job.

    The bound is re-derived when the committed table is refreshed; this pins
    the floor to the table itself so a refresh that drifts the distribution
    reddens here instead of silently re-cheapening new jobs.
    """
    committed = PACK.measured_job_weight_table(today=TODAY)
    assert committed, "the committed measured table must load and be non-empty"
    measured = sorted(committed.values())
    median = measured[len(measured) // 2]
    assert PACK.UNOBSERVED_JOB_COST_SECONDS >= median, (
        PACK.UNOBSERVED_JOB_COST_SECONDS, median
    )
    assert PACK.UNOBSERVED_JOB_COST_SECONDS >= 60


def test_job_weight_uses_measured_seconds_or_the_bound(tmp_path):
    table = _write_table(tmp_path / "measured.json", _table({
        "observed-job": [_sample(90.0)],
    }))
    original = PACK.MEASURED_JOB_SECONDS_PATH
    try:
        PACK.MEASURED_JOB_SECONDS_PATH = table
        definition = {"steps": [{"run": "pytest tests/test_example.py"}]}
        assert PACK._job_weight("observed-job", definition) == 99  # ceil(1.10 * 90)
        assert PACK._job_weight("some-new-job", definition) == (
            PACK.UNOBSERVED_JOB_COST_SECONDS
        )
    finally:
        PACK.MEASURED_JOB_SECONDS_PATH = original


# ── ingest tool ─────────────────────────────────────────────────────────────

def _artifact_tree(root: Path, records_by_file: dict[str, list[dict[str, object]]]) -> Path:
    artifacts = root / "artifacts"
    for relative, records in records_by_file.items():
        target = artifacts / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )
    return artifacts


def _observed(job: str, phase: str, duration_ns: int) -> dict[str, object]:
    return {
        "logical_job_id": job,
        "phase": phase,
        "status": "observed",
        "started_monotonic_ns": 0,
        "ended_monotonic_ns": duration_ns,
        "duration_ns": duration_ns,
    }


def test_ingest_merges_by_run_identity_and_takes_upper_tail(tmp_path):
    artifacts = _artifact_tree(tmp_path, {
        "pack-0/timing.jsonl": [
            _observed("fif-kernel-guards", "test", 4_700_500_000_000),
            _observed("fif-kernel-guards", "dependency_install", 20_200_000_000),
        ],
        "pack-1/timing.jsonl": [
            _observed("neural-web", "test", 37_000_000_000),
        ],
    })
    output = tmp_path / "measured.json"
    args = ["--artifacts", str(artifacts), "--run-id", "42559449303",
            "--attempt", "1", "--captured", FRESH, "--output", str(output)]
    UPDATE.main(args)
    first = json.loads(output.read_text(encoding="utf-8"))
    assert first["schema"] == 1
    assert first["jobs"]["fif-kernel-guards"]["samples"] == [{
        "run_id": "42559449303", "attempt": 1, "observed": FRESH,
        "test_seconds": 4700.5, "dependency_install_seconds": 20.2,
    }]
    # Re-ingesting the same run is refused without --replace-run (a partial
    # artifact download must not silently drop that run's jobs) and replaces
    # its samples wholesale with it; a second run appends.
    with pytest.raises(UPDATE.IngestError, match="already in the table"):
        UPDATE.main(args)
    UPDATE.main([*args, "--replace-run"])
    second_artifacts = _artifact_tree(tmp_path / "second", {
        "pack-0/timing.jsonl": [
            _observed("fif-kernel-guards", "test", 5_100_000_000_000),
            _observed("unrun-newcomer", "test", 61_000_000_000),
        ],
    })
    UPDATE.main(["--artifacts", str(second_artifacts), "--run-id", "42559449304",
                 "--attempt", "1", "--captured", FRESH, "--output", str(output)])
    merged = json.loads(output.read_text(encoding="utf-8"))
    fif_samples = merged["jobs"]["fif-kernel-guards"]["samples"]
    assert sorted(sample["run_id"] for sample in fif_samples) == [
        "42559449303", "42559449304",
    ]
    weights = PACK.measured_job_weight_table(output, today=TODAY)
    # max fresh sample (5100 s) with headroom, not the mean.
    assert weights["fif-kernel-guards"] == 5610  # ceil(1.10 * 5100)
    assert "unrun-newcomer" in weights


@pytest.mark.parametrize("record", [
    {"logical_job_id": "x", "phase": "tears-down", "status": "observed",
     "duration_ns": 1, "started_monotonic_ns": 0, "ended_monotonic_ns": 1},
    {"logical_job_id": "x", "phase": "test", "status": "speculative",
     "duration_ns": 1, "started_monotonic_ns": 0, "ended_monotonic_ns": 1},
    {"logical_job_id": "x", "phase": "test", "status": "observed",
     "duration_ns": -1, "started_monotonic_ns": 0, "ended_monotonic_ns": -1},
    {"logical_job_id": "x", "phase": "test", "status": "observed",
     "duration_ns": 1, "started_monotonic_ns": 0, "ended_monotonic_ns": 1,
     "surprise": True},
])
def test_ingest_is_fail_closed_on_unknown_shapes(tmp_path, record):
    artifacts = _artifact_tree(tmp_path, {"pack-0/timing.jsonl": [record]})
    with pytest.raises(UPDATE.IngestError):
        UPDATE.main(["--artifacts", str(artifacts), "--run-id", "1",
                     "--attempt", "1", "--captured", FRESH,
                     "--output", str(tmp_path / "out.json")])


def test_a_partial_reingest_cannot_silently_drop_jobs(tmp_path):
    """--replace-run makes wholesale replacement an explicit choice.

    Re-ingesting a run replaces that run's samples wholesale, so a partial
    download (fewer packs, fewer jobs) with the flag deliberately narrows
    the run's job set — visibly, in the reviewed diff — while the refusal
    keeps the accident impossible.
    """
    output = tmp_path / "measured.json"
    full = _artifact_tree(tmp_path / "full", {
        "pack-0/timing.jsonl": [
            _observed("alpha", "test", 100_000_000_000),
            _observed("beta", "test", 200_000_000_000),
        ],
    })
    args = ["--artifacts", str(full), "--run-id", "42", "--attempt", "1",
            "--captured", FRESH, "--output", str(output)]
    UPDATE.main(args)
    assert sorted(json.loads(output.read_text())["jobs"]) == ["alpha", "beta"]

    partial = _artifact_tree(tmp_path / "partial", {
        "pack-0/timing.jsonl": [_observed("alpha", "test", 90_000_000_000)],
    })
    partial_args = ["--artifacts", str(partial), "--run-id", "42", "--attempt", "1",
                    "--captured", FRESH, "--output", str(output)]
    with pytest.raises(UPDATE.IngestError, match="--replace-run"):
        UPDATE.main(partial_args)
    UPDATE.main([*partial_args, "--replace-run"])
    table = json.loads(output.read_text())
    assert sorted(table["jobs"]) == ["alpha"]  # beta is gone — visibly
    assert table["jobs"]["alpha"]["samples"][0]["test_seconds"] == 90.0


def test_ingest_refuses_an_empty_download(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    with pytest.raises(UPDATE.IngestError):
        UPDATE.main(["--artifacts", str(artifacts), "--run-id", "1",
                     "--attempt", "1", "--captured", FRESH,
                     "--output", str(tmp_path / "out.json")])


# ── replay parity: the migration may regroup, never lose or invent work ─────

def _commands(job) -> list[str]:
    return [
        str(step["run"])
        for step in job.definition.get("steps", [])
        if isinstance(step, dict) and "run" in step
    ]


def _semantic_identity(plan) -> list[tuple[str, str, tuple[str, ...]]]:
    return sorted(
        (spec.logical_job_id, spec.job_exec_sha256,
         tuple(step.proof_id for step in spec.steps))
        for spec in plan.semantic_jobs
    )


def test_replay_parity_measured_grouping_preserves_the_selected_workload():
    """Same selected logical workload, old model vs new model, nothing lost.

    The legacy estimator is frozen in ``_legacy_heuristic_weight``; grouping
    the full manifest selection through it versus through the measured table
    must differ ONLY in which pack each untouched job lands in.
    """
    jobs = PACK.load_legacy_jobs(MANIFEST)
    assert any(job.job_id in PACK.measured_job_weight_table(today=TODAY)
               for job in jobs), "the committed table must cover this manifest"

    legacy_jobs = [
        replace(job, weight=PACK._legacy_heuristic_weight(job.job_id, job.definition))
        for job in jobs
    ]
    new_packs = PACK.partition_jobs(jobs, 12)
    old_packs = PACK.partition_jobs(legacy_jobs, 12)

    new_flat = [job for pack in new_packs for job in pack]
    old_flat = [job for pack in old_packs for job in pack]
    # No lost or duplicated logical jobs — and therefore no lost, duplicated
    # or invented commands: the job objects (and their step lists) are the
    # same population in both groupings.
    assert sorted(job.job_id for job in new_flat) == sorted(
        job.job_id for job in jobs
    )
    assert sorted(job.job_id for job in old_flat) == sorted(
        job.job_id for job in jobs
    )
    assert len({job.job_id for job in new_flat}) == len(new_flat)
    assert len({job.job_id for job in old_flat}) == len(old_flat)
    new_commands = sorted(cmd for job in new_flat for cmd in _commands(job))
    old_commands = sorted(cmd for job in old_flat for cmd in _commands(job))
    assert new_commands == old_commands
    # Definitions are shared, not rewritten: interpreter isolation and the
    # per-job venv contract (byte-identical installs share, different
    # installs stay separate) ride the definition, so both groupings keep
    # the identical dependency surface.
    assert sorted(str(PACK.dependency_command(job)) for job in new_flat) == sorted(
        str(PACK.dependency_command(job)) for job in old_flat
    )
    # Semantic identity: identical (job, exec digest, proof ids) population,
    # and no duplicate proof id WITHIN any one job. (The same proof id may
    # legitimately appear in two different jobs — legacy-jobs.yml documents
    # intentional dual-runs — so global uniqueness is not the contract.)
    for packs, label in ((new_packs, "measured"), (old_packs, "legacy")):
        flat = [job for pack in packs for job in pack]
        identities = [
            (job.job_id, PACK.semantic_job_digest(job),
             tuple(step.proof_id for step in PACK.semantic_step_specs(job)))
            for job in flat
        ]
        assert len(identities) == len(jobs), label
        for job in flat:
            proofs = [step.proof_id for step in PACK.semantic_step_specs(job)]
            assert len(proofs) == len(set(proofs)), (label, job.job_id)

    # Predicted wall model, from the measured data only: the migration must
    # not lengthen the critical-path pack. The shared model helper is the
    # one production surface (no test-local copy to drift from it).
    new_walls = sorted(PACK.predicted_pack_walls_seconds(new_packs))
    old_walls = sorted(PACK.predicted_pack_walls_seconds(old_packs))
    total_new = sum(new_walls)
    total_old = sum(old_walls)
    print(
        f"\nmodel: legacy grouping -> measured grouping\n"
        f"  max pack wall: {old_walls[-1]}s -> {new_walls[-1]}s\n"
        f"  total runner-seconds (nonempty packs): {total_old} -> {total_new}"
    )
    assert new_walls[-1] <= old_walls[-1]


def test_replay_parity_main_plan_keeps_baseline_fields_and_named_packs():
    """A main full-suite plan through either model is the same contract.

    The main baseline must never compact (named pack ci-pack-0..11 stay the
    incumbent comparison surface) and the baseline-replay provenance fields
    are grouping-independent: identical eligible/skipped populations, SHAs
    and semantic surface, with only pack membership allowed to move.
    """
    jobs = PACK.load_legacy_jobs(MANIFEST)
    legacy_jobs = [
        replace(job, weight=PACK._legacy_heuristic_weight(job.job_id, job.definition))
        for job in jobs
    ]

    def build(selected):
        return PACK.build_plan(
            selected, None, changed_from=None, scope_mode="off", pack_count=12,
            role="main", event="workflow_dispatch", workflow_run_id="parity",
            tested_tree_sha="a" * 40, subject_head_sha="a" * 40, base_sha="a" * 40,
        )

    new_plan, old_plan = build(jobs), build(legacy_jobs)
    assert new_plan.role == old_plan.role == "main"
    assert new_plan.eligible_job_ids == old_plan.eligible_job_ids
    assert new_plan.skipped_job_ids == old_plan.skipped_job_ids
    assert new_plan.tested_tree_sha == old_plan.tested_tree_sha
    assert new_plan.subject_head_sha == old_plan.subject_head_sha
    assert new_plan.base_sha == old_plan.base_sha
    assert new_plan.changed_from == old_plan.changed_from is None
    assert _semantic_identity(new_plan) == _semantic_identity(old_plan)
    # Both models keep all twelve named baseline packs: no compaction lane.
    assert new_plan.nonempty_pack_indices == tuple(range(12))
    assert old_plan.nonempty_pack_indices == tuple(range(12))
    # The grouping itself IS allowed to differ — that is the entire point of
    # the migration — and each pack's semantic specs stay consistent with it.
    for plan in (new_plan, old_plan):
        placement = {
            spec.logical_job_id: spec.pack_index for spec in plan.semantic_jobs
        }
        assert placement == {
            job_id: index
            for index, pack in enumerate(plan.pack_jobs)
            for job_id in pack
        }


def test_scoped_compaction_parity_across_cost_models():
    """The scoped compactor holds its invariants under either cost model."""
    def synth(weights: list[int]) -> list[object]:
        return [
            PACK.LegacyJob(
                job_id=f"parity-{index}",
                definition={"if": PACK.DISABLED_IF, "runs-on": "ubuntu-latest",
                            "steps": []},
                ordinal=index,
                weight=weight,
                paths=("engine/**",),
            )
            for index, weight in enumerate(weights)
        ]

    measured_style = synth([5193] + [180] * 24 + [42] * 40)
    legacy_style = [
        replace(job, weight=max(1, job.weight // 90)) for job in measured_style
    ]
    for model_jobs in (measured_style, legacy_style):
        baseline = PACK.partition_jobs(model_jobs, 12)
        compact = PACK.compact_scoped_packs(model_jobs, 12)
        flat = [job for pack in compact for job in pack]
        assert sorted(job.job_id for job in flat) == sorted(
            job.job_id for job in model_jobs
        )
        assert len({job.job_id for job in flat}) == len(flat)
        assert max(sum(job.weight for job in pack) for pack in compact) <= max(
            sum(job.weight for job in pack) for pack in baseline
        )


# ── narrowed-lane width budget (2026-11-09 queue census follow-up) ──────────


def _budget_job(job_id: str, ordinal: int, weight: int, paths: tuple[str, ...]):
    return PACK.LegacyJob(
        job_id=job_id,
        definition={"if": PACK.DISABLED_IF, "runs-on": "ubuntu-latest",
                    "steps": []},
        ordinal=ordinal,
        weight=weight,
        paths=paths,
    )


def test_narrowed_pr_lanes_hold_the_width_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The width decision, pinned where it executes: build_plan.

    The 48h queue census (research/ci_pack_measured_costs_20261109/) showed
    the shared hosted fleet saturated for long stretches — extra packs
    serialized behind the backlog instead of starting on demand, while each
    spent a fixed 303 s setup. A genuinely narrowed PR lane therefore
    activates at most NARROWED_PR_MAX_ACTIVE_PACKS packs, and never loses or
    duplicates a selected job doing so. The main full-suite baseline keeps
    every one of its twelve named packs (pinned by the replay-parity test
    above). Scope inference is frozen to the hand-written scopes, exactly as
    the plan-shape tests in test_ci_pack.py freeze it: this test pins the
    width budget, not the inference.
    """
    monkeypatch.setattr(
        PACK, "infer_job_scopes", lambda jobs: (jobs, "frozen for width test")
    )
    heavy = [
        _budget_job(f"heavy-{index}", index, 900, ("engine/**",))
        for index in range(16)
    ]
    off_lane = [
        _budget_job(f"off-{index}", 100 + index, 900, ("site/**",))
        for index in range(3)
    ]
    plan = PACK.build_plan(
        heavy + off_lane,
        ["engine/prophet/plan_book.py"],
        changed_from="0" * 40,
        scope_mode="active",
        pack_count=12,
        role="pr_head",
        event="pull_request",
        workflow_run_id="width-budget",
        tested_tree_sha="a" * 40,
        subject_head_sha="a" * 40,
        base_sha="0" * 40,
    )
    assert plan.role == "pr_head"
    nonempty = [pack for pack in plan.pack_jobs if pack]
    assert 1 <= len(nonempty) <= PACK.NARROWED_PR_MAX_ACTIVE_PACKS
    placed = [job_id for pack in nonempty for job_id in pack]
    assert sorted(placed) == sorted(job.job_id for job in heavy)
    assert len(placed) == len(set(placed))
    assert set(plan.skipped_job_ids) == {job.job_id for job in off_lane}


def test_width_budget_keeps_runner_minutes_at_or_below_the_uncapped_lane():
    """The budget's reason to exist: a capped lane never spends more.

    Total execution seconds are grouping-invariant; every active pack adds
    one PACK_SETUP_OVERHEAD_SECONDS. Capping the bin count therefore caps
    runner-minutes — the quantity the saturated fleet actually rations.
    """
    jobs = [_budget_job(f"w-{index}", index, 900, ("engine/**",))
            for index in range(16)]
    capped = [p for p in PACK.compact_scoped_packs(
        jobs, PACK.NARROWED_PR_MAX_ACTIVE_PACKS) if p]
    uncapped = [p for p in PACK.compact_scoped_packs(jobs, 12) if p]
    assert len(capped) <= PACK.NARROWED_PR_MAX_ACTIVE_PACKS
    assert len(capped) <= len(uncapped)
    capped_walls = PACK.predicted_pack_walls_seconds(capped)
    uncapped_walls = PACK.predicted_pack_walls_seconds(uncapped)
    assert sum(capped_walls) <= sum(uncapped_walls)
    # The work itself is never lost to the tighter budget.
    flat = [job for pack in capped for job in pack]
    assert sorted(job.job_id for job in flat) == sorted(
        job.job_id for job in jobs)


def test_probe_packs_axis_mirrors_the_lane_grant(tmp_path):
    """The probe packs axis reports the lane's grant, not raw demand.

    Under demand the probe selections need ceil(weight/600) packs — more
    than ten under true seconds — but build_plan grants a narrowed lane at
    most NARROWED_PR_MAX_ACTIVE_PACKS, and the axis must mirror that grant
    or it stops guarding runner spend. Below the cap it still follows
    demand, so growth inside the budget stays visible.
    """
    import yaml

    def job(name: str, path: str) -> dict:
        return {
            "if": PACK.DISABLED_IF,
            "runs-on": "ubuntu-latest",
            "steps": [{"name": "fixture", "run": "echo fixture"}],
            "paths": [path],
        }

    # 30 engine jobs x 150 s unobserved bound = 4,500 s demand = 8 packs of
    # 600 s: over the budget, so the axis must clip to the grant.
    over = {"jobs": {f"engine-{index}": job(f"engine-{index}", "engine/**")
                     for index in range(30)}}
    manifest_over = tmp_path / "over.yml"
    manifest_over.write_text(yaml.safe_dump(over), encoding="utf-8")
    row = PACK.packing_probe_measurements(
        manifest_over, [("engine/prophet/plan_book.py", 30, 999_999)],
        max_packs=PACK.NARROWED_PR_MAX_ACTIVE_PACKS,
    )[0]
    assert row["packs"] == PACK.NARROWED_PR_MAX_ACTIVE_PACKS

    # 12 engine jobs = 1,800 s demand = 3 packs: under the budget, so the
    # axis follows demand exactly.
    under = {"jobs": {f"engine-{index}": job(f"engine-{index}", "engine/**")
                      for index in range(12)}}
    manifest_under = tmp_path / "under.yml"
    manifest_under.write_text(yaml.safe_dump(under), encoding="utf-8")
    row = PACK.packing_probe_measurements(
        manifest_under, [("engine/prophet/plan_book.py", 12, 999_999)],
        max_packs=PACK.NARROWED_PR_MAX_ACTIVE_PACKS,
    )[0]
    assert row["packs"] == 3
