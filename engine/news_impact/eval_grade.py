"""A3 grading core: gold/candidate normalisation and the per-item critical-numeric grader.

Implements the seat-accepted design packet ``A3_eval`` section 4 (frozen spec):
normalisation §4.1-§4.6 and the §4.7 ``grade_critical_numeric`` pseudocode, per
masterplan §9-§11 (evaluation pre-registration; MASTERPLAN.md §11 freeze-before-
outcomes) and PHASE0_FREEZE_2026-10-11 §6/§7 grading definitions 1-3. The frozen
endpoint registry is ``contracts/news_impact/endpoints.v1.json``; graded quantity
shapes are the Phase 0 frozen contract ``news_impact_event.v1.schema.json``
(sha256 prefix ``3edc7139``; closed enums never widened). Rulings R1-R4 and the
Wave 3 seat rulings W3-R1..W3-R6 bind; W3-R3 (strip confidence/probability/score/
price_target/fair_value/sentiment/contagion keys at ingest into ``stripped_fields``)
overrides design §7 Q9.

Totality closures this module adds over the §4.7 pseudocode (the pseudocode indexes
``sys[field]`` and ``gold[field]`` and never handles: a missing candidate field key,
a malformed candidate quantity, period-as-typed-absence, unknown unit tokens, or a
``null`` gold/candidate packet). Every closure is candidate-side (graded outcome,
never an exception, so a schema-invalid auto-published packet still lands in the 98%
denominator exactly as design case 2 demands); gold-side malformation raises a typed
``EvalGradeError`` code because the label store is adjudicated and schema-validated
upstream. Outcomes are exactly the §4.7 closed set; ``bound`` is NOT compared
(§4.6 CanonPresent omits it — frozen spec, not an oversight here); an unknown unit
token canonicalises to ``UNKNOWN_UNIT`` which equals nothing, not even itself (§2
assumption A7: "unknown unit tokens mismatch; they are never guessed").

Pure leaf (W3-R4): no network, no subprocess, no file I/O, no clock; span replay is
an injected ``span_verifier`` callable (the receipt lane wraps owner
``engine.company_intelligence.documents.verify_span``), never reimplemented here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

__all__ = [
    "EvalGradeError",
    "CODES",
    "OUTCOMES",
    "CRITICAL_NUMERIC_FIELDS",
    "SCALE_WORDS",
    "UNIT_MAP",
    "FORBIDDEN_KEY_RE",
    "CanonAbsent",
    "CanonQuantity",
    "CandidatePacket",
    "GradedItem",
    "CaseForGrading",
    "canonical_json",
    "strip_forbidden_keys",
    "ingest_candidate",
    "parse_number",
    "canon_period",
    "normalise_quantity",
    "grade_critical_numeric_field",
    "grade_case",
    "grade_batch",
    "graded_items_to_dicts",
]


class EvalGradeError(Exception):
    """Module error carrying a closed code string (W3-R5).

    ``code`` is always a member of :data:`CODES`; the string form is
    ``"<CODE>: <detail>"`` so tests assert the exact code prefix.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


#: Closed error-code set (W3-R5). Every code has a test asserting the exact string.
CODES: frozenset[str] = frozenset(
    {
        "TEMPLATE_NOT_GRADED",
        "GOLD_PACKET_ABSENT",
        "GOLD_PACKET_MALFORMED",
        "GOLD_FIELD_MISSING",
        "GOLD_FIELD_MALFORMED",
        "GOLD_ABSENCE_MALFORMED",
        "NUMBER_UNPARSABLE",
        "QUANTITY_FORM_UNKNOWN",
        "PERIOD_MALFORMED",
        "CANDIDATE_PACKET_MALFORMED",
        "ROW_MALFORMED",
    }
)

#: Closed outcome set — exactly the §4.7 marks (freeze §3 gate 4 field marks).
OUTCOMES: frozenset[str] = frozenset(
    {"correct", "wrong_value", "wrong_absence", "unevidenced"}
)

