from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import pytest
import yaml

from scripts import ci_semantic_proof as SEMANTIC


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"
SPEC = importlib.util.spec_from_file_location(
    "run_ci_pack_semantic", ROOT / "scripts" / "run_ci_pack.py"
)
assert SPEC and SPEC.loader
PACK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACK
SPEC.loader.exec_module(PACK)

SHA_TREE = "1" * 40
SHA_HEAD = "2" * 40
SHA_BASE = "3" * 40


def _job(
    job_id: str,
    steps: list[dict[str, object]],
    *,
    ordinal: int = 0,
    timeout: int | None = 1,
) -> object:
    definition: dict[str, object] = {
        "if": PACK.DISABLED_IF,
        "runs-on": "ubuntu-latest",
        "steps": steps,
    }
    if timeout is not None:
        definition["timeout-minutes"] = timeout
    return PACK.LegacyJob(job_id, definition, ordinal, 1)


def _write_manifest(path: Path, jobs: list[object]) -> Path:
    payload = {
        "jobs": {
            job.job_id: job.definition
            for job in jobs
        }
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _plan(jobs: list[object], *, changed: list[str] | None = None, pack_count: int | None = None) -> object:
    return PACK.build_plan(
        jobs,
        changed,
        changed_from=SHA_BASE if changed is not None else None,
        scope_mode="active",
        pack_count=pack_count or max(1, len(jobs)),
        workflow_run_id="987654321",
        workflow="ci",
        event="pull_request",
        role="pr_head",
        tested_tree_sha=SHA_TREE,
        subject_head_sha=SHA_HEAD,
        base_sha=SHA_BASE,
    )


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _small_repository(path: Path) -> tuple[str, str]:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "ci@example.test")
    _git(path, "config", "user.name", "CI Test")
    subject = path / "subject.txt"
    subject.write_text("base\n", encoding="utf-8")
    _git(path, "add", "subject.txt")
    _git(path, "commit", "-m", "base")
    base = _git(path, "rev-parse", "HEAD")
    subject.write_text("head\n", encoding="utf-8")
    _git(path, "commit", "-am", "head")
    return base, _git(path, "rev-parse", "HEAD")


def test_real_manifest_only_disambiguates_the_two_duplicate_sbir_steps() -> None:
    payload = yaml.safe_load(MANIFEST.read_text())
    explicit = [
        (job_id, step.get("name"), step["proof_id"])
        for job_id, definition in payload["jobs"].items()
        for step in definition.get("steps", [])
        if isinstance(step, dict) and "proof_id" in step
    ]
    assert explicit == [
        (
            "unrun-government-revenue",
            "SBIR/STTR progression evidence lane — collector + engine rail (#5012)",
            "sbir-sttr-progression-evidence-pre-amount-semantics",
        ),
        (
            "unrun-government-revenue",
            "SBIR/STTR progression evidence lane — collector + engine rail (#5012)",
            "sbir-sttr-progression-evidence-post-amount-semantics",
        ),
    ]


def test_real_manifest_plan_digest_is_shared_with_reconciler() -> None:
    """The exact production proof universe must cross the runner/core boundary."""
    jobs = PACK.load_legacy_jobs(MANIFEST)
    plan = PACK.build_plan(
        jobs,
        [".github/ci/legacy-jobs.yml"],
        changed_from=SHA_BASE,
        scope_mode="active",
        pack_count=12,
        workflow_run_id="987654321",
        workflow="ci",
        event="pull_request",
        role="pr_head",
        tested_tree_sha=SHA_TREE,
        subject_head_sha=SHA_HEAD,
        base_sha=SHA_BASE,
    )

    assert len(plan.semantic_jobs) == len(jobs)
    assert SEMANTIC.authoritative_plan_sha256(plan.to_dict()) == plan.plan_sha256
    # The production census migration is executable: all 614 semantic units now
    # have one non-empty identity unique inside their existing logical job.
    jobs = PACK.load_legacy_jobs(MANIFEST)
    semantic_count = sum(len(PACK.semantic_step_specs(job)) for job in jobs)
    assert semantic_count >= 614


def test_unnamed_and_duplicate_effective_proof_ids_fail_closed(
    tmp_path: Path,
) -> None:
    unnamed = _job("unnamed", [{"run": "true"}])
    path = _write_manifest(tmp_path / "unnamed.yml", [unnamed])
    with pytest.raises(PACK.ManifestError, match="invalid semantic identity"):
        PACK.load_legacy_jobs(path)

    duplicate = _job(
        "duplicate",
        [
            {"name": "same semantic proof", "run": "true"},
            {"name": "same semantic proof", "run": "true"},
        ],
    )
    path = _write_manifest(tmp_path / "duplicate.yml", [duplicate])
    with pytest.raises(PACK.ManifestError, match="not unique"):
        PACK.load_legacy_jobs(path)

    explicit = _job(
        "explicit",
        [
            {"name": "same semantic proof", "proof_id": "proof-a", "run": "true"},
            {"name": "same semantic proof", "proof_id": "proof-b", "run": "true"},
        ],
    )
    assert len(PACK.load_legacy_jobs(_write_manifest(tmp_path / "ok.yml", [explicit]))) == 1


def test_infrastructure_never_receives_a_semantic_identity(tmp_path: Path) -> None:
    job = _job(
        "demo",
        [
            {"uses": "actions/checkout@v4"},
            {"name": "install", "run": "python -m pip install pytest"},
            {"name": "proof", "run": "python -m pytest tests/test_demo.py -q"},
        ],
    )
    specs = PACK.semantic_step_specs(job)
    assert [spec.display_name for spec in specs] == ["proof"]

    job.definition["steps"][1]["proof_id"] = "not-semantic"
    path = _write_manifest(tmp_path / "bad.yml", [job])
    with pytest.raises(PACK.ManifestError, match="dependency infrastructure"):
        PACK.load_legacy_jobs(path)


def test_step_and_job_digests_separate_identity_from_execution_contract(
    tmp_path: Path,
) -> None:
    first = _job(
        "demo",
        [
            {"name": "old display", "proof_id": "stable-proof", "run": "echo ok"},
        ],
    )
    renamed = _job(
        "demo",
        [
            {"name": "new display", "proof_id": "stable-proof", "run": "echo ok"},
        ],
    )
    changed = _job(
        "demo",
        [
            {"name": "old display", "proof_id": "stable-proof", "run": "echo changed"},
        ],
    )
    assert PACK.semantic_step_specs(first)[0].proof_id == "stable-proof"
    assert (
        PACK.semantic_step_specs(first)[0].step_spec_sha256
        == PACK.semantic_step_specs(renamed)[0].step_spec_sha256
    )
    assert (
        PACK.semantic_step_specs(first)[0].step_spec_sha256
        != PACK.semantic_step_specs(changed)[0].step_spec_sha256
    )

    dependency_changed = _job(
        "demo",
        [
            {"name": "install", "run": "python -m pip install pytest==9"},
            {"name": "old display", "proof_id": "stable-proof", "run": "echo ok"},
        ],
    )
    assert PACK.semantic_job_digest(first) != PACK.semantic_job_digest(dependency_changed)

    default_checkout = _job(
        "demo",
        [
            {"uses": "actions/checkout@v4"},
            {"name": "old display", "proof_id": "stable-proof", "run": "echo ok"},
        ],
    )
    full_history = _job(
        "demo",
        [
            {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
            {"name": "old display", "proof_id": "stable-proof", "run": "echo ok"},
        ],
    )
    assert PACK.semantic_job_digest(default_checkout) != PACK.semantic_job_digest(
        full_history
    )

    unsupported = _job(
        "demo",
        [
            {"uses": "actions/checkout@v4", "with": {"fetch-depth": 2}},
            {"name": "proof", "run": "true"},
        ],
    )
    with pytest.raises(PACK.ManifestError, match="not provided by the pack runner"):
        PACK.load_legacy_jobs(
            _write_manifest(tmp_path / "unsupported-action.yml", [unsupported])
        )


def test_fetch_depth_zero_action_is_materialized_for_the_exact_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _job(
        "history",
        [
            {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
            {"name": "proof", "run": "true"},
        ],
    )
    calls: list[tuple[list[str], Path]] = []
    readiness = iter([False, True])

    def run(command: list[str], *, cwd: Path, **_kwargs: object) -> object:
        calls.append((list(command), cwd))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(PACK, "_trusted_git_environment", lambda _root: {})
    monkeypatch.setattr(PACK.subprocess, "run", run)
    monkeypatch.setattr(
        PACK,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: next(readiness),
    )
    PACK._prepare_provided_actions(job, root=tmp_path, tested_tree_sha=SHA_TREE)
    assert calls == [
        (
            [
                "git",
                "fetch",
                "--no-recurse-submodules",
                "--no-tags",
                "--depth=2",
                "origin",
                SHA_TREE,
            ],
            tmp_path,
        )
    ]


def test_fetch_depth_zero_bounded_ancestry_preserves_pr_history_contract(
    tmp_path: Path,
) -> None:
    """Bounded exact-tree history preserves merge/diff/trailer semantics."""
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.email", "ci@example.test")
    _git(source, "config", "user.name", "CI Test")

    base_file = source / "base.txt"
    base_file.write_text("base\n", encoding="utf-8")
    _git(source, "add", "base.txt")
    _git(source, "commit", "-m", "base")
    base_sha = _git(source, "rev-parse", "HEAD")

    _git(source, "checkout", "-b", "feature")
    feature_file = source / "feature.txt"
    feature_file.write_text("feature one\n", encoding="utf-8")
    _git(source, "add", "feature.txt")
    _git(source, "commit", "-m", "feature one")
    feature_file.write_text("feature two\n", encoding="utf-8")
    _git(source, "commit", "-am", "feature two")

    _git(source, "checkout", "main")
    main_file = source / "main.txt"
    main_file.write_text("tested base\n", encoding="utf-8")
    _git(source, "add", "main.txt")
    _git(source, "commit", "-m", "tested base")
    tested_base_sha = _git(source, "rev-parse", "HEAD")

    _git(source, "checkout", "-b", "test-merge")
    _git(source, "merge", "--no-ff", "feature", "-m", "synthetic PR merge")
    tested_sha = _git(source, "rev-parse", "HEAD")

    _git(source, "checkout", "main")
    main_file.write_text("current main\n", encoding="utf-8")
    _git(source, "commit", "-am", "main advanced after tested merge")

    _git(source, "checkout", "-b", "unrelated", base_sha)
    unrelated_file = source / "unrelated.txt"
    unrelated_file.write_text("unrelated\n", encoding="utf-8")
    _git(source, "add", "unrelated.txt")
    _git(source, "commit", "-m", "unrelated")
    unrelated_sha = _git(source, "rev-parse", "HEAD")
    _git(source, "tag", "unrelated-tag", unrelated_sha)
    _git(source, "checkout", "main")

    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "clone", "--bare", str(source), str(remote)],
        check=True,
        capture_output=True,
    )
    checkout = tmp_path / "checkout"
    subprocess.run(
        [
            "git",
            "clone",
            "--depth=1",
            "--branch",
            "test-merge",
            remote.as_uri(),
            str(checkout),
        ],
        check=True,
        capture_output=True,
    )
    assert _git(checkout, "rev-parse", "HEAD") == tested_sha
    before_merge_base = subprocess.run(
        ["git", "merge-base", f"{tested_sha}^1", f"{tested_sha}^2"],
        cwd=checkout,
        capture_output=True,
        text=True,
    )
    assert before_merge_base.returncode != 0

    job = _job(
        "history",
        [
            {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
            {"name": "proof", "run": "true"},
        ],
    )
    PACK._prepare_provided_actions(
        job,
        root=checkout,
        tested_tree_sha=tested_sha,
    )

    git_env = PACK._trusted_git_environment(checkout)
    assert PACK._tested_tree_ancestry_ready(checkout, git_env, tested_sha)
    assert _git(checkout, "merge-base", f"{tested_sha}^1", f"{tested_sha}^2") == base_sha

    subprocess.run(
        [
            "git",
            "fetch",
            "origin",
            "main:refs/remotes/origin/main",
        ],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
    assert _git(checkout, "merge-base", "origin/main", "HEAD") == tested_base_sha
    pr_messages = _git(checkout, "log", "--format=%s", "origin/main..HEAD").splitlines()
    assert "synthetic PR merge" in pr_messages
    assert "feature one" in pr_messages
    assert "feature two" in pr_messages

    unrelated_ref = subprocess.run(
        ["git", "rev-parse", "--verify", "refs/remotes/origin/unrelated"],
        cwd=checkout,
        capture_output=True,
        text=True,
    )
    unrelated_tag = subprocess.run(
        ["git", "rev-parse", "--verify", "refs/tags/unrelated-tag"],
        cwd=checkout,
        capture_output=True,
        text=True,
    )
    unrelated_object = subprocess.run(
        ["git", "cat-file", "-e", unrelated_sha],
        cwd=checkout,
        capture_output=True,
        text=True,
    )
    assert unrelated_ref.returncode != 0
    assert unrelated_tag.returncode != 0
    assert unrelated_object.returncode != 0


def test_fetch_depth_zero_linear_main_stops_after_immediate_parent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _base_sha, tested_sha = _small_repository(source)
    subject = source / "subject.txt"
    subject.write_text("newer main\n", encoding="utf-8")
    _git(source, "commit", "-am", "newer main")
    tested_sha = _git(source, "rev-parse", "HEAD")

    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "clone", "--bare", str(source), str(remote)],
        check=True,
        capture_output=True,
    )
    checkout = tmp_path / "checkout"
    subprocess.run(
        [
            "git",
            "clone",
            "--depth=1",
            "--branch",
            "main",
            remote.as_uri(),
            str(checkout),
        ],
        check=True,
        capture_output=True,
    )

    job = _job(
        "history",
        [
            {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
            {"name": "proof", "run": "true"},
        ],
    )
    PACK._prepare_provided_actions(job, root=checkout, tested_tree_sha=tested_sha)

    git_env = PACK._trusted_git_environment(checkout)
    assert PACK._tested_tree_ancestry_ready(checkout, git_env, tested_sha)
    visible = _git(checkout, "rev-list", "--parents", "-n", "1", tested_sha).split()
    assert len(visible) == 2


def test_plan_v2_hash_binds_provenance_semantic_inventory_and_authority() -> None:
    job = _job("demo", [{"name": "proof", "run": "echo ok"}])
    plan = _plan([job], changed=["engine/example.py"])
    document = plan.to_dict()
    assert document["schema"] == "ci.pack_plan.v2"
    assert document["tested_tree_sha"] == SHA_TREE
    assert document["subject_head_sha"] == SHA_HEAD
    assert document["base_sha"] == SHA_BASE
    assert document["authority_changed"] is False
    assert document["semantic_jobs"] == [
        {
            "logical_job_id": "demo",
            "pack_index": 0,
            "job_exec_sha256": PACK.semantic_job_digest(job),
            "steps": [PACK.semantic_step_specs(job)[0].plan_dict()],
        }
    ]

    command_changed = _job("demo", [{"name": "proof", "run": "echo changed"}])
    assert _plan([command_changed], changed=["engine/example.py"]).plan_sha256 != plan.plan_sha256
    assert _plan([job], changed=["scripts/new_authority.py"]).authority_changed is True
    main = PACK.build_plan(
        [job],
        ["scripts/new_authority.py"],
        changed_from=None,
        scope_mode="active",
        pack_count=1,
        workflow_run_id="1",
        workflow="ci",
        event="workflow_dispatch",
        role="main",
        tested_tree_sha=SHA_TREE,
        subject_head_sha=SHA_TREE,
        base_sha=SHA_TREE,
    )
    assert main.authority_changed is False

    hash_payload = PACK.plan_hash_payload(
        workflow_run_id=plan.workflow_run_id,
        workflow=plan.workflow,
        event=plan.event,
        role=plan.role,
        tested_tree_sha=plan.tested_tree_sha,
        subject_head_sha=plan.subject_head_sha,
        base_sha=plan.base_sha,
        authority_changed=plan.authority_changed,
        changed_from=plan.changed_from,
        scope_mode=plan.scope_mode,
        changed_files_sha256=plan.changed_files_sha256,
        pack_count=plan.pack_count,
        eligible_job_ids=plan.eligible_job_ids,
        pack_jobs=plan.pack_jobs,
        pack_weights=plan.pack_weights,
        semantic_jobs=plan.semantic_jobs,
    )
    baseline = PACK._canonical_digest(hash_payload)
    mutations = {
        "tested_tree_sha": "a" * 40,
        "subject_head_sha": "b" * 40,
        "base_sha": "c" * 40,
        "changed_files_sha256": "d" * 64,
        "authority_changed": True,
    }
    for key, value in mutations.items():
        changed_payload = dict(hash_payload)
        changed_payload[key] = value
        assert PACK._canonical_digest(changed_payload) != baseline, key

    with pytest.raises(PACK.ManifestError, match="main semantic plan"):
        PACK.build_plan(
            [job],
            None,
            changed_from=SHA_BASE,
            scope_mode="active",
            event="workflow_dispatch",
            role="main",
            tested_tree_sha=SHA_TREE,
            subject_head_sha=SHA_TREE,
            base_sha=SHA_TREE,
        )
    with pytest.raises(PACK.ManifestError, match="changed_from must equal"):
        PACK.build_plan(
            [job],
            ["engine/example.py"],
            changed_from=SHA_BASE,
            scope_mode="active",
            event="pull_request",
            role="pr_head",
            tested_tree_sha=SHA_TREE,
            subject_head_sha=SHA_HEAD,
            base_sha="e" * 40,
        )


def test_pack_consumes_the_authoritative_plan_without_replanning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = _job("demo", [{"name": "proof", "run": "echo ok"}])
    manifest = _write_manifest(tmp_path / "manifest.yml", [job])
    loaded_job = PACK.load_legacy_jobs(manifest)[0]
    plan = _plan([loaded_job], changed=["engine/example.py"])
    plan_path = tmp_path / "plan" / "plan.json"
    PACK._atomic_write_json(plan_path, plan.to_dict(), indent=2)
    changed_path = tmp_path / "changed.json"
    changed_path.write_text('["engine/example.py"]\n', encoding="utf-8")

    monkeypatch.setattr(
        PACK,
        "infer_job_scopes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("consumer must not replan")
        ),
    )
    consumed = PACK.load_authoritative_plan(
        plan_path,
        workflow=manifest,
        changed_files_file=changed_path,
        expect_plan_sha=plan.plan_sha256,
        expect_tested_tree_sha=SHA_TREE,
        expect_subject_head_sha=SHA_HEAD,
        expect_base_sha=SHA_BASE,
    )
    assert consumed == plan
    with pytest.raises(PACK.ManifestError, match="expected"):
        PACK.load_authoritative_plan(
            plan_path,
            workflow=manifest,
            changed_files_file=changed_path,
            expect_subject_head_sha="f" * 40,
        )

    duplicate = tmp_path / "duplicate-plan.json"
    duplicate.write_text(
        '{"schema":"ci.pack_plan.v2","schema":"ci.pack_plan.v2"}\n',
        encoding="utf-8",
    )
    with pytest.raises(PACK.ManifestError, match="duplicate key 'schema'"):
        PACK.load_authoritative_plan(duplicate, workflow=manifest)


def _canary_plan(jobs: list[object], *, changed: list[str] | None = None) -> object:
    """The one narrow diagnostic pair: pr_head/workflow_dispatch, admitted
    ONLY under the exact canary workflow name (#6351 P0R bridge, spec A).
    """
    return PACK.build_plan(
        jobs,
        changed,
        changed_from=SHA_BASE if changed is not None else None,
        scope_mode="active",
        pack_count=max(1, len(jobs)),
        workflow_run_id="987654321",
        workflow=PACK.DIAGNOSTIC_CANARY_WORKFLOW,
        event="workflow_dispatch",
        role="pr_head",
        tested_tree_sha=SHA_TREE,
        subject_head_sha=SHA_HEAD,
        base_sha=SHA_BASE,
    )


