"""PK12 producer: biotech cash, R&D and financing disclosures.

Thin by design — the fact mappings below are frozen B.2 declarations over the
shared framework in ``base.py``. The two text fields stay ``unsupported`` rows
at this producer version: the framework reserves ``TextSpanMapping`` for a
later lane and this pack never implements a narrative locator. Applicability
is SIC-set membership OR the pre-revenue test (no revenue fact through the
core aliases, or one at/below zero, while R&D resolves), never an issuer-class
guess. The four catalogue checks are producer-owned rows
(``register_extra_check``): a recomputed runway, an FCF-basis month count
reported beside (never substituted for) the opCF-basis row, and two ratios —
arithmetic the framework's identity/relation operand shapes cannot express.
The envelope reports filed facts only and carries no projection of future
financing; ``engine/cash_runway.py`` is cited as the consumer-side runway
convention and is never imported here.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Mapping

from ..raw_ledger import RawFactLedger, decimal_text
from .base import (
    FactMapping,
    FormulaAbsence,
    FormulaMapping,
    PackProducer,
    PackSpec,
    TextSpanMapping,
    primary_period,
    probe_core_fact,
    register_extra_check,
    register_extra_receipts,
)

SPEC = PackSpec(
    pack_id="PK12",
    forms=frozenset({"10-K", "10-K/A"}),
    applicability_rule_id="pack.pk12.applicability/v1",
    applicable_classes=None,
)

_QUANTUM = Decimal("0.000001")
_BIOTECH_SICS = frozenset({"2834", "2835", "2836"})
_REVENUE_ALIASES = (
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:SalesRevenueNet",
    "us-gaap:Revenues",
)
_RD_ALIASES = (
    "us-gaap:ResearchAndDevelopmentExpense",
    "us-gaap:ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
)
_CAPEX_ALIASES = (
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    "us-gaap:PaymentsToAcquireProductiveAssets",
)

_RUNWAY_EVIDENCE = (
    "cash_runway_quarters",
    "cash_and_cash_equivalents",
    "short_term_investments",
    "net_cash_from_operating_activities",
)
_STI_LIMITATION = (
    "cash_runway_quarters: short_term_investments is a required dependency;"
    " an absent value is missing_dependency, never an implied zero"
)
_FCF_BASIS_LIMITATION = (
    "runway_months_annual_fcf_div_12: annual FCF burn ="
    " core:capital_expenditures - net_cash_from_operating_activities"
    " (payments-positive capex); months = (cash + short-term investments) /"
    " (annual FCF burn / 12). The FCF basis differs from the opCF-basis"
    " runway row by capex and is reported beside it, never substituted for"
    " it (consumer-side convention: engine/cash_runway.py)"
)
_NO_FORECAST_LIMITATION = (
    "financing_disclosed_not_forecast: the envelope reports filed financing"
    " facts (net financing cash flow, issuance proceeds, ATM/shelf disclosure"
    " spans) and carries no projection of future financing"
)
_SPAN_UNSUPPORTED_LIMITATION = (
    "atm_or_shelf_span and going_concern_or_liquidity_span: text-span"
    " evidence is not produced at this producer version; both rows stay"
    " unsupported until the framework's span lane lands"
)


# --------------------------------------------------------------------------
# Applicability (B.1) and receipts
# --------------------------------------------------------------------------


def _admission(
    pack_input: Any, ledger: RawFactLedger | None
) -> tuple[bool, bool]:
    """Return ``(sic_in_biotech_set, pre_revenue_test)`` under B.1.

    The pre-revenue test is evaluated for the receipt regardless of the SIC
    outcome, so a biotech-coded issuer also reports whether it is pre-revenue.
    """
    sic = pack_input.issuer_sic
    sic_in_set = sic is not None and str(sic) in _BIOTECH_SICS
    pre_revenue = False
    if ledger is not None:
        por = primary_period(pack_input, SPEC.forms)
        revenue = probe_core_fact(FactMapping(_REVENUE_ALIASES), ledger, por)
        if revenue is None or revenue <= 0:
            research = probe_core_fact(FactMapping(_RD_ALIASES), ledger, por)
            pre_revenue = research is not None
    return sic_in_set, pre_revenue


def _extra_applicability(
    pack_input: Any, ledger: RawFactLedger | None
) -> tuple[str, str] | None:
    sic_in_set, pre_revenue = _admission(pack_input, ledger)
    if sic_in_set or pre_revenue:
        return None
    # SIC-set membership failed and the pre-revenue test does not hold; the
    # test is set membership, not issuer class, so even an unbound SIC cites
    # the biotech-set reason here.
    return "not_applicable", "sic_outside_biotech_codes"


def _extra_receipts(
    pack_input: Any, ledger: RawFactLedger | None
) -> tuple[str, str]:
    sic_in_set, pre_revenue = _admission(pack_input, ledger)
    return (
        f"sic_in_biotech_set={str(sic_in_set).lower()}",
        f"pre_revenue_test={str(pre_revenue).lower()}",
    )


# --------------------------------------------------------------------------
# Field mappings (B.2)
# --------------------------------------------------------------------------


def _cash_runway_quarters(values: Mapping[str, Decimal]) -> Decimal:
    burn = -values["net_cash_from_operating_activities"] / Decimal(4)
    if burn <= 0:
        raise FormulaAbsence("non_positive_burn")
    total = values["cash_and_cash_equivalents"] + values["short_term_investments"]
    return (total / burn).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)


_FIELD_MAPPINGS = {
    "cash_and_cash_equivalents": FactMapping(
        (
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        )
    ),
    "short_term_investments": FactMapping(
        (
            "us-gaap:ShortTermInvestments",
            "us-gaap:MarketableSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        )
    ),
    "research_and_development_expense": FactMapping(_RD_ALIASES),
    "net_cash_from_operating_activities": FactMapping(
        (
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
            "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        )
    ),
    "net_cash_from_financing_activities": FactMapping(
        (
            "us-gaap:NetCashProvidedByUsedInFinancingActivities",
            "us-gaap:NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
        )
    ),
    "equity_financing_proceeds": FactMapping(
        (
            "us-gaap:ProceedsFromIssuanceOfCommonStock",
            "us-gaap:ProceedsFromIssuanceOrSaleOfEquity",
            "us-gaap:ProceedsFromIssuanceInitialPublicOffering",
        )
    ),
    # Reserved (A.4): span evidence is a later lane; both rows stay
    # unsupported rather than inventing a narrative locator.
    "atm_or_shelf_span": TextSpanMapping(),
    "going_concern_or_liquidity_span": TextSpanMapping(),
    "cash_runway_quarters": FormulaMapping(
        rule_id="pk12.cash_runway_quarters/v1",
        inputs=(
            "cash_and_cash_equivalents",
            "short_term_investments",
            "net_cash_from_operating_activities",
        ),
        fn=_cash_runway_quarters,
        operand_unit="USD",  # R-FOLD-F1: USD cash over USD burn -> quarters
    ),
}


# --------------------------------------------------------------------------
# Checks (B.3) — producer-owned rows
# --------------------------------------------------------------------------


def _valued_decimal(
    outcomes: Mapping[str, Any], field_id: str
) -> Decimal | None:
    outcome = outcomes.get(field_id)
    if outcome is None or outcome.value is None:
        return None
    return outcome.value


def _check_row(
    catalogue_check: Mapping[str, Any],
    status: str,
    evidence: tuple[str, ...],
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "check_id": catalogue_check["check_id"],
        "kind": catalogue_check["kind"],
        "status": status,
        "operands": list(catalogue_check.get("operands") or []),
        "tolerance": decimal_text(Decimal("0")),
        "evidence_field_ids": list(dict.fromkeys(evidence)),
        "reason": reason,
    }


def _runway_check(
    catalogue_check: Mapping[str, Any],
    outcomes: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Recompute the runway row from its three valued inputs (B.3)."""
    cash = _valued_decimal(outcomes, "cash_and_cash_equivalents")
    sti = _valued_decimal(outcomes, "short_term_investments")
    opcf = _valued_decimal(outcomes, "net_cash_from_operating_activities")
    limitations: tuple[str, ...] = ()
    if sti is None:
        limitations = (_STI_LIMITATION,)
    if cash is None or sti is None or opcf is None:
        return (
            _check_row(
                catalogue_check, "not_evaluable", _RUNWAY_EVIDENCE,
                reason="missing_dependency",
            ),
            limitations,
        )
    if opcf >= 0:  # burn = -opcf/4 is zero or negative
        return (
            _check_row(
                catalogue_check, "not_evaluable", _RUNWAY_EVIDENCE,
                reason="non_positive_burn",
            ),
            limitations,
        )
    row_value = _valued_decimal(outcomes, "cash_runway_quarters")
    if row_value is None:
        return (
            _check_row(
                catalogue_check, "not_evaluable", _RUNWAY_EVIDENCE,
                reason="missing_dependency",
            ),
            limitations,
        )
    recomputed = _cash_runway_quarters(
        {
            "cash_and_cash_equivalents": cash,
            "short_term_investments": sti,
            "net_cash_from_operating_activities": opcf,
        }
    )
    status = "pass" if row_value == recomputed else "fail"
    return (_check_row(catalogue_check, status, _RUNWAY_EVIDENCE), limitations)


