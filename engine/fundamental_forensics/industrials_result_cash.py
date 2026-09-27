"""Pure, signed, exact-decimal result-to-cash derivations (T04).

This module is the production constructor for the closed
``derive_result_cash`` / ``qualify_operands`` typed-limitation pair, plus
the comparison-receipt constructor ``build_comparison_receipt``.  It is
deliberately new: no imports from ``engine.fundamental_forensics.detectors``
or any other private forensic helper, no I/O, no persistence, no model
call, no store, no ranking/valuation.  All numbers are exact-decimal text
produced from ``Decimal``; a loss keeps its sign; equal nulls never
certify comparability.

The forensic refusal idiom mirrors the typed-limitation return SHAPE of
``detectors._not_evaluable`` (``engine/fundamental_forensics/detectors.py``
on the research branch): a closed dict that carries the original refs,
the formula identity/version, the typed limitations and the receipt
reference — never an exception, never a fabricated 0.

The package has no VERSION convention yet; this module declares
``FORMULA_VERSION = 'v1'`` as a new contract.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


FORMULA_VERSION = "v1"

ALLOWED_FORMULAS: tuple[str, ...] = (
    "growth_pct",
    "margin_pct",
    "paired_remeasurement",
    "cash_after_capital_payments",
    "cash_rollforward",
    "segment_change_bridge",
    "final_vs_preview",
)

_ALLOWED_PURPOSES: frozenset[str] = frozenset(
    {"same_period", "year_over_year", "final_vs_preview", "segment_bridge", "rollforward"}
)

_REQUIRED_QUALIFIER_FIELDS: tuple[str, ...] = (
    "owner_ref",
    "revision",
    "digest",
    "semantic_selector",
    "metric",
    "unit",
    "scale",
    "currency",
    "stock_or_flow",
    "period",
    "business_dimensions",
    "basis",
    "source_mode",
    "quality",
)

_NON_FINITE_TOKENS: frozenset[str] = frozenset({"nan", "inf", "-inf", "infinity", "-infinity", "+inf", "-inf"})

_REFUSAL_UNAUTHORIZED_REF_FORMAT: str = "operand_ref_malformed"

CLOSED_RESULT_KEYS: frozenset[str] = frozenset(
    {
        "status",
        "formula",
        "formula_version",
        "value",
        "unit",
        "scale",
        "currency",
        "operand_refs",
        "limitations",
        "receipt_ref",
        "label",
    }
)


@dataclass(frozen=True)
class _Operand:
    """Validated operand, carrying only the fields the module needs."""

    owner_ref: str
    revision: str
    digest: str
    semantic_selector: Mapping[str, Any]
    metric: str
    unit: str
    scale: int
    currency: str
    stock_or_flow: str
    period: Mapping[str, Any]
    business_dimensions: Mapping[str, Any]
    basis: Mapping[str, Any]
    source_mode: str
    quality: Mapping[str, Any]
    value_text: str | None
    absence_reason: str | None


def _operand_ref_tuple(op: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(op["owner_ref"]), str(op["revision"]), str(op["digest"]))


def _decimal_text(value: Any) -> str:
    """Normalize a Decimal to its canonical text form (no exponent)."""
    return format(Decimal(value), "f")


# ---------------------------------------------------------------------------
# Comparison receipt constructor — production
# ---------------------------------------------------------------------------


def build_comparison_receipt(
    purpose: str,
    cells: Iterable[Mapping[str, Any]],
    *,
    checked: Mapping[str, bool] | None = None,
    unknowns: Sequence[str] = (),
    transformations: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build the production comparison receipt.

    Closed shape — exactly the keys ``T01.comparison(...)`` documents:
    ``receipt_id``, ``purpose``, ``operand_refs`` (in cell order),
    ``checked`` with ``basis``, ``currency``, ``scale``, ``duration``,
    ``perimeter``, ``definition``, ``source_mode`` booleans,
    ``unknowns`` (field names), and ``transformations`` whose entries
    each contain ``kind`` (str), ``factor`` (decimal text) and
    ``lineage`` (str).  This is the ONLY production constructor of a
    comparison receipt in the Industrials T04 module.

    An ABSENT ``checked`` argument is NOT a certification: a caller that
    says nothing about comparability has verified nothing, so every gate
    defaults False.  ``checked=None`` and ``checked={}`` are therefore the
    same receipt.
    """
    if purpose not in _ALLOWED_PURPOSES:
        raise ValueError(f"unknown comparison purpose: {purpose}")
    operand_list = list(cells)
    if not operand_list:
        raise ValueError("comparison requires operands")

    refs: list[str] = []
    for operand in operand_list:
        owner_ref = operand.get("owner_ref")
        if not isinstance(owner_ref, str) or not owner_ref:
            raise ValueError("comparison operand lacks owner_ref")
        refs.append(str(owner_ref))

    # Defaulting an omitted `checked` to all-True silently suppressed a REAL
    # refusal: a quarter compared against a year qualified `ready` with no
    # limitations, because `duration` read as verified when the caller had said
    # nothing.  Absent qualification information is not qualification.
    checked_in = checked or {}
    checked_dict = {name: bool(checked_in.get(name, False)) for name in _CHECKED_FIELDS}

    unknown_list = [str(name) for name in unknowns]
    transforms: list[dict[str, Any]] = []
    for entry in transformations:
        if not isinstance(entry, Mapping):
            raise ValueError("transformation must be a mapping")
        kind = entry.get("kind")
        factor = entry.get("factor")
        lineage = entry.get("lineage")
        if not isinstance(kind, str) or not kind:
            raise ValueError("transformation kind must be a non-empty string")
        if not isinstance(factor, str):
            raise ValueError("transformation factor must be decimal text")
        # Validate the factor parses as exact decimal.
        try:
            Decimal(factor)
        except InvalidOperation as exc:
            raise ValueError("transformation factor must be decimal text") from exc
        if not isinstance(lineage, str):
            raise ValueError("transformation lineage must be a string")
        transforms.append({"kind": kind, "factor": factor, "lineage": lineage})

    digest_input = (
        purpose + "|"
        + "|".join(refs) + "|"
        + "|".join(f"{k}:{int(v)}" for k, v in sorted(checked_dict.items())) + "|"
        + "|".join(sorted(unknown_list)) + "|"
        + "|".join(f"{t['kind']}:{t['factor']}:{t['lineage']}" for t in transforms)
    )
    receipt_id = "synthetic:comparison:" + _sha256_text(digest_input)[:16]

    return {
        "receipt_id": receipt_id,
        "purpose": purpose,
        "operand_refs": refs,
        "checked": checked_dict,
        "unknowns": unknown_list,
        "transformations": transforms,
    }


