"""PK11 producer: financial-institution credit, capital and liquidity.

Thin by design over the shared framework in ``base.py`` — every mapping below
is a frozen B.2 declaration. The pack is class-gated to banks: the gate is
declared through ``extra_applicability`` (not ``PackSpec.applicable_classes``)
so an unbound class types as ``not_applicable`` + ``issuer_class_unknown``,
the frozen catalogue's C3 treatment, while the framework's built-in class
gate would type it ``not_evaluable``.

The framework at this lane's BASE carries no prior-instant rollforward
operand, no ratio-tolerance cross-statement check and no core-catalogue
presence check, and assembles ``limitations`` from producer constants only.
Those semantics live in ``Pk11Producer.finalize_result``, a producer hook the
registry calls after the framework's own envelope passes the contract
validator; the hook rewrites the affected check rows, appends the conditional
limitations and re-digests + re-checks the envelope, so a PK11 result never
bypasses the contract. The ``checks`` tuple below therefore declares the
closest framework specs for those rows — placeholders the hook replaces.
``cet1_vs_minimum`` is replaced too: the framework would decide it before the
hook values the disclosed cells (and never again), so the hook re-decides it
against the valued rows — minimum <= CET1 ratio, same instant, same approach.

The A30 limitation ids and the core ``revenue`` aliases are copied exactly
from ``config/fundamental_forensics/metrics/v1/`` (metric_catalog.yaml and
mappings/core.yaml): the core catalogue's own class gating is the declared
source, never this producer's opinion.

Dev-corpus banks_v1 (DEC-FIF-PACK-GENERALIZATION-DEV-CORPUS): the finalize
hook additionally resolves three of the six reserved disclosed regulatory
fields from the standard-taxonomy iXBRL facts that ARE the displayed
capital-adequacy / credit-quality table cells of US bank filings — the facts
carry exactly the consolidated-entity and regulatory-approach dimensions
those tables display, so the evidence is a table cell with the fact's own
occurrence ids and presentation-linkbase coordinates (see
``_disclosed_table_cell``). ``lcr_disclosed``, ``nsfr_disclosed`` and
``liquid_assets_disclosed`` stay reserved: the dev corpus carries no
standard-taxonomy liquidity fact at all (those disclosures are prose-only,
and R-K4' forbids scraping narrative).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from .. import detectors
from .. import specialist_pack_contract as contract
from ..raw_ledger import RawFactLedger, canonical_json, decimal_text
from .base import (
    MAX_DURATION_DAYS,
    CrossStatement,
    FactMapping,
    FormulaMapping,
    PackInput,
    PackProducer,
    PackSpec,
    Presence,
    Rollforward,
    SpecialistPackError,
    TableMapping,
    _project_reason,
    _unit_equivalents,
    _unit_measure,
    formula_sum,
)

SPEC = PackSpec(
    pack_id="PK11",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="pack.pk11.applicability/v1",
    applicable_classes=None,
)

# B.2 concept aliases (us-gaap; priority order; undimensioned). The first
# allowance alias and the net write-off alias are the spellings the dev
# corpus banks_v1 actually carries as UNDIMENSIONED totals (JPM/WFC/C/USB/PNC
# filings inspected on the lane host); the historical spellings stay below
# them in priority order.
_ALLOWANCE_CONCEPTS = (
    "us-gaap:FinancingReceivableAllowanceForCreditLossExcludingAccruedInterest",
    "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLoss",
    "us-gaap:FinancingReceivableAllowanceForCreditLosses",
)
_PROVISION_FINANCING_CONCEPTS = (
    "us-gaap:FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal",
    "us-gaap:ProvisionForLoanLeaseAndOtherLosses",
    "us-gaap:ProvisionForLoanLossesExpensed",
)
_NET_WRITE_OFF_CONCEPTS = (
    "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLossWriteoffAfterRecovery",
    "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLossWriteoffNet",
    "us-gaap:FinancingReceivableAllowanceForCreditLossesWriteOffsNet",
)
_TABLE_CELL_FIELDS = (
    "cet1_ratio_disclosed",
    "regulatory_minimum_disclosed",
    "lcr_disclosed",
    "nsfr_disclosed",
    "liquid_assets_disclosed",
    "npl_or_npa_disclosed",
)

# B.3 nii_not_revenue: the core catalogue's revenue aliases, copied exactly
# from mapping.revenue/v1 in metrics/v1/mappings/core.yaml. The core rule
# carries a 2009-2017 taxonomy-version window on SalesRevenueNet; this read
# keeps the priority order and does not re-derive that window.
_CORE_REVENUE_CONCEPTS = (
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:SalesRevenueNet",
    "us-gaap:Revenues",
)

# B.4 (A30): core metric ids whose industrial basis the core catalogue gates
# out for banks, copied exactly (order included) from the entries carrying
# ``excluded_classes: [bank]`` in metrics/v1/metric_catalog.yaml.
_A30_EXCLUDED_CORE_METRICS = (
    "cost_of_revenue",
    "gross_profit",
    "gross_margin",
    "operating_expenses",
    "operating_income_loss",
    "inventory_net",
    "current_assets",
    "current_liabilities",
    "working_capital",
    "current_ratio",
    "cash_to_total_debt",
    "net_debt",
    "free_cash_flow",
    "debt_to_equity",
    "receivables_to_revenue",
    "inventory_to_revenue",
)

_RATIO_QUANTUM = Decimal("0.000001")  # 6 dp under ROUND_HALF_EVEN (B.3)
_CAPITAL_RATIO_TOLERANCE = Decimal("0.001")
_PROVISION_TOTAL_LIMITATION = (
    "pk11.provision_total: off-balance-sheet component absent; total not inferred"
)
_NII_REVENUE_LIMITATION = (
    "pk11.nii_not_revenue: net interest income equals a core revenue fact;"
    " bank interest is not contract revenue (bank_interest_not_contract_revenue)"
)

_FIELD_MAPPINGS = {
    "provision_for_credit_losses_total": FormulaMapping(
        rule_id="pk11.provision_total/v1",
        inputs=(
            "credit_loss_expense_financing_receivables",
            "credit_loss_expense_off_balance_sheet",
        ),
        fn=formula_sum,
    ),
    "credit_loss_expense_financing_receivables": FactMapping(
        _PROVISION_FINANCING_CONCEPTS
    ),
    "credit_loss_expense_off_balance_sheet": FactMapping(
        ("us-gaap:OffBalanceSheetCreditLossLiabilityCreditLossExpenseReversal",)
    ),
    # ``precision_consistent`` (A.1): the dev filings' rounded summary tables
    # repeat the disclosed allowance at a coarser scale/decimals (C's 10-K
    # carries 19,247 at scale 6/decimals -6 next to 19.2 at scale 9/decimals
    # -8 in the same undimensioned context); the most precise occurrence
    # governs when every coarser duplicate rounds onto it.
    "allowance_for_credit_losses": FactMapping(
        _ALLOWANCE_CONCEPTS, duplicate_policy="precision_consistent"
    ),
    "net_write_offs": FactMapping(_NET_WRITE_OFF_CONCEPTS),
    # Gross carrying amount only: the net spelling already deducts the
    # allowance this pack values separately, so it would double-count it in
    # the acl_coverage denominator.
    "loans_held_for_investment": FactMapping(
        (
            "us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss",
            "us-gaap:LoansAndLeasesReceivableGrossCarryingAmount",
        )
    ),
    "deposits": FactMapping(("us-gaap:Deposits",)),
    "cet1_capital": FactMapping(
        (
            "us-gaap:CommonEquityTier1Capital",
            "us-gaap:BankingRegulationCommonEquityTier1Capital",
        )
    ),
    "risk_weighted_assets": FactMapping(
        ("us-gaap:RiskWeightedAssets", "us-gaap:BankingRegulationRiskWeightedAssets")
    ),
    "net_interest_income": FactMapping(("us-gaap:InterestIncomeExpenseNet",)),
    # A.4: table-cell evidence is reserved for a later lane; the six disclosed
    # regulatory/liquidity fields resolve to typed absence in this version.
    "cet1_ratio_disclosed": TableMapping(),
    "regulatory_minimum_disclosed": TableMapping(),
    "lcr_disclosed": TableMapping(),
    "nsfr_disclosed": TableMapping(),
    "liquid_assets_disclosed": TableMapping(),
    "npl_or_npa_disclosed": TableMapping(),
}

_CHECKS = (
    # Placeholder relation (allowance <= loans); finalize_result replaces the
    # row with the true 6-dp ratio band 0 <= ratio <= 1.
    CrossStatement(
        check_id="acl_coverage",
        left="allowance_for_credit_losses",
        right="loans_held_for_investment",
        relation="left_lte_right",
    ),
    # Placeholder only: finalize_result ALWAYS replaces this row (the
    # framework decides it before the hook values the cells, and this
    # relation is inverted). The true relation is minimum <= CET1 ratio,
    # decided only at the same instant and under the same approach.
    CrossStatement(
        check_id="cet1_vs_minimum",
        left="cet1_ratio_disclosed",
        right="regulatory_minimum_disclosed",
        relation="left_lte_right",
    ),
    # Placeholder relation; finalize_result replaces the row with the
    # cet1_capital / risk_weighted_assets ratio vs the disclosed ratio at a
    # 0.001 tolerance.
    CrossStatement(
        check_id="capital_ratio_arithmetic",
        left="cet1_capital",
        right="cet1_ratio_disclosed",
        relation="equal",
    ),
    # Placeholder identity (the framework resolves the opening at the closing
    # instant); finalize_result replaces the row with the prior-instant
    # opening + provision - write-offs = closing rollforward.
    Rollforward(
        check_id="provision_vs_acl_rollforward",
        opening="allowance_for_credit_losses",
        additions=("credit_loss_expense_financing_receivables",),
        reductions=("net_write_offs",),
        closing="allowance_for_credit_losses",
    ),
    # Placeholder presence; finalize_result replaces the row with the
    # core-revenue comparison (fail when a core revenue fact equals NII).
    Presence(check_id="nii_not_revenue", field_id="net_interest_income"),
)


def _bank_class_gate(
    pack_input: PackInput, ledger: RawFactLedger | None
) -> tuple[str, str] | None:
    """C3: bank-class issuers only, evaluated after the form gate (R-K1).

    The frozen catalogue types an unbound class ``not_applicable`` +
    ``issuer_class_unknown``; the framework's built-in class gate would type
    it ``not_evaluable``, so the gate is declared here instead.
    """
    issuer_class = detectors.issuer_class_for_sic(pack_input.issuer_sic)
    if issuer_class == "bank":
        return None
    if issuer_class == "unknown":
        return "not_applicable", "issuer_class_unknown"
    return "not_applicable", "issuer_class_not_bank"


def _undimensioned(occurrence: Any) -> bool:
    context = occurrence.context
    return not (set(context.explicit_dimensions) | set(context.typed_dimensions))


def _duration_days(occurrence: Any) -> int:
    context = occurrence.context
    return (context.end - context.start).days + 1


def _instant_value(
    ledger: RawFactLedger, concepts: tuple[str, ...], instant: date
) -> Decimal | None:
    """Undimensioned non-nil instant value at exactly ``instant``.

    Concepts are tried in the field's priority order; conflicting values at
    that instant leave the reading unresolvable (R-K3: never an implied
    zero).
    """
    for concept in concepts:
        candidates = [
            occurrence
            for occurrence in ledger.events
            if occurrence.concept_qname == concept
            and not occurrence.is_nil
            and occurrence.context.instant == instant
            and _undimensioned(occurrence)
        ]
        if not candidates:
            continue
        values = {
            Decimal(str(occurrence.parsed_value))
            for occurrence in candidates
        }
        if len(values) == 1:
            return values.pop()
        return None
    return None


def _primary_duration_value(
    ledger: RawFactLedger, concepts: tuple[str, ...], por: date
) -> Decimal | None:
    """First alias value for the primary annual window ending at ``por``.

    Mirrors the framework's duration admission: context end == por, at most
    ``MAX_DURATION_DAYS`` inclusive days, longest duration wins,
    undimensioned only. A conflicting read at the same window is treated as
    unreadable, never guessed.
    """
    for concept in concepts:
        candidates = [
            occurrence
            for occurrence in ledger.events
            if occurrence.concept_qname == concept
            and not occurrence.is_nil
            and occurrence.context.end == por
            and occurrence.context.start is not None
            and _duration_days(occurrence) <= MAX_DURATION_DAYS
            and _undimensioned(occurrence)
        ]
        if not candidates:
            continue
        longest = max(_duration_days(occurrence) for occurrence in candidates)
        values = {
            Decimal(str(occurrence.parsed_value))
            for occurrence in candidates
            if _duration_days(occurrence) == longest
        }
        if len(values) == 1:
            return values.pop()
        return None
    return None


def _row_value(rows: Mapping[str, Mapping[str, Any]], field_id: str) -> Decimal | None:
    row = rows[field_id]
    if row["quality_state"] != "valued" or row.get("value") is None:
        return None
    return Decimal(str(row["value"]))


def _check_row(
    catalogue_check: Mapping[str, Any],
    status: str,
    *,
    tolerance: Decimal | None = None,
    evidence: tuple[str, ...] = (),
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "check_id": catalogue_check["check_id"],
        "kind": catalogue_check["kind"],
        "status": status,
        "operands": list(catalogue_check.get("operands") or []),
        "tolerance": decimal_text(tolerance),
        "evidence_field_ids": list(evidence),
        "reason": reason,
    }


def _acl_coverage_row(
    rows: Mapping[str, Mapping[str, Any]],
    catalogue_check: Mapping[str, Any],
    extra_limitations: list[str],
) -> dict[str, Any]:
    evidence = ("allowance_for_credit_losses", "loans_held_for_investment")
    allowance = _row_value(rows, "allowance_for_credit_losses")
    loans = _row_value(rows, "loans_held_for_investment")
    if allowance is None or loans is None:
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="missing_dependency",
        )
    if loans == 0:
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="division_by_zero",
        )
    ratio = (allowance / loans).quantize(_RATIO_QUANTUM, rounding=ROUND_HALF_EVEN)
    extra_limitations.append(f"pk11.acl_coverage: {ratio}")
    status = "pass" if Decimal(0) <= ratio <= Decimal(1) else "fail"
    return _check_row(catalogue_check, status, evidence=evidence)


def _row_methodology(row: Mapping[str, Any]) -> str | None:
    """The row's regulatory-approach member (lowercased local), if any.

    Two rows carrying no approach member count as equal callers.
    """
    for dimension in row.get("dimensions") or ():
        member = _member_local(str(dimension.get("member") or ""))
        if any(hint in member for hint in _METHODOLOGY_HINTS):
            return member
    return None


def _capital_ratio_row(
    rows: Mapping[str, Mapping[str, Any]], catalogue_check: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = ("cet1_capital", "risk_weighted_assets", "cet1_ratio_disclosed")
    cet1_row = rows["cet1_capital"]
    rwa_row = rows["risk_weighted_assets"]
    disclosed_row = rows["cet1_ratio_disclosed"]
    cet1 = _row_value(rows, "cet1_capital")
    rwa = _row_value(rows, "risk_weighted_assets")
    disclosed = _row_value(rows, "cet1_ratio_disclosed")
    if cet1 is None or rwa is None or disclosed is None:
        return _check_row(
            catalogue_check, "not_evaluable",
            tolerance=_CAPITAL_RATIO_TOLERANCE, evidence=evidence,
            reason="missing_dependency",
        )
    if rwa == 0:
        return _check_row(
            catalogue_check, "not_evaluable",
            tolerance=_CAPITAL_RATIO_TOLERANCE, evidence=evidence,
            reason="division_by_zero",
        )
    # The arithmetic may only mix one date and one regulatory approach: a
    # ratio disclosed under the advanced approach against standardized RWA
    # (or a prior-instant operand) is not the same calculation.
    period_ends = {
        cet1_row["period"].get("end"),
        rwa_row["period"].get("end"),
        disclosed_row["period"].get("end"),
    }
    if len(period_ends) > 1 or (
        _row_methodology(disclosed_row) != _row_methodology(rwa_row)
    ):
        return _check_row(
            catalogue_check, "not_evaluable",
            tolerance=_CAPITAL_RATIO_TOLERANCE, evidence=evidence,
            reason="unit_mismatch",
        )
    computed = (cet1 / rwa).quantize(_RATIO_QUANTUM, rounding=ROUND_HALF_EVEN)
    status = (
        "pass" if abs(computed - disclosed) <= _CAPITAL_RATIO_TOLERANCE else "fail"
    )
    return _check_row(
        catalogue_check, status, tolerance=_CAPITAL_RATIO_TOLERANCE,
        evidence=evidence,
    )


def _closing_tolerance(
    ledger: RawFactLedger, closing_row: Mapping[str, Any]
) -> Decimal:
    """1x10^-d from the closing fact's decimals attribute (B.3)."""
    for occurrence_id in closing_row.get("source_occurrence_ids") or []:
        occurrence = ledger.by_id(occurrence_id)
        if (
            occurrence is not None
            and occurrence.decimals is not None
            and occurrence.decimals != "INF"
        ):
            return Decimal(1).scaleb(-int(occurrence.decimals))
    return Decimal("0")


