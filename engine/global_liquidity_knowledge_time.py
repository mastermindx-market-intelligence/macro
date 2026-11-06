"""Pure knowledge-time (point-in-time eligibility) law for global-liquidity series.

Research/display tier: VALIDATED is False and CLAIM_LEVEL is
"knowledge_time_law_display_tier"; nothing in this module is a
trading-grade claim.

Six distinct clocks, never substituted for one another (C04):

1. economic period      -- when the measured economic window closed
                           (``economic_period_end``);
2. publication          -- when the source published the value
                           (``published_at``);
3. evidence available / first system known -- when this system could first
                           have held the value (``evidence_available_at``);
4. vintage              -- which release cohort carried the record
                           (``vintage_id``);
5. correction           -- when an amendment superseding retained truth
                           became known (``supersedes`` + correction evidence);
6. decision             -- the ``as_of`` instant the caller decides at.

BoJ-style month-end series are anchored to the month-end date, never a
month-start label (C09). Corrections are amendments layered on retained
first-known truth: the original value survives as the row value and eligible
corrections are recorded as amendments (C10). A "latest" vintage label or a
wrapper file's generated_at timestamp can never make evidence available
earlier than the system actually first knew it.

This module never reads the system clock: the caller always supplies the
wall clock and every as_of instant. Stdlib only.
"""

import calendar
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Iterable
from zoneinfo import ZoneInfo

__all__ = [
    "VALIDATED",
    "CLAIM_LEVEL",
    "AVAILABILITY_BASES",
    "LATEST_VINTAGE_LABELS",
    "PERIOD_ANCHORS",
    "KnowledgeTimeError",
    "anchor_month_end",
    "availability_start_utc",
    "earliest_possible_utc",
    "cutoff_utc",
    "Observation",
    "Amendment",
    "EligibleRow",
    "EligibilityResult",
    "eligible_as_of",
    "latest_by_series",
    "observation_from_wrapper",
]

VALIDATED = False
CLAIM_LEVEL = "knowledge_time_law_display_tier"

AVAILABILITY_BASES = (
    "first_system_known",
    "release_lag_aligned_reconstruction",
    "explicit_conservative_availability",
)
LATEST_VINTAGE_LABELS = frozenset({"latest", "current", "current_vintage"})
PERIOD_ANCHORS = ("period_end", "month_end")

_UTC = timezone.utc


class KnowledgeTimeError(ValueError):
    """Raised when a record or a decision instant violates the knowledge-time law."""


class _BoundKind(Enum):
    AWARE_DATETIME = "aware_datetime"
    DATE_ONLY = "date_only"


def _classify_bound(name: str, bound) -> _BoundKind:
    if isinstance(bound, datetime):
        if bound.tzinfo is None or bound.utcoffset() is None:
            raise KnowledgeTimeError(f"{name} is a naive datetime; supply an aware datetime or a date")
        return _BoundKind.AWARE_DATETIME
    if isinstance(bound, date):
        return _BoundKind.DATE_ONLY
    raise KnowledgeTimeError(f"{name} must be an aware datetime or a date, got {type(bound).__name__}")


def _zone(tz_name: str | None) -> ZoneInfo | None:
    """Resolve an IANA zone name, refusing unknown zones."""
    if tz_name is None:
        return None
    try:
        return ZoneInfo(tz_name)
    except Exception as exc:  # unknown or malformed zone names
        raise KnowledgeTimeError(f"unknown availability_tz: {tz_name!r}") from exc


def _required_zone(tz_name: str | None) -> ZoneInfo:
    zone = _zone(tz_name)
    if zone is None:
        raise KnowledgeTimeError("a date-only bound requires availability_tz (an IANA zone name)")
    return zone


def _local_midnight_utc(day: date, zone: ZoneInfo) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=zone).astimezone(_UTC)


