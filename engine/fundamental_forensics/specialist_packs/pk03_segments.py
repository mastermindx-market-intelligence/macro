"""PK03 producer: segments and geographic/product dimensions.

PK03 owns the segment map (the business-segment axis), the
segment-to-consolidated revenue bridge and the tagged segment count. The
geographic and product/service fields are READ-ONLY mirrors of PK04's
``revenue_disaggregated`` field — same concept, same axis, same
definition-linkbase member filter — so the two packs can never disagree on
those axes; PK04 owns them and any change belongs there. The consolidated
operand ``core:revenue`` and the revenue-basis elimination rows bind
``base.CORE_REVENUE_CONCEPTS``, the shared core-catalogue alias tuple. The
narrative segment count is never extracted (R-K4'): the count is the tagged
fact or the honest ``missing`` typed absence, and both text fields stay
reserved span evidence (``unsupported``).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from ..raw_ledger import RawFactLedger, canonical_json, decimal_text
from .base import (
    CORE_REVENUE_CONCEPTS,
    CheckRule,
    CrossStatement,
    DimensionedFactMapping,
    FactMapping,
    PackProducer,
    PackSpec,
    ReconcileToConsolidated,
    RuleOperand,
    RuleOutcome,
    TextSpanMapping,
    primary_period,
    probe_core_fact,
    register_extra_check,
)

SPEC = PackSpec(
    pack_id="PK03",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="specialist_pack.pk03.applicability/v1",
    # ``applicable_classes`` stays None: PK03 applies to every issuer class
    # (banks included); the framework never consults the class gate.
)

SEGMENT_AXIS = "us-gaap:StatementBusinessSegmentsAxis"
CONSOLIDATION_ITEMS_AXIS = "srt:ConsolidationItemsAxis"
GEOGRAPHICAL_AXIS = "srt:StatementGeographicalAxis"
PRODUCT_OR_SERVICE_AXIS = "srt:ProductOrServiceAxis"
# Segment-table facts carry the segment axis plus ConsolidationItemsAxis =
# OperatingSegmentsMember (the "operating segments" subtotal basis).
SEGMENT_FACT_OTHER_MEMBERS = {
    CONSOLIDATION_ITEMS_AXIS: "us-gaap:OperatingSegmentsMember"
}
_SEGMENT_PROFIT_CONCEPTS = (
    "us-gaap:OperatingIncomeLoss",
    "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinary"
    "ItemsNoncontrollingInterest",
)
_ELIMINATION_MEMBER_ALLOWLIST = (
    "us-gaap:CorporateNonSegmentMember",
    "us-gaap:MaterialReconcilingItemsMember",
    "us-gaap:IntersegmentEliminationMember",
    "us-gaap:ConsolidationEliminationsMember",
    "srt:ConsolidationEliminationsMember",
)
_TOLERANCE = Decimal("1000000")
_SEGMENT_COUNT_RULE_ID = "pk03.segment_count_consistent/v1"

_FIELD_MAPPINGS = {
    # The filing tags no segment-count fact; the narrative count ("five
    # reportable segments") is not extractable evidence (R-K4').
    "number_of_operating_segments": FactMapping(
        (
            "us-gaap:NumberOfOperatingSegments",
            "us-gaap:NumberOfReportableSegments",
        )
    ),
    "segment_revenue": DimensionedFactMapping(
        primary_axis=SEGMENT_AXIS,
        member_filter="definition_linkbase",
        optional_other_members=SEGMENT_FACT_OTHER_MEMBERS,
        concepts=CORE_REVENUE_CONCEPTS,
    ),
    "segment_profit_or_loss": DimensionedFactMapping(
        primary_axis=SEGMENT_AXIS,
        member_filter="definition_linkbase",
        optional_other_members=SEGMENT_FACT_OTHER_MEMBERS,
        concepts=_SEGMENT_PROFIT_CONCEPTS,
    ),
    "unallocated_corporate_and_eliminations": DimensionedFactMapping(
        primary_axis=CONSOLIDATION_ITEMS_AXIS,
        member_allowlist=_ELIMINATION_MEMBER_ALLOWLIST,
        # Mixed revenue/profit basis: only revenue-concept rows join the
        # revenue bridge (the check's elimination_concepts filter).
        concepts=(*CORE_REVENUE_CONCEPTS, "us-gaap:OperatingIncomeLoss"),
    ),
    # Read-only mirrors of PK04 revenue_disaggregated (single-axis slices).
    "geographic_revenue": DimensionedFactMapping(
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        primary_axis=GEOGRAPHICAL_AXIS,
        member_filter="definition_linkbase",
    ),
    "product_service_revenue": DimensionedFactMapping(
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        primary_axis=PRODUCT_OR_SERVICE_AXIS,
        member_filter="definition_linkbase",
    ),
    # Reserved (A.4): span evidence a later lane owns.
    "segment_definition_change_note": TextSpanMapping(),
    "segment_reporting_text_block": TextSpanMapping(),
}

_CHECKS = (
    ReconcileToConsolidated(
        check_id="segment_sum_plus_eliminations_equals_consolidated",
        parts=("segment_revenue",),
        eliminations=("unallocated_corporate_and_eliminations",),
        elimination_concepts=CORE_REVENUE_CONCEPTS,
        consolidated="core:revenue",
        tolerance=_TOLERANCE,
    ),
    CrossStatement(
        check_id="segment_count_consistent",
        operands=("number_of_operating_segments", "segment_revenue"),
        rule=_SEGMENT_COUNT_RULE_ID,
    ),
)


def _segment_count_consistent(operands: Mapping[str, RuleOperand]) -> RuleOutcome:
    """A.3: the tagged count equals the number of valued segment rows.

    The framework's rule gate already made the check ``not_evaluable`` when
    the count is unvalued or no segment row is valued; the rule only decides
    pass/fail between the valued count and the valued segment rows.
    """
    count = operands["number_of_operating_segments"]
    segments = operands["segment_revenue"]
    valued_rows = [
        row for row in segments.rows if row.get("quality_state") == "valued"
    ]
    if count.value is None or not valued_rows:
        return RuleOutcome("not_evaluable", "missing_dependency")
    return RuleOutcome(
        "pass" if count.value == Decimal(len(valued_rows)) else "fail"
    )


CHECK_RULES = {
    _SEGMENT_COUNT_RULE_ID: CheckRule(
        rule_id=_SEGMENT_COUNT_RULE_ID,
        fn=_segment_count_consistent,
    ),
}


def _axis_local(axis: str) -> str:
    """The axis local name, Clark form or prefixed (same binding as base)."""
    if axis.startswith("{") and "}" in axis:
        return axis.rsplit("}", 1)[1]
    return axis.rsplit(":", 1)[-1] if ":" in axis else axis


def _segment_member_key(row: Mapping[str, Any]) -> str:
    """A row's segment-axis member, falling back to its full dimensions."""
    for dimension in row.get("dimensions") or ():
        if _axis_local(str(dimension["axis"])) == _axis_local(SEGMENT_AXIS):
            return str(dimension["member"])
    return canonical_json(row.get("dimensions") or [])