def _rollforward_row(
    rows: Mapping[str, Mapping[str, Any]],
    catalogue_check: Mapping[str, Any],
    ledger: RawFactLedger,
) -> dict[str, Any]:
    evidence = (
        "allowance_for_credit_losses",
        "credit_loss_expense_financing_receivables",
        "net_write_offs",
    )
    provision_row = rows["credit_loss_expense_financing_receivables"]
    write_offs_row = rows["net_write_offs"]
    provision = _row_value(rows, "credit_loss_expense_financing_receivables")
    write_offs = _row_value(rows, "net_write_offs")
    closing = _row_value(rows, "allowance_for_credit_losses")
    if provision is None or write_offs is None or closing is None:
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="missing_dependency",
        )
    provision_period = provision_row.get("period") or {}
    write_offs_period = write_offs_row.get("period") or {}
    if provision_period.get("kind") != "duration" or not provision_period.get(
        "start"
    ):
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="missing_dependency",
        )
    if (write_offs_period.get("start"), write_offs_period.get("end")) != (
        provision_period.get("start"),
        provision_period.get("end"),
    ):
        # Provision and write-offs must cover the same window or the
        # rollforward adds unlike flows.
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="unit_mismatch",
        )
    # The flows are year-to-date, so the opening is the day before the YTD
    # window opened — the prior fiscal period end. The latest allowance
    # instant before por would instead open a 10-Q at the prior quarter end
    # against nine-month flows.
    opening_instant = date.fromisoformat(
        str(provision_period["start"])
    ) - timedelta(days=1)
    opening = _instant_value(ledger, _ALLOWANCE_CONCEPTS, opening_instant)
    if opening is None:
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="missing_dependency",
        )
    tolerance = _closing_tolerance(ledger, rows["allowance_for_credit_losses"])
    expected = opening + provision - write_offs
    status = "pass" if abs(expected - closing) <= tolerance else "fail"
    return _check_row(
        catalogue_check, status, tolerance=tolerance, evidence=evidence
    )


