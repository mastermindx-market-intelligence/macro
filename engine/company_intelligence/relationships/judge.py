"""M2 judge bridge: packs, the quote->bytes map, and the materializer.

The harvester emits byte-exact candidate spans and judges nothing.  This module
is the bridge from candidates to contract-valid extraction rows:

``pack``        turns candidates into judge packs + a frozen judging guide;
judgments       (written by later lanes, one JSON record per candidate) name
                ONLY quotes, kinds and fact ids — never issuer ids, tickers,
                computed numbers or byte offsets;
``materialize`` maps quotes back to exact document bytes (K3), names to issuers
                through the A34 resolver, XBRL facts and narrative percents to
                magnitudes (K6/K7), and writes extraction rows, source excerpts
                and a ledger in which EVERY refusal is a named code and counted.

No network, no wall clock: EDGAR bytes are read only through
``edgar.EdgarCache(root).load`` and only when ``integrity_ok`` is True.
Nothing here scores, ranks, predicts or sizes anything.
"""
from __future__ import annotations

import hashlib
import html
import importlib
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from engine.company_intelligence.relationships import edgar as rel_edgar
from engine.company_intelligence.relationships import harvest as rel_harvest
from engine.company_intelligence.relationships import replay
from engine.company_intelligence.relationships import resolve as rel_resolve
from engine.company_intelligence.relationships.package_v2 import (
    SPECIES_ROLES,
    assessment_identity,
    canon,
    normalize_span,
    observation_identity,
    sha,
)

# --- record / pack / report schemas -------------------------------------------

JUDGMENT_SCHEMA_ID = "gmi_rel_m2.judgment/v1"
PACK_SCHEMA = "gmi_rel_m2.judge_pack/v1"
INDEX_SCHEMA = "gmi_rel_m2.judge_index/v1"
REPORT_SCHEMA = "gmi_rel_m2.materialize_report/v1"

EXTRACTION_SCHEMA = "company_intelligence.relationship_extraction/v1"
EXCERPT_SCHEMA = "company_intelligence.relationship_source_excerpt/v1"

#: The excerpt note materialize writes over the harvest note (the M1 wording,
#: verbatim — the reproduced M1 sources must stay byte-identical).
M1_EXCERPT_NOTE = (
    "Verbatim byte excerpt of a public SEC EDGAR filing for research "
    "provenance; the full document is identified by doc_sha256 and "
    "re-verifiable by replay. public_display: unknown (F03 A7)."
)

MAX_CONDITION_CHARS = 600
PER_PACK_DEFAULT = 25

HARVEST_NOTE_TEMPLATE = (
    "Verbatim byte excerpt of a public SEC EDGAR filing for research "
    "provenance; harvest candidate {candidate_id} (origin {origin}), not yet "
    "judged. public_display: unknown (F03 A7)."
)
#: Kept under its historical name for callers mirroring the harvester CLI.
EXCERPT_NOTE_TEMPLATE = HARVEST_NOTE_TEMPLATE

ROLES = (
    "supplier", "customer", "manufacturer", "client", "licensor", "licensee",
    "distributor", "provider", "dependent",
)
SPECIES = tuple(SPECIES_ROLES)
CHANNELS = ("direct", "distributor", "contract_manufacturer", "other")
RELATION_STATUSES = ("asserted", "terminated", "denied")
CONDITION_KINDS = (
    "contractual_term", "volume_commitment", "pricing", "exclusivity",
    "termination_right", "concentration_risk", "other",
)
MAGNITUDE_KINDS = (
    "seller_revenue_share", "buyer_procurement_share", "contract_value",
    "purchase_commitment",
)
NON_EDGE_REASONS = (
    "UNRESOLVED_COUNTERPARTY", "PRIVATE_COMPANY", "OUT_OF_CORE_MARKET",
    "CN_SECURITY_LEVEL_ONLY", "ANONYMOUS_ALIAS",
)
NO_RELATIONSHIP_REASONS = (
    "generic_risk_language", "no_counterparty_named",
    "not_a_commercial_relationship", "affiliate_or_subsidiary",
    "duplicate_of_other_candidate", "other",
)
ASSESSMENTS = ("restatement", "reassertion", "not_restated")


def _enum(values):
    return {"type": "string", "enum": list(values)}


#: K1 — the judgment record.  ``additionalProperties`` is false at every level.
#: Cross-field REQUIRED rules whose refusal must carry a named code (status
#: quote presence, product quote presence) are enforced by the materializer,
#: not here, so a violation is counted instead of merely unparseable.
JUDGMENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://mastermind-x.com/contracts/company_intelligence/gmi_rel_m2.judgment/v1",
    "title": "GMI REL M2 judgment record (v1)",
    "description": (
        "One judging-agent decision for one harvested candidate.  Names only "
        "quotes, kinds and fact ids: never issuer ids, tickers, computed "
        "numbers or byte offsets — code resolves the quotes against the "
        "candidate's document bytes."
    ),
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema", "candidate_id", "judge", "verdict", "no_relationship_reason",
        "relationships", "assessment",
    ],
    "properties": {
        "schema": {"const": JUDGMENT_SCHEMA_ID},
        "candidate_id": {"type": "string", "pattern": "^cand:[0-9a-f]{20}$"},
        "judge": {
            "type": "object",
            "additionalProperties": False,
            "required": ["agent", "lane_run_id"],
            "properties": {
                "agent": {"type": "string", "minLength": 1},
                "lane_run_id": {"type": ["string", "null"]},
            },
        },
        "verdict": _enum(["relationship", "no_relationship", "assessment",
                          "unclear"]),
        "no_relationship_reason": {
            "anyOf": [{"const": None}, _enum(NO_RELATIONSHIP_REASONS)],
        },
        "relationships": {"type": "array", "items": {"$ref": "#/$defs/rel"}},
        "assessment": {
            "anyOf": [{"const": None}, {"$ref": "#/$defs/assessment"}],
        },
    },
    "allOf": [
        {
            "if": {"properties": {"verdict": {"const": "relationship"}},
                   "required": ["verdict"]},
            "then": {"properties": {
                "relationships": {"minItems": 1},
                "assessment": {"const": None},
                "no_relationship_reason": {"const": None},
            }},
        },
        {
            "if": {"properties": {"verdict": {"const": "assessment"}},
                   "required": ["verdict"]},
            "then": {"properties": {
                "relationships": {"maxItems": 0},
                "assessment": {"type": "object"},
                "no_relationship_reason": {"const": None},
            }},
        },
        {
            "if": {"properties": {"verdict": {"const": "no_relationship"}},
                   "required": ["verdict"]},
            "then": {"properties": {
                "relationships": {"maxItems": 0},
                "assessment": {"const": None},
                "no_relationship_reason": _enum(NO_RELATIONSHIP_REASONS),
            }},
        },
        {
            "if": {"properties": {"verdict": {"const": "unclear"}},
                   "required": ["verdict"]},
            "then": {"properties": {
                "relationships": {"maxItems": 0},
                "assessment": {"const": None},
                "no_relationship_reason": {"const": None},
            }},
        },
    ],
    "$defs": {
        "role": _enum(ROLES),
        "species": _enum(SPECIES),
        "channel": _enum(CHANNELS),
        "condition_kind": _enum(CONDITION_KINDS),
        "magnitude_kind": _enum(MAGNITUDE_KINDS),
        "occurrence": {"type": "integer", "minimum": 1},
        "scope_text": {"type": ["string", "null"]},
        "scopes": {
            "type": "string", "minLength": 1, "maxLength": 240,
            "description": "judge-written free text naming the two quantities",
        },
        "rel": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "species", "subject_role", "relation_status", "status_quote",
                "object", "channel", "scope", "conditions", "magnitudes",
            ],
            "properties": {
                "species": {"$ref": "#/$defs/species"},
                "subject_role": {"anyOf": [{"const": None},
                                           {"$ref": "#/$defs/role"}]},
                "relation_status": _enum(RELATION_STATUSES),
                "status_quote": {"type": ["string", "null"]},
                "object": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["quote", "kind"],
                    "properties": {
                        "quote": {"type": "string"},
                        "kind": _enum(["named", "anonymous_alias"]),
                        "occurrence": {"$ref": "#/$defs/occurrence"},
                    },
                },
                "channel": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/channel"},
                    "uniqueItems": True,
                },
                "scope": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["product_key", "product_quote",
                                 "segment_quote", "geography_quote"],
                    "properties": {
                        "product_key": {
                            "type": "string",
                            "pattern": "(^all$|^[a-z0-9]+(_[a-z0-9]+)*$)",
                        },
                        "product_quote": {"$ref": "#/$defs/scope_text"},
                        "segment_quote": {"$ref": "#/$defs/scope_text"},
                        "geography_quote": {"$ref": "#/$defs/scope_text"},
                    },
                },
                "conditions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["kind", "quote"],
                        "properties": {
                            "kind": {"$ref": "#/$defs/condition_kind"},
                            "quote": {"type": "string"},
                            "occurrence": {"$ref": "#/$defs/occurrence"},
                        },
                    },
                },
                "magnitudes": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"$ref": "#/$defs/xbrl_magnitude"},
                            {"$ref": "#/$defs/narrative_magnitude"},
                        ]
                    },
                },
            },
        },
        "xbrl_magnitude": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "xbrl_fact_ids", "numerator_scope",
                         "denominator_scope"],
            "properties": {
                "kind": {"$ref": "#/$defs/magnitude_kind"},
                "xbrl_fact_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "numerator_scope": {"$ref": "#/$defs/scopes"},
                "denominator_scope": {"$ref": "#/$defs/scopes"},
            },
        },
        "narrative_magnitude": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "quote", "period", "numerator_scope",
                         "denominator_scope"],
            "properties": {
                "kind": {"$ref": "#/$defs/magnitude_kind"},
                "quote": {"type": "string"},
                "period": {"const": "current"},
                "occurrence": {"$ref": "#/$defs/occurrence"},
                "numerator_scope": {"$ref": "#/$defs/scopes"},
                "denominator_scope": {"$ref": "#/$defs/scopes"},
            },
        },
        "assessment": {
            "type": "object",
            "additionalProperties": False,
            "required": ["assessment", "reason", "reason_quote"],
            "properties": {
                "assessment": _enum(ASSESSMENTS),
                "reason": {"type": "string", "pattern": "^[a-z0-9_]{3,60}$"},
                "reason_quote": {"type": "string"},
                "occurrence": {"$ref": "#/$defs/occurrence"},
            },
        },
    },
}


