"""Byte-replayable span receipts over a supplied release body.

The discipline is copied from ``engine.earnings_narrative.contracts``
(``_RECEIPT_KEYS`` / ``receipt_for_span``): a receipt is only worth storing if a
later reader can re-open the original bytes, re-slice them, re-hash them, and
get the same answer.  ``receipt_for_literal`` therefore replays every receipt it
mints **before returning it**, so an unreplayable receipt can never leave this
module.

Why a second receipt type rather than reusing the transcript one: the transcript
receipt is segment-indexed (``segment_index`` into a JSON body's segment list).
A filing body is one flat document, and
``engine.fundamental_forensics.disclosure_diff`` already supplies exact
character/byte coordinates into it.  The invariants are the same; the coordinate
space is not.

The receipt binds the FIGURE, not merely some bytes.  Replay checks four things
in order, and any one of them failing raises:

1. the whole source still hashes to ``source_sha256``;
2. the byte slice still hashes to ``span_sha256``;
3. the slice still decodes to exactly ``span_text``;
4. the slice still yields ``value_text`` after the same deterministic
   normalization the extractor used.

Check 4 is what makes a one-digit tamper fail rather than merely shift.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html as _html
import re
from typing import Any, Mapping

RECEIPT_SCHEMA = "earnings_release.span_receipt/v1"

RECEIPT_KEYS = frozenset({
    "schema", "source_sha256", "char_start", "char_end", "byte_start", "byte_end",
    "span_sha256", "span_bytes", "span_text", "value_text", "value_text_sha256",
})

_TAG_RE = re.compile(r"<[^>]*>")
_WS_RE = re.compile(r"\s+")
# U+00A0 NO-BREAK SPACE arrives as &#160; in every EDGAR table cell; U+200B
# ZERO WIDTH SPACE is EDGAR's typesetting spacer and must not survive into a
# compared value.
_INVISIBLE = str.maketrans({" ": " ", "​": "", " ": " ", "﻿": ""})


class ReceiptError(ValueError):
    """A receipt could not be minted from the supplied coordinates."""


class ReceiptReplayError(ReceiptError):
    """A stored receipt does not reproduce against the source it names."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


# A decimal character reference is read at its limit before it is resolved (R187).  ``html.unescape`` converts the
# digits of every decimal reference with ``int()``, which refuses a run longer than the interpreter's integer
# string-conversion limit (4,300 digits by default, as low as 640), so whether a document raised was a property of
# the process, not of the document.  Leading zeros carry no value and are dropped; every value above 0x10FFFF
# resolves to U+FFFD, so a run of more than seven significant digits reads as 1114112 (0x110000) and resolves as
# its full value did.  Hexadecimal references are converted without a limit and are left alone.
_DECIMAL_REFERENCE = re.compile(r"(?<=&#)[0-9]+")


def _reference_at_limit(match: re.Match[str]) -> str:
    digits = match.group().lstrip("0")
    return (digits or "0") if len(digits) <= 7 else "1114112"


def unescape(text: str) -> str:
    """``html.unescape`` with each decimal character reference read at its limit first (R187): the same text
    wherever ``html.unescape`` returns one, and never the interpreter's integer-conversion ValueError."""
    return _html.unescape(_DECIMAL_REFERENCE.sub(_reference_at_limit, text))


def visible_text(markup: str) -> str:
    """Strip tags, resolve entities, normalize invisible space — deterministically.

    This is the ONLY normalization a receipt replay is allowed to apply, so that
    "the bytes still say the same number" is a checkable statement rather than a
    negotiable one.
    """
    text = _TAG_RE.sub(" ", markup)
    text = unescape(text)
    text = text.translate(_INVISIBLE)
    return _WS_RE.sub(" ", text).strip()


