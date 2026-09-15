"""Nightly reachability guard for the system-wide AI Daily Brief.

2026-09-15 production evidence (daily run 34957877090) showed the regional/desk
parallel barrier running for more than three hours.  The engine job hit its 300m
cap before the downstream ``master brain`` and ``AI Daily Brief page`` steps, so
``site/master_brief.json`` remained stale even though the macro regime source had
advanced.  A resilient producer is only useful if the workflow can reach it.

This suite pins the narrow failure-domain repair: the regional band is bounded and
its timeout is non-fatal, while the canonical master_brain/build_aibrief tail stays
after that band.  It does not create a second scheduler or a second brief producer.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / ".github" / "workflows" / "daily.yml"
REGIONAL = "regional + desk builders (parallelised — independent clusters, barrier before the hub)"
MASTER = "master brain (multi-lens LLM synthesis; default-off, resilient)"
AIBRIEF = "AI Daily Brief page (build_aibrief)"
MAX_REGIONAL_MIN = 60


def _engine_steps() -> list[dict]:
    workflow = yaml.safe_load(DAILY.read_text(encoding="utf-8"))
    return workflow["jobs"]["engine"]["steps"]


def _step(name: str) -> dict:
    return next(s for s in _engine_steps() if s.get("name") == name)


def test_regional_barrier_is_bounded_and_non_fatal() -> None:
    step = _step(REGIONAL)
    timeout = step.get("timeout-minutes")
    assert isinstance(timeout, int), "regional builder barrier must declare timeout-minutes"
    assert 1 <= timeout <= MAX_REGIONAL_MIN, (
        f"regional barrier timeout={timeout}m can starve the AI brief tail again; "
        f"keep it <= {MAX_REGIONAL_MIN}m or re-budget the engine job from measured runs"
    )
    assert step.get("continue-on-error") is True, (
        "regional barrier timeout must be non-fatal so master_brain/build_aibrief still run"
    )


def test_ai_brief_tail_remains_reachable_after_regional_barrier() -> None:
    steps = _engine_steps()
    names = [s.get("name", "") for s in steps]
    regional = names.index(REGIONAL)
    master = names.index(MASTER)
    aibrief = names.index(AIBRIEF)
    assert regional < master < aibrief, (
        "canonical order must remain regional inputs -> master_brain synthesis -> aibrief render"
    )


def test_canonical_brief_commands_are_unchanged() -> None:
    master = _step(MASTER)
    aibrief = _step(AIBRIEF)
    assert "python -m engine.master_brain" in (master.get("run") or "")
    assert "python -m scripts.build_aibrief" in (aibrief.get("run") or "")