def test_load_authoritative_plan_admits_the_diagnostic_pair_only_for_its_exact_workflow_name(
    tmp_path: Path,
) -> None:
    """``load_authoritative_plan`` reads ``workflow`` BEFORE its role/event
    validation and grants the same narrow admission ``build_plan`` does — no
    other workflow name may pose as the diagnostic canary, and the refusal
    must fire on the role/event gate itself (before the digest check ever
    runs), not merely because a mutated document happens to hash differently.
    """
    job = _job("demo", [{"name": "proof", "run": "echo ok"}])
    manifest = _write_manifest(tmp_path / "manifest.yml", [job])
    loaded_job = PACK.load_legacy_jobs(manifest)[0]
    plan = _canary_plan([loaded_job], changed=["engine/example.py"])
    plan_path = tmp_path / "plan.json"
    PACK._atomic_write_json(plan_path, plan.to_dict(), indent=2)
    changed_path = tmp_path / "changed.json"
    changed_path.write_text('["engine/example.py"]\n', encoding="utf-8")

    consumed = PACK.load_authoritative_plan(
        plan_path,
        workflow=manifest,
        changed_files_file=changed_path,
        expect_plan_sha=plan.plan_sha256,
    )
    assert consumed.workflow == PACK.DIAGNOSTIC_CANARY_WORKFLOW
    assert consumed.role == "pr_head"
    assert consumed.event == "workflow_dispatch"

    document = json.loads(plan_path.read_text(encoding="utf-8"))
    for other_workflow in ("ci", "some-other-workflow"):
        mutated = dict(document, workflow=other_workflow)
        mutated_path = tmp_path / f"mutated-{other_workflow}.json"
        mutated_path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(PACK.ManifestError, match="unsupported"):
            PACK.load_authoritative_plan(
                mutated_path,
                workflow=manifest,
                changed_files_file=changed_path,
            )


def test_exact_empty_changed_list_round_trips_as_a_distinct_plan_input(
    tmp_path: Path,
) -> None:
    job = _job("demo", [{"name": "proof", "run": "echo ok"}])
    manifest = _write_manifest(tmp_path / "manifest.yml", [job])
    loaded_job = PACK.load_legacy_jobs(manifest)[0]
    plan = _plan([loaded_job], changed=[])
    assert plan.changed_paths == ()
    assert plan.changed_files_sha256 == PACK.changed_files_digest([])
    assert plan.changed_files_sha256

    plan_path = tmp_path / "plan.json"
    changed_path = tmp_path / "changed.json"
    PACK._atomic_write_json(plan_path, plan.to_dict())
    changed_path.write_text("[]\n", encoding="utf-8")
    consumed = PACK.load_authoritative_plan(
        plan_path,
        workflow=manifest,
        changed_files_file=changed_path,
        expect_plan_sha=plan.plan_sha256,
    )
    assert consumed.changed_paths == ()
    assert consumed.plan_sha256 == plan.plan_sha256


def test_runner_and_shared_reconciler_hash_unicode_plan_identically() -> None:
    """Production proof names are UTF-8; JSON escape style is not identity."""
    job = _job("unicode-proof", [{"name": "证明 receipt", "run": "echo ok"}])
    plan = _plan([job], changed=["engine/example.py"])

    assert SEMANTIC.authoritative_plan_sha256(plan.to_dict()) == plan.plan_sha256


def test_invalid_internal_job_result_blocks_infrastructure() -> None:
    job = _job("demo", [{"name": "proof", "run": "true"}])
    execution = PACK._coerce_job_execution(job, None)
    assert execution.infrastructure["outcome"] == "unknown"
    assert execution.steps[0]["outcome"] == "infrastructure_blocked"
    assert execution.failure is not None


def test_logical_job_deadline_yields_timeout_then_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _job(
        "demo",
        [
            {"name": "first", "run": "true"},
            {"name": "second", "run": "true"},
            {"name": "third", "run": "true"},
        ],
        timeout=1,
    )
    ticks = iter([100.0, 100.0, 161.0])
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_args: None)
    calls: list[float] = []

    def stream(*_args: object, timeout_seconds: float, **_kwargs: object) -> object:
        calls.append(timeout_seconds)
        return PACK.CommandObservation(outcome="passed", returncode=0)

    monkeypatch.setattr(PACK, "_stream_command", stream)
    result = PACK._run_job(job, base_ref="main", head_ref="feature", command_env={})
    assert calls == [60.0]
    assert [step["outcome"] for step in result.steps] == [
        "passed",
        "timed_out",
        "not_run_prior_failure",
    ]
    assert result.failure == "demo: timed out after 1 minutes"


def test_step_runner_exception_preserves_prior_pass_and_complete_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _job(
        "demo",
        [
            {"name": "first", "run": "true"},
            {"name": "runner breaks", "run": "true"},
            {"name": "blocked later", "run": "true"},
        ],
    )
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_args: None)
    outcomes: Iterator[object] = iter(
        [
            PACK.CommandObservation(outcome="passed", returncode=0),
            RuntimeError("popen unavailable"),
        ]
    )

    def stream(*_args: object, **_kwargs: object) -> object:
        value = next(outcomes)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(PACK, "_stream_command", stream)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.infrastructure["outcome"] == "unknown"
    assert [step["outcome"] for step in result.steps] == [
        "passed",
        "infrastructure_blocked",
        "infrastructure_blocked",
    ]


def test_dependency_failure_is_infrastructure_and_blocks_every_semantic_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    job = _job(
        "demo",
        [
            {"name": "install", "run": "python -m pip install pytest"},
            {"name": "first proof", "run": "false"},
            {"name": "second proof", "run": "false"},
        ],
    )
    fragment = tmp_path / "fragment.json"
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_args: None)
    monkeypatch.setattr(
        PACK,
        "_dependency_environment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("install exploded")
        ),
    )
    assert PACK.execute_pack([job], emit_semantic_fragment=fragment) == 1
    payload = json.loads(fragment.read_text())
    record = payload["jobs"][0]
    assert record["infrastructure"]["outcome"] == "dependency_failed"
    assert [step["outcome"] for step in record["steps"]] == [
        "infrastructure_blocked",
        "infrastructure_blocked",
    ]
    assert all(step["failure_signature"] is None for step in record["steps"])
    output = capsys.readouterr().out
    assert "::error title=legacy-job-demo::" in output
    assert json.loads(
        next(
            line.split("=", 1)[1]
            for line in output.splitlines()
            if line.startswith("CI_PACK_FAILED_JOBS=")
        )
    ) == ["demo"]


def test_dependency_environment_retries_exact_tls_record_once_in_a_fresh_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    observations = iter(
        [
            PACK.CommandObservation(
                outcome="failed",
                returncode=1,
                detail="exited 1",
                retryable_dependency_transport=True,
            ),
            PACK.CommandObservation(outcome="passed", returncode=0),
        ]
    )
    streamed: list[str] = []
    venv_creations: list[Path] = []

    def stream(command: str, **kwargs: object) -> object:
        streamed.append(command)
        assert kwargs["detect_retryable_dependency_transport"] is True
        return next(observations)

    def run(command: list[str], **_kwargs: object) -> object:
        assert command[:3] == [sys.executable, "-m", "venv"]
        target = Path(command[3])
        sentinel = target / "partial-install"
        if venv_creations:
            assert not sentinel.exists(), "retry inherited the partial first venv"
        target.mkdir(parents=True)
        sentinel.write_text("partial\n", encoding="utf-8")
        venv_creations.append(target)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(PACK.subprocess, "run", run)

    environment = PACK._dependency_environment("python -m pip install plotly")

    assert streamed == [
        "python -m pip install plotly",
        "python -m pip install plotly",
    ]
    assert len(venv_creations) == 2
    assert venv_creations[0] == venv_creations[1]
    assert environment["PATH"].split(os.pathsep, 1)[0] == str(
        tmp_path / "ci-pack-job-env" / "bin"
    )
    output = capsys.readouterr().out
    assert "ci dependency transport retry" in output
    assert "recreating the isolated environment once" in output


def test_dependency_environment_does_not_retry_an_unclassified_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    streamed: list[str] = []

    def stream(command: str, **kwargs: object) -> object:
        streamed.append(command)
        assert kwargs["detect_retryable_dependency_transport"] is True
        return PACK.CommandObservation(
            outcome="failed",
            returncode=23,
            detail="exited 23",
        )

    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(
        PACK.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )

    with pytest.raises(RuntimeError, match="dependency install exited 23"):
        PACK._dependency_environment("python -m pip install plotly")
    assert streamed == ["python -m pip install plotly"]


def test_dependency_environment_fails_after_one_classified_tls_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    calls = 0

    def stream(_command: str, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        assert kwargs["detect_retryable_dependency_transport"] is True
        return PACK.CommandObservation(
            outcome="failed",
            returncode=1,
            detail="exited 1",
            retryable_dependency_transport=True,
        )

    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(
        PACK.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )

    with pytest.raises(RuntimeError, match="after one classified TLS retry"):
        PACK._dependency_environment("python -m pip install plotly")
    assert calls == 2


def test_dependency_environment_records_tls_retry_before_different_second_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    observations = iter(
        [
            PACK.CommandObservation(
                outcome="failed",
                returncode=1,
                detail="exited 1",
                retryable_dependency_transport=True,
            ),
            PACK.CommandObservation(
                outcome="failed",
                returncode=23,
                detail="exited 23",
            ),
        ]
    )
    monkeypatch.setattr(
        PACK,
        "_stream_command",
        lambda *_args, **_kwargs: next(observations),
    )
    monkeypatch.setattr(
        PACK.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )

    with pytest.raises(
        RuntimeError,
        match="dependency install exited 23 after one classified TLS retry",
    ):
        PACK._dependency_environment("python -m pip install plotly")


@pytest.mark.parametrize(
    "command",
    [
        "echo prepare; python -m pip install plotly",
        "python -m pip install plotly && echo replayed",
        "python -m pip install plotly; ./non_idempotent_step",
        "python -m pip install plotly | tee /tmp/output",
        "python -m pip install $(cat requirements.txt)",
        "python -m pip install `cat requirements.txt`",
    ],
)
def test_dependency_command_refuses_a_mixed_shell_body(command: str) -> None:
    job = _job(
        "mixed-install",
        [
            {
                "name": "not standalone",
                "run": command,
            },
            {"name": "proof", "run": "true"},
        ],
    )
    with pytest.raises(PACK.ManifestError, match="not a standalone pip command"):
        PACK.dependency_command(job)


def test_dependency_transport_marker_detection_crosses_stream_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = iter(
        [
            b"ssl.SSLError: [SSL: DECRYPTION_FAILED_OR_BAD_",
            b"RECORD_MAC] decryption failed or bad record mac\n",
            b"",
        ]
    )

    class Process:
        returncode = 1
        pid = 77
        stdout = SimpleNamespace(
            read=lambda _size: next(chunks),
            close=lambda: None,
        )

        def wait(self, timeout: object = None) -> int:
            return self.returncode

    monkeypatch.setattr(PACK.subprocess, "Popen", lambda *_args, **_kwargs: Process())
    observation = PACK._stream_command(
        "python -m pip install plotly",
        env={},
        timeout_seconds=None,
        detect_retryable_dependency_transport=True,
    )
    assert observation.outcome == "failed"
    assert observation.retryable_dependency_transport is True


@pytest.mark.parametrize(
    "near_miss",
    [
        b"ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed\n",
        b"ssl.SSLError: [SSL: DECRYPTION_FAILED] decryption failed\n",
        b"ssl.SSLError: [SSL: DECRYPTION_FAILED_OR_BAD_RECORD] incomplete marker\n",
    ],
)
def test_dependency_transport_near_misses_are_not_retryable(
    monkeypatch: pytest.MonkeyPatch,
    near_miss: bytes,
) -> None:
    chunks = iter([near_miss, b""])

    class Process:
        returncode = 1
        pid = 77
        stdout = SimpleNamespace(
            read=lambda _size: next(chunks),
            close=lambda: None,
        )

        def wait(self, timeout: object = None) -> int:
            return self.returncode

    monkeypatch.setattr(PACK.subprocess, "Popen", lambda *_args, **_kwargs: Process())
    observation = PACK._stream_command(
        "python -m pip install plotly",
        env={},
        timeout_seconds=None,
        detect_retryable_dependency_transport=True,
    )
    assert observation.outcome == "failed"
    assert observation.retryable_dependency_transport is False


def test_explicit_changed_file_handle_overrides_stale_child_transports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = tmp_path / "stale.json"
    authoritative = tmp_path / "authoritative.json"
    monkeypatch.setenv("CI_CHANGED_FILES_FILE", str(stale))
    monkeypatch.setenv("CI_CHANGED_FILES_JSON", '["stale.py"]')
    child = PACK._child_environment(authoritative)
    assert child["CI_CHANGED_FILES_FILE"] == str(authoritative)
    assert "CI_CHANGED_FILES_JSON" not in child


def test_child_environment_strips_repo_binding_git_vars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/foreign/repository/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/foreign/repository")
    monkeypatch.setenv("GIT_INDEX_FILE", "/foreign/repository/.git/index")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "keep-me")
    handle = tmp_path / "changed.json"
    handle.write_text("[]", encoding="utf-8")
    child = PACK._child_environment(handle)
    assert "GIT_DIR" not in child
    assert "GIT_WORK_TREE" not in child
    assert "GIT_INDEX_FILE" not in child
    assert child["GIT_AUTHOR_NAME"] == "keep-me"
    assert child["CI_CHANGED_FILES_FILE"] == str(handle)


def test_streaming_capture_retains_only_one_bounded_prefix_of_a_giant_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    collectors: list[object] = []

    class SpyCollector:
        def __init__(self, **limits: int) -> None:
            self.limits = limits
            self.feeds: list[bytes] = []
            collectors.append(self)

        def feed(self, value: str | bytes, *, truncated: bool = False) -> None:
            encoded = value if isinstance(value, bytes) else value.encode()
            self.feeds.append(encoded)

        def signature(self) -> None:
            return None

    monkeypatch.setattr(PACK, "FailureAtomCollector", SpyCollector)
    command = (
        f"{sys.executable} -c \"import sys; "
        "sys.stdout.write('x'*200000); sys.exit(7)\""
    )
    result = PACK._stream_command(
        command,
        env=os.environ,
        timeout_seconds=10,
    )
    capsys.readouterr()  # discard the deliberately streamed live payload
    collector = collectors[0]
    assert collector.limits == {
        "max_bytes": PACK.FAILURE_CAPTURE_MAX_BYTES,
        "max_atoms": PACK.FAILURE_CAPTURE_MAX_ATOMS,
        "max_line_bytes": PACK.FAILURE_CAPTURE_MAX_LINE_BYTES,
    }
    assert len(collector.feeds) == 1
    assert len(collector.feeds[0]) == PACK.FAILURE_CAPTURE_MAX_LINE_BYTES
    assert result.outcome == "failed"
    assert result.detail == "exited 7"
    assert "x" * 100 not in json.dumps(result.__dict__)


def test_streaming_capture_finds_a_late_failure_atom(
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = (
        "import sys\n"
        "for index in range(2000): print(f'benign {index} ' + 'x' * 90)\n"
        "print('FAILED tests/test_demo.py::test_late - assertion changed')\n"
        "sys.exit(1)\n"
    )
    result = PACK._stream_command(
        f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}",
        env=os.environ,
        timeout_seconds=20,
    )
    capsys.readouterr()
    assert result.outcome == "failed"
    assert result.failure_signature is not None
    assert any(
        atom.startswith("pytest:failed:tests/test_demo.py::test_late")
        for atom in result.failure_signature["atoms"]
    )


def test_overlong_failure_atom_is_non_comparable_instead_of_prefix_colliding(
    capsys: pytest.CaptureFixture[str],
) -> None:
    signatures: list[object] = []
    for tail in ("HEAD_ASSERTION", "BASE_EXCEPTION"):
        summary = "FAILED tests/test_long.py::test_same - " + "A" * 5000 + tail
        script = f"import sys; print({summary!r}); sys.exit(1)"
        result = PACK._stream_command(
            f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}",
            env=os.environ,
            timeout_seconds=20,
        )
        signatures.append(result.failure_signature)
    capsys.readouterr()
    assert signatures == [None, None]


def test_exact_sha_acquisition_fetches_only_the_requested_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def git_run(args: list[str], **_kwargs: object) -> object:
        calls.append(list(args))
        if args[1:3] == ["cat-file", "-e"]:
            return SimpleNamespace(returncode=1, stdout="")
        if args[1] == "rev-parse":
            return SimpleNamespace(returncode=0, stdout=SHA_BASE + "\n")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(PACK, "_git_run_bounded", git_run)
    assert PACK._ensure_exact_commit(tmp_path, SHA_BASE, deadline=999999999.0) == SHA_BASE
    fetch = next(command for command in calls if command[1] == "fetch")
    assert fetch == [
        "git",
        "fetch",
        "--no-tags",
        "--depth=1",
        "origin",
        SHA_BASE,
    ]
    assert all("--unshallow" not in command for command in calls)


def test_exact_base_checkout_pins_origin_main_even_after_source_advances(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    base_sha, head_sha = _small_repository(source)
    assert _git(source, "rev-parse", "main") == head_sha
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))

    with PACK._exact_base_worktree(
        source,
        base_sha,
        deadline=PACK.time.monotonic() + 30,
    ) as replay:
        assert _git(replay, "rev-parse", "HEAD") == base_sha
        assert _git(replay, "rev-parse", "origin/main") == base_sha
        _git(replay, "fetch", "origin", "main")
        assert _git(replay, "rev-parse", "origin/main") == base_sha
        assert Path(_git(replay, "rev-parse", "--git-dir")).resolve() != (
            source / ".git"
        ).resolve()


def _blobless_partial_clone(tmp_path: Path) -> tuple[Path, str, str]:
    """Build a ``blob:none`` partial-clone runner checkout.

    ci.yml handed every hosted pack ``filter: blob:none`` + ``fetch-depth: 1``
    until 2026-09-23 (DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION); the replay must
    still survive that shape wherever it persists (a partial-clone runner
    borrows objects that are missing exactly the blobs the PR changed).
    Reproducing that needs a server that honours the filter — a bare
    repo without ``uploadpack.allowFilter`` answers "filtering not recognized
    by server, ignoring" and hands back a COMPLETE clone, which is how this
    trap hides from a test that looks correct.
    """
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    _git(origin, "config", "uploadpack.allowFilter", "true")
    _git(origin, "config", "uploadpack.allowAnySHA1InWant", "true")

    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.email", "ci@example.test")
    _git(source, "config", "user.name", "CI Test")
    (source / "changed.txt").write_text("base\n", encoding="utf-8")
    (source / "untouched.txt").write_text("shared\n", encoding="utf-8")
    _git(source, "add", "-A")
    _git(source, "commit", "-m", "base")
    base = _git(source, "rev-parse", "HEAD")
    (source / "changed.txt").write_text("head\n", encoding="utf-8")
    _git(source, "commit", "-am", "head")
    head = _git(source, "rev-parse", "HEAD")
    _git(source, "remote", "add", "origin", str(origin))
    _git(source, "push", "origin", "main")

    work = tmp_path / "work"
    _git(
        tmp_path,
        "clone",
        "--filter=blob:none",
        "--depth=1",
        "--no-local",
        origin.as_uri(),
        str(work),
    )
    # The base commit is not in a depth-1 checkout; acquiring it is exactly what
    # `_ensure_exact_commit` does, and it brings trees without blobs.
    _git(work, "fetch", "--no-tags", "--depth=1", "origin", base)
    return work, base, head


def _locally_missing_blobs(work: Path, sha: str) -> list[str]:
    oids = [
        line.split()[2]
        for line in _git(work, "ls-tree", "-r", sha).splitlines()
        if line.split()[1] == "blob"
    ]
    probe = subprocess.run(
        ["git", "cat-file", "--batch-check"],
        cwd=work,
        input="".join(f"{oid}\n" for oid in oids),
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )
    return [
        line.split(" ", 1)[0]
        for line in probe.stdout.splitlines()
        if line.endswith(" missing")
    ]


def test_base_replay_checks_out_a_base_sha_inside_a_partial_clone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A classifier that degrades to ``unknown`` reads as "probably your fault".

    Measured on PR #5853: `git checkout --detach --force <base>` inside the
    replay repository exited 1 on every pack, on every base, because alternates
    share OBJECTS but neither the partial-clone extension nor the promisor
    remote that could fetch the omitted ones. Every main-inherited red on the
    fleet was then reported `classification=unknown`, and `ship_loop_guard.py`
    charged it to the PR under the INTERNAL block ladder.
    """
    work, base, head = _blobless_partial_clone(tmp_path)

    # Guard the guard: if the fixture ever stops omitting blobs, this test is
    # vacuous and must say so rather than pass.
    missing = _locally_missing_blobs(work, base)
    assert missing, (
        "fixture is not a partial clone — no blob at the base commit is "
        "missing locally, so this test could not observe the defect"
    )

    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path / "runner-temp"))
    (tmp_path / "runner-temp").mkdir()
    with PACK._exact_base_worktree(
        work,
        base,
        deadline=PACK.time.monotonic() + 120,
    ) as replay:
        assert _git(replay, "rev-parse", "HEAD") == base
        # Content, not just the ref: a checkout that skipped unreadable blobs
        # still moves HEAD and still exits 1.
        assert (replay / "changed.txt").read_text(encoding="utf-8") == "base\n"
        assert (replay / "untouched.txt").read_text(encoding="utf-8") == "shared\n"
        assert _git(replay, "status", "--porcelain") == ""
    assert head != base


def test_base_replay_hydration_is_a_noop_without_a_promisor_remote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full checkout must not pay for, or trip over, partial-clone repair."""
    source = tmp_path / "source"
    base, _head = _small_repository(source)
    assert PACK._promisor_remote(source, deadline=PACK.time.monotonic() + 30) is None

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("hydration probed a repository with no promisor remote")

    monkeypatch.setattr(PACK, "_missing_tree_objects", _fail)
    PACK._hydrate_exact_base_objects(
        source, base, deadline=PACK.time.monotonic() + 30
    )