@dataclass(frozen=True)
class SpanReceipt:
    """Exact source coordinates plus everything needed to prove them again."""

    source_sha256: str
    char_start: int
    char_end: int
    byte_start: int
    byte_end: int
    span_sha256: str
    span_bytes: int
    span_text: str
    value_text: str
    value_text_sha256: str
    schema: str = RECEIPT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_sha256": self.source_sha256,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "span_sha256": self.span_sha256,
            "span_bytes": self.span_bytes,
            "span_text": self.span_text,
            "value_text": self.value_text,
            "value_text_sha256": self.value_text_sha256,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SpanReceipt:
        if not isinstance(payload, Mapping):
            raise ReceiptError("receipt must be a mapping")
        actual = set(payload)
        if actual != RECEIPT_KEYS:
            missing = sorted(RECEIPT_KEYS - actual)
            unknown = sorted(actual - RECEIPT_KEYS)
            raise ReceiptError(
                f"receipt fields mismatch (missing={missing}, unsupported={unknown})"
            )
        if payload["schema"] != RECEIPT_SCHEMA:
            raise ReceiptError(f"unsupported receipt schema {payload['schema']!r}")
        return cls(
            source_sha256=str(payload["source_sha256"]),
            char_start=int(payload["char_start"]),
            char_end=int(payload["char_end"]),
            byte_start=int(payload["byte_start"]),
            byte_end=int(payload["byte_end"]),
            span_sha256=str(payload["span_sha256"]),
            span_bytes=int(payload["span_bytes"]),
            span_text=str(payload["span_text"]),
            value_text=str(payload["value_text"]),
            value_text_sha256=str(payload["value_text_sha256"]),
        )


def replay_receipt(receipt: SpanReceipt | Mapping[str, Any], *, source: str) -> str:
    """Re-derive every hash and re-slice the bytes.  Raise on any disagreement.

    Returns the replayed ``value_text`` so a caller cannot "verify" a receipt
    and then go on using a different string.
    """
    row = receipt if isinstance(receipt, SpanReceipt) else SpanReceipt.from_dict(receipt)

    encoded = source.encode("utf-8")
    if sha256_bytes(encoded) != row.source_sha256:
        raise ReceiptReplayError(
            "source_sha256 does not match the supplied source — the receipt "
            "belongs to a different document revision"
        )
    if row.byte_start < 0 or row.byte_end < row.byte_start or row.byte_end > len(encoded):
        raise ReceiptReplayError("byte span is outside the source")
    if row.byte_end - row.byte_start != row.span_bytes:
        raise ReceiptReplayError("span_bytes disagrees with the byte span")

    slice_bytes = encoded[row.byte_start:row.byte_end]
    if sha256_bytes(slice_bytes) != row.span_sha256:
        raise ReceiptReplayError("span_sha256 mismatch — the source bytes changed")
    try:
        slice_text = slice_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - guarded by char alignment
        raise ReceiptReplayError("byte span does not start on a character boundary") from exc
    if slice_text != row.span_text:
        raise ReceiptReplayError("span_text mismatch — the source bytes changed")

    # Character coordinates are an aid for humans and for narrowing; they must
    # still agree with the authoritative byte coordinates.
    if source[row.char_start:row.char_end] != row.span_text:
        raise ReceiptReplayError("char span and byte span disagree")

    replayed_value = visible_text(slice_text)
    if replayed_value != row.value_text:
        raise ReceiptReplayError(
            f"replayed value {replayed_value!r} does not match the receipt's "
            f"{row.value_text!r} — the figure at this location changed"
        )
    if sha256_text(replayed_value) != row.value_text_sha256:
        raise ReceiptReplayError("value_text_sha256 mismatch")
    return replayed_value


def byte_offsets(source: str, char_start: int, char_end: int) -> tuple[int, int]:
    """UTF-8 byte offsets for a code-point range."""
    return (
        len(source[:char_start].encode("utf-8")),
        len(source[:char_end].encode("utf-8")),
    )


