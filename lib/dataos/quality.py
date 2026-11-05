"""Quality — nine check families, four severities (Data OS §D8).

WHY THIS FILE EXISTS.  The house's existing detectors are excellent and each sees
exactly one thing: ``detect_stale_series`` is frame-grain (one live column keeps a
dead frame "fresh" — china_connect hid the death of ``net``/``buy``/``sell`` for ~2
years behind a still-ticking ``turnover``), ``detect_dark_columns`` fixed that at the
column grain, and the circuit breaker covers reachability.  None of them can answer
"is this dataset internally consistent", "is it complete against a universe", or "does
it claim to have known something before it could have".  This module is the missing
row of that table, expressed as PURE functions so a check is a unit test, not a
nightly.

FAMILIES: completeness · freshness · uniqueness · validity · continuity ·
distribution · cross-source reconciliation · referential integrity · temporal
integrity.

SEVERITIES: ``INFO`` (record) · ``WARN`` (annotate) · ``DEGRADED`` (serve, with a
user-visible degradation state) · ``BLOCK`` (refuse to publish).  Severity is
declared by the caller, not inferred here: the same missing row is INFO on a research
scratch table and BLOCK on a published tape, and only the contract knows which.

EVERY VALIDATOR IS PURE.  List-of-dicts in, :class:`Finding` list out; ``now`` is
INJECTED, never read from the wall clock (mirroring ``detect_dark_columns``, whose
docstring records the same rule and the same reason: the caller owns the clock, and a
test can pin it).  No pandas at import — these run in the thin CI lanes.

ANNOTATIONS ARE BARE PRINTS.  :func:`emit_annotations` prints at column 0 with
``flush=True`` and never touches a logger.  Every builder here configures logging with
a prefixing format, so ``log.warning("::warning …")`` emits ``WARNING ::warning …``,
GitHub only parses a workflow command when ``::`` sits at column 0, and the alarm
silently disappears.  That shipped dead five separate times (#3487, #3515, #3562,
#3563, #3570) before #3587 swept 69 sites and added
``tests/test_gh_annotation_line_start.py``.  ``flush`` is load-bearing: stdout is
block-buffered when piped in CI.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from decimal import Decimal
from fractions import Fraction

from lib.dataos.temporal import Clock, TemporalProfile, known_at, utc

__all__ = [
    "Severity",
    "CheckFamily",
    "Finding",
    "check_uniqueness",
    "check_validity_ohlc",
    "check_freshness",
    "check_completeness",
    "check_referential",
    "check_temporal_integrity",
    "annotation_line",
    "emit_annotations",
    "AgreementState",
    "InspectionOutcome",
    "DiscrepancyCause",
    "AgreementTolerance",
    "SourceSemantics",
    "AgreementInspection",
    "inspect_agreement",
    "agreement_findings",
]


class Severity(Enum):
    """What a finding obliges the pipeline to DO (§D8)."""

    INFO = "INFO"           # record it
    WARN = "WARN"           # annotate the run
    DEGRADED = "DEGRADED"   # serve, with a user-visible degradation state
    BLOCK = "BLOCK"         # refuse to publish


class CheckFamily(Enum):
    """The nine families of §D8."""

    COMPLETENESS = "completeness"
    FRESHNESS = "freshness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    CONTINUITY = "continuity"
    DISTRIBUTION = "distribution"
    CROSS_SOURCE = "cross_source_reconciliation"
    REFERENTIAL = "referential_integrity"
    TEMPORAL_INTEGRITY = "temporal_integrity"


@dataclass(frozen=True)
class Finding:
    """One quality defect, with the EVIDENCE that proves it.

    ``evidence`` is a mapping and not prose because a finding whose proof is only in
    its message cannot be re-checked, deduplicated, or counted.  ``message`` says what
    a human should do; ``evidence`` says what the checker actually saw.
    """

    family: CheckFamily
    severity: Severity
    dataset_id: str
    message: str
    evidence: dict = field(default_factory=dict)


def _finding(family, severity, dataset_id, message, evidence) -> Finding:
    return Finding(family=family, severity=severity, dataset_id=dataset_id,
                   message=message, evidence=evidence)


def _key(row: Mapping, key_cols: Sequence[str]) -> tuple:
    return tuple(row.get(c) for c in key_cols)


def check_uniqueness(
    rows: Iterable[Mapping],
    key_cols: Sequence[str],
    *,
    dataset_id: str = "",
    severity: Severity = Severity.BLOCK,
) -> list[Finding]:
    """Every ``key_cols`` tuple must appear at most once.

    ``BLOCK`` by default: a duplicated grain key silently multiplies whatever a
    consumer sums, and there is no downstream check that can see it.
    """
    counts: dict[tuple, int] = {}
    order: list[tuple] = []
    for row in rows:
        k = _key(row, key_cols)
        if k not in counts:
            order.append(k)
        counts[k] = counts.get(k, 0) + 1
    findings = []
    for k in order:
        if counts[k] > 1:
            findings.append(_finding(
                CheckFamily.UNIQUENESS, severity, dataset_id,
                f"duplicate grain key {dict(zip(key_cols, k))} appears {counts[k]}x — "
                "anything a consumer sums over this grain is multiplied",
                {"key_cols": list(key_cols), "key": list(k), "count": counts[k]},
            ))
    return findings


_OHLC_FIELDS = ("open", "high", "low", "close")


def _num(value) -> float | None:
    """A comparable number, or ``None`` for anything that is not one.

    ``None`` and ``NaN`` are SKIPPED rather than raised on: a missing leg is a
    completeness/null question (``lib/dataos/nulls.py``) and answering it here would
    turn every gap into a spurious validity failure — which is how a validator gets
    turned off.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return None if math.isnan(f) else f
    return None