def test_a_failed_replay_command_reports_git_stderr_not_only_its_exit_status(
) -> None:
    """The exit status alone is why this stayed invisible for a whole fleet."""
    failure = subprocess.CalledProcessError(
        1,
        ["git", "checkout", "--detach", "--force", SHA_BASE],
        output="",
        stderr="error: unable to read sha1 file of data/x.json (deadbeef)\n",
    )
    detail = PACK._bounded_detail(failure)
    assert "returned non-zero exit status 1" in detail
    assert "unable to read sha1 file of data/x.json" in detail
    assert "\n" not in detail


def test_each_job_restores_and_verifies_the_immutable_tested_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, other_sha = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    first = _job(
        "moves-head",
        [
            {"name": "move checkout", "run": f"git checkout --detach {other_sha}"},
            {"name": "must not run", "run": "true"},
        ],
        ordinal=0,
    )
    second = _job(
        "observes-bound-tree",
        [
            {
                "name": "exact tree proof",
                "run": f'test "$(git rev-parse HEAD)" = "{tested_sha}"',
            }
        ],
        ordinal=1,
    )
    plan = PACK.build_plan(
        [first, second],
        None,
        changed_from=None,
        scope_mode="active",
        pack_count=1,
        workflow_run_id="1",
        workflow="ci",
        event="workflow_dispatch",
        role="main",
        tested_tree_sha=tested_sha,
        subject_head_sha=tested_sha,
        base_sha=tested_sha,
    )
    fragment = tmp_path / "fragment.json"
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path / "runner-temp"))
    (tmp_path / "runner-temp").mkdir()
    monkeypatch.chdir(source)
    monkeypatch.setattr(PACK, "_workspace_root", lambda: source)
    assert (
        PACK.execute_pack(
            [first, second],
            plan=plan,
            emit_semantic_fragment=fragment,
            enable_base_replay=False,
        )
        == 1
    )
    payload = json.loads(fragment.read_text())
    by_job = {row["logical_job_id"]: row for row in payload["jobs"]}
    assert by_job["moves-head"]["infrastructure"]["outcome"] == "unknown"
    assert [step["outcome"] for step in by_job["moves-head"]["steps"]] == [
        "infrastructure_blocked",
        "infrastructure_blocked",
    ]
    assert by_job["observes-bound-tree"]["steps"][0]["outcome"] == "passed"
    assert _git(source, "rev-parse", "HEAD") == tested_sha


def test_git_replace_metadata_cannot_substitute_the_tested_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, replacement_sha = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    job = _job(
        "replace-tree",
        [
            {
                "name": "plant replacement",
                "run": f"git replace {tested_sha} {replacement_sha}",
            },
            {"name": "must remain blocked", "run": "true"},
        ],
    )
    monkeypatch.chdir(source)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=os.environ.copy(),
        tested_tree_sha=tested_sha,
    )
    assert result.infrastructure["outcome"] == "unknown"
    assert [step["outcome"] for step in result.steps] == [
        "infrastructure_blocked",
        "infrastructure_blocked",
    ]
    PACK._restore_workspace(tested_sha)
    assert _git(source, "for-each-ref", "--format=%(refname)", "refs/replace") == ""
    assert _git(source, "rev-parse", "HEAD") == tested_sha


def _stub_for_each_ref_128(monkeypatch: pytest.MonkeyPatch) -> None:
    real = PACK.subprocess.run

    def wrapped(args: object, **kwargs: object) -> object:
        argv = [str(part) for part in list(args)]  # type: ignore[arg-type]
        if len(argv) >= 2 and argv[0] == "git" and argv[1] == "for-each-ref":
            return subprocess.CompletedProcess(
                argv,
                128,
                stdout="",
                stderr="fatal: Unable to create packed-refs.lock: File exists\n",
            )
        return real(args, **kwargs)

    monkeypatch.setattr(PACK.subprocess, "run", wrapped)


def test_for_each_ref_128_without_replace_refs_is_not_infra_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A racy replace-ref probe must not fail a job that did not rewrite history.

    Measured 2026-08-15 on PR #5750 pack-9: the 5-minute deadline SIGKILL'd
    pytest, then `git for-each-ref refs/replace` exited 128 and was reported
    as infrastructure unknown.
    """
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    _stub_for_each_ref_128(monkeypatch)
    job = _job("probe-128", [{"name": "ok", "run": "true"}])
    monkeypatch.chdir(source)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=os.environ.copy(),
        tested_tree_sha=tested_sha,
    )
    assert result.failure is None
    assert result.infrastructure["outcome"] == "passed"
    assert [step["outcome"] for step in result.steps] == ["passed"]


def test_filesystem_replace_refs_still_block_when_for_each_ref_exits_128(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, replacement_sha = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    _stub_for_each_ref_128(monkeypatch)
    job = _job(
        "replace-hidden",
        [
            {
                "name": "plant replacement",
                "run": f"git replace {tested_sha} {replacement_sha}",
            }
        ],
    )
    monkeypatch.chdir(source)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=os.environ.copy(),
        tested_tree_sha=tested_sha,
    )
    assert result.infrastructure["outcome"] == "unknown"
    assert result.steps[0]["outcome"] == "infrastructure_blocked"
    assert "replace" in str(result.failure)


def test_timed_out_step_is_not_masked_by_rewrite_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    job = _job("slow", [{"name": "sleep", "run": "true"}])
    monkeypatch.chdir(source)

    def fake_stream(*_args: object, **_kwargs: object) -> object:
        return PACK.CommandObservation(
            outcome="timed_out",
            returncode=None,
            failure_signature=None,
            detail="semantic step exceeded its job timeout",
        )

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError(
            "Command '['git', 'for-each-ref', '--format=%(refname)', "
            "'refs/replace']' returned non-zero exit status 128."
        )

    monkeypatch.setattr(PACK, "_stream_command", fake_stream)
    monkeypatch.setattr(PACK, "_assert_no_git_rewrites", boom)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=os.environ.copy(),
        tested_tree_sha=tested_sha,
    )
    assert result.failure is not None
    assert "timed out" in result.failure
    assert "infrastructure unknown" not in result.failure
    assert [step["outcome"] for step in result.steps] == ["timed_out"]


def test_trusted_git_environment_disables_optional_locks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    _small_repository(source)
    monkeypatch.setenv("GIT_DIR", "/foreign/repository/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/foreign/repository")
    env = PACK._trusted_git_environment(source)
    assert env["GIT_OPTIONAL_LOCKS"] == "0"
    assert env["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert "GIT_DIR" not in env
    assert "GIT_WORK_TREE" not in env


def test_rewrite_probe_uses_checkout_path_not_foreign_git_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    monkeypatch.setenv("GIT_DIR", "/foreign/repository/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/foreign/repository")
    PACK._assert_no_git_rewrites(source)
    assert PACK._current_commit_sha(source) == tested_sha


def test_job_steps_must_not_inherit_checkout_git_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nested `git init` must not operate on the pack checkout.

    Measured 2026-08-15 on PR #5750: GIT_DIR/GIT_WORK_TREE in the job env
    made tmp_path inits hit the CI tree (exit 128), a sparse cone hid
    tests/*.py (pytest usage exit 4), and rev-parse HEAD then failed as
    infrastructure unknown.
    """
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    nested = tmp_path / "nested-work"
    job = _job(
        "nested-git",
        [
            {
                "name": "init a throwaway repo",
                "run": (
                    f"mkdir -p {shlex.quote(str(nested))} && "
                    f"git init -q -b main {shlex.quote(str(nested))} && "
                    f"git -C {shlex.quote(str(nested))} config user.email t@t && "
                    f"git -C {shlex.quote(str(nested))} config user.name t && "
                    f"git -C {shlex.quote(str(nested))} commit --allow-empty -qm seed"
                ),
            }
        ],
    )
    monkeypatch.chdir(source)
    captured: list[dict[str, str]] = []
    real_stream = PACK._stream_command

    def stream(
        command: str,
        *,
        env: dict[str, str],
        timeout_seconds: float | None = None,
    ) -> object:
        captured.append(dict(env))
        return real_stream(command, env=env, timeout_seconds=timeout_seconds)

    monkeypatch.setattr(PACK, "_stream_command", stream)
    planted = os.environ.copy()
    planted["GIT_DIR"] = str(source / ".git")
    planted["GIT_WORK_TREE"] = str(source)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=planted,
        tested_tree_sha=tested_sha,
    )
    assert result.failure is None
    assert [step["outcome"] for step in result.steps] == ["passed"]
    assert captured
    assert "GIT_DIR" not in captured[0]
    assert "GIT_WORK_TREE" not in captured[0]
    assert captured[0].get("GIT_NO_REPLACE_OBJECTS") == "1"
    assert (nested / ".git").exists()
    assert _git(nested, "rev-parse", "--is-inside-work-tree") == "true"
    assert _git(source, "rev-parse", "HEAD") == tested_sha


def test_restore_workspace_reopens_a_sparse_cone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    _small_repository(source)
    keep = source / "keep" / "nested"
    skip = source / "skip" / "nested"
    keep.mkdir(parents=True)
    skip.mkdir(parents=True)
    (keep / "a.txt").write_text("keep\n", encoding="utf-8")
    (skip / "b.txt").write_text("skip\n", encoding="utf-8")
    _git(source, "add", "keep", "skip")
    _git(source, "commit", "-m", "nested")
    tested_sha = _git(source, "rev-parse", "HEAD")
    _git(source, "checkout", "--detach", tested_sha)
    _git(source, "sparse-checkout", "init", "--cone")
    _git(source, "sparse-checkout", "set", "--cone", "--", "keep")
    assert not (skip / "b.txt").exists()
    assert (keep / "a.txt").exists()
    monkeypatch.chdir(source)
    PACK._restore_workspace(tested_sha)
    assert _git(source, "rev-parse", "HEAD") == tested_sha
    assert (skip / "b.txt").read_text(encoding="utf-8") == "skip\n"


def _assert_pack_git_boundary(source: Path, tested_sha: str) -> None:
    assert _git(source, "for-each-ref", "--format=%(refname)", "refs/replace") == ""
    assert _git(source, "rev-parse", "HEAD") == tested_sha


def test_restore_workspace_heals_corrupt_packed_refs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    (source / ".git" / "packed-refs").write_text("not-valid\n", encoding="utf-8")
    with pytest.raises(subprocess.CalledProcessError):
        _git(source, "for-each-ref", "--format=%(refname)", "refs/replace")
    monkeypatch.chdir(source)
    PACK._restore_workspace(tested_sha)
    _assert_pack_git_boundary(source, tested_sha)
    assert (source / "subject.txt").read_text(encoding="utf-8") == "base\n"


def test_restore_workspace_heals_missing_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    (source / ".git" / "HEAD").unlink()
    monkeypatch.chdir(source)
    PACK._restore_workspace(tested_sha)
    _assert_pack_git_boundary(source, tested_sha)


def test_passed_step_that_breaks_packed_refs_leaves_probes_working(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    job = _job(
        "smash-refs",
        [{"name": "corrupt packed-refs", "run": "printf 'not-valid\\n' > .git/packed-refs"}],
    )
    monkeypatch.chdir(source)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=os.environ.copy(),
        tested_tree_sha=tested_sha,
    )
    assert result.infrastructure["outcome"] == "unknown"
    assert [step["outcome"] for step in result.steps] == ["infrastructure_blocked"]
    _assert_pack_git_boundary(source, tested_sha)


def test_timeout_after_broken_git_retains_original_without_unsafe_healing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    tested_sha, _other = _small_repository(source)
    _git(source, "checkout", "--detach", tested_sha)
    job = _job(
        "timeout-smash",
        [{"name": "killed mid-step", "run": "true"}],
    )

    def stream(
        command: str,
        *,
        env: dict[str, str],
        timeout_seconds: float | None = None,
    ) -> object:
        (source / ".git" / "packed-refs").write_text("not-valid\n", encoding="utf-8")
        return PACK.CommandObservation(
            outcome="timed_out",
            returncode=None,
            failure_signature=None,
            detail="semantic step exceeded its job timeout",
        )

    monkeypatch.chdir(source)
    monkeypatch.setattr(PACK, "_stream_command", stream)
    result = PACK._run_job(
        job,
        base_ref="main",
        head_ref="",
        command_env=os.environ.copy(),
        tested_tree_sha=tested_sha,
    )
    assert result.infrastructure["outcome"] == "unknown"
    assert result.timeout_settlement == "unknown"
    assert result.failure == "timeout-smash: timed out after 1 minutes"
    assert [step["outcome"] for step in result.steps] == ["timed_out"]
    assert (source / ".git/packed-refs").read_text() == "not-valid\n"


def test_base_replay_uses_base_runner_and_is_serial_without_matrix_fanout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for capability in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_URL",
        "ACTIONS_CACHE_URL",
        "ACTIONS_RESULTS_URL",
    ):
        monkeypatch.setenv(capability, "must-not-reach-base")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/candidate/controlled/library/path")
    monkeypatch.setattr(
        PACK,
        "_selected_python_loader_environment",
        lambda: {"LD_LIBRARY_PATH": "/trusted/python-3.12.13/lib"},
    )
    jobs = [
        _job("alpha", [{"name": "proof alpha", "run": "false"}], ordinal=0),
        _job("beta", [{"name": "proof beta", "run": "false"}], ordinal=1),
    ]
    plan = _plan(jobs, changed=["engine/example.py"])
    base_root = tmp_path / "exact-base-worktree"
    (base_root / "scripts").mkdir(parents=True)
    (base_root / ".github" / "ci").mkdir(parents=True)
    (base_root / "scripts" / "run_ci_pack.py").write_text("# base runner\n")
    (base_root / ".github" / "ci" / "legacy-jobs.yml").write_text("jobs: {}\n")

    @contextlib.contextmanager
    def base_worktree(*_args: object, **_kwargs: object) -> Iterator[Path]:
        yield base_root

    monkeypatch.setattr(PACK, "_exact_base_worktree", base_worktree)
    calls: list[tuple[list[str], Path, dict[str, str]]] = []
    active = 0
    max_active = 0

    def stream(
        command: list[str], *, cwd: Path, env: dict[str, str], deadline: float
    ) -> tuple[int, bool]:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        job_id = command[command.index("--semantic-replay-job") + 1]
        output = Path(command[command.index("--emit-semantic-fragment") + 1])
        calls.append((list(command), cwd, dict(env)))
        output.write_text(
            json.dumps(
                {
                    "schema": PACK.FRAGMENT_SCHEMA,
                    "tested_tree_sha": SHA_BASE,
                    "subject_head_sha": SHA_BASE,
                    "base_sha": SHA_BASE,
                    "role": "main",
                    "jobs": [
                        {
                            "logical_job_id": job_id,
                            "job_exec_sha256": "a" * 64,
                            "infrastructure": {"outcome": "passed"},
                            "steps": [
                                {
                                    "proof_id": f"proof-{job_id}",
                                    "step_spec_sha256": "b" * 64,
                                    "outcome": "passed",
                                    "failure_signature": None,
                                }
                            ],
                        }
                    ],
                }
            )
        )
        active -= 1
        return 0, False

    monkeypatch.setattr(PACK, "_stream_process_with_deadline", stream)
    records = [
        {
            "logical_job_id": job.job_id,
            "job_exec_sha256": PACK.semantic_job_digest(job),
            "infrastructure": {"outcome": "passed"},
            "steps": [
                {
                    **PACK.semantic_step_specs(job)[0].plan_dict(),
                    "outcome": "failed",
                    "failure_signature": {"sha256": "c" * 64, "atoms": ["x"]},
                }
            ],
        }
        for job in jobs
    ]
    PACK._run_exact_base_replays(
        root=tmp_path,
        plan=plan,
        records=records,
        budget_seconds=60,
    )
    assert max_active == 1
    assert len(calls) == 2
    for command, cwd, env in calls:
        assert command[1] == str(base_root / "scripts" / "run_ci_pack.py")
        assert cwd == base_root
        assert env["GITHUB_WORKSPACE"] == str(base_root)
        assert env["CI_BASE_REF"] == "main"
        assert env["CI_HEAD_REF"] == "main"
        assert env["LD_LIBRARY_PATH"] == "/trusted/python-3.12.13/lib"
        assert Path(env["CI_CHANGED_FILES_FILE"]).read_text() == "null\n"
        assert not any(
            value == "must-not-reach-base" for value in env.values()
        )
        assert "--pack-index" not in command
        assert "--pack-count" not in command
        assert "--semantic-replay-job" in command
    assert all(
        step["base_replay"]["tested_tree_sha"] == SHA_BASE
        for record in records
        for step in record["steps"]
    )
    assert all(
        step["base_replay"]["job_present"] is True
        for record in records
        for step in record["steps"]
    )


def test_selected_python_loader_environment_is_derived_from_the_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "python-3.12.13"
    library_dir = prefix / "lib"
    library_dir.mkdir(parents=True)
    (library_dir / "libpython3.12.so.1.0").write_bytes(b"fixture")
    monkeypatch.setattr(PACK.platform, "system", lambda: "Linux")
    monkeypatch.setattr(PACK.sys, "base_prefix", str(prefix))
    monkeypatch.setattr(
        PACK.sysconfig,
        "get_config_var",
        lambda name: {
            "LIBDIR": str(library_dir),
            "LDLIBRARY": "libpython3.12.so.1.0",
        }.get(name),
    )
    monkeypatch.setenv("LD_LIBRARY_PATH", "/candidate/controlled/library/path")

    assert PACK._selected_python_loader_environment() == {
        "LD_LIBRARY_PATH": str(library_dir.resolve())
    }


def test_selected_python_loader_environment_preserves_the_attested_tool_cache_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "hostedtoolcache" / "Python" / "3.12.13" / "x64"
    library_dir = prefix / "lib"
    library_dir.mkdir(parents=True)
    (library_dir / "libpython3.12.so.1.0").write_bytes(b"fixture")
    tool_cache_alias = (
        tmp_path / "runner" / "_work" / "_tool" / "Python" / "3.12.13" / "x64"
    )
    tool_cache_alias.parent.mkdir(parents=True)
    tool_cache_alias.symlink_to(prefix, target_is_directory=True)
    ambient_library_dir = tool_cache_alias / "lib"
    monkeypatch.setattr(PACK.platform, "system", lambda: "Linux")
    monkeypatch.setattr(PACK.sys, "base_prefix", str(prefix))
    monkeypatch.setattr(
        PACK.sysconfig,
        "get_config_var",
        lambda name: {
            "LIBDIR": str(library_dir),
            "LDLIBRARY": "libpython3.12.so",
            "INSTSONAME": "libpython3.12.so.1.0",
        }.get(name),
    )
    monkeypatch.setenv("LD_LIBRARY_PATH", str(ambient_library_dir))

    assert PACK._selected_python_loader_environment() == {
        "LD_LIBRARY_PATH": str(ambient_library_dir)
    }


def test_selected_python_loader_environment_refuses_a_library_outside_the_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "python-3.12.13"
    prefix.mkdir()
    outside = tmp_path / "candidate-library"
    outside.mkdir()
    (outside / "libpython3.12.so.1.0").write_bytes(b"fixture")
    monkeypatch.setattr(PACK.platform, "system", lambda: "Linux")
    monkeypatch.setattr(PACK.sys, "base_prefix", str(prefix))
    monkeypatch.setattr(
        PACK.sysconfig,
        "get_config_var",
        lambda name: {
            "LIBDIR": str(outside),
            "LDLIBRARY": "libpython3.12.so.1.0",
        }.get(name),
    )

    with pytest.raises(PACK.ExecutionProfileError, match="outside selected interpreter"):
        PACK._selected_python_loader_environment()


@pytest.mark.parametrize(
    ("library_dir", "library_name", "message"),
    [
        (None, "libpython3.12.so.1.0", "does not declare LIBDIR"),
        ("inside", None, "does not declare LDLIBRARY"),
        ("inside", "libpython3.12.so.1.0", "shared library is absent"),
    ],
)
def test_selected_python_loader_environment_refuses_missing_library_metadata_or_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    library_dir: str | None,
    library_name: str | None,
    message: str,
) -> None:
    prefix = tmp_path / "python-3.12.13"
    prefix.mkdir()
    declared_dir = prefix / "lib"
    declared_dir.mkdir()
    monkeypatch.setattr(PACK.platform, "system", lambda: "Linux")
    monkeypatch.setattr(PACK.sys, "base_prefix", str(prefix))
    monkeypatch.setattr(
        PACK.sysconfig,
        "get_config_var",
        lambda name: {
            "LIBDIR": str(declared_dir) if library_dir == "inside" else library_dir,
            "LDLIBRARY": library_name,
        }.get(name),
    )

    with pytest.raises(PACK.ExecutionProfileError, match=message):
        PACK._selected_python_loader_environment()


