"""PK08 producer: legal contingencies.

B.1 forms are {10-K, 10-K/A, 10-Q, 10-Q/A} with no issuer-class gate (ASC 450
is general), so every form outside that set types the whole pack
``not_applicable`` + ``form_outside_pack_forms``. The ledger fields ride the
framework: the accrual and range aliases are frozen B.3 ``FactMapping``
declarations, the balance-sheet line state is the framework's
``NilStateMapping`` (A.1 — the nil path the plain fact laws refuse) and the
contingency nature is the framework's ``AxisMemberMapping`` (A.2 — members of
the loss-contingency axis inside the primary period).

The five narrative fields and all three checks are producer-owned through
``Pk08Producer.finalize_result`` (the registry hook PK11 introduced; PK07
precedent), for one frozen-catalogue reason: PK08's catalogue carries no
narrative reason code at all (no ``narrative_span_not_located``, no
``governing_section_not_supplied``), so the stock section-scoped
``TextSpanMapping`` resolver would hand the contract validator reasons the
catalogue refuses and no envelope could ever be produced. ``finalize_result``
therefore runs the exact B.2/B.3 search itself (same :mod:`narrative`
pipeline, same frozen sections and patterns) and types every narrative absence
with the catalogue's ``missing_dependency``, carrying the intended stock code
verbatim in ``limitations`` (one line per non-valued row naming the section
searched; a row typed ``not_applicable`` by the form gate names no section —
no search ran). The hook also applies the C2 prose-range ruling: a range that
exists only in prose is never valued — the range rows retype
``numeric_value_in_narrative_only`` when the Contingencies subsection carries
a dollar amount within 200 characters of ``reasonably possible``.

The declared text mappings are the reserved form, so a producer that
registers no finalize hook stays byte-identical to BASE. Private imports from
:mod:`base` (``_select_primary`` precedent: PK10/PK07) reuse the frozen span
and digest shapes instead of duplicating them.
"""
from __future__ import annotations

from decimal import Decimal
import re
from typing import Any, Mapping

from .. import specialist_pack_contract as contract
from . import narrative
from .base import (
    AxisMemberMapping,
    CrossStatement,
    FactMapping,
    NilStateMapping,
    NarrativeHooks,
    PackInput,
    PackProducer,
    PackSpec,
    Presence,
    SpecialistPackError,
    TextSpanMapping,
    _dimensions_admitted,
    _raw_span,
    _select_primary,
    _text_span_digest,
    primary_period,
    register_extra_receipts,
)

SPEC = PackSpec(
    pack_id="PK08",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="pack.pk08.applicability/v1",
    applicable_classes=None,
)

# B.2 governing sections (frozen). The Contingencies subsection is the tail
# of NOTE_CC starting at the last occurrence of the word "Contingencies"
# inside it — the note heading itself may carry the only other occurrence.
NOTE_CC = narrative.SectionSpec(
    r"Note \d+ [–-] Commitments(?:, Contingencies)?[^.]{0,60}",
    (r"Note \d+ [–-]",),
)
ITEM3 = narrative.SectionSpec(
    r"Item\s+3\.?\s*Legal Proceedings",
    (r"Item\s+4\.",),
)
CONTINGENCIES_WORD = "Contingencies"