def validate_judgment(record) -> list:
    """[] when the record validates against JUDGMENT_SCHEMA, else [message]."""
    import jsonschema

    try:
        jsonschema.validators.validator_for(JUDGMENT_SCHEMA)(
            JUDGMENT_SCHEMA
        ).validate(record)
    except jsonschema.ValidationError as error:
        return [error.message]
    return []


# --- K1b: the frozen judging guide ---------------------------------------------

JUDGING_GUIDE = """# GMI REL M2 judging guide (gmi_rel_m2.judgment/v1)

You judge one candidate at a time from a judge pack.  Read only the pack's
`text` and this guide.  Write one JSON judgment per line, in the pack's
candidate order.  Every quote you write must be an EXACT substring of the pack
`text` — code maps it back to the document's exact bytes and refuses it
otherwise.  Never guess; when the text alone cannot decide, answer `unclear`.

G1 — A relationship needs a NAMED counterparty (or a defined alias such as
"Customer A") in one of the five species: supplier_customer,
contract_manufacturing, licensing, distribution, component_dependency.
Generic dependence is not a relationship: "we depend on a limited number of
customers" is verdict no_relationship with reason
generic_risk_language or no_counterparty_named.  Example: "certain of our
customers account for a significant portion of revenue" -> no_relationship /
no_counterparty_named.

G2 — Species and subject_role are read from the filer's side of the sentence.
The filer sells to X -> species supplier_customer with the default subject_role
supplier (omit the key).  The filer buys from X -> supplier_customer with
subject_role customer.  X manufactures for the filer (foundry, contract
manufacturer, OSAT) -> contract_manufacturing with subject_role client.  The
filer manufactures for X -> contract_manufacturing, default subject_role
manufacturer (omit).  Licensing -> licensing.  Distribution -> distribution.
The filer depends on X's component/platform/service -> component_dependency
with subject_role dependent; the default provider role means the filer
provides.  Example: "we purchase wafers from TSMC" -> supplier_customer /
subject_role customer.

G3 — relation_status is "asserted" unless the text says the relationship ended
(terminated) or explicitly denies one (denied).  When it is not asserted,
status_quote must hold the exact words that say so.  Example: "Agreement,
which was terminated in March" -> terminated + that quote.

G4 — Every quote is an EXACT substring of the pack `text`, same spacing and
punctuation.  Quote at least 2 characters.  When the substring appears more
than once in the text, give the 1-based "occurrence" of the intended one.
Example: if "Apple" appears three times, quote the sentence containing the
naming you mean, or set occurrence.

G5 — Never write issuer ids, tickers, CIKs, numbers you computed, or byte
offsets anywhere in the judgment.  The object quote is the name exactly as
written: "Apple", "Taiwan Semiconductor Manufacturing Company Limited".  Code
resolves the name to an issuer.  Example: write "Samsung Electronics", never
"005930.KS" or "ISS:KR-XKRX-005930".

G6 — channel records only what the text states: "distributors",
"contract manufacturers", "direct".  Order kept as written; empty array when
the text states no channel.  Example: "through sales to multiple distributors,
contract manufacturers, and direct sales" -> ["distributor",
"contract_manufacturer", "direct"].

G7 — When the candidate lists XBRL facts that state the share, cite them by
fact_id (kind seller_revenue_share or buyer_procurement_share as derived from
the benchmark member); use a narrative percent quote only when no xbrl fact
carries the share.  Example: xbrl [{"fact_id": "f-977", ...}] -> magnitudes
[{"kind": "seller_revenue_share", "xbrl_fact_ids": ["f-977"], ...}].

G8 — conditions: quote the clause that states a term, volume commitment,
pricing, exclusivity, termination right or concentration risk, and classify it
with the matching condition kind.  Example: "under a take-or-pay arrangement"
-> kind pricing (or contractual_term when it is a plain term).

G9 — One relationship entry per (species, counterparty) per candidate.  Repeat
a counterparty only under a different species.  Example: Apple as a customer is
ONE supplier_customer entry even if the paragraph names Apple twice; a second
entry only if Apple is also, say, a licensee.

G10 — Candidates with origin "amendment_note" are judged as verdict
"assessment": restatement when the amendment amends the financial statements
or relationship facts, reassertion when it merely repeats them, not_restated
when it does not touch them (e.g. a Part III-only amendment).  reason_quote is
the sentence that says so, reason a short snake_case slug.  Example: "filed
solely to provide Part III information" -> not_restated /
part_iii_only_amendment.

G11 — Answer "unclear" whenever the text alone cannot decide.  A parent,
subsidiary or affiliate is NOT a counterparty relationship: verdict
no_relationship / affiliate_or_subsidiary.  A government or agency
counterparty is quoted as written (it resolves to UNRESOLVED_COUNTERPARTY by
design).  Bare ambiguous names — hp, ge, general electric, arm — are quoted
exactly as written; the resolver refuses to guess them, so never expand them.
Example: "sales to HP represented 3% of revenue" -> object quote "HP", the
resolver keeps it unresolved rather than guessing an issuer.
"""


# --- counters + refusals -------------------------------------------------------

COUNTER_KEYS = (
    "subject_name_from_sec_name",
    "duplicate_span_bytes",
    "sources_reused",
    "sources_written",
    "excerpt_self_check_failed",
)


def new_counters() -> dict:
    return {key: 0 for key in COUNTER_KEYS}


class SpanMapError(ValueError):
    """The candidate span's raw bytes cannot be mapped honestly (K3)."""


class QuoteError(ValueError):
    """A judged quote cannot be mapped to exactly one byte span (K3)."""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


class Refused(Exception):
    """One relationship entry (or the whole candidate) is refused; code named."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# --- K3: the quote -> bytes map -------------------------------------------------

_TAG_RE = re.compile(rb"<[^>]+>")
#: The html charref form mapped byte-exactly (K3): numeric with or without the
#: semicolon, hex, or a named ref without whitespace, <, &, # or ; inside.
_CHARREF_RE = re.compile(
    r"&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)"
)
_WS_RE = re.compile(r"\s+")


class SpanMap:
    """The normalized text of one span plus each char's raw byte range."""

    __slots__ = ("text", "ranges", "byte_start", "raw")

    def __init__(self, text: str, ranges, byte_start: int, raw: bytes):
        self.text = text
        self.ranges = ranges  # per char of `text`: (raw_start, raw_end) in `raw`
        self.byte_start = byte_start  # the span's doc offset
        self.raw = raw

    def doc_offsets(self, raw_start: int, raw_end: int) -> tuple:
        return self.byte_start + raw_start, self.byte_start + raw_end

    def __iter__(self):
        """(text, ranges) — the K3 pair form used by direct callers."""
        return iter((self.text, self.ranges))


def span_map(raw: bytes, byte_start: int = 0) -> SpanMap:
    """Build the per-character map from span.raw to normalize_span(raw) (K3).

    Tags are removed; surviving byte runs are decoded and their charrefs
    unescaped with each produced char mapped to the match's whole byte range;
    whitespace runs collapse to one space mapped to the run's first char; the
    result is stripped.  The string MUST equal ``normalize_span(raw)`` — any
    disagreement raises :class:`SpanMapError` and the candidate is refused,
    never silently patched.
    """
    pieces: list = []  # (char, raw_start, raw_end)

    def emit_plain(segment: bytes, base: int) -> None:
        try:
            text = segment.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SpanMapError("span raw is not utf-8") from error
        cursor = base
        pos = 0
        for match in _CHARREF_RE.finditer(text):
            prefix = text[pos:match.start()]
            if prefix:
                _emit_chars(prefix, cursor, pieces)
                cursor += len(prefix.encode("utf-8"))
            mbs = cursor
            mbe = mbs + len(match.group(0).encode("utf-8"))
            for char in html.unescape(match.group(0)):
                pieces.append((char, mbs, mbe))
            cursor = mbe
            pos = match.end()
        if pos < len(text):
            _emit_chars(text[pos:], cursor, pieces)

    pos = 0
    for tag in _TAG_RE.finditer(raw):
        if tag.start() > pos:
            emit_plain(raw[pos:tag.start()], pos)
        pos = tag.end()
    if pos < len(raw):
        emit_plain(raw[pos:], pos)

    inter = "".join(piece[0] for piece in pieces)
    chars: list = []
    ranges: list = []
    scan = 0
    for run in _WS_RE.finditer(inter):
        if run.start() > scan:
            _append(chars, ranges, pieces, scan, run.start())
        chars.append(" ")
        ranges.append(pieces[run.start()][1:])
        scan = run.end()
    if scan < len(inter):
        _append(chars, ranges, pieces, scan, len(inter))

    text = "".join(chars)
    lead = len(text) - len(text.lstrip())
    trail = len(text.rstrip())
    text = text[lead:trail]
    ranges = ranges[lead:trail]
    expected = normalize_span(raw)
    if text != expected:
        raise SpanMapError(
            "mapped span does not equal normalize_span(raw): "
            f"{text[:60]!r} != {expected[:60]!r}"
        )
    return SpanMap(text, ranges, byte_start, raw)