def test_replay_process_never_invents_time_after_the_shared_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []

    class Process:
        pid = 123
        returncode: int | None = None

        def wait(self, *, timeout: float) -> int:
            waits.append(timeout)
            if len(waits) == 1:
                raise subprocess.TimeoutExpired(["base-runner"], timeout)
            self.returncode = -9
            return self.returncode

    ticks = iter([0.0, 2.0, 10.0])
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(PACK.subprocess, "Popen", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(PACK.os, "killpg", lambda *_args: None)
    with pytest.raises(PACK._ProcessSettlementUnknown) as caught:
        PACK._stream_process_with_deadline(
            ["base-runner"], cwd=tmp_path, env={}, deadline=10.0
        )
    assert caught.value.original_outcome == "timed_out"
    assert waits == [8.0, 0.0]


def test_replay_cleanup_does_not_extend_an_exhausted_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = PACK.threading.Event()
    release = PACK.threading.Event()

    def slow_cleanup(*_args: object, **_kwargs: object) -> None:
        started.set()
        release.wait(timeout=5)

    monkeypatch.setattr(PACK.shutil, "rmtree", slow_cleanup)
    before = PACK.time.monotonic()
    PACK._bounded_rmtree(tmp_path / "replay", deadline=before - 1)
    elapsed = PACK.time.monotonic() - before
    assert started.wait(timeout=0.2)
    assert elapsed < 0.2
    release.set()


def test_fragment_is_bound_to_exact_plan_tree_head_base_and_accounts_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = _job(
        "demo",
        [
            {"name": "first", "run": "true"},
            {"name": "second", "run": "true"},
        ],
    )
    plan = _plan([job], changed=["engine/example.py"])
    fragment = tmp_path / "nested" / "fragment.json"
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_current_commit_sha", lambda _root: SHA_TREE)
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_args: None)
    monkeypatch.setattr(
        PACK,
        "_dependency_environment",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(PACK, "_run_exact_base_replays", lambda **_kwargs: None)
    assert (
        PACK.execute_pack(
            [job],
            plan=plan,
            pack_index=0,
            emit_semantic_fragment=fragment,
        )
        == 0
    )
    payload = json.loads(fragment.read_text())
    assert payload["schema"] == PACK.FRAGMENT_SCHEMA
    assert set(payload) == {
        "schema",
        "workflow_run_id",
        "workflow",
        "event",
        "role",
        "tested_tree_sha",
        "subject_head_sha",
        "base_sha",
        "plan_sha256",
        "pack_index",
        "infrastructure",
        "jobs",
    }
    assert payload["plan_sha256"] == plan.plan_sha256
    assert payload["tested_tree_sha"] == SHA_TREE
    assert payload["subject_head_sha"] == SHA_HEAD
    assert payload["base_sha"] == SHA_BASE
    rows = payload["jobs"][0]["steps"]
    assert set(payload["jobs"][0]) == {
        "logical_job_id",
        "job_exec_sha256",
        "infrastructure",
        "steps",
    }
    assert all(
        set(row)
        == {
            "proof_id",
            "step_spec_sha256",
            "outcome",
            "failure_signature",
        }
        for row in rows
    )
    assert [(row["proof_id"], row["outcome"]) for row in rows] == [
        (spec.proof_id, "passed") for spec in PACK.semantic_step_specs(job)
    ]
    assert all("classification" not in row for row in rows)

    # The pack emits raw transport facts only. The shared authority consumes
    # that exact fragment and is solely responsible for the clear verdict.
    evidence = SEMANTIC.reconcile_evidence(plan.to_dict(), [payload])
    assert evidence["status"] == "clear"
    assert SEMANTIC.semantic_gate_verdict(evidence).clear is True
    assert [step["classification"] for step in evidence["jobs"][0]["steps"]] == [
        "passed",
        "passed",
    ]


def test_wrong_checkout_emits_runner_startup_blocked_fragment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = _job("demo", [{"name": "proof", "run": "true"}])
    plan = _plan([job], changed=["engine/example.py"])
    fragment = tmp_path / "blocked.json"
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_current_commit_sha", lambda _root: "f" * 40)
    monkeypatch.setattr(
        PACK,
        "_run_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("wrong checkout must execute nothing")
        ),
    )
    assert (
        PACK.execute_pack(
            [job],
            plan=plan,
            pack_index=0,
            emit_semantic_fragment=fragment,
        )
        == 1
    )
    payload = json.loads(fragment.read_text())
    assert payload["tested_tree_sha"] == SHA_TREE
    assert payload["infrastructure"][0]["outcome"] == "runner_startup_failed"
    assert payload["jobs"][0]["infrastructure"]["outcome"] == (
        "runner_startup_failed"
    )
    assert payload["jobs"][0]["steps"][0]["outcome"] == (
        "infrastructure_blocked"
    )


# Shared browser acquisition and timeout-custody contracts. No hosted package
# acquisition or CI run is performed by these integration boundary tests.
def _browser_setup_step(command="python -m playwright install --with-deps chromium", minutes=10):
    return {"name": "browser setup", "phase": "browser_setup", "timeout-minutes": minutes, "run": command}


def test_browser_setup_is_infrastructure_but_remains_digest_bound(tmp_path):
    setup = _browser_setup_step()
    job = _job("browser", [setup, {"name": "actual assertion", "run": "false"}], timeout=10)
    assert [spec.display_name for spec in PACK.semantic_step_specs(job)] == ["actual assertion"]
    assert len(PACK.load_legacy_jobs(_write_manifest(tmp_path / "manifest.yml", [job]))) == 1
    smaller = _job("browser", [_browser_setup_step(minutes=9), {"name": "actual assertion", "run": "false"}], timeout=10)
    assert PACK.semantic_job_digest(job) != PACK.semantic_job_digest(smaller)


def test_ontology720_manifest_keeps_native_dependencies_and_six_assertions():
    job = next(j for j in PACK.load_legacy_jobs(MANIFEST) if j.job_id == "ontology-explorer")
    setup = PACK._browser_setup_contract(job)[0]
    assert job.definition["timeout-minutes"] == 12
    assert setup["activation_job_id"] == "ontology-explorer"
    assert setup["logical_job_timeout_minutes"] == 12
    assert setup["timeout_minutes"] == 10
    assert setup["command"] == "python -m playwright install --with-deps chromium"
    assert setup["executed_strategy"] == "native_apt_transaction_download4_no_download_install_then_playwright_chromium"
    assert len(setup["native_source_sha256"]) == 7
    specs = PACK.semantic_step_specs(job)
    assert [s.step_index for s in specs] == [4, 5, 6, 7, 8, 9]
    assert [s.step_spec_sha256 for s in specs] == [
        "bca1372cc63fbb96695565266cfcceae9b2c771adc9e0e96b73de94de290d361",
        "75d5f2b5ac5b03ca38c5774b25609325854d01493b4eb9d85e5ee74c0c154b67",
        "31e57516c291f23c6a6d7e6e8d23023b328baa678dc9ad610696759649afdb3b",
        "dd629ae237930d7d9f366fdb9bd339a813ae441f54ac683ebd30cf146eb30bcf",
        "62be4da3641b8ca31e7e6e6ec9a32e4ec08e913a51dda045a73b1f80ed7ead2d",
        "364e79fc9c6b40ff89f6c39b7cbac3b6a3757cebfe0a0dcdc0f6d1e147ed10f9",
    ]
    assert specs[-1].raw_step["run"].startswith("MM_REQUIRE_BROWSER=1 ")


def test_international_canonical_fetch_is_bounded_and_still_fails_closed(monkeypatch, tmp_path):
    """The current canonical helper receives the exact tree and propagates failure."""
    from scripts import run_ci_pack as actual_pack

    jobs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["jobs"]
    command = next(
        s["run"] for s in jobs["international-workspace-browser"]["steps"]
        if s.get("name") == "canonical base for the frozen-file guard (fail closed)"
    )
    assert jobs["international-workspace-browser"]["timeout-minutes"] == 12
    source = command.replace("${{ github.base_ref || 'main' }}", "main")
    assert subprocess.run(["bash", "-n"], input=source, text=True, capture_output=True).returncode == 0
    lines = source.splitlines()
    assert lines[0] == "python - <<'PY'" and lines[-1] == "PY"
    calls = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI_TESTED_TREE_SHA", "a" * 40)

    def refuse(root, *, tested_tree_sha, base_ref):
        calls.append((root, tested_tree_sha, base_ref))
        raise RuntimeError("canonical ancestry unavailable")

    monkeypatch.setattr(actual_pack, "prepare_canonical_main", refuse)
    with pytest.raises(RuntimeError, match="canonical ancestry unavailable"):
        exec(compile("\n".join(lines[1:-1]), "canonical-main-step", "exec"), {})
    assert calls == [(tmp_path, "a" * 40, "main")]


@pytest.mark.parametrize("command", [
    "python -m playwright install --with-deps chromium && python -m pytest tests/test_subject.py",
    "python -m playwright install --with-deps chromium; false",
    "python -m playwright install chromium",
])
def test_browser_setup_refuses_mixed_or_different_commands(tmp_path, command):
    job = _job("browser", [_browser_setup_step(command), {"name": "proof", "run": "true"}])
    with pytest.raises(PACK.ManifestError, match="browser setup"):
        PACK.load_legacy_jobs(_write_manifest(tmp_path / "manifest.yml", [job]))


def test_timed_out_command_preserves_timeout_and_blocks_git_heal(monkeypatch):
    job = _job("unknown-child", [{"name": "original", "run": "true"}, {"name": "later", "run": "true"}])
    heals = []
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_ensure_pack_git_usable", lambda *_a: heals.append(True) or True)
    monkeypatch.setattr(PACK, "_stream_command", lambda *_a, **_k: PACK.CommandObservation(outcome="timed_out", returncode=None, detail="original timeout"))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={}, tested_tree_sha=SHA_TREE)
    assert result.infrastructure["outcome"] == "unknown"
    assert [s["outcome"] for s in result.steps] == ["timed_out", "infrastructure_blocked"]
    assert getattr(result, "timeout_settlement", None) == "unknown"
    assert heals == [], "workspace healing is a write before descendant settlement"


def test_unknown_timeout_stops_environment_reuse_restore_and_base_replay(tmp_path, monkeypatch):
    jobs = [
        _job("alpha", [{"name": "install", "run": "pip install pytest"}, {"name": "original", "run": "true"}]),
        _job("beta", [{"name": "install", "run": "pip install pytest pyyaml"}, {"name": "later", "run": "true"}], ordinal=1),
    ]
    plan = _plan(jobs, changed=[".github/ci/legacy-jobs.yml"], pack_count=1)
    fragment = tmp_path / "fragment.json"
    calls = {"jobs": [], "deps": [], "restores": [], "replays": []}
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_current_commit_sha", lambda *_a: SHA_TREE)
    monkeypatch.setattr(PACK, "_dependency_environment", lambda dep, **_k: calls["deps"].append(dep) or {})
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: calls["restores"].append(True))
    monkeypatch.setattr(PACK, "_run_exact_base_replays", lambda **_k: calls["replays"].append(True))

    def run(job, **kwargs):
        calls["jobs"].append(job.job_id)
        result = PACK.JobExecution(job.job_id, PACK.semantic_job_digest(job), {"outcome": "unknown", "detail": "timeout settlement unknown"}, tuple({**s.plan_dict(), "outcome": "timed_out", "failure_signature": None} for s in PACK.semantic_step_specs(job)), "original timeout")
        object.__setattr__(result, "timeout_settlement", "unknown")
        return result

    monkeypatch.setattr(PACK, "_run_job", run)
    assert PACK.execute_pack(jobs, plan=plan, emit_semantic_fragment=fragment) == 1
    assert calls == {"jobs": ["alpha"], "deps": ["pip install pytest"], "restores": [], "replays": []}
    doc = json.loads(fragment.read_text())
    assert doc["jobs"][0]["steps"][0]["outcome"] == "timed_out"
    assert doc["jobs"][1]["steps"][0]["outcome"] == "infrastructure_blocked"
    assert any(row["outcome"] == "unknown" for row in doc["infrastructure"])

    evidence = SEMANTIC.reconcile_evidence(plan.to_dict(), [doc])
    assert SEMANTIC.semantic_gate_verdict(evidence).clear is False
    assert evidence["status"] != "clear"

def test_unsettled_base_boundary_preserves_original_checkout(tmp_path, monkeypatch):
    source = tmp_path / "source"
    exact, _ = _small_repository(source)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    fault = type("TestSettlementUnknown", (RuntimeError,), {})
    monkeypatch.setattr(PACK, "_ProcessSettlementUnknown", fault, raising=False)
    holder = None
    with pytest.raises(fault):
        with PACK._exact_base_worktree(source, exact, deadline=PACK.time.monotonic()+30) as base:
            holder = base.parent
            raise fault("original base child settlement unknown")
    assert holder is not None and holder.exists(), "cleanup cannot race unknown descendants"


def test_outer_base_timeout_stops_replays_and_preserves_first_outcome(tmp_path, monkeypatch):
    jobs = [_job("first", [{"name": "proof", "run": "false"}]), _job("second", [{"name": "proof", "run": "false"}], ordinal=1)]
    plan = _plan(jobs, changed=[".github/ci/legacy-jobs.yml"])
    base = tmp_path / "base"
    (base / "scripts").mkdir(parents=True)
    (base / "scripts/run_ci_pack.py").write_text("# never executed\n")
    (base / ".github/ci").mkdir(parents=True)
    (base / ".github/ci/legacy-jobs.yml").write_text("jobs: {}\n")
    calls = []

    @contextlib.contextmanager
    def isolated(*args, **kwargs):
        yield base

    monkeypatch.setattr(PACK, "_exact_base_worktree", isolated)
    monkeypatch.setattr(PACK, "_selected_python_loader_environment", lambda: {})
    monkeypatch.setattr(PACK, "_stream_process_with_deadline", lambda *args, **kwargs: calls.append(args) or (None, True))
    records = [{"logical_job_id": j.job_id, "job_exec_sha256": PACK.semantic_job_digest(j), "infrastructure": {"outcome": "passed"}, "steps": [{**s.plan_dict(), "outcome": "failed", "failure_signature": None} for s in PACK.semantic_step_specs(j)]} for j in jobs]
    PACK._run_exact_base_replays(root=tmp_path, plan=plan, records=records, budget_seconds=30)
    assert len(calls) == 1
    assert records[0]["steps"][0]["base_replay"]["outcome"] == "timed_out"
    assert records[1]["steps"][0]["base_replay"]["outcome"] == "unavailable"


def test_browser_setup_consumes_original_total_deadline(monkeypatch):
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", lambda: ())
    job = _job("browser", [_browser_setup_step(), {"name": "proof", "run": "true"}], timeout=10)
    ticks = iter([0.0, 0.0, 400.0])
    calls = []
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **kwargs: calls.append((command, kwargs["timeout_seconds"])) or PACK.CommandObservation(outcome="passed", returncode=0))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == [("python -m playwright install --with-deps chromium", 600.0), ("true", 200.0)]
    assert [s["outcome"] for s in result.steps] == ["passed"]


def test_browser_setup_failure_is_blocking_infrastructure_not_product_pass(monkeypatch):
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", lambda: ())
    job = _job("browser", [_browser_setup_step(), {"name": "proof", "run": "true"}], timeout=10)
    calls = []
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **kwargs: calls.append(command) or PACK.CommandObservation(outcome="failed", returncode=17, detail="original acquisition failure"))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == ["python -m playwright install --with-deps chromium"]
    assert result.infrastructure["outcome"] == "dependency_failed"
    assert "17" in result.infrastructure["detail"] and "failed" in result.infrastructure["detail"]
    assert [s["outcome"] for s in result.steps] == ["infrastructure_blocked"]


def test_old_base_runner_timeout_cannot_hide_unsettled_children(tmp_path, monkeypatch):
    jobs = [_job("first", [{"name": "proof", "run": "false"}]), _job("second", [{"name": "proof", "run": "false"}], ordinal=1)]
    plan = _plan(jobs, changed=[".github/ci/legacy-jobs.yml"])
    base = tmp_path / "base"
    (base / "scripts").mkdir(parents=True)
    (base / "scripts/run_ci_pack.py").write_text("# old runner\n")
    (base / ".github/ci").mkdir(parents=True)
    (base / ".github/ci/legacy-jobs.yml").write_text("jobs: {}\n")
    observed = {"calls": 0, "retained": False, "cleaned": False}

    @contextlib.contextmanager
    def isolated(*args, **kwargs):
        try:
            yield base
        except PACK._ProcessSettlementUnknown:
            observed["retained"] = True
            raise
        else:
            observed["cleaned"] = True

    def stream(command, **kwargs):
        observed["calls"] += 1
        output = Path(command[command.index("--emit-semantic-fragment") + 1])
        jobid = command[command.index("--semantic-replay-job") + 1]
        job = next(j for j in jobs if j.job_id == jobid)
        doc = {"schema": PACK.FRAGMENT_SCHEMA, "tested_tree_sha": SHA_BASE, "subject_head_sha": SHA_BASE, "base_sha": SHA_BASE, "role": "main", "infrastructure": [], "jobs": [{"logical_job_id": jobid, "job_exec_sha256": PACK.semantic_job_digest(job), "infrastructure": {"outcome": "passed"}, "steps": [{**s.plan_dict(), "outcome": "timed_out", "failure_signature": None} for s in PACK.semantic_step_specs(job)]}]}
        output.write_text(json.dumps(doc))
        return 1, False

    monkeypatch.setattr(PACK, "_exact_base_worktree", isolated)
    monkeypatch.setattr(PACK, "_selected_python_loader_environment", lambda: {})
    monkeypatch.setattr(PACK, "_stream_process_with_deadline", stream)
    records = [{"logical_job_id": j.job_id, "job_exec_sha256": PACK.semantic_job_digest(j), "infrastructure": {"outcome": "passed"}, "steps": [{**s.plan_dict(), "outcome": "failed", "failure_signature": None} for s in PACK.semantic_step_specs(j)]} for j in jobs]
    PACK._run_exact_base_replays(root=tmp_path, plan=plan, records=records, budget_seconds=30)
    assert observed == {"calls": 1, "retained": True, "cleaned": False}
    assert (base.parent / "runner-temp/base-replay.json").is_file()
    assert records[0]["steps"][0]["outcome"] == "failed"
    assert all(r["steps"][0]["base_replay"]["outcome"] == "unavailable" for r in records)


def test_normal_exact_base_boundary_still_cleans_up(tmp_path, monkeypatch):
    source = tmp_path / "source"
    exact, _ = _small_repository(source)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    with PACK._exact_base_worktree(source, exact, deadline=PACK.time.monotonic()+30) as base:
        holder = base.parent
        assert holder.is_dir()
    assert not holder.exists()


def test_command_observation_loss_blocks_later_steps(monkeypatch):
    job = _job("lost", [{"name": "original", "run": "true"}, {"name": "later", "run": "true"}])
    calls = []
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)

    def lost(command, **kwargs):
        calls.append(command)
        raise RuntimeError("original command observation lost")

    monkeypatch.setattr(PACK, "_stream_command", lost)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.timeout_settlement == "unknown"
    assert result.infrastructure["outcome"] == "unknown"
    assert [s["outcome"] for s in result.steps] == ["infrastructure_blocked", "infrastructure_blocked"]
    assert calls == ["true"]


def test_exhausted_prelaunch_clock_does_not_invent_a_child(monkeypatch):
    job = _job("not-started", [{"name": "proof", "run": "true"}])
    ticks = iter([0.0, 60.0])
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_stream_command", lambda *_a, **_k: pytest.fail("no command may start"))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.timeout_settlement is None
    assert result.steps[0]["outcome"] == "timed_out"
    assert result.infrastructure["outcome"] == "passed"


@pytest.mark.parametrize("minutes", [0, 11, True, "10"])
def test_browser_setup_refuses_unbounded_or_invalid_step_limit(tmp_path, minutes):
    job = _job("browser", [_browser_setup_step(minutes=minutes), {"run": "true"}], timeout=10)
    with pytest.raises(PACK.ManifestError, match="browser setup"):
        PACK.load_legacy_jobs(_write_manifest(tmp_path / "manifest.yml", [job]))


