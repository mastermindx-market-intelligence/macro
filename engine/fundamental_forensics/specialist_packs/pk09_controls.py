"""PK09 producer: controls, auditor and going concern.

Every field here is a frozen B.3 declaration read as ``text_span`` evidence
through :mod:`narrative` — no numeric fact, table cell or formula enters this
pack. Enum and boolean literals ride in ``text_value`` (the envelope schema's
``value`` is a decimal-or-null slot); checks compare those literals. The six
auditor/going-concern fields resolve on annual forms only; the controls family
switches from the Item 9A section to the Item 4 section on quarterly forms.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

from . import narrative
from .base import (
    CrossStatement,
    NarrativeHooks,
    NarrativeRuntime,
    PackProducer,
    PackSpec,
    Presence,
    TextSpanMapping,
)

SPEC = PackSpec(
    pack_id="PK09",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="pack.pk09.applicability/v1",
    applicable_classes=None,
)

# B.2 governing sections.
ITEM9A = narrative.SectionSpec(
    r"Item\s+9A\.?\s*Controls and Procedures",
    (r"Item\s+9B\.", r"Item\s+9C\.", r"Part\s+III"),
)
ITEM4_CONTROLS = narrative.SectionSpec(
    r"Item\s+4\.?\s*Controls and Procedures",
    (r"Part\s+II", r"Item\s+1\."),
)
AUDIT = narrative.SectionSpec(
    r"Report of Independent Registered Public Accounting Firm",
    (r"Item\s+9\.", r"Item\s+9A\."),
)
ICFR_REPORT = narrative.SectionSpec(
    r"Opinion on Internal Control Over Financial Reporting",
    (r"Item\s+9\.",),
)

# B.3 patterns (frozen). The critical-audit-matters guard is the one frozen
# departure in this producer: the seat spec's ``(?!.{0,40}communicated)`` was
# authored against uncollapsed raw byte distances (196 bytes on this fixture's
# heading); under the frozen A.1 whitespace collapse the same "communicated"
# sits 21 characters after the heading, so a 40-character window rejects the
# only capitalized occurrence and B.7's valued expectation is unreachable.
# The window is narrowed to 15 so the heading matches while an immediately
# following "communicated" is still rejected.
# B.3 pattern revision v2 (review F1/F2, 2026-10-20): every arm is anchored
# to its management-conclusion phrase, so a remediated-acquisition "not
# effective" earlier in the section can no longer win by leftmost hit; the
# material-weakness arm is tied to a nearby unnegated management conclusion.
# B.3 pattern revision v3 (review F1-a, 2026-10-20): the material-weakness
# arm resolves inside ONE "."-bounded sentence: it fires only when the window
# from the anchor verb to the noun carries no negation token (the v2 60-char
# sub-window left a dead zone inside the 80-char arm window), when no
# negating or remediating predicate follows the noun within 60 characters,
# and when no negator sits immediately before the anchor verb. A stated
# effective/ineffective conclusion anywhere in the same sentence governs
# over the mention; that precedence is resolved by _icfr_conclusion_value.
ICFR_CONCLUSION = (
    r"internal control over financial reporting (?:was|is|were) "
    r"(?P<effective>effective)"
    r"|internal control over financial reporting (?:was|is|were) "
    r"(?P<ineffective>not effective|ineffective)"
    r"|(?P<material_weakness>(?<!not )(?<!not yet )(?<!never )(?<!no )"
    r"(?<!did not )(?<!have not )(?<!has not )(?<!without )"
    r"(?:concluded|conclude|determined|identified)"
    r"(?![^.]{0,80}?\b(?:no|not|never|without|absence of|free of)\b"
    r"[^.]{0,80}?material weakness)"
    r"[^.]{0,80}?material weakness"
    r"(?![^.]{0,60}?\b(?:does not exist|did not exist|has been remediated|"
    r"was remediated|were remediated|were not|was not|is not)\b))"
)
# B.3 pattern revision v2 (review F1/F2, 2026-10-20): the ineffective arm
# carries the same disclosure-controls anchor as the effective arm.
DISCLOSURE_CONTROLS = (
    r"disclosure controls and procedures[^.]{0,400}?(?:were|are) "
    r"(?P<effective>effective)"
    r"|disclosure controls and procedures[^.]{0,400}?(?:were|are) "
    r"(?P<ineffective>not effective|ineffective)"
)
# B.3 pattern revision v2 (review F1/F2, 2026-10-20): the boolean fires only
# on an affirmative identification or existence; negated mentions ("no
# material weakness", "did not identify any material weakness", "without a
# material weakness") and bare remediation prose no longer flip it to true.
# B.3 pattern revision v3 (review F1-b, 2026-10-20): the lookbehind guard in
# front of the identifying verb also refuses "never", "no", "did not",
# "have not", "has not" and "without" immediately before it (v2 guarded
# only "not"/"not yet", so "We never identified a material weakness"
# resolved true); _material_weakness_value extends the guard to a negator
# anywhere earlier in the same "."-bounded sentence.
# B.3 pattern revision v4 (review F1-2, 2026-10-20): the sentence-bounded
# look-back above over-negated — any earlier negator in the sentence, even
# one in a relative clause that had already closed, flipped an affirmative
# identification to a confident false. The look-back is now clause-bounded
# (see _material_weakness_value), and the existence arms accept the
# affirmative existential forms "there was/were/is/are (a|an|one|one or
# more) material weakness(es)" and "material weakness(es) exists/existed";
# their forward guard reads only the predicate of the SAME clause, so a
# relative "which has not been remediated" no longer refuses the mention.
# B.3 pattern revision v5 (review F1-A/F1-B/F1-C/F2-A/F2-B, 2026-10-20):
# the negation look-back below is case-insensitive and the bare-existence
# arm carries the same "(?<![Nn]o )" lookbehind as arm 2 (a sentence-
# initial "No material weakness existed" is a negated existence), the
# existential copula "there was/were/is/are" is an anchor verb of that
# look-back ("We do not believe there was a material weakness" is
# false), the bare existence arm anchors on the whole word
# exist/exists/existed and refuses a following "remediated" (a
# prior-year remediated mention is not a presence), the existence
# guard's forward scan stops at a coordinating "and"/"but" ("There was
# a material weakness and it has not been remediated" is true), and the
# clause-boundary set below gains the subordinators because/since/due
# to/as a result of/resulting from plus "and"/"but" followed (within 3
# tokens) by a subject restart, so the negation of an earlier predicate
# ("was not effective ... because a material weakness ... existed") no
# longer reaches the existence verb.
# B.3 pattern revision v6 (review F4-1..F4-4, 2026-10-31): remediation
# timing. A weakness is PRESENT as of the balance date unless the
# sentence says it was remediated on or before that date. Arm 2's
# refusal therefore splits in two: a negator ("no|not|without") still
# refuses unless it belongs to a negated remediation ("has not been
# remediated"), and "remediated" refuses only when the scan reaches it
# without passing a "subsequently|later|after|not|never|no" marker or a
# following "after" — so "was subsequently remediated" (after the as-of
# date) and "has not been remediated" carry an affirmative match again,
# while a bare "was remediated" stays refused. Arms 3/4 keep stopping at
# "and"/"but"; the coordinated clause after the coordinator is read by
# _material_weakness_value for a remediation predicate with its date
# semantics.
_MW_EXISTENCE_GUARD = (
    r"(?!(?:(?![,;]|\bwhich\b|\bthat\b|\band\b|\bbut\b)[^.]){0,60}?"
    r"\b(?:does not exist|did not exist|has been remediated|"
    r"was remediated|were remediated|were not|was not|is not|"
    r"no|not|never|without)\b)"
)
MATERIAL_WEAKNESS_IDENTIFIED = (
    r"(?<!not )(?<!not yet )(?<!never )(?<!no )(?<!did not )"
    r"(?<!have not )(?<!has not )(?<!without )"
    r"identif(?:y|ied)(?![^.]{0,40}?(?:no|not|without)\b)"
    r"[^.]{0,40}?material weakness"
    r"|(?<![Nn]o )material weakness(?:es)?"
    r"(?![^.]{0,80}?(?:no|not|without)\b(?![^.]{0,40}?\bremediated\b)"
    r"|(?:(?!\b(?:subsequently|later|after|not|never|no)\b)[^.]){0,80}?"
    r"remediated\b(?![^.]{0,30}?\bafter\b))"
    r"[^.]{0,80}?\bexist(?:s|ed)?\b"
    r"|[Tt]here (?:was|were|is|are)(?: a| an| one| one or more)?"
    r" material weakness(?:es)?" + _MW_EXISTENCE_GUARD +
    r"|(?<![Nn]o )material weakness(?:es)? (?:exists?|existed)"
    + _MW_EXISTENCE_GUARD
)
ICFR_CHANGE = (
    r"(?:no changes|changes) in (?:the Company.s |our )?"
    r"internal control over financial reporting"
)
AUDITOR_FIRM = r"/s/\s*(?P<firm>[A-Z][A-Za-z&.,\s]{2,80}?LLP)"
AUDITOR_OPINION_FS = (
    r"(?P<unqualified>present fairly, in all material respects)"
    r"|(?P<adverse>do not present fairly)"
    r"|(?P<disclaimer>do not express an opinion)"
)
AUDITOR_OPINION_ICFR = (
    r"(?P<effective>maintained, in all material respects, effective internal "
    r"control)|(?P<adverse>has not maintained effective internal control)"
)
CRITICAL_AUDIT_MATTERS = r"Critical Audit Matters?\b(?!.{0,15}communicated)"
GOING_CONCERN_DOUBT = (
    r"(?P<present>substantial doubt about (?:the Company.s|our|its) ability "
    r"to continue as a going concern)"
)
GOING_CONCERN_PLAN = r"management.s plans?"
REMEDIATION = "remediat"

_CAM_WINDOW_CHARS = 512
_QUARTERLY_FORMS = frozenset({"10-Q", "10-Q/A"})
_CONTROLS_FAMILY = (
    "icfr_management_conclusion",
    "disclosure_controls_effective",
    "material_weakness_present",
    "icfr_change_in_period",
    "remediation_span",
)
_ANNUAL_ONLY = (
    "auditor_firm",
    "auditor_opinion_fs",
    "auditor_opinion_icfr",
    "critical_audit_matters",
    "going_concern_substantial_doubt",
    "going_concern_management_plan",
)

_FIELD_MAPPINGS = {
    "icfr_management_conclusion": TextSpanMapping(
        section=ITEM9A,
        pattern=ICFR_CONCLUSION,
        kind="enum",
        enum_map={
            "effective": "effective",
            "ineffective": "ineffective",
            "material_weakness": "material_weakness",
        },
    ),
    "disclosure_controls_effective": TextSpanMapping(
        section=ITEM9A,
        pattern=DISCLOSURE_CONTROLS,
        kind="enum",
        enum_map={"effective": "effective", "ineffective": "ineffective"},
    ),
    "material_weakness_present": TextSpanMapping(
        # ITEM9A ONLY: the auditor's report carries the phrase as boilerplate.
        # B.3 pattern revision v3 (review F1-b, 2026-10-20).
        section=ITEM9A,
        pattern=MATERIAL_WEAKNESS_IDENTIFIED,
        kind="boolean",
        absent_value=False,
    ),
    "icfr_change_in_period": TextSpanMapping(
        section=ITEM9A, pattern=ICFR_CHANGE, kind="text"
    ),
    "auditor_firm": TextSpanMapping(
        section=AUDIT, pattern=AUDITOR_FIRM, kind="text"
    ),
    "auditor_opinion_fs": TextSpanMapping(
        section=AUDIT,
        pattern=AUDITOR_OPINION_FS,
        kind="enum",
        enum_map={
            "unqualified": "unqualified",
            "adverse": "adverse",
            "disclaimer": "disclaimer",
        },
    ),
    "auditor_opinion_icfr": TextSpanMapping(
        section=ICFR_REPORT,
        pattern=AUDITOR_OPINION_ICFR,
        kind="enum",
        enum_map={"effective": "effective", "adverse": "adverse"},
    ),
    "critical_audit_matters": TextSpanMapping(
        section=AUDIT, pattern=CRITICAL_AUDIT_MATTERS, kind="text"
    ),
    "going_concern_substantial_doubt": TextSpanMapping(
        section=None,
        pattern=GOING_CONCERN_DOUBT,
        kind="enum",
        enum_map={"present": "disclosed"},
        absent_value="not_disclosed",
    ),
    "going_concern_management_plan": TextSpanMapping(
        section=None, pattern=GOING_CONCERN_PLAN, kind="text"
    ),
    "remediation_span": TextSpanMapping(
        section=ITEM9A, pattern=REMEDIATION, kind="text"
    ),
}

_CHECKS = (
    CrossStatement(
        check_id="management_vs_auditor_icfr",
        left="icfr_management_conclusion",
        right="auditor_opinion_icfr",
        relation="equal",
    ),
    Presence(
        check_id="going_concern_vs_opinion",
        field_id="going_concern_substantial_doubt",
    ),
    Presence(check_id="cam_present_on_10k", field_id="critical_audit_matters"),
)


# --- text_value overrides (B.3 fields whose value is not the sentence) ------


def _auditor_firm_value(
    nt: Any, section_span: tuple[int, int], match: Any
) -> tuple[str, tuple[int, int]]:
    firm = match.group("firm")
    return firm, (match.start("firm"), match.end("firm"))


def _cam_value(
    nt: Any, section_span: tuple[int, int], match: Any
) -> tuple[str, tuple[int, int]]:
    window = nt.text[match.end() : match.end() + _CAM_WINDOW_CHARS].strip()
    cut = window.rfind(". ")
    if cut >= 0:
        window = window[: cut + 1]
    return window, (match.end(), match.end() + len(window))


# B.3 v3 (review F1-a): the stated-conclusion clause shared by the mapping
# pattern's first two arms; the resolver below searches it inside one
# "."-bounded sentence so either side of a material-weakness mention counts.
_ICFR_STATED_CONCLUSION = re.compile(
    r"internal control over financial reporting (?:was|is|were) "
    r"(?P<effective>effective)"
    r"|internal control over financial reporting (?:was|is|were) "
    r"(?P<ineffective>not effective|ineffective)"
)
# B.3 v3 (review F1-b): the identifying verb whose lead the presence
# resolver scans for a negation token.
# B.3 v4 (review F1-1): the verb set gains "identifies", and the negation
# scan below starts at the clause boundary, not the sentence boundary.
# B.3 v5 (review F1-B): the existential copula "there was/were/is/are"
# is an anchor too, so the clause look-back runs for the existential
# arm's matches as well.
_MW_IDENTIFYING_VERB = re.compile(
    r"identif(?:y|ied|ies)|exists?|existed|[Tt]here (?:was|were|is|are)"
)
# B.3 v5 (reviews F1-A/F1-B): the negator match is case-insensitive (a
# sentence-initial "No" negates), and "do not"/"does not" are listed
# alongside the bare "not" they already matched through.
_MW_NEGATION_BEFORE = re.compile(
    r"\b(?:never|no|not|without|absence of|free of|did not|do not|"
    r"does not|have not|has not)\b",
    re.IGNORECASE,
)
# B.3 v4 (review F1-1): a clause boundary inside a "."-bounded sentence —
# a semicolon, a colon, an em/en dash, or a comma followed (within 3
# tokens) by a subject restart.
# B.3 v5 (review F2-A/F2-B): the subordinators "because", "since",
# "due to", "as a result of" and "resulting from" are boundaries in
# their own right, and "and"/"but" followed (within 3 tokens) by the
# same subject restart is one too — a negation attached to the
# predicate of an earlier clause ("was not effective") never reaches
# the verb of the clause they introduce.
_MW_CLAUSE_BOUNDARY = re.compile(
    r"[;:—–]|,\s*(?:\S+\s+){0,2}?(?:management|we|the company|"
    r"our management|the audit committee|it)\b"
    r"|\b(?:because|since|due to|as a result of|resulting from)\b"
    r"|\b(?:and|but)\s+(?:\S+\s+){0,2}?(?:management|we|the company|"
    r"our management|the audit committee|it)\b"
)
# B.3 v6 (review F4-1..F4-4): the coordinated clause after "and"/"but" is
# read forward for a remediation predicate. A negated remediation ("has
# not been remediated") is not a remediation; a marker
# "subsequently|later|after" places it after the balance date; a stated
# "as of <Month D, YYYY>" remediation date is compared against the
# sentence's own as-of date when both are present.
_MW_COORDINATOR = re.compile(r"\b(?:and|but)\b", re.IGNORECASE)
_MW_REMEDIATION_PARTICIPLE = re.compile(r"\bremediated\b", re.IGNORECASE)
_MW_REMEDIATION_NEGATED = re.compile(r"\b(?:not|never|no)\b", re.IGNORECASE)
_MW_REMEDIATION_LATER = re.compile(
    r"\b(?:subsequently|later|after)\b", re.IGNORECASE
)
_MW_AS_OF_DATE = re.compile(
    r"\bas of\s+((?:january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
_MW_MONTH_ORDINALS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _mw_date_key(stated: str) -> tuple[int, int, int]:
    month, day, year = stated.replace(",", "").split()
    return (int(year), _MW_MONTH_ORDINALS[month.lower()], int(day))


def _mw_coordinated_remediation_absent(text: str, from_pos: int) -> bool:
    """B.3 v6: does the coordinated clause after ``from_pos`` read as an
    unnegated remediation completed on or before the balance date?

    The scan is bounded by the "."-bounded sentence holding the match, so
    a remediation narrated in a later sentence never reaches it. A
    remediation preceded by "not"/"never"/"no" ("has not been remediated")
    or placed after the balance date by a "subsequently"/"later"/"after"
    marker leaves the weakness present; a stated "as of <date>" on the
    remediation is compared against the sentence's own as-of date when
    both parse, and a remediation with no date and no marker is treated
    as remediated (absent).
    """
    sentence_lo, sentence_hi = _sentence_bounds(text, from_pos, from_pos)
    coordinator = _MW_COORDINATOR.search(text, from_pos, sentence_hi)
    if coordinator is None:
        return False
    tail_lo = coordinator.end()
    for hit in _MW_REMEDIATION_PARTICIPLE.finditer(text, tail_lo, sentence_hi):
        if _MW_REMEDIATION_NEGATED.search(
            text, max(sentence_lo, hit.start() - 30), hit.start()
        ):
            continue
        if _MW_REMEDIATION_LATER.search(
            text,
            max(sentence_lo, hit.start() - 40),
            min(sentence_hi, hit.end() + 30),
        ):
            continue
        remediated_as_of = _MW_AS_OF_DATE.search(text, hit.end(), sentence_hi)
        if remediated_as_of is not None:
            as_of = _MW_AS_OF_DATE.search(text, sentence_lo, tail_lo)
            if as_of is not None and _mw_date_key(as_of.group(1)) < _mw_date_key(
                remediated_as_of.group(1)
            ):
                continue
        return True
    return False


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Char range of the "."-bounded sentence containing [start, end)."""
    lo = text.rfind(".", 0, start) + 1
    dot = text.find(".", end)
    hi = len(text) if dot == -1 else dot
    return lo, hi