def _emit_chars(text: str, base: int, pieces: list) -> None:
    cursor = base
    for char in text:
        width = len(char.encode("utf-8"))
        pieces.append((char, cursor, cursor + width))
        cursor += width


def _append(chars: list, ranges: list, pieces: list, start: int, end: int) -> None:
    for index in range(start, end):
        chars.append(pieces[index][0])
        ranges.append(pieces[index][1:])


def find_quote(span: SpanMap, quote, occurrence=None):
    """Locate one judged quote in the mapped span (K3).

    Returns ``(normalized_quote, raw_start, raw_end, occurrence_count)`` where
    the raw offsets are into ``span.raw``.  Raises :class:`QuoteError` with the
    named code for every refusal: QUOTE_TOO_SHORT, QUOTE_NOT_FOUND,
    QUOTE_AMBIGUOUS.
    """
    if not isinstance(span, SpanMap):
        text, ranges = span
        span = SpanMap(text, ranges, 0, b"")
    if not isinstance(quote, str):
        raise QuoteError("QUOTE_NOT_FOUND", "quote is not a string")
    try:
        normalized = normalize_span(quote.encode("utf-8"))
    except UnicodeDecodeError:
        raise QuoteError("QUOTE_NOT_FOUND", "quote is not utf-8") from None
    if len(normalized) < 2:
        raise QuoteError("QUOTE_TOO_SHORT", f"quote too short: {quote!r}")
    count = 0
    hit = -1
    positions: list = []
    pos = 0
    while True:
        index = span.text.find(normalized, pos)
        if index < 0:
            break
        count += 1
        positions.append(index)
        pos = index + 1
    if occurrence is None:
        if count == 0:
            raise QuoteError("QUOTE_NOT_FOUND", f"quote not found: {quote!r}")
        if count > 1:
            raise QuoteError(
                "QUOTE_AMBIGUOUS", f"quote appears {count} times: {quote!r}"
            )
        index = positions[0]
    else:
        if not isinstance(occurrence, int) or occurrence < 1 or occurrence > count:
            raise QuoteError(
                "QUOTE_NOT_FOUND",
                f"occurrence {occurrence} of {count}: {quote!r}",
            )
        index = positions[occurrence - 1]
    raw_start = span.ranges[index][0]
    raw_end = span.ranges[index + len(normalized) - 1][1]
    return normalized, raw_start, raw_end, count


# --- K6 helpers: facts -> values, periods, kinds --------------------------------


def fact_value(fact):
    """float value of one harvested fact, or None when unparseable (K6)."""
    raw = (fact.get("raw_value") or "").replace(",", "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw).scaleb(int(fact.get("scale") or 0))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if fact.get("sign") == "-":
        value = -value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fact_period(fact):
    """{start, end, label} for one fact's period, or None when absent (K6)."""
    period = fact.get("period") or {}
    instant = period.get("instant")
    if instant:
        return {"start": None, "end": instant, "label": f"as of {instant}"}
    start, end = period.get("start"), period.get("end")
    if not end:
        return None
    if start:
        try:
            days = (date.fromisoformat(end) - date.fromisoformat(start)).days
        except ValueError:
            return None
        if 330 <= days <= 380:
            return {"start": start, "end": end, "label": f"FY{end[:4]}"}
        return {"start": start, "end": end, "label": f"{start}/{end}"}
    return {"start": None, "end": end, "label": f"as of {end}"}


BENCHMARK_AXIS_SUFFIX = "ConcentrationRiskByBenchmarkAxis"


def benchmark_member(fact):
    """The us-gaap:ConcentrationRiskByBenchmarkAxis member, or None."""
    for member in fact.get("members") or []:
        dimension = member.get("dimension") or ""
        if dimension.endswith(BENCHMARK_AXIS_SUFFIX):
            return member.get("member")
    return None


def derived_kind(member) -> str | None:
    """seller_revenue_share / buyer_procurement_share from the member local
    name (after the colon), else None (MAGNITUDE_BENCHMARK_UNSUPPORTED)."""
    if not isinstance(member, str):
        return None
    local = member.split(":")[-1].lower()
    if ("revenue" in local or "sales" in local) and "cost" not in local:
        return "seller_revenue_share"
    if "costof" in local or "purchase" in local or "procurement" in local:
        return "buyer_procurement_share"
    return None


# --- K7 helpers: narrative percents and dollar amounts ---------------------------

_PERCENT_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:%|percent)", re.I)
_DOLLAR_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)(?:\s*(thousand|million|billion))?", re.I
)
_RANGE_JOIN_RE = re.compile(r"\b(?:and|to)\b", re.I)
_PRECISION_LOWER = ("more than", "over", "at least", "in excess of",
                    "greater than")
_PRECISION_UPPER = ("less than", "under", "below", "up to", "nearly", "almost")
_PRECISION_EXACT = ("approximately", "about", "roughly", "none")
_UNIT_MULTIPLIERS = {"thousand": 10 ** 3, "million": 10 ** 6,
                     "billion": 10 ** 9}


def _precision_before(text: str, number_start: int) -> str:
    """The nearest precision word preceding the number; none -> exact (K7)."""
    head = text[:number_start].lower()
    best_kind, best_at = "exact", -1
    for phrases, kind in (
        (_PRECISION_LOWER, "lower_bound"),
        (_PRECISION_UPPER, "upper_bound"),
        (_PRECISION_EXACT, "exact"),
    ):
        for phrase in phrases:
            index = head.rfind(phrase)
            if index > best_at:
                best_kind, best_at = kind, index
    return best_kind


def _number_value(digits: str, unit_word) -> float:
    value = Decimal(digits.replace(",", ""))
    if unit_word:
        value *= _UNIT_MULTIPLIERS[str(unit_word).lower()]
    return float(value)


def parse_narrative_amount(text: str):
    """(unit, value, value_high, precision) or a refusal code string (K7).

    Exactly one number -> its precision word; two numbers joined by
    "between ... and" / "to" -> precision range with value + value_high;
    anything else is MAGNITUDE_PARSE_AMBIGUOUS.
    """
    percents = list(_PERCENT_RE.finditer(text))
    dollars = list(_DOLLAR_RE.finditer(text))
    if percents and dollars:
        return "MAGNITUDE_PARSE_AMBIGUOUS", None, None, None
    matches = percents or dollars
    if not matches or len(matches) > 2:
        return "MAGNITUDE_PARSE_AMBIGUOUS", None, None, None
    if dollars:
        unit = "USD"
    else:
        unit = "ratio"

    def value_of(match):
        value = _number_value(match.group(1),
                              match.group(2) if dollars else None)
        return value if dollars else value / 100

    if len(matches) == 1:
        match = matches[0]
        return (
            unit,
            value_of(match),
            None,
            _precision_before(text, match.start()),
        )
    first, second = matches
    if not _RANGE_JOIN_RE.search(text[first.end():second.start()]):
        return "MAGNITUDE_PARSE_AMBIGUOUS", None, None, None
    return unit, value_of(first), value_of(second), "range"


# --- K5: the subject -------------------------------------------------------------

_DEI_NAME_OPEN_RE = re.compile(
    rb"<ix:nonNumeric\b[^>]*\bname\s*=\s*(\"[^\"]*\"|'[^']*')[^>]*>", re.I
)
_DEI_NAME_CLOSE_RE = re.compile(rb"</ix:nonNumeric\s*>", re.I)
_REGISTRANT_NAME = "dei:EntityRegistrantName"


def dei_registrant_name(body: bytes):
    """normalize_span of the inner bytes of the FIRST registrant-name element,
    or None when the document carries none."""
    for opening in _DEI_NAME_OPEN_RE.finditer(body):
        attribute = opening.group(1)[1:-1].decode("utf-8").strip()
        if attribute != _REGISTRANT_NAME:
            continue
        closing = _DEI_NAME_CLOSE_RE.search(body, opening.end())
        if closing is None:
            return None
        try:
            return normalize_span(body[opening.end():closing.start()])
        except UnicodeDecodeError:
            return None
    return None


def census_filing(census_entry: dict, accession: str):
    """The census filing record whose accessionNumber matches, or None."""
    for role in ("latest", "prior"):
        filing = (census_entry or {}).get(role)
        if isinstance(filing, dict) and filing.get("accessionNumber") == accession:
            return filing
    for role in ("amendments_of_latest", "amendments_of_prior"):
        for filing in (census_entry or {}).get(role) or []:
            if filing.get("accessionNumber") == accession:
                return filing
    return None


