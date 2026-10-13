"""Prospective readiness-floor reporter for the Grey Deer pullback lane.

Reads ``forward_log.jsonl`` and ``forward_log_graded.jsonl`` and counts, per
cohort ``(prereg_blob, recipe_fingerprint)``, horizon, and gate family, whether
the design §5 floors hold. ``floors_met`` is only a gate for a future
adjudication. It records that every sample-size floor in the cell holds. This
reporter only counts. It does not produce an outcome result.

No clock and no git. Absent logs are empty. The function never writes into
``log_dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib import nyse_calendar
from scripts.research import grey_deer_pullback_stage1 as s1

SCHEMA = "grey_deer_pullback_readiness.v1"
ISSUE_SCHEMA = "grey_deer_pullback_forward_issue.v1"
GRADE_SCHEMA = "grey_deer_pullback_forward_grade.v1"
ISSUE_NAME = "forward_log.jsonl"
GRADE_NAME = "forward_log_graded.jsonl"

VERDICT_MET = "floors_met"
VERDICT_BLOCKED = "underpowered/blocked claim"

NOTE = (
    "floors_met is a gate for a future adjudication. "
    "It records that every sample-size floor in this cell holds. "
    "This reporter only counts. It does not produce an outcome result."
)

# Binary gate and quantile gate. Other config ids never form a cell.
FAMILIES: tuple[tuple[str, str], ...] = (
    ("binary", "M3-ALL@C=1.0"),
    ("quantile", "Q3-ALL"),
)

# Design §5, with the episode and event-month bars taken from stage-1 §8.
FLOORS: dict[str, int] = {
    "issued_sessions": 252,
    "span_days": 300,
    "graded": 200,
    "events": 20,
    "non_events": 50,
    "clusters": 5,
    "episodes": s1.POWER_MIN_EPISODES,
    "event_months": s1.POWER_MIN_MONTHS,
}

_GRADING_FIELDS = ("realized_A", "Y", "graded_at", "grader_sha")
_EXCLUDED_KEYS = (
    "orphan_grade",
    "malformed_issue",
    "malformed_grade",
    "non_issued_rows",
)


class ReadinessInputError(Exception):
    """A log path exists but cannot be read."""


@dataclass(frozen=True, slots=True)
class _Issue:
    prereg_blob: str
    recipe_fingerprint: str
    asof: str
    ticker: str
    horizon: int
    config_id: str
    abstained: bool
    line_sha256: str

    @property
    def key(self) -> tuple[str, str, int, str]:
        return (self.asof, self.ticker, self.horizon, self.config_id)

    @property
    def cohort(self) -> tuple[str, str]:
        return (self.prereg_blob, self.recipe_fingerprint)


@dataclass(frozen=True, slots=True)
class _Grade:
    issue_line_sha256: str
    asof: str
    ticker: str
    horizon: int
    config_id: str
    y: object
    revision_flag: object

    @property
    def key(self) -> tuple[str, str, int, str]:
        return (self.asof, self.ticker, self.horizon, self.config_id)


def _empty_excluded() -> dict[str, int]:
    return {name: 0 for name in _EXCLUDED_KEYS}


def _read_bytes(path: Path) -> bytes | None:
    """Return file bytes, None when the path is absent, or raise when unreadable."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ReadinessInputError(f"{path}: {exc}") from exc


def _raw_lines(blob: bytes) -> list[bytes]:
    """Split a JSONL blob into raw lines without their trailing newline."""
    if blob == b"":
        return []
    parts = blob.split(b"\n")
    if parts[-1] == b"":
        parts.pop()
    lines: list[bytes] = []
    for part in parts:
        if part.endswith(b"\r"):
            part = part[:-1]
        lines.append(part)
    return lines


def _parse_object(line: bytes) -> dict | None:
    if line == b"" or line.isspace():
        return None
    try:
        text = line.decode("utf-8")
        obj = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _as_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _f2_accept(obj: dict) -> bool:
    return (
        obj.get("schema") == ISSUE_SCHEMA
        and obj.get("evidence_class") == "GENUINELY_ISSUED"
        and obj.get("writer_lane") == "nightly"
        and obj.get("backfill") is False
        and obj.get("rerun") is False
        and obj.get("intraday") is False
    )


def _grading_fields_clean(obj: dict) -> bool:
    """Design §2: a non-null grading field on an issue row is not issued."""
    return all(obj.get(name) is None for name in _GRADING_FIELDS)


def _usable_issue(obj: dict, line_sha: str) -> _Issue | None:
    asof = obj.get("asof")
    if _as_day(asof) is None or not isinstance(asof, str):
        return None
    horizon = _as_int(obj.get("horizon"))
    ticker = obj.get("ticker")
    config_id = obj.get("config_id")
    blob = obj.get("prereg_blob")
    fingerprint = obj.get("recipe_fingerprint")
    if horizon is None:
        return None
    if not isinstance(ticker, str) or not isinstance(config_id, str):
        return None
    if not isinstance(blob, str) or blob == "" or not isinstance(fingerprint, str) or fingerprint == "":
        return None
    return _Issue(
        prereg_blob=blob,
        recipe_fingerprint=fingerprint,
        asof=asof,
        ticker=ticker,
        horizon=horizon,
        config_id=config_id,
        abstained=obj.get("abstention_reason") is not None,
        line_sha256=line_sha,
    )


