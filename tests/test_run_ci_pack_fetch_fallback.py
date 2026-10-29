"""The fetch-depth-0 emulation acquires only the tested ancestry consumers need.

The healthy path must not enumerate the repository's branch/tag namespace or
walk all history. It deepens the authoritative tested tree through a bounded
ladder until the synthetic merge exposes both parents and their merge base.
Current consumers then fetch their canonical base themselves.

If exact tested-tree ancestry cannot be established, the established recovery
ladder remains available: all branches -> main only -> a 30-day main window.
Every current fetch-depth-0 consumer is pinned here so a future job cannot
silently depend on the removed full-remote side effect.
"""
from __future__ import annotations

import ast
import copy
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import run_ci_pack


TESTED_TREE_SHA = "0" * 40
MANIFEST = Path(__file__).parents[1] / ".github" / "ci" / "legacy-jobs.yml"
EXPECTED_FETCH_DEPTH_ZERO_CONSUMERS = {
    "board-contradictions",
    "signal-gate-pair-coherence",
    "ruling-graph",
    "design-governance",
    "p0b-receipt-closure",
    "self-mod-fence",
    # W2F #9949 (2026-10-22): the frozen-file guard in tests/test_intl_gs_foundation.py
    # compares against origin/<base_ref>, which this job fetches in its own fail-closed step.
    "international-workspace-browser",
}


def _fetch_depth_zero_job() -> run_ci_pack.LegacyJob:
    return run_ci_pack.LegacyJob(
        job_id="design-governance",
        definition={
            "steps": [
                {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
            ]
        },
        ordinal=0,
        weight=1,
    )


def test_exact_tree_stops_at_depth_two_when_missing_ancestry_becomes_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    readiness = iter([False, True])

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_ci_pack,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: next(readiness),
    )
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert calls == [
        [
            "git",
            "fetch",
            "--no-recurse-submodules",
            "--no-tags",
            "--depth=2",
            "origin",
            TESTED_TREE_SHA,
        ]
    ]


def test_exact_tree_deepens_only_until_merge_ancestry_is_ready(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []
    readiness = iter([False, False, True])

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_ci_pack,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: next(readiness),
    )
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )

    assert len(calls) == 2
    assert "--depth=2" in calls[0]
    assert "--depth=8" in calls[1]
    assert all("--tags" not in call for call in calls)
    assert all("+refs/heads/*:refs/remotes/origin/*" not in call for call in calls)
    out = capsys.readouterr().out
    assert "ancestry incomplete at depth 2; deepening to 8" in out


def test_exact_tree_transport_failure_enters_legacy_all_branches_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []
    readiness = iter([False])

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if cmd[-1] == TESTED_TREE_SHA:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_ci_pack,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: next(readiness),
    )
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 2
    assert "--depth=2" in calls[0]
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[1]
    out = capsys.readouterr().out
    assert "ancestry fetch failed at depth 2" in out


def test_incomplete_exact_ancestry_through_bound_enters_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_ci_pack,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: False,
    )
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )

    depths = list(run_ci_pack._EXACT_TESTED_TREE_DEPTHS)
    assert len(calls) == len(depths) + 1
    for call, depth in zip(calls[:-1], depths, strict=True):
        assert f"--depth={depth}" in call
        assert call[-1] == TESTED_TREE_SHA
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[-1]
    out = capsys.readouterr().out
    assert f"ancestry remained incomplete through depth {depths[-1]}" in out


def test_deepen_falls_back_to_main_when_exact_and_all_branches_fetch_fail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if cmd[-1] == TESTED_TREE_SHA:
            raise subprocess.CalledProcessError(1, cmd)
        if "+refs/heads/*:refs/remotes/origin/*" in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(run_ci_pack, "_tested_tree_ancestry_ready", lambda *_: False)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 3
    assert "--depth=2" in calls[0]
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[1]
    assert "+refs/heads/main:refs/remotes/origin/main" in calls[2]
    assert "--depth=2147483647" in calls[2]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 2


def test_deepen_falls_back_to_shallow_window_when_main_deepen_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if "--shallow-since=30 days ago" in cmd:
            return subprocess.CompletedProcess(cmd, 0)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(run_ci_pack, "_tested_tree_ancestry_ready", lambda *_: False)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 4
    assert "--depth=2" in calls[0]
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[1]
    assert "+refs/heads/main:refs/remotes/origin/main" in calls[2]
    assert "--shallow-since=30 days ago" in calls[3]
    assert "--tags" not in calls[3]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 3


def test_deepen_raises_when_every_recovery_rung_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(run_ci_pack, "_tested_tree_ancestry_ready", lambda *_: False)
    with pytest.raises(subprocess.CalledProcessError):
        run_ci_pack._prepare_provided_actions(
            _fetch_depth_zero_job(),
            root=Path.cwd(),
            tested_tree_sha=TESTED_TREE_SHA,
        )
    assert len(calls) == 4