def subject_identity(cand: dict, census_entry, cache, issuers):
    """(subject, refusal_code, counter) for one candidate (K5).

    ``subject`` is the extraction row's subject object.  ``refusal_code`` is
    SUBJECT_NOT_IN_MANIFEST when the issuer is not in the universe manifest
    (the candidate is refused whole).  ``counter`` is
    subject_name_from_sec_name when the DEI registrant name was unavailable
    and the census sec_name was used.
    """
    issuer_id = cand["issuer_id"]
    if issuer_id not in (issuers or {}):
        return None, "SUBJECT_NOT_IN_MANIFEST", None
    subject = {
        "cik": cand["cik"],
        "issuer_id": issuer_id,
        "name_as_filed": None,
        "security_ids": list(issuers[issuer_id]),
    }
    name = None
    filing = census_filing(census_entry or {}, cand["accession"])
    if filing is not None and filing.get("primaryDocument") and cache is not None:
        body, _meta, integrity_ok = cache.load(
            int(cand["cik"]),
            cand["accession"].replace("-", ""),
            filing["primaryDocument"],
        )
        if body is not None and integrity_ok:
            name = dei_registrant_name(body)
    counter = None
    if name is None:
        name = (census_entry or {}).get("sec_name") or cand.get("sec_name")
        counter = "subject_name_from_sec_name"
    subject["name_as_filed"] = name
    return subject, None, counter


# --- K2: packs --------------------------------------------------------------------


def pack_sort_key(cand: dict) -> tuple:
    span = cand["excerpt"]["span"]
    return (
        cand["issuer_id"],
        cand["accession"],
        cand["primary_document"],
        span["byte_start"],
        span["byte_end"],
        cand["candidate_id"],
    )


def pack_candidate_view(cand: dict) -> dict:
    """The projection a judging agent sees: names the pack text, not the bytes."""
    xbrl = []
    for fact in cand.get("xbrl_facts") or []:
        xbrl.append(
            {
                "fact_id": fact.get("fact_id"),
                "concept": fact.get("concept"),
                "benchmark_member": benchmark_member(fact),
                "members": {
                    member.get("dimension"): member.get("member")
                    for member in fact.get("members") or []
                },
                "value": fact_value(fact),
                "period_label": (fact_period(fact) or {}).get("label"),
            }
        )
    return {
        "candidate_id": cand["candidate_id"],
        "issuer_id": cand["issuer_id"],
        "filer_name": cand.get("sec_name"),
        "form": cand["form"],
        "filing_role": cand["filing_role"],
        "origin": cand["origin"],
        "rank": cand["rank"],
        "cues": cand.get("cues") or [],
        "hints": cand.get("hints") or [],
        "period_of_report": cand.get("period_of_report"),
        "text": cand["excerpt"]["span"]["normalized"],
        "xbrl": xbrl,
    }


def build_packs(cands: list, leaf: str, dirname: str,
                per_pack: int = PER_PACK_DEFAULT):
    """(pack_documents, index_document) per K2 — candidates sorted and split."""
    ordered = sorted(cands, key=pack_sort_key)
    packs = []
    for number in range(0, len(ordered), max(1, per_pack)):
        group = ordered[number:number + max(1, per_pack)]
        packs.append(
            {
                "schema": PACK_SCHEMA,
                "leaf": leaf,
                "dirname": dirname,
                "pack": len(packs) + 1,
                "candidates": [pack_candidate_view(cand) for cand in group],
            }
        )
    index = {
        "schema": INDEX_SCHEMA,
        "candidates_sha256": None,  # set by the CLI over the file bytes
        "packs": [
            {
                "pack": pack["pack"],
                "file": f"pack_{pack['pack']:03d}.json",
                "candidate_ids": [c["candidate_id"] for c in pack["candidates"]],
            }
            for pack in packs
        ],
        "judgments_dir": "judgments",
    }
    return packs, index


