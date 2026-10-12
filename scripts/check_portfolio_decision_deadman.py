"""Read-only dead-man for the three active Mastermind paper-PM decision cycles.

``--collect`` runs on the authoritative VPS and reads only local GET endpoints.
It emits a closed snapshot with no holdings, prompts, provider error text,
credentials, account values, target weights, or fills. Evaluation runs off-host
and fails when a due decision cycle is stale, missing, semantically failed, or
no longer supported by a healthy scheduler/reasoning lane.

The monitor never starts a portfolio run, retries a job, writes state, or changes
positions. It is standard-library-only for GitHub-hosted monitoring.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

UTC = timezone.utc
SNAPSHOT_SCHEMA = "mastermind.portfolio_decision_deadman.snapshot.v1"
RESULT_SCHEMA = "mastermind.portfolio_decision_deadman.result.v1"
DEFAULT_BASE_URL = "http://127.0.0.1:8001"

_JOB_SPECS: dict[str, dict[str, Any]] = {
    "autonomous_daily": {"book": "autonomous"},
    "china_daily": {"book": "china"},
    "hk_daily": {"book": "hk"},
}
_HEALTH_FIELDS = (
    "status", "commit", "version", "paper_only", "reasoning_policy_ok",
    "scheduled_portfolio_reasoning_available",
    "scheduled_portfolio_reasoning_policy_ok", "scheduler_running",
    "scheduled_runtime_ok", "reasoning_primary",
)
_JOB_FIELDS = (
    "id", "next_run_time", "last_started", "last_finished", "last_status",
    "last_severity", "last_reason", "last_target_status",
)
_DECISION_FIELDS = (
    "asof", "settled_asof", "target_status", "decision_effective",
    "execution_evidence_status",
)
_FORBIDDEN_TARGETS = {"", "rejected_no_submission", "rejected_execution_error"}
_FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_COLLECTION_ERROR = re.compile(
    r"(?:scheduler_duplicate:(?:autonomous_daily|china_daily|hk_daily)"
    r"|decision_(?:identity|scope|payload|rows):(?:autonomous|china|hk))"
)


def _aware_utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _previous_weekday_schedule(next_run: datetime) -> datetime:
    """Previous Mon-Fri occurrence using the live scheduler's own UTC clock."""
    candidate = _aware_utc(next_run) - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def _parse_date(value: Any):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def build_snapshot(
    health: dict[str, Any],
    scheduler: dict[str, Any],
    decisions: dict[str, dict[str, Any]],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Return the strict, private-safe snapshot consumed by the off-host check."""
    safe_health = {key: health.get(key) for key in _HEALTH_FIELDS}
    collection_errors: list[str] = []

    safe_jobs: dict[str, dict[str, Any]] = {}
    rows = scheduler.get("jobs") if isinstance(scheduler, dict) else None
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            job_id = str(row.get("id") or "")
            if job_id not in _JOB_SPECS:
                continue
            if job_id in safe_jobs:
                collection_errors.append(f"scheduler_duplicate:{job_id}")
                continue
            safe_jobs[job_id] = {key: row.get(key) for key in _JOB_FIELDS}

    safe_decisions: dict[str, dict[str, Any]] = {}
    for spec in _JOB_SPECS.values():
        book = str(spec["book"])
        payload = decisions.get(book) if isinstance(decisions, dict) else None
        if not isinstance(payload, dict):
            collection_errors.append(f"decision_payload:{book}")
            payload = {}
        if payload.get("portfolio") != book:
            collection_errors.append(f"decision_identity:{book}")
        if payload.get("scope") != "mastermind_portfolio":
            collection_errors.append(f"decision_scope:{book}")
        decision_rows = payload.get("decisions")
        latest = (
            decision_rows[0]
            if isinstance(decision_rows, list)
            and decision_rows
            and isinstance(decision_rows[0], dict)
            else {}
        )
        if not latest:
            collection_errors.append(f"decision_rows:{book}")
        safe_decisions[book] = {key: latest.get(key) for key in _DECISION_FIELDS}

    return {
        "schema": SNAPSHOT_SCHEMA,
        "observed_at": _aware_utc(observed_at).isoformat(),
        "health": safe_health,
        "jobs": safe_jobs,
        "decisions": safe_decisions,
        "collection_errors": sorted(set(collection_errors)),
    }


def _get_json(
    base_url: str,
    path: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={"User-Agent": "Mastermind-Portfolio-Decision-Deadman/1.0"},
    )
    with opener(request, timeout=30) as response:
        status = int(getattr(response, "status", 200))
        if status != 200:
            raise RuntimeError(f"read endpoint returned HTTP {status}")
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise ValueError("read endpoint did not return a JSON object")
    return payload


def collect(
    *,
    base_url: str = DEFAULT_BASE_URL,
    opener: Callable[..., Any] = urllib.request.urlopen,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Collect a sanitized snapshot from the authoritative local read APIs."""
    health = _get_json(base_url, "/health", opener=opener)
    scheduler = _get_json(base_url, "/api/scheduler", opener=opener)
    decisions = {
        book: _get_json(
            base_url,
            f"/api/decisions?portfolio={book}&limit=5",
            opener=opener,
        )
        for book in ("autonomous", "china", "hk")
    }
    return build_snapshot(health, scheduler, decisions, observed_at=observed_at)


def _decision_failure(
    job_id: str,
    expected_date: str,
    job: dict[str, Any],
    decision: dict[str, Any],
) -> str | None:
    status = str(job.get("last_status") or "").strip().lower()
    reason = str(job.get("last_reason") or "").strip().lower()
    target = str(job.get("last_target_status") or "").strip().lower()
    severity = str(job.get("last_severity") or "").strip().upper()

    if status == "skip":
        if reason == "market_closed" and not target:
            if severity != "ADVISORY_ONLY":
                return f"{job_id}: skip severity mismatch ({severity or 'missing'})"
            return None
        return (
            f"{job_id}: unacceptable skip reason={reason or 'missing'} "
            f"target={target or 'missing'}"
        )

    if status == "error":
        return (
            f"{job_id}: last run failed reason={reason or 'missing'} "
            f"target={target or 'missing'}"
        )

    asof_date = _parse_date(decision.get("asof"))
    decision_target = str(decision.get("target_status") or "").strip().lower()
    settled_date = (
        _parse_date(decision.get("settled_asof"))
        if decision_target == "executed"
        else None
    )
    decision_clock = settled_date if decision_target == "executed" else asof_date
    if decision_clock is None:
        return f"{job_id}: decision date is missing or invalid"
    if decision_clock.isoformat() != expected_date:
        return (
            f"{job_id}: decision stale "
            f"(clock={decision_clock.isoformat()}, expected={expected_date})"
        )
    if target in _FORBIDDEN_TARGETS or decision_target in _FORBIDDEN_TARGETS:
        return (
            f"{job_id}: missing/failed decision target="
            f"{target or decision_target or 'missing'} reason={reason or 'missing'}"
        )

    if status == "ok":
        if severity:
            return f"{job_id}: ok run carried unexpected severity={severity}"
        if reason:
            return f"{job_id}: ok run carried unexpected reason={reason}"
        if target not in {"queued", "executed"}:
            return f"{job_id}: ok run has invalid target={target}"
        settled_transition = target == "queued" and decision_target == "executed"
        if target != decision_target and not settled_transition:
            return (
                f"{job_id}: scheduler/decision target mismatch "
                f"({target} != {decision_target})"
            )
        if decision.get("decision_effective") is not True:
            return f"{job_id}: {decision_target} decision is not effective"
        if decision_target == "queued":
            evidence = str(
                decision.get("execution_evidence_status") or ""
            ).strip().lower()
            if evidence not in {"", "none"}:
                return f"{job_id}: queued execution evidence is invalid ({evidence})"
            if str(decision.get("settled_asof") or "").strip():
                return f"{job_id}: queued settlement date must be absent"
        if decision_target == "executed":
            if decision.get("execution_evidence_status") != "receipt_verified":
                return f"{job_id}: executed decision lacks a verified execution receipt"
            if settled_date is None:
                return f"{job_id}: executed decision settled_asof is missing or invalid"
            if asof_date is None:
                return f"{job_id}: executed decision asof is missing or invalid"
            if settled_date < asof_date:
                return f"{job_id}: executed decision settled before decision acceptance"
        return None

    if status == "warn":
        if severity != "FREEZE":
            return f"{job_id}: warn severity mismatch ({severity or 'missing'})"
        if target != decision_target:
            return (
                f"{job_id}: scheduler/decision target mismatch "
                f"({target} != {decision_target})"
            )
        explicit_hold = (
            target.startswith("rejected_") or target.startswith("frozen_")
        )
        if not explicit_hold:
            return f"{job_id}: warn run has non-governed target={target}"
        if reason != target:
            return (
                f"{job_id}: governed target/reason mismatch "
                f"({target} != {reason or 'missing'})"
            )
        if decision.get("decision_effective") is not False:
            return f"{job_id}: governed hold must not be effective"
        return None

    return f"{job_id}: unsupported last_status={status or 'missing'}"


def evaluate(payload: dict[str, Any], *, now: datetime | None = None) -> list[str]:
    """Return closed human-readable failures; an empty list is healthy."""
    current = _aware_utc(now)
    failures: list[str] = []
    if not isinstance(payload, dict) or payload.get("schema") != SNAPSHOT_SCHEMA:
        return ["snapshot: missing or invalid schema"]

    observed = _parse_ts(payload.get("observed_at"))
    if observed is None:
        failures.append("snapshot: observed_at missing or invalid")
    else:
        age = current - observed
        if age > timedelta(minutes=10):
            failures.append(f"snapshot: stale by {age.total_seconds() / 60:.1f}m")
        elif age < -timedelta(minutes=5):
            failures.append("snapshot: observed_at is implausibly in the future")

    raw_collection_errors = payload.get("collection_errors", [])
    if not isinstance(raw_collection_errors, list):
        failures.append("collection: error list is invalid")
    else:
        for code in raw_collection_errors:
            if isinstance(code, str) and _COLLECTION_ERROR.fullmatch(code):
                failures.append(f"collection: {code}")
            else:
                failures.append("collection: invalid_error_code")

    health = payload.get("health")
    if not isinstance(health, dict):
        return failures + ["health: missing"]
    if health.get("status") != "ok":
        failures.append("health: status is not ok")
    commit = health.get("commit")
    if not isinstance(commit, str) or not commit:
        failures.append("health: release commit is missing")
    elif _FULL_GIT_SHA.fullmatch(commit) is None:
        failures.append("health: release commit is invalid")
    if health.get("paper_only") is not True:
        failures.append("health: paper_only safety is not true")
    for field in (
        "reasoning_policy_ok",
        "scheduled_portfolio_reasoning_available",
        "scheduled_portfolio_reasoning_policy_ok",
        "scheduler_running",
        "scheduled_runtime_ok",
    ):
        if health.get(field) is not True:
            failures.append(f"health: {field} is not true")

    jobs = payload.get("jobs")
    decisions = payload.get("decisions")
    if not isinstance(jobs, dict):
        failures.append("jobs: missing")
        jobs = {}
    if not isinstance(decisions, dict):
        failures.append("decisions: missing")
        decisions = {}

    for job_id, spec in _JOB_SPECS.items():
        book = str(spec["book"])
        job = jobs.get(job_id)
        if not isinstance(job, dict):
            failures.append(f"{job_id}: scheduler row missing")
            continue

        next_run = _parse_ts(job.get("next_run_time"))
        started = _parse_ts(job.get("last_started"))
        finished = _parse_ts(job.get("last_finished"))
        if next_run is None:
            failures.append(f"{job_id}: next_run_time missing or invalid")
            continue
        if next_run <= current:
            failures.append(
                f"{job_id}: next_run_time is not in the future "
                f"({next_run.isoformat()})"
            )
            continue
        if next_run.weekday() >= 5:
            failures.append(
                f"{job_id}: next_run_time falls on a weekend "
                f"({next_run.isoformat()})"
            )
            continue
        due = _previous_weekday_schedule(next_run)
        expected_date = due.date().isoformat()
        if started is None:
            failures.append(f"{job_id}: last_started missing or invalid")
            continue
        if finished is None:
            failures.append(f"{job_id}: last_finished missing or invalid")
            continue
        evidence_clock = observed if observed is not None else current
        future_limit = evidence_clock + timedelta(minutes=5)
        if started > future_limit or finished > future_limit:
            failures.append(
                f"{job_id}: run timestamp is in the future "
                f"(started={started.isoformat()}, finished={finished.isoformat()})"
            )
            continue
        if started < due - timedelta(minutes=5):
            failures.append(
                f"{job_id}: stale run "
                f"(started={started.isoformat()}, expected>={due.isoformat()})"
            )
            continue
        if finished < due or finished < started:
            failures.append(
                f"{job_id}: run incomplete/stale "
                f"(started={started.isoformat()}, finished={finished.isoformat()})"
            )
            continue

        decision = decisions.get(book)
        if not isinstance(decision, dict):
            decision = {}
        failure = _decision_failure(job_id, expected_date, job, decision)
        if failure:
            failures.append(failure)

    return failures


def _load_payload(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("snapshot must be a JSON object")
    return payload


def main(argv: list[str, Any] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--file")
    args = parser.parse_args(argv)

    if args.collect:
        snapshot = collect(base_url=args.base_url)
        print(json.dumps(snapshot, sort_keys=True, separators=(",", ":")))
        return 0

    try:
        payload = _load_payload(args.file)
        failures = evaluate(payload)
    except Exception as exc:  # closed error class only
        result = {
            "schema": RESULT_SCHEMA,
            "status": "error",
            "checked_at": datetime.now(UTC).isoformat(),
            "failures": [f"snapshot_unavailable:{type(exc).__name__}"],
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 1

    result = {
        "schema": RESULT_SCHEMA,
        "status": "ok" if not failures else "error",
        "checked_at": datetime.now(UTC).isoformat(),
        "failures": failures,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