def _cet1_vs_minimum_row(
    rows: Mapping[str, Mapping[str, Any]], catalogue_check: Mapping[str, Any]
) -> dict[str, Any]:
    """Re-decide the placeholder relation after the disclosed rows exist.

    The framework evaluated the placeholder (inverted, and before the cells
    were valued); the true relation is minimum <= CET1 ratio, decided only
    when both cells sit at the same instant under the same regulatory
    approach.
    """
    evidence = ("cet1_ratio_disclosed", "regulatory_minimum_disclosed")
    cet1_row = rows["cet1_ratio_disclosed"]
    minimum_row = rows["regulatory_minimum_disclosed"]
    cet1 = _row_value(rows, "cet1_ratio_disclosed")
    minimum = _row_value(rows, "regulatory_minimum_disclosed")
    if cet1 is None or minimum is None:
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="missing_dependency",
        )
    if cet1_row["period"].get("end") != minimum_row["period"].get(
        "end"
    ) or _row_methodology(cet1_row) != _row_methodology(minimum_row):
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="unit_mismatch",
        )
    status = "pass" if minimum <= cet1 else "fail"
    return _check_row(catalogue_check, status, evidence=evidence)


def _nii_row(
    rows: Mapping[str, Mapping[str, Any]],
    catalogue_check: Mapping[str, Any],
    ledger: RawFactLedger,
    por: date,
    extra_limitations: list[str],
) -> dict[str, Any]:
    evidence = ("net_interest_income",)
    nii = _row_value(rows, "net_interest_income")
    if nii is None:
        return _check_row(
            catalogue_check, "not_evaluable", evidence=evidence,
            reason="missing_dependency",
        )
    revenue = _primary_duration_value(ledger, _CORE_REVENUE_CONCEPTS, por)
    if revenue is not None and revenue == nii:
        # The frozen catalogue carries no bank_interest_not_contract_revenue
        # reason code, so the check row keeps a null reason and the finding
        # rides in limitations.
        extra_limitations.append(_NII_REVENUE_LIMITATION)
        return _check_row(catalogue_check, "fail", evidence=evidence)
    return _check_row(catalogue_check, "pass", evidence=evidence)