def check_validity_ohlc(
    rows: Iterable[Mapping],
    *,
    dataset_id: str = "",
    severity: Severity = Severity.BLOCK,
) -> list[Finding]:
    """A bar must be internally possible: high >= low, high >= open/close,
    low <= open/close, volume >= 0.

    Rows where a field is absent or null are SKIPPED, not flagged and not raised on
    — ``data/stocks`` has no ``open`` column at all (§D4), so a validator that
    demanded four legs would fail on every row of a real store and be disabled within
    a day.
    """
    findings: list[Finding] = []
    for i, row in enumerate(rows):
        vals = {f: _num(row.get(f)) for f in _OHLC_FIELDS}
        high, low, opn, close = vals["high"], vals["low"], vals["open"], vals["close"]
        if high is not None and low is not None and high < low:
            findings.append(_finding(
                CheckFamily.VALIDITY, severity, dataset_id,
                f"row {i}: high {high} < low {low} — the bar is impossible",
                {"row_index": i, "high": high, "low": low},
            ))
        for name, value in (("open", opn), ("close", close)):
            if high is not None and value is not None and value > high:
                findings.append(_finding(
                    CheckFamily.VALIDITY, severity, dataset_id,
                    f"row {i}: {name} {value} > high {high}",
                    {"row_index": i, "field": name, "value": value, "high": high},
                ))
            if low is not None and value is not None and value < low:
                findings.append(_finding(
                    CheckFamily.VALIDITY, severity, dataset_id,
                    f"row {i}: {name} {value} < low {low}",
                    {"row_index": i, "field": name, "value": value, "low": low},
                ))
        volume = _num(row.get("volume"))
        if volume is not None and volume < 0:
            findings.append(_finding(
                CheckFamily.VALIDITY, severity, dataset_id,
                f"row {i}: volume {volume} is negative",
                {"row_index": i, "volume": volume},
            ))
    return findings


def check_freshness(
    newest_ts: datetime | str | None,
    sla_hours: float,
    now: datetime | str,
    *,
    dataset_id: str = "",
    severity: Severity = Severity.DEGRADED,
) -> list[Finding]:
    """Is the newest observation inside the dataset's freshness SLA?

    ``now`` is injected so the check is pure and a test can pin it.  A ``None``
    newest observation is an EMPTY dataset, which is a freshness failure with an
    unbounded age — deliberately reported as ``age_hours: None`` rather than a magic
    number a consumer could average or sort as if it were a real age
    (same rule as ``detect_dark_columns``).
    """
    now_utc = utc(now)
    if newest_ts is None:
        return [_finding(
            CheckFamily.FRESHNESS, severity, dataset_id,
            f"dataset has no observation at all (SLA {sla_hours}h)",
            {"age_hours": None, "sla_hours": sla_hours, "as_of": now_utc.isoformat()},
        )]
    newest = utc(newest_ts)
    age_hours = (now_utc - newest).total_seconds() / 3600.0
    if age_hours > sla_hours:
        return [_finding(
            CheckFamily.FRESHNESS, severity, dataset_id,
            f"newest observation {newest.isoformat()} is {age_hours:.1f}h old, past its "
            f"{sla_hours}h SLA",
            {"age_hours": round(age_hours, 3), "sla_hours": sla_hours,
             "newest": newest.isoformat(), "as_of": now_utc.isoformat()},
        )]
    return []