def _icfr_conclusion_value(
    nt: Any, section_span: tuple[int, int], match: Any
) -> tuple[str, tuple[int, int]]:
    """B.3 v3 sentence-bounded resolution (review F1-a).

    Rule: within the "."-bounded sentence that produced the mapping match,
    a stated conclusion clause — "internal control over financial reporting
    was/is/were effective / not effective / ineffective" — governs over a
    material-weakness mention on either side of it. One sentence-bounded
    search collects the stated-conclusion arms together with the mapping
    match (the material-weakness arm, already guarded by the pattern) and
    resolves effective/ineffective before material_weakness: only a
    sentence carrying no stated conclusion may hold the material_weakness
    literal.
    """
    text = nt.text
    lo, hi = _sentence_bounds(text, match.start(), match.end())
    stated = _ICFR_STATED_CONCLUSION.search(text, lo, hi)
    if stated is not None:
        literal = (
            "effective" if stated.group("effective") is not None else "ineffective"
        )
        return literal, (stated.start(), stated.end())
    return "material_weakness", (match.start(), match.end())


def _mw_clause_start(text: str, sentence_lo: int, verb_start: int) -> int:
    """Scan start for the negation look-back: the nearest clause boundary.

    B.3 v4 (review F1-1): candidates are the sentence start and every
    semicolon, colon, em/en dash, or comma followed (within 3 tokens) by a
    subject restart (``management|we|the company|our management|the audit
    committee|it``) that lies before the verb; the latest one wins. A
    negator before that boundary belongs to a clause that already closed
    and never reaches the verb.

    B.3 v5 (review F2-A/F2-B): the boundary set additionally counts the
    subordinators ``because|since|due to|as a result of|resulting from``
    in their own right and ``and``/``but`` followed (within 3 tokens) by
    the same subject restart, so a negation tied to the predicate of an
    earlier clause ("was not effective ... because a material weakness
    ... existed") no longer reaches the verb.
    """
    start = sentence_lo
    for boundary in _MW_CLAUSE_BOUNDARY.finditer(text, sentence_lo, verb_start):
        start = boundary.end()
    return start