def canonical_json_bytes(value) -> bytes:
    return (
        json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def canonical_jsonl(value) -> bytes:
    return (canon(value) + "\n").encode("utf-8")


# --- K4 bridge: the resolver ------------------------------------------------------


def resolve_object(entry_object: dict, span: SpanMap, subject_issuer_id: str,
                   aliases, resolver_rows, manifest_issuers):
    """(object_party, note, normalized_quote) or raises Refused (K4)."""
    quote = (entry_object or {}).get("quote")
    kind = (entry_object or {}).get("kind", "named")
    normalized, _raw_start, _raw_end, _count = find_quote(
        span, quote, (entry_object or {}).get("occurrence")
    )
    resolution = rel_resolve.resolve_counterparty(
        normalized,
        kind=kind,
        subject_issuer_id=subject_issuer_id,
        aliases=aliases,
        resolver_rows=resolver_rows,
        manifest_issuers=manifest_issuers,
    )
    if resolution["refusal"]:
        raise Refused(resolution["refusal"])
    object_party = {
        "issuer_id": resolution["issuer_id"],
        "name_as_filed": resolution["name_as_filed"],
        "anonymous_alias": resolution["anonymous_alias"],
        "non_edge_reason": resolution["non_edge_reason"],
    }
    return object_party, resolution["note"], normalized


# --- K6/K7: magnitudes ------------------------------------------------------------


def _cited_facts(cand: dict, fact_ids) -> list:
    """Validated candidate facts for the cited ids, in fact_byte_start order."""
    facts_by_id = {}
    for fact in cand.get("xbrl_facts") or []:
        fact_id = fact.get("fact_id")
        if isinstance(fact_id, str) and fact_id and fact_id not in facts_by_id:
            facts_by_id[fact_id] = fact
    if not isinstance(fact_ids, list) or not fact_ids:
        raise Refused("FACT_NOT_IN_CANDIDATE")
    validated = []
    for fact_id in fact_ids:
        if not isinstance(fact_id, str) or not fact_id.strip():
            raise Refused("FACT_ID_NULL")
        fact = facts_by_id.get(fact_id)
        if fact is None:
            raise Refused("FACT_NOT_IN_CANDIDATE")
        if fact not in validated:
            validated.append(fact)
    validated.sort(
        key=lambda f: (
            f.get("fact_byte_start")
            if f.get("fact_byte_start") is not None
            else 0
        )
    )
    return validated


def _xbrl_source_fact(fact: dict) -> dict:
    decimals = fact.get("decimals")
    return {
        "concept": fact.get("concept"),
        "context_ref": fact.get("context_ref"),
        "decimals": None if decimals == "INF" else (
            int(decimals) if decimals is not None else None
        ),
        "fact_id": fact.get("fact_id"),
        "members": {
            member.get("dimension"): member.get("member")
            for member in fact.get("members") or []
        },
        "raw_value": fact.get("raw_value"),
        "scale": int(fact.get("scale") or 0),
    }


def map_xbrl_magnitude(cand: dict, magnitude: dict, species: str,
                       effective_role) -> list:
    """Row magnitudes for one judged xbrl magnitude (K6), in fact order."""
    facts = _cited_facts(cand, magnitude.get("xbrl_fact_ids"))
    from_role, to_role = SPECIES_ROLES[species][0], SPECIES_ROLES[species][1]
    for fact in facts:
        kind = derived_kind(benchmark_member(fact))
        if kind is None:
            raise Refused("MAGNITUDE_BENCHMARK_UNSUPPORTED")
        if kind != magnitude.get("kind"):
            raise Refused("MAGNITUDE_BENCHMARK_MISMATCH")
    if magnitude.get("kind") == "seller_revenue_share" and (
        effective_role != from_role
    ):
        raise Refused("MAGNITUDE_ROLE_MISMATCH")
    if magnitude.get("kind") == "buyer_procurement_share" and (
        effective_role != to_role
    ):
        raise Refused("MAGNITUDE_ROLE_MISMATCH")
    magnitudes = []
    for fact in facts:
        value = fact_value(fact)
        if value is None:
            raise Refused("FACT_VALUE_UNPARSEABLE")
        period = fact_period(fact)
        if period is None:
            raise Refused("FACT_PERIOD_MISSING")
        magnitudes.append(
            {
                "kind": magnitude["kind"],
                "value": value,
                "unit": "ratio",
                "precision": "exact",
                "period": period,
                "numerator_scope": magnitude["numerator_scope"],
                "denominator_scope": magnitude["denominator_scope"],
                "xbrl_fact_id": fact["fact_id"],
            }
        )
    return magnitudes, [_xbrl_source_fact(fact) for fact in facts]


def map_narrative_magnitude(cand: dict, magnitude: dict, span: SpanMap):
    """(row_magnitude, normalized_quote) for one judged narrative magnitude."""
    kind = magnitude.get("kind")
    if kind in ("seller_revenue_share", "buyer_procurement_share") and cand.get(
        "xbrl_facts"
    ):
        raise Refused("MAGNITUDE_XBRL_AVAILABLE")
    normalized, _raw_start, _raw_end, _count = find_quote(
        span, magnitude.get("quote"), magnitude.get("occurrence")
    )
    parsed = parse_narrative_amount(normalized)
    unit, value, value_high, precision = parsed
    if unit == "MAGNITUDE_PARSE_AMBIGUOUS":
        raise Refused("MAGNITUDE_PARSE_AMBIGUOUS")
    if unit == "USD" and kind not in ("contract_value", "purchase_commitment"):
        raise Refused("MAGNITUDE_UNIT_KIND_MISMATCH")
    if unit == "ratio" and kind in ("contract_value", "purchase_commitment"):
        raise Refused("MAGNITUDE_UNIT_KIND_MISMATCH")
    if kind == "seller_revenue_share" and not re.search(
        r"revenue|sales", normalized, re.I
    ):
        raise Refused("MAGNITUDE_KIND_WORDING")
    if kind == "buyer_procurement_share" and not re.search(
        r"purchas|procure|cost of", normalized, re.I
    ):
        raise Refused("MAGNITUDE_KIND_WORDING")
    period_of_report = cand.get("period_of_report")
    row_magnitude = {
        "kind": kind,
        "value": value,
        "unit": unit,
        "precision": precision,
        "period": {
            "start": None,
            "end": period_of_report,
            "label": f"FY{str(period_of_report)[:4]}",
        },
        "numerator_scope": magnitude["numerator_scope"],
        "denominator_scope": magnitude["denominator_scope"],
        "xbrl_fact_id": None,
    }
    if precision == "range":
        row_magnitude["value_high"] = value_high
    return row_magnitude, normalized


# --- K8/K9: the candidate mapper ---------------------------------------------------


def _dedupe_facts(source_facts: list) -> list:
    """Cited facts deduped by fact_id, kept in (byte) order already applied."""
    seen = set()
    ordered = []
    for fact in source_facts:
        if fact["fact_id"] in seen:
            continue
        seen.add(fact["fact_id"])
        ordered.append(fact)
    return ordered


class CandidateMapper:
    """Maps judged entries of one candidate to extraction rows (K3-K9).

    Every refusal is a named code; a code refuses ONLY its own relationship
    entry — other entries of the same candidate still materialize.
    """

    def __init__(self, *, issuers, aliases, resolver_rows, census, cache,
                 counters, ledger_index=None):
        self.issuers = issuers or {}
        self.aliases = aliases or []
        self.resolver_rows = resolver_rows or []
        self.census = census or {}
        self.cache = cache
        self.counters = counters if counters is not None else new_counters()
        self.ledger_index = ledger_index if ledger_index is not None else {}
        self.unresolved_names: Counter = Counter()
        self._seen_observation_ids: set = set()
        self._producer = None

    def _validate_row(self, row: dict) -> list:
        if self._producer is None:
            self._producer = importlib.import_module(
                "scripts.build_relationship_observations"
            )
        return self._producer._validate_row(
            row, self._producer._extraction_validator()
        )

    def span(self, cand: dict) -> SpanMap:
        span = cand["excerpt"]["span"]
        return span_map(span["raw"].encode("utf-8"), span["byte_start"])

    def ingested_at(self, cand: dict):
        return self.ledger_index.get(
            (cand["accession"], cand["primary_document"])
        )

    def unresolved_entry(self, object_party: dict, normalized_quote: str) -> None:
        if (
            object_party.get("issuer_id") is None
            and object_party.get("non_edge_reason") == "UNRESOLVED_COUNTERPARTY"
        ):
            self.unresolved_names[normalized_quote] += 1

    def map(self, cand: dict, judgment: dict) -> dict:
        codes: list = []
        notes: list = []
        self._entry_notes = notes
        rows: list = []
        observation_ids: list = []
        assessment_id = None
        verdict = judgment.get("verdict")
        try:
            span = self.span(cand)
        except SpanMapError:
            span = None
            codes.append("SPAN_MAP_MISMATCH")

        if verdict == "relationship":
            entries = judgment.get("relationships") or []
            subject = None
            subject_code = None
            if entries and span is not None:
                subject, subject_code, counter = subject_identity(
                    cand,
                    (self.census.get("issuers") or {}).get(cand["issuer_id"]),
                    self.cache,
                    self.issuers,
                )
                if counter:
                    self.counters[counter] = self.counters.get(counter, 0) + 1
            for entry in entries:
                if span is None:
                    codes.append("SPAN_MAP_MISMATCH")
                    continue
                if subject_code:
                    codes.append(subject_code)
                    continue
                try:
                    row = self._observation_row(cand, judgment, entry, span,
                                                subject)
                except (Refused, QuoteError) as refusal:
                    codes.append(getattr(refusal, "code", None) or str(refusal))
                    continue
                rows.append(row)
                observation_ids.append(row["observation_id"])
        elif verdict == "assessment":
            if span is None:
                codes.append("SPAN_MAP_MISMATCH")
            else:
                try:
                    row = self._assessment_row(cand, judgment, span)
                except (Refused, QuoteError) as refusal:
                    codes.append(getattr(refusal, "code", None) or str(refusal))
                else:
                    rows.append(row)
                    assessment_id = row["assessment_id"]

        if rows:
            outcome = "admitted"
        elif verdict == "no_relationship" and not codes:
            outcome = "no_relationship"
        elif verdict == "unclear" and not codes:
            outcome = "unclear"
        else:
            outcome = "refused"
        return {
            "rows": rows,
            "codes": codes,
            "notes": notes,
            "observation_ids": observation_ids,
            "assessment_id": assessment_id,
            "outcome": outcome,
        }

    # -- one relationship entry -> one observation row (K8) ---------------------

    def _observation_row(self, cand, judgment, entry, span, subject):
        species = entry.get("species")
        if species not in SPECIES_ROLES:
            raise Refused("ROLE_NOT_IN_SPECIES")
        from_role, to_role, default_role = SPECIES_ROLES[species][:3]
        subject_role = entry.get("subject_role")
        if subject_role is not None and subject_role not in (from_role, to_role):
            raise Refused("ROLE_NOT_IN_SPECIES")
        effective_role = subject_role or default_role

        object_party, note, normalized_object = resolve_object(
            entry.get("object"),
            span,
            cand["issuer_id"],
            self.aliases,
            self.resolver_rows,
            self.issuers,
        )
        if note:
            self._entry_notes.append(note)
        self.unresolved_entry(object_party, normalized_object)

        relation_status = entry.get("relation_status")
        status_quote = entry.get("status_quote")
        if relation_status != "asserted" and not status_quote:
            raise Refused("STATUS_QUOTE_MISSING")
        if status_quote:
            try:
                find_quote(span, status_quote)
            except QuoteError:
                raise Refused("STATUS_QUOTE_MISSING") from None

        scope_judged = entry.get("scope") or {}
        segment = geography = None
        for key, target in (
            ("segment_quote", "segment"),
            ("geography_quote", "geography"),
        ):
            quote = scope_judged.get(key)
            if quote is None:
                continue
            normalized, _s, _e, _c = find_quote(span, quote)
            if target == "segment":
                segment = normalized
            else:
                geography = normalized
        if scope_judged.get("product_quote") is not None:
            find_quote(span, scope_judged["product_quote"])

        conditions = []
        for condition in entry.get("conditions") or []:
            normalized, raw_start, raw_end, _count = find_quote(
                span, condition.get("quote"), condition.get("occurrence")
            )
            if len(normalized) > MAX_CONDITION_CHARS:
                raise Refused("CONDITION_TOO_LONG")
            raw_bytes = span.raw[raw_start:raw_end]
            byte_start, byte_end = span.doc_offsets(raw_start, raw_end)
            conditions.append(
                {
                    "kind": condition.get("kind"),
                    "text": normalized,
                    "byte_start": byte_start,
                    "byte_end": byte_end,
                    "span_sha256": sha(raw_bytes),
                }
            )

        magnitudes = []
        source_facts = []
        for magnitude in entry.get("magnitudes") or []:
            if isinstance(magnitude, dict) and "xbrl_fact_ids" in magnitude:
                mapped, facts = map_xbrl_magnitude(
                    cand, magnitude, species, effective_role
                )
                magnitudes.extend(mapped)
                source_facts.extend(facts)
            else:
                mapped, _normalized = map_narrative_magnitude(
                    cand, magnitude, span
                )
                magnitudes.append(mapped)

        fetched_at = self.ingested_at(cand)
        if not fetched_at:
            raise Refused("LEDGER_DOCUMENT_MISSING")

        excerpt_span = cand["excerpt"]["span"]
        method = (
            "xbrl_fact+narrative_span"
            if any(m.get("xbrl_fact_id") for m in magnitudes)
            else "narrative_span"
        )
        row = {
            "schema": EXTRACTION_SCHEMA,
            "row_kind": "observation",
            "temporal_eligibility": "acceptance_time",
            "published_at": cand["accepted_at"],
            "ingested_at": fetched_at,
            "period_end": cand["period_of_report"],
            "sec_index_header_acceptance_et":
                cand["sec_index_header_acceptance_et"],
            "sec_submissions_acceptance_raw":
                cand["sec_submissions_acceptance_raw"],
            "observation_id": None,
            "species": species,
            "relation_status": relation_status,
            "subject": subject,
            "object": object_party,
            "asserting_party": subject["issuer_id"],
            "channel": list(entry.get("channel") or []),
            "scope": {
                "product_key": scope_judged.get("product_key"),
                "segment": segment,
                "geography": geography,
            },
            "conditions": conditions,
            "magnitudes": magnitudes,
            "extracted_by": {
                "agent": (judgment.get("judge") or {}).get("agent"),
                "lane_run_id": (judgment.get("judge") or {}).get("lane_run_id"),
                "method": method,
            },
            "source_ref": {
                "accepted_at": cand["accepted_at"],
                "accession": cand["accession"],
                "byte_start": excerpt_span["byte_start"],
                "byte_end": excerpt_span["byte_end"],
                "cik": cand["cik"],
                "doc_byte_length": cand["doc_byte_length"],
                "doc_sha256": cand["doc_sha256"],
                "filed_at": cand["filed_at"],
                "form": cand["form"],
                "normalized_span_sha256": excerpt_span["normalized_sha256"],
                "period_of_report": cand["period_of_report"],
                "primary_document": cand["primary_document"],
                "span_sha256": excerpt_span["raw_sha256"],
                "url": cand["url"],
                "xbrl": _dedupe_facts(source_facts),
            },
        }

        object_label = (
            object_party.get("anonymous_alias")
            if object_party.get("anonymous_alias") is not None
            else object_party.get("name_as_filed")
        )
        observation_id = observation_identity(
            cand["accession"],
            excerpt_span["byte_start"],
            excerpt_span["byte_end"],
            species,
            subject["issuer_id"],
            object_party["issuer_id"],
            object_label=object_label,
        )
        row["observation_id"] = observation_id
        refusal = self._check_row(row, cand)
        if refusal:
            raise Refused(refusal)
        if observation_id in self._seen_observation_ids:
            raise Refused("OBSERVATION_ID_DUPLICATE")
        self._seen_observation_ids.add(observation_id)
        return row

    # -- one assessment judgment -> one document_assessment row (K9) -------------

    def _assessment_row(self, cand, judgment, span):
        if cand.get("origin") != "amendment_note":
            raise Refused("ASSESSMENT_ON_NON_AMENDMENT")
        judged = judgment.get("assessment") or {}
        quote = judged.get("reason_quote")
        find_quote(span, quote, judged.get("occurrence"))
        census_entry = (self.census.get("issuers") or {}).get(cand["issuer_id"]) or {}
        accession = cand["accession"]
        target = None
        latest = (census_entry.get("latest") or {}).get("accessionNumber")
        if any(
            amendment.get("accessionNumber") == accession
            for amendment in census_entry.get("amendments_of_latest") or []
        ):
            target = latest
        prior = (census_entry.get("prior") or {}).get("accessionNumber")
        if target is None and any(
            amendment.get("accessionNumber") == accession
            for amendment in census_entry.get("amendments_of_prior") or []
        ):
            target = prior
        if target is None:
            raise Refused("AMENDMENT_TARGET_UNKNOWN")
        fetched_at = self.ingested_at(cand)
        if not fetched_at:
            raise Refused("LEDGER_DOCUMENT_MISSING")
        excerpt_span = cand["excerpt"]["span"]
        row = {
            "schema": EXTRACTION_SCHEMA,
            "row_kind": "document_assessment",
            "temporal_eligibility": "acceptance_time",
            "published_at": cand["accepted_at"],
            "ingested_at": fetched_at,
            "period_end": cand["period_of_report"],
            "sec_index_header_acceptance_et":
                cand["sec_index_header_acceptance_et"],
            "sec_submissions_acceptance_raw":
                cand["sec_submissions_acceptance_raw"],
            "assessment_id": assessment_identity(
                accession, excerpt_span["byte_start"], excerpt_span["byte_end"],
                judged.get("assessment"),
            ),
            "issuer_id": cand["issuer_id"],
            "amends_accession": target,
            "assessment": judged.get("assessment"),
            "reason": judged.get("reason"),
            "extracted_by": {
                "agent": (judgment.get("judge") or {}).get("agent"),
                "lane_run_id": (judgment.get("judge") or {}).get("lane_run_id"),
                "method": "narrative_span",
            },
            "source_ref": {
                "accepted_at": cand["accepted_at"],
                "accession": accession,
                "byte_start": excerpt_span["byte_start"],
                "byte_end": excerpt_span["byte_end"],
                "cik": cand["cik"],
                "doc_byte_length": cand["doc_byte_length"],
                "doc_sha256": cand["doc_sha256"],
                "filed_at": cand["filed_at"],
                "form": cand["form"],
                "normalized_span_sha256": excerpt_span["normalized_sha256"],
                "period_of_report": cand["period_of_report"],
                "primary_document": cand["primary_document"],
                "span_sha256": excerpt_span["raw_sha256"],
                "url": cand["url"],
                "xbrl": [],
            },
        }
        refusal = self._check_row(row, cand)
        if refusal:
            raise Refused(refusal)
        return row

    def _check_row(self, row: dict, cand: dict):
        """clock_refusal + contract validation; the refusal reason, or None."""
        reason = self._clock_refusal(row, cand)
        if reason:
            return f"CLOCK_REFUSED:{reason}"
        problems = self._validate_row(row)
        if problems:
            return f"ROW_INVALID:{problems[0]}"
        return None

    def _clock_refusal(self, row: dict, cand: dict):
        from engine.company_intelligence.relationships.package_v2 import (
            clock_refusal,
        )

        return clock_refusal(row, cand.get("excerpt"))


# --- K10/K11: materialize ----------------------------------------------------------

def read_jsonl(path: Path) -> list:
    rows = []
    with open(path, "rb") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line.decode("utf-8")))
    return rows