def check_completeness(
    rows: Iterable[Mapping],
    expected_keys: Iterable[str],
    *,
    dataset_id: str = "",
    severity: Severity = Severity.WARN,
) -> list[Finding]:
    """Every row must carry every expected key, non-null.

    Row-grain completeness: a key that is absent and a key that is present-but-null
    are the SAME defect to a consumer (both arrive as ``None``), so both are reported
    — with ``present`` in the evidence, because the repair differs (fix the writer vs
    fix the source).
    """
    wanted = tuple(expected_keys)
    findings: list[Finding] = []
    for i, row in enumerate(rows):
        for key in wanted:
            present = key in row
            if present and row.get(key) is not None:
                continue
            findings.append(_finding(
                CheckFamily.COMPLETENESS, severity, dataset_id,
                f"row {i}: {key!r} is " + ("null" if present else "absent"),
                {"row_index": i, "key": key, "present": present},
            ))
    return findings


def check_referential(
    rows: Iterable[Mapping],
    id_col: str,
    known_ids: Iterable[str],
    *,
    dataset_id: str = "",
    severity: Severity = Severity.BLOCK,
) -> list[Finding]:
    """Every ``id_col`` value must exist in *known_ids* (the master).

    This is the check that would have caught the MMC incident from the other side:
    a basket declaring 19 members while the price store answers for 18 is a dangling
    reference, and today nothing anywhere compares the two.
    """
    universe = set(known_ids)
    findings: list[Finding] = []
    for i, row in enumerate(rows):
        value = row.get(id_col)
        if value is None or value in universe:
            continue
        findings.append(_finding(
            CheckFamily.REFERENTIAL, severity, dataset_id,
            f"row {i}: {id_col}={value!r} is not in the known id universe "
            f"({len(universe)} ids)",
            {"row_index": i, "id_col": id_col, "value": value},
        ))
    return findings


def check_temporal_integrity(
    rows: Iterable[Mapping],
    profile: TemporalProfile,
    *,
    now: datetime | str,
    dataset_id: str = "",
    severity: Severity = Severity.BLOCK,
) -> list[Finding]:
    """Clocks must be physically possible.

    Two invariants, both of which a silent violation of makes a backtest LOOK better:

    * ``known_at`` may not be in the future relative to the injected *now* — a row
      that claims it will be knowable tomorrow is either a clock bug or a leak.
    * ``effective_at`` may not precede ``period_end`` where both exist — information
      cannot become applicable before the interval it describes has closed.

    ``now`` is keyword-only and has NO default: a default would read the wall clock
    and make the function impure, and an impure quality check cannot be a unit test.
    Rows the profile cannot answer ``known_at`` for are reported as findings rather
    than raising, because a checker that dies on row 3 tells you nothing about rows
    4..n.
    """
    now_utc = utc(now)
    findings: list[Finding] = []
    for i, row in enumerate(rows):
        try:
            k = known_at(row, profile)
        except Exception as exc:  # noqa: BLE001 — a bad row is a finding, not a crash
            findings.append(_finding(
                CheckFamily.TEMPORAL_INTEGRITY, severity, dataset_id,
                f"row {i}: known_at is unanswerable — {exc}",
                {"row_index": i, "profile": profile.value if hasattr(profile, "value") else str(profile)},
            ))
        else:
            if k > now_utc:
                findings.append(_finding(
                    CheckFamily.TEMPORAL_INTEGRITY, severity, dataset_id,
                    f"row {i}: known_at {k.isoformat()} is in the FUTURE relative to "
                    f"{now_utc.isoformat()}",
                    {"row_index": i, "known_at": k.isoformat(), "now": now_utc.isoformat()},
                ))
        effective = row.get(Clock.EFFECTIVE_AT.value)
        period_end = row.get(Clock.PERIOD_END.value)
        if effective is not None and period_end is not None:
            try:
                eff, end = utc(effective), utc(period_end)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                findings.append(_finding(
                    CheckFamily.TEMPORAL_INTEGRITY, severity, dataset_id,
                    f"row {i}: effective_at/period_end are not usable timestamps — {exc}",
                    {"row_index": i},
                ))
                continue
            if eff < end:
                findings.append(_finding(
                    CheckFamily.TEMPORAL_INTEGRITY, severity, dataset_id,
                    f"row {i}: effective_at {eff.isoformat()} precedes period_end "
                    f"{end.isoformat()} — information cannot apply before its interval closed",
                    {"row_index": i, "effective_at": eff.isoformat(),
                     "period_end": end.isoformat()},
                ))
    return findings


