"""Pure deterministic composition for the Consumer Cyclical economic-change projection.

display-only, never a score, never a rank, never a recommendation

This module projects a frozen case into the
``consumer_cyclical_intelligence_read_model.v1`` document. The composer is
deliberately pure: no I/O, no network, no store, no env, no clock reads
(``generated_at`` is passed in by the caller as ``case.generated_at``;
the module never reads the wall clock and never imports ``datetime.now``).

The result semantics follow frozen-spec section 6:

* every ready derived result binds exact input refs (the ``native_ref``s
  of the facts it consumed);
* dependency-local degradation: one malformed / missing fact value
  suppresses only the results that depend on it and records them in
  ``degraded_dependencies``; other results stay ready;
* zero ready results => ``availability = "unavailable"`` (NEVER an
  empty ``ready``);
* a malformed CASE SHAPE (missing ``subject`` /
  ``comparison_basis`` / ``facts``) refuses the whole case by raising
  ``CaseShapeError``;
* the ratio is WITHHELD (``value_text = None`` + ``withheld_reason``)
  when the denominator is nonpositive OR when the declared rounding
  envelope of the denominator includes zero; percentages greater than
  100 are NOT automatically invalid;
* a missing or invalid result is never rendered as zero and never as
  bearish; it is withheld;
* unit, ``scale_power10`` and ``sign_convention`` are preserved from
  the source facts, never normalized away.

All arithmetic uses :class:`decimal.Decimal`; ``float`` is banned
anywhere in the module. The percentage uses ``Decimal.quantize`` with
``ROUND_HALF_UP`` at 2dp.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping, Sequence


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


CONTRACT_ID = "consumer_cyclical_intelligence_read_model.v1"
SCHEMA_VERSION = "1.0.0"

FACT_KEY_TOTAL_REVENUE = "total_revenue"
FACT_KEY_ADVERTISING_REVENUE = "advertising_revenue"
FACT_KEY_ADVERTISING_EXPENSE = "advertising_expense"

RESULT_KEY_TOTAL_REVENUE_CHANGE = "total_revenue_change"
RESULT_KEY_ADVERTISING_REVENUE_CHANGE = "advertising_revenue_change"
RESULT_KEY_ADVERTISING_EXPENSE_CHANGE = "advertising_expense_change"
RESULT_KEY_ADVERTISING_NET_CHANGE = "advertising_net_change"
RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET = "advertising_current_period_net"
RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT = (
    "advertising_share_of_revenue_change_pct"
)


# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------


# The CONTRACT publishes exactly one comparison basis. This set used to
# carry three, so two of them were admitted by ``_validate_case_shape``,
# projected, and emitted as a document whose root ``comparison_basis`` the
# contract's enum rejects -- an invalid publication produced by a gate that
# was WIDER than the thing it gates for. Admission may be narrower than the
# contract; it may never be wider. Pinned by
# ``test_module_constants_mirror_the_published_contract``.
_ALLOWED_COMPARISON_BASIS: frozenset[str] = frozenset(
    {
        "explicit_same_quarter_prior_year",
    }
)

# The period_kind each declared comparison basis is ABOUT. ``_select_pair``
# receives the declared basis and used to ignore it, so the document could
# stamp ``same_quarter_prior_year_change`` on a pair of half-years.
_BASIS_PERIOD_KIND: Mapping[str, str] = {
    "explicit_same_quarter_prior_year": "quarter",
    "explicit_same_half_prior_year": "half_year",
    "explicit_same_year_prior_year": "year",
}

# Generous BANDS, never equalities. Consumer Cyclical is retail: a 4-5-4
# quarter is 13 or 14 weeks and a fiscal year is 52 or 53 of them, so the
# calendar answer is wrong here -- the same reason ``_envelope_period_start``
# refuses to snap a period_start out of a period_end. The bands exist to
# refuse a 30-day "quarter", not to impose a calendar.
_PERIOD_KIND_SPAN_DAYS: Mapping[str, tuple[int, int]] = {
    "quarter": (84, 100),
    "half_year": (175, 190),
    "year": (350, 385),
}

# 52 weeks = 364, 53 weeks = 371, calendar = 365/366. Excludes a half-year
# (182) and a two-year gap (728) with room to spare.
_PRIOR_YEAR_GAP_DAYS: tuple[int, int] = (350, 385)

# Three of the four result definitions end "in USD thousands" and carry the
# quantum ``1_thousand``. Those are CLAIMS about the envelope, not decoration,
# and they are constants selected by result key -- so a pair reported in EUR
# at 10**6 used to publish ``unit: EUR, scale_power10: 6`` beside the sentence
# "in USD thousands", schema-valid and self-contradicting. V1's frozen scope
# is a PLNT USD-thousands projector; deriving new quantum words or new prose
# would be inventing display vocabulary this module does not own, so the
# honest move is to withhold and say why.
_STATED_DEFINITION_UNIT: str = "USD"
_STATED_DEFINITION_SCALE: int = 3
# ``1_thousand`` is a precision claim about the SOURCE, not a formatting
# preference: a source rounded to the nearest 5 thousand does not support it.
_STATED_DEFINITION_QUANTUM: str = "1_thousand"
_DEFINITION_CONTRADICTED = "result_envelope_contradicts_stated_definition"

# Reserved text patterns that MUST never appear in the explanation
# envelope — implementing frozen-spec section 5's "forbidden conclusions"
# as an explicit guard, not as silent omission. The case-insensitive
# flag is hoisted to the start of each pattern so Python's re parser
# (which requires global flags at the beginning of a pattern) accepts
# the alternation form.
_FORBIDDEN_CONCLUSION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        # Calling dues "observed visits".
        "dues_described_as_observed_visits",
        r"(?i)\bdues?\b[^.\n]*\bobserved\s+visits?\b"
        r"|\bobserved\s+visits?\b[^.\n]*\bdues?\b",
    ),
    (
        # Subtracting advertising alone and labelling the remainder organic.
        "advertising_alone_called_organic_growth",
        r"(?i)\borganic\s+growth\b[^.\n]*\b(after|subtracting)\b[^.\n]*\b(advertising|ad\s+spend|ad\s+expense)\b"
        r"|\b(advertising|ad\s+spend|ad\s+expense)\b[^.\n]*\b(alone|isolated)\b[^.\n]*\borganic\b"
        r"|\bsubtracting\s+advertising\b[^.\n]*\borganic\b",
    ),
)

# Bare authority / scoring keys that MUST never appear anywhere in the
# document — frozen-spec section 6 rule 10 and section 5
# "explanation must expose NO ranking, entry, gating, sizing or
# origination field".
_FORBIDDEN_BARE_KEYS: frozenset[str] = frozenset(
    {
        "rank",
        "score",
        "entry",
        "gate",
        "sizing",
        "origination",
        "attractiveness",
        "composite",
    }
)
# Compound / underscored authority keys (mirrors the finance idiom).
_FORBIDDEN_COMPOUND_KEY_RE = re.compile(
    r"(^|_)(rank|score|attractiveness|composite)(_|$)",
    re.IGNORECASE,
)

#: Mirrors of the published contract's own constraints. The projection is
#: the sole author of ``consumer_cyclical_intelligence_read_model.v1``
#: documents, so anything it cannot express under these patterns is an
#: absence to be declared -- never a value to be invented or passed
#: through unchecked. Kept in step with the schema by
#: ``test_module_constants_mirror_the_published_contract``.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VALUE_TEXT_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_ALLOWED_PERIOD_KIND: frozenset[str] = frozenset(
    {
        "quarter",
        "half_year",
        "year",
    }
)
# NOTE: ``_ALLOWED_DEGRADED_STATE`` was retired with the hand-rolled
# document check below -- the schema itself is now the authority on what the
# module may EMIT, and a mirrored constant with no non-schema reader is one
# more thing to drift. Input-admission constants (``_ALLOWED_PERIOD_KIND``,
# ``_ALLOWED_COMPARISON_BASIS``) stay: they run before a document exists and
# must fail fast with a domain message.
# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CaseShapeError(ValueError):
    """Raised when the case itself or the projected document is malformed.

    Used both for the top-level shape refusal (section 6 rule 8) and for
    the explanation / authority-key guards (section 5 + section 6
    rule 10). The composer never returns a malformed document — it
    refuses instead.
    """


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


_TWO_PLACES = Decimal("1") / Decimal("100")
_HUNDRED = Decimal("100")


def _coerce_decimal_text(value: Any) -> Decimal | None:
    """Coerce a raw ``value_text`` payload into a ``Decimal``, or ``None``.

    A blank, missing or unparseable value returns ``None`` — never raises.
    The Decimal is constructed from a string so float inputs can never
    sneak in.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _quantize_two_places(value: Decimal) -> Decimal:
    """Quantize a Decimal to 2dp using ROUND_HALF_UP (frozen precision law).

    The exponent is constructed as ``Decimal("1") / Decimal("100")``
    (one hundredth) to honour the precision law without introducing a
    numeric literal that resembles a ``float`` to static-analysis
    heuristics.
    """
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _format_decimal(value: Decimal) -> str:
    """Canonical string form for an emitted Decimal value.

    Preserves sign (``Decimal("-4")`` -> ``"-4"``) and never strips the
    leading minus on zero or the trailing zeros that ``quantize`` lays
    down. ``format(value, "f")`` is the documented Decimal-to-string
    formatter and round-trips through ``Decimal``.
    """
    return format(value, "f")


