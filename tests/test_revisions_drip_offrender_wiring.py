"""daily.yml wiring: the revisions drip is a collect_tail accrual step, off the engine render path.

macro #7646 root cause (2026-11-07). The engine job must tell build_site that collect_tail
owns the drip (``MACRO_REVISIONS_DRIP=collect_tail``), and collect_tail must run the
collector's CLI bare, step-bounded, after the budgeted scorers and before the commit — the
same starvation defenses the earnings sweep carries (tests/test_earnings_sweep_entrypoint.py).

stdlib + pyyaml only: reads the workflow text, imports no builder or collector.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DAILY = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
_WF = yaml.safe_load(DAILY)

DRIP_STEP = "analyst revisions drip"
_BARE_CLI = re.compile(r"python -m collectors\.equity_revisions\s*(\\\s*)?\|\|")
_DEADLINE = re.compile(
    r"job_deadline=\$\(\(\s*start\s*\+\s*\(\s*(\d+)\s*-\s*(\d+)\s*\)\s*\*\s*60\s*\)\)"
)
_STEP_BUDGET = re.compile(r"step_deadline=\$\(\(\s*now\s*\+\s*(\d+)\s*\*\s*60\s*\)\)")
_EXPORT_MIN = re.compile(
    r"export MACRO_REVISIONS_DEADLINE_EPOCH=\$\(\(\s*job_deadline\s*<\s*step_deadline\s*\?\s*job_deadline\s*:\s*step_deadline\s*\)\)"
)
_START_STAMP = 'stamp="${RUNNER_TEMP}/nightly-timings-${GITHUB_RUN_ID}-${GITHUB_JOB}-start"'


def _steps(job: str) -> list[dict]:
    return _WF["jobs"][job]["steps"]


def _step_index(steps: list[dict], fragment: str):
    for i, s in enumerate(steps):
        if fragment in (s.get("name") or ""):
            return i, s
    raise AssertionError(f"no step named like {fragment!r}")


def test_engine_job_hands_the_drip_to_collect_tail():
    env = _WF["jobs"]["engine"].get("env") or {}
    assert env.get("MACRO_REVISIONS_DRIP") == "collect_tail", (
        "the engine job must set MACRO_REVISIONS_DRIP=collect_tail at JOB level so build_site "
        "(inside the regime-dashboard step) reads the committed parquet instead of dripping "
        "~100 min of yfinance on the render path"
    )
    for s in _steps("engine"):
        assert "collectors.equity_revisions" not in (s.get("run") or ""), (
            f"engine step {s.get('name')!r} invokes the drip directly"
        )


def test_collect_tail_runs_the_drip_bare_bounded_and_before_the_commit():
    steps = _steps("collect_tail")
    i_drip, drip = _step_index(steps, DRIP_STEP)
    run = drip.get("run") or ""
    assert _BARE_CLI.search(run), (
        "collect_tail must invoke `python -m collectors.equity_revisions` BARE — an argv "
        "overrides the nightly config cap (equity_profile.per_build)"
    )
    assert drip.get("timeout-minutes"), "the drip needs a step timeout — unbounded network"
    assert drip.get("continue-on-error") is True, (
        "a step timeout without continue-on-error fails the job and skips the commit"
    )
    job = _WF["jobs"]["collect_tail"]
    assert drip["timeout-minutes"] <= job["timeout-minutes"] - 60, (
        f"drip bound {drip['timeout-minutes']}m leaves <60m of the job's "
        f"{job['timeout-minutes']}m for the organs and the commit"
    )
    i_w4, _ = _step_index(steps, "W4 PIT-correct scorer")
    i_commit, _ = _step_index(steps, "commit tail data")
    assert i_w4 < i_drip < i_commit, (
        f"order W4={i_w4} drip={i_drip} commit={i_commit} — the drip is the one expensive "
        "accrual step and must sit LAST before the commit so a blowout truncates only itself"
    )


def test_the_drip_gets_a_wall_clock_deadline_from_the_job_cap():
    """The earlier step bounds already sum past the 200-min job cap on paper; the
    cap comment says the STEP bounds guarantee the commit. So the drip must stop
    by wall clock: job start (W2 stamp) + cap − a commit reserve of ≥20 min."""
    steps = _steps("collect_tail")
    _, drip = _step_index(steps, DRIP_STEP)
    run = drip.get("run") or ""
    assert _START_STAMP in run, "the deadline must be derived from the W2 job-start stamp"
    assert 'cat "$stamp"' in run and "::warning::" in run.split("job_deadline=")[0], (
        "a missing stamp must be loud (::warning) and fall back to now, never silent"
    )
    m = _DEADLINE.search(run)
    assert m, "the drip must compute job_deadline=$(( start + (CAP - RESERVE) * 60 ))"
    cap, reserve = int(m.group(1)), int(m.group(2))
    job_cap = _WF["jobs"]["collect_tail"]["timeout-minutes"]
    assert cap == job_cap, f"deadline arithmetic uses cap {cap} but the job cap is {job_cap}"
    assert reserve >= 20, f"commit reserve {reserve}m is too thin for the tail commit + push"
    i_stamp, _ = _step_index(steps, "timings — job start mark")
    assert i_stamp == 0, "the job-start stamp must be the job's first step"


def test_the_drip_stops_itself_under_its_own_step_bound():
    """GitHub's step-timeout cancel signals the step's bash, not the python child,
    so the collector cannot rely on a signal to flush. The step hands it a
    self-budget deadline BELOW timeout-minutes so the normal stop is the
    collector's own clock (flushed in its finally), and exports the EARLIER of
    the job-cap deadline and the self-budget."""
    _, drip = _step_index(_steps("collect_tail"), DRIP_STEP)
    run = drip.get("run") or ""
    m = _STEP_BUDGET.search(run)
    assert m, "the drip must compute step_deadline=$(( now + BUDGET * 60 ))"
    budget = int(m.group(1))
    assert budget < drip["timeout-minutes"], (
        f"self-budget {budget}m must be strictly under the step bound {drip['timeout-minutes']}m"
    )
    assert drip["timeout-minutes"] - budget <= 10, (
        "the step bound is a backstop; keep it within 10 min of the self-budget so the "
        "budget comment's arithmetic stays honest"
    )
    assert _EXPORT_MIN.search(run), (
        "MACRO_REVISIONS_DEADLINE_EPOCH must be the EARLIER of job_deadline and step_deadline"
    )


def test_the_drip_has_its_own_timings_band():
    steps = _steps("collect_tail")
    i_band, band = _step_index(steps, "timings band — revisions-drip")
    i_drip, _ = _step_index(steps, DRIP_STEP)
    assert "--band revisions-drip" in (band.get("run") or "")
    assert i_band == i_drip - 1, "the band mark must immediately precede the drip step"


def test_collect_tail_commit_covers_the_revisions_store():
    _, commit = _step_index(_steps("collect_tail"), "commit tail data")
    assert "git add data/" in (commit.get("run") or ""), (
        "data/revisions/ rides the broad `git add data/` — if that narrows, add the path"
    )