def test_browser_setup_refuses_no_original_deadline_or_proof_identity(tmp_path):
    no_deadline = _job("browser", [_browser_setup_step(), {"run": "true"}], timeout=None)
    with pytest.raises(PACK.ManifestError, match="original logical-job deadline"):
        PACK.load_legacy_jobs(_write_manifest(tmp_path / "no-deadline.yml", [no_deadline]))
    setup = {**_browser_setup_step(), "proof_id": "cannot-be-both"}
    job = _job("browser", [setup, {"run": "true"}], timeout=10)
    with pytest.raises(PACK.ManifestError, match="browser setup"):
        PACK.load_legacy_jobs(_write_manifest(tmp_path / "with-proof.yml", [job]))


# Fabric ci-timeout-settlement-01a15d64-tests: retained artifact adfd7216.
# Parent integrates these two owned-process fault tests in the existing suite.
"""Fault tests: timeout settlement reporting for ``scripts.run_ci_pack._stream_command``.

Source contract under test (POSIX)
----------------------------------
``_stream_command(command, env=..., timeout_seconds=...)`` launches
``Popen(['bash', '-eo', 'pipefail', '-c', command], env=dict(env),
stdout=PIPE, stderr=STDOUT, bufsize=0, start_new_session=True)``, pumps stdout
from a daemon reader thread and, on ``TimeoutExpired``, ``SIGKILL``s the launch
process group via ``os.killpg(process.pid, SIGKILL)``.  It then reports
``CommandObservation(outcome='timed_out', ...)`` without being able to prove
that every descendant of the launch is gone.  The required contract is:

* the observation keeps ``outcome == 'timed_out'``;
* the observation reports ``timeout_settlement == 'unknown'`` -- it must never
  claim that the whole descendant tree was settled.

Both tests drive the *real* ``_stream_command`` with one explicitly owned
synthetic descendant:

1. ``test_timeout_descendant_inherited_group_kill_reports_unknown_settlement``
   -- the descendant inherits the launch process group.
2. ``test_timeout_descendant_separate_session_survivor_reports_unknown_settlement``
   -- the descendant calls ``os.setsid()`` and redirects its stdout/stderr to
   ``DEVNULL``, so an escaped descendant cannot hold the launch pipe open and
   stall the harness.

Neither test asserts that the ordinary process-group kill settled the
descendant tree; a surviving (or zombied) descendant is exactly what
``timeout_settlement == 'unknown'`` is hiding.  Cleanup in ``finally``
terminates only processes this test itself launched, identified by PID files
the synthetic launcher writes inside the test's own temporary directory.

Platform caveats
----------------
* POSIX only: skipped when ``os.killpg`` is unavailable.
* Liveness prefers ``/proc/<pid>/stat`` so a zombie (state ``Z``) counts as
  terminated.  Where ``/proc`` is missing the ``kill(pid, 0)`` fallback is used
  only to steer best-effort cleanup, never as an asserted proof of death,
  because zombies keep ``kill(pid, 0)`` succeeding.
"""


import importlib
import os
import pathlib
import signal
import subprocess
import sys
import time
import uuid

import pytest

#: Job timeout handed to ``_stream_command``; the synthetic step outlives it.
_TIMEOUT_DESCENDANT_STEP_TIMEOUT_SECONDS = 1.0

#: Bounds for the launch readiness handshake and for best-effort cleanup.
_TIMEOUT_DESCENDANT_HANDSHAKE_TIMEOUT_SECONDS = 2.0
_TIMEOUT_DESCENDANT_CLEANUP_TIMEOUT_SECONDS = 1.0

#: How long the synthetic launcher and its descendant would live un-killed.
_TIMEOUT_DESCENDANT_LIFETIME_SECONDS = 60

_TIMEOUT_DESCENDANT_CHILD_PID = "child.pid"
_TIMEOUT_DESCENDANT_SHELL_PID = "shell_child.pid"
_TIMEOUT_DESCENDANT_CHILD_READY = "child.ready"

_TIMEOUT_DESCENDANT_CHILD_SOURCE = """\
import os
import pathlib
import sys
import time

mode, workdir, lifetime = sys.argv[1], sys.argv[2], float(sys.argv[3])
if mode == "own-session":
    # Escape the launch group the way a daemonised grandchild would.
    os.setsid()
pid = os.getpid()
workdir = pathlib.Path(workdir)
workdir.joinpath("child.pid").write_text(str(pid))
workdir.joinpath("child.ready").write_text(str(pid))
time.sleep(lifetime)
"""


def _timeout_descendant_import_target():
    """Import ``scripts.run_ci_pack``, locating the repo root if needed."""
    try:
        return importlib.import_module("scripts.run_ci_pack")
    except ModuleNotFoundError:
        here = pathlib.Path(__file__).resolve().parent
        for candidate in (here, *here.parents):
            if (candidate / "scripts" / "run_ci_pack.py").is_file():
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                return importlib.import_module("scripts.run_ci_pack")
        raise


def _timeout_descendant_proc_state(pid):
    """Return the process state char, or ``None`` when ``pid`` is gone.

    Uses ``/proc`` when available so a zombie is reported as terminated; the
    ``kill(pid, 0)`` fallback is ambiguous for zombies, so callers treat it as
    "maybe alive" and only use it to steer cleanup.
    """
    try:
        stat = pathlib.Path("/proc/%d/stat" % pid).read_text()
    except (OSError, ValueError):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            return "unknown"
        except OSError:
            return None
        return "R"
    tail = stat.rpartition(")")[2].split()
    return tail[0] if tail else "unknown"


def _timeout_descendant_is_gone(pid):
    """True when the process exited; a zombie counts as gone (never death-proof)."""
    state = _timeout_descendant_proc_state(pid)
    if state is None:
        return True
    return state in ("Z", "X", "x")


def _timeout_descendant_write_child_script(directory):
    path = directory / "timeout_descendant_child.py"
    path.write_text(_TIMEOUT_DESCENDANT_CHILD_SOURCE)
    return path


def _timeout_descendant_build_command(child_script, workdir, ready_path, token, mode):
    """Bash step: start one descendant, handshake, then outlive the job timeout."""
    redirect = "< /dev/null > /dev/null 2>&1" if mode == "own-session" else ""
    child_ready = workdir / _TIMEOUT_DESCENDANT_CHILD_READY
    shell_pid = workdir / _TIMEOUT_DESCENDANT_SHELL_PID
    lines = [
        "child_pid=0",
        "python3 '{script}' '{mode}' '{workdir}' {lifetime} {redirect} &".format(
            script=child_script,
            mode=mode,
            workdir=workdir,
            lifetime=_TIMEOUT_DESCENDANT_LIFETIME_SECONDS,
            redirect=redirect,
        ),
        "child_pid=$!",
        "spin=0",
        "while [ \"$spin\" -lt 300 ] && [ ! -f '{ready}' ]; do".format(ready=child_ready),
        "  sleep 0.01",
        "  spin=$((spin + 1))",
        "done",
        "echo \"$child_pid\" > '{shell_pid}'".format(shell_pid=shell_pid),
        "echo '{token}' > '{ready}'".format(token=token, ready=ready_path),
        "sleep {lifetime}".format(lifetime=_TIMEOUT_DESCENDANT_LIFETIME_SECONDS),
    ]
    return "\n".join(lines)


def _timeout_descendant_intercept_popen(monkeypatch, token, ready_path, recorded):
    """Patch ``Popen`` to keep the exact launch handle and gate on the handshake.

    The wrapper lets the real ``Popen`` run, records the handle for our token
    and blocks until the synthetic launcher announces readiness, so by the time
    ``_stream_command`` starts waiting there is no startup race left.
    """
    real_popen = subprocess.Popen

    def wrapper(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        argv = args[0] if args else ()
        joined = " ".join(str(part) for part in argv)
        if token in joined:
            recorded.append(process)
            deadline = time.monotonic() + _TIMEOUT_DESCENDANT_HANDSHAKE_TIMEOUT_SECONDS
            while not ready_path.exists():
                if process.poll() is not None:
                    raise AssertionError(
                        "synthetic launcher exited before the readiness handshake"
                    )
                if time.monotonic() >= deadline:
                    raise AssertionError(
                        "readiness handshake with the synthetic launcher timed out"
                    )
                time.sleep(0.02)
        return process

    monkeypatch.setattr(subprocess, "Popen", wrapper)
    module = _timeout_descendant_import_target()
    if getattr(module, "Popen", None) is real_popen:
        monkeypatch.setattr(module, "Popen", wrapper)
    return module


def _timeout_descendant_terminate_owned(workdir, recorded_handles):
    """Kill exactly the processes this test launched; never touch anything else."""
    tracked = set()
    for name in (_TIMEOUT_DESCENDANT_CHILD_PID, _TIMEOUT_DESCENDANT_SHELL_PID):
        try:
            pid = int((workdir / name).read_text().strip())
        except (OSError, ValueError):
            continue
        if pid > 0:
            tracked.add(pid)
    for process in recorded_handles:
        try:
            still_running = process.poll() is None
        except OSError:
            still_running = True
        if still_running:
            tracked.add(process.pid)

    forced = []
    already_gone = []
    for pid in sorted(tracked):
        if _timeout_descendant_is_gone(pid):
            already_gone.append(pid)
            continue
        # Signal a process group only when the recorded descendant itself is
        # the leader of a group that is not ours: that can only be the
        # separate session this test created.
        try:
            pgid = os.getpgid(pid)
        except OSError:
            pgid = None
        if pgid == pid and pgid != os.getpgrp():
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError:
                pass
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        forced.append(pid)

    deadline = time.monotonic() + _TIMEOUT_DESCENDANT_CLEANUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if all(_timeout_descendant_is_gone(pid) for pid in tracked):
            break
        time.sleep(0.05)
    return {
        "tracked": sorted(tracked),
        "forced": forced,
        "already_gone": already_gone,
    }


def _timeout_descendant_run_timed_step(monkeypatch, tmp_path, mode):
    """Run the real ``_stream_command`` against one synthetic descendant."""
    handshake_dir = tmp_path / "timeout_descendant_handshake"
    handshake_dir.mkdir()
    ready_path = handshake_dir / "launch.ready"
    token = "timeout-descendant-" + uuid.uuid4().hex
    child_script = _timeout_descendant_write_child_script(tmp_path)
    command = _timeout_descendant_build_command(
        child_script, handshake_dir, ready_path, token, mode
    )
    recorded = []
    module = _timeout_descendant_intercept_popen(monkeypatch, token, ready_path, recorded)
    env = dict(os.environ)
    env["TIMEOUT_DESCENDANT_TOKEN"] = token
    try:
        observation = module._stream_command(
            command, env=env, timeout_seconds=_TIMEOUT_DESCENDANT_STEP_TIMEOUT_SECONDS
        )
    finally:
        cleanup = _timeout_descendant_terminate_owned(handshake_dir, recorded)
    return observation, cleanup


def _timeout_descendant_field(observation, name):
    if isinstance(observation, dict):
        return observation.get(name)
    return getattr(observation, name, None)


def test_timeout_descendant_inherited_group_kill_reports_unknown_settlement(
    monkeypatch, tmp_path
):
    """A launch-group descendant keeps ``timeout_settlement`` unknown.

    The descendant inherits the launch process group, so an ordinary
    ``os.killpg`` on the launch group is expected to reach it -- but the timed
    out observation must not claim that as proof: it still reports
    ``timeout_settlement == 'unknown'`` while preserving ``timed_out``.
    """
    if not hasattr(os, "killpg"):
        pytest.skip("POSIX process groups (os.killpg) are unavailable")
    observation, cleanup = _timeout_descendant_run_timed_step(
        monkeypatch, tmp_path, mode="inherited"
    )
    assert cleanup["tracked"], (
        "the synthetic descendant never registered; the launcher or handshake broke"
    )
    assert _timeout_descendant_field(observation, "outcome") == "timed_out", (
        "the job timeout must preserve outcome='timed_out'; got %r" % (observation,)
    )
    assert _timeout_descendant_field(observation, "timeout_settlement") == "unknown", (
        "a timed_out observation must report timeout_settlement='unknown': the "
        "ordinary launch-group kill does not prove every descendant was settled; "
        "got %r" % (observation,)
    )
    # Deliberately no assertion that the group kill settled the tree.  Any
    # descendant this test owned has already been re-terminated by
    # _timeout_descendant_terminate_owned in the run's finally block.


def test_timeout_descendant_separate_session_survivor_reports_unknown_settlement(
    monkeypatch, tmp_path
):
    """A ``setsid`` descendant is outside the launch group; settlement stays unknown.

    The descendant starts its own session and redirects stdout/stderr to
    ``DEVNULL`` (so escaping cannot hang the launch pipe).  The launch-group
    ``killpg`` cannot reach it, and the observation must still preserve
    ``outcome == 'timed_out'`` while reporting ``timeout_settlement ==
    'unknown'`` -- never claiming the descendant tree was settled.
    """
    if not hasattr(os, "killpg"):
        pytest.skip("POSIX process groups (os.killpg) are unavailable")
    observation, cleanup = _timeout_descendant_run_timed_step(
        monkeypatch, tmp_path, mode="own-session"
    )
    assert cleanup["tracked"], (
        "the synthetic descendant never registered; the launcher or handshake broke"
    )
    assert _timeout_descendant_field(observation, "outcome") == "timed_out", (
        "the job timeout must preserve outcome='timed_out'; got %r" % (observation,)
    )
    assert _timeout_descendant_field(observation, "timeout_settlement") == "unknown", (
        "a timed_out observation must report timeout_settlement='unknown': a "
        "separate-session descendant escapes the launch-group kill, so the "
        "descendant tree is provably not settled; got %r" % (observation,)
    )
    # Cleanup already re-terminated the escaped session this test owned via
    # _timeout_descendant_terminate_owned in the run's finally block.


@pytest.mark.parametrize("response_loss", [False, True])
def test_uncertain_dependency_retains_environment_without_transport_retry(tmp_path, monkeypatch, response_loss):
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    calls = []
    environment = tmp_path / "ci-pack-job-env"

    def create(command, **kwargs):
        environment.mkdir()
        (environment / "original-partial").write_text("retain")
        calls.append("create")

    def stream(*args, **kwargs):
        calls.append("install")
        if response_loss:
            raise RuntimeError("original observation unavailable")
        return PACK.CommandObservation(
            outcome="failed", returncode=17, timeout_settlement="unknown",
            retryable_dependency_transport=True,
        )

    monkeypatch.setattr(PACK.subprocess, "run", create)
    monkeypatch.setattr(PACK, "_stream_command", stream)
    with pytest.raises(PACK._ProcessSettlementUnknown) as caught:
        PACK._dependency_environment("python -m pip install plotly")
    assert caught.value.original_outcome == ("unavailable" if response_loss else "failed")
    assert calls == ["create", "install"]
    assert (environment / "original-partial").read_text() == "retain"


def _review_replay_boundary(tmp_path, monkeypatch):
    from dataclasses import replace

    source = tmp_path / "source"
    exact, _ = _small_repository(source)
    jobs = [_job("first", [{"name": "proof", "run": "false"}]),
            _job("second", [{"name": "proof", "run": "false"}], ordinal=1)]
    plan = replace(_plan(jobs, changed=[".github/ci/legacy-jobs.yml"]), base_sha=exact)
    holders = []
    real_boundary = PACK._exact_base_worktree

    @contextlib.contextmanager
    def boundary(*args, **kwargs):
        with real_boundary(*args, **kwargs) as base:
            holders.append(base.parent)
            yield base

    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setattr(PACK, "_exact_base_worktree", boundary)
    monkeypatch.setattr(PACK, "_selected_python_loader_environment", lambda: {})
    records = [{"logical_job_id": j.job_id, "job_exec_sha256": PACK.semantic_job_digest(j),
                "infrastructure": {"outcome": "passed"},
                "steps": [{**s.plan_dict(), "outcome": "failed", "failure_signature": None}
                          for s in PACK.semantic_step_specs(j)]} for j in jobs]
    return source, plan, jobs, records, holders


@pytest.mark.parametrize("fault", [OSError, RuntimeError])
def test_review_timeout_second_wait_error_preserves_checkout_and_stops_replay(tmp_path, monkeypatch, fault):
    source, plan, jobs, records, holders = _review_replay_boundary(tmp_path, monkeypatch)
    real_stream = PACK._stream_process_with_deadline
    calls = []
    waits = []

    class Process:
        pid = 123
        returncode = None

        def wait(self, **kwargs):
            waits.append(kwargs)
            if len(waits) == 1:
                raise subprocess.TimeoutExpired(["base-runner"], 1)
            raise fault("original timeout cleanup observation lost")

    def stream(*args, **kwargs):
        calls.append(True)
        with monkeypatch.context() as patch:
            patch.setattr(PACK.subprocess, "Popen", lambda *_a, **_k: Process())
            patch.setattr(PACK.os, "killpg", lambda *_a: None)
            return real_stream(*args, **kwargs)

    monkeypatch.setattr(PACK, "_stream_process_with_deadline", stream)
    PACK._run_exact_base_replays(root=source, plan=plan, records=records, budget_seconds=30)
    assert len(calls) == 1 and len(waits) == 2
    assert len(holders) == 1 and holders[0].is_dir()
    assert records[0]["steps"][0]["base_replay"]["outcome"] == "timed_out"
    assert records[1]["steps"][0]["base_replay"]["outcome"] == "unavailable"


@pytest.mark.parametrize("missing", ["null_row", "job_exec_sha256", "infrastructure", "steps"])
def test_review_malformed_base_job_retains_result_and_stops_replay(tmp_path, monkeypatch, missing):
    source, plan, jobs, records, holders = _review_replay_boundary(tmp_path, monkeypatch)
    calls = []
    emitted = []

    def stream(command, **kwargs):
        calls.append(True)
        output = Path(command[command.index("--emit-semantic-fragment") + 1])
        row = {"logical_job_id": "first", "job_exec_sha256": PACK.semantic_job_digest(jobs[0]),
               "infrastructure": {"outcome": "passed"}, "steps": []}
        if missing == "null_row":
            row = None
        else:
            del row[missing]
        doc = {"schema": PACK.FRAGMENT_SCHEMA, "tested_tree_sha": plan.base_sha,
               "subject_head_sha": plan.base_sha, "base_sha": plan.base_sha,
               "role": "main", "infrastructure": [], "jobs": [row]}
        raw = json.dumps(doc)
        output.write_text(raw)
        emitted.append((output, raw))
        return 0, False

    monkeypatch.setattr(PACK, "_stream_process_with_deadline", stream)
    PACK._run_exact_base_replays(root=source, plan=plan, records=records, budget_seconds=30)
    assert calls == [True]
    assert len(holders) == 1 and holders[0].is_dir()
    assert emitted[0][0].read_text() == emitted[0][1]
    assert all(r["steps"][0]["base_replay"]["outcome"] == "unavailable" for r in records)
    assert all(r["steps"][0]["outcome"] == "failed" for r in records)


@pytest.mark.parametrize("fault", ["read", "display", "collector"])
def test_review_pump_error_after_root_wait_blocks_all_dependent_effects(tmp_path, monkeypatch, fault):
    import builtins

    jobs = [_job("alpha", [{"name": "install", "run": "pip install pytest"}, {"name": "original", "run": "true"}]),
            _job("beta", [{"name": "install", "run": "pip install pytest pyyaml"}, {"name": "later", "run": "true"}], ordinal=1)]
    plan = _plan(jobs, changed=[".github/ci/legacy-jobs.yml"], pack_count=1)
    calls = {"wait": [], "deps": [], "restore": [], "heal": [], "replay": []}
    chunks = iter([b"original output\n", b""])

    def read(*args):
        if fault == "read":
            raise OSError("original read failed")
        return next(chunks)

    class Process:
        pid = 123
        returncode = 0
        stdout = SimpleNamespace(read=read, close=lambda: None)

        def wait(self, **kwargs):
            calls["wait"].append(True)
            return self.returncode

    if fault == "display":
        def display(*args, **kwargs):
            if kwargs.get("end") == "":
                raise OSError("original display failed")
            return builtins.print(*args, **kwargs)
        monkeypatch.setattr(PACK, "print", display, raising=False)
    elif fault == "collector":
        def collect(*args, **kwargs):
            raise RuntimeError("original collector failed")
        monkeypatch.setattr(PACK.FailureAtomCollector, "feed", collect)
    monkeypatch.setattr(PACK.subprocess, "Popen", lambda *_a, **_k: Process())
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_current_commit_sha", lambda *_a: SHA_TREE)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_dependency_environment", lambda dep, **_k: calls["deps"].append(dep) or {})
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: calls["restore"].append(True))
    monkeypatch.setattr(PACK, "_ensure_pack_git_usable", lambda *_a: calls["heal"].append(True) or True)
    monkeypatch.setattr(PACK, "_run_exact_base_replays", lambda **_k: calls["replay"].append(True))
    fragment = tmp_path / "fragment.json"
    assert PACK.execute_pack(jobs, plan=plan, emit_semantic_fragment=fragment) == 1
    assert calls == {"wait": [True], "deps": ["pip install pytest"], "restore": [True], "heal": [], "replay": []}
    doc = json.loads(fragment.read_text())
    assert doc["jobs"][0]["steps"][0]["outcome"] == "failed"
    assert "original " + fault + " failed" in doc["jobs"][0]["steps"][0]["detail"]
    assert doc["jobs"][0]["infrastructure"]["outcome"] == "unknown"
    assert doc["jobs"][1]["steps"][0]["outcome"] == "infrastructure_blocked"
    evidence = SEMANTIC.reconcile_evidence(plan.to_dict(), [doc])
    assert SEMANTIC.semantic_gate_verdict(evidence).clear is False