# ---------------------------------------------------------------------------
# A.4v2 (dev corpus banks_v1): disclosed regulatory table cells.
#
# Three of the six reserved disclosed fields resolve from standard-taxonomy
# iXBRL facts that are the displayed cells of the filing's capital-adequacy /
# credit-quality tables. US bank filings dimension exactly those cells, so an
# explicit rule — not the framework's undimensioned-only FactMapping — picks
# the consolidated entity's cell:
#
#   entity rule (member local names, case-insensitive; no issuer extension
#   namespace is ever named here): an undimensioned fact wins, else a member
#   naming the consolidated entity — "ConsolidatedEntities" (srt), then
#   "ParentCompany" (srt; the consolidated parent in these tables), then
#   "BankHoldingCompan" (the standard regulator phrase for the top holding
#   company). A fact whose only entity members match none of those (depositary
#   subsidiaries, bank N.A. members, portfolio segments) is NOT the issuer's
#   consolidated cell and never resolves the field.
#
#   methodology rule: when the disclosed cells carry the regulatory-approach
#   dimension and both a "standardized" and an "advanced" member report
#   different values, the CET1 ratio takes the LOWER of the two (the binding
#   constraint) and a limitation says so, while the regulatory minimum instead
#   follows the approach of the chosen CET1 ratio cell (a minimum belongs to
#   one approach; a lower-of minimum would splice two regimes); any other
#   conflicting reads leave the field reserved.
#
#   period rule: instant fields at exactly period_of_report — the capital
#   tables display the current period next to comparative columns, and a
#   prior-instant comparative cell is never the current cell.
# ---------------------------------------------------------------------------