def _classify_issue(obj: dict, line_sha: str) -> _Issue | str:
    if not _f2_accept(obj) or not _grading_fields_clean(obj):
        return "non_issued"
    issue = _usable_issue(obj, line_sha)
    if issue is None:
        return "malformed"
    return issue


def _usable_grade(obj: dict) -> _Grade | None:
    if obj.get("schema") != GRADE_SCHEMA:
        return None
    asof = obj.get("asof")
    if _as_day(asof) is None or not isinstance(asof, str):
        return None
    horizon = _as_int(obj.get("horizon"))
    ticker = obj.get("ticker")
    config_id = obj.get("config_id")
    line_sha = obj.get("issue_line_sha256")
    if horizon is None:
        return None
    if not isinstance(ticker, str) or not isinstance(config_id, str) or not isinstance(line_sha, str):
        return None
    return _Grade(
        issue_line_sha256=line_sha,
        asof=asof,
        ticker=ticker,
        horizon=horizon,
        config_id=config_id,
        y=obj.get("Y"),
        revision_flag=obj.get("revision_flag", None),
    )


def _load_issues(path: Path) -> tuple[list[_Issue], set[str], dict[str, int]]:
    counts = {"malformed_issue": 0, "non_issued_rows": 0}
    blob = _read_bytes(path)
    if blob is None:
        return [], set(), counts
    accepted: list[_Issue] = []
    parsed_shas: set[str] = set()
    for line in _raw_lines(blob):
        obj = _parse_object(line)
        if obj is None:
            counts["malformed_issue"] += 1
            continue
        line_sha = hashlib.sha256(line).hexdigest()
        parsed_shas.add(line_sha)
        classified = _classify_issue(obj, line_sha)
        if isinstance(classified, _Issue):
            accepted.append(classified)
        elif classified == "non_issued":
            counts["non_issued_rows"] += 1
        else:
            counts["malformed_issue"] += 1
    return accepted, parsed_shas, counts


def _load_grades(path: Path) -> tuple[list[_Grade], int]:
    blob = _read_bytes(path)
    if blob is None:
        return [], 0
    grades: list[_Grade] = []
    malformed = 0
    for line in _raw_lines(blob):
        obj = _parse_object(line)
        if obj is None:
            malformed += 1
            continue
        grade = _usable_grade(obj)
        if grade is None:
            malformed += 1
            continue
        grades.append(grade)
    return grades, malformed


def _span_days(asofs: set[str]) -> int:
    if not asofs:
        return 0
    days = [date.fromisoformat(asof) for asof in asofs]
    return (max(days) - min(days)).days


def _session_power(rows: list[tuple[str, object]], h: int) -> tuple[int, int, int]:
    """Clusters, episodes and event-months from ``s1.honest_n``.

    ``honest_n`` keeps ``origin_idx`` where ``y`` is true, then reads
    ``dates[origin]``. The cluster rule is the session index, so ``origin_idx``
    is ``session_ordinals`` of the graded asofs and ``dates`` is the full NYSE
    session calendar from the earliest graded asof through the latest. A
    non-session asof has no ordinal and stays out of this call.
    """
    parsed: list[tuple[date, bool]] = []
    for asof, outcome in sorted(rows, key=lambda item: item[0]):
        parsed.append((date.fromisoformat(asof), outcome == 1))
    ordinals = nyse_calendar.session_ordinals([day for day, _flag in parsed])
    kept_idx: list[int] = []
    kept_y: list[bool] = []
    kept_days: list[date] = []
    for ordinal, (day, flag) in zip(ordinals, parsed):
        if ordinal is None:
            continue
        kept_idx.append(int(ordinal))
        kept_y.append(flag)
        kept_days.append(day)
    if not kept_days:
        report = s1.honest_n([], [], [], h)
    else:
        calendar = [
            day.isoformat()
            for day in nyse_calendar.sessions_between(min(kept_days), max(kept_days))
        ]
        report = s1.honest_n(kept_idx, kept_y, calendar, h)
    return int(report["clusters"]), int(report["episodes"]), int(report["event_months"])


