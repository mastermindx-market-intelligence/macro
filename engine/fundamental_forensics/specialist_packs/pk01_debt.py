"""PK01 producer: debt, liquidity, covenants and maturities.

Thin by design — every mapping below is a frozen B.2 declaration over the
shared framework in ``base.py``. Finance-lease liabilities are absent on
purpose: PK06 owns them, and the instrument rows exclude lease members.
The core-catalogue aliases consumed here (short_term_debt, long_term_debt,
long_term_debt_current, cash_and_cash_equivalents, short_term_investments,
current_assets, current_liabilities) are copied exactly from
``config/fundamental_forensics/metrics/v1/mappings/core.yaml``.

2026-11-01 repair lane (dev corpus diversified_v1, DEC-FIF-PACK-
GENERALIZATION-DEV-CORPUS): every numeric mapping above is byte-identical
to BASE — the widened aliases the dev filings would justify
(CommercialPaper / OtherShortTermBorrowings for short_term_debt, the
precision-consistent duplicate policy for double-tagged balances) would
move the committed base-fixture envelope away from its pinned sha256 and
the pinned missing-row test, so they stay unapplied and are reported as
gaps by the lane. The repair this lane ships is
``covenant_term_observation``: the framework-layer mapping stays the
reserved form and ``Pk01Producer.finalize_result`` runs the real B.2
text-span search (the PK07 finalize-hook pattern) because the PK01
catalogue declares no narrative reason code, so the stock section-scoped
resolver's absence codes could never validate. The hook only upgrades
the row when a covenant span is located — every searched-but-not-found
outcome returns the result byte-identical (the base-envelope digest pins
require that).
"""
from __future__ import annotations

import re
from typing import Any

from .. import specialist_pack_contract as contract
from ..financial_intelligence_packet import PACKET_MAX_LIMITATIONS
from . import narrative
from .base import (
    DimensionedFactMapping,
    FactMapping,
    FactOrFormulaMapping,
    FormulaMapping,
    PackProducer,
    PackSpec,
    Presence,
    Reconcile,
    SpecialistPackError,
    SumIdentity,
    TextSpanMapping,
    _raw_span,
    _select_primary,
    _text_span_digest,
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
    # Reserved at the framework layer: the finalize hook below runs the real
    # B.2 search (the PK01 catalogue declares no narrative reason code, so
    # the stock resolver's absence codes are unemittable).
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


# --- B.2 covenant text search (producer-owned; PK07 finalize-hook pattern) -----

# Governing section: the debt / borrowings / credit-facility note, in the
# heading forms the diversified_v1 dev filings actually use — "Note 7. Debt"
# and "Note 5. Debt", "Note 3. Debt and Other Financing Arrangements",
# "NOTE 13. FINANCING" / "NOTE 11. FINANCING", "Note 9 Debt and Credit
# Agreements" / "Note 9 – Debt and Credit Agreements" / "NOTE 9. LONG-TERM
# DEBT AND CREDIT AGREEMENTS", and "Note 10: Short-term and Long-term Debt".
# The last body occurrence wins (skip_toc=False): every dev filing lists
# the note in its index first. The section ends at the next note heading.
NOTE_DEBT = narrative.SectionSpec(
    r"(?:Note|NOTE)\s*\d+\s*[.:–\-]?\s*"
    r"(?:(?:Short[- ]?[Tt]erm and )?Long[- ]?[Tt]erm )?"
    r"(?:Debt|Financing|Borrowings)",
    (r"(?:Note|NOTE)\s*\d+\s*[.:–\-]",),
    skip_toc=False,
)
# Covenant-language pattern, precision first: named financial covenants
# (leverage / interest-coverage ratios), an explicit financial-covenant
# reference, covenants attached to a named facility, and compliance-with-
# covenants statements — the four forms the dev filings carry.
COVENANT_TERM_PATTERN = (
    r"financial covenant"
    r"|[Ll]everage ratio"
    r"|[Ii]nterest coverage ratio"
    r"|[Cc]ovenants? in the [A-Za-z ]{0,30}[Ff]acility"
    r"|(?:are|was|is|were) in compliance with [^.]{0,80}covenants?"
    r"|covenants? (?:include|requires|that restrict)"
)
_COVENANT_MAPPING = TextSpanMapping(
    section=NOTE_DEBT, pattern=COVENANT_TERM_PATTERN, kind="text"
)


def _recompute_coverage(envelope: dict[str, Any]) -> None:
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


def _covenant_span(nt: Any) -> tuple[str, tuple[int, int]] | None:
    """(sentence text, char span) of the first covenant term in the note."""
    section_span = narrative.locate_section(nt, _COVENANT_MAPPING.section)
    if section_span is None:
        return None
    lo, hi = section_span
    match = re.compile(_COVENANT_MAPPING.pattern).search(nt.text, lo, hi)
    if match is None:
        return None
    span = narrative.sentence_span(nt.text, match.start(), match.end(), section_span)
    text_value = nt.text[span[0] : span[1]].strip()[: _COVENANT_MAPPING.max_chars]
    return text_value, span


class Pk01Producer(PackProducer):
    """PK01 declaration plus the covenant text-span finalize hook."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact
        primary, _matched = _select_primary(pack_input.packages, SPEC.forms)
        if primary is None:
            return result
        try:
            nt = narrative.primary_document_text(primary)
        except SpecialistPackError:
            return result  # reserved row already types the narrative absence
        found = _covenant_span(nt)
        if found is None:
            # Searched, not supplied. The reserved-form row and its check are
            # already exact, and the A.7 base-envelope pins require this
            # result to stay byte-identical to the no-hook build, so nothing
            # is appended.
            return result
        text_value, span = found
        accession = str(primary.manifest.get("accession") or "")
        row = next(
            item
            for item in result["fields"]
            if item["field_id"] == "covenant_term_observation"
        )
        row["quality_state"] = "valued"
        row["non_value_state"] = None
        row["coverage_state"] = "source_trace_complete"
        row["reason"] = None
        row["value"] = None
        row["text_value"] = text_value
        row["source_span"] = _raw_span(nt, span[0], span[1], accession)
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["mapping_rule_id"] = "pk01.covenant_term_observation.text_span/v1"
        row["mapping_rule_digest"] = _text_span_digest(_COVENANT_MAPPING)
        for check in result["checks"]:
            if check["check_id"] == "covenant_span_present":
                check["status"] = "pass"
                check["reason"] = None
        result["limitations"] = list(result["limitations"])[:PACKET_MAX_LIMITATIONS]
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK01 finalize refused: " + "; ".join(errors[:5])
            )
        return result


PRODUCER = Pk01Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
)

__all__ = [
    "COVENANT_TERM_PATTERN",
    "NOTE_DEBT",
    "PRODUCER",
    "SPEC",
]