_CET1_RATIO_CONCEPTS = (
    # Dev corpus (WFC 10-Q, PNC 10-K) carries this 2018+ spelling; the
    # 2011-2022 spelling stays second as the older equivalent.
    "us-gaap:CommonEquityTierOneCapitalRatio",
    "us-gaap:CapitalAdequacyCommonEquityTier1CapitalRatio",
)
_REGULATORY_MINIMUM_CONCEPTS = (
    "us-gaap:BankingRegulationCommonEquityTierOneRiskBasedCapitalRatioCapitalAdequacyMinimum",
)
_NPL_CONCEPTS = (
    "us-gaap:FinancingReceivableExcludingAccruedInterestNonaccrual",
)
# The disclosed-total marker the credit-quality tables carry on their
# nonperforming row (a portfolio-segment member never matches it).
_NPL_MEMBER_HINT = "nonperforming"

_ENTITY_MEMBER_HINTS = (
    ("consolidatedentities", 1),
    ("parentcompany", 2),
    ("bankholdingcompan", 3),
)
_METHODOLOGY_HINTS = ("standardized", "advanced")
_APPROACH_MATCHED_LIMITATION = (
    "pk11.regulatory_minimum_disclosed: approach matched to cet1_ratio_disclosed"
)
_ENTITY_OUT_TIER = 4
_TABLE_CELL_RULE_SUFFIX = ".table/v1"
_TABLE_ID_MAX_CHARS = 256
XLINK = "{http://www.w3.org/1999/xlink}"


def _member_local(qname: Any) -> str:
    text = str(qname)
    local = text.rsplit("}", 1)[-1] if text.startswith("{") else text.rsplit(":", 1)[-1]
    return local.lower()


def _dimension_pairs(dimensions: Any) -> list[tuple[str, str]]:
    """(axis, member) pairs from a context's canonical pair tuple or mapping."""
    if isinstance(dimensions, Mapping):
        return [(str(axis), str(member)) for axis, member in dimensions.items()]
    pairs: list[tuple[str, str]] = []
    for item in dimensions or ():
        try:
            axis, member = item
        except (TypeError, ValueError):
            continue
        pairs.append((str(axis), str(member)))
    return pairs


def _occurrence_members(occurrence: Any) -> list[str]:
    context = occurrence.context
    pairs = _dimension_pairs(context.explicit_dimensions)
    pairs += _dimension_pairs(context.typed_dimensions)
    return [_member_local(member) for _axis, member in pairs]


def _entity_tier(occurrence: Any) -> int:
    """0 = the consolidated entity's cell; 4 = a member that is not it."""
    members = _occurrence_members(occurrence)
    if not members:
        return 0
    tier = _ENTITY_OUT_TIER
    for member in members:
        if any(hint in member for hint in _METHODOLOGY_HINTS):
            # A regulatory-approach member never decides the entity level.
            continue
        for hint, rank in _ENTITY_MEMBER_HINTS:
            if hint in member:
                tier = min(tier, rank)
    return tier


def _methodology_of(occurrence: Any) -> str | None:
    """The occurrence's regulatory-approach member (lowercased local), if any."""
    for member in _occurrence_members(occurrence):
        if any(hint in member for hint in _METHODOLOGY_HINTS):
            return member
    return None


def _numeric_value(occurrence: Any) -> Decimal | None:
    """The occurrence's numeric value; the ledger may carry it as text."""
    if occurrence.is_nil:
        return None
    value = occurrence.parsed_value
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return None


def _unit_admitted(occurrence: Any, catalogue_unit: str | None) -> bool:
    equivalents = _unit_equivalents(catalogue_unit)
    if equivalents is None:
        return True
    return _unit_measure(occurrence.unit) in equivalents


