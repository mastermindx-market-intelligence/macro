"""PK02 producer: stock-based compensation and dilution.

Thin by design — every mapping below is a frozen B.2 declaration over the
shared framework in ``base.py``. The core-catalogue aliases consumed here
(weighted_average_shares_basic, weighted_average_shares_diluted, eps_basic,
eps_diluted, shares_outstanding_cover) are copied exactly from
``config/fundamental_forensics/metrics/v1/mappings/core.yaml``. Capitalized
share-based compensation has no frozen standard alias: ``sbc_capitalized`` is
a declared unmapped field (A.3) and any issuer-extension ruling belongs to
the core catalogue, never this pack.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

from .base import (
    CheckRule,
    CrossStatement,
    FactMapping,
    PackProducer,
    PackSpec,
    RuleOperand,
    RuleOutcome,
    SumIdentity,
)

SPEC = PackSpec(
    pack_id="PK02",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="specialist_pack.pk02.applicability/v1",
    applicable_classes=None,
)

INCOME_STATEMENT_LOCATION_AXIS = "us-gaap:IncomeStatementLocationAxis"
ANTIDILUTIVE_SECURITIES_AXIS = (
    "us-gaap:AntidilutiveSecuritiesExcludedFromComputationOfEarningsPerShare"
    "ByAntidilutiveSecuritiesAxis"
)
CLASS_OF_STOCK_AXIS = "us-gaap:StatementClassOfStockAxis"

PER_CLASS_RULE_ID = "pk02.per_class_shares_vs_cover/v1"
EPS_IDENTITY_RULE_ID = "pk02.eps_identity/v1"

_FIELD_MAPPINGS = {
    "sbc_expense_total": FactMapping(
        (
            "us-gaap:AllocatedShareBasedCompensationExpense",
            "us-gaap:ShareBasedCompensation",
        )
    ),
    # The consolidated row would duplicate sbc_expense_total, so only the
    # IncomeStatementLocationAxis members are rows here.
    "sbc_allocated_by_line": FactMapping(
        ("us-gaap:AllocatedShareBasedCompensationExpense",),
        optional_axes=(INCOME_STATEMENT_LOCATION_AXIS,),
        consolidated_row=False,
        limitation_when_absent=(
            "sbc_allocated_by_line: no IncomeStatementLocationAxis members"
            " tagged"
        ),
    ),
    "weighted_average_shares_basic": FactMapping(
        ("us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",)
    ),
    "weighted_average_shares_diluted": FactMapping(
        ("us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",)
    ),
    "eps_basic": FactMapping(("us-gaap:EarningsPerShareBasic",)),
    "eps_diluted": FactMapping(("us-gaap:EarningsPerShareDiluted",)),
    "antidilutive_securities_excluded": FactMapping(
        (
            "us-gaap:AntidilutiveSecuritiesExcludedFromComputationOf"
            "EarningsPerShareAmount",
        ),
        optional_axes=(ANTIDILUTIVE_SECURITIES_AXIS,),
    ),
    "shares_outstanding_cover": FactMapping(
        ("dei:EntityCommonStockSharesOutstanding",),
        period_select="cover_instant",
        optional_axes=(CLASS_OF_STOCK_AXIS,),
    ),
    "shares_issued_parenthetical": FactMapping(
        ("us-gaap:CommonStockSharesIssued",),
        optional_axes=(CLASS_OF_STOCK_AXIS,),
    ),
    "share_repurchase_amount": FactMapping(
        (
            "us-gaap:PaymentsForRepurchaseOfCommonStock",
            "us-gaap:StockRepurchasedAndRetiredDuringPeriodValue",
        )
    ),
    # A.3: no standard us-gaap alias is frozen for capitalized SBC.
    "sbc_capitalized": FactMapping(concepts=()),
    "dilutive_securities_increment": FactMapping(
        (
            "us-gaap:WeightedAverageNumberDilutedSharesOutstandingAdjustment",
            "us-gaap:IncrementalCommonSharesAttributableToShareBasedPayment"
            "Arrangements",
        )
    ),
    # Equity-component rows are ignored: undimensioned only.
    "net_income_available_to_common": FactMapping(
        (
            "us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic",
            "us-gaap:NetIncomeLoss",
        )
    ),
}

_CHECKS = (
    SumIdentity(
        check_id="basic_to_diluted_reconciliation",
        addends=(
            "weighted_average_shares_basic",
            "dilutive_securities_increment",
        ),
        total="weighted_average_shares_diluted",
    ),
    # A.4 shape: the field's consolidated row is the total, its axis member
    # rows the addends.
    SumIdentity(
        check_id="antidilutive_table_total_vs_rows",
        addends=("antidilutive_securities_excluded",),
        total="antidilutive_securities_excluded",
    ),
    CrossStatement(
        check_id="per_class_shares_vs_cover",
        operands=("shares_outstanding_cover", "shares_issued_parenthetical"),
        rule=PER_CLASS_RULE_ID,
    ),
    CrossStatement(
        check_id="eps_identity",
        operands=(
            "net_income_available_to_common",
            "weighted_average_shares_basic",
            "eps_basic",
            "weighted_average_shares_diluted",
            "eps_diluted",
        ),
        rule=EPS_IDENTITY_RULE_ID,
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


def _class_key(row: dict) -> tuple[tuple[str, str], ...]:
    dimensions = row.get("dimensions") or ()
    return tuple(
        sorted((str(item["axis"]), str(item["member"])) for item in dimensions)
    )


def _per_class_shares_vs_cover(
    operands: dict,
) -> RuleOutcome:
    """Per class member (undimensioned = single class), cover vs parenthetical."""
    cover = operands["shares_outstanding_cover"]
    parenthetical = operands["shares_issued_parenthetical"]
    tolerance = Decimal(1).scaleb(
        -min(_decimals_of(cover), _decimals_of(parenthetical))
    )
    issued_by_class = {
        _class_key(row): row
        for row in parenthetical.rows
        if row.get("quality_state") == "valued"
    }
    for row in cover.rows:
        if row.get("quality_state") != "valued":
            continue
        matched = issued_by_class.get(_class_key(row))
        if matched is None:
            return RuleOutcome("not_evaluable", "missing_dependency", tolerance)
        if (
            abs(Decimal(str(row["value"])) - Decimal(str(matched["value"])))
            > tolerance
        ):
            return RuleOutcome("fail", None, tolerance)
    return RuleOutcome("pass", None, tolerance)


def _eps_identity(operands: dict) -> RuleOutcome:
    """Computed EPS, quantized to the disclosed decimals, equals disclosure."""
    income = operands["net_income_available_to_common"].value
    pairs = (
        (operands["weighted_average_shares_basic"], operands["eps_basic"]),
        (operands["weighted_average_shares_diluted"], operands["eps_diluted"]),
    )
    tolerance = Decimal(1).scaleb(-min(_decimals_of(eps) for _shares, eps in pairs))
    for shares, eps in pairs:
        decimals = _decimals_of(eps)
        computed = (income / shares.value).quantize(
            Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN
        )
        if computed != eps.value:
            return RuleOutcome("fail", None, tolerance)
    return RuleOutcome("pass", None, tolerance)


CHECK_RULES = {
    PER_CLASS_RULE_ID: CheckRule(
        rule_id=PER_CLASS_RULE_ID,
        fn=_per_class_shares_vs_cover,
        same_period_required=True,
        limitation_when_period_mismatch=(
            "per_class_shares_vs_cover: cover date differs from balance-sheet"
            " date"
        ),
    ),
    EPS_IDENTITY_RULE_ID: CheckRule(
        rule_id=EPS_IDENTITY_RULE_ID,
        fn=_eps_identity,
    ),
}

PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    check_rules=CHECK_RULES,
    limitations=(
        "sbc_capitalized: no standard us-gaap alias frozen; issuer extensions"
        " need a core-catalog ruling",
    ),
)

__all__ = ["CHECK_RULES", "PRODUCER", "SPEC"]
