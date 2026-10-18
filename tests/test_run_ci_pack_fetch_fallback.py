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


def test_exact_tree_stops_at_depth_two_when_ancestry_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_ci_pack,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: True,
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

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if cmd[-1] == TESTED_TREE_SHA:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    monkeypatch.setattr(
        run_ci_pack,
        "_tested_tree_ancestry_ready",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("readiness must not run after fetch failure")
        ),
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
