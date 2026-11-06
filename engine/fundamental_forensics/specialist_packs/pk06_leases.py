"""PK06 producer: leases and off-balance commitments.

Thin by design — every mapping below is a frozen B.2 declaration over the
shared framework in ``base.py``. Bank lessor / financing receivable concepts
are absent on purpose: they are never PK06 rows.
"""
from __future__ import annotations

from .base import (
    CrossStatement,
    FactMapping,
    PackProducer,
    PackSpec,
    SumIdentity,
)

SPEC = PackSpec(
    pack_id="PK06",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="specialist_pack.pk06.applicability/v1",
    applicable_classes=None,
)

_FIELD_MAPPINGS = {
    "rou_assets_operating": FactMapping(
        ("us-gaap:OperatingLeaseRightOfUseAsset",)
    ),
    "rou_assets_finance": FactMapping(
        ("us-gaap:FinanceLeaseRightOfUseAsset",)
    ),
    "operating_lease_liability_current": FactMapping(
        ("us-gaap:OperatingLeaseLiabilityCurrent",)
    ),
    "operating_lease_liability_noncurrent": FactMapping(
        ("us-gaap:OperatingLeaseLiabilityNoncurrent",)
    ),
    "finance_lease_liability_current": FactMapping(
        ("us-gaap:FinanceLeaseLiabilityCurrent",)
    ),
    "finance_lease_liability_noncurrent": FactMapping(
        ("us-gaap:FinanceLeaseLiabilityNoncurrent",)
    ),
    "lease_cost_operating": FactMapping(("us-gaap:OperatingLeaseCost",)),
    "lease_cost_finance_amortization": FactMapping(
        ("us-gaap:FinanceLeaseRightOfUseAssetAmortization",)
    ),
    "lease_cost_finance_interest": FactMapping(
        ("us-gaap:FinanceLeaseInterestExpense",)
    ),
    "lease_cost_variable": FactMapping(("us-gaap:VariableLeaseCost",)),
    "lease_cost_short_term": FactMapping(("us-gaap:ShortTermLeaseCost",)),
    "lease_cost_total": FactMapping(("us-gaap:LeaseCost",)),
    "lease_cash_payments": FactMapping(("us-gaap:OperatingLeasePayments",)),
    "weighted_average_remaining_term": FactMapping(
        ("us-gaap:OperatingLeaseWeightedAverageRemainingLeaseTerm1",)
    ),
    "weighted_average_discount_rate": FactMapping(
        ("us-gaap:OperatingLeaseWeightedAverageDiscountRatePercent",)
    ),
    "undiscounted_payments_total": FactMapping(
        (
            "us-gaap:LesseeOperatingLeaseLiabilityPaymentsDue",
            "us-gaap:OperatingAndFinanceLeaseLiabilityPaymentsDue",
        )
    ),
    "undiscounted_payments_by_year": FactMapping(
        ("us-gaap:LesseeOperatingLeaseLiabilityPaymentsDueNextTwelveMonths",)
    ),
    "offbalance_purchase_commitments": FactMapping(
        (
            "us-gaap:UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
            "us-gaap:PurchaseObligation",
        )
    ),
    "operating_lease_liability_total": FactMapping(
        ("us-gaap:OperatingLeaseLiability",)
    ),
    "finance_lease_liability_total": FactMapping(
        ("us-gaap:FinanceLeaseLiability",)
    ),
    "lease_imputed_interest": FactMapping(
        (
            "us-gaap:LesseeOperatingLeaseLiabilityUndiscountedExcessAmount",
            "us-gaap:OperatingAndFinanceLeaseLiabilityUndiscountedExcessAmount",
        )
    ),
}

_CHECKS = (
    SumIdentity(
        check_id="lease_liability_split_vs_total",
        addends=(
            "operating_lease_liability_current",
            "operating_lease_liability_noncurrent",
        ),
        total="operating_lease_liability_total",
    ),
    SumIdentity(
        check_id="lease_liability_split_vs_total",
        addends=(
            "finance_lease_liability_current",
            "finance_lease_liability_noncurrent",
        ),
        total="finance_lease_liability_total",
    ),
    # undiscounted_total - imputed_interest = operating_total + finance_total,
    # stated as sum(imputed, operating_total, finance_total) = undiscounted_total.
    # Evaluated honestly: on a filing whose standard ladder is operating-only
    # while the liabilities include finance leases, this identity fails and the
    # failure is reported, never bent into a pass.
    SumIdentity(
        check_id="undiscounted_minus_imputed_equals_liability",
        addends=(
            "lease_imputed_interest",
            "operating_lease_liability_total",
            "finance_lease_liability_total",
        ),
        total="undiscounted_payments_total",
    ),
    CrossStatement(
        check_id="commitments_not_in_contingencies",
        left="offbalance_purchase_commitments",
        right="pk08:loss_contingency_accrual",
        relation="disjoint",
    ),
)

PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    limitations=(
        "undiscounted_payments_by_year: only the next-twelve-months row is"
        " produced; the by-year maturity table is a later lane",
    ),
)

__all__ = ["PRODUCER", "SPEC"]
