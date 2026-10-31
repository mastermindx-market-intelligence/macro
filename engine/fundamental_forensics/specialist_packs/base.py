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
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
import re
from typing import TYPE_CHECKING, Any, Callable, Mapping, Sequence

if TYPE_CHECKING:  # pragma: no cover - narrative imports base at runtime
    from .narrative import NarrativeText, SectionSpec, Span

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
    """Map a field onto the first standard concept that resolves.

    ``period_select="cover_instant"`` (A.1) admits, for an ``instant`` field,
    the latest instant context on or after ``period_of_report`` and on or
    before ``filed_at``; the row's ``period`` reports the instant actually
    used. ``optional_axes`` (A.2) emits the undimensioned fact first as the
    consolidated row, then one row per admitted axis member, all under the
    same ``field_id``; ``consolidated_row=False`` suppresses the consolidated
    row (B.2: it duplicates another field). ``concepts=()`` (A.3) declares the
    field unmapped. ``limitation_when_absent`` is appended to the envelope's
    limitations when the mapping yields a ``missing`` row.
    """

    concepts: tuple[str, ...]
    dimensions_allowed: tuple[str, ...] = ()
    period_select: str = "primary"
    optional_axes: tuple[str, ...] = ()
    consolidated_row: bool = True
    limitation_when_absent: str | None = None
    # A.1 (PK05): ``"precision_consistent"`` admits undimensioned duplicates
    # that differ only by stated precision — the most precise ``decimals``
    # occurrence governs when every coarser one rounds to it. The default
    # keeps the BASE behaviour: differing ``parsed_value`` at the same
    # concept/period stays ``not_evaluable`` (PK-FW A.6).
    duplicate_policy: str = ""


@dataclass(frozen=True)
class FormulaMapping:
    """Map a field onto a decimal formula over other fields of this pack."""

    rule_id: str
    inputs: tuple[str, ...]
    fn: Callable[[Mapping[str, Decimal]], Decimal]
    # R-F1 derived-unit declaration: when the field unit is a derived count
    # (``quarters`` from USD cash over USD burn) the operands share THIS unit
    # rather than the field unit.  ``None`` keeps the plain R-F1 rule.
    operand_unit: str | None = None


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

    concept: str = ""
    # A.4: ``primary_axis`` defaults to ``""`` so a multi-axis mapping may
    # declare ``primary_axes`` alone; every BASE producer passes the single
    # axis positionally and is unaffected.
    primary_axis: str = ""
    other_axes_allowed: tuple[str, ...] = ()
    exclude_member_substrings: tuple[str, ...] = ()
    # A.4 additions: the tuple form of ``primary_axis`` (multi-axis grouped
    # emission in declared order), the definition-linkbase member filter and
    # the optional-other-member admission. All three default to PK01
    # behaviour, and none enters the mapping digest unless used.
    primary_axes: tuple[str, ...] = ()
    member_filter: str = ""
    optional_other_members: Mapping[str, str] | None = None
    # A.1/A.2 additions (PK03 lane): ``concepts`` is the tuple form of
    # ``concept`` — rows are emitted per concept in declared order, each row's
    # ``concept`` naming the concept it came from, and zero rows over all
    # concepts emit one ``missing`` row for the first concept. A
    # ``member_allowlist`` admits only primary-axis members it lists, in
    # declared (never canonical) order; facts under other members are ignored
    # silently (they belong to other fields). Both default to the PK01/PK04
    # behaviour and enter the mapping digest only when used.
    concepts: tuple[str, ...] = ()
    member_allowlist: tuple[str, ...] = ()


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
    """A.3: one field read as a regex span over the primary document narrative.

    An instance with an empty ``pattern`` is the reserved form (A.4): it still
    produces the ``unsupported`` typed absence and no span evidence. A real
    mapping resolves through :mod:`narrative` — see the end of this module.
    ``section`` is a ``narrative.SectionSpec``; ``None`` reads the whole text.
    """

    section: "SectionSpec | None" = None
    pattern: str = ""
    kind: str = "text"  # "text" | "enum" | "boolean"
    enum_map: Mapping[str, str] = field(default_factory=dict)
    absent_value: str | bool | None = None
    max_chars: int = 1024


FieldMapping = (
    FactMapping
    | FormulaMapping
    | DimensionedFactMapping
    | FactOrFormulaMapping
    | TableMapping
    | TextSpanMapping
)
# A.2 (PK04) adds TypedDimensionedFactMapping as a sixth mapping kind; it is
# declared at the end of this module and intentionally not spliced into the
# historical FieldMapping alias above, which is documentation for the kinds
# the BASE producers declare. Dispatch is isinstance-based either way.


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
    # A.6: format template (``{field_id}``, ``{implied}``) for the limitation
    # that names the single missing operand's implied value the producer
    # refused to derive (R-K3). ``None`` (every earlier pack) emits nothing.
    implied_limitation_template: str | None = None


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
    """Two-operand relation, or an A.5 named-rule check over ``operands``.

    The historical ``left``/``right``/``relation`` form is unchanged. A
    ``rule`` id (resolved through the producer's ``check_rules``) selects the
    A.5 form: ``operands`` names the participating fields and the rule
    callable decides pass/fail; ``same_period_required`` makes differing
    operand periods ``not_evaluable`` / ``unit_mismatch`` — never a pass.
    """

    check_id: str
    left: str = ""
    right: str = ""
    relation: str = "equal"
    operands: tuple[str, ...] = ()
    rule: str = ""

    def __post_init__(self) -> None:
        if self.rule:
            # A.5 named-rule form: R-F8 applies to ``operands`` instead.
            if not self.operands:
                raise SpecialistPackError(
                    f"cross statement {self.check_id} lacks an operand field"
                )
            return
        if not self.left or not self.right:  # R-F8
            raise SpecialistPackError(
                f"cross statement {self.check_id} lacks an operand field"
            )


@dataclass(frozen=True)
class Presence:
    check_id: str
    field_id: str


CheckSpec = SumIdentity | Rollforward | Reconcile | CrossStatement | Presence


@dataclass(frozen=True)
class RuleOperand:
    """One named operand of an A.5 rule check, with its emitted rows."""

    field_id: str
    value: Decimal | None
    decimals: int | None
    unit: str | None
    period: Mapping[str, Any] | None
    rows: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class RuleOutcome:
    """A rule callable's verdict; ``tolerance`` overrides the printed one."""

    status: str
    reason: str | None = None
    tolerance: Decimal | None = None


CheckRuleFn = Callable[[Mapping[str, RuleOperand]], RuleOutcome]


@dataclass(frozen=True)
class CheckRule:
    """A named producer-side rule an A.5 CrossStatement cites by id."""

    rule_id: str
    fn: CheckRuleFn
    same_period_required: bool = False
    limitation_when_period_mismatch: str | None = None


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
    # A.5: rule_id -> named rule callable for rule-based CrossStatements.
    check_rules: Mapping[str, CheckRule] = field(default_factory=dict)
    # Optional extra R-K1 rule evaluated after the framework's own rules.
    extra_applicability: ExtraApplicabilityFn | None = None
    # Extension prefixes this producer acknowledges, prefix -> namespace URI.
    # An unaliased extension fact is only nameable when its namespace is here;
    # the map carries issuer knowledge as data, never code literals.
    extension_prefixes: Mapping[str, str] = field(default_factory=dict)
    # Optional narrative extensions (defined at the end of this module).
    # ``None`` keeps producer behaviour byte-identical to a no-hook build.
    hooks: "NarrativeHooks | None" = None


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


def _period_matches(
    occurrence: Any,
    period_kind: str,
    por: date,
    *,
    filed_at: date | None = None,
    period_select: str = "primary",
    opening_bound: date | None = None,
) -> bool:
    context = occurrence.context
    if period_kind == "instant":
        if period_select == "cover_instant":
            # A.1: latest DEI cover instant inside [period_of_report, filed_at].
            if context.instant is None:
                return False
            if context.instant < por:
                return False
            return filed_at is None or context.instant <= filed_at
        if period_select == "opening_instant":
            # A.1 (PK04): the day before the primary fiscal duration's start,
            # falling back to the latest instant strictly before that start.
            return (
                context.instant is not None
                and opening_bound is not None
                and context.instant <= opening_bound
            )
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
    # The payload keeps its historical two-element shape for mappings that use
    # no A.1/A.2 hook, so an existing producer's digest (and envelope bytes)
    # cannot move when the new keywords stay at their defaults.
    payload: list[Any] = [list(mapping.concepts), list(mapping.dimensions_allowed)]
    if (
        mapping.period_select != "primary"
        or mapping.optional_axes
        or not mapping.consolidated_row
        or mapping.limitation_when_absent is not None
        or mapping.duplicate_policy != ""
    ):
        hooks: dict[str, Any] = {
            "period_select": mapping.period_select,
            "optional_axes": list(mapping.optional_axes),
            "consolidated_row": mapping.consolidated_row,
            "limitation_when_absent": mapping.limitation_when_absent,
        }
        if mapping.duplicate_policy != "":
            # A.1 (PK05): enters the digest only when a mapping declares it,
            # so a BASE mapping's digest (and envelope) cannot move.
            hooks["duplicate_policy"] = mapping.duplicate_policy
        payload.append(hooks)
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _FieldOutcome:
    """One field's production: its first row, value and any repeated rows.

    ``value`` is the field total a check consumes — for a dimensioned field
    the sum of every valued member row (A.5). ``extra_rows`` carries the
    member rows after the first; they keep catalogue order and adjacency.
    A.2 optional-axis fields additionally expose the emitted consolidated
    value and the per-member values (``None`` for a non-valued member row)
    under ``axis_breakdown`` for the A.4 table check shape.
    """

    row: dict[str, Any]
    value: Decimal | None
    decimals: int | None
    unit: str | None
    extra_rows: tuple[dict[str, Any], ...] = ()
    consolidated_value: Decimal | None = None
    member_values: tuple[Decimal | None, ...] = ()
    axis_breakdown: bool = False
    # A.4/A.5 (PK04): per-axis definition-linkbase member groups and each
    # member's row value, consumed only by the grouped sum identity.
    group_breakdown: tuple["_AxisGroupBreakdown", ...] = ()
    # A.2/A.3 (PK05): the calculation-arc weights of a calculation-children
    # field's rows, in emission (arc) order, consumed only by the weighted
    # sum identity when its spec declares no weights of its own.
    calculation_weights: tuple[Decimal, ...] = ()


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


def _rf9_conflict_limitation(
    limitations: list[str] | None,
    field_id: str,
    occurrences: Sequence[Any],
) -> None:
    """R-F9: same unit, different values — name the conflict in limitations.

    Shared by every whole-field conflict branch (plain, axes-consolidated,
    typed-dimensioned and calculation-children resolvers) so the disclosure
    line is byte-identical whichever resolver observed the duplicate facts.
    """
    if limitations is None:
        return
    limitations.append(
        f"{field_id}: conflicting duplicate facts "
        + ", ".join(
            f"{item.occurrence_id}={item.parsed_value}"
            for item in sorted(occurrences, key=lambda item: item.occurrence_id)
        )
    )