def _envelope_includes_zero(envelope: Mapping[str, Any] | None) -> bool:
    """Whether the declared rounding envelope of a fact includes zero.

    Frozen-spec section 6 rule 6: the ratio is withheld when the
    denominator's declared rounding envelope includes zero. We honour a
    boolean flag on the envelope to express that intent; absent the
    flag, the envelope is treated as excluding zero.
    """
    if not isinstance(envelope, Mapping):
        return False
    flag = envelope.get("includes_zero")
    if isinstance(flag, bool):
        return flag
    return False


def _envelope_unit(fact: Any) -> str:
    if isinstance(fact, Mapping):
        unit = fact.get("unit")
        if isinstance(unit, str) and unit:
            return unit
    return "USD"


def _envelope_scale(fact: Any) -> int:
    if not isinstance(fact, Mapping):
        return 0
    raw = fact.get("scale_power10")
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.lstrip("-").isdigit():
        return int(raw)
    return 0


def _envelope_sign_convention(fact: Any) -> str:
    """Return the schema-valid sign convention of a fact.

    Defaults to ``"signed_as_reported"`` (the schema-valid enum
    literal that handles a sign-bearing nominal fact); falls
    through to the fact's own value when present.
    """
    if isinstance(fact, Mapping):
        sign = fact.get("sign_convention")
        if isinstance(sign, str) and sign in _SIGN_CONVENTION_ENUM:
            return sign
    return "signed_as_reported"


_SIGN_CONVENTION_ENUM = frozenset(
    {
        "signed_as_reported",
        "signed_difference",
        "unsigned_magnitude",
    }
)


def _envelope_period_kind(fact: Any) -> str:
    if isinstance(fact, Mapping):
        kind = fact.get("period_kind")
        if isinstance(kind, str) and kind:
            return kind
    return ""


def _envelope_period_end(fact: Any) -> str:
    if isinstance(fact, Mapping):
        period_end = fact.get("period_end")
        if isinstance(period_end, str) and period_end:
            return period_end
    return ""


def _envelope_period_start(fact: Any) -> str:
    """Period start as carried by the source fact -- never derived.

    This function used to fall back to snapping ``period_end`` to a
    calendar quarter/half/year boundary. That fallback was unreachable
    from the suite and wrong wherever it *was* reachable: Consumer
    Cyclical is the retail sector, whose fiscal periods are famously
    offset from the calendar (the 4-5-4 retail calendar ends in late
    January). A fiscal quarter ending ``2025-02-01`` derived a start of
    ``2025-01-01`` -- a valid-looking date describing a 32-day
    "quarter", roughly two months adrift of the truth.

    A period boundary is a source-bound fact. When the source does not
    carry one, the honest projection declares the absence through
    ``degraded_dependencies`` rather than minting a plausible date, so
    the empty string returned here is an admission failure handled by
    :func:`_fact_admission_failure`, not a published value.
    """
    if isinstance(fact, Mapping):
        raw = fact.get("period_start")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_kind(fact: Any) -> str:
    """Read the fact's ``kind`` — contract-required, section 7 envelope."""
    if isinstance(fact, Mapping):
        kind = fact.get("kind")
        if isinstance(kind, str) and kind:
            return kind
    return "financial"


