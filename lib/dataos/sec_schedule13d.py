"""Strict SEC structured Schedule 13D/A identity-evidence parser.

Pure stdlib. No I/O, no network, no dependency installation, no clock reads,
no fuzzy joining and no preselected security. Every refusal is a typed
``ValueError``. This module extracts issuer, share-class and reporting-person
evidence from a single Schedule 13D / 13D/A submission; it never binds
canonical identity, never aggregates group members into a common position,
and carries the Item 2 / Item 5 narratives as source text only.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from .sec_filing_identity import (
    AMERICA_NEW_YORK,
    _RE_ACCESSION_NUMBER,
    _RE_DOCUMENT_TYPE,
    _RE_SEC_DOCUMENT_LINE,
    _RE_SUBMISSION_TYPE,
    _RE_TEN_DIGITS,
    _checked_raw_bytes,
    _checked_retained_at,
    _decoded_utf8,
    _parse_acceptance_datetime,
    _parse_event_date,
    _parse_subject_company_cik,
    _reject_dtd_or_entities,
    _single_block,
    _single_match,
    _validate_cusip,
)

__all__ = [
    "Schedule13dEvidence",
    "Schedule13dReportingPerson",
    "parse_schedule13d_evidence",
]

SCHEDULE13D_NAMESPACE = "http://www.sec.gov/edgar/schedule13D"
_COMMON_NAMESPACE = "http://www.sec.gov/edgar/common"
_DNS = "{" + SCHEDULE13D_NAMESPACE + "}"
ACCEPTED_13D_FORM_TYPES = ("SCHEDULE 13D", "SCHEDULE 13D/A")
MAX_REPORTING_PERSONS = 64
_MAX_DECIMAL_DIGITS = 30

_RE_DECIMAL_STRING = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_RE_ACCESSION_FORMAT = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_RE_DIGITS = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class Schedule13dReportingPerson:
    """One reporting person exactly as the 13D/A cover page states it.

    ``cik`` is the person's own ``reportingPersonCIK`` when
    ``reportingPersonNoCIK`` is ``N`` and is explicitly ``None`` when that
    flag is ``Y``; the issuer or filing-agent CIK is never substituted.
    Amount fields stay canonical decimal strings so no binary float ever
    touches a share count.
    """

    name: str
    cik: Optional[str]
    no_cik: bool
    member_of_group: Optional[str]
    fund_type: Optional[str]
    citizenship_or_organization: Optional[str]
    type_of_reporting_person: Optional[str]
    legal_proceedings: Optional[bool]
    sole_voting_power: str
    shared_voting_power: str
    sole_dispositive_power: str
    shared_dispositive_power: str
    aggregate_amount_owned: str
    aggregate_exclude_shares: bool
    percent_of_class: str
    comment: Optional[str]


@dataclass(frozen=True)
class Schedule13dEvidence:
    """Identity and cover-page evidence carried by one Schedule 13D/13D/A."""

    accession: str
    form_type: str
    amendment_no: int
    previously_filed: bool
    previous_accession: Optional[str]
    issuer_cik: str
    issuer_name: str
    share_class: str
    cusip: str
    event_on: date
    accepted_at: datetime
    retained_at: datetime
    known_at: datetime
    raw_sha256: str
    reporting_persons: Tuple[Schedule13dReportingPerson, ...]
    item2_principal_job: str
    item5_percentage_of_class: str


def _d_unique_child(parent, name: str):
    children = parent.findall(_DNS + name)
    if len(children) != 1:
        raise ValueError(
            "expected exactly one <%s> under <%s>, found %d"
            % (name, _local_name_of(parent), len(children))
        )
    return children[0]


def _d_children(parent, name: str) -> list:
    return parent.findall(_DNS + name)


def _local_name_of(element) -> str:
    tag = element.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[tag.index("}") + 1 :]
    return str(tag)


def _leaf_text(element, name: str) -> str:
    if len(element):
        raise ValueError("identity leaf <%s> contains nested elements" % name)
    text = element.text
    if text is None or not text.strip():
        raise ValueError("element <%s> must carry explicit text" % name)
    return text.strip()


def _d_leaf(parent, name: str) -> str:
    return _leaf_text(_d_unique_child(parent, name), name)


def _d_optional_leaf(parent, name: str) -> Optional[str]:
    found = _d_children(parent, name)
    if not found:
        return None
    if len(found) != 1:
        raise ValueError(
            "expected at most one <%s> under <%s>, found %d"
            % (name, _local_name_of(parent), len(found))
        )
    return _leaf_text(found[0], name)


def _d_yn(parent, name: str, *, required: bool = True) -> Optional[bool]:
    found = _d_children(parent, name)
    if not found:
        if required:
            raise ValueError("missing required <%s> flag" % name)
        return None
    if len(found) != 1:
        raise ValueError(
            "expected exactly one <%s> under <%s>, found %d"
            % (name, _local_name_of(parent), len(found))
        )
    text = _leaf_text(found[0], name)
    if text == "Y":
        return True
    if text == "N":
        return False
    raise ValueError("<%s> must be exactly Y or N, got %r" % (name, text))


def _d_bool_literal(parent, name: str) -> bool:
    """Read a schema boolean carried as the literal ``true``/``false``."""
    found = _d_children(parent, name)
    if len(found) != 1:
        raise ValueError(
            "expected exactly one <%s> under <%s>, found %d"
            % (name, _local_name_of(parent), len(found))
        )
    text = _leaf_text(found[0], name)
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(
        "<%s> must be exactly true or false, got %r" % (name, text)
    )


def _canonical_decimal(text: str, label: str) -> str:
    """Return the canonical plain decimal string for an EDGAR number.

    Accepts only unsigned plain decimals (no exponent, no NaN/Infinity, no
    sign, finite by construction) and re-renders them without leading zeros
    or a trailing zero-only fraction, so ``804139.00`` and ``0.00`` come back
    as ``804139`` and ``0``. The value is never routed through a binary
    float.
    """
    if not _RE_DECIMAL_STRING.fullmatch(text):
        raise ValueError(
            "%s must be a plain nonnegative decimal number with no sign, "
            "exponent, NaN or Infinity, got %r" % (label, text)
        )
    whole, _, fraction = text.partition(".")
    whole = whole.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    canonical = whole if not fraction else whole + "." + fraction
    if len(canonical.replace(".", "", 1)) > _MAX_DECIMAL_DIGITS:
        raise ValueError(
            "%s exceeds the strict %d significant-digit limit: %r"
            % (label, _MAX_DECIMAL_DIGITS, text)
        )
    return canonical


def _decimal_field(parent, name: str) -> str:
    return _canonical_decimal(_d_leaf(parent, name), "<%s>" % name)


def _percent_field(parent, name: str) -> str:
    raw = _d_leaf(parent, name)
    canonical = _canonical_decimal(raw, "<%s>" % name)
    try:
        value = Decimal(canonical)
    except InvalidOperation as exc:  # pragma: no cover - regex already gates this
        raise ValueError("<%s> %r is not a usable decimal" % (name, raw)) from exc
    if value < 0 or value > 100:
        raise ValueError(
            "<%s> must be between 0 and 100 inclusive, got %r" % (name, raw)
        )
    return canonical


def _d_accession(parent, name: str) -> Optional[str]:
    text = _d_optional_leaf(parent, name)
    if text is None:
        return None
    if not _RE_ACCESSION_FORMAT.fullmatch(text):
        raise ValueError(
            "<%s> %r must be a 0000000000-00-000000 accession number"
            % (name, text)
        )
    return text


def _amendment_number(cover) -> int:
    text = _d_leaf(cover, "amendmentNo")
    if not _RE_DIGITS.fullmatch(text):
        raise ValueError(
            "<amendmentNo> %r must be a plain nonnegative integer" % text
        )
    if len(text) > 6:
        raise ValueError("<amendmentNo> %r is out of range" % text)
    return int(text)


def _parse_13d_document(document: str):
    document_type = _single_match(_RE_DOCUMENT_TYPE, document, "DOCUMENT <TYPE>").strip()
    if document_type not in ACCEPTED_13D_FORM_TYPES:
        raise ValueError(
            "unsupported DOCUMENT <TYPE> %r; expected SCHEDULE 13D or SCHEDULE 13D/A"
            % document_type
        )
    text_block = _single_block(document, "TEXT")
    xml_text = _single_block(text_block, "XML").strip()
    return document_type, xml_text


def _parse_13d_xml(xml_text: str):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("malformed or ambiguous XML: %s" % exc) from exc
    if root.tag != _DNS + "edgarSubmission":
        raise ValueError(
            "XML root must be {%s}edgarSubmission (case-sensitive), got %r"
            % (SCHEDULE13D_NAMESPACE, root.tag)
        )
    for element in root.iter():
        tag = element.tag
        if not isinstance(tag, str):
            # Comments and processing instructions carry no identity facts.
            continue
        if not tag.startswith("{"):
            raise ValueError("unqualified XML element %r refused" % tag)
        namespace = tag[1 : tag.index("}")]
        if namespace not in (SCHEDULE13D_NAMESPACE, _COMMON_NAMESPACE):
            raise ValueError("unsupported XML namespace %r" % namespace)
    return root


def _parse_reporting_person(info) -> Schedule13dReportingPerson:
    no_cik = _d_yn(info, "reportingPersonNoCIK")
    assert no_cik is not None  # required flag; _d_yn already raised if absent
    cik_nodes = _d_children(info, "reportingPersonCIK")
    if no_cik:
        if cik_nodes:
            raise ValueError(
                "<reportingPersonCIK> contradicts reportingPersonNoCIK=Y; "
                "a no-CIK person carries no CIK evidence"
            )
        cik = None
    else:
        if len(cik_nodes) != 1:
            raise ValueError(
                "expected exactly one <reportingPersonCIK> when "
                "reportingPersonNoCIK=N, found %d" % len(cik_nodes)
            )
        cik = _leaf_text(cik_nodes[0], "reportingPersonCIK")
        if not _RE_TEN_DIGITS.fullmatch(cik):
            raise ValueError(
                "reportingPersonCIK %r must be a zero-padded 10-digit CIK" % cik
            )
    name = _d_leaf(info, "reportingPersonName")
    return Schedule13dReportingPerson(
        name=name,
        cik=cik,
        no_cik=no_cik,
        member_of_group=_d_optional_leaf(info, "memberOfGroup"),
        fund_type=_d_optional_leaf(info, "fundType"),
        citizenship_or_organization=_d_optional_leaf(info, "citizenshipOrOrganization"),
        type_of_reporting_person=_d_optional_leaf(info, "typeOfReportingPerson"),
        legal_proceedings=_d_yn(info, "legalProceedings", required=False),
        sole_voting_power=_decimal_field(info, "soleVotingPower"),
        shared_voting_power=_decimal_field(info, "sharedVotingPower"),
        sole_dispositive_power=_decimal_field(info, "soleDispositivePower"),
        shared_dispositive_power=_decimal_field(info, "sharedDispositivePower"),
        aggregate_amount_owned=_decimal_field(info, "aggregateAmountOwned"),
        aggregate_exclude_shares=_d_yn(info, "isAggregateExcludeShares"),
        percent_of_class=_percent_field(info, "percentOfClass"),
        comment=_d_optional_leaf(info, "commentContent"),
    )


def _parse_reporting_persons(form_data) -> Tuple[Schedule13dReportingPerson, ...]:
    container = _d_unique_child(form_data, "reportingPersons")
    infos = _d_children(container, "reportingPersonInfo")
    element_children = [child for child in container if isinstance(child.tag, str)]
    if not infos or len(element_children) != len(infos):
        raise ValueError(
            "<reportingPersons> must carry one or more <reportingPersonInfo> "
            "elements and nothing else"
        )
    if len(infos) > MAX_REPORTING_PERSONS:
        raise ValueError(
            "refusing %d reporting persons; the strict bound is %d"
            % (len(infos), MAX_REPORTING_PERSONS)
        )
    persons = tuple(_parse_reporting_person(info) for info in infos)
    seen_names = {}
    seen_ciks = {}
    for person in persons:
        name_key = person.name.casefold()
        if name_key in seen_names:
            raise ValueError(
                "duplicate reporting person name %r (also used by %r)"
                % (person.name, seen_names[name_key])
            )
        seen_names[name_key] = person.name
        if person.cik is not None:
            if person.cik in seen_ciks:
                raise ValueError(
                    "duplicate reporting person CIK %s (%r and %r)"
                    % (person.cik, seen_ciks[person.cik], person.name)
                )
            seen_ciks[person.cik] = person.name
    return persons


def parse_schedule13d_evidence(
    raw: bytes, *, expected_sha256: str, retained_at: datetime
) -> Schedule13dEvidence:
    """Parse one Schedule 13D/13D/A submission into identity evidence.

    Every refusal raises ``ValueError``. The caller supplies the exact raw
    bytes, the expected SHA-256 of those bytes, and the aware UTC retention
    timestamp; nothing is read from disk, network or the system clock. The
    Item 2 / Item 5 narratives are returned verbatim as source text and are
    not interpreted, and no group position is folded into a common aggregate.
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
    if header_type not in ACCEPTED_13D_FORM_TYPES:
        raise ValueError(
            "unsupported CONFORMED SUBMISSION TYPE %r; expected SCHEDULE 13D "
            "or SCHEDULE 13D/A" % header_type
        )
    subject_cik = _parse_subject_company_cik(header)

    document_type, xml_text = _parse_13d_document(document)
    if document_type != header_type:
        raise ValueError(
            "DOCUMENT <TYPE> %r does not match CONFORMED SUBMISSION TYPE %r"
            % (document_type, header_type)
        )

    root = _parse_13d_xml(xml_text)

    header_data = _d_unique_child(root, "headerData")
    submission_type = _d_leaf(header_data, "submissionType")
    if submission_type != document_type:
        raise ValueError(
            "XML submissionType %r does not match DOCUMENT <TYPE> %r"
            % (submission_type, document_type)
        )
    previous_accession = _d_accession(header_data, "previousAccessionNumber")

    form_data = _d_unique_child(root, "formData")
    cover = _d_unique_child(form_data, "coverPageHeader")
    amendment_no = _amendment_number(cover)
    if header_type == "SCHEDULE 13D" and amendment_no != 0:
        raise ValueError(
            "an initial SCHEDULE 13D cannot carry amendmentNo %d" % amendment_no
        )
    if header_type == "SCHEDULE 13D/A" and amendment_no < 1:
        raise ValueError(
            "a SCHEDULE 13D/A must carry a positive amendmentNo, got %d"
            % amendment_no
        )
    previously_filed = _d_bool_literal(cover, "previouslyFiledFlag")
    share_class = _d_leaf(cover, "securitiesClassTitle")
    event_on = _parse_event_date(_d_leaf(cover, "dateOfEvent"))

    issuer_info = _d_unique_child(cover, "issuerInfo")
    issuer_cik = _d_leaf(issuer_info, "issuerCIK")
    if not _RE_TEN_DIGITS.fullmatch(issuer_cik):
        raise ValueError(
            "issuerCIK %r must be a zero-padded 10-digit CIK" % issuer_cik
        )
    issuer_name = _d_leaf(issuer_info, "issuerName")
    cusips = _d_unique_child(issuer_info, "issuerCusips")
    cusip = _d_leaf(cusips, "issuerCusipNumber")
    _validate_cusip(cusip)

    if issuer_cik != subject_cik:
        raise ValueError(
            "SEC-HEADER SUBJECT COMPANY CIK %r does not match XML issuerCIK %r; "
            "the FILED BY custodian CIK never binds issuer identity"
            % (subject_cik, issuer_cik)
        )

    reporting_persons = _parse_reporting_persons(form_data)

    items = _d_unique_child(form_data, "items1To7")
    item2 = _d_unique_child(items, "item2")
    principal_job = _d_leaf(item2, "principalJob")
    item5 = _d_unique_child(items, "item5")
    item5_text = _d_leaf(item5, "percentageOfClassSecurities")

    accepted_local_date = accepted_at.astimezone(AMERICA_NEW_YORK).date()
    if event_on > accepted_local_date:
        raise ValueError(
            "event date %s would backdate this statement past its acceptance "
            "date %s" % (event_on.isoformat(), accepted_local_date.isoformat())
        )
    if accepted_at > retained:
        raise ValueError(
            "acceptance %s is later than retained_at %s; cutoff conflicts refused"
            % (accepted_at.isoformat(), retained.isoformat())
        )

    return Schedule13dEvidence(
        accession=header_accession,
        form_type=header_type,
        amendment_no=amendment_no,
        previously_filed=previously_filed,
        previous_accession=previous_accession,
        issuer_cik=issuer_cik,
        issuer_name=issuer_name,
        share_class=share_class,
        cusip=cusip,
        event_on=event_on,
        accepted_at=accepted_at,
        retained_at=retained,
        known_at=max(accepted_at, retained),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        reporting_persons=reporting_persons,
        item2_principal_job=principal_job,
        item5_percentage_of_class=item5_text,
    )