def _resolve_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: FactMapping,
    ledger: RawFactLedger,
    por: date,
    extension_prefixes: Mapping[str, str],
    filed_at: date | None = None,
    opening_bound: date | None = None,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    period_kind = catalogue_field["period_kind"]
    field_id = catalogue_field["field_id"]
    if not mapping.concepts:
        # A.3: an empty alias tuple is a declared unmapped field.
        allowed_kinds = list(
            catalogue_field.get("allowed_evidence_kinds") or ["xbrl_fact"]
        )
        outcome = _unsupported_row(catalogue_field, por, allowed_kinds[0])
        outcome.row["mapping_rule_id"] = f"{pack_id}.{field_id}.fact/v1"
        outcome.row["mapping_rule_digest"] = _mapping_digest(mapping)
        return outcome
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
            and _period_matches(
                occurrence,
                period_kind,
                por,
                filed_at=filed_at,
                period_select=mapping.period_select,
                opening_bound=opening_bound,
            )
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
        if (
            period_kind == "instant"
            and mapping.period_select == "opening_instant"
            and opening_bound is not None
        ):
            # A.1 (PK04): prefer the instant exactly one day before the
            # fiscal duration's start; with none there, the latest instant
            # strictly before that start. Comparative prior-year instants
            # outside the selected date never enter the conflict check.
            selected = [
                item
                for item in admitted
                if item.context.instant == opening_bound
            ]
            if not selected:
                latest = max(item.context.instant for item in admitted)
                selected = [
                    item for item in admitted if item.context.instant == latest
                ]
            admitted = selected
        distinct = {str(item.parsed_value) for item in admitted}
        precision_extra_ids: set[str] = set()
        if len(distinct) > 1:
            reconciled: tuple[list[Any], set[str]] | None = None
            if mapping.duplicate_policy == "precision_consistent":
                # A.1 (PK05): duplicates that differ only by stated precision
                # reconcile onto the most precise occurrence's value.
                reconciled = _precision_consistent_selection(admitted)
            if reconciled is None:
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
            precise_group, precision_extra_ids = reconciled
            admitted = precise_group
        if period_kind == "instant":
            if mapping.period_select == "cover_instant":
                # A.1: the latest admissible cover instant wins.
                latest = max(item.context.instant for item in admitted)
                admitted = [
                    item for item in admitted if item.context.instant == latest
                ]
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
        if precision_extra_ids:
            # A.1 (PK05): coarser precision-consistent duplicates share the
            # evidence row with the precise occurrence that governs it.
            row["source_occurrence_ids"] = sorted(
                set(row["source_occurrence_ids"]) | precision_extra_ids
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
        elif mapping.period_select in ("cover_instant", "opening_instant"):
            # A.1: the row reports the instant actually used, not period_of_report.
            row["period"] = {
                "kind": "instant",
                "end": representative.context.instant.isoformat(),
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
    payload: list[Any] = [
        mapping.concept,
        mapping.primary_axis,
        list(mapping.other_axes_allowed),
        list(mapping.exclude_member_substrings),
    ]
    if (
        mapping.primary_axes
        or mapping.member_filter
        or mapping.optional_other_members is not None
    ):
        # A.4 hooks enter the digest only when a mapping actually uses them,
        # so every BASE producer's digest (and envelope) is unchanged.
        payload.append(
            {
                "primary_axes": list(mapping.primary_axes),
                "member_filter": mapping.member_filter,
                "optional_other_members": (
                    None
                    if mapping.optional_other_members is None
                    else dict(sorted(mapping.optional_other_members.items()))
                ),
            }
        )
    if mapping.concepts or mapping.member_allowlist:
        # A.1/A.2 (PK03): same rule — the digest moves only for a mapping
        # that actually declares the concept tuple or the member allowlist.
        payload.append(
            {
                "concepts": list(mapping.concepts),
                "member_allowlist": list(mapping.member_allowlist),
            }
        )
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


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
    if catalogue_field["period_kind"] != "instant":
        # A duration-kind dimensioned field (PK04 revenue disaggregation is
        # the first) reports its facts' own duration, like the undimensioned
        # resolver already does; instant fields keep the base instant.
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


def _axes_valued_row(
    *,
    catalogue_field: Mapping[str, Any],
    por: date,
    occurrences: Sequence[Any],
    representative: Any,
    dimensions: Sequence[tuple[str, Any]] = (),
    instant: date | None = None,
) -> tuple[dict[str, Any], Decimal, int | None]:
    """Build one valued A.2 row (consolidated or member) from its facts."""
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
        {item.occurrence_id for item in occurrences}
    )
    if dimensions:
        row["dimensions"] = [
            {"axis": axis, "member": str(member)} for axis, member in dimensions
        ]
    if instant is not None:
        row["period"] = {"kind": "instant", "end": instant.isoformat()}
    elif catalogue_field["period_kind"] != "instant":
        row["period"] = {
            "kind": "duration",
            "start": representative.context.start.isoformat(),
            "end": representative.context.end.isoformat(),
        }
    catalogue_unit = catalogue_field.get("unit")
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
    return row, Decimal(str(representative.parsed_value)), decimals


def _resolve_axes_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: FactMapping,
    ledger: RawFactLedger,
    por: date,
    filed_at: date | None,
    opening_bound: date | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    """A.2: consolidated row first, then one row per optional-axis member.

    Facts carrying any axis outside ``optional_axes`` are ignored. The
    undimensioned fact (when ``consolidated_row`` admits it) is the
    consolidated row; member rows are ordered by the canonical JSON of their
    ``dimensions``. With neither an admitted consolidated row nor a member
    row, exactly one ``missing`` row is emitted — ``disallowed_dimension``
    when facts exist only under other axes, else ``missing_standard_fact``.
    """
    field_id = catalogue_field["field_id"]
    period_kind = catalogue_field["period_kind"]
    allowed_axes = set(mapping.optional_axes)

    undimensioned: list[Any] = []
    members: list[Any] = []
    foreign_axis_seen = False
    concept = mapping.concepts[0]
    for candidate in mapping.concepts:
        concept = candidate
        undimensioned, members, foreign_axis_seen = [], [], False
        for occurrence in ledger.events:
            if occurrence.concept_qname != candidate or occurrence.is_nil:
                continue
            if not _period_matches(
                occurrence,
                period_kind,
                por,
                filed_at=filed_at,
                period_select=mapping.period_select,
                opening_bound=opening_bound,
            ):
                continue
            context = occurrence.context
            axes = {axis for axis, _m in context.explicit_dimensions} | {
                axis for axis, _m in context.typed_dimensions
            }
            if not axes:
                undimensioned.append(occurrence)
            elif axes <= allowed_axes:
                members.append(occurrence)
            else:
                foreign_axis_seen = True
        if undimensioned or members:
            break  # first concept in order that resolves wins

    def stamp(row: dict[str, Any]) -> None:
        row["mapping_rule_id"] = f"{pack_id}.{field_id}.fact/v1"
        row["mapping_rule_digest"] = _mapping_digest(mapping)

    if not undimensioned and not members:
        reason = (
            "disallowed_dimension"
            if foreign_axis_seen
            else f"missing_standard_fact:{concept}"
        )
        outcome = _absence_row(
            catalogue_field, por, "missing", reason, concept=concept
        )
        stamp(outcome.row)
        return _FieldOutcome(
            row=outcome.row,
            value=None,
            decimals=None,
            unit=outcome.unit,
            axis_breakdown=True,
        )

    if undimensioned and mapping.consolidated_row:
        distinct = {str(item.parsed_value) for item in undimensioned}
        if len(distinct) > 1:
            # The FactMapping conflict rule aborts the whole field.
            units = {_unit_measure(item.unit) for item in undimensioned}
            if len(units) == 1:
                _rf9_conflict_limitation(limitations, field_id, undimensioned)
            outcome = _absence_row(
                catalogue_field,
                por,
                "not_evaluable",
                "unit_mismatch" if len(units) > 1 else "missing_dependency",
                concept=concept,
                occurrence_ids=[item.occurrence_id for item in undimensioned],
            )
            stamp(outcome.row)
            return _FieldOutcome(
                row=outcome.row,
                value=None,
                decimals=None,
                unit=outcome.unit,
                axis_breakdown=True,
            )

    groups: dict[tuple[tuple[tuple[str, Any], ...], Any], list[Any]] = {}
    for occurrence in members:
        context = occurrence.context
        key = (
            tuple(sorted(context.explicit_dimensions)),
            tuple(sorted(context.typed_dimensions)),
        )
        groups.setdefault(key, []).append(occurrence)

    emitted: list[dict[str, Any]] = []
    decimals_seen: list[int] = []
    consolidated_value: Decimal | None = None
    member_values: list[Decimal | None] = []
    cover = mapping.period_select == "cover_instant" and period_kind == "instant"

    if undimensioned and mapping.consolidated_row:
        representative = min(undimensioned, key=lambda item: item.occurrence_id)
        instant = representative.context.instant if cover else None
        row, value, decimals = _axes_valued_row(
            catalogue_field=catalogue_field,
            por=por,
            occurrences=undimensioned,
            representative=representative,
            instant=instant,
        )
        stamp(row)
        emitted.append(row)
        consolidated_value = value
        if decimals is not None:
            decimals_seen.append(decimals)

    member_rows: list[tuple[str, dict[str, Any], Decimal | None]] = []
    for (explicit_key, typed_key), occurrences in groups.items():
        distinct = {str(item.parsed_value) for item in occurrences}
        if len(distinct) > 1:
            units = {_unit_measure(item.unit) for item in occurrences}
            row = _base_row(catalogue_field, por)
            row["quality_state"] = "not_evaluable"
            row["non_value_state"] = "not_evaluable"
            row["coverage_state"] = "unmapped"
            row["reason"] = (
                "unit_mismatch" if len(units) > 1 else "missing_dependency"
            )
            row["concept"] = concept
            row["source_occurrence_ids"] = sorted(
                {item.occurrence_id for item in occurrences}
            )
            stamp(row)
            member_rows.append((canonical_json(row["dimensions"]), row, None))
            continue
        representative = min(occurrences, key=lambda item: item.occurrence_id)
        row, value, decimals = _axes_valued_row(
            catalogue_field=catalogue_field,
            por=por,
            occurrences=occurrences,
            representative=representative,
            dimensions=explicit_key,
            instant=representative.context.instant if cover else None,
        )
        stamp(row)
        member_rows.append((canonical_json(row["dimensions"]), row, value))
        if decimals is not None:
            decimals_seen.append(decimals)

    member_rows.sort(key=lambda item: canonical_json([item[0], item[1]["concept"]]))
    for _key, row, value in member_rows:
        emitted.append(row)
        member_values.append(value)

    if not emitted:
        # consolidated_row=False suppressed the only admitted facts.
        reason = (
            "disallowed_dimension"
            if foreign_axis_seen and not undimensioned
            else f"missing_standard_fact:{concept}"
        )
        outcome = _absence_row(
            catalogue_field, por, "missing", reason, concept=concept
        )
        stamp(outcome.row)
        return _FieldOutcome(
            row=outcome.row,
            value=None,
            decimals=None,
            unit=outcome.unit,
            axis_breakdown=True,
        )

    total: Decimal | None = consolidated_value
    if total is None and member_values and all(
        item is not None for item in member_values
    ):
        total = sum(member_values, Decimal("0"))
    return _FieldOutcome(
        row=emitted[0],
        value=total,
        decimals=min(decimals_seen) if decimals_seen else None,
        unit=emitted[0]["unit"],
        extra_rows=tuple(emitted[1:]),
        consolidated_value=consolidated_value,
        member_values=tuple(member_values),
        axis_breakdown=True,
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
        if not unit_consistent and mapping.operand_unit is not None:
            # Declared derived unit (fold ruling R-FOLD-F1): identical
            # operands in the mapping's declared unit yield the field unit.
            unit_consistent = (
                operand_unit is not None
                and operand_unit in _unit_equivalents(mapping.operand_unit)
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
    except FormulaAbsence as absence:
        # Additive hook (module end): a producer formula declares a typed
        # absence whose reason is a catalogue code of its own pack.
        return not_evaluable(absence.reason)
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
        ledger: RawFactLedger | None = None,
        por: date | None = None,
        *,
        pack_id: str | None = None,
        limitations: list[str] | None = None,
    ) -> None:
        self._outcomes = outcomes
        self._pack_input = pack_input
        self._foreign_cache = foreign_cache
        # A.4 (PK03): the ledger + primary period a ``core:`` operand probes.
        self._ledger = ledger
        self._por = por
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

    def outcome(self, name: str) -> _FieldOutcome | None:
        """The own-pack field outcome behind an operand, A.4/A.5 access."""
        if not self.own(name):
            return None
        return self._outcomes.get(name)

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
        if name == _CORE_REVENUE_OPERAND:
            # A.4 (PK03): a core-catalogue operand resolves through the same
            # core-alias mapping the revenue field uses, probed undimensioned
            # over the ledger (no row is minted for it).
            if self._ledger is None or self._por is None:
                return None, None, None
            value = probe_core_fact(
                FactMapping(concepts=CORE_REVENUE_CONCEPTS),
                self._ledger,
                self._por,
            )
            return value, None, None
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
    check_rules: Mapping[str, CheckRule] | None = None,
    limitation_sink: list[str] | None = None,
    pack_id: str = "",
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
    rule_tolerance: Decimal | None = None

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
            if len(spec.addends) == 1 and spec.addends[0] == spec.total:
                # A.4 catalogue shape (antidilutive_table_total_vs_rows): the
                # consolidated row of an optional-axis field is the TOTAL and
                # its member rows are the ADDENDS.
                field = spec.addends[0]
                gate = not_applicable_gate(names)
                if gate is not None:
                    statuses.append("not_applicable")
                    reasons.append(gate)
                    continue
                outcome = resolver.outcome(field)
                if outcome is None or not outcome.axis_breakdown:
                    raise SpecialistPackError(
                        f"check {check_id} lists {field!r} as its only operand"
                        " but the field carries no optional-axis breakdown"
                    )
                operand_decimals.append(outcome.decimals)
                if (
                    outcome.consolidated_value is None
                    or not outcome.member_values
                    or any(item is None for item in outcome.member_values)
                ):
                    statuses.append("not_evaluable")
                    reasons.append("missing_dependency")
                    continue
                tolerance = _identity_tolerance([outcome.decimals])
                addends = sum(outcome.member_values, Decimal("0"))
                statuses.append(
                    "pass"
                    if abs(outcome.consolidated_value - addends) <= tolerance
                    else "fail"
                )
                reasons.append(None)
                continue
            if len(spec.addends) == 1 and resolver.own(spec.addends[0]):
                grouped = resolver.outcome(spec.addends[0])
                if grouped is not None and grouped.group_breakdown:
                    # A.5 (PK04): the addend field is a multi-axis grouped
                    # emission; evaluate the identity per (axis, group).
                    status, reason = _evaluate_axis_group_sum_identity(
                        spec,
                        grouped,
                        resolver,
                        operand_decimals,
                        limitation_sink=limitation_sink,
                        pack_id=pack_id,
                    )
                    statuses.append(status)
                    reasons.append(reason)
                    continue
            identity(names, len(spec.addends))
        elif isinstance(spec, WeightedSumIdentity):
            # A.3 (PK05): Σ weight_i × row value_i over EVERY row of the
            # addend field vs the total row; weights have no row slot.
            own_operands.extend(
                name
                for name in (spec.addends, spec.total)
                if resolver.own(name)
            )
            gate = not_applicable_gate((spec.addends, spec.total))
            if gate is not None:
                statuses.append("not_applicable")
                reasons.append(gate)
                continue
            outcome = resolver.outcome(spec.addends)
            total_value, total_decimals, total_unit = resolver.resolve(
                spec.total
            )
            operand_decimals.append(total_decimals)
            rows: tuple[Mapping[str, Any], ...] = ()
            addend_decimals: int | None = None
            if outcome is not None:
                rows = (outcome.row, *outcome.extra_rows)
                addend_decimals = outcome.decimals
                operand_decimals.append(addend_decimals)
            weights = tuple(spec.weights) or (
                outcome.calculation_weights if outcome is not None else ()
            )
            if (
                outcome is None
                or not rows
                or len(weights) != len(rows)
                or any(
                    row.get("quality_state") != "valued"
                    or row.get("value") is None
                    for row in rows
                )
                or total_value is None
            ):
                statuses.append("not_evaluable")
                reasons.append("missing_dependency")
                _weighted_negative_limitation(
                    spec, rows, weights, limitation_sink, pack_id=pack_id
                )
                continue
            units = {row.get("unit") for row in rows}
            units.discard(None)
            if total_unit is not None:
                units.add(total_unit)
            if len(units) > 1:
                statuses.append("not_evaluable")
                reasons.append("unit_mismatch")
                continue
            tolerance = _identity_tolerance(
                [
                    item
                    for item in (addend_decimals, total_decimals)
                    if item is not None
                ]
            )
            weighted = sum(
                (
                    weight * Decimal(str(row["value"]))
                    for weight, row in zip(weights, rows)
                ),
                Decimal("0"),
            )
            statuses.append(
                "pass" if abs(weighted - total_value) <= tolerance else "fail"
            )
            reasons.append(None)
            _weighted_negative_limitation(
                spec, rows, weights, limitation_sink, pack_id=pack_id
            )
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
                if spec.implied_limitation_template is not None:
                    _append_implied_rollforward_limitation(
                        spec, names, resolved, limitation_sink
                    )
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
        elif isinstance(spec, ReconcileToConsolidated):
            # A.4 (PK03): parts + eliminations vs the consolidated value; the
            # elimination operand may name a concept-filtered row subset and
            # an absent elimination is never an implied zero. The evaluator
            # (module end) owns the semantics; this branch only dispatches.
            own_operands.extend(
                name
                for name in (
                    *spec.parts,
                    *spec.eliminations,
                    spec.consolidated,
                )
                if resolver.outcome(name) is not None
            )
            status, reason = _evaluate_reconcile_to_consolidated(
                spec,
                resolver,
                limitation_sink=limitation_sink,
                pack_id=pack_id,
            )
            statuses.append(status)
            reasons.append(reason)
            rule_tolerance = spec.tolerance
            continue
        elif isinstance(spec, Reconcile):
            names = [*spec.parts, spec.consolidated]
            own_operands.extend(name for name in names if resolver.own(name))
            identity(names, len(spec.parts))
        elif isinstance(spec, CrossStatement):
            if spec.rule:
                if spec.left or spec.right:
                    raise SpecialistPackError(
                        f"check {check_id} declares both a rule and left/right"
                        " operands"
                    )
                rules = check_rules or {}
                if spec.rule not in rules:
                    raise SpecialistPackError(
                        f"check {check_id} cites unknown rule {spec.rule!r}"
                    )
                rule = rules[spec.rule]
                names = tuple(spec.operands)
                if not names:
                    raise SpecialistPackError(
                        f"check {check_id} cites rule {spec.rule!r} with no"
                        " operands"
                    )
                own_operands.extend(name for name in names if resolver.own(name))
                gate = not_applicable_gate(names)
                if gate is not None:
                    statuses.append("not_applicable")
                    reasons.append(gate)
                    continue
                operands: dict[str, RuleOperand] = {}
                for name in names:
                    value, decimals, unit = resolver.resolve(name)
                    outcome = resolver.outcome(name)
                    if outcome is None:
                        operand_decimals.append(decimals)
                        operands[name] = RuleOperand(
                            field_id=name,
                            value=value,
                            decimals=decimals,
                            unit=unit,
                            period=None,
                            rows=(),
                        )
                        continue
                    operand_decimals.append(decimals)
                    operands[name] = RuleOperand(
                        field_id=name,
                        value=value,
                        decimals=decimals,
                        unit=unit,
                        period=outcome.row.get("period"),
                        rows=(outcome.row, *outcome.extra_rows),
                    )
                if any(
                    operand.value is None
                    and not any(
                        row.get("quality_state") == "valued"
                        for row in operand.rows
                    )
                    for operand in operands.values()
                ):
                    statuses.append("not_evaluable")
                    reasons.append("missing_dependency")
                    continue
                if rule.same_period_required:
                    periods = {
                        canonical_json(operand.period)
                        for operand in operands.values()
                        if operand.period is not None
                    }
                    if len(periods) > 1:
                        # A.5: differing period bases are never a pass.
                        statuses.append("not_evaluable")
                        reasons.append("unit_mismatch")
                        if (
                            rule.limitation_when_period_mismatch is not None
                            and limitation_sink is not None
                        ):
                            limitation_sink.append(
                                rule.limitation_when_period_mismatch
                            )
                        continue
                try:
                    verdict = rule.fn(operands)
                except ZeroDivisionError:
                    statuses.append("not_evaluable")
                    reasons.append("division_by_zero")
                    continue
                if verdict.status not in ("pass", "fail", "not_evaluable"):
                    raise SpecialistPackError(
                        f"rule {spec.rule!r} returned unknown status"
                        f" {verdict.status!r}"
                    )
                statuses.append(verdict.status)
                reasons.append(
                    verdict.reason if verdict.status != "pass" else None
                )
                if verdict.tolerance is not None:
                    rule_tolerance = verdict.tolerance
                continue
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
    if rule_tolerance is not None:
        tolerance = rule_tolerance
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
    filed_at_text = str(primary_manifest.get("filing_date") or "")
    filed_at = date.fromisoformat(filed_at_text[:10]) if filed_at_text else None
    issuer_class = detectors.issuer_class_for_sic(pack_input.issuer_sic)
    state, reason = evaluate_applicability(
        producer,
        pack_input,
        primary_form,
        ledger,
        catalogue=catalogue,
        limitations=framework_limitations,
    )
    runtime = NarrativeRuntime(
        pack_input=pack_input, primary=primary, primary_form=primary_form, por=por
    )

    fields_rows: list[dict[str, Any]] = []
    checks_rows: list[dict[str, Any]] = []
    outcomes: dict[str, _FieldOutcome | None] = {}
    # A.3: the fact half of a FactOrFormulaMapping, kept for the fallback.
    fact_only_outcomes: dict[str, _FieldOutcome] = {}
    # B.3-style conditional limitations emitted when a formula branch won.
    branch_limitations: list[str] = []
    # A.5/B.3 conditional limitations emitted when a rule check trips a gate.
    rule_limitations: list[str] = []
    # Additive hook: limitations minted by a registered producer check fn.
    extra_check_limitations: list[str] = []
    # A.4 conditional limitations emitted while resolving grouped mappings.
    mapping_limitations: list[str] = []
    # A.1/A.4 lazily computed inputs: the opening-instant bound and the
    # definition-linkbase axis groups of the primary package.
    lazily: dict[str, Any] = {}

    def _opening_bound() -> date | None:
        if "opening_bound" not in lazily:
            lazily["opening_bound"] = _primary_duration_opening_bound(ledger, por)
        return lazily["opening_bound"]

    def _axis_groups() -> Mapping[str, tuple[tuple[str, ...], ...]]:
        if "axis_groups" not in lazily:
            from . import definition_linkbase  # deferred: keeps imports flat

            lazily["axis_groups"] = definition_linkbase.parse_axis_member_groups(
                _package_definition_linkbase_bytes(primary)
            )
        return lazily["axis_groups"]

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
            form_reason = _field_form_reason(producer, field_id, primary_form)
            blocked_dependency = _field_condition_blocked(
                producer, field_id, outcomes
            )
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
            elif form_reason is not None:
                # Narrative hook: a field that resolves only on some forms.
                outcomes[field_id] = _absence_row(
                    catalogue_field, por, "not_applicable", form_reason
                )
            elif blocked_dependency is not None:
                # Narrative hook: a field gated on another field's value.
                gated = _absence_row(
                    catalogue_field, por, "not_evaluable", "missing_dependency"
                )
                gated.row["dependency_field_ids"] = [blocked_dependency]
                outcomes[field_id] = gated
            elif isinstance(mapping, TextSpanMapping) and mapping.pattern:
                outcomes[field_id] = _resolve_text_span_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    producer=producer,
                    runtime=runtime,
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
            elif isinstance(mapping, CalculationChildrenMapping):
                # A.2 (PK05): rows declared by the issuer's own calculation
                # arcs under the mapping's parent concept.
                outcomes[field_id] = _resolve_calculation_children_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    ledger=ledger,
                    por=por,
                    primary=primary,
                    limitation_sink=mapping_limitations,
                )
            elif isinstance(mapping, DimensionedFactMapping):
                if mapping.primary_axes or mapping.member_filter:
                    # A.4: grouped multi-axis emission over the definition
                    # linkbase's member groups.
                    outcomes[field_id] = _resolve_grouped_dimensioned_fact_mapping(
                        pack_id=pack_id,
                        catalogue_field=catalogue_field,
                        mapping=mapping,
                        ledger=ledger,
                        por=por,
                        axis_groups=_axis_groups(),
                        limitation_sink=mapping_limitations,
                    )
                elif mapping.concepts or mapping.member_allowlist:
                    # A.1/A.2 (PK03): concept tuple and/or primary-axis member
                    # allowlist emission, no definition-linkbase filter.
                    outcomes[field_id] = _resolve_allowlist_dimensioned_fact_mapping(
                        pack_id=pack_id,
                        catalogue_field=catalogue_field,
                        mapping=mapping,
                        ledger=ledger,
                        por=por,
                        limitations=mapping_limitations,
                    )
                else:
                    outcomes[field_id] = _resolve_dimensioned_fact_mapping(
                        pack_id=pack_id,
                        catalogue_field=catalogue_field,
                        mapping=mapping,
                        ledger=ledger,
                        por=por,
                        catalogue=catalogue,
                        limitations=framework_limitations,
                    )
            elif isinstance(mapping, TypedDimensionedFactMapping):
                outcomes[field_id] = _resolve_typed_dimensioned_fact_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    ledger=ledger,
                    por=por,
                    catalogue=catalogue,
                    limitations=framework_limitations,
                )
            elif isinstance(mapping, NilStateMapping):
                # A.1 (PK08): the enum row read from a concept's nil state.
                outcomes[field_id] = _resolve_nil_state_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    ledger=ledger,
                    por=por,
                )
            elif isinstance(mapping, AxisMemberMapping):
                # A.2 (PK08): the axis_member row over the primary period.
                outcomes[field_id] = _resolve_axis_member_mapping(
                    pack_id=pack_id,
                    catalogue_field=catalogue_field,
                    mapping=mapping,
                    ledger=ledger,
                    por=por,
                )
            elif isinstance(mapping, FactMapping):
                if mapping.optional_axes:
                    outcomes[field_id] = _resolve_axes_fact_mapping(
                        pack_id=pack_id,
                        catalogue_field=catalogue_field,
                        mapping=mapping,
                        ledger=ledger,
                        por=por,
                        filed_at=filed_at,
                        opening_bound=(
                            _opening_bound()
                            if mapping.period_select == "opening_instant"
                            else None
                        ),
                        limitations=framework_limitations,
                    )
                else:
                    outcomes[field_id] = _resolve_fact_mapping(
                        pack_id=pack_id,
                        catalogue_field=catalogue_field,
                        mapping=mapping,
                        ledger=ledger,
                        por=por,
                        extension_prefixes=producer.extension_prefixes,
                        filed_at=filed_at,
                        opening_bound=(
                            _opening_bound()
                            if mapping.period_select == "opening_instant"
                            else None
                        ),
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
                    filed_at=filed_at,
                    opening_bound=(
                        _opening_bound()
                        if mapping.fact.period_select == "opening_instant"
                        else None
                    ),
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
        # B.2 conditional limitations: a mapping-declared note that fires when
        # its field resolved to a missing row (e.g. no axis members tagged).
        for field_id, mapping in producer.field_mappings.items():
            if not isinstance(mapping, FactMapping):
                continue
            if mapping.limitation_when_absent is None:
                continue
            outcome = outcomes.get(field_id)
            if (
                outcome is not None
                and outcome.row["quality_state"] == "missing"
            ):
                branch_limitations.append(mapping.limitation_when_absent)

        specs_by_check: dict[str, list[CheckSpec]] = {}
        for check_spec in producer.checks:
            specs_by_check.setdefault(check_spec.check_id, []).append(check_spec)
        resolver = _OperandResolver(
            outcomes,
            pack_input,
            foreign_cache={},
            ledger=ledger,
            por=por,
            pack_id=pack_id,
            limitations=framework_limitations,
        )
        for catalogue_check in catalogue["checks"]:
            check_id = catalogue_check["check_id"]
            # Additive hook (module end): a registered producer check fn owns
            # this catalogue check row outright when one exists.
            produced = _produce_extra_check(
                pack_id, pack_input, ledger, outcomes, catalogue_check
            )
            if produced is not None:
                row, produced_limitations = produced
                checks_rows.append(row)
                extra_check_limitations.extend(produced_limitations)
                continue
            specs = specs_by_check.get(check_id)
            if not specs:
                raise SpecialistPackError(
                    f"{pack_id} producer declares no check: {check_id}"
                )
            checks_rows.append(
                _evaluate_check_with_hooks(
                    catalogue_check,
                    specs,
                    resolver,
                    producer,
                    runtime,
                    outcomes,
                    check_rules=producer.check_rules,
                    limitation_sink=rule_limitations,
                    pack_id=pack_id,
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
    # Additive hook (module end): producer-declared receipt lines ride last.
    receipts.extend(_extra_receipts_for(pack_id, pack_input, ledger))
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
    narrative_limitations: list[str] = []
    if state == "applicable" and producer.hooks is not None:
        hook_rows = {
            field_id: outcome.row
            for field_id, outcome in outcomes.items()
            if outcome is not None
        }
        if producer.hooks.extra_receipts is not None:
            receipts.extend(producer.hooks.extra_receipts(runtime, hook_rows))
        if producer.hooks.extra_limitations is not None:
            narrative_limitations.extend(
                producer.hooks.extra_limitations(runtime, hook_rows)
            )

    limitations = list(
        dict.fromkeys(
            (
                DISPLAY_ONLY_LIMITATION,
                *producer.limitations,
                *branch_limitations,
                *framework_limitations,
                *mapping_limitations,
                *rule_limitations,
                *extra_check_limitations,
                *narrative_limitations,
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


# --------------------------------------------------------------------------
# Narrative extensions (A.3; added at the end of the module so parallel pack
# lanes merge mechanically). Everything below is inert for a producer that
# declares no hooks: earlier packs' envelopes stay byte-identical.
# --------------------------------------------------------------------------


class NarrativeRuntime:
    """One production's shared narrative context, built lazily and cached.

    ``narrative_text()`` parses the primary document exactly once per
    production and only when a narrative hook actually asks for it.
    """

    def __init__(
        self,
        *,
        pack_input: PackInput,
        primary: Any,
        primary_form: str | None,
        por: date,
    ) -> None:
        self.pack_input = pack_input
        self.primary = primary
        self.primary_form = primary_form
        self.por = por
        manifest: Mapping[str, Any] = primary.manifest
        self.accession = str(manifest.get("accession") or "")
        self._narrative_text: Any = None

    def narrative_text(self) -> Any:
        from . import narrative  # deferred: narrative imports this module

        if self._narrative_text is None:
            self._narrative_text = narrative.primary_document_text(self.primary)
        return self._narrative_text


@dataclass(frozen=True)
class NarrativeHooks:
    """Producer-declared narrative extensions (first user: PK09).

    ``section_overrides``: field_id -> (forms, ``SectionSpec``); the override
    spec replaces the mapping's section when the primary form is in ``forms``.
    ``field_form_exclusions``: field_id -> (excluded forms, reason code).
    ``conditional_fields``: field_id -> (dependency field_id, guard over the
    dependency's ``text_value``); the guard failing yields a non-valued
    ``missing_dependency`` row naming the dependency.
    ``text_value_overrides``: field_id -> callable(narrative_text, section
    span, match) -> (text_value, char span) for fields whose text_value is not
    the containing sentence.
    ``check_evaluator``: callable(catalogue_check, rows, runtime) -> check row
    or ``None`` to fall back to the stock numeric evaluation.
    ``extra_receipts`` / ``extra_limitations``: callable(runtime, rows) ->
    extra envelope lines, appended after the framework's own.
    """

    section_overrides: Mapping[str, Any] = field(default_factory=dict)
    field_form_exclusions: Mapping[str, tuple[frozenset[str], str]] = field(
        default_factory=dict
    )
    conditional_fields: Mapping[str, Any] = field(default_factory=dict)
    text_value_overrides: Mapping[str, Any] = field(default_factory=dict)
    check_evaluator: Callable[..., Any] | None = None
    extra_receipts: Callable[..., Any] | None = None
    extra_limitations: Callable[..., Any] | None = None


def _field_form_reason(
    producer: PackProducer, field_id: str, primary_form: str | None
) -> str | None:
    if producer.hooks is None:
        return None
    entry = producer.hooks.field_form_exclusions.get(field_id)
    if entry is None:
        return None
    forms, reason = entry
    return reason if primary_form in forms else None


def _field_condition_blocked(
    producer: PackProducer,
    field_id: str,
    outcomes: Mapping[str, "_FieldOutcome | None"],
) -> str | None:
    if producer.hooks is None:
        return None
    entry = producer.hooks.conditional_fields.get(field_id)
    if entry is None:
        return None
    dependency, guard = entry
    outcome = outcomes.get(dependency)
    if outcome is None:
        return dependency
    text_value = outcome.row.get("text_value")
    if text_value is not None and guard(str(text_value)):
        return None
    return dependency


def _text_span_digest(mapping: TextSpanMapping) -> str:
    section = mapping.section
    payload = canonical_json(
        [
            mapping.pattern,
            None
            if section is None
            else [section.heading, list(section.end_headings), section.skip_toc],
        ]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _catalogue_enum_literals(
    catalogue_field: Mapping[str, Any],
) -> frozenset[str] | None:
    """A.4: literals the catalogue field's own name declares, when it does.

    Catalogue enum lists live inside the field ``name`` (e.g. ``(disclosed |
    not_disclosed)``); a name without such a list binds no literals and the
    A.4 check is skipped for that field.
    """
    declared: set[str] | None = None
    for match in re.finditer(
        r"\(([^()]*\|[^()]*)\)", str(catalogue_field.get("name") or "")
    ):
        if declared is None:
            declared = set()
        declared.update(item.strip() for item in match.group(1).split("|"))
    return frozenset(declared) if declared else None


def _absent_text(value: str | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _raw_span(nt: Any, start: int, end: int, accession: str) -> dict[str, Any]:
    """A raw-document ``source_span`` object for the char range [start, end)."""
    last = end - 1
    return {
        "accession": accession,
        "document_id": nt.document_id,
        "start_offset": nt.offsets[start],
        "end_offset": nt.offsets[last] + len(nt.text[last].encode("utf-8")),
    }


def _resolve_text_span_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: TextSpanMapping,
    producer: PackProducer,
    runtime: NarrativeRuntime,
) -> _FieldOutcome:
    """A.3: resolve one ``TextSpanMapping`` against the narrative text."""
    from . import narrative

    nt = runtime.narrative_text()
    field_id = catalogue_field["field_id"]
    por = runtime.por
    section_spec = mapping.section
    if producer.hooks is not None:
        entry = producer.hooks.section_overrides.get(field_id)
        if entry is not None and runtime.primary_form in entry[0]:
            section_spec = entry[1]

    def absence(quality_state: str, reason: str) -> _FieldOutcome:
        outcome = _absence_row(catalogue_field, por, quality_state, reason)
        outcome.row["evidence_kind"] = "text_span"
        outcome.row["required_evidence_kind"] = "text_span"
        outcome.row["mapping_rule_id"] = f"{pack_id}.{field_id}.text_span/v1"
        outcome.row["mapping_rule_digest"] = _text_span_digest(mapping)
        return outcome

    if section_spec is None:
        section_span = (0, len(nt.text))
    else:
        section_span = narrative.locate_section(nt, section_spec)
        if section_span is None:
            return absence("not_evaluable", "governing_section_not_supplied")
    lo, hi = section_span
    match = re.compile(mapping.pattern).search(nt.text, lo, hi)
    declared = _catalogue_enum_literals(catalogue_field)
    if match is None:
        if (
            mapping.kind == "enum"
            and isinstance(mapping.absent_value, str)
            and declared is not None
            and mapping.absent_value not in declared
        ):
            # A.4: the absent literal itself is not in the catalogue.
            return absence("missing", "narrative_span_not_located")
        if mapping.absent_value is None:
            return absence("missing", "narrative_span_not_located")
        # A valued absence asserted over the whole section (or whole text).
        row = _base_row(catalogue_field, por)
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["quality_state"] = "valued"
        row["non_value_state"] = None
        row["coverage_state"] = "source_trace_complete"
        row["reason"] = None
        row["text_value"] = _absent_text(mapping.absent_value)
        row["source_span"] = _raw_span(nt, lo, hi, runtime.accession)
        row["mapping_rule_id"] = f"{pack_id}.{field_id}.text_span/v1"
        row["mapping_rule_digest"] = _text_span_digest(mapping)
        return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])

    span = (match.start(), match.end())
    text_value: str | None = None
    override = None
    if producer.hooks is not None:
        override = producer.hooks.text_value_overrides.get(field_id)
    if override is not None:
        text_value, span = override(nt, section_span, match)
    elif mapping.kind == "enum":
        literal = next(
            (
                mapping.enum_map[group]
                for group, matched in match.groupdict().items()
                if matched is not None and group in mapping.enum_map
            ),
            None,
        )
        if literal is None or (
            declared is not None and literal not in declared
        ):
            # A.4: never invent a literal the catalogue does not declare.
            return absence("missing", "narrative_span_not_located")
        text_value = literal
    elif mapping.kind == "boolean":
        text_value = "true"
    else:
        span = narrative.sentence_span(
            nt.text, match.start(), match.end(), section_span
        )
        text_value = nt.text[span[0] : span[1]].strip()
        if len(text_value) > mapping.max_chars:
            text_value = text_value[: mapping.max_chars]
    row = _base_row(catalogue_field, por)
    row["evidence_kind"] = "text_span"
    row["required_evidence_kind"] = "text_span"
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["text_value"] = text_value
    row["source_span"] = _raw_span(nt, span[0], span[1], runtime.accession)
    row["mapping_rule_id"] = f"{pack_id}.{field_id}.text_span/v1"
    row["mapping_rule_digest"] = _text_span_digest(mapping)
    return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])


def _evaluate_check_with_hooks(
    catalogue_check: Mapping[str, Any],
    specs: Sequence[CheckSpec],
    resolver: _OperandResolver,
    producer: PackProducer,
    runtime: NarrativeRuntime,
    outcomes: Mapping[str, "_FieldOutcome | None"],
    check_rules: Mapping[str, CheckRule] | None = None,
    limitation_sink: list[str] | None = None,
    pack_id: str = "",
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    if producer.hooks is not None and producer.hooks.check_evaluator is not None:
        rows = {
            field_id: outcome.row
            for field_id, outcome in outcomes.items()
            if outcome is not None
        }
        row = producer.hooks.check_evaluator(catalogue_check, rows, runtime)
        if row is not None:
            return row
    return _evaluate_check(
        catalogue_check,
        specs,
        resolver,
        check_rules=check_rules,
        limitation_sink=limitation_sink,
        pack_id=pack_id,
        catalogue=catalogue,
        limitations=limitations,
    )


# --------------------------------------------------------------------------
# A.1/A.2/A.4/A.5 additions (PK04 lane; strictly additive, merged after the
# historical module body so parallel pack lanes stay mechanically mergeable)
# --------------------------------------------------------------------------


def _primary_duration_opening_bound(ledger: RawFactLedger, por: date) -> date | None:
    """A.1: the day before the primary fiscal duration's start, or ``None``.

    The primary fiscal duration is the longest duration context ending at
    ``period_of_report`` inside the annual window — the same basis the
    duration-field selection uses, so the opening instant and the fiscal-year
    facts share one period identity.
    """
    starts: list[date] = []
    for occurrence in ledger.events:
        context = occurrence.context
        if context.start is None or context.end is None or context.end != por:
            continue
        days = (context.end - context.start).days + 1
        if 0 < days <= MAX_DURATION_DAYS:
            starts.append(context.start)
    if not starts:
        return None
    return min(starts) - timedelta(days=1)


def _dimension_qname_matches(ledger_qname: str, declared_qname: str) -> bool:
    """Bind one dimension qname across the ledger and the definition linkbase.

    The definition linkbase spells qnames with taxonomy prefixes resolved
    from ``loc`` hrefs; the raw ledger canonicalizes only the namespaces in
    its closed policy to prefixes and keeps every other namespace in Clark
    form. Exact equality covers the policy-canonicalized spellings; for a
    Clark-form ledger qname the local name is the binding available without
    the schema's namespace declarations (the grouped sum identity, A.5,
    guards a cross-namespace local-name collision as a failed group).
    """
    if ledger_qname == declared_qname:
        return True
    if ledger_qname.startswith("{") and "}" in ledger_qname:
        ledger_local = ledger_qname.rsplit("}", 1)[1]
        declared_local = (
            declared_qname.rsplit(":", 1)[-1]
            if ":" in declared_qname
            else declared_qname
        )
        return ledger_local == declared_local
    return False


def _typed_member_iso_date(member: str) -> date | None:
    """Extract the ISO date a typed-dimension member carries, if any.

    The converter serializes a typed member as its source token, e.g.
    ``<us-gaap:...Axis.domain>2025-09-28</us-gaap:...Axis.domain>``; the
    typed value is the element text. Members that carry no parseable date
    are not date-typed and cannot be ordered by ``select``.
    """
    opening = member.find(">")
    closing = member.rfind("<")
    if opening == -1 or closing <= opening:
        return None
    try:
        return date.fromisoformat(member[opening + 1 : closing].strip()[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class TypedDimensionedFactMapping:
    """A.2: one row from a fact carrying exactly one typed dimension.

    ``select="earliest_on_or_after_period_of_report"`` picks the fact whose
    typed value (an ISO date) is the earliest date at or after the primary
    package's ``period_of_report``; the emitted row reports the typed axis
    and the typed value string as its single dimension.
    """

    concept: str
    typed_axis: str
    select: str = "earliest_on_or_after_period_of_report"


def _typed_dimensioned_mapping_digest(mapping: TypedDimensionedFactMapping) -> str:
    payload = canonical_json([mapping.concept, mapping.typed_axis, mapping.select])
    return sha256(payload.encode("utf-8")).hexdigest()


def _resolve_typed_dimensioned_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: TypedDimensionedFactMapping,
    ledger: RawFactLedger,
    por: date,
    catalogue: Mapping[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    """A.2: resolve one typed-dimensioned fact selection (one row at most)."""
    if mapping.select != "earliest_on_or_after_period_of_report":
        raise SpecialistPackError(f"unknown typed select: {mapping.select!r}")
    field_id = catalogue_field["field_id"]
    period_kind = catalogue_field["period_kind"]
    rule_id = f"{pack_id}.{field_id}.typed_dimensioned_fact/v1"
    digest = _typed_dimensioned_mapping_digest(mapping)

    candidates: list[tuple[date, Any]] = []
    for occurrence in ledger.events:
        if occurrence.concept_qname != mapping.concept or occurrence.is_nil:
            continue
        if not _period_matches(occurrence, period_kind, por):
            continue
        context = occurrence.context
        if context.explicit_dimensions or len(context.typed_dimensions) != 1:
            continue
        axis, member = context.typed_dimensions[0]
        if not _dimension_qname_matches(str(axis), mapping.typed_axis):
            continue
        typed_date = _typed_member_iso_date(str(member))
        if typed_date is None or typed_date < por:
            continue  # only typed values on or after period_of_report compete
        candidates.append((typed_date, occurrence))

    if not candidates:
        absence = _absence_row(
            catalogue_field,
            por,
            "missing",
            f"missing_standard_fact:{mapping.concept}",
            concept=mapping.concept,
            catalogue=catalogue,
            limitations=limitations,
        )
        absence.row["mapping_rule_id"] = rule_id
        absence.row["mapping_rule_digest"] = digest
        return absence

    earliest = min(typed_date for typed_date, _occurrence in candidates)
    selected = [
        occurrence
        for typed_date, occurrence in candidates
        if typed_date == earliest
    ]
    distinct = {str(item.parsed_value) for item in selected}
    if len(distinct) > 1:
        units = {_unit_measure(item.unit) for item in selected}
        if len(units) == 1:
            _rf9_conflict_limitation(limitations, field_id, selected)
        conflict = _absence_row(
            catalogue_field,
            por,
            "not_evaluable",
            "unit_mismatch" if len(units) > 1 else "missing_dependency",
            concept=mapping.concept,
            occurrence_ids=[item.occurrence_id for item in selected],
            catalogue=catalogue,
            limitations=limitations,
        )
        conflict.row["mapping_rule_id"] = rule_id
        conflict.row["mapping_rule_digest"] = digest
        return conflict

    representative = min(selected, key=lambda item: item.occurrence_id)
    row = _base_row(catalogue_field, por)
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
        {item.occurrence_id for item in selected}
    )
    row["dimensions"] = [
        {"axis": mapping.typed_axis, "member": earliest.isoformat()}
    ]
    row["mapping_rule_id"] = rule_id
    row["mapping_rule_digest"] = digest
    catalogue_unit = catalogue_field.get("unit")
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
    if period_kind == "instant":
        row["period"] = {
            "kind": "instant",
            "end": representative.context.instant.isoformat(),
        }
    else:
        row["period"] = {
            "kind": "duration",
            "start": representative.context.start.isoformat(),
            "end": representative.context.end.isoformat(),
        }
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


def _package_definition_linkbase_bytes(primary: Any) -> bytes | None:
    """The primary package's stored ``_def.xml`` member bytes, or ``None``.

    Located through the package's member listing only (A33): the name is
    matched by its ``_def.xml`` suffix, never by issuer identity.
    """
    names = sorted(
        str(item.get("name") or "")
        for item in primary.manifest.get("members") or []
        if isinstance(item, dict)
        and item.get("state") == "stored"
        and str(item.get("name") or "").endswith("_def.xml")
    )
    if not names:
        return None
    return primary.members.get(names[0])


@dataclass(frozen=True)
class _AxisGroupBreakdown:
    """A.5 evidence: one axis's member groups and each member's row value.

    ``groups`` are the definition-linkbase groups for the axis (or, in the
    fallback, one synthetic group of every emitted member); ``member_values``
    keys are the group member qnames (fallback: the emitted member strings)
    with ``None`` for a member whose row did not resolve to a value.
    """

    axis: str
    groups: tuple[tuple[str, ...], ...]
    member_values: Mapping[str, Decimal | None]


def _resolve_grouped_dimensioned_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: DimensionedFactMapping,
    ledger: RawFactLedger,
    por: date,
    axis_groups: Mapping[str, tuple[tuple[str, ...], ...]],
    limitation_sink: list[str] | None,
) -> _FieldOutcome:
    """A.4: emit member rows per axis, partitioned by definition groups.

    Axes are emitted in declared order; within an axis one row per member the
    definition linkbase lists for it, in canonical order. Members carried by
    facts but absent from every group are not emitted (counted in a
    limitation); an axis with no group falls back to every admitted member in
    canonical order with its own limitation. The outcome exposes the
    per-(axis, group) breakdown for the A.5 grouped sum identity; its
    ``value`` stays ``None`` because a multi-axis member sum is not a
    meaningful operand.

    A.1 (PK03): a mapping that declares ``concepts`` runs the whole per-axis
    emission once per concept in declared order (concept-major, then axis,
    then member), each emitted row's ``concept`` naming the concept it came
    from; a concept with no admitted fact contributes no rows, and one
    breakdown is exposed per (concept, axis) pass — an empty pass keeps its
    incomplete breakdown so a grouped identity never mistakes it for complete.
    With no ``concepts`` declared the single-concept BASE behaviour is
    unchanged byte for byte.
    """
    field_id = catalogue_field["field_id"]
    period_kind = catalogue_field["period_kind"]
    axes = tuple(mapping.primary_axes) or (mapping.primary_axis,)
    concepts = mapping.concepts or (mapping.concept,)
    optional_members = dict(mapping.optional_other_members or {})
    excluded_lower = tuple(
        substring.lower() for substring in mapping.exclude_member_substrings
    )
    rule_id = f"{pack_id}.{field_id}.dimensioned_fact/v1"
    digest = _dimensioned_mapping_digest(mapping)

    all_candidates: list[Any] = []
    emitted: list[dict[str, Any]] = []
    decimals_seen: list[int] = []
    breakdowns: list[_AxisGroupBreakdown] = []
    admitted_ids: set[str] = set()

    for concept in concepts:
        period_candidates = [
            occurrence
            for occurrence in ledger.events
            if occurrence.concept_qname == concept
            and not occurrence.is_nil
            and _period_matches(occurrence, period_kind, por)
        ]
        all_candidates.extend(period_candidates)

        for axis in axes:
            by_member: dict[str, list[Any]] = {}
            for occurrence in period_candidates:
                context = occurrence.context
                if context.typed_dimensions:
                    continue  # typed axes are never admitted on this mapping kind
                explicit = dict(context.explicit_dimensions)
                ledger_axis = next(
                    (
                        candidate
                        for candidate in explicit
                        if _dimension_qname_matches(candidate, axis)
                    ),
                    None,
                )
                if ledger_axis is None:
                    continue
                admissible = True
                for other_axis, other_member in explicit.items():
                    if other_axis == ledger_axis:
                        continue
                    admitted_member = next(
                        (
                            member
                            for declared, member in optional_members.items()
                            if _dimension_qname_matches(other_axis, declared)
                        ),
                        None,
                    )
                    if (
                        admitted_member is None
                        or str(other_member) != admitted_member
                    ):
                        admissible = False
                        break
                if not admissible:
                    continue
                member = str(explicit[ledger_axis])
                if any(
                    substring in _local_name(member).lower()
                    for substring in excluded_lower
                ):
                    continue
                by_member.setdefault(member, []).append(occurrence)
                admitted_ids.add(occurrence.occurrence_id)

            groups = axis_groups.get(axis, ()) if axis_groups else ()
            member_values: dict[str, Decimal | None] = {}
            if groups:
                union = sorted({m for group in groups for m in group})
                outside = 0
                ledger_by_member_key: dict[str, list[str]] = {}
                for ledger_member in sorted(by_member):
                    target = next(
                        (
                            group_member
                            for group_member in union
                            if _dimension_qname_matches(
                                ledger_member, group_member
                            )
                        ),
                        None,
                    )
                    if target is None:
                        outside += 1
                    else:
                        # Two ledger members may bind one group member through
                        # the local-name fallback; both rows emit, and the
                        # LAST value is the one the group sum sees (a
                        # collision then surfaces as a failed group, never as
                        # silent double counting).
                        ledger_by_member_key.setdefault(target, []).append(
                            ledger_member
                        )
                if outside and limitation_sink is not None:
                    limitation_sink.append(
                        f"{field_id}: {outside} {axis} member(s) outside every"
                        " definition group not emitted"
                    )
                for group_member in union:
                    for ledger_member in sorted(
                        ledger_by_member_key.get(group_member, ())
                    ):
                        outcome = _dimensioned_row(
                            catalogue_field=catalogue_field,
                            por=por,
                            mapping=mapping,
                            occurrences=by_member[ledger_member],
                            limitations=limitation_sink,
                        )
                        outcome.row["mapping_rule_id"] = rule_id
                        outcome.row["mapping_rule_digest"] = digest
                        if mapping.concepts:
                            # A.1: the row names the concept it came from.
                            outcome.row["concept"] = concept
                            outcome.row["taxonomy"] = (
                                "extension"
                                if concept.startswith("{")
                                else concept.split(":", 1)[0]
                            )
                        emitted.append(outcome.row)
                        member_values[group_member] = outcome.value
                        if outcome.decimals is not None:
                            decimals_seen.append(outcome.decimals)
                groups_used = groups
            else:
                if limitation_sink is not None:
                    limitation_sink.append(
                        f"{field_id}: {axis} has no definition group; member"
                        " rows unpartitioned"
                    )
                for ledger_member in sorted(by_member):
                    outcome = _dimensioned_row(
                        catalogue_field=catalogue_field,
                        por=por,
                        mapping=mapping,
                        occurrences=by_member[ledger_member],
                        limitations=limitation_sink,
                    )
                    outcome.row["mapping_rule_id"] = rule_id
                    outcome.row["mapping_rule_digest"] = digest
                    if mapping.concepts:
                        outcome.row["concept"] = concept
                        outcome.row["taxonomy"] = (
                            "extension"
                            if concept.startswith("{")
                            else concept.split(":", 1)[0]
                        )
                    emitted.append(outcome.row)
                    member_values[ledger_member] = outcome.value
                    if outcome.decimals is not None:
                        decimals_seen.append(outcome.decimals)
                groups_used = (tuple(sorted(by_member)),) if by_member else ()
            breakdowns.append(
                _AxisGroupBreakdown(
                    axis=axis, groups=groups_used, member_values=dict(member_values)
                )
            )

    if not emitted:
        foreign_axis_seen = False
        for occurrence in all_candidates:
            if occurrence.occurrence_id in admitted_ids:
                continue
            context = occurrence.context
            if context.explicit_dimensions or context.typed_dimensions:
                foreign_axis_seen = True
                break
        absence = _absence_row(
            catalogue_field,
            por,
            "missing",
            (
                "disallowed_dimension"
                if foreign_axis_seen
                else f"missing_standard_fact:{concepts[0]}"
            ),
            concept=concepts[0],
        )
        absence.row["mapping_rule_id"] = rule_id
        absence.row["mapping_rule_digest"] = digest
        return absence

    return _FieldOutcome(
        row=emitted[0],
        value=None,
        decimals=min(decimals_seen) if decimals_seen else None,
        unit=emitted[0]["unit"],
        extra_rows=tuple(emitted[1:]),
        group_breakdown=tuple(breakdowns),
    )


def _evaluate_axis_group_sum_identity(
    spec: SumIdentity,
    addend: _FieldOutcome,
    resolver: _OperandResolver,
    operand_decimals: list[int | None],
    *,
    limitation_sink: list[str] | None,
    pack_id: str,
) -> tuple[str, str | None]:
    """A.5: one grouped sum identity, evaluated per (axis, group).

    A group is complete when every one of its members has a valued row. The
    identity passes only when every declared axis has at least one complete
    group and every complete group sums to the total within tolerance; any
    complete group beyond tolerance fails it. The group census rides in the
    limitations sink as ``<pack>.<check>: groups <complete>/<total>``.
    """
    total_value, total_decimals, total_unit = resolver.resolve(spec.total)
    operand_decimals.append(addend.decimals)
    if total_decimals is not None:
        operand_decimals.append(total_decimals)

    complete_sums: list[Decimal] = []
    total_groups = 0
    complete_groups = 0
    every_axis_complete = True
    for breakdown in addend.group_breakdown:
        axis_complete = False
        for group in breakdown.groups:
            total_groups += 1
            values = [breakdown.member_values.get(member) for member in group]
            if group and all(value is not None for value in values):
                complete_groups += 1
                axis_complete = True
                complete_sums.append(sum(values, Decimal("0")))
        if not axis_complete:
            every_axis_complete = False

    if limitation_sink is not None and total_groups:
        limitation_sink.append(
            f"{pack_id.lower()}.{spec.check_id}:"
            f" groups {complete_groups}/{total_groups}"
        )

    if total_value is None:
        return "not_evaluable", "missing_dependency"
    if every_axis_complete and total_unit is not None and addend.unit not in (
        None,
        total_unit,
    ):
        return "not_evaluable", "unit_mismatch"
    if not every_axis_complete:
        return "not_evaluable", "missing_dependency"
    tolerance = _identity_tolerance(
        [
            item
            for item in (addend.decimals, total_decimals)
            if item is not None
        ]
    )
    for group_sum in complete_sums:
        if abs(group_sum - total_value) > tolerance:
            return "fail", None
    return "pass", None


def _solve_rollforward_missing(
    spec: Rollforward,
    missing: str,
    resolved: Sequence[tuple[Decimal | None, int | None, str | None]],
) -> Decimal | None:
    """Solve the rollforward identity for its single unvalued operand."""
    names = [spec.opening, *spec.additions, *spec.reductions, spec.closing]
    values = {name: value for name, (value, _, _unit) in zip(names, resolved)}
    if any(
        values.get(name) is None for name in dict.fromkeys(names) if name != missing
    ):
        return None
    opening = values[spec.opening]
    closing = values[spec.closing]
    additions = sum(
        (values[name] for name in spec.additions if name != missing), Decimal("0")
    )
    reductions = sum(
        (values[name] for name in spec.reductions if name != missing), Decimal("0")
    )
    if missing == spec.opening:
        return closing - additions + reductions
    if missing == spec.closing:
        return opening + additions - reductions
    if missing in spec.additions:
        # ``additions`` excludes the missing operand, so the implied member
        # is the identity's total addition minus the known ones (PK05: the
        # first rollforward with several additions; a single-member side
        # keeps the exact BASE number).
        return closing - opening + reductions - additions
    if missing in spec.reductions:
        # Symmetrically for a missing reduction among several known ones.
        return opening + additions - closing - reductions
    return None  # pragma: no cover - missing is one of the four slots


def _append_implied_rollforward_limitation(
    spec: Rollforward,
    names: Sequence[str],
    resolved: Sequence[tuple[Decimal | None, int | None, str | None]],
    limitation_sink: list[str] | None,
) -> None:
    """A.6: name the implied value the producer refused to derive (R-K3)."""
    if limitation_sink is None:
        return
    missing = [
        name for name, (value, _, _unit) in zip(names, resolved) if value is None
    ]
    if len(missing) != 1:
        return
    valued_units = {
        unit for value, _, unit in resolved if value is not None and unit
    }
    if len(valued_units) > 1:
        return  # never imply a figure across clashing units
    implied = _solve_rollforward_missing(spec, missing[0], resolved)
    if implied is None:
        return
    limitation_sink.append(
        str(spec.implied_limitation_template).format(
            field_id=missing[0], implied=decimal_text(implied)
        )
    )


__all__ = [
    "CalculationChildrenMapping",
    "CheckRule",
    "CheckRuleFn",
    "CheckSpec",
    "CORE_REVENUE_CONCEPTS",
    "CrossStatement",
    "DISPLAY_ONLY_LIMITATION",
    "DimensionedFactMapping",
    "FactMapping",
    "FactOrFormulaMapping",
    "FieldMapping",
    "FormulaAbsence",
    "FormulaMapping",
    "MAX_DURATION_DAYS",
    "NarrativeHooks",
    "NarrativeRuntime",
    "PackInput",
    "PackProducer",
    "PackSpec",
    "Presence",
    "Reconcile",
    "ReconcileToConsolidated",
    "Rollforward",
    "RuleOperand",
    "RuleOutcome",
    "SCHEMA",
    "SpecialistPackError",
    "SumIdentity",
    "TableMapping",
    "TextSpanMapping",
    "TypedDimensionedFactMapping",
    "WeightedSumIdentity",
    "UNIT_EQUIVALENTS",
    "evaluate_applicability",
    "formula_difference",
    "formula_ratio",
    "formula_sum",
    "primary_period",
    "probe_core_fact",
    "produce_pack_result",
    "register_extra_check",
    "register_extra_receipts",
]


# ---------------------------------------------------------------------------
# Additive producer hooks (PK12 lane; later lanes append below this banner)
#
# Everything above this banner keeps the BASE frame's behaviour: a producer
# that registers nothing produces byte-identical envelopes to BASE, so the
# specialist-pack lanes running in parallel merge mechanically. Each hook is
# strictly opt-in per pack id and pure (no wall clock, deterministic output).
# ---------------------------------------------------------------------------


class FormulaAbsence(Exception):
    """A producer formula's typed absence; ``reason`` is a catalogue code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


ExtraReceiptsFn = Callable[[Any, RawFactLedger | None], Sequence[str]]
# Returns ``(check_row, limitations)`` for a catalogue check this producer
# owns, or ``None`` to fall through to the producer's declared CheckSpecs.
ExtraCheckFn = Callable[
    [Any, RawFactLedger | None, Mapping[str, Any]],
    "tuple[dict[str, Any], Sequence[str]] | None",
]

_EXTRA_RECEIPTS_FNS: dict[str, ExtraReceiptsFn] = {}
_EXTRA_CHECK_FNS: dict[str, ExtraCheckFn] = {}


def register_extra_receipts(pack_id: str, fn: ExtraReceiptsFn) -> None:
    """Declare extra receipt lines for one pack's envelopes.

    The fn receives ``(pack_input, ledger)``, is evaluated once per produced
    envelope in both applicability branches, and its lines are appended after
    the framework's own ``issuer_class`` receipt (deduplicated, receipt order
    preserved).
    """
    if pack_id not in contract.PACK_IDS:
        raise SpecialistPackError(f"unknown pack id: {pack_id}")
    _EXTRA_RECEIPTS_FNS[pack_id] = fn


def register_extra_check(pack_id: str, fn: ExtraCheckFn) -> None:
    """Let one producer own its catalogue check rows outright.

    The fn receives ``(pack_input, ledger, outcomes, catalogue_check)`` —
    ``outcomes`` maps field_id to the framework's resolved field outcome —
    and returns ``(check_row, limitations)`` or ``None`` to fall through to
    the declared ``CheckSpec`` shapes. Consulted only in the applicable
    branch; the returned row must satisfy the same envelope contract the
    framework's own check rows satisfy (catalogue kind/operands, member
    reason codes, evidence fields of this result).
    """
    if pack_id not in contract.PACK_IDS:
        raise SpecialistPackError(f"unknown pack id: {pack_id}")
    _EXTRA_CHECK_FNS[pack_id] = fn


def _extra_receipts_for(
    pack_id: str,
    pack_input: Any,
    ledger: RawFactLedger | None,
) -> list[str]:
    fn = _EXTRA_RECEIPTS_FNS.get(pack_id)
    if fn is None:
        return []
    return list(dict.fromkeys(fn(pack_input, ledger)))


def _produce_extra_check(
    pack_id: str,
    pack_input: Any,
    ledger: RawFactLedger | None,
    outcomes: Mapping[str, Any],
    catalogue_check: Mapping[str, Any],
) -> tuple[dict[str, Any], Sequence[str]] | None:
    fn = _EXTRA_CHECK_FNS.get(pack_id)
    if fn is None:
        return None
    return fn(pack_input, ledger, outcomes, catalogue_check)


def primary_period(pack_input: Any, forms: frozenset[str]) -> date:
    """Primary filing period of a pack input under the producer's own forms."""
    primary, _matched = _select_primary(pack_input.packages, forms)
    por_text = str(primary.manifest.get("period_of_report") or "")
    if not por_text:
        raise SpecialistPackError("primary package carries no period_of_report")
    return date.fromisoformat(por_text[:10])


def probe_core_fact(
    mapping: FactMapping,
    ledger: RawFactLedger,
    por: date,
    *,
    period_kind: str = "duration",
) -> Decimal | None:
    """Resolve one alias list under the field-mapping admission laws, no row.

    For producer-declared extra rules (e.g. a pre-revenue applicability test)
    that consume a core-catalogue alias without minting a field row. Returns
    the resolved value, or ``None`` when the aliases do not resolve to a
    valued admitted fact; the intermediate row is discarded, never emitted.
    """
    catalogue_field = {
        "field_id": "core_probe",
        "name": "core probe",
        "type": "decimal",
        "unit": None,
        "period_kind": period_kind,
    }
    outcome = _resolve_fact_mapping(
        pack_id="PK00",
        catalogue_field=catalogue_field,
        mapping=mapping,
        ledger=ledger,
        por=por,
        extension_prefixes={},
    )
    return outcome.value


# ---------------------------------------------------------------------------
# A.1/A.2/A.4 additions (PK03 lane; strictly additive, appended after the
# PK12 banner so parallel pack lanes stay mechanically mergeable)
# ---------------------------------------------------------------------------

# A.4: the shared core-catalogue revenue alias tuple, priority order 10/20/30
# (``SalesRevenueNet`` is a 2009–2017 taxonomy element; ``Revenues`` is the
# pre-606/other-basis residual). Copied from the core mapping PK04's
# ``revenue`` field consumes, so the ``core:revenue`` check operand and any
# revenue-basis row filter bind the same aliases without coupling producers.
CORE_REVENUE_CONCEPTS = (
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:SalesRevenueNet",
    "us-gaap:Revenues",
)
_CORE_REVENUE_OPERAND = "core:revenue"


@dataclass(frozen=True)
class ReconcileToConsolidated:
    """A.4: ``sum(parts rows) + sum(elimination rows)`` vs the consolidated.

    Row-level, signed ledger values, Decimal only. ``eliminations`` names
    fields whose valued rows join the parts side; ``elimination_concepts``
    (optional) admits only rows whose ``concept`` is listed — the revenue
    basis of a mixed revenue/profit eliminations field. An eliminations
    operand with NO valued admitted row is never an implied zero: the check
    passes only when the parts alone tie within ``tolerance`` (emitting the
    ``<pack>.<check>: eliminations absent, exact tie`` limitation), and is
    ``not_evaluable`` / ``missing_dependency`` otherwise. A consolidated
    operand that does not resolve (``core:revenue`` probes the ledger) or an
    empty parts side is equally ``not_evaluable`` / ``missing_dependency``.
    """

    check_id: str
    parts: tuple[str, ...]
    eliminations: tuple[str, ...]
    consolidated: str
    tolerance: Decimal
    elimination_concepts: tuple[str, ...] | None = None


_KIND_BY_SPEC["ReconcileToConsolidated"] = "reconcile_to_consolidated"


def _valued_row_decimal(row: Mapping[str, Any]) -> Decimal:
    """A valued row's signed value as a Decimal (rows store decimal text)."""
    return Decimal(str(row["value"]))


def _evaluate_reconcile_to_consolidated(
    spec: ReconcileToConsolidated,
    resolver: _OperandResolver,
    *,
    limitation_sink: list[str] | None,
    pack_id: str,
) -> tuple[str, str | None]:
    """A.4: evaluate one parts + eliminations vs consolidated reconciliation."""
    names = (*spec.parts, *spec.eliminations, spec.consolidated)
    for name in names:
        outcome = resolver.outcome(name)
        if outcome is not None and outcome.row.get("quality_state") == (
            "not_applicable"
        ):
            return "not_applicable", outcome.row.get("reason")
    parts_rows: list[Mapping[str, Any]] = []
    for name in spec.parts:
        outcome = resolver.outcome(name)
        if outcome is None:
            continue
        parts_rows.extend(
            row
            for row in (outcome.row, *outcome.extra_rows)
            if row.get("quality_state") == "valued"
        )
    elimination_rows: list[Mapping[str, Any]] = []
    for name in spec.eliminations:
        outcome = resolver.outcome(name)
        if outcome is None:
            continue
        elimination_rows.extend(
            row
            for row in (outcome.row, *outcome.extra_rows)
            if row.get("quality_state") == "valued"
            and (
                spec.elimination_concepts is None
                or row.get("concept") in spec.elimination_concepts
            )
        )
    consolidated, _decimals, _unit = resolver.resolve(spec.consolidated)
    if consolidated is None or not parts_rows:
        return "not_evaluable", "missing_dependency"
    parts_sum = sum(
        (_valued_row_decimal(row) for row in parts_rows), Decimal("0")
    )
    if elimination_rows:
        eliminations_sum = sum(
            (_valued_row_decimal(row) for row in elimination_rows), Decimal("0")
        )
        if abs(parts_sum + eliminations_sum - consolidated) <= spec.tolerance:
            return "pass", None
        return "fail", None
    # The eliminations field carries no valued admitted row: never zero.
    if abs(parts_sum - consolidated) <= spec.tolerance:
        if limitation_sink is not None:
            limitation_sink.append(
                f"{pack_id.lower()}.{spec.check_id}:"
                " eliminations absent, exact tie"
            )
        return "pass", None
    return "not_evaluable", "missing_dependency"


def _admitted_allowlist_occurrence(
    occurrence: Any, mapping: DimensionedFactMapping, declared_member: str
) -> bool:
    """A.2: the fact carries the primary axis, no other dimension, and its
    primary-axis member binds the declared allowlist qname."""
    context = occurrence.context
    if context.typed_dimensions:
        return False
    explicit = dict(context.explicit_dimensions)
    ledger_axis = next(
        (
            axis
            for axis in explicit
            if _dimension_qname_matches(axis, mapping.primary_axis)
        ),
        None,
    )
    if ledger_axis is None:
        return False
    if any(axis != ledger_axis for axis in explicit):
        return False  # facts must carry no other explicit dimension
    return _dimension_qname_matches(str(explicit[ledger_axis]), declared_member)


def _resolve_allowlist_dimensioned_fact_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: DimensionedFactMapping,
    ledger: RawFactLedger,
    por: date,
    limitations: list[str] | None = None,
) -> _FieldOutcome:
    """A.1/A.2: concept tuple + primary-axis member allowlist emission.

    Rows are emitted per concept in declared order, then per the allowlist's
    declared member order — never canonical. A fact is admitted only when it
    carries the primary axis and no other explicit or typed dimension and its
    member binds an allowlisted qname; facts under other members are ignored
    silently (they belong to other fields). Zero rows over all concepts emit
    one ``missing`` row for the first concept; same-member value conflicts
    follow the FactMapping conflict rule. The outcome's ``value`` is the sum
    of every valued row when all rows are valued, else ``None``.
    """
    field_id = catalogue_field["field_id"]
    period_kind = catalogue_field["period_kind"]
    concepts = mapping.concepts or (mapping.concept,)
    rule_id = f"{pack_id}.{field_id}.dimensioned_fact/v1"
    digest = _dimensioned_mapping_digest(mapping)

    emitted: list[dict[str, Any]] = []
    decimals_seen: list[int] = []
    for concept in concepts:
        candidates = [
            occurrence
            for occurrence in ledger.events
            if occurrence.concept_qname == concept
            and not occurrence.is_nil
            and _period_matches(occurrence, period_kind, por)
        ]
        for declared_member in mapping.member_allowlist:
            occurrences = [
                occurrence
                for occurrence in candidates
                if _admitted_allowlist_occurrence(
                    occurrence, mapping, declared_member
                )
            ]
            if not occurrences:
                continue
            distinct = {str(item.parsed_value) for item in occurrences}
            if len(distinct) > 1:
                # Same admitted member, different values: the FactMapping
                # conflict rule, kept row-level.
                units = {_unit_measure(item.unit) for item in occurrences}
                if len(units) == 1:
                    # R-F9: same unit, different values — name the conflict.
                    _rf9_conflict_limitation(limitations, field_id, occurrences)
                row = _base_row(catalogue_field, por)
                row["quality_state"] = "not_evaluable"
                row["non_value_state"] = "not_evaluable"
                row["coverage_state"] = "unmapped"
                row["reason"] = (
                    "unit_mismatch" if len(units) > 1 else "missing_dependency"
                )
                row["concept"] = concept
                row["taxonomy"] = (
                    "extension"
                    if concept.startswith("{")
                    else concept.split(":", 1)[0]
                )
                row["source_occurrence_ids"] = sorted(
                    {item.occurrence_id for item in occurrences}
                )
                row["mapping_rule_id"] = rule_id
                row["mapping_rule_digest"] = digest
                emitted.append(row)
                continue
            representative = min(
                occurrences, key=lambda item: item.occurrence_id
            )
            row, value, decimals = _axes_valued_row(
                catalogue_field=catalogue_field,
                por=por,
                occurrences=occurrences,
                representative=representative,
                dimensions=sorted(representative.context.explicit_dimensions),
            )
            row["mapping_rule_id"] = rule_id
            row["mapping_rule_digest"] = digest
            emitted.append(row)
            if decimals is not None:
                decimals_seen.append(decimals)

    if not emitted:
        absence = _absence_row(
            catalogue_field,
            por,
            "missing",
            f"missing_standard_fact:{concepts[0]}",
            concept=concepts[0],
        )
        absence.row["mapping_rule_id"] = rule_id
        absence.row["mapping_rule_digest"] = digest
        return absence

    values = [
        None if row["value"] is None else Decimal(str(row["value"]))
        for row in emitted
    ]
    total = (
        sum((value for value in values if value is not None), Decimal("0"))
        if all(value is not None for value in values)
        else None
    )
    return _FieldOutcome(
        row=emitted[0],
        value=total,
        decimals=min(decimals_seen) if decimals_seen else None,
        unit=emitted[0]["unit"],
        extra_rows=tuple(emitted[1:]),
    )


# ---------------------------------------------------------------------------
# A.1/A.2/A.3 additions (PK05 lane; strictly additive, appended after the
# PK03 banner so parallel pack lanes stay mechanically mergeable)
# ---------------------------------------------------------------------------

from decimal import InvalidOperation, ROUND_HALF_UP  # noqa: E402


def _decimals_rank(decimals: str | None) -> tuple[int, int]:
    """Precision rank of an XBRL ``decimals`` attribute (A.1).

    ``INF`` is the most precise rank; otherwise a larger integer is more
    precise (``-6`` beats ``-8``). An absent ``decimals`` ranks least — the
    source plane stated no precision, so the occurrence cannot out-rank one
    that did. Tuple keys keep the ordering free of floats.
    """
    if decimals == "INF":
        return (1, 0)
    try:
        return (0, int(decimals))
    except (TypeError, ValueError):
        return (0, -(10**9))


def _precision_consistent_selection(
    occurrences: Sequence[Any],
) -> tuple[list[Any], set[str]] | None:
    """A.1: reconcile precision-consistent duplicate undimensioned facts.

    Returns ``(precise_group, extra_ids)`` — the occurrences carrying the
    most precise ``decimals`` (whose ``parsed_value`` must agree) and the
    occurrence ids of every coarser duplicate that reconciles onto it — or
    ``None`` when the duplicates are not precision-consistent (the BASE A.6
    conflict outcome then governs). A coarser occurrence reconciles when its
    value equals the precise value rounded (ROUND_HALF_UP, Decimal) to the
    coarser occurrence's own ``decimals``; a coarser occurrence that stated
    no ``decimals`` must equal the precise value exactly.
    """
    ordered = sorted(
        occurrences,
        key=lambda item: (
            _decimals_rank(item.decimals),
            item.occurrence_id or "",
        ),
    )
    top = _decimals_rank(ordered[-1].decimals)
    precise = [
        item for item in ordered if _decimals_rank(item.decimals) == top
    ]
    precise_values = {str(item.parsed_value) for item in precise}
    if len(precise_values) != 1:
        return None
    try:
        precise_value = Decimal(next(iter(precise_values)))
    except InvalidOperation:
        return None  # a non-decimal duplicate is never precision-reconcilable
    precise_ids = {item.occurrence_id for item in precise}
    extra_ids: set[str] = set()
    for item in ordered:
        if item.occurrence_id in precise_ids:
            continue
        try:
            coarse_value = Decimal(str(item.parsed_value))
        except InvalidOperation:
            return None
        rounded = precise_value
        if item.decimals is not None and item.decimals != "INF":
            try:
                rounded = precise_value.quantize(
                    Decimal(1).scaleb(-int(item.decimals)),
                    rounding=ROUND_HALF_UP,
                )
            except (InvalidOperation, ValueError):
                return None
        if coarse_value != rounded:
            return None
        extra_ids.add(item.occurrence_id)
    return precise, extra_ids


@dataclass(frozen=True)
class CalculationChildrenMapping:
    """A.2 (PK05): rows declared by the issuer's own calculation arcs.

    One row per child the chosen calculation role declares under
    ``parent_concept``, in arc order; the child qname is the row ``concept``
    and its prefix the row ``taxonomy``. Each row resolves an undimensioned
    fact for the primary duration under the A.1 precision-consistent
    duplicate policy; a child without one is a typed ``missing`` row —
    ``missing_standard_fact:<qname>`` for a ``us-gaap:`` child,
    ``extension_concept_unaliased:<prefix>`` for any other prefix. An
    extension child WITH a fact is a VALUED row: the issuer's own
    calculation arc aliases it as a component of the reconciliation (the
    reading recorded in :mod:`calculation_linkbase`). No qualifying role
    yields one ``missing`` row for the parent concept plus the mapping's
    ``no calculation role`` limitation.
    """

    field_id: str
    parent_concept: str
    child_prefix: str


def _calculation_children_mapping_digest(
    mapping: CalculationChildrenMapping,
) -> str:
    payload = canonical_json(
        [mapping.parent_concept, mapping.child_prefix]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _calculation_child_row(
    *,
    catalogue_field: Mapping[str, Any],
    por: date,
    child_qname: str,
    occurrences: Sequence[Any],
    representative: Any,
) -> tuple[dict[str, Any], Decimal, int | None]:
    """Build one valued calculation-child row from its admitted facts."""
    row = _base_row(catalogue_field, por)
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["concept"] = child_qname
    row["taxonomy"] = (
        child_qname.split(":", 1)[0] if ":" in child_qname else child_qname
    )
    row["source_occurrence_ids"] = sorted(
        {item.occurrence_id for item in occurrences}
    )
    row["period"] = {
        "kind": "duration",
        "start": representative.context.start.isoformat(),
        "end": representative.context.end.isoformat(),
    }
    catalogue_unit = catalogue_field.get("unit")
    row["unit"] = (
        catalogue_unit
        if catalogue_unit is not None
        else _unit_measure(representative.unit)
    )
    row["value"] = decimal_text(Decimal(str(representative.parsed_value)))
    decimals: int | None = None
    if (
        representative.decimals is not None
        and representative.decimals != "INF"
    ):
        decimals = int(representative.decimals)
    return row, Decimal(str(representative.parsed_value)), decimals


def _resolve_calculation_children_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: CalculationChildrenMapping,
    ledger: RawFactLedger,
    por: date,
    primary: Any,
    limitation_sink: list[str] | None,
) -> _FieldOutcome:
    """A.2: emit one row per calculation child of the parent concept.

    The chosen role's arcs fix the row set and order (module docstring of
    :mod:`calculation_linkbase` records the extension-child reading); the
    outcome exposes the arc weights in row order for the A.3 weighted sum
    identity and keeps ``value`` ``None`` — an unweighted member sum is not
    a meaningful operand for a reconciliation whose arcs carry −1 weights.
    """
    from . import calculation_linkbase  # deferred: keeps imports flat

    field_id = catalogue_field["field_id"]
    period_kind = catalogue_field["period_kind"]
    rule_id = f"{pack_id.lower()}.{field_id}.calculation_children/v1"
    digest = _calculation_children_mapping_digest(mapping)

    children = calculation_linkbase.parse_parent_children(
        calculation_linkbase.calculation_linkbase_bytes(primary),
        mapping.parent_concept,
        mapping.child_prefix,
    )
    if not children:
        if limitation_sink is not None:
            limitation_sink.append(
                f"{pack_id.lower()}.{field_id}: no calculation role declares"
                " reconciliation children"
            )
        absence = _absence_row(
            catalogue_field,
            por,
            "missing",
            f"missing_standard_fact:{mapping.parent_concept}",
            concept=mapping.parent_concept,
        )
        absence.row["mapping_rule_id"] = rule_id
        absence.row["mapping_rule_digest"] = digest
        return absence

    emitted: list[dict[str, Any]] = []
    weights: list[Decimal] = []
    decimals_seen: list[int] = []
    for child_qname, weight in children:
        weights.append(weight)
        candidates = [
            occurrence
            for occurrence in ledger.events
            if not occurrence.is_nil
            and _dimension_qname_matches(
                occurrence.concept_qname, child_qname
            )
            and _period_matches(occurrence, period_kind, por)
            and not (
                occurrence.context.explicit_dimensions
                or occurrence.context.typed_dimensions
            )
        ]
        if not candidates:
            reason = (
                f"missing_standard_fact:{child_qname}"
                if child_qname.startswith("us-gaap:")
                else (
                    "extension_concept_unaliased:"
                    + (
                        child_qname.split(":", 1)[0]
                        if ":" in child_qname
                        else child_qname
                    )
                )
            )
            absence = _absence_row(
                catalogue_field, por, "missing", reason, concept=child_qname
            )
            absence.row["taxonomy"] = (
                child_qname.split(":", 1)[0]
                if ":" in child_qname
                else child_qname
            )
            absence.row["mapping_rule_id"] = rule_id
            absence.row["mapping_rule_digest"] = digest
            emitted.append(absence.row)
            continue
        longest = max(_duration_days(item) for item in candidates)
        candidates = [
            item for item in candidates if _duration_days(item) == longest
        ]
        distinct = {str(item.parsed_value) for item in candidates}
        selected_ids: set[str] = set()
        if len(distinct) > 1:
            reconciled = _precision_consistent_selection(candidates)
            if reconciled is None:
                units = {_unit_measure(item.unit) for item in candidates}
                if len(units) == 1:
                    _rf9_conflict_limitation(limitation_sink, field_id, candidates)
                conflict = _absence_row(
                    catalogue_field,
                    por,
                    "not_evaluable",
                    "unit_mismatch" if len(units) > 1 else "missing_dependency",
                    concept=child_qname,
                    occurrence_ids=[
                        item.occurrence_id for item in candidates
                    ],
                )
                conflict.row["taxonomy"] = (
                    child_qname.split(":", 1)[0]
                    if ":" in child_qname
                    else child_qname
                )
                conflict.row["mapping_rule_id"] = rule_id
                conflict.row["mapping_rule_digest"] = digest
                emitted.append(conflict.row)
                continue
            candidates, selected_ids = reconciled[0], reconciled[1]
        representative = min(
            candidates, key=lambda item: item.occurrence_id or ""
        )
        row, _value, decimals = _calculation_child_row(
            catalogue_field=catalogue_field,
            por=por,
            child_qname=child_qname,
            occurrences=candidates,
            representative=representative,
        )
        if selected_ids:
            row["source_occurrence_ids"] = sorted(
                set(row["source_occurrence_ids"]) | selected_ids
            )
        row["mapping_rule_id"] = rule_id
        row["mapping_rule_digest"] = digest
        emitted.append(row)
        if decimals is not None:
            decimals_seen.append(decimals)

    return _FieldOutcome(
        row=emitted[0],
        value=None,
        decimals=min(decimals_seen) if decimals_seen else None,
        unit=emitted[0]["unit"],
        extra_rows=tuple(emitted[1:]),
        calculation_weights=tuple(weights),
    )


@dataclass(frozen=True)
class WeightedSumIdentity:
    """A.3 (PK05): Σ weight_i × row value_i vs the total field's value.

    ``weights`` aligns with the addend field's rows in emission order; an
    empty tuple takes the weights the addend field's calculation-children
    outcome exposed (the issuer's own arc weights). Any addend row or the
    total not valued keeps the check ``not_evaluable`` / ``missing_dependency``
    (R-K3). A negative weight names its line in the check's limitation —
    weights have no row slot, so the reader cannot see the sign in the rows.
    """

    check_id: str
    addends: str
    total: str
    weights: tuple[Decimal, ...] = ()


_KIND_BY_SPEC["WeightedSumIdentity"] = "sum_identity"


def _weighted_negative_limitation(
    spec: WeightedSumIdentity,
    rows: Sequence[Mapping[str, Any]],
    weights: Sequence[Decimal],
    limitation_sink: list[str] | None,
    *,
    pack_id: str,
) -> None:
    """A.3: name the negative-weight lines once the weights are known."""
    if limitation_sink is None or len(weights) != len(rows):
        return
    negative = [
        str(row.get("concept"))
        for weight, row in zip(weights, rows)
        if weight < 0
    ]
    if negative:
        limitation_sink.append(
            f"{pack_id.lower()}.{spec.check_id}: negative-weight lines"
            f" {','.join(negative)}"
        )


# ---------------------------------------------------------------------------
# A.1/A.2 additions (PK08 lane; strictly additive, appended after the PK05
# banner so parallel pack lanes stay mechanically mergeable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NilStateMapping:
    """A.1 (PK08): an enum row read from a numeric concept's nil/valued state.

    Resolves the undimensioned occurrence of ``concept`` at the instant
    ``period_of_report`` — the one admission the plain :class:`FactMapping`
    laws refuse, because they skip nil occurrences by design. An ``is_nil``
    occurrence yields ``nil_literal``; an occurrence with a parsed value yields
    ``valued_literal``; no occurrence is the typed absence
    ``missing_standard_fact:<qname>``. A literal the catalogue's field name
    does not declare is never invented (A.4 law): the row degrades to a
    non-valued ``missing_dependency`` citing the occurrence ids it refused to
    name (the A.3 ruling for a pack whose catalogue lacks the literal).
    """

    concept: str
    nil_literal: str
    valued_literal: str


def _nil_state_mapping_digest(mapping: NilStateMapping) -> str:
    payload = canonical_json(
        [mapping.concept, mapping.nil_literal, mapping.valued_literal]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _nil_state_stamps(
    row: dict[str, Any], pack_id: str, field_id: str, mapping: NilStateMapping
) -> None:
    row["mapping_rule_id"] = f"{pack_id}.{field_id}.nil_state/v1"
    row["mapping_rule_digest"] = _nil_state_mapping_digest(mapping)


def _resolve_nil_state_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: NilStateMapping,
    ledger: RawFactLedger,
    por: date,
) -> _FieldOutcome:
    """Resolve one A.1 nil-state enum row against the raw ledger."""
    field_id = catalogue_field["field_id"]
    candidates = [
        occurrence
        for occurrence in ledger.events
        if occurrence.concept_qname == mapping.concept
        and occurrence.context.instant is not None
        and occurrence.context.instant == por
        and _dimensions_admitted(occurrence, ())
    ]
    if not candidates:
        outcome = _absence_row(
            catalogue_field,
            por,
            "missing",
            f"missing_standard_fact:{mapping.concept}",
            concept=mapping.concept,
        )
        _nil_state_stamps(outcome.row, pack_id, field_id, mapping)
        return outcome
    nil_occurrences = [item for item in candidates if item.is_nil]
    valued_occurrences = [item for item in candidates if not item.is_nil]
    if nil_occurrences and valued_occurrences:
        # A.6 conflicting facts: the same instant carries both a nil and a
        # valued undimensioned occurrence of the line.
        outcome = _absence_row(
            catalogue_field,
            por,
            "not_evaluable",
            "missing_dependency",
            concept=mapping.concept,
            occurrence_ids=[item.occurrence_id for item in candidates],
        )
        _nil_state_stamps(outcome.row, pack_id, field_id, mapping)
        return outcome
    literal = (
        mapping.nil_literal if nil_occurrences else mapping.valued_literal
    )
    declared = _catalogue_enum_literals(catalogue_field)
    if declared is not None and literal not in declared:
        # A.3: the catalogue does not declare this literal; never invent it.
        outcome = _absence_row(
            catalogue_field,
            por,
            "missing",
            "missing_dependency",
            concept=mapping.concept,
            occurrence_ids=[item.occurrence_id for item in candidates],
        )
        _nil_state_stamps(outcome.row, pack_id, field_id, mapping)
        return outcome
    row = _base_row(catalogue_field, por)
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["text_value"] = literal
    row["concept"] = mapping.concept
    row["taxonomy"] = (
        "extension"
        if mapping.concept.startswith("{")
        else mapping.concept.split(":", 1)[0]
    )
    row["source_occurrence_ids"] = sorted(
        {item.occurrence_id for item in candidates}
    )
    _nil_state_stamps(row, pack_id, field_id, mapping)
    return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])


