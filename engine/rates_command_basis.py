"""rates_command_basis.v1 -- basis-aware qualified-comparison contract (B0).

Pure stdlib module freezing the qualified-observation basis contract for the
Rates & Inflation Command board: every numeric operand travels with its full
basis record (basket/index, reference interval, unit, vintage, rights,
evidence class, publication cutoff) and every cross-basis comparison is
refused, not-identified or explicitly transformed instead of silently
subtracted (acceptance case A06).

Semantic laws implemented (MASTERPLAN para-4 / seat ruling 2026-10-14):
- None on a basis field means UNKNOWN; unknown basis never yields a number.
- ``n/a`` marks a field explicitly not applicable to the target.
- missing != zero != neutral; a non-present value never compares numerically.
- an evidence timestamp after the qualification cutoff refuses the value.
- ZQ (monthly-average EFFR) and SR3 (compounded SOFR quarter) never
  interchange; CPI != PCE; par != zero != forward; build time != evidence
  time; the evidence class travels with the value.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields as dc_fields
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

SCHEMA_VERSION = "rates_command_basis.v1"

NA = "n/a"


class EvidenceClass(str, Enum):
    OFFICIAL_MEASUREMENT = "official_measurement"
    HOUSE_ESTIMATE = "house_estimate"
    MARKET_IMPLIED_EXPECTATION = "market_implied_expectation"
    SURVEY_PARTICIPANT_PROJECTION = "survey_participant_projection"
    ESTIMATED_DECOMPOSITION = "estimated_decomposition"
    HYPOTHETICAL_SCENARIO = "hypothetical_scenario"


class ValueState(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    WITHHELD = "withheld"
    STALE = "stale"
    REFUSED = "refused"


class Precision(str, Enum):
    MINUTE = "minute"
    DAY = "day"
    MONTH = "month"
    UNKNOWN = "unknown"


class ComparisonStatus(str, Enum):
    DIRECTLY_COMPARABLE = "directly_comparable"
    COMPARABLE_AFTER_TRANSFORMATION = "comparable_after_transformation"
    NOT_COMPARABLE = "not_comparable"
    NOT_IDENTIFIED = "not_identified"
    UNAVAILABLE = "unavailable"


class PathStatus(str, Enum):
    IDENTIFIED_CONDITIONAL = "identified_conditional"
    FEASIBLE_ALTERNATIVES = "feasible_alternatives"
    INCONSISTENT = "inconsistent"
    MISSING_INPUTS = "missing_inputs"


UNIT_VALUES = (
    "pct_mom", "pct_yoy", "pct_ann_rate", "pct_3m_ann", "index_level",
    "thousands_persons", "persons", "bp",
)
QUALITY_FLAGS = (
    "stale", "carried", "interpolated", "fallback_strip", "proxy_vintage",
    "accuracy_withheld", "benchmark_only", "experimental",
)
RIGHTS_VALUES = ("public_official", "redistribution_limited", "display_only", "unknown")
SEASONAL_VALUES = ("sa", "nsa", NA)
RATE_INDEX_VALUES = ("EFFR", "SOFR", NA)
AVERAGING_VALUES = ("arithmetic_calendar_day", "compounded_business_day", "point", NA)
CURVE_VALUES = ("par", "zero", "forward", "real_par", NA)
PCT_UNITS = ("pct_mom", "pct_yoy", "pct_ann_rate", "pct_3m_ann")


def _jsonify(obj: Any) -> Any:
    """Convert enums/tuples to plain JSON types (stable wire shape)."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (tuple, list)):
        return [_jsonify(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    return obj


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        _jsonify(dict(payload)), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _digest16(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]


_COARSER_GRANULARITY = {"month": 0, "day": 1, "instant": 2}


@dataclass(frozen=True)
class _Stamp:
    """One parsed publication stamp (private parser state).

    ``granularity`` is ``month`` (``YYYY-MM``), ``day`` (``YYYY-MM-DD``) or
    ``instant`` (any ISO datetime). ``utc`` is the exact aware-UTC instant
    for ``instant`` stamps and None for month/day stamps. A naive datetime
    is interpreted as UTC -- the house convention for this contract
    (FREEZE-QUESTION: naive stamps = UTC).
    """

    granularity: str
    text: str
    utc: Optional[datetime] = None


def _parse_stamp(stamp: Any) -> Optional[_Stamp]:
    """Parse ``YYYY-MM``, ``YYYY-MM-DD`` or an ISO datetime; None otherwise.

    A trailing ``Z`` is explicitly rewritten to ``+00:00`` before parsing so
    the accepted forms do not depend on the Python minor version. A naive
    datetime is interpreted as UTC (house convention).
    """
    if not isinstance(stamp, str) or not stamp:
        return None
    if len(stamp) == 7:
        try:
            date.fromisoformat(stamp + "-01")
        except ValueError:
            return None
        return _Stamp("month", stamp)
    if len(stamp) == 10:
        try:
            date.fromisoformat(stamp)
        except ValueError:
            return None
        return _Stamp("day", stamp)
    text = stamp[:-1] + "+00:00" if stamp.endswith("Z") else stamp
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return _Stamp("instant", stamp, parsed.replace(tzinfo=timezone.utc))
    return _Stamp("instant", stamp, parsed.astimezone(timezone.utc))


def _stamp_keys(stamp: _Stamp, granularity: str) -> frozenset:
    """Calendar keys ``stamp`` could denote at ``granularity`` (month/day).

    Each stamp contributes its literal key (the text truncated to the
    comparison width) and, for an aware instant, also the key of its UTC
    instant, so a comparison can never be flattered by a time-zone shift.
    """
    width = 7 if granularity == "month" else 10
    keys = {stamp.text[:width]}
    if stamp.granularity == "instant":
        keys.add(stamp.utc.date().isoformat()[:width])
    return frozenset(keys)


def _not_after_cutoff(stamp: Any, cutoff: str) -> bool:
    """True when `stamp` can be shown at or before `cutoff`.

    Two instants compare exactly on their aware-UTC datetimes (seconds and
    microseconds included). Any coarser pairing compares at the coarser
    granularity, fail-closed across time zones: each side contributes every
    calendar key it could denote (its literal key, plus the UTC-instant key
    when aware), and the stamp is admitted only when its latest possible key
    is at or before the cutoff's earliest possible key. An unparsable side
    can never be shown to be at or before the cutoff, so it is not
    admissible here.
    """
    parsed = _parse_stamp(stamp)
    parsed_cutoff = _parse_stamp(cutoff)
    if parsed is None or parsed_cutoff is None:
        return False
    if parsed.granularity == "instant" and parsed_cutoff.granularity == "instant":
        return parsed.utc <= parsed_cutoff.utc
    coarse = min(
        (parsed.granularity, parsed_cutoff.granularity),
        key=lambda g: _COARSER_GRANULARITY[g],
    )
    return max(_stamp_keys(parsed, coarse)) <= min(_stamp_keys(parsed_cutoff, coarse))


def _cutoff_violation(cutoff: Any, *stamps: Any) -> Optional[str]:
    """First cutoff-law violation among `cutoff` and the evidence `stamps`.

    Returns the limitation string naming it -- ``cutoff_unparsable``,
    ``evidence_time_unparsable`` or ``after_cutoff`` -- or None when the
    cutoff parses, every non-None stamp parses, and every non-None stamp can
    be shown at or before the cutoff. None evidence stamps stay UNKNOWN and
    admitted (freeze rule; FREEZE-QUESTION: unknown evidence time admitted);
    qualify_observation then carries that unknown as a visible limitation
    ('evidence_time_unknown' / 'first_public_evidence_unknown'), never
    silently as known. A refused record (violation) gets neither tag.
    """
    if _parse_stamp(cutoff) is None:
        return "cutoff_unparsable"
    for stamp in stamps:
        if stamp is not None and _parse_stamp(stamp) is None:
            return "evidence_time_unparsable"
    for stamp in stamps:
        if stamp is not None and not _not_after_cutoff(stamp, cutoff):
            return "after_cutoff"
    return None


def _glob_match(value: str, pattern: str) -> bool:
    """Tiny '*' wildcard match for constraint patterns (e.g. '*_first_print')."""
    if "*" not in pattern:
        return value == pattern
    parts = pattern.split("*")
    if not value.startswith(parts[0]) or not value.endswith(parts[-1]):
        return False
    pos = len(parts[0])
    for part in parts[1:-1]:
        idx = value.find(part, pos)
        if idx < 0:
            return False
        pos = idx + len(part)
    return True


def _allowed(value: Any, allowed_values: Sequence[Any]) -> bool:
    if isinstance(value, Enum):
        value = value.value
    for entry in allowed_values:
        pat = entry.value if isinstance(entry, Enum) else entry
        if isinstance(pat, str) and "*" in pat:
            if isinstance(value, str) and _glob_match(value, pat):
                return True
        elif value == pat:
            return True
    return False


@dataclass(frozen=True)
class QualifiedObservation:
    """One numeric operand plus its full basis record (frozen wire fields)."""

    subject: str
    evidence_class: EvidenceClass
    value: Optional[float]
    value_state: ValueState
    unit: str
    target: str
    basket_or_index: Optional[str] = None
    reference_start: Optional[str] = None
    reference_end: Optional[str] = None
    tenor: Optional[str] = None
    observation_time: Optional[str] = None
    observation_precision: Precision = Precision.UNKNOWN
    seasonal_treatment: Optional[str] = None
    rate_index: Optional[str] = None
    averaging_law: Optional[str] = None
    curve_convention: Optional[str] = None
    source: Optional[str] = None
    source_version: Optional[str] = None
    content_ref: Optional[str] = None
    first_public_evidence: Optional[str] = None
    first_public_precision: Precision = Precision.UNKNOWN
    admitted_at: Optional[str] = None
    cutoff: str = ""
    model_id: Optional[str] = None
    target_epoch: Optional[str] = None
    vintage: Optional[str] = None
    rights: str = "unknown"
    quality: Tuple[str, ...] = ()
    authority: str = "display_only"
    limitations: Tuple[str, ...] = ()
    obs_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_class", EvidenceClass(self.evidence_class))
        object.__setattr__(self, "value_state", ValueState(self.value_state))
        object.__setattr__(self, "observation_precision", Precision(self.observation_precision))
        object.__setattr__(self, "first_public_precision", Precision(self.first_public_precision))
        object.__setattr__(self, "quality", tuple(self.quality))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        if self.unit not in UNIT_VALUES:
            raise ValueError("unknown unit: %r" % (self.unit,))
        if self.rights not in RIGHTS_VALUES:
            raise ValueError("unknown rights: %r" % (self.rights,))
        for flag in self.quality:
            if flag not in QUALITY_FLAGS:
                raise ValueError("unknown quality flag: %r" % (flag,))
        for name, allowed_vals in (
            ("seasonal_treatment", SEASONAL_VALUES),
            ("rate_index", RATE_INDEX_VALUES),
            ("averaging_law", AVERAGING_VALUES),
            ("curve_convention", CURVE_VALUES),
        ):
            got = getattr(self, name)
            if got is not None and got not in allowed_vals:
                raise ValueError("unknown %s: %r" % (name, got))
        if not self.cutoff:
            raise ValueError("cutoff is required")
        if self.authority != "display_only":
            raise ValueError("authority is frozen to display_only in this programme")
        if self.value_state == ValueState.PRESENT and self.value is None:
            raise ValueError("value_state present requires a value")
        if self.value_state != ValueState.PRESENT and self.value is not None:
            raise ValueError("value must be None unless value_state is present")
        if self.value_state == ValueState.PRESENT and _cutoff_violation(
            self.cutoff, self.first_public_evidence, self.observation_time
        ) is not None:
            raise ValueError(
                "present value cannot be shown at or before its publication "
                "cutoff (cutoff law); refusing to construct a leaked number"
            )
        payload = {f.name: getattr(self, f.name) for f in dc_fields(self) if f.name != "obs_id"}
        object.__setattr__(self, "obs_id", _digest16(payload))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonify({f.name: getattr(self, f.name) for f in dc_fields(self)})

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "QualifiedObservation":
        known = {f.name for f in dc_fields(cls)}
        unknown = sorted(k for k in dict(raw) if k not in known)
        if unknown:
            raise ValueError(
                "unknown %s keys (schema is closed): %s"
                % (cls.__name__, ", ".join(unknown))
            )
        return cls(**dict(raw))


def qualify_observation(
    value: Any, metadata: Mapping[str, Any], cutoff: str
) -> QualifiedObservation:
    """Qualify a raw value against its basis metadata at a publication cutoff.

    Missing metadata keys become None (UNKNOWN), never guessed. A value that
    is None / NaN / empty yields value_state 'missing' unless the metadata
    explicitly supplies 'withheld' / 'stale' / 'refused'. An evidence
    timestamp (first_public_evidence or observation_time) after the cutoff
    refuses the value with limitation 'after_cutoff' -- the number never
    leaks past its cutoff. A cutoff or evidence stamp that cannot be parsed
    refuses the value ('cutoff_unparsable' / 'evidence_time_unparsable')
    rather than admitting it: a number that cannot be shown to be at or
    before its publication cutoff is never present. An unknown evidence
    time (both stamps None, or only first_public_evidence None) stays
    ADMITTED but is carried as a visible limitation ('evidence_time_unknown'
    / 'first_public_evidence_unknown'); a refused record gets neither tag.
    The refusal is decided
    BEFORE the record is constructed, so a tampered record carrying a leaked
    number is rejected by the constructor itself.
    """
    meta = dict(metadata or {})
    state_raw = meta.get("value_state")
    blank = value is None or (isinstance(value, float) and value != value) or value == ""
    violation = _cutoff_violation(
        cutoff, meta.get("first_public_evidence"), meta.get("observation_time")
    )
    if violation is not None:
        value_state = ValueState.REFUSED
        value_out: Optional[float] = None
    elif state_raw in ("withheld", "stale", "refused"):
        value_state = ValueState(state_raw)
        value_out = None
    elif blank:
        value_state = ValueState.MISSING
        value_out = None
    else:
        value_state = ValueState.PRESENT
        value_out = float(value)
    quality = meta.get("quality") or ()
    if isinstance(quality, str):
        quality = (quality,)
    limitations = meta.get("limitations") or ()
    if isinstance(limitations, str):
        limitations = (limitations,)
    limitations = tuple(limitations)
    if violation is None:
        # FQ2: an unknown evidence time stays admitted, but is surfaced as a
        # visible limitation -- never silently as if its timing were known.
        if meta.get("first_public_evidence") is None:
            tag = (
                "evidence_time_unknown"
                if meta.get("observation_time") is None
                else "first_public_evidence_unknown"
            )
            if tag not in limitations:
                limitations = limitations + (tag,)
    obs = QualifiedObservation(
        subject=meta.get("subject", ""),
        evidence_class=EvidenceClass(meta.get("evidence_class")),
        value=value_out,
        value_state=value_state,
        unit=meta.get("unit", ""),
        target=meta.get("target", ""),
        basket_or_index=meta.get("basket_or_index"),
        reference_start=meta.get("reference_start"),
        reference_end=meta.get("reference_end"),
        tenor=meta.get("tenor"),
        observation_time=meta.get("observation_time"),
        observation_precision=Precision(meta.get("observation_precision", "unknown")),
        seasonal_treatment=meta.get("seasonal_treatment"),
        rate_index=meta.get("rate_index"),
        averaging_law=meta.get("averaging_law"),
        curve_convention=meta.get("curve_convention"),
        source=meta.get("source"),
        source_version=meta.get("source_version"),
        content_ref=meta.get("content_ref"),
        first_public_evidence=meta.get("first_public_evidence"),
        first_public_precision=Precision(meta.get("first_public_precision", "unknown")),
        admitted_at=meta.get("admitted_at"),
        cutoff=cutoff,
        model_id=meta.get("model_id"),
        target_epoch=meta.get("target_epoch"),
        vintage=meta.get("vintage"),
        rights=meta.get("rights", "unknown"),
        quality=tuple(quality),
        limitations=tuple(limitations)
        + ((violation,) if violation is not None else ()),
    )
    return obs


@dataclass(frozen=True)
class ComparisonRule:
    """A documented rule under which two qualified operands may be compared.

    Constraints map a field name to the tuple of allowed values for that side
    (a '*' inside an allowed value is a wildcard). `match_fields` must be
    equal AND known (not None) on both sides unless the rule's transform
    explicitly bridges the difference.
    """

    rule_id: str
    version: str
    purpose: str
    left_constraints: Dict[str, Tuple[str, ...]]
    right_constraints: Dict[str, Tuple[str, ...]]
    match_fields: Tuple[str, ...]
    transform: Optional[str]
    output_unit: str


@dataclass(frozen=True)
class ComparisonResult:
    status: ComparisonStatus
    difference: Optional[float]
    range: Optional[Tuple[float, float]]
    unit: str
    rule_id: str
    rule_version: str
    transform: Optional[str]
    assumptions: Tuple[str, ...]
    limitations: Tuple[str, ...]
    reason: str
    left_ref: str
    right_ref: str
    left_cutoff: str
    right_cutoff: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", ComparisonStatus(self.status))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        if self.status not in (
            ComparisonStatus.DIRECTLY_COMPARABLE,
            ComparisonStatus.COMPARABLE_AFTER_TRANSFORMATION,
        ):
            object.__setattr__(self, "difference", None)
            object.__setattr__(self, "range", None)
        if self.range is not None:
            object.__setattr__(self, "range", tuple(self.range))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonify({f.name: getattr(self, f.name) for f in dc_fields(self)})

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ComparisonResult":
        known = {f.name for f in dc_fields(cls)}
        unknown = sorted(k for k in dict(raw) if k not in known)
        if unknown:
            raise ValueError(
                "unknown %s keys (schema is closed): %s"
                % (cls.__name__, ", ".join(unknown))
            )
        return cls(**dict(raw))


def compare_qualified(
    left: QualifiedObservation,
    right: QualifiedObservation,
    rule: ComparisonRule,
    *,
    context: Optional[Mapping[str, Any]] = None,
) -> ComparisonResult:
    """Evaluate a rule over two qualified operands (frozen order, first hit wins).

    Optional keyword-only `context` carries caller-supplied explicit bases
    (e.g. the calendar owner's effr_minus_midpoint_bp); the frozen three-arg
    call form is unchanged.
    """

    def _mk(
        status: ComparisonStatus,
        reason: str,
        difference: Optional[float] = None,
        rng=None,
        unit: str = "",
        transform: Optional[str] = None,
        assumptions: Sequence[str] = (),
        limitations: Sequence[str] = (),
    ) -> ComparisonResult:
        return ComparisonResult(
            status=status,
            difference=difference,
            range=rng,
            unit=unit or rule.output_unit,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            transform=transform,
            assumptions=tuple(assumptions),
            limitations=tuple(limitations),
            reason=reason,
            left_ref=left.obs_id,
            right_ref=right.obs_id,
            left_cutoff=left.cutoff,
            right_cutoff=right.cutoff,
        )

    # 1. operand availability: a non-present value never compares numerically
    for side, operand in (("left", left), ("right", right)):
        if operand.value_state != ValueState.PRESENT:
            return _mk(
                ComparisonStatus.UNAVAILABLE,
                "operand_%s:%s" % (operand.value_state.value, side),
            )
    # 2. unknown rights block export purposes (display of the refusal is fine)
    if rule.purpose == "export" and (left.rights == "unknown" or right.rights == "unknown"):
        return _mk(ComparisonStatus.NOT_COMPARABLE, "rights_unknown")
    # 3. per-side constraints
    for side, operand, cons in (
        ("left", left, rule.left_constraints),
        ("right", right, rule.right_constraints),
    ):
        for fname, allowed_vals in cons.items():
            if not _allowed(getattr(operand, fname), allowed_vals):
                return _mk(ComparisonStatus.NOT_COMPARABLE, "constraint:%s:%s" % (fname, side))
    # 4. a match field that is UNKNOWN on either side refuses the comparison
    for fname in rule.match_fields:
        if getattr(left, fname) is None or getattr(right, fname) is None:
            return _mk(ComparisonStatus.NOT_COMPARABLE, "unknown_basis:%s" % fname)
    # 5. basis equality, unless a per-rule bridge explicitly spans the field
    bridge = _BRIDGES.get(rule.rule_id)
    if bridge is not None:
        bridged_reason = bridge(left, right)
        if bridged_reason is not None:
            return _mk(ComparisonStatus.NOT_COMPARABLE, bridged_reason)
    for fname in rule.match_fields:
        if getattr(left, fname) != getattr(right, fname):
            return _mk(ComparisonStatus.NOT_COMPARABLE, "basis_mismatch:%s" % fname)
    # 6. decomposition / attribution rules the operands cannot identify
    under = _UNDERIDENTIFIED.get(rule.rule_id)
    if under is not None:
        under_result = under(left, right, rule, context, _mk)
        if under_result is not None:
            return under_result
    # 7. compute
    return _compute(left, right, rule, context, _mk)


def _convert_unit(diff: float, operand_unit: str, output_unit: str) -> float:
    """Explicit difference-unit conversion: pct -> bp (x100) only when the
    rule's output_unit is bp; anything else is passed through unchanged."""
    if output_unit == "bp" and operand_unit in PCT_UNITS:
        return diff * 100.0
    return diff


def _compute(
    left: QualifiedObservation,
    right: QualifiedObservation,
    rule: ComparisonRule,
    context: Optional[Mapping[str, Any]],
    _mk,
) -> ComparisonResult:
    fn = _COMPUTE.get(rule.rule_id)
    if fn is not None:
        result = fn(left, right, rule, context, _mk)
        if result is not None:
            return result
    diff = _convert_unit(left.value - right.value, left.unit, rule.output_unit)
    if rule.transform is None:
        return _mk(
            ComparisonStatus.DIRECTLY_COMPARABLE,
            "same_basis_direct_difference",
            difference=diff,
            transform=None,
        )
    return _mk(
        ComparisonStatus.COMPARABLE_AFTER_TRANSFORMATION,
        "transform:%s" % rule.transform,
        difference=diff,
        transform=rule.transform,
    )


def _bridge_sep_vs_market(
    left: QualifiedObservation, right: QualifiedObservation
) -> Optional[str]:
    """SEP (left) vs market (right): comparable only when the market operand's
    reference interval contains the SEP year-end month (A19)."""
    if left.reference_end is None or right.reference_start is None or right.reference_end is None:
        return "unknown_basis:reference_end"
    year_end_month = left.reference_end[:7]
    if right.reference_start[:7] <= year_end_month <= right.reference_end[:7]:
        return None
    return "basis_mismatch:reference_end"


def _bridge_cpi_month_vs_breakeven(
    left: QualifiedObservation, right: QualifiedObservation
) -> Optional[str]:
    """CPI month print (left) vs 10y inflation compensation (right): a monthly
    print and a 10-year compensation horizon never share a reference basis, so
    the refusal is structural (A13) and must not hinge on the data-dependent
    ``reference_end`` equality a forged operand can satisfy."""
    return "basis_mismatch:reference_end"


def _bridge_h1_target_stem(
    left: QualifiedObservation, right: QualifiedObservation
) -> Optional[str]:
    """Frozen house projection (left, ``*_first_print``) vs H1 receipt
    (right, ``*_h1``): the release-identity stem must agree (A30 / R2-E1-S13).
    Constraints already guarantee both suffixes; the bridge still refuses a
    non-str target defensively so the bridge contract stays total."""
    if not isinstance(left.target, str) or not isinstance(right.target, str):
        return "basis_mismatch:target_stem"
    left_stem = (
        left.target[: -len("_first_print")]
        if left.target.endswith("_first_print")
        else left.target
    )
    right_stem = (
        right.target[: -len("_h1")]
        if right.target.endswith("_h1")
        else right.target
    )
    if not left_stem.strip() or not right_stem.strip():
        return "basis_mismatch:target_stem"
    if left_stem != right_stem:
        return "basis_mismatch:target_stem"
    return None


def _explicit_effr_gap_bp(context: Optional[Mapping[str, Any]]) -> Optional[float]:
    """The caller-supplied EFFR-minus-target-midpoint gap in bp, or None when
    it is absent or unusable (None, bool, non-numeric, NaN, +/-inf). Never raises."""
    if context is None:
        return None
    raw = dict(context).get("effr_minus_midpoint_bp")
    if raw is None or isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    gap = float(raw)
    if gap != gap or gap in (float("inf"), float("-inf")):
        return None
    return gap


def _under_zq_vs_midpoint(
    left: QualifiedObservation,
    right: QualifiedObservation,
    rule: ComparisonRule,
    context: Optional[Mapping[str, Any]],
    _mk,
) -> ComparisonResult:
    """ZQ monthly-average EFFR vs target midpoint: only with an explicit
    EFFR-midpoint basis supplied by the canonical owner. The returned
    difference = (ZQ - midpoint) - effr_minus_midpoint_bp, expressed in
    rule.output_unit."""
    if context is None or "effr_minus_midpoint_bp" not in dict(context):
        return _mk(
            ComparisonStatus.NOT_IDENTIFIED,
            "underidentified:effr_target_basis",
            limitations=("no explicit EFFR-target-midpoint basis supplied",),
        )
    gap = _explicit_effr_gap_bp(context)
    if gap is None:
        return _mk(
            ComparisonStatus.NOT_IDENTIFIED,
            "underidentified:effr_target_basis",
            limitations=("explicit EFFR-target-midpoint basis is not a finite number",),
        )
    raw = left.value - right.value
    if left.unit != right.unit:
        return _mk(
            ComparisonStatus.NOT_IDENTIFIED,
            "underidentified:effr_target_basis",
            limitations=("operand units differ; EFFR-midpoint gap cannot be applied",),
        )
    if rule.output_unit == "bp" and left.unit in PCT_UNITS:
        diff = raw * 100.0 - gap
    elif rule.output_unit == "bp" and left.unit == "bp":
        diff = raw - gap
    elif rule.output_unit in PCT_UNITS and left.unit == rule.output_unit:
        diff = raw - gap / 100.0
    else:
        return _mk(
            ComparisonStatus.NOT_IDENTIFIED,
            "underidentified:effr_target_basis",
            limitations=("EFFR-midpoint gap cannot be expressed in output unit %s" % rule.output_unit,),
        )
    return _mk(
        ComparisonStatus.COMPARABLE_AFTER_TRANSFORMATION,
        "transform:monthly_average_vs_level",
        difference=diff,
        transform="monthly_average_vs_level",
        assumptions=(
            "effr_minus_midpoint_bp=%g" % gap,
            "effr_gap_applied_in=%s" % rule.output_unit,
        ),
    )


def _under_yield_attribution(
    left: QualifiedObservation,
    right: QualifiedObservation,
    rule: ComparisonRule,
    context: Optional[Mapping[str, Any]],
    _mk,
) -> ComparisonResult:
    """A nominal yield move is never identified as expected-short vs premium
    (or real vs compensation) by its total alone (A23/A24)."""
    move = left.value
    es = round(move / 3.0, 2)
    tp = round(2.0 * move / 3.0, 2)
    alts = (
        "expected_short=%+gbp + term_premium=%+gbp" % (es, tp),
        "expected_short=%+gbp + term_premium=%+gbp" % (-es, move + es),
        "real + inflation_compensation accounting view fits the same total; "
        "the two views are never summed",
    )
    return _mk(
        ComparisonStatus.NOT_IDENTIFIED,
        "underidentified:decomposition",
        limitations=alts,
    )


def _compute_sep_vs_market(left, right, rule, context, _mk) -> ComparisonResult:
    diff = _convert_unit(left.value - right.value, left.unit, rule.output_unit)
    return _mk(
        ComparisonStatus.COMPARABLE_AFTER_TRANSFORMATION,
        "transform:year_end_interval_match",
        difference=diff,
        transform="year_end_interval_match",
        limitations=(
            "participant appropriate-policy projection, not a committee promise or probability",
        ),
    )


def _compute_inflation_compensation(left, right, rule, context, _mk) -> ComparisonResult:
    diff = _convert_unit(left.value - right.value, left.unit, rule.output_unit)
    return _mk(
        ComparisonStatus.COMPARABLE_AFTER_TRANSFORMATION,
        "transform:nominal_minus_real",
        difference=diff,
        transform="nominal_minus_real",
        limitations=(
            "liquidity and on-the-run premium differences",
            "indexation lag",
            "instrument basis",
        ),
    )


def _compute_term_premium(left, right, rule, context, _mk) -> ComparisonResult:
    diff = _convert_unit(left.value - right.value, left.unit, rule.output_unit)
    return _mk(
        ComparisonStatus.COMPARABLE_AFTER_TRANSFORMATION,
        "transform:model_disagreement",
        difference=diff,
        transform="model_disagreement",
        limitations=("model disagreement, not a forecast or signal",),
    )


def _epoch_token(value) -> Optional[str]:
    """Strip whitespace and refuse the blank / NA-sentinel shapes; return the
    cleaned string or None when the value is absent, whitespace-only, or a
    ``NA`` / ``na`` / ``n/a`` literal (per the B0H1-R1 ruling)."""
    if not isinstance(value, str):
        return None
    s = value.strip()
    if s == "" or s.lower() in ("na", NA):
        return None
    return s


def _compute_h1_target(left, right, rule, context, _mk) -> ComparisonResult:
    """Frozen house projection (left, ``*_first_print``) vs H1 receipt
    (right, ``*_h1``): matched at an explicit evaluation epoch (A29).

    The H1 epoch arrives ONLY via ``context["eval_target_epoch"]`` and is
    matched against the RIGHT operand's own ``target_epoch``; the LEFT
    ``target_epoch`` is echoed in ``assumptions`` and is never compared.
    """
    ctx = dict(context) if context else {}
    ref = right.content_ref
    if not isinstance(ref, str) or ref[len("same_vintage:"):].strip() == "":
        return _mk(ComparisonStatus.NOT_COMPARABLE, "unknown_basis:content_ref")
    eval_tok = _epoch_token(ctx.get("eval_target_epoch"))
    right_tok = _epoch_token(right.target_epoch)
    if eval_tok is None or right_tok is None:
        return _mk(ComparisonStatus.NOT_COMPARABLE, "unknown_basis:eval_target_epoch")
    left_tok = _epoch_token(left.target_epoch)
    if left_tok is None:
        return _mk(ComparisonStatus.NOT_COMPARABLE, "unknown_basis:model_target_epoch")
    if eval_tok != right_tok:
        return _mk(ComparisonStatus.NOT_COMPARABLE, "basis_mismatch:eval_target_epoch")
    if left.unit in PCT_UNITS:
        diff = (left.value - right.value) * 100.0
        unit = "bp"
    else:
        diff = left.value - right.value
        unit = left.unit
    limitations: Tuple[str, ...] = ("h1_target_not_official_first_print",)
    if "proxy_vintage" in right.quality:
        limitations = limitations + ("proxy_vintage:right",)
    return _mk(
        ComparisonStatus.DIRECTLY_COMPARABLE,
        "h1_target_direct_difference",
        difference=diff,
        unit=unit,
        assumptions=(
            "eval_target_epoch:%s" % eval_tok,
            "model_target_epoch:%s" % left_tok,
        ),
        limitations=limitations,
    )


_BRIDGES = {
    "sep_vs_market_year_end.v1": _bridge_sep_vs_market,
    "cpi_month_vs_breakeven_10y.v1": _bridge_cpi_month_vs_breakeven,
    "forecast_vs_h1_target.v1": _bridge_h1_target_stem,
}
_UNDERIDENTIFIED = {
    "zq_month_vs_policy_midpoint.v1": _under_zq_vs_midpoint,
    "yield_move_attribution.v1": _under_yield_attribution,
}
_COMPUTE = {
    "sep_vs_market_year_end.v1": _compute_sep_vs_market,
    "inflation_compensation.v1": _compute_inflation_compensation,
    "term_premium_kw_vs_acm.v1": _compute_term_premium,
    "forecast_vs_h1_target.v1": _compute_h1_target,
}


def _rule(
    rule_id: str,
    purpose: str,
    left: Mapping[str, Sequence[str]],
    right: Mapping[str, Sequence[str]],
    match_fields: Sequence[str],
    transform: Optional[str],
    output_unit: str = "bp",
) -> ComparisonRule:
    return ComparisonRule(
        rule_id=rule_id,
        version="1",
        purpose=purpose,
        left_constraints={k: tuple(v) for k, v in dict(left).items()},
        right_constraints={k: tuple(v) for k, v in dict(right).items()},
        match_fields=tuple(match_fields),
        transform=transform,
        output_unit=output_unit,
    )


#: Frozen first-slice rule registry (seat ruling para-5).
RULES: Dict[str, ComparisonRule] = {
    "forecast_vs_first_print.v1": _rule(
        "forecast_vs_first_print.v1",
        "accuracy",
        {"evidence_class": ("house_estimate",)},
        {"evidence_class": ("official_measurement",), "target": ("*_first_print",)},
        (
            "target", "basket_or_index", "reference_start", "reference_end",
            "unit", "seasonal_treatment", "target_epoch",
        ),
        None,
    ),
    "same_basis_level_change.v1": _rule(
        "same_basis_level_change.v1",
        "level_change",
        {},
        {},
        (
            "subject", "target", "basket_or_index", "unit", "seasonal_treatment",
            "rate_index", "averaging_law", "curve_convention", "tenor",
            "model_id", "target_epoch", "evidence_class",
        ),
        None,
    ),
    "zq_month_vs_policy_midpoint.v1": _rule(
        "zq_month_vs_policy_midpoint.v1",
        "meeting_gap",
        {"basket_or_index": ("EFFR",), "averaging_law": ("arithmetic_calendar_day",)},
        {"target": ("fed_funds_target_midpoint",)},
        (),
        "monthly_average_vs_level",
    ),
    "sr3_vs_zq.v1": _rule(
        "sr3_vs_zq.v1",
        "quarter_vs_month",
        {"rate_index": ("SOFR",), "averaging_law": ("compounded_business_day",)},
        {"rate_index": ("EFFR",), "averaging_law": ("arithmetic_calendar_day",)},
        ("rate_index",),
        None,
    ),
    "sep_vs_market_year_end.v1": _rule(
        "sep_vs_market_year_end.v1",
        "projection_vs_expectation",
        {"evidence_class": ("survey_participant_projection",)},
        {"evidence_class": ("market_implied_expectation",)},
        (),
        "year_end_interval_match",
    ),
    "par_vs_zero.v1": _rule(
        "par_vs_zero.v1",
        "curve_convention_check",
        {"curve_convention": ("par",)},
        {"curve_convention": ("zero",)},
        ("curve_convention",),
        None,
    ),
    "inflation_compensation.v1": _rule(
        "inflation_compensation.v1",
        "decomposition_real",
        {"curve_convention": ("par",)},
        {"curve_convention": ("real_par",)},
        ("tenor", "reference_start", "reference_end"),
        "nominal_minus_real",
    ),
    "term_premium_kw_vs_acm.v1": _rule(
        "term_premium_kw_vs_acm.v1",
        "model_disagreement",
        {"model_id": ("*kw*",), "target": ("term_premium_kw",)},
        {"model_id": ("*acm*",), "target": ("term_premium_acm",)},
        ("tenor", "reference_start", "reference_end"),
        "model_disagreement",
    ),
    "cpi_vs_pce.v1": _rule(
        "cpi_vs_pce.v1",
        "basket_check",
        {"basket_or_index": ("CPI-U",)},
        {"basket_or_index": ("PCE",)},
        ("basket_or_index",),
        None,
    ),
    "cpi_month_vs_breakeven_10y.v1": _rule(
        "cpi_month_vs_breakeven_10y.v1",
        "horizon_check",
        {"target": ("cpi_u_all_items_mom_sa_first_print",)},
        {"target": ("inflation_compensation",), "tenor": ("10y",)},
        ("reference_end",),
        None,
    ),
    "yield_move_attribution.v1": _rule(
        "yield_move_attribution.v1",
        "attribution",
        {"unit": ("bp",)},
        {"unit": ("bp",)},
        ("unit",),
        None,
    ),
    "forecast_vs_h1_target.v1": _rule(
        "forecast_vs_h1_target.v1",
        "accuracy",
        {"evidence_class": ("house_estimate",), "target": ("*_first_print",)},
        {
            "evidence_class": ("official_measurement",),
            "target": ("*_h1",),
            "content_ref": ("same_vintage:*",),
        },
        (
            "basket_or_index", "reference_start", "reference_end",
            "unit", "seasonal_treatment",
            "curve_convention", "rate_index", "averaging_law", "tenor",
        ),
        None,
    ),
}


@dataclass(frozen=True)
class PathAssumptions:
    """Calendar-owner-supplied assumptions for one reference month.

    Effective dates are SUPPLIED by the canonical calendar owner; this pure
    module never derives them. ``tolerance_bp`` bounds path acceptance.
    """

    month_start: str
    month_end: str
    effective_dates: Tuple[str, ...] = ()
    realised_through: Optional[str] = None
    realised_average: Optional[float] = None
    pre_change_rate: Optional[float] = None
    rate_step_bp: Optional[float] = None
    effr_minus_midpoint_bp: Optional[float] = None
    tolerance_bp: float = 1e-6


@dataclass(frozen=True)
class PathIdentification:
    """Result of identifying an intra-month rate path from its average.

    Each path dict is ``{"segments": [[start, end, rate], ...], "end_rate": float}``.
    """

    status: PathStatus
    identified: Optional[Dict[str, Any]]
    alternatives: Tuple[Dict[str, Any], ...]
    end_rate_range: Optional[Tuple[float, float]]
    assumptions_used: Tuple[str, ...]
    missing: Tuple[str, ...]
    residual_bp: Optional[float] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", PathStatus(self.status))
        object.__setattr__(self, "alternatives", tuple(dict(p) for p in self.alternatives))
        object.__setattr__(self, "assumptions_used", tuple(self.assumptions_used))
        object.__setattr__(self, "missing", tuple(self.missing))
        if self.end_rate_range is not None:
            object.__setattr__(self, "end_rate_range", tuple(self.end_rate_range))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonify({f.name: getattr(self, f.name) for f in dc_fields(self)})

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PathIdentification":
        known = {f.name for f in dc_fields(cls)}
        unknown = sorted(k for k in dict(raw) if k not in known)
        if unknown:
            raise ValueError(
                "unknown %s keys (schema is closed): %s"
                % (cls.__name__, ", ".join(unknown))
            )
        return cls(**dict(raw))


_GRID_OFFSETS = (-2.0, -1.0, 0.0, 1.0, 2.0)
_GRID_PATH_CAP = 50


def _step_supplied(assumptions: PathAssumptions) -> bool:
    """True iff rate_step_bp names a usable grid step (F3: never defaulted).

    An invalid step -- 0, negative, NaN, infinity, a bool, or anything that
    is not a real number -- counts as NOT supplied.
    """
    step = assumptions.rate_step_bp
    if step is None or isinstance(step, bool):
        return False
    if not isinstance(step, (int, float)):
        return False
    return 0 < step < float("inf")


def _grid_step_pct(assumptions: PathAssumptions) -> float:
    if not _step_supplied(assumptions):
        raise ValueError("grid step (rate_step_bp) is not supplied")
    return float(assumptions.rate_step_bp) / 100.0 / 2.0


def _grid_step_tags(assumptions: PathAssumptions) -> Tuple[str, ...]:
    """Assumption tags naming the grid step actually used (additive F3: no
    status ever depends on them). Only reached when the step is supplied;
    there is no default step to name."""
    return ("rate_step_bp=%g" % float(assumptions.rate_step_bp),)


def _paths_result(
    paths, best_bp, tol_pct, assumptions_used
) -> PathIdentification:
    capped = ()
    if len(paths) > _GRID_PATH_CAP:
        paths = paths[:_GRID_PATH_CAP]
        capped = ("grid_paths_capped_at_%d" % _GRID_PATH_CAP,)
    if paths:
        end_rates = [p["end_rate"] for p in paths]
        return PathIdentification(
            PathStatus.FEASIBLE_ALTERNATIVES,
            None,
            paths,
            (min(end_rates) - tol_pct, max(end_rates) + tol_pct),
            tuple(assumptions_used) + capped,
            (),
        )
    return PathIdentification(
        PathStatus.INCONSISTENT,
        None,
        (),
        None,
        tuple(assumptions_used) + capped,
        (),
        residual_bp=best_bp,
    )


def _grid_unknown_split(
    start: date, end: date, n_days: int, avg: float,
    assumptions: PathAssumptions, tol_pct: float,
):
    """No effective date supplied: enumerate split days and grid rate pairs.
    A flat path is feasible here (maybe there was no meeting at all)."""
    g = _grid_step_pct(assumptions)
    start_iso, end_iso = start.isoformat(), end.isoformat()
    paths, best = [], None
    for d_pre in range(1, n_days):
        d_post = n_days - d_pre
        eff = (start + timedelta(days=d_pre)).isoformat()
        for k_pre in _GRID_OFFSETS:
            for k_post in _GRID_OFFSETS:
                r_pre, r_post = avg + k_pre * g, avg + k_post * g
                resid = r_pre * d_pre + r_post * d_post - avg * n_days
                if best is None or abs(resid) < abs(best):
                    best = resid
                if abs(resid) <= tol_pct * n_days:
                    paths.append(
                        {
                            "segments": [[start_iso, eff, r_pre], [eff, end_iso, r_post]],
                            "end_rate": r_post,
                        }
                    )
    return paths, None if best is None else best * 100.0


def _grid_known_split(
    start: date, end: date, eff: str, n_days: int, avg: float,
    assumptions: PathAssumptions, tol_pct: float,
):
    """One supplied effective date, pre-change rate unknown. The supplied date
    is a change date by premise, so flat (no-change) paths are excluded."""
    g = _grid_step_pct(assumptions)
    start_iso, end_iso = start.isoformat(), end.isoformat()
    d_pre = (date.fromisoformat(eff) - start).days
    d_post = n_days - d_pre
    paths, best = [], None
    for k_pre in _GRID_OFFSETS:
        for k_post in _GRID_OFFSETS:
            if k_pre == k_post:
                continue
            r_pre, r_post = avg + k_pre * g, avg + k_post * g
            resid = r_pre * d_pre + r_post * d_post - avg * n_days
            if best is None or abs(resid) < abs(best):
                best = resid
            if abs(resid) <= tol_pct * n_days:
                paths.append(
                    {
                        "segments": [[start_iso, eff, r_pre], [eff, end_iso, r_post]],
                        "end_rate": r_post,
                    }
                )
    return paths, None if best is None else best * 100.0


def _grid_multi_segment(
    start_iso: str, end_iso: str, inside, n_days: int, avg: float,
    assumptions: PathAssumptions, tol_pct: float,
):
    """>=2 supplied effective dates: enumerate grid rates per unknown segment;
    at least one boundary must carry an actual change (supplied dates are
    change dates by premise)."""
    g = _grid_step_pct(assumptions)
    bounds = [start_iso] + list(inside) + [end_iso]
    # segment i runs [bounds[i], bounds[i+1]); the final segment carries the
    # month-end day itself, so its length gains one day
    lengths = [
        (date.fromisoformat(bounds[i + 1]) - date.fromisoformat(bounds[i])).days
        + (1 if i == len(bounds) - 2 else 0)
        for i in range(len(bounds) - 1)
    ]
    offsets = list(_GRID_OFFSETS) if len(lengths) <= 4 else (-1.0, 0.0, 1.0)
    fixed_first = assumptions.pre_change_rate
    paths, best = [], None

    def walk(idx: int, rates) -> None:
        nonlocal best
        if idx == len(lengths):
            if all(rates[i] == rates[i + 1] for i in range(len(rates) - 1)):
                return  # flat path contradicts the supplied change dates
            total = sum(r * d for r, d in zip(rates, lengths))
            resid = total - avg * n_days
            if best is None or abs(resid) < abs(best):
                best = resid
            if abs(resid) <= tol_pct * n_days:
                segs = [[bounds[i], bounds[i + 1], rates[i]] for i in range(len(rates))]
                paths.append({"segments": segs, "end_rate": rates[-1]})
            return
        if idx == 0 and fixed_first is not None:
            walk(idx + 1, rates + [float(fixed_first)])
            return
        for k in offsets:
            walk(idx + 1, rates + [avg + k * g])

    walk(0, [])
    return paths, None if best is None else best * 100.0


def solve_reference_average(
    observations: Sequence[QualifiedObservation],
    assumptions: PathAssumptions,
) -> PathIdentification:
    """Identify intra-month rate paths consistent with a monthly average.

    Calendar-day arithmetic identity: ``avg * N = sum(rate_i * days_i)``.
    Effective dates are supplied by the canonical calendar owner and never
    derived here. Underidentified inputs stay nonunique: the canonical
    witness (30-day month, 15d @ 4.50 + 15d @ 4.00 -> average 4.25) has a
    -25 bp average change vs 4.50 while the second-half level change is
    -50 bp, and the same average admits multiple paths.
    """
    start = date.fromisoformat(assumptions.month_start)
    end = date.fromisoformat(assumptions.month_end)
    n_days = (end - start).days + 1
    if n_days <= 0:
        raise ValueError("month_end must not precede month_start")
    tol_pct = assumptions.tolerance_bp / 100.0
    start_iso, end_iso = start.isoformat(), end.isoformat()
    base_used = ("calendar_day_arithmetic", "month_days=%d" % n_days)

    avg = None
    for obs in observations or ():
        if obs.value_state == ValueState.PRESENT and obs.value is not None:
            avg = float(obs.value)
            break
    monthly_from_realised = False
    if avg is None and assumptions.realised_average is not None:
        # A realised average may stand in for the monthly average only on
        # full-month coverage; a partial window is a pre-rate at best and
        # never the month's average.
        if (
            assumptions.realised_through is not None
            and assumptions.realised_through >= end_iso
        ):
            avg = float(assumptions.realised_average)
            monthly_from_realised = True
    if avg is None:
        return PathIdentification(
            PathStatus.MISSING_INPUTS, None, (), None, base_used, ("monthly_average",)
        )
    if monthly_from_realised:
        base_used = base_used + ("monthly_average_source=realised_average",)

    inside = sorted({d for d in assumptions.effective_dates if start_iso <= d <= end_iso})

    if not assumptions.effective_dates:
        # nothing supplied: the average alone does not identify a path, and
        # F3 forbids minting one from a default grid step
        if not _step_supplied(assumptions):
            return PathIdentification(
                PathStatus.MISSING_INPUTS, None, (), None,
                base_used + ("no_effective_date_supplied", "rate_step_unsupplied"),
                ("rate_step_bp",),
            )
        paths, best_bp = _grid_unknown_split(start, end, n_days, avg, assumptions, tol_pct)
        return _paths_result(
            paths, best_bp, tol_pct,
            base_used + ("no_effective_date_supplied", "grid_enumeration")
            + _grid_step_tags(assumptions),
        )

    if not inside:
        # declared non-meeting month: the monthly average is the month level
        return PathIdentification(
            PathStatus.IDENTIFIED_CONDITIONAL,
            {"segments": [[start_iso, end_iso, avg]], "end_rate": avg},
            (),
            (avg - tol_pct, avg + tol_pct),
            base_used + ("no_intra_month_change",),
            (),
        )

    realised_ok = False
    if len(inside) == 1:
        # The realised average is a pre-change rate only when its window is a
        # strict prefix of the pre segment [month_start, eff): a window that
        # reaches or passes the effective date (or ends before the month
        # began) carries no pre-change information at all.
        realised_ok = assumptions.realised_average is not None and (
            assumptions.realised_through is None
            or start_iso <= assumptions.realised_through < inside[0]
        )
    if len(inside) == 1 and (
        assumptions.pre_change_rate is not None or realised_ok
    ):
        eff = inside[0]
        r_pre = assumptions.pre_change_rate
        d_pre = (date.fromisoformat(eff) - start).days
        if r_pre is None:
            r_pre = float(assumptions.realised_average)
        if d_pre < 0:
            d_pre = 0
        d_post = n_days - d_pre
        if d_post <= 0:
            d_pre, d_post = 0, n_days
        r_post = (avg * n_days - float(r_pre) * d_pre) / d_post
        identified = {
            "segments": [[start_iso, eff, float(r_pre)], [eff, end_iso, float(r_post)]],
            "end_rate": float(r_post),
        }
        used = base_used + (
            "effective_date=%s" % eff, "pre_change_rate=%g" % float(r_pre),
        )
        if assumptions.pre_change_rate is None:
            used = used + ("pre_change_rate_source=realised_average",)
            if assumptions.realised_through is None:
                # V1: the pre-rate is carried without a known window -- say
                # so instead of showing it as if its timing were known.
                used = used + ("realised_through_unknown",)
            else:
                used = used + ("realised_through=%s" % assumptions.realised_through,)
        return PathIdentification(
            PathStatus.IDENTIFIED_CONDITIONAL,
            identified,
            (),
            (r_post - tol_pct, r_post + tol_pct),
            used,
            (),
        )

    if len(inside) == 1:
        used = base_used + (
            "effective_date=%s" % inside[0], "pre_change_rate_unknown",
        )
        if (
            assumptions.realised_average is not None
            and assumptions.pre_change_rate is None
        ):
            used = used + ("realised_average_unusable_as_pre_rate",)
        if not _step_supplied(assumptions):
            # F3: no usable pre-change rate and no supplied step -- there is
            # nothing to enumerate against, so no path may be minted.
            return PathIdentification(
                PathStatus.MISSING_INPUTS, None, (), None,
                used + ("rate_step_unsupplied",),
                ("pre_change_rate",),
            )
        paths, best_bp = _grid_known_split(
            start, end, inside[0], n_days, avg, assumptions, tol_pct
        )
        used = used + ("grid_enumeration",)
    else:
        if not _step_supplied(assumptions):
            # F3: multiple inside dates identify nothing without a supplied
            # step; a default grid may not mint candidate end rates.
            return PathIdentification(
                PathStatus.MISSING_INPUTS, None, (), None,
                base_used + ("effective_dates=%s" % ",".join(inside), "rate_step_unsupplied"),
                ("rate_step_bp",),
            )
        paths, best_bp = _grid_multi_segment(
            start_iso, end_iso, inside, n_days, avg, assumptions, tol_pct
        )
        used = base_used + (
            "effective_dates=%s" % ",".join(inside), "grid_enumeration",
        )
    return _paths_result(paths, best_bp, tol_pct, used + _grid_step_tags(assumptions))