# B.3 patterns (frozen). The enum literals come from the catalogue field's
# own name (A.3): disclosed_range | not_estimable | no_range_language. The
# not_material arm's literal is deliberately kept as the packet names it —
# the catalogue does not declare it, so a match on that arm degrades to a
# non-valued missing_dependency row (A.3) instead of inventing a literal.
#
# Range-pattern revision v2 (F1/F2 review, 2026-10-20; provenance repaired
# F3, second review): the not_estimable arm also matches the adverb-after-"be"
# ("cannot be reasonably estimated"), the no-"be" ("cannot reasonably
# estimate"), not-able/unable, not-possible/impossible and estimate-cannot-
# be-made phrasings, and the governing arm is chosen by RANGE_ARM_PRIORITY
# over the whole Contingencies span, never first-match-by-position (a "no
# material" phrase earlier in the span must not oust a governing estimate
# clause). The digest of a text-span mapping is the digest of the bytes that
# performed the match, so the declared mapping below stamps
# mapping_rule_digest from the live RANGE_DISCLOSED_PATTERN — never from a
# shadow copy of older bytes kept only to hold a pin still.
RANGE_PATTERN_REVISION = "v2"
RANGE_ARM_PRIORITY = ("disclosed", "not_estimable", "not_material")
_RANGE_DISCLOSED_ARMS = (
    ("disclosed", r"range of (?:reasonably )?possible loss"),
    (
        "not_estimable",
        r"cannot (?:reasonably )?be estimated"
        r"|cannot be reasonably estimated"
        r"|cannot (?:reasonably )?estimate"
        r"|cannot be estimated"
        r"|not able to (?:reasonably )?estimate"
        r"|unable to (?:reasonably )?estimate"
        r"|not (?:reasonably )?estimable"
        # F2 (second review): the not-possible / impossible and estimate-
        # cannot-be-made sentences. The "of ..." gap may never cross a "."
        # (one sentence) and is bounded at 80 chars.
        r"|(?:is |was )?not possible to (?:reasonably )?(?:estimate|determine)"
        r"|impossible to (?:reasonably )?estimate"
        r"|estimates? (?:of [^.]{0,80}?)?(?:cannot|can not|could not) be made",
    ),
    (
        "not_material",
        r"not at least a reasonable possibility"
        r"|would not (?:have )?a material|no material",
    ),
)
RANGE_DISCLOSED_PATTERN = "|".join(
    f"(?P<{arm}>{body})" for arm, body in _RANGE_DISCLOSED_ARMS
)
_RANGE_ARM_SEARCH = {arm: re.compile(body) for arm, body in _RANGE_DISCLOSED_ARMS}
RANGE_ENUM_MAP = {
    "disclosed": "disclosed_range",
    "not_estimable": "not_estimable",
    "not_material": "not_material",
}
ALLEGATION_PATTERN = r"alleg(?:es|ed|ing|ations?)"
PROCEDURAL_STATUS_PATTERN = (
    r"(?:appeal|ruling|verdict|trial|dismiss|judgment|injunction|settle)"
)
# C2: a dollar amount within this many characters of "reasonably possible"
# inside the Contingencies subsection types the range rows as prose-only.
# v2 (F1 review, 2026-10-20): the amount also matches the full-digit form
# ($450,000,000), "$450 thousand" and $450m/$1.2bn abbreviations; every arm
# requires a digit after the optional space, so a bare "$" — or "$
# reasonably possible" — never fires the retype.
PROSE_RANGE_WINDOW = 200
PROSE_RANGE_PHRASE = "reasonably possible"
PROSE_RANGE_AMOUNT = re.compile(
    r"\$\s?\d[\d,.]* (?:million|billion|thousand)"
    r"|\$\s?\d[\d,]*(?:\.\d+)? ?[mbn]\b"
    r"|\$\s?\d[\d,]*(?:\.\d+)?"
)

# B.3 concept aliases (us-gaap; priority order p10/p20; undimensioned).
_ACCRUAL = (
    "us-gaap:LossContingencyAccrualAtCarryingValue",
    "us-gaap:AccrualForEnvironmentalLossContingencies",
)
_RANGE_LOW = ("us-gaap:LossContingencyRangeOfPossibleLossMinimum",)
_RANGE_HIGH = ("us-gaap:LossContingencyRangeOfPossibleLossMaximum",)
_BS_STATE_CONCEPT = "us-gaap:CommitmentsAndContingencies"
_NATURE_AXIS = "us-gaap:LossContingenciesByNatureOfContingencyAxis"

# The B.3 text-value contracts the finalize hook executes (and whose digests
# it stamps). Every narrative field is searched inside its governing section
# or the Contingencies subsection derived from it, so each mapping declares
# NOTE_CC/ITEM3 and the hook narrows the span itself. The range mapping
# carries the live RANGE_DISCLOSED_PATTERN — the bytes the search runs are
# the bytes mapping_rule_digest pins (F3 seat ruling).
_RANGE_DISCLOSED_MAPPING = TextSpanMapping(
    section=NOTE_CC, pattern=RANGE_DISCLOSED_PATTERN, kind="enum"
)
_COMMITMENTS_BLOCK_MAPPING = TextSpanMapping(
    section=NOTE_CC, pattern="", kind="text", max_chars=512
)
_ITEM3_BLOCK_MAPPING = TextSpanMapping(
    section=ITEM3, pattern="", kind="text", max_chars=512
)
_ALLEGATION_MAPPING = TextSpanMapping(
    section=ITEM3, pattern=ALLEGATION_PATTERN, kind="text"
)
_PROCEDURAL_MAPPING = TextSpanMapping(
    section=ITEM3, pattern=PROCEDURAL_STATUS_PATTERN, kind="text"
)