#: Critical numeric fields per template (design §4.7, frozen; matches the frozen
#: contract's required quantity slots for each template).
CRITICAL_NUMERIC_FIELDS: Mapping[str, tuple[str, ...]] = {
    "capital_allocation_event.v1": (
        "incremental_amount",
        "remaining_authorization",
        "executed_amount",
    ),
    "demand_guidance_contract_event.v1": ("stated_amount",),
    "strategic_product_partnership_event.v1": ("stated_quantity",),
}

#: Scale words in the §4.6 literal iteration order (the frozen algorithm breaks on
#: the FIRST whole-word match in THIS order; a fixed tuple, not a dict, so the
#: sequence is explicit and deterministic). Matched in ``claimed_quote`` only.
SCALE_WORDS: tuple[tuple[str, Decimal], ...] = (
    ("thousand", Decimal(10) ** 3),
    ("million", Decimal(10) ** 6),
    ("billion", Decimal(10) ** 9),
    ("trillion", Decimal(10) ** 12),
    ("k", Decimal(10) ** 3),
    ("m", Decimal(10) ** 6),
    ("bn", Decimal(10) ** 9),
    ("t", Decimal(10) ** 12),
)

#: Unit canonicalisation map — §4.6 / endpoints.v1.json ``normalisation.unit_map``
#: verbatim. Keys are matched on ``unit.strip().lower()``; anything else maps to
#: ``UNKNOWN_UNIT`` (never guessed, never equal).
UNIT_MAP: dict[str, str] = {
    "usd": "USD",
    "us$": "USD",
    "$": "USD",
    "dollars": "USD",
    "dollar": "USD",
    "eur": "EUR",
    "€": "EUR",
    "gbp": "GBP",
    "£": "GBP",
    "shares": "shares",
    "share": "shares",
    "percent": "percent",
    "%": "percent",
    "pct": "percent",
    "pp": "percent",
    "units": "units",
    "unit": "units",
}

#: Forbidden quality-score key pattern (W3-R3; A3 §4.4 aggregation strip, widened
#: with ``sentiment``/``contagion``/``price_target`` per W3-R3). Applied to dict
#: KEYS at ingest; no frozen-contract property name matches it (verified against
#: news_impact_event.v1.schema.json).
FORBIDDEN_KEY_RE = re.compile(
    r"confidence|probability|score|target|fair.?value|rating|sentiment|contagion",
    re.IGNORECASE,
)

_ABSENCE_SCHEMAS = frozenset({"field_absence.v1", "typed_absence.v1"})
_FORM_PRESENT = frozenset({"point", "range"})
_QUANTITY_FORMS = frozenset({"point", "range", "absent"})

SpanVerifier = Callable[[Mapping[str, Any]], bool]
CanonValue = Union["CanonAbsent", "CanonQuantity"]


