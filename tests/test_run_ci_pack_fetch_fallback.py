"""The fetch-depth-0 deepen prefers the exact tested tree and fails closed.

The healthy path must not enumerate the repository's branch/tag namespace.
That keeps history acquisition bound to the authoritative tested tree instead
of paying for unrelated refs. If the exact-tree fetch cannot satisfy the
history contract, the established recovery ladder remains available:
all branches -> main only -> a 30-day main window.

The real manifest is also pinned here because this optimization removes the
incidental side effect of materializing unrelated refs/tags. Every current
fetch-depth-0 consumer must fetch its canonical base explicitly and must not
silently depend on the removed remote namespace.
"""
from __future__ import annotations

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


def test_deepen_single_exact_tree_fetch_when_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if "--is-shallow-repository" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="false\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 2
    assert calls[0] == [
        "git",
        "fetch",
        "--no-recurse-submodules",
        "--no-tags",
        "--depth=2147483647",
        "origin",
        TESTED_TREE_SHA,
    ]
    assert calls[1][-2:] == ["rev-parse", "--is-shallow-repository"]
    assert "--tags" not in calls[0]
    assert "+refs/heads/*:refs/remotes/origin/*" not in calls[0]


def test_exact_tree_success_that_remains_shallow_enters_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if "--is-shallow-repository" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="true\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 3
    assert calls[0][-1] == TESTED_TREE_SHA
    assert calls[1][-2:] == ["rev-parse", "--is-shallow-repository"]
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[2]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 1
    assert "exact tested-tree deepen remained shallow" in warning_lines[0]


def test_exact_tree_failure_enters_legacy_all_branches_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if cmd[-1] == TESTED_TREE_SHA:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 2
    assert calls[0][-1] == TESTED_TREE_SHA
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[1]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 1
    assert "exact tested-tree deepen failed" in warning_lines[0]


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
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 3
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[1]
    assert "+refs/heads/main:refs/remotes/origin/main" in calls[2]
    assert "--depth=2147483647" in calls[2]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 2
    assert all(line.startswith("::warning") for line in warning_lines)


def test_deepen_falls_back_to_shallow_window_when_main_deepen_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if "--depth=2147483647" in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha=TESTED_TREE_SHA,
    )
    assert len(calls) == 4
    assert "--shallow-since=30 days ago" in calls[3]
    assert "+refs/heads/main:refs/remotes/origin/main" in calls[3]
    assert "--tags" not in calls[3]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 3
    assert all(line.startswith("::warning") for line in warning_lines)


def test_deepen_raises_when_every_rung_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        run_ci_pack._prepare_provided_actions(
            _fetch_depth_zero_job(),
            root=Path.cwd(),
            tested_tree_sha=TESTED_TREE_SHA,
        )
    assert len(calls) == 4


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