def _resolve_disclosed(
    ledger: RawFactLedger,
    concepts: tuple[str, ...],
    por: date,
    *,
    catalogue_unit: str | None,
    member_hint: str | None = None,
    follow_cet1_approach: bool = False,
    cet1_methodology: str | None = None,
) -> tuple[Decimal, Any, str] | None:
    """(value, occurrence, rule) for one disclosed cell.

    ``rule`` names the tie-break that produced the value: ``""`` (a single
    disclosed figure), ``"lower_of_approaches"`` or ``"approach_matched"``.

    ``member_hint`` switches the dimension rule from the consolidated-entity
    tiers to a single marker member (the nonperforming-total row): only facts
    whose EVERY member carries the hint (or that are undimensioned) are the
    disclosed total; portfolio-segment members exclude a fact.

    ``follow_cet1_approach`` (the regulatory minimum only): when the
    period-of-report cells disagree under both regulatory approaches, the
    occurrence whose methodology member equals ``cet1_methodology`` (the
    chosen CET1 ratio cell's) wins — a minimum belongs to one approach, so
    the lower-of splice never applies to it. Without a CET1 methodology to
    follow, or with no matching cell, the field stays reserved.
    """
    for concept in concepts:
        tiered: dict[int, list[Any]] = {}
        for occurrence in ledger.events:
            if occurrence.concept_qname != concept:
                continue
            value = _numeric_value(occurrence)
            if value is None or occurrence.context.instant is None:
                continue
            if occurrence.context.instant != por:
                continue  # only the period-of-report column is the current cell
            if not _unit_admitted(occurrence, catalogue_unit):
                continue
            if member_hint is not None:
                members = _occurrence_members(occurrence)
                if members and not all(member_hint in m for m in members):
                    continue
                tier = 0
            else:
                tier = _entity_tier(occurrence)
                if tier >= _ENTITY_OUT_TIER:
                    continue
            tiered.setdefault(tier, []).append(occurrence)
        if not tiered:
            continue
        candidates = tiered[min(tiered)]
        values = {_numeric_value(item) for item in candidates}
        if len(values) == 1:
            return values.pop(), candidates[0], ""
        if len(values) > 2:
            continue  # a conflict the approach rule cannot name: stay reserved
        members_at = {
            member
            for item in candidates
            for member in _occurrence_members(item)
        }
        approaches = [
            member for member in members_at if any(h in member for h in _METHODOLOGY_HINTS)
        ]
        if len(approaches) < 2:
            continue  # differing values without both approaches: never guess
        if follow_cet1_approach:
            if cet1_methodology is None:
                continue  # no chosen CET1 approach to follow: stay reserved
            matched = [
                item for item in candidates
                if _methodology_of(item) == cet1_methodology
            ]
            matched_values = {_numeric_value(item) for item in matched}
            if len(matched_values) == 1:
                winner = min(matched, key=lambda item: item.occurrence_id)
                return _numeric_value(winner), winner, "approach_matched"
            continue  # no single cell under the CET1 approach: stay reserved
        # Both regulatory approaches disclosed different figures: the lower
        # ratio is the binding constraint.
        winner = min(candidates, key=lambda item: (_numeric_value(item), item.occurrence_id))
        return _numeric_value(winner), winner, "lower_of_approaches"
    return None


def _presentation_table_coordinates(
    members: Mapping[str, bytes] | None, concept_local: str
) -> tuple[str, int] | None:
    """(table_id, row) from the filing's own presentation linkbase.

    The first presentation role (in linkbase order) that presents the concept
    names the displayed table; the concept's position among that role's arcs
    (sorted by the arcs' declared order) is its row. No presentation evidence
    means no table-cell row — coordinates are never invented.
    """
    if not isinstance(members, Mapping):
        return None
    pre_bytes = next(
        (payload for name, payload in sorted(members.items()) if name.endswith("_pre.xml")),
        None,
    )
    if not pre_bytes:
        return None
    try:
        root = ET.fromstring(pre_bytes)
    except ET.ParseError:
        return None
    for link in root.iter():
        if link.tag.rsplit("}", 1)[-1] != "presentationLink":
            continue
        table_id = link.get(f"{XLINK}role")
        if not isinstance(table_id, str) or not table_id or len(table_id) > _TABLE_ID_MAX_CHARS:
            continue
        locals_by_id: dict[str, str] = {}
        for loc in link:
            if loc.tag.rsplit("}", 1)[-1] != "loc":
                continue
            href = loc.get(f"{XLINK}href") or ""
            local = href.rsplit("_", 1)[-1] if "#" in href else ""
            if local:
                locals_by_id[loc.get(f"{XLINK}label") or ""] = local
        ordered: list[tuple[float, str]] = []
        for arc in link:
            if arc.tag.rsplit("}", 1)[-1] != "presentationArc":
                continue
            target = locals_by_id.get(arc.get(f"{XLINK}to") or "")
            if target is None:
                continue
            try:
                order = float(arc.get("order") or 0.0)
            except ValueError:
                order = 0.0
            ordered.append((order, target))
        ordered.sort()
        for row, (_order, target) in enumerate(ordered):
            if target == concept_local:
                return table_id, row
    return None


def _concept_instant_column(
    ledger: RawFactLedger, concept: str, instant: date
) -> int | None:
    """0-based position of ``instant`` among the concept's instants, latest first."""
    instants = sorted(
        {
            item.context.instant
            for item in ledger.events
            if item.concept_qname == concept
            and item.context is not None
            and item.context.instant is not None
        },
        reverse=True,
    )
    try:
        return instants.index(instant)
    except ValueError:
        return None