def _material_weakness_value(
    nt: Any, section_span: tuple[int, int], match: Any
) -> tuple[str, tuple[int, int]]:
    """B.3 v5 clause-bounded resolution (reviews F1-b, F1-1/F1-2, then
    F1-A/F1-B/F1-C/F2-A/F2-B), plus the B.3 v6 remediation-timing read
    (review F4-1..F4-4).

    Clause-boundary rule: the boolean is true only for an affirmative
    identification or existence, and a negation token ("no", "not",
    "never", "without", "absence of", "free of", "did not", "do not",
    "does not", "have not", "has not" — matched case-insensitively, so a
    sentence-initial "No" negates) negates the identification only when
    it lies in the SAME CLAUSE as the anchor verb ("identify",
    "identified", "identifies", "exist", "exists", "existed", or the
    existential copula "there was/were/is/are"). The look-back starts at
    the nearest clause boundary before the verb — the sentence start, a
    ";", a ":", an em/en dash, a comma followed (within 3 tokens) by a
    subject restart (management, we, the company, our management, the
    audit committee, it), a subordinator (because, since, due to, as a
    result of, resulting from), or "and"/"but" followed (within 3
    tokens) by that subject restart — and never earlier; the mapping
    pattern's own 40-char verb-to-noun window stays as an additional cap
    on the identification. A negator inside a relative or participial
    clause that ends before the subject restart, one before a ";", and
    one tied to an earlier predicate before a subordinator ("was not
    effective ... because a material weakness ... existed") therefore do
    not reach the verb, while "We never identified a material weakness"
    and "Management did not identify any material weakness" stay false.

    Existential rule: an affirmative existence is a presence. The mapping
    pattern's existence arms accept "there was/were/is/are (a|an|one|one
    or more) material weakness(es)" and "material weakness(es)
    exists/existed"; their forward negation/remediation guard reads only
    the predicate of the SAME clause — the scan stops at a ",", a ";", a
    relative-pronoun "which"/"that", or a coordinating "and"/"but" — so
    "There was a material weakness, which has not been remediated" and
    "There was a material weakness and it has not been remediated"
    resolve true. The bare "material weakness ... exist/exists/existed"
    arm anchors on the whole word and refuses a "remediated" inside its
    80-char window unless that remediation is negated ("has not been
    remediated") or placed after the balance date by a marker, so a
    prior-year remediated mention ("a material weakness that existed in
    the prior year was remediated") carries no affirmative existential
    match, while "There was no material weakness", "a material weakness
    does not exist" and the arm's "No material weakness existed" opening
    stay false.

    Remediation-timing rule (v6): after the clause-bounded look-back, the
    coordinated clause following the match — text after the first
    "and"/"but" inside the same "."-bounded sentence — is read for an
    unnegated remediation predicate (see
    ``_mw_coordinated_remediation_absent``). A remediation stated for
    the balance date ("... but it has been remediated as of June 30,
    2026") or with no date at all is an absence; a remediation placed
    after the as-of date ("was subsequently remediated in the first
    quarter of fiscal 2027") and a negated one ("and has not been
    remediated") leave the weakness present.
    """
    text = nt.text
    verb = _MW_IDENTIFYING_VERB.search(text, match.start(), match.end())
    if verb is not None:
        lo, _ = _sentence_bounds(text, match.start(), match.end())
        clause_start = _mw_clause_start(text, lo, verb.start())
        if _MW_NEGATION_BEFORE.search(text, clause_start, verb.start()):
            return "false", (match.start(), match.end())
    if _mw_coordinated_remediation_absent(text, match.end()):
        return "false", (match.start(), match.end())
    return "true", (match.start(), match.end())


