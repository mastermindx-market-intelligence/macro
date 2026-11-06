#!/usr/bin/env python3
"""Dead-man switch for the QUEUED-JOB HOSTAGE class: a job addressed to a
self-hosted label that no online runner carries.

WHY THIS EXISTS — the 2026-09-25 render-lane outage, and the 2026-08-17 Prophet
outage before it.  Both are the same mechanism, and both were invisible to every
instrument we owned:

  * 2026-08-14→17: ``theta-m1`` died with mac-builder-1/2, ``daily.yml``'s
    ``collect_tail`` became unschedulable, and the queued job held its cron
    concurrency group until GitHub's 24h kill — freezing every Prophet board for
    three days with no red anywhere
    (research/PROPHET_OUTAGE_2026_08_17_POSTMORTEM.md,
    DSC:QUEUED-JOB-HOSTAGE-HOLDS-THE-NIGHTLY-CRON-GROUP).
  * 2026-09-23→25: ``render-linux`` lost its last carrier — ``pc-render-1`` stayed
    online and idle but its custom labels were stripped to the read-only set — so
    ``render.yml``, ``engine-render.yml`` and ``sector-intelligence.yml`` all went
    dark for three days.  Run 35819881039's job was the last one ever assigned
    (started 2026-09-23T09:45:34Z on pc-render-1); the next job, created
    12:05:09Z, never got a runner and was killed at +24h exactly; its successor
    35989213316 took the slot and sat queued for another day.  1,479 committed
    site pages went stale behind it.

WHAT MADE IT SILENT, TWICE.  Every other instrument asks about the SUBJECT:
  * ``check_nightly_liveness.py`` watches ``daily.yml`` alone.  daily.yml routes
    ``macstudio`` — a live label — so it ran green all three days and the watchdog
    correctly said nothing.  A per-lane watchdog can only cover the lane someone
    thought to name.
  * ``check_runner_policy.py`` R11/R12 own the label DECLARATION boundary, but the
    registry is hand-maintained documentation: nobody edited it when the label
    died, so the static rules had nothing to fire on.  A declaration check cannot
    observe a fact no human wrote down.
  * The lanes themselves emit nothing: a run whose job is never assigned produces
    no logs, no annotation, and no failure — it is indistinguishable from a quiet
    night until GitHub kills it 24h later.

THE INVARIANT THIS CHECK USES INSTEAD.  The SYMPTOM is universal even when the
cause is not: whatever label died, whichever lane it starved, the observable is
always a job sitting ``queued`` with NO runner assigned.  That question is
label-agnostic, lane-agnostic, needs no calendar anchor, and needs no admin token
— only ``actions: read``.  It therefore covers every lane we have, including the
ones nobody has thought to watch yet, and it would have fired on day one of both
outages.

WHY THE THRESHOLD IS 8 HOURS.  A queued self-hosted job is NOT automatically a
breach: ``macstudio`` is a two-host pool that the nightly, closing-bell,
asia-close and the close-pass backstop all share, so a job can honestly wait
behind a multi-hour bake.  Measured worst legitimate waits: daily.yml 1h12m–2h31m,
a scope=all render 40–85m, closing-bell holding the window on top of that.  8h is
~3x the worst honest wait and a third of GitHub's 24h queued-job kill, so this
pages with ~16h of margin before the run dies unproven — and cannot be reached by
a legitimate queue.  A false alarm every night is how a dead-man switch dies
(verdict discipline borrowed verbatim from ``check_nightly_liveness``).

VERDICT DISCIPLINE.  Blindness is never a breach.  An unreadable API response, a
missing registry, an unparseable timestamp -> INDETERMINATE: a ``::warning``, exit
0.  Only a POSITIVE observation of a job held past the threshold fails.

WHERE IT RUNS.  ``.github/workflows/nightly-liveness.yml``, its own hosted
``ubuntu-latest`` job — deliberately NOT on any self-hosted pool, because a
watchdog for "no runner can take this job" must not itself need a runner from the
pool under test.  Three looks a day bound detection latency to ~6h on top of the
8h threshold.

Usage:
    python3 scripts/check_runner_queue_hostage.py               # live
    python3 scripts/check_runner_queue_hostage.py --selftest    # synthetic
    python3 scripts/check_runner_queue_hostage.py --runs-json F --jobs-json G

Exit codes:
    0  healthy, or INDETERMINATE (blind — see above)
    1  a positive observation: a self-hosted-addressed job held queued past the
       threshold with no runner assigned
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# UNCONDITIONAL by contract (tests/test_check_script_import_pinning.py) — this runs
# from a bare `python3 scripts/…` on a GitHub-hosted runner whose CWD and
# sys.path[0] are not this repo.
sys.path.insert(0, str(REPO_ROOT))

#: How long a self-hosted-addressed job may sit unassigned before it is a breach.
#: See "WHY THE THRESHOLD IS 8 HOURS" above — this is a measured budget, not taste.
MAX_QUEUE = timedelta(hours=8)

#: Bound on the number of live runs whose jobs we expand, AFTER the age filter
#: below.  The shared REST pool is 5,000/hr for the whole fleet (CLAUDE.md).  The
#: age filter is what makes this cheap: measured 2026-09-25 this repo carried 32
#: live runs but only 3 older than the threshold, so a look costs ~5 calls rather
#: than ~34.  Truncation is reported, never silent.
MAX_RUNS_INSPECTED = 40

#: The declared label model.  Used ONLY to classify a label as hosted vs
#: self-hosted and to enrich the breach message with what the registry believes —
#: never as the source of truth about liveness, which is the mistake that made
#: R11/R12 blind here.
REGISTRY_PATH = REPO_ROOT / ".github" / "runner-policy.yml"

#: Fallback hosted-label families for when the registry is unreadable.  GitHub's
#: hosted images are the only labels that legitimately queue briefly without a
#: self-hosted carrier.
HOSTED_PREFIXES = ("ubuntu-", "windows-", "macos-")

REPO = os.environ.get("GITHUB_REPOSITORY") or "mastermindx-market-intelligence/macro"


def _warn(title: str, message: str) -> None:
    """GitHub annotations MUST start the line and MUST flush (CLAUDE.md house law:
    a logger-prefixed annotation is silently dropped, and stdout is block-buffered
    when piped in CI)."""
    print(f"::warning title={title}::{message}", flush=True)


def _parse_dt(value: object) -> "datetime | None":
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def load_hosted_labels(path: Path = REGISTRY_PATH) -> "set[str] | None":
    """Labels the registry declares GitHub-hosted.  None on any blindness."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        _warn("runner-queue-hostage-blind", "PyYAML unavailable; using prefix families")
        return None
    try:
        registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _warn("runner-queue-hostage-blind", f"registry unreadable ({exc}); using prefix families")
        return None
    entries = (registry or {}).get("label_registry")
    if not isinstance(entries, dict):
        _warn("runner-queue-hostage-blind", "registry has no label_registry; using prefix families")
        return None
    return {
        str(label)
        for label, entry in entries.items()
        if isinstance(entry, dict) and entry.get("status") == "github-hosted"
    }