def _valued_rows(outcomes: Mapping[str, Any], field_id: str) -> tuple[dict, ...]:
    outcome = outcomes.get(field_id)
    if outcome is None:
        return ()
    return tuple(
        row
        for row in (outcome.row, *outcome.extra_rows)
        if row.get("quality_state") == "valued"
    )


def _fp_internal_revenue_not_double_counted(
    pack_input: Any,
    ledger: RawFactLedger | None,
    outcomes: Mapping[str, Any],
    catalogue_check: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]] | None:
    """A.5: no segment member repeats and the revenue basis does not exceed
    the consolidated revenue (intersegment revenue is never counted twice)."""
    if catalogue_check["check_id"] != "fp_internal_revenue_not_double_counted":
        return None
    evidence = ("segment_revenue", "unallocated_corporate_and_eliminations")

    def check_row(status: str, reason: str | None = None) -> dict[str, Any]:
        return {
            "check_id": catalogue_check["check_id"],
            "kind": catalogue_check["kind"],
            "status": status,
            "operands": list(catalogue_check.get("operands") or []),
            "tolerance": decimal_text(_TOLERANCE),
            "evidence_field_ids": list(evidence),
            "reason": reason,
        }

    segment_rows = _valued_rows(outcomes, "segment_revenue")
    elimination_rows = tuple(
        row
        for row in _valued_rows(outcomes, "unallocated_corporate_and_eliminations")
        if row.get("concept") in CORE_REVENUE_CONCEPTS
    )
    consolidated = None
    if ledger is not None:
        consolidated = probe_core_fact(
            FactMapping(CORE_REVENUE_CONCEPTS),
            ledger,
            primary_period(pack_input, SPEC.forms),
        )
    if consolidated is None or not segment_rows:
        return check_row("not_evaluable", "missing_dependency"), ()
    member_keys = [_segment_member_key(row) for row in segment_rows]
    if len(set(member_keys)) != len(member_keys):
        # Two valued rows share one segment member: double counting.
        return check_row("fail"), ()
    revenue_basis = sum(
        (
            Decimal(str(row["value"]))
            for row in (*segment_rows, *elimination_rows)
        ),
        Decimal("0"),
    )
    if revenue_basis > consolidated + _TOLERANCE:
        return check_row("fail"), ()
    return check_row("pass"), ()


PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    check_rules=CHECK_RULES,
)

register_extra_check("PK03", _fp_internal_revenue_not_double_counted)

__all__ = ["CHECK_RULES", "PRODUCER", "SPEC"]
