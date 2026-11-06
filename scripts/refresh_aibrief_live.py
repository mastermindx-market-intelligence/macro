"""Refresh AI Brief inside the existing independently locked VPS live lane.

No Git writes, frontend build, ledger emission or provider retry loop. One
private atomic envelope per lens contains last-good content, current facts and
attempt status. A killed/uncertain operation is held for original-owner
reconciliation; the next timer tick never silently reissues it.
"""
from __future__ import annotations

import copy
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.aibrief_live import (FILES, SCHEMA, content_id, evidence_usable, interval,
                             qualify_inputs, read_publication, safe_facts, utc, validate_brief)
from scripts.vps_live_orchestrator import TaskResult, atomic_write_json

log = logging.getLogger("aibrief_live")


def refresh_lens(root: Path, state_dir: Path, *, lens: str, now: datetime,
                 brain=None, prepare=None, generate=None, write=atomic_write_json) -> str:
    from engine import aibrief_runtime
    if brain is None:
        from engine import master_brain as brain
    prepare = prepare or aibrief_runtime.prepare
    generate = generate or aibrief_runtime.generate
    path = state_dir / f"aibrief-{lens}.json"
    prior, fallback = read_publication(root, state_dir, lens)
    if path.exists() and prior is None:
        # A corrupt/missing receipt may conceal dispatch. Do not replace it with
        # a blank state and launch another operation.
        return "publication_unreadable"
    envelope = copy.deepcopy(prior) if prior else {
        "schema": SCHEMA, "lens": lens, "sequence": 0, "last_good": fallback,
    }
    previous_attempt = envelope.get("attempt") or {}
    hold = envelope.get("hold") or {}

    def publish(state, reason, **extra):
        envelope["sequence"] += 1
        envelope["published_at"] = datetime.now(timezone.utc).isoformat()
        envelope["attempt"] = {
            **previous_attempt, "state": state, "reason": reason,
            "checked_at": now.isoformat(), **extra,
        }
        if state in ("running", "effect_unknown", "refused"):
            envelope["hold"] = {key: envelope["attempt"].get(key) for key in
                                ("state", "operation_id", "route_identity")}
        write(path, envelope)
        return state

    cfg = brain._cfg()
    if cfg.get("refresh_owner", "legacy") != "vps_live":
        return publish("disabled", "another_refresh_owner_selected")
    if not cfg.get("enabled", False) or lens not in (cfg.get("lenses") or FILES):
        # Disablement must not erase an uncertain original operation.
        return publish(previous_attempt.get("state") if previous_attempt.get("state") in (
            "running", "effect_unknown") else "disabled", "generation_disabled")
    try:
        state = brain.LENSES[lens]["state_fn"](root)
        primary = state.get(lens) if isinstance(state, dict) else None
        source_date = primary.get("date") if isinstance(primary, dict) else None
        state, manifest = qualify_inputs(state, lens=lens, now=now)
        digest = content_id(state)
        envelope["facts"] = {
            "state_asof": source_date, "input_digest": digest,
            "gathered_at": now.isoformat(),
            "key_facts": safe_facts(brain._key_facts_for(lens, state)) if lens in state else [],
            "sources": manifest,
        }
    except Exception:
        return publish(previous_attempt.get("state") if previous_attempt.get("state") in (
            "running", "effect_unknown") else "source_unavailable", "source_unavailable")
    if hold.get("state", previous_attempt.get("state")) in ("running", "effect_unknown"):
        return publish("effect_unknown", "original_operation_requires_reconciliation")
    if not evidence_usable(source_date, lens=lens, now=now):
        return publish("source_stale", "primary_evidence_not_current")
    last = envelope.get("last_good") or {}
    last_at = utc(last.get("generated_at"))
    cadence = interval(brain._interval_for(lens, cfg), lens=lens)
    if (validate_brief(last, lens=lens) and last_at and last_at <= now
            and now - last_at < timedelta(days=cadence)
            and last.get("state_asof") == source_date and last.get("input_digest") == digest):
        return publish("not_due", "cadence_not_due")
    if hold.get("state", previous_attempt.get("state")) == "refused":
        # A different model/configuration is not authorization to bypass a
        # refusal. Only the original owner can reconcile and release this hold.
        return publish("refused", "original_owner_refusal_requires_reconciliation")
    last_attempt = utc(previous_attempt.get("started_at"))
    if last_attempt and now - last_attempt < timedelta(hours=1):
        return publish("deferred", "refresh_budget_wait")
    try:
        prepared = prepare(root, cfg)
    except Exception:
        # No input credentials are read here; owner inspection can recover when
        # its installed source/selection/eligibility changes.
        return publish("unavailable", "fabric_route_unavailable")
    # Bound known-terminal retries to one per hour and three per unchanged input
    # + route. This is the consumer's refresh budget, never account/provider retry.
    same = (previous_attempt.get("input_digest") == digest
            and previous_attempt.get("route_identity") == prepared.identity)
    count = previous_attempt.get("attempt_count", 0) if same else 0
    if same and count >= 3:
        return publish(previous_attempt.get("state", "unavailable"), "refresh_budget_wait")
    operation_id = "aibrief:" + lens + ":" + uuid.uuid4().hex
    # Persistence BEFORE binding/dispatch: a crash, timeout or failed final write
    # leaves a durable original ID which blocks duplicate inference next tick.
    publish("running", "inference_started", operation_id=operation_id,
            started_at=now.isoformat(), finished_at=None, route_identity=prepared.identity,
            input_digest=digest, attempt_count=count + 1)
    previous_attempt = dict(envelope["attempt"])
    try:
        result = generate(state, cfg, lens=lens, root=root, operation_id=operation_id,
                          prepared=prepared, brain=brain)
    except Exception:
        return publish("effect_unknown", "inference_interrupted")
    brief = result.brief
    if (validate_brief(brief, lens=lens) and brief["state_asof"] == source_date
            and now - timedelta(minutes=5) <= utc(brief["generated_at"]) <= now + timedelta(minutes=10)):
        brief["refresh_days"] = cadence
        brief["key_facts"] = envelope["facts"]["key_facts"]
        brief["input_digest"] = digest
        envelope["last_good"] = brief
    elif result.state == "succeeded":
        envelope.pop("hold", None)
        return publish("unavailable", "invalid_output", finished_at=datetime.now(timezone.utc).isoformat())
    if result.state not in ("effect_unknown", "refused"):
        envelope.pop("hold", None)
    return publish(result.state, result.reason, finished_at=datetime.now(timezone.utc).isoformat(),
                   close_confirmed=result.close_confirmed)


def run(orchestrator) -> None:
    """The existing orchestrator owns lock, schedule, resource budget and health."""
    for lens in FILES:
        started = time.monotonic()
        try:
            result = refresh_lens(orchestrator.root if hasattr(orchestrator, "root") else
                                  Path(__file__).resolve().parents[1], orchestrator.state_dir,
                                  lens=lens, now=orchestrator.now)
        except Exception as exc:
            log.error("AI Brief %s publication failed (%s)", lens, type(exc).__name__)
            result = "publication_failed"
        orchestrator.results.append(TaskResult(
            name="aibrief_" + lens, status="ok" if result in ("succeeded", "not_due") else "error",
            elapsed_s=round(time.monotonic() - started, 3),
            returncode=0 if result in ("succeeded", "not_due") else 1, detail=result))
