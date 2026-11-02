"""PK01 producer: debt, liquidity, covenants and maturities.

Thin by design — every mapping below is a frozen B.2 declaration over the
shared framework in ``base.py``. Finance-lease liabilities are absent on
purpose: PK06 owns them, and the instrument rows exclude lease members.
The core-catalogue aliases consumed here (short_term_debt, long_term_debt,
long_term_debt_current, cash_and_cash_equivalents, short_term_investments,
current_assets, current_liabilities) are copied exactly from
``config/fundamental_forensics/metrics/v1/mappings/core.yaml``.
"""
from __future__ import annotations

from .base import (
    DimensionedFactMapping,
    FactMapping,
    FactOrFormulaMapping,
    FormulaMapping,
    PackProducer,
    PackSpec,
    Presence,
    Reconcile,
    SumIdentity,
    TextSpanMapping,
    formula_difference,
    formula_ratio,
    formula_sum,
)

SPEC = PackSpec(
    pack_id="PK01",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="specialist_pack.pk01.applicability/v1",
    applicable_classes=None,
    field_class_exclusions={
        "current_ratio": (
            frozenset({"bank"}),
            "industrial_basis_excluded_for_financial_institution",
        ),
        "working_capital": (
            frozenset({"bank"}),
            "industrial_basis_excluded_for_financial_institution",
        ),
    },
)

_FIELD_MAPPINGS = {
    # Core catalog alias only: the allowlist law owns any CommercialPaper
    # ruling, never this pack.
    "short_term_debt": FactMapping(("us-gaap:ShortTermBorrowings",)),
    "long_term_debt_current": FactMapping(("us-gaap:LongTermDebtCurrent",)),
    # The core long_term_debt alias is the NONCURRENT portion; us-gaap:LongTermDebt
    # includes the current portion and would double-count in the components check.
    "long_term_debt": FactMapping(("us-gaap:LongTermDebtNoncurrent",)),
    "total_debt": FactOrFormulaMapping(
        fact=FactMapping(("us-gaap:DebtLongtermAndShorttermCombinedAmount",)),
        formula=FormulaMapping(
            rule_id="pk01.total_debt.sum/v1",
            inputs=("short_term_debt", "long_term_debt_current", "long_term_debt"),
            fn=formula_sum,
        ),
        limitation_when_formula=(
            "debt_components_vs_total: total_debt is formula-derived from"
            " the same addends"
        ),
    ),
    "debt_maturity_y1": FactMapping(
        (
            "us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
        )
    ),
    "debt_maturity_y2": FactMapping(
        ("us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",)
    ),
    "debt_maturity_y3": FactMapping(
        ("us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",)
    ),
    "debt_maturity_y4": FactMapping(
        ("us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",)
    ),
    "debt_maturity_y5": FactMapping(
        ("us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",)
    ),
    "debt_maturity_after_5y": FactMapping(
        ("us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive",)
    ),
    "debt_carrying_amount_total": FactMapping(
        ("us-gaap:DebtInstrumentCarryingAmount",)
    ),
    # Finance-lease members are excluded: PK06 owns those liabilities.
    "debt_carrying_amount_by_instrument": DimensionedFactMapping(
        concept="us-gaap:DebtInstrumentCarryingAmount",
        primary_axis="us-gaap:DebtInstrumentAxis",
        other_axes_allowed=("us-gaap:LongtermDebtTypeAxis",),
        exclude_member_substrings=("Lease",),
    ),
    "debt_fair_value": DimensionedFactMapping(
        concept="us-gaap:LongTermDebtFairValue",
        primary_axis="us-gaap:FairValueByFairValueHierarchyLevelAxis",
    ),
    "revolver_undrawn_capacity": FactMapping(
        ("us-gaap:LineOfCreditFacilityRemainingBorrowingCapacity",)
    ),
    # Reserved (A.4): the Capital Structure receipt owns covenant wording.
    "covenant_term_observation": TextSpanMapping(),
    "liquidity_total_cash_and_securities": FormulaMapping(
        rule_id="pk01.liquidity_total_cash_and_securities.sum/v1",
        inputs=("cash_and_cash_equivalents", "short_term_investments"),
        fn=formula_sum,
    ),
    "cash_and_cash_equivalents": FactMapping(
        ("us-gaap:CashAndCashEquivalentsAtCarryingValue",)
    ),
    "short_term_investments": FactMapping(
        ("us-gaap:ShortTermInvestments", "us-gaap:MarketableSecuritiesCurrent")
    ),
    "current_assets": FactMapping(("us-gaap:AssetsCurrent",)),
    "current_liabilities": FactMapping(("us-gaap:LiabilitiesCurrent",)),
    "current_ratio": FormulaMapping(
        rule_id="pk01.current_ratio.div/v1",
        inputs=("current_assets", "current_liabilities"),
        fn=formula_ratio("current_assets", "current_liabilities"),
    ),
    "working_capital": FormulaMapping(
        rule_id="pk01.working_capital.diff/v1",
        inputs=("current_assets", "current_liabilities"),
        fn=formula_difference("current_assets", "current_liabilities"),
    ),
}

_CHECKS = (
    SumIdentity(
        check_id="maturity_ladder_vs_carrying",
        addends=(
            "debt_maturity_y1",
            "debt_maturity_y2",
            "debt_maturity_y3",
            "debt_maturity_y4",
            "debt_maturity_y5",
            "debt_maturity_after_5y",
        ),
        total="debt_carrying_amount_total",
    ),
    SumIdentity(
        check_id="debt_components_vs_total",
        addends=("short_term_debt", "long_term_debt_current", "long_term_debt"),
        total="total_debt",
    ),
    Reconcile(
        check_id="instrument_rows_vs_total",
        parts=("debt_carrying_amount_by_instrument",),
        consolidated="debt_carrying_amount_total",
    ),
    Presence(check_id="covenant_span_present", field_id="covenant_term_observation"),
)

PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
)

__all__ = ["PRODUCER", "SPEC"]