def _capture_job_environment(monkeypatch):
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", lambda: ("capture apt", "capture playwright"), raising=False)
    from scripts import ci_browser_native_setup as native
    def mocked_native_setup(**kwargs):
        observation = PACK._stream_command(
            "python -m playwright install --with-deps chromium",
            env=kwargs["command_env"],
            timeout_seconds=max(0.0, kwargs["deadline"] - PACK.time.monotonic()),
        )
        return dict(outcome=observation.outcome, returncode=observation.returncode,
                    failure_signature=observation.failure_signature,
                    timeout_settlement=observation.timeout_settlement, detail=observation.detail)
    monkeypatch.setattr(native, "run_native_setup", mocked_native_setup)


def test_capture_deducts_from_same_original_deadline_and_keeps_installer(monkeypatch):
    _capture_job_environment(monkeypatch)
    job = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition": "native_parallel"}, {"name": "assertion", "run": "true"}], timeout=10)
    ticks = iter([0.0, 0.0, 40.0, 100.0, 100.0, 500.0])
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    calls = []

    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        return PACK.CommandObservation(outcome="passed", returncode=0)

    monkeypatch.setattr(PACK, "_stream_command", stream)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.failure is None
    assert calls == [("capture apt", 600), ("capture playwright", 560),
                     ("python -m playwright install --with-deps chromium", 500), ("true", 100)]
    assert [s["outcome"] for s in result.steps] == ["passed"]


@pytest.mark.parametrize("outcome", ["timed_out", "failed"])
def test_capture_uncertainty_blocks_original_installer_and_semantics(monkeypatch, outcome):
    _capture_job_environment(monkeypatch)
    job = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition": "native_parallel"}, {"name": "assertion", "run": "true"}], timeout=10)
    calls = []

    def stream(command, **kwargs):
        calls.append(command)
        return PACK.CommandObservation(outcome=outcome, returncode=None, timeout_settlement="unknown", detail="original capture uncertainty")

    monkeypatch.setattr(PACK, "_stream_command", stream)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == ["capture apt"]
    assert result.timeout_settlement == "unknown"
    assert result.infrastructure["outcome"] == "unknown"
    assert result.steps[0]["outcome"] == "infrastructure_blocked"
    assert outcome in result.infrastructure["detail"]


def test_settled_capture_failure_does_not_replace_required_installation(monkeypatch):
    _capture_job_environment(monkeypatch)
    job = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition": "native_parallel"}, {"name": "assertion", "run": "true"}], timeout=10)
    calls = []

    def stream(command, **kwargs):
        calls.append(command)
        return PACK.CommandObservation(outcome="failed" if len(calls) == 1 else "passed", returncode=1 if len(calls) == 1 else 0)

    monkeypatch.setattr(PACK, "_stream_command", stream)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == ["capture apt", "capture playwright", "python -m playwright install --with-deps chromium", "true"]
    assert result.failure is None
    assert result.steps[0]["outcome"] == "passed"


def test_capture_cannot_launch_installer_after_total_budget_exhausted(monkeypatch):
    _capture_job_environment(monkeypatch)
    job = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition": "native_parallel"}, {"name": "assertion", "run": "true"}], timeout=10)
    ticks = iter([0.0, 0.0, 600.0])
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    calls = []
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **_k: calls.append(command) or PACK.CommandObservation(outcome="passed", returncode=0))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == ["capture apt"]
    assert result.failure is not None and result.timeout_settlement is None
    assert result.steps[0]["outcome"] == "infrastructure_blocked"


def test_capture_commands_are_bound_only_to_declared_setup_jobs(monkeypatch):
    _capture_job_environment(monkeypatch)
    setup = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition": "native_parallel"}, {"run": "true"}], timeout=10)
    ordinary = _job("ordinary", [{"run": "true"}], timeout=10)
    before = PACK.semantic_job_digest(setup), PACK.semantic_job_digest(ordinary)
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", lambda: ("different capture",))
    after = PACK.semantic_job_digest(setup), PACK.semantic_job_digest(ordinary)
    assert before[0] != after[0]
    assert before[1] == after[1]


def test_capture_helper_source_is_part_of_setup_digest(monkeypatch):
    _capture_job_environment(monkeypatch)
    setup = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition": "native_parallel"}, {"run": "true"}], timeout=10)
    before = PACK.semantic_job_digest(setup)
    original = Path.read_bytes

    def changed_helper(path):
        content = original(path)
        return content + b"\n# changed capture input source\n" if path.name == "ci_browser_dependency_inputs.py" else content

    monkeypatch.setattr(Path, "read_bytes", changed_helper)
    assert PACK.semantic_job_digest(setup) != before


def test_capture_shares_the_finite_setup_bound_as_well_as_the_job_deadline(monkeypatch):
    _capture_job_environment(monkeypatch)
    job = _job("ontology-explorer", [{**_browser_setup_step(minutes=9), "acquisition": "native_parallel"}, {"name": "assertion", "run": "true"}], timeout=10)
    ticks = iter([0.0, 0.0, 300.0, 540.0])
    monkeypatch.setattr(PACK.time, "monotonic", lambda: next(ticks))
    calls = []
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **kwargs: calls.append((command, kwargs["timeout_seconds"])) or PACK.CommandObservation(outcome="passed", returncode=0))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == [("capture apt", 540), ("capture playwright", 240)]
    assert result.failure is not None
    assert result.steps[0]["outcome"] == "infrastructure_blocked"


# Explicit native acquisition is closed opt-in; default setup path is retained.
def test_native_acquisition_strategy_and_every_helper_are_digest_bound(monkeypatch):
    original = _job("ontology-explorer", [_browser_setup_step(), {"name":"assertion","run":"true"}], timeout=10)
    native = _job("ontology-explorer", [{**_browser_setup_step(), "acquisition":"native_parallel"}, {"name":"assertion","run":"true"}], timeout=10)
    assert PACK.semantic_job_digest(original) != PACK.semantic_job_digest(native)
    before = PACK.semantic_job_digest(native)
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda p:read(p)+b"#changed" if p.name=="ci_apt_native_stage.py" else read(p))
    assert PACK.semantic_job_digest(native) != before
    spec=PACK._browser_setup_contract(native)[0]
    assert len(spec["native_source_sha256"])==7
    assert spec["activation_job_id"] == "ontology-explorer"
    assert spec["budget"]=="within_original_logical_job_deadline"


def test_native_acquisition_unknown_never_falls_back_or_runs_assertions(monkeypatch):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job=_job("ontology-explorer", [{**_browser_setup_step(),"acquisition":"native_parallel"}, {"name":"assertion","run":"true"}],timeout=10)
    calls=[];ticks=iter([0.,0.,20.,40.])
    monkeypatch.setattr(PACK.time,"monotonic",lambda:next(ticks))
    monkeypatch.setattr(PACK,"_stream_command",lambda c,**k:calls.append(c) or PACK.CommandObservation(outcome="passed",returncode=0))
    def setup(**kwargs):
        assert kwargs["deadline"]==600 and len(kwargs["expected_sources"])==7
        calls.append("native once")
        return dict(outcome="timed_out",returncode=None,failure_signature=None,timeout_settlement="unknown",detail="original native acquisition timeout")
    monkeypatch.setattr(native,"run_native_setup",setup)
    result=PACK._run_job(job,base_ref="main",head_ref="",command_env={})
    assert calls==["capture apt","capture playwright","native once"]
    assert result.timeout_settlement=="unknown" and result.steps[0]["outcome"]=="infrastructure_blocked"
    assert result.infrastructure["outcome"]=="unknown"


def test_native_acquisition_normal_success_leaves_only_remaining_total_for_assertions(monkeypatch):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job=_job("ontology-explorer", [{**_browser_setup_step(),"acquisition":"native_parallel"}, {"name":"assertion","run":"true"}],timeout=10)
    calls=[];ticks=iter([0.,0.,20.,40.,500.])
    monkeypatch.setattr(PACK.time,"monotonic",lambda:next(ticks))
    monkeypatch.setattr(PACK,"_stream_command",lambda c,**k:calls.append((c,k["timeout_seconds"])) or PACK.CommandObservation(outcome="passed",returncode=0))
    def setup(**kwargs):
        calls.append(("native once",kwargs["deadline"]))
        return dict(outcome="passed",returncode=0,failure_signature=None,timeout_settlement=None,detail="native and browser acquisition passed")
    monkeypatch.setattr(native,"run_native_setup",setup)
    result=PACK._run_job(job,base_ref="main",head_ref="",command_env={})
    assert result.failure is None
    assert calls==[("capture apt",600),("capture playwright",580),("native once",600),("true",100)]


@pytest.mark.parametrize("strategy", ["foreign",None,True,{},[]])
def test_native_acquisition_has_no_unknown_strategy_fallback(strategy):
    with pytest.raises(PACK.ManifestError):PACK._browser_setup_spec({**_browser_setup_step(),"acquisition":strategy})


def test_native_acquisition_manifest_is_explicit_and_nonphase_selection_refused(tmp_path):
    native=_job("ontology-explorer", [{**_browser_setup_step(),"acquisition":"native_parallel"},{"name":"assertion","run":"true"}],timeout=10)
    assert len(PACK.load_legacy_jobs(_write_manifest(tmp_path/"manifest.yml",[native])))==1
    with pytest.raises(PACK.ManifestError):PACK._browser_setup_spec({"name":"assertion","run":"true","acquisition":"native_parallel"})


@pytest.mark.parametrize("job_id", ["ontology-explorer"])
def test_native_manifest900_inherits_one720_total_before_setup_and_preserves_all_assertions(monkeypatch, job_id):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job(job_id, [
        {"name":"before setup assertion", "run":"before"},
        {**_browser_setup_step(), "acquisition":"native_parallel"},
        {"name":"after setup assertion one", "run":"after-one"},
        {"name":"after setup assertion two", "run":"after-two"},
    ], timeout=15)
    ticks = iter([1000., 1000., 1020., 1040., 1060., 1490., 1599.])
    monkeypatch.setattr(PACK.time, "monotonic", lambda:next(ticks))
    calls = []
    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        return PACK.CommandObservation(outcome="passed", returncode=0)
    monkeypatch.setattr(PACK, "_stream_command", stream)
    def setup(**kwargs):
        calls.append(("native once", kwargs["deadline"]))
        return dict(outcome="passed", returncode=0, failure_signature=None, timeout_settlement=None, detail="native and browser acquisition passed")
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.failure is None
    # Setup phase remains bounded to ten minutes from its own start;
    # the surrounding logical job is separately limited to twelve total.
    assert calls == [("before",720), ("capture apt",600), ("capture playwright",580),
                     ("native once",1620), ("after-one",230), ("after-two",121)]
    assert [step["outcome"] for step in result.steps] == ["passed"] * 3
    assert len(result.steps) == len(PACK.semantic_step_specs(job)) == 3


@pytest.mark.parametrize("job_id", ["ontology-explorer"])
def test_native_manifest900_stops_postsetup_assertions_at_bounded720_without_dropping_evidence(monkeypatch, job_id):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job(job_id, [
        {"name":"before setup assertion", "run":"before"},
        {**_browser_setup_step(), "acquisition":"native_parallel"},
        {"name":"after setup assertion one", "run":"after-one"},
        {"name":"after setup assertion two", "run":"after-two"},
    ], timeout=15)
    ticks = iter([0., 0., 100., 120., 140., 720.])
    monkeypatch.setattr(PACK.time, "monotonic", lambda:next(ticks))
    calls = []
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **kwargs:calls.append(command) or PACK.CommandObservation(outcome="passed", returncode=0))
    def setup(**kwargs):
        calls.append(("native once", kwargs["deadline"]))
        return dict(outcome="passed", returncode=0, failure_signature=None, timeout_settlement=None, detail="native and browser acquisition passed")
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == ["before", "capture apt", "capture playwright", ("native once",700)]
    assert [step["outcome"] for step in result.steps] == ["passed", "timed_out", "not_run_prior_failure"]
    assert len(result.steps) == len(PACK.semantic_step_specs(job)) == 3
    assert "after 12 minutes" in result.failure
    assert result.timeout_settlement is None  # the exhausted assertion never launched


def test_native_inherited_total_is_explicitly_digest_bound_without_changing_ordinary_digest(monkeypatch):
    native = _job("ontology-explorer", [{**_browser_setup_step(),"acquisition":"native_parallel"}, {"name":"assertion","run":"true"}], timeout=15)
    ordinary = _job("ordinary", [{"name":"assertion","run":"true"}], timeout=15)
    assert PACK._browser_setup_contract(native)[0]["logical_job_timeout_minutes"] == 12
    before = PACK.semantic_job_digest(native), PACK.semantic_job_digest(ordinary)
    monkeypatch.setattr(PACK, "NATIVE_BROWSER_LOGICAL_JOB_TIMEOUT_MINUTES", 9)
    assert PACK.semantic_job_digest(native) != before[0]
    assert PACK.semantic_job_digest(ordinary) == before[1]


@pytest.mark.parametrize("minutes", [15,12])
def test_non_native_owner_total_remains900_or_international720(monkeypatch, minutes):
    _capture_job_environment(monkeypatch)
    job = _job("ordinary-owner", [{"name":"first","run":"before"}, {"name":"last","run":"after"}], timeout=minutes)
    ticks = iter([0., 0., 650.])
    monkeypatch.setattr(PACK.time, "monotonic", lambda:next(ticks))
    calls = []
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **kwargs:calls.append((command,kwargs["timeout_seconds"])) or PACK.CommandObservation(outcome="passed", returncode=0))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.failure is None
    assert calls == [("before",minutes*60), ("after",minutes*60-650)]


@pytest.mark.parametrize("job_id", ["unrun-brain-gateway-copy", "ordinary-browser",
                                    "bea-gvc-current-descriptive-consumer-copy", "options-matrix-code"])
def test_native_opt_in_refuses_jobs_outside_closed_owner_set(job_id, tmp_path):
    job = _job(job_id, [{**_browser_setup_step(), "acquisition": "native_parallel"},
                        {"name": "assertion", "run": "true"}], timeout=15)
    with pytest.raises(PACK.ManifestError, match="restricted to ontology-explorer"):
        PACK.semantic_job_digest(job)
    with pytest.raises(PACK.ManifestError, match="restricted to ontology-explorer"):
        PACK.load_legacy_jobs(_write_manifest(tmp_path / "forbidden-native.yml", [job]))