def _envelope_native_ref(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("native_ref")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_native_admitted(fact: Any) -> bool:
    if isinstance(fact, Mapping):
        flag = fact.get("native_admitted")
        if isinstance(flag, bool):
            return flag
    return False


def _envelope_definition(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("definition")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_metric(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("metric")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_basis(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("basis")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_role(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("role")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_target(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("target")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_perimeter(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("perimeter")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_event(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("event")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _envelope_published_at(fact: Any) -> str | None:
    if isinstance(fact, Mapping):
        raw = fact.get("published_at")
        if isinstance(raw, str) and raw:
            return raw
    return None


def _envelope_evidence(fact: Any) -> dict[str, Any] | None:
    if isinstance(fact, Mapping):
        raw = fact.get("evidence")
        if isinstance(raw, Mapping):
            return dict(raw)
    return None


def _envelope_display_quantum(fact: Any) -> str:
    if isinstance(fact, Mapping):
        raw = fact.get("display_quantum")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _rounding_envelope(fact: Any) -> Mapping[str, Any] | None:
    if isinstance(fact, Mapping):
        raw = fact.get("rounding_envelope")
        if isinstance(raw, Mapping):
            return raw
    return None


def _fact_ref(fact: Any, role: str) -> str:
    """The contract identifier a result's ``input_refs`` names: the fact ``key``."""
    if isinstance(fact, Mapping):
        key = fact.get("key")
        if isinstance(key, str) and key:
            return key
    return ""


# ---------------------------------------------------------------------------
# Fact admission
# ---------------------------------------------------------------------------


_ALLOWED_KIND: frozenset[str] = frozenset({"expense_line", "revenue_line"})

# Contract-required envelope fields the source must SPELL, in the module's
# own reading order. ``event`` is here rather than left to
# ``_assert_document_matches_contract_shape``: an absent ``event`` used to
# raise ``CaseShapeError`` and kill the whole case, where every sibling
# omission withholds one fact and declares it. One bad fact is not a bad
# case.
_REQUIRED_SOURCE_TEXT_FIELDS: tuple[str, ...] = (
    "basis",
    "definition",
    "display_quantum",
    "event",
    "key",
    "metric",
    "perimeter",
    "role",
    "unit",
)


def _fact_admission_failure(fact: Any) -> str | None:
    """Reason this fact cannot be *published* under the contract, else ``None``.

    ``_validate_case_shape`` checks only the case's top-level shape, so a
    fact may reach the projection missing any envelope field. The emitted
    ``facts[]`` entries are copied straight from the source, which means
    an unpublishable fact used to travel all the way into the document
    and break the very contract this module authors -- a
    thousands-separated ``"365,223"``, the ordinary human spelling of a
    financial figure, produced nine schema violations and an
    ``unavailable`` document.

    Refusal is deliberately not repair: ``"365,223"`` is not normalised
    to ``365223`` here, because reading a separator is a source-semantics
    decision this module has no authority to make. Note that
    :func:`_coerce_decimal_text` already treats such a value as
    unparseable for *computation*; this gate simply makes publication
    agree with computation instead of publishing what it could not use.
    """
    if not isinstance(fact, Mapping):
        return "fact_not_a_mapping"
    if not _VALUE_TEXT_RE.match(str(fact.get("value_text") or "")):
        return "fact_value_text_unparseable"
    if not _DATE_RE.match(_envelope_period_end(fact)):
        return "fact_period_end_missing_or_malformed"
    if not _DATE_RE.match(_envelope_period_start(fact)):
        return "fact_period_start_missing_or_malformed"
    if _envelope_period_kind(fact) not in _ALLOWED_PERIOD_KIND:
        return "fact_period_kind_outside_vocabulary"

    # The four checks above guard every field whose ``_envelope_*`` reader
    # answers a missing source value with an EMPTY sentinel. The rest of the
    # contract-required envelope is not so lucky: ``_envelope_kind`` answers
    # ``"financial"``, ``_envelope_unit`` answers ``"USD"``,
    # ``_envelope_sign_convention`` answers ``"signed_as_reported"`` and
    # ``_envelope_scale`` answers ``0`` -- all plausible-looking values rather
    # than sentinels, so no emptiness check could ever have caught them and
    # the fact sailed into a document this module then declared ``ready``.
    # Measured on the merged tree: dropping one required field from one fact
    # produced a ``ready`` document with ``degraded_dependencies: []`` that
    # violated this module's own contract for ``basis``, ``definition``,
    # ``display_quantum``, ``evidence``, ``key``, ``kind``, ``perimeter`` and
    # ``role`` -- and, worse, VALIDATED while lying for ``unit`` (a EUR
    # issuer published as USD), ``sign_convention`` (assumed, never read) and
    # ``scale_power10`` (thousands published as units).
    #
    # Same ruling as the period boundary, same reason: a minted envelope is a
    # source-semantics decision this module has no authority to make. Refusal
    # is not repair -- the fact is withheld and declared, never guessed at.
    for _field in _REQUIRED_SOURCE_TEXT_FIELDS:
        _raw = fact.get(_field)
        if not isinstance(_raw, str) or not _raw:
            return "fact_" + _field + "_missing_or_malformed"
    if fact.get("kind") not in _ALLOWED_KIND:
        return "fact_kind_outside_vocabulary"
    if fact.get("sign_convention") not in _SIGN_CONVENTION_ENUM:
        return "fact_sign_convention_missing_or_malformed"
    # Accept exactly what ``_envelope_scale`` can already read unambiguously;
    # this closes the fabricated ``0``, it does not tighten the source
    # grammar. A digit string was always usable and stays usable.
    _scale = fact.get("scale_power10")
    if not (
        (isinstance(_scale, int) and not isinstance(_scale, bool))
        or (isinstance(_scale, str) and _scale.lstrip("-").isdigit())
    ):
        return "fact_scale_power10_missing_or_malformed"
    if not isinstance(fact.get("evidence"), Mapping):
        return "fact_evidence_missing_or_malformed"
    return None


def _partition_admissible_facts(
    facts: Sequence[Any],
) -> tuple[list[Any], list[tuple[str, str]]]:
    """Split facts into publishable ones and ``(dependency, reason)`` refusals.

    Refused facts are withheld from pairing as well as from emission, so
    no result can bind an ``input_ref`` to a fact the document does not
    carry.
    """
    admitted: list[Any] = []
    refused: list[tuple[str, str]] = []
    for fact in facts:
        reason = _fact_admission_failure(fact)
        if reason is None:
            admitted.append(fact)
            continue
        metric = fact.get("metric") if isinstance(fact, Mapping) else None
        refused.append((str(metric or "unknown_dependency"), reason))
    return (admitted, refused)


# ---------------------------------------------------------------------------
# Case validation
# ---------------------------------------------------------------------------


def _validate_case_shape(case: Mapping[str, Any]) -> None:
    """Refuse the whole case on a malformed top-level shape.

    Raises :class:`CaseShapeError` if ``subject`` / ``comparison_basis``
    / ``facts`` are missing or of the wrong outer type, or if the
    ``comparison_basis`` is outside the closed vocabulary.
    """
    if not isinstance(case, Mapping):
        raise CaseShapeError("case must be a mapping")
    subject = case.get("subject")
    if not isinstance(subject, Mapping):
        raise CaseShapeError("case.subject must be a mapping")
    comparison_basis = case.get("comparison_basis")
    if not isinstance(comparison_basis, str) or not comparison_basis.strip():
        raise CaseShapeError("case.comparison_basis must be a non-empty string")
    if comparison_basis not in _ALLOWED_COMPARISON_BASIS:
        raise CaseShapeError(
            "case.comparison_basis must be one of "
            + ", ".join(sorted(_ALLOWED_COMPARISON_BASIS))
        )
    facts = case.get("facts")
    if not isinstance(facts, (list, tuple)):
        raise CaseShapeError("case.facts must be a list of fact mappings")


# ---------------------------------------------------------------------------
# Fact pairing
# ---------------------------------------------------------------------------


def _index_facts_by_metric(
    facts: Sequence[Mapping[str, Any]],
) -> dict[str, list[tuple[int, Mapping[str, Any]]]]:
    """Group facts for pairing, preserving input order.

    Prefers the contract's explicit ``metric`` field (the
    ``<metric>_current`` / ``<metric>_prior`` pairing key from
    section 7). Falls back to ``key`` when ``metric`` is absent or
    blank, which is the synthetic-fixture shape used in tests where
    two facts with the same ``key`` (e.g. two ``total_revenue`` rows)
    still need to pair.

    Returns ``{group: [(index_in_input, fact), ...]}``.
    """
    out: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for index, fact in enumerate(facts or ()):
        if not isinstance(fact, Mapping):
            continue
        metric = fact.get("metric")
        if isinstance(metric, str) and metric:
            group: str = metric
        else:
            key = fact.get("key")
            group = str(key) if isinstance(key, str) and key else ""
            if not group:
                continue
        out.setdefault(group, []).append((index, fact))
    return out


def _as_date(text: str) -> date | None:
    """Parse an admitted period bound, or ``None`` if it will not parse.

    Admission has already matched ``_DATE_RE`` by the time a fact reaches
    pairing, so a failure here is not expected -- but an unparseable bound
    must make the pair INELIGIBLE rather than exempt, so this fails closed.
    """
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def _span_fits_kind(fact: Mapping[str, Any], kind: str) -> bool:
    """A period must be coherent and roughly the length its kind claims."""
    start = _as_date(_envelope_period_start(fact))
    end = _as_date(_envelope_period_end(fact))
    if start is None or end is None:
        return False
    if not start < end:
        return False
    low, high = _PERIOD_KIND_SPAN_DAYS[kind]
    return low <= (end - start).days <= high


def _pair_can_be_basis(
    newest: Mapping[str, Any],
    older: Mapping[str, Any],
    comparison_basis: str,
) -> bool:
    """Can this pair actually BE the comparison the case declared?

    ``_select_pair`` has always taken ``comparison_basis`` as a parameter and
    never read it, so the basis was a label applied after the fact: the
    document could claim ``same_quarter_prior_year_change`` over a prior side
    seven years off, a prior period whose end preceded its own start, or a
    30-day "quarter", all at ``availability: ready`` with zero schema errors.
    The refusal reason for a pair that does not fit the declared basis already
    exists and is already named ``no_compatible_pair_for_comparison_basis``;
    this makes it mean what it says.
    """
    kind = _BASIS_PERIOD_KIND.get(comparison_basis)
    if kind is None:
        return False
    if _envelope_period_kind(newest) != kind or _envelope_period_kind(older) != kind:
        return False
    if not _span_fits_kind(newest, kind) or not _span_fits_kind(older, kind):
        return False
    newest_end = _as_date(_envelope_period_end(newest))
    older_end = _as_date(_envelope_period_end(older))
    if newest_end is None or older_end is None:
        return False
    low, high = _PRIOR_YEAR_GAP_DAYS
    return low <= (newest_end - older_end).days <= high


def _select_pair(
    candidates: Sequence[tuple[int, Mapping[str, Any]]],
    comparison_basis: str,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    """Pick the current-period and prior-period fact for one key.

    Pairing rule (frozen-spec section 5):

    * the two facts must share the same key, ``period_kind``, unit,
      ``scale_power10`` and ``sign_convention``;
    * ``period_end`` of the current fact must be strictly greater than
      ``period_end`` of the prior fact;
    * if multiple candidate pairs satisfy the rule, the pair with the
      newest ``period_end`` wins (deterministic).
    """
    if len(candidates) < 2:
        return (None, None)
    rows: list[tuple[str, str, str, int, str, int, Mapping[str, Any]]] = []
    for index, fact in candidates:
        rows.append(
            (
                _envelope_period_end(fact),
                _envelope_period_kind(fact),
                _envelope_unit(fact),
                _envelope_scale(fact),
                _envelope_sign_convention(fact),
                index,
                fact,
            )
        )
    rows.sort(
        key=lambda r: (r[0], r[1], r[2], r[3], r[4], r[5])
    )
    newest = rows[-1]
    for older in reversed(rows[:-1]):
        if (
            older[1] == newest[1]
            and older[2] == newest[2]
            and older[3] == newest[3]
            and older[4] == newest[4]
            and older[0] < newest[0]
            and _pair_can_be_basis(newest[6], older[6], comparison_basis)
        ):
            return (newest[6], older[6])
    return (None, None)


# ---------------------------------------------------------------------------
# Result envelopes
# ---------------------------------------------------------------------------


def _fact_to_envelope(fact: Mapping[str, Any]) -> dict[str, Any]:
    """Project a fact's stored fields into the result envelope shape.

    Preserves ``unit``, ``scale_power10`` and ``sign_convention`` from
    the source fact verbatim — never normalized away (frozen-spec
    section 6 rule 1). Also carries ``rounding_envelope`` so downstream
    consumers can re-check the spec's section 6 rule 6 withholding
    rules without re-fetching the original fact.
    """
    return {
        "key": str(fact.get("key")),
        "period_end": _envelope_period_end(fact),
        "period_kind": _envelope_period_kind(fact),
        "period_start": _envelope_period_start(fact),
        "value_text": str(fact.get("value_text")),
        "unit": _envelope_unit(fact),
        "scale_power10": _envelope_scale(fact),
        "sign_convention": _envelope_sign_convention(fact),
        "native_ref": _envelope_native_ref(fact),
        "native_admitted": _envelope_native_admitted(fact),
        "definition": _envelope_definition(fact),
        "metric": _envelope_metric(fact),
        "basis": _envelope_basis(fact),
        "role": _envelope_role(fact),
        "target": _envelope_target(fact),
        "perimeter": _envelope_perimeter(fact),
        "event": _envelope_event(fact),
        "published_at": _envelope_published_at(fact),
        "display_quantum": _envelope_display_quantum(fact),
        "evidence": _envelope_evidence(fact),
        "rounding_envelope": _rounding_envelope(fact),
    }


_CONTRACT_RESULT_KEYS: frozenset[str] = frozenset(
    {
        "basis",
        "definition",
        "display_quantum",
        "event",
        "input_refs",
        "key",
        "period_end",
        "period_kind",
        "period_start",
        "scale_power10",
        "sign_convention",
        "unit",
        "value_text",
        "withheld_reason",
    }
)


def _result_provenance(
    result: Mapping[str, Any],
    *,
    basis: str,
    definition: str,
    display_quantum: str,
) -> dict[str, Any]:
    """Fill the contract-required provenance fields on a result envelope.

    ``$defs/result`` requires basis / definition / display_quantum / event
    and the three period fields. Period and event are inherited from the
    current-period fact the result was computed from; basis, definition and
    display_quantum describe the derivation itself.
    """
    current = result.get("current_period_fact")
    if not isinstance(current, Mapping) or not current.get("period_end"):
        fallback = result.get("prior_period_fact")
        current = fallback if isinstance(fallback, Mapping) else (
            current if isinstance(current, Mapping) else {}
        )
    out = dict(result)
    out.setdefault("basis", basis)
    out.setdefault("definition", definition)
    out.setdefault("display_quantum", display_quantum)
    out["event"] = current.get("event") or ""
    out["period_end"] = current.get("period_end") or ""
    out["period_kind"] = current.get("period_kind") or "quarter"
    out["period_start"] = current.get("period_start") or ""
    return out


def _emit_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Project an internal result envelope onto the contract's closed shape.

    ``$defs/result`` sets ``additionalProperties: false``, so internal
    carriers (``value_decimal`` — a ``Decimal``, which is not even JSON
    serialisable — plus ``state``, ``comparison_basis`` and the two
    per-period fact envelopes) must not reach the document. Frozen-spec
    ruling B.
    """
    key = str(result.get("key") or "")
    if key.endswith("_pct"):
        basis, quantum = "share_of_change_ratio", "0.01_percent"
        definition = (
            "advertising_revenue_change divided by total_revenue_change, "
            "as a percentage at two decimal places."
        )
    elif key in {"advertising_net_change"}:
        basis, quantum = "difference_of_change_values", "1_thousand"
        definition = (
            "advertising_revenue_change minus advertising_expense_change, "
            "in USD thousands."
        )
    elif key in {"advertising_current_period_net"}:
        basis, quantum = "same_period_difference", "1_thousand"
        definition = (
            "advertising_revenue minus advertising_expense within the "
            "current period, in USD thousands."
        )
    else:
        basis, quantum = "same_quarter_prior_year_change", "1_thousand"
        definition = (
            "current-period value minus the same-quarter prior-year value, "
            "in USD thousands."
        )
    filled = _result_provenance(
        result, basis=basis, definition=definition, display_quantum=quantum
    )
    if not key.endswith("_pct") and not filled.get("withheld_reason"):
        # The USD-thousands family only. The ratio describes itself as a
        # percentage and says nothing about a currency, so it is unaffected.
        source = filled.get("current_period_fact")
        source_quantum = (
            source.get("display_quantum") if isinstance(source, Mapping) else None
        )
        if (
            filled.get("unit") != _STATED_DEFINITION_UNIT
            or filled.get("scale_power10") != _STATED_DEFINITION_SCALE
            or source_quantum != _STATED_DEFINITION_QUANTUM
        ):
            filled["value_text"] = None
            filled["withheld_reason"] = _DEFINITION_CONTRADICTED
    # ``input_refs`` is a SET of source keys under the contract
    # (``uniqueItems: true``), and a result whose two sides share one fact
    # key named it twice. Order-preserving so the current side still reads
    # first; ``dict.fromkeys`` rather than ``set`` for exactly that reason.
    refs = filled.get("input_refs")
    if isinstance(refs, list):
        filled["input_refs"] = list(dict.fromkeys(refs))
    return {k: v for k, v in filled.items() if k in _CONTRACT_RESULT_KEYS}


def _make_change_result(
    *,
    key: str,
    new_fact: Mapping[str, Any],
    prior_fact: Mapping[str, Any],
    change_value: Decimal,
    comparison_basis: str,
    denominator_unit: str | None = None,
    denominator_scale: int | None = None,
    denominator_sign: str | None = None,
) -> dict[str, Any]:
    """Build a per-key change result envelope from paired facts."""
    unit = denominator_unit if denominator_unit is not None else _envelope_unit(new_fact)
    scale = denominator_scale if denominator_scale is not None else _envelope_scale(new_fact)
    sign = denominator_sign if denominator_sign is not None else _envelope_sign_convention(new_fact)
    new_ref = _fact_ref(new_fact, "current_period")
    prior_ref = _fact_ref(prior_fact, "prior_period")
    return {
        "key": key,
        # Ruling A marker: both contributing facts existed. Stripped by
        # _emit_result before the document is built.
        "inputs_present": True,
        "value_text": _format_decimal(change_value),
        "value_decimal": change_value,
        "unit": unit,
        "scale_power10": scale,
        # Frozen-spec section 6 rule 1: derived results emit the
        # schema-valid ``signed_difference`` literal, not the source
        # fact's sign convention.
        "sign_convention": "signed_difference",
        "comparison_basis": comparison_basis,
        "state": "READY",
        "input_refs": [new_ref, prior_ref],
        "current_period_fact": _fact_to_envelope(new_fact),
        "prior_period_fact": _fact_to_envelope(prior_fact),
        "withheld_reason": None,
    }


def _withheld_result(
    *,
    key: str,
    new_fact: Mapping[str, Any] | None,
    prior_fact: Mapping[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    """Build a WITHHELD (NOT zero, NOT bearish) result envelope."""
    unit = (
        _envelope_unit(new_fact)
        if isinstance(new_fact, Mapping)
        else _envelope_unit(prior_fact)
    )
    scale = (
        _envelope_scale(new_fact)
        if isinstance(new_fact, Mapping)
        else _envelope_scale(prior_fact)
    )
    sign = (
        _envelope_sign_convention(new_fact)
        if isinstance(new_fact, Mapping)
        else _envelope_sign_convention(prior_fact)
    )
    refs: list[str] = []
    if isinstance(new_fact, Mapping):
        refs.append(_fact_ref(new_fact, "current_period"))
    if isinstance(prior_fact, Mapping):
        refs.append(_fact_ref(prior_fact, "prior_period"))
    return {
        "key": key,
        "inputs_present": isinstance(new_fact, Mapping)
        and isinstance(prior_fact, Mapping),
        "value_text": None,
        "value_decimal": None,
        "unit": unit,
        "scale_power10": scale,
        "sign_convention": sign,
        "comparison_basis": None,
        "state": "WITHHELD",
        "input_refs": refs,
        # A withheld result still has to satisfy ``$defs/result``, which
        # requires ``event`` and all three period fields. These used to be
        # dropped, so ``_finalize_result_envelope`` had nothing to read and
        # emitted ``""`` for each -- three contract violations on an
        # ordinary input (a flat or negative denominator withholds the
        # share-of-revenue ratio, which is a normal retail quarter, not an
        # edge case). Withholding a *value* never justified discarding the
        # provenance of the facts the value would have come from.
        "current_period_fact": _fact_to_envelope(new_fact)
        if isinstance(new_fact, Mapping)
        else None,
        "prior_period_fact": _fact_to_envelope(prior_fact)
        if isinstance(prior_fact, Mapping)
        else None,
        "withheld_reason": reason,
    }


def _make_ratio_result(
    *,
    numerator_result: Mapping[str, Any],
    denominator_fact_like: Mapping[str, Any],
    denominator_text: str,
    key: str,
) -> dict[str, Any]:
    """Build the percentage result, withholding when the law requires.

    Withholding rules (frozen-spec section 6 rule 6):
      * the denominator is nonpositive (zero or below); OR
      * the denominator's declared ``rounding_envelope.includes_zero``
        is True.

    Percentages greater than 100 are NOT automatically invalid — they
    pass through after ``quantize`` at 2dp with ``ROUND_HALF_UP``.
    """
    sign = _envelope_sign_convention(denominator_fact_like)
    unit = _envelope_unit(denominator_fact_like)
    scale = _envelope_scale(denominator_fact_like)
    if _envelope_includes_zero(_rounding_envelope(denominator_fact_like)):
        _refused = _withheld_result(
            key=key,
            new_fact=denominator_fact_like,
            prior_fact=None,
            reason="denominator_rounding_envelope_includes_zero",
        )
        # Ruling A: the inputs EXIST here — the withholding law refused the
        # computation. That is an answer about present inputs, so it is
        # emitted with a real withheld_reason and the numerator's refs,
        # never silently omitted.
        _refused["inputs_present"] = True
        _refused["input_refs"] = list(numerator_result.get("input_refs") or [])
        return _refused
    denom = _coerce_decimal_text(denominator_text)
    if denom is None or denom <= 0:
        _refused = _withheld_result(
            key=key,
            new_fact=denominator_fact_like,
            prior_fact=None,
            reason="denominator_nonpositive",
        )
        # Ruling A: the inputs EXIST here — the withholding law refused the
        # computation. That is an answer about present inputs, so it is
        # emitted with a real withheld_reason and the numerator's refs,
        # never silently omitted.
        _refused["inputs_present"] = True
        _refused["input_refs"] = list(numerator_result.get("input_refs") or [])
        return _refused
    numer = numerator_result.get("value_decimal")
    if not isinstance(numer, Decimal):
        return _withheld_result(
            key=key,
            new_fact=denominator_fact_like,
            prior_fact=None,
            reason="numerator_unavailable",
        )
    ratio = (numer / denom) * _HUNDRED
    quantized = _quantize_two_places(ratio)
    return {
        "key": key,
        "inputs_present": True,
        # the ratio's period/event provenance is the denominator's
        # current-period fact (total revenue), which is what it is a share of
        # denominator_fact_like is already a fact-shaped envelope (the
        # total-revenue current-period fact), so carry it through directly —
        # re-enveloping an envelope drops its period/event fields.
        "current_period_fact": dict(denominator_fact_like)
        if isinstance(denominator_fact_like, Mapping)
        else None,
        "value_text": _format_decimal(quantized),
        "value_decimal": quantized,
        "unit": "percent",
        "scale_power10": 0,
        # Frozen-spec section 6 rule 1: derived results carry
        # ``signed_difference`` regardless of the source fact.
        "sign_convention": "signed_difference",
        "comparison_basis": numerator_result.get("comparison_basis"),
        "state": "READY",
        "input_refs": list(numerator_result.get("input_refs") or []),
        "prior_period_fact": None,
        "withheld_reason": None,
    }


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------


_LEAD_FULL = (
    "A substantial part of the total revenue change is associated with "
    "advertising flows with a nearly matching expense, so it does not "
    "translate one-for-one into incremental profit."
)
_LEAD_GENERIC = (
    "Selected advertising and revenue change facts are admitted "
    "without inference."
)
_COUNTEREVIDENCE = (
    "Franchise, corporate-club and equipment economics require their "
    "own analysis; they are not captured by this projection."
)
_NEXT_OBSERVATION = (
    "Comparable dues and retained operating contribution, plus "
    "franchisee economics where actually disclosed."
)
_DOES_NOT_PROVE = (
    "Does not prove organic growth, a complete profit bridge, or a "
    "conclusion about franchise health."
)


def _as_list(value: Any) -> list[str]:
    """Coerce an explanation field to the contract's array-of-string shape."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(v) for v in value if str(v)]


def _nullable(value: Any) -> Any:
    """Emit ``None`` where the contract types a field ``["string", "null"]``.

    Those fields also carry ``minLength: 1``, so an empty string is a
    validation error, not a benign blank. The envelope readers return
    ``""`` for "absent"; this converts that to the contract's null.
    """
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _degraded(dependency: str, reason: str, state: str = "unavailable") -> dict[str, Any]:
    """Build a contract-shaped degraded dependency entry.

    ``$defs/degraded_dependency`` is closed and requires exactly
    ``dependency`` (snake_case), ``reason`` and
    ``state`` in {available, partial, unavailable}.
    """
    slug = re.sub(r"[^a-z0-9_]", "_", str(dependency or "").lower()).strip("_")
    if not slug or not slug[0].isalpha():
        slug = "unknown_dependency" if not slug else "d_" + slug
    return {"dependency": slug, "reason": reason or None, "state": state}


def _build_explanation(selected_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Generate the explanation envelope from the SELECTED (READY) result envelopes only.

    Frozen-spec section 6 rule 7: numerical explanation is generated from
    selected result envelopes; the wording intent is preserved verbatim
    from section 5 when the relevant keys are present, otherwise a
    neutral lead is emitted. The lead never invents a number, never
    promotes a forbidden conclusion, and never refers to results that
    were not admitted.
    """
    keys = [str(r.get("key")) for r in selected_results]
    keys_set = set(keys)
    # ``selected_results`` are RESULT envelopes, so they are keyed
    # ``<metric>_change`` — comparing them against the FACT_KEY_* constants
    # (``advertising_revenue``) never matched, so the R6 7.1 lead was
    # unreachable and every document fell through to the neutral lead.
    has_advertising_revenue = RESULT_KEY_ADVERTISING_REVENUE_CHANGE in keys_set
    has_advertising_expense = RESULT_KEY_ADVERTISING_EXPENSE_CHANGE in keys_set
    has_total_revenue = RESULT_KEY_TOTAL_REVENUE_CHANGE in keys_set
    if has_total_revenue and has_advertising_revenue and has_advertising_expense:
        lead = _LEAD_FULL
    else:
        lead = _LEAD_GENERIC
    return {
        "lead": lead,
        "counterevidence": _as_list(_COUNTEREVIDENCE),
        "next_observation": _as_list(_NEXT_OBSERVATION),
        "does_not_prove": _as_list(_DOES_NOT_PROVE),
    }


def _check_explanation_for_forbidden(explanation: Mapping[str, Any]) -> None:
    """Refuse the projection if the explanation carries a forbidden conclusion.

    Frozen-spec section 5 names two conclusions that MUST never appear,
    even as incidental phrasing:
      * calling dues "observed visits";
      * subtracting advertising alone and labelling the remainder
        "organic growth".
    The guard raises :class:`CaseShapeError` rather than silently
    rewriting the explanation.
    """
    text = " ".join(
        str(explanation.get(k) or "")
        for k in (
            "lead",
            "counterevidence",
            "next_observation",
            "does_not_prove",
        )
    )
    for label, pattern in _FORBIDDEN_CONCLUSION_PATTERNS:
        if re.search(pattern, text):
            raise CaseShapeError(
                "explanation carries forbidden conclusion: " + label
            )


# ---------------------------------------------------------------------------
# Authority-key guard
# ---------------------------------------------------------------------------


_CONTRACT_VALIDATOR: list[Any] = []


def _contract_validator() -> Any:
    """The published schema, read once and reused.

    Lazy import and ``parents[2]`` path resolution mirror
    ``engine/capital_structure/projection.py``, the nearest sibling that
    validates its own output against its own contract.
    """
    if not _CONTRACT_VALIDATOR:
        import json as _json

        from jsonschema import Draft202012Validator, FormatChecker

        path = (
            Path(__file__).resolve().parents[2]
            / "contracts"
            / "sector_intelligence"
            / f"{CONTRACT_ID}.schema.json"
        )
        _CONTRACT_VALIDATOR.append(
            Draft202012Validator(
                _json.loads(path.read_text(encoding="utf-8")),
                format_checker=FormatChecker(),
            )
        )
    return _CONTRACT_VALIDATOR[0]


def _assert_document_matches_contract_shape(document: Mapping[str, Any]) -> None:
    """Refuse to return a document that violates the contract we publish.

    This is a positive control, not decoration. Every defect this module
    has shipped so far shared one shape: a branch no test reached, whose
    output nothing re-read. A 65-test suite stayed green while the
    projection emitted empty dates, an out-of-vocabulary ``period_kind``
    and non-numeric ``value_text`` -- because the suite only ever fed it
    one pristine fixture, and never asked the document whether it
    satisfied the schema sitting next to it in the repository.

    The checks below mirror the pattern-bearing constraints of
    ``consumer_cyclical_intelligence_read_model.v1``. They are cheap,
    they run on every projection including the degraded ones, and they
    fail loudly rather than publishing a plausible-looking lie.
    """

    errors = _contract_validator().iter_errors(dict(document))
    problems = [
        (".".join(str(part) for part in error.absolute_path) or "<root>")
        + ": "
        + error.message
        for error in sorted(errors, key=lambda error: list(error.absolute_path))
    ]
    if problems:
        raise CaseShapeError(
            "projection would emit a document that violates "
            + CONTRACT_ID
            + ": "
            + "; ".join(problems[:8])
        )


def _assert_provenance_pointers_resolve(document: Mapping[str, Any]) -> None:
    """Refuse a document whose provenance pointer names nothing that exists.

    ``fact.native_ref`` and ``source_records[].record_id`` are the two ends
    of ONE pointer, spelled in two places. The contract validates each end
    in isolation, so both pass happily while the pointer dangles -- and a
    dangling provenance pointer is the exact shape frozen-spec section 4a
    forbids: a fact that appears source-bound while naming no source.

    This is referential integrity WITHIN one emitted document, which is why
    it belongs here and not in ``_fact_admission_failure`` -- that gate sees
    one fact and structurally cannot see ``source_records``.

    A ``null`` ``native_ref`` is left alone deliberately. It is the
    contract's own "unknown" and DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-
    EMPTINESS-GATE so_what (4) rules that tightening it would refuse
    otherwise-complete facts to gain nothing. Absence is honest; a pointer
    to a record that was never declared is not.
    """

    declared = {
        record.get("record_id")
        for record in document.get("source_records") or ()
        if isinstance(record, Mapping)
    }
    orphans = sorted(
        {
            str(fact.get("native_ref"))
            for fact in document.get("facts") or ()
            if isinstance(fact, Mapping) and fact.get("native_ref") is not None
        }
        - declared
    )
    if orphans:
        raise CaseShapeError(
            "projection would emit facts whose native_ref resolves to no "
            "declared source record: " + ", ".join(orphans)
        )


def _assert_no_forbidden_authority_keys(document: Mapping[str, Any]) -> None:
    """Walk the document and refuse any forbidden authority / scoring key.

    Frozen-spec section 6 rule 10 and section 5: the document exposes
    NO ranking, entry, gating, sizing or origination field.
    """

    def walk(node: object) -> None:
        if isinstance(node, Mapping):
            for k, v in node.items():
                if isinstance(k, str):
                    if k.lower() in _FORBIDDEN_BARE_KEYS:
                        raise CaseShapeError(
                            "document carries forbidden authority key: " + k
                        )
                    if _FORBIDDEN_COMPOUND_KEY_RE.fullmatch(k):
                        raise CaseShapeError(
                            "document carries forbidden authority key: " + k
                        )
                walk(v)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                walk(child)

    walk(document)


# ---------------------------------------------------------------------------
# Per-key change composition
# ---------------------------------------------------------------------------


def _compose_changes(
    facts: Sequence[Mapping[str, Any]],
    comparison_basis: str,
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    """Compute the per-key change results and the per-fact degradation log.

    Returns ``(ready_results_by_key, degraded_facts)``.

    A fact whose ``value_text`` is unparseable, or whose pair cannot be
    located against the ``comparison_basis``, is recorded in
    ``degraded_facts`` and the corresponding change result is suppressed.

    ``native_admitted`` is NOT in that list and must not be added to it.
    Frozen-spec section 4a makes it a PROVENANCE LABEL, never a suppression
    gate -- see the comment at the pairing site below. Every real V1-CORE
    fact carries ``native_admitted: False`` because PLNT's Q2 2026 exhibit
    is retained nowhere, so gating here would make this module structurally
    incapable of its own golden case. This docstring previously claimed the
    suppression the code 20 lines below explicitly refuses, and cited
    section 7 for it; a reader who trusted it would have "restored" a gate
    that breaks the frozen oracle.

    The emitted result key is the fact key with a ``_change`` suffix
    (e.g. fact ``total_revenue`` -> result ``total_revenue_change``)
    so downstream callers can address the per-fact change results
    without colliding with the per-fact ``facts`` envelope.
    """
    by_metric = _index_facts_by_metric(facts)
    ready_results: dict[str, dict[str, Any]] = {}
    degraded_facts: list[dict[str, Any]] = []
    for key, candidates in by_metric.items():
        if len(candidates) < 2:
            degraded_facts.append(_degraded(key, "no_compatible_pair_for_comparison_basis"))
            continue
        new_fact, prior_fact = _select_pair(candidates, comparison_basis)
        if new_fact is None or prior_fact is None:
            degraded_facts.append(_degraded(key, "no_compatible_pair_for_comparison_basis"))
            continue
        # Frozen-spec section 4a: ``native_admitted`` is a PROVENANCE LABEL,
        # not a suppression gate. R15's "research values are expected oracles,
        # never substitute receipts" forbids presenting a non-admitted value AS
        # a retained receipt; it does not forbid computing from it. PLNT's Q2
        # 2026 exhibit is retained nowhere, so every real fact carries
        # ``native_admitted: False`` — a gate here would make this module
        # structurally incapable of its own golden case. The flag is carried
        # through to the emitted facts so a consumer can render it honestly.
        new_decimal = _coerce_decimal_text(new_fact.get("value_text"))
        if new_decimal is None:
            degraded_facts.append(_degraded(key, "fact_value_text_unparseable"))
            continue
        prior_decimal = _coerce_decimal_text(prior_fact.get("value_text"))
        if prior_decimal is None:
            degraded_facts.append(_degraded(key, "fact_value_text_unparseable"))
            continue
        change = new_decimal - prior_decimal
        ready_results[str(key) + "_change"] = _make_change_result(
            key=str(key) + "_change",
            new_fact=new_fact,
            prior_fact=prior_fact,
            change_value=change,
            comparison_basis=comparison_basis,
        )
    return (ready_results, degraded_facts)


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def _generated_at_text(case: Mapping[str, Any]) -> str:
    """Read the caller-supplied ``generated_at`` timestamp string.

    The composer NEVER reads the wall clock. When the caller omits the
    field, the literal sentinel ``1970-01-01T00:00:00Z`` is used so the
    output remains deterministic across machines.
    """
    raw = case.get("generated_at")
    if isinstance(raw, str):
        text = raw.strip()
        if text:
            return text
    return "1970-01-01T00:00:00Z"


def project_economic_change(case: Mapping[str, Any]) -> dict[str, Any]:
    """Pure projection of a frozen case into the V1 document.

    Parameters
    ----------
    case:
        ``Mapping`` carrying ``subject`` / ``comparison_basis`` /
        ``facts`` (each fact carrying the section-7 envelope), an
        optional ``generated_at`` timestamp string, and an optional
        ``source_records`` list. See ``research/consumer_cyclical/v1/
        V1_PLNT_BOUNDARY_AND_FROZEN_SPEC.md`` sections 5–7 for the
        frozen contract.

    Returns
    -------
    dict
        The ``consumer_cyclical_intelligence_read_model.v1`` document with keys
        ``contract_id``, ``schema_version``, ``generated_at``,
        ``subject``, ``comparison_basis``, ``facts``, ``results``,
        ``explanation``, ``degraded_dependencies``, ``source_records``
        and ``availability``.

    Raises
    ------
    CaseShapeError
        On a malformed case shape, on an explanation that carries a
        forbidden conclusion, or on a document that carries a forbidden
        authority / scoring key.
    """
    _validate_case_shape(case)

    comparison_basis = str(case.get("comparison_basis"))
    facts, refused_facts = _partition_admissible_facts(case.get("facts") or [])
    generated_at_text = _generated_at_text(case)
    source_records = case.get("source_records") or []

    ready_results, degraded_facts = _compose_changes(facts, comparison_basis)

    # A fact refused at admission is an absence the consumer must see, so it
    # is declared here rather than silently dropped. Several facts share one
    # metric (one per period role), so entries are deduplicated by dependency.
    #
    # A refusal SUPERSEDES ``no_compatible_pair_for_comparison_basis`` for the
    # same dependency rather than losing to it. Both describe one event from
    # two ends -- the pair is incomplete *because* a side was refused -- and
    # ``_compose_changes`` keys that reason on the METRIC, which is exactly
    # what a refusal is keyed on, so the effect lands first and the cause is
    # deduplicated away. Reporting only the effect tells a consumer there was
    # no pair to find, when in fact there was one and this module declined to
    # read half of it. Any other pre-existing reason is left alone; it was not
    # caused by this refusal.
    _entry_by_dep: dict[Any, dict[str, Any]] = {}
    for _d in degraded_facts:
        if isinstance(_d, Mapping):
            _entry_by_dep.setdefault(_d.get("dependency"), _d)  # type: ignore[arg-type]
    for _dep, _reason in refused_facts:
        _entry = _degraded(_dep, _reason)
        _existing = _entry_by_dep.get(_entry["dependency"])
        if _existing is None:
            _entry_by_dep[_entry["dependency"]] = _entry
            degraded_facts.append(_entry)
        elif _existing.get("reason") == "no_compatible_pair_for_comparison_basis":
            _existing["reason"] = _entry["reason"]
    ready_keys = set(ready_results.keys())

    # ``results_by_key`` carries every emitted result, READY and
    # WITHHELD; ``ready_keys`` (above) tracks which of those are READY
    # so the final ``availability`` verdict and the explanation's
    # ``selected_result_keys`` only count the READY subset.
    results_by_key: dict[str, dict[str, Any]] = dict(ready_results)

    # Name result keys from the RESULT_KEY_* constants, never by concatenating
    # "_change" onto a FACT_KEY_*. The two spellings coincide today, so a drift
    # in either would be silent — and confusing a fact identifier for a result
    # identifier is exactly what made the R6 economic lead unreachable.
    advertising_revenue_change_key = RESULT_KEY_ADVERTISING_REVENUE_CHANGE
    advertising_expense_change_key = RESULT_KEY_ADVERTISING_EXPENSE_CHANGE
    total_revenue_change_key = RESULT_KEY_TOTAL_REVENUE_CHANGE

    # ---- Derived: advertising_net_change ---------------------------------
    if (
        advertising_revenue_change_key in ready_keys
        and advertising_expense_change_key in ready_keys
    ):
        ar_change = ready_results[advertising_revenue_change_key]["value_decimal"]
        ae_change = ready_results[advertising_expense_change_key]["value_decimal"]
        # Frozen precision law: the residual -4 must survive.
        net_change = ar_change - ae_change
        new_fact_like = ready_results[advertising_revenue_change_key][
            "current_period_fact"
        ]
        prior_fact_like = ready_results[advertising_expense_change_key][
            "current_period_fact"
        ]
        advertising_net = _make_change_result(
            key=RESULT_KEY_ADVERTISING_NET_CHANGE,
            new_fact=new_fact_like,
            prior_fact=prior_fact_like,
            change_value=net_change,
            comparison_basis=comparison_basis,
        )
    else:
        advertising_net = _withheld_result(
            key=RESULT_KEY_ADVERTISING_NET_CHANGE,
            new_fact=ready_results.get(advertising_revenue_change_key, {}).get(
                "current_period_fact"
            )
            if advertising_revenue_change_key in ready_keys
            else None,
            prior_fact=ready_results.get(advertising_expense_change_key, {}).get(
                "current_period_fact"
            )
            if advertising_expense_change_key in ready_keys
            else None,
            reason="dependency_suppressed",
        )
    results_by_key[RESULT_KEY_ADVERTISING_NET_CHANGE] = advertising_net

    # ---- Derived: advertising_current_period_net --------------------------
    by_metric_facts = _index_facts_by_metric(facts)
    ar_facts = by_metric_facts.get(FACT_KEY_ADVERTISING_REVENUE, [])
    ae_facts = by_metric_facts.get(FACT_KEY_ADVERTISING_EXPENSE, [])
    ar_current: Mapping[str, Any] | None = None
    ae_current: Mapping[str, Any] | None = None
    if ar_facts:
        ar_current, _ = _select_pair(ar_facts, comparison_basis)
    if ae_facts:
        ae_current, _ = _select_pair(ae_facts, comparison_basis)

    advertising_current_net: dict[str, Any]
    if (
        # frozen-spec 4a: native_admitted is provenance, never a gate
        isinstance(ar_current, Mapping)
        and isinstance(ae_current, Mapping)
    ):
        ar_dec = _coerce_decimal_text(ar_current.get("value_text"))
        ae_dec = _coerce_decimal_text(ae_current.get("value_text"))
        if ar_dec is not None and ae_dec is not None:
            advertising_current_net = _make_change_result(
                key=RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
                new_fact=ar_current,
                prior_fact=ae_current,
                change_value=ar_dec - ae_dec,
                comparison_basis=comparison_basis,
            )
        else:
            advertising_current_net = _withheld_result(
                key=RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
                new_fact=ar_current,
                prior_fact=ae_current,
                reason="fact_value_text_unparseable",
            )
    else:
        advertising_current_net = _withheld_result(
            key=RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET,
            new_fact=ar_current,
            prior_fact=ae_current,
            reason="dependency_suppressed",
        )
    results_by_key[RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET] = (
        advertising_current_net
    )

    # ---- Derived: advertising_share_of_revenue_change_pct -----------------
    # Numerator = advertising_revenue_change; denominator = total_revenue_change.
    advertising_share: dict[str, Any]
    if (
        advertising_revenue_change_key in ready_keys
        and total_revenue_change_key in ready_keys
    ):
        numerator_result = ready_results[advertising_revenue_change_key]
        denom_change = ready_results[total_revenue_change_key]["value_decimal"]
        denom_current_fact = ready_results[total_revenue_change_key][
            "current_period_fact"
        ]
        # Build a fact-shaped envelope so the ratio helper can read
        # unit / scale / sign / rounding_envelope consistently.
        if isinstance(denom_current_fact, Mapping):
            denom_fact_like: dict[str, Any] = dict(denom_current_fact)
        else:
            denom_fact_like = {}
        denom_fact_like["value_text"] = _format_decimal(denom_change)
        advertising_share = _make_ratio_result(
            numerator_result=numerator_result,
            denominator_fact_like=denom_fact_like,
            denominator_text=_format_decimal(denom_change),
            key=RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
        )
    else:
        advertising_share = _withheld_result(
            key=RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT,
            new_fact=None,
            prior_fact=None,
            reason="dependency_suppressed",
        )
    results_by_key[RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT] = (
        advertising_share
    )

    # ---- Sort results deterministically ---------------------------------
    all_results: list[dict[str, Any]] = [
        results_by_key[k] for k in sorted(results_by_key.keys())
    ]

    # ---- Availability ----------------------------------------------------
    has_any_ready = any(r.get("state") == "READY" for r in all_results)
    availability = "ready" if has_any_ready else "unavailable"

    # ---- Explanation (selected-only) -------------------------------------
    selected_for_explanation = [
        r for r in all_results if r.get("state") == "READY"
    ]
    explanation = _build_explanation(selected_for_explanation)
    _check_explanation_for_forbidden(explanation)

    # ---- Document --------------------------------------------------------
    subject = dict(case.get("subject") or {})
    facts_out: list[dict[str, Any]] = []
    for fact in facts:
        if not isinstance(fact, Mapping):
            continue
        facts_out.append(
            {
                "key": str(fact.get("key")),
                "period_end": _envelope_period_end(fact),
                "period_kind": _envelope_period_kind(fact),
                "period_start": _envelope_period_start(fact),
                "kind": _envelope_kind(fact),
                "value_text": str(fact.get("value_text")),
                "unit": _envelope_unit(fact),
                "scale_power10": _envelope_scale(fact),
                "sign_convention": _envelope_sign_convention(fact),
                "native_admitted": _envelope_native_admitted(fact),
                "native_ref": _nullable(_envelope_native_ref(fact)),
                "definition": _envelope_definition(fact),
                "metric": _envelope_metric(fact),
                "basis": _envelope_basis(fact),
                "role": _envelope_role(fact),
                "target": _nullable(_envelope_target(fact)),
                "perimeter": _envelope_perimeter(fact),
                "event": _envelope_event(fact),
                "published_at": _envelope_published_at(fact),
                "display_quantum": _envelope_display_quantum(fact),
                "evidence": _envelope_evidence(fact),
            }
        )

    _omitted_keys = [
        r.get("key") for r in all_results if not r.get("inputs_present")
    ]
    # ``_degraded`` builds a closed ``{dependency, reason, state}`` entry, so
    # the earlier form of this set read a ``fact_key`` that never existed and
    # was always ``{None}`` -- a deduplication guard that could not fire. It
    # is behaviour-neutral today (the two sides use disjoint vocabularies:
    # fact metrics here, result keys below) and is corrected so it stays that
    # way by construction rather than by luck.
    _already_degraded = {
        d.get("dependency") for d in degraded_facts if isinstance(d, Mapping)
    }
    for _key in _omitted_keys:
        if _key and _key not in _already_degraded:
            degraded_facts.append(_degraded(_key, "inputs_absent_result_omitted"))

    # Ruling A: every emittable result key whose inputs were never
    # present (whether the entry survived the ``_omitted_keys`` filter
    # above OR was never created in ``_compose_changes``) must show up
    # in ``degraded_dependencies`` so downstream consumers can see the
    # full unmet-result set.
    _emittable_keys = [
        "total_revenue_change",
        "advertising_revenue_change",
        "advertising_expense_change",
        "advertising_net_change",
        "advertising_current_period_net",
        "advertising_share_of_revenue_change_pct",
    ]
    _present_result_keys = {
        r.get("key") for r in all_results if r.get("inputs_present")
    }
    for _rk in _emittable_keys:
        if _rk in _present_result_keys:
            continue
        # Skip the keys the loop above already covered.
        if _rk in _omitted_keys:
            continue
        degraded_facts.append(
            _degraded(_rk, "ready_result_unavailable_for_" + _rk)
        )

    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at_text,
        "subject": subject,
        "comparison_basis": comparison_basis,
        "facts": facts_out,
        # Ruling A: a result is emitted only when its inputs exist, so a
        # result with empty ``input_refs`` is an absence, not an answer — it
        # belongs in ``degraded_dependencies``, never in ``results`` (where
        # the contract requires ``input_refs`` minItems 1). Ruling B: project
        # every survivor onto the contract's closed key set.
        "results": [
            _emit_result(r) for r in all_results if r.get("inputs_present")
        ],
        "explanation": explanation,
        "degraded_dependencies": degraded_facts,
        "source_records": list(source_records) if isinstance(source_records, list) else list(source_records or ()),
        "availability": availability,
    }

    _assert_no_forbidden_authority_keys(document)
    _assert_document_matches_contract_shape(document)
    _assert_provenance_pointers_resolve(document)

    return document


__all__ = [
    "CONTRACT_ID",
    "SCHEMA_VERSION",
    "CaseShapeError",
    "FACT_KEY_TOTAL_REVENUE",
    "FACT_KEY_ADVERTISING_REVENUE",
    "FACT_KEY_ADVERTISING_EXPENSE",
    "RESULT_KEY_TOTAL_REVENUE_CHANGE",
    "RESULT_KEY_ADVERTISING_REVENUE_CHANGE",
    "RESULT_KEY_ADVERTISING_EXPENSE_CHANGE",
    "RESULT_KEY_ADVERTISING_NET_CHANGE",
    "RESULT_KEY_ADVERTISING_CURRENT_PERIOD_NET",
    "RESULT_KEY_ADVERTISING_SHARE_OF_REVENUE_CHANGE_PCT",
    "project_economic_change",
]