# --- conditional-field guards (B.3) ------------------------------------------


def _doubt_is_present(value: str) -> bool:
    return value == "disclosed"


def _weakness_is_present(value: str) -> bool:
    return value == "true"


# --- checks (B.4) ------------------------------------------------------------


def _check_row(
    catalogue_check: Mapping[str, Any], status: str, reason: str | None
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


def _not_applicable_gate(
    rows: Mapping[str, Mapping[str, Any]], field_ids: tuple[str, ...]
) -> str | None:
    for field_id in field_ids:
        row = rows.get(field_id)
        if row is not None and row.get("quality_state") == "not_applicable":
            reason = row.get("reason")
            return str(reason) if reason is not None else "form_outside_pack_forms"
    return None


def _management_vs_auditor_icfr(
    catalogue_check: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    ids = ("icfr_management_conclusion", "auditor_opinion_icfr")
    gate = _not_applicable_gate(rows, ids)
    if gate is not None:
        return _check_row(catalogue_check, "not_applicable", gate)
    management = rows["icfr_management_conclusion"]
    auditor = rows["auditor_opinion_icfr"]
    if (
        management.get("quality_state") != "valued"
        or auditor.get("quality_state") != "valued"
    ):
        return _check_row(catalogue_check, "not_evaluable", "missing_dependency")
    conclusion = str(management["text_value"])
    opinion = str(auditor["text_value"])
    holds = (conclusion == "effective" and opinion == "effective") or (
        conclusion in ("ineffective", "material_weakness")
        and opinion == "adverse"
    )
    return _check_row(catalogue_check, "pass" if holds else "fail", None)


def _going_concern_vs_opinion(
    catalogue_check: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, Any]],
    runtime: NarrativeRuntime,
) -> dict[str, Any]:
    ids = ("going_concern_substantial_doubt", "auditor_opinion_fs")
    gate = _not_applicable_gate(rows, ids)
    if gate is not None:
        return _check_row(catalogue_check, "not_applicable", gate)
    doubt = rows["going_concern_substantial_doubt"]
    opinion = rows["auditor_opinion_fs"]
    if (
        doubt.get("quality_state") != "valued"
        or opinion.get("quality_state") != "valued"
    ):
        return _check_row(catalogue_check, "not_evaluable", "missing_dependency")
    if str(doubt["text_value"]) != "disclosed":
        return _check_row(catalogue_check, "pass", None)
    nt = runtime.narrative_text()
    audit_span = narrative.locate_section(nt, AUDIT)
    audit_text = "" if audit_span is None else nt.text[audit_span[0] : audit_span[1]]
    corroborated = "substantial doubt" in audit_text
    return _check_row(catalogue_check, "pass" if corroborated else "fail", None)


