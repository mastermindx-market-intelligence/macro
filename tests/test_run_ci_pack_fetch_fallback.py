"""The fetch-depth-0 deepen must survive one broken sibling ref.

2026-09-21: the all-branches full-depth fetch in
``run_ci_pack._prepare_provided_actions`` began failing fleet-wide with
``fatal: missing blob object ...`` / ``error: remote did not send all
necessary objects`` — a sibling branch referenced objects the server could
not serve — and every design-governance job after it concluded
"infrastructure unknown". The checks behind that contract diff against main
and the PR's own refs, so the fallback narrows the deepen to
``refs/heads/main`` instead of failing the job.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import run_ci_pack


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


def test_deepen_falls_back_to_main_when_all_branches_fetch_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if "+refs/heads/*:refs/remotes/origin/*" in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha="0" * 40,
    )
    assert len(calls) == 2
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[0]
    assert "+refs/heads/main:refs/remotes/origin/main" in calls[1]
    assert "--depth=2147483647" in calls[1]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert warning_lines, out
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
        tested_tree_sha="0" * 40,
    )
    assert len(calls) == 3
    assert "--shallow-since=30 days ago" in calls[2]
    assert "+refs/heads/main:refs/remotes/origin/main" in calls[2]
    assert "--tags" not in calls[2]
    out = capsys.readouterr().out
    warning_lines = [line for line in out.splitlines() if "::warning" in line]
    assert len(warning_lines) == 2
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
            tested_tree_sha="0" * 40,
        )
    assert len(calls) == 3


def test_deepen_single_fetch_when_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(run_ci_pack.subprocess, "run", fake_run)
    run_ci_pack._prepare_provided_actions(
        _fetch_depth_zero_job(),
        root=Path.cwd(),
        tested_tree_sha="0" * 40,
    )
    assert len(calls) == 1
    assert "+refs/heads/*:refs/remotes/origin/*" in calls[0]