def availability_start_utc(bound, tz_name: str | None) -> datetime:
    """First instant at which a bound is conservatively known to be available.

    An aware datetime is itself. A plain date ``d`` is NOT known until that
    local date has fully elapsed, so its availability starts at local
    midnight of ``d + 1`` in ``tz_name``, converted to UTC (conservative).
    """
    kind = _classify_bound("bound", bound)
    if kind is _BoundKind.AWARE_DATETIME:
        return bound.astimezone(_UTC)
    return _local_midnight_utc(bound + timedelta(days=1), _required_zone(tz_name))


def earliest_possible_utc(bound, tz_name: str | None) -> datetime:
    """Earliest instant a bound could possibly refer to (used only for the future-clock check).

    An aware datetime is itself. A plain date ``d`` could refer to any
    instant from local midnight of ``d`` in ``tz_name`` onwards.
    """
    kind = _classify_bound("bound", bound)
    if kind is _BoundKind.AWARE_DATETIME:
        return bound.astimezone(_UTC)
    return _local_midnight_utc(bound, _required_zone(tz_name))


def cutoff_utc(as_of, decision_tz: str | None) -> datetime:
    """Normalize the decision instant to UTC.

    An aware datetime is converted to UTC. A plain date means deciding at the
    start of that local date, which requires ``decision_tz``. A naive
    datetime is refused.
    """
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise KnowledgeTimeError("as_of is a naive datetime; supply an aware datetime or a date")
        return as_of.astimezone(_UTC)
    if isinstance(as_of, date):
        zone = _zone(decision_tz)
        if zone is None:
            raise KnowledgeTimeError("a date as_of requires decision_tz (an IANA zone name)")
        return _local_midnight_utc(as_of, zone)
    raise KnowledgeTimeError("as_of must be an aware datetime or a date")


def anchor_month_end(label: date) -> date:
    """Anchor a month label to the last calendar day of that month (C09)."""
    if isinstance(label, datetime) or not isinstance(label, date):
        raise KnowledgeTimeError("anchor_month_end expects a plain date, not a datetime")
    last_day = calendar.monthrange(label.year, label.month)[1]
    return date(label.year, label.month, last_day)


