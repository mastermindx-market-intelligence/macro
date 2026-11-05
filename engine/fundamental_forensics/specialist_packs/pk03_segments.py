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

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from .. import specialist_pack_contract as contract
from ..raw_ledger import RawFactLedger, canonical_json, decimal_text
from . import definition_linkbase
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
    SpecialistPackError,
    TextSpanMapping,
    _package_definition_linkbase_bytes,
    _resolve_grouped_dimensioned_fact_mapping,
    _select_primary,
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


# --- dev-corpus widened re-resolution (diversified_v1) ------------------------
#
# Dev-corpus rules (diversified_v1, DEC-FIF-PACK-GENERALIZATION-DEV-CORPUS).
# Three fields abstain on filings whose evidence the frozen single-concept
# mapping declarations above do not name:
#
# 1. ``segment_profit_or_loss``: an ASU 2023-07 filer whose CODM measure is
#    NET EARNINGS tags the per-segment measure with ``us-gaap:ProfitLoss``
#    (the standard net-income concept), not an operating-income concept.
# 2. ``geographic_revenue`` / ``product_service_revenue``: a filer that
#    presents the geographic or product/service table on an
#    other-than-606 basis tags those rows ``us-gaap:Revenues`` — already a
#    ``core:revenue`` alias — optionally stamped with the
#    OperatingSegmentsMember subtotal basis on ConsolidationItemsAxis, the
#    same optional second-axis admission ``SEGMENT_FACT_OTHER_MEMBERS``
#    grants the segment fields.
#
# The repair re-resolves exactly these three fields through the framework's
# own grouped resolver with the widened concept tuple, emitting what a
# mapping-level concept list would: each appended row names its own concept
# and carries the digest of the widened mapping that produced it. A field
# whose base block is a single absence row is REPLACED by the widened rows
# (the resolver emits no absence row once any listed concept resolves); a
# field with any valued base row gets the widened rows appended after the
# base block (concept-major order). A filing that carries no widened-concept
# fact on the field's axis leaves the envelope byte-identical — the hook
# returns it untouched, which is exactly what the BASE envelope pins of the
# later lanes' test modules assert. Fields never rewritten here:
# ``segment_revenue``, ``unallocated_corporate_and_eliminations``,
# ``number_of_operating_segments`` and both text placeholders. The mirrors
# keep PK04's axis, member filter and row shape; the added concept is
# PK03-side and deliberately does not touch PK04.
_WIDENED_FIELD_MAPPINGS: Mapping[str, DimensionedFactMapping] = {
    "segment_profit_or_loss": DimensionedFactMapping(
        concepts=("us-gaap:ProfitLoss",),
        primary_axis=SEGMENT_AXIS,
        member_filter="definition_linkbase",
        optional_other_members=SEGMENT_FACT_OTHER_MEMBERS,
    ),
    "geographic_revenue": DimensionedFactMapping(
        concepts=("us-gaap:Revenues",),
        primary_axis=GEOGRAPHICAL_AXIS,
        member_filter="definition_linkbase",
        optional_other_members={
            CONSOLIDATION_ITEMS_AXIS: "us-gaap:OperatingSegmentsMember"
        },
    ),
    "product_service_revenue": DimensionedFactMapping(
        concepts=("us-gaap:Revenues",),
        primary_axis=PRODUCT_OR_SERVICE_AXIS,
        member_filter="definition_linkbase",
        optional_other_members={
            CONSOLIDATION_ITEMS_AXIS: "us-gaap:OperatingSegmentsMember"
        },
    ),
}


def _recompute_coverage(envelope: dict[str, Any]) -> None:
    """Recount the coverage block after finalize rewrote field rows."""
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


class Pk03Producer(PackProducer):
    """PK03 declaration plus the dev-corpus widened-concept finalize hook."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: Any
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact
        from ..ixbrl_raw_ledger import (  # call-time: a test double is honoured
            parse_and_convert_golden_packages
        )

        ledger, _filing_metadata, _report = parse_and_convert_golden_packages(
            pack_input.packages
        )
        primary, _matched = _select_primary(pack_input.packages, SPEC.forms)
        por_text = str(primary.manifest.get("period_of_report") or "")
        por = date.fromisoformat(por_text[:10])
        catalogue_fields = {
            str(item["field_id"]): item
            for item in contract.load_pack_schema("PK03")["fields"]
        }
        axis_groups = definition_linkbase.parse_axis_member_groups(
            _package_definition_linkbase_bytes(primary)
        )

        replacements: dict[str, list[dict[str, Any]]] = {}
        widened_limitations: list[str] = []
        for field_id, mapping in _WIDENED_FIELD_MAPPINGS.items():
            outcome = _resolve_grouped_dimensioned_fact_mapping(
                pack_id="PK03",
                catalogue_field=catalogue_fields[field_id],
                mapping=mapping,
                ledger=ledger,
                por=por,
                axis_groups=axis_groups,
                limitation_sink=widened_limitations,
            )
            widened_rows = [outcome.row, *outcome.extra_rows]
            if not any(
                row["quality_state"] == "valued" for row in widened_rows
            ):
                # The filing carries no widened-concept evidence for this
                # field: the base mapping's rows stay byte-identical.
                continue
            base_indexes = [
                index
                for index, row in enumerate(result["fields"])
                if row["field_id"] == field_id
            ]
            base_rows = [result["fields"][index] for index in base_indexes]
            if len(base_rows) == 1 and base_rows[0]["quality_state"] != (
                "valued"
            ):
                # A single absence row: the widened pass replaces it (a
                # mapping-level concept list emits no absence row once any
                # listed concept resolves).
                replacements[field_id] = widened_rows
            else:
                # Concept-major order: the base block stays, the widened
                # concept's rows follow it.
                replacements[field_id] = [*base_rows, *widened_rows]

        if not replacements:
            return result

        # Emit each replacement block at its field's first base-row
        # position; every other base row of a replaced field is skipped
        # (it is already inside the block, or dropped by the replacement).
        emit_at: dict[int, list[dict[str, Any]]] = {}
        skip_ids: set[int] = set()
        for field_id, block in replacements.items():
            base_rows = [
                row
                for row in result["fields"]
                if str(row["field_id"]) == field_id
            ]
            for row in base_rows:
                skip_ids.add(id(row))
            emit_at[id(base_rows[0])] = block
        rewritten: list[dict[str, Any]] = []
        for row in result["fields"]:
            if id(row) in skip_ids:
                if id(row) in emit_at:
                    rewritten.extend(emit_at[id(row)])
                continue
            rewritten.append(row)
        result["fields"] = rewritten
        result["limitations"] = list(
            dict.fromkeys((*result["limitations"], *widened_limitations))
        )[:32]
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK03 finalize refused: " + "; ".join(errors[:5])
            )
        return result


PRODUCER = Pk03Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    check_rules=CHECK_RULES,
)

register_extra_check("PK03", _fp_internal_revenue_not_double_counted)

__all__ = ["CHECK_RULES", "PRODUCER", "SPEC"]