def receipt_for_char_span(
    *,
    source: str,
    source_sha256: str,
    char_start: int,
    char_end: int,
) -> SpanReceipt:
    """Mint a receipt for an exact code-point range and replay it before returning."""
    if char_start < 0 or char_end < char_start or char_end > len(source):
        raise ReceiptError("char span is outside the source")
    span_text = source[char_start:char_end]
    byte_start, byte_end = byte_offsets(source, char_start, char_end)
    value_text = visible_text(span_text)
    receipt = SpanReceipt(
        source_sha256=source_sha256,
        char_start=char_start,
        char_end=char_end,
        byte_start=byte_start,
        byte_end=byte_end,
        span_sha256=sha256_text(span_text),
        span_bytes=byte_end - byte_start,
        span_text=span_text,
        value_text=value_text,
        value_text_sha256=sha256_text(value_text),
    )
    # Non-negotiable: a receipt that cannot be replayed never leaves this module.
    replay_receipt(receipt, source=source)
    return receipt


def mask_markup(window: str) -> str:
    """Blank every tag to same-length spaces, preserving character offsets.

    Without this, locating the literal ``2.18`` inside one EDGAR table cell can
    land inside ``<td style="width:2.18%">`` — real EX-99.1 markup carries
    percentage column widths on every cell, so a bare substring search points
    the receipt at a stylesheet instead of at the figure.  Masking rather than
    stripping keeps offsets aligned with the untouched source.
    """
    return _TAG_RE.sub(lambda match: " " * len(match.group(0)), window)


def receipt_for_literal(
    *,
    source: str,
    source_sha256: str,
    search_start: int,
    search_end: int,
    literal: str,
) -> SpanReceipt:
    """Mint a receipt for the UNIQUE occurrence of ``literal`` inside a window.

    The search ignores markup (see ``mask_markup``) and requires uniqueness.
    Uniqueness is required, not preferred: if the literal appears twice inside
    the window there is no fact of the matter about which one the extractor
    read, and a receipt pointing at "one of them" is not evidence — the caller
    is expected to turn the ``ReceiptError`` into a typed absence.
    """
    if not literal:
        raise ReceiptError("cannot locate an empty literal")
    if search_start < 0 or search_end < search_start or search_end > len(source):
        raise ReceiptError("search window is outside the source")
    window = mask_markup(source[search_start:search_end])
    first = window.find(literal)
    if first < 0:
        raise ReceiptError(f"literal {literal!r} does not occur in the window")
    if window.find(literal, first + 1) >= 0:
        raise ReceiptError(
            f"literal {literal!r} occurs more than once in the window — "
            "ambiguous location, refusing to mint a receipt"
        )
    char_start = search_start + first
    return receipt_for_char_span(
        source=source,
        source_sha256=source_sha256,
        char_start=char_start,
        char_end=char_start + len(literal),
    )


__all__ = [
    "RECEIPT_KEYS",
    "RECEIPT_SCHEMA",
    "ReceiptError",
    "ReceiptReplayError",
    "SpanReceipt",
    "byte_offsets",
    "mask_markup",
    "receipt_for_char_span",
    "receipt_for_literal",
    "replay_receipt",
    "sha256_bytes",
    "sha256_text",
    "unescape",
    "visible_text",
]


# Acquisition provenance is separate from span replay and from permission to use
# a source. Only the HTTP producer emits this optional record; offline binding
# validates it without creating an acquisition event or reading a clock.
SEC_ACQUISITION_SCHEMA = "earnings_release.sec_acquisition.v1"
SEC_REDIRECT_POLICY = "sec_https_same_filing_max5.v1"
_SEC_ACQUISITION_KEYS = frozenset({
    "schema", "filing_key", "requested_url", "final_url", "redirect_policy",
    "redirects", "http_status", "body_representation", "content_type",
    "content_encoding", "declared_charset", "entity_sha256", "entity_length",
    "decoder", "decode_errors", "decode_policy", "source_sha256",
    "source_utf8_length", "acquired_at",
})
_SEC_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SEC_ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")
_SEC_ACQUIRED_AT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z")