_CHECKED_FIELDS: tuple[str, ...] = (
    "basis",
    "currency",
    "scale",
    "duration",
    "perimeter",
    "definition",
    "source_mode",
)


def _sha256_text(text: str) -> str:
    """Stable, stdlib-only digest for receipt identity."""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Operand parsing and validation
# ---------------------------------------------------------------------------


def _parse_operand(index: int, raw: Mapping[str, Any]) -> _Operand | None:
    """Return a typed operand or a (None, limitation_string) pair."""
    if not isinstance(raw, Mapping):
        return None
    missing: list[str] = []
    string_fields = {
        "owner_ref": raw.get("owner_ref"),
        "revision": raw.get("revision"),
        "digest": raw.get("digest"),
        "metric": raw.get("metric"),
        "unit": raw.get("unit"),
        "currency": raw.get("currency"),
        "stock_or_flow": raw.get("stock_or_flow"),
        "source_mode": raw.get("source_mode"),
    }
    for name, value in string_fields.items():
        if not isinstance(value, str) or not value:
            missing.append(f"operand_field_missing:{name}")
    mapping_fields = {
        "semantic_selector": raw.get("semantic_selector"),
        "period": raw.get("period"),
        "business_dimensions": raw.get("business_dimensions"),
        "basis": raw.get("basis"),
        "quality": raw.get("quality"),
    }
    for name, value in mapping_fields.items():
        if not isinstance(value, Mapping):
            missing.append(f"operand_field_missing:{name}")
    if missing:
        raise _OperandParseError(missing)

    scale = raw.get("scale")
    if not isinstance(scale, int) or isinstance(scale, bool):
        raise _OperandParseError(["operand_field_missing:scale"])

    value_text = raw.get("value")
    absence_reason: str | None = None
    absence = raw.get("absence")
    if value_text is None:
        if not isinstance(absence, str) or not absence:
            raise _OperandParseError(["operand_value_missing"])
        absence_reason = str(absence)
        value_text_parsed: str | None = None
    else:
        if isinstance(value_text, bool) or not isinstance(value_text, str):
            raise _OperandParseError(["operand_malformed:value_not_text"])
        # Float values arrive here only if a caller serialized them as text;
        # we still reject bare numeric strings that look like Python floats
        # (1e2 is allowed, but anything containing '.' followed by anything
        # other than digits is fine — exact-decimal text preserves magnitude).
        if value_text.strip().lower() in _NON_FINITE_TOKENS:
            raise _OperandParseError(["operand_malformed:non_finite"])
        try:
            Decimal(value_text)
        except InvalidOperation as exc:
            raise _OperandParseError(["operand_malformed:not_decimal"]) from exc
        value_text_parsed = value_text

    return _Operand(
        owner_ref=str(string_fields["owner_ref"]),
        revision=str(string_fields["revision"]),
        digest=str(string_fields["digest"]),
        semantic_selector=mapping_fields["semantic_selector"],
        metric=str(string_fields["metric"]),
        unit=str(string_fields["unit"]),
        scale=scale,
        currency=str(string_fields["currency"]),
        stock_or_flow=str(string_fields["stock_or_flow"]),
        period=mapping_fields["period"],
        business_dimensions=mapping_fields["business_dimensions"],
        basis=mapping_fields["basis"],
        source_mode=str(string_fields["source_mode"]),
        quality=mapping_fields["quality"],
        value_text=value_text_parsed,
        absence_reason=absence_reason,
    )


