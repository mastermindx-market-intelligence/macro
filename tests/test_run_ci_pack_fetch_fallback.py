"""The fetch-depth-0 emulation acquires only the tested ancestry consumers need.

The healthy path must not enumerate the repository's branch/tag namespace or
walk all history. It deepens the authoritative tested tree through a bounded
ladder until the synthetic merge exposes both parents and their merge base.
Current consumers then fetch their canonical base themselves.

If exact tested-tree ancestry cannot be established within the finite ladder,
fail closed. A successful fetch cannot replace the readiness postcondition,
and unrelated branches/tags are not a recovery path. Every current consumer
is pinned so future jobs cannot silently depend on a full-remote side effect.
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
    # W3U: the frozen-seam guard in tests/test_intl_gs_dislocations_view.py
    # compares against origin/<base_ref>, fetched by this job's fail-closed step.
    "international-dislocation-explorer",
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


def test_exact_tree_transport_failure_stops_without_namespace_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        raise subprocess.CalledProcessError(128, cmd)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(run_ci_pack, "_tested_tree_ancestry_ready", lambda *_: False)
    with pytest.raises(subprocess.CalledProcessError) as error:
        run_ci_pack._prepare_provided_actions(
            _fetch_depth_zero_job(), root=Path.cwd(), tested_tree_sha=TESTED_TREE_SHA,
        )
    assert error.value.returncode == 128
    assert calls == [[
        "git", "fetch", "--no-recurse-submodules", "--no-tags", "--depth=2",
        "origin", TESTED_TREE_SHA,
    ]]


def test_successful_fetches_cannot_replace_required_exact_ancestry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(run_ci_pack, "_tested_tree_ancestry_ready", lambda *_: False)
    with pytest.raises(RuntimeError, match=TESTED_TREE_SHA + ".*depth 8192"):
        run_ci_pack._prepare_provided_actions(
            _fetch_depth_zero_job(), root=Path.cwd(), tested_tree_sha=TESTED_TREE_SHA,
        )
    assert calls == [[
        "git", "fetch", "--no-recurse-submodules", "--no-tags", f"--depth={depth}",
        "origin", TESTED_TREE_SHA,
    ] for depth in (2, 8, 32, 128, 512, 2048, 8192)]
    # Canonical-main acquisition retains its independently accepted bound.
    assert run_ci_pack._EXACT_TESTED_TREE_DEPTHS == (2, 8, 32, 128, 512, 2048)


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


_DISLOCATION_CANONICAL_PYTHON = '''\
import os
from pathlib import Path
from scripts.run_ci_pack import prepare_canonical_main

prepare_canonical_main(
    Path.cwd(),
    tested_tree_sha=os.environ.get("CI_TESTED_TREE_SHA") or os.environ["TESTED_TREE_SHA"],
    base_ref="${{ github.base_ref || 'main' }}",
    frozen_paths=(
        "templates/intl_workspace_surveillance.css",
        "lib/intl_surveillance_mount.py",
        "scripts/build_intl.py",
    ),
)
'''

# Jobs whose frozen-file guard compares against canonical main through the
# fail-closed helper: the test module the gate must precede and the exact
# helper invocation (the dislocation job names its own compared paths; F10).
_INTERNATIONAL_CANONICAL_JOBS = {
    "international-workspace-browser": (
        "test_intl_gs_foundation.py", _INTERNATIONAL_CANONICAL_PYTHON),
    "international-dislocation-explorer": (
        "test_intl_gs_dislocations_view.py", _DISLOCATION_CANONICAL_PYTHON),
}


def _assert_international_canonical_fetch(
    definition: dict[str, object],
    frozen_test: str = "test_intl_gs_foundation.py",
    expected_python: str = _INTERNATIONAL_CANONICAL_PYTHON,
) -> None:
    """Pin the required gate, its uncaught helper call, and its shell envelope."""
    gates = [step for step in definition.get('steps', [])
             if isinstance(step, dict) and step.get('name') == _INTERNATIONAL_CANONICAL_STEP]
    assert len(gates) == 1, 'International must have exactly one named canonical gate'
    gate = gates[0]
    steps = definition['steps']
    frozen_steps = [index for index, step in enumerate(steps)
                    if isinstance(step, dict) and
                    frozen_test in str(step.get('run', ''))]
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
    expected = ast.parse(expected_python)
    assert ast.dump(actual, include_attributes=False) == ast.dump(
        expected, include_attributes=False,
    ), 'International must invoke the exact canonical-main helper without swallowing failure'


def _assert_ruling_graph_exact_base_contract(definition: dict[str, object]) -> None:
    """Ruling-graph uses exact tested-tree ancestry instead of a moving fetch.

    A missing base must fail closed and never skip H1/H2/W1; the replay
    identity is distinct from PR-head first-parent and normal main baseline.
    """
    gates = [step for step in definition.get("steps", [])
             if isinstance(step, dict)
             and step.get("name") == "conflict checker (hard fail on new FDR family or privacy boundary violations)"]
    assert len(gates) == 1
    command = str(gates[0].get("run", ""))
    assert "git fetch" not in command
    required = (
        'head_sha="$(git rev-parse --verify HEAD)"',
        'git rev-list --parents -n 1 HEAD',
        'git rev-parse --verify \'HEAD^1\'',
        'CI_DISABLE_BASE_REPLAY',
        'CI_SEMANTIC_ROLE',
        'CI_TESTED_TREE_SHA',
        'CI_BASE_SHA',
        'TESTED_BASE_SHA',
        'GITHUB_EVENT_NAME',
        'workflow_dispatch',
        'TESTED_TREE_SHA',
        'git cat-file -e "${TESTED_BASE_SHA}^{commit}"',
        'git merge-base --is-ancestor "$TESTED_BASE_SHA" HEAD',
        'RULING_DIFF_BASE="$TESTED_BASE_SHA" python scripts/check_ruling_conflicts.py',
        '::error::ruling-graph',
        'head=$head_sha',
    )
    for evidence in required:
        assert evidence in command, f"ruling-graph missing exact-base fence: {evidence}"
    assert command.index("git cat-file -e") < command.index("python scripts/check_ruling_conflicts.py")
    assert command.index("git merge-base --is-ancestor") < command.index("python scripts/check_ruling_conflicts.py")


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
        if job_id in _INTERNATIONAL_CANONICAL_JOBS:
            _assert_international_canonical_fetch(
                definition, *_INTERNATIONAL_CANONICAL_JOBS[job_id])
        elif job_id == "ruling-graph":
            _assert_ruling_graph_exact_base_contract(definition)
        else:
            assert any(
                "git fetch origin " in run and "github.base_ref" in run for run in runs
            ), f"{job_id} must fetch its canonical base explicitly"

        command_surface = "\n".join(runs)
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


def test_exact_history_beyond_2048_preserves_subject_and_excludes_unrelated_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuinely divergent PR must deepen past the old bound without all refs."""
    remote = tmp_path / "remote.git"
    root = tmp_path / "candidate"
    real_run = subprocess.run
    env = dict(run_ci_pack._trusted_git_environment(tmp_path))

    def git(*args: str, cwd: Path = remote, data: str | None = None) -> str:
        return real_run(
            ["git", *args], cwd=cwd, env=env, input=data, text=True,
            capture_output=True, check=True,
        ).stdout.strip()

    git("init", "--bare", str(remote), cwd=tmp_path)
    stream = []
    next_mark = 1

    def blob(content: str) -> int:
        nonlocal next_mark
        mark = next_mark
        next_mark += 1
        stream.extend(["blob", f"mark :{mark}",
                       f"data {len(content.encode())}", content])
        return mark

    def commit(ref: str, message: str, parent: int | None = None,
               merge: int | None = None, files: tuple[str, ...] = ()) -> int:
        nonlocal next_mark
        mark = next_mark
        next_mark += 1
        stream.extend([
            f"commit {ref}", f"mark :{mark}",
            f"committer CI fixture <ci@example.invalid> {1700000000 + mark} +0000",
            f"data {len(message.encode())}", message,
        ])
        if parent is not None:
            stream.append(f"from :{parent}")
        if merge is not None:
            stream.append(f"merge :{merge}")
        stream.extend(files)
        stream.append("")
        return mark

    common_blob = blob("common fixture\n")
    feature_blob = blob("feature fixture\n")
    unrelated_blob = blob("unrelated object must remain absent\n")
    base_mark = commit("refs/heads/base", "base", files=(
        f"M 100644 :{common_blob} common.txt",))
    tips = []
    for branch in ("main", "feature"):
        parent = base_mark
        for index in range(2300):
            message = f"{branch}-{index}\n\nFixture-Trailer: {branch}-{index}"
            files = (f"M 100644 :{feature_blob} feature.txt",) if (
                branch == "feature" and index == 0) else ()
            parent = commit(f"refs/heads/{branch}", message, parent, files=files)
        tips.append(parent)
    commit("refs/heads/tested", "tested merge", tips[0], tips[1],
           files=(f"M 100644 :{feature_blob} feature.txt",))
    unrelated = commit("refs/heads/unrelated", "unrelated root", files=(
        f"M 100644 :{unrelated_blob} unrelated.txt",))
    stream.extend(["reset refs/tags/unrelated-tag", f"from :{unrelated}", ""])
    git("fast-import", "--quiet", data="\n".join(stream) + "\n")

    tested = git("rev-parse", "refs/heads/tested")
    parents = git("rev-list", "--parents", "-n", "1", tested).split()[1:]
    base = git("rev-parse", "refs/heads/base")
    expected_tree = git("rev-parse", f"{tested}^{{tree}}")
    unrelated_objects = [
        git("rev-parse", "refs/heads/unrelated"),
        git("rev-parse", "refs/heads/unrelated^{tree}"),
        git("rev-parse", "refs/heads/unrelated:unrelated.txt"),
    ]
    expected_paths = git("diff", "--name-only", parents[0], tested)
    expected_trailers = git("log", "--format=%B", f"{parents[0]}..{tested}")
    assert expected_paths == "feature.txt"
    assert expected_trailers.count("Fixture-Trailer: feature-") == 2300
    git("clone", "--no-checkout", "--single-branch", "--no-tags", "--depth=2",
        "--branch=tested", remote.as_uri(), str(root), cwd=tmp_path)
    assert git("rev-parse", "--is-shallow-repository", cwd=root) == "true"
    assert not (root / ".git/objects/info/alternates").exists()
    for oid in unrelated_objects:
        assert real_run(["git", "cat-file", "-e", oid], cwd=root,
                        env=env, capture_output=True).returncode != 0
    assert not run_ci_pack._tested_tree_ancestry_ready(root, env, tested)
    fetches = []

    def recording_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        if list(cmd[:2]) == ["git", "fetch"]:
            command = list(cmd)
            assert command[-2:] == ["origin", tested], "unrelated namespace acquisition"
            assert "--no-tags" in command and "--tags" not in command
            if "--depth=8192" in command:
                assert not run_ci_pack._tested_tree_ancestry_ready(root, env, tested)
            fetches.append(command)
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", recording_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(), root=root, tested_tree_sha=tested,
    )
    assert [next(arg for arg in call if arg.startswith("--depth="))
            for call in fetches] == [
        "--depth=2", "--depth=8", "--depth=32", "--depth=128",
        "--depth=512", "--depth=2048", "--depth=8192",
    ]
    assert git("rev-parse", "HEAD", cwd=root) == tested
    assert git("rev-parse", "HEAD^{tree}", cwd=root) == expected_tree
    assert git("rev-list", "--parents", "-n", "1", tested, cwd=root).split() == [
        tested, *parents]
    assert git("merge-base", *parents, cwd=root) == base
    assert git("diff", "--name-only", parents[0], tested, cwd=root) == expected_paths
    assert git("log", "--format=%B", f"{parents[0]}..{tested}", cwd=root) == expected_trailers
    assert git("show", f"{tested}:feature.txt", cwd=root) == "feature fixture"
    for oid in unrelated_objects:
        assert real_run(["git", "cat-file", "-e", oid], cwd=root,
                        env=env, capture_output=True).returncode != 0
    refs = git("for-each-ref", "--format=%(refname)", cwd=root)
    assert "unrelated" not in refs
    # A ready checkout must not need a reachable origin for the next consumer.
    git("remote", "set-url", "origin", (tmp_path / "absent.git").as_uri(), cwd=root)
    before = list(fetches)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(), root=root, tested_tree_sha=tested,
    )
    assert fetches == before