_ANNOTATION_LEVEL: dict[Severity, str] = {
    Severity.INFO: "notice",
    Severity.WARN: "warning",
    Severity.DEGRADED: "warning",
    Severity.BLOCK: "error",
}


def annotation_line(finding: Finding) -> str:
    """Render one finding as a SINGLE GitHub Actions annotation line.

    The caller MUST emit this with a bare ``print(..., flush=True)`` — see
    :func:`emit_annotations` and this module's docstring for what happens otherwise.
    """
    level = _ANNOTATION_LEVEL.get(finding.severity, "warning")
    slug = f"{finding.family.value}-{finding.severity.value.lower()}"
    where = f"{finding.dataset_id}: " if finding.dataset_id else ""
    message = " ".join(str(finding.message).split())
    return f"::{level} title={slug}::{where}{message}"


def emit_annotations(findings: Iterable[Finding]) -> int:
    """Print one GitHub annotation per finding; return how many were emitted.

    BARE print, never ``log.*``: a logger's prefixing format pushes ``::`` off column
    0 and GitHub drops the annotation entirely.  ``flush`` is load-bearing — stdout is
    block-buffered when piped in CI.
    """
    count = 0
    for finding in findings:
        print(annotation_line(finding), flush=True)
        count += 1
    return count


# ── cross-source agreement (C03; CheckFamily.CROSS_SOURCE) ──
#
# Masterplan §9: the canonical view is a DECLARED answer, not a vote among feeds —
# instrument, session, currency, trade eligibility, timestamp convention,
# adjustment/reference and observation revision are compared FIRST, values only
# after, and only on actual overlapping observations in the same window, under
# DECLARED tolerances, in exact arithmetic.  ARCHITECTURE §7 fixes the agreement
# vocabulary below; its escalation (quarantine, last-good, incident) is NOT built
# here.  D00: never average incompatible sources; D00.A1.3: a TRADJ series is never
# compared against a printed price.
#
# A malformed DECLARATION is a caller bug → ValueError/TypeError.  A disagreement in
# the DATA is never an exception — it is an inspection result, retained with its raw
# values, never voted, averaged or preferred into a consensus.


class AgreementState(Enum):
    """ARCHITECTURE §7's agreement vocabulary — exactly these five, in this order."""

    AGREE = "AGREE"                          # equal within the declared absolute precision
    WITHIN_TOLERANCE = "WITHIN_TOLERANCE"    # independent; |a-b| <= within * max(|a|,|b|)
    DISCREPANT_MINOR = "DISCREPANT_MINOR"    # independent; |a-b| <= minor * max(|a|,|b|)
    DISCREPANT_MAJOR = "DISCREPANT_MAJOR"    # beyond minor (independent) or precision (same generation)
    UNRESOLVED = "UNRESOLVED"                # no value on a side, an incompatible pair, or an
    #                                            independent discrepancy RETAINED, never voted away


class InspectionOutcome(Enum):
    """What the inspection was able to DO, declared before any value is examined."""

    COMPARED = "COMPARED"                    # semantics compatible, keys unique, overlap sufficient
    INCOMPATIBLE = "INCOMPATIBLE"            # a declared semantic differs; rows were NEVER examined
    INSUFFICIENT_OVERLAP = "INSUFFICIENT_OVERLAP"  # fewer exact-key overlaps than declared min_overlap
    DUPLICATE_KEY = "DUPLICATE_KEY"          # a key repeats on a side; the grain is ambiguous


class DiscrepancyCause(Enum):
    """Exactly two members — there is NO vendor-error member: causes stay unknown."""

    SEMANTIC_DIFFERENCE = "SEMANTIC_DIFFERENCE"  # the declarations differ (the explanation names which)
    UNKNOWN = "UNKNOWN"                          # every other non-agreement: unknown stays unknown


