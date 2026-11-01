"""PK05 producer: income tax and uncertain tax positions.

Thin by design — every mapping below is a frozen B.2 declaration over the
shared framework in ``base.py``. The effective-rate reconciliation is the
first pack field whose row set is declared by the issuer's own calculation
linkbase rather than by a fixed concept list (A.2): the chosen role's child
arcs are the rows, the arcs' weights drive the weighted sum identity (A.3),
and an extension child carrying a fact is VALUED because the issuer's own
calculation arc aliases it as a component of the reconciliation (the reading
recorded in ``calculation_linkbase``; a candidate catalogue ruling for the
Q1 held-out evaluation). Deferred-tax detail beyond the catalogue's gross
DTA instant is out of scope, and no number is ever read from narrative text
(R-K4'). Every ``FactMapping`` declares the A.1 precision-consistent
duplicate policy: filings tag one balance in the statement (``decimals=-6``)
and again as a rounded rollforward bound (``decimals=-8``), and those
duplicates reconcile onto the more precise occurrence instead of poisoning
the field as a conflict.
"""
from __future__ import annotations

from decimal import Decimal

from .base import (
    CalculationChildrenMapping,
    CheckRule,
    CrossStatement,
    FactMapping,
    FormulaMapping,
    PackProducer,
    PackSpec,
    Rollforward,
    RuleOperand,
    RuleOutcome,
    TextSpanMapping,
    WeightedSumIdentity,
    formula_ratio,
)

SPEC = PackSpec(
    pack_id="PK05",
    forms=frozenset({"10-K", "10-K/A"}),
    applicability_rule_id="specialist_pack.pk05.applicability/v1",
    applicable_classes=None,
)

ETR_FORMULA_RULE_ID = "pk05.effective_tax_rate_formula/v1"
ETR_VS_DISCLOSED_RULE_ID = "pk05.etr_formula_vs_disclosed/v1"

_FIELD_MAPPINGS = {
    "income_tax_expense": FactMapping(
        ("us-gaap:IncomeTaxExpenseBenefit",),
        duplicate_policy="precision_consistent",
    ),
    "pretax_income": FactMapping(
        (
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
            "ExtraordinaryItemsNoncontrollingInterest",
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
            "MinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ),
        duplicate_policy="precision_consistent",
    ),
    "effective_tax_rate_formula": FormulaMapping(
        rule_id=ETR_FORMULA_RULE_ID,
        inputs=("income_tax_expense", "pretax_income"),
        fn=formula_ratio("income_tax_expense", "pretax_income"),
    ),
    "effective_tax_rate_disclosed": FactMapping(
        ("us-gaap:EffectiveIncomeTaxRateContinuingOperations",),
        duplicate_policy="precision_consistent",
    ),
    "statutory_federal_rate": FactMapping(
        (
            "us-gaap:EffectiveIncomeTaxRateReconciliationAtFederalStatutory"
            "IncomeTaxRate",
        ),
        duplicate_policy="precision_consistent",
    ),
    "etr_reconciliation_line": CalculationChildrenMapping(
        field_id="etr_reconciliation_line",
        parent_concept="us-gaap:IncomeTaxExpenseBenefit",
        child_prefix="us-gaap:IncomeTaxReconciliation",
    ),
    "utp_opening": FactMapping(
        ("us-gaap:UnrecognizedTaxBenefits",),
        period_select="opening_instant",
        duplicate_policy="precision_consistent",
    ),
    "utp_closing": FactMapping(
        ("us-gaap:UnrecognizedTaxBenefits",),
        duplicate_policy="precision_consistent",
    ),
    "utp_rollforward_increases_prior_period": FactMapping(
        (
            "us-gaap:UnrecognizedTaxBenefitsIncreasesResultingFromPriorPeriod"
            "TaxPositions",
        ),
        duplicate_policy="precision_consistent",
    ),
    "utp_rollforward_decreases_prior_period": FactMapping(
        (
            "us-gaap:UnrecognizedTaxBenefitsDecreasesResultingFromPriorPeriod"
            "TaxPositions",
        ),
        duplicate_policy="precision_consistent",
    ),
    "utp_rollforward_increases_current_period": FactMapping(
        (
            "us-gaap:UnrecognizedTaxBenefitsIncreasesResultingFromCurrentPeriod"
            "TaxPositions",
        ),
        duplicate_policy="precision_consistent",
    ),
    "utp_rollforward_settlements": FactMapping(
        (
            "us-gaap:UnrecognizedTaxBenefitsDecreasesResultingFrom"
            "SettlementsWithTaxingAuthorities",
        ),
        duplicate_policy="precision_consistent",
    ),
    "utp_rollforward_lapse_of_statute": FactMapping(
        (
            "us-gaap:UnrecognizedTaxBenefitsReductionsResultingFromLapseOf"
            "ApplicableStatuteOfLimitations",
        ),
        duplicate_policy="precision_consistent",
    ),
    "utp_impact_on_etr": FactMapping(
        ("us-gaap:UnrecognizedTaxBenefitsThatWouldImpactEffectiveTaxRate",),
        duplicate_policy="precision_consistent",
    ),
    "income_taxes_paid": FactMapping(
        (
            "us-gaap:IncomeTaxesPaidNet",
            "us-gaap:IncomeTaxesPaid",
        ),
        duplicate_policy="precision_consistent",
    ),
    "deferred_tax_assets_gross": FactMapping(
        ("us-gaap:DeferredTaxAssetsGross",),
        duplicate_policy="precision_consistent",
    ),
    # Reserved (A.4): the tax note's own text is span evidence a later lane owns.
    "tax_note_text_block": TextSpanMapping(),
}

_CHECKS = (
    WeightedSumIdentity(
        check_id="etr_reconciliation_sum",
        addends="etr_reconciliation_line",
        total="income_tax_expense",
    ),
    Rollforward(
        check_id="utp_rollforward",
        opening="utp_opening",
        additions=(
            "utp_rollforward_increases_prior_period",
            "utp_rollforward_increases_current_period",
        ),
        reductions=(
            "utp_rollforward_decreases_prior_period",
            "utp_rollforward_settlements",
            "utp_rollforward_lapse_of_statute",
        ),
        closing="utp_closing",
        implied_limitation_template=(
            "utp_rollforward: refused to imply {field_id} = {implied}"
            " (R-K3: never an implied value)"
        ),
    ),
    CrossStatement(
        check_id="etr_formula_vs_disclosed",
        operands=(
            "effective_tax_rate_formula",
            "effective_tax_rate_disclosed",
        ),
        rule=ETR_VS_DISCLOSED_RULE_ID,
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


def _etr_formula_vs_disclosed(operands: dict) -> RuleOutcome:
    """A.6: the formula rate must tie to the disclosed rate within the
    disclosed fact's own ``decimals`` (its stated precision after scale)."""
    formula = operands["effective_tax_rate_formula"]
    disclosed = operands["effective_tax_rate_disclosed"]
    if formula.value is None or disclosed.value is None:
        return RuleOutcome("not_evaluable", "missing_dependency")
    tolerance = Decimal(1).scaleb(-_decimals_of(disclosed))
    status = (
        "pass" if abs(formula.value - disclosed.value) <= tolerance else "fail"
    )
    return RuleOutcome(status, None, tolerance)


CHECK_RULES = {
    ETR_VS_DISCLOSED_RULE_ID: CheckRule(
        rule_id=ETR_VS_DISCLOSED_RULE_ID,
        fn=_etr_formula_vs_disclosed,
    ),
}

PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    check_rules=CHECK_RULES,
)

__all__ = ["CHECK_RULES", "PRODUCER", "SPEC"]