class _OperandParseError(Exception):
    """Internal error: a single operand is structurally malformed."""

    def __init__(self, limitations: list[str]) -> None:
        super().__init__("; ".join(limitations))
        self.limitations = limitations


def _decimal_from_operand(op: _Operand) -> Decimal:
    """Convert an operand's decimal-text value to a Decimal — exact."""
    assert op.value_text is not None, "operand value must be present for arithmetic"
    return Decimal(op.value_text)


def _operand_has_value(op: _Operand) -> bool:
    return op.value_text is not None


def _operand_quality_basis(op: _Operand) -> Mapping[str, Any]:
    quality = op.quality or {}
    definition = quality.get("definition")
    return {
        "accounting_basis": (op.basis or {}).get("accounting"),
        "recast": (op.basis or {}).get("recast"),
        "definition": definition,
    }


# ---------------------------------------------------------------------------
# qualification
# ---------------------------------------------------------------------------


def qualify_operands(
    purpose: str,
    cells: Sequence[Mapping[str, Any]],
    *,
    comparison_receipt: Mapping[str, Any] | None,
    formula: str | None = None,
) -> dict[str, Any]:
    """Verify every operand carries the native fields and the receipt
    names them all.  Returns a typed qualification result.

    Refusals (never inferences):
      - ``required_basis_unknown`` when any required basis / currency /
        perimeter / definition is missing on either side
      - ``definition_unqualified:<field>`` when a definition field is missing
      - ``duration_mismatch`` when durations differ without a declared
        comparability basis in the receipt
      - ``scale_mismatch`` / ``currency_mismatch`` when scales / currencies
        differ without an exact conversion factor that carries its input lineage
      - ``perimeter_mismatch`` when the business perimeter differs without a
        declared basis
      - ``receipt_incomplete`` when the receipt does not name every operand
        it claims to have checked
      - ``duplicate_operand_ref`` for every formula EXCEPT ``final_vs_preview``,
        which legitimately compares same-owner / same-metric across distinct
        editions; the ``distinct_edition_required`` limitation lives in the
        formula dispatch.
    """
    if not isinstance(cells, list):
        # Allow tuple for backward compatibility but require sequence-like.
        if isinstance(cells, Sequence):
            cells_list = list(cells)
        else:
            raise TypeError("cells must be a list of mappings")
    else:
        cells_list = cells
    if not isinstance(comparison_receipt, Mapping):
        raise TypeError("comparison_receipt must be a mapping")

    parsed: list[_Operand] = []
    limitations: list[str] = []
    for index, raw in enumerate(cells_list):
        try:
            operand = _parse_operand(index, raw)
        except _OperandParseError as exc:
            return _refusal_qualification(exc.limitations, parsed_count=index)
        if operand is None:
            limitations.append("operand_not_mapping")
            continue
        parsed.append(operand)

    if len(parsed) < len(cells_list):
        limitations.append("operand_not_mapping")

    # Receipt completeness — every operand must be named in the receipt.
    receipt_refs = list(comparison_receipt.get("operand_refs") or [])
    parsed_refs = [op.owner_ref for op in parsed]
    if not all(ref in receipt_refs for ref in parsed_refs):
        limitations.append("receipt_incomplete")

    # Duplicate operand refs are a refusal for every formula EXCEPT
    # ``final_vs_preview``, which legitimately compares same-owner / same-metric
    # across distinct editions (distinct revision/digest).  For other
    # formulas, uniqueness is judged on ``(owner_ref, revision, digest,
    # metric)``: T01's ``cell()`` helper shares a default placeholder
    # owner_ref across cells, so two legitimately-distinct operands at the
    # same source location but measuring different facts (different
    # ``metric``) are NOT duplicates.
    if formula != "final_vs_preview":
        if (
            len({(op.owner_ref, op.revision, op.digest, op.metric) for op in parsed})
            != len(parsed)
        ):
            limitations.append("duplicate_operand_ref")

    # Formula-aware gate: a segment_change_bridge with zero segment legs is
    # not a bridge — corporate + eliminations alone certify no segments.  The
    # formula dispatch in ``_derive_segment_change_bridge`` enforces the
    # same refusal; gating here too so the qualification surface refuses a
    # bad bridge BEFORE the formula code is reached.
    if formula == "segment_change_bridge" and not any(
        (op.metric or "").startswith("segment_")
        and (op.metric or "").endswith("_change")
        for op in parsed
    ):
        limitations.append("operand_missing:segments")

    # Basis / definition qualification.
    checked = comparison_receipt.get("checked") or {}
    basis_checked = bool(checked.get("basis"))
    definition_checked = bool(checked.get("definition"))
    perimeter_checked = bool(checked.get("perimeter"))
    scale_checked = bool(checked.get("scale"))
    currency_checked = bool(checked.get("currency"))
    duration_checked = bool(checked.get("duration"))
    source_mode_checked = bool(checked.get("source_mode"))

    if parsed and not _all_basis_present(parsed):
        limitations.append("required_basis_unknown")
    if parsed and not _all_definition_present(parsed) and not definition_checked:
        limitations.append("required_basis_unknown")

    # Perimeter — only flag mismatch when perimeters differ AND receipt does
    # not declare a basis for that mismatch.
    if parsed and not _perimeters_compatible(parsed) and not perimeter_checked:
        limitations.append("perimeter_mismatch")

    # Duration — quarter vs half-year is refused for subtraction.
    if parsed and not _durations_compatible(parsed) and not duration_checked:
        limitations.append("duration_mismatch")

    # Scale — only flag when scales differ AND no exact conversion factor in
    # the receipt (any non-empty transformations list carries one).
    transforms = list(comparison_receipt.get("transformations") or [])
    if parsed and not _scales_compatible(parsed) and not (scale_checked and transforms):
        limitations.append("scale_mismatch")
    if parsed and not _currencies_compatible(parsed) and not (currency_checked and transforms):
        limitations.append("currency_mismatch")

    if limitations:
        return {
            "status": "refused",
            "purpose": purpose,
            "limitations": limitations,
            "receipt_ref": comparison_receipt.get("receipt_id"),
            "operand_refs": [_operand_ref_payload(op) for op in parsed],
        }

    return {
        "status": "ready",
        "purpose": purpose,
        "limitations": [],
        "receipt_ref": comparison_receipt.get("receipt_id"),
        "operand_refs": [_operand_ref_payload(op) for op in parsed],
        "checked": {
            "basis": basis_checked,
            "definition": definition_checked,
            "perimeter": perimeter_checked,
            "duration": duration_checked,
            "scale": scale_checked,
            "currency": currency_checked,
            "source_mode": source_mode_checked,
        },
    }