_SEMANTIC_KEYS = (
    "instrument", "session", "currency", "price_type", "timestamp_convention",
    "basis", "adjustment_reference", "unit",
)

_EVIDENCE_SAMPLE = 5


def _tolerance_field(name: str, raw) -> Fraction:
    """One declared tolerance as an exact :class:`Fraction`, or a refusal."""
    if isinstance(raw, bool) or isinstance(raw, float):
        raise TypeError(
            f"{name}: declare the tolerance exactly (int, Fraction, Decimal or str), "
            f"not {type(raw).__name__} — a float is a binary approximation")
    if isinstance(raw, Fraction):
        value = raw
    elif isinstance(raw, int):
        value = Fraction(raw)
    elif isinstance(raw, Decimal):
        if not raw.is_finite():
            raise ValueError(f"{name}: the tolerance must be finite, got {raw}")
        value = Fraction(raw)
    elif isinstance(raw, str):
        try:
            value = Fraction(raw.strip())
        except (ValueError, ZeroDivisionError, ArithmeticError) as exc:
            raise ValueError(f"{name}: unparseable tolerance {raw!r}") from exc
    else:
        raise TypeError(
            f"{name}: the tolerance must be int, Fraction, finite Decimal or str, "
            f"got {type(raw).__name__}")
    if value < 0:
        raise ValueError(f"{name}: the tolerance must be non-negative, got {value}")
    return value


@dataclass(frozen=True)
class AgreementTolerance:
    """The caller's DECLARED comparison bands — exact quantities, never floats.

    ``precision`` is ABSOLUTE in the value's unit; ``within`` and ``minor`` are
    RELATIVE (fractions of ``max(|a|,|b|)``).  A ``float`` tolerance is refused: a
    band that is itself a binary approximation cannot judge a boundary inclusive
    and exact.  Everything is normalised to :class:`Fraction` so every comparison
    below is exact.
    """

    precision: Fraction
    within: Fraction
    minor: Fraction

    def __post_init__(self) -> None:
        for name in ("precision", "within", "minor"):
            object.__setattr__(self, name, _tolerance_field(name, getattr(self, name)))
        if self.within > self.minor:
            raise ValueError(
                f"within ({self.within}) must not exceed minor ({self.minor})")


@dataclass(frozen=True)
class SourceSemantics:
    """The DECLARATION of one source — compared exactly as declared, never normalised.

    ``source_id`` + ``generation`` identify the source and its observation
    revision / view generation.  ``price_type`` carries trade eligibility
    (``"CLOSING_AUCTION"``, ``"CONSOLIDATED_LAST"``); ``basis`` carries the D00 view
    basis (``"RAW"``, ``"SADJ"``, ``"TRADJ"``); ``adjustment_reference`` names the
    action set an adjusted basis was built under (``""`` is allowed for RAW).  No
    case-folding, no aliasing: a declaration is compared exactly as declared.
    """

    source_id: str
    generation: str
    instrument: str
    session: str
    currency: str
    price_type: str
    timestamp_convention: str
    basis: str
    adjustment_reference: str
    unit: str

    def __post_init__(self) -> None:
        for name in ("source_id", "generation", *_SEMANTIC_KEYS):
            declared = getattr(self, name)
            if not isinstance(declared, str):
                raise ValueError(
                    f"{name}: a source declaration must be str, "
                    f"got {type(declared).__name__}")
            if name != "adjustment_reference" and not declared.strip():
                raise ValueError(f"{name}: a source declaration must be non-empty")


@dataclass(frozen=True)
class PairObservation:
    """One exact-key overlap with the RAW values exactly as given.

    ``left``/``right`` are never converted, rounded or replaced: a retained
    discrepancy must stay re-checkable against what each source actually said.
    """

    key: tuple
    left: object
    right: object
    state: AgreementState
    abs_diff: Fraction | None
    rel_diff: Fraction | None


@dataclass(frozen=True)
class RatioStep:
    """An observed SHAPE consistent with a one-sided adjustment — not proof of one.

    ``boundary`` is ``(last key of the first run, first key of the second run)``: an
    INTERVAL between two sampled keys, never an inferred event date (C03.03).  A
    step never sets a cause; it is reported and nothing more.
    """

    before: Fraction
    after: Fraction
    first_run: int
    second_run: int
    boundary: tuple