def build_ledger_index(ledger_rows: list) -> dict:
    """{(accession, filename): fetched_at} over collected|partial documents."""
    index = {}
    for row in ledger_rows:
        if row.get("state") not in ("collected", "partial"):
            continue
        for document in row.get("documents") or []:
            key = (row.get("accession"), document.get("filename"))
            if key not in index:
                index[key] = document.get("fetched_at")
    return index


def read_judgments(judgments_dir: Path, candidate_ids):
    """Read every judgments/*.jsonl line once (K12 judgment-level codes).

    Returns ``(records, all_lines, codes)``: ``records`` maps candidate_id ->
    record | None (missing) | "duplicate" | "invalid"; ``all_lines`` is every
    parsed record in read order (for judgments.jsonl); ``codes`` counts the
    judgment-level codes.
    """
    import jsonschema

    codes: Counter = Counter()
    records: dict = {}
    all_lines: list = []
    wanted = set(candidate_ids)
    grouped: dict = {}
    for path in sorted(Path(judgments_dir).glob("*.jsonl")):
        with open(path, "rb") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line.decode("utf-8"))
                except ValueError:
                    codes["JUDGMENT_SCHEMA_INVALID"] += 1
                    continue
                if not isinstance(record, dict):
                    codes["JUDGMENT_SCHEMA_INVALID"] += 1
                    continue
                all_lines.append(record)
                candidate_id = record.get("candidate_id")
                if candidate_id not in wanted:
                    codes["JUDGMENT_UNKNOWN_CANDIDATE"] += 1
                    continue
                grouped.setdefault(candidate_id, []).append(record)
    for candidate_id, lines in grouped.items():
        if len(lines) > 1:
            codes["JUDGMENT_DUPLICATE"] += len(lines)
            records[candidate_id] = "duplicate"
            continue
        record = lines[0]
        try:
            jsonschema.validators.validator_for(JUDGMENT_SCHEMA)(
                JUDGMENT_SCHEMA
            ).validate(record)
        except jsonschema.ValidationError:
            codes["JUDGMENT_SCHEMA_INVALID"] += 1
            records[candidate_id] = "invalid"
            continue
        records[candidate_id] = record
    return records, all_lines, codes


def committed_issuers(committed_dir, exclude_path) -> set:
    """Issuer ids in any committed extraction row under committed_dir (K10)."""
    issuers: set = set()
    root = Path(committed_dir)
    if not root.is_dir():
        return issuers
    exclude = Path(exclude_path).resolve() if exclude_path else None
    for path in sorted(root.rglob("*.jsonl")):
        if exclude is not None and path.resolve() == exclude:
            continue
        try:
            rows = read_jsonl(path)
        except (OSError, ValueError):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            issuer_id = row.get("issuer_id")
            if isinstance(issuer_id, str):
                issuers.add(issuer_id)
            subject = row.get("subject")
            if isinstance(subject, dict) and isinstance(
                subject.get("issuer_id"), str
            ):
                issuers.add(subject["issuer_id"])
    return issuers


def duplicate_span_exclusions(candidates: list) -> set:
    """Candidate ids excluded because an identical span exists at a lower
    byte_start under the same accession (K11); the lowest offset is kept."""
    groups: dict = {}
    for cand in candidates:
        span = cand["excerpt"]["span"]
        key = (cand["accession"], span["raw_sha256"])
        groups.setdefault(key, []).append(cand)
    excluded = set()
    for members in groups.values():
        if len(members) < 2:
            continue
        winner = min(
            members, key=lambda c: (c["excerpt"]["span"]["byte_start"],
                                    c["candidate_id"])
        )
        for cand in members:
            if cand["candidate_id"] != winner["candidate_id"]:
                excluded.add(cand["candidate_id"])
    return excluded


def excerpt_for(cand: dict) -> dict:
    """The candidate's excerpt with the M1 note (K11)."""
    excerpt = dict(cand["excerpt"])
    excerpt["excerpt_note"] = M1_EXCERPT_NOTE
    return excerpt


def _self_check_excerpt(excerpt: dict) -> list:
    import jsonschema

    try:
        jsonschema.validate(excerpt, _excerpt_contract())
    except jsonschema.ValidationError as error:
        return [error.message]
    return replay.verify_excerpt(excerpt)


_CONTRACT_CACHE = {}


def _excerpt_contract():
    if "excerpt" not in _CONTRACT_CACHE:
        path = (
            Path(__file__).resolve().parents[3]
            / "contracts/company_intelligence/"
            "relationship_source_excerpt.v1.schema.json"
        )
        _CONTRACT_CACHE["excerpt"] = json.loads(
            path.read_text(encoding="utf-8")
        )
    return _CONTRACT_CACHE["excerpt"]


def existing_source_files(sources_dir: Path, accession: str) -> list:
    """Every on-disk excerpt file of one accession (flat + nested)."""
    files = []
    flat = Path(sources_dir) / f"{accession}.json"
    if flat.is_file():
        files.append(flat)
    nested = Path(sources_dir) / accession
    if nested.is_dir():
        files.extend(sorted(p for p in nested.glob("*.json") if p.is_file()))
    return files


