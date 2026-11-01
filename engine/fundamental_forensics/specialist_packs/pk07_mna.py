"""PK07 producer: M&A, goodwill, intangibles and impairments.

B.1 forms are {10-K, 10-K/A, 8-K} with no issuer-class gate, so a 10-Q probe
types the whole pack ``not_applicable`` + ``form_outside_pack_forms`` and a
deal-free year stays ``applicable`` with every numeric row an honest typed
absence. The nine numeric fields are frozen B.2 ``FactMapping`` declarations
(first-resolving priority order, undimensioned); the rollforward's opening
balance is the prior-instant ``Goodwill`` resolved on the framework's own
``opening_instant`` admission (B.4) through the framework's own resolver, used
as a probe — no row is minted for it.

The three narrative fields and all three checks are producer-owned through
``Pk07Producer.finalize_result`` (the registry hook PK11 introduced), for one
frozen-catalogue reason: PK07's catalogue carries no narrative reason code at
all (PK09's does), so the stock ``TextSpanMapping`` section-scoped resolver —
whose absences type ``governing_section_not_supplied`` /
``narrative_span_not_located`` — would hand the contract validator a reason
the PK07 catalogue refuses and no envelope could ever be produced. The PK10
ruling extended: a pattern the document does not supply may never emit a
reason the catalogue refuses. ``finalize_result`` therefore runs the exact
B.2 search (same :mod:`narrative` pipeline, same frozen sections and
patterns) itself and types every narrative absence with the catalogue's
closest code ``missing_dependency``, carrying the intended stock code verbatim
in the envelope's ``limitations`` (one line per narrative row naming the
section searched). The stock resolver is never entered: the declared mappings
are the reserved form, so a producer that registers no finalize hook stays
byte-identical to BASE.

The checks ride the same hook because the frozen catalogue names one
``goodwill`` field for both the rollforward's opening (prior instant) and
closing (period_of_report instant) — the framework's ``Rollforward`` resolves
both operands through the same current-period row — and because
``acquisition_scope_stated`` is a three-field disjunctive presence the stock
``Presence`` check cannot state. Placeholder ``CheckSpec`` shapes (kind-matched
to the catalogue) keep the framework's own production complete; the hook then
replaces every check row, recomputes coverage, re-digests and re-checks the
envelope, so a PK07 result never bypasses the contract.

Private imports from :mod:`base` (``_select_primary`` precedent: PK10) reuse
the frozen admission laws — the opening-instant bound, the undimensioned
resolver, the span/digest shapes — instead of duplicating them; the
additive-only merge law keeps them stable.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from typing import Any, Mapping

from .. import specialist_pack_contract as contract
from ..raw_ledger import RawFactLedger, decimal_text
from . import narrative
from .base import (
    CrossStatement,
    FactMapping,
    PackInput,
    PackProducer,
    PackSpec,
    Presence,
    Rollforward,
    SpecialistPackError,
    TextSpanMapping,
    _primary_duration_opening_bound,
    _raw_span,
    _resolve_fact_mapping,
    _select_primary,
    _text_span_digest,
    _unit_measure,
    register_extra_receipts,
)

SPEC = PackSpec(
    pack_id="PK07",
    forms=frozenset({"10-K", "10-K/A", "8-K"}),
    applicability_rule_id="pack.pk07.applicability/v1",
    applicable_classes=None,
)

# B.2 concept aliases (us-gaap; priority order p10/p20/p30; undimensioned).
_GOODWILL = ("us-gaap:Goodwill",)
_INTANGIBLES_NET = (
    "us-gaap:IntangibleAssetsNetExcludingGoodwill",
    "us-gaap:FiniteLivedIntangibleAssetsNet",
)
_INDEFINITE_LIVED = ("us-gaap:IndefiniteLivedIntangibleAssetsExcludingGoodwill",)
_GOODWILL_ACQUIRED = ("us-gaap:GoodwillAcquiredDuringPeriod",)
_GOODWILL_DISPOSALS = ("us-gaap:GoodwillWrittenOffRelatedToSaleOfBusinessUnit",)
_GOODWILL_FX_OTHER = (
    "us-gaap:GoodwillForeignCurrencyTranslationGainLoss",
    "us-gaap:GoodwillOtherIncreaseDecrease",
)
_GOODWILL_IMPAIRMENT = ("us-gaap:GoodwillImpairmentLoss",)
_INTANGIBLE_IMPAIRMENT = (
    "us-gaap:ImpairmentOfIntangibleAssetsExcludingGoodwill",
    "us-gaap:ImpairmentOfIntangibleAssetsFinitelived",
    "us-gaap:ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill",
)
_CONSIDERATION = ("us-gaap:BusinessCombinationConsiderationTransferred1",)

_NUMERIC_CONCEPTS = tuple(
    dict.fromkeys(
        _GOODWILL
        + _INTANGIBLES_NET
        + _INDEFINITE_LIVED
        + _GOODWILL_ACQUIRED
        + _GOODWILL_DISPOSALS
        + _GOODWILL_FX_OTHER
        + _GOODWILL_IMPAIRMENT
        + _INTANGIBLE_IMPAIRMENT
        + _CONSIDERATION
    )
)
_NUMERIC_FIELD_IDS = (
    "goodwill",
    "intangible_assets_net",
    "indefinite_lived_intangibles",
    "goodwill_acquired",
    "goodwill_disposals",
    "goodwill_fx_other",
    "goodwill_impairment_loss",
    "intangible_impairment_loss",
    "business_combination_consideration",
)

# B.2 governing sections and patterns (frozen).
NOTE_BC = narrative.SectionSpec(
    r"Note \d+ [–-] (?:Business Combinations?|Acquisitions?)",
    (r"Note \d+ [–-]",),
)
NOTE_IMP = narrative.SectionSpec(
    r"(?:Goodwill and (?:Other )?Intangible Assets|Impairment)",
    (r"Note \d+ [–-]",),
)
ACQUISITION_DATE_PATTERN = (
    r"(?:on|as of|completed on) "
    r"(?P<d>(?:January|February|March|April|May|June|July|August|September"
    r"|October|November|December) \d{1,2}, \d{4})"
)
PURCHASE_ACCOUNTING_PATTERN = (
    r"purchase price|consideration"
    r"|fair value of (?:the )?(?:assets acquired|net assets)"
)
IMPAIRMENT_TESTING_PATTERN = (
    r"impairment test|tested for impairment|qualitative assessment"
)

# The real B.2 text mappings: the search contracts the finalize hook executes
# (and the digests it stamps). The declared field mappings below stay the
# reserved form so the stock resolver — whose absence codes the PK07 catalogue
# refuses — is never entered during framework production.
_ACQUISITION_DATE_MAPPING = TextSpanMapping(
    section=NOTE_BC, pattern=ACQUISITION_DATE_PATTERN, kind="text"
)
_PURCHASE_ACCOUNTING_MAPPING = TextSpanMapping(
    section=NOTE_BC, pattern=PURCHASE_ACCOUNTING_PATTERN, kind="text"
)
_IMPAIRMENT_TESTING_MAPPING = TextSpanMapping(
    section=NOTE_IMP, pattern=IMPAIRMENT_TESTING_PATTERN, kind="text"
)

TABLE_CELL_RESERVED_LIMITATION = (
    "pk07.table_cell_reserved: business_combination_consideration resolves "
    "from xbrl_fact only in this version"
)
NEGATIVE_YEAR_LIMITATION = (
    "pk07.negative_year: no goodwill, intangible or business-combination "
    "facts in the primary filing"
)

_FIELD_MAPPINGS = {
    "goodwill": FactMapping(_GOODWILL),
    "intangible_assets_net": FactMapping(_INTANGIBLES_NET),
    "indefinite_lived_intangibles": FactMapping(_INDEFINITE_LIVED),
    "goodwill_acquired": FactMapping(_GOODWILL_ACQUIRED),
    "goodwill_disposals": FactMapping(_GOODWILL_DISPOSALS),
    "goodwill_fx_other": FactMapping(_GOODWILL_FX_OTHER),
    "goodwill_impairment_loss": FactMapping(_GOODWILL_IMPAIRMENT),
    "intangible_impairment_loss": FactMapping(_INTANGIBLE_IMPAIRMENT),
    # B.2: the table_cell half of this field's evidence kinds is reserved
    # (not built here); the xbrl_fact half is the p10 concept above, and an
    # absent fact types missing_standard_fact — never unsupported.
    "business_combination_consideration": FactMapping(_CONSIDERATION),
    # Reserved at the mapping layer; the finalize hook runs the real B.2
    # search (see _ACQUISITION_DATE_MAPPING and friends above).
    "acquisition_date": TextSpanMapping(),
    "purchase_accounting_note_span": TextSpanMapping(),
    "impairment_testing_note_span": TextSpanMapping(),
}

# Placeholder CheckSpecs (kind-matched to the catalogue) the finalize hook
# replaces: the stock Rollforward cannot state a prior-instant opening from
# the single catalogue goodwill field, and the stock Presence check cannot
# state the three-field disjunction below.
_CHECKS = (
    Rollforward(
        check_id="goodwill_rollforward_closed",
        opening="goodwill",
        additions=("goodwill_acquired", "goodwill_fx_other"),
        reductions=("goodwill_disposals", "goodwill_impairment_loss"),
        closing="goodwill",
    ),
    CrossStatement(
        check_id="impairment_vs_carrying",
        left="goodwill_impairment_loss",
        right="goodwill",
        relation="left_lte_right",
    ),
    Presence(check_id="acquisition_scope_stated", field_id="acquisition_date"),
)


# --- B.6 receipts --------------------------------------------------------------


def _extra_receipts(
    pack_input: Any, ledger: RawFactLedger | None
) -> tuple[str, ...]:
    """One receipt line: ledger facts matching any B.2 numeric concept."""
    if ledger is None:
        return ()
    wanted = frozenset(_NUMERIC_CONCEPTS)
    count = sum(
        1 for occurrence in ledger.events if occurrence.concept_qname in wanted
    )
    return (f"pk07_numeric_fact_count={count}",)


register_extra_receipts("PK07", _extra_receipts)


# --- B.2 narrative search (producer-owned; see module docstring) ---------------


def _narrative_or_none(primary: Any) -> Any:
    """The primary document's narrative text, or ``None`` when not retained."""
    try:
        return narrative.primary_document_text(primary)
    except SpecialistPackError:
        return None


