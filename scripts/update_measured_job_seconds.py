#!/usr/bin/env python3
"""Refresh ``.github/ci/measured-job-seconds.json`` from hosted timing artifacts.

The pack planner's balancing weights are conservative observed seconds (see
``scripts/run_ci_pack.py::_job_weight``).  This tool is the only writer of
that committed table: it ingests the JSONL timing-observation artifacts a
natural hosted run published (``--emit-timing-observations``, PR #10878
collection path), merges them into the existing table by run identity, and
rewrites it deterministically.

Usage (artifacts first fetched with ``gh run download <run-id>`` into an
empty directory; those downloads are untrusted data and are only ever
parsed here, never executed):

    python3 scripts/update_measured_job_seconds.py \
        --artifacts /tmp/timing-42559449303 \
        --run-id 42559449303 --attempt 1 \
        --runner hosted-ubuntu-latest --captured 2026-11-09

Merge policy, fail-closed on ambiguous input:

* one sample per (job, run, attempt, phase-set): re-ingesting the same run
  replaces that run's samples instead of duplicating them;
* records with an unknown phase, a non-"observed" status, or a malformed
  duration abort the run — a silently wrong planning table is worse than a
  failed refresh;
* samples older than ``RETENTION_DAYS`` are dropped at rewrite time, so the
  committed table cannot accumulate indefinitely stale evidence;
* output is byte-deterministic (sorted keys, sorted samples, fixed float
  rendering) for reviewable diffs.

Durations are wall-clock seconds of the observed phase, including any
retries inside it; a timed-out phase's observation is a lower bound, which
is the conservative direction for balancing.  The table records samples and
their dates; the estimator (freshness window, headroom, unobserved bound)
lives in ``run_ci_pack.py`` next to its consumer.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
TABLE_PATH = ROOT / ".github" / "ci" / "measured-job-seconds.json"
SCHEMA = 1
# Keep samples long enough that the freshness window in run_ci_pack.py
# (MEASURED_SAMPLE_MAX_AGE_DAYS) can distinguish fresh from stale, but not
# indefinitely: planning evidence has a shelf life.
RETENTION_DAYS = 180
RUN_ID_RE = re.compile(r"\A[0-9]+\Z")
DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
ALLOWED_PHASES = frozenset({"dependency_install", "test"})


class IngestError(ValueError):
    """The downloaded artifacts do not match the timing-observation shape."""


def _iter_timing_records(artifacts_dir: Path) -> list[dict[str, Any]]:
    """Parse every ``*.jsonl`` under the download tree into records.

    ``gh run download`` materializes one directory per artifact; the timing
    artifacts are JSONL files of ``_timing_observation`` records.  Any file
    that is not such a record stream aborts the ingest: this tool must never
    guess which half of a malformed download to trust.
    """
    records: list[dict[str, Any]] = []
    paths = sorted(artifacts_dir.rglob("*.jsonl"))
    if not paths:
        raise IngestError(f"no *.jsonl timing files under {artifacts_dir}")
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise IngestError(f"{path}:{line_number}: not JSON ({exc})") from exc
                if not isinstance(record, dict):
                    raise IngestError(f"{path}:{line_number}: record is not an object")
                unknown = sorted(set(record) - {
                    "logical_job_id", "phase", "status",
                    "started_monotonic_ns", "ended_monotonic_ns", "duration_ns",
                })
                if unknown:
                    raise IngestError(
                        f"{path}:{line_number}: unknown keys {unknown}; "
                        "the timing schema moved and this tool must be taught it"
                    )
                if record.get("status") != "observed":
                    raise IngestError(
                        f"{path}:{line_number}: status {record.get('status')!r} "
                        "is not an observation this tool ingests"
                    )
                phase = record.get("phase")
                if phase not in ALLOWED_PHASES:
                    raise IngestError(f"{path}:{line_number}: unknown phase {phase!r}")
                job_id = record.get("logical_job_id")
                if not isinstance(job_id, str) or not job_id:
                    raise IngestError(f"{path}:{line_number}: missing logical_job_id")
                duration_ns = record.get("duration_ns")
                if not isinstance(duration_ns, int) or duration_ns < 0:
                    raise IngestError(
                        f"{path}:{line_number}: duration_ns {duration_ns!r} is not "
                        "a nonnegative integer"
                    )
                records.append(record)
    return records


def _seconds_from_ns(duration_ns: int) -> float:
    # Round half-up to 0.1 s so identical inputs yield byte-identical tables.
    return round(duration_ns / 1_000_000_000, 1)


def ingest_samples(
    records: list[dict[str, Any]],
    *,
    run_id: str,
    attempt: int,
    observed: str,
) -> dict[str, dict[str, Any]]:
    """Fold parsed records into one sample per logical job."""
    per_job: dict[str, dict[str, float]] = {}
    for record in records:
        job_id = record["logical_job_id"]
        phase_seconds = per_job.setdefault(job_id, {})
        seconds = _seconds_from_ns(record["duration_ns"])
        # At most one dependency_install observation exists per job per run
        # (the pack installs a venv only when the install command changes);
        # keep the largest if a future runner emits several.
        phase_seconds[record["phase"]] = max(
            seconds, phase_seconds.get(record["phase"], 0.0)
        )
    return {
        job_id: {
            "run_id": run_id,
            "attempt": attempt,
            "observed": observed,
            "test_seconds": phases["test"],
            "dependency_install_seconds": phases.get("dependency_install", 0.0),
        }
        for job_id, phases in sorted(per_job.items())
        if "test" in phases
    }


def merge_table(
    existing: Mapping[str, Any] | None,
    samples: Mapping[str, Mapping[str, Any]],
    *,
    run_id: str,
    attempt: int,
    runner: str,
    captured: str,
    today: str,
) -> dict[str, Any]:
    """Merge new samples into the committed table shape, deterministically."""
    if existing is None:
        jobs: dict[str, dict[str, Any]] = {}
        sources: list[dict[str, Any]] = []
        schema = SCHEMA
    else:
        if existing.get("schema") != SCHEMA:
            raise IngestError(
                f"existing table schema {existing.get('schema')!r} != {SCHEMA}; "
                "teach this tool the migration explicitly"
            )
        jobs = {
            str(job_id): dict(value)
            for job_id, value in existing.get("jobs", {}).items()
        }
        sources = list(existing.get("provenance", {}).get("sources", []))
        schema = existing["schema"]

    kept_sources: list[dict[str, Any]] = []
    for source in sources:
        if source.get("run_id") == run_id and source.get("attempt") == attempt:
            continue  # re-ingesting a run replaces its samples wholesale
        kept_sources.append(source)
    kept_sources.append({
        "run_id": run_id,
        "attempt": attempt,
        "runner": runner,
        "captured": captured,
    })
    sources = sorted(kept_sources, key=lambda s: (str(s.get("run_id")), int(s.get("attempt", 1))))

    active_runs = {
        (str(source["run_id"]), int(source["attempt"]))
        for source in sources
    }
    ingested_key = (run_id, attempt)
    cutoff = dt.date.fromisoformat(today) - dt.timedelta(days=RETENTION_DAYS)
    merged: dict[str, dict[str, Any]] = {}
    for job_id, sample in samples.items():
        merged.setdefault(job_id, {"samples": []})["samples"].append(dict(sample))
    for job_id, entry in jobs.items():
        fresh_samples = []
        for sample in entry.get("samples", []):
            key = (str(sample.get("run_id")), int(sample.get("attempt", 1)))
            observed = str(sample.get("observed", ""))
            if key == ingested_key:
                continue  # this ingest replaces that run's samples wholesale
            if key not in active_runs or not DATE_RE.fullmatch(observed):
                continue  # source run was superseded or the sample is malformed
            if dt.date.fromisoformat(observed) < cutoff:
                continue  # past retention
            fresh_samples.append(dict(sample))
        if fresh_samples:
            merged.setdefault(job_id, {"samples": []})["samples"].extend(fresh_samples)

    table_jobs = {
        job_id: {"samples": sorted(
            entry["samples"],
            key=lambda s: (str(s.get("observed")), str(s.get("run_id")), int(s.get("attempt", 1))),
        )}
        for job_id, entry in sorted(merged.items())
        if entry["samples"]
    }
    return {
        "schema": schema,
        "provenance": {
            "description": (
                "Per-logical-job hosted timing samples ingested by "
                "scripts/update_measured_job_seconds.py from natural run "
                "timing artifacts. Consumed (freshness-windowed, headroom-"
                "scaled) as the pack planner's balancing weights; never "
                "proof authority."
            ),
            "refreshed_at": today,
            "sources": sources,
        },
        "jobs": table_jobs,
    }


def render_table(table: Mapping[str, Any]) -> str:
    return json.dumps(table, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True,
                        help="directory holding the downloaded timing artifacts")
    parser.add_argument("--run-id", required=True,
                        help="GitHub Actions run id that published the artifacts")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--runner", default="hosted-ubuntu-latest")
    parser.add_argument("--captured", required=True,
                        help="date the artifacts were captured, YYYY-MM-DD")
    parser.add_argument("--observed", default=None,
                        help="date the run executed, YYYY-MM-DD (default: --captured)")
    parser.add_argument("--output", type=Path, default=TABLE_PATH)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the rendered table instead of writing it")
    args = parser.parse_args(argv)

    if not RUN_ID_RE.fullmatch(args.run_id):
        parser.error(f"--run-id must be numeric, got {args.run_id!r}")
    for label, value in (("captured", args.captured), ("observed", args.observed or args.captured)):
        if not DATE_RE.fullmatch(value):
            parser.error(f"--{label} must be YYYY-MM-DD, got {value!r}")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    records = _iter_timing_records(args.artifacts)
    samples = ingest_samples(
        records, run_id=args.run_id, attempt=args.attempt,
        observed=args.observed or args.captured,
    )
    if not samples:
        raise IngestError("no complete job observations in the downloaded artifacts")
    existing: dict[str, Any] | None = None
    if args.output.exists():
        try:
            existing = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IngestError(f"existing table {args.output} is unreadable ({exc})") from exc
        if not isinstance(existing, dict):
            raise IngestError(f"existing table {args.output} is not a JSON object")
    table = merge_table(
        existing, samples, run_id=args.run_id, attempt=args.attempt,
        runner=args.runner, captured=args.captured, today=today,
    )
    rendered = render_table(table)
    if args.dry_run:
        sys.stdout.write(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    job_count = len(table["jobs"])
    total_test = sum(
        sample["test_seconds"]
        for entry in table["jobs"].values()
        for sample in entry["samples"]
    )
    print(
        f"table: {job_count} jobs, {len(table['provenance']['sources'])} source runs, "
        f"{round(total_test, 1)} observed test-seconds total -> {args.output}"
        f"{' (dry run)' if args.dry_run else ''}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IngestError as exc:
        print(f"update_measured_job_seconds: {exc}", file=sys.stderr)
        raise SystemExit(2)