def _fcf_months_check(
    pack_input: Any,
    ledger: RawFactLedger | None,
    catalogue_check: Mapping[str, Any],
    outcomes: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Month count on the FCF basis, reported beside the opCF-basis row."""
    evidence = (
        "cash_and_cash_equivalents",
        "short_term_investments",
        "net_cash_from_operating_activities",
    )
    cash = _valued_decimal(outcomes, "cash_and_cash_equivalents")
    sti = _valued_decimal(outcomes, "short_term_investments")
    opcf = _valued_decimal(outcomes, "net_cash_from_operating_activities")
    if cash is None or sti is None or opcf is None:
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="missing_dependency",
            ),
            (_FCF_BASIS_LIMITATION,),
        )
    capex = None
    if ledger is not None:
        por = primary_period(pack_input, SPEC.forms)
        capex = probe_core_fact(FactMapping(_CAPEX_ALIASES), ledger, por)
    if capex is None:
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="missing_dependency",
            ),
            (_FCF_BASIS_LIMITATION,),
        )
    fcf_burn = capex - opcf  # -(opcf - capex): annual free-cash-flow burn
    if fcf_burn <= 0:
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="non_positive_burn",
            ),
            (_FCF_BASIS_LIMITATION,),
        )
    months = ((cash + sti) / (fcf_burn / Decimal(12))).quantize(
        _QUANTUM, rounding=ROUND_HALF_EVEN
    )
    status = "pass" if months > 0 else "fail"
    return (
        _check_row(catalogue_check, status, evidence),
        (_FCF_BASIS_LIMITATION, f"pk12.runway_months_fcf: {months}"),
    )


def _rd_to_cash_check(
    catalogue_check: Mapping[str, Any],
    outcomes: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    evidence = (
        "research_and_development_expense",
        "cash_and_cash_equivalents",
    )
    research = _valued_decimal(outcomes, "research_and_development_expense")
    cash = _valued_decimal(outcomes, "cash_and_cash_equivalents")
    if research is None or cash is None:
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="missing_dependency",
            ),
            (),
        )
    if cash == 0:
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="division_by_zero",
            ),
            (),
        )
    ratio = (research / cash).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)
    return (
        _check_row(catalogue_check, "pass", evidence),
        (f"pk12.rd_to_cash: {ratio}",),
    )


def _financing_check(
    catalogue_check: Mapping[str, Any],
    outcomes: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    evidence = (
        "net_cash_from_financing_activities",
        "atm_or_shelf_span",
        "equity_financing_proceeds",
    )
    financing = _valued_decimal(outcomes, "net_cash_from_financing_activities")
    span = _valued_decimal(outcomes, "atm_or_shelf_span")
    proceeds = _valued_decimal(outcomes, "equity_financing_proceeds")
    limitations = (_NO_FORECAST_LIMITATION, _SPAN_UNSUPPORTED_LIMITATION)
    if financing is not None and (span is not None or proceeds is not None):
        return (_check_row(catalogue_check, "pass", evidence), limitations)
    return (
        _check_row(
            catalogue_check, "not_evaluable", evidence,
            reason="missing_dependency",
        ),
        limitations,
    )


def _produce_check(
    pack_input: Any,
    ledger: RawFactLedger | None,
    outcomes: Mapping[str, Any],
    catalogue_check: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]] | None:
    check_id = catalogue_check["check_id"]
    if check_id == "cash_runway_quarters":
        return _runway_check(catalogue_check, outcomes)
    if check_id == "runway_months_annual_fcf_div_12":
        return _fcf_months_check(pack_input, ledger, catalogue_check, outcomes)
    if check_id == "rd_to_cash":
        return _rd_to_cash_check(catalogue_check, outcomes)
    if check_id == "financing_disclosed_not_forecast":
        return _financing_check(catalogue_check, outcomes)
    return None


PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=(),
    extra_applicability=_extra_applicability,
)

register_extra_receipts("PK12", _extra_receipts)
register_extra_check("PK12", _produce_check)

__all__ = ["PRODUCER", "SPEC"]