@dataclass(frozen=True)
class Observation:
    """A single point-in-time-known fact about an economic period.

    ``value`` is ``None`` when the component is genuinely missing (it is
    never zero-filled). ``evidence_available_at`` is REQUIRED evidence of
    when this system first knew the value: there is no fallback to a
    vintage label, a wrapper's generated_at, or the system clock.
    """

    series_id: str
    observation_id: str
    economic_period_end: date
    published_at: "date | datetime"
    evidence_available_at: "date | datetime"
    vintage_id: str
    value: "int | float | Decimal | None"
    is_correction: bool = False
    supersedes: "str | None" = None
    availability_basis: str = "first_system_known"
    period_anchor: str = "period_end"
    availability_tz: "str | None" = None

    def __post_init__(self) -> None:
        if isinstance(self.economic_period_end, datetime) or not isinstance(
            self.economic_period_end, date
        ):
            raise KnowledgeTimeError(
                "economic_period_end must be a plain date, not a datetime"
            )
        pub_kind = _classify_bound("published_at", self.published_at)
        ev_kind = _classify_bound("evidence_available_at", self.evidence_available_at)
        zone = _zone(self.availability_tz)
        if (pub_kind is _BoundKind.DATE_ONLY or ev_kind is _BoundKind.DATE_ONLY) and zone is None:
            raise KnowledgeTimeError(
                "a date-only bound requires availability_tz (an IANA zone name)"
            )
        if self.availability_basis not in AVAILABILITY_BASES:
            raise KnowledgeTimeError(
                f"availability_basis {self.availability_basis!r} not in {AVAILABILITY_BASES}"
            )
        if self.period_anchor not in PERIOD_ANCHORS:
            raise KnowledgeTimeError(
                f"period_anchor {self.period_anchor!r} not in {PERIOD_ANCHORS}"
            )
        if self.is_correction and not (isinstance(self.supersedes, str) and self.supersedes):
            raise KnowledgeTimeError("is_correction=True requires a non-empty supersedes observation_id")
        if not self.is_correction and self.supersedes:
            raise KnowledgeTimeError("supersedes requires is_correction=True")
        if (
            isinstance(self.vintage_id, str)
            and self.vintage_id.lower() in LATEST_VINTAGE_LABELS
            and self.availability_basis != "release_lag_aligned_reconstruction"
        ):
            raise KnowledgeTimeError(
                "a latest vintage is never first-known evidence; "
                "availability_basis must be release_lag_aligned_reconstruction"
            )

        # Backdating: evidence cannot be available before publication.
        published_start = availability_start_utc(self.published_at, self.availability_tz)
        evidence_start = availability_start_utc(self.evidence_available_at, self.availability_tz)
        if evidence_start < published_start:
            raise KnowledgeTimeError(
                "evidence_available_at precedes published_at (backdating refused)"
            )

        # The published END must not fall before the economic period even started.
        # For the default ``period_end`` anchor a same-day publication is lawful
        # by design: end-of-day fixings (e.g. ECB reference rates) publish on
        # the economic_period_end day itself. ``month_end`` (C09) is strict and
        # requires publication after that day has fully elapsed (below).
        period_zone = zone if zone is not None else ZoneInfo("UTC")
        period_day_start = _local_midnight_utc(self.economic_period_end, period_zone)
        if published_start < period_day_start:
            raise KnowledgeTimeError("published before the economic period ended")

        if self.period_anchor == "month_end":
            if self.economic_period_end != anchor_month_end(self.economic_period_end):
                raise KnowledgeTimeError("month-start label: anchor to month end (C09)")
            period_day_end = _local_midnight_utc(
                self.economic_period_end + timedelta(days=1), period_zone
            )
            published_earliest = earliest_possible_utc(self.published_at, self.availability_tz)
            if not published_earliest > period_day_end:
                raise KnowledgeTimeError(
                    "month_end anchor: published_at must be strictly after the end of "
                    "the economic_period_end day (C09)"
                )

    @property
    def evidence_start(self) -> datetime:
        """Availability start of the evidence bound, normalized to UTC."""
        return availability_start_utc(self.evidence_available_at, self.availability_tz)


@dataclass(frozen=True)
class Amendment:
    """An eligible correction: an amendment to retained first-known truth (C10)."""

    observation_id: str
    vintage_id: str
    value: "int | float | Decimal | None"
    evidence_available_at: datetime
    supersedes: str


@dataclass(frozen=True)
class EligibleRow:
    """An eligible (series, economic period): the first-known original plus amendments."""

    series_id: str
    economic_period_end: date
    observation_id: str
    value: "int | float | Decimal | None"
    evidence_available_at: datetime
    availability_basis: str
    vintage_id: str
    amendments: "tuple[Amendment, ...]"


@dataclass(frozen=True)
class EligibilityResult:
    """Outcome of an as-of eligibility decision, with its own clocks made explicit."""

    as_of_instant: datetime
    wall_clock: datetime
    rows: "tuple[EligibleRow, ...]"
    missing_required: "tuple[str, ...]"
    null_value_required: "tuple[str, ...]"
    coverage_complete: bool
    excluded_basis_count: int


def _root_original(record: Observation, by_id: "dict[str, Observation]") -> Observation:
    current = record
    seen: set[str] = set()
    while current.is_correction:
        if current.observation_id in seen:
            raise KnowledgeTimeError(f"correction cycle at {current.observation_id!r}")
        seen.add(current.observation_id)
        current = by_id[current.supersedes]
    return current


def _is_null_value(value: "int | float | Decimal | None") -> bool:
    """``None``, NaN or infinite (float or Decimal) is a null component value.

    A non-finite value is not coverage: it is reported in
    ``null_value_required`` exactly like ``None`` and never counts as present.
    """
    if value is None:
        return True
    if isinstance(value, Decimal):
        return not value.is_finite()
    if isinstance(value, float):
        return not math.isfinite(value)
    return False


