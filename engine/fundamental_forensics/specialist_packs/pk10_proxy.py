"""PK10 producer: proxy compensation and governance (DEF 14A).

Two honest states at this version (frozen B.1/B.2). No proxy capture path
exists yet (owned by the D3 seam), so every package list admitted today —
the committed 10-K fixture included — types ``not_evaluable`` +
``proxy_package_not_supplied``: the pack is applicable in principle to
every issuer but the governing document was not supplied. The shared
framework's R-K1 form gate answers a form miss ``not_applicable`` +
``form_outside_pack_forms``, so
``Pk10Producer.finalize_result`` (the registry hook PK11 introduced)
rewrites that envelope to the frozen not-supplied shape and re-digests +
re-checks it against the contract. A DEFA14A-only package list is also
"not supplied": B.1 keys applicability on a DEF 14A package being present.

With a DEF 14A package admitted, the four ``text_span`` rows resolve over
the proxy's primary document through :mod:`narrative` (frozen patterns, no
section specs). The frozen PK10 catalogue carries no
``narrative_span_not_located`` code (PK09's does), so a pattern the proxy
does not supply resolves as the framework's valued absence —
``not_disclosed`` asserted over the whole document — never a reason the
catalogue refuses. The six ``table_cell`` rows stay reserved for the later
table-extraction lane (C2) as ``unsupported`` + ``missing_dependency`` —
except when the quantity is visible as a prose numeral, which types the
row ``numeric_value_in_narrative_only`` and never scrapes a number. The
four checks are all ``not_evaluable`` + ``missing_dependency`` through the
``register_extra_check`` hook; ``cap_vs_sct_total`` never splices CAP and
SCT Total into one number.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .. import specialist_pack_contract as contract
from . import narrative
from .base import (
    NarrativeHooks,
    PackInput,
    PackProducer,
    PackSpec,
    SpecialistPackError,
    TableMapping,
    TextSpanMapping,
    _select_primary,
    register_extra_check,
    register_extra_receipts,
)

SPEC = PackSpec(
    pack_id="PK10",
    forms=frozenset({"DEF 14A"}),
    applicability_rule_id="pack.pk10.applicability/v1",
    applicable_classes=None,
)

# B.2 frozen patterns over the proxy's primary document (whole text: a proxy
# statement has no Item-numbered governing sections to pin).
PERFORMANCE_MEASURE = r"(?:most important|selected) (?:financial )?performance measure"
DIRECTOR_INDEPENDENCE = r"independent (?:director|under the)"
RELATED_PARTY = r"related[- ]party transaction"
# B.3 pattern revision v4 (review F1/F2/F3, 2026-10-20): the say-on-pay
# frequency resolves ORDER-INDEPENDENTLY inside the anchor's sentence; a
# rejected alternative is never evidence, and an "annual" that heads a
# non-meeting compound noun is not a frequency. The v3 one-regex arms are gone
# (their alternation order silently decided contrastive sentences); the
# mapping pattern is the anchor alone — it triggers the resolution and keeps
# the no-anchor valued absence — and the frequency decision is the
# ``_say_on_pay_frequency_value`` override, which implements this rule:
#
# * Same sentence only, either side of the anchor. The anchor and every
#   candidate frequency phrase must sit inside one ``. ``-delimited sentence
#   (only the advisory-vote anchor arm carries a ``[^.]`` gap; the sentence
#   boundary itself comes from ``narrative.sentence_span``); phrases
#   are collected on both sides of the anchor, and the leftmost anchored
#   sentence that keeps a surviving frequency governs.
# * Frequency phrases, hyphenated variants (``every-three-years``,
#   ``every-two-years``) accepted wherever the spaced form is: annual
#   ``annual|annually|every year|each year|once a year|one year``, biennial
#   ``biennial|biennially|every two years|every other year``,
#   triennial ``triennial|triennially|every three years``. A bare duration
#   ("three years", "two years") is never a frequency.
# * Discards — a phrase is not evidence when it is the object of a
#   rejection/contrast in the same sentence, i.e. ``rejecting|rejected|rather
#   than|instead of|as opposed to|not|against|alternative`` precedes it within
#   40 chars or ``alternative|was rejected|were rejected|option`` follows it
#   within 20 chars; when ``annual`` is a compound-noun head — ``annual
#   (meeting|report|incentive|bonus|cash|equity|compensation|proxy|statement|
#   shareholder meeting)`` — while ``annual say-on-pay vote`` / ``annual
#   advisory vote`` / ``annual vote`` / ``annual basis`` stay frequency
#   evidence; or when the phrase is followed within 12 chars by ``review|
#   cycle|period|plan|program`` — a noun other than vote/election/resolution/
#   proposal/frequency, so the phrase modifies that noun (e.g. a peer-group
#   review), not the vote. Discarded phrases never appear in the evidence
#   span.
# * Resolution: exactly one distinct frequency surviving in the sentence
#   values that frequency, the span running from the earlier of anchor and
#   leftmost surviving phrase to the later of the two, bounded to the
#   sentence. Two or more distinct frequencies surviving one sentence with no
#   contrast marker separating them, and an anchored sentence with no
#   surviving frequency alike, resolve the pack's existing
#   anchor-present-no-resolvable-frequency emission: the valued
#   ``not_disclosed`` asserted over the whole document.
_SAY_ON_PAY_ANCHOR = (
    r"(?:say[- ]on[- ]pay|advisory vote[^.]{0,120}?(?:executive )?compensation"
    r"|frequency of)"
)
_ANNUAL_COMPOUND_HEAD = (
    r"(?:meeting|report|incentive|bonus|cash|equity|compensation|proxy"
    r"|statement|shareholder meeting)"
)
# Longest alternative first; the word boundaries keep "annual" out of
# "semiannually" and the like.
_FREQUENCY_PHRASES = (
    (
        "triennial",
        r"every three years|every-three-years|triennially|triennial",
    ),
    (
        "biennial",
        r"every two years|every-two-years|every other year|biennially"
        r"|biennial",
    ),
    (
        "annual",
        r"every year|each year|once a year|one year|annually"
        r"|annual(?! " + _ANNUAL_COMPOUND_HEAD + r")",
    ),
)
_FREQUENCY_RES = tuple(
    (literal, re.compile(r"\b(?:" + body + r")\b", re.IGNORECASE))
    for literal, body in _FREQUENCY_PHRASES
)
_ANCHOR_RE = re.compile(_SAY_ON_PAY_ANCHOR, re.IGNORECASE)
_REJECT_BEFORE_RE = re.compile(
    r"\b(?:rejecting|rejected|rather than|instead of|as opposed to|not"
    r"|against|alternative)\b",
    re.IGNORECASE,
)
_REJECT_AFTER_RE = re.compile(
    r"\b(?:alternative|was rejected|were rejected|option)\b", re.IGNORECASE
)
_NON_VOTE_NOUN_RE = re.compile(
    r"\b(?:review|cycle|period|plan|program)\b", re.IGNORECASE
)
# The rejection / compound-head windows (chars before / after a phrase).
_REJECT_BEFORE_WINDOW = 40
_REJECT_AFTER_WINDOW = 20
_NON_VOTE_NOUN_WINDOW = 12


def _surviving_frequencies(
    text: str, start: int, end: int
) -> list[tuple[str, "re.Match[str]"]]:
    """Every frequency phrase inside ``[start, end)`` that survives all
    discards, as ``(enum literal, match)`` pairs in text order per literal."""
    survivors: list[tuple[str, "re.Match[str]"]] = []
    for literal, phrase_re in _FREQUENCY_RES:
        for match in phrase_re.finditer(text, start, end):
            window = max(start, match.start() - _REJECT_BEFORE_WINDOW)
            before = text[window : match.start()]
            if _REJECT_BEFORE_RE.search(before):
                continue
            after = text[match.end() : min(end, match.end() + _REJECT_AFTER_WINDOW)]
            if _REJECT_AFTER_RE.search(after):
                continue
            heads = text[match.end() : min(end, match.end() + _NON_VOTE_NOUN_WINDOW)]
            if _NON_VOTE_NOUN_RE.search(heads):
                continue
            survivors.append((literal, match))
    return survivors


def _say_on_pay_frequency_value(
    nt: Any, section_span: tuple[int, int], match: Any
) -> tuple[str, tuple[int, int]]:
    """``say_on_pay_frequency`` text-value override: resolve the frequency
    from the anchor's own sentence, order-independently, under the v4 discard
    and precedence rule documented at ``_SAY_ON_PAY_ANCHOR`` above. Returns
    the enum literal with its char span, or the pack's valued
    ``not_disclosed`` over the whole document when no anchored sentence keeps
    exactly one distinct surviving frequency."""
    text = nt.text
    lo, hi = section_span
    seen_sentences: set[tuple[int, int]] = set()
    for anchor in _ANCHOR_RE.finditer(text, lo, hi):
        sentence = narrative.sentence_span(
            text, anchor.start(), anchor.end(), section_span
        )
        if sentence in seen_sentences:
            continue
        seen_sentences.add(sentence)
        survivors = _surviving_frequencies(text, sentence[0], sentence[1])
        if not survivors:
            continue
        literals = {literal for literal, _match in survivors}
        if len(literals) > 1:
            return "not_disclosed", (lo, hi)
        phrase = min(survivors, key=lambda item: item[1].start())[1]
        return literals.pop(), (
            min(anchor.start(), phrase.start()),
            max(anchor.end(), phrase.end()),
        )
    return "not_disclosed", (lo, hi)

# The catalogue field name declares no "(annual | ...)" literal list, so the
# A.4 literal gate binds nothing here; the frequency literals below are the
# say-on-pay frequencies the enum type names.
_FIELD_MAPPINGS = {
    # Six reserved table-cell quantities (SCT + PvP tables): no numeric row
    # is produced from prose or tables at this version.
    "ceo_total_comp": TableMapping(),
    "other_neo_total": TableMapping(),
    "comp_actually_paid_peo": TableMapping(),
    "compensation_year": TableMapping(),
    "total_shareholder_return": TableMapping(),
    "peer_group_tsr": TableMapping(),
    # The absent_value is the frozen-catalogue constraint: PK10 carries no
    # narrative_span_not_located code, so an unmatched pattern resolves as
    # the valued absence "not_disclosed" over the whole document (the PK09
    # whole-document precedent), never a reason the contract refuses.
    "performance_measure_selected": TextSpanMapping(
        pattern=PERFORMANCE_MEASURE, absent_value="not_disclosed"
    ),
    "director_independence_span": TextSpanMapping(
        pattern=DIRECTOR_INDEPENDENCE, absent_value="not_disclosed"
    ),
    "related_party_span": TextSpanMapping(
        pattern=RELATED_PARTY, absent_value="not_disclosed"
    ),
    "say_on_pay_frequency": TextSpanMapping(
        # v4: the anchor alone triggers _say_on_pay_frequency_value; with no
        # anchor anywhere the row keeps the valued not_disclosed absence.
        pattern=_SAY_ON_PAY_ANCHOR,
        kind="enum",
        enum_map={
            "annual": "annual",
            "biennial": "biennial",
            "triennial": "triennial",
        },
        absent_value="not_disclosed",
    ),
}

# C2 prose-numeral probes: a quantity whose prose phrasing is unambiguous
# types its reserved row ``numeric_value_in_narrative_only`` — the number is
# visible in narrative and this producer refuses to extract it. The other
# table quantities have no single frozen prose phrase; they keep
# ``missing_dependency`` under the reserved-table limitation.
_PROSE_NUMERAL_PROBES = {
    "ceo_total_comp": r"total compensation of \$[\d,.]+",
    "comp_actually_paid_peo": r"compensation actually paid[^.;]{0,200}\$[\d,.]+",
}

NOT_SUPPLIED_REASON = "proxy_package_not_supplied"
NARRATIVE_ONLY_REASON = "numeric_value_in_narrative_only"
TABLE_EXTRACTION_RESERVED_LIMITATION = (
    "pk10.table_extraction_reserved: SCT and PvP tables are sources for a "
    "later lane; no numeric row is produced from prose"
)
NOT_SUPPLIED_LIMITATION = (
    "pk10.proxy_package_not_supplied: no DEF 14A package admitted for this "
    "entity; capture path owned by the D3 seam"
)
_CATALOGUE_REASON_CODES = frozenset(
    item["code"]
    for item in contract.load_pack_schema("PK10")["reason_codes"]
)


def _def_14a_present(pack_input: PackInput) -> bool:
    """B.1: applicability keys on a DEF 14A package being in the list."""
    return any(
        str(package.manifest.get("form") or "") == "DEF 14A"
        for package in pack_input.packages
    )


def _proxy_forms_seen(pack_input: Any, ledger: Any) -> tuple[str, ...]:
    """B.4 receipt: the proxy forms present in the package list, or ``none``."""
    forms = sorted(
        {
            str(package.manifest.get("form") or "")
            for package in pack_input.packages
            if str(package.manifest.get("form") or "") in SPEC.forms
        }
    )
    return (f"proxy_forms_seen={','.join(forms) if forms else 'none'}",)


def _produce_check(
    pack_input: Any,
    ledger: Any,
    outcomes: Mapping[str, Any],
    catalogue_check: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]] | None:
    """Own all four catalogue check rows: every operand is a reserved table
    quantity at this version, so each check abstains typed (R-K3) and never
    compares, splices or scrapes."""
    operands = list(catalogue_check.get("operands") or [])
    return (
        {
            "check_id": catalogue_check["check_id"],
            "kind": catalogue_check["kind"],
            "status": "not_evaluable",
            "operands": operands,
            "tolerance": None,
            "evidence_field_ids": operands,
            "reason": "missing_dependency",
        },
        (),
    )


def _not_supplied_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """Rewrite the framework's form-miss envelope to the frozen B.1/B.2
    not-supplied shape: applicability ``not_evaluable``, every field row and
    check typed with ``proxy_package_not_supplied``, coverage ``not_supplied``."""
    envelope["applicability"]["state"] = "not_evaluable"
    envelope["applicability"]["reason"] = NOT_SUPPLIED_REASON
    for row in envelope["fields"]:
        row["quality_state"] = "not_evaluable"
        row["non_value_state"] = "not_evaluable"
        row["coverage_state"] = "unmapped"
        row["reason"] = NOT_SUPPLIED_REASON
        row["value"] = None
        row["text_value"] = None
        row["source_span"] = None
    for check in envelope["checks"]:
        check["status"] = "not_evaluable"
        check["reason"] = NOT_SUPPLIED_REASON
    coverage = envelope["coverage"]
    for key in (
        "valued_fields",
        "missing_fields",
        "unsupported_fields",
        "not_applicable_fields",
    ):
        coverage[key] = 0
    coverage["not_evaluable_fields"] = len(envelope["fields"])
    coverage["disclosure_coverage_state"] = "not_supplied"
    envelope["limitations"] = list(
        dict.fromkeys((*envelope["limitations"], NOT_SUPPLIED_LIMITATION))
    )[:32]
    return envelope


def _supplied_envelope(
    envelope: dict[str, Any], pack_input: PackInput
) -> dict[str, Any]:
    """B.2 supplied case: type prose numerals, keep every reason a PK10
    catalogue code, and carry the reserved-table limitation."""
    primary, _matched = _select_primary(pack_input.packages, SPEC.forms)
    nt = narrative.primary_document_text(primary)
    by_field = {row["field_id"]: row for row in envelope["fields"]}
    for field_id, probe in _PROSE_NUMERAL_PROBES.items():
        row = by_field.get(field_id)
        if row is None or row["quality_state"] == "valued":
            continue
        if re.search(probe, nt.text, re.IGNORECASE):
            row["reason"] = NARRATIVE_ONLY_REASON
    # The framework's span-absence code (narrative_span_not_located) is not a
    # PK10 catalogue code; the closest frozen code is missing_dependency.
    for row in envelope["fields"]:
        if row["quality_state"] != "valued" and row.get("reason") not in (
            _CATALOGUE_REASON_CODES
        ):
            row["reason"] = "missing_dependency"
    for check in envelope["checks"]:
        if (
            check.get("status") in ("not_evaluable", "not_applicable")
            and check.get("reason") not in _CATALOGUE_REASON_CODES
        ):
            check["reason"] = "missing_dependency"
    envelope["limitations"] = list(
        dict.fromkeys((*envelope["limitations"], TABLE_EXTRACTION_RESERVED_LIMITATION))
    )[:32]
    return envelope


class Pk10Producer(PackProducer):
    """PK10 declaration plus the not-supplied / prose-numeral finalize hook."""

    def finalize_result(
        self, result: dict[str, Any], pack_input: PackInput
    ) -> dict[str, Any]:
        if _def_14a_present(pack_input):
            envelope = _supplied_envelope(result, pack_input)
        else:
            envelope = _not_supplied_envelope(result)
        envelope["pack_content_sha256"] = contract.pack_content_digest(envelope)
        errors = contract.validate_pack_result(envelope)
        if errors:
            raise SpecialistPackError(
                "PK10 finalize refused: " + "; ".join(errors[:5])
            )
        return envelope


PRODUCER = Pk10Producer(
    spec=SPEC,
    field_mappings=_FIELD_MAPPINGS,
    checks=(),
    hooks=NarrativeHooks(
        text_value_overrides={
            "say_on_pay_frequency": _say_on_pay_frequency_value,
        }
    ),
)

register_extra_receipts("PK10", _proxy_forms_seen)
register_extra_check("PK10", _produce_check)

__all__ = ["PRODUCER", "SPEC"]
