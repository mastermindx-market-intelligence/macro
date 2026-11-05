"""Dormant trusted feature-ordering measurement; no admission, routing or writes.

All records are supplied by trusted owners after source/calendar/runtime/trial/
Vault qualification. Shape checks cannot authenticate those facts. Candidate
code, callable selection and filesystem references are never inputs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

COHORT = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
FORMATION_ANCHOR = "2010-01-04"


@dataclass(frozen=True)
class SourcePath:
    node: str
    session_dates: tuple[str, ...]
    returns: tuple[float, ...]


@dataclass(frozen=True)
class Formation:
    calendar_index: int
    trigger_date: str
    eligible_nodes: tuple[str, ...]


@dataclass(frozen=True)
class FeatureScore:
    calendar_index: int
    node: str
    value: float


@dataclass(frozen=True)
class MeasuredEntry:
    node: str
    trigger_date: str
    exec_date: str
    mfe: float
    mae: float
    ret_exit: float
    hold_sessions: int


@dataclass(frozen=True)
class CoveragePosition:
    calendar_index: int
    trigger_date: str
    opportunities: int


@dataclass(frozen=True)
class PairedFormation:
    calendar_index: int
    trigger_date: str
    selected_nodes: tuple[str, ...]
    foregone_nodes: tuple[str, ...]
    baseline_entries: tuple[MeasuredEntry, ...]
    candidate_entries: tuple[MeasuredEntry, ...]
    baseline_loss: float
    candidate_loss: float
    difference: float


@dataclass(frozen=True)
class EvaluationResult:
    status: str
    refusal_reasons: tuple[str, ...]
    coverage: tuple[CoveragePosition, ...]
    pairs: tuple[PairedFormation, ...]
    authority: str = "display_only"
    scientific_acceptance: str = "UNQUALIFIED"

    @property
    def refusal_count(self) -> int:
        return len(self.refusal_reasons)


def _finite(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _date(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _measure_incumbent_rows(paths, entry_dates):
    """Private fixed binding. Tests stub this wrapper, never a public callback."""
    import pandas as pd
    from scripts.oracle_reversion_screen import _per_entry_rows

    index = pd.MultiIndex.from_tuples(
        [(path.node, pd.Timestamp(day)) for path in paths for day in path.session_dates],
        names=("node", "date"),
    )
    panel = pd.DataFrame(
        {"ret": [value for path in paths for value in path.returns]}, index=index,
    )
    entries = {node: pd.DatetimeIndex(days) for node, days in entry_dates.items()}
    rows = _per_entry_rows(entries, panel, window=25, exit_sessions=21, exit_mode="time")
    # Date normalization only; native numerical fields remain unchanged.
    return [dict(row, trigger_date=row["trigger_date"].strftime("%Y-%m-%d"),
                 exec_date=row["exec_date"].strftime("%Y-%m-%d")) for row in rows]


def evaluate_feature_ordering(*, paths, formations, scores, expected_session_dates):
    """Return paired diagnostics or whole-call refusal; never inferential PASS.

    Predeclared source-excluded schedule positions remain in the source owner's
    external coverage record. This helper cannot create post-output exclusions.
    A runtime failure is refused upstream, never passed as a survivor-only batch.
    """
    coverage = ()

    def refused(*reasons):
        return EvaluationResult("REFUSED", tuple(reasons), coverage, ())

    if any(type(value) is not tuple for value in
           (paths, formations, scores, expected_session_dates)):
        return refused("IMMUTABLE_INPUT_REQUIRED")
    if (not expected_session_dates or any(not _date(day) for day in expected_session_dates)
            or any(a >= b for a, b in zip(expected_session_dates, expected_session_dates[1:]))):
        return refused("INVALID_CALENDAR_SEQUENCE")
    positions = {day: index for index, day in enumerate(expected_session_dates)}
    anchor_position = positions.get(FORMATION_ANCHOR)
    if anchor_position is None:
        return refused("FORMATION_ANCHOR_ABSENT")
    if (len(paths) != len(COHORT) or any(type(path) is not SourcePath for path in paths)
            or any(type(path.node) is not str for path in paths)
            or sorted(path.node for path in paths) != sorted(COHORT)):
        return refused("EXACT_COHORT_PATHS_REQUIRED")
    for path in paths:
        if (type(path.session_dates) is not tuple or type(path.returns) is not tuple
                or any(not _date(day) for day in path.session_dates)
                or path.session_dates != expected_session_dates
                or len(path.returns) != len(expected_session_dates)):
            return refused("SOURCE_CALENDAR_OR_LENGTH_MISMATCH")
        if any(not _finite(value) or value <= -1 for value in path.returns):
            return refused("INVALID_SOURCE_RETURN")
    if any(type(formation) is not Formation for formation in formations):
        return refused("INVALID_FORMATION_RECORD")
    previous = None
    for formation in formations:
        if (type(formation.calendar_index) is not int or formation.calendar_index < 0
                or not _date(formation.trigger_date)
                or type(formation.eligible_nodes) is not tuple
                or any(type(node) is not str or node not in COHORT for node in formation.eligible_nodes)
                or len(set(formation.eligible_nodes)) != len(formation.eligible_nodes)):
            return refused("INVALID_FORMATION_IDENTITY")
        trigger = positions.get(formation.trigger_date)
        if trigger is None or trigger < 259 or trigger + 26 >= len(expected_session_dates):
            return refused("INCOMPLETE_WARMUP_ENTRY_OR_LABEL_HORIZON")
        if trigger != anchor_position + 26 * formation.calendar_index:
            return refused("FORMATION_ANCHOR_MISMATCH")
        if previous is not None:
            old_index, old_trigger = previous
            if (formation.calendar_index <= old_index
                    or trigger - old_trigger != 26 * (formation.calendar_index - old_index)):
                return refused("FORMATION_SCHEDULE_MISMATCH")
        previous = (formation.calendar_index, trigger)
    coverage = tuple(CoveragePosition(f.calendar_index, f.trigger_date, len(f.eligible_nodes))
                     for f in formations)
    expected = {(f.calendar_index, node) for f in formations for node in f.eligible_nodes}
    values = {}
    reasons = []
    for score in scores:
        if (type(score) is not FeatureScore or type(score.calendar_index) is not int
                or type(score.node) is not str):
            reasons.append("INVALID_SCORE_RECORD")
            continue
        key = (score.calendar_index, score.node)
        if key not in expected:
            reasons.append("UNEXPECTED_SCORE")
        elif key in values:
            reasons.append("DUPLICATE_SCORE")
        elif not _finite(score.value):
            reasons.append("NONFINITE_SCORE")
        else:
            values[key] = score.value
    reasons.extend("MISSING_SCORE" for key in sorted(expected - values.keys()))
    if reasons:
        return refused(*reasons)
    if not expected:
        return EvaluationResult("DIAGNOSTIC_ONLY", (), coverage, ())
    entries = {node: tuple(f.trigger_date for f in formations if node in f.eligible_nodes)
               for node in COHORT}
    entries = {node: days for node, days in entries.items() if days}
    try:
        rows = _measure_incumbent_rows(paths, entries)
    except Exception:
        return refused("INCUMBENT_CALL_FAILURE")
    if type(rows) is not list:
        return refused("INVALID_NATIVE_ROWS")
    wanted_rows = {(node, f.trigger_date): expected_session_dates[positions[f.trigger_date] + 1]
                   for f in formations for node in f.eligible_nodes}
    measured = {}
    for row in rows:
        if type(row) is not dict:
            return refused("INVALID_NATIVE_ROW")
        node, trigger = row.get("node"), row.get("trigger_date")
        if type(node) is not str or type(trigger) is not str:
            return refused("INVALID_NATIVE_IDENTITY")
        key = (node, trigger)
        if key not in wanted_rows or key in measured:
            return refused("UNEXPECTED_OR_DUPLICATE_NATIVE_ROW")
        if (type(row.get("exec_date")) is not str or row["exec_date"] != wanted_rows[key]
                or type(row.get("hold_sessions")) is not int or row["hold_sessions"] != 21
                or any(not _finite(row.get(metric)) for metric in ("MFE", "MAE", "ret_exit"))):
            return refused("INVALID_NATIVE_MEASUREMENT")
        if (not -1 < row["MAE"] <= row["MFE"] or not -1 < row["ret_exit"]
                or not row["MAE"] <= row["ret_exit"] <= row["MFE"]):
            return refused("INCONSISTENT_NATIVE_MEASUREMENT")
        measured[key] = MeasuredEntry(node, trigger, row["exec_date"],
                                      row["MFE"], row["MAE"], row["ret_exit"], 21)
    if measured.keys() != wanted_rows.keys():
        return refused("MISSING_NATIVE_ROW")
    pairs = []
    for formation in formations:
        nodes = formation.eligible_nodes
        if not nodes:
            continue
        ordered = sorted(nodes, key=lambda node: (-values[(formation.calendar_index, node)], node))
        selected = tuple(ordered[:(len(nodes) + 1) // 2])
        baseline = tuple(measured[(node, formation.trigger_date)] for node in sorted(nodes))
        candidate = tuple(measured[(node, formation.trigger_date)] for node in selected)
        try:
            base_loss = math.fsum(max(0, -row.mae) for row in baseline) / len(baseline)
            selected_loss = math.fsum(max(0, -row.mae) for row in candidate) / len(candidate)
        except OverflowError:
            return refused("NONFINITE_AGGREGATE")
        if not _finite(base_loss - selected_loss):
            return refused("NONFINITE_AGGREGATE")
        pairs.append(PairedFormation(
            formation.calendar_index, formation.trigger_date, selected,
            tuple(node for node in sorted(nodes) if node not in selected), baseline, candidate,
            base_loss, selected_loss, base_loss - selected_loss,
        ))
    return EvaluationResult("DIAGNOSTIC_ONLY", (), coverage, tuple(pairs))