def eligible_as_of(
    records: "Iterable[Observation]",
    as_of,
    *,
    wall_clock: datetime,
    required_series: "tuple[str, ...] | list[str]" = (),
    allowed_bases: "tuple[str, ...] | list[str]" = ("first_system_known",),
    decision_tz: "str | None" = None,
) -> EligibilityResult:
    """Decide which observations were eligible given what was knowable at ``as_of``."""
    if not isinstance(wall_clock, datetime) or wall_clock.tzinfo is None or wall_clock.utcoffset() is None:
        raise KnowledgeTimeError("wall_clock must be an aware datetime")
    wall_utc = wall_clock.astimezone(_UTC)
    cutoff = cutoff_utc(as_of, decision_tz)
    if cutoff > wall_utc:
        raise KnowledgeTimeError("as_of is after the supplied wall clock")

    record_list = list(records)
    by_id: "dict[str, Observation]" = {}
    for record in record_list:
        if record.observation_id in by_id:
            raise KnowledgeTimeError(f"duplicate observation_id: {record.observation_id!r}")
        by_id[record.observation_id] = record

    for record in record_list:
        if (
            earliest_possible_utc(record.evidence_available_at, record.availability_tz) > wall_utc
            or earliest_possible_utc(record.published_at, record.availability_tz) > wall_utc
        ):
            raise KnowledgeTimeError(
                f"record {record.observation_id!r} claims a future clock"
            )

    for record in record_list:
        if not record.is_correction:
            continue
        target = by_id.get(record.supersedes)
        if target is None:
            raise KnowledgeTimeError(
                f"dangling supersedes: {record.observation_id!r} names {record.supersedes!r}, "
                "which is not in the record set"
            )
        if target.series_id != record.series_id or target.economic_period_end != record.economic_period_end:
            raise KnowledgeTimeError(
                f"correction {record.observation_id!r} must not change series_id or "
                "economic_period_end relative to the record it supersedes"
            )
        if availability_start_utc(
            record.evidence_available_at, record.availability_tz
        ) <= availability_start_utc(target.evidence_available_at, target.availability_tz):
            raise KnowledgeTimeError(
                "a correction must be known strictly after the value it corrects"
            )

    seen_originals: "set[tuple[str, date]]" = set()
    for record in record_list:
        if record.is_correction:
            continue
        key = (record.series_id, record.economic_period_end)
        if key in seen_originals:
            raise KnowledgeTimeError(f"duplicate originals for series/period {key}")
        seen_originals.add(key)

    excluded_basis_count = 0
    eligible_ids: "set[str]" = set()
    for record in record_list:
        if record.availability_basis not in tuple(allowed_bases):
            excluded_basis_count += 1
            continue
        if availability_start_utc(record.evidence_available_at, record.availability_tz) <= cutoff:
            eligible_ids.add(record.observation_id)

    rows_by_key: "dict[tuple[str, date], EligibleRow]" = {}
    amendments_by_key: "dict[tuple[str, date], list[Amendment]]" = {}
    for record in record_list:
        if not record.is_correction and record.observation_id in eligible_ids:
            key = (record.series_id, record.economic_period_end)
            rows_by_key[key] = EligibleRow(
                series_id=record.series_id,
                economic_period_end=record.economic_period_end,
                observation_id=record.observation_id,
                value=record.value,
                evidence_available_at=availability_start_utc(
                    record.evidence_available_at, record.availability_tz
                ),
                availability_basis=record.availability_basis,
                vintage_id=record.vintage_id,
                amendments=(),
            )
    for record in record_list:
        if not record.is_correction or record.observation_id not in eligible_ids:
            continue
        root = _root_original(record, by_id)
        root_key = (root.series_id, root.economic_period_end)
        if root_key not in rows_by_key:
            continue  # an amendment is invisible when its root original is absent
        amendments_by_key.setdefault(root_key, []).append(
            Amendment(
                observation_id=record.observation_id,
                vintage_id=record.vintage_id,
                value=record.value,
                evidence_available_at=availability_start_utc(
                    record.evidence_available_at, record.availability_tz
                ),
                supersedes=record.supersedes,
            )
        )

    rows: "list[EligibleRow]" = []
    for key, row in rows_by_key.items():
        amendments = tuple(
            sorted(
                amendments_by_key.get(key, ()),
                key=lambda a: (a.evidence_available_at, a.observation_id),
            )
        )
        rows.append(EligibleRow(**{**row.__dict__, "amendments": amendments}))
    rows.sort(key=lambda r: (r.series_id, r.economic_period_end))

    rows_by_series: "dict[str, list[EligibleRow]]" = {}
    for row in rows:
        rows_by_series.setdefault(row.series_id, []).append(row)

    missing_required: "list[str]" = []
    null_value_required: "list[str]" = []
    seen_required: "set[str]" = set()
    for series_id in required_series:
        if series_id in seen_required:
            continue
        seen_required.add(series_id)
        if series_id not in rows_by_series:
            missing_required.append(series_id)
            continue
        latest = max(rows_by_series[series_id], key=lambda r: r.economic_period_end)
        if _is_null_value(latest.value):
            null_value_required.append(series_id)

    return EligibilityResult(
        as_of_instant=cutoff,
        wall_clock=wall_utc,
        rows=tuple(rows),
        missing_required=tuple(missing_required),
        null_value_required=tuple(null_value_required),
        coverage_complete=not missing_required and not null_value_required,
        excluded_basis_count=excluded_basis_count,
    )