@dataclass(frozen=True)
class AxisMemberMapping:
    """A.2 (PK08): an ``axis_member`` row listing one axis's primary members.

    The sorted, de-duplicated member qnames carried on ``axis_qname`` by any
    ledger occurrence whose period lies inside the primary period (an instant
    at ``period_of_report`` or a duration ending at it). ``text_value`` is the
    full list joined by ``;`` (the first member leads); ``dimensions`` carries
    every member on the axis; no member at all is the typed absence
    ``missing_standard_fact:<axis_qname>``. The envelope's ``value`` slot stays
    null: ``axis_member`` is a non-numeric row type.
    """

    axis_qname: str


def _axis_member_mapping_digest(mapping: AxisMemberMapping) -> str:
    payload = canonical_json([mapping.axis_qname])
    return sha256(payload.encode("utf-8")).hexdigest()


def _resolve_axis_member_mapping(
    *,
    pack_id: str,
    catalogue_field: Mapping[str, Any],
    mapping: AxisMemberMapping,
    ledger: RawFactLedger,
    por: date,
) -> _FieldOutcome:
    """Resolve one A.2 axis-member row against the raw ledger."""
    field_id = catalogue_field["field_id"]

    def absence(reason: str) -> _FieldOutcome:
        outcome = _absence_row(
            catalogue_field, por, "missing", reason, concept=mapping.axis_qname
        )
        outcome.row["mapping_rule_id"] = f"{pack_id}.{field_id}.axis_member/v1"
        outcome.row["mapping_rule_digest"] = _axis_member_mapping_digest(mapping)
        return outcome

    members: set[str] = set()
    occurrence_ids: set[str] = set()
    for occurrence in ledger.events:
        context = occurrence.context
        in_primary_period = (
            context.instant is not None and context.instant == por
        ) or (
            context.start is not None
            and context.end is not None
            and context.end == por
        )
        if not in_primary_period:
            continue
        for axis, member in context.explicit_dimensions:
            if _dimension_qname_matches(str(axis), mapping.axis_qname):
                members.add(str(member))
                occurrence_ids.add(str(occurrence.occurrence_id))
    if not members:
        return absence(f"missing_standard_fact:{mapping.axis_qname}")
    ordered = sorted(members)
    row = _base_row(catalogue_field, por)
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["text_value"] = ";".join(ordered)
    row["dimensions"] = [
        {"axis": mapping.axis_qname, "member": member} for member in ordered
    ]
    row["concept"] = mapping.axis_qname
    row["taxonomy"] = (
        "extension"
        if mapping.axis_qname.startswith("{")
        else mapping.axis_qname.split(":", 1)[0]
    )
    row["source_occurrence_ids"] = sorted(occurrence_ids)
    row["mapping_rule_id"] = f"{pack_id}.{field_id}.axis_member/v1"
    row["mapping_rule_digest"] = _axis_member_mapping_digest(mapping)
    return _FieldOutcome(row=row, value=None, decimals=None, unit=row["unit"])