TABLE_CELL_RESERVED_LIMITATION = (
    "pk08.table_cell_reserved: loss_contingency_range_low and "
    "loss_contingency_range_high resolve from xbrl_fact only in this version"
)
RANGE_IN_PROSE_ONLY_LIMITATION = (
    "pk08.range_in_prose_only: a reasonably possible loss range appears only "
    "in the Contingencies narrative; the range rows are never valued from "
    "prose (R-K4')"
)

_QUARTERLY_FORMS = frozenset({"10-Q", "10-Q/A"})

_FIELD_MAPPINGS = {
    "loss_contingency_accrual": FactMapping(_ACCRUAL),
    "loss_contingency_range_low": FactMapping(_RANGE_LOW),
    "loss_contingency_range_high": FactMapping(_RANGE_HIGH),
    # Reserved at the mapping layer; the finalize hook runs the real B.3
    # search (see the mappings above).
    "loss_contingency_range_disclosed": TextSpanMapping(),
    "contingency_nature": AxisMemberMapping(_NATURE_AXIS),
    # A.1: nil_literal is the catalogue's own literal; valued_literal is the
    # packet's name — a catalogue that does not declare it gets the A.3
    # refusal (non-valued missing_dependency), never an invented literal.
    "commitments_and_contingencies_bs_state": NilStateMapping(
        _BS_STATE_CONCEPT,
        nil_literal="nil_disclosed",
        valued_literal="valued",
    ),
    "commitments_text_block": TextSpanMapping(),
    # Part II Item 1 carries legal proceedings on 10-Q (K3K4 ruling), so the
    # Item 3 field is form-excluded there through the stock narrative hook.
    "legal_proceedings_item3": TextSpanMapping(),
    "allegation_span": TextSpanMapping(),
    "procedural_status_span": TextSpanMapping(),
}

# Placeholder CheckSpecs (kind-matched to the catalogue) the finalize hook
# replaces: the stock CrossStatement cannot state the three-operand
# low <= accrual <= high band, and the stock Presence check cannot state the
# nil-vs-note explanation pattern.
_CHECKS = (
    CrossStatement(
        check_id="accrual_vs_range",
        left="loss_contingency_range_low",
        right="loss_contingency_range_high",
        relation="left_lte_right",
    ),
    Presence(
        check_id="nil_bs_vs_note",
        field_id="commitments_and_contingencies_bs_state",
    ),
    Presence(check_id="item3_vs_note", field_id="legal_proceedings_item3"),
)


# --- B.6 receipts --------------------------------------------------------------


def _extra_receipts(pack_input: Any, ledger: Any) -> tuple[str, ...]:
    """One receipt line: the nil occurrences the bs_state row cites."""
    if ledger is None:
        return ("nil_fact_ids=",)
    try:
        por = primary_period(pack_input, SPEC.forms)
    except SpecialistPackError:
        return ("nil_fact_ids=",)
    ids = sorted(
        str(occurrence.occurrence_id)
        for occurrence in ledger.events
        if occurrence.concept_qname == _BS_STATE_CONCEPT
        and occurrence.is_nil
        and occurrence.context.instant is not None
        and occurrence.context.instant == por
        and _dimensions_admitted(occurrence, ())
    )
    return (f"nil_fact_ids={','.join(ids)}",)


register_extra_receipts("PK08", _extra_receipts)


# --- B.2/B.3 narrative search (producer-owned; see module docstring) -----------


def _narrative_or_none(primary: Any) -> Any:
    """The primary document's narrative text, or ``None`` when not retained."""
    try:
        return narrative.primary_document_text(primary)
    except SpecialistPackError:
        return None


def _contingencies_span(nt: Any, note_span: tuple[int, int]) -> tuple[int, int] | None:
    """The Contingencies subsection: last "Contingencies" inside NOTE_CC."""
    segment = nt.text[note_span[0] : note_span[1]]
    last = None
    for match in re.finditer(CONTINGENCIES_WORD, segment):
        last = match
    if last is None:
        return None
    return (note_span[0] + last.start(), note_span[1])