def latest_by_series(result: EligibilityResult) -> "dict[str, EligibleRow]":
    """Per series, the eligible row with the greatest ``economic_period_end``."""
    latest: "dict[str, EligibleRow]" = {}
    for row in result.rows:
        current = latest.get(row.series_id)
        if current is None or row.economic_period_end > current.economic_period_end:
            latest[row.series_id] = row
    return latest


def observation_from_wrapper(
    *,
    series_id: str,
    observation_id: str,
    economic_period_end: date,
    published_at: "date | datetime",
    vintage_id: str,
    value: "int | float | Decimal | None",
    wrapper_generated_at: datetime,
    row_first_known_at: "datetime | None" = None,
    claimed_available_at: "datetime | None" = None,
    availability_tz: "str | None" = None,
    period_anchor: str = "period_end",
) -> Observation:
    """Build a first-system-known Observation from a wrapper file snapshot.

    ``wrapper_generated_at`` is when the wrapper file was generated;
    ``row_first_known_at`` is when the row was first ingested. Neither a
    wrapper timestamp nor a latest-vintage label can backdate availability:
    the evidence time is the later of first-known and any claimed instant.
    """
    for name, moment in (
        ("wrapper_generated_at", wrapper_generated_at),
        ("row_first_known_at", row_first_known_at),
        ("claimed_available_at", claimed_available_at),
    ):
        if moment is None:
            continue
        if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
            raise KnowledgeTimeError(f"{name} must be an aware datetime")
    first_known = (
        row_first_known_at if row_first_known_at is not None else wrapper_generated_at
    ).astimezone(_UTC)
    generated = wrapper_generated_at.astimezone(_UTC)
    if row_first_known_at is not None and first_known > generated:
        raise KnowledgeTimeError(
            "row_first_known_at is after wrapper_generated_at: a row cannot be first "
            "known after the file that carries it was generated"
        )
    claimed = claimed_available_at.astimezone(_UTC) if claimed_available_at is not None else None
    if claimed is not None and claimed < first_known:
        raise KnowledgeTimeError("wrapper/latest timestamp cannot backdate availability")
    evidence = max(first_known, claimed) if claimed is not None else first_known
    return Observation(
        series_id=series_id,
        observation_id=observation_id,
        economic_period_end=economic_period_end,
        published_at=published_at,
        evidence_available_at=evidence,
        vintage_id=vintage_id,
        value=value,
        is_correction=False,
        supersedes=None,
        availability_basis="first_system_known",
        period_anchor=period_anchor,
        availability_tz=availability_tz,
    )
