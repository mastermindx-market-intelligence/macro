from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "trusted-ci-executor.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_trusted_pr_calls_use_native_fifo_admission_without_cancellation() -> None:
    document = _workflow()
    concurrency = document["concurrency"]

    assert concurrency["group"] == (
        "${{ github.event_name == 'pull_request' "
        "&& 'trusted-ci-executor-production-fifo' "
        "|| format('trusted-ci-executor-{0}', github.run_id) }}"
    )
    assert concurrency["queue"] == "max"
    assert concurrency["cancel-in-progress"] is False


def test_fifo_admission_preserves_three_runner_parallelism_and_route() -> None:
    trusted_pack = _workflow()["jobs"]["trusted-pack"]

    assert trusted_pack["strategy"]["max-parallel"] == 3
    assert trusted_pack["runs-on"] == {
        "group": "macro-home-canary",
        "labels": "ci-linux",
    }


def test_direct_diagnostics_remain_run_unique_not_in_production_fifo() -> None:
    group = _workflow()["concurrency"]["group"]

    assert "github.event_name == 'pull_request'" in group
    assert "github.run_id" in group
    assert "workflow_dispatch" not in group