def plan_source(sources_dir: Path, accession: str, raw_sha256: str,
                excerpt: dict):
    """(disposition, path) for one (accession, raw_sha256) key (K11).

    disposition is "reuse" (an existing byte-identical file, nothing written),
    "write" (absent — materialize the nested layout), or "conflict" (existing
    bytes differ: SOURCE_DUPLICATE_CONFLICT, citing rows refused).
    """
    expected = canonical_json_bytes(excerpt)
    matching = []
    for path in existing_source_files(sources_dir, accession):
        try:
            document = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, ValueError):
            return "conflict", path
        span = document.get("span") if isinstance(document, dict) else None
        if not isinstance(span, dict) or span.get("raw_sha256") != raw_sha256:
            continue  # a different span of the same accession: another key
        if path.read_bytes() == expected:
            matching.append(path)
        else:
            return "conflict", path
    if matching:
        return "reuse", matching[0]
    return "write", Path(sources_dir) / accession / f"{raw_sha256[:20]}.json"


def evaluate_materialize(
    *,
    leaf: str,
    dirname: str,
    workdir,
    repo_root,
    committed_dir,
    inputs_dir,
    manifest_path,
    cache_root,
    allow_missing: bool,
    enforce_committed: bool = True,
):
    """The whole K10/K11 computation without writing anything.

    Returns (rc, result) where rc is 2 for a hard stop (input hash drift,
    candidates/index disagreement, missing judgments without --allow-missing)
    and 0 otherwise; result carries rows, ledger, coverage, report and the
    source plan for the caller to write.  ``enforce_committed`` applies the
    K10 issuer-already-extracted skip (materialize); verify leaves it off so
    the dry-run never suppresses a mapping.
    """
    base = Path(workdir) / dirname
    candidates_path = base / "candidates.jsonl"
    ledger_path = base / "fetch_ledger.jsonl"
    index_path = base / "packs" / "index.json"
    report_source_path = base / "harvest_report.json"
    for path in (candidates_path, ledger_path, index_path, report_source_path):
        if not path.is_file():
            return 2, {"error": f"missing workdir input: {path}"}
    candidates = read_jsonl(candidates_path)
    ledger = read_jsonl(ledger_path)
    index = json.loads(index_path.read_bytes().decode("utf-8"))
    candidates_sha = hashlib.sha256(candidates_path.read_bytes()).hexdigest()
    if index.get("candidates_sha256") != candidates_sha:
        return 2, {"error": "packs/index.json candidates_sha256 mismatch"}
    candidate_ids = [cand["candidate_id"] for cand in candidates]
    records, all_judgment_lines, judgment_codes = read_judgments(
        base / (index.get("judgments_dir") or "judgments"), candidate_ids
    )
    committed = (
        committed_issuers(committed_dir, default_output_path(repo_root, dirname))
        if enforce_committed
        else set()
    )
    committed_ids = {
        cand["candidate_id"]
        for cand in candidates
        if cand["issuer_id"] in committed
    }
    # a judgment is only "missing" for a candidate that would still run: an
    # issuer skipped whole is skipped before the completeness gate
    missing = [
        cid
        for cid in candidate_ids
        if records.get(cid) is None and cid not in committed_ids
    ]
    if missing and not allow_missing:
        return 2, {"error": f"{len(missing)} judgment(s) missing"}

    inputs = rel_harvest.load_inputs(inputs_dir)
    manifest_version, issuers = _load_manifest(manifest_path)
    cache = rel_edgar.EdgarCache(cache_root)
    mapper = CandidateMapper(
        issuers=issuers,
        aliases=inputs["aliases"]["aliases"],
        resolver_rows=inputs["resolver"]["rows"],
        census=inputs["census"],
        cache=cache,
        counters=new_counters(),
        ledger_index=build_ledger_index(ledger),
    )
    excluded = duplicate_span_exclusions(candidates)

    codes: Counter = Counter(judgment_codes)
    ledger_entries: list = []
    rows_by_candidate: dict = {}
    for cand in candidates:
        candidate_id = cand["candidate_id"]
        issuer_id = cand["issuer_id"]
        record = records.get(candidate_id)
        entry = {
            "candidate_id": candidate_id,
            "issuer_id": issuer_id,
            "verdict": (
                record.get("verdict") if isinstance(record, dict) else None
            ),
            "outcome": "refused",
            "codes": [],
            "observation_ids": [],
            "assessment_id": None,
            "notes": [],
        }
        ledger_entries.append(entry)
        rows_by_candidate[candidate_id] = []
        if issuer_id in committed:
            entry["outcome"] = "skipped"
            entry["codes"].append("ISSUER_ALREADY_EXTRACTED")
            codes["ISSUER_ALREADY_EXTRACTED"] += 1
            continue
        if record is None:
            entry["outcome"] = "missing"
            entry["codes"].append("JUDGMENT_MISSING")
            codes["JUDGMENT_MISSING"] += 1
            continue
        if record == "duplicate":
            entry["codes"].append("JUDGMENT_DUPLICATE")
            continue
        if record == "invalid":
            entry["codes"].append("JUDGMENT_SCHEMA_INVALID")
            continue
        if candidate_id in excluded:
            entry["codes"].append("DUPLICATE_SPAN_BYTES")
            mapper.counters["duplicate_span_bytes"] += 1
            codes["DUPLICATE_SPAN_BYTES"] += 1
            continue
        outcome = mapper.map(cand, record)
        entry["codes"].extend(outcome["codes"])
        entry["notes"].extend(outcome["notes"])
        entry["outcome"] = outcome["outcome"]
        entry["observation_ids"] = outcome["observation_ids"]
        entry["assessment_id"] = outcome["assessment_id"]
        rows_by_candidate[candidate_id] = outcome["rows"]
        for code in outcome["codes"]:
            codes[code] += 1

    rows = [row for cand in candidates
            for row in rows_by_candidate[cand["candidate_id"]]]

    # --- sources: reuse / write / conflict over the cited (accession, sha) ---
    cited_keys = {}
    for cand in candidates:
        for row in rows_by_candidate[cand["candidate_id"]]:
            span = cand["excerpt"]["span"]
            cited_keys.setdefault(
                (cand["accession"], span["raw_sha256"]), cand
            )
    repo_root = Path(repo_root)
    sources_dir = (
        repo_root / "research/theme_graph/gmi_relationships_20261021/sources"
    )
    plans = {}
    conflicted_keys = set()
    for key, cand in sorted(cited_keys.items()):
        excerpt = excerpt_for(cand)
        problems = _self_check_excerpt(excerpt)
        if problems:
            mapper.counters["excerpt_self_check_failed"] += 1
            _refuse_rows(rows_by_candidate, cand, "EXCERPT_SELF_CHECK_FAILED",
                         codes)
            continue
        disposition, path = plan_source(
            sources_dir, key[0], key[1], excerpt
        )
        plans[key] = (disposition, path, excerpt)
        if disposition == "conflict":
            conflicted_keys.add(key)
            _refuse_rows(rows_by_candidate, cand, "SOURCE_DUPLICATE_CONFLICT",
                         codes)
    rows = [row for cand in candidates
            for row in rows_by_candidate[cand["candidate_id"]]]

    # outcomes after every refusal pass
    observations = 0
    assessments = 0
    rows_by_species: Counter = Counter()
    non_edge_reason: Counter = Counter()
    edges_seen = set()
    observed_issuers: set = set()
    assessed_issuers: set = set()
    for cand in candidates:
        entry = _ledger_entry(ledger_entries, cand["candidate_id"])
        cand_rows = rows_by_candidate[cand["candidate_id"]]
        obs = [r for r in cand_rows if r["row_kind"] == "observation"]
        asm = [r for r in cand_rows if r["row_kind"] == "document_assessment"]
        entry["observation_ids"] = [r["observation_id"] for r in obs]
        entry["assessment_id"] = asm[0]["assessment_id"] if asm else None
        if cand_rows:
            entry["outcome"] = "admitted"
        elif entry["outcome"] == "admitted":
            entry["outcome"] = "refused"
        observations += len(obs)
        assessments += len(asm)
        for row in obs:
            rows_by_species[row["species"]] += 1
            observed_issuers.add(cand["issuer_id"])
            reason = row["object"].get("non_edge_reason")
            if reason:
                non_edge_reason[reason] += 1
            if row["object"].get("issuer_id") is not None:
                edges_seen.add(
                    (
                        row["species"],
                        row["subject"]["issuer_id"],
                        row["object"]["issuer_id"],
                    )
                )
        if asm:
            assessed_issuers.add(cand["issuer_id"])

    coverage = _coverage_rows(
        ledger=ledger,
        candidates=candidates,
        records=records,
        rows_by_candidate=rows_by_candidate,
        observed_issuers=observed_issuers,
        committed=committed,
        census=inputs["census"],
        codes=codes,
    )

    missing_now = [
        cand["candidate_id"]
        for cand in candidates
        if records.get(cand["candidate_id"]) is None
        and cand["issuer_id"] not in committed
    ]
    judged = len(
        [cand for cand in candidates
         if records.get(cand["candidate_id"]) is not None]
    )
    outcomes: Counter = Counter(entry["outcome"] for entry in ledger_entries)
    edges = [
        {"species": species, "subject_issuer_id": subject, "object_issuer_id":
         object_iid}
        for species, subject, object_iid in sorted(edges_seen)
    ]
    unresolved_names = [
        {"name": name, "count": count}
        for name, count in sorted(
            mapper.unresolved_names.items(), key=lambda kv: (-kv[1], kv[0])
        )[:50]
    ]
    inputs_listing = {
        _relpath(candidates_path, workdir): hashlib.sha256(
            candidates_path.read_bytes()
        ).hexdigest(),
        _relpath(ledger_path, workdir): hashlib.sha256(
            ledger_path.read_bytes()
        ).hexdigest(),
        _relpath(index_path, workdir): hashlib.sha256(
            index_path.read_bytes()
        ).hexdigest(),
        _relpath(report_source_path, workdir): hashlib.sha256(
            report_source_path.read_bytes()
        ).hexdigest(),
    }
    for name, pin in rel_harvest.PINS.items():
        inputs_listing[f"research/theme_graph/gmi_relationships_20261021/"
                       f"m2_inputs/{name}"] = pin
    inputs_listing[_relpath(manifest_path, repo_root)] = hashlib.sha256(
        Path(manifest_path).read_bytes()
    ).hexdigest()

    result = {
        "candidates_total": len(candidates),
        "judged": judged,
        "missing": len(missing_now),
        "outcomes": dict(sorted(outcomes.items())),
        "codes": dict(sorted(codes.items())),
        "rows_by_species": dict(sorted(rows_by_species.items())),
        "non_edge_reason": dict(sorted(non_edge_reason.items())),
        "observations": observations,
        "assessments": assessments,
        "coverage": coverage,
        "coverage_by_state": dict(sorted(
            Counter(row["state"] for row in coverage).items()
        )),
        "edges": edges,
        "unresolved_names": unresolved_names,
        "counters": dict(sorted(mapper.counters.items())),
        "inputs": dict(sorted(inputs_listing.items())),
        "rows": rows,
        "ledger_entries": ledger_entries,
        "judgment_lines": all_judgment_lines,
        "source_plans": plans,
        "manifest_version": manifest_version,
        "leaf": leaf,
        "dirname": dirname,
    }
    return 0, result