def _refusal_qualification(limitations: list[str], *, parsed_count: int) -> dict[str, Any]:
    return {
        "status": "refused",
        "purpose": None,
        "limitations": limitations,
        "receipt_ref": None,
        "operand_refs": [],
    }


def _operand_ref_payload(op: _Operand) -> dict[str, str]:
    return {"owner_ref": op.owner_ref, "revision": op.revision, "digest": op.digest}


def _all_basis_present(operands: Sequence[_Operand]) -> bool:
    for op in operands:
        basis = op.basis or {}
        if not basis.get("accounting"):
            return False
        if "recast" not in basis:
            return False
    return True


def _all_definition_present(operands: Sequence[_Operand]) -> bool:
    for op in operands:
        if not (op.quality or {}).get("definition"):
            return False
    return True


def _perimeters_compatible(operands: Sequence[_Operand]) -> bool:
    perimeters = {tuple(sorted((op.business_dimensions or {}).items())) for op in operands}
    return len(perimeters) <= 1


def _durations_compatible(operands: Sequence[_Operand]) -> bool:
    durations = {(op.period or {}).get("duration") for op in operands}
    durations.discard(None)
    return len(durations) <= 1


def _scales_compatible(operands: Sequence[_Operand]) -> bool:
    return len({op.scale for op in operands}) <= 1


def _currencies_compatible(operands: Sequence[_Operand]) -> bool:
    return len({op.currency for op in operands}) <= 1


# ---------------------------------------------------------------------------
# Arithmetic — Decimal from string; never float
# ---------------------------------------------------------------------------


