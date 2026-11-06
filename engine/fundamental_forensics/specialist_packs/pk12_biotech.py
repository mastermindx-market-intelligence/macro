"""PK12 producer: biotech cash, R&D and financing disclosures.

Thin by design — the fact mappings below are frozen B.2 declarations over the
shared framework in ``base.py``. The two text fields stay ``unsupported`` rows
at this producer version: the framework reserves ``TextSpanMapping`` for a
later lane and this pack never implements a narrative locator. Applicability
is SIC-set membership OR the pre-revenue test (no revenue fact through the
core aliases, or one at/below zero, while R&D resolves), never an issuer-class
guess. The four catalogue checks are producer-owned rows
(``register_extra_check``): a recomputed runway, an FCF-basis month count
computed only over an annual USD capex operand (the count itself is withheld
from limitations; the capex provenance is cited instead) and reported beside
(never substituted for) the opCF-basis row, and two ratios — arithmetic the
framework's identity/relation operand shapes cannot express. The runway row
and both runway checks refuse as ``unit_mismatch`` unless the operating-cash-
flow fact covers a full fiscal year (the formula divides it by 4 for
quarters). The envelope reports filed facts only and carries no projection of
future financing; ``engine/cash_runway.py`` is cited as the consumer-side
runway convention and is never imported here.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Mapping

from .. import specialist_pack_contract as contract
from ..raw_ledger import RawFactLedger, decimal_text
from .base import (
    FactMapping,
    FormulaAbsence,
    FormulaMapping,
    MAX_DURATION_DAYS,
    PackProducer,
    PackSpec,
    SpecialistPackError,
    TextSpanMapping,
    _resolve_fact_mapping,
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
# Inclusive-day floor for a duration fact to count as a full fiscal year.
MIN_ANNUAL_DURATION_DAYS = 350
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
_RUNWAY_ASSUMPTIONS_LIMITATION = (
    "cash_runway_quarters: static formula (cash_and_cash_equivalents +"
    " short_term_investments) / (-annual net_cash_from_operating_activities"
    " / 4); the burn is held constant at the trailing annual rate, and no"
    " future financing, revenue change or restricted-cash release is assumed"
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
            # biotech_v1 dev corpus: many biotechs report their only
            # equity-issuance financing line as proceeds from incentive/stock
            # plans, tagged with the standard us-gaap stock-plan issuance
            # concepts ("Issuances of common stock under benefit plans",
            # "Proceeds from issuance of common stock through equity plans").
            # Period rule: the cash-flow duration ending at period_of_report,
            # exactly like every alias above (the resolver admits the longest
            # duration context whose end equals period_of_report). Declared
            # AFTER the capital-raise aliases so a filing carrying both a
            # capital-raise line and a stock-plan line keeps reporting the
            # capital-raise proceeds; footnote option-table facts are usually
            # dimensioned and never resolve here (dimensions_allowed=()).
            "us-gaap:ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions",
            "us-gaap:ProceedsFromStockPlans",
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


def _is_annual_duration(period: Mapping[str, Any] | None) -> bool:
    """True when a row period covers a full fiscal year under spec 1.

    A duration counts as annual when its inclusive day count
    ``(end - start).days + 1`` lies in ``[MIN_ANNUAL_DURATION_DAYS,
    MAX_DURATION_DAYS]``; an instant or start-less period never does.
    """
    if not isinstance(period, Mapping):
        return False
    start_text = str(period.get("start") or "")
    end_text = str(period.get("end") or "")
    if not start_text or not end_text:
        return False
    days = (
        date.fromisoformat(end_text[:10]) - date.fromisoformat(start_text[:10])
    ).days + 1
    return MIN_ANNUAL_DURATION_DAYS <= days <= MAX_DURATION_DAYS


def _resolve_usd_capex(pack_input: Any, ledger: RawFactLedger | None) -> Any:
    """Resolve capex through the base resolver under a USD catalogue unit.

    ``probe_core_fact``'s call shape (``base.py``), but the outcome object is
    kept, not only its value: the R-F1 unit law then refuses a non-USD capex
    fact as a ``unit_mismatch`` absence, and the outcome row carries the
    concept, occurrence ids, period and unit the FCF check's provenance
    limitation cites. The intermediate row is discarded, never emitted.
    """
    if ledger is None:
        return None
    por = primary_period(pack_input, SPEC.forms)
    return _resolve_fact_mapping(
        pack_id="PK00",
        catalogue_field={
            "field_id": "core_probe",
            "name": "core probe",
            "type": "decimal",
            "unit": "USD",
            "period_kind": "duration",
        },
        mapping=FactMapping(_CAPEX_ALIASES),
        ledger=ledger,
        por=por,
        extension_prefixes={},
    )


def _capex_provenance_limitation(capex_outcome: Any) -> str:
    """Name the capex operand's provenance from the resolved outcome row."""
    row = capex_outcome.row
    period = row.get("period") or {}
    occurrences = ",".join(
        str(item) for item in row.get("source_occurrence_ids") or ()
    )
    return (
        "runway_months_annual_fcf_div_12: capex operand"
        f" {row.get('concept')} occurrence(s) {occurrences} period"
        f" {period.get('start')}..{period.get('end')} unit {row.get('unit')}"
        " (core probe, not a PK12 field row)"
    )


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
    # D4: a valued runway row carries its static assumptions with it.
    return (
        _check_row(catalogue_check, status, _RUNWAY_EVIDENCE),
        (*limitations, _RUNWAY_ASSUMPTIONS_LIMITATION),
    )


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
    opcf_outcome = outcomes.get("net_cash_from_operating_activities")
    if not _is_annual_duration(opcf_outcome.row.get("period")):
        # D1: the FCF burn basis divides an ANNUAL opCF by 12; a non-annual
        # opCF row is a period-basis unit_mismatch (the finalize hook owns
        # the row and both runway checks for the same cause).
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="unit_mismatch",
            ),
            (_FCF_BASIS_LIMITATION,),
        )
    capex_outcome = _resolve_usd_capex(pack_input, ledger)
    if capex_outcome is None or capex_outcome.value is None:
        # D2: an alias fact that failed the R-F1 USD test is a unit_mismatch;
        # no resolvable alias at all stays the honest missing_dependency.
        reason = (
            "unit_mismatch"
            if capex_outcome is not None
            and capex_outcome.row.get("reason") == "unit_mismatch"
            else "missing_dependency"
        )
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence, reason=reason,
            ),
            (_FCF_BASIS_LIMITATION,),
        )
    if not _is_annual_duration(capex_outcome.row.get("period")):
        # D2: a quarter-only capex fact is not an annual burn operand.
        return (
            _check_row(
                catalogue_check, "not_evaluable", evidence,
                reason="unit_mismatch",
            ),
            (_FCF_BASIS_LIMITATION,),
        )
    capex = capex_outcome.value
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
    # D3: the month count itself is withheld until it can be traced; the
    # capex operand that produced it is cited by provenance instead.
    return (
        _check_row(catalogue_check, status, evidence),
        (_FCF_BASIS_LIMITATION, _capex_provenance_limitation(capex_outcome)),
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


# --------------------------------------------------------------------------
# Finalize hook (registry.py) — the opCF period basis (D1)
# --------------------------------------------------------------------------


def _recompute_coverage(envelope: dict[str, Any]) -> None:
    """Recount the coverage block after finalize rewrote a field row."""
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


class Pk12Producer(PackProducer):
    """PK12 declaration plus the opCF period-basis finalize hook (D1)."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: Any
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact
        rows = {str(row["field_id"]): row for row in result["fields"]}
        opcf_row = rows.get("net_cash_from_operating_activities")
        if (
            opcf_row is None
            or opcf_row.get("quality_state") != "valued"
            or _is_annual_duration(opcf_row.get("period"))
        ):
            return result  # an annual (or absent) opCF row changes nothing
        # The runway formula divides opCF by 4 for quarters, so a valued opCF
        # row that does not cover a full fiscal year is a period-basis
        # unit_mismatch: the runway row is retracted to the framework's own
        # non-valued formula-absence shape and both runway checks follow.
        runway = rows.get("cash_runway_quarters")
        if runway is not None:
            runway["value"] = None
            runway["quality_state"] = "not_evaluable"
            runway["non_value_state"] = "not_evaluable"
            runway["coverage_state"] = "unmapped"
            runway["reason"] = "unit_mismatch"
        for check in result["checks"]:
            if str(check.get("check_id")) in (
                "cash_runway_quarters",
                "runway_months_annual_fcf_div_12",
            ):
                check["status"] = "not_evaluable"
                check["reason"] = "unit_mismatch"
        # D4 fires only while the runway row is valued; the retraction
        # withdraws its assumptions limitation with it.
        result["limitations"] = [
            item
            for item in result["limitations"]
            if item != _RUNWAY_ASSUMPTIONS_LIMITATION
        ]
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK12 finalize refused: " + "; ".join(errors[:5])
            )
        return result


PRODUCER = Pk12Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=(),
    extra_applicability=_extra_applicability,
)

register_extra_receipts("PK12", _extra_receipts)
register_extra_check("PK12", _produce_check)

__all__ = ["PRODUCER", "SPEC"]