def _trimmed_block(text: str, limit: int) -> str:
    """The first ``limit`` characters, trimmed back to a sentence boundary."""
    if len(text) <= limit:
        return text
    block = text[:limit]
    cut = block.rfind(". ")
    return block[: cut + 1] if cut >= 0 else block


def _declared_enum_literals(
    catalogue: Mapping[str, Any], field_id: str
) -> frozenset[str]:
    """A.3: the enum literals the catalogue field's own name declares."""
    from .base import _catalogue_enum_literals

    for field in catalogue["fields"]:
        if field["field_id"] == field_id:
            declared = _catalogue_enum_literals(field)
            return declared if declared is not None else frozenset()
    return frozenset()


class _Sections:
    """The located governing sections of one production."""

    def __init__(self, nt: Any) -> None:
        self.note_cc: tuple[int, int] | None = None
        self.conting: tuple[int, int] | None = None
        self.item3: tuple[int, int] | None = None
        if nt is None:
            return
        self.note_cc = narrative.locate_section(nt, NOTE_CC)
        if self.note_cc is not None:
            self.conting = _contingencies_span(nt, self.note_cc)
        self.item3 = narrative.locate_section(nt, ITEM3)


class _RowRewriter:
    """Rewrites one reserved narrative row with the B.2/B.3 search result."""

    def __init__(self, row: dict[str, Any], nt: Any, accession: str) -> None:
        self.row = row
        self.nt = nt
        self.accession = accession
        self.note: str | None = None  # intended stock code, for limitations

    def _stamp(self, mapping: TextSpanMapping) -> None:
        field_id = self.row["field_id"]
        self.row["mapping_rule_id"] = f"pk08.{field_id}.text_span/v1"
        self.row["mapping_rule_digest"] = _text_span_digest(mapping)

    def valued(
        self,
        mapping: TextSpanMapping,
        text_value: str,
        span: tuple[int, int],
    ) -> None:
        row = self.row
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["quality_state"] = "valued"
        row["non_value_state"] = None
        row["coverage_state"] = "source_trace_complete"
        row["reason"] = None
        row["value"] = None
        row["text_value"] = text_value
        row["source_span"] = _raw_span(self.nt, span[0], span[1], self.accession)
        self._stamp(mapping)

    def absent(self, mapping: TextSpanMapping, note: str) -> None:
        """Type one absence with the catalogue's ``missing_dependency``.

        ``note`` is the intended stock reason (``governing_section_not_
        supplied`` / ``narrative_span_not_located`` / the refused-literal
        case) and rides verbatim in the envelope's limitations.
        """
        row = self.row
        quality_state = (
            "not_evaluable" if note == "governing_section_not_supplied" else "missing"
        )
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["quality_state"] = quality_state
        row["non_value_state"] = quality_state
        row["coverage_state"] = "unmapped"
        row["reason"] = "missing_dependency"
        row["value"] = None
        row["text_value"] = None
        row["source_span"] = None
        self._stamp(mapping)
        self.note = note


def _governing_range_arm(
    text: str, lo: int, hi: int
) -> tuple[str, re.Match[str] | None]:
    """The governing range arm in ``text[lo:hi]``: fixed priority, not position.

    F2: arms evaluate in RANGE_ARM_PRIORITY order (disclosed >
    not_estimable > not_material) over the whole Contingencies span, so a
    ``no material`` phrase earlier in the span never ousts a governing
    estimate clause. Returns ``("", None)`` when no arm matches.
    """
    for arm in RANGE_ARM_PRIORITY:
        match = _RANGE_ARM_SEARCH[arm].search(text, lo, hi)
        if match is not None:
            return arm, match
    return "", None