def _refuse_rows(rows_by_candidate, cand, code, codes) -> None:
    for row in rows_by_candidate.get(cand["candidate_id"]) or []:
        codes[code] += 1
    rows_by_candidate[cand["candidate_id"]] = []


def _ledger_entry(entries, candidate_id):
    for entry in entries:
        if entry["candidate_id"] == candidate_id:
            return entry
    raise KeyError(candidate_id)


def _relpath(path, base) -> str:
    try:
        return Path(path).resolve().relative_to(Path(base).resolve()).as_posix()
    except ValueError:
        return str(path)


def _load_manifest(manifest_path):
    from engine.company_intelligence.relationships.package_v2 import (
        load_manifest_issuers,
    )

    return load_manifest_issuers(manifest_path)


def default_output_path(repo_root, dirname: str) -> Path:
    return (
        Path(repo_root)
        / "research/theme_graph/gmi_relationships_20261021/extraction/m2"
        / f"{dirname}.jsonl"
    )


def _coverage_rows(*, ledger, candidates, records, rows_by_candidate,
                   observed_issuers, committed, census, codes):
    issuers = sorted({row.get("issuer_id") for row in ledger if row.get("issuer_id")})
    coverage = []
    for issuer_id in issuers:
        if issuer_id in committed:
            continue  # skipped whole: no coverage row either
        rows_of = [row for row in ledger if row.get("issuer_id") == issuer_id]
        active = [
            row for row in rows_of if row.get("state") in ("collected", "partial")
        ]
        cands_of = [c for c in candidates if c["issuer_id"] == issuer_id]
        census_entry = (census.get("issuers") or {}).get(issuer_id) or {}
        if not active:
            first = rows_of[0] if rows_of else {}
            reason = first.get("reason") or census_entry.get("state")
            fetched_at = first.get("census_fetched_at") or census_entry.get(
                "fetched_at"
            )
            if not fetched_at:
                codes["COVERAGE_NO_CLOCK"] += 1
                continue
            latest = census_entry.get("latest") or {}
            period_end = latest.get("reportDate") if latest else None
            if not period_end:
                period_end = str(fetched_at)[:10]
            coverage.append(
                {
                    "schema": EXTRACTION_SCHEMA,
                    "row_kind": "coverage",
                    "temporal_eligibility": "acceptance_time",
                    "published_at": fetched_at,
                    "ingested_at": fetched_at,
                    "period_end": period_end,
                    "issuer_id": issuer_id,
                    "documents": [],
                    "state": "unavailable",
                    "reason": reason,
                }
            )
            continue
        documents = sorted({row["accession"] for row in active if row.get("accession")})
        missing = [
            c for c in cands_of if records.get(c["candidate_id"]) is None
        ]
        admitted_obs = sum(
            1
            for c in cands_of
            for r in rows_by_candidate.get(c["candidate_id"]) or []
            if r["row_kind"] == "observation"
        )
        if missing:
            state, reason = "not_assessed", f"judgments_missing:{len(missing)}"
        elif admitted_obs:
            state, reason = "assessed", None
        elif cands_of:
            state = "no_supported_result"
            reason = f"no_admitted_observation:{len(cands_of)}"
        else:
            state, reason = "no_supported_result", "no_candidates"
        accepted = [
            row["accepted_at"] for row in active if row.get("accepted_at")
        ]
        fetched = []
        periods = []
        for row in active:
            for document in row.get("documents") or []:
                if document.get("fetched_at"):
                    fetched.append(document["fetched_at"])
            if row.get("period_of_report"):
                periods.append(row["period_of_report"])
        coverage.append(
            {
                "schema": EXTRACTION_SCHEMA,
                "row_kind": "coverage",
                "temporal_eligibility": "acceptance_time",
                "published_at": max(accepted) if accepted else None,
                "ingested_at": max(fetched) if fetched else None,
                "period_end": max(periods) if periods else None,
                "issuer_id": issuer_id,
                "documents": documents,
                "state": state,
                "reason": reason,
            }
        )
    return coverage


def write_materialized(result: dict, *, workdir, dirname, repo_root) -> None:
    """Write every materialize output under repo_root (K11); byte-identical
    reruns produce byte-identical files."""
    repo_root = Path(repo_root)
    base = repo_root / "research/theme_graph/gmi_relationships_20261021"
    sources_dir = base / "sources"
    extraction_dir = base / "extraction" / "m2"
    judging_dir = base / "m2" / "judging" / dirname
    for directory in (sources_dir, extraction_dir, judging_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for key, (disposition, path, excerpt) in sorted(
        result["source_plans"].items()
    ):
        if disposition == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical_json_bytes(excerpt))
            result["counters"]["sources_written"] += 1
        elif disposition == "reuse":
            result["counters"]["sources_reused"] += 1
    result["counters"] = dict(sorted(result["counters"].items()))

    observations = [
        row for row in result["rows"] if row["row_kind"] == "observation"
    ]
    assessments = [
        row for row in result["rows"] if row["row_kind"] == "document_assessment"
    ]
    coverage = result["coverage"]
    observations.sort(key=_observation_sort_key)
    assessments.sort(key=_assessment_sort_key)
    coverage.sort(key=lambda row: row["issuer_id"])

    extraction_path = default_output_path(repo_root, dirname)
    with extraction_path.open("wb") as handle:
        for row in observations + assessments + coverage:
            handle.write(canonical_jsonl(row))

    judged_lines = sorted(
        result["judgment_lines"], key=lambda record: record.get("candidate_id")
    )
    with (judging_dir / "judgments.jsonl").open("wb") as handle:
        for record in judged_lines:
            handle.write(canonical_jsonl(record))
    ledger_entries = sorted(
        result["ledger_entries"], key=lambda entry: entry["candidate_id"]
    )
    with (judging_dir / "materialize_ledger.jsonl").open("wb") as handle:
        for entry in ledger_entries:
            handle.write(canonical_jsonl(entry))

    report = {
        "schema": REPORT_SCHEMA,
        "leaf": result["leaf"],
        "dirname": result["dirname"],
        "candidates_total": result["candidates_total"],
        "judged": result["judged"],
        "outcomes": result["outcomes"],
        "codes": result["codes"],
        "rows_by_species": result["rows_by_species"],
        "non_edge_reason": result["non_edge_reason"],
        "observations": result["observations"],
        "assessments": result["assessments"],
        "coverage_by_state": result["coverage_by_state"],
        "edges": result["edges"],
        "unresolved_names": result["unresolved_names"],
        "counters": result["counters"],
        "inputs": result["inputs"],
    }
    (judging_dir / "materialize_report.json").write_bytes(
        canonical_json_bytes(report)
    )
    workdir_base = Path(workdir) / dirname
    (judging_dir / "fetch_ledger.jsonl").write_bytes(
        (workdir_base / "fetch_ledger.jsonl").read_bytes()
    )
    (judging_dir / "harvest_report.json").write_bytes(
        (workdir_base / "harvest_report.json").read_bytes()
    )


def _observation_sort_key(row: dict) -> tuple:
    return (
        row["subject"]["issuer_id"],
        row["published_at"],
        row["source_ref"]["accession"],
        row["source_ref"]["byte_start"],
        row["observation_id"],
    )


def _assessment_sort_key(row: dict) -> tuple:
    return (
        row["issuer_id"],
        row["published_at"],
        row["source_ref"]["accession"],
        row["assessment_id"],
    )