def _cam_present_on_10k(
    catalogue_check: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    gate = _not_applicable_gate(rows, ("critical_audit_matters",))
    if gate is not None:
        return _check_row(catalogue_check, "not_applicable", gate)
    if rows["critical_audit_matters"].get("quality_state") == "valued":
        return _check_row(catalogue_check, "pass", None)
    return _check_row(catalogue_check, "not_evaluable", "filer_category_unbound")


def _evaluate_check(
    catalogue_check: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, Any]],
    runtime: NarrativeRuntime,
) -> dict[str, Any] | None:
    check_id = catalogue_check["check_id"]
    if check_id == "management_vs_auditor_icfr":
        return _management_vs_auditor_icfr(catalogue_check, rows)
    if check_id == "going_concern_vs_opinion":
        return _going_concern_vs_opinion(catalogue_check, rows, runtime)
    if check_id == "cam_present_on_10k":
        return _cam_present_on_10k(catalogue_check, rows)
    return None


# --- receipts and limitations (B.5, B.6) --------------------------------------


def _extra_receipts(
    runtime: NarrativeRuntime, rows: Mapping[str, Mapping[str, Any]]
) -> tuple[str, ...]:
    nt = runtime.narrative_text()
    audit_span = narrative.locate_section(nt, AUDIT)
    audit_text = "" if audit_span is None else nt.text[audit_span[0] : audit_span[1]]
    return (
        f"cam_count={audit_text.count('Description of the Matter')}",
        "narrative_text_sha256="
        + sha256(nt.text.encode("utf-8")).hexdigest(),
    )