def _rewrite_enum_row(
    row: dict[str, Any],
    nt: Any,
    sections: _Sections,
    accession: str,
    declared: frozenset[str],
) -> _RowRewriter:
    rewriter = _RowRewriter(row, nt, accession)
    if row.get("quality_state") == "not_applicable":
        return rewriter  # the form gate owns this row; no search ran
    if nt is None:
        rewriter.absent(_RANGE_DISCLOSED_MAPPING, "narrative document not retained")
        return rewriter
    if sections.conting is None:
        # No Contingencies subsection: the note itself was not supplied, or
        # the note carries no such heading (B.2's optional arm).
        rewriter.absent(_RANGE_DISCLOSED_MAPPING, "governing_section_not_supplied")
        return rewriter
    lo, hi = sections.conting
    arm, match = _governing_range_arm(nt.text, lo, hi)
    if match is None:
        rewriter.absent(_RANGE_DISCLOSED_MAPPING, "narrative_span_not_located")
        return rewriter
    literal = RANGE_ENUM_MAP[arm]
    if literal not in declared:
        # A.3: this packet names a literal the catalogue does not declare;
        # never invent it (the framework's own A.4 law for enum rows).
        rewriter.absent(
            _RANGE_DISCLOSED_MAPPING,
            f"narrative_span_not_located (catalogue lacks literal {literal!r})",
        )
        return rewriter
    rewriter.valued(
        _RANGE_DISCLOSED_MAPPING, literal, (match.start(), match.end())
    )
    return rewriter


def _rewrite_block_row(
    row: dict[str, Any],
    nt: Any,
    sections: _Sections,
    accession: str,
    *,
    mapping: TextSpanMapping,
    span: tuple[int, int] | None,
    after_heading: bool,
) -> _RowRewriter:
    rewriter = _RowRewriter(row, nt, accession)
    if row.get("quality_state") == "not_applicable":
        return rewriter  # the form gate owns this row; no search ran
    if nt is None:
        rewriter.absent(mapping, "narrative document not retained")
        return rewriter
    if span is None:
        rewriter.absent(mapping, "governing_section_not_supplied")
        return rewriter
    lo, hi = span
    if after_heading:
        heading_match = re.compile(ITEM3.heading).match(nt.text, lo, hi)
        if heading_match is not None:
            lo = heading_match.end()
    block = _trimmed_block(nt.text[lo:hi], mapping.max_chars)
    lead = len(block) - len(block.lstrip())
    text_value = block.strip()
    rewriter.valued(mapping, text_value, (lo + lead, lo + lead + len(text_value)))
    return rewriter


def _rewrite_sentence_row(
    row: dict[str, Any],
    nt: Any,
    sections: _Sections,
    accession: str,
    *,
    mapping: TextSpanMapping,
    pattern: str,
) -> _RowRewriter:
    rewriter = _RowRewriter(row, nt, accession)
    if row.get("quality_state") == "not_applicable":
        return rewriter  # the form gate owns this row; no search ran
    if nt is None:
        rewriter.absent(mapping, "narrative document not retained")
        return rewriter
    if sections.item3 is None:
        rewriter.absent(mapping, "governing_section_not_supplied")
        return rewriter
    lo, hi = sections.item3
    match = re.compile(pattern).search(nt.text, lo, hi)
    if match is None:
        rewriter.absent(mapping, "narrative_span_not_located")
        return rewriter
    span = narrative.sentence_span(nt.text, match.start(), match.end(), (lo, hi))
    text_value = nt.text[span[0] : span[1]].strip()[: mapping.max_chars]
    rewriter.valued(mapping, text_value, span)
    return rewriter


def _prose_range_fires(nt: Any, sections: _Sections) -> bool:
    """C2: a dollar amount near ``reasonably possible`` inside CONTING."""
    if nt is None or sections.conting is None:
        return False
    segment = nt.text[sections.conting[0] : sections.conting[1]]
    for match in re.finditer(PROSE_RANGE_PHRASE, segment):
        window = segment[
            max(0, match.start() - PROSE_RANGE_WINDOW) : match.start()
            + PROSE_RANGE_WINDOW
        ]
        if PROSE_RANGE_AMOUNT.search(window):
            return True
    return False


# --- B.4 checks (producer-owned rows) ------------------------------------------


