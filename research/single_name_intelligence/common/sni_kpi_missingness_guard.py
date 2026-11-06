"""SNI-local DRAFT KPI-missingness-guard contract (A10 missing KPI refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
FIF / Company Event/Earnings KPI disclosure records (period_id, state,
value, optional carry_forward / imputed flags). It does not re-implement
Data OS identity, Company Event/Earnings, FIF, Capital Structure,
Stock Identity, Options, Research Vault, or qledger/Evaluation. Identity
ids are caller-supplied opaque strings owned by Stock Identity / Data OS;
this guard never mints, derives, or guesses canonical HK/US issuer or
security identifiers from a ticker, name, code, or CIK. Unknown identity
stays UNRESOLVED / null. Period identifiers are caller-supplied opaque
strings; this guard never constructs them.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, impute, carry forward, or repair
anything. A missing KPI is refused, not filled with zero and not taken
from a prior period. An aggregate is refused unless every named period
is reported.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal,
score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence

KPI_STATES: tuple[str, ...] = (
    "reported",
    "not_reported",
    "not_applicable",
    "withheld",
)

REASONS: tuple[str, ...] = (
    "PERIOD_ID_MISSING",
    "DUPLICATE_PERIOD",
    "STATE_UNKNOWN",
    "REPORTED_VALUE_INVALID",
    "MISSING_CARRIES_VALUE",
    "PERIOD_ABSENT",
    "UNEXPECTED_PERIOD",
    "CARRY_FORWARD_DECLARED",
    "IMPUTATION_DECLARED",
)

AUTHORITY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
)

_KPI_STATE_SET = frozenset(KPI_STATES)
_NON_REPORTED_STATES = frozenset(
    {
        "not_reported",
        "not_applicable",
        "withheld",
    }
)


def refuse_nonfalse_authority(flags: Mapping[str, object] | None = None) -> None:
    """Refuse any authority flag that is not literal False.

    Idiom copied from research/single_name_intelligence/event_response/s2_seal.py
    (refuse_nonfalse_authority); this module does not import that owner.
    """
    for key, value in AUTHORITY_FLAGS.items():
        if value is not False:
            raise ValueError(
                f"AUTHORITY_FLAGS[{key!r}] is {value!r}; every authority flag "
                "must be literal False"
            )
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("authority flags is not a mapping")
    for key, value in flags.items():
        if key in AUTHORITY_FLAGS and value is not False:
            raise ValueError(
                f"authority_flags[{key!r}] is {value!r}; "
                "every authority flag must be literal False"
            )


@dataclass(frozen=True)
class KpiSeriesVerdict:
    """Descriptive KPI-missingness refusal. Carries no filled or imputed value."""

    allowed: bool
    reasons: tuple[str, ...]
    reported_periods: tuple[object, ...]  # expected_periods order: caller-supplied expected_periods iteration

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        object.__setattr__(self, "reported_periods", tuple(self.reported_periods))

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """FAMILY TEXT RULE v2 (seat ruling): an opaque-text id / ref /
    label is PRESENT iff it is a non-empty ``str`` that does not begin
    or end with whitespace. None, ``""``, ``"  "``, ``"ID "``,
    ``" ID"``, ``"\tID"``, ``"ID　"``, ``1``, ``True``, ``1.0``,
    ``b"id"``, ``["id"]`` and any other object are ABSENT and never
    match each other.

    The helper calls NO normalisation method (no ``.strip`` /
    ``.lower`` / ``.upper`` / ``.casefold`` / ``.replace``), which
    keeps the family's no-normalisation static scans green.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _finite_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return isfinite(value)
    return False


