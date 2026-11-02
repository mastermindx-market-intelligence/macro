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
# A "Financing" heading that names receivables or a lease-only note is not a
# debt note (N4), so it never matches. The last body occurrence wins
# (skip_toc=False): every dev filing lists the note in its index first, and
# the cross-reference filter below keeps a trailing "see Note 9. Debt"
# mention from stealing that pick. The section ends at the next note heading.
NOTE_DEBT = narrative.SectionSpec(
    r"(?:Note|NOTE)\s*\d+\s*[.:–\-]?\s*"
    r"(?:(?:Short[- ]?[Tt]erm and )?Long[- ]?[Tt]erm )?"
    r"(?:Debt|Financing(?!\s+(?:Receivables?|Leases?))|Borrowings)",
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
# One raw-document tag: ``<div ...>``, ``</ix:nonFraction>``, ...
_TAG_RE = re.compile(rb"</?\s*([A-Za-z:][\w.:-]*)")
# HTML elements that open or close a block. Only these bound a sentence or
# separate a heading from preceding text; inline markup (``span``, ``a``,
# ``b``, ``i``, ``font``, ...) and the ``ix:*`` wrappers sit mid-sentence.
_BLOCK_TAGS = frozenset(
    (
        "address article aside blockquote body br caption center dd div dl dt"
        " footer h1 h2 h3 h4 h5 h6 header hr html li ol p pre section table"
        " tbody td tfoot th thead tr ul"
    ).split()
)
# A footnote or list marker that opens a sentence: "(1) ", "(a) ", "(iv) ",
# "* ". It is table-footnote residue, not part of the disclosure.
_LEADING_MARKER_RE = re.compile(
    r"(?:\((?:\d{1,3}|[A-Za-z]|[ivxlcIVXLC]{1,6})\)|[*\u2020\u2021]+) "
)


def _is_block_tag(name: bytes) -> bool:
    """True for an HTML block element under any namespace prefix but ``ix:``."""
    lowered = name.decode("ascii", "replace").lower()
    if lowered.startswith("ix:"):
        return False
    return lowered.rsplit(":", 1)[-1] in _BLOCK_TAGS


def _block_tag_between(raw: bytes, start: int, end: int) -> bool:
    """True when a block tag opens or closes in ``raw[start:end]``."""
    return any(
        _is_block_tag(tag.group(1)) for tag in _TAG_RE.finditer(raw, start, end)
    )


def _cross_reference(nt: Any, raw: bytes, heading: re.Match) -> bool:
    """N4: True when a heading mention continues another note's sentence.

    A cross-reference ("see Note 9. Debt", "(Note 9. Debt)", "Item 8 Note 9.
    Debt") runs mid-sentence: the text immediately before it is a lowercase
    word, a digit (a page or item number), a comma, a semicolon or an opening
    parenthesis, with no block tag between that text and the heading. Inline
    markup such as a hyperlink around the mention does not clear it. A real
    note heading starts its own block even when its element carries a
    trailing space, so a block tag in between clears the mention; the
    selection stays structural and never issuer-shaped. A number that opens
    the heading's own block ("<div>F-12 Note 7. Debt") is page residue, not
    an item number, so a block tag before that number clears the mention too.
    """
    back = heading.start() - 1
    while back >= 0 and nt.text[back] == " ":
        back -= 1
    if back < 0 or not (
        nt.text[back].islower() or nt.text[back].isdigit() or nt.text[back] in ",;("
    ):
        return False
    prev_end = nt.offsets[back] + len(nt.text[back].encode("utf-8"))
    if _block_tag_between(raw, prev_end, nt.offsets[heading.start()]):
        return False
    if not nt.text[back].isdigit():
        return True
    token = back
    while token > 0 and nt.text[token - 1] != " ":
        token -= 1
    prior = token - 1
    while prior >= 0 and nt.text[prior] == " ":
        prior -= 1
    if prior < 0:
        return False
    prior_end = nt.offsets[prior] + len(nt.text[prior].encode("utf-8"))
    return not _block_tag_between(raw, prior_end, nt.offsets[token])


def _locate_debt_section(nt: Any, raw: bytes) -> narrative.Span | None:
    """(start, end) of the debt-note body, or ``None`` when not supplied.

    ``narrative.locate_section`` semantics over ``NOTE_DEBT`` with the N4
    filter: cross-reference mentions are dropped before the last-occurrence
    pick, so the note body wins over a trailing mention.
    """
    matches = list(re.finditer(NOTE_DEBT.heading, nt.text, re.IGNORECASE))
    if not matches:
        return None
    body = [m for m in matches if not _cross_reference(nt, raw, m)]
    chosen = (body or matches)[-1]
    end = len(nt.text)
    for end_heading in NOTE_DEBT.end_headings:
        boundary = re.compile(end_heading, re.IGNORECASE).search(
            nt.text, chosen.end()
        )
        if boundary is not None:
            end = min(end, boundary.start())
    return (chosen.start(), end)


def _structural_break(nt: Any, raw: bytes, space_at: int, bound: int) -> bool:
    """True when the collapsed space at ``space_at`` abuts a block tag.

    The raw slice between this space and the next emitted character (which
    must lie before ``bound``) holds the tags the whitespace collapse folded
    into it. A block element (``div``, ``p``, ``td``, ``br``, ...) is a
    heading / table-cell / paragraph boundary. Inline markup (``span``,
    ``a``, ``b``, ``font``, ...) and the inline-XBRL ``ix:*`` wrappers sit
    mid-sentence, so a bolded "not" or a hyperlinked subject stays in the
    sentence.
    """
    nxt = space_at + 1
    while nxt < bound and nt.text[nxt] == " ":
        nxt += 1
    if nxt >= bound:
        return False
    return _block_tag_between(raw, nt.offsets[space_at], nt.offsets[nxt])


_OPENERS = "\"'\u201c\u2018"
_CLOSERS = "\"')\u201d\u2019"


# Page residue a page break leaves inside a sentence: a bare page number
# ("42", "F-23", "Page 7") or a running "Table of Contents" link.
_PAGE_RESIDUE_RE = re.compile(
    r"(?:Page |F-)?\d{1,4}|Table of Contents", re.IGNORECASE
)
# A negation or failure word. Dropping one from the front of a sentence
# could invert the disclosure ("was not, as of<br/>December 31, ...").
_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|nor|neither|cannot|without|unable"
    r"|fail(?:ed|s|ing|ure)?\s+to)\b"
    r"|n['’]t",
    re.IGNORECASE,
)