def load_registry_view(path: Path = REGISTRY_PATH) -> dict:
    """``{label: {"status":…, "carried_by":[…]}}`` for breach enrichment.  This is
    read to EXPLAIN a breach the live API already proved, never to decide one — the
    registry being wrong is the condition this check exists to survive."""
    try:
        import yaml  # noqa: PLC0415

        registry = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, ImportError):
        return {}
    entries = registry.get("label_registry")
    if not isinstance(entries, dict):
        return {}
    view = {}
    for label, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        carried = entry.get("carried_by")
        view[str(label)] = {
            "status": str(entry.get("status")),
            "carried_by": [str(x) for x in carried] if isinstance(carried, list) else [],
        }
    return view


def is_self_hosted_addressed(labels: object, hosted: "set[str] | None") -> bool:
    """True when the job's runs-on set names anything only a self-hosted runner
    can carry.  A hosted-only job never waits hours, so it is out of scope."""
    if not isinstance(labels, list) or not labels:
        return False
    names = [str(x) for x in labels]
    if hosted is not None:
        return any(name not in hosted for name in names)
    return any(not name.startswith(HOSTED_PREFIXES) for name in names)


def evaluate(
    live_jobs: "list[dict]",
    *,
    now: datetime,
    hosted: "set[str] | None",
    registry_view: "dict | None" = None,
    max_queue: timedelta = MAX_QUEUE,
) -> dict:
    """Grade already-fetched job rows.  Pure — every caller (live, offline fixture,
    selftest) goes through here so the fixtures test the shipped logic."""
    registry_view = registry_view or {}
    breaches: list[str] = []
    watched = 0
    undated = 0
    for row in live_jobs:
        if not isinstance(row, dict) or row.get("status") != "queued":
            continue
        # A job with a runner assigned is starting or started — not a hostage.
        if (row.get("runner_name") or "").strip():
            continue
        if not is_self_hosted_addressed(row.get("labels"), hosted):
            continue
        watched += 1
        queued_at = _parse_dt(row.get("created_at")) or _parse_dt(row.get("started_at"))
        if queued_at is None:
            # Undated -> INDETERMINATE for this row. Never a breach, never a pass.
            undated += 1
            continue
        held = now - queued_at
        if held < max_queue:
            continue
        labels = ",".join(str(x) for x in (row.get("labels") or []))
        note = ""
        for name in (str(x) for x in (row.get("labels") or [])):
            entry = registry_view.get(name)
            if isinstance(entry, dict) and entry.get("status") != "live":
                note = (f"registry says {name} is status={entry.get('status')!r} "
                        f"carried_by=[{','.join(entry.get('carried_by') or [])}]")
                break
        breaches.append(
            f"run {row.get('run_id', '?')} job {row.get('name', '?')!r} "
            f"({row.get('workflow_name') or '?'}) addressed to [{labels}] has been "
            f"queued {held.total_seconds() / 3600:.1f}h with no runner assigned"
            + (f" — {note}" if note else "")
        )
    return {
        "ok": not breaches,
        "fail_reasons": breaches,
        "queued_self_hosted_jobs": watched,
        "undated_rows": undated,
        "threshold_hours": max_queue.total_seconds() / 3600,
    }


