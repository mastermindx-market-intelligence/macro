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
closest framework specs for those rows — placeholders the hook replaces —
while ``cet1_vs_minimum`` needs no hook (reserved table-cell operands are
already ``not_evaluable`` + ``missing_dependency`` under the framework).

The A30 limitation ids and the core ``revenue`` aliases are copied exactly
from ``config/fundamental_forensics/metrics/v1/`` (metric_catalog.yaml and
mappings/core.yaml): the core catalogue's own class gating is the declared
source, never this producer's opinion.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Mapping

from .. import detectors
from .. import specialist_pack_contract as contract
from ..raw_ledger import RawFactLedger, decimal_text
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
    formula_sum,
)

SPEC = PackSpec(
    pack_id="PK11",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="pack.pk11.applicability/v1",
    applicable_classes=None,
)

# B.2 concept aliases (us-gaap; priority order; undimensioned).
_ALLOWANCE_CONCEPTS = (
    "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLoss",
    "us-gaap:FinancingReceivableAllowanceForCreditLosses",
)
_PROVISION_FINANCING_CONCEPTS = (
    "us-gaap:FinancingReceivableExcludingAccruedInterestCreditLossExpenseReversal",
    "us-gaap:ProvisionForLoanLeaseAndOtherLosses",
    "us-gaap:ProvisionForLoanLossesExpensed",
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
    "allowance_for_credit_losses": FactMapping(_ALLOWANCE_CONCEPTS),
    "net_write_offs": FactMapping(
        (
            "us-gaap:FinancingReceivableExcludingAccruedInterestAllowanceForCreditLossWriteoffNet",
            "us-gaap:FinancingReceivableAllowanceForCreditLossesWriteOffsNet",
        )
    ),
    "loans_held_for_investment": FactMapping(
        (
            "us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss",
            "us-gaap:LoansAndLeasesReceivableGrossCarryingAmount",
            "us-gaap:LoansAndLeasesReceivableNetReportedAmount",
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
    # Exact under the framework: reserved operands are not_evaluable with
    # missing_dependency; two valued ratio rows would compare left <= right.
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


def _prior_instant_value(
    ledger: RawFactLedger, concepts: tuple[str, ...], before: date
) -> Decimal | None:
    """Latest undimensioned non-nil instant strictly before ``before``.

    Concepts are tried in the field's priority order; conflicting values at
    the same prior instant leave the opening unresolvable (R-K3: never an
    implied zero).
    """
    for concept in concepts:
        candidates = [
            occurrence
            for occurrence in ledger.events
            if occurrence.concept_qname == concept
            and not occurrence.is_nil
            and occurrence.context.instant is not None
            and occurrence.context.instant < before
            and _undimensioned(occurrence)
        ]
        if not candidates:
            continue
        latest = max(occurrence.context.instant for occurrence in candidates)
        values = {
            Decimal(str(occurrence.parsed_value))
            for occurrence in candidates
            if occurrence.context.instant == latest
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


def _capital_ratio_row(
    rows: Mapping[str, Mapping[str, Any]], catalogue_check: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = ("cet1_capital", "risk_weighted_assets", "cet1_ratio_disclosed")
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
    por: date,
) -> dict[str, Any]:
    evidence = (
        "allowance_for_credit_losses",
        "credit_loss_expense_financing_receivables",
        "net_write_offs",
    )
    opening = _prior_instant_value(ledger, _ALLOWANCE_CONCEPTS, por)
    provision = _row_value(rows, "credit_loss_expense_financing_receivables")
    write_offs = _row_value(rows, "net_write_offs")
    closing = _row_value(rows, "allowance_for_credit_losses")
    if (
        opening is None
        or provision is None
        or write_offs is None
        or closing is None
    ):
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
            "provision_vs_acl_rollforward": _rollforward_row(
                rows, catalogue_checks["provision_vs_acl_rollforward"], ledger, por
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