def test_unmarked_brain_setup_projection_and_digest_match_protected_contract(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("unmarked setup touched native diagnostics/helpers")
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", forbidden)
    step = _browser_setup_step()
    assert PACK._browser_setup_spec(step) == {
        "phase": "browser_setup", "command": step["run"],
        "timeout_minutes": 10, "budget": "within_original_logical_job_deadline",
    }
    job = _job("unrun-brain-gateway", [step, {"name": "assertion", "run": "true"}], timeout=15)
    # Frozen protected0feed runner, same synthetic definition; no helper-source inputs.
    assert PACK.semantic_job_digest(job) == "13f33f0541d856c443f4137c7376a329773632326d9bb6e91f1957a24aaff876"
    monkeypatch.setattr(PACK, "NATIVE_BROWSER_LOGICAL_JOB_TIMEOUT_MINUTES", 1)
    assert PACK.semantic_job_digest(job) == "13f33f0541d856c443f4137c7376a329773632326d9bb6e91f1957a24aaff876"


@pytest.mark.parametrize("job_id,minutes,setup_minutes", [
    ("unrun-brain-gateway", 15, 10), ("ordinary-browser", 12, 9),
])
def test_unmarked_setup_preserves_installer_only_sequence_and_owner_deadlines(monkeypatch, job_id, minutes, setup_minutes):
    import builtins
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    def forbidden(*_a, **_k):
        raise AssertionError("unmarked setup touched native diagnostics/helpers")
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", forbidden)
    monkeypatch.setattr(PACK, "_run_native_browser_setup", forbidden)
    original_import = builtins.__import__
    def scoped_import(name, *args, **kwargs):
        if name.startswith(("scripts.ci_browser_", "scripts.ci_apt_")):
            forbidden()
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", scoped_import)
    clock = [0.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []
    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += 100 if command == "before" else 400 if "playwright install" in command else 0
        return PACK.CommandObservation(outcome="passed", returncode=0)
    monkeypatch.setattr(PACK, "_stream_command", stream)
    job = _job(job_id, [{"name": "before", "run": "before"},
                       _browser_setup_step(minutes=setup_minutes),
                       {"name": "after", "run": "after"}], timeout=minutes)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.failure is None
    assert calls == [("before", minutes * 60),
                     ("python -m playwright install --with-deps chromium", min(minutes * 60 - 100, setup_minutes * 60)),
                     ("after", minutes * 60 - 500)]
    assert [step["outcome"] for step in result.steps] == ["passed", "passed"]


@pytest.mark.parametrize("outcome", ["failed", "timed_out"])
def test_unmarked_brain_unknown_installer_preserves_settlement_fence(monkeypatch, outcome):
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    def forbidden(*_a, **_k):
        raise AssertionError("unknown original command must not trigger native capture or Git healing")
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", forbidden)
    monkeypatch.setattr(PACK, "_run_native_browser_setup", forbidden)
    monkeypatch.setattr(PACK, "_ensure_pack_git_usable", forbidden)
    calls = []
    def stream(command, **kwargs):
        calls.append(command)
        return PACK.CommandObservation(outcome=outcome, returncode=None,
                                       timeout_settlement="unknown", detail="original installer settlement unknown")
    monkeypatch.setattr(PACK, "_stream_command", stream)
    job = _job("unrun-brain-gateway", [_browser_setup_step(),
                                     {"name": "assertion", "run": "true"}], timeout=15)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={}, tested_tree_sha=SHA_TREE)
    assert calls == ["python -m playwright install --with-deps chromium"]
    assert result.timeout_settlement == "unknown"
    assert result.infrastructure["outcome"] == "unknown"
    assert result.steps[0]["outcome"] == "infrastructure_blocked"


def test_explicit_owner_manifest_activation_keeps_brain900_and_international720():
    jobs = {job.job_id: job for job in PACK.load_legacy_jobs(MANIFEST)}
    native = [job.job_id for job in jobs.values()
              if any(spec.get("acquisition") == "native_parallel" for spec in PACK._browser_setup_contract(job))]
    assert native == ["bea-gvc-current-descriptive-consumer", "ontology-explorer", "unrun-brain-gateway"]
    assert jobs["unrun-brain-gateway"].definition["timeout-minutes"] == 15
    assert jobs["international-workspace-browser"].definition["timeout-minutes"] == 12
    brain = PACK._browser_setup_contract(jobs["unrun-brain-gateway"])[0]
    assert brain["activation_job_id"] == "unrun-brain-gateway"
    assert brain["logical_job_timeout_minutes"] == 15 and brain["timeout_minutes"] == 10
    assert len(brain["native_source_sha256"]) == 7


# Explicit Brain activation preserves its own original total, not Ontology's.
def test_native_brain900_keeps_prior_python_and_setup_inside_original_deadline(monkeypatch):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job("unrun-brain-gateway", [
        {"name": "prior Python", "run": "before"},
        {**_browser_setup_step(), "acquisition": "native_parallel"},
        {"name": "financial assertion one", "run": "after-one"},
        {"name": "financial assertion two", "run": "after-two"},
    ], timeout=15)
    clock = [1000.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []
    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += {"before": 200, "capture apt": 40, "capture playwright": 60,
                     "after-one": 90}.get(command, 0)
        return PACK.CommandObservation(outcome="passed", returncode=0)
    monkeypatch.setattr(PACK, "_stream_command", stream)
    def setup(**kwargs):
        assert kwargs["deadline"] == 1800  # min(original1900, setup1200+600)
        assert len(kwargs["expected_sources"]) == 7
        calls.append(("native once", kwargs["deadline"]))
        clock[0] = 1790
        return dict(outcome="passed", returncode=0, failure_signature=None,
                    timeout_settlement=None, detail="native and browser setup passed")
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.failure is None
    assert calls == [("before", 900), ("capture apt", 600), ("capture playwright", 560),
                     ("native once", 1800), ("after-one", 110), ("after-two", 20)]
    assert [s["outcome"] for s in result.steps] == ["passed"] * 3


@pytest.mark.parametrize("prior_elapsed", [550, 899, 900])
def test_native_brain_late_setup_cannot_reset_original900(monkeypatch, prior_elapsed):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job("unrun-brain-gateway", [{"name": "prior", "run": "before"},
        {**_browser_setup_step(), "acquisition": "native_parallel"},
        {"name": "financial assertion", "run": "after"}], timeout=15)
    clock = [0.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []
    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += prior_elapsed if command == "before" else 1 if prior_elapsed == 899 else 10 if command.startswith("capture") else 0
        return PACK.CommandObservation(outcome="passed", returncode=0)
    monkeypatch.setattr(PACK, "_stream_command", stream)
    def setup(**kwargs):
        assert prior_elapsed == 550
        calls.append(("native once", kwargs["deadline"]))
        assert kwargs["deadline"] == 900  # remaining350, no new setup grant
        clock[0] = 899
        return dict(outcome="passed", returncode=0, failure_signature=None,
                    timeout_settlement=None, detail="setup completed")
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    if prior_elapsed == 550:
        assert calls == [("before",900),("capture apt",350),("capture playwright",340),("native once",900),("after",1)]
        assert result.failure is None
    else:
        assert calls == [("before",900)] + ([("capture apt",1)] if prior_elapsed == 899 else [])
        assert result.failure is not None and result.timeout_settlement is None
        assert result.steps[-1]["outcome"] == "infrastructure_blocked"


@pytest.mark.parametrize("helper", [
    "ci_apt_cold_acquisition.py", "ci_apt_native_plan.py", "ci_apt_native_stage.py",
    "ci_browser_native_setup.py", "ci_apt_transaction_contract.py",
    "ci_browser_dependency_capture.py", "ci_browser_dependency_inputs.py",
])
def test_native_brain_binds_each_helper_and_its_explicit_owner_total(monkeypatch, helper):
    native = _job("unrun-brain-gateway", [{**_browser_setup_step(), "acquisition":"native_parallel"}, {"run":"true"}], timeout=15)
    ordinary = _job("unrun-brain-gateway", [_browser_setup_step(), {"run":"true"}], timeout=15)
    contract = PACK._browser_setup_contract(native)[0]
    assert contract["activation_job_id"] == "unrun-brain-gateway"
    assert contract["logical_job_timeout_minutes"] == 15
    assert contract["timeout_minutes"] == 10 and len(contract["native_source_sha256"]) == 7
    before = PACK.semantic_job_digest(native), PACK.semantic_job_digest(ordinary)
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda p: read(p) + b"# source changed" if p.name == helper else read(p))
    assert PACK.semantic_job_digest(native) != before[0]
    assert PACK.semantic_job_digest(ordinary) == before[1]

def test_native_brain_total_is_digest_bound_without_changing_other_owners(monkeypatch):
    setup = {**_browser_setup_step(), "acquisition": "native_parallel"}
    brain = _job("unrun-brain-gateway", [setup, {"run":"true"}], timeout=15)
    ontology = _job("ontology-explorer", [setup, {"run":"true"}], timeout=15)
    unmarked = _job("unrun-brain-gateway", [_browser_setup_step(), {"run":"true"}], timeout=15)
    before = tuple(PACK.semantic_job_digest(job) for job in [brain, ontology, unmarked])
    assert before[0] != before[1]
    monkeypatch.setattr(PACK, "NATIVE_BRAIN_LOGICAL_JOB_TIMEOUT_MINUTES", 14)
    assert PACK.semantic_job_digest(brain) != before[0]
    assert PACK.semantic_job_digest(ontology) == before[1]
    assert PACK.semantic_job_digest(unmarked) == before[2]


@pytest.mark.parametrize("job_id,minutes", [("unrun-brain-gateway", 15), ("ontology-explorer", 12)])
def test_native_setup600_exhausts_before_larger_job_total(monkeypatch, job_id, minutes):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job(job_id, [{**_browser_setup_step(), "acquisition":"native_parallel"},
                {"name":"financial assertion","run":"after"}], timeout=minutes)
    clock = [0.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda:clock[0])
    calls = []
    def stream(command, **kwargs):
        calls.append((command,kwargs["timeout_seconds"]))
        clock[0] = 600
        return PACK.CommandObservation(outcome="passed",returncode=0)
    monkeypatch.setattr(PACK,"_stream_command",stream)
    monkeypatch.setattr(native,"run_native_setup",lambda **_k:pytest.fail("setup cannot restart after its original600"))
    result = PACK._run_job(job,base_ref="main",head_ref="",command_env={})
    assert calls == [("capture apt",600)]
    assert result.failure is not None and result.timeout_settlement is None
    assert result.steps[0]["outcome"] == "infrastructure_blocked"


def test_native_brain_postsetup_assertions_stop_at_original900(monkeypatch):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job("unrun-brain-gateway", [
        {"name":"prior Python","run":"before"},
        {**_browser_setup_step(),"acquisition":"native_parallel"},
        {"name":"financial one","run":"after-one"},
        {"name":"financial two","run":"after-two"},
        {"name":"financial three","run":"after-three"}],timeout=15)
    clock = [0.0]
    monkeypatch.setattr(PACK.time,"monotonic",lambda:clock[0])
    calls=[]
    def stream(command,**kwargs):
        calls.append((command,kwargs["timeout_seconds"]))
        clock[0] += 200 if command=="before" else 101 if command=="after-one" else 0
        return PACK.CommandObservation(outcome="passed",returncode=0)
    monkeypatch.setattr(PACK,"_stream_command",stream)
    def setup(**kwargs):
        assert kwargs["deadline"]==800
        calls.append(("native once",kwargs["deadline"]))
        clock[0]=799
        return dict(outcome="passed",returncode=0,failure_signature=None,timeout_settlement=None,detail="setup completed")
    monkeypatch.setattr(native,"run_native_setup",setup)
    result=PACK._run_job(job,base_ref="main",head_ref="",command_env={})
    assert calls==[("before",900),("capture apt",600),("capture playwright",600),("native once",800),("after-one",101)]
    assert [s["outcome"] for s in result.steps]==["passed","passed","timed_out","not_run_prior_failure"]
    assert "after 15 minutes" in result.failure
    assert result.timeout_settlement is None


@pytest.mark.parametrize("job_id", ["unrun-brain-gateway", "bea-gvc-current-descriptive-consumer", "ontology-explorer"])
@pytest.mark.parametrize("mode", ["timeout_unknown", "response_loss", "settled_failure"])
def test_native_owner_result_controls_pack_reuse(tmp_path, monkeypatch, mode, job_id):
    from scripts import ci_browser_native_setup as native

    jobs = [
        _job(job_id, [
            {"run": "pip install pytest"},
            {**_browser_setup_step(), "acquisition": "native_parallel"},
            {"name": "financial assertion", "run": "must-not-run"},
        ], timeout={"unrun-brain-gateway": 15, "bea-gvc-current-descriptive-consumer": 10, "ontology-explorer": 12}[job_id]),
        _job("later", [{"run": "pip install pytest pyyaml"}, {"name": "later assertion", "run": "later-command"}], ordinal=1),
    ]
    calls = {"native": [], "deps": [], "restore": [], "heal": [], "replay": [], "commands": []}
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_current_commit_sha", lambda *_a: SHA_TREE)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", lambda: ())
    monkeypatch.setattr(PACK, "_dependency_environment", lambda dep, **_k: calls["deps"].append(dep) or {})
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: calls["restore"].append(True))
    monkeypatch.setattr(PACK, "_ensure_pack_git_usable", lambda *_a: calls["heal"].append(True) or False)
    monkeypatch.setattr(PACK, "_assert_no_git_rewrites", lambda *_a: None)
    monkeypatch.setattr(PACK, "_run_exact_base_replays", lambda **_k: calls["replay"].append(True))
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **_k:
                        calls["commands"].append(command) or PACK.CommandObservation(outcome="passed", returncode=0))

    def setup(**kwargs):
        calls["native"].append(True)
        assert len(calls["restore"]) == 1
        assert kwargs["deadline"] == 600
        if mode == "response_loss":
            raise OSError("original native response lost")
        return dict(outcome="timed_out" if mode == "timeout_unknown" else "failed",
                    returncode=None if mode == "timeout_unknown" else 1,
                    failure_signature=None,
                    timeout_settlement="unknown" if mode == "timeout_unknown" else None,
                    detail="original native result")

    monkeypatch.setattr(native, "run_native_setup", setup)
    plan = _plan(jobs, changed=[], pack_count=1)
    fragment = tmp_path / "fragment.json"
    assert PACK.execute_pack(jobs, plan=plan, emit_semantic_fragment=fragment) == 1
    doc = json.loads(fragment.read_text())
    assert calls["native"] == [True]
    assert doc["jobs"][0]["steps"][0]["outcome"] == "infrastructure_blocked"
    if mode == "settled_failure":
        assert calls["deps"] == ["pip install pytest", "pip install pytest pyyaml"]
        assert calls["commands"] == ["later-command"]
        assert doc["jobs"][0]["infrastructure"]["outcome"] == "dependency_failed"
        assert doc["jobs"][1]["steps"][0]["outcome"] == "passed"
    else:
        assert calls["deps"] == ["pip install pytest"]
        assert calls["commands"] == []
        assert calls["restore"] == [True] and calls["heal"] == [] and calls["replay"] == []
        assert doc["jobs"][0]["infrastructure"]["outcome"] == "unknown"
        assert doc["jobs"][1]["steps"][0]["outcome"] == "infrastructure_blocked"
    assert not SEMANTIC.semantic_gate_verdict(SEMANTIC.reconcile_evidence(plan.to_dict(), [doc])).clear


