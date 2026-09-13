#!/usr/bin/env python3
"""Read-only off-host dead-man for Mastermind portfolio decision cycles.

The collector is intentionally safe to stream over SSH to the production Python
interpreter: it performs only local GETs and repository identity reads.  The
evaluator is pure and turns that sanitized snapshot into a fail-closed receipt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

UTC = dt.timezone.utc
ALERT_EXIT = 20
FIX_COMMIT = "e61f2951136bdc03a7ec2f5f12f960af26656a4c"
LOCAL_API = "http://127.0.0.1:8001"
DEPLOY_ROOT = Path("/opt/mastermind")

SAFE_DECISION_KEYS = (
    "asof",
    "accepted_asof",
    "settled_asof",
    "target_status",
    "decision_effective",
    "execution_evidence_status",
    "today",
    "trading_day",
)
SAFE_JOB_KEYS = (
    "id",
    "next_run_time",
    "last_started",
    "last_finished",
    "last_skipped",
    "last_status",
    "last_severity",
    "last_reason",
    "last_target_status",
)
BOOKS = {
    "autonomous": {"job_id": "autonomous_daily", "hour": 23, "minute": 10},
    "china": {"job_id": "china_daily", "hour": 8, "minute": 0},
    "hk": {"job_id": "hk_daily", "hour": 9, "minute": 0},
}
SCOPES = {
    "us": ("autonomous",),
    "asia": ("china", "hk"),
    "all": ("autonomous", "china", "hk"),
}
EXPECTED_SKIP_REASONS = {"market_closed"}
MISSING_DECISION_TARGETS = {"rejected_no_submission", "rejected_execution_error"}


def _parse_datetime(value: object) -> dt.datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_date(value: object) -> dt.date | None:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def latest_due_date(
    observed_at: dt.datetime,
    *,
    hour: int,
    minute: int,
    grace_minutes: int = 45,
) -> dt.date:
    """Return the latest Mon-Fri scheduler date whose grace window has elapsed."""
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    observed_at = observed_at.astimezone(UTC)
    cutoff = dt.datetime.combine(
        observed_at.date(), dt.time(hour=hour, minute=minute), tzinfo=UTC
    ) + dt.timedelta(minutes=grace_minutes)
    candidate = observed_at.date()
    if observed_at < cutoff:
        candidate -= dt.timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= dt.timedelta(days=1)
    return candidate


def sanitize_decision(row: object) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {key: row.get(key) for key in SAFE_DECISION_KEYS if key in row}


def sanitize_job(row: object) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {key: row.get(key) for key in SAFE_JOB_KEYS if key in row}


def _alert(book: str, due: dt.date, reason: str, job: object, decision: object) -> dict[str, Any]:
    return {
        "book": book,
        "state": "ALERT",
        "reason": reason,
        "expected_cycle_date": due.isoformat(),
        "job": sanitize_job(job),
        "decision": sanitize_decision(decision),
    }


def _evaluate_book(snapshot: Mapping[str, Any], book: str, observed_at: dt.datetime) -> dict[str, Any]:
    policy = BOOKS[book]
    due = latest_due_date(
        observed_at,
        hour=int(policy["hour"]),
        minute=int(policy["minute"]),
    )
    jobs = snapshot.get("jobs") if isinstance(snapshot.get("jobs"), Mapping) else {}
    decisions = snapshot.get("decisions") if isinstance(snapshot.get("decisions"), Mapping) else {}
    job = jobs.get(policy["job_id"], {}) if isinstance(jobs, Mapping) else {}
    envelope = decisions.get(book, {}) if isinstance(decisions, Mapping) else {}
    decision = envelope.get("latest", {}) if isinstance(envelope, Mapping) else {}

    started = _parse_datetime(job.get("last_started")) if isinstance(job, Mapping) else None
    finished = _parse_datetime(job.get("last_finished")) if isinstance(job, Mapping) else None
    if started is None or started.date() != due:
        return _alert(book, due, "scheduled_cycle_stale", job, decision)
    if finished is None or finished < started:
        return _alert(book, due, "scheduled_cycle_incomplete", job, decision)

    status = str(job.get("last_status") or "").strip().lower()
    reason = str(job.get("last_reason") or "").strip().lower()
    target = str(job.get("last_target_status") or "").strip().lower()

    if status == "skip" and reason in EXPECTED_SKIP_REASONS:
        return {
            "book": book,
            "state": "EXPECTED_SKIP",
            "reason": reason,
            "expected_cycle_date": due.isoformat(),
            "job": sanitize_job(job),
            "decision": {},
        }
    if status == "skip":
        return _alert(book, due, reason or "scheduler_skip_without_decision", job, decision)
    if status == "error":
        return _alert(book, due, reason or target or "scheduler_error", job, decision)
    if target in MISSING_DECISION_TARGETS:
        return _alert(book, due, reason or target, job, decision)
    if not isinstance(envelope, Mapping) or envelope.get("http") != 200:
        return _alert(book, due, "decision_read_failed", job, decision)
    if not isinstance(decision, Mapping) or not decision:
        return _alert(book, due, "decision_missing", job, decision)
    if _parse_date(decision.get("asof")) != due:
        return _alert(book, due, "decision_stale", job, decision)

    decision_target = str(decision.get("target_status") or "").strip().lower()
    if not target or target != decision_target:
        return _alert(book, due, "scheduler_decision_mismatch", job, decision)

    if status == "ok" and target in {"queued", "executed"}:
        if decision.get("decision_effective") is not True:
            return _alert(book, due, "decision_not_effective", job, decision)
        if (
            target == "executed"
            and decision.get("execution_evidence_status") != "receipt_verified"
        ):
            return _alert(book, due, "execution_receipt_unverified", job, decision)
        state = "DECISION_ACCEPTED"
    elif status == "warn" and (
        target.startswith("rejected_") or target.startswith("frozen_")
    ):
        if decision.get("decision_effective") is not False:
            return _alert(book, due, "governed_hold_marked_effective", job, decision)
        state = "GOVERNED_HOLD"
    else:
        return _alert(book, due, reason or "invalid_scheduler_outcome", job, decision)

    return {
        "book": book,
        "state": state,
        "reason": reason or None,
        "expected_cycle_date": due.isoformat(),
        "job": sanitize_job(job),
        "decision": sanitize_decision(decision),
    }


def _release_healthy(snapshot: Mapping[str, Any]) -> bool:
    release = snapshot.get("release")
    if not isinstance(release, Mapping):
        return False
    deployed = str(release.get("deployed_commit") or "")
    return bool(
        release.get("fix_commit") == FIX_COMMIT
        and release.get("release_contains_fix") is True
        and release.get("health_http") == 200
        and release.get("health_status") == "ok"
        and deployed
        and release.get("health_commit") == deployed
        and release.get("scheduler_http") == 200
    )


def evaluate_snapshot(
    snapshot: Mapping[str, Any],
    *,
    scope: str,
    observed_at: dt.datetime | None = None,
) -> dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError(f"unknown scope: {scope}")
    observed = observed_at or _parse_datetime(snapshot.get("observed_at")) or dt.datetime.now(UTC)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    observed = observed.astimezone(UTC)
    receipt: dict[str, Any] = {
        "schema": "mastermind.portfolio_decision_deadman_receipt.v1",
        "scope": scope,
        "observed_at": observed.isoformat(),
        "fix_commit": FIX_COMMIT,
        "state": "ALERT",
        "reason": None,
        "books": {},
        "exit_code": ALERT_EXIT,
    }
    if not _release_healthy(snapshot):
        receipt["reason"] = "release_or_scheduler_unhealthy"
        return receipt

    rows = {book: _evaluate_book(snapshot, book, observed) for book in SCOPES[scope]}
    receipt["books"] = rows
    alerts = [row for row in rows.values() if row.get("state") == "ALERT"]
    if alerts:
        receipt["reason"] = "one_or_more_decision_cycles_unhealthy"
        return receipt
    receipt.update(
        state="HEALTHY",
        reason="selected_decision_cycles_healthy",
        exit_code=0,
    )
    return receipt


def _get_json(path: str) -> tuple[dict[str, Any] | None, int | None, str | None]:
    request = urllib.request.Request(
        LOCAL_API + path,
        method="GET",
        headers={"User-Agent": "Mastermind-Portfolio-Decision-Deadman/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.loads(response.read())
            return (value if isinstance(value, dict) else None, int(response.status), None)
    except urllib.error.HTTPError as exc:
        return None, int(exc.code), "HTTPError"
    except Exception as exc:  # noqa: BLE001 - only the exception class leaves production
        return None, None, type(exc).__name__


def _deployed_contract_contains_fix() -> bool:
    """Verify the repair semantics when a shallow deploy cannot prove ancestry."""
    try:
        provider = (DEPLOY_ROOT / "brain/provider_waterfall.py").read_text(encoding="utf-8")
        scheduler = (DEPLOY_ROOT / "app/scheduler.py").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 - missing source is a closed failure
        return False
    return (
        "access token could not be refreshed" in provider
        and "def _brain_job_outcome" in scheduler
        and 'target == "rejected_no_submission"' in scheduler
        and '"reason": "missing_submission"' in scheduler
        and 'finished_extra.get("target_status")' in scheduler
        and "_brain_job_outcome(_result)" in scheduler
    )


def _release_contains_fix(deployed_commit: str | None) -> bool:
    if not deployed_commit:
        return False
    if deployed_commit == FIX_COMMIT:
        return True
    try:
        if subprocess.run(
            ["git", "-C", str(DEPLOY_ROOT), "merge-base", "--is-ancestor", FIX_COMMIT, deployed_commit],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0:
            return True
    except Exception:  # noqa: BLE001 - source contract remains the fail-closed fallback
        pass
    return _deployed_contract_contains_fix()


def collect_snapshot() -> dict[str, Any]:
    health, health_http, health_error = _get_json("/health")
    scheduler, scheduler_http, scheduler_error = _get_json("/api/scheduler")
    try:
        deployed_commit = (DEPLOY_ROOT / ".deployed_git_sha").read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001 - absence is represented, never exposed raw
        deployed_commit = None

    raw_jobs = scheduler.get("jobs") if isinstance(scheduler, Mapping) else []
    jobs = {
        str(row.get("id")): sanitize_job(row)
        for row in raw_jobs
        if isinstance(row, Mapping) and row.get("id") in {policy["job_id"] for policy in BOOKS.values()}
    }
    decisions: dict[str, Any] = {}
    for book in BOOKS:
        payload, http, error_class = _get_json(f"/api/decisions?portfolio={book}&limit=1")
        rows = payload.get("decisions") if isinstance(payload, Mapping) else []
        latest = rows[0] if isinstance(rows, list) and rows else {}
        decisions[book] = {
            "http": http,
            "error_class": error_class,
            "latest": sanitize_decision(latest),
        }

    return {
        "schema": "mastermind.portfolio_decision_snapshot.v1",
        "observed_at": dt.datetime.now(UTC).isoformat(),
        "transport": "read_only_ssh_get",
        "release": {
            "fix_commit": FIX_COMMIT,
            "deployed_commit": deployed_commit,
            "release_contains_fix": _release_contains_fix(deployed_commit),
            "health_http": health_http,
            "health_error_class": health_error,
            "health_status": health.get("status") if isinstance(health, Mapping) else None,
            "health_commit": health.get("commit") if isinstance(health, Mapping) else None,
            "scheduler_http": scheduler_http,
            "scheduler_error_class": scheduler_error,
        },
        "jobs": jobs,
        "decisions": decisions,
    }


def _load_json(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("snapshot must be a JSON object")
    return value


def _write_json(value: Mapping[str, Any], path: str | None) -> None:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if path:
        Path(path).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("collect", help="collect a sanitized production snapshot")
    evaluate = subparsers.add_parser("evaluate", help="evaluate a sanitized snapshot")
    evaluate.add_argument("--scope", choices=sorted(SCOPES), required=True)
    evaluate.add_argument("--input", default="-")
    evaluate.add_argument("--output")
    evaluate.add_argument("--observed-at")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "collect":
        _write_json(collect_snapshot(), None)
        return 0
    snapshot = _load_json(args.input)
    observed = _parse_datetime(args.observed_at) if args.observed_at else None
    receipt = evaluate_snapshot(snapshot, scope=args.scope, observed_at=observed)
    _write_json(receipt, args.output)
    return int(receipt["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