_INTERNATIONAL_CANONICAL_STEP = 'canonical base for the frozen-file guard (fail closed)'
_INTERNATIONAL_CANONICAL_PYTHON = '''\
import os
from pathlib import Path
from scripts.run_ci_pack import prepare_canonical_main

prepare_canonical_main(
    Path.cwd(),
    tested_tree_sha=os.environ.get("CI_TESTED_TREE_SHA") or os.environ["TESTED_TREE_SHA"],
    base_ref="${{ github.base_ref || 'main' }}",
)
'''


def _assert_international_canonical_fetch(definition: dict[str, object]) -> None:
    """Pin the required gate, its uncaught helper call, and its shell envelope."""
    gates = [step for step in definition.get('steps', [])
             if isinstance(step, dict) and step.get('name') == _INTERNATIONAL_CANONICAL_STEP]
    assert len(gates) == 1, 'International must have exactly one named canonical gate'
    gate = gates[0]
    steps = definition['steps']
    frozen_steps = [index for index, step in enumerate(steps)
                    if isinstance(step, dict) and
                    'test_intl_gs_foundation.py' in str(step.get('run', ''))]
    assert len(frozen_steps) == 1 and steps.index(gate) < frozen_steps[0], (
        'International canonical gate must precede its frozen-file test'
    )
    assert set(gate) == {'name', 'run'}, 'International canonical gate must run unconditionally'
    assert isinstance(gate['run'], str), 'International canonical gate must be a script'
    lines = gate['run'].splitlines()
    assert len(lines) >= 3, 'International canonical fetch must be a Python heredoc'
    assert lines[0] == "python - <<'PY'", 'International helper must run directly'
    assert lines[-1] == 'PY', 'International helper must have no trailing shell commands'
    try:
        actual = ast.parse('\n'.join(lines[1:-1]))
    except SyntaxError as error:
        raise AssertionError('International canonical gate must be valid Python') from error
    expected = ast.parse(_INTERNATIONAL_CANONICAL_PYTHON)
    assert ast.dump(actual, include_attributes=False) == ast.dump(
        expected, include_attributes=False,
    ), 'International must invoke the exact canonical-main helper without swallowing failure'


def test_fetch_depth_zero_consumers_own_the_narrow_history_contract() -> None:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    consumers: dict[str, dict[str, object]] = {}
    for job_id, definition in payload["jobs"].items():
        steps = definition.get("steps", [])
        if any(
            step.get("uses") == "actions/checkout@v4"
            and step.get("with", {}).get("fetch-depth") == 0
            for step in steps
            if isinstance(step, dict)
        ):
            consumers[job_id] = definition

    assert set(consumers) == EXPECTED_FETCH_DEPTH_ZERO_CONSUMERS

    for job_id, definition in consumers.items():
        runs = [
            str(step["run"])
            for step in definition.get("steps", [])
            if isinstance(step, dict) and "run" in step
        ]
        if job_id == "international-workspace-browser":
            _assert_international_canonical_fetch(definition)
        else:
            assert any(
                "git fetch origin " in run and "github.base_ref" in run for run in runs
            ), f"{job_id} must fetch its canonical base explicitly"

        # The exact single-base destination is permitted; arbitrary remote
        # namespace enumeration remains forbidden.
        command_surface = "\n".join(runs).replace(
            "refs/remotes/origin/$base_ref", "<exact-base-destination>"
        ).replace("--no-tags", "<tags-disabled>")
        for forbidden in (
            "--tags",
            "refs/tags/",
            "refs/remotes/",
            "+refs/heads/*",
            "git branch -r",
            "git for-each-ref",
        ):
            assert forbidden not in command_surface, (
                f"{job_id} depends on unrelated remote namespace via {forbidden!r}"
            )


@pytest.fixture(scope="module")
def international_canonical_definition() -> dict[str, object]:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return payload["jobs"]["international-workspace-browser"]