def canonical_json(obj: Any) -> str:
    """Canonical JSON — lane ruling: sort_keys, compact separators, ensure_ascii off."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _dec_str(value: Decimal) -> str:
    """Stable string form of a Decimal for JSON emission (1.50 -> "1.5")."""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def strip_forbidden_keys(obj: Any, _path: str = "") -> tuple[Any, list[str]]:
    """Recursively drop dict keys matching :data:`FORBIDDEN_KEY_RE` (W3-R3).

    Returns ``(cleaned, stripped_paths)`` where stripped paths are dotted key
    paths like ``confidence`` or ``packet.confidence``. Lists are walked; every
    other type is returned as-is. Pure; no key is ever guessed or renamed.
    """
    if isinstance(obj, dict):
        clean: dict[str, Any] = {}
        stripped: list[str] = []
        for key in sorted(obj.keys(), key=str):
            value = obj[key]
            child = f"{_path}.{key}" if _path else str(key)
            if isinstance(key, str) and FORBIDDEN_KEY_RE.search(key):
                stripped.append(child)
                continue
            clean[key], sub = strip_forbidden_keys(value, child)
            stripped.extend(sub)
        return clean, stripped
    if isinstance(obj, list):
        items: list[Any] = []
        stripped: list[str] = []
        for idx, value in enumerate(obj):
            item, sub = strip_forbidden_keys(value, f"{_path}[{idx}]")
            items.append(item)
            stripped.extend(sub)
        return items, stripped
    return obj, []


@dataclass(frozen=True)
class CandidatePacket:
    """Ingested candidate: forbidden keys stripped (W3-R3), paths recorded."""

    packet: Optional[dict[str, Any]]
    stripped_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet": self.packet,
            "stripped_fields": list(self.stripped_fields),
        }


def ingest_candidate(packet: Any) -> CandidatePacket:
    """Strip forbidden quality-score keys from a candidate packet (W3-R3).

    ``None`` passes through (``packet=None``, nothing stripped) so abstaining
    candidates stay visible to the grader. A non-mapping, non-None packet raises
    ``CANDIDATE_PACKET_MALFORMED``; the grader catches that and grades every
    critical field as an outcome (totality), never an exception.
    """
    if packet is None:
        return CandidatePacket(None, ())
    if not isinstance(packet, Mapping):
        raise EvalGradeError("CANDIDATE_PACKET_MALFORMED", type(packet).__name__)
    clean, stripped = strip_forbidden_keys(dict(packet))
    return CandidatePacket(clean, tuple(sorted(stripped)))


def parse_number(token: Any) -> Decimal:
    """§4.6 ``parse_number``: exact Decimal; grouping separators stripped.

    Rejects NaN/Inf and anything Decimal cannot parse exactly
    (``NUMBER_UNPARSABLE``). JSON numbers arrive as int/float and are stringified
    first (``str(value)``), matching the frozen pseudocode.
    """
    text = str(token).strip().replace(",", "").replace("_", "")
    if not text:
        raise EvalGradeError("NUMBER_UNPARSABLE", repr(str(token)))
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise EvalGradeError("NUMBER_UNPARSABLE", repr(text)) from exc
    if not number.is_finite():
        raise EvalGradeError("NUMBER_UNPARSABLE", repr(text))
    return number


def _scale_from_quote(
    claimed_quote: Optional[str], note_prefix: str, notes: list[str]
) -> Decimal:
    """First §4.6 scale word appearing as a whole word in the (lowered) quote."""
    if not claimed_quote:
        return Decimal(1)
    qlow = claimed_quote.lower()
    for word, factor in SCALE_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", qlow):
            notes.append(f"{note_prefix}:{word}")
            return factor
    return Decimal(1)


def canon_period(period: Any) -> tuple:
    """Canonicalise a quantity ``period`` (§4.6).

    Present fiscal period -> ``("period", year, quarter, period_kind,
    calendar_end, end_year)`` where ``end_year`` participates only when
    ``period_kind == "multi_year"`` (None otherwise; FY is not Q4, null quarter
    is not 4 — the tuple keeps them distinct). Typed-absence period ->
    ``("period_absent", schema, reason)`` with the exact absence enum token.
    Anything else is malformed (``PERIOD_MALFORMED``).
    """
    if isinstance(period, Mapping):
        schema = period.get("schema")
        if schema in _ABSENCE_SCHEMAS:
            return ("period_absent", str(schema), str(period.get("reason", "")))
        try:
            year = period["year"]
            quarter = period.get("quarter")
            kind = period["period_kind"]
        except KeyError as exc:
            raise EvalGradeError("PERIOD_MALFORMED", f"missing {exc.args[0]}") from exc
        if not isinstance(year, int) or not isinstance(kind, str):
            raise EvalGradeError("PERIOD_MALFORMED", "year/period_kind type")
        end_year = period.get("end_year") if kind == "multi_year" else None
        calendar_end = period.get("calendar_end")
        return ("period", year, quarter, kind, calendar_end, end_year)
    raise EvalGradeError("PERIOD_MALFORMED", type(period).__name__)


def _absence_token(absence: Any) -> tuple[str, str]:
    if not isinstance(absence, Mapping):
        raise EvalGradeError("GOLD_ABSENCE_MALFORMED", type(absence).__name__)
    schema = absence.get("schema")
    reason = absence.get("reason")
    if schema not in _ABSENCE_SCHEMAS or not isinstance(reason, str) or not reason:
        raise EvalGradeError("GOLD_ABSENCE_MALFORMED", f"{schema!r}/{reason!r}")
    return str(schema), reason


@dataclass(frozen=True)
class CanonAbsent:
    """Canonical typed absence: exact schema + reason (never collapsed, §7 Q3)."""

    schema: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"form": "absent", "schema": self.schema, "reason": self.reason}


@dataclass(frozen=True)
class CanonQuantity:
    """Canonical present quantity (§4.6 CanonPresent): post-normalisation view."""

    form: str
    values: tuple[Decimal, ...]
    unit: str
    currency: str
    basis: Any
    period: tuple
    negated: bool
    unit_raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "form": self.form,
            "values": [_dec_str(v) for v in self.values],
            "unit": self.unit,
            "currency": self.currency,
            "basis": self.basis,
            "period": list(self.period),
            "negated": self.negated,
            "unit_raw": self.unit_raw,
        }


def _quote_of(qty: Mapping[str, Any]) -> Optional[str]:
    evidence = qty.get("evidence")
    if isinstance(evidence, Mapping):
        quote = evidence.get("claimed_quote")
        if isinstance(quote, str):
            return quote
    return None


def normalise_quantity(
    qty: Any, claimed_quote: Optional[str] = None, notes: Optional[list[str]] = None
) -> CanonValue:
    """§4.6 ``normalise_quantity`` — applied identically to gold and candidates.

    ``absent`` form -> :class:`CanonAbsent` (exact schema+reason). ``point`` /
    ``range`` -> :class:`CanonQuantity` with §4.6 scale words (whole-word match in
    ``claimed_quote`` only; never inferred from unit or magnitude), unit map
    (unknown token -> ``UNKNOWN_UNIT``), upper-cased currency, basis as-is, canon
    period, boolean negation. Malformed shapes raise typed codes
    (``QUANTITY_FORM_UNKNOWN`` / ``NUMBER_UNPARSABLE`` / ``PERIOD_MALFORMED`` /
    ``GOLD_ABSENCE_MALFORMED``). Provenance notes (``scale_word:<w>``) are
    appended to ``notes`` when a list is supplied.
    """
    if not isinstance(qty, Mapping):
        raise EvalGradeError("QUANTITY_FORM_UNKNOWN", type(qty).__name__)
    form = qty.get("form")
    if form == "absent":
        schema, reason = _absence_token(qty.get("absence"))
        return CanonAbsent(schema, reason)
    if form not in _FORM_PRESENT:
        raise EvalGradeError("QUANTITY_FORM_UNKNOWN", repr(form))
    notes = notes if notes is not None else []
    scale = _scale_from_quote(claimed_quote, "scale_word", notes)
    unit_raw = qty.get("unit")
    unit_token = str(unit_raw).strip().lower() if unit_raw is not None else ""
    unit = UNIT_MAP.get(unit_token, "UNKNOWN_UNIT") if unit_token else "UNKNOWN_UNIT"
    currency_raw = qty.get("currency")
    currency = str(currency_raw).upper() if currency_raw is not None else ""
    if form == "point":
        if "value" not in qty:
            raise EvalGradeError("GOLD_FIELD_MALFORMED", "point missing value")
        values = (parse_number(qty["value"]) * scale,)
    else:
        if "low" not in qty or "high" not in qty:
            raise EvalGradeError("GOLD_FIELD_MALFORMED", "range missing low/high")
        values = (
            parse_number(qty["low"]) * scale,
            parse_number(qty["high"]) * scale,
        )
    period = canon_period(qty.get("period"))
    return CanonQuantity(
        form=str(form),
        values=values,
        unit=unit,
        currency=currency,
        basis=qty.get("basis"),
        period=period,
        negated=bool(qty.get("negated")),
        unit_raw=unit_token,
    )


def canon_equal(gold: CanonValue, cand: CanonValue) -> tuple[bool, tuple[str, ...]]:
    """§4.6 equality after normalisation; returns ``(equal, mismatched_components)``.

    Components (fixed order): form, value, unit, currency, basis, period, negated.
    ``UNKNOWN_UNIT`` equals nothing (A3 assumption A7). ``USD`` vs ``NA`` is a
    currency mismatch. Decimal equality is numeric (trailing zeros irrelevant);
    range bounds compare order-sensitively (an inverted range is incorrect).
    """
    if isinstance(gold, CanonAbsent) or isinstance(cand, CanonAbsent):
        if isinstance(gold, CanonAbsent) and isinstance(cand, CanonAbsent):
            ok = gold.schema == cand.schema and gold.reason == cand.reason
            return ok, () if ok else ("absence_reason",)
        return False, ("form",)
    mismatched: list[str] = []
    if gold.form != cand.form:
        mismatched.append("form")
    elif gold.values != cand.values:
        mismatched.append("value")
    if not (
        gold.unit != "UNKNOWN_UNIT"
        and cand.unit != "UNKNOWN_UNIT"
        and gold.unit == cand.unit
    ):
        mismatched.append("unit")
    if gold.currency != cand.currency:
        mismatched.append("currency")
    if gold.basis != cand.basis:
        mismatched.append("basis")
    if gold.period != cand.period:
        mismatched.append("period")
    if gold.negated != cand.negated:
        mismatched.append("negated")
    return (not mismatched, tuple(mismatched))


def _span_ok(
    qty: Mapping[str, Any], span_verifier: Optional[SpanVerifier], notes: list[str]
) -> bool:
    """§4.7 ``span_ok``: present numbers must carry replayable owner evidence.

    Missing/unusable evidence -> not ok. Evidence present: the injected verifier
    decides (owner ``verify_span`` wrapper); no verifier injected -> assumed ok
    with note ``span_unverified`` (pure leaf cannot replay spans itself, W3-R4).
    A raising verifier counts as a failed replay (``span_verifier_error``).
    """
    evidence = qty.get("evidence")
    if not isinstance(evidence, Mapping) or "span" not in evidence:
        notes.append("evidence_missing")
        return False
    if span_verifier is None:
        notes.append("span_unverified")
        return True
    try:
        ok = bool(span_verifier(evidence))
    except Exception:  # noqa: BLE001 - owner verify_span signals failure by raising
        notes.append("span_verifier_error")
        return False
    if not ok:
        notes.append("span_verify_failed")
    return ok


@dataclass(frozen=True)
class GradedItem:
    """One frozen graded slot — the seam the receipt lane folds over.

    ``outcome`` ∈ :data:`OUTCOMES` (§4.7 closed set); ``gold_value`` /
    ``candidate_value`` are JSON-compatible normalised views (canon ``to_dict``);
    ``notes`` is a tuple of deterministic plain-string provenance tokens.
    No confidence/probability/score/price_target/fair_value/sentiment/contagion
    key is ever emitted (W3-R3).
    """

    case_id: str
    fold: str
    template: str
    field: str
    outcome: str
    gold_value: Optional[dict[str, Any]]
    candidate_value: Optional[dict[str, Any]]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "fold": self.fold,
            "template": self.template,
            "field": self.field,
            "outcome": self.outcome,
            "gold_value": self.gold_value,
            "candidate_value": self.candidate_value,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CaseForGrading:
    """One joined (manifest row, gold label, candidate emission) input (W3-R4:
    ledgers/manifests/packets are injected as data; nothing is read from disk)."""

    case_id: str
    fold: str
    template: str
    disposition: str
    gold_packet: Optional[dict[str, Any]] = None
    candidate_packet: Optional[dict[str, Any]] = None

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "CaseForGrading":
        if not isinstance(row, Mapping):
            raise EvalGradeError("ROW_MALFORMED", type(row).__name__)
        case_id = row.get("case_id")
        template = row.get("template")
        if not isinstance(case_id, str) or not case_id:
            raise EvalGradeError("ROW_MALFORMED", "case_id")
        if not isinstance(template, str):
            raise EvalGradeError("ROW_MALFORMED", "template")
        return cls(
            case_id=case_id,
            fold=str(row.get("fold", "")),
            template=template,
            disposition=str(row.get("disposition", "")),
            gold_packet=row.get("gold_packet"),
            candidate_packet=row.get("candidate_packet"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "fold": self.fold,
            "template": self.template,
            "disposition": self.disposition,
            "gold_packet": self.gold_packet,
            "candidate_packet": self.candidate_packet,
        }


def _stripped_note(stripped: Sequence[str]) -> Optional[str]:
    if not stripped:
        return None
    return "ingest_stripped:" + "|".join(sorted(set(stripped)))


def grade_critical_numeric_field(
    *,
    case_id: str,
    fold: str,
    template: str,
    field: str,
    gold_quantity: Any,
    candidate_quantity: Any,
    span_verifier: Optional[SpanVerifier] = None,
) -> GradedItem:
    """§4.7 ``grade_critical_numeric`` — one (case_id, template, field) slot.

    Precedence is the frozen pseudocode order: (1) present candidate with failed/
    missing evidence -> ``unevidenced``; (2) gold absent -> ``correct`` on exact
    absence-schema+reason match else ``wrong_absence``; (3) candidate absent ->
    ``wrong_value``; (4) canon equality -> ``correct``; else ``wrong_value``.
    Candidate-side totality closures (missing key, non-dict, malformed numbers,
    malformed period) grade to an outcome with a note and never raise; gold-side
    malformation raises a typed ``EvalGradeError`` code.
    """
    notes: list[str] = []
    cand = candidate_quantity
    cand_is_dict = isinstance(cand, Mapping)
    cand_form = cand.get("form") if cand_is_dict else None
    cand_present = cand_form in _FORM_PRESENT

    # (1) unevidenced — present number whose evidence is missing or fails replay
    if cand_present and not _span_ok(cand, span_verifier, notes):
        gold_canon: Optional[CanonValue]
        try:
            gold_canon = normalise_quantity(
                _gold_quantity_wrapper(field, gold_quantity), None
            )
            gold_view = gold_canon.to_dict()
        except EvalGradeError:
            gold_view = None
        cand_view = _candidate_view(cand)
        return GradedItem(
            case_id, fold, template, field, "unevidenced", gold_view, cand_view,
            tuple(notes),
        )

    gold_qty = _gold_quantity_wrapper(field, gold_quantity)
    gold_canon = normalise_quantity(gold_qty, _quote_of(gold_qty), notes)

    # (2) gold absent — exact schema+reason match required (§7 Q3: no collapsing)
    if isinstance(gold_canon, CanonAbsent):
        if cand_form == "absent" and isinstance(cand, Mapping):
            try:
                cand_canon = normalise_quantity(cand)
            except EvalGradeError as exc:
                notes.append(f"candidate_quantity_malformed:{exc.code}")
                cand_view = _candidate_view(cand)
                return GradedItem(
                    case_id, fold, template, field, "wrong_absence",
                    gold_canon.to_dict(), cand_view, tuple(notes),
                )
            equal, bad = canon_equal(gold_canon, cand_canon)
            if equal:
                return GradedItem(
                    case_id, fold, template, field, "correct",
                    gold_canon.to_dict(), cand_canon.to_dict(), tuple(notes),
                )
            notes.append("mismatch:" + "|".join(bad))
            return GradedItem(
                case_id, fold, template, field, "wrong_absence",
                gold_canon.to_dict(), cand_canon.to_dict(), tuple(notes),
            )
        elif cand_present:
            notes.append("candidate_present_where_gold_absent")
        else:
            notes.append(
                "candidate_field_missing" if cand is None else "candidate_field_malformed"
            )
        return GradedItem(
            case_id, fold, template, field, "wrong_absence",
            gold_canon.to_dict(), _candidate_view(cand), tuple(notes),
        )

    # (3) candidate absent / missing / malformed-present -> wrong_value
    if not cand_is_dict or "form" not in cand:
        notes.append("candidate_field_missing" if cand is None else "candidate_field_malformed")
        return GradedItem(
            case_id, fold, template, field, "wrong_value",
            gold_canon.to_dict(), _candidate_view(cand), tuple(notes),
        )
    if cand_form == "absent":
        notes.append("candidate_absent_where_gold_present")
        return GradedItem(
            case_id, fold, template, field, "wrong_value",
            gold_canon.to_dict(), _candidate_view(cand), tuple(notes),
        )
    if cand_form not in _FORM_PRESENT:
        notes.append(f"candidate_quantity_form_unknown:{cand_form!r}")
        return GradedItem(
            case_id, fold, template, field, "wrong_value",
            gold_canon.to_dict(), _candidate_view(cand), tuple(notes),
        )

    # (4) canon comparison (candidate malformation -> wrong_value, never raise)
    try:
        cand_canon = normalise_quantity(cand, _quote_of(cand), notes)
    except EvalGradeError as exc:
        notes.append(f"candidate_quantity_malformed:{exc.code}")
        return GradedItem(
            case_id, fold, template, field, "wrong_value",
            gold_canon.to_dict(), _candidate_view(cand), tuple(notes),
        )
    equal, bad = canon_equal(gold_canon, cand_canon)
    seen_unknown: set[str] = set()
    for canon in (gold_canon, cand_canon):
        if canon.unit == "UNKNOWN_UNIT" and canon.unit_raw and canon.unit_raw not in seen_unknown:
            seen_unknown.add(canon.unit_raw)
            notes.append(f"unit_unknown:{canon.unit_raw}")
    if equal:
        return GradedItem(
            case_id, fold, template, field, "correct",
            gold_canon.to_dict(), cand_canon.to_dict(), tuple(notes),
        )
    notes.append("mismatch:" + "|".join(bad))
    return GradedItem(
        case_id, fold, template, field, "wrong_value",
        gold_canon.to_dict(), cand_canon.to_dict(), tuple(notes),
    )


def _gold_quantity_wrapper(field: str, gold_quantity: Any) -> Mapping[str, Any]:
    """Gold is strict: an explicitly passed quantity must be a well-formed dict."""
    if gold_quantity is None:
        raise EvalGradeError("GOLD_FIELD_MISSING", field)
    if not isinstance(gold_quantity, Mapping):
        raise EvalGradeError("GOLD_FIELD_MALFORMED", f"{field}: {type(gold_quantity).__name__}")
    form = gold_quantity.get("form")
    if form not in _QUANTITY_FORMS:
        raise EvalGradeError("GOLD_FIELD_MALFORMED", f"{field}: form={form!r}")
    return gold_quantity


def _candidate_view(cand: Any) -> Optional[dict[str, Any]]:
    """Best-effort JSON view of a (possibly malformed) candidate quantity."""
    if cand is None:
        return {"form": "missing"}
    if not isinstance(cand, Mapping):
        return {"form": "malformed", "type": type(cand).__name__}
    view: dict[str, Any] = {"form": cand.get("form")}
    if cand.get("form") == "absent":
        absence = cand.get("absence")
        if isinstance(absence, Mapping):
            view["schema"] = absence.get("schema")
            view["reason"] = absence.get("reason")
    return view


def grade_case(
    *,
    case_id: str,
    fold: str,
    template: str,
    gold_packet: Any,
    candidate_packet: Any = None,
    span_verifier: Optional[SpanVerifier] = None,
) -> tuple[GradedItem, ...]:
    """Grade every critical numeric field of one case (§4.7 field list, in order).

    ``gold_packet=None`` raises ``GOLD_PACKET_ABSENT`` (use :func:`grade_batch`,
    which skips abstaining rows per the §4.7 ``continue``); a ``None`` /
    malformed candidate packet grades every slot to an outcome (A3 §4.9
    current_news_stack: "all slots wrong_absence/wrong_value because no packet").
    """
    fields = CRITICAL_NUMERIC_FIELDS.get(template)
    if fields is None:
        raise EvalGradeError("TEMPLATE_NOT_GRADED", template)
    if gold_packet is None:
        raise EvalGradeError("GOLD_PACKET_ABSENT", case_id)
    if not isinstance(gold_packet, Mapping):
        raise EvalGradeError("GOLD_PACKET_MALFORMED", type(gold_packet).__name__)
    try:
        ingested = ingest_candidate(candidate_packet)
    except EvalGradeError:
        ingested = CandidatePacket(None, ())
    strip_note = _stripped_note(ingested.stripped_fields)
    base_notes: tuple[str, ...] = (strip_note,) if strip_note else ()
    if ingested.packet is None:
        why = (
            "candidate_packet_absent"
            if candidate_packet is None
            else "candidate_packet_malformed"
        )
        base_notes = base_notes + (why,)
    items: list[GradedItem] = []
    for field_name in fields:
        gold_qty = gold_packet.get(field_name)
        if gold_qty is None:
            raise EvalGradeError("GOLD_FIELD_MISSING", f"{case_id}:{field_name}")
        cand_qty = (
            ingested.packet.get(field_name) if ingested.packet is not None else None
        )
        item = grade_critical_numeric_field(
            case_id=case_id,
            fold=fold,
            template=template,
            field=field_name,
            gold_quantity=gold_qty,
            candidate_quantity=cand_qty,
            span_verifier=span_verifier,
        )
        if base_notes:
            item = GradedItem(
                item.case_id,
                item.fold,
                item.template,
                item.field,
                item.outcome,
                item.gold_value,
                item.candidate_value,
                item.notes + base_notes,
            )
        items.append(item)
    return tuple(items)


def grade_batch(
    rows: Iterable[Union[CaseForGrading, Mapping[str, Any]]],
    *,
    dispositions: Optional[Iterable[str]] = None,
    span_verifier: Optional[SpanVerifier] = None,
) -> tuple[GradedItem, ...]:
    """Fold-ready batch: one GradedItem per (case_id, template, field).

    Mirrors the §4.7 ``critical_numeric_correctness`` join semantics: rows whose
    disposition is not in ``dispositions`` (when given) contribute nothing, and
    rows with ``gold_packet=None`` are skipped (the pseudocode ``continue`` —
    abstention is printed by the receipt, not silently graded). Rows whose
    candidate packet is missing are still graded when their disposition passes
    (A3 §4.9 baselines without packets; design case 2 keeps a claimed
    auto-publish in the 98% denom). Output is sorted by
    ``(case_id, template, field, canonical JSON)`` so permuted input order yields
    byte-identical canonical JSON (W3-R6).
    """
    allowed = frozenset(dispositions) if dispositions is not None else None
    items: list[GradedItem] = []
    for row in rows:
        case = row if isinstance(row, CaseForGrading) else CaseForGrading.from_dict(row)
        if allowed is not None and case.disposition not in allowed:
            continue
        if case.gold_packet is None:
            continue
        items.extend(
            grade_case(
                case_id=case.case_id,
                fold=case.fold,
                template=case.template,
                gold_packet=case.gold_packet,
                candidate_packet=case.candidate_packet,
                span_verifier=span_verifier,
            )
        )
    items.sort(
        key=lambda item: (
            item.case_id,
            item.template,
            item.field,
            canonical_json(item.to_dict()),
        )
    )
    return tuple(items)


def graded_items_to_dicts(items: Sequence[GradedItem]) -> list[dict[str, Any]]:
    """JSON-compatible list of ``to_dict`` views, in the given order."""
    return [item.to_dict() for item in items]