def _check_row(
    catalogue_check: Mapping[str, Any],
    status: str,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    operands = list(catalogue_check.get("operands") or [])
    return {
        "check_id": catalogue_check["check_id"],
        "kind": catalogue_check["kind"],
        "status": status,
        "operands": operands,
        "tolerance": None,
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


def _accrual_vs_range_row(
    rows: Mapping[str, Mapping[str, Any]], catalogue_check: Mapping[str, Any]
) -> dict[str, Any]:
    """low <= accrual <= high when all three are valued (B.4)."""
    accrual = _row_decimal(rows, "loss_contingency_accrual")
    low = _row_decimal(rows, "loss_contingency_range_low")
    high = _row_decimal(rows, "loss_contingency_range_high")
    if accrual is None or low is None or high is None:
        return _check_row(
            catalogue_check, "not_evaluable", reason="missing_dependency"
        )
    holds = low <= accrual <= high
    return _check_row(catalogue_check, "pass" if holds else "fail")


def _nil_bs_vs_note_row(
    rows: Mapping[str, Mapping[str, Any]], catalogue_check: Mapping[str, Any]
) -> dict[str, Any]:
    bs_state = rows["commitments_and_contingencies_bs_state"]
    block = rows["commitments_text_block"]
    if bs_state.get("quality_state") != "valued":
        return _check_row(
            catalogue_check, "not_evaluable", reason="missing_dependency"
        )
    if str(bs_state["text_value"]) == "valued":
        # A valued balance-sheet line needs no note explanation (B.4).
        return _check_row(catalogue_check, "pass")
    # The nil literal: the note must explain the nil line.
    if block.get("quality_state") == "valued":
        return _check_row(catalogue_check, "pass")
    return _check_row(catalogue_check, "fail")


def _item3_vs_note_row(
    rows: Mapping[str, Mapping[str, Any]], catalogue_check: Mapping[str, Any]
) -> dict[str, Any]:
    item3 = rows["legal_proceedings_item3"]
    block = rows["commitments_text_block"]
    if item3.get("quality_state") == "not_applicable":
        # K3K4: on quarterly forms legal proceedings live in Part II Item 1.
        reason = item3.get("reason")
        return _check_row(
            catalogue_check,
            "not_applicable",
            reason=str(reason) if reason is not None else "form_outside_pack_forms",
        )
    if (
        item3.get("quality_state") != "valued"
        or block.get("quality_state") != "valued"
    ):
        return _check_row(
            catalogue_check, "not_evaluable", reason="missing_dependency"
        )
    return _check_row(catalogue_check, "pass")


# --- B.5/B.6 limitations + the finalize hook -----------------------------------


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


_NARRATIVE_FIELD_IDS = (
    "loss_contingency_range_disclosed",
    "commitments_text_block",
    "legal_proceedings_item3",
    "allegation_span",
    "procedural_status_span",
)


_ITEM3_SECTION_FIELDS = (
    "legal_proceedings_item3",
    "allegation_span",
    "procedural_status_span",
)


def _section_heading_for(field_id: str) -> str:
    if field_id in _ITEM3_SECTION_FIELDS:
        return ITEM3.heading
    return NOTE_CC.heading


class Pk08Producer(PackProducer):
    """PK08 declaration plus the narrative/check finalize hook."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        if result["applicability"]["state"] != "applicable":
            return result  # the not-applicable path is already exact (B.1)
        primary, _matched = _select_primary(pack_input.packages, SPEC.forms)
        accession = str(primary.manifest.get("accession") or "")
        rows = {row["field_id"]: row for row in result["fields"]}
        nt = _narrative_or_none(primary)
        sections = _Sections(nt)
        catalogue = contract.load_pack_schema("PK08")
        declared = _declared_enum_literals(
            catalogue, "loss_contingency_range_disclosed"
        )

        notes: list[tuple[str, str]] = []
        rewriter = _rewrite_enum_row(
            rows["loss_contingency_range_disclosed"],
            nt,
            sections,
            accession,
            declared,
        )
        if rewriter.note is not None:
            notes.append(
                ("loss_contingency_range_disclosed", rewriter.note)
            )
        rewriter = _rewrite_block_row(
            rows["commitments_text_block"],
            nt,
            sections,
            accession,
            mapping=_COMMITMENTS_BLOCK_MAPPING,
            span=sections.conting,
            after_heading=False,
        )
        if rewriter.note is not None:
            notes.append(("commitments_text_block", rewriter.note))
        rewriter = _rewrite_block_row(
            rows["legal_proceedings_item3"],
            nt,
            sections,
            accession,
            mapping=_ITEM3_BLOCK_MAPPING,
            span=sections.item3,
            after_heading=True,
        )
        if rewriter.note is not None:
            notes.append(("legal_proceedings_item3", rewriter.note))
        rewriter = _rewrite_sentence_row(
            rows["allegation_span"],
            nt,
            sections,
            accession,
            mapping=_ALLEGATION_MAPPING,
            pattern=ALLEGATION_PATTERN,
        )
        if rewriter.note is not None:
            notes.append(("allegation_span", rewriter.note))
        rewriter = _rewrite_sentence_row(
            rows["procedural_status_span"],
            nt,
            sections,
            accession,
            mapping=_PROCEDURAL_MAPPING,
            pattern=PROCEDURAL_STATUS_PATTERN,
        )
        if rewriter.note is not None:
            notes.append(("procedural_status_span", rewriter.note))

        # C2: the prose-only range ruling retypes the absent range rows.
        prose_range = _prose_range_fires(nt, sections)
        if prose_range:
            for field_id in (
                "loss_contingency_range_low",
                "loss_contingency_range_high",
            ):
                row = rows[field_id]
                if row["quality_state"] != "valued":
                    row["reason"] = "numeric_value_in_narrative_only"

        catalogue_checks = {
            check["check_id"]: check for check in catalogue["checks"]
        }
        recomputed = {
            "accrual_vs_range": _accrual_vs_range_row(
                rows, catalogue_checks["accrual_vs_range"]
            ),
            "nil_bs_vs_note": _nil_bs_vs_note_row(
                rows, catalogue_checks["nil_bs_vs_note"]
            ),
            "item3_vs_note": _item3_vs_note_row(
                rows, catalogue_checks["item3_vs_note"]
            ),
        }
        for index, check in enumerate(result["checks"]):
            replacement = recomputed.get(check["check_id"])
            if replacement is not None:
                result["checks"][index] = replacement

        # B.6: one line per non-valued row naming what was searched. Rows the
        # form gate typed not_applicable cite no section — no search ran.
        limitations: list[str] = []
        if prose_range:
            limitations.append(RANGE_IN_PROSE_ONLY_LIMITATION)
        note_by_field = dict(notes)
        for field_id in _NARRATIVE_FIELD_IDS:
            note = note_by_field.get(field_id)
            if note is None:
                continue
            limitations.append(
                f"pk08.{field_id}: {note}; "
                f"section searched: {_section_heading_for(field_id)}"
            )
        for field_id, aliases in (
            ("loss_contingency_accrual", _ACCRUAL),
            ("loss_contingency_range_low", _RANGE_LOW),
            ("loss_contingency_range_high", _RANGE_HIGH),
        ):
            row = rows[field_id]
            if row["quality_state"] == "valued":
                continue
            if row["reason"] == "numeric_value_in_narrative_only":
                continue  # the prose-only limitation line already names it
            limitations.append(
                f"pk08.{field_id}: {row['reason']}; "
                f"ledger aliases searched: {', '.join(aliases)}"
            )
        nature = rows["contingency_nature"]
        if nature["quality_state"] != "valued":
            limitations.append(
                f"pk08.contingency_nature: {nature['reason']}; "
                f"axis searched: {_NATURE_AXIS} (primary period)"
            )
        bs_state = rows["commitments_and_contingencies_bs_state"]
        if bs_state["quality_state"] != "valued" and bs_state["source_occurrence_ids"]:
            # The A.3 refusal: the occurrence exists but the catalogue
            # declares no literal for its state.
            limitations.append(
                "pk08.commitments_and_contingencies_bs_state: "
                "narrative_span_not_located (catalogue lacks literal 'valued'); "
                "occurrence retained, literal refused"
            )
        result["limitations"] = list(
            dict.fromkeys((*result["limitations"], *limitations))
        )[:32]

        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK08 finalize refused: " + "; ".join(errors[:5])
            )
        return result


HOOKS = NarrativeHooks(
    field_form_exclusions={
        "legal_proceedings_item3": (_QUARTERLY_FORMS, "form_outside_pack_forms"),
    },
)

PRODUCER = Pk08Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    limitations=(TABLE_CELL_RESERVED_LIMITATION,),
    hooks=HOOKS,
)

__all__ = [
    "ALLEGATION_PATTERN",
    "HOOKS",
    "ITEM3",
    "NOTE_CC",
    "PRODUCER",
    "PROCEDURAL_STATUS_PATTERN",
    "RANGE_ARM_PRIORITY",
    "RANGE_DISCLOSED_PATTERN",
    "RANGE_IN_PROSE_ONLY_LIMITATION",
    "RANGE_PATTERN_REVISION",
    "SPEC",
    "TABLE_CELL_RESERVED_LIMITATION",
]
