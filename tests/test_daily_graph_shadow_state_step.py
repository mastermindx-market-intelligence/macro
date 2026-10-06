"""Pin the gate #8 graph shadow-state step to daily.yml oracle_offrender (seat ruling G1-RC1).

The shadow is produced off-render, after the engine job committed fresh owner inputs,
as one bounded non-fatal step whose only output is the shadow file. It must never move
into the engine job (render budget) or onto the commit-engine-outputs / pages path.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DAILY = REPO / ".github" / "workflows" / "daily.yml"
DAG = REPO / "config" / "dag.yml"
STEP = "GMI graph shadow theme state (gate 8 — off-render, non-fatal)"
RUN = "python -m scripts.build_thematic_state --mode GRAPH_SHADOW_STATE"
SHADOW = "data/theme_graph/shadow_theme_state.v1.json"
TRIPWIRE = "Time Machine freshness tripwire (loud — the feed must advance daily)"
COMMIT = "commit oracle Time Machine feed + ratio lens"


def _jobs():
    return yaml.safe_load(DAILY.read_text(encoding="utf-8"))["jobs"]


def _names(job):
    return [step.get("name") for step in job.get("steps", [])]


def test_step_lives_only_in_oracle_offrender_between_tripwire_and_commit():
    jobs = _jobs()
    owners = [job_id for job_id, job in jobs.items() if STEP in _names(job)]
    assert owners == ["oracle_offrender"]
    job = jobs["oracle_offrender"]
    names = _names(job)
    assert names.count(STEP) == 1
    assert names.index(TRIPWIRE) < names.index(STEP) < names.index(COMMIT)
    assert job["needs"] == ["et_gate", "engine"]
    assert not any("oracle_offrender" in (other.get("needs") or []) for other in jobs.values())


def test_step_bounds_and_command():
    step = next(s for s in _jobs()["oracle_offrender"]["steps"] if s.get("name") == STEP)
    assert step["run"].strip() == RUN
    assert step["timeout-minutes"] == 8
    assert step["continue-on-error"] is True
    assert step["if"] == "needs.engine.result == 'success'"
    assert step["env"] == {"COLLECT_LANE": "nightly"}


def test_mode_runs_nowhere_else_and_engine_til_step_stays_legacy():
    jobs = _jobs()
    hits = [(job_id, step.get("name")) for job_id, job in jobs.items() for step in job.get("steps", [])
            if "GRAPH_SHADOW_STATE" in str(step.get("run", ""))]
    assert hits == [("oracle_offrender", STEP)]
    engine_runs = [str(step.get("run", "")) for step in jobs["engine"]["steps"]
                   if "scripts.build_thematic_state" in str(step.get("run", ""))]
    assert len(engine_runs) == 1
    assert "--mode" not in engine_runs[0]


def test_commit_step_adds_only_the_shadow_path_tolerantly():
    step = next(s for s in _jobs()["oracle_offrender"]["steps"] if s.get("name") == COMMIT)
    lines = [line.strip() for line in step["run"].splitlines()]
    assert f"git add {SHADOW} 2>/dev/null || true" in lines
    assert sum(SHADOW in line for line in lines) == 1


def test_dag_declares_the_step_in_the_oracle_lane():
    dag = yaml.safe_load(DAG.read_text(encoding="utf-8"))
    lane = next(lane for lane in dag["lanes"]
                if lane.get("workflow") == ".github/workflows/daily.yml" and lane.get("job") == "oracle_offrender")
    ids = [step.get("id") for step in lane["steps"]]
    assert ids.index("publish_oracle_panels") < ids.index("build_graph_shadow_theme_state")
    entry = lane["steps"][ids.index("build_graph_shadow_theme_state")]
    assert entry["module"] == "scripts.build_thematic_state"