def _rewrite_narrative_row(
    row: dict[str, Any],
    nt: Any,
    mapping: TextSpanMapping,
    *,
    date_group: str | None,
    accession: str,
) -> str | None:
    """Resolve one B.2 text field over the primary document narrative.

    Executes the stock ``_resolve_text_span_mapping`` semantics (section
    location, pattern search, sentence span or named group, 1024-char cap)
    but types every absence with the catalogue's ``missing_dependency`` —
    the PK10 ruling for a pack whose catalogue carries no narrative code —
    and returns the intended stock code for the envelope's limitations.
    """
    field_id = row["field_id"]
    rule_id = f"pk07.{field_id}.text_span/v1"
    digest = _text_span_digest(mapping)
    row["evidence_kind"] = "text_span"
    row["required_evidence_kind"] = "text_span"
    row["mapping_rule_id"] = rule_id
    row["mapping_rule_digest"] = digest

    def absence(quality_state: str, note: str) -> str:
        row["quality_state"] = quality_state
        row["non_value_state"] = quality_state
        row["coverage_state"] = "unmapped"
        row["reason"] = "missing_dependency"
        row["value"] = None
        row["text_value"] = None
        row["source_span"] = None
        return note

    if nt is None:
        return absence("missing", "narrative document not retained")
    assert mapping.section is not None  # every PK07 text field is section-scoped
    section_span = narrative.locate_section(nt, mapping.section)
    if section_span is None:
        return absence("not_evaluable", "governing_section_not_supplied")
    lo, hi = section_span
    match = re.compile(mapping.pattern).search(nt.text, lo, hi)
    if match is None:
        return absence("missing", "narrative_span_not_located")
    if date_group is not None:
        text_value = match.group(date_group)
        span = (match.start(date_group), match.end(date_group))
    else:
        span = narrative.sentence_span(
            nt.text, match.start(), match.end(), section_span
        )
        text_value = nt.text[span[0] : span[1]].strip()[: mapping.max_chars]
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["text_value"] = text_value
    row["source_span"] = _raw_span(nt, span[0], span[1], accession)
    return None