@dataclass(frozen=True)
class AgreementInspection:
    """The result of one cross-source inspection.  No consensus, no golden, no pick.

    Every non-agreement is RETAINED here — in ``observations``, with raw values —
    and never voted, averaged or preferred away (C03.01, C03.04).
    """

    outcome: InspectionOutcome
    state: AgreementState
    cause: DiscrepancyCause | None
    same_generation: bool
    explanation: tuple
    overlap: int | None
    left_only: int | None
    right_only: int | None
    left_unkeyed: int | None
    right_unkeyed: int | None
    duplicate_keys: tuple
    observations: tuple
    ratio_step: RatioStep | None

    def counts(self) -> dict[str, int]:
        """``{state value: n}`` over ALL five states, zeros included."""
        tally = {s.value: 0 for s in AgreementState}
        for obs in self.observations:
            tally[obs.state.value] += 1
        return tally


def _exact(v) -> Fraction | None:
    """The declared value as an exact :class:`Fraction`, or ``None`` if there is none.

    A finite ``float`` is read through ``repr`` — its shortest round-trip decimal —
    so ``114.8`` is exactly 1148/10 and ``114.8 / 57.4`` is exactly 2.  A missing
    value is NEVER zero (C03.04).
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, Decimal):
        return Fraction(v) if v.is_finite() else None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return Fraction(repr(v))
    return None


def _index_side(rows, keys: Sequence[str]) -> tuple[dict[tuple, object], int, set[tuple]]:
    """Materialise one side ONCE: first row per exact key, unkeyed count, duplicates.

    A key with ANY ``None`` component is UNKEYED — counted, never indexed, never
    compared.  A key seen twice on a side is a duplicate: a finding, not a crash.
    """
    positions: dict[tuple, object] = {}
    seen: set[tuple] = set()
    duplicated: set[tuple] = set()
    unkeyed = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError(
                f"every row must be a Mapping, got {type(row).__name__}")
        k = _key(row, keys)
        if k in seen:
            duplicated.add(k)
        seen.add(k)
        if any(component is None for component in k):
            unkeyed += 1
            continue
        if k not in positions:
            positions[k] = row
    return positions, unkeyed, duplicated


def _sorted_keys(keys_iterable) -> list[tuple]:
    """Overlap keys in sorted order, falling back to their string form."""
    keys_list = list(keys_iterable)
    try:
        return sorted(keys_list)
    except TypeError:
        return sorted(keys_list, key=lambda k: tuple(str(c) for c in k))


def inspect_agreement(
    left_rows,
    left: SourceSemantics,
    right_rows,
    right: SourceSemantics,
    *,
    keys: Sequence[str],
    value_col: str,
    tolerance: AgreementTolerance,
    min_overlap: int,
) -> AgreementInspection:
    """Compare two DECLARED sources: semantics first, values only on exact-key overlap.

    The four keyword-only declarations have NO defaults: a tolerance or an overlap
    the caller did not declare is a bug, not a preset.  Order of operations is
    frozen: declarations → semantics → index → overlap → sufficiency → compare.
    An incompatible pair is returned BEFORE the rows are ever iterated.
    """
    if isinstance(keys, str) or not isinstance(keys, Sequence):
        raise TypeError(
            "keys: a non-empty sequence of column names is required, got "
            + ("a bare str" if isinstance(keys, str) else type(keys).__name__))
    if not keys:
        raise ValueError("keys: must name at least one column")
    for col in keys:
        if not isinstance(col, str) or not col:
            raise ValueError(
                f"keys: every key column must be a non-empty str, got {col!r}")
    if not isinstance(value_col, str) or not value_col:
        raise ValueError("value_col: must be a non-empty str")
    if value_col in keys:
        raise ValueError(
            f"value_col ({value_col!r}) must not also be a key column")
    if not isinstance(tolerance, AgreementTolerance):
        raise TypeError(
            f"tolerance: must be an AgreementTolerance, got {type(tolerance).__name__}")
    if not isinstance(left, SourceSemantics) or not isinstance(right, SourceSemantics):
        raise TypeError(
            "left/right: must be SourceSemantics declarations, got "
            f"{type(left).__name__} and {type(right).__name__}")
    if isinstance(min_overlap, bool) or not isinstance(min_overlap, int):
        raise TypeError(
            f"min_overlap: must be an int, got {type(min_overlap).__name__}")
    if min_overlap < 1:
        raise ValueError(f"min_overlap: must be >= 1, got {min_overlap}")

    explanation = tuple(
        (name, getattr(left, name), getattr(right, name))
        for name in _SEMANTIC_KEYS
        if getattr(left, name) != getattr(right, name)
    )
    if left.source_id == right.source_id and left.generation != right.generation:
        explanation += (("generation", left.generation, right.generation),)
    same_generation = (left.source_id == right.source_id
                       and left.generation == right.generation)
    if explanation:
        return AgreementInspection(
            InspectionOutcome.INCOMPATIBLE, AgreementState.UNRESOLVED,
            DiscrepancyCause.SEMANTIC_DIFFERENCE, same_generation, explanation,
            None, None, None, None, None, (), (), None)

    left_index, left_unkeyed, left_dups = _index_side(left_rows, keys)
    right_index, right_unkeyed, right_dups = _index_side(right_rows, keys)
    if left_dups or right_dups:
        duplicate_keys = tuple(
            (side, k)
            for side, dups in (("left", left_dups), ("right", right_dups))
            for k in _sorted_keys(dups)
        )
        return AgreementInspection(
            InspectionOutcome.DUPLICATE_KEY, AgreementState.UNRESOLVED,
            DiscrepancyCause.UNKNOWN, same_generation, (), None, None, None,
            left_unkeyed, right_unkeyed, duplicate_keys, (), None)

    overlap = _sorted_keys(set(left_index) & set(right_index))
    left_only = len(set(left_index) - set(right_index))
    right_only = len(set(right_index) - set(left_index))
    if len(overlap) < min_overlap:
        return AgreementInspection(
            InspectionOutcome.INSUFFICIENT_OVERLAP, AgreementState.UNRESOLVED,
            DiscrepancyCause.UNKNOWN, same_generation, (), len(overlap),
            left_only, right_only, left_unkeyed, right_unkeyed, (), (), None)

    observations: list[PairObservation] = []
    for k in overlap:
        left_raw = left_index[k].get(value_col)
        right_raw = right_index[k].get(value_col)
        a, b = _exact(left_raw), _exact(right_raw)
        if a is None or b is None:
            observations.append(PairObservation(
                k, left_raw, right_raw, AgreementState.UNRESOLVED, None, None))
            continue
        d = abs(a - b)
        m = max(abs(a), abs(b))
        rel = d / m if m != 0 else None
        if same_generation:
            state = (AgreementState.AGREE if d <= tolerance.precision
                     else AgreementState.DISCREPANT_MAJOR)
        elif d <= tolerance.precision:
            state = AgreementState.AGREE
        elif rel is not None and d <= tolerance.within * m:
            state = AgreementState.WITHIN_TOLERANCE
        elif rel is not None and d <= tolerance.minor * m:
            state = AgreementState.DISCREPANT_MINOR
        else:
            state = AgreementState.DISCREPANT_MAJOR
        observations.append(PairObservation(k, left_raw, right_raw, state, d, rel))

    states = [obs.state for obs in observations]
    if same_generation:
        if AgreementState.DISCREPANT_MAJOR in states:
            overall = AgreementState.DISCREPANT_MAJOR
        elif AgreementState.UNRESOLVED in states:
            overall = AgreementState.UNRESOLVED
        else:
            overall = AgreementState.AGREE
    elif all(s is AgreementState.AGREE for s in states):
        overall = AgreementState.AGREE
    elif all(s in (AgreementState.AGREE, AgreementState.WITHIN_TOLERANCE)
             for s in states):
        overall = AgreementState.WITHIN_TOLERANCE
    else:
        overall = AgreementState.UNRESOLVED
    cause = (None if overall in (AgreementState.AGREE,
                                 AgreementState.WITHIN_TOLERANCE)
             else DiscrepancyCause.UNKNOWN)
    return AgreementInspection(
        InspectionOutcome.COMPARED, overall, cause, same_generation, (),
        len(overlap), left_only, right_only, left_unkeyed, right_unkeyed,
        (), tuple(observations), _ratio_step(observations, tolerance))


def _ratio_step(observations: Sequence[PairObservation],
                tolerance: AgreementTolerance) -> RatioStep | None:
    """The observed SHAPE of a ratio that changed once — never a cause (C03.03).

    Defined only when EVERY overlapping observation is valued and nonzero on both
    sides.  Ratios are grouped into runs (a ratio joins the current run while it
    stays within ``within`` of the run's FIRST ratio); the step is reported only for
    exactly two runs of length >= 2 where exactly one run is unity.
    """
    ratios: list[Fraction] = []
    for obs in observations:
        a, b = _exact(obs.left), _exact(obs.right)
        if a is None or b is None or a == 0 or b == 0:
            return None
        ratios.append(b / a)
    if len(ratios) < 4:
        return None
    runs: list[list[Fraction]] = [[ratios[0]]]
    for r in ratios[1:]:
        if abs(r / runs[-1][0] - 1) <= tolerance.within:
            runs[-1].append(r)
        else:
            runs.append([r])
    if len(runs) != 2 or len(runs[0]) < 2 or len(runs[1]) < 2:
        return None

    def _unity(run: list[Fraction]) -> bool:
        return all(abs(r - 1) <= tolerance.within for r in run)

    if [ _unity(runs[0]), _unity(runs[1]) ].count(True) != 1:
        return None
    split = len(runs[0]) - 1
    return RatioStep(
        before=ratios[0],
        after=ratios[split + 1],
        first_run=len(runs[0]),
        second_run=len(runs[1]),
        boundary=(observations[split].key, observations[split + 1].key),
    )


def _agreement_evidence(inspection: AgreementInspection) -> dict:
    """Bounded, JSON-serialisable evidence — no raw dump, no verdict about anyone."""
    sample = [
        [[str(c) for c in obs.key], repr(obs.left), repr(obs.right), obs.state.value]
        for obs in inspection.observations
        if obs.state not in (AgreementState.AGREE, AgreementState.WITHIN_TOLERANCE)
    ][:_EVIDENCE_SAMPLE]
    step = None
    if inspection.ratio_step is not None:
        s = inspection.ratio_step
        step = {
            "before": str(s.before),
            "after": str(s.after),
            "first_run": s.first_run,
            "second_run": s.second_run,
            "boundary": [[str(c) for c in s.boundary[0]],
                         [str(c) for c in s.boundary[1]]],
        }
    return {
        "outcome": inspection.outcome.value,
        "state": inspection.state.value,
        "cause": inspection.cause.value if inspection.cause is not None else None,
        "same_generation": inspection.same_generation,
        "explanation": [[name, lv, rv] for name, lv, rv in inspection.explanation],
        "overlap": inspection.overlap,
        "left_only": inspection.left_only,
        "right_only": inspection.right_only,
        "left_unkeyed": inspection.left_unkeyed,
        "right_unkeyed": inspection.right_unkeyed,
        "duplicate_keys": [
            [side, [str(c) for c in k]]
            for side, k in inspection.duplicate_keys[:_EVIDENCE_SAMPLE]
        ],
        "duplicate_key_count": len(inspection.duplicate_keys),
        "counts": inspection.counts(),
        "sample": sample,
        "ratio_step": step,
    }


def agreement_findings(
    inspection: AgreementInspection,
    *,
    dataset_id: str = "",
    severity: Severity = Severity.WARN,
) -> list[Finding]:
    """One CROSS_SOURCE finding per non-agreement inspection — or none at all.

    Severity is the CALLER's declaration (module law); ``WARN`` is only the default.
    The evidence is bounded and JSON-serialisable; the message names the outcome and
    state, never a cause, a vendor or a winner — unknown causes stay unknown.
    """
    if not isinstance(inspection, AgreementInspection):
        raise TypeError(
            "inspection: must be an AgreementInspection, got "
            f"{type(inspection).__name__}")
    if inspection.state in (AgreementState.AGREE, AgreementState.WITHIN_TOLERANCE):
        return []
    head = (f"cross-source inspection: {inspection.outcome.value}/"
            f"{inspection.state.value}")
    if inspection.outcome is InspectionOutcome.INCOMPATIBLE:
        named = ", ".join(name for name, _, _ in inspection.explanation)
        message = (f"{head} — the declarations differ on {named};"
                   " the rows were never examined")
    elif inspection.outcome is InspectionOutcome.COMPARED:
        not_agree = sum(
            1 for obs in inspection.observations
            if obs.state not in (AgreementState.AGREE, AgreementState.WITHIN_TOLERANCE))
        message = (f"{head} — {not_agree} of {inspection.overlap} overlapping "
                   "observations not in agreement; retained, not reconciled")
    else:
        message = f"{head} — nothing compared"
    return [_finding(CheckFamily.CROSS_SOURCE, severity, dataset_id, message,
                     _agreement_evidence(inspection))]