@pytest.mark.parametrize("declared_minutes", [10, 15])
def test_native_bea_total600_includes_prior_work_setup_and_all_assertions(monkeypatch, declared_minutes):
    from scripts import ci_browser_native_setup as native

    _capture_job_environment(monkeypatch)
    job = _job("bea-gvc-current-descriptive-consumer", [
        {"name": "prior work", "run": "before"},
        {**_browser_setup_step(), "acquisition": "native_parallel"},
        *[{"name": f"assertion {i}", "run": f"assert-{i}"} for i in range(3)],
    ], timeout=declared_minutes)
    clock = [1000.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []

    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += 200 if command == "before" else 40 if command == "capture apt" else 60 if command == "capture playwright" else 5
        return PACK.CommandObservation(outcome="passed", returncode=0)

    def setup(**kwargs):
        assert kwargs["deadline"] == 1600  # Original1000+600, never setup1200+600.
        assert len(kwargs["expected_sources"]) == 7
        calls.append(("native once", kwargs["deadline"]))
        clock[0] = 1580
        return dict(outcome="passed", returncode=0, failure_signature=None,
                    timeout_settlement=None, detail="native setup completed")

    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert result.failure is None
    assert calls == [("before", 600), ("capture apt", 400), ("capture playwright", 360),
                     ("native once", 1600), ("assert-0", 20), ("assert-1", 15), ("assert-2", 10)]
    assert [step["outcome"] for step in result.steps] == ["passed"] * 4


@pytest.mark.parametrize("prior_elapsed", [599, 600])
def test_native_bea_exhausted_original600_cannot_start_or_restart_setup(monkeypatch, prior_elapsed):
    from scripts import ci_browser_native_setup as native

    _capture_job_environment(monkeypatch)
    job = _job("bea-gvc-current-descriptive-consumer", [
        {"name": "prior work", "run": "before"},
        {**_browser_setup_step(), "acquisition": "native_parallel"},
        *[{"name": f"assertion {i}", "run": f"assert-{i}"} for i in range(3)],
    ], timeout=10)
    clock = [0.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []

    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += prior_elapsed if command == "before" else 1
        return PACK.CommandObservation(outcome="passed", returncode=0)

    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(native, "run_native_setup", lambda **_k: pytest.fail("elapsed original budget cannot launch native setup"))
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    assert calls == [("before", 600)] + ([("capture apt", 1)] if prior_elapsed == 599 else [])
    assert result.failure is not None and result.timeout_settlement is None
    assert [step["outcome"] for step in result.steps] == ["passed"] + ["infrastructure_blocked"] * 3


def test_bea_original_installer_proof_cannot_satisfy_new_blocking_setup_plan(tmp_path, monkeypatch):
    import copy
    from scripts import ci_browser_native_setup as native

    monkeypatch.setattr(PACK, "_browser_dependency_diagnostic_commands", lambda: ())
    job = next(j for j in PACK.load_legacy_jobs(MANIFEST) if j.job_id == "bea-gvc-current-descriptive-consumer")
    old_definition = copy.deepcopy(job.definition)
    installer = old_definition["steps"][3]
    for key in ("phase", "acquisition", "timeout-minutes"):
        del installer[key]
    old = PACK.LegacyJob(job.job_id, old_definition, job.ordinal, job.weight)
    plans = [_plan([j], changed=["tests/test_bea_gvc_browser.py"], pack_count=1) for j in (old, job)]
    monkeypatch.setattr(PACK, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(PACK, "_current_commit_sha", lambda *_a: SHA_TREE)
    monkeypatch.setattr(PACK, "_prepare_provided_actions", lambda *_a, **_k: None)
    monkeypatch.setattr(PACK, "_dependency_environment", lambda *_a, **_k: {})
    monkeypatch.setattr(PACK, "_restore_workspace", lambda *_a: None)
    monkeypatch.setattr(PACK, "_assert_no_git_rewrites", lambda *_a: None)
    monkeypatch.setattr(PACK, "_ensure_pack_git_usable", lambda *_a: False)
    monkeypatch.setattr(PACK.time, "monotonic", lambda: 0.0)
    commands = []
    monkeypatch.setattr(PACK, "_stream_command", lambda command, **_k:
                        commands.append(command) or PACK.CommandObservation(outcome="passed", returncode=0))
    native_calls = []
    def setup(**kwargs):
        native_calls.append(kwargs["deadline"])
        return dict(outcome="passed", returncode=0, failure_signature=None,
                    timeout_settlement=None, detail="verified fixture setup")
    monkeypatch.setattr(native, "run_native_setup", setup)
    documents = []
    for j, plan in zip((old, job), plans):
        target = tmp_path / ("old.json" if j is old else "new.json")
        assert PACK.execute_pack([j], plan=plan, emit_semantic_fragment=target) == 0
        documents.append(json.loads(target.read_text()))
        assert SEMANTIC.semantic_gate_verdict(SEMANTIC.reconcile_evidence(plan.to_dict(), [documents[-1]])).clear
    assert native_calls == [600]
    old_steps, new_steps = (doc["jobs"][0]["steps"] for doc in documents)
    assert len(old_steps) == 4 and len(new_steps) == 3
    assert old_steps[1:] == new_steps
    assert documents[1]["jobs"][0]["infrastructure"]["outcome"] == "passed"
    assert commands.count("python -m playwright install --with-deps chromium") == 1
    for step in job.definition["steps"][4:]:
        assert commands.count(step["run"]) == 2  # Each fixture still executes every actual assertion.
    with pytest.raises(SEMANTIC.SemanticProofError, match="plan_sha256"):
        SEMANTIC.reconcile_evidence(plans[1].to_dict(), [documents[0]])
    forged = copy.deepcopy(documents[0])
    forged["plan_sha256"] = plans[1].plan_sha256
    with pytest.raises(SEMANTIC.SemanticProofError, match="job digest mismatch"):
        SEMANTIC.reconcile_evidence(plans[1].to_dict(), [forged])


@pytest.mark.parametrize("job_id,total,setup_deadline", [
    ("ontology-explorer", 720, 1720),
    ("unrun-brain-gateway", 900, 1800),
    ("bea-gvc-current-descriptive-consumer", 600, 1600),
])
def test_native_per_owner_totals_share_original_clock(monkeypatch, job_id, total, setup_deadline):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job(job_id, [{"name": "prior", "run": "before"},
        {**_browser_setup_step(), "acquisition": "native_parallel"},
        {"name": "assertion one", "run": "after-one"},
        {"name": "assertion two", "run": "after-two"}], timeout=15)
    clock = [1000.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []
    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += {"before": 200, "capture apt": 40, "capture playwright": 60}.get(command, 5)
        return PACK.CommandObservation(outcome="passed", returncode=0)
    def setup(**kwargs):
        assert kwargs["deadline"] == setup_deadline
        assert len(kwargs["expected_sources"]) == 7
        calls.append(("native once", kwargs["deadline"]))
        clock[0] = setup_deadline - 10
        return dict(outcome="passed", returncode=0, failure_signature=None,
                    timeout_settlement=None, detail="verified setup")
    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    setup_remaining = min(total - 200, 600)
    after_remaining = 1000 + total - setup_deadline + 10
    assert calls == [("before", total), ("capture apt", setup_remaining),
                     ("capture playwright", setup_remaining - 40), ("native once", setup_deadline),
                     ("after-one", after_remaining), ("after-two", after_remaining - 5)]
    assert result.failure is None
    assert [step["outcome"] for step in result.steps] == ["passed"] * 3


@pytest.mark.parametrize("prior_elapsed", [119, 121, 719, 720])
def test_ontology720_late_setup_preserves_both_deadlines(monkeypatch, prior_elapsed):
    from scripts import ci_browser_native_setup as native
    _capture_job_environment(monkeypatch)
    job = _job("ontology-explorer", [{"name": "prior", "run": "before"},
        {**_browser_setup_step(), "acquisition": "native_parallel"},
        {"name": "assertion", "run": "after"}], timeout=12)
    clock = [0.0]
    monkeypatch.setattr(PACK.time, "monotonic", lambda: clock[0])
    calls = []
    def stream(command, **kwargs):
        calls.append((command, kwargs["timeout_seconds"]))
        clock[0] += prior_elapsed if command == "before" else 1 if prior_elapsed == 719 else 0
        return PACK.CommandObservation(outcome="passed", returncode=0)
    def setup(**kwargs):
        assert prior_elapsed < 719
        deadline = min(720, prior_elapsed + 600)
        assert kwargs["deadline"] == deadline
        calls.append(("native once", deadline))
        clock[0] = deadline - 1
        return dict(outcome="passed", returncode=0, failure_signature=None,
                    timeout_settlement=None, detail="verified setup")
    monkeypatch.setattr(PACK, "_stream_command", stream)
    monkeypatch.setattr(native, "run_native_setup", setup)
    result = PACK._run_job(job, base_ref="main", head_ref="", command_env={})
    if prior_elapsed < 719:
        limit = min(720 - prior_elapsed, 600)
        deadline = min(720, prior_elapsed + 600)
        assert calls == [("before", 720), ("capture apt", limit), ("capture playwright", limit),
                         ("native once", deadline), ("after", 721 - deadline)]
        assert result.failure is None
    else:
        assert calls == [("before", 720)] + ([("capture apt", 1)] if prior_elapsed == 719 else [])
        assert result.failure is not None and result.timeout_settlement is None
        assert result.steps[-1]["outcome"] == "infrastructure_blocked"


def test_ontology720_digest_change_does_not_change_other_owner_contracts(monkeypatch):
    native_step = {**_browser_setup_step(), "acquisition": "native_parallel"}
    jobs = [_job(name, [native_step, {"name": "assertion", "run": "true"}], timeout=15)
            for name in ("ontology-explorer", "unrun-brain-gateway", "bea-gvc-current-descriptive-consumer")]
    jobs.append(_job("ordinary", [_browser_setup_step(), {"name": "assertion", "run": "true"}], timeout=15))
    before = [PACK.semantic_job_digest(job) for job in jobs]
    monkeypatch.setattr(PACK, "NATIVE_BROWSER_LOGICAL_JOB_TIMEOUT_MINUTES", 10)
    after = [PACK.semantic_job_digest(job) for job in jobs]
    assert before[0] != after[0]
    assert before[1:] == after[1:]


import ast as _cm_ast
import json as _cm_json
from pathlib import Path as _CMPath
import re as _cm_re
import shlex as _cm_shlex
import subprocess as _cm_subprocess
import sys as _cm_sys
import tempfile as _cm_tempfile
import unittest as _cm_unittest
from unittest import mock as _cm_mock

_CM_FROZEN_PATHS = (
    'templates/theme.css',
    'templates/_navlinks.html.j2',
    'engine/intl_global_universe.py',
    'engine/intl_global_observation.py',
    'lib/intl_global_observation_adapter.py',
)


def _cm_git(root, *args):
    return _cm_subprocess.run(
        ['git', '-C', str(root), *map(str, args)], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def _cm_commit(root, path, content, message):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    _cm_git(root, 'add', '--', path)
    _cm_git(root, 'commit', '-qm', message)
    return _cm_git(root, 'rev-parse', 'HEAD')


def _cm_fixture(parent, *, changed_frozen=False, shallow_remote=False, full_checkout=False, old_history=False):
    """main is ahead of tested's first parent; tested itself diverges from main.

    Both tested parents meet at main-2, 22 first-parent edges behind main-24.
    A depth-one checkout therefore requires multiple completed deepen fetches.
    Plain local-path clone is intentionally avoided: it ignores --depth.
    """
    source = parent / 'source'
    source.mkdir()
    _cm_git(source, 'init', '-q', '--initial-branch=main')
    # These disposable repositories must not leave housekeeping writers behind
    # after the real Git commands return and TemporaryDirectory cleanup begins.
    _cm_git(source, 'config', '--local', 'gc.auto', '0')
    _cm_git(source, 'config', '--local', 'maintenance.auto', 'false')
    _cm_git(source, 'config', 'user.name', 'Canonical Fixture')
    _cm_git(source, 'config', 'user.email', 'canonical@example.invalid')
    for path in _CM_FROZEN_PATHS:
        dest = source / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('frozen baseline\n', encoding='utf-8')
    _cm_git(source, 'add', '.')
    _cm_git(source, 'commit', '-qm', 'frozen baseline')
    if old_history:
        for number in range(32):
            _cm_commit(source, 'older.txt', f'{number}\n', f'older-{number}')
    commits = []
    for number in range(36):
        commits.append(_cm_commit(source, 'main.txt', f'{number}\n', f'main-{number}'))
    canonical = commits[-1]
    _cm_git(source, 'switch', '-qc', 'feature', commits[2])
    for number in range(4):
        _cm_commit(source, 'feature.txt', f'{number}\n', f'feature-{number}')
    if changed_frozen:
        _cm_commit(source, _CM_FROZEN_PATHS[0], 'changed by feature\n', 'change frozen file')
    feature = _cm_git(source, 'rev-parse', 'HEAD')
    _cm_git(source, 'switch', '-qc', 'tested', commits[24])
    _cm_git(source, 'merge', '--no-ff', '-qm', 'synthetic tested merge', 'feature')
    tested = _cm_git(source, 'rev-parse', 'HEAD')
    _cm_git(source, 'switch', '-q', 'main')
    remote = source
    if shallow_remote:
        remote = parent / 'shallow.git'
        _cm_git(parent, 'clone', '-q', '--bare', '--no-tags', '--depth=2',
                '--config=gc.auto=0', '--config=maintenance.auto=false',
                '--single-branch', '--branch=tested', source.as_uri(), remote)
        # Canonical main deliberately shares the tested tip in this source.
        # Parent history is genuinely capped, so fetches can complete without
        # ever satisfying the tested-parent merge-base requirement.
        _cm_git(remote, 'update-ref', 'refs/heads/main', tested)
        canonical = tested
    checkout = parent / 'checkout'
    args = ['clone', '-q', '--no-tags', '--single-branch', '--branch=tested',
            '--config=gc.auto=0', '--config=maintenance.auto=false']
    if not full_checkout:
        args.append('--depth=1')
    _cm_git(parent, *args, remote.as_uri(), checkout)
    return {'source': source, 'remote': remote, 'checkout': checkout,
            'tested': tested, 'canonical': canonical, 'commits': commits,
            'parents': (commits[24], feature), 'fetches': []}


def _cm_prepare(fixture, *, hook=None, tested=None, base_ref='main'):
    """Observe real fetches; hook only injects a boundary mutation/exception.

    All normal commands run through the original subprocess.run. No fetch result
    or readiness probe is replaced with a mocked successful response.
    """
    real_run = _cm_subprocess.run
    fixture['fetches'] = []

    def observed(argv, *args, **kwargs):
        command = list(argv) if isinstance(argv, (list, tuple)) else []
        is_fetch = bool(command and command[0] == 'git' and 'fetch' in command)
        if is_fetch:
            fixture['fetches'].append(command)
            if hook:
                hook('before', fixture, command, len(fixture['fetches']))
        result = real_run(argv, *args, **kwargs)
        if is_fetch and hook:
            hook('after', fixture, command, len(fixture['fetches']))
        return result

    with _cm_mock.patch.object(PACK.subprocess, 'run', side_effect=observed):
        return PACK.prepare_canonical_main(
            fixture['checkout'], tested_tree_sha=tested or fixture['tested'],
            base_ref=base_ref,
        )


def _cm_python_environment(parent, executable):
    """Bind literal python privately without resolving away its runtime context."""
    environment = os.environ.copy()
    interpreter_bin = parent / "interpreter-bin"
    interpreter_bin.mkdir()
    wrapper = interpreter_bin / "python"
    wrapper.write_text(
        '#!/bin/sh\nexec ' + _cm_shlex.quote(executable) + ' "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    environment["PATH"] = str(interpreter_bin) + os.pathsep + environment.get("PATH", "")
    return environment


def _cm_frozen_namespace(checkout):
    """Compile the two ORIGINAL guard bodies, dropping only pytest decoration."""
    source = ROOT / 'tests' / 'test_intl_gs_foundation.py'
    parsed = _cm_ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    names = {'_frozen_base', 'test_frozen_files_unchanged_vs_origin_main'}
    functions = [node for node in parsed.body
                 if isinstance(node, _cm_ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names:
        raise AssertionError('original frozen-file functions are missing')
    for node in functions:
        node.decorator_list = []
    namespace = {'REPO': checkout, 'subprocess': _cm_subprocess,
                 're': _cm_re, 'pytest': pytest}
    exec(compile(_cm_ast.Module(body=functions, type_ignores=[]),
                 str(source), 'exec'), namespace)
    return namespace


class CanonicalMainPreparationTests(_cm_unittest.TestCase):
    def test_manifest_step_runs_actual_helper_with_replay_identity_precedence(self):
        f = self.fixture()
        definition = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["jobs"][
            "international-workspace-browser"
        ]
        step = next(item for item in definition["steps"] if item.get("name") ==
                    "canonical base for the frozen-file guard (fail closed)")
        command = PACK.render_command(step["run"], base_ref="main", head_ref="feature")
        # Keep the actual manifest command and the current interpreter's exact
        # path, including the venv/relocatable runtime context it identifies.
        environment = _cm_python_environment(self.parent, _cm_sys.executable)
        environment.update({
            "PYTHONPATH": str(ROOT),
            # Base replay has its own exact tree; inherited parent-run identity
            # must not replace it. Neither event-base value is canonical main.
            "CI_TESTED_TREE_SHA": f["tested"],
            "TESTED_TREE_SHA": "f" * 40,
            "CI_BASE_SHA": f["parents"][0],
            "TESTED_BASE_SHA": f["parents"][0],
        })
        result = _cm_subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", command],
            cwd=f["checkout"], env=environment, capture_output=True, text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(_cm_git(f["checkout"], "rev-parse", "origin/main"), f["canonical"])
        self.assertIn(f["canonical"], result.stdout)
        self.assert_head(f)

    def test_private_python_binding_preserves_venv_context_and_arguments(self):
        venv_root = self.parent / "driver's isolated venv"
        _cm_subprocess.run(
            [_cm_sys.executable, "-m", "venv", "--without-pip", str(venv_root)],
            check=True, capture_output=True, text=True, timeout=30,
        )
        probe = (
            "import json,sys,sysconfig; "
            "print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,"
            "'base_prefix':sys.base_prefix,'purelib':sysconfig.get_path('purelib')}))"
        )
        direct = _cm_subprocess.run(
            [str(venv_root / "bin" / "python"), "-c", probe],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(direct.returncode, 0, direct.stdout + direct.stderr)
        driver = _cm_json.loads(direct.stdout)
        site_packages = _CMPath(driver["purelib"])
        self.assertEqual(_CMPath(driver["prefix"]).resolve(), venv_root.resolve())
        self.assertTrue(site_packages.resolve().is_relative_to(venv_root.resolve()))
        (site_packages / "canonical_fixture_venv_only.py").write_text(
            "VALUE = 'available only inside the fresh driver venv'\n", encoding="utf-8",
        )
        environment = _cm_python_environment(self.parent, driver["executable"])
        environment["PYTHONPATH"] = str(ROOT)
        environment["PYTHONNOUSERSITE"] = "1"
        child_probe = (
            "import json,sys,canonical_fixture_venv_only as marker; "
            "print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,"
            "'base_prefix':sys.base_prefix,'marker':marker.VALUE,'arguments':sys.argv[1:]}))"
        )
        arguments = ["argument with spaces", "argument's apostrophe"]
        child = _cm_subprocess.run(
            ["python", "-c", child_probe, *arguments], env=environment,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        actual = _cm_json.loads(child.stdout)
        for key in ("executable", "prefix", "base_prefix"):
            self.assertEqual(actual[key], driver[key])
        self.assertEqual(actual["marker"], "available only inside the fresh driver venv")
        self.assertEqual(actual["arguments"], arguments)

    def setUp(self):
        self.temporary = _cm_tempfile.TemporaryDirectory(prefix='canonical-main-test-')
        self.addCleanup(self.temporary.cleanup)
        self.parent = _CMPath(self.temporary.name)

    def fixture(self, **kwargs):
        case = self.parent / f'case-{len(list(self.parent.iterdir()))}'
        case.mkdir()
        return _cm_fixture(case, **kwargs)

    def assert_head(self, fixture):
        self.assertEqual(_cm_git(fixture['checkout'], 'rev-parse', 'HEAD'), fixture['tested'])

    def assert_fetch_contract(self, fixture):
        fetches = fixture['fetches']
        self.assertTrue(fetches)
        self.assertLessEqual(len(fetches), 6)
        increments = (2, 6, 24, 96, 384, 1536)
        for index, command in enumerate(fetches):
            self.assertIn('--no-tags', command)
            self.assertIn('--no-recurse-submodules', command)
            self.assertIn(f'--deepen={increments[index]}', command)
            self.assertIn(fixture['tested'], command)
            self.assertFalse(any(arg.startswith('--depth=') for arg in command))
            if index == 0:
                self.assertIn('+refs/heads/main:refs/remotes/origin/main', command)
            else:
                self.assertIn(fixture['canonical'], command)
                self.assertFalse(any('refs/heads/main' in arg for arg in command))

    def test_canonical_filter_is_child_only_and_probes_are_offline(self):
        f = self.fixture(full_checkout=True)
        _cm_git(f['source'], 'config', 'uploadpack.allowFilter', 'true')
        before = (f['checkout'] / '.git' / 'config').read_bytes()
        real_run = _cm_subprocess.run
        seen = []

        def observe(argv, *args, **kwargs):
            command = list(argv)
            if command and command[0] == 'git':
                env = kwargs.get('env', {})
                if 'fetch' in command:
                    self.assertIn('--filter=blob:none', command)
                    self.assertEqual(env.get('GIT_CONFIG_COUNT'), '2')
                    self.assertEqual(env.get('GIT_CONFIG_KEY_0'), 'remote.origin.promisor')
                    self.assertEqual(env.get('GIT_CONFIG_VALUE_0'), 'true')
                    self.assertEqual(env.get('GIT_CONFIG_KEY_1'), 'remote.origin.partialclonefilter')
                    self.assertEqual(env.get('GIT_CONFIG_VALUE_1'), 'blob:none')
                else:
                    self.assertEqual(env.get('GIT_NO_LAZY_FETCH'), '1')
                    self.assertEqual(env.get('GIT_ALLOW_PROTOCOL'), '')
                seen.append(command)
            return real_run(argv, *args, **kwargs)

        with _cm_mock.patch.object(PACK.subprocess, 'run', side_effect=observe):
            self.assertEqual(PACK.prepare_canonical_main(
                f['checkout'], tested_tree_sha=f['tested']), f['canonical'])
        self.assertTrue(seen)
        self.assertEqual(before, (f['checkout'] / '.git' / 'config').read_bytes())
        guards = _cm_frozen_namespace(f['checkout'])
        for path in _CM_FROZEN_PATHS:
            guards['test_frozen_files_unchanged_vs_origin_main'](path)

    def test_missing_required_blob_refuses_after_fetch_without_lazy_fallback(self):
        f = self.fixture(full_checkout=True)
        _cm_git(f['source'], 'config', 'uploadpack.allowFilter', 'true')
        removed = []

        def remove(phase, fixture, command, count):
            if phase != 'after' or count != 1:
                return
            repo = fixture['checkout']
            blob = _cm_git(repo, 'rev-parse', fixture['tested'] + ':' + _CM_FROZEN_PATHS[0])
            packs = repo / '.git' / 'objects' / 'pack'
            held = self.parent / 'retained-fixture-packs'
            held.mkdir()
            names = [p.name for p in packs.glob('*.pack')]
            for path in list(packs.iterdir()):
                path.rename(held / path.name)
            for name in names:
                with (held / name).open('rb') as data:
                    _cm_subprocess.run(['git', '-C', str(repo), 'unpack-objects', '-r'],
                        stdin=data, check=True, capture_output=True,
                        env=dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL=''))
            target = repo / '.git' / 'objects' / blob[:2] / blob[2:]
            self.assertTrue(target.is_file())
            target.unlink()
            removed.append(blob)

        with self.assertRaisesRegex(RuntimeError, 'required.*object'):
            _cm_prepare(f, hook=remove)
        self.assertEqual(len(removed), 1)
        self.assertEqual(len(f['fetches']), 1)
        self.assert_head(f)

    def test_missing_origin_main_acquires_actual_canonical_tip(self):
        f = self.fixture()
        absent = _cm_subprocess.run(
            ['git', '-C', str(f['checkout']), 'show-ref', '--verify', 'refs/remotes/origin/main'],
            capture_output=True, text=True,
        )
        self.assertNotEqual(absent.returncode, 0)
        self.assertEqual(_cm_prepare(f), f['canonical'])
        self.assertEqual(_cm_git(f['checkout'], 'rev-parse', 'origin/main'), f['canonical'])
        self.assert_head(f)
        self.assert_fetch_contract(f)
        self.assertGreater(len(f['fetches']), 1)
        self.assertEqual(_cm_git(f['checkout'], 'merge-base', *f['parents']), f['commits'][2])
        self.assertEqual(_cm_git(f['checkout'], 'merge-base', 'origin/main', 'HEAD'), f['parents'][0])

    def test_pre_ready_tested_ancestry_is_retained_by_canonical_fetch(self):
        f = self.fixture(old_history=True)
        _cm_git(f['checkout'], 'fetch', '--no-tags', '--no-recurse-submodules',
                '--deepen=24', 'origin', f['tested'])
        self.assertEqual(_cm_git(f['checkout'], 'rev-parse', '--is-shallow-repository'), 'true')
        before = set(_cm_git(f['checkout'], 'rev-list', 'HEAD').splitlines())
        before_base = _cm_git(f['checkout'], 'merge-base', *f['parents'])
        self.assertEqual(_cm_prepare(f), f['canonical'])
        after = set(_cm_git(f['checkout'], 'rev-list', 'HEAD').splitlines())
        self.assertLessEqual(before, after)
        self.assertEqual(_cm_git(f['checkout'], 'merge-base', *f['parents']), before_base)
        self.assert_head(f)
        self.assert_fetch_contract(f)
        self.assertEqual(len(f['fetches']), 1)

    def test_first_fetched_tip_remains_pinned_when_remote_main_moves(self):
        f = self.fixture()
        moved = []

        def move(phase, fixture, command, count):
            if phase == 'after' and count == 1:
                moved.append(_cm_commit(fixture['source'], 'main.txt', 'later main\n', 'main moves'))

        self.assertEqual(_cm_prepare(f, hook=move), f['canonical'])
        self.assertNotEqual(moved[0], f['canonical'])
        self.assertEqual(_cm_git(f['source'], 'rev-parse', 'main'), moved[0])
        self.assertEqual(_cm_git(f['checkout'], 'rev-parse', 'origin/main'), f['canonical'])
        self.assertGreater(len(f['fetches']), 1)
        self.assert_fetch_contract(f)
        self.assert_head(f)

    def test_failed_named_acquisition_is_terminal_despite_stale_origin_main(self):
        for failure in ('missing-remote', 'missing-main'):
            with self.subTest(failure=failure):
                f = self.fixture()
                _cm_git(f['checkout'], 'update-ref', 'refs/remotes/origin/main', f['tested'])
                if failure == 'missing-remote':
                    _cm_git(f['checkout'], 'remote', 'set-url', 'origin',
                            (f['source'].parent / 'absent.git').as_uri())
                else:
                    _cm_git(f['source'], 'update-ref', '-d', 'refs/heads/main')
                with self.assertRaises((RuntimeError, _cm_subprocess.CalledProcessError)):
                    _cm_prepare(f)
                self.assertEqual(len(f['fetches']), 1)
                self.assert_head(f)

    def test_later_nonzero_fetch_is_terminal_and_does_not_repin(self):
        f = self.fixture()

        def break_remote(phase, fixture, command, count):
            if phase == 'after' and count == 1:
                _cm_git(fixture['checkout'], 'remote', 'set-url', 'origin',
                        (fixture['source'].parent / 'absent-after-first.git').as_uri())

        with self.assertRaises((RuntimeError, _cm_subprocess.CalledProcessError)):
            _cm_prepare(f, hook=break_remote)
        self.assertEqual(len(f['fetches']), 2)
        self.assert_fetch_contract(f)
        self.assert_head(f)

    def test_unknown_fetch_settlement_is_terminal(self):
        f = self.fixture()

        def unknown(phase, fixture, command, count):
            # This command really completed; the injected lost-settlement signal
            # must still prohibit the helper from launching another acquisition.
            if phase == 'after' and count == 1:
                raise OSError('fixture: acquisition settlement unavailable')

        with self.assertRaises((OSError, RuntimeError)):
            _cm_prepare(f, hook=unknown)
        self.assertEqual(len(f['fetches']), 1)
        self.assert_head(f)

    def test_shallow_remote_cap_exhausts_completed_fetch_ladder(self):
        f = self.fixture(shallow_remote=True)
        self.assertEqual(_cm_git(f['remote'], 'rev-parse', '--is-shallow-repository'), 'true')
        with self.assertRaises(RuntimeError):
            _cm_prepare(f)
        self.assertEqual(len(f['fetches']), 6)
        self.assert_fetch_contract(f)
        self.assert_head(f)

    def test_nonshallow_unrelated_canonical_main_fails_without_ladder(self):
        f = self.fixture(full_checkout=True)
        _cm_git(f['source'], 'switch', '--orphan', 'unrelated')
        unrelated = _cm_commit(f['source'], 'unrelated.txt', 'unrelated\n', 'unrelated root')
        _cm_git(f['source'], 'update-ref', 'refs/heads/main', unrelated)
        self.assertEqual(_cm_git(f['checkout'], 'rev-parse', '--is-shallow-repository'), 'false')
        with self.assertRaises(RuntimeError):
            _cm_prepare(f)
        self.assertLessEqual(len(f['fetches']), 1)
        self.assert_head(f)

    def test_wrong_tested_head_and_wrong_base_fail_before_fetch(self):
        for option in ('head', 'base', 'malformed-sha'):
            with self.subTest(option=option):
                f = self.fixture()
                kwargs = ({'tested': f['canonical']} if option == 'head' else
                          {'tested': 'not-an-exact-sha'} if option == 'malformed-sha' else
                          {'base_ref': 'feature'})
                with self.assertRaises(RuntimeError):
                    _cm_prepare(f, **kwargs)
                self.assertEqual(f['fetches'], [])
                self.assert_head(f)

    def test_mutated_head_ref_or_fetch_head_fails_after_actual_fetch(self):
        for mutation in ('head', 'origin-main', 'fetch-head'):
            with self.subTest(mutation=mutation):
                f = self.fixture()

                def mutate(phase, fixture, command, count):
                    if phase != 'after' or count != 1:
                        return
                    if mutation == 'head':
                        _cm_git(fixture['checkout'], 'update-ref', 'HEAD', fixture['parents'][0])
                    elif mutation == 'origin-main':
                        _cm_git(fixture['checkout'], 'update-ref', 'refs/remotes/origin/main', fixture['tested'])
                    else:
                        (fixture['checkout'] / '.git' / 'FETCH_HEAD').write_text(
                            fixture['tested'] + '\t\tfixture wrong binding\n', encoding='utf-8')

                with self.assertRaises(RuntimeError):
                    _cm_prepare(f, hook=mutate)
                self.assertEqual(len(f['fetches']), 1)

    def test_original_frozen_file_guard_passes_unchanged_and_rejects_change(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                f = self.fixture(changed_frozen=changed)
                self.assertEqual(_cm_prepare(f), f['canonical'])
                guards = _cm_frozen_namespace(f['checkout'])
                self.assertEqual(guards['_frozen_base'](), f['parents'][0])
                guard = guards['test_frozen_files_unchanged_vs_origin_main']
                for path in _CM_FROZEN_PATHS:
                    if changed and path == _CM_FROZEN_PATHS[0]:
                        with self.assertRaisesRegex(AssertionError, 'changed vs merge-base'):
                            guard(path)
                    else:
                        guard(path)
                self.assert_head(f)
