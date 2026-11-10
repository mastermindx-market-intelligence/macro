"""Strict SEC structured Schedule 13G/A identity-evidence parser.

Pure stdlib. No I/O, no network, no dependency installation, no clock reads,
no fuzzy joining and no preselected security. Every refusal is a typed
``ValueError``. This module extracts identity evidence from a single
Schedule 13G / 13G/A submission; it never binds canonical identity.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = ["Sec13gIdentityEvidence", "parse_schedule13g_evidence"]

UTC = timezone.utc
MAX_RAW_BYTES = 2 * 1024 * 1024
SCHEDULE13G_NAMESPACE = "http://www.sec.gov/edgar/schedule13g"
_COMMON_NAMESPACE = "http://www.sec.gov/edgar/common"
_NS = "{" + SCHEDULE13G_NAMESPACE + "}"
ACCEPTED_FORM_TYPES = ("SCHEDULE 13G", "SCHEDULE 13G/A")

_RE_SEC_DOCUMENT_LINE = re.compile(
    r"^<SEC-DOCUMENT>(\d{10}-\d{2}-\d{6})\.txt\b", re.MULTILINE
)
_RE_ACCESSION_NUMBER = re.compile(
    r"^ACCESSION NUMBER:[ \t]*(\d{10}-\d{2}-\d{6})[ \t]*\r?$", re.MULTILINE
)
_RE_SUBMISSION_TYPE = re.compile(
    r"^CONFORMED SUBMISSION TYPE:[ \t]*(\S[^\r\n]*)", re.MULTILINE
)
_RE_ACCEPTANCE_DATETIME = re.compile(
    r"^<ACCEPTANCE-DATETIME>(\d{14})[ \t]*\r?$", re.MULTILINE
)
_RE_SUBJECT_COMPANY = re.compile(r"^SUBJECT COMPANY:[ \t]*\r?$", re.MULTILINE)
_RE_FILED_BY = re.compile(r"^FILED BY:[ \t]*\r?$", re.MULTILINE)
_RE_CENTRAL_INDEX_KEY = re.compile(
    r"^[ \t]*CENTRAL INDEX KEY:[ \t]*(\d+)[ \t]*\r?$", re.MULTILINE
)
_RE_DOCUMENT_TYPE = re.compile(r"^<TYPE>[ \t]*([^\r\n<]*)", re.MULTILINE)
_RE_TEN_DIGITS = re.compile(r"\d{10}")
_RE_CUSIP = re.compile(r"[0-9A-Z]{9}")
_RE_HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


try:
    AMERICA_NEW_YORK = ZoneInfo("America/New_York")
except ZoneInfoNotFoundError:
    AMERICA_NEW_YORK = None


@dataclass(frozen=True)
class Sec13gIdentityEvidence:
    """Identity evidence carried by one strict Schedule 13G/13G/A submission."""

    accession: str
    issuer_cik: str
    issuer_name: str
    share_class: str
    cusip: str
    event_on: date
    accepted_at: datetime
    retained_at: datetime
    known_at: datetime
    raw_sha256: str


@dataclass(frozen=True)
class _XmlFacts:
    issuer_cik: str
    issuer_name: str
    share_class: str
    cusip: str
    event_on: date
    submission_type: str


def _checked_raw_bytes(raw, expected_sha256: str) -> bytes:
    if isinstance(raw, (bytearray, memoryview)):
        raw = bytes(raw)
    if not isinstance(raw, bytes):
        raise ValueError("raw document must be bytes")
    if not raw:
        raise ValueError("raw document is empty")
    if len(raw) > MAX_RAW_BYTES:
        raise ValueError(
            "raw document is %d bytes; the strict limit is %d bytes"
            % (len(raw), MAX_RAW_BYTES)
        )
    if not isinstance(expected_sha256, str):
        raise ValueError("expected_sha256 must be a 64-hex-digit SHA-256 string")
    wanted = expected_sha256.strip().lower()
    if not _RE_HEX_DIGEST.fullmatch(wanted):
        raise ValueError("expected_sha256 must be a 64-hex-digit SHA-256 string")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != wanted:
        raise ValueError(
            "raw byte SHA-256 mismatch: expected %s, got %s (byte tamper refused)"
            % (wanted, actual)
        )
    return raw


def _checked_retained_at(retained_at) -> datetime:
    if not isinstance(retained_at, datetime):
        raise ValueError("retained_at must be a timezone-aware datetime")
    if retained_at.tzinfo is None or retained_at.utcoffset() is None:
        raise ValueError("retained_at must be timezone-aware; naive timestamps refused")
    if retained_at.utcoffset() != timedelta(0):
        raise ValueError("retained_at must be expressed in UTC")
    return retained_at.astimezone(UTC)


def _decoded_utf8(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("raw document is not valid UTF-8: %s" % exc) from exc
    if text.startswith("﻿"):
        raise ValueError("raw document must not begin with a byte-order mark")
    return text


def _reject_dtd_or_entities(text: str) -> None:
    marker = re.search(r"<!(?!--)", text)
    if marker:
        snippet = text[marker.start() : marker.start() + 40]
        raise ValueError("DTD or entity declaration refused near %r" % snippet)


def _blocks(text: str, tag: str) -> list:
    pattern = re.compile(
        r"<%s>(.*?)</%s>" % (re.escape(tag), re.escape(tag)), re.DOTALL
    )
    return pattern.findall(text)


def _single_block(text: str, tag: str) -> str:
    opens = len(re.findall(r"<%s>" % re.escape(tag), text))
    closes = len(re.findall(r"</%s>" % re.escape(tag), text))
    found = _blocks(text, tag)
    if opens != 1 or closes != 1 or len(found) != 1:
        raise ValueError(
            "expected exactly one <%s> block, found opens=%d closes=%d blocks=%d"
            % (tag, opens, closes, len(found))
        )
    return found[0]


def _single_match(pattern: re.Pattern, text: str, label: str) -> str:
    found = pattern.findall(text)
    if len(found) != 1:
        raise ValueError("expected exactly one %s, found %d" % (label, len(found)))
    return found[0]


def _parse_acceptance_datetime(header: str) -> datetime:
    stamp = _single_match(
        _RE_ACCEPTANCE_DATETIME, header, "14-digit SGML ACCEPTANCE-DATETIME"
    )
    try:
        local = datetime.strptime(stamp, "%Y%m%d%H%M%S")
    except ValueError as exc:
        raise ValueError(
            "malformed ACCEPTANCE-DATETIME %r; no clock may be guessed" % stamp
        ) from exc
    if AMERICA_NEW_YORK is None:
        raise ValueError("IANA America/New_York timezone data required; no clock fallback")
    early = local.replace(tzinfo=AMERICA_NEW_YORK, fold=0)
    late = local.replace(tzinfo=AMERICA_NEW_YORK, fold=1)
    if early.utcoffset() != late.utcoffset():
        raise ValueError("ambiguous or nonexistent ACCEPTANCE-DATETIME")
    accepted = early.astimezone(UTC)
    if accepted.astimezone(AMERICA_NEW_YORK).replace(tzinfo=None) != local:
        raise ValueError("nonexistent ACCEPTANCE-DATETIME")
    return accepted


def _parse_subject_company_cik(header: str) -> str:
    subjects = list(_RE_SUBJECT_COMPANY.finditer(header))
    if len(subjects) != 1:
        raise ValueError("exactly one SUBJECT COMPANY section required")
    subject = subjects[0]
    filed_by_matches = list(_RE_FILED_BY.finditer(header))
    if len(filed_by_matches) > 1:
        raise ValueError("multiple FILED BY sections are ambiguous")
    end = len(header)
    if filed_by_matches:
        if filed_by_matches[0].start() <= subject.end():
            raise ValueError("FILED BY precedes SUBJECT COMPANY")
        end = filed_by_matches[0].start()
    scope = header[subject.end():end]
    cik = _single_match(
        _RE_CENTRAL_INDEX_KEY, scope, "SUBJECT COMPANY CENTRAL INDEX KEY"
    )
    if not _RE_TEN_DIGITS.fullmatch(cik):
        raise ValueError(
            "SUBJECT COMPANY CIK must be zero-padded 10 digits, got %r" % cik
        )
    return cik


def _parse_document(document: str):
    document_type = _single_match(_RE_DOCUMENT_TYPE, document, "DOCUMENT <TYPE>").strip()
    if document_type not in ACCEPTED_FORM_TYPES:
        raise ValueError(
            "unsupported DOCUMENT <TYPE> %r; expected SCHEDULE 13G or SCHEDULE 13G/A"
            % document_type
        )
    text_block = _single_block(document, "TEXT")
    xml_text = _single_block(text_block, "XML").strip()
    return document_type, xml_text


def _parse_xml(xml_text: str):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("malformed or ambiguous XML: %s" % exc) from exc
    if root.tag != _NS + "edgarSubmission":
        raise ValueError(
            "XML root must be {%s}edgarSubmission, got %r"
            % (SCHEDULE13G_NAMESPACE, root.tag)
        )
    for element in root.iter():
        tag = element.tag
        if not isinstance(tag, str):
            raise ValueError("XML comments or processing instructions are not elements")
        if not tag.startswith("{"):
            raise ValueError("unqualified XML identity element refused")
        namespace = tag[1 : tag.index("}")]
        if namespace not in (SCHEDULE13G_NAMESPACE, _COMMON_NAMESPACE):
            raise ValueError("unsupported XML namespace %r" % namespace)
    return root


def _local_name(element) -> str:
    tag = element.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[tag.index("}") + 1 :]
    return str(tag)


def _unique_child(parent, name: str):
    children = parent.findall(_NS + name)
    if len(children) != 1:
        raise ValueError(
            "expected exactly one <%s> under <%s>, found %d"
            % (name, _local_name(parent), len(children))
        )
    return children[0]


def _unique_text(parent, name: str) -> str:
    element = _unique_child(parent, name)
    if len(element):
        raise ValueError("identity leaf <%s> contains nested elements" % name)
    if element.text is None or not element.text.strip():
        raise ValueError("element <%s> must carry explicit text" % name)
    return element.text.strip()


def _parse_event_date(text: str) -> date:
    if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", text):
        raise ValueError("event date must be explicit MM/DD/YYYY")
    try:
        return datetime.strptime(text, "%m/%d/%Y").date()
    except ValueError as exc:
        raise ValueError(
            "eventDateRequiresFilingThisStatement %r must be explicit MM/DD/YYYY"
            % text
        ) from exc


def _validate_cusip(cusip: str) -> None:
    if not _RE_CUSIP.fullmatch(cusip):
        raise ValueError(
            "CUSIP %r must be exactly 9 uppercase alphanumeric characters" % cusip
        )
    total = 0
    for index, character in enumerate(cusip[:8]):
        if character.isdigit():
            value = int(character)
        else:
            value = 10 + ord(character) - ord("A")
        if index % 2 == 1:
            value *= 2
        total += value // 10 + value % 10
    expected = (10 - total % 10) % 10
    if expected != int(cusip[8]):
        raise ValueError(
            "CUSIP %r fails the strict check digit (expected %d)" % (cusip, expected)
        )


def _extract_xml_facts(root) -> _XmlFacts:
    header_data = _unique_child(root, "headerData")
    submission_type = _unique_text(header_data, "submissionType")
    form_data = _unique_child(root, "formData")
    cover = _unique_child(form_data, "coverPageHeader")
    share_class = _unique_text(cover, "securitiesClassTitle")
    event_text = _unique_text(cover, "eventDateRequiresFilingThisStatement")
    event_on = _parse_event_date(event_text)
    issuer_info = _unique_child(cover, "issuerInfo")
    issuer_cik = _unique_text(issuer_info, "issuerCik")
    if not _RE_TEN_DIGITS.fullmatch(issuer_cik):
        raise ValueError(
            "issuerCik %r must be a zero-padded 10-digit CIK" % issuer_cik
        )
    issuer_name = _unique_text(issuer_info, "issuerName")
    cusips = _unique_child(issuer_info, "issuerCusips")
    cusip = _unique_text(cusips, "issuerCusipNumber")
    _validate_cusip(cusip)
    return _XmlFacts(
        issuer_cik=issuer_cik,
        issuer_name=issuer_name,
        share_class=share_class,
        cusip=cusip,
        event_on=event_on,
        submission_type=submission_type,
    )


def parse_schedule13g_evidence(
    raw: bytes, *, expected_sha256: str, retained_at: datetime
) -> Sec13gIdentityEvidence:
    """Parse one Schedule 13G/13G/A submission into identity evidence.

    Every refusal raises ``ValueError``. The caller supplies the exact raw
    bytes, the expected SHA-256 of those bytes, and the aware UTC retention
    timestamp; nothing is read from disk, network or the system clock.
    """
    raw = _checked_raw_bytes(raw, expected_sha256)
    retained = _checked_retained_at(retained_at)
    text = _decoded_utf8(raw)
    _reject_dtd_or_entities(text)

    wire_accession = _single_match(
        _RE_SEC_DOCUMENT_LINE, text, "SEC-DOCUMENT accession line"
    )
    header = _single_block(text, "SEC-HEADER")
    document = _single_block(text, "DOCUMENT")

    accepted_at = _parse_acceptance_datetime(header)
    header_accession = _single_match(_RE_ACCESSION_NUMBER, header, "ACCESSION NUMBER")
    if header_accession != wire_accession:
        raise ValueError(
            "SEC-HEADER accession %r does not match SEC-DOCUMENT accession %r"
            % (header_accession, wire_accession)
        )
    header_type = _single_match(
        _RE_SUBMISSION_TYPE, header, "CONFORMED SUBMISSION TYPE"
    ).strip()
    if header_type not in ACCEPTED_FORM_TYPES:
        raise ValueError("unsupported CONFORMED SUBMISSION TYPE %r" % header_type)
    subject_cik = _parse_subject_company_cik(header)

    document_type, xml_text = _parse_document(document)
    if document_type != header_type:
        raise ValueError(
            "DOCUMENT <TYPE> %r does not match CONFORMED SUBMISSION TYPE %r"
            % (document_type, header_type)
        )

    root = _parse_xml(xml_text)
    facts = _extract_xml_facts(root)
    if facts.submission_type != document_type:
        raise ValueError(
            "XML submissionType %r does not match DOCUMENT <TYPE> %r"
            % (facts.submission_type, document_type)
        )
    if facts.issuer_cik != subject_cik:
        raise ValueError(
            "SEC-HEADER SUBJECT COMPANY CIK %r does not match XML issuerCik %r; "
            "the FILED BY custodian CIK never binds issuer identity"
            % (subject_cik, facts.issuer_cik)
        )

    accepted_local_date = accepted_at.astimezone(AMERICA_NEW_YORK).date()
    if facts.event_on > accepted_local_date:
        raise ValueError(
            "event date %s would backdate this statement past its acceptance date %s"
            % (facts.event_on.isoformat(), accepted_local_date.isoformat())
        )
    if accepted_at > retained:
        raise ValueError(
            "acceptance %s is later than retained_at %s; cutoff conflicts refused"
            % (accepted_at.isoformat(), retained.isoformat())
        )

    return Sec13gIdentityEvidence(
        accession=header_accession,
        issuer_cik=facts.issuer_cik,
        issuer_name=facts.issuer_name,
        share_class=facts.share_class,
        cusip=facts.cusip,
        event_on=facts.event_on,
        accepted_at=accepted_at,
        retained_at=retained,
        known_at=max(accepted_at, retained),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
    )