def _as_records(series: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(series, (list, tuple)):
        raise TypeError("series must be a list or tuple of mappings")
    records: list[Mapping[str, object]] = []
    for item in series:
        if not isinstance(item, Mapping):
            raise TypeError("each record must be a Mapping")
        records.append(item)
    return tuple(records)


def _as_period_ids(periods: object, *, name: str) -> tuple[object, ...]:
    if not isinstance(periods, (list, tuple)):
        raise TypeError(f"{name} must be a list or tuple")
    return tuple(periods)


def _contains(items: Sequence[object], needle: object) -> bool:
    for item in items:
        if item == needle:
            return True
    return False


def kpi_value(record: Mapping[str, object]) -> int | float | None:
    """Return the numeric value of a valid reported record; otherwise None.

    Never substitutes 0 for a missing, withheld, not-applicable, invalid,
    or non-reported state.
    """
    if not isinstance(record, Mapping):
        raise TypeError("record must be a Mapping")
    if record.get("state") != "reported":
        return None
    value = record.get("value")
    if not _finite_number(value):
        return None
    return value


def aggregate_sum(
    series: object,
    *,
    periods: object,
) -> int | float | None:
    """Sum reported values only when every named period is fully reported.

    Returns None (never a partial sum, never a stand-in 0) unless every
    name in ``periods`` has exactly one reported record with a valid
    finite numeric value. An empty ``periods`` tuple returns None.
    """
    refuse_nonfalse_authority()
    records = _as_records(series)
    named = _as_period_ids(periods, name="periods")
    if not named:
        return None
    seen_names: list[object] = []
    total: int | float | None = None
    for period_id in named:
        if _contains(seen_names, period_id):
            return None
        seen_names.append(period_id)
        matches = [
            rec for rec in records if rec.get("period_id") == period_id
        ]
        if len(matches) != 1:
            return None
        rec = matches[0]
        if rec.get("state") != "reported":
            return None
        value = rec.get("value")
        if not _finite_number(value):
            return None
        if total is None:
            total = value
        else:
            total = total + value
    return total


def check_kpi_series(
    series: object,
    *,
    expected_periods: object,
) -> KpiSeriesVerdict:
    """Refuse a KPI series that treats a missing value as zero or carries it.

    Reports every applicable reason, de-duplicated, in REASONS order.
    ``allowed`` is True iff the reason tuple is empty.

    ``reported_periods`` follows the expected_periods order: it is built by
    iterating ``expected_periods`` in the caller-supplied order and keeping
    only those periods that are present in the series AND whose record
    state is "reported". The order is the expected_periods order even when
    the input records are in a different order.
    """
    refuse_nonfalse_authority()
    records = _as_records(series)
    expected = _as_period_ids(expected_periods, name="expected_periods")

    reasons: list[str] = []
    present_ids: list[object] = []
    reported_present: set[object] = set()
    duplicate = False

    for rec in records:
        period_id = rec.get("period_id")
        # FAMILY TEXT RULE v2: a record period_id is PRESENT only when
        # _text_present(period_id) is True. Anything else (None, "",
        # whitespace-only, padded, non-str, unhashable) is ABSENT and
        # gets the existing PERIOD_ID_MISSING reason. It is then NOT
        # compared against present_ids or expected, NOT added to
        # present_ids, and NOT added to reported_present. As a result,
        # an unhashable period_id (e.g. ["P1"], {"a": 1}) never raises.
        if not _text_present(period_id):
            reasons.append("PERIOD_ID_MISSING")
        else:
            if _contains(present_ids, period_id):
                duplicate = True
            else:
                present_ids.append(period_id)
            if not _contains(expected, period_id):
                reasons.append("UNEXPECTED_PERIOD")

        state = rec.get("state")
        value = rec.get("value")
        if state not in _KPI_STATE_SET:
            reasons.append("STATE_UNKNOWN")
        if state == "reported":
            if not _finite_number(value):
                reasons.append("REPORTED_VALUE_INVALID")
            if _text_present(period_id):
                reported_present.add(period_id)
        elif state in _NON_REPORTED_STATES:
            if value is not None:
                reasons.append("MISSING_CARRIES_VALUE")

        if rec.get("carry_forward") is True:
            reasons.append("CARRY_FORWARD_DECLARED")
        if rec.get("imputed") is True:
            reasons.append("IMPUTATION_DECLARED")

    if duplicate:
        reasons.append("DUPLICATE_PERIOD")

    # FAMILY TEXT RULE v2: every expected entry that is not text-present
    # (None, "", " ", "SYN-P-1 ", 1, True, 1.0, ["SYN-P-1"], {"a": 1})
    # can never be matched by anything in present_ids, so it yields the
    # existing PERIOD_ABSENT. A text-present entry yields PERIOD_ABSENT
    # only when it is not in present_ids. The reported_periods walk below
    # still skips them so an unhashable value never raises from
    # ``in reported_present``.
    for period_id in expected:
        if not _text_present(period_id) or not _contains(present_ids, period_id):
            reasons.append("PERIOD_ABSENT")

    # Walk expected_periods in caller order so reported_periods is in the
    # expected_periods order, regardless of input record order (X8C-03).
    # Only text-present entries participate; a non-text-present expected
    # entry is skipped so unhashable values never raise here either.
    reported_acc: list[object] = []
    for period_id in expected:
        if _text_present(period_id) and period_id in reported_present:
            reported_acc.append(period_id)

    frozen = _freeze_reasons(reasons)
    return KpiSeriesVerdict(
        allowed=not frozen,
        reasons=frozen,
        reported_periods=tuple(reported_acc),
    )
