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
"""
from __future__ import annotations

from decimal import Decimal

from .base import (
    CheckRule,
    CrossStatement,
    DimensionedFactMapping,
    FactMapping,
    PackProducer,
    PackSpec,
    Rollforward,
    RuleOperand,
    RuleOutcome,
    SumIdentity,
    TextSpanMapping,
    TypedDimensionedFactMapping,
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

PRODUCER = PackProducer(
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