def test_disconnected_parent_histories_fail_after_successful_exact_fetches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transfer success cannot invent a common ancestor between two roots."""
    remote = tmp_path / "remote.git"
    root = tmp_path / "candidate"
    real_run = subprocess.run
    env = dict(run_ci_pack._trusted_git_environment(tmp_path))
    env.update(GIT_AUTHOR_NAME="CI fixture", GIT_AUTHOR_EMAIL="ci@example.invalid",
               GIT_COMMITTER_NAME="CI fixture", GIT_COMMITTER_EMAIL="ci@example.invalid")

    def git(*args: str, cwd: Path = remote, data: str | None = None) -> str:
        return real_run(["git", *args], cwd=cwd, env=env, input=data,
                        text=True, capture_output=True, check=True).stdout.strip()

    git("init", "--bare", str(remote), cwd=tmp_path)
    tree = git("mktree", data="")
    parents = [git("commit-tree", tree, data=name) for name in ("left", "right")]
    tested = git("commit-tree", tree, "-p", parents[0], "-p", parents[1], data="merge")
    git("update-ref", "refs/heads/main", tested)
    git("symbolic-ref", "HEAD", "refs/heads/main")
    git("clone", "--no-checkout", "--depth=1", remote.as_uri(), str(root), cwd=tmp_path)
    fetches = []

    def recording_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        if list(cmd[:2]) == ["git", "fetch"]:
            fetches.append(list(cmd))
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", recording_run)
    with pytest.raises(RuntimeError, match=tested + ".*depth 8192"):
        run_ci_pack._prepare_provided_actions(
            _fetch_depth_zero_job(), root=root, tested_tree_sha=tested,
        )
    assert len(fetches) == 7
    assert all(call[-2:] == ["origin", tested] and "--no-tags" in call for call in fetches)
    assert git("rev-parse", "HEAD", cwd=root) == tested
    assert not run_ci_pack._tested_tree_ancestry_ready(root, env, tested)
