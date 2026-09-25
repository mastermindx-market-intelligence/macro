"""The queued-job-hostage dead-man switch.

This guard exists because the SAME mechanism took production down twice and was
invisible both times: a job addressed to a self-hosted label that no online runner
carries sits `queued`, holds its concurrency group until GitHub's 24h kill, and
every firing behind it is superseded as `pending`. 2026-08-14→17 it was `theta-m1`
and the Prophet boards; 2026-09-23→25 it was `render-linux` and the render lanes,
with 1,479 committed site pages going stale behind it.

The fixtures below are the REAL run shapes from 2026-09-25, with constant
timestamps — a guard whose fixtures age is a scheduled red.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "check_runner_queue_hostage.py"
WORKFLOW = ROOT / ".github" / "workflows" / "nightly-liveness.yml"

NOW = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)
HOSTED = {"ubuntu-latest"}
VIEW = {
    "render-linux": {"status": "orphaned", "carried_by": []},
    "self-hosted": {"status": "live", "carried_by": ["pc-render-1"]},
    "macstudio": {"status": "live", "carried_by": ["mac-builder-5", "mac-builder-light"]},
}


@pytest.fixture(scope="module")
def guard():
    spec = importlib.util.spec_from_file_location("check_runner_queue_hostage", GUARD)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def job(**kw) -> dict:
    """Run 35989213316's job 107623716720 as the API actually returned it."""
    row = {
        "status": "queued",
        "runner_name": "",
        "labels": ["self-hosted", "render-linux"],
        "created_at": "2026-09-24T12:05:10Z",
        "name": "render",
        "run_id": 35989213316,
        "workflow_name": "render",
    }
    row.update(kw)
    return row


def test_selftest_passes() -> None:
    result = subprocess.run(
        ["python3", str(GUARD), "--selftest"], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_real_2026_09_25_hostage_is_a_breach(guard) -> None:
    report = guard.evaluate([job()], now=NOW, hosted=HOSTED, registry_view=VIEW)
    assert report["ok"] is False
    reason = report["fail_reasons"][0]
    assert "35989213316" in reason
    assert "render-linux" in reason
    # The message must carry the actionable half: how long, and what the registry
    # believes about the label. An alert that only says "something is queued" makes
    # the operator do the diagnosis this check already did.
    assert "19.9h" in reason, reason
    assert "orphaned" in reason, reason


def test_a_long_queue_behind_a_live_pool_is_not_a_breach(guard) -> None:
    """`macstudio` is a two-host pool shared by the nightly, closing-bell,
    asia-close and the close-pass backstop, so a job can honestly wait behind a
    multi-hour bake. Measured worst honest waits: daily.yml 1h12m-2h31m, a scope=all
    render 40-85m. Alarming on those trains the operator to ignore the channel."""
    waited = job(created_at="2026-09-25T05:00:00Z", labels=["self-hosted", "macstudio"])
    assert guard.evaluate([waited], now=NOW, hosted=HOSTED, registry_view=VIEW)["ok"] is True


def test_the_threshold_leaves_margin_before_githubs_24h_kill(guard) -> None:
    """The budget must page while the run can still be rescued. GitHub kills a
    queued self-hosted job at exactly 24h (run 35855143666: created
    2026-09-23T12:05:09Z, cancelled 2026-09-24T12:05:09Z), and this lane looks three
    times a day, so threshold + 8h of look latency must still land well short."""
    assert guard.MAX_QUEUE <= timedelta(hours=12)
    assert guard.MAX_QUEUE + timedelta(hours=8) < timedelta(hours=24)


@pytest.mark.parametrize(
    ("kw", "why"),
    [
        ({"runner_name": "pc-render-1"}, "a runner is assigned — starting, not stuck"),
        ({"status": "in_progress"}, "running is not queued"),
        ({"status": "completed"}, "finished is not queued"),
        ({"labels": ["ubuntu-latest"]}, "hosted capacity backlogs are not this class"),
        ({"labels": []}, "no addressed labels to judge"),
    ],
)
def test_shapes_that_must_never_alarm(guard, kw: dict, why: str) -> None:
    assert guard.evaluate([job(**kw)], now=NOW, hosted=HOSTED)["ok"] is True, why


def test_blindness_is_indeterminate_never_a_breach(guard) -> None:
    """Verdict discipline, borrowed verbatim from check_nightly_liveness: an
    unparseable row is reported, not alarmed on. Only a POSITIVE observation of a
    job held past the budget fails."""
    report = guard.evaluate(
        [job(created_at=None, started_at=None), job(created_at="not-a-date")],
        now=NOW,
        hosted=HOSTED,
    )
    assert report["ok"] is True
    assert report["undated_rows"] == 2


def test_a_missing_registry_does_not_blind_the_check(guard, tmp_path: Path) -> None:
    """The registry is hand-maintained documentation and was WRONG during the very
    outage this guard is for, so the guard must never depend on it to reach a
    verdict — it falls back to hosted-label prefix families."""
    assert guard.load_hosted_labels(tmp_path / "absent.yml") is None
    assert guard.evaluate([job()], now=NOW, hosted=None)["ok"] is False
    assert guard.evaluate([job(labels=["ubuntu-latest"])], now=NOW, hosted=None)["ok"] is True


def test_the_age_filter_cannot_drop_a_hostage(guard) -> None:
    """`fetch_live_jobs` only expands runs older than the budget. That is exact, not
    a heuristic: a job's created_at can never precede its run's, so a younger run
    cannot hold a job queued past the budget. Measured 2026-09-25 it cut 32 live
    runs to 3 and a look from ~34 REST calls to ~5, which matters on a 5,000/hr pool
    shared by the whole fleet."""
    assert guard.MAX_RUNS_INSPECTED >= 25
    old = {"id": 1, "created_at": "2026-09-24T12:00:00Z", "name": "render"}
    fresh = {"id": 2, "created_at": "2026-09-25T07:55:00Z", "name": "render"}
    cutoff = NOW - guard.MAX_QUEUE
    assert guard._parse_dt(old["created_at"]) <= cutoff
    assert guard._parse_dt(fresh["created_at"]) > cutoff


def test_the_watchdog_never_routes_to_the_pool_it_watches() -> None:
    """Load-bearing, not a cost choice: a check for "no runner can take this job"
    must not need a runner from the pool under test. It also may not be a step of
    the `liveness` job — that one grades daily.yml alone and stayed correctly silent
    through the whole render outage, because daily.yml routes a live label."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job_spec = document["jobs"]["queue-hostage"]
    assert job_spec["runs-on"] == "ubuntu-latest"
    assert document["permissions"]["actions"] == "read"
    steps = " ".join(str(step.get("run", "")) for step in job_spec["steps"])
    assert "check_runner_queue_hostage.py" in steps
    liveness = " ".join(str(s.get("run", "")) for s in document["jobs"]["liveness"]["steps"])
    assert "check_runner_queue_hostage.py" not in liveness


def test_the_workflow_checks_out_what_the_guard_reads() -> None:
    """A sparse-checkout omission does not turn this lane red — the guard degrades
    to prefix families and annotates itself blind. A forgotten path is therefore a
    SILENTLY degraded watchdog, which is the exact failure class it was written for
    (same reasoning as test_every_market_board_is_in_the_sparse_checkout)."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    checkout = next(
        step for step in document["jobs"]["queue-hostage"]["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout")
    )
    sparse = checkout["with"]["sparse-checkout"]
    for needed in ("scripts", ".github/runner-policy.yml"):
        assert needed in sparse, needed
