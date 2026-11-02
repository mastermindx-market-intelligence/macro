"""PK04 producer: revenue recognition and contract balances.

Thin by design — every mapping below is a frozen B.2 declaration over the
shared framework in ``base.py``. The core-catalogue alias consumed here
(``revenue``) is copied exactly from
``config/fundamental_forensics/metrics/v1/mappings/core.yaml`` (including the
``SalesRevenueNet`` 2009–2017 window note, which the ordered alias tuple
carries as documentation). Gross contract-liability additions have no frozen
standard us-gaap element and RPO timing exists only as non-numeric iXBRL
duration facts the raw ledger excludes by design, so both are declared
unmapped typed absences, never narrative extractions (R-K4').

One declaration carries a pack-side finalize rule: ``rpo_total`` also admits
a filing that tags the total only on the standard expected-timing start-date
axis as a single aggregate (``Pk04Producer.finalize_result``, the registry
hook PK11 introduced), under the guard documented at that mapping.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Mapping

from .. import specialist_pack_contract as contract
from ..raw_ledger import decimal_text
from .base import (
    CheckRule,
    CrossStatement,
    DimensionedFactMapping,
    FactMapping,
    PackInput,
    PackProducer,
    PackSpec,
    Rollforward,
    RuleOperand,
    RuleOutcome,
    SpecialistPackError,
    SumIdentity,
    TextSpanMapping,
    TypedDimensionedFactMapping,
    _dimensions_admitted,
    _identity_tolerance,
    _mapping_digest,
    _typed_member_iso_date,
    _unit_equivalents,
    _unit_measure,
)

SPEC = PackSpec(
    pack_id="PK04",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="specialist_pack.pk04.applicability/v1",
    applicable_classes=frozenset(
        {"industrial", "software", "insurance", "reit", "utility"}
    ),
    inapplicable_class_reason="bank_interest_not_contract_revenue",
)

PRODUCT_OR_SERVICE_AXIS = "srt:ProductOrServiceAxis"
GEOGRAPHICAL_AXIS = "srt:StatementGeographicalAxis"
RPO_TIMING_AXIS = (
    "us-gaap:RevenueRemainingPerformanceObligationExpectedTimingOf"
    "SatisfactionStartDateAxis"
)
# The standard duration element that marks a numeric RPO fact's context as
# one timing bucket of a ladder rather than the disclosure's total.
RPO_TIMING_PERIOD1_CONCEPT = (
    "us-gaap:RevenueRemainingPerformanceObligationExpectedTimingOf"
    "SatisfactionPeriod1"
)
RPO_TOTAL_CONCEPT = "us-gaap:RevenueRemainingPerformanceObligation"
RPO_SCOPE_RULE_ID = "pk04.rpo_vs_deferred_scope/v1"

_FIELD_MAPPINGS = {
    # Core revenue aliases in priority order (10/20/30); SalesRevenueNet is a
    # taxonomy 2009-2017 element exactly as the core alias records it.
    "revenue": FactMapping(
        (
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:SalesRevenueNet",
            "us-gaap:Revenues",
        )
    ),
    "contract_liability_current": FactMapping(
        ("us-gaap:ContractWithCustomerLiabilityCurrent",)
    ),
    "contract_liability_noncurrent": FactMapping(
        ("us-gaap:ContractWithCustomerLiabilityNoncurrent",)
    ),
    "contract_liability_rollforward_opening": FactMapping(
        ("us-gaap:ContractWithCustomerLiability",),
        period_select="opening_instant",
    ),
    "contract_liability_rollforward_recognized": FactMapping(
        ("us-gaap:ContractWithCustomerLiabilityRevenueRecognized",)
    ),
    # No standard us-gaap element for gross additions; narrative-only.
    "contract_liability_rollforward_additions": FactMapping(concepts=()),
    "contract_liability_rollforward_closing": FactMapping(
        ("us-gaap:ContractWithCustomerLiability",)
    ),
    # RPO total (instant), undimensioned-first. The framework resolves an
    # undimensioned fact for the period whenever one exists; the mapping
    # keeps the default empty ``dimensions_allowed`` so its digest — pinned
    # by the base-envelope tests over this pack — is unchanged, and the one
    # additional admissible shape is the finalize hook below. ACCEPTED
    # shapes: (1) an undimensioned fact for the period (framework); (2)
    # exactly one non-nil fact at the period end whose ONLY dimension is the
    # standard expected-timing-of-satisfaction start-date axis, with no
    # expected-timing Period1 duration on the same context, and a unit the
    # catalogue admits. REJECTED shapes — the field stays a typed absence;
    # buckets are never summed and never picked: two or more facts on that
    # axis for the period end (a timing ladder); a fact whose context also
    # carries the Period1 duration (one timing bucket, not the total); a
    # fact on any other axis or carrying any additional axis (e.g. a
    # product-or-service-dimensioned subset alongside the axis).
    "rpo_total": FactMapping(
        ("us-gaap:RevenueRemainingPerformanceObligation",)
    ),
    "rpo_percentage_next_12m": TypedDimensionedFactMapping(
        concept="us-gaap:RevenueRemainingPerformanceObligationPercentage",
        typed_axis=RPO_TIMING_AXIS,
        select="earliest_on_or_after_period_of_report",
    ),
    # Expected timing is tagged as non-numeric duration facts; the raw ledger
    # excludes nonnumeric facts by design, so this stays unsupported here.
    "rpo_timing": FactMapping(concepts=()),
    "revenue_disaggregated": DimensionedFactMapping(
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        primary_axes=(PRODUCT_OR_SERVICE_AXIS, GEOGRAPHICAL_AXIS),
        member_filter="definition_linkbase",
    ),
    # Reserved (A.4): policy text is span evidence a later lane owns.
    "revenue_policy_text_block": TextSpanMapping(),
}

_CHECKS = (
    Rollforward(
        check_id="contract_liability_rollforward",
        opening="contract_liability_rollforward_opening",
        additions=("contract_liability_rollforward_additions",),
        reductions=("contract_liability_rollforward_recognized",),
        closing="contract_liability_rollforward_closing",
        implied_limitation_template=(
            "contract_liability_rollforward: refused to imply {field_id} ="
            " {implied} (R-K3: never an implied value)"
        ),
    ),
    CrossStatement(
        check_id="rpo_vs_deferred_scope",
        operands=(
            "rpo_total",
            "contract_liability_current",
            "contract_liability_noncurrent",
        ),
        rule=RPO_SCOPE_RULE_ID,
    ),
    SumIdentity(
        check_id="disaggregation_sums_to_revenue",
        addends=("revenue_disaggregated",),
        total="revenue",
    ),
)


def _decimals_of(operand: RuleOperand) -> int:
    """The operand's fact decimals, falling back to the value's own scale."""
    if operand.decimals is not None:
        return operand.decimals
    if operand.value is not None:
        exponent = operand.value.as_tuple().exponent
        if isinstance(exponent, int):
            return -exponent
    return 0


def _rpo_vs_deferred_scope(operands: dict) -> RuleOutcome:
    """RPO scope: RPO total covers at least the deferred contract liabilities.

    Any unvalued operand — a ``missing`` noncurrent liability included, never
    an implied zero — keeps the check ``not_evaluable`` / ``missing_dependency``.
    """
    rpo = operands["rpo_total"]
    current = operands["contract_liability_current"]
    noncurrent = operands["contract_liability_noncurrent"]
    if any(
        operand.value is None
        for operand in (rpo, current, noncurrent)
    ):
        return RuleOutcome("not_evaluable", "missing_dependency")
    tolerance = Decimal(1).scaleb(
        -min(_decimals_of(operand) for operand in (rpo, current, noncurrent))
    )
    deferred = current.value + noncurrent.value
    status = "pass" if rpo.value + tolerance >= deferred else "fail"
    return RuleOutcome(status, None, tolerance)


CHECK_RULES = {
    RPO_SCOPE_RULE_ID: CheckRule(
        rule_id=RPO_SCOPE_RULE_ID,
        fn=_rpo_vs_deferred_scope,
    ),
}


def _dimension_pairs(dimensions: Any) -> tuple:
    """Canonical comparable (axis, member) pairs for either container form."""
    if hasattr(dimensions, "items"):
        dimensions = dimensions.items()
    return tuple(
        sorted(dimensions, key=lambda pair: (str(pair[0]), str(pair[1])))
    )


def _context_shape_key(context: Any) -> tuple:
    """The economic identity of a context: period plus dimensions.

    Two document-local context ids with the same period and the same
    dimension pairs are the same context for the Period1 guard; the reverse
    (one id, two economic contexts) is impossible by XBRL construction.
    """
    return (
        str(context.instant) if context.instant is not None else None,
        str(context.start) if context.start is not None else None,
        str(context.end) if context.end is not None else None,
        _dimension_pairs(context.explicit_dimensions),
        _dimension_pairs(context.typed_dimensions),
    )


def _rpo_single_typed_axis_aggregate(
    ledger: Any, por: date, unit_equivalents: frozenset[str] | None
) -> Any | None:
    """The single-aggregate guard for the typed-axis RPO total.

    Implements the ``rpo_total`` rule's clause (2): returns the one
    admissible occurrence — a non-nil ``RPO_TOTAL_CONCEPT`` fact at ``por``
    whose only dimension is ``RPO_TIMING_AXIS`` carried as the context's
    TYPED dimension with a member date inside the period-adjacent window
    ``por < member_date <= por + 92 days``, with no
    ``RPO_TIMING_PERIOD1_CONCEPT`` fact on the same context and a ledger
    unit inside ``unit_equivalents`` — or ``None`` for every rejected shape
    (no such fact; an undimensioned fact present, which the framework's own
    resolution owns; two or more such facts; a Period1-marked bucket; a
    unit the catalogue refuses; the axis carried as an explicit member; a
    typed member at or before ``por``, past the window, or carrying no
    parseable date). Axis membership is decided by the framework's
    ``_dimensions_admitted`` over axis NAMES.
    """
    undimensioned: list[Any] = []
    candidates: list[Any] = []
    for occurrence in ledger.events:
        if occurrence.concept_qname != RPO_TOTAL_CONCEPT or occurrence.is_nil:
            continue
        context = occurrence.context
        if context.instant is None or context.instant != por:
            continue
        if occurrence.dimensions_known is False:
            continue  # R-F3: never admissible as consolidated
        if not (context.explicit_dimensions or context.typed_dimensions):
            undimensioned.append(occurrence)
            continue
        # The axis must be the context's TYPED dimension: an occurrence
        # carrying the timing axis as an EXPLICIT member names the same axis
        # but is a different shape (never date-typed), so it is skipped here
        # — never a candidate, never a source the mint reads.
        if any(axis == RPO_TIMING_AXIS for axis, _ in context.explicit_dimensions):
            continue
        if RPO_TIMING_AXIS not in {axis for axis, _ in context.typed_dimensions}:
            continue
        if _dimensions_admitted(occurrence, (RPO_TIMING_AXIS,)):
            candidates.append(occurrence)
    if undimensioned or len(candidates) != 1:
        return None
    aggregate = candidates[0]
    # Period-adjacent window: both real filer conventions put the
    # aggregate's typed member at the day after the period end. ACCEPTED:
    # ``por < member_date <= por + 92 days``. REFUSED (the field stays a
    # typed absence): a member at or before the period end; one past the
    # window — a lone far-future bucket is one bucket of the disclosure,
    # not its total; a member with no parseable date at all.
    member = next(
        member
        for axis, member in aggregate.context.typed_dimensions
        if axis == RPO_TIMING_AXIS
    )
    member_date = _typed_member_iso_date(str(member))
    if member_date is None or not (por < member_date <= por + timedelta(days=92)):
        return None
    shape = _context_shape_key(aggregate.context)
    for occurrence in ledger.events:
        if occurrence.concept_qname == RPO_TIMING_PERIOD1_CONCEPT and (
            _context_shape_key(occurrence.context) == shape
        ):
            return None  # one timing bucket, not the total
    if (
        unit_equivalents is not None
        and _unit_measure(aggregate.unit) not in unit_equivalents
    ):
        return None
    return aggregate


def _mint_rpo_total_row(row: dict[str, Any], aggregate: Any) -> None:
    """Rewrite the disallowed-dimension absence as the valued aggregate row.

    Faithful to the framework's own valued FactMapping row for this field:
    the mapping is unchanged, so the mapping identity already on the
    absence row equals every undimensioned filer's; the aggregate's
    occurrence id is the sole source; the start-date axis is the row's
    single dimension, its typed member reported as the ISO date when the
    member is date-typed (the typed-dimensioned resolver's convention).
    """
    axis, member = aggregate.context.typed_dimensions[0]
    typed_date = _typed_member_iso_date(str(member))
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["concept"] = aggregate.concept_qname
    row["taxonomy"] = (
        "extension"
        if aggregate.concept_qname.startswith("{")
        else aggregate.concept_qname.split(":", 1)[0]
    )
    row["source_occurrence_ids"] = [aggregate.occurrence_id]
    row["mapping_rule_id"] = f"{SPEC.pack_id}.rpo_total.fact/v1"
    row["mapping_rule_digest"] = _mapping_digest(_FIELD_MAPPINGS["rpo_total"])
    row["dimensions"] = [
        {
            "axis": axis,
            "member": (
                typed_date.isoformat() if typed_date is not None else str(member)
            ),
        }
    ]
    row["value"] = decimal_text(Decimal(str(aggregate.parsed_value)))


def _recompute_coverage(envelope: dict[str, Any]) -> None:
    counts = {
        "valued_fields": 0,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
    }
    for row in envelope["fields"]:
        coverage_key = contract.QUALITY_TO_COVERAGE.get(row["quality_state"])
        if coverage_key is not None:
            counts[coverage_key] += 1
    disclosure = "present" if counts["valued_fields"] > 0 else "empty"
    envelope["coverage"] = {**counts, "disclosure_coverage_state": disclosure}


def _operand_decimals(row: Mapping[str, Any], by_id: Mapping[str, Any]) -> int | None:
    """The representative fact's decimals for one valued instant row.

    The plain FactMapping resolver picks its representative by lowest
    occurrence id, and a valued row's source facts all carry the same
    parsed value (differing values stay ``not_evaluable``), so the lowest-id
    source occurrence's decimals are the operand decimals the framework's
    own check pass would have used.
    """
    source_ids = row.get("source_occurrence_ids") or ()
    if not source_ids:
        return None
    representative = by_id.get(min(source_ids))
    if (
        representative is not None
        and representative.decimals is not None
        and representative.decimals != "INF"
    ):
        return int(representative.decimals)
    return None


def _refresh_rpo_scope_check(
    envelope: dict[str, Any],
    rows: Mapping[str, dict[str, Any]],
    ledger: Any,
) -> None:
    """Re-run the rpo_vs_deferred_scope verdict over the finalized rows.

    The framework evaluated the check against the still-absent ``rpo_total``
    row; with the aggregate valued, the verdict is recomputed exactly as the
    framework's rule branch does — not_applicable gate, missing dependency,
    then the registered rule over RuleOperands, with the rule's tolerance
    when it returns one and the operand-decimals identity tolerance
    otherwise. ``check_id``/``kind``/``operands``/``evidence_field_ids``
    stay the framework's own bytes.
    """
    check_row = next(
        (
            row
            for row in envelope["checks"]
            if row.get("check_id") == "rpo_vs_deferred_scope"
        ),
        None,
    )
    if check_row is None:
        return
    field_ids = (
        "rpo_total",
        "contract_liability_current",
        "contract_liability_noncurrent",
    )
    gate = next(
        (
            rows[name].get("reason")
            for name in field_ids
            if rows[name].get("quality_state") == "not_applicable"
        ),
        None,
    )
    if gate is not None:
        check_row["status"] = "not_applicable"
        check_row["reason"] = gate
        check_row["tolerance"] = None
        return
    by_id = {item.occurrence_id: item for item in ledger.events}
    operands: dict[str, RuleOperand] = {}
    decimals_list: list[int | None] = []
    for name in field_ids:
        row = rows[name]
        value = (
            Decimal(str(row["value"]))
            if row.get("quality_state") == "valued"
            and row.get("value") is not None
            else None
        )
        decimals = _operand_decimals(row, by_id) if value is not None else None
        decimals_list.append(decimals)
        operands[name] = RuleOperand(
            field_id=name,
            value=value,
            decimals=decimals,
            unit=row.get("unit"),
            period=row.get("period"),
            rows=(row,),
        )
    if any(
        operand.value is None
        and not any(
            item.get("quality_state") == "valued" for item in operand.rows
        )
        for operand in operands.values()
    ):
        check_row["status"] = "not_evaluable"
        check_row["reason"] = "missing_dependency"
        check_row["tolerance"] = decimal_text(_identity_tolerance(decimals_list))
        return
    verdict = _rpo_vs_deferred_scope(operands)
    check_row["status"] = verdict.status
    check_row["reason"] = verdict.reason if verdict.status != "pass" else None
    tolerance = (
        verdict.tolerance
        if verdict.tolerance is not None
        else _identity_tolerance(decimals_list)
    )
    check_row["tolerance"] = decimal_text(tolerance)


@dataclass(frozen=True)
class Pk04Producer(PackProducer):
    """PK04 declaration plus the typed-axis RPO-total finalize hook."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact (B.5)
        rows = {row["field_id"]: row for row in result["fields"]}
        rpo_row = rows.get("rpo_total")
        if rpo_row is None or rpo_row.get("quality_state") != "missing":
            return result  # valued/conflict rows: the framework's own word
        from ..ixbrl_raw_ledger import parse_and_convert_golden_packages

        # Same converter the framework used (call-time import), so a test
        # double is honoured identically by both passes.
        ledger, _filing_metadata, _report = parse_and_convert_golden_packages(
            pack_input.packages
        )
        catalogue_field = next(
            item
            for item in contract.load_pack_schema("PK04")["fields"]
            if item["field_id"] == "rpo_total"
        )
        por = date.fromisoformat(str(rpo_row["period"]["end"])[:10])
        aggregate = _rpo_single_typed_axis_aggregate(
            ledger,
            por,
            _unit_equivalents(catalogue_field.get("unit")),
        )
        if aggregate is None:
            return result
        _mint_rpo_total_row(rpo_row, aggregate)
        _refresh_rpo_scope_check(result, rows, ledger)
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK04 finalize refused: " + "; ".join(errors[:5])
            )
        return result


PRODUCER = Pk04Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    check_rules=CHECK_RULES,
    limitations=(
        "contract_liability_rollforward_additions: no standard alias; gross"
        " additions are narrative-only for most issuers",
        "rpo_timing: duration facts are non-numeric iXBRL and are not"
        " represented in the raw ledger",
    ),
)

__all__ = ["CHECK_RULES", "PRODUCER", "SPEC"]
