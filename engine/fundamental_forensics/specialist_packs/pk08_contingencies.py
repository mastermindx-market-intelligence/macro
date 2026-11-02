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

Dev-corpus generalization (litigation_v1, DEC-FIF-PACK-GENERALIZATION-DEV-
CORPUS; five litigation-heavy issuers disjoint from the held-out split). The
held-out run showed the pack abstaining on nearly every other filing; the
dev filings named four causes, each repaired behind its own explicit rule:

* **Note-title v2 (R1).** Real filings title the contingencies note
  ``19. Legal proceedings`` (no ``Note`` word, no ``Commitments``),
  ``NOTE 19. Commitments and Contingencies`` (dot, uppercase) or
  ``Note 23 – Legal Proceedings``. The frozen v1 heading matches none of
  them, so every note-ledger field abstained. v2 keeps NOTE_CC as the
  primary spec and adds three fallback specs (commitments / contingencies /
  legal-proceedings titles) consulted only when v1 locates nothing; every
  existing v1 result is therefore unchanged by construction.
* **Item-section v2 (R2/R3).** Litigation-heavy issuers put the allegations
  in the note and leave Part II Item 3 (10-K) / Part II Item 1 (10-Q) as a
  one-sentence incorporation-by-reference, and some 10-Ks carry no Part II
  Item 3 body at all (only the table-of-contents line, which the stock
  locator mistakes for the section — the held-out precision miss). v2
  artifact-guards the located item section (a page-number remnant is never a
  governing section) and, when a supplied item section carries no matching
  sentence, follows the issuer's own cross-reference into the contingencies
  subsection for ``allegation_span`` / ``procedural_status_span``. An item
  section that is not supplied at all keeps the frozen not_evaluable
  typed absence (K3K4). Inside that note fallback the procedural row also
  carries a precision guard: a matched sentence that names no proceeding
  (case, lawsuit, litigation, court, claim, proceeding, trial, action), or
  that carries estimation vocabulary, is accrual-methodology boilerplate
  the frozen keyword pattern collides with ("a complex series of judgments
  about future events"), not a procedural status, and is skipped; a note
  with no qualifying sentence keeps the typed absence. The primary
  item-section search is unchanged.
* **Range-arm v3 (R1b).** The note-location fix exposed the disclosed arm
  matching inside the standard ASC 450 refusal sentence ("unable to
  reasonably estimate a possible loss or range of possible loss"), which
  fixed arm priority then typed as disclosed_range. v3 requires a dollar
  amount after the phrase inside the same sentence — every genuine
  disclosure carries one ("range of reasonably possible loss of $10
  million to $20 million") — so the refusal idiom falls through to the
  not_estimable arm that already matches its verb.
* **Accrual dimension rule (R4).** ``us-gaap:LossContingencyAccrualAtCarrying
  Value`` is reported only under contingency-identity axes (a filer that
  reports the whole accrual only under an ``srt:LitigationCaseAxis`` or
  ``srt:ProductOrServiceAxis`` member on the dev corpus). The rule admits
  those facts when no undimensioned accrual resolves, every candidate's
  axes are inside the declared contingency-identity set and all candidates
  agree on one value; any other shape (extra axes such as a
  balance-sheet-location or litigation-status axis, or disagreeing member
  values) keeps the typed absence.
* **Range-axis rule (R5).** ``us-gaap:LossContingencyEstimateOfPossibleLoss``
  facts dimensioned by ``srt:RangeAxis`` ``MinimumMember``/``MaximumMember``
  carry the same range endpoints the frozen minimum/maximum concepts carry.
  The rule values the range rows from those facts (never from prose, R-K4');
  the row reports the instant the fact actually carries.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from typing import Any, Callable, Mapping

from .. import specialist_pack_contract as contract
from ..raw_ledger import decimal_text
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
    _dimension_qname_matches,
    _dimensions_admitted,
    _mapping_digest,
    _raw_span,
    _select_primary,
    _text_span_digest,
    _unit_equivalents,
    _unit_measure,
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
# K3K4: on quarterly forms legal proceedings live in Part II Item 1; the
# heading there uses the same title with the quarterly item number (a filer
# whose quarterly heading reads "Item 1 — Legal proceedings"). Searched for
# the two span fields only; legal_proceedings_item3 itself stays
# form-excluded on 10-Q.
ITEM1_QUARTERLY = narrative.SectionSpec(
    r"Item\s+1\s*[.·:–—-]?\s*Legal Proceedings",
    (r"Item\s+1A\.?", r"Item\s+2\.?"),
)
CONTINGENCIES_WORD = "Contingencies"

# R1 note-title v2. Real note titles: "Note N – Commitments and
# Contingencies" (v1), "NOTE N. Commitments and Contingencies", "N.
# Contingencies ...", "Note N – Legal Proceedings", "N. Legal proceedings".
# A note number is separated from its title by a dot or a spaced dash (a
# dash without spaces is a product/model number: "737-10", "450-20-25"),
# must not be glued to a preceding number or dot ("$1.2.", "2024.") and must
# not belong to an "Item N." heading. Cross-references ("See Note 19. The
# Company…") never carry a contingencies/commitments/legal-proceedings
# title, and the last match wins: every in-text cross-reference precedes
# the note body it cites. A table-of-contents line ("Legal Proceedings 114")
# is rejected by the page-number lookahead.
_NOTE_NUMBER = r"(?<![\d.·:–—/-])(?<!Item )(?:Note\s+)?\d{1,2}\s*(?:\.\s*|\s[.·:–—-]\s)"
_NOTE_HEADING_END = (
    # The next note-shaped heading: number + dot/spaced-dash + TitleCase,
    # with the same number-gluing guards.
    r"(?<![\d.·:–—/-])(?<!Item )(?:Note\s+)?\d{1,2}\s*(?:\.\s*|\s[.·:–—-]\s)[A-Z]",
    # The notes end where the next Part I/II item heading begins.
    r"Item\s+\d",
)
NOTE_CC_V2_SPECS = (
    narrative.SectionSpec(
        _NOTE_NUMBER + r"Commitments(?:\s+(?:and|&)\s+Contingencies)?(?!\s*\d)",
        _NOTE_HEADING_END,
    ),
    narrative.SectionSpec(
        _NOTE_NUMBER + r"Contingencies(?:\s+[A-Z][A-Za-z]+){0,3}(?!\s*\d)",
        _NOTE_HEADING_END,
    ),
    narrative.SectionSpec(
        _NOTE_NUMBER + r"Legal\s+Proceedings(?!\s*\d)",
        _NOTE_HEADING_END,
    ),
)
# The v2 contingencies subsection starts at the first title-shaped
# "Contingencies" occurrence (a capital-C word heading a run of text:
# "Contingencies The Company…", "Contingencies Warranties…"); a note without
# one ("19. Legal proceedings …") uses the whole note. The v1 path keeps the
# frozen last-occurrence rule (the golden fixture's subsection start is
# pinned by the existing envelope digest).
_CONTINGENCIES_TITLE = re.compile(r"Contingencies\s+[A-Z]")
# A located item section whose body is a bare page-number remnant (the
# section's end heading cut at the next TOC entry, leaving only " 114 "), or
# whose opening window carries a page number followed by the next item
# heading ("Legal Proceedings 22 Item 4. …"), is a table-of-contents line,
# never the governing section.
_ITEM_TOC_ARTIFACT = re.compile(r"\b\d{1,3}\s+Item\b")
_ITEM_TOC_REMNANT = re.compile(r"^[\s\d.,;:()\-–—]*$")

# R3 note-fallback precision guard (procedural_status_span): the frozen
# keyword pattern also matches estimation boilerplate — "a complex series of
# judgments about future events" and "estimates and judgments can be
# affected by" are accrual-methodology sentences, not a procedural status,
# and a proceeding noun alone does not separate them (the methodology
# sentence goes on to name ongoing litigation). Inside the note fallback a
# matched sentence must name the proceeding itself (case/lawsuit/litigation/
# court/claim/proceeding/trial/action, singular or plural) AND carry no
# estimation vocabulary ("estimate", "estimation", "assumption") and no
# "subject to … uncertainties" hedging; a note whose keyword sentences all
# fail the guard keeps the typed absence. The primary item-section search
# keeps the frozen first-match behavior.
#
# v2 (dev-corpus review, 2026-11-01) refuses two more wrong kinds. Accept:
# a sentence whose proceeding noun is stated indicatively ("lawsuits are
# pending", "verdicts … have been reversed on appeal"), and a sentence that
# reports an actual matter even though the reported words sit in a modal
# clause ("the Department notified us of its determination that it would
# not move to dismiss the case" — a dated report of an actual
# determination is a status). An actual matter is anchored by a
# pending/has-been state or a past-tense proceeding event
# (notified/ruled/dismissed/settled/tried/prevailed/…). Reject: (a) a
# sentence whose every proceeding noun is governed by a modal or
# forward-looking verb (can/may/could/might/would/will — "such requests
# can also lead to the assertion of claims … as well as to settlements",
# "the Company will retain … liabilities resulting from … litigation
# matters") and that carries no actual-matter anchor: it states a
# possibility or an allocation, not the status of any matter, and the
# search continues to a later genuine status sentence; (b) uncertainty
# hedging ("litigation is subject to inherent uncertainties"), which is
# accrual methodology whatever proceeding noun it names.
#
# v3 (second dev-corpus review, 2026-11-01) closes two admissions in v2.
# A bare-participle anchor ("obtained", "reversed") no longer fires when a
# modal sits in its immediate verb group: "any adverse judgment obtained
# at trial could be reversed on appeal" and "a trial verdict may be
# reversed on appeal" state possibilities, not statuses, while a modal
# reported in a distant subordinate clause ("notified us of its
# determination that the Department would not move to dismiss") does not
# govern the anchor and a dated report stays a status. And the no-anchor
# fallthrough now demands every proceeding noun's whole clause — left and
# right of the noun, up to the clause boundary — be modal-free, so
# "further proceedings could result in additional settlements" and
# "claims may be asserted in the future that could lead to trials" state
# possibilities even though a noun precedes the modal.
#
# v4 (third dev-corpus review, 2026-11-01) replaces v3's four-word
# verb-group window with whole-clause governance. An anchor is governed
# when a modal ("should"/"shall" now included) or a forward-looking
# marker ("expect"/"anticipate" in any form, "likely", "intends to",
# "plans to", "future", "potential") sits anywhere in its clause, before
# or after it at any distance; after the anchor a reported clause opened
# by a complementizer "that"/"whether" shields the governor so a dated
# report of another party's intention stays a status. The no-anchor
# fallthrough and the allegation against-branch test the same vocabulary
# over the whole clause. A "may" is the calendar month, never a modal,
# when whitespace and a digit follow it or when it is written "May" past
# the sentence's first word.
_PROCEEDING_NOUN = re.compile(
    r"\b(?:cases?|lawsuits?|litigation|courts?|claims?|proceedings?|trials?|actions?)\b",
    re.IGNORECASE,
)
_ESTIMATION_VOCAB = re.compile(r"\bestimat|\bassumption", re.IGNORECASE)
_UNCERTAINTY_VOCAB = re.compile(
    r"subject to (?:[a-z]+ ){0,2}uncertaint", re.IGNORECASE
)
# v4 modality vocabulary: a clause that carries a modal verb or a
# forward-looking marker states a possibility or an expectation, never
# the status of a matter or a made claim. ``must`` and ``seeks to`` are
# deliberately absent: an obligation or a request is not a possibility.
# v5 (fourth dev-corpus review): the bare verbs "expect"/"anticipate"
# with a noun object or a negation ("does not expect the cases to reach
# trial", "expects a ruling by year end") state an expected future just
# as the to-complement forms do, so every inflection is a marker.
_MODAL_WORD = re.compile(
    r"\b(?:can|could|may|might|would|will|should|shall)\b", re.IGNORECASE
)
_FORWARD_MARKER = re.compile(
    r"\b(?:expect(?:s|ed|ing)?|anticipat(?:e|es|ed|ing)|likely"
    r"|intends to|plans to|future|potential)\b",
    re.IGNORECASE,
)
# A reported clause opened by "that"/"whether" carries its own modality,
# which never governs an earlier anchor: "notified us of its
# determination that the Department would not move to dismiss". The
# opening word is a complementizer only when the next word is a
# determiner, a pronoun or a capitalized word; a demonstrative ("in that
# matter could") opens nothing and leaves the modal governing.
_COMPLEMENTIZER = re.compile(r"\b(?:that|whether)\b", re.IGNORECASE)
_COMPLEMENTIZER_HEAD = frozenset(
    "the a an it its we our they their he she this these those such no any".split()
)
_MAY_NUMBER = re.compile(r"\s+\d")
_ANY_WORD = re.compile(r"\w")
_NEXT_WORD = re.compile(r"\s+(\w+)")
_ACTUAL_MATTER = re.compile(
    r"\b(?:is|are|was|were|remains?|remain)\s+(?:currently\s+)?pending"
    r"|\b(?:has|have|had)\s+been"
    r"|\b(?:notified|determined|ruled|decided|dismissed|settled|entered|"
    r"filed|granted|denied|prevailed|obtained|reversed|tried|defended|"
    r"begun|began|delivered|returned|held|awarded|appealed|paid|accrued)\b",
    re.IGNORECASE,
)


def _clause_head(sentence: str, upto: int) -> int:
    """Offset just past the last clause-breaking punctuation before ``upto``."""
    cut = -1
    for match in re.finditer(r"[.!?;:]", sentence[:upto]):
        cut = match.end()
    return cut + 1


def _clause_end(sentence: str, after: int) -> int:
    """Offset of the next clause-breaking punctuation at/after ``after``."""
    match = re.search(r"[.!?;:]", sentence[after:])
    return after + match.start() if match else len(sentence)


def _is_calendar_may(sentence: str, m: "re.Match[str]") -> bool:
    """True when a matched "may" is the calendar month, never a modal.

    Either whitespace and a digit follow the word ("May 2", "May 2024"),
    or it is written exactly ``May`` (capital M, rest lowercase) at a
    position past the sentence's first word.
    """
    if _MAY_NUMBER.match(sentence, m.end()):
        return True
    return m.group(0) == "May" and _ANY_WORD.search(sentence, 0, m.start())


def _has_modal(sentence: str, start: int, end: int) -> bool:
    """A modal verb in sentence[start:end], calendar months excepted."""
    return any(
        not _is_calendar_may(sentence, m)
        for m in _MODAL_WORD.finditer(sentence, start, end)
    )


def _clause_states_possibility(sentence: str, start: int, end: int) -> bool:
    """A modal or a forward-looking marker anywhere in sentence[start:end]."""
    return _has_modal(sentence, start, end) or bool(
        _FORWARD_MARKER.search(sentence, start, end)
    )


def _reported_clause_between(sentence: str, start: int, end: int) -> bool:
    """A complementizer opens a reported clause between start and end."""
    for m in _COMPLEMENTIZER.finditer(sentence, start, end):
        nxt = _NEXT_WORD.match(sentence, m.end())
        if nxt is None:
            continue
        word = nxt.group(1)
        if word.lower() in _COMPLEMENTIZER_HEAD or word[:1].isupper():
            return True
    return False


def _governs_after(sentence: str, start: int, end: int) -> bool:
    """A modal or marker after ``start`` that no reported clause shields.

    A governor sitting beyond a complementizer ("determination that the
    Department would not move to dismiss") belongs to the reported
    clause, not to the anchor.
    """
    for m in _MODAL_WORD.finditer(sentence, start, end):
        if _is_calendar_may(sentence, m):
            continue
        if not _reported_clause_between(sentence, start, m.start()):
            return True
    for m in _FORWARD_MARKER.finditer(sentence, start, end):
        if not _reported_clause_between(sentence, start, m.start()):
            return True
    return False


def _anchor_is_governed(sentence: str, start: int, end: int) -> bool:
    """True when a modal or a forward-looking marker governs the anchor.

    The anchor's whole clause — the text between clause-breaking
    punctuation around it, commas included — is searched on both sides at
    any distance: "a trial verdict may be reversed" and "judgment
    obtained by the trial court in that matter could, in the event of an
    appeal, ultimately be reversed" are governed possibilities, while a
    modal reported in a subordinate clause ("notified us of its
    determination that the Department would not move to dismiss") does
    not govern the anchor and a dated report stays a status. A calendar
    "May" is never a modal.
    """
    if _clause_states_possibility(sentence, _clause_head(sentence, start), start):
        return True
    return _governs_after(sentence, end, _clause_end(sentence, end))


def _procedural_note_sentence(sentence: str) -> bool:
    """R3 guard: this keyword sentence is a procedural status, not method."""
    if _ESTIMATION_VOCAB.search(sentence) or _UNCERTAINTY_VOCAB.search(sentence):
        return False
    proceedings = list(_PROCEEDING_NOUN.finditer(sentence))
    if not proceedings:
        return False
    if any(
        not _anchor_is_governed(sentence, m.start(), m.end())
        for m in _ACTUAL_MATTER.finditer(sentence)
    ):
        return True
    # No anchor of an actual matter: a sentence states a possibility, not
    # the status of a matter, unless every proceeding noun sits in a
    # clause free of modals and forward-looking markers.
    return all(
        not _clause_states_possibility(
            sentence,
            _clause_head(sentence, m.start()),
            _clause_end(sentence, m.end()),
        )
        for m in proceedings
    )


# R3 note-fallback precision guard (allegation_span), symmetric to
# _procedural_note_sentence: the frozen allegation keyword also matches
# methodology and process sentences — a disclosure-process heading whose
# sentence goes on to hedge alleged damages as "subject to substantial
# uncertainties", a categories sentence ("the categories of legal
# proceedings … may involve … plaintiffs, raising claims"), a matter-
# progress sentence and a liability-allocation sentence ("will retain …
# liabilities resulting from … claims alleging harm"). The caller's
# pattern guarantees the assertion word (alleges/alleged/alleging/
# allegation(s)); the guard adds the claimed shape. Accept: a proceeding
# noun (case/lawsuit/litigation/court/claim/proceeding/trial/action)
# together with the assertion being made against the issuer — an
# "against the Company/Issuer/Registrant/us" reference whose own clause
# is indicative, an asserter shape (plaintiffs allege/assert/claim/
# contend; a complaint alleges/asserts/seeks), or claims that have been
# asserted/filed/brought. Reject: methodology vocabulary ("estimat",
# "assumption", a "process for disclosure" heading, "subject to …
# uncertainties" hedging), any sentence without a made-against shape,
# and an against-issuer reference whose whole clause carries a modal
# (can/could/may/might/would/will/should/shall, a calendar "May"
# excepted) or a forward-looking marker ("expect"/"anticipate" in any
# form, "likely", "intends to", "plans to", "future", "potential" —
# "future claims alleging fraud may be brought against the Company" is
# a possibility, not a made claim — the asserter and been-asserted
# shapes carry their own tense and stay accepted); a
# note whose keyword sentences all fail the guard keeps the typed
# absence. The primary item-section search keeps the frozen first-match
# behavior.
_ASSERTED_AGAINST_ISSUER = re.compile(
    r"\bagainst (?:the )?(?:company|issuer|registrant)\b"
    r"|\bagainst us\b"
    r"|\b(?:plaintiffs?|complainants?)\s+"
    r"(?:alleg\w*|assert\w*|claims?\b|claiming|contend\w*)"
    r"|\bcomplaint\s+(?:alleges|asserts|seeks)\b"
    r"|\b(?:have|has|had|were|was)\s+(?:been\s+)?(?:asserted|filed|brought)\b",
    re.IGNORECASE,
)
_METHODOLOGY_VOCAB = re.compile(
    r"\bestimat|\bassumption|\bprocess for disclosure\b"
    r"|subject to (?:[a-z]+ ){0,2}uncertaint",
    re.IGNORECASE,
)


def _allegation_note_sentence(sentence: str) -> bool:
    """R3 guard: this keyword sentence states a claim against the issuer."""
    if _METHODOLOGY_VOCAB.search(sentence):
        return False
    if not _PROCEEDING_NOUN.search(sentence):
        return False
    for m in _ASSERTED_AGAINST_ISSUER.finditer(sentence):
        if m.group(0).startswith("against"):
            # A bare against-issuer reference carries no tense of its
            # own: accept it only when its whole clause is indicative —
            # no modal, no forward-looking marker, a calendar "May"
            # excepted.
            if _clause_states_possibility(
                sentence,
                _clause_head(sentence, m.start()),
                _clause_end(sentence, m.end()),
            ):
                continue
        return True
    return False

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
RANGE_PATTERN_REVISION = "v3"
RANGE_ARM_PRIORITY = ("disclosed", "not_estimable", "not_material")
# The arm bytes stay frozen (v2): every mapping digest pins
# RANGE_DISCLOSED_PATTERN, and the golden envelope pin carries that digest, so
# the v3 refusal below lives in the chooser, never in the pattern.
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
        # F3-2 (third + fourth review, F4-1/F4-2): "determine" is object-
        # bound — the bare outcome form ("not possible to determine the
        # outcome", a "… whether …" clause with no object noun inside the
        # window) is excluded, while a sentence whose window does reach an
        # object noun within three lowercase words still values
        # not_estimable ("determine whether a loss will occur" bridges to
        # "loss"). The object ends on a word boundary, so the span for
        # "…determine the losses." ends at "losses", never cut mid-word at
        # "loss".
        # F3-3 (fifth review, F5-1/F5-2/F5-5; F5-3 ruled in): the object
        # alternation admits each noun's plural form — amounts, ranges,
        # losses, exposures, liabilities all value not_estimable, with the
        # span ending at the plural itself. The boundary still excludes
        # everything outside the vocabulary: a misspelling such as
        # "lossess" matches no alternative and stays typed absent, and the
        # bare "outcome" noun remains outside the alternation.
        r"|(?:is |was )?not possible to (?:reasonably )?estimate"
        r"|(?:is |was )?not possible to (?:reasonably )?determine "
        r"(?:the |an? )?(?:[a-z]+ ){0,3}?"
        r"(?:amounts?|ranges?|loss(?:es)?|exposures?|liabilit(?:y|ies))\b"
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

# R4 accrual dimension rule (dev corpus litigation_v1): the accrual is often
# reported ONLY under axes that identify the contingency matter. The rule
# admits exactly the contingency-identity axes — the us-gaap nature axis,
# srt:LitigationCaseAxis (a filer that reports the whole accrual only under
# a litigation-case-axis member, e.g. a single indemnity matter) and
# srt:ProductOrServiceAxis (the same filer tags a second matter's accrual
# under the product-or-service axis) — all standard taxonomy (us-gaap/srt;
# no issuer extension axis is ever named here; axes bind by local name the
# way the framework's own dimension rules bind a Clark-form ledger qname,
# across srt yearly namespaces). It fires only when no undimensioned accrual
# resolved, every candidate fact's axes lie inside this set, and every
# candidate agrees on one value. An accrual under any other axis — for
# example a balance-sheet-location axis or a litigation-status axis, which
# also carry per-member values that must not be pooled — or disagreeing
# member values keep the typed absence.
_ACCRUAL_IDENTITY_AXES = (
    "us-gaap:LossContingenciesByNatureOfContingencyAxis",
    "srt:LitigationCaseAxis",
    "srt:ProductOrServiceAxis",
)
_ACCRUAL_DIMENSIONED_MAPPING = FactMapping(
    _ACCRUAL, dimensions_allowed=_ACCRUAL_IDENTITY_AXES
)

# R5 range-axis rule: issuers that do not tag the frozen minimum/maximum
# concepts tag the same endpoints as us-gaap:LossContingencyEstimateOf
# PossibleLoss dimensioned by srt:RangeAxis with the srt MinimumMember /
# MaximumMember members (standard taxonomy only; matter-identifying
# co-occurring axes are never consulted, so an issuer-extension member on a
# standard axis does not enter the rule). Both endpoints must carry one
# agreeing value each; the row reports the instant the fact carries.
_RANGE_CONCEPT = "us-gaap:LossContingencyEstimateOfPossibleLoss"
_RANGE_AXIS = "srt:RangeAxis"
_RANGE_AXIS_MIN_MEMBER = "srt:MinimumMember"
_RANGE_AXIS_MAX_MEMBER = "srt:MaximumMember"
_RANGE_AXIS_MAPPING = FactMapping((_RANGE_CONCEPT,), dimensions_allowed=(_RANGE_AXIS,))

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
# R3 note-fallback mappings: the same frozen patterns searched inside the
# contingencies note when the item section cross-references it and carries
# no matching sentence of its own. The digest pins the bytes that performed
# the match, so the fallback row carries its own rule id and digest.
_ALLEGATION_NOTE_MAPPING = TextSpanMapping(
    section=NOTE_CC, pattern=ALLEGATION_PATTERN, kind="text"
)
_PROCEDURAL_NOTE_MAPPING = TextSpanMapping(
    section=NOTE_CC, pattern=PROCEDURAL_STATUS_PATTERN, kind="text"
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


def _locate_note_last(nt: Any, spec: "narrative.SectionSpec") -> tuple[int, int] | None:
    """Locate a v2 note section: the LAST heading match governs.

    Every in-text cross-reference to a note ("See Note 19. The …") precedes
    the note body it cites, so the last match is the body; the heading
    grammar itself already refuses cross-reference and TOC shapes.
    """
    matches = list(re.finditer(spec.heading, nt.text, re.IGNORECASE))
    if not matches:
        return None
    chosen = matches[-1]
    end = len(nt.text)
    for end_heading in spec.end_headings:
        boundary = re.compile(end_heading, re.IGNORECASE).search(
            nt.text, chosen.end()
        )
        if boundary is not None:
            end = min(end, boundary.start())
    return (chosen.start(), end)


def _contingencies_span_v2(
    nt: Any, note_span: tuple[int, int]
) -> tuple[int, int] | None:
    """The v2 contingencies subsection: first title-shaped "Contingencies".

    A v2 note title ("Contingencies and Environmental Liabilities",
    "Legal proceedings") is itself the contingencies disclosure, so the
    subsection starts at the first capital-C "Contingencies" that heads a
    run of text ("Contingencies The Company…", "Contingencies
    Warranties…") and is the whole note when no such occurrence exists
    (a "19. Legal proceedings" note). Mid-sentence occurrences
    ("Contingencies, and related guidance") never head a run of text and
    are skipped by the same shape test.
    """
    segment = nt.text[note_span[0] : note_span[1]]
    match = _CONTINGENCIES_TITLE.search(segment)
    if match is None:
        return note_span
    return (note_span[0] + match.start(), note_span[1])


def _item_section_or_none(
    nt: Any, span: tuple[int, int] | None, heading: str
) -> tuple[int, int] | None:
    """The located item section, or ``None`` when only a TOC line matched.

    A governing section never reduces to a page-number remnant ("Item 3.
    Legal Proceedings 114" with the end heading cutting at the next TOC
    entry) and never opens on a page number followed by the next item
    heading ("Legal Proceedings 22 Item 4. …" is the table of contents);
    the stock locator keeps such a line when no body match exists, so both
    artifact checks run on the located span itself. The heading match is
    stripped first — the section's own heading is not an artifact.
    """
    if span is None:
        return None
    lo, hi = span
    heading_match = re.compile(heading, re.IGNORECASE).match(nt.text, lo, hi)
    body_start = heading_match.end() if heading_match is not None else lo
    body = nt.text[body_start:hi]
    if _ITEM_TOC_REMNANT.match(body):
        return None
    window = body[:200]
    if _ITEM_TOC_ARTIFACT.search(window):
        return None
    return span


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

    def __init__(self, nt: Any, *, quarterly: bool = False) -> None:
        self.note_cc: tuple[int, int] | None = None
        self.note_v2 = False
        self.conting: tuple[int, int] | None = None
        self.item3: tuple[int, int] | None = None
        # The item section the span fields search: Part II Item 3 on annual
        # forms, Part II Item 1 on quarterly forms (K3K4). Both carry the
        # TOC-artifact guard.
        self.item_section: tuple[int, int] | None = None
        if nt is None:
            return
        self.note_cc = narrative.locate_section(nt, NOTE_CC)
        if self.note_cc is not None:
            self.conting = _contingencies_span(nt, self.note_cc)
        else:
            # R1: the v2 fallbacks are consulted only when v1 located
            # nothing, so every v1 result is unchanged by construction.
            for spec in NOTE_CC_V2_SPECS:
                span = _locate_note_last(nt, spec)
                if span is not None:
                    self.note_cc = span
                    self.note_v2 = True
                    self.conting = _contingencies_span_v2(nt, span)
                    break
        self.item3 = _item_section_or_none(
            nt, narrative.locate_section(nt, ITEM3), ITEM3.heading
        )
        item1 = _item_section_or_none(
            nt, narrative.locate_section(nt, ITEM1_QUARTERLY), ITEM1_QUARTERLY.heading
        )
        self.item_section = item1 if quarterly else self.item3


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


# R1b (range-arm v3): the disclosed arm's phrase also appears inside the
# standard ASC 450 refusal idiom — "unable to reasonably estimate a possible
# loss or range of possible loss" — which fixed arm priority then typed as
# disclosed_range from the filer's own refusal sentence. A disclosed match
# governs only when the phrase's own sentence carries its amount: a dollar
# sign within 80 characters after the phrase, never crossing a sentence
# boundary. Every genuine disclosure has one ("range of reasonably possible
# loss of $10 million to $20 million"); the bare negated idiom falls through
# to the not_estimable arm that already matches its verb.
_DISCLOSED_AMOUNT_FOLLOWS = re.compile(r"[^.]{0,80}\$")


def _governing_range_arm(
    text: str, lo: int, hi: int
) -> tuple[str, re.Match[str] | None]:
    """The governing range arm in ``text[lo:hi]``: fixed priority, not position.

    F2: arms evaluate in RANGE_ARM_PRIORITY order (disclosed >
    not_estimable > not_material) over the whole Contingencies span, so a
    ``no material`` phrase earlier in the span never ousts a governing
    estimate clause. R1b (v3): a disclosed-arm match whose sentence carries
    no amount is the refusal idiom's own phrase and never governs; the
    search continues to the next disclosed match before falling through to
    the lower arms. Returns ``("", None)`` when no arm matches.
    """
    for arm in RANGE_ARM_PRIORITY:
        for match in _RANGE_ARM_SEARCH[arm].finditer(text, lo, hi):
            if arm == "disclosed" and not _DISCLOSED_AMOUNT_FOLLOWS.match(
                text, match.end()
            ):
                continue
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
    note_mapping: TextSpanMapping,
    note_guard: "Callable[[str], bool] | None" = None,
) -> _RowRewriter:
    rewriter = _RowRewriter(row, nt, accession)
    if row.get("quality_state") == "not_applicable":
        return rewriter  # the form gate owns this row; no search ran
    if nt is None:
        rewriter.absent(mapping, "narrative document not retained")
        return rewriter
    if sections.item_section is None:
        rewriter.absent(mapping, "governing_section_not_supplied")
        return rewriter
    lo, hi = sections.item_section
    match = re.compile(pattern).search(nt.text, lo, hi)
    if match is not None:
        span = narrative.sentence_span(nt.text, match.start(), match.end(), (lo, hi))
        text_value = nt.text[span[0] : span[1]].strip()[: mapping.max_chars]
        rewriter.valued(mapping, text_value, span)
        return rewriter
    # R3: a supplied item section without a matching sentence is the
    # issuer's incorporation-by-reference — the contingencies note it names
    # is the governing disclosure for the span fields. A guard, when one is
    # declared, skips a matched sentence of the wrong kind (the
    # keyword-collision methodology, process, possibility and allocation
    # boilerplate the frozen patterns admit).
    if sections.conting is not None:
        clo, chi = sections.conting
        for note_match in re.compile(pattern).finditer(nt.text, clo, chi):
            span = narrative.sentence_span(
                nt.text, note_match.start(), note_match.end(), (clo, chi)
            )
            sentence = nt.text[span[0] : span[1]]
            if note_guard is not None and not note_guard(sentence):
                continue
            text_value = sentence.strip()[: note_mapping.max_chars]
            rewriter.valued(note_mapping, text_value, span)
            row["mapping_rule_id"] = f"pk08.{row['field_id']}.text_span_note/v1"
            return rewriter
    rewriter.absent(mapping, "narrative_span_not_located")
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


# --- R4/R5 dimension rules over the raw ledger -----------------------------------


def _value_dimensioned_fact_row(
    row: dict[str, Any],
    occurrences: list[Any],
    representative: Any,
    *,
    mapping: FactMapping,
    rule_id: str,
) -> None:
    """Rewrite one ``missing`` row as valued from dimensioned facts.

    Mirrors the framework's own valued ``xbrl_fact`` row shape (concept,
    occurrence ids, the representative's dimensions, the instant actually
    used, the catalogue unit); the rule id and digest name the dimension
    rule that performed the resolution.
    """
    row["quality_state"] = "valued"
    row["non_value_state"] = None
    row["coverage_state"] = "source_trace_complete"
    row["reason"] = None
    row["evidence_kind"] = "xbrl_fact"
    row["required_evidence_kind"] = "xbrl_fact"
    row["value"] = decimal_text(Decimal(str(representative.parsed_value)))
    row["text_value"] = None
    row["source_span"] = None
    row["table_cell"] = None
    row["concept"] = representative.concept_qname
    row["taxonomy"] = representative.concept_qname.split(":", 1)[0]
    row["source_occurrence_ids"] = sorted(
        {item.occurrence_id for item in occurrences}
    )
    row["dimensions"] = [
        {"axis": axis, "member": str(member)}
        for axis, member in sorted(representative.context.explicit_dimensions)
    ]
    # The row reports the period the fact actually carries (the framework's
    # own cover-instant precedent): the dev corpus reports both the accrual
    # and the range endpoints as instants at the balance-sheet date.
    row["period"] = {
        "kind": "instant",
        "end": representative.context.instant.isoformat(),
    }
    row["unit"] = "USD"
    row["mapping_rule_id"] = rule_id
    row["mapping_rule_digest"] = _mapping_digest(mapping)


def _usd_occurrence(occurrence: Any) -> bool:
    """The fact satisfies the catalogue's USD unit law (R-F1)."""
    return _unit_measure(occurrence.unit) in (_unit_equivalents("USD") or frozenset())


def _apply_accrual_dimension_rule(
    rows: Mapping[str, dict[str, Any]], ledger: Any, por: date | None
) -> None:
    """R4: the accrual reported only under contingency-identity axes.

    Fires only on a ``missing`` row (a conflicting undimensioned pool stays
    the framework's own not_evaluable) with no undimensioned candidate, and
    only when every dimensioned candidate's axes lie inside
    ``_ACCRUAL_IDENTITY_AXES`` and all candidates agree on one value.
    """
    row = rows["loss_contingency_accrual"]
    if por is None or row.get("quality_state") != "missing":
        return
    candidates: list[Any] = []
    for occurrence in ledger.events:
        if occurrence.concept_qname not in _ACCRUAL or occurrence.is_nil:
            continue
        if occurrence.context.instant != por or not _usd_occurrence(occurrence):
            continue
        # ``Context`` dimensions are canonical (axis, member) pair tuples
        # (raw_ledger), never a mapping: iterating the container yields the
        # pair tuples, so the axis qname is the pair's first element.
        axes = {axis for axis, _member in occurrence.context.explicit_dimensions} | {
            axis for axis, _member in occurrence.context.typed_dimensions
        }
        if not axes:
            continue  # undimensioned facts are the framework's own path
        if all(
            any(
                _dimension_qname_matches(axis, declared)
                for declared in _ACCRUAL_IDENTITY_AXES
            )
            for axis in axes
        ):
            candidates.append(occurrence)
    if not candidates:
        return
    if len({str(item.parsed_value) for item in candidates}) > 1:
        return  # disagreeing member values never pool into one row
    representative = min(candidates, key=lambda item: item.occurrence_id)
    _value_dimensioned_fact_row(
        row,
        candidates,
        representative,
        mapping=_ACCRUAL_DIMENSIONED_MAPPING,
        rule_id="PK08.loss_contingency_accrual.fact_dimensioned/v1",
    )


def _apply_range_axis_rule(
    rows: Mapping[str, dict[str, Any]], ledger: Any, por: date | None
) -> None:
    """R5: range endpoints from ``srt:RangeAxis``-dimensioned estimates.

    ``us-gaap:LossContingencyEstimateOfPossibleLoss`` facts at the primary
    instant whose ``srt:RangeAxis`` member is the srt minimum/maximum member
    value the low/high row; other co-occurring axes identify the matter and
    are never consulted. All candidates for one endpoint must agree on one
    value; the row reports the instant the fact carries. Valued only from
    XBRL facts, never from prose (R-K4').
    """
    if por is None:
        return
    for field_id, wanted_member in (
        ("loss_contingency_range_low", _RANGE_AXIS_MIN_MEMBER),
        ("loss_contingency_range_high", _RANGE_AXIS_MAX_MEMBER),
    ):
        row = rows[field_id]
        if row.get("quality_state") != "missing":
            continue
        candidates: list[Any] = []
        for occurrence in ledger.events:
            if occurrence.concept_qname != _RANGE_CONCEPT or occurrence.is_nil:
                continue
            if occurrence.context.instant != por or not _usd_occurrence(occurrence):
                continue
            carries_member = any(
                _dimension_qname_matches(axis, _RANGE_AXIS)
                and _dimension_qname_matches(member, wanted_member)
                for axis, member in occurrence.context.explicit_dimensions
            )
            if carries_member:
                candidates.append(occurrence)
        if not candidates:
            continue
        if len({str(item.parsed_value) for item in candidates}) > 1:
            continue  # disagreeing endpoints never value the row
        representative = min(candidates, key=lambda item: item.occurrence_id)
        _value_dimensioned_fact_row(
            row,
            candidates,
            representative,
            mapping=_RANGE_AXIS_MAPPING,
            rule_id=f"PK08.{field_id}.fact_range_axis/v1",
        )


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
        from ..ixbrl_raw_ledger import (  # call-time: a test double is honoured
            parse_and_convert_golden_packages
        )

        ledger, _filing_metadata, _report = parse_and_convert_golden_packages(
            pack_input.packages
        )
        primary, _matched = _select_primary(pack_input.packages, SPEC.forms)
        accession = str(primary.manifest.get("accession") or "")
        rows = {row["field_id"]: row for row in result["fields"]}
        nt = _narrative_or_none(primary)
        sections = _Sections(
            nt, quarterly=str(primary.manifest.get("form") or "") in _QUARTERLY_FORMS
        )
        # A manifest without a parseable period_of_report simply leaves the
        # dimension rules inert; the narrative rules never needed it.
        try:
            por = date.fromisoformat(
                str(primary.manifest.get("period_of_report") or "")[:10]
            )
        except ValueError:
            por = None
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
            note_mapping=_ALLEGATION_NOTE_MAPPING,
            note_guard=_allegation_note_sentence,
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
            note_mapping=_PROCEDURAL_NOTE_MAPPING,
            note_guard=_procedural_note_sentence,
        )
        if rewriter.note is not None:
            notes.append(("procedural_status_span", rewriter.note))

        # R4/R5: the dimension rules run before the checks and the C2
        # retype, so the arithmetic sees the XBRL-valued rows and the
        # prose-only ruling touches only the rows still without a value.
        _apply_accrual_dimension_rule(rows, ledger, por)
        _apply_range_axis_rule(rows, ledger, por)

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