def _sec_filing_key(cik: object, accession: object) -> dict[str, str]:
    if isinstance(cik, bool) or not re.fullmatch(r"[0-9]{1,10}", str(cik)) or int(str(cik)) == 0:
        raise ReceiptError("SEC acquisition requires an exact CIK")
    if not isinstance(accession, str) or not _SEC_ACCESSION.fullmatch(accession):
        raise ReceiptError("SEC acquisition requires an exact accession")
    return {"cik": str(cik).zfill(10), "accession": accession}


def validate_sec_acquisition_url(url: object, *, cik: object, accession: object) -> str:
    """Validate a canonical public SEC filing URL before requesting/following it."""
    from urllib.parse import urlsplit

    key = _sec_filing_key(cik, accession)
    if (not isinstance(url, str) or not 0 < len(url) <= 8192
            or not url.startswith("https://") or any(ord(c) <= 32 or ord(c) > 126 for c in url)
            or "%" in url or "\\" in url or "?" in url or "#" in url):
        raise ReceiptError("SEC acquisition URL is not canonical")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise ReceiptError("SEC acquisition URL is invalid") from exc
    if parsed.netloc not in {"www.sec.gov", "sec.gov"} or parsed.query or parsed.fragment:
        raise ReceiptError("SEC acquisition URL origin or suffix is not eligible")
    prefix = f"/Archives/edgar/data/{int(key['cik'])}/{key['accession'].replace('-', '')}/"
    if not parsed.path.startswith(prefix):
        raise ReceiptError("SEC acquisition URL does not match its filing")
    filename = parsed.path[len(prefix):]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.(?:htm|html|txt)", filename):
        raise ReceiptError("SEC acquisition filename is not canonical")
    if re.search(r"(?:^index(?:-headers)?\.|-index(?:-headers)?\.(?:htm|html|txt)$)", filename, re.IGNORECASE):
        raise ReceiptError("SEC acquisition index documents are not eligible exhibits")
    return url


def resolve_sec_acquisition_location(current: str, location: object, *, cik: object, accession: object) -> str:
    """Reject unsafe raw Location syntax BEFORE URL normalization or follow."""
    from urllib.parse import urljoin

    if (not isinstance(location, str) or not 0 < len(location) <= 8192
            or any(ord(c) <= 32 or ord(c) > 126 for c in location)
            or any(c in location for c in "%\\?#")
            or any(segment in {".", ".."} for segment in location.split("/"))):
        raise ReceiptError("SEC acquisition redirect Location is not canonical")
    validate_sec_acquisition_url(current, cik=cik, accession=accession)
    if location.startswith("//"):
        validate_sec_acquisition_url("https:" + location, cik=cik, accession=accession)
    elif re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", location):
        validate_sec_acquisition_url(location, cik=cik, accession=accession)
    return validate_sec_acquisition_url(urljoin(current, location), cik=cik, accession=accession)


def sec_declared_charset(content_type: str | None) -> str | None:
    """Declared header metadata, not a claim about the decoder actually used."""
    from email.message import Message

    if content_type is None:
        return None
    message = Message()
    message["content-type"] = content_type
    return message.get_content_charset()