def _ends_sentence(text: str, space_at: int) -> bool:
    """True when the text before ``space_at`` ends a sentence.

    Its last non-space character is ".", "!" or "?", optionally followed by
    a closing quote or parenthesis.
    """
    back = space_at - 1
    while back >= 0 and text[back] == " ":
        back -= 1
    while back >= 0 and text[back] in _CLOSERS:
        back -= 1
    return back >= 0 and text[back] in ".!?"


def _opens_sentence(text: str, nxt: int) -> bool:
    """True when the text at ``nxt`` can open a sentence.

    An uppercase letter or digit after an optional opening quote, or a
    footnote / list marker.
    """
    if _LEADING_MARKER_RE.match(text, nxt):
        return True
    head = nxt
    while head < len(text) and text[head] in _OPENERS:
        head += 1
    return head < len(text) and (text[head].isupper() or text[head].isdigit())


def _block_start(nt: Any, raw: bytes, end: int, lo: int) -> int:
    """Start of the block that holds the text just before ``end``."""
    k = end - 1
    while k > lo:
        if nt.text[k] == " " and _structural_break(nt, raw, k, end):
            return k + 1
        k -= 1
    return lo


def _ends_before_residue(nt: Any, raw: bytes, space_at: int, lo: int) -> bool:
    """True when the text before ``space_at`` ends a sentence.

    Page-residue blocks directly before the break are skipped first, so a
    page number between a sentence's end and the next sentence still counts
    as the end of that sentence.
    """
    end = space_at
    while True:
        start = _block_start(nt, raw, end, lo)
        if start <= lo or not _PAGE_RESIDUE_RE.fullmatch(nt.text[start:end].strip()):
            return _ends_sentence(nt.text, end)
        end = start - 1