def _international_contract_mutation(definition: dict[str, object], case: str) -> dict[str, object]:
    """Mutate actual manifest data; do not manufacture a successful gate."""
    changed = copy.deepcopy(definition)
    gate = next(step for step in changed['steps']
                if isinstance(step, dict) and step.get('name') == _INTERNATIONAL_CANONICAL_STEP)
    if case == 'missing-gate':
        changed['steps'].remove(gate)
    elif case == 'renamed-gate':
        gate['name'] += ' renamed'
    elif case == 'duplicate-gate':
        changed['steps'].append(copy.deepcopy(gate))
    elif case == 'gate-after-tests':
        changed['steps'].remove(gate)
        changed['steps'].append(gate)
    elif case == 'conditional-gate':
        gate['if'] = '${{ false }}'
    elif case == 'continue-on-error':
        gate['continue-on-error'] = True
    else:
        run = gate['run']
        if case == 'missing-import':
            run = run.replace('from scripts.run_ci_pack import prepare_canonical_main\n', '')
        elif case == 'missing-call':
            body = run.splitlines()[1:-1]
            prefix = '\n'.join(body).split('\nprepare_canonical_main(', 1)[0]
            run = "python - <<'PY'\n" + prefix + '\nPY\n'
        elif case == 'wrong-import':
            run = run.replace('from scripts.run_ci_pack import', 'from scripts.ci_semantic_proof import')
        elif case == 'wrong-helper':
            run = run.replace('prepare_canonical_main', '_prepare_provided_actions')
        elif case == 'wrong-tested-identity':
            run = run.replace('"CI_TESTED_TREE_SHA"', '"GITHUB_SHA"')
        elif case == 'wrong-fallback-identity':
            run = run.replace('"TESTED_TREE_SHA"', '"GITHUB_SHA"')
        elif case == 'wrong-base':
            run = run.replace("github.base_ref || 'main'", "github.head_ref || 'main'")
        elif case == 'swallowed-exception':
            body = '\n'.join(run.splitlines()[1:-1])
            imports, call = body.split('\nprepare_canonical_main(', 1)
            call = 'prepare_canonical_main(' + call
            run = "python - <<'PY'\n" + imports + '\ntry:\n' + ''.join(
                '    ' + line + '\n' for line in call.splitlines()
            ) + 'except Exception:\n    pass\nPY\n'
        elif case == 'shell-or-true':
            run = run.replace("python - <<'PY'", "python - <<'PY' || true", 1)
        elif case == 'trailing-shell':
            run += 'true\n'
        else:
            raise AssertionError(f'unknown contract mutation: {case}')
        assert run != gate['run'], f'mutation {case} did not change actual manifest script'
        gate['run'] = run
    return changed


@pytest.mark.parametrize('case', [
    'missing-gate', 'renamed-gate', 'duplicate-gate', 'conditional-gate',
    'gate-after-tests', 'continue-on-error', 'missing-import', 'missing-call', 'wrong-import',
    'wrong-helper', 'wrong-tested-identity', 'wrong-fallback-identity',
    'wrong-base', 'swallowed-exception', 'shell-or-true', 'trailing-shell',
])
def test_international_canonical_fetch_rejects_contract_mutation(
    case: str, international_canonical_definition: dict[str, object],
) -> None:
    definition = _international_contract_mutation(international_canonical_definition, case)
    with pytest.raises(AssertionError):
        _assert_international_canonical_fetch(definition)


def test_complete_history_survives_multiple_consumers_without_refetching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later consumer must not re-shallow ancestry an earlier one proved."""
    remote = tmp_path / "remote.git"
    root = tmp_path / "candidate"
    isolated = tmp_path / "isolated"
    real_run = subprocess.run
    env = dict(run_ci_pack._trusted_git_environment(tmp_path))
    env.update(
        GIT_AUTHOR_NAME="CI fixture", GIT_AUTHOR_EMAIL="ci@example.invalid",
        GIT_COMMITTER_NAME="CI fixture", GIT_COMMITTER_EMAIL="ci@example.invalid",
    )

    def git(*args: str, cwd: Path = tmp_path, data: str | None = None) -> str:
        return real_run(
            ["git", *args], cwd=cwd, env=env, input=data, text=True,
            capture_output=True, check=True,
        ).stdout.strip()

    git("init", "--bare", str(remote))
    tree = git("mktree", cwd=remote, data="")
    base = git("commit-tree", tree, cwd=remote, data="base\n")
    parents = []
    for branch in ("left", "right"):
        parent = base
        for index in range(20):
            parent = git(
                "commit-tree", tree, "-p", parent, cwd=remote,
                data=f"{branch}-{index}\n",
            )
        parents.append(parent)
    tested = git(
        "commit-tree", tree, "-p", parents[0], "-p", parents[1],
        cwd=remote, data="tested merge\n",
    )
    git("update-ref", "refs/heads/main", tested, cwd=remote)
    git("symbolic-ref", "HEAD", "refs/heads/main", cwd=remote)
    for checkout in (root, isolated):
        git("clone", "--no-checkout", "--depth=2", remote.as_uri(), str(checkout))
    assert not run_ci_pack._tested_tree_ancestry_ready(root, env, tested)
    fetches = []

    def recording_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        if list(cmd[:2]) == ["git", "fetch"]:
            fetches.append((kwargs["cwd"], list(cmd)))
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", recording_run)
    job = _fetch_depth_zero_job()
    run_ci_pack._prepare_provided_actions(job, root=root, tested_tree_sha=tested)
    assert run_ci_pack._tested_tree_ancestry_ready(root, env, tested)
    first_fetches = list(fetches)
    assert first_fetches
    run_ci_pack._prepare_provided_actions(job, root=root, tested_tree_sha=tested)
    assert fetches == first_fetches
    assert run_ci_pack._tested_tree_ancestry_ready(root, env, tested)

    # Readiness belongs to this repository and tree, never a process-wide cache.
    assert not run_ci_pack._tested_tree_ancestry_ready(isolated, env, tested)
    run_ci_pack._prepare_provided_actions(job, root=isolated, tested_tree_sha=tested)
    assert len(fetches) > len(first_fetches)
    assert run_ci_pack._tested_tree_ancestry_ready(isolated, env, tested)