def _table_cell_digest(concepts: tuple[str, ...], *, member_hint: str | None) -> str:
    payload = {
        "concepts": list(concepts),
        "entity_hints": [hint for hint, _rank in _ENTITY_MEMBER_HINTS]
        if member_hint is None
        else [member_hint],
        "methodology": "lower_ratio_when_both_approaches_disclosed",
        "period": "instant_equal_to_period_of_report",
        "table": "presentation_linkbase_first_role_v1",
    }
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


_DISCLOSED_FIELD_RULES = {
    "cet1_ratio_disclosed": (_CET1_RATIO_CONCEPTS, None),
    "regulatory_minimum_disclosed": (_REGULATORY_MINIMUM_CONCEPTS, None),
    "npl_or_npa_disclosed": (_NPL_CONCEPTS, _NPL_MEMBER_HINT),
}
# cet1_ratio_disclosed is valued first; the minimum's approach-conflict rule
# consumes the chosen CET1 occurrence, so this iteration order is load-bearing.
_DISCLOSED_FIELD_ORDER = (
    "cet1_ratio_disclosed",
    "regulatory_minimum_disclosed",
    "npl_or_npa_disclosed",
)
_RATIO_RANGE_FIELDS = frozenset({"cet1_ratio_disclosed", "regulatory_minimum_disclosed"})
_DISCLOSED_FIELD_DIGESTS = {
    field_id: _table_cell_digest(concepts, member_hint=member_hint)
    for field_id, (concepts, member_hint) in _DISCLOSED_FIELD_RULES.items()
}


def _rewrite_one_disclosed_row(
    row: dict[str, Any],
    concepts: tuple[str, ...],
    *,
    catalogue: Mapping[str, Any],
    catalogue_field: Mapping[str, Any],
    ledger: RawFactLedger,
    por: date,
    presentation_members: Mapping[str, bytes] | None,
    limitations: list[str],
    member_hint: str | None = None,
    follow_cet1_approach: bool = False,
    cet1_methodology: str | None = None,
) -> Any:
    """Value one disclosed field as a table-cell row.

    Returns the occurrence the row was valued from, or ``None`` when the row
    stayed reserved (no admissible cell, or no honest table evidence) or was
    refused as out of range.
    """
    field_id = row["field_id"]
    resolved = _resolve_disclosed(
        ledger,
        concepts,
        por,
        catalogue_unit=catalogue_field.get("unit"),
        member_hint=member_hint,
        follow_cet1_approach=follow_cet1_approach,
        cet1_methodology=cet1_methodology,
    )
    if resolved is None:
        return None
    value, occurrence, rule = resolved
    concept_local = occurrence.concept_qname.rsplit(":", 1)[-1]
    coordinates = _presentation_table_coordinates(
        presentation_members, concept_local
    )
    column = _concept_instant_column(
        ledger, occurrence.concept_qname, occurrence.context.instant
    )
    if coordinates is None or column is None:
        return None  # no honest table evidence for this cell: stay reserved
    if field_id in _RATIO_RANGE_FIELDS and not (
        Decimal(0) <= value <= Decimal(1)
    ):
        # A ratio cell outside 0..1 is a percent or basis-point figure in the
        # wrong scale; refuse it as a typed absence the way the framework
        # refuses a fact whose unit does not satisfy the catalogue unit.
        row.update(
            {
                "quality_state": "not_evaluable",
                "non_value_state": "not_evaluable",
                "coverage_state": "unmapped",
                "reason": _project_reason(
                    "unit_mismatch", catalogue, field_id, limitations
                ),
                "concept": occurrence.concept_qname,
                "source_occurrence_ids": [occurrence.occurrence_id],
            }
        )
        return None
    table_id, table_row = coordinates
    row.update(
        {
            "quality_state": "valued",
            "non_value_state": None,
            "coverage_state": "source_trace_complete",
            "reason": None,
            "value": decimal_text(value),
            "text_value": None,
            "evidence_kind": "table_cell",
            "required_evidence_kind": "table_cell",
            "concept": occurrence.concept_qname,
            "taxonomy": occurrence.concept_qname.split(":", 1)[0],
            "source_occurrence_ids": [occurrence.occurrence_id],
            "dimensions": [
                {"axis": axis, "member": member}
                for axis, member in sorted(
                    _dimension_pairs(occurrence.context.explicit_dimensions)
                )
            ],
            "mapping_rule_id": f"PK11.{field_id}{_TABLE_CELL_RULE_SUFFIX}",
            "mapping_rule_digest": _DISCLOSED_FIELD_DIGESTS[field_id],
            "table_cell": {
                "table_id": table_id,
                "row": table_row,
                "column": column,
            },
            "period": {
                "kind": "instant",
                "end": occurrence.context.instant.isoformat(),
            },
            "unit": catalogue_field.get("unit"),
        }
    )
    if rule == "lower_of_approaches":
        limitations.append(
            f"pk11.{field_id}: standardized and advanced approaches both "
            "disclosed; lower ratio taken"
        )
    elif rule == "approach_matched":
        limitations.append(_APPROACH_MATCHED_LIMITATION)
    return occurrence