def _is_residue_block(nt: Any, raw: bytes, start: int, bound: int) -> bool:
    """True when the block opening at ``start`` is page residue.

    The block runs to the next block break before ``bound``; a block that
    reaches ``bound`` holds the matched term and is never residue.
    """
    end = start
    while end < bound and not (
        nt.text[end] == " " and _structural_break(nt, raw, end, bound)
    ):
        end += 1
    if end >= bound:
        return False
    return bool(_PAGE_RESIDUE_RE.fullmatch(nt.text[start:end]))


def _drops_negation(text: str, lo: int, space_at: int) -> bool:
    """True when the sentence words before ``space_at`` hold a negation.

    Those are the words a span starting after ``space_at`` would drop: from
    the last sentence end (or ``lo``) up to the break.
    """
    j = space_at - 1
    while j > lo and not (text[j] == " " and _ends_sentence(text, j)):
        j -= 1
    return bool(_NEGATION_RE.search(text, max(j, lo), space_at))


def _sentence_start(nt: Any, raw: bytes, match_start: int, lo: int) -> int:
    """Char index where the covenant sentence begins (N3/N2).

    Scans left from the match: the sentence starts after the nearest ``". "``
    terminator or block-tag break that opens a sentence, so a note heading or
    a facilities table without sentence punctuation cannot bleed into the
    emitted text. A ``<br>`` or a page-break ``<div>`` / ``<hr>`` can fall
    mid-clause ("The Company was not<br/>in compliance ..."), so a block-tag
    break counts only when the text before it ends a sentence, or when the
    text after it opens one and the words it would drop hold no negation
    (F1). Page residue left by a page break (a page number or a "Table of
    Contents" link) never starts the sentence and never hides the end of the
    sentence before it. Otherwise the scan goes on left, which can only
    lengthen the span; the cap check still applies. The bound is one past
    the match start, so the space directly before the matched term is tested
    too.
    """
    i = match_start
    while i > lo:
        i -= 1
        if nt.text[i] != " ":
            continue
        if i - 1 >= lo and nt.text[i - 1] == ".":
            return i + 1
        if _structural_break(nt, raw, i, match_start + 1):
            nxt = i + 1
            while nxt < match_start and nt.text[nxt] == " ":
                nxt += 1
            if _is_residue_block(nt, raw, nxt, match_start + 1):
                continue
            if _ends_before_residue(nt, raw, i, lo):
                return nxt
            if _opens_sentence(nt.text, nxt) and not _drops_negation(
                nt.text, lo, i
            ):
                return nxt
    return lo


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


def _covenant_span(nt: Any, raw: bytes) -> tuple[str, tuple[int, int]] | None:
    """(sentence text, char span) of the governing covenant term in the note.

    The first covenant sentence that survives the cap check wins, as in the
    shipped selection. Known N1 limitation, fail-safe: that sentence can be
    a generic compliance sentence while a later sentence states the ratio
    and its threshold; the emitted value still contains its covenant term
    and its source_span slices back to it. N3/N2: the emitted
    text starts at the matched sentence, so heading words, table cells and
    page residue before it are dropped, as are leading footnote or list
    markers such as "(1) (a) ". A candidate whose matched term ends
    past the ``max_chars`` cap is dropped, so the cap only ever cuts a
    sentence's tail and an emitted value always contains its covenant term;
    when no candidate survives, the field stays unsupported.
    """
    section_span = _locate_debt_section(nt, raw)
    if section_span is None:
        return None
    lo, hi = section_span
    for match in re.compile(_COVENANT_MAPPING.pattern).finditer(nt.text, lo, hi):
        end = narrative.sentence_span(
            nt.text, match.start(), match.end(), section_span
        )[1]
        start = _sentence_start(nt, raw, match.start(), lo)
        marker = _LEADING_MARKER_RE.match(nt.text, start, match.start())
        while marker is not None:
            start = marker.end()
            marker = _LEADING_MARKER_RE.match(nt.text, start, match.start())
        if match.end() - start > _COVENANT_MAPPING.max_chars:
            continue  # the cap would cut the covenant term itself away
        while end > start and nt.text[end - 1] == " ":
            end -= 1
        if end - start > _COVENANT_MAPPING.max_chars:
            end = start + _COVENANT_MAPPING.max_chars
        return nt.text[start:end], (start, end)
    return None


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
        raw = primary.members.get(
            str(primary.manifest.get("primary_document") or "")
        )
        found = _covenant_span(nt, raw) if raw else None
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