def _cell(
    issues: list[_Issue],
    pairs: list[tuple[_Issue, _Grade]],
    h: int,
    family: str,
    config_id: str,
) -> dict:
    mine = [issue for issue in issues if issue.horizon == h and issue.config_id == config_id]
    issued_asofs = {issue.asof for issue in mine if not issue.abstained}
    abstained_asofs = {issue.asof for issue in mine if issue.abstained}

    graded_rows: list[tuple[str, object]] = []
    revision_flagged = 0
    revision_flag_null = 0
    for issue, grade in pairs:
        if issue.horizon != h or issue.config_id != config_id or issue.abstained:
            continue
        if grade.revision_flag is True:
            revision_flagged += 1
            continue
        if grade.revision_flag is None:
            revision_flag_null += 1
        graded_rows.append((issue.asof, grade.y))

    events = sum(1 for _asof, outcome in graded_rows if outcome == 1)
    non_events = sum(1 for _asof, outcome in graded_rows if outcome == 0)
    clusters, episodes, event_months = _session_power(graded_rows, h)
    values = {
        "issued_sessions": len(issued_asofs),
        "span_days": _span_days(issued_asofs),
        "graded": len(graded_rows),
        "events": events,
        "non_events": non_events,
        "clusters": clusters,
        "episodes": episodes,
        "event_months": event_months,
    }
    floors = {
        name: {"value": values[name], "min": minimum, "met": values[name] >= minimum}
        for name, minimum in FLOORS.items()
    }
    all_met = all(item["met"] for item in floors.values())
    return {
        "horizon": h,
        "family": family,
        "config_id": config_id,
        "issued_sessions": values["issued_sessions"],
        "abstained_sessions": len(abstained_asofs),
        "span_days": values["span_days"],
        "graded": values["graded"],
        "events": events,
        "non_events": non_events,
        "clusters": clusters,
        "episodes": episodes,
        "event_months": event_months,
        "revision_flagged": revision_flagged,
        "revision_flag_null": revision_flag_null,
        "floors": floors,
        "all_met": all_met,
        "verdict": VERDICT_MET if all_met else VERDICT_BLOCKED,
    }


def _join(
    issues: list[_Issue],
    grades: list[_Grade],
    parsed_issue_shas: set[str],
) -> tuple[list[tuple[_Issue, _Grade]], int]:
    by_sha: dict[str, list[_Issue]] = defaultdict(list)
    for issue in issues:
        by_sha[issue.line_sha256].append(issue)
    pairs: list[tuple[_Issue, _Grade]] = []
    orphans = 0
    for grade in grades:
        if grade.issue_line_sha256 not in parsed_issue_shas:
            orphans += 1
            continue
        match = next((issue for issue in by_sha.get(grade.issue_line_sha256, []) if issue.key == grade.key), None)
        if match is None or match.abstained:
            continue
        pairs.append((match, grade))
    return pairs, orphans


def readiness(log_dir: Path) -> dict:
    """Count design §5 floors for every cohort, horizon and gate family.

    Pure: no clock and no git. Missing log files count as empty. Raises
    ``ReadinessInputError`` when a log path exists but cannot be read.
    """
    log_dir = Path(log_dir)
    issues, parsed_shas, issue_counts = _load_issues(log_dir / ISSUE_NAME)
    grades, malformed_grade = _load_grades(log_dir / GRADE_NAME)
    pairs, orphans = _join(issues, grades, parsed_shas)

    excluded = _empty_excluded()
    excluded["malformed_issue"] = issue_counts["malformed_issue"]
    excluded["non_issued_rows"] = issue_counts["non_issued_rows"]
    excluded["malformed_grade"] = malformed_grade
    excluded["orphan_grade"] = orphans

    by_cohort: dict[tuple[str, str], list[_Issue]] = defaultdict(list)
    pairs_by_cohort: dict[tuple[str, str], list[tuple[_Issue, _Grade]]] = defaultdict(list)
    for issue in issues:
        by_cohort[issue.cohort].append(issue)
    for issue, grade in pairs:
        pairs_by_cohort[issue.cohort].append((issue, grade))

    cohorts = []
    for blob, fingerprint in sorted(by_cohort):
        cohort_issues = by_cohort[(blob, fingerprint)]
        cohort_pairs = pairs_by_cohort.get((blob, fingerprint), [])
        cells = [
            _cell(cohort_issues, cohort_pairs, h, family, config_id)
            for h in s1.HORIZONS
            for family, config_id in FAMILIES
        ]
        cohorts.append({
            "prereg_blob": blob,
            "recipe_fingerprint": fingerprint,
            "cells": cells,
        })
    return {
        "schema": SCHEMA,
        "cohorts": cohorts,
        "excluded": excluded,
        "note": NOTE,
    }


def _contained_by(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count Grey Deer pullback prospective readiness floors.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("data/grey_deer_pullback"),
        help="Directory of forward_log.jsonl and forward_log_graded.jsonl.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Also write the JSON here. Refuses a path inside --log-dir.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.out is not None and _contained_by(args.out, args.log_dir):
        print("refusing to write inside --log-dir", file=sys.stderr)
        return 1
    try:
        payload = readiness(args.log_dir)
    except ReadinessInputError as exc:
        print(f"unreadable input: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    sys.stdout.write(text)
    if args.out is not None:
        try:
            args.out.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"cannot write output: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