def derive_result_cash(
    formula: str,
    cells: Sequence[Mapping[str, Any]],
    *,
    comparison_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Run one allowed formula over the supplied cells.

    Closed-dict return shape (the standard 11 keys plus formula-specific
    additions).  Sign, unit, scale, currency and period propagate from the
    first qualified operand.
    """
    if formula not in ALLOWED_FORMULAS:
        return _refusal_result(
            formula=formula,
            cells=[],
            receipt=comparison_receipt,
            limitations=["unknown_formula"],
            operand_refs=[],
        )

    if not isinstance(cells, list):
        if isinstance(cells, tuple):
            cells_list = list(cells)
        else:
            # Strings, scalars, sets, generators are all non-list shapes and
            # raise TypeError rather than fabricate a list.
            raise TypeError("cells must be a list of mappings")
    else:
        cells_list = cells
    if not isinstance(comparison_receipt, Mapping):
        raise TypeError("comparison_receipt must be a mapping")

    parsed: list[_Operand] = []
    parse_limitations: list[str] = []
    for index, raw in enumerate(cells_list):
        try:
            operand = _parse_operand(index, raw)
        except _OperandParseError as exc:
            parse_limitations.extend(exc.limitations)
            continue
        if operand is None:
            parse_limitations.append("operand_not_mapping")
            continue
        parsed.append(operand)

    operand_refs = [_operand_ref_payload(op) for op in parsed]

    if parse_limitations:
        return _refusal_result(
            formula=formula,
            cells=parsed,
            receipt=comparison_receipt,
            limitations=parse_limitations,
            operand_refs=operand_refs,
        )

    if not parsed:
        return _refusal_result(
            formula=formula,
            cells=[],
            receipt=comparison_receipt,
            limitations=["operand_missing"],
            operand_refs=[],
        )

    # Qualification gate — only when needed by the formula.
    qualifier = qualify_operands(
        _purpose_for(formula),
        [_as_mapping(op) for op in parsed],
        comparison_receipt=comparison_receipt,
        formula=formula,
    )
    if qualifier["status"] != "ready":
        return _refusal_result(
            formula=formula,
            cells=parsed,
            receipt=comparison_receipt,
            limitations=qualifier["limitations"],
            operand_refs=operand_refs,
        )

    # Formula dispatch.
    if formula == "cash_after_capital_payments":
        return _derive_cash_after_payments(parsed, comparison_receipt)
    if formula == "growth_pct":
        return _derive_growth_pct(parsed, comparison_receipt)
    if formula == "margin_pct":
        return _derive_margin_pct(parsed, comparison_receipt)
    if formula == "paired_remeasurement":
        return _derive_paired_remeasurement(parsed, comparison_receipt)
    if formula == "cash_rollforward":
        return _derive_cash_rollforward(parsed, comparison_receipt)
    if formula == "segment_change_bridge":
        return _derive_segment_change_bridge(parsed, comparison_receipt)
    if formula == "final_vs_preview":
        return _derive_final_vs_preview(parsed, comparison_receipt)
    return _refusal_result(  # pragma: no cover — ALLOWED_FORMULAS guards above
        formula=formula,
        cells=parsed,
        receipt=comparison_receipt,
        limitations=["unknown_formula"],
        operand_refs=operand_refs,
    )


def _purpose_for(formula: str) -> str:
    return {
        "cash_after_capital_payments": "same_period",
        "growth_pct": "year_over_year",
        "margin_pct": "same_period",
        "paired_remeasurement": "same_period",
        "cash_rollforward": "rollforward",
        "segment_change_bridge": "segment_bridge",
        "final_vs_preview": "final_vs_preview",
    }[formula]


def _as_mapping(op: _Operand) -> dict[str, Any]:
    return {
        "owner_ref": op.owner_ref,
        "revision": op.revision,
        "digest": op.digest,
        "semantic_selector": dict(op.semantic_selector),
        "metric": op.metric,
        "unit": op.unit,
        "scale": op.scale,
        "currency": op.currency,
        "stock_or_flow": op.stock_or_flow,
        "period": dict(op.period),
        "business_dimensions": dict(op.business_dimensions),
        "basis": dict(op.basis),
        "source_mode": op.source_mode,
        "quality": dict(op.quality),
        "value": op.value_text,
        "absence": op.absence_reason,
    }


def _refusal_result(
    *,
    formula: str,
    cells: Sequence[_Operand],
    receipt: Mapping[str, Any] | None,
    limitations: list[str],
    operand_refs: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    base = {
        "status": "refused",
        "formula": formula,
        "formula_version": FORMULA_VERSION,
        "value": None,
        "unit": cells[0].unit if cells else None,
        "scale": cells[0].scale if cells else None,
        "currency": cells[0].currency if cells else None,
        "operand_refs": list(operand_refs),
        "limitations": sorted(set(limitations)),
        "receipt_ref": receipt.get("receipt_id") if isinstance(receipt, Mapping) else None,
        "label": "reported",
    }
    return base


def _ready_result(
    *,
    formula: str,
    cells: Sequence[_Operand],
    receipt: Mapping[str, Any],
    label: str,
    value: str,
    limitations: list[str] | None = None,
    extras: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "status": "ready" if not limitations else "limited",
        "formula": formula,
        "formula_version": FORMULA_VERSION,
        "value": value,
        "unit": cells[0].unit,
        "scale": cells[0].scale,
        "currency": cells[0].currency,
        "operand_refs": [_operand_ref_payload(op) for op in cells],
        "limitations": sorted(set(limitations or [])),
        "receipt_ref": receipt.get("receipt_id"),
        "label": label,
    }
    if extras:
        for key, value_ in extras.items():
            base[key] = value_
    return base


# ---------------------------------------------------------------------------
# Per-formula implementations
# ---------------------------------------------------------------------------


def _derive_cash_after_payments(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    operating = _pick_by_metric(cells, "operating_cash")
    payments = _pick_by_metric(cells, "cash_capital_payments")
    if operating is None or payments is None:
        missing = []
        if operating is None:
            missing.append("operand_missing:operating_cash")
        if payments is None:
            missing.append("operand_missing:cash_capital_payments")
        return _refusal_result(
            formula="cash_after_capital_payments",
            cells=cells,
            receipt=receipt,
            limitations=missing,
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    # Typed absence is never treated as 0.
    if not _operand_has_value(operating) or not _operand_has_value(payments):
        return _refusal_result(
            formula="cash_after_capital_payments",
            cells=cells,
            receipt=receipt,
            limitations=["operand_typed_absence"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    result_decimal = _decimal_from_operand(operating) - _decimal_from_operand(payments)
    label = _label_for_cash_after_payments(receipt)
    return _ready_result(
        formula="cash_after_capital_payments",
        cells=cells,
        receipt=receipt,
        label=label,
        value=_decimal_text(result_decimal),
    )


def _label_for_cash_after_payments(receipt: Mapping[str, Any]) -> str:
    transforms = receipt.get("transformations") or []
    for entry in transforms:
        if isinstance(entry, Mapping) and entry.get("kind") == "issuer_fcf_definition":
            return "company_adjusted"
    return "researcher_proxy"


def _derive_growth_pct(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    current = _pick_first_value(cells)
    prior = _pick_second_value(cells)
    if current is None or prior is None:
        return _refusal_result(
            formula="growth_pct",
            cells=cells,
            receipt=receipt,
            limitations=["operand_missing"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    current_dec = _decimal_from_operand(current)
    prior_dec = _decimal_from_operand(prior)
    abs_change = current_dec - prior_dec
    if prior_dec <= 0:
        return _limited_result(
            formula="growth_pct",
            cells=cells,
            receipt=receipt,
            label="reported",
            value=None,
            limitations=["percentage_refused_nonpositive_base"],
            extras={"absolute_change": _decimal_text(abs_change)},
        )
    growth = Decimal("100") * abs_change / prior_dec
    return _ready_result(
        formula="growth_pct",
        cells=cells,
        receipt=receipt,
        label="reported",
        value=_decimal_text(growth),
    )


def _derive_margin_pct(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    numerator = _pick_first_value(cells)
    denominator = _pick_second_value(cells)
    if numerator is None or denominator is None:
        return _refusal_result(
            formula="margin_pct",
            cells=cells,
            receipt=receipt,
            limitations=["operand_missing"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    num_dec = _decimal_from_operand(numerator)
    den_dec = _decimal_from_operand(denominator)
    if den_dec <= 0:
        return _refusal_result(
            formula="margin_pct",
            cells=cells,
            receipt=receipt,
            limitations=["percentage_refused_nonpositive_base"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    # Perimeter: numerator and denominator must share the same business
    # dimensions unless the receipt declares a basis for the perimeter
    # mismatch.  This is also enforced by qualify_operands; the formula
    # never silently re-derives magnitude from scale.
    margin = Decimal("100") * num_dec / den_dec
    return _ready_result(
        formula="margin_pct",
        cells=cells,
        receipt=receipt,
        label="reported",
        value=_decimal_text(margin),
    )


def _derive_paired_remeasurement(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    operating = _pick_by_metric(cells, "operating_profit")
    expense = _pick_by_metric(cells, "matched_expense")
    other_income = _pick_by_metric(cells, "other_income")
    matched_gain = _pick_by_metric(cells, "matched_gain")
    missing: list[str] = []
    if operating is None or not _operand_has_value(operating):
        missing.append("operand_missing:operating_profit")
    if expense is None or not _operand_has_value(expense):
        missing.append("operand_missing:matched_expense")
    if other_income is None or not _operand_has_value(other_income):
        missing.append("operand_missing:other_income")
    if matched_gain is None or not _operand_has_value(matched_gain):
        missing.append("operand_missing:matched_gain")
    if missing:
        return _refusal_result(
            formula="paired_remeasurement",
            cells=cells,
            receipt=receipt,
            limitations=missing,
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    op_with_expense = _decimal_from_operand(operating) + _decimal_from_operand(expense)
    other_net = _decimal_from_operand(other_income) - _decimal_from_operand(matched_gain)
    pretax_after = op_with_expense - other_net
    return _ready_result(
        formula="paired_remeasurement",
        cells=cells,
        receipt=receipt,
        label="company_adjusted",
        value=_decimal_text(pretax_after),
        extras={
            "legs": {
                "operating_with_expense": _decimal_text(op_with_expense),
                "other_income_net": _decimal_text(other_net),
            },
            "pretax_after_pairing": _decimal_text(pretax_after),
        },
    )


def _derive_cash_rollforward(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    opening = _pick_by_metric(cells, "opening_cash")
    operating = _pick_by_metric(cells, "operating_movement")
    investing = _pick_by_metric(cells, "investing_movement")
    financing = _pick_by_metric(cells, "financing_movement")
    exchange = _pick_by_metric(cells, "exchange_movement")
    closing = _pick_by_metric(cells, "closing_cash")
    missing: list[str] = []
    for name, op in (
        ("opening_cash", opening),
        ("operating_movement", operating),
        ("investing_movement", investing),
        ("financing_movement", financing),
        ("exchange_movement", exchange),
    ):
        if op is None or not _operand_has_value(op):
            missing.append(f"operand_missing:{name}")
    if missing:
        return _refusal_result(
            formula="cash_rollforward",
            cells=cells,
            receipt=receipt,
            limitations=missing,
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    total = (
        _decimal_from_operand(opening)
        + _decimal_from_operand(operating)
        + _decimal_from_operand(investing)
        + _decimal_from_operand(financing)
        + _decimal_from_operand(exchange)
    )
    extras: dict[str, Any] = {"computed_total": _decimal_text(total)}
    if closing is not None and _operand_has_value(closing):
        closing_dec = _decimal_from_operand(closing)
        residual = closing_dec - total
        extras["residual"] = _decimal_text(residual)
        if residual != 0:
            return _limited_result(
                formula="cash_rollforward",
                cells=cells,
                receipt=receipt,
                label="reported",
                value=_decimal_text(total),
                limitations=["rollforward_residual"],
                extras=extras,
            )
        extras["value"] = _decimal_text(total)
    else:
        # No closing supplied — disclose the residual limitation.
        return _limited_result(
            formula="cash_rollforward",
            cells=cells,
            receipt=receipt,
            label="reported",
            value=_decimal_text(total),
            limitations=["rollforward_residual"],
            extras=extras,
        )
    return _ready_result(
        formula="cash_rollforward",
        cells=cells,
        receipt=receipt,
        label="reported",
        value=_decimal_text(total),
        extras=extras,
    )


def _derive_segment_change_bridge(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    segments = [op for op in cells if (op.metric or "").startswith("segment_") and (op.metric or "").endswith("_change")]
    # A bridge with no segment legs is not a bridge — corporate + eliminations
    # alone would certify no segments and silently fabricate the segment
    # subtotal as zero.  Refuse explicitly so the caller distinguishes
    # "no segment_change legs supplied" from a clean bridge.
    if not segments:
        return _refusal_result(
            formula="segment_change_bridge",
            cells=cells,
            receipt=receipt,
            limitations=["operand_missing:segments"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    corporate = _pick_by_metric(cells, "corporate_change")
    eliminations = _pick_by_metric(cells, "eliminations")
    unallocated = [op for op in cells if op.metric in {"unallocated_change", "unallocated_refund"}]
    total = Decimal("0")
    for op in segments:
        if not _operand_has_value(op):
            return _refusal_result(
                formula="segment_change_bridge",
                cells=cells,
                receipt=receipt,
                limitations=[f"operand_missing:{op.metric}"],
                operand_refs=[_operand_ref_payload(o) for o in cells],
            )
        total += _decimal_from_operand(op)
    if corporate is None or eliminations is None:
        return _refusal_result(
            formula="segment_change_bridge",
            cells=cells,
            receipt=receipt,
            limitations=["operand_missing:corporate_or_eliminations"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    if not _operand_has_value(corporate) or not _operand_has_value(eliminations):
        return _refusal_result(
            formula="segment_change_bridge",
            cells=cells,
            receipt=receipt,
            limitations=["operand_typed_absence"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    total += _decimal_from_operand(corporate)
    total += _decimal_from_operand(eliminations)
    residual = Decimal("0")
    for op in unallocated:
        # A typed-absent unallocated leg must surface — the caller must be
        # able to distinguish "the issuer disclosed no unallocated amount"
        # from "the issuer disclosed one we could not read".  Silently
        # treating typed absence as zero would contradict the typed-absence
        # invariant this suite asserts for sibling formulas
        # (test_cash_after_capital_payments_refuses_typed_absence_operand).
        if not _operand_has_value(op):
            return _refusal_result(
                formula="segment_change_bridge",
                cells=cells,
                receipt=receipt,
                limitations=[f"operand_missing:{op.metric}"],
                operand_refs=[_operand_ref_payload(o) for o in cells],
            )
        residual += _decimal_from_operand(op)
    extras: dict[str, Any] = {"residual": _decimal_text(residual)}
    # The unallocated total is the residual — disclosed, NOT silently
    # allocated to a segment.  Disclosure keeps status=ready: the bridge
    # computed cleanly, the limitation names what could not be allocated.
    if residual != 0:
        base = _ready_result(
            formula="segment_change_bridge",
            cells=cells,
            receipt=receipt,
            label="reported",
            value=_decimal_text(total + residual),
            limitations=["bridge_residual_disclosed"],
            extras=extras,
        )
        base["status"] = "ready"
        return base
    return _ready_result(
        formula="segment_change_bridge",
        cells=cells,
        receipt=receipt,
        label="reported",
        value=_decimal_text(total),
        extras=extras,
    )


def _derive_final_vs_preview(
    cells: Sequence[_Operand], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    if len(cells) < 2:
        return _refusal_result(
            formula="final_vs_preview",
            cells=cells,
            receipt=receipt,
            limitations=["operand_missing"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    current, prior = cells[0], cells[1]
    if not _operand_has_value(current) or not _operand_has_value(prior):
        return _refusal_result(
            formula="final_vs_preview",
            cells=cells,
            receipt=receipt,
            limitations=["operand_typed_absence"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    if (current.revision, current.digest) == (prior.revision, prior.digest):
        return _refusal_result(
            formula="final_vs_preview",
            cells=cells,
            receipt=receipt,
            limitations=["distinct_edition_required"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    if current.metric != prior.metric:
        return _refusal_result(
            formula="final_vs_preview",
            cells=cells,
            receipt=receipt,
            limitations=["metric_mismatch"],
            operand_refs=[_operand_ref_payload(op) for op in cells],
        )
    delta = _decimal_from_operand(current) - _decimal_from_operand(prior)
    return _ready_result(
        formula="final_vs_preview",
        cells=cells,
        receipt=receipt,
        label="reported",
        value=_decimal_text(delta),
        extras={
            "delta": _decimal_text(delta),
            "editions": {
                "current": {"owner_ref": current.owner_ref, "revision": current.revision, "digest": current.digest},
                "prior": {"owner_ref": prior.owner_ref, "revision": prior.revision, "digest": prior.digest},
            },
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pick_by_metric(operands: Sequence[_Operand], metric: str) -> _Operand | None:
    for op in operands:
        if op.metric == metric:
            return op
    return None


def _pick_first_value(operands: Sequence[_Operand]) -> _Operand | None:
    for op in operands:
        if _operand_has_value(op):
            return op
    return None


def _pick_second_value(operands: Sequence[_Operand]) -> _Operand | None:
    found = 0
    for op in operands:
        if _operand_has_value(op):
            found += 1
            if found == 2:
                return op
    return None


def _limited_result(
    *,
    formula: str,
    cells: Sequence[_Operand],
    receipt: Mapping[str, Any],
    label: str,
    value: str | None,
    limitations: list[str],
    extras: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "status": "limited",
        "formula": formula,
        "formula_version": FORMULA_VERSION,
        "value": value,
        "unit": cells[0].unit,
        "scale": cells[0].scale,
        "currency": cells[0].currency,
        "operand_refs": [_operand_ref_payload(op) for op in cells],
        "limitations": sorted(set(limitations)),
        "receipt_ref": receipt.get("receipt_id"),
        "label": label,
    }
    if extras:
        for key, value_ in extras.items():
            base[key] = value_
    return base


__all__ = (
    "FORMULA_VERSION",
    "ALLOWED_FORMULAS",
    "qualify_operands",
    "derive_result_cash",
    "build_comparison_receipt",
)