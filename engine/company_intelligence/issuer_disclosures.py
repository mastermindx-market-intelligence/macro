"""Standalone issuer disclosures, owned by Company Intelligence.

These contracts do not invent an earnings period or an SEC filing identity.
Source editions and reviewed fact revisions have separate immutable chains.
The producer owns original source bytes; the object store below receives only
bounded metadata and constrained fact fields, never original/reviewer text.

``DisclosureAuthority`` is an injected *trusted source-owner* boundary, not an
entitlement supplied by a web caller. No production resolver, dataset adoption,
rights grant or HTTP endpoint is installed by this module. F04 must authenticate
and check its actual feature entitlement before calling the private reader.
Synthetic resolvers prove the contract, not permission to admit real C01.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import codecs
import hashlib
import html
import json
import re
import unicodedata
from typing import Protocol

from .documents import text_span
from ..research_vault.r2_store import VersionedBytes

EDITION_SCHEMA = "company_intelligence.issuer_disclosure_edition/v1"
FACT_SCHEMA = "company_intelligence.product_integration_fact/v1"
SEC_EDITION_SCHEMA = "company_intelligence.sec_disclosure_edition/v1"
SUPPLIER_FACT_SCHEMA = "company_intelligence.disclosed_supplier_fact/v1"
SEGMENT_FACT_SCHEMA = "company_intelligence.segment_activity_fact/v1"
SEC_SUPPLIER_PURPOSE = "private_company_intelligence_context"
SEC_SUPPLIER_AUDIENCE = "company_intelligence_entitled"
EDITION_SCHEMAS = frozenset({EDITION_SCHEMA, SEC_EDITION_SCHEMA})
FACT_SCHEMAS = frozenset({FACT_SCHEMA, SUPPLIER_FACT_SCHEMA, SEGMENT_FACT_SCHEMA})
# The annual report (an amendment counts) is the only form that admits a segment
# activity fact; any other form is refused. The pinned EDGAR manifest's own form
# must additionally equal this value at source replay.
SEGMENT_FORM_TYPES = frozenset({"10-K", "10-K/A", "20-F", "20-F/A"})
SEGMENT_SHARE_SCOPES = frozenset({"segment", "product_line"})
# A disclosed figure is the exact characters the filing prints (digits and
# separators, no sign), a declared sign and a stated scale. The numeric value is
# sign x digits x scale; a loss (parentheses or minus) is carried negative.
SEGMENT_FIGURE_NAMES = ("revenue", "revenue_denominator", "profit", "profit_denominator")
SEGMENT_FIGURE_SCALES = {"units": 1, "thousands": 1000, "millions": 1000000, "billions": 1000000000}
SEGMENT_FIGURE_SIGNS = frozenset({"+", "-"})
_FIGURE_TEXT = re.compile(r"(?:0|[1-9][0-9]{0,2}(?:,[0-9]{3}){1,6}|[1-9][0-9]{0,20})\Z")
MAX_OBJECT_BYTES = 16 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
MAX_SEC_SOURCE_BYTES = 4 * 1024 * 1024
MAX_REVISIONS = 64
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}\Z")
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")
_FIELDS = frozenset({"fact_id", "revision", "kind", "lifecycle", "subject_id",
                     "object_id", "product", "platform", "amount", "economic_share"})


class DisclosureError(ValueError):
    """A closed contract or a source-owner admission failed."""

    def __init__(self, code: str, *, effect_unknown: bool = False):
        super().__init__(code)
        self.code = code
        self.effect_unknown = effect_unknown
        self.automatic_retry_permitted = False


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise DisclosureError(code)


def _identifier(value: object) -> str:
    _require(type(value) is str and _ID.fullmatch(value) is not None, "IDENTITY_INVALID")
    return value


def _digest(value: object) -> str:
    _require(type(value) is str and _SHA.fullmatch(value) is not None, "DIGEST_INVALID")
    return value


def _integer(value: object, minimum: int, maximum: int) -> int:
    _require(type(value) is int and minimum <= value <= maximum, "INTEGER_INVALID")
    return value


def _instant(value: object) -> datetime:
    _require(type(value) is str and _INSTANT.fullmatch(value) is not None, "INSTANT_PRECISION_INVALID")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise DisclosureError("INSTANT_INVALID") from None


def _closed(value: object, fields: set[str]) -> dict:
    _require(type(value) is dict and set(value) == fields, "SCHEMA_INVALID")
    return value


def _canonical(value: dict) -> bytes:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise DisclosureError("JSON_INVALID") from None
    _require(0 < len(raw) <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE")
    return raw


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def _decode(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE")
    try:
        result = json.loads(raw, object_pairs_hook=_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(DisclosureError("JSON_INVALID")))
    except (ValueError, UnicodeError, RecursionError):
        raise DisclosureError("JSON_INVALID") from None
    _require(type(result) is dict and _canonical(result) == raw, "NONCANONICAL_OBJECT")
    return result


def disclosure_id(issuer_id: str, source_key: str) -> str:
    """Stable native identity; the source owner supplies the original key."""
    material = [_identifier(issuer_id), _identifier(source_key)]
    return "disclosure:" + hashlib.sha256(json.dumps(material, separators=(",", ":")).encode()).hexdigest()


def fact_id(disclosure: str, claim_key: str) -> str:
    material = [_identifier(disclosure), _identifier(claim_key)]
    return "integration:" + hashlib.sha256(json.dumps(material, separators=(",", ":")).encode()).hexdigest()


def activity_fact_id(disclosure: str, claim_key: str) -> str:
    """Stable native identity for a segment-activity fact (``activity:`` prefix).

    The ``integration:`` identity above is left untouched for the existing two
    species; the activity route gets its own prefix so a segment fact can never
    collide with or impersonate a product-integration or supplier fact.
    """
    material = [_identifier(disclosure), _identifier(claim_key)]
    return "activity:" + hashlib.sha256(json.dumps(material, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Reference:
    schema: str
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        _require(type(self.schema) is str and self.schema in EDITION_SCHEMAS | FACT_SCHEMAS, "REFERENCE_SCHEMA_INVALID")
        _digest(self.sha256)
        _integer(self.byte_length, 1, MAX_OBJECT_BYTES)

    def payload(self) -> dict:
        return {"schema": self.schema, "sha256": self.sha256, "byte_length": self.byte_length}


def _reference(value: object, schema: str) -> Reference:
    value = _closed(value, {"schema", "sha256", "byte_length"})
    result = Reference(**value)
    _require(result.schema == schema, "REFERENCE_SCHEMA_INVALID")
    return result


def _ref(value: dict) -> Reference:
    raw = _canonical(value)
    return Reference(value["schema"], hashlib.sha256(raw).hexdigest(), len(raw))


def validate_edition(value: dict) -> Reference:
    _require(type(value) is dict, "SCHEMA_INVALID")
    sec = value.get("schema") == SEC_EDITION_SCHEMA
    _closed(value, {"schema", "disclosure_id", "issuer_id", "source_key", "revision",
                    "previous", "source_sha256", "source_byte_length", "published_date",
                    "published_at", "publication_precision", "known_at"} | ({"sec_source"} if sec else set()))
    _require(value["schema"] in EDITION_SCHEMAS, "SCHEMA_INVALID")
    _require(value["disclosure_id"] == disclosure_id(value["issuer_id"], value["source_key"]), "DISCLOSURE_ID_MISMATCH")
    _integer(value["revision"], 1, MAX_REVISIONS)
    _integer(value["source_byte_length"], 1, MAX_SEC_SOURCE_BYTES if sec else MAX_SOURCE_BYTES)
    _digest(value["source_sha256"])
    known = _instant(value["known_at"])
    _require((value["revision"] == 1) == (value["previous"] is None), "PREDECESSOR_REQUIRED")
    if value["previous"] is not None:
        _reference(value["previous"], value["schema"])
    try:
        published_date = value["published_date"]
        _require(type(published_date) is str and date.fromisoformat(published_date).isoformat() == published_date, "DATE_INVALID")
    except ValueError:
        raise DisclosureError("DATE_INVALID") from None
    _require(type(value["publication_precision"]) is str and value["publication_precision"] in {"date", "instant"}, "PUBLICATION_PRECISION_INVALID")
    if value["publication_precision"] == "date":
        _require(value["published_at"] is None, "DATE_IS_NOT_INSTANT")
        _require(date.fromisoformat(published_date) <= known.date(), "FUTURE_PUBLICATION")
    else:
        published = _instant(value["published_at"])
        source_day = datetime.fromisoformat(value["published_at"].replace("Z", "+00:00")).date()
        _require(source_day.isoformat() == published_date and published <= known, "PUBLICATION_TIME_MISMATCH")
    if sec:
        s = _closed(value["sec_source"], {"snapshot_id", "snapshot_at", "manifest_key", "document_id",
            "accession", "issuer_cik", "archive_url", "accepted_at", "retrieved_at", "recorded_at",
            "retrieval_receipt_id", "span_start_byte", "span_end_byte", "span_sha256"})
        _require(type(s["snapshot_id"]) is str and re.fullmatch(r"ffsecsrc_[0-9a-f]{64}", s["snapshot_id"]) is not None,
                 "SEC_SOURCE_INVALID")
        _require(type(s["accession"]) is str and re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", s["accession"]) is not None
                 and type(s["issuer_cik"]) is str and re.fullmatch(r"[0-9]{10}", s["issuer_cik"]) is not None,
                 "SEC_SOURCE_INVALID")
        for field in ("manifest_key", "document_id", "archive_url", "retrieval_receipt_id"):
            _require(type(s[field]) is str and 0 < len(s[field]) <= 700 and not any(ord(c) < 32 for c in s[field]), "SEC_SOURCE_INVALID")
        _require(s["document_id"] == value["source_key"] and value["publication_precision"] == "date"
                 and value["published_at"] is None, "SEC_SOURCE_BINDING_MISMATCH")
        _require(_instant(s["accepted_at"]) <= _instant(s["retrieved_at"]) <= _instant(s["recorded_at"])
                 <= _instant(s["snapshot_at"]) <= known <= datetime.now(timezone.utc), "SEC_SOURCE_CLOCK_INVALID")
        _integer(s["span_start_byte"], 0, value["source_byte_length"])
        _integer(s["span_end_byte"], s["span_start_byte"] + 1, value["source_byte_length"])
        _digest(s["span_sha256"])
    return _ref(value)


def validate_fact(value: dict) -> Reference:
    _require(type(value) is dict, "SCHEMA_INVALID")
    if value.get("schema") == SEGMENT_FACT_SCHEMA:
        return _validate_segment_fact(value)
    supplier = value.get("schema") == SUPPLIER_FACT_SCHEMA
    _closed(value, {"schema", "fact_id", "claim_key", "disclosure_id", "edition",
                    "revision", "previous", "review_revision", "subject_id", "object_id",
                    "subject_identity", "object_identity", "kind", "lifecycle", "product",
                    "platform", "amount", "economic_share", "span", "known_at"} | ({"qualification"} if supplier else set()))
    _require(value["schema"] in FACT_SCHEMAS, "SCHEMA_INVALID")
    _require(value["fact_id"] == fact_id(value["disclosure_id"], value["claim_key"]), "FACT_ID_MISMATCH")
    _reference(value["edition"], SEC_EDITION_SCHEMA if supplier else EDITION_SCHEMA)
    _integer(value["revision"], 1, MAX_REVISIONS)
    _require((value["revision"] == 1) == (value["previous"] is None), "PREDECESSOR_REQUIRED")
    if value["previous"] is not None:
        _reference(value["previous"], value["schema"])
    for field in ("review_revision", "subject_identity", "object_identity"):
        _digest(value[field])
    _identifier(value["subject_id"]); _identifier(value["object_id"])
    _require(value["subject_id"] != value["object_id"], "PARTY_IDENTITY_AMBIGUOUS")
    _require((value["kind"], value["lifecycle"]) ==
             (("disclosed_supplier", "reported_use") if supplier else ("product_integration", "planned")), "FACT_SPECIES_INVALID")
    for field in ("product", "platform"):
        _require(type(value[field]) is str and 0 < len(value[field]) <= 256 and len(value[field].encode("utf-8")) <= 256
                 and value[field].strip() == value[field], "FACT_SCOPE_INVALID")
    _require(value["amount"] is None and value["economic_share"] is None, "MAGNITUDE_NOT_ADMITTED")
    span = _closed(value["span"], {"start_byte", "end_byte", "text_sha256"})
    limit = MAX_SEC_SOURCE_BYTES if supplier else MAX_SOURCE_BYTES
    _integer(span["start_byte"], 0, limit)
    _integer(span["end_byte"], span["start_byte"] + 1, limit)
    _digest(span["text_sha256"])
    adopted = _instant(value["known_at"])
    if supplier:
        q = _closed(value["qualification"], {"direction", "identity_mode", "identity_observed_at", "evidence_revision"})
        _require(q["direction"] == "object_supplies_subject" and q["identity_mode"] == "current", "SUPPLIER_QUALIFICATION_INVALID")
        _require(_instant(q["identity_observed_at"]) <= adopted <= datetime.now(timezone.utc), "SUPPLIER_ADOPTION_CLOCK_INVALID")
        _digest(q["evidence_revision"])
    return _ref(value)


def _segment_span(value: object) -> dict:
    """A required, non-zero-length byte span; missing or empty is ``SPAN_REQUIRED``."""
    _require(type(value) is dict, "SPAN_REQUIRED")
    span = _closed(value, {"start_byte", "end_byte", "text_sha256"})
    _integer(span["start_byte"], 0, MAX_SEC_SOURCE_BYTES)
    _require(type(span["end_byte"]) is int and span["end_byte"] > span["start_byte"], "SPAN_REQUIRED")
    _integer(span["end_byte"], span["start_byte"] + 1, MAX_SEC_SOURCE_BYTES)
    _digest(span["text_sha256"])
    return span


def _segment_figure_span(value: object) -> dict:
    """One figure's own pinned byte span in the same document as the activity span."""
    span = _closed(value, {"start_byte", "end_byte", "text_sha256"})
    _integer(span["start_byte"], 0, MAX_SEC_SOURCE_BYTES)
    _require(type(span["end_byte"]) is int and span["end_byte"] > span["start_byte"], "FIGURE_SPAN_MISMATCH")
    _integer(span["end_byte"], span["start_byte"] + 1, MAX_SEC_SOURCE_BYTES)
    _digest(span["text_sha256"])
    return span


_FIGURE_WINDOW_BYTES = 2000
# One tokenizer decides what a filing prints. Alternatives are tried in this
# order at each position: comment (the empty forms ``<!-->`` and ``<!--->``
# end at once), CDATA section, opening tag in a strict attribute grammar
# (quoted values may hold '>'; an unquoted value holds no quote), closing tag,
# declaration or processing instruction, character reference, and last a tag
# opener that fits none of these. Such an opener is unreadable: everything
# from it to the end of the bytes counts as not printed.
_FIGURE_TOKEN = re.compile(
    rb"<!--(?:>|->|.*?(?:-->|--!>|\Z))"
    rb"|<!\[CDATA\[.*?(?:\]\]>|\Z)"
    rb"|<[A-Za-z][^\s<>/\"'=]*"
    rb"(?:(?:\s+|(?<=[\"']))[^\s<>/\"'=]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s<>\"'`]+))?)*"
    rb"\s*/?>"
    rb"|</[A-Za-z][^\s<>/\"'=]*\s*>"
    rb"|<[!?][^<>]*>"
    rb"|&(?:#[0-9]+;?|#[xX][0-9A-Fa-f]+;?|[A-Za-z0-9]+;?)"
    rb"|<(?=[A-Za-z/!?])", re.DOTALL)
_FIGURE_TAG_NAME = re.compile(rb"<(/?)([^\s<>/\"'=]+)")
_FIGURE_BLOCK_NAMES = frozenset(
    b"td th tr table thead tbody tfoot caption p div br hr li ul ol dl dt dd"
    b" h1 h2 h3 h4 h5 h6 section article blockquote pre".split())
# Elements whose content is raw text up to their own closing tag.
_FIGURE_RAWTEXT_NAMES = frozenset(
    b"script style title textarea xmp plaintext noembed noframes iframe noscript".split())
# Elements whose content a reader does not see as ordinary running text
# (matched on the local name, with any namespace prefix or none).
_FIGURE_HIDDEN_NAMES = frozenset(
    b"head header hidden template select datalist object svg math bdo".split())
_FIGURE_VOID_NAMES = frozenset(
    b"area base br col embed hr img input link meta param source track wbr".split())
_FIGURE_HIDDEN_STYLE = ("display:none", "visibility:hidden", "bidi-override")
_FIGURE_QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
_FIGURE_HIDDEN_ATTR = re.compile(r"\shidden(?=[\s=/>])")
_FIGURE_NEG_SIGN = re.compile(r"sign\s*=\s*[\"']?\s*[-−]")
_FIGURE_NBSP_REFS = frozenset((b"&#160;", b"&nbsp;", b"&#xa0;", b"&#XA0;"))
_FIGURE_BIDI = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
_FIGURE_TAG_KIND, _FIGURE_BLOCK_KIND, _FIGURE_DEAD_KIND, _FIGURE_REF_KIND = 1, 2, 3, 4
# Fix 6 (ruling 61): the check admits only markup it knows. An element open at
# the figure and every tag inside the window must carry one of these names (an
# inline-XBRL name needs a prefix and a colon); anything else is refused.
_FIGURE_KNOWN_NAMES = frozenset(
    b"html body div p span font b i u em strong small a br hr table thead tbody tfoot"
    b" tr td th caption col colgroup sup sub ul ol li h1 h2 h3 h4 h5 h6 center nobr"
    b" blockquote img".split())
_FIGURE_KNOWN_XBRL = frozenset((b"nonfraction", b"nonnumeric", b"continuation"))
_FIGURE_ATTR = re.compile(
    rb"(?:\s+|(?<=[\"']))([^\s<>/\"'=]+)(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s<>\"'`]+))?")
_FIGURE_DISPLAY = re.compile(r"(?:^|;)\s*display\s*:", re.IGNORECASE)
# Fix 7 (ruling 67). R7-5: a style that sets text direction cannot be read plainly.
_FIGURE_DIRECTION = re.compile(r"(?:^|;)\s*(?:direction|unicode-bidi)\s*:", re.IGNORECASE)
# R7-8: after an empty self-closed hidden cell, only blanks and then a cell opens or a row closes.
_FIGURE_EMPTY_CELL_NEXT = re.compile(
    rb"[ \t\r\n\f]*(?:<(?:td|th)(?=[ \t\r\n\f/>])|</tr[ \t\r\n\f]*>)", re.IGNORECASE)
# R8-4: an unprefixed html or body opening tag, anywhere in the document.
_FIGURE_ROOT_OPEN = re.compile(rb"<(html|body)(?=[ \t\r\n\f/>])", re.IGNORECASE)
# R8-2: a self-closed tag of these names stays open in a browser; refused anywhere.
_FIGURE_SC_REFUSED = frozenset(b"table thead tbody tfoot caption colgroup".split())
# R7-4: the table content model. A tag whose innermost open element is one of the
# table parents must be one that belongs there, and holds no text of its own.
_FIGURE_TABLE_PARENTS = frozenset(b"table thead tbody tfoot tr colgroup".split())
_FIGURE_TABLE_NEEDS = {
    b"tr": frozenset(b"table thead tbody tfoot".split()),
    b"td": frozenset((b"tr",)), b"th": frozenset((b"tr",)),
    b"thead": frozenset((b"table",)), b"tbody": frozenset((b"table",)),
    b"tfoot": frozenset((b"table",)), b"caption": frozenset((b"table",)),
    b"colgroup": frozenset((b"table",)), b"col": frozenset((b"colgroup", b"table")),
}


def _figure_blank(ch: str) -> bool:
    """A character that prints as plain horizontal space: ASCII whitespace or a
    space separator (Zs) other than U+1680, which prints as a stroke."""
    return ch in " \t\n\r\f\v" or (unicodedata.category(ch) == "Zs" and ch != "\u1680")


def _figure_tag_hidden(local: bytes, tok: bytes) -> bool:
    """An opening tag whose element content is not shown as running text."""
    if local in _FIGURE_HIDDEN_NAMES:
        return True
    text = tok.decode("utf-8", errors="ignore").lower()
    squeezed = "".join(html.unescape(text).split())
    if any(mark in squeezed for mark in _FIGURE_HIDDEN_STYLE):
        return True
    return _FIGURE_HIDDEN_ATTR.search(_FIGURE_QUOTED.sub('""', text)) is not None


def _figure_name_known(name: bytes) -> bool:
    """R6-2: a name this check knows: the fixed list, or an inline-XBRL
    ``nonFraction``/``nonNumeric``/``continuation`` with exactly one prefix."""
    if b":" not in name:
        return name in _FIGURE_KNOWN_NAMES
    prefix, _, local = name.partition(b":")
    return bool(prefix) and b":" not in local and local in _FIGURE_KNOWN_XBRL


def _figure_tag_style(tok: bytes) -> tuple[bool, bool]:
    """R6-3 and R6-4 on one opening tag: ``(unreadable, display)``. Unreadable is
    a ``style`` value holding a backslash, ``/*`` or ``&``, or any ``dir``
    attribute; display is a ``display`` declaration in the style value. Fix 7:
    a ``direction`` or ``unicode-bidi`` declaration in the style value (R7-5) and
    an ``img`` ``alt`` value holding an ASCII digit (R7-6) are unreadable too."""
    nm = _FIGURE_TAG_NAME.match(tok)
    unreadable = display = False
    if nm is None:
        return False, False
    is_img = nm.group(2).lower() == b"img" and not nm.group(1)
    for m in _FIGURE_ATTR.finditer(tok, nm.end()):
        attr = m.group(1).lower()
        value = (m.group(2) or b"")
        if value[:1] in (b'"', b"'"):
            value = value[1:-1]
        if attr == b"dir":
            unreadable = True
        elif attr == b"alt" and is_img:
            if re.search(rb"[0-9]", value):
                unreadable = True
        elif attr == b"style":
            if b"\\" in value or b"/*" in value or b"&" in value:
                unreadable = True
            style = value.decode("utf-8", errors="ignore")
            if _FIGURE_DIRECTION.search(style):
                unreadable = True
            if _FIGURE_DISPLAY.search(style):
                display = True
    return unreadable, display


# Fix 9 (ruling 80), refusals only. R9-1: a right-to-left character, or an explicit direction
# control (A5), anywhere from byte 0 to the scan limit.
_FIGURE_R9_BIDI_CLASSES = frozenset(("R", "AL", "AN", "LRE", "RLE", "LRO", "RLO", "PDF",
                                     "LRI", "RLI", "FSI", "PDI"))
# Computed once per document (see _figure_bidi_offsets); at most four documents are kept.
_FIGURE_BIDI_CACHE: dict = {}
# R9-2: comment and processing-instruction forms the two readings split differently.
_FIGURE_R9_MARK = re.compile(rb"<[?!]")
_FIGURE_R9_XMLDECL = re.compile(rb"<\?xml[ \t\r\n]")
_FIGURE_R9_DOCTYPE = re.compile(rb"<!DOCTYPE[ \t\r\n]", re.IGNORECASE)
_FIGURE_R9_ELEMENT = re.compile(rb"<[A-Za-z]")
# R9-3: a namespace declaration that moves an element out of XHTML.
_FIGURE_R9_XMLNS = re.compile(
    rb"(?<=[\s\"'])xmlns(?::([^\s<>/\"'=]+))?\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s<>\"'`]+)",
    re.IGNORECASE)
_FIGURE_R9_XHTML_NS = "http://www.w3.org/1999/xhtml"
# R9-3b: a prefix bound to the XHTML namespace is refused too (an XML reader gives it XHTML meaning).
_FIGURE_R9_FOREIGN_NS = frozenset(("http://www.w3.org/2000/svg", "http://www.w3.org/1998/Math/MathML",
                                   "http://www.w3.org/1999/xhtml"))