_NARRATIVE_FIELDS = (
    ("acquisition_date", _ACQUISITION_DATE_MAPPING, "d"),
    ("purchase_accounting_note_span", _PURCHASE_ACCOUNTING_MAPPING, None),
    ("impairment_testing_note_span", _IMPAIRMENT_TESTING_MAPPING, None),
)


# --- B.4 checks (producer-owned rows) ------------------------------------------


def _check_row(
    catalogue_check: Mapping[str, Any],
    status: str,
    *,
    tolerance: Decimal | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    operands = list(catalogue_check.get("operands") or [])
    return {
        "check_id": catalogue_check["check_id"],
        "kind": catalogue_check["kind"],
        "status": status,
        "operands": operands,
        "tolerance": decimal_text(tolerance),
        "evidence_field_ids": operands,
        "reason": reason,
    }


def _row_decimal(
    rows: Mapping[str, Mapping[str, Any]], field_id: str
) -> Decimal | None:
    row = rows[field_id]
    if row.get("quality_state") != "valued" or row.get("value") is None:
        return None
    return Decimal(str(row["value"]))


def _row_unit(ledger: RawFactLedger, row: Mapping[str, Any]) -> str | None:
    """The row's underlying fact unit measure (the catalogue unit is fixed)."""
    for occurrence_id in row.get("source_occurrence_ids") or []:
        occurrence = ledger.by_id(occurrence_id)
        if occurrence is not None:
            return _unit_measure(occurrence.unit)
    return None


def _opening_probe(
    ledger: RawFactLedger, concepts: tuple[str, ...], por: date
) -> tuple[Decimal, str | None] | None:
    """(value, unit measure) of the prior-instant balance, or ``None``.

    The framework's own ``opening_instant`` admission (PK05): the comparative
    balance-sheet date — the day before the primary fiscal duration's start,
    falling back to the latest instant strictly before it — resolved as a
    probe through ``_resolve_fact_mapping``, so the conflict and precision
    laws are the framework's, never re-implemented here.
    """
    bound = _primary_duration_opening_bound(ledger, por)
    if bound is None:
        return None
    outcome = _resolve_fact_mapping(
        pack_id="PK07",
        catalogue_field={
            "field_id": "opening_probe",
            "name": "opening probe",
            "type": "decimal",
            "unit": None,
            "period_kind": "instant",
        },
        mapping=FactMapping(concepts, period_select="opening_instant"),
        ledger=ledger,
        por=por,
        extension_prefixes={},
        opening_bound=bound,
    )
    if outcome.value is None:
        return None
    return outcome.value, outcome.unit


def _closing_tolerance(
    ledger: RawFactLedger, closing_row: Mapping[str, Any]
) -> Decimal:
    """1x10^-d from the closing fact's decimals attribute (B.4)."""
    for occurrence_id in closing_row.get("source_occurrence_ids") or []:
        occurrence = ledger.by_id(occurrence_id)
        if (
            occurrence is not None
            and occurrence.decimals is not None
            and occurrence.decimals != "INF"
        ):
            return Decimal(1).scaleb(-int(occurrence.decimals))
    return Decimal("0")


def _goodwill_rollforward_row(
    rows: Mapping[str, Mapping[str, Any]],
    catalogue_check: Mapping[str, Any],
    ledger: RawFactLedger,
    por: date,
) -> dict[str, Any]:
    """opening + acquired - disposals - impairment + fx_other = closing."""
    opening = _opening_probe(ledger, _GOODWILL, por)
    closing = _row_decimal(rows, "goodwill")
    components = {
        field_id: _row_decimal(rows, field_id)
        for field_id in (
            "goodwill_acquired",
            "goodwill_disposals",
            "goodwill_impairment_loss",
            "goodwill_fx_other",
        )
    }
    # K3K4: an absent component is ABSENT, never zero.
    if opening is None or closing is None or any(
        value is None for value in components.values()
    ):
        return _check_row(
            catalogue_check, "not_evaluable", reason="missing_dependency"
        )
    tolerance = _closing_tolerance(ledger, rows["goodwill"])
    expected = (
        opening[0]
        + components["goodwill_acquired"]
        - components["goodwill_disposals"]
        - components["goodwill_impairment_loss"]
        + components["goodwill_fx_other"]
    )
    status = "pass" if abs(expected - closing) <= tolerance else "fail"
    return _check_row(catalogue_check, status, tolerance=tolerance)


def _impairment_vs_carrying_row(
    rows: Mapping[str, Mapping[str, Any]],
    catalogue_check: Mapping[str, Any],
    ledger: RawFactLedger,
    por: date,
) -> dict[str, Any]:
    """Each impairment against its prior-instant carrying amount (B.4)."""
    goodwill_opening = _opening_probe(ledger, _GOODWILL, por)
    intangibles_opening = _opening_probe(ledger, _INTANGIBLES_NET, por)
    goodwill_impairment = _row_decimal(rows, "goodwill_impairment_loss")
    intangible_impairment = _row_decimal(rows, "intangible_impairment_loss")
    # Each pair is evaluated only when both sides are valued.
    pairs: list[tuple[Decimal, Decimal, str | None, str | None]] = []
    if goodwill_impairment is not None and goodwill_opening is not None:
        pairs.append(
            (
                goodwill_impairment,
                goodwill_opening[0],
                _row_unit(ledger, rows["goodwill_impairment_loss"]),
                goodwill_opening[1],
            )
        )
    if intangible_impairment is not None and intangibles_opening is not None:
        pairs.append(
            (
                intangible_impairment,
                intangibles_opening[0],
                _row_unit(ledger, rows["intangible_impairment_loss"]),
                intangibles_opening[1],
            )
        )
    if not pairs:
        return _check_row(
            catalogue_check, "not_evaluable", reason="missing_dependency"
        )
    for _impairment, _carrying, left_unit, right_unit in pairs:
        if (
            left_unit is not None
            and right_unit is not None
            and left_unit != right_unit
        ):
            return _check_row(
                catalogue_check, "not_evaluable", reason="unit_mismatch"
            )
    for impairment, carrying, _left, _right in pairs:
        if impairment > carrying:
            return _check_row(catalogue_check, "fail")
    return _check_row(catalogue_check, "pass")


def _acquisition_scope_row(
    rows: Mapping[str, Mapping[str, Any]],
    catalogue_check: Mapping[str, Any],
) -> dict[str, Any]:
    """Pass when any of the three scope fields is valued (B.4)."""
    valued = any(
        rows[field_id].get("quality_state") == "valued"
        for field_id in (
            "acquisition_date",
            "business_combination_consideration",
            "purchase_accounting_note_span",
        )
    )
    if valued:
        return _check_row(catalogue_check, "pass")
    return _check_row(
        catalogue_check, "not_evaluable", reason="missing_dependency"
    )


# --- B.5 limitations + the finalize hook ---------------------------------------


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


class Pk07Producer(PackProducer):
    """PK07 declaration plus the narrative/check finalize hook."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact (B.1)
        from ..ixbrl_raw_ledger import (  # call-time: a test double is honoured
            parse_and_convert_golden_packages
        )

        ledger, _filing_metadata, _report = parse_and_convert_golden_packages(
            pack_input.packages
        )
        primary, _matched = _select_primary(pack_input.packages, SPEC.forms)
        por_text = str(primary.manifest.get("period_of_report") or "")
        por = date.fromisoformat(por_text[:10])
        accession = str(primary.manifest.get("accession") or "")
        rows = {row["field_id"]: row for row in result["fields"]}
        nt = _narrative_or_none(primary)

        notes: list[tuple[str, str]] = []
        for field_id, mapping, date_group in _NARRATIVE_FIELDS:
            note = _rewrite_narrative_row(
                rows[field_id],
                nt,
                mapping,
                date_group=date_group,
                accession=accession,
            )
            if note is not None:
                notes.append((field_id, note))

        catalogue_checks = {
            check["check_id"]: check
            for check in contract.load_pack_schema("PK07")["checks"]
        }
        recomputed = {
            "goodwill_rollforward_closed": _goodwill_rollforward_row(
                rows, catalogue_checks["goodwill_rollforward_closed"], ledger, por
            ),
            "impairment_vs_carrying": _impairment_vs_carrying_row(
                rows, catalogue_checks["impairment_vs_carrying"], ledger, por
            ),
            "acquisition_scope_stated": _acquisition_scope_row(
                rows, catalogue_checks["acquisition_scope_stated"]
            ),
        }
        for index, check in enumerate(result["checks"]):
            replacement = recomputed.get(check["check_id"])
            if replacement is not None:
                result["checks"][index] = replacement

        limitations = [TABLE_CELL_RESERVED_LIMITATION]
        if all(
            rows[field_id]["quality_state"] != "valued"
            for field_id in _NUMERIC_FIELD_IDS
        ):
            limitations.append(NEGATIVE_YEAR_LIMITATION)
        note_by_field = dict(notes)
        for field_id, mapping, _date_group in _NARRATIVE_FIELDS:
            note = note_by_field.get(field_id)
            if note is None:
                continue
            section = mapping.section
            heading = (
                "whole document" if section is None else section.heading
            )
            limitations.append(
                f"pk07.{field_id}: {note}; section searched: {heading}"
            )
        result["limitations"] = list(
            dict.fromkeys((*result["limitations"], *limitations))
        )[:32]

        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK07 finalize refused: " + "; ".join(errors[:5])
            )
        return result


PRODUCER = Pk07Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
)

__all__ = [
    "ACQUISITION_DATE_PATTERN",
    "IMPAIRMENT_TESTING_PATTERN",
    "NEGATIVE_YEAR_LIMITATION",
    "NOTE_BC",
    "NOTE_IMP",
    "PURCHASE_ACCOUNTING_PATTERN",
    "TABLE_CELL_RESERVED_LIMITATION",
    "PRODUCER",
    "SPEC",
]