def _rewrite_disclosed_rows(
    envelope: dict[str, Any],
    pack_input: PackInput,
    ledger: RawFactLedger,
    por: date,
    limitations: list[str],
) -> None:
    """Value the three resolvable disclosed fields as table-cell rows."""
    catalogue = contract.load_pack_schema("PK11")
    catalogue_fields = {
        row["field_id"]: row for row in catalogue["fields"]
    }
    presentation_members = None
    for package in pack_input.packages:
        candidate = getattr(package, "members", None)
        if isinstance(candidate, Mapping) and any(
            name.endswith("_pre.xml") for name in candidate
        ):
            presentation_members = candidate
            break
    rows = {row["field_id"]: row for row in envelope["fields"]}
    chosen_cet1_occurrence = None
    for field_id in _DISCLOSED_FIELD_ORDER:
        row = rows.get(field_id)
        if row is None or row["quality_state"] == "valued":
            continue
        concepts, member_hint = _DISCLOSED_FIELD_RULES[field_id]
        follows_cet1 = field_id == "regulatory_minimum_disclosed"
        chosen = _rewrite_one_disclosed_row(
            row,
            concepts,
            catalogue=catalogue,
            catalogue_field=catalogue_fields[field_id],
            ledger=ledger,
            por=por,
            presentation_members=presentation_members,
            limitations=limitations,
            member_hint=member_hint,
            follow_cet1_approach=follows_cet1,
            cet1_methodology=(
                _methodology_of(chosen_cet1_occurrence)
                if follows_cet1 and chosen_cet1_occurrence is not None
                else None
            ),
        )
        if field_id == "cet1_ratio_disclosed":
            chosen_cet1_occurrence = chosen


def _refresh_coverage(envelope: dict[str, Any]) -> None:
    """Re-tally coverage from the field rows after finalize rewrites."""
    counts = {key: 0 for key in (
        "valued_fields",
        "missing_fields",
        "unsupported_fields",
        "not_evaluable_fields",
        "not_applicable_fields",
    )}
    for row in envelope["fields"]:
        key = contract.QUALITY_TO_COVERAGE.get(row["quality_state"])
        if key is not None:
            counts[key] += 1
    envelope["coverage"].update(counts)
    if counts["valued_fields"] > 0:
        envelope["coverage"]["disclosure_coverage_state"] = "present"


@dataclass(frozen=True)
class Pk11Producer(PackProducer):
    """PK11 declaration plus the bank-sector finalize hook (see module docstring)."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact (B.5)
        from ..ixbrl_raw_ledger import parse_and_convert_golden_packages

        envelope = result
        # Same converter the framework used (call-time import), so a test
        # double is honoured identically by both passes.
        ledger, _filing_metadata, _report = parse_and_convert_golden_packages(
            pack_input.packages
        )
        catalogue_checks = {
            row["check_id"]: row for row in contract.load_pack_schema("PK11")["checks"]
        }
        rows = {row["field_id"]: row for row in envelope["fields"]}
        allowance_period_end = rows["allowance_for_credit_losses"]["period"]["end"]
        por = date.fromisoformat(str(allowance_period_end))

        limitations: list[str] = []
        if detectors.issuer_class_for_sic(pack_input.issuer_sic) == "bank":
            limitations.append(
                "pk11.industrial_basis_excluded: "
                + ",".join(_A30_EXCLUDED_CORE_METRICS)
            )
        # Dev corpus banks_v1: value the resolvable disclosed regulatory table
        # cells BEFORE the checks read them and before the reserved limitation
        # is decided.
        _rewrite_disclosed_rows(envelope, pack_input, ledger, por, limitations)
        reserved_not_valued = any(
            rows[field_id]["quality_state"] != "valued"
            for field_id in _TABLE_CELL_FIELDS
        )
        if reserved_not_valued:
            limitations.append("pk11.table_cell_reserved")
        if rows["credit_loss_expense_off_balance_sheet"]["quality_state"] != "valued":
            limitations.append(_PROVISION_TOTAL_LIMITATION)

        check_limitations: list[str] = []
        recomputed = {
            "acl_coverage": _acl_coverage_row(
                rows, catalogue_checks["acl_coverage"], check_limitations
            ),
            "capital_ratio_arithmetic": _capital_ratio_row(
                rows, catalogue_checks["capital_ratio_arithmetic"]
            ),
            # The framework decided the placeholder before the disclosed rows
            # existed (and never again); re-decide it against the valued rows.
            "cet1_vs_minimum": _cet1_vs_minimum_row(
                rows, catalogue_checks["cet1_vs_minimum"]
            ),
            "provision_vs_acl_rollforward": _rollforward_row(
                rows, catalogue_checks["provision_vs_acl_rollforward"], ledger
            ),
            "nii_not_revenue": _nii_row(
                rows, catalogue_checks["nii_not_revenue"], ledger, por,
                check_limitations,
            ),
        }
        for index, check in enumerate(envelope["checks"]):
            replacement = recomputed.get(check["check_id"])
            if replacement is not None:
                envelope["checks"][index] = replacement
        if limitations or check_limitations:
            envelope["limitations"] = list(
                dict.fromkeys(
                    (*envelope["limitations"], *limitations, *check_limitations)
                )
            )[:32]

        _refresh_coverage(envelope)
        envelope["pack_content_sha256"] = contract.pack_content_digest(envelope)
        errors = contract.validate_pack_result(envelope)
        if errors:
            raise SpecialistPackError(
                "PK11 finalize refused: " + "; ".join(errors[:5])
            )
        return envelope


PRODUCER = Pk11Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    extra_applicability=_bank_class_gate,
)

__all__ = ["PRODUCER", "SPEC"]