# R9-4: a numeric reference to U+0080..U+009F (a browser maps it to another character).
# R9-1 (A2): every bidi R/AL/AN character of the document, literal or as a reference.
_FIGURE_R9_HIGH = re.compile(rb"[\x80-\xff]+")
_FIGURE_R9_ANYREF = re.compile(rb"&(?:#[0-9]+;?|#[xX][0-9A-Fa-f]+;?|[A-Za-z0-9]+;?)")
# R9-6 (A4): a declared encoding other than UTF-8 or ASCII.
_FIGURE_R9_ENCODINGS = frozenset(("utf-8", "ascii", "us-ascii"))
_FIGURE_R9_XMLDECL_ENC = re.compile(rb"<\?xml[ \t\r\n][^>]*?encoding\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
_FIGURE_R9_META = re.compile(rb"<meta(?=[\s/>])(?:\"[^\"]*\"|'[^']*'|[^>\"'])*>?", re.IGNORECASE)
_FIGURE_R9_CHARSET = re.compile(r"charset\s*=\s*[\"']?\s*([^\s\"';>/]*)", re.IGNORECASE)
_FIGURE_R9_NUMREF = re.compile(rb"&#(?:([0-9]+)|[xX]([0-9A-Fa-f]+))")
# A numeric reference of 21 or more figures is no character, and html.unescape raises ValueError on
# thousands of them: refuse it here, before any unescape (the scan's own call included).
_FIGURE_R9_LONGREF = re.compile(rb"&#(?:[0-9]{21}|[xX][0-9A-Fa-f]{21})")


def _figure_bidi_offsets(raw: bytes) -> tuple:
    """Sorted byte offsets of every character of bidirectional class R, AL or AN in ``raw``,
    written literally or as a character reference. Computed once per document and cached."""
    cached = _FIGURE_BIDI_CACHE.get(raw)
    if cached is not None:
        return cached
    found = []
    for run in _FIGURE_R9_HIGH.finditer(raw):
        at = run.start()
        for ch in run.group(0).decode("utf-8", errors="surrogateescape"):
            if unicodedata.bidirectional(ch) in _FIGURE_R9_BIDI_CLASSES:
                found.append(at)
            at += len(ch.encode("utf-8", errors="surrogateescape"))
    for ref in _FIGURE_R9_ANYREF.finditer(raw):
        text = ref.group(0).decode("ascii")
        if len(text) < 30 and any(unicodedata.bidirectional(ch) in _FIGURE_R9_BIDI_CLASSES
                                  for ch in html.unescape(text)):
            found.append(ref.start())
    result = tuple(sorted(found))
    if len(_FIGURE_BIDI_CACHE) >= 4:
        _FIGURE_BIDI_CACHE.clear()
    _FIGURE_BIDI_CACHE[raw] = result
    return result


def _figure_r9(raw: bytes, window_lo: int, limit: int) -> None:
    """Fix 9 (rulings 80 and 81): R9-1 to R9-6 on ``raw`` up to the scan limit; each only refuses.

    R9-1 bidi characters and direction controls, R9-2 comment and processing-instruction
    forms, R9-3 foreign and XHTML-prefixed namespaces, R9-4 numeric references to
    U+0080 to U+009F, R9-5 is in ``sec_segment_adoption`` (replay types), R9-6 declared encoding.
    """
    # R9-2, from byte 0: the empty comment forms, any processing instruction but one
    # XML declaration at byte 0 (after a byte-order mark), any ``<!`` that is neither a
    # comment nor the one doctype before the first element (a CDATA section included).
    _require(raw.find(b"<!-->", 0, limit + 4) < 0 and raw.find(b"<!--->", 0, limit + 5) < 0,
             "FIGURE_SPAN_MISMATCH")
    bom = 3 if raw.startswith(b"\xef\xbb\xbf") else 0
    first = _FIGURE_R9_ELEMENT.search(raw)
    doctypes = 0
    for mark in _FIGURE_R9_MARK.finditer(raw, 0, limit):
        at = mark.start()
        if raw.startswith(b"<!--", at):
            continue
        if mark.group(0) == b"<?":
            _require(at == bom and _FIGURE_R9_XMLDECL.match(raw, at) is not None, "FIGURE_SPAN_MISMATCH")
            continue
        doctypes += 1
        _require(doctypes == 1 and _FIGURE_R9_DOCTYPE.match(raw, at) is not None
                 and (first is None or at < first.start()), "FIGURE_SPAN_MISMATCH")
    # R9-3, from byte 0, on any tag.
    for decl in _FIGURE_R9_XMLNS.finditer(raw, 0, limit):
        value = decl.group(2)
        if value[:1] in (b'"', b"'"):
            value = value[1:-1]
        value = html.unescape(value.decode("utf-8", errors="ignore"))
        if decl.group(1) is None:
            _require(value == _FIGURE_R9_XHTML_NS, "FIGURE_SPAN_MISMATCH")
        else:
            _require(value not in _FIGURE_R9_FOREIGN_NS, "FIGURE_SPAN_MISMATCH")
    # Fix 9b (B3): invalid UTF-8 anywhere from byte 0 to the scan limit (a multi-byte character cut
    # by the limit itself is not invalid).
    try:
        codecs.getincrementaldecoder("utf-8")("strict").decode(raw[:limit])
    except UnicodeDecodeError:
        raise DisclosureError("FIGURE_SPAN_MISMATCH") from None
    # Fix 9b (B4): the comment end ``--!>``, and a comment whose body holds ``--``, from byte 0 to the limit.
    _require(raw.find(b"--!>", 0, limit + 3) < 0, "FIGURE_SPAN_MISMATCH")
    at = raw.find(b"<!--", 0, limit)
    while at >= 0:
        close = raw.find(b"-->", at + 4)
        if close < 0:
            break
        _require(raw.find(b"--", at + 4, min(close, limit)) < 0, "FIGURE_SPAN_MISMATCH")
        at = raw.find(b"<!--", close + 3, limit)
    # R9-6 (A4): a declared encoding other than UTF-8 or ASCII, and an ESC byte, before the scan limit.
    _require(raw.find(b"\x1b", 0, limit) < 0, "FIGURE_SPAN_MISMATCH")
    declared = _FIGURE_R9_XMLDECL_ENC.match(raw, bom, limit)
    _require(declared is None or declared.group(1).decode("ascii", errors="replace").strip().lower()
             in _FIGURE_R9_ENCODINGS, "FIGURE_SPAN_MISMATCH")
    for meta in _FIGURE_R9_META.finditer(raw, 0, limit):
        tag = html.unescape(meta.group(0).decode("utf-8", errors="ignore"))
        for charset in _FIGURE_R9_CHARSET.finditer(tag):
            _require(charset.group(1).lower() in _FIGURE_R9_ENCODINGS, "FIGURE_SPAN_MISMATCH")
    # R9-1 (A2): any right-to-left character from byte 0 to the scan limit.
    offsets = _figure_bidi_offsets(raw)
    _require(not offsets or offsets[0] >= limit, "FIGURE_SPAN_MISMATCH")
    # R9-4, in the window (2,000 bytes before the span, to the scan limit).
    window = raw[max(0, window_lo):limit]
    for ref in _FIGURE_R9_NUMREF.finditer(window):
        number = (ref.group(1) or ref.group(2)).lstrip(b"0")
        if len(number) <= 4:
            _require(not 0x80 <= int(number or b"0", 10 if ref.group(1) else 16) <= 0x9F,
                     "FIGURE_SPAN_MISMATCH")


def _figure_scan(raw: bytes, start: int, end: int) -> tuple[list, bool]:
    """Tokenise ``raw`` from byte 0 to just past the right-hand window.

    Returns ``(tokens, ix_negative)``. ``tokens`` is the document-order list of
    ``(start, end, kind, shown)`` for everything that is not plain text: a tag or
    comment (TAG), a block-level tag (BLOCK), a character reference (REF, with the
    text it prints in ``shown``) and a region that is not printed (DEAD: the
    content of a raw-text or hidden element, tags included, and everything from
    an unreadable tag opener to the end). The bytes between tokens are the
    printed text. ``ix_negative`` is true when any inline-XBRL ``nonFraction``
    element still open at the span start, or opened inside the span, carries a
    negative ``sign`` attribute (any prefix or none, any quoting, entity-decoded).
    A ``/>`` ending is never honoured: an element counts as open until its own
    closing tag, which can only add refusals.

    Fix 6 (ruling 61), refusals only. R6-1: inside a hidden region the elements
    opened there are kept on a stack (a self-closed non-void tag opens one); a
    closing tag that is not the innermost open element, or the region's own
    element once the stack is empty, makes the region last to the end of the
    document. Fix 7 (ruling 67) R7-1: a prefixed self-closed tag (``ix:hidden/``)
    is pushed flagged. A closing tag walks down skipping flagged entries of
    another name; reaching a flagged entry of its own name makes the region
    permanent, because HTML closes the self-closed element and XML closes an
    outer one, so the two readings disagree. R7-2: only an unprefixed name is raw
    text. R7-3: the shown elements keep one HTML-reading stack; a stray or
    mis-nested closing tag in the window is refused, and an sc tag (a non-void
    tag ending ``/>``) is closed by the XML reading as well. R7-4: the table
    content model (``td`` needs ``tr`` and so on; nothing else, and no text or
    reference, directly inside a table parent). R7-5/R7-6: a ``direction`` or
    ``unicode-bidi`` style, and an ``img`` ``alt`` holding a digit, are unreadable.
    R6-2/R6-3: every element open at the span start, and every shown
    tag within the window of the span, needs a known name and no unreadable
    ``style`` value or ``dir`` attribute, else FIGURE_SPAN_MISMATCH (a tag that
    only opens or continues a hidden region is not checked). R6-4: a block-level
    tag whose own ``style`` holds a ``display`` declaration, and its closing tag,
    is an ordinary inline tag, not a separator.
    """
    tokens: list = []
    stack: list = []      # open nonFraction elements, True when flagged negative
    enclosing = None      # any(stack) frozen at the span start
    inner = False
    hidden = None         # (name, inner names, start, permanent) in a not-shown element
    # open shown elements, one HTML-reading stack: (name, refused-if-in-scope, display, sc)
    shown_open: list = []
    limit = end + _FIGURE_WINDOW_BYTES
    window_lo = start - _FIGURE_WINDOW_BYTES
    pos = prev_end = 0
    # R8-1: a vertical tab is a blank to the tokenizer's ``\s`` and not to a browser.
    _require(raw.find(b"\x0b", 0, limit) < 0, "FIGURE_SPAN_MISMATCH")
    # R9-4 (support): the root-tag loop below unescapes tag text anywhere in the document.
    _require(_FIGURE_R9_LONGREF.search(raw) is None, "FIGURE_SPAN_MISMATCH")
    # R8-4: a browser copies the attributes of any later html/body start tag onto
    # the root or body element, wherever it lies; so over the whole document.
    roots = {b"html": 0, b"body": 0}
    for rm in _FIGURE_ROOT_OPEN.finditer(raw):
        rname = rm.group(1).lower()
        roots[rname] += 1
        rtok = _FIGURE_TOKEN.match(raw, rm.start())
        _require(roots[rname] == 1 and rtok is not None and rtok.group(0) != b"<",
                 "FIGURE_SPAN_MISMATCH")
        runreadable, rdisplay = _figure_tag_style(rtok.group(0))
        _require(not (runreadable or rdisplay or _figure_tag_hidden(rname, rtok.group(0))),
                 "FIGURE_SPAN_MISMATCH")
    _figure_r9(raw, window_lo, limit)

    def table_text(lo: int, hi: int, *, reference: bool = False) -> None:
        # R7-4: text, or a character reference, directly inside a table parent.
        if not shown_open or shown_open[-1][0] not in _FIGURE_TABLE_PARENTS:
            return
        if not reference and not raw[lo:hi].strip(b" \t\r\n\f"):
            return
        _require(not hi > window_lo, "FIGURE_SPAN_MISMATCH")
        top = shown_open[-1]
        shown_open[-1] = (top[0], True, top[2], top[3])

    while True:
        m = _FIGURE_TOKEN.search(raw, pos)
        if m is None or m.start() >= limit:
            if hidden is None:
                table_text(prev_end, min(len(raw) if m is None else m.start(), limit))
            break
        s, e = m.span()
        tok = m.group(0)
        pos = e
        if hidden is None and prev_end < s:
            table_text(prev_end, s)
        if enclosing is None and s >= start:
            enclosing = any(stack)
            _require(not any(item[1] for item in shown_open), "FIGURE_SPAN_MISMATCH")
        if tok[:1] == b"&":
            text = tok.decode("ascii")
            shown = html.unescape(text)
            if shown == text:      # not a reference: the '&' is literal text
                pos = s + 1
            else:
                if hidden is None:
                    table_text(s, e, reference=True)
                    tokens.append((s, e, _FIGURE_REF_KIND, shown))
                prev_end = e
            continue
        prev_end = e
        if tok == b"<":            # a tag opener that never closes
            hidden = (b"", [], hidden[2] if hidden is not None else s, True)
            break
        if tok.startswith(b"<![CDATA["):
            # XHTML prints a CDATA section, HTML reads it as a comment that ends
            # at the first '>': what it shows is not established, so not printed.
            if hidden is None:
                tokens.append((s, e, _FIGURE_DEAD_KIND, ""))
            continue
        if tok.startswith(b"<!--"):
            if hidden is None:
                tokens.append((s, e, _FIGURE_TAG_KIND, ""))
            continue
        nm = _FIGURE_TAG_NAME.match(tok)
        closing = nm is not None and bool(nm.group(1))
        name = nm.group(2).lower() if nm is not None else b""
        local = name.rsplit(b":", 1)[-1]
        decl = tok[1:2] in (b"!", b"?")
        if not closing and name in _FIGURE_RAWTEXT_NAMES:     # R7-2: unprefixed names only
            if hidden is None:
                unreadable, _display = _figure_tag_style(tok)
                _require(not (e > window_lo and (not _figure_name_known(name) or unreadable)),
                         "FIGURE_SPAN_MISMATCH")
            close = re.compile(rb"</" + re.escape(name) + rb"(?=[\s/>])[^>]*>",
                               re.IGNORECASE).search(raw, e)
            stop = close.end() if close is not None else len(raw)
            if hidden is None:
                tokens.append((s, stop, _FIGURE_DEAD_KIND, ""))
            pos = prev_end = stop
            continue
        if hidden is not None:
            hname, names, hstart, permanent = hidden
            if permanent or decl:
                continue
            if closing:
                # R7-1: walk down skipping flagged (prefixed self-closed) entries not
                # named like the closing tag; the first other entry decides.
                i = len(names) - 1
                while i >= 0 and names[i][1] and names[i][0] != name:
                    i -= 1
                if i >= 0:
                    if names[i][1] or names[i][0] != name:
                        hidden = (hname, names, hstart, True)   # readings disagree / broken nesting
                    else:
                        del names[i:]
                elif name == hname:
                    tokens.append((hstart, e, _FIGURE_DEAD_KIND, ""))
                    hidden = None
                else:
                    hidden = (hname, names, hstart, True)
            elif name not in _FIGURE_VOID_NAMES:
                names.append((name, tok.endswith(b"/>") and b":" in name))
            continue
        if not closing and name not in _FIGURE_VOID_NAMES and _figure_tag_hidden(local, tok):
            if (tok.endswith(b"/>") and name in (b"td", b"th")
                    and _FIGURE_EMPTY_CELL_NEXT.match(raw, e) is not None):
                # R7-8: an empty closed hidden cell; the next token is not consumed.
                # Recorded as a plain tag: a DEAD token met before any neighbour is
                # FIGURE_SIGN_UNSUPPORTED, which would refuse the honest row again.
                tokens.append((s, e, _FIGURE_TAG_KIND, ""))
                continue
            hidden = (name, [], s, False)
            continue
        display = False
        if not decl:
            unreadable, display = _figure_tag_style(tok)
            bad = unreadable or not _figure_name_known(name)
            if closing:
                # R7-3: one HTML-reading stack of the shown elements.
                _require(not (e > window_lo and bad), "FIGURE_SPAN_MISMATCH")
                idx = next((i for i in range(len(shown_open) - 1, -1, -1)
                            if shown_open[i][0] == name), None)
                if idx is None:        # a stray closing tag: no separator, pops nothing
                    # R7-3a: with nothing open its opening tag lies before the excerpt.
                    # R8-3: with anything open it is a nesting fault, refused anywhere.
                    _require(not shown_open, "FIGURE_SPAN_MISMATCH")
                    display = True
                else:
                    # R8-3: a mis-nested closing tag is refused wherever it lies.
                    _require(not any(not item[3] for item in shown_open[idx + 1:]),
                             "FIGURE_SPAN_MISMATCH")
                    found = shown_open[idx]
                    del shown_open[idx:]
                    display = found[2]
                    if found[3]:       # the XML reading closed the nearest lower same-name element
                        for j in range(len(shown_open) - 1, -1, -1):
                            if shown_open[j][0] == name:
                                low = shown_open[j]
                                shown_open[j] = (name, low[1], low[2], True)
                                display = display or low[2]
                                break
            else:
                sc = tok.endswith(b"/>") and name not in _FIGURE_VOID_NAMES
                # R8-2: a browser leaves a self-closed table part open.
                _require(not (sc and name in _FIGURE_SC_REFUSED), "FIGURE_SPAN_MISMATCH")
                if name in (b"td", b"th"):
                    if shown_open and shown_open[-1][3] and shown_open[-1][0] in (b"td", b"th"):
                        shown_open.pop()
                elif name == b"tr":
                    if shown_open and shown_open[-1][3] and shown_open[-1][0] in (b"td", b"th"):
                        shown_open.pop()
                    if shown_open and shown_open[-1][3] and shown_open[-1][0] == b"tr":
                        shown_open.pop()
                # R7-4: the table content model.
                innermost = shown_open[-1][0] if shown_open else None
                needs = _FIGURE_TABLE_NEEDS.get(name)
                if needs is not None:
                    bad = bad or (innermost is not None and innermost not in needs)
                elif innermost in _FIGURE_TABLE_PARENTS:
                    bad = True
                _require(not (e > window_lo and bad), "FIGURE_SPAN_MISMATCH")
                if name not in _FIGURE_VOID_NAMES:
                    shown_open.append((name, bad, display, sc))
        if local == b"nonfraction":
            if closing:
                if stack:
                    stack.pop()
            else:
                attrs = html.unescape(tok.decode("utf-8", errors="ignore")).casefold()
                negative = _FIGURE_NEG_SIGN.search(attrs) is not None
                stack.append(negative)
                if negative and start <= s < end:
                    inner = True
        block = (name in _FIGURE_BLOCK_NAMES and not display
                 and (closing or not _figure_tag_hidden(local, tok)))
        tokens.append((s, e, _FIGURE_BLOCK_KIND if block else _FIGURE_TAG_KIND, ""))
    if hidden is not None:
        tokens.append((hidden[2], len(raw), _FIGURE_DEAD_KIND, ""))
    if enclosing is None:
        enclosing = any(stack)
        _require(not any(item[1] for item in shown_open), "FIGURE_SPAN_MISMATCH")
    return tokens, bool(enclosing or inner)


def _figure_printed_text(raw: bytes, tokens: list, start: int, end: int) -> str:
    """Rules 0 and 1: the span sits in printed text, and the text it prints.

    Rule 0: no span edge lies strictly inside a tag, comment or character
    reference, and no byte of the span lies in a region that is not printed.
    Rule 1: drop the tags and comments inside the span, fold the four literal
    no-break-space references and every blank character to one space, refuse any
    other reference and any leftover ``<``/``>``/``&``, collapse runs of spaces
    and strip the ends.
    """
    pieces = []
    pos = start
    for s, e, kind, _shown in tokens:
        if e <= start:
            continue
        if s >= end:
            break
        _require(kind != _FIGURE_DEAD_KIND and s >= start and e <= end, "FIGURE_SPAN_MISMATCH")
        pieces.append(raw[pos:s])
        if kind == _FIGURE_REF_KIND:
            _require(raw[s:e] in _FIGURE_NBSP_REFS, "FIGURE_SPAN_MISMATCH")
            pieces.append(b" ")
        pos = e
    pieces.append(raw[pos:end])
    try:
        text = b"".join(pieces).decode("utf-8")
    except UnicodeDecodeError:
        raise DisclosureError("FIGURE_SPAN_MISMATCH") from None
    _require("<" not in text and ">" not in text and "&" not in text, "FIGURE_SPAN_MISMATCH")
    folded = "".join(" " if _figure_blank(ch) else ch for ch in text)
    return " ".join(part for part in folded.split(" ") if part)


def _figure_not_cut_from_number(raw: bytes, start: int, end: int) -> None:
    """Rule 3: the span is not cut out of a longer number (raw bytes, no skipping).

    Refuse an ASCII digit immediately before/after the span, and a ',' or '.'
    immediately before/after that is itself glued to an ASCII digit. A sentence
    end ("... of 54,602.") is allowed.
    """
    def digit(byte):
        return byte is not None and 48 <= byte <= 57

    before = raw[start - 1] if start > 0 else None
    after = raw[end] if end < len(raw) else None
    _require(not digit(before) and not digit(after), "FIGURE_SPAN_MISMATCH")
    if before in (44, 46) and start >= 2:
        _require(not digit(raw[start - 2]), "FIGURE_SPAN_MISMATCH")
    if after in (44, 46) and end + 1 < len(raw):
        _require(not digit(raw[end + 1]), "FIGURE_SPAN_MISMATCH")


def _figure_side(raw: bytes, tokens: list, lo: int, hi: int, *, left: bool) -> list:
    """What is printed in ``raw[lo:hi]``, in outward order from the span edge.

    Each item is one printed character (a ``str``) or a marker (an ``int``): TAG,
    BLOCK or DEAD. A reference contributes the characters it prints; one cut by
    the window edge contributes nothing. Text cut mid-character is dropped.
    """
    out: list = []
    pos = lo
    for s, e, kind, shown in tokens:
        if e <= lo:
            continue
        if s >= hi:
            break
        if s > pos:
            out.extend(raw[pos:s].decode("utf-8", errors="ignore"))
        if kind == _FIGURE_REF_KIND:
            if s >= lo and e <= hi:
                out.extend(shown)
        else:
            out.append(kind)
        pos = max(pos, e)
    if pos < hi:
        out.extend(raw[pos:hi].decode("utf-8", errors="ignore"))
    return out[::-1] if left else out


def _figure_fragment_neighbour(side: list) -> str | None:
    """Rule 3, second part: the first non-skipped character before the nearest
    block boundary, walking outward. Tags are passed over; a BLOCK tag or a
    not-printed region ends the walk. Skips whitespace, category Zs/Zl/Zp/Cf and
    ``,`` ``.`` ``'`` U+2019. A returned character of category N is a number
    fragment."""
    for item in side:
        if type(item) is int:
            if item == _FIGURE_TAG_KIND:
                continue
            return None
        if item.isspace() or unicodedata.category(item) in ("Zs", "Zl", "Zp", "Cf"):
            continue
        if item in ",.'’":
            continue
        return item
    return None


def _figure_neighbour(side: list) -> str:
    """Rule 4: the outward printed text from the first non-skipped character.

    Tags and block tags are passed over on the way to the neighbour; blank
    characters and at most one ``$`` are skipped (category Cf is NOT skipped).
    After the neighbour the text runs to the next block tag. A not-printed region met before any
    neighbour is FIGURE_SIGN_UNSUPPORTED: what stands next to the figure cannot
    be established. Returns ``""`` when the window holds nothing else.
    """
    dollars = 0
    chars: list = []
    for item in side:
        if type(item) is int:
            if item == _FIGURE_DEAD_KIND:
                _require(bool(chars), "FIGURE_SIGN_UNSUPPORTED")
                break
            if item == _FIGURE_BLOCK_KIND and chars:
                break      # the neighbour's own text ends at the next block
            continue
        if not chars:
            if _figure_blank(item):
                continue
            if item == "$" and dollars < 1:
                dollars += 1
                continue
        chars.append(item)
    return "".join(chars)


def _figure_neighbour_allowed(ch: str, *, left: bool) -> bool:
    """Rule 4 allowlist: an ASCII digit, a cased letter whose base is an ASCII
    letter, or one of the few punctuation marks that cannot carry a sign on that
    side. Every other neighbour is a potential sign mark and is refused."""
    if ch in "0123456789":
        return True
    if unicodedata.category(ch) in ("Lu", "Ll"):
        base = unicodedata.normalize("NFKD", ch)[:1]
        return base.isascii() and base.isalpha()
    punct = (".", ",", ";", ":", ")", "]") if left else (".", ",", ";", ":", "(", "[")
    return ch in punct


def _figure_credit_mark(text: str, *, left: bool) -> bool:
    """Rule 4: the neighbour text is an accounting credit/debit mark, ``CR`` or
    ``DR`` in any letter case, standing alone (no letter beyond it). On the left
    one full stop between the mark and the figure is passed over."""
    if left and text[:1] == ".":
        text = text[1:]
    word = text[:2][::-1] if left else text[:2]
    beyond = text[2:3]
    return (word.casefold() in ("cr", "dr")
            and not (beyond and unicodedata.category(beyond)[0] == "L"))


def _verify_figure_span(name: str, span: dict, text: str, sign: str, raw: bytes,
                        *, whole_document: bool = True) -> None:
    """Replay one figure span against pinned bytes: the span IS the figure.

    ``raw`` is the whole document at replay (``whole_document=True``, the default)
    but only the activity span at prepare (``whole_document=False``), where the
    figure span is relative to it. Prepare is an early check on an excerpt and
    cannot see markup that opened before the excerpt; replay on the whole
    document is the gate, and ``publish_disclosure`` runs it before any write.

    The types, bounds and sha256 are checked first. ``raw`` is then tokenised
    from byte 0 (``_figure_scan``) and six closed rules run, in order:

    0. The span sits in printed text. No span edge lies strictly inside a tag, a
       comment, a CDATA section or a character reference, and no byte of the span
       lies in a region that is not printed: the content of ``script``, ``style``,
       ``title`` and the other raw-text elements; of ``head``, an inline-XBRL
       ``header``/``hidden`` (any prefix or none) and the other hidden elements;
       of an element styled ``display:none``, ``visibility:hidden`` or
       ``bidi-override`` or carrying a ``hidden`` attribute; or anything after a
       tag opener the strict tag grammar cannot read. At prepare, an excerpt whose first angle
       bracket is ``>`` (it starts inside a tag) is refused.
    1. Printed text P: drop the tags and comments inside the span, fold the
       literal ``&#160;``/``&nbsp;``/``&#xa0;``/``&#XA0;`` and every blank
       character (ASCII whitespace, or a space separator other than U+1680) to
       one space, refuse any other reference and any leftover ``<``/``>``/``&``,
       collapse runs of spaces and strip the ends.
    2. Closed shapes: ``text`` must full-match the ``_FIGURE_TEXT`` grammar
       (zero, grouped thousands, or plain digits with no leading zero, at most
       21 digits) and P must full-match exactly one of PLUS ``$? s T``,
       MINUS-parentheses ``$? s ( s $? s T s )`` or MINUS-leading-sign
       ``$? s [-−] s $? s T`` (``s`` = an optional single space, ``T`` =
       ``re.escape(text)``). The shape decides the sign; a shape sign differing
       from the declared sign is FIGURE_SIGN_UNSUPPORTED.
    3. Not cut from a longer number: on the raw bytes, refuse an ASCII digit
       immediately before/after the span, or a ','/'.' before/after that is itself
       glued to an ASCII digit. Then, in the printed text of a <=2000-byte window
       each side, walk outward to the nearest block-level tag skipping
       whitespace, Zs/Zl/Zp/Cf and ``,`` ``.`` ``'`` U+2019; a first non-skipped
       character of category N (a number fragment) is FIGURE_SPAN_MISMATCH. On
       the right, a neighbour ``.`` or ``,`` directly followed by a digit in the
       same block (inline tags passed over) is FIGURE_SPAN_MISMATCH, so a decimal
       part printed in the next cell is caught and a sentence end is not.
    4. No sign mark left outside the span: in the same windows walk outward over
       the printed text, passing over tags and skipping blank characters and at
       most one '$' (Cf is NOT skipped). No neighbour because raw ends passes,
       except on the LEFT at prepare. No neighbour without reaching raw's end is
       FIGURE_SIGN_UNSUPPORTED, as is a not-printed region met before any
       neighbour. A neighbour is allowed only if it is an ASCII digit, a cased
       letter whose base is an ASCII letter, or LEFT one of ``. , ; : ) ]`` /
       RIGHT one of ``. , ; : ( [``; every other neighbour is
       FIGURE_SIGN_UNSUPPORTED. So is a neighbouring ``CR``/``DR`` mark in any
       letter case standing alone, on either side; a bidirectional embedding,
       override or isolate control anywhere in the left window; and, for a MINUS
       shape, a letter or digit printed directly against the span's left edge
       (``COVID-19``, ``X-1234``).
    5. An inline-XBRL negative ``sign`` on any ``nonFraction`` element open at the
       span start or opened inside the span is never read as plus: with a
       declared '+' it is FIGURE_SIGN_UNSUPPORTED. This rule only refuses; the
       printed shape in rule 2 still decides the sign.

    Fix 6 (ruling 61) only adds refusals; the check admits markup it knows. R6-1:
    a hidden region whose nesting is broken stays hidden to the end of the
    document. R6-2: every element open at the span and every tag in the window
    needs a known name. R6-3: a ``style`` value holding a backslash, ``/*`` or
    ``&``, or any ``dir`` attribute, is refused there. R6-4: a block tag that is
    hidden or carries a ``display`` declaration is not a separator in rules 3 and
    4. Pre-2001 SGML text filings are refused (accepted limit). Fix 7 (ruling 67)
    adds R7-1 to R7-6, described in ``_figure_scan``, with the same property.
    Accepted limits (ruling 70): a table tag is tested against the table content
    model only when something is open (a document with no root element passes it);
    a stray closing tag with nothing open is ignored (a fragment). R7-8, the one
    change that admits more than before: a hidden self-closed ``td``/``th`` followed
    only by blanks and then an opening ``td``/``th`` or a closing ``tr`` is an
    empty closed cell and opens no hidden region.
    Fix 8 (ruling 73), refusals only: R8-1 a vertical tab (0x0B) in the bytes the
    scan covers; R8-2 a self-closed ``table``, ``thead``, ``tbody``, ``tfoot``,
    ``caption`` or ``colgroup`` (a browser leaves it open); R8-3 a mis-nested
    closing tag, or a stray one with anything open, refuses wherever it lies, not
    only in the window. A page that is not well formed is refused wherever the
    fault lies, so plain-HTML filings with unclosed elements are refused (accepted
    limit); Inline XBRL filings are well formed XHTML. Ruling 74, R8-4: over the
    whole document, more than one unprefixed ``html`` tag or more than one
    ``body`` tag refuses, as does any such tag that is hidden, unreadable or
    carries a ``display`` declaration (a browser merges the attributes of a later
    one onto the root element, even after the figure). A match inside a comment,
    a script or an attribute value refuses too (accepted, refusal only).
    Fix 9 (ruling 80, addendum 81), refusals only: R9-1 a character of bidirectional class
    R, AL or AN, literal or as a reference, anywhere from byte 0 to the scan limit (blanks
    collapse on screen, so the window is not enough; computed once per document); R9-6 a
    declared encoding other than UTF-8 or ASCII (XML declaration or a meta charset) and a 0x1B
    byte before the scan limit; R9-3b an ``xmlns:`` prefix bound to the XHTML namespace; R9-2 from byte 0 to the scan
    limit, the strings ``<!-->`` and ``<!--->``, a processing instruction other than
    one XML declaration at byte 0, and a ``<!`` that is neither a comment nor the one
    doctype before the first element (a CDATA section included); R9-3 an unprefixed
    ``xmlns`` that is not the XHTML namespace, or an ``xmlns:`` prefix bound to the
    SVG or MathML namespace; R9-4 a numeric reference to U+0080 to U+009F in the window.

    Known limits, left to the ratifier who reads the rendered excerpt: the
    meaning of nearby words ("loss", "credit"), the stated scale, and invisibility
    produced by a style sheet class or by CSS other than the three forms above.
    """
    # Fix 9b (B1): every argument is shape-checked before its first use, so only a DisclosureError
    # can leave for a malformed span, text, sign or page.
    _require(type(span) is dict and set(span) == {"start_byte", "end_byte", "text_sha256"}
             and type(span["start_byte"]) is int and type(span["end_byte"]) is int
             and type(span["text_sha256"]) is str, "FIGURE_SPAN_MISMATCH")
    _require(type(raw) is bytes and type(text) is str, "FIGURE_SPAN_MISMATCH")
    _require(type(sign) is str, "FIGURE_SIGN_UNSUPPORTED")
    start, end = span["start_byte"], span["end_byte"]
    _require(0 <= start < end <= len(raw), "FIGURE_SPAN_MISMATCH")
    _require(hashlib.sha256(raw[start:end]).hexdigest() == span["text_sha256"], "FIGURE_SPAN_MISMATCH")
    _require(_FIGURE_TEXT.fullmatch(text) is not None, "FIGURE_SPAN_MISMATCH")
    if not whole_document:
        first = re.search(rb"[<>]", raw)
        _require(first is None or first.group(0) == b"<", "FIGURE_SPAN_MISMATCH")
    tokens, ix_negative = _figure_scan(raw, start, end)
    # Rules 0 and 1: the span sits in printed text; its printed text.
    printed = _figure_printed_text(raw, tokens, start, end)
    # Rule 2: the closed shape decides the sign.
    t = re.escape(text)
    if re.fullmatch(rf"\$? ?{t}", printed):
        shape_sign = "+"
    elif (re.fullmatch(rf"\$? ?\( ?\$? ?{t} ?\)", printed)
          or re.fullmatch(rf"\$? ?[-−] ?\$? ?{t}", printed)):
        shape_sign = "-"
    else:
        shape_sign = None
    _require(shape_sign is not None, "FIGURE_SPAN_MISMATCH")
    _require(shape_sign == sign, "FIGURE_SIGN_UNSUPPORTED")
    # Rule 3: the span is not a fragment of a longer number.
    _figure_not_cut_from_number(raw, start, end)
    left_side = _figure_side(raw, tokens, max(0, start - _FIGURE_WINDOW_BYTES), start, left=True)
    right_side = _figure_side(raw, tokens, end, min(len(raw), end + _FIGURE_WINDOW_BYTES), left=False)
    for side in (left_side, right_side):
        fragment = _figure_fragment_neighbour(side)
        _require(fragment is None or not unicodedata.category(fragment).startswith("N"),
                 "FIGURE_SPAN_MISMATCH")
    # Rule 4: no sign mark left outside the span.
    _require(not any(type(item) is str and item in _FIGURE_BIDI for item in left_side),
             "FIGURE_SIGN_UNSUPPORTED")
    left_text = _figure_neighbour(left_side)
    right_text = _figure_neighbour(right_side)
    if not left_text:
        if start <= _FIGURE_WINDOW_BYTES:  # the window reached the start of raw
            _require(whole_document, "FIGURE_SIGN_UNSUPPORTED")
        else:
            raise DisclosureError("FIGURE_SIGN_UNSUPPORTED")
    else:
        _require(_figure_neighbour_allowed(left_text[0], left=True), "FIGURE_SIGN_UNSUPPORTED")
        _require(not _figure_credit_mark(left_text, left=True), "FIGURE_SIGN_UNSUPPORTED")
    if not right_text:
        _require(end + _FIGURE_WINDOW_BYTES >= len(raw), "FIGURE_SIGN_UNSUPPORTED")
    else:
        _require(_figure_neighbour_allowed(right_text[0], left=False), "FIGURE_SIGN_UNSUPPORTED")
        _require(not _figure_credit_mark(right_text, left=False), "FIGURE_SIGN_UNSUPPORTED")
        _require(not (right_text[0] in ".," and right_text[1:2] != ""
                      and unicodedata.category(right_text[1]).startswith("N")),
                 "FIGURE_SPAN_MISMATCH")
    if shape_sign == "-":
        for item in left_side:
            if item == _FIGURE_TAG_KIND:
                continue
            _require(not (type(item) is str and unicodedata.category(item)[0] in "LN"),
                     "FIGURE_SIGN_UNSUPPORTED")
            break
    # Rule 5: an inline-XBRL negative flag is never read as plus.
    if sign == "+":
        _require(not ix_negative, "FIGURE_SIGN_UNSUPPORTED")


def _segment_figure_number(value: object, code: str) -> None:
    """A derived figure magnitude: null when undisclosed; a loss is carried negative."""
    if value is None:
        return
    _require(type(value) in (int, float) and not isinstance(value, bool), code)


def _segment_number(value: object, code: str, *, minimum: float | None = None,
                    exclusive: bool = False) -> None:
    """A disclosed magnitude: null when undisclosed, never a fabricated zero."""
    if value is None:
        return
    _require(type(value) in (int, float) and not isinstance(value, bool), code)
    if minimum is not None:
        _require((value > minimum) if exclusive else (value >= minimum), code)


def _validate_segment_fact(value: dict) -> Reference:
    """The ``segment_activity`` species: one issuer's own disclosed business line.

    Single-party (the subject is the issuer itself), so there is no object,
    direction or supplier qualification. The annual-report form gate and the
    required activity span are the species-specific admission boundaries; the
    exposure magnitudes stay null when the filing does not disclose them.
    """
    # The activity span is a required admission boundary: a missing span key is
    # SPAN_REQUIRED, not a generic closed-set mismatch (the closed-set check below
    # still governs every other field).
    _require("span" in value, "SPAN_REQUIRED")
    _closed(value, {"schema", "fact_id", "claim_key", "disclosure_id", "edition",
                    "revision", "previous", "review_revision", "subject_id",
                    "subject_identity", "kind", "lifecycle", "form_type", "accession",
                    "disclosed_line", "share_scope", "revenue", "revenue_denominator",
                    "profit", "profit_denominator", "profit_measure", "fiscal_year",
                    "span", "figure_spans", "known_at"}
                   | {f"{name}_{suffix}" for name in SEGMENT_FIGURE_NAMES
                      for suffix in ("text", "sign", "scale")})
    _require(value["schema"] == SEGMENT_FACT_SCHEMA, "SCHEMA_INVALID")
    _require(value["fact_id"] == activity_fact_id(value["disclosure_id"], value["claim_key"]), "FACT_ID_MISMATCH")
    _reference(value["edition"], SEC_EDITION_SCHEMA)
    _integer(value["revision"], 1, MAX_REVISIONS)
    _require((value["revision"] == 1) == (value["previous"] is None), "PREDECESSOR_REQUIRED")
    if value["previous"] is not None:
        _reference(value["previous"], value["schema"])
    _digest(value["review_revision"])
    _digest(value["subject_identity"])
    _identifier(value["subject_id"])
    _require((value["kind"], value["lifecycle"]) == ("segment_activity", "reported"), "FACT_SPECIES_INVALID")
    _require(type(value["form_type"]) is str and value["form_type"] in SEGMENT_FORM_TYPES,
             "SEGMENT_FORM_NOT_ADMITTED")
    _require(type(value["accession"]) is str
             and re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", value["accession"]) is not None,
             "SEGMENT_ACCESSION_INVALID")
    line = value["disclosed_line"]
    _require(type(line) is str and 0 < len(line) <= 256 and len(line.encode("utf-8")) <= 256
             and line.strip() == line, "FACT_SCOPE_INVALID")
    _require(type(value["share_scope"]) is str and value["share_scope"] in SEGMENT_SHARE_SCOPES,
             "SEGMENT_SHARE_SCOPE_INVALID")
    # A loss is carried negative; the share-level refusals live in the writer.
    for name in SEGMENT_FIGURE_NAMES:
        _segment_figure_number(value[name], "SEGMENT_EXPOSURE_INVALID")
    measure = value["profit_measure"]
    _require(measure is None or (type(measure) is str and 0 < len(measure) <= 128 and measure.strip() == measure),
             "SEGMENT_EXPOSURE_INVALID")
    _integer(value["fiscal_year"], 1900, 2200)
    _segment_span(value["span"])
    spans = _closed(value["figure_spans"], set(SEGMENT_FIGURE_NAMES))
    for name in SEGMENT_FIGURE_NAMES:
        disclosed = value[name] is not None
        span = spans[name]
        if disclosed:
            _require(span is not None, "FIGURE_SPAN_REQUIRED")
            _segment_figure_span(span)
        else:
            _require(span is None, "FIGURE_SPAN_MISMATCH")
        for suffix in ("text", "sign", "scale"):
            field = value[f"{name}_{suffix}"]
            if disclosed:
                _require(field is not None, "SEGMENT_EXPOSURE_INVALID")
            else:
                _require(field is None, "SEGMENT_EXPOSURE_INVALID")
        if disclosed:
            text = value[f"{name}_text"]
            _require(type(text) is str and _FIGURE_TEXT.fullmatch(text) is not None, "SEGMENT_EXPOSURE_INVALID")
            _require(value[f"{name}_sign"] in SEGMENT_FIGURE_SIGNS, "SEGMENT_EXPOSURE_INVALID")
            _require(value[f"{name}_scale"] in SEGMENT_FIGURE_SCALES, "SEGMENT_EXPOSURE_INVALID")
            # The value must equal sign x digits x scale at EVERY read-back, not only
            # at prepare: an altered magnitude with an unchanged printed text is refused.
            derived = ((-1 if value[f"{name}_sign"] == "-" else 1)
                       * int(text.replace(",", "")) * SEGMENT_FIGURE_SCALES[value[f"{name}_scale"]])
            _require(value[name] == derived, "FIGURE_TEXT_MISMATCH")
    _instant(value["known_at"])
    return _ref(value)


@dataclass(frozen=True)
class Request:
    fact_id: str
    purpose: str
    audience: str
    as_of: str | None = None
    mode: str = "current"

    def __post_init__(self) -> None:
        for field in (self.fact_id, self.purpose, self.audience):
            _identifier(field)
        _require(type(self.mode) is str and self.mode in {"current", "historical"}, "QUERY_MODE_INVALID")
        if self.mode == "current":
            _require(self.as_of is None, "CURRENT_CUTOFF_NOT_ALLOWED")
        else:
            _instant(self.as_of)


@dataclass(frozen=True)
class SubjectIdentityBinding:
    """Owner-attested link from one fact decision to an immutable identity receipt.

    The schema names the actual supplied receipt; it does not invent a DataOS
    contract. The aggregate Admission.identity_revision remains a separate
    decision and must not be confused with this subject-specific revision.
    """
    issuer_id: str
    evidenced_cik: str
    snapshot_schema: str
    snapshot_sha256: str
    snapshot_byte_length: int
    decision_revision: str

    def __post_init__(self) -> None:
        _identifier(self.issuer_id)
        _require(type(self.evidenced_cik) is str
                 and re.fullmatch(r"[0-9]{10}", self.evidenced_cik) is not None
                 and int(self.evidenced_cik) > 0, "SUBJECT_IDENTITY_INVALID")
        _identifier(self.snapshot_schema)
        _digest(self.snapshot_sha256)
        _integer(self.snapshot_byte_length, 1, MAX_OBJECT_BYTES)
        _digest(self.decision_revision)


@dataclass(frozen=True)
class Admission:
    """Metadata returned only by the injected, adopted source-owner resolver.

    The exact request/reference bind the decision. Immutable decision digests
    name independently maintained registry, purpose, legal identity, temporal
    and correction decisions. They are not themselves permission tokens.
    """
    request: Request
    reference: Reference
    edition: Reference
    generation: str
    dataset_id: str
    profile: str
    adoption_revision: str
    purpose_revision: str
    identity_revision: str
    temporal_revision: str
    correction_revision: str
    known_at: str
    publication_precision: str
    identity_mode: str
    allowed_fields: frozenset[str]
    operation: str = "read"
    subject_binding: SubjectIdentityBinding | None = None
    object_binding: SubjectIdentityBinding | None = None

    def validate(self, request: Request, candidate: Reference | None) -> None:
        _require(self.subject_binding is None or type(self.subject_binding) is SubjectIdentityBinding,
                 "SUBJECT_IDENTITY_INVALID")
        _require(self.request == request, "ADMISSION_REQUEST_MISMATCH")
        _require(self.operation == ("publish" if candidate is not None else "read"), "ADMISSION_OPERATION_MISMATCH")
        _require(type(self.reference) is Reference and self.reference.schema in FACT_SCHEMAS, "ADMISSION_REFERENCE_INVALID")
        supplier = self.reference.schema == SUPPLIER_FACT_SCHEMA
        _require(type(self.edition) is Reference and self.edition.schema ==
                 (SEC_EDITION_SCHEMA if supplier else EDITION_SCHEMA), "ADMISSION_REFERENCE_INVALID")
        if supplier:
            _require((request.purpose, request.audience) == (SEC_SUPPLIER_PURPOSE, SEC_SUPPLIER_AUDIENCE), "PURPOSE_NOT_ADMITTED")
            _require(request.mode == "current" and self.identity_mode == "current" and self.profile == "DERIVED",
                     "HISTORICAL_BINDING_UNAVAILABLE")
            _require(type(self.subject_binding) is SubjectIdentityBinding
                     and type(self.object_binding) is SubjectIdentityBinding
                     and self.subject_binding.issuer_id != self.object_binding.issuer_id,
                     "SUPPLIER_IDENTITY_BINDING_REQUIRED")
        _require(candidate is None or self.reference == candidate, "ADMISSION_REFERENCE_MISMATCH")
        for field in (self.generation, self.dataset_id, self.profile):
            _identifier(field)
        for field in (self.adoption_revision, self.purpose_revision, self.identity_revision,
                      self.temporal_revision, self.correction_revision):
            _digest(field)
        now = datetime.now(timezone.utc)
        cutoff = now if request.mode == "current" else _instant(request.as_of)
        _require(cutoff <= now and _instant(self.known_at) <= cutoff, "FUTURE_KNOWLEDGE")
        _require(type(self.publication_precision) is str and self.publication_precision in {"date", "instant"}, "PUBLICATION_PRECISION_INVALID")
        _require(type(self.identity_mode) is str and self.identity_mode in {"current", "historical"}, "IDENTITY_MODE_INVALID")
        if request.mode == "historical":
            _require(self.publication_precision == "instant" and self.identity_mode == "historical", "HISTORICAL_BINDING_UNAVAILABLE")
        _require(type(self.allowed_fields) is frozenset and self.allowed_fields <= _FIELDS
                 and {"fact_id", "kind", "lifecycle"} <= self.allowed_fields, "FIELD_GRANT_INVALID")
        if supplier:
            # The closed supplier metadata binds both parties and product.
            # A restricted field grant cannot silently expose that linkage.
            _require(self.allowed_fields == _FIELDS, "SUPPLIER_FIELD_GRANT_REQUIRED")


class DisclosureAuthority(Protocol):
    def resolve(self, request: Request) -> Admission | None:
        """Resolve adopted source/purpose/identity/time/correction metadata only.

        Must not retrieve private source/reviewer content. For reads, select the
        owner-current immutable reference for the request. Read authority does
        not imply publication authority. Production installation is separate.
        """
        ...

    def authorize_publication(self, request: Request, candidate: Reference) -> Admission | None:
        """Separate source-owner write decision for this exact proposed root."""
        ...


def preflight(authority: DisclosureAuthority, request: Request,
              candidate: Reference | None = None) -> Admission:
    """Metadata only; no source/reviewer/artifact bodies or artifact Store.

    An installed owner may read bounded decision/current-selection metadata.
    HTTP authentication and actual entitlement must precede even that access.
    """
    _require(type(request) is Request, "REQUEST_INVALID")
    try:
        admitted = (authority.resolve(request) if candidate is None
                    else authority.authorize_publication(request, candidate))
    except Exception:
        raise DisclosureError("OWNER_RESOLUTION_UNAVAILABLE") from None
    _require(type(admitted) is Admission, "SOURCE_NOT_ADMITTED")
    admitted.validate(request, candidate)
    return admitted


def _subject_binding(fact: dict, admission: Admission) -> None:
    binding = admission.subject_binding
    if binding is not None:
        _require(fact["subject_id"] == binding.issuer_id
                 and fact["subject_identity"] == binding.decision_revision,
                 "SUBJECT_IDENTITY_MISMATCH")
    if fact["schema"] == SUPPLIER_FACT_SCHEMA:
        binding = admission.object_binding
        _require(type(binding) is SubjectIdentityBinding and fact["object_id"] == binding.issuer_id
                 and fact["object_identity"] == binding.decision_revision, "OBJECT_IDENTITY_MISMATCH")


def _source_binding(edition: dict, fact: dict, admission: Admission) -> None:
    if fact["schema"] == SUPPLIER_FACT_SCHEMA:
        s = edition["sec_source"]
        _require(admission.subject_binding.evidenced_cik == s["issuer_cik"]
                 and fact["qualification"]["evidence_revision"] == hashlib.sha256(_canonical(s)).hexdigest()
                 and fact["span"] == {"start_byte": s["span_start_byte"], "end_byte": s["span_end_byte"],
                                      "text_sha256": s["span_sha256"]}, "SUPPLIER_EVIDENCE_MISMATCH")


def _key(reference: Reference) -> str:
    kind = "editions" if reference.schema in EDITION_SCHEMAS else "facts"
    return f"company_intelligence/issuer_disclosures/v1/{kind}/{reference.sha256}.json"


def _read(store: object, reference: Reference) -> bytes | None:
    try:
        raw = store.get_bytes_strict_bounded(_key(reference), expected_byte_length=reference.byte_length,
                                            max_byte_length=MAX_OBJECT_BYTES)
    except Exception:
        raise DisclosureError("PRIVATE_READ_UNAVAILABLE") from None
    if raw is not None:
        _require(type(raw) is bytes and len(raw) == reference.byte_length
                 and hashlib.sha256(raw).hexdigest() == reference.sha256, "PRIVATE_OBJECT_MISMATCH")
    return raw


def _load(store: object, reference: Reference) -> dict:
    raw = _read(store, reference)
    _require(raw is not None, "PRIVATE_OBJECT_ABSENT")
    value = _decode(raw)
    actual = validate_edition(value) if reference.schema in EDITION_SCHEMAS else validate_fact(value)
    _require(actual == reference, "PRIVATE_OBJECT_MISMATCH")
    return value


def _slot(value: dict) -> tuple[str, bytes]:
    """The incumbent CAS store binds one value to each native revision."""
    identity = value["disclosure_id"] if value["schema"] in EDITION_SCHEMAS else value["fact_id"]
    family = "editions" if value["schema"] in EDITION_SCHEMAS else "facts"
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    path = f"company_intelligence/issuer_disclosures/v1/revisions/{family}/{key}/{value['revision']}.json"
    return path, _canonical({"schema": "company_intelligence.disclosure_revision_binding/v1",
                             "reference": _ref(value).payload()})


def _slot_read(store: object, key: str) -> bytes | None:
    try:
        versioned = store.get_bytes_strict_bounded_versioned(key, MAX_OBJECT_BYTES)
    except Exception:
        raise DisclosureError("PRIVATE_BINDING_UNAVAILABLE") from None
    _require(type(versioned) is VersionedBytes, "PRIVATE_BINDING_PROTOCOL_INVALID")
    if versioned.data is not None:
        _require(len(versioned.data) <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE")
    return versioned.data


def _binding(store: object, value: dict, *, reserve: bool = False) -> bool:
    key, raw = _slot(value)
    existing = _slot_read(store, key)
    if existing is not None:
        _require(existing == raw, "REVISION_CONFLICT")
        return False
    _require(reserve, "REVISION_BINDING_ABSENT")
    raised = False
    try:
        store.put_bytes_strict_conditional(key, raw, expected_version=None, content_type="application/json")
    except Exception:
        raised = True
    try:
        observed = _slot_read(store, key)
    except DisclosureError:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN", effect_unknown=True) from None
    if raised and observed != raw:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN", effect_unknown=True)
    _require(observed is not None, "WRITE_NOT_OBSERVED")
    _require(observed == raw, "REVISION_CONFLICT")
    return True


def _chain(store: object, value: dict) -> None:
    # Revision counters are bounded, decrease exactly once, and reach revision1.
    while value["previous"] is not None:
        prior = _load(store, _reference(value["previous"], value["schema"]))
        _binding(store, prior)
        identity = "disclosure_id" if value["schema"] in EDITION_SCHEMAS else "fact_id"
        _require(prior[identity] == value[identity] and prior["revision"] + 1 == value["revision"], "CORRECTION_CHAIN_MISMATCH")
        _require(_instant(prior["known_at"]) <= _instant(value["known_at"]), "CORRECTION_TIME_REVERSED")
        value = prior


def _create(store: object, reference: Reference, raw: bytes) -> bool:
    existing = _read(store, reference)
    if existing is not None:
        _require(existing == raw, "PRIVATE_OBJECT_MISMATCH")
        return False
    raised = False
    try:
        store.put_bytes_strict_conditional(_key(reference), raw, expected_version=None,
                                           content_type="application/json")
    except Exception:
        raised = True
    try:
        observed = _read(store, reference)
    except DisclosureError:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN", effect_unknown=True) from None
    if observed != raw:
        raise DisclosureError("WRITE_EFFECT_UNKNOWN" if raised else "WRITE_NOT_OBSERVED", effect_unknown=raised)
    return True


class DisclosureSourceReader(Protocol):
    def read_source(self, *, disclosure_id: str, edition_reference: Reference,
                    source_sha256: str, expected_byte_length: int,
                    max_byte_length: int) -> bytes:
        """Owner-pinned private source retrieval; enforce bounds before buffering."""
        ...


def publish_disclosure(store: object, authority: DisclosureAuthority, request: Request,
                       *, edition: dict, fact: dict, source_reader: DisclosureSourceReader) -> dict:
    """Append exact owner-admitted metadata/fact bytes; never chooses credentials.

    Original source is retrieved only after metadata admission and only for span
    verification. Publication does not change the resolver's current selection.
    The final fact is the root; a partial edition remains immutable and harmless.
    """
    # Snapshot before invoking untrusted callbacks; later mutation cannot rebind.
    _require(type(request) is Request, "REQUEST_INVALID")
    validate_edition(edition); validate_fact(fact)
    edition = _decode(_canonical(edition)); fact = _decode(_canonical(fact))
    eref, fref = validate_edition(edition), validate_fact(fact)
    _require(fact["fact_id"] == request.fact_id and fact["edition"] == eref.payload()
             and fact["disclosure_id"] == edition["disclosure_id"]
             and fact["subject_id"] == edition["issuer_id"], "SOURCE_BINDING_MISMATCH")
    _require(_instant(edition["known_at"]) <= _instant(fact["known_at"]), "FACT_PRECEDES_SOURCE")
    admission = preflight(authority, request, fref)
    _subject_binding(fact, admission)
    _source_binding(edition, fact, admission)
    _require(admission.edition == eref and admission.known_at == fact["known_at"]
             and admission.publication_precision == edition["publication_precision"], "ADMISSION_METADATA_MISMATCH")
    try:
        store.validate_strict_conditional_write_capability()
    except Exception:
        raise DisclosureError("CONDITIONAL_STORE_UNAVAILABLE") from None
    _chain(store, edition); _chain(store, fact)
    try:
        body = source_reader.read_source(disclosure_id=edition["disclosure_id"], edition_reference=eref,
                                         source_sha256=edition["source_sha256"],
                                         expected_byte_length=edition["source_byte_length"],
                                         max_byte_length=MAX_SEC_SOURCE_BYTES if edition["schema"] == SEC_EDITION_SCHEMA else MAX_SOURCE_BYTES)
    except Exception:
        raise DisclosureError("SOURCE_READ_UNAVAILABLE") from None
    _require(type(body) is bytes and len(body) == edition["source_byte_length"]
             and hashlib.sha256(body).hexdigest() == edition["source_sha256"], "SOURCE_BYTES_MISMATCH")
    span = fact["span"]
    try:
        segment = body.decode("utf-8")
        excerpt = body[span["start_byte"]:span["end_byte"]].decode("utf-8")
        receipt = text_span(document_id=edition["disclosure_id"], document_version=edition["revision"],
                            body_sha256=edition["source_sha256"], segment_index=0, segment_text=segment,
                            start_byte=span["start_byte"], end_byte=span["end_byte"], text=excerpt,
                            display_excerpt="")
    except Exception:
        raise DisclosureError("SOURCE_SPAN_INVALID") from None
    _require(receipt.text_sha256 == span["text_sha256"], "SOURCE_SPAN_MISMATCH")
    if fact["schema"] == SEGMENT_FACT_SCHEMA:
        # The figure check binds the write itself, whichever reader was supplied.
        for figure_name in SEGMENT_FIGURE_NAMES:
            figure_span = fact["figure_spans"][figure_name]
            if figure_span is not None:
                _verify_figure_span(figure_name, figure_span, fact[f"{figure_name}_text"],
                                    fact[f"{figure_name}_sign"], body)
    _require(preflight(authority, request, fref) == admission, "ADMISSION_CHANGED")
    writes = int(_create(store, eref, _canonical(edition)))
    writes += int(_binding(store, edition, reserve=True))
    # Stop before committing the root if rights/current generation changed.
    _require(preflight(authority, request, fref) == admission, "ADMISSION_CHANGED")
    writes += int(_create(store, fref, _canonical(fact)))
    writes += int(_binding(store, fact, reserve=True))
    return {"status": "COMMITTED_OBSERVED" if writes else "REPEATED", "reference": fref.payload(),
            "conditional_objects_observed": writes, "automatic_retry_permitted": False}


def read_disclosure(store: object, authority: DisclosureAuthority, request: Request, *,
                    expected_admission: Admission | None = None) -> dict:
    """Owner-selected private fact read, optionally pinned by a composing caller."""
    _require(expected_admission is None or type(expected_admission) is Admission,
             "ADMISSION_INVALID")
    admission = preflight(authority, request)
    _require(expected_admission is None or admission == expected_admission,
             "ADMISSION_CHANGED")
    fact = _load(store, admission.reference)
    _subject_binding(fact, admission)
    _require(fact["fact_id"] == request.fact_id and fact["edition"] == admission.edition.payload()
             and fact["known_at"] == admission.known_at, "ADMISSION_METADATA_MISMATCH")
    edition = _load(store, admission.edition)
    _require(fact["disclosure_id"] == edition["disclosure_id"]
             and fact["subject_id"] == edition["issuer_id"]
             and edition["publication_precision"] == admission.publication_precision
             and _instant(edition["known_at"]) <= _instant(fact["known_at"]), "SOURCE_BINDING_MISMATCH")
    _source_binding(edition, fact, admission)
    _binding(store, fact); _binding(store, edition)
    _chain(store, fact); _chain(store, edition)
    _require(preflight(authority, request) == admission, "ADMISSION_CHANGED")
    result = {"schema": "company_intelligence.private_product_integration/v2",
            "fact": {k: fact[k] for k in sorted(admission.allowed_fields)},
            "reference": admission.reference.payload(), "edition": admission.edition.payload(),
            "source_timing": {k: edition[k] for k in
                              ("published_date", "published_at", "publication_precision", "known_at")},
            "generation": admission.generation, "authority": "context_only"}
    if fact["schema"] == SUPPLIER_FACT_SCHEMA:
        result["schema"] = "company_intelligence.private_disclosed_supplier/v1"
        result["source_timing"]["sec_source"] = dict(edition["sec_source"])
        result["supplier_binding"] = {**fact["qualification"], "span": dict(fact["span"]),
            "subject_identity": fact["subject_identity"], "object_identity": fact["object_identity"],
            "adopted_at": fact["known_at"],
            "current_subject_identity": admission.subject_binding.snapshot_sha256,
            "current_object_identity": admission.object_binding.snapshot_sha256}
    return result