def _get(url: str, token: "str | None", *, what: str) -> "dict | None":
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "macro-runner-queue-hostage",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        _warn("runner-queue-hostage-blind", f"{what} fetch failed: {exc}")
        return None


def fetch_live_jobs(
    repo: str,
    token: "str | None",
    *,
    now: "datetime | None" = None,
    max_queue: timedelta = MAX_QUEUE,
) -> "list[dict] | None":
    """Jobs of every unfinished run OLD ENOUGH to hold a hostage, flattened with the
    run id and workflow name.  None on any blindness — a partial picture is
    INDETERMINATE, never a green.

    The age filter is exact, not a heuristic: a job's ``created_at`` can never
    precede its run's, so a run younger than the threshold cannot contain a job
    queued past it.  It only over-includes (an old run whose jobs are fresh), which
    ``evaluate`` then filters on the job's own timestamp.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - max_queue
    runs: list[dict] = []
    for status in ("queued", "in_progress"):
        payload = _get(
            f"https://api.github.com/repos/{repo}/actions/runs"
            f"?status={status}&per_page=50",
            token,
            what=f"{status} runs",
        )
        if payload is None:
            return None
        found = payload.get("workflow_runs")
        if not isinstance(found, list):
            _warn("runner-queue-hostage-blind", f"{status} runs payload has no workflow_runs")
            return None
        runs.extend(found)
    aged = [r for r in runs if (_parse_dt(r.get("created_at")) or now) <= cutoff]
    if len(aged) > MAX_RUNS_INSPECTED:
        _warn(
            "runner-queue-hostage-blind",
            f"{len(aged)} live runs older than {max_queue.total_seconds() / 3600:.0f}h "
            f"exceeds the {MAX_RUNS_INSPECTED}-run inspection bound; grading the "
            "oldest (a hostage is always among the oldest live runs)",
        )
        aged.sort(key=lambda r: str(r.get("created_at") or ""))
        aged = aged[:MAX_RUNS_INSPECTED]
    runs = aged
    jobs: list[dict] = []
    for run in runs:
        run_id = run.get("id")
        if run_id is None:
            continue
        payload = _get(
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100",
            token,
            what=f"run {run_id} jobs",
        )
        if payload is None:
            return None
        for job in payload.get("jobs") or []:
            if isinstance(job, dict):
                job.setdefault("run_id", run_id)
                job.setdefault("workflow_name", run.get("name"))
                jobs.append(job)
    return jobs


def _selftest() -> int:
    """Fixture timestamps are CONSTANTS with no relation to the wall clock — a guard
    whose fixtures age is a scheduled red."""
    now = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)
    hosted = {"ubuntu-latest"}
    view = {
        "render-linux": {"status": "orphaned", "carried_by": []},
        "self-hosted": {"status": "live", "carried_by": ["pc-render-1"]},
        "macstudio": {"status": "live", "carried_by": ["mac-builder-5"]},
    }
    failures = 0

    def check(label: str, got: bool, want: bool) -> None:
        nonlocal failures
        if got is not want:
            failures += 1
            print(f"::error title=selftest::{label}: ok={got}, expected {want}", flush=True)

    def job(**kw):
        base = {
            "status": "queued", "runner_name": "", "labels": ["self-hosted", "render-linux"],
            "created_at": "2026-09-24T12:05:10Z", "name": "render", "run_id": 35989213316,
            "workflow_name": "render",
        }
        base.update(kw)
        return base

    # The 2026-09-25 shape: 19.9h queued, no runner, dead label -> BREACH.
    got = evaluate([job()], now=now, hosted=hosted, registry_view=view)
    check("render-linux hostage is a breach", got["ok"], False)
    assert "orphaned" in got["fail_reasons"][0], got["fail_reasons"]
    assert "19.9h" in got["fail_reasons"][0], got["fail_reasons"]

    # Inside the budget: a job queued behind a live multi-hour bake is NOT a breach.
    check("a 3h queue behind a live pool passes",
          evaluate([job(created_at="2026-09-25T05:00:00Z", labels=["self-hosted", "macstudio"])],
                   now=now, hosted=hosted, registry_view=view)["ok"], True)

    # A runner IS assigned -> starting, not a hostage, however long the row is old.
    check("assigned runner is never a hostage",
          evaluate([job(runner_name="pc-render-1")], now=now, hosted=hosted)["ok"], True)

    # Hosted-only jobs are out of scope (hosted capacity backlogs are not our class).
    check("hosted-only job is out of scope",
          evaluate([job(labels=["ubuntu-latest"])], now=now, hosted=hosted)["ok"], True)

    # A running job is not queued.
    check("in_progress job is not a hostage",
          evaluate([job(status="in_progress")], now=now, hosted=hosted)["ok"], True)

    # Verdict discipline: an undated row is INDETERMINATE, never a breach.
    undated = evaluate([job(created_at=None, started_at=None)], now=now, hosted=hosted)
    check("undated row is INDETERMINATE not a breach", undated["ok"], True)
    assert undated["undated_rows"] == 1, undated

    # Nothing live at all -> healthy.
    check("empty job list is healthy", evaluate([], now=now, hosted=hosted)["ok"], True)

    # Registry blindness must not blind the CHECK: prefix families still classify.
    check("prefix fallback still catches the hostage",
          evaluate([job()], now=now, hosted=None)["ok"], False)
    check("prefix fallback still exempts hosted",
          evaluate([job(labels=["ubuntu-latest"])], now=now, hosted=None)["ok"], True)

    # The 2026-08-17 theta-m1 shape, for the class rather than the instance.
    check("theta-m1 (2026-08-17) shape is a breach",
          evaluate([job(labels=["self-hosted", "theta-m1"], name="collect_tail",
                        workflow_name="daily", created_at="2026-09-24T09:00:00Z")],
                   now=now, hosted=hosted)["ok"], False)

    if failures:
        return 1
    print("::notice title=runner-queue-hostage::selftest ok", flush=True)
    return 0


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--jobs-json", type=Path, help="offline: pre-fetched job rows")
    parser.add_argument("--max-queue-hours", type=float, default=None)
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    max_queue = (
        timedelta(hours=args.max_queue_hours) if args.max_queue_hours else MAX_QUEUE
    )
    hosted = load_hosted_labels()
    registry_view = load_registry_view()

    if args.jobs_json:
        try:
            jobs = json.loads(args.jobs_json.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _warn("runner-queue-hostage-blind", f"jobs fixture unreadable: {exc}")
            return 0
    else:
        jobs = fetch_live_jobs(
            REPO, os.environ.get("GITHUB_TOKEN"), max_queue=max_queue
        )
    if jobs is None:
        # Transport blindness already annotated. INDETERMINATE, never a false green
        # and never a false red.
        return 0

    report = evaluate(
        jobs, now=datetime.now(timezone.utc), hosted=hosted,
        registry_view=registry_view, max_queue=max_queue,
    )
    if report["ok"]:
        print(
            "::notice title=runner-queue-hostage::no self-hosted job held past "
            f"{report['threshold_hours']:.0f}h "
            f"({report['queued_self_hosted_jobs']} queued self-hosted job(s) seen)",
            flush=True,
        )
        return 0
    for line in report["fail_reasons"]:
        print(f"::error title=runner-queue-hostage::{line}", flush=True)
    print(
        "::error title=runner-queue-hostage::a job no online runner can take holds "
        "its concurrency group until GitHub's 24h kill, and every push behind it is "
        "superseded — restore the label's carrier or re-point the lane "
        "(.github/runner-policy.yml label_registry is the declared model)",
        flush=True,
    )
    _notify(report)
    return 1


def _notify(report: dict) -> None:
    """Best-effort push on the same W6b spine healthcheck and nightly-liveness use.
    The non-zero exit is the primary signal; this is what reaches a phone."""
    msg = "🚨 macro-dashboard RUNNER QUEUE HOSTAGE — " + "; ".join(report["fail_reasons"])
    try:
        from engine.alert_triage import push_ops_alert  # noqa: PLC0415

        push_ops_alert(
            source="runner_queue_hostage",
            type_="runner_label_dead",
            message=msg,
            severity="critical",
            lane="runner_queue_hostage",
        )
    except Exception:  # noqa: BLE001 — alerting is best-effort, never the gate
        pass


if __name__ == "__main__":
    raise SystemExit(main())
