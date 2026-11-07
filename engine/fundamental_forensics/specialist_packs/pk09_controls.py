"""PK09 producer: controls, auditor and going concern.

Every field here is a frozen B.3 declaration read as ``text_span`` evidence
through :mod:`narrative` — no numeric fact, table cell or formula enters this
pack. Enum and boolean literals ride in ``text_value`` (the envelope schema's
``value`` is a decimal-or-null slot); checks compare those literals. The six
auditor/going-concern fields resolve on annual forms only; the controls family
switches from the Item 9A section to the Item 4 section on quarterly forms.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import calendar
import re
from typing import Any, Mapping, Sequence

from .. import specialist_pack_contract as contract
from ..financial_intelligence_packet import PACKET_MAX_LIMITATIONS
from . import narrative
from .base import (
    CrossStatement,
    NarrativeHooks,
    NarrativeRuntime,
    PackInput,
    PackProducer,
    PackSpec,
    Presence,
    SpecialistPackError,
    TextSpanMapping,
    _raw_span,
    _select_primary,
    _text_span_digest,
)

SPEC = PackSpec(
    pack_id="PK09",
    forms=frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"}),
    applicability_rule_id="pack.pk09.applicability/v1",
    applicable_classes=None,
)

# B.2 governing sections.
# Dev-corpus recall repair (2026-11-01, corpora diversified_v1 + litigation_v1):
# four locator shapes kept standard-wording sections out of reach. (1) The
# financial-statement index pages list "Report of Independent Registered
# Public Accounting Firm 42" and "Controls and Procedures 123" with a bare
# trailing page number and no "Item N." fingerprint, so the shared TOC-skip
# rule chose the index line and the real section fell outside the span; a
# heading arm that refuses a bare 1-3 digit successor kills those lines.
# (2) Some issuers set the real Item 9A / audit heading in forms the plain
# arm never matches (an em/en dash between number and title, or the
# title-only all-caps heading with the item number dropped from the text);
# the dash-tolerant and all-caps title-only arms carry them. (3) The
# auditor's own scope paragraph says "...appearing under Item 9A", and the
# bare "Item 9A\." end boundary matched it mid-report, truncating the audit
# span before the signature block; the end boundaries below are attached to
# the item TITLE, which the scope cross-reference never carries.
_TOC_PAGE_GUARD = r"(?!\s+\d{1,3}\b)"
_ITEM9_END = r"Item\s+9\b[\s.]*[—–-]?\s*Changes"
_ITEM9A_END = r"Item\s+9A\b[\s.]*[—–-]?\s*Controls"
_REPORT_END_HEADINGS = (
    _ITEM9A_END,
    _ITEM9_END,
    r"Item\s+9B\b",
    r"Part\s+III",
)
ITEM9A = narrative.SectionSpec(
    r"Item\s+9A\.?\s*Controls and Procedures"
    r"|Item\s+9A\b[\s.]*[—–-]?\s*Controls and Procedures" + _TOC_PAGE_GUARD
    # Title-only heading, rendered in capitals with the item number outside
    # the heading text; the scoped (?-i:) keeps it off body prose.
    + r"|(?-i:CONTROLS\s+AND\s+PROCEDURES)" + _TOC_PAGE_GUARD,
    (r"Item\s+9B\.", r"Item\s+9C\.", r"Part\s+III"),
)
ITEM4_CONTROLS = narrative.SectionSpec(
    r"Item\s+4\b[\s.]*[—–-]?\s*Controls and Procedures" + _TOC_PAGE_GUARD,
    (r"Part\s+II", r"Item\s+1\."),
)
_AUDIT_HEADING = (
    r"Report of Independent Registered Public Accounting Firm" + _TOC_PAGE_GUARD
)
AUDIT = narrative.SectionSpec(_AUDIT_HEADING, _REPORT_END_HEADINGS)
ICFR_REPORT = narrative.SectionSpec(
    r"Opinion on Internal Control Over Financial Reporting" + _TOC_PAGE_GUARD
    + r"|"
    + _AUDIT_HEADING,
    _REPORT_END_HEADINGS,
)
# Management's own ICFR report heading: the conclusion sentence lives here
# when the issuer files it inside Item 8 instead of Item 9A (the Item 9A text
# then incorporates it by reference). Searched only by the finalize fallback.
MGMT_ICFR_REPORT = narrative.SectionSpec(
    r"Management.s (?:Annual )?Report on Internal Control Over Financial Reporting"
    + _TOC_PAGE_GUARD
    + r"|Report of Management on [^.]{3,120}?Internal Control Over Financial Reporting"
    + _TOC_PAGE_GUARD,
    (r"Report of Independent Registered Public Accounting Firm",)
    + _REPORT_END_HEADINGS,
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
# Dev-corpus recall repair (2026-11-01, corpora diversified_v1 + litigation_v1):
# three standard management-conclusion wordings matched no pre-existing arm —
# the adjective-first conclusion ("management determined that the Company
# maintained effective internal control over financial reporting"), the
# issuer-named copula ("the internal control over financial reporting of
# a diversified issuer is effective") and the lowercase possessive change
# sentence. The
# new arms stay anchored to the standard conclusion verbs and to the exact
# noun phrase, and an arm that resolves to effective refuses a negation
# between verb and conclusion plus a trailing "except for" qualifier (B.3
# rule: a negated, conditional or except-for sentence never resolves to
# effective/unqualified).
_ICFR_MGMT_VERB = r"(?:concluded|concludes|determin(?:e|ed)|believes?)"
_ICFR_BRIDGE = (
    r"internal control over financial reporting"
    r"(?:\s+(?:of|at)\s+[^.]{0,60}?)?\s+(?:was|is|were) "
)
_ICFR_MGMT_CONCLUSION_ARMS = (
    _ICFR_MGMT_VERB + r"(?:(?!\b(?:not|never|unable)\b)[^.]){0,200}?"
    + _ICFR_BRIDGE + r"(?P<mgmt_effective>effective)(?![^.]{0,120}\bexcept\b)"
    r"|" + _ICFR_MGMT_VERB + r"[^.]{0,200}?"
    + _ICFR_BRIDGE + r"(?P<mgmt_ineffective>not effective|ineffective)"
    r"|" + _ICFR_MGMT_VERB + r"(?:(?!\b(?:not|never|unable)\b)[^.]){0,160}?"
    r"maintained\s*(?:,\s*in all material respects,\s*)?"
    r"(?P<mgmt_effective_adj>effective) internal control over financial reporting"
    r"(?![^.]{0,120}\bexcept\b)"
    r"|" + _ICFR_MGMT_VERB + r"[^.]{0,160}?"
    r"(?:did not maintain|do not maintain|does not maintain|has not maintained|"
    r"have not maintained|failed to maintain|not maintain|never maintain)"
    r"[^.]{0,60}?effective internal control over financial reporting"
)
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
    + r"|" + _ICFR_MGMT_CONCLUSION_ARMS
)
# The management-conclusion arms alone: what the finalize fallback searches
# inside Management's own ICFR report, where the un-anchored arms would
# otherwise latch onto Section 404 requirement boilerplate ("... required to
# report ... whether the Company's internal control over financial reporting
# is effective") instead of the stated conclusion.
_ICFR_MGMT_CONCLUSION = _ICFR_MGMT_CONCLUSION_ARMS
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
# B.3 pattern revision v6 (review F4-1..F4-4, 2026-10-31), corrected by
# v7 (review F5-1/F5-5, 2026-10-31): remediation timing. A weakness is
# PRESENT as of the filing's period of report unless the remediation is
# placed on or before that date: when the remediation carries its own
# parseable date, _mw_coordinated_remediation_absent compares that date
# against the period of report (D on or before the period end is an
# absence, D after it leaves the weakness present); when the date does
# not parse, the v6 undated read — marker and sentence as-of only,
# never a guessed year and never today's date — decides. Arm 2's
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
    r"(?:no changes|changes) in (?:the Company.s |the company.s |our |"
    r"[A-Z][A-Za-z.’']+ )?"
    r"internal control over financial reporting"
)
# Dev-corpus recall repair (2026-11-01): two standard signature-block forms
# matched no arm — the conformed signature set in capitals ("/S/ BIG FOUR &
# CO LLP") and the bare signature block with no conformed "/s/" prefix at
# all ("Auditor & Co LLP City, State February 24, 2026"). The bare arm stays
# anchored to the auditor signature-block shape
# (firm name ending LLP, then the office city/state and the report date).
#
# Precedence repair (review follow-up, 2026-11-01): the framework resolves a
# selector with one leftmost search, so a predecessor auditor's bare dated
# block before the incumbent's conformed block used to win the field. The
# two arms are split here (concatenation is byte-identical to the v2
# pattern, so the mapping digest is unchanged) so ``_auditor_firm_value``
# can prefer the conformed arm across the whole audit span; see the
# resolver below.
_AUDITOR_FIRM_CONFORMED = (
    r"/[sS]/\s*(?P<firm>[A-Z][A-Za-z&.,\s'’]{2,80}?LLP)"
)
_AUDITOR_FIRM_BARE = (
    r"(?P<firm2>[A-Z][A-Za-z&,'’\s]{2,80}?LLP)\s+"
    r"(?:[A-Z][A-Za-z.,'’]*\s+){0,4}"
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s*\d{4}"
)
AUDITOR_FIRM = _AUDITOR_FIRM_CONFORMED + "|" + _AUDITOR_FIRM_BARE
# Dev-corpus precision guard (2026-11-01): an except-for qualifier after the
# opinion phrase is a qualified opinion the enum does not carry; it must stay
# typed-absent, never resolve to unqualified/effective.
AUDITOR_OPINION_FS = (
    r"(?P<unqualified>present fairly, in all material respects)"
    r"(?![^.]{0,120}\bexcept\b)"
    r"|(?P<adverse>do not present fairly)"
    r"|(?P<disclaimer>do not express an opinion)"
)
AUDITOR_OPINION_ICFR = (
    r"(?P<effective>maintained, in all material respects, effective internal "
    r"control)(?![^.]{0,120}\bexcept\b)"
    r"|(?P<adverse>has not maintained effective internal control)"
)
CRITICAL_AUDIT_MATTERS = r"Critical Audit Matters?\b(?!.{0,15}communicated)"
# Review repairs D1+E1/E2 (per-pack reviews, 2026-11-02): the arm refuses
# an occurrence preceded by no/not/never/free of/without — capitals
# included (E2) — one followed by may/might/could/would in the same
# clause, or (E1) one whose same clause run re-mentions the doubt directly
# negated ("no|not|never (any) substantial doubt", 160 chars). A refused
# match never discloses; the field falls to 'not_disclosed' as if absent.
_GC_DOUBT_PHRASE = (
    r"substantial doubt about (?:the Company.s|our|its) ability "
    r"to continue as a going concern"
)
GOING_CONCERN_DOUBT = (
    r"(?<![Nn]o )(?<![Nn]ot )(?<![Nn]ever )(?<![Ff]ree of )(?<![Ww]ithout )"
    r"(?P<present>" + _GC_DOUBT_PHRASE + r")"
    r"(?![^.;:]{0,24}\b(?:may|might|could|would)\b)"
    r"(?![^.;:]{0,160}\b(?:[Nn]o|[Nn]ot|[Nn]ever)\s+(?:any\s+)?substantial doubt)"
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
# F6-3 (review follow-up, 2026-10-31): the deactivate path appends a
# limitation only below the framework's production cap — base.py's R-F10
# gate refuses an envelope over 32 limitations at mint time and the result
# schema's ``limitations.maxItems`` matches it, so a finalize-time append
# must not be the line that breaks that ceiling. base.py spells its cap as
# an inline literal, so the framework's same-valued named constant is
# imported rather than a second hard-coded 32.
_LIMITATION_CAP = PACKET_MAX_LIMITATIONS

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


def _normalize_firm_name(name: str) -> str:
    return " ".join(name.split())


def _collect_auditor_firm_matches(
    nt: Any, section_span: tuple[int, int]
) -> tuple[str, list[tuple[str, int, int]]]:
    """Collect every auditor-firm candidate across the whole audit span.

    Returns ``(arm, matches)``. The conformed ``/s/`` arm wins whenever the
    span carries at least one conformed signature — the incumbent signs the
    report, so a predecessor's bare office block never outranks it — and the
    bare dated-block arm is read only when no conformed signature exists.
    Each match is the raw firm name and its span.
    """
    lo, hi = section_span
    conformed = [
        (m.group("firm"), m.start("firm"), m.end("firm"))
        for m in re.compile(_AUDITOR_FIRM_CONFORMED).finditer(nt.text, lo, hi)
    ]
    if conformed:
        return "conformed", conformed
    bare = [
        (m.group("firm2"), m.start("firm2"), m.end("firm2"))
        for m in re.compile(_AUDITOR_FIRM_BARE).finditer(nt.text, lo, hi)
    ]
    return "bare", bare


def _auditor_firm_value(
    nt: Any, section_span: tuple[int, int], match: Any
) -> tuple[str, tuple[int, int]]:
    # 2026-11-01: the bare signature-block arm captures through ``firm2``.
    # Precedence repair (review follow-up, 2026-11-01): the passed match is
    # the framework's single leftmost search over the span, which a
    # predecessor's earlier bare block wins. Re-read the whole span instead:
    # the conformed arm outranks every bare block, and the chosen arm's
    # first candidate is returned. When the chosen arm names two distinct
    # firms the override still returns the first candidate — a text-value
    # override cannot mint an absence — and ``finalize_result`` demotes that
    # row to the framework's typed absence (never guess between two firms).
    _arm, matches = _collect_auditor_firm_matches(nt, section_span)
    if matches:
        firm, lo, hi = matches[0]
        return firm, (lo, hi)
    name = "firm" if match.group("firm") is not None else "firm2"
    return match.group(name), (match.start(name), match.end(name))


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
    # Dev-corpus recall repair (2026-11-01): the issuer-named copula and the
    # adjective-first conclusion resolve through these added arms; the
    # negated adjective forms ("did not maintain effective ...") resolve
    # ineffective.
    r"|internal control over financial reporting\s+(?:of|at)\s+[^.]{0,60}?\s+"
    r"(?:was|is|were) (?P<effective_bridge>effective)"
    r"|internal control over financial reporting\s+(?:of|at)\s+[^.]{0,60}?\s+"
    r"(?:was|is|were) (?P<ineffective_bridge>not effective|ineffective)"
    r"|maintained\s*(?:,\s*in all material respects,\s*)?"
    r"(?P<effective_adj>effective) internal control over financial reporting"
    r"|(?:did not maintain|do not maintain|does not maintain|"
    r"has not maintained|have not maintained|failed to maintain|"
    r"not maintain|never maintain)[^.]{0,60}?"
    r"(?P<ineffective_adj>effective) internal control over financial reporting"
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
# "subsequently|later|after" places it after the balance date.
# B.3 v7 (review F5-1): a remediation carrying its own date is dated in
# one of four forms — "as of <Month D, YYYY>" (v6's only form), "on
# <Month D, YYYY>", "in <Month YYYY>" (read at that month's LAST day)
# and "(during the) quarter ended <Month D, YYYY>" — and that date is
# compared against the filing's period of report (see
# Pk09Producer.finalize_result), not against the sentence's own as-of
# date. The sentence-internal comparison below remains only as the
# fallback for a remediation whose date does not parse; fiscal-period-
# only phrases ("in the first quarter of fiscal 2027", "during fiscal
# 2026", "in the fourth quarter") match no form and stay undated, and
# no year is ever guessed.
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
_MW_REMEDIATION_DATE = re.compile(
    r"\b(?:during\s+the\s+quarter\s+ended|quarter\s+ended|as\s+of|on|in)\s+"
    r"((?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{1,2},\s+\d{4}"
    r"|(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{4})",
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


def _mw_remediation_date_key(stated: str) -> tuple[int, int, int]:
    """B.3 v7: date key for one of _MW_REMEDIATION_DATE's two spellings.

    "September 30, 2026" (day form) keys to its own day; "July 2026"
    (month-year form) keys to that month's LAST day, so a remediation
    "in <the balance month>" still counts as on or before a period end
    falling inside that month.
    """
    parts = stated.replace(",", "").split()
    month = _MW_MONTH_ORDINALS[parts[0].lower()]
    if len(parts) == 3:
        return (int(parts[2]), month, int(parts[1]))
    return (int(parts[1]), month, calendar.monthrange(int(parts[1]), month)[1])


def _mw_coordinated_remediation_absent(
    text: str, from_pos: int, por: date | None
) -> bool:
    """B.3 v6/v7: does the coordinated clause after ``from_pos`` read as
    an unnegated remediation completed on or before the balance date?

    The scan is bounded by the "."-bounded sentence holding the match, so
    a remediation narrated in a later sentence never reaches it. A
    remediation preceded by "not"/"never"/"no" ("has not been remediated")
    or placed after the balance date by a "subsequently"/"later"/"after"
    marker leaves the weakness present. A remediation whose own date
    parses (v7: "as of"/"on <Month D, YYYY>", "in <Month YYYY>" at the
    month's last day, "(during the) quarter ended <Month D, YYYY>") is
    compared against the filing's period of report ``por``: a date on or
    before the period end is an absence, a date after it leaves the
    weakness present. Only when that date does not parse — or ``por`` is
    unknown — does the v6 undated fallback run: a stated "as of <date>"
    on the remediation is compared against the sentence's own earlier
    as-of date, and a remediation with no date and no marker is treated
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
        dated = _MW_REMEDIATION_DATE.search(text, hit.end(), sentence_hi)
        if dated is not None and por is not None:
            if _mw_remediation_date_key(dated.group(1)) <= (
                por.year,
                por.month,
                por.day,
            ):
                return True
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
        return _stated_conclusion_literal(stated), (stated.start(), stated.end())
    return "material_weakness", (match.start(), match.end())


def _stated_conclusion_literal(match: Any) -> str:
    """The enum literal a stated-conclusion match carries."""
    return (
        "effective"
        if any(
            match.group(name) is not None
            for name in ("effective", "effective_bridge", "effective_adj")
        )
        else "ineffective"
    )


# Review repair D2 (per-pack review, 2026-11-02): the framework resolves a
# selector with one leftmost search, so the acquired-subsidiary exclusion
# wording ("Management determined that the internal control over financial
# reporting of <acquired firm> was not effective as of the acquisition
# date") placed before management's period-end conclusion used to win the
# field, and reversing the two sentences flipped it back — a purely
# leftmost-order read. Among multiple conclusion clauses the v7 period
# machinery (the _MW_AS_OF_DATE read the dated-remediation rule uses) now
# prefers the clause whose sentence's as-of date equals the period of
# report; clauses with that date that disagree, or none dated to it,
# demote to the typed absence the two-firm auditor demotion produces. A
# single conclusion clause behaves exactly as before.
_KEEP_TODAY = object()


def _sentence_as_of_key(
    text: str, start: int, end: int
) -> tuple[int, int, int] | None:
    """The "as of <Month D, YYYY>" key of the sentence holding [start, end),
    or None when the sentence carries no parseable as-of date."""
    lo, hi = _sentence_bounds(text, start, end)
    stated = _MW_AS_OF_DATE.search(text, lo, hi)
    return None if stated is None else _mw_date_key(stated.group(1))


def _prefer_period_conclusion(
    text: str,
    candidates: Sequence[tuple[str, tuple[int, int]]],
    por: date | None,
) -> Any:
    """D2 selection among conclusion ``candidates`` — ``(literal, span)``
    pairs.

    Returns the period-of-report clause's ``(literal, span)`` when one
    exists and the clauses dated to the period agree; ``None`` to demote
    (no clause dated to the period, or those clauses disagree); the
    ``_KEEP_TODAY`` sentinel when today's resolution must stand (a single
    clause, or no period of report to compare against — the v7 pass's own
    precedent for an unknown period).
    """
    if len(candidates) <= 1 or por is None:
        return _KEEP_TODAY
    preferred = [
        (literal, span)
        for literal, span in candidates
        if _sentence_as_of_key(text, span[0], span[1]) == (por.year, por.month, por.day)
    ]
    if not preferred:
        return None
    if len({literal for literal, _span in preferred}) > 1:
        return None
    return preferred[0]


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
    F1-A/F1-B/F1-C/F2-A/F2-B), plus the B.3 v6/v7 remediation-timing
    read (reviews F4-1..F4-4, then F5-1/F5-5).

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

    Remediation-timing rule (v6, corrected v7): after the clause-bounded
    look-back, the coordinated clause following the match — text after
    the first "and"/"but" inside the same "."-bounded sentence — is read
    for an unnegated remediation predicate (see
    ``_mw_coordinated_remediation_absent``). A remediation carrying its
    own parseable date D ("as of" or "on <Month D, YYYY>", "in <Month
    YYYY>" read at that month's last day, "(during the) quarter ended
    <Month D, YYYY>") is compared against the filing's period of report
    (``por``, read off the narrative object when it carries one — the
    ``Pk09Producer.finalize_result`` pass below — and unknown on the
    framework's override pass): D on or before the period end ("... but
    it has been remediated as of June 30, 2026" against a June 30, 2026
    period) is an absence, D after it ("... remediated as of September
    30, 2026" against the same period) leaves the weakness present. A
    remediation whose date does not parse — every fiscal-period-only
    phrase ("in the first quarter of fiscal 2027") matches no form — and
    a remediation with no date at all fall back to the v6 undated read:
    a "subsequently|later|after" marker places it after the balance
    date, a stated "as of <date>" is compared against the sentence's own
    earlier as-of date, and a dateless unmarked remediation is an
    absence. A negated remediation ("and has not been remediated")
    always leaves the weakness present.
    """
    text = nt.text
    verb = _MW_IDENTIFYING_VERB.search(text, match.start(), match.end())
    if verb is not None:
        lo, _ = _sentence_bounds(text, match.start(), match.end())
        clause_start = _mw_clause_start(text, lo, verb.start())
        if _MW_NEGATION_BEFORE.search(text, clause_start, verb.start()):
            return "false", (match.start(), match.end())
    if _mw_coordinated_remediation_absent(
        text, match.end(), getattr(nt, "por", None)
    ):
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


def _gc_refused_only(audit_text: str) -> bool:
    """D1: does the audit span carry the full doubt phrase with every
    occurrence refused (negated or hypothetical wording)?

    The refusal set is exactly GOING_CONCERN_DOUBT's guards: the raw phrase
    matches but the guarded arm does not.
    """
    if re.search(_GC_DOUBT_PHRASE, audit_text) is None:
        return False
    return re.search(GOING_CONCERN_DOUBT, audit_text) is None


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
    nt = runtime.narrative_text()
    audit_span = narrative.locate_section(nt, AUDIT)
    audit_text = "" if audit_span is None else nt.text[audit_span[0] : audit_span[1]]
    if str(doubt["text_value"]) != "disclosed":
        # D1: the auditor's report repeating the phrase only in refused
        # (negated or hypothetical) wording is the false-positive
        # corroboration channel (review run A1b) — never a pass on the
        # strength of a refused match.
        if _gc_refused_only(audit_text):
            return _check_row(catalogue_check, "fail", None)
        return _check_row(catalogue_check, "pass", None)
    corroborated = "substantial doubt" in audit_text and not _gc_refused_only(
        audit_text
    )
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


# --- B.3 v7 finalize hook (review F5-1) ----------------------------------------


@dataclass(frozen=True)
class _PorNarrative:
    """``narrative_text`` stand-in that also carries the period of report.

    The framework's ``text_value_overrides`` call hands the producer the
    parsed :class:`narrative.NarrativeText` alone, and that object carries
    no period. ``Pk09Producer.finalize_result`` re-resolves the
    material-weakness boolean through this stand-in so the v7
    dated-remediation comparison can see ``por``.
    """

    text: str
    por: date


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


def _effective_section(field_id: str, primary_form: str | None):
    """The section actually searched for ``field_id`` (HOOKS override applied)."""
    section = _FIELD_MAPPINGS[field_id].section
    if field_id in _CONTROLS_FAMILY and primary_form in _QUARTERLY_FORMS:
        section = ITEM4_CONTROLS
    return section


def _section_text_span(nt: Any, section: Any) -> tuple[int, int] | None:
    if section is None:
        return (0, len(nt.text))
    return narrative.locate_section(nt, section)


def _manifest_por(primary: Any) -> date | None:
    """The filing's period of report, or None when the manifest carries none."""
    por_text = str(primary.manifest.get("period_of_report") or "")
    return date.fromisoformat(por_text[:10]) if por_text else None


class Pk09Producer(PackProducer):
    """PK09 declaration plus the B.3 v7 dated-remediation finalize hook and
    the 2026-11-01 management-report ICFR fallback.

    The framework's override pass resolves ``material_weakness_present``
    with the period of report unknown (its ``text_value_overrides``
    contract passes the parsed narrative, which carries no period), so a
    remediation carrying its own date takes the v6 undated read there.
    ``finalize_result`` — the registry hook PK11 introduced and
    PK07/PK08/PK10 already use for semantics the shared framework cannot
    express — re-runs the SAME mapping match with the filing's period of
    report and applies the v7 rule: the remediation's own date is
    compared against the period end (D after it leaves the weakness
    present, D on or before it is an absence), superseding both the v6
    dateless default and the v6 sentence-internal as-of comparison. The
    match, its span and every por-independent guard are identical
    between the two passes, so a production whose remediation is
    undated, unparseably dated, or whose dated value agrees with the
    undated read keeps the framework's envelope byte-for-byte; only a
    disagreement flips the boolean, and with it the conditional
    ``remediation_span`` row, the coverage counts, the one stale
    limitation line and the content digest.

    The second finalize pass (2026-11-01 dev-corpus repair, corpora
    diversified_v1 + litigation_v1) resolves ``icfr_management_conclusion``
    for the annual issuers that file Management's own ICFR report inside
    Item 8 and only incorporate it by reference from Item 9A: when the
    Item 9A span carries no conclusion, the verb-anchored
    management-conclusion arms are searched inside the
    ``MGMT_ICFR_REPORT`` section and a hit mints the row with the stock
    resolver's mapping identity. Quarterly forms never carry that
    report, so the pass is annual-only and 10-Qs keep their typed
    absence.
    """

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        rows = {row["field_id"]: row for row in result["fields"]}
        primary, form_matched = _select_primary(pack_input.packages, SPEC.forms)
        primary_form = (
            str(primary.manifest.get("form") or "") if form_matched else None
        )
        if self._apply_icfr_management_fallback(result, rows, primary, primary_form):
            self._repair_envelope_after_finalize(result, rows)
            self._apply_management_report_weakness_fallback(
                result, rows, primary, primary_form
            )
        else:
            # D2 reads the effective section the stock search resolved; a
            # fallback-minted row is governed by the fallback's own D2
            # selection inside Management's report instead.
            self._finalize_icfr_conclusion(result, rows, primary, primary_form)
        self._finalize_auditor_firm(result, rows, primary, primary_form)
        return self._finalize_material_weakness(result, rows, primary, primary_form)

    @staticmethod
    def _apply_icfr_management_fallback(
        result: Mapping[str, Any],
        rows: Mapping[str, Mapping[str, Any]],
        primary: Any,
        primary_form: str | None,
    ) -> bool:
        """Mint the ICFR management conclusion from Management's own report.

        Returns True when the row moved from a typed miss to a valued
        conclusion. The search runs ONLY through the verb-anchored arms
        (``_ICFR_MGMT_CONCLUSION``) so Section 404 requirement boilerplate
        inside the same report ("... whether the Company's internal control
        over financial reporting is effective") never satisfies the field;
        the value itself resolves through the same sentence-bounded
        stated-conclusion resolver the stock row uses. When the report
        holds more than one conclusion clause, the D2 selection
        (``_prefer_period_conclusion``) governs: the clause dated to the
        period of report wins, and disagreeing or undated clause sets mint
        nothing (the typed miss stands).
        """
        if primary_form in _QUARTERLY_FORMS or primary_form is None:
            return False
        row = rows.get("icfr_management_conclusion")
        if row is None or row.get("quality_state") != "missing":
            return False
        if primary is None:
            return False
        nt = narrative.primary_document_text(primary)
        section_span = narrative.locate_section(nt, MGMT_ICFR_REPORT)
        if section_span is None:
            return False
        lo, hi = section_span
        resolutions = [
            _icfr_conclusion_value(nt, section_span, match)
            for match in re.compile(_ICFR_MGMT_CONCLUSION).finditer(nt.text, lo, hi)
        ]
        if not resolutions:
            return False
        if len(resolutions) == 1:
            value, span = resolutions[0]
        else:
            selection = _prefer_period_conclusion(
                nt.text, resolutions, _manifest_por(primary)
            )
            if selection is None:
                return False
            value, span = (
                resolutions[0] if selection is _KEEP_TODAY else selection
            )
        mapping = _FIELD_MAPPINGS["icfr_management_conclusion"]
        accession = str(primary.manifest.get("accession") or "")
        row["quality_state"] = "valued"
        row["non_value_state"] = None
        row["coverage_state"] = "source_trace_complete"
        row["reason"] = None
        row["value"] = None
        row["text_value"] = value
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["mapping_rule_id"] = (
            f"{SPEC.pack_id}.icfr_management_conclusion.text_span/v1"
        )
        row["mapping_rule_digest"] = _text_span_digest(mapping)
        row["source_span"] = _raw_span(nt, span[0], span[1], accession)
        row["dependency_field_ids"] = []
        return True

    @staticmethod
    def _repair_envelope_after_finalize(
        result: dict[str, Any], rows: Mapping[str, Mapping[str, Any]]
    ) -> None:
        """Drop the stale limitation line, refresh the cross check, coverage
        and digest after a finalize pass minted a valued row."""
        result["limitations"] = [
            line
            for line in result["limitations"]
            if not line.startswith("pk09.icfr_management_conclusion: non-valued")
        ]
        for index, check in enumerate(result["checks"]):
            if check.get("check_id") != "management_vs_auditor_icfr":
                continue
            result["checks"][index] = _management_vs_auditor_icfr(check, rows)
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK09 finalize refused: " + "; ".join(errors[:5])
            )

    def _apply_management_report_weakness_fallback(
        self,
        result: dict[str, Any],
        rows: Mapping[str, Mapping[str, Any]],
        primary: Any,
        primary_form: str | None,
    ) -> None:
        """D3: never a confident material_weakness_present ``false`` over an
        Item 9A that only incorporates Management's report by reference.

        Runs only directly behind ``_apply_icfr_management_fallback``, so
        the governing conclusion row was just minted from outside Item 9A,
        and only when the effective Item 9A span is an incorporation shell
        — it carries an "incorporated by reference" marker and no own
        disclosure-controls conclusion, so the weakness boolean was
        asserted over the incorporation sentence alone. (An Item 9A that
        evaluates disclosure controls of its own keeps the framework's
        valued false over that substantive section.) The same
        MGMT_ICFR_REPORT span is then searched for the weakness boolean: a
        management-voice mention values the row through the stock resolver
        (with the period of report for the v7 remediation read); a mention
        whose sentence also lies inside the audit report is auditor-scope
        boilerplate ("assessing the risk that a material weakness exists")
        and is refused; no usable mention demotes the row to the typed
        absence the two-firm auditor demotion produces.
        ``remediation_span`` follows the boolean through the pack's
        existing gating.
        """
        row = rows.get("material_weakness_present")
        if (
            row is None
            or row.get("quality_state") != "valued"
            or row.get("text_value") != "false"
        ):
            return
        if primary is None:
            return
        por = _manifest_por(primary)
        nt = narrative.primary_document_text(primary)
        shell_span = _section_text_span(
            nt, _effective_section("material_weakness_present", primary_form)
        )
        if shell_span is None:
            return
        shell_lo, shell_hi = shell_span
        section_text = nt.text[shell_lo:shell_hi]
        if (
            re.search(r"incorporat\w+\s+(?:herein\s+)?by\s+reference", section_text)
            is None
            or re.compile(DISCLOSURE_CONTROLS).search(
                nt.text, shell_lo, shell_hi
            )
            is not None
        ):
            return  # a substantive Item 9A: the valued false over it stands
        section_span = narrative.locate_section(nt, MGMT_ICFR_REPORT)
        if section_span is None:
            return
        lo, hi = section_span
        audit_span = narrative.locate_section(nt, AUDIT)
        chosen = None
        for match in re.compile(MATERIAL_WEAKNESS_IDENTIFIED).finditer(
            nt.text, lo, hi
        ):
            sentence_lo, sentence_hi = _sentence_bounds(
                nt.text, match.start(), match.end()
            )
            if (
                audit_span is not None
                and sentence_lo < audit_span[1]
                and sentence_hi > audit_span[0]
            ):
                continue
            chosen = match
            break
        accession = str(primary.manifest.get("accession") or "")
        if chosen is not None:
            value, span = _material_weakness_value(
                _PorNarrative(nt.text, por) if por is not None else nt,
                section_span,
                chosen,
            )
            row["text_value"] = value
            row["source_span"] = _raw_span(nt, span[0], span[1], accession)
            if value == "true":
                self._activate_remediation_span(rows, nt, primary_form, primary)
                result["limitations"] = [
                    line
                    for line in result["limitations"]
                    if not line.startswith("pk09.remediation_span: non-valued")
                ]
        else:
            row["quality_state"] = "missing"
            row["non_value_state"] = "missing"
            row["coverage_state"] = "unmapped"
            row["reason"] = "narrative_span_not_located"
            row["value"] = None
            row["text_value"] = None
            row["evidence_kind"] = "text_span"
            row["required_evidence_kind"] = "text_span"
            row["mapping_rule_id"] = (
                f"{SPEC.pack_id}.material_weakness_present.text_span/v1"
            )
            row["mapping_rule_digest"] = _text_span_digest(
                _FIELD_MAPPINGS["material_weakness_present"]
            )
            row["source_span"] = None
            row["dependency_field_ids"] = []
            # F6-3: never the line that breaks the framework's R-F10 cap.
            if len(result["limitations"]) < _LIMITATION_CAP:
                result["limitations"].append(
                    "pk09.material_weakness_present: non-valued "
                    "(narrative_span_not_located); the governing conclusion "
                    "was minted from Management's report outside Item 9A and "
                    "no material-weakness mention was located there; section "
                    f"searched: {MGMT_ICFR_REPORT.heading}"
                )
        self._repair_envelope_after_finalize(result, rows)

    def _finalize_icfr_conclusion(
        self,
        result: dict[str, Any],
        rows: Mapping[str, Mapping[str, Any]],
        primary: Any,
        primary_form: str | None,
    ) -> None:
        """D2: prefer the period-of-report conclusion clause among many
        inside the effective section (see ``_prefer_period_conclusion``).

        The stock row resolves through the framework's single leftmost
        search, so an acquired-subsidiary exclusion clause placed first used
        to win the literal. When the effective section holds more than one
        stated conclusion clause, the clause whose sentence's as-of date
        equals the period of report governs: a different literal rewrites
        the row's value and evidence span, while disagreeing clauses dated
        to the period — or none dated to it — demote the row to the typed
        absence the two-firm auditor demotion produces. A single clause, a
        preferred literal equal to the row's own, or an unknown period of
        report leaves the row exactly as the framework resolved it.
        """
        row = rows.get("icfr_management_conclusion")
        if row is None or row.get("quality_state") != "valued":
            return
        if primary is None or primary_form is None:
            return
        por = _manifest_por(primary)
        if por is None:
            return
        nt = narrative.primary_document_text(primary)
        section = _effective_section("icfr_management_conclusion", primary_form)
        section_span = _section_text_span(nt, section)
        if section_span is None:
            return
        lo, hi = section_span
        candidates = [
            (_stated_conclusion_literal(match), (match.start(), match.end()))
            for match in re.compile(_ICFR_STATED_CONCLUSION).finditer(
                nt.text, lo, hi
            )
        ]
        selection = _prefer_period_conclusion(nt.text, candidates, por)
        if selection is _KEEP_TODAY:
            return
        if selection is not None:
            value, span = selection
            if value == row.get("text_value"):
                return  # same literal: the stock leftmost evidence stands
            accession = str(primary.manifest.get("accession") or "")
            row["text_value"] = value
            row["source_span"] = _raw_span(nt, span[0], span[1], accession)
            self._repair_envelope_after_finalize(result, rows)
            return
        section_text = "whole document" if section is None else section.heading
        mapping = _FIELD_MAPPINGS["icfr_management_conclusion"]
        row["quality_state"] = "missing"
        row["non_value_state"] = "missing"
        row["coverage_state"] = "unmapped"
        row["reason"] = "narrative_span_not_located"
        row["value"] = None
        row["text_value"] = None
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["mapping_rule_id"] = (
            f"{SPEC.pack_id}.icfr_management_conclusion.text_span/v1"
        )
        row["mapping_rule_digest"] = _text_span_digest(mapping)
        row["source_span"] = None
        row["dependency_field_ids"] = []
        # F6-3: never the line that breaks the framework's R-F10 cap.
        if len(result["limitations"]) < _LIMITATION_CAP:
            result["limitations"].append(
                "pk09.icfr_management_conclusion: non-valued "
                "(narrative_span_not_located); "
                f"{len(candidates)} conclusion clauses in the section "
                "disagree or none is dated to the period of report; section "
                f"searched: {section_text}"
            )
        self._repair_envelope_after_finalize(result, rows)

    @staticmethod
    def _finalize_auditor_firm(
        result: dict[str, Any],
        rows: Mapping[str, Mapping[str, Any]],
        primary: Any,
        primary_form: str | None,
    ) -> None:
        """Demote an ambiguous auditor_firm read to the framework's typed
        absence.

        ``_auditor_firm_value`` cannot mint an absence row, so an audit span
        whose chosen arm names two distinct firms (after whitespace
        normalisation) reaches finalize briefly valued with the first
        candidate. This pass re-runs the same two-arm collection and, on
        ambiguity, restores the typed absence the framework's own miss
        produces — quality_state ``missing`` under the declared reason
        ``narrative_span_not_located`` — with a limitation naming the
        ambiguity. Never guess between two firms.
        """
        row = rows.get("auditor_firm")
        if row is None or row.get("quality_state") != "valued":
            return
        if primary is None or primary_form in _QUARTERLY_FORMS:
            return
        nt = narrative.primary_document_text(primary)
        section = _effective_section("auditor_firm", primary_form)
        section_span = _section_text_span(nt, section)
        if section_span is None:
            return
        arm, matches = _collect_auditor_firm_matches(nt, section_span)
        distinct = {_normalize_firm_name(name) for name, _lo, _hi in matches}
        if len(distinct) <= 1:
            return  # one firm in the chosen arm: the resolver's value stands
        section_text = "whole document" if section is None else section.heading
        mapping = _FIELD_MAPPINGS["auditor_firm"]
        row["quality_state"] = "missing"
        row["non_value_state"] = "missing"
        row["coverage_state"] = "unmapped"
        row["reason"] = "narrative_span_not_located"
        row["value"] = None
        row["text_value"] = None
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["mapping_rule_id"] = f"{SPEC.pack_id}.auditor_firm.text_span/v1"
        row["mapping_rule_digest"] = _text_span_digest(mapping)
        row["source_span"] = None
        row["dependency_field_ids"] = []
        # F6-3: never the line that breaks the framework's R-F10 cap.
        if len(result["limitations"]) < _LIMITATION_CAP:
            result["limitations"].append(
                "pk09.auditor_firm: non-valued (narrative_span_not_located); "
                f"auditor signature block ambiguous: {len(distinct)} distinct "
                f"firm names in the {arm} arm; section searched: "
                f"{section_text}"
            )
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK09 finalize refused: " + "; ".join(errors[:5])
            )

    def _finalize_material_weakness(
        self,
        result: dict[str, Any],
        rows: Mapping[str, Mapping[str, Any]],
        primary: Any,
        primary_form: str | None,
    ) -> dict[str, Any]:
        weakness = rows.get("material_weakness_present")
        if weakness is None or weakness.get("quality_state") != "valued":
            return result  # no affirmed weakness mention to re-date
        if primary is None:
            return result
        por_text = str(primary.manifest.get("period_of_report") or "")
        if not por_text:
            return result
        por = date.fromisoformat(por_text[:10])
        nt = narrative.primary_document_text(primary)
        section = _effective_section("material_weakness_present", primary_form)
        section_span = _section_text_span(nt, section)
        if section_span is None:
            return result  # the framework row already types this absence
        lo, hi = section_span
        match = re.compile(MATERIAL_WEAKNESS_IDENTIFIED).search(nt.text, lo, hi)
        if match is None:
            return result  # valued absence over the section: nothing dated
        value, _span = _material_weakness_value(
            _PorNarrative(nt.text, por), section_span, match
        )
        if value == weakness.get("text_value"):
            return result  # undated/unparseably dated: the v6 read stands
        weakness["text_value"] = value
        if value == "true":
            self._activate_remediation_span(rows, nt, primary_form, primary)
            result["limitations"] = [
                line
                for line in result["limitations"]
                if not line.startswith("pk09.remediation_span: non-valued")
            ]
        else:
            self._deactivate_remediation_span(rows)
            section = _effective_section("remediation_span", primary_form)
            section_text = "whole document" if section is None else section.heading
            # F6-3: never the line that breaks the framework's R-F10 cap.
            if len(result["limitations"]) < _LIMITATION_CAP:
                result["limitations"].append(
                    "pk09.remediation_span: non-valued (missing_dependency); "
                    f"section searched: {section_text}"
                )
        _recompute_coverage(result)
        result["pack_content_sha256"] = contract.pack_content_digest(result)
        errors = contract.validate_pack_result(result)
        if errors:
            raise SpecialistPackError(
                "PK09 finalize refused: " + "; ".join(errors[:5])
            )
        return result

    @staticmethod
    def _activate_remediation_span(
        rows: Mapping[str, dict[str, Any]],
        nt: Any,
        primary_form: str | None,
        primary: Any,
    ) -> None:
        """Mint the valued remediation_span row on a false→true flip.

        ``finalize_result`` calls this only when its v7 re-read flips
        ``material_weakness_present`` to ``true`` while the framework's
        conditional gate had left ``remediation_span`` un-valued. The
        row re-runs the stock resolver's own search over the effective
        section (the frozen ``REMEDIATION`` pattern, the same sentence
        span and ``max_chars`` truncation) and carries the mapping
        identity that resolver stamps: ``mapping_rule_id`` is
        ``f"{SPEC.pack_id}.remediation_span.text_span/v1"`` — equal to
        the stock row's ``PK09.remediation_span.text_span/v1`` — and
        ``mapping_rule_digest`` is the field's ``_text_span_digest``.
        """
        row = rows.get("remediation_span")
        if row is None:
            return
        section_span = _section_text_span(
            nt, _effective_section("remediation_span", primary_form)
        )
        if section_span is None:
            return
        lo, hi = section_span
        hit = re.compile(REMEDIATION).search(nt.text, lo, hi)
        if hit is None:
            return
        mapping = _FIELD_MAPPINGS["remediation_span"]
        span = narrative.sentence_span(nt.text, hit.start(), hit.end(), section_span)
        text_value = nt.text[span[0] : span[1]].strip()[: mapping.max_chars]
        accession = str(primary.manifest.get("accession") or "")
        row["quality_state"] = "valued"
        row["non_value_state"] = None
        row["coverage_state"] = "source_trace_complete"
        row["reason"] = None
        row["value"] = None
        row["text_value"] = text_value
        row["evidence_kind"] = "text_span"
        row["required_evidence_kind"] = "text_span"
        row["mapping_rule_id"] = f"{SPEC.pack_id}.remediation_span.text_span/v1"
        row["mapping_rule_digest"] = _text_span_digest(mapping)
        row["source_span"] = _raw_span(nt, span[0], span[1], accession)
        row["dependency_field_ids"] = []

    @staticmethod
    def _deactivate_remediation_span(
        rows: Mapping[str, dict[str, Any]]
    ) -> None:
        """Restore the gated remediation_span row the conditional hook
        mints when the weakness is not present (byte-faithful to the
        framework's own ``missing_dependency`` absence)."""
        row = rows.get("remediation_span")
        if row is None:
            return
        row["quality_state"] = "not_evaluable"
        row["non_value_state"] = "not_evaluable"
        row["coverage_state"] = "unmapped"
        row["reason"] = "missing_dependency"
        row["value"] = None
        row["text_value"] = None
        row["evidence_kind"] = "xbrl_fact"
        row["required_evidence_kind"] = "xbrl_fact"
        row["mapping_rule_id"] = None
        row["mapping_rule_digest"] = None
        row["source_span"] = None
        row["dependency_field_ids"] = ["material_weakness_present"]


PRODUCER = Pk09Producer(
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
    "MGMT_ICFR_REPORT",
    "PRODUCER",
    "SPEC",
]
