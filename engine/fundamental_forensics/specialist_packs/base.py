"""Specialist pack producer framework (shared by every ``PKnn`` producer).

The catalogues under ``contracts/specialist_packs/`` are frozen; this module is
the single producer-side engine: it builds the raw ledger once per input
(``ixbrl_raw_ledger.parse_and_convert_golden_packages`` — never parses XML
itself), evaluates applicability (R-K1), resolves each catalogue field against
admitted undimensioned facts or formulas, evaluates the declared checks, and
mints the ``specialist_pack_result.v1`` envelope. A producer module only
declares a ``PackSpec``, per-field mappings and check identities; a producer
never returns an envelope the contract validator refuses.

Laws: decimal arithmetic only (never float); deterministic output (same input,
byte-identical canonical JSON); no wall clock; no ticker/CIK/accession/issuer
literals here.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from .. import detectors
from .. import specialist_pack_contract as contract
from ..raw_ledger import RawFactLedger, canonical_json, decimal_text

SCHEMA = "specialist_pack_result.v1"
DISPLAY_ONLY_LIMITATION = (
    "display_only: no Q1 held-out evaluation under Q0 has been run for this pack"
)
# Annual window: the duration admitted for a ``duration`` field may not exceed
# this many inclusive days, so a fiscal-year fact never competes with a
# multi-year cumulative fact at the same context end.  380 admits a 53-week
# fiscal year (a 371-day context, the 2023 annual shape) while still refusing
# a multi-year cumulative context.
MAX_DURATION_DAYS = 380
# R-F1: catalogue unit -> ledger unit spellings that satisfy the field.  A
# catalogue unit with no entry here maps to itself only.  Durations and
# percentages are dimensionless numerics in iXBRL, so the ``pure`` spellings
# satisfy ``years``/``quarters``/``months``/``percent``; a ``pure`` value is
# never rescaled into a ``percent``/``ratio`` field (it passes through tagged).
UNIT_EQUIVALENTS: Mapping[str, frozenset[str]] = {
    "USD": frozenset({"USD", "iso4217:USD"}),
    "shares": frozenset({"shares", "xbrli:shares"}),
    "ratio": frozenset({"ratio", "pure", "xbrli:pure"}),
    "USD_per_share": frozenset(
        {"USD/shares", "iso4217:USD/xbrli:shares", "USDPerShare"}
    ),
    # The pk02 catalogue spells the per-share unit ``USD/shares``; the
    # ``USD_per_share`` key above keeps the ruling's alias spelling.
    "USD/shares": frozenset(
        {"USD/shares", "iso4217:USD/xbrli:shares", "USDPerShare"}
    ),
    "years": frozenset({"years", "xbrli:pure", "pure"}),
    "quarters": frozenset({"quarters", "xbrli:pure", "pure"}),
    "months": frozenset({"months", "xbrli:pure", "pure"}),
    "percent": frozenset({"percent", "pure", "xbrli:pure"}),
}
# R-F10: primary-package ranking prefers the annual family over a newer
# interim filing inside ``spec.forms``; forms outside the tuple rank last.
_FORM_FAMILY_RANK = (
    "10-K",
    "10-K/A",
    "20-F",
    "20-F/A",
    "40-F",
    "40-F/A",
    "10-Q",
    "10-Q/A",
    "10-QT",
)
_FIELD_ROW_KEYS = (
    "field_id",
    "name",
    "type",
    "unit",
    "period",
    "value",
    "text_value",
    "non_value_state",
    "evidence_kind",
    "required_evidence_kind",
    "source_occurrence_ids",
    "source_span",
    "table_cell",
    "concept",
    "taxonomy",
    "dimensions",
    "mapping_rule_id",
    "mapping_rule_digest",
    "formula_rule_id",
    "dependency_field_ids",
    "quality_state",
    "coverage_state",
    "reason",
)
_CROSS_OPERAND_SEPARATOR = ":"
_FOREIGN_OPERAND_PREFIX = "pk"
_CROSS_RELATIONS = frozenset({"equal", "left_lte_right", "disjoint"})
_KIND_BY_SPEC = {
    "SumIdentity": "sum_identity",
    "Rollforward": "rollforward",
    "Reconcile": "reconcile_to_consolidated",
    "CrossStatement": "cross_statement",
    "Presence": "qualitative_presence",
}


class SpecialistPackError(ValueError):
    """A pack result cannot be produced lawfully from the given input."""


def _project_reason(
    code: str,
    catalogue: Mapping[str, Any] | None,
    context: str,
    limitations: list[str] | None,
) -> str:
    """R-F6: emit ``code`` when the pack catalogue declares it.

    An undeclared code (the bare part before ``:``) is emitted as
    ``missing_dependency`` — declared by every catalogue — with the limitation
    ``<context>: <code> undeclared by pack catalogue``.  ``catalogue=None``
    (pure function use, no envelope) passes the code through unchanged.
    """
    if catalogue is None:
        return code
    declared = {
        str(item.get("code"))
        for item in catalogue.get("reason_codes") or ()
        if isinstance(item, Mapping)
    }
    if code.partition(":")[0] in declared:
        return code
    if limitations is not None:
        limitations.append(f"{context}: {code} undeclared by pack catalogue")
    return "missing_dependency"


def _unit_equivalents(catalogue_unit: str | None) -> frozenset[str] | None:
    """Ledger unit spellings admitted for a catalogue unit (R-F1); ``None``
    when the catalogue field declares no unit (no check is imposed)."""
    if catalogue_unit is None:
        return None
    return UNIT_EQUIVALENTS.get(catalogue_unit, frozenset({catalogue_unit}))


def _cik10(value: Any) -> str:
    """10-digit zero-padded CIK spelling for the R-F4 issuer gate."""
    return str(value).strip().zfill(10)


def _form_rank(form: str) -> int:
    """Position of ``form`` in the canonical form-family order (R-F10)."""
    if form in _FORM_FAMILY_RANK:
        return _FORM_FAMILY_RANK.index(form)
    return len(_FORM_FAMILY_RANK)


# --------------------------------------------------------------------------
# Producer declarations
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PackSpec:
    """R-K1 applicability declaration for one pack."""

    pack_id: str
    forms: frozenset[str]
    applicability_rule_id: str
    # ``None`` means every issuer class is in scope.
    applicable_classes: frozenset[str] | None = None
    # Catalogue reason code cited when the issuer class is outside the set.
    inapplicable_class_reason: str = "issuer_class_outside_pack_classes"
    # A.1 field-level issuer-class exclusions: field_id -> (issuer classes
    # excluded, catalogue reason code). The framework compares
    # ``detectors.issuer_class_for_sic`` output against the producer's
    # frozenset; it never tests a word from configuration.
    field_class_exclusions: Mapping[str, tuple[frozenset[str], str]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class FactMapping:
    """Map a field onto the first standard concept that resolves."""

    concepts: tuple[str, ...]
    dimensions_allowed: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormulaMapping:
    """Map a field onto a decimal formula over other fields of this pack."""

    rule_id: str
    inputs: tuple[str, ...]
    fn: Callable[[Mapping[str, Decimal]], Decimal]


# A.6 formula helpers. A ratio quantizes to 6 decimal places with
# ROUND_HALF_EVEN; a decimal sum/difference keeps the exact Decimal. A zero
# denominator raises ``ZeroDivisionError`` so the framework emits the
# ``division_by_zero`` typed absence.
_RATIO_QUANTUM = Decimal("0.000001")


def formula_sum(values: Mapping[str, Decimal]) -> Decimal:
    """Exact decimal sum of every formula input, in declaration order."""
    return sum(values.values(), Decimal("0"))


def formula_difference(
    minuend: str, subtrahend: str
) -> Callable[[Mapping[str, Decimal]], Decimal]:
    """Build an exact decimal ``minuend - subtrahend`` formula function."""

    def difference(values: Mapping[str, Decimal]) -> Decimal:
        return values[minuend] - values[subtrahend]

    return difference


def formula_ratio(
    numerator: str, denominator: str
) -> Callable[[Mapping[str, Decimal]], Decimal]:
    """Build a ratio formula quantized to 6 dp under ROUND_HALF_EVEN."""

    def ratio(values: Mapping[str, Decimal]) -> Decimal:
        divisor = values[denominator]
        if divisor == 0:
            raise ZeroDivisionError("ratio denominator is zero")
        return (values[numerator] / divisor).quantize(
            _RATIO_QUANTUM, rounding=ROUND_HALF_EVEN
        )

    return ratio


@dataclass(frozen=True)
class DimensionedFactMapping:
    """A.2: emit one row per admitted explicit-dimension tuple of a concept.

    Admitted facts carry the primary axis and no axis outside
    ``{primary_axis} ∪ other_axes_allowed``. Dimension tuples whose member
    local names contain an excluded substring (case-insensitive) are skipped.
    """

    concept: str
    primary_axis: str
    other_axes_allowed: tuple[str, ...] = ()
    exclude_member_substrings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FactOrFormulaMapping:
    """A.3: the fact wins when it resolves to a valued row, else the formula.

    The row's ``required_evidence_kind`` is ``xbrl_fact``;
    ``evidence_kind`` reports which branch produced it.
    """

    fact: FactMapping
    formula: FormulaMapping
    # Limitation appended when the formula branch produced the row (e.g. a
    # sum identity over the same addends becomes tautological).
    limitation_when_formula: str | None = None


@dataclass(frozen=True)
class TableMapping:
    """Reserved for a later lane: table-cell evidence is never produced here."""


@dataclass(frozen=True)
class TextSpanMapping:
    """Reserved for a later lane: span evidence is never produced here."""


FieldMapping = (
    FactMapping
    | FormulaMapping
    | DimensionedFactMapping
    | FactOrFormulaMapping
    | TableMapping
    | TextSpanMapping
)


@dataclass(frozen=True)
class SumIdentity:
    check_id: str
    addends: tuple[str, ...]
    total: str

    def __post_init__(self) -> None:
        # R-F8: an identity over no operands can never be evaluated.
        if not self.addends or not self.total:
            raise SpecialistPackError(
                f"sum identity {self.check_id} lacks addends or a total field"
            )


@dataclass(frozen=True)
class Rollforward:
    check_id: str
    opening: str
    additions: tuple[str, ...] = ()
    reductions: tuple[str, ...] = ()
    closing: str = ""


@dataclass(frozen=True)
class Reconcile:
    check_id: str
    parts: tuple[str, ...]
    consolidated: str

    def __post_init__(self) -> None:
        if not self.parts or not self.consolidated:  # R-F8
            raise SpecialistPackError(
                f"reconcile {self.check_id} lacks parts or a consolidated field"
            )


@dataclass(frozen=True)
class CrossStatement:
    check_id: str
    left: str
    right: str
    relation: str

    def __post_init__(self) -> None:
        if not self.left or not self.right:  # R-F8
            raise SpecialistPackError(
                f"cross statement {self.check_id} lacks an operand field"
            )


@dataclass(frozen=True)
class Presence:
    check_id: str
    field_id: str


CheckSpec = SumIdentity | Rollforward | Reconcile | CrossStatement | Presence

ExtraApplicabilityFn = Callable[
    [Any, RawFactLedger | None], tuple[str, str] | None
]


@dataclass(frozen=True)
class PackInput:
    """One production context: admitted packages, packet identity and query.

    ``packages`` accepts ``GoldenFilingPackage`` and the duck-compatible
    ``AdmittedFilingPackage``; both expose ``manifest`` and ``members``.
    ``packs_in_progress`` (R-F5) is the ordered chain of pack ids currently
    being produced on this resolution path; the framework threads it through
    ``produce_pack`` calls so a cross-pack cycle is cut, never recursed.
    """

    packages: tuple[Any, ...]
    entity: Mapping[str, str]
    query: Mapping[str, Any]
    issuer_sic: str | None = None
    sic_source: str | None = None
    packet_id: str | None = None
    packs_in_progress: tuple[str, ...] = ()


@dataclass(frozen=True)
class PackProducer:
    """Everything a producer module declares; the framework does the rest."""

    spec: PackSpec
    field_mappings: Mapping[str, FieldMapping]
    checks: tuple[CheckSpec, ...] = ()
    limitations: tuple[str, ...] = ()
    # Optional extra R-K1 rule evaluated after the framework's own rules.
    extra_applicability: ExtraApplicabilityFn | None = None
    # Extension prefixes this producer acknowledges, prefix -> namespace URI.
    # An unaliased extension fact is only nameable when its namespace is here;
    # the map carries issuer knowledge as data, never code literals.
    extension_prefixes: Mapping[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Applicability (R-K1)
# --------------------------------------------------------------------------


def evaluate_applicability(
    producer: PackProducer,
    pack_input: PackInput,
    primary_form: str | None,
    ledger: RawFactLedger | None = None,
    *,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> tuple[str, str]:
    """Return ``(state, reason)`` under the frozen R-K1 order.

    With a ``catalogue`` the reason is projected (R-F6): an undeclared code is
    emitted as ``missing_dependency`` with a limitation naming it.
    """

    def project(code: str) -> str:
        return _project_reason(code, catalogue, "applicability", limitations)

    spec = producer.spec
    if primary_form is None or primary_form not in spec.forms:
        return "not_applicable", project("form_outside_pack_forms")
    if spec.applicable_classes is not None:
        issuer_class = detectors.issuer_class_for_sic(pack_input.issuer_sic)
        if issuer_class == "unknown":
            return "not_evaluable", project("issuer_class_unknown")
        if issuer_class not in spec.applicable_classes:
            return "not_applicable", project(spec.inapplicable_class_reason)
    if producer.extra_applicability is not None:  # producer-declared extra rule
        outcome = producer.extra_applicability(pack_input, ledger)
        if outcome is not None:
            return outcome[0], project(outcome[1])
    return "applicable", project("applicability_rule_satisfied")


def _select_primary(
    packages: Sequence[Any], forms: frozenset[str]
) -> tuple[Any, bool]:
    """Primary package: form-family rank, then latest period, then accession.

    R-F10: inside ``forms`` the annual family outranks a newer interim filing;
    when no package matches ``forms``, the latest-period package is primary
    exactly as before.
    """
    if not packages:
        raise SpecialistPackError("pack input carries no filing packages")
    matched = [
        item for item in packages if str(item.manifest.get("form") or "") in forms
    ]

    def period_order(item: Any) -> tuple[str, str]:
        manifest = item.manifest
        return (
            str(manifest.get("period_of_report") or ""),
            str(manifest.get("accession") or ""),
        )

    if matched:

        def ranked(item: Any) -> tuple[int, str, str]:
            manifest = item.manifest
            # Lower family rank is better, so negate it for ``max``; ties
            # fall through to latest period, then descending accession.
            return (
                -_form_rank(str(manifest.get("form") or "")),
                *period_order(item),
            )

        return max(matched, key=ranked), True
    return max(packages, key=period_order), False


# --------------------------------------------------------------------------
# Fact resolution (R-K2', R-K3, R-K4')
# --------------------------------------------------------------------------


def _period_matches(occurrence: Any, period_kind: str, por: date) -> bool:
    context = occurrence.context
    if period_kind == "instant":
        return context.instant is not None and context.instant == por
    if context.end is None or context.start is None or context.end != por:
        return False
    days = (context.end - context.start).days + 1
    return 0 < days <= MAX_DURATION_DAYS


def _duration_days(occurrence: Any) -> int:
    context = occurrence.context
    return (context.end - context.start).days + 1


def _dimensions_admitted(occurrence: Any, allowed: tuple[str, ...]) -> bool:
    # R-F3: a source plane that did not expose dimensional context never
    # proves an occurrence consolidated, so it is never in the undimensioned
    # pool.
    if occurrence.dimensions_known is False:
        return False
    context = occurrence.context
    axes = set(context.explicit_dimensions) | set(context.typed_dimensions)
    return axes <= set(allowed)


def _unit_measure(unit: Any) -> str | None:
    if unit is None:
        return None
    parts = [str(measure).rsplit(":", 1)[-1] for measure in unit.measures]
    denominator = [
        str(measure).rsplit(":", 1)[-1]
        for measure in unit.denominator_measures
    ]
    return "/".join(parts + denominator) or None


def _local_name(qname: str) -> str:
    if qname.startswith("{") and "}" in qname:
        return qname.rsplit("}", 1)[-1]
    return qname.rsplit(":", 1)[-1] if ":" in qname else qname


def _namespace_uri(qname: str) -> str | None:
    if qname.startswith("{") and "}" in qname:
        return qname[1:].split("}", 1)[0]
    return None


def _extension_prefix(
    namespace: str | None, extension_prefixes: Mapping[str, str]
) -> str | None:
    if namespace is None:
        return None
    for prefix in sorted(extension_prefixes):
        if extension_prefixes[prefix] == namespace:
            return prefix
    return None


def _mapping_digest(mapping: FactMapping) -> str:
    payload = canonical_json(
        [list(mapping.concepts), list(mapping.dimensions_allowed)]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _FieldOutcome:
    """One field's production: its first row, value and any repeated rows.

    ``value`` is the field total a check consumes — for a dimensioned field
    the sum of every valued member row (A.5). ``extra_rows`` carries the
    member rows after the first; they keep catalogue order and adjacency.
    """

    row: dict[str, Any]
    value: Decimal | None
    decimals: int | None
    unit: str | None
    extra_rows: tuple[dict[str, Any], ...] = ()


def _base_row(catalogue_field: Mapping[str, Any], por: date) -> dict[str, Any]:
    period_kind = catalogue_field["period_kind"]
    if period_kind == "instant":
        period: dict[str, Any] = {"kind": "instant", "end": por.isoformat()}
    else:
        period = {"kind": "duration", "start": None, "end": por.isoformat()}
    row = {key: None for key in _FIELD_ROW_KEYS}
    row.update(
        {
            "field_id": catalogue_field["field_id"],
            "name": catalogue_field["name"],
            "type": catalogue_field["type"],
            "unit": catalogue_field.get("unit"),
            "period": period,
            "evidence_kind": "xbrl_fact",
            "required_evidence_kind": "xbrl_fact",
            "source_occurrence_ids": [],
            "source_span": None,
            "table_cell": None,
            "dimensions": [],
            "dependency_field_ids": [],
        }
    )
    return row


def _absence_row(
    catalogue_field: Mapping[str, Any],
    por: date,
    quality_state: str,
    reason: str,
    *,
    concept: str | None = None,
    occurrence_ids: Sequence[str] = (),
    mapping: FactMapping | None = None,
    pack_id: str | None = None,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    row = _base_row(catalogue_field, por)
    row["quality_state"] = quality_state
    row["non_value_state"] = quality_state
    row["coverage_state"] = (
        "not_applicable_period"
        if quality_state == "not_applicable"
        else "unmapped"
    )
    row["reason"] = _project_reason(
        reason, catalogue, catalogue_field["field_id"], limitations
    )
    row["concept"] = concept
    row["source_occurrence_ids"] = sorted(set(occurrence_ids))
    if mapping is not None and pack_id is not None:
        row["mapping_rule_id"] = f"{pack_id}.{catalogue_field['field_id']}.fact/v1"
        row["mapping_rule_digest"] = _mapping_digest(mapping)
    return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])


def _resolve_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: FactMapping,
    ledger: RawFactLedger,
    por: date,
    extension_prefixes: Mapping[str, str],
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    period_kind = catalogue_field["period_kind"]
    field_id = catalogue_field["field_id"]
    by_concept: dict[str, list[Any]] = {}
    for occurrence in ledger.events:
        by_concept.setdefault(occurrence.concept_qname, []).append(occurrence)

    admitted: list[Any] = []
    dimensioned_seen = False
    unknown_dimensions_seen: list[Any] = []
    for concept in mapping.concepts:
        candidates = [
            occurrence
            for occurrence in by_concept.get(concept, ())
            if not occurrence.is_nil
            and _period_matches(occurrence, period_kind, por)
        ]
        for occurrence in candidates:
            if occurrence.dimensions_known is False:
                # R-F3: the source plane did not expose dimensional context,
                # so the occurrence is never admitted as consolidated.
                unknown_dimensions_seen.append(occurrence)
            elif _dimensions_admitted(occurrence, mapping.dimensions_allowed):
                admitted.append(occurrence)
            else:
                dimensioned_seen = True
        if admitted:
            if period_kind != "instant":
                # Longest duration at this context end is the fiscal year.
                longest = max(_duration_days(item) for item in admitted)
                admitted = [
                    item for item in admitted if _duration_days(item) == longest
                ]
            break  # first concept in order that resolves wins

    if admitted:
        distinct = {str(item.parsed_value) for item in admitted}
        if len(distinct) > 1:
            # A.6 conflicting facts: same concept/period, different values.
            units = {_unit_measure(item.unit) for item in admitted}
            reason = "unit_mismatch" if len(units) > 1 else "missing_dependency"
            if len(units) == 1 and limitations is not None:
                # R-F9: same unit, different values — name the conflict.
                limitations.append(
                    f"{field_id}: conflicting duplicate facts "
                    + ", ".join(
                        f"{item.occurrence_id}={item.parsed_value}"
                        for item in sorted(
                            admitted, key=lambda item: item.occurrence_id
                        )
                    )
                )
            return _absence_row(
                catalogue_field,
                por,
                "not_evaluable",
                reason,
                concept=mapping.concepts[0],
                occurrence_ids=[item.occurrence_id for item in admitted],
                mapping=mapping,
                pack_id=pack_id,
                catalogue=catalogue,
                limitations=limitations,
            )
        if period_kind == "instant":
            representative = min(admitted, key=lambda item: item.occurrence_id)
        else:
            representative = max(admitted, key=_duration_days)
        catalogue_unit = catalogue_field.get("unit")
        equivalents = _unit_equivalents(catalogue_unit)
        if equivalents is not None:
            # R-F1: the ledger unit must satisfy the catalogue unit before the
            # catalogue unit is copied onto the row.
            ledger_unit = _unit_measure(representative.unit)
            if ledger_unit not in equivalents:
                mismatching = [
                    item
                    for item in admitted
                    if _unit_measure(item.unit) not in equivalents
                ]
                if limitations is not None:
                    limitations.append(
                        f"{field_id}: fact unit {ledger_unit} is not"
                        f" {catalogue_unit}"
                    )
                return _absence_row(
                    catalogue_field,
                    por,
                    "not_evaluable",
                    "unit_mismatch",
                    concept=mapping.concepts[0],
                    occurrence_ids=[
                        item.occurrence_id for item in mismatching
                    ],
                    mapping=mapping,
                    pack_id=pack_id,
                    catalogue=catalogue,
                    limitations=limitations,
                )
        row = _base_row(catalogue_field, por)
        row["quality_state"] = "valued"
        row["non_value_state"] = None
        row["coverage_state"] = "source_trace_complete"
        row["reason"] = None
        row["concept"] = representative.concept_qname
        row["taxonomy"] = (
            "extension"
            if representative.concept_qname.startswith("{")
            else representative.concept_qname.split(":", 1)[0]
        )
        row["source_occurrence_ids"] = sorted(
            {item.occurrence_id for item in admitted}
        )
        row["mapping_rule_id"] = f"{pack_id}.{field_id}.fact/v1"
        row["mapping_rule_digest"] = _mapping_digest(mapping)
        if representative.context.explicit_dimensions:
            row["dimensions"] = [
                {"axis": axis, "member": str(member)}
                for axis, member in sorted(
                    representative.context.explicit_dimensions.items()
                )
            ]
        if period_kind != "instant":
            row["period"] = {
                "kind": "duration",
                "start": representative.context.start.isoformat(),
                "end": representative.context.end.isoformat(),
            }
        row["unit"] = (
            catalogue_unit
            if catalogue_unit is not None
            else _unit_measure(representative.unit)
        )
        if catalogue_field["type"] in contract.NUMERIC_TYPES:
            row["value"] = decimal_text(
                Decimal(str(representative.parsed_value))
            )
        else:
            token = representative.raw_token
            row["text_value"] = (
                token if token is not None else str(representative.parsed_value)
            )
        decimals: int | None = None
        if (
            representative.decimals is not None
            and representative.decimals != "INF"
        ):
            decimals = int(representative.decimals)
        return _FieldOutcome(
            row=row,
            value=Decimal(str(representative.parsed_value)),
            decimals=decimals,
            unit=row["unit"],
        )

    if dimensioned_seen:
        return _absence_row(
            catalogue_field,
            por,
            "missing",
            "disallowed_dimension",
            concept=mapping.concepts[0],
            mapping=mapping,
            pack_id=pack_id,
            catalogue=catalogue,
            limitations=limitations,
        )
    if unknown_dimensions_seen:
        # R-F3: dimensional context not exposed by the source plane.
        if limitations is not None:
            limitations.append(
                f"{field_id}: dimensional context not exposed by the source"
                " plane (dimensions_known=false)"
            )
        return _absence_row(
            catalogue_field,
            por,
            "missing",
            "disallowed_dimension",
            concept=mapping.concepts[0],
            occurrence_ids=[
                item.occurrence_id for item in unknown_dimensions_seen
            ],
            mapping=mapping,
            pack_id=pack_id,
            catalogue=catalogue,
            limitations=limitations,
        )
    wanted_locals = {_local_name(concept) for concept in mapping.concepts}
    extension_namespaces = sorted(
        {
            _namespace_uri(qname)
            for qname in by_concept
            if qname.startswith("{")
            and _local_name(qname) in wanted_locals
            and any(
                _period_matches(item, period_kind, por)
                for item in by_concept[qname]
            )
        }
    )
    for namespace in extension_namespaces:
        prefix = _extension_prefix(namespace, extension_prefixes)
        if prefix is not None:
            return _absence_row(
                catalogue_field,
                por,
                "missing",
                f"extension_concept_unaliased:{prefix}",
                concept=mapping.concepts[0],
                mapping=mapping,
                pack_id=pack_id,
                catalogue=catalogue,
                limitations=limitations,
            )
    return _absence_row(
        catalogue_field,
        por,
        "missing",
        f"missing_standard_fact:{mapping.concepts[0]}",
        concept=mapping.concepts[0],
        mapping=mapping,
        pack_id=pack_id,
        catalogue=catalogue,
        limitations=limitations,
    )


def _dimensioned_mapping_digest(mapping: DimensionedFactMapping) -> str:
    payload = canonical_json(
        [
            mapping.concept,
            mapping.primary_axis,
            list(mapping.other_axes_allowed),
            list(mapping.exclude_member_substrings),
        ]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _dimensioned_row(
    *,
    catalogue_field: Mapping[str, Any],
    por: date,
    mapping: DimensionedFactMapping,
    occurrences: Sequence[Any],
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    """Build one member row for one explicit-dimension tuple (A.2)."""
    field_id = catalogue_field["field_id"]
    representative = min(occurrences, key=lambda item: item.occurrence_id)
    row = _base_row(catalogue_field, por)
    distinct = {str(item.parsed_value) for item in occurrences}
    if len(distinct) > 1:
        # Same dimension tuple, different values: the FactMapping conflict rule.
        units = {_unit_measure(item.unit) for item in occurrences}
        reason = "unit_mismatch" if len(units) > 1 else "missing_dependency"
        if len(units) == 1 and limitations is not None:
            # R-F9: same unit, different values — name the conflict.
            limitations.append(
                f"{field_id}: conflicting duplicate facts "
                + ", ".join(
                    f"{item.occurrence_id}={item.parsed_value}"
                    for item in sorted(
                        occurrences, key=lambda item: item.occurrence_id
                    )
                )
            )
        row["quality_state"] = "not_evaluable"
        row["non_value_state"] = "not_evaluable"
        row["coverage_state"] = "unmapped"
        row["reason"] = _project_reason(
            reason, catalogue, field_id, limitations
        )
        row["concept"] = mapping.concept
        row["source_occurrence_ids"] = sorted(
            {item.occurrence_id for item in occurrences}
        )
        return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])
    catalogue_unit = catalogue_field.get("unit")
    equivalents = _unit_equivalents(catalogue_unit)
    if equivalents is not None:
        # R-F1: the ledger unit must satisfy the catalogue unit before the
        # catalogue unit is copied onto the member row.
        ledger_unit = _unit_measure(representative.unit)
        if ledger_unit not in equivalents:
            mismatching = [
                item
                for item in occurrences
                if _unit_measure(item.unit) not in equivalents
            ]
            if limitations is not None:
                limitations.append(
                    f"{field_id}: fact unit {ledger_unit} is not"
                    f" {catalogue_unit}"
                )
            row["quality_state"] = "not_evaluable"
            row["non_value_state"] = "not_evaluable"
            row["coverage_state"] = "unmapped"
            row["reason"] = _project_reason(
                "unit_mismatch", catalogue, field_id, limitations
            )
            row["concept"] = mapping.concept
            row["source_occurrence_ids"] = sorted(
                {item.occurrence_id for item in mismatching}
            )
            return _FieldOutcome(
                row=row, value=None, decimals=None, unit=row["unit"]
            )
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["concept"] = mapping.concept
    row["taxonomy"] = (
        "extension"
        if mapping.concept.startswith("{")
        else mapping.concept.split(":", 1)[0]
    )
    row["source_occurrence_ids"] = sorted(
        {item.occurrence_id for item in occurrences}
    )
    row["dimensions"] = [
        {"axis": axis, "member": str(member)}
        for axis, member in sorted(representative.context.explicit_dimensions)
    ]
    row["unit"] = (
        catalogue_unit
        if catalogue_unit is not None
        else _unit_measure(representative.unit)
    )
    if catalogue_field["type"] in contract.NUMERIC_TYPES:
        row["value"] = decimal_text(Decimal(str(representative.parsed_value)))
    else:
        token = representative.raw_token
        row["text_value"] = (
            token if token is not None else str(representative.parsed_value)
        )
    decimals: int | None = None
    if (
        representative.decimals is not None
        and representative.decimals != "INF"
    ):
        decimals = int(representative.decimals)
    return _FieldOutcome(
        row=row,
        value=Decimal(str(representative.parsed_value)),
        decimals=decimals,
        unit=row["unit"],
    )


def _resolve_dimensioned_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: DimensionedFactMapping,
    ledger: RawFactLedger,
    por: date,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    """A.2: one row per admitted explicit-dimension tuple of one concept.

    The outcome's ``value`` is the sum over every valued member row, so a
    check operand (A.5) reconciles the member rows against the consolidated
    field. Rows are ordered by the canonical JSON of their ``dimensions``
    list. Occurrences whose dimensional context the source plane did not
    expose (R-F3) never join a tuple.
    """
    field_id = catalogue_field["field_id"]
    period_kind = catalogue_field["period_kind"]
    candidates: list[Any] = []
    unknown_dimensions_seen: list[Any] = []
    for occurrence in ledger.events:
        if occurrence.concept_qname != mapping.concept or occurrence.is_nil:
            continue
        if not _period_matches(occurrence, period_kind, por):
            continue
        if occurrence.dimensions_known is False:
            unknown_dimensions_seen.append(occurrence)  # R-F3
            continue
        candidates.append(occurrence)
    allowed_axes = {mapping.primary_axis, *mapping.other_axes_allowed}
    excluded_lower = tuple(
        substring.lower() for substring in mapping.exclude_member_substrings
    )
    groups: dict[tuple[tuple[str, str], ...], list[Any]] = {}
    foreign_axis_seen = False
    for occurrence in candidates:
        context = occurrence.context
        # ``explicit_dimensions`` is a canonical tuple of (axis, member) pairs.
        axes = {axis for axis, _member in context.explicit_dimensions} | {
            axis for axis, _member in context.typed_dimensions
        }
        if not axes <= allowed_axes:
            foreign_axis_seen = True
            continue
        if mapping.primary_axis not in axes:
            continue
        if any(
            substring in _local_name(str(member)).lower()
            for substring in excluded_lower
            for _axis, member in context.explicit_dimensions
        ):
            continue
        key = tuple(sorted(context.explicit_dimensions))
        groups.setdefault(key, []).append(occurrence)

    outcomes = [
        _dimensioned_row(
            catalogue_field=catalogue_field,
            por=por,
            mapping=mapping,
            occurrences=occurrences,
            catalogue=catalogue,
            limitations=limitations,
        )
        for _key, occurrences in groups.items()
    ]
    outcomes.sort(key=lambda outcome: canonical_json(outcome.row["dimensions"]))
    if not outcomes:
        if unknown_dimensions_seen:
            # R-F3: dimensional context not exposed by the source plane.
            if limitations is not None:
                limitations.append(
                    f"{field_id}: dimensional context not exposed by the"
                    " source plane (dimensions_known=false)"
                )
            row = _absence_row(
                catalogue_field,
                por,
                "missing",
                "disallowed_dimension",
                concept=mapping.concept,
                occurrence_ids=[
                    item.occurrence_id for item in unknown_dimensions_seen
                ],
                catalogue=catalogue,
                limitations=limitations,
            )
        else:
            row = _absence_row(
                catalogue_field,
                por,
                "missing",
                (
                    "disallowed_dimension"
                    if foreign_axis_seen
                    else f"missing_standard_fact:{mapping.concept}"
                ),
                concept=mapping.concept,
                catalogue=catalogue,
                limitations=limitations,
            )
        row.row["mapping_rule_id"] = f"{pack_id}.{field_id}.dimensioned_fact/v1"
        row.row["mapping_rule_digest"] = _dimensioned_mapping_digest(mapping)
        return row

    for outcome in outcomes:
        outcome.row["mapping_rule_id"] = f"{pack_id}.{field_id}.dimensioned_fact/v1"
        outcome.row["mapping_rule_digest"] = _dimensioned_mapping_digest(mapping)
    valued = [outcome for outcome in outcomes if outcome.value is not None]
    total = (
        sum((outcome.value for outcome in valued), Decimal("0"))
        if len(valued) == len(outcomes)
        else None
    )
    decimals_known = [
        outcome.decimals for outcome in outcomes if outcome.decimals is not None
    ]
    return _FieldOutcome(
        row=outcomes[0].row,
        value=total,
        decimals=min(decimals_known) if decimals_known else None,
        unit=outcomes[0].unit,
        extra_rows=tuple(outcome.row for outcome in outcomes[1:]),
    )


def _resolve_formula(
    *,
    catalogue_field: Mapping[str, Any],
    mapping: FormulaMapping,
    por: date,
    resolve_input: Callable[[str], _FieldOutcome],
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    field_id = catalogue_field["field_id"]
    row = _base_row(catalogue_field, por)
    row["evidence_kind"] = "formula"
    row["required_evidence_kind"] = "formula"
    row["formula_rule_id"] = mapping.rule_id
    row["dependency_field_ids"] = list(dict.fromkeys(mapping.inputs))

    def not_evaluable(reason: str) -> _FieldOutcome:
        row["quality_state"] = "not_evaluable"
        row["non_value_state"] = "not_evaluable"
        row["coverage_state"] = "unmapped"
        row["reason"] = _project_reason(
            reason, catalogue, field_id, limitations
        )
        return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])

    resolved_inputs: dict[str, _FieldOutcome] = {}
    for input_id in mapping.inputs:
        outcome = resolve_input(input_id)
        if outcome is None or outcome.value is None:
            return not_evaluable("missing_dependency")  # R-K3: never zero
        resolved_inputs[input_id] = outcome
    units = {
        outcome.unit for outcome in resolved_inputs.values() if outcome.unit
    }
    if len(units) > 1:
        return not_evaluable("unit_mismatch")
    field_unit = catalogue_field.get("unit")
    if field_unit is not None:
        # R-F1: the field unit, not only operand-vs-operand agreement, governs
        # a formula.  A sum/difference needs identical operand units equal to
        # the field unit; a ratio needs a ratio/percent field (or identical
        # operand units under a currency field).  A ``pure`` operand value is
        # never rescaled into a percent/ratio field.
        operand_unit = next(iter(units), None)
        unit_consistent = field_unit in ("ratio", "percent") or (
            operand_unit is not None
            and operand_unit in _unit_equivalents(field_unit)
        )
        if not unit_consistent:
            return not_evaluable("unit_mismatch")
    values = {
        input_id: outcome.value for input_id, outcome in resolved_inputs.items()
    }
    try:
        result = mapping.fn(values)
    except ZeroDivisionError:
        return not_evaluable("division_by_zero")
    if not isinstance(result, Decimal):
        raise SpecialistPackError(
            f"formula {mapping.rule_id} returned a non-decimal result"
        )
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["value"] = decimal_text(result)
    return _FieldOutcome(row=row, value=result, decimals=None, unit=row["unit"])


# --------------------------------------------------------------------------
# Check evaluation
# --------------------------------------------------------------------------


class _OperandResolver:
    """Resolves check operands: own-pack fields and ``pkNN:field`` foreigns.

    R-F5: the resolver carries the ordered chain of pack ids in progress
    (threaded through ``produce_pack`` via ``PackInput.packs_in_progress``,
    never a module global).  Re-entering a pack already on the chain resolves
    the operand as non-valued and records the cycle limitation; the outer
    pack still produces its envelope.
    """

    def __init__(
        self,
        outcomes: Mapping[str, _FieldOutcome],
        pack_input: PackInput,
        foreign_cache: dict[str, dict[str, Any]],
        *,
        pack_id: str | None = None,
        limitations: list[str] | None = None,
    ) -> None:
        self._outcomes = outcomes
        self._pack_input = pack_input
        self._foreign_cache = foreign_cache
        self._chain = tuple(pack_input.packs_in_progress) + (
            (pack_id,) if pack_id is not None else ()
        )
        self._limitations = limitations

    def own(self, name: str) -> bool:
        head, sep, _tail = name.partition(_CROSS_OPERAND_SEPARATOR)
        return not (
            sep
            and head.lower().startswith(_FOREIGN_OPERAND_PREFIX)
            and head[2:].isdigit()
        )

    def quality(self, name: str) -> str | None:
        if not self.own(name):
            return None
        outcome = self._outcomes.get(name)
        return None if outcome is None else str(outcome.row["quality_state"])

    def reason(self, name: str) -> str | None:
        if not self.own(name):
            return None
        outcome = self._outcomes.get(name)
        return None if outcome is None else outcome.row.get("reason")

    def _foreign_result(
        self, pack_id: str, context: str | None = None
    ) -> dict[str, Any] | None:
        from .registry import produce_pack  # deferred: registry imports base

        if pack_id in self._chain:
            # R-F5: cut the cross-pack cycle at the re-entry edge.
            if self._limitations is not None:
                segment = self._chain[self._chain.index(pack_id) :] + (pack_id,)
                self._limitations.append(
                    f"{context or pack_id}: cross-pack cycle"
                    f" {' -> '.join(segment)}"
                )
            return None
        if pack_id not in self._foreign_cache:
            if pack_id not in _registered_pack_ids():
                return None
            child_input = replace(
                self._pack_input, packs_in_progress=self._chain
            )
            self._foreign_cache[pack_id] = produce_pack(pack_id, child_input)
        return self._foreign_cache[pack_id]

    def resolve(
        self, name: str, context: str | None = None
    ) -> tuple[Decimal | None, int | None, str | None]:
        """Return ``(value, decimals, unit)``; value ``None`` if unresolvable."""
        if self.own(name):
            outcome = self._outcomes.get(name)
            if outcome is None:
                return None, None, None
            return outcome.value, outcome.decimals, outcome.unit
        pack_id, _, foreign_field = name.partition(_CROSS_OPERAND_SEPARATOR)
        result = self._foreign_result(pack_id.upper(), context=context)
        if result is None:
            return None, None, None
        for row in result.get("fields", []):
            if row.get("field_id") == foreign_field:
                if row.get("quality_state") != "valued" or row.get("value") is None:
                    return None, None, None
                return Decimal(str(row["value"])), None, row.get("unit")
        return None, None, None


def _registered_pack_ids() -> tuple[str, ...]:
    from .registry import registered_pack_ids  # deferred: registry imports base

    return registered_pack_ids()


def _identity_tolerance(decimals: Sequence[int | None]) -> Decimal:
    known = [item for item in decimals if item is not None]
    if not known:
        return Decimal("0")
    return Decimal(1).scaleb(-min(known))


def _units_clash(units: Sequence[str | None]) -> bool:
    distinct = {item for item in units if item is not None}
    return len(distinct) > 1


def _relation_holds(
    relation: str, left: Decimal, right: Decimal, tolerance: Decimal
) -> bool:
    if relation == "equal":
        return abs(left - right) <= tolerance
    if relation == "left_lte_right":
        return left <= right + tolerance
    # Scalar reading of ``disjoint``: the two amounts are materially distinct,
    # so the same dollars are not counted on both sides.
    return abs(left - right) > tolerance


def _evaluate_check(
    catalogue_check: Mapping[str, Any],
    specs: Sequence[CheckSpec],
    resolver: _OperandResolver,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    check_id = catalogue_check["check_id"]
    kind = catalogue_check["kind"]
    catalogue_operands: list[str] = list(catalogue_check.get("operands") or [])
    own_operands: list[str] = []
    operand_decimals: list[int | None] = []
    statuses: list[str] = []
    reasons: list[str | None] = []

    def project(code: str | None) -> str | None:
        if code is None:
            return None
        return _project_reason(code, catalogue, check_id, limitations)

    def resolve_many(
        names: Sequence[str],
    ) -> list[tuple[Decimal | None, int | None, str | None]]:
        resolved = [
            resolver.resolve(name, context=check_id) for name in names
        ]
        operand_decimals.extend(item for _, item, _ in resolved)
        return resolved

    def not_applicable_gate(names: Sequence[str]) -> str | None:
        # A.1: a check whose operand field is field-level not_applicable is
        # not_applicable with that field's catalogue reason.
        for name in names:
            if resolver.own(name) and resolver.quality(name) == "not_applicable":
                return resolver.reason(name)
        return None

    def identity(names: Sequence[str], left_count: int) -> None:
        gate = not_applicable_gate(names)
        if gate is not None:
            statuses.append("not_applicable")
            reasons.append(project(gate))
            return
        resolved = resolve_many(names)
        if any(value is None for value, _, _ in resolved):
            statuses.append("not_evaluable")
            reasons.append(project("missing_dependency"))
            return
        if _units_clash([unit for _, _, unit in resolved]):
            statuses.append("not_evaluable")
            reasons.append(project("unit_mismatch"))
            return
        tolerance = _identity_tolerance([item for _, item, _ in resolved])
        left = sum((value for value, _, _ in resolved[:left_count]), Decimal("0"))
        right = sum((value for value, _, _ in resolved[left_count:]), Decimal("0"))
        statuses.append("pass" if abs(left - right) <= tolerance else "fail")
        reasons.append(None)

    for spec in specs:
        spec_kind = _KIND_BY_SPEC[type(spec).__name__]
        if spec_kind != kind:
            raise SpecialistPackError(
                f"check {check_id} declared as {spec_kind}, catalogue says {kind}"
            )
        if isinstance(spec, SumIdentity):
            names = [*spec.addends, spec.total]
            own_operands.extend(name for name in names if resolver.own(name))
            identity(names, len(spec.addends))
        elif isinstance(spec, Rollforward):
            if not spec.opening or not spec.closing:
                raise SpecialistPackError(
                    f"rollforward {check_id} lacks an opening or closing field"
                )
            names = [spec.opening, *spec.additions, *spec.reductions, spec.closing]
            own_operands.extend(name for name in names if resolver.own(name))
            gate = not_applicable_gate(names)
            if gate is not None:
                statuses.append("not_applicable")
                reasons.append(project(gate))
                continue
            resolved = resolve_many(names)
            if any(value is None for value, _, _ in resolved):
                statuses.append("not_evaluable")
                reasons.append(project("missing_dependency"))
                continue
            if _units_clash([unit for _, _, unit in resolved]):
                statuses.append("not_evaluable")
                reasons.append(project("unit_mismatch"))
                continue
            tolerance = _identity_tolerance([item for _, item, _ in resolved])
            expected = resolved[0][0] + sum(
                (value for value, _, _ in resolved[1 : 1 + len(spec.additions)]),
                Decimal("0"),
            ) - sum(
                (
                    value
                    for value, _, _ in resolved[1 + len(spec.additions) : -1]
                ),
                Decimal("0"),
            )
            statuses.append(
                "pass" if abs(expected - resolved[-1][0]) <= tolerance else "fail"
            )
            reasons.append(None)
        elif isinstance(spec, Reconcile):
            names = [*spec.parts, spec.consolidated]
            own_operands.extend(name for name in names if resolver.own(name))
            identity(names, len(spec.parts))
        elif isinstance(spec, CrossStatement):
            if spec.relation not in _CROSS_RELATIONS:
                raise SpecialistPackError(
                    f"check {check_id} declares unknown relation {spec.relation!r}"
                )
            for name in (spec.left, spec.right):
                if resolver.own(name):
                    own_operands.append(name)
            gate = not_applicable_gate([spec.left, spec.right])
            if gate is not None:
                statuses.append("not_applicable")
                reasons.append(project(gate))
                continue
            resolved = resolve_many([spec.left, spec.right])
            if any(value is None for value, _, _ in resolved):
                statuses.append("not_evaluable")
                reasons.append(project("missing_dependency"))
                continue
            tolerance = _identity_tolerance([item for _, item, _ in resolved])
            holds = _relation_holds(
                spec.relation, resolved[0][0], resolved[1][0], tolerance
            )
            statuses.append("pass" if holds else "fail")
            reasons.append(None)
        elif isinstance(spec, Presence):
            own_operands.append(spec.field_id)
            gate = not_applicable_gate([spec.field_id])
            if gate is not None:
                statuses.append("not_applicable")
                reasons.append(project(gate))
                continue
            resolved = resolve_many([spec.field_id])
            value, _, _ = resolved[0]
            if value is not None:
                statuses.append("pass")
                reasons.append(None)
            elif resolver.quality(spec.field_id) == "missing":
                statuses.append("fail")
                reasons.append(None)
            else:
                statuses.append("not_evaluable")
                reasons.append(project("missing_dependency"))
        else:  # pragma: no cover - closed CheckSpec union
            raise SpecialistPackError(f"unsupported check spec for {check_id}")

    status = "pass"
    if "not_applicable" in statuses:
        status = "not_applicable"
    elif "not_evaluable" in statuses:
        status = "not_evaluable"
    elif "fail" in statuses:
        status = "fail"
    reason = next(
        (
            item
            for item, state in zip(reasons, statuses)
            if state == status and item is not None
        ),
        None,
    )
    if status == "not_evaluable" and reason is None:
        reason = "missing_dependency"
    tolerance = (
        _identity_tolerance(operand_decimals) if operand_decimals else None
    )
    return {
        "check_id": check_id,
        "kind": kind,
        "status": status,
        "operands": catalogue_operands,
        "tolerance": decimal_text(tolerance) if tolerance is not None else None,
        "evidence_field_ids": list(dict.fromkeys(own_operands)),
        "reason": reason,
    }


# --------------------------------------------------------------------------
# Envelope production
# --------------------------------------------------------------------------


def _not_applicable_check_row(
    catalogue_check: Mapping[str, Any], reason: str
) -> dict[str, Any]:
    operands = list(catalogue_check.get("operands") or [])
    return {
        "check_id": catalogue_check["check_id"],
        "kind": catalogue_check["kind"],
        "status": "not_applicable",
        "operands": operands,
        "tolerance": None,
        "evidence_field_ids": [
            name for name in operands if _CROSS_OPERAND_SEPARATOR not in name
        ],
        "reason": reason,
    }


def _mint_packet_id(
    entity: Mapping[str, str], accession: str, query: Mapping[str, Any]
) -> str:
    payload = canonical_json(
        {
            "entity_id": entity.get("entity_id"),
            "cik": entity.get("cik"),
            "accession": accession,
            "query": dict(query),
        }
    )
    return "fip_" + sha256(payload.encode("utf-8")).hexdigest()[:24]


def _unsupported_row(
    catalogue_field: Mapping[str, Any],
    por: date,
    evidence_kind: str = "table_cell",
    *,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    # TableMapping and TextSpanMapping are reserved for later lanes (A.4).
    row = _base_row(catalogue_field, por)
    row["evidence_kind"] = evidence_kind
    row["required_evidence_kind"] = evidence_kind
    row["quality_state"] = "unsupported"
    row["non_value_state"] = "unsupported"
    row["coverage_state"] = "unmapped"
    row["reason"] = _project_reason(
        "missing_dependency",
        catalogue,
        catalogue_field["field_id"],
        limitations,
    )
    return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])


def produce_pack_result(
    producer: PackProducer, pack_input: PackInput
) -> dict[str, Any]:
    """Produce one contract-valid ``specialist_pack_result.v1`` envelope."""
    from ..ixbrl_raw_ledger import parse_and_convert_golden_packages

    spec = producer.spec
    pack_id = spec.pack_id
    if pack_id not in contract.PACK_IDS:
        raise SpecialistPackError(f"unknown pack id: {pack_id}")
    catalogue = contract.load_pack_schema(pack_id)

    # R-F7: a producer check spec outside the catalogue is never silently
    # dropped.
    catalogue_check_ids = {
        str(item["check_id"])
        for item in catalogue["checks"]
        if isinstance(item, Mapping) and item.get("check_id")
    }
    for check_spec in producer.checks:
        if check_spec.check_id not in catalogue_check_ids:
            raise SpecialistPackError(
                f"unknown check spec: {check_spec.check_id}"
            )

    # R-F4: every package must belong to the packet entity (10-digit CIK
    # compare against the entity CIK or source entity id), checked before the
    # ledger is built.
    entity_ciks = {
        _cik10(value)
        for value in (
            pack_input.entity.get("cik"),
            pack_input.entity.get("source_entity_id"),
        )
        if value not in (None, "")
    }
    entity_cik_text = str(
        pack_input.entity.get("cik") or pack_input.entity.get("source_entity_id")
    )
    for item in pack_input.packages:
        package_cik = _cik10(item.manifest.get("cik"))
        if package_cik not in entity_ciks:
            raise SpecialistPackError(
                f"package issuer mismatch:"
                f" {str(item.manifest.get('accession') or '')}"
                f" cik={package_cik} entity cik={entity_cik_text}"
            )

    # Framework-appended limitation lines (R-F1, R-F3, R-F6, R-F9, R-F10);
    # branch/producer lines keep their frozen order ahead of these.
    framework_limitations: list[str] = []
    # R-F10: the numeric-only converter cannot value a text/enum/boolean/
    # duration field; say so once per envelope, whatever the applicability.
    for catalogue_field in catalogue["fields"]:
        if catalogue_field["type"] in contract.NON_NUMERIC_TYPES:
            framework_limitations.append(
                f"{catalogue_field['field_id']}: text-type field;"
                " numeric-only converter cannot value it"
            )

    ledger, _filing_metadata, report = parse_and_convert_golden_packages(
        pack_input.packages
    )
    primary, form_matched = _select_primary(pack_input.packages, spec.forms)
    primary_manifest: Mapping[str, Any] = primary.manifest
    primary_form = str(primary_manifest.get("form") or "") if form_matched else None
    por_text = str(primary_manifest.get("period_of_report") or "")
    if not por_text:
        raise SpecialistPackError("primary package carries no period_of_report")
    por = date.fromisoformat(por_text[:10])
    issuer_class = detectors.issuer_class_for_sic(pack_input.issuer_sic)
    state, reason = evaluate_applicability(
        producer,
        pack_input,
        primary_form,
        ledger,
        catalogue=catalogue,
        limitations=framework_limitations,
    )

    fields_rows: list[dict[str, Any]] = []
    checks_rows: list[dict[str, Any]] = []
    outcomes: dict[str, _FieldOutcome | None] = {}
    # A.3: the fact half of a FactOrFormulaMapping, kept for the fallback.
    fact_only_outcomes: dict[str, _FieldOutcome] = {}
    # B.3-style conditional limitations emitted when a formula branch won.
    branch_limitations: list[str] = []

    if state != "applicable":
        for catalogue_field in catalogue["fields"]:
            outcome = _absence_row(catalogue_field, por, state, reason)
            outcomes[catalogue_field["field_id"]] = outcome
            fields_rows.append(outcome.row)
        for catalogue_check in catalogue["checks"]:
            checks_rows.append(_not_applicable_check_row(catalogue_check, reason))
    else:
        for catalogue_field in catalogue["fields"]:
            field_id = catalogue_field["field_id"]
            mapping = producer.field_mappings.get(field_id)
            if mapping is None:
                raise SpecialistPackError(
                    f"{pack_id} producer maps no field: {field_id}"
                )
            allowed = catalogue_field.get("allowed_evidence_kinds") or []
            exclusion = spec.field_class_exclusions.get(field_id)
            if exclusion is not None and (
                issuer_class == "unknown" or issuer_class in exclusion[0]
            ):
                # A.1 field-level issuer-class exclusion (never a silent
                # industrial default when the class is unknown).
                if issuer_class == "unknown":
                    outcomes[field_id] = _absence_row(
                        catalogue_field,
                        por,
                        "not_evaluable",
                        "issuer_class_unknown",
                        catalogue=catalogue,
                        limitations=framework_limitations,
                    )
                else:
                    outcomes[field_id] = _absence_row(
                        catalogue_field,
                        por,
                        "not_applicable",
                        exclusion[1],
                        catalogue=catalogue,
                        limitations=framework_limitations,
                    )
            elif isinstance(mapping, (TableMapping, TextSpanMapping)) or allowed in (
                ["table_cell"],
                ["text_span"],
            ):
                outcomes[field_id] = _unsupported_row(
                    catalogue_field,
                    por,
                    "text_span"
                    if isinstance(mapping, TextSpanMapping) or allowed == ["text_span"]
                    else "table_cell",
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            elif isinstance(mapping, DimensionedFactMapping):
                outcomes[field_id] = _resolve_dimensioned_fact_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    ledger=ledger,
                    por=por,
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            elif isinstance(mapping, FactMapping):
                outcomes[field_id] = _resolve_fact_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    ledger=ledger,
                    por=por,
                    extension_prefixes=producer.extension_prefixes,
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            elif isinstance(mapping, FactOrFormulaMapping):
                fact_only_outcomes[field_id] = _resolve_fact_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping.fact,
                    ledger=ledger,
                    por=por,
                    extension_prefixes=producer.extension_prefixes,
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            else:
                outcomes[field_id] = None  # formulas resolve after facts

        def _run_formula(field_id: str, mapping: FormulaMapping) -> _FieldOutcome:
            if field_id in resolving:
                raise SpecialistPackError(
                    f"formula dependency cycle at {field_id}"
                )
            resolving.add(field_id)
            try:
                return _resolve_formula(
                    catalogue_field=next(
                        item
                        for item in catalogue["fields"]
                        if item["field_id"] == field_id
                    ),
                    mapping=mapping,
                    por=por,
                    resolve_input=resolve_field,
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            finally:
                resolving.discard(field_id)

        def resolve_field(field_id: str) -> _FieldOutcome | None:
            outcome = outcomes.get(field_id)
            if outcome is not None:
                return outcome
            mapping = producer.field_mappings.get(field_id)
            if isinstance(mapping, FormulaMapping):
                outcome = _run_formula(field_id, mapping)
            elif isinstance(mapping, FactOrFormulaMapping):
                fact_outcome = fact_only_outcomes.get(field_id)
                if fact_outcome is not None and fact_outcome.value is not None:
                    outcome = fact_outcome  # A.3: the fact wins
                else:
                    outcome = _run_formula(field_id, mapping.formula)
                    # A.3: the fact is the required evidence; the formula
                    # only reports which branch produced the row.
                    outcome.row["required_evidence_kind"] = "xbrl_fact"
                    if mapping.limitation_when_formula is not None:
                        branch_limitations.append(mapping.limitation_when_formula)
            else:
                return outcome
            outcomes[field_id] = outcome
            return outcome

        resolving: set[str] = set()
        for catalogue_field in catalogue["fields"]:
            outcomes[catalogue_field["field_id"]] = resolve_field(
                catalogue_field["field_id"]
            )
        for catalogue_field in catalogue["fields"]:
            outcome = outcomes[catalogue_field["field_id"]]
            assert outcome is not None
            fields_rows.append(outcome.row)
            fields_rows.extend(outcome.extra_rows)

        specs_by_check: dict[str, list[CheckSpec]] = {}
        for check_spec in producer.checks:
            specs_by_check.setdefault(check_spec.check_id, []).append(check_spec)
        resolver = _OperandResolver(
            outcomes,
            pack_input,
            foreign_cache={},
            pack_id=pack_id,
            limitations=framework_limitations,
        )
        for catalogue_check in catalogue["checks"]:
            check_id = catalogue_check["check_id"]
            specs = specs_by_check.get(check_id)
            if not specs:
                raise SpecialistPackError(
                    f"{pack_id} producer declares no check: {check_id}"
                )
            checks_rows.append(
                _evaluate_check(
                    catalogue_check,
                    specs,
                    resolver,
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            )

    coverage_counts = {
        "valued_fields": 0,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
    }
    for row in fields_rows:
        coverage_key = contract.QUALITY_TO_COVERAGE.get(row["quality_state"])
        if coverage_key is not None:
            coverage_counts[coverage_key] += 1
    if state != "applicable":
        disclosure_state = "not_supplied"
    elif coverage_counts["valued_fields"] > 0:
        disclosure_state = "present"
    else:
        disclosure_state = "empty"

    accession = str(primary_manifest.get("accession") or "")
    minted_basis: str | None = None
    packet_id = pack_input.packet_id
    if packet_id is None:
        packet_id = _mint_packet_id(
            pack_input.entity, accession, pack_input.query
        )
        minted_basis = "standalone_pack_context"

    receipts = [
        f"catalogue_digest={contract.pack_schema_digest(pack_id)}",
        f"accession={accession}",
        f"form={primary_manifest.get('form')}",
        f"period_of_report={por_text}",
    ]
    primary_document = str(primary_manifest.get("primary_document") or "")
    for item in primary_manifest.get("members") or []:
        if (
            isinstance(item, dict)
            and item.get("name") == primary_document
            and item.get("state") == "stored"
            and item.get("content_sha256")
        ):
            receipts.append(f"primary_document_sha256={item['content_sha256']}")
            break
    conversion_fact_count = sum(
        filing.represented_count for filing in report.filings
    )
    receipts.append(f"conversion_fact_count={conversion_fact_count}")
    receipts.append(f"issuer_class={issuer_class}")
    # R-F4/R-F10 receipts: non-primary packages stay visible, and the primary
    # selection rule is named. R-F1: the unit law this envelope obeyed.
    accessions = [
        str(item.manifest.get("accession") or "") for item in pack_input.packages
    ]
    ordered_accessions = [accession] + [
        item for item in accessions if item != accession
    ]
    receipts.append(f"packages_admitted={len(pack_input.packages)}")
    receipts.append("package_accessions=" + ",".join(ordered_accessions))
    receipts.append("primary_selection=form_rank_then_latest_period")
    receipts.append("unit_check=catalogue_equivalence_v1")
    if minted_basis is not None:
        receipts.append(f"packet_id_basis={minted_basis}")

    limitations = list(
        dict.fromkeys(
            (
                DISPLAY_ONLY_LIMITATION,
                *producer.limitations,
                *branch_limitations,
                *framework_limitations,
            )
        )
    )
    if len(limitations) > 32:  # R-F10: overflow is a loud refusal, not a trim
        raise SpecialistPackError(f"limitations overflow: {len(limitations)}")

    obj: dict[str, Any] = {
        "schema": SCHEMA,
        "pack_id": pack_id,
        "pack_schema_id": catalogue["pack_schema_id"],
        "pack_schema_digest": contract.pack_schema_digest(pack_id),
        "pack_content_sha256": None,
        "packet_id": packet_id,
        "entity": dict(pack_input.entity),
        "query": dict(pack_input.query),
        "applicability": {
            "state": state,
            "reason": reason,
            "rule_id": spec.applicability_rule_id,
            "sic": pack_input.issuer_sic,
            "sic_source": pack_input.sic_source,
        },
        "fields": fields_rows,
        "checks": checks_rows,
        "coverage": {
            **coverage_counts,
            "disclosure_coverage_state": disclosure_state,
        },
        "limitations": limitations,
        "receipts": receipts,
        "authority": {"class": "context_only", "display_only": True},
    }
    obj["pack_content_sha256"] = contract.pack_content_digest(obj)
    errors = contract.validate_pack_result(obj)
    if errors:
        raise SpecialistPackError("invalid pack result: " + "; ".join(errors[:5]))
    return obj


__all__ = [
    "CheckSpec",
    "CrossStatement",
    "DISPLAY_ONLY_LIMITATION",
    "DimensionedFactMapping",
    "FactMapping",
    "FactOrFormulaMapping",
    "FieldMapping",
    "FormulaMapping",
    "MAX_DURATION_DAYS",
    "PackInput",
    "PackProducer",
    "PackSpec",
    "Presence",
    "Reconcile",
    "Rollforward",
    "SCHEMA",
    "SpecialistPackError",
    "SumIdentity",
    "TableMapping",
    "TextSpanMapping",
    "UNIT_EQUIVALENTS",
    "evaluate_applicability",
    "formula_difference",
    "formula_ratio",
    "formula_sum",
    "produce_pack_result",
]