def _section_description(field_id: str, runtime: NarrativeRuntime) -> str:
    section = _FIELD_MAPPINGS[field_id].section
    if field_id in _CONTROLS_FAMILY and runtime.primary_form in _QUARTERLY_FORMS:
        section = ITEM4_CONTROLS
    return "whole document" if section is None else section.heading


def _extra_limitations(
    runtime: NarrativeRuntime, rows: Mapping[str, Mapping[str, Any]]
) -> tuple[str, ...]:
    lines = [
        "pk09.text_span_rows: regex over the primary document narrative; no "
        "table or footnote resolution"
    ]
    for field_id in _FIELD_MAPPINGS:
        row = rows.get(field_id)
        if row is None or row.get("quality_state") == "valued":
            continue
        lines.append(
            f"pk09.{field_id}: non-valued ({row.get('reason')}); "
            f"section searched: {_section_description(field_id, runtime)}"
        )
    return tuple(lines)


HOOKS = NarrativeHooks(
    section_overrides={
        field_id: (_QUARTERLY_FORMS, ITEM4_CONTROLS)
        for field_id in _CONTROLS_FAMILY
    },
    field_form_exclusions={
        field_id: (_QUARTERLY_FORMS, "form_outside_pack_forms")
        for field_id in _ANNUAL_ONLY
    },
    conditional_fields={
        "going_concern_management_plan": (
            "going_concern_substantial_doubt",
            _doubt_is_present,
        ),
        "remediation_span": ("material_weakness_present", _weakness_is_present),
    },
    text_value_overrides={
        "auditor_firm": _auditor_firm_value,
        "critical_audit_matters": _cam_value,
        "icfr_management_conclusion": _icfr_conclusion_value,
        "material_weakness_present": _material_weakness_value,
    },
    check_evaluator=_evaluate_check,
    extra_receipts=_extra_receipts,
    extra_limitations=_extra_limitations,
)

PRODUCER = PackProducer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=_CHECKS,
    hooks=HOOKS,
)

__all__ = [
    "AUDIT",
    "HOOKS",
    "ICFR_REPORT",
    "ITEM4_CONTROLS",
    "ITEM9A",
    "PRODUCER",
    "SPEC",
]