def validate_sec_acquisition_receipt(
    receipt: object, *, cik: object, accession: object, source_url: object,
    source_text: str, entity_body: bytes | None = None,
) -> dict[str, Any]:
    """Replay optional acquisition metadata; this does not authorize source use.

    Entity bytes mean requests.Response.content AFTER HTTP Content-Encoding
    processing, never raw wire bytes. UTF-8/Latin-1 are reversible here, so a
    retained decoded body can replay that exact transformation without minting
    missing transport history. No current-time, network or rights decision exists
    in this validator.
    """
    from copy import deepcopy
    from datetime import datetime

    def fail(message: str) -> None:
        raise ReceiptError(f"invalid SEC acquisition receipt: {message}")

    if type(receipt) is not dict or set(receipt) != _SEC_ACQUISITION_KEYS:
        fail("closed schema keys")
    if (receipt["schema"] != SEC_ACQUISITION_SCHEMA
            or receipt["redirect_policy"] != SEC_REDIRECT_POLICY
            or type(receipt["http_status"]) is not int or receipt["http_status"] != 200
            or receipt["body_representation"] != "requests.content_after_content_decoding"):
        fail("schema, redirect policy or response representation")
    key = _sec_filing_key(cik, accession)
    if type(receipt["filing_key"]) is not dict or receipt["filing_key"] != key:
        fail("filing identity")
    current = validate_sec_acquisition_url(receipt["requested_url"], **key)
    if current != source_url:
        fail("requested URL differs from retained source URL")
    hops = receipt["redirects"]
    if type(hops) is not list or len(hops) > 5:
        fail("redirect count")
    visited = {current}
    for hop in hops:
        if type(hop) is not dict or set(hop) != {"url", "status", "location", "next_url"}:
            fail("closed redirect keys")
        if hop["url"] != current or type(hop["status"]) is not int or hop["status"] not in {301, 302, 303, 307, 308}:
            fail("redirect chain or status")
        location = hop["location"]
        next_url = resolve_sec_acquisition_location(current, location, **key)
        if next_url != hop["next_url"] or next_url in visited:
            fail("redirect target or cycle")
        visited.add(next_url)
        current = next_url
    if validate_sec_acquisition_url(receipt["final_url"], **key) != current:
        fail("final URL differs from observed chain")
    for field, limit in (("content_type", 1024), ("content_encoding", 256), ("declared_charset", 128)):
        value = receipt[field]
        if value is not None and (not isinstance(value, str) or len(value) > limit or "\r" in value or "\n" in value):
            fail(f"{field} metadata")
    if receipt["declared_charset"] != sec_declared_charset(receipt["content_type"]):
        fail("declared charset differs from Content-Type")
    acquired_at = receipt["acquired_at"]
    if not isinstance(acquired_at, str) or not _SEC_ACQUIRED_AT.fullmatch(acquired_at):
        fail("acquisition clock")
    try:
        datetime.fromisoformat(acquired_at[:-1] + "+00:00")
    except ValueError:
        fail("acquisition clock")
    if (not isinstance(receipt["decoder"], str) or not isinstance(receipt["decode_policy"], str)
            or receipt["decoder"] not in {"utf-8", "latin-1"} or receipt["decode_errors"] != "strict"
            or receipt["decode_policy"] not in {"utf8_strict", "utf8_strict_then_latin1_strict"}
            or (receipt["decode_policy"] == "utf8_strict" and receipt["decoder"] != "utf-8")):
        fail("decoder or error policy")
    for field in ("entity_sha256", "source_sha256"):
        if not isinstance(receipt[field], str) or not _SEC_SHA.fullmatch(receipt[field]):
            fail(f"{field} digest")
    for field in ("entity_length", "source_utf8_length"):
        if type(receipt[field]) is not int or receipt[field] < 1:
            fail(f"{field} length")
    if not isinstance(source_text, str) or not source_text:
        fail("source text")
    try:
        source_bytes = source_text.encode("utf-8", errors="strict")
        replay_entity = source_text.encode(receipt["decoder"], errors="strict")
    except UnicodeError:
        fail("source text cannot replay the recorded encoding")
    if (sha256_bytes(source_bytes) != receipt["source_sha256"]
            or len(source_bytes) != receipt["source_utf8_length"]
            or sha256_bytes(replay_entity) != receipt["entity_sha256"]
            or len(replay_entity) != receipt["entity_length"]):
        fail("entity or source digest/length")
    if entity_body is not None and (not isinstance(entity_body, bytes) or entity_body != replay_entity):
        fail("actual response entity differs from decoded source")
    if receipt["decoder"] == "latin-1":
        try:
            replay_entity.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            pass
        else:
            fail("Latin-1 fallback was not required by the recorded policy")
    return deepcopy(receipt)
