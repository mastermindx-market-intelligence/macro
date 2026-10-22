"""Discriminating tests for the strict Schedule 13G/A identity parser.

Every fixture is synthetic and built in memory. No host, repository,
network or market-data effects: documents are wire-shaped but clearly
synthetic (SYNTHETIC ISSUER INC / SYNTHETIC FILER LLC), and every digest
is computed from the synthetic bytes themselves.
"""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import date, datetime, timedelta, timezone

import pytest
from lib.dataos import sec_filing_identity

UTC = timezone.utc

ISSUER_CIK = "0009999999"
FILER_CIK = "0001111111"
ISSUER_NAME = "SYNTHETIC ISSUER INC"
CUSIP = "123456782"
LETTERED_CUSIP = "12345Y781"
SHARE_CLASS = "Common Stock"
EVENT_DATE = "03/13/2026"
ACCESSION = "0001111111-26-000001"
ACCEPTANCE_LOCAL = "20260326150603"
ACCEPTED_UTC = datetime(2026, 3, 26, 19, 6, 3, tzinfo=UTC)
RETAINED_UTC = datetime(2026, 3, 26, 21, 0, 0, tzinfo=UTC)


def _header(params) -> str:
    return (
        "<SEC-HEADER>%s.hdr.sgml : 20260326\n" % params["accession"]
        + "<ACCEPTANCE-DATETIME>%s\n" % params["acceptance"]
        + "ACCESSION NUMBER:\t\t%s\n" % params["accession"]
        + "CONFORMED SUBMISSION TYPE:\t%s\n" % params["submission_type"]
        + "PUBLIC DOCUMENT COUNT:\t\t1\n"
        + "FILED AS OF DATE:\t\t20260326\n"
        + "DATE AS OF CHANGE:\t\t20260326\n"
        + "\nSUBJECT COMPANY:\n\n\tCOMPANY DATA:\n"
        + "\t\tCOMPANY CONFORMED NAME:\t\t\t%s\n" % params["header_issuer_name"]
        + "\t\tCENTRAL INDEX KEY:\t\t\t%s\n" % params["header_cik"]
        + "\tFILING VALUES:\n"
        + "\t\tFORM TYPE:\t\t%s\n" % params["submission_type"]
        + "\nFILED BY:\n\n\tCOMPANY DATA:\n"
        + "\t\tCOMPANY CONFORMED NAME:\t\t\tSYNTHETIC FILER LLC\n"
        + "\t\tCENTRAL INDEX KEY:\t\t\t%s\n" % params["filed_by_cik"]
        + "\tFILING VALUES:\n"
        + "\t\tFORM TYPE:\t\t%s\n" % params["submission_type"]
        + "</SEC-HEADER>"
    )


def _xml_payload(params) -> str:
    if params.get("omit_cusip"):
        cusip_block = ""
    else:
        cusip_entry = "<issuerCusipNumber>%s</issuerCusipNumber>" % params["cusip"]
        if params.get("duplicate_cusip"):
            cusip_entry += "<issuerCusipNumber>%s</issuerCusipNumber>" % params["cusip"]
        cusip_block = "<issuerCusips>%s</issuerCusips>" % cusip_entry
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<edgarSubmission xmlns="%s" xmlns:com="http://www.sec.gov/edgar/common">'
        % sec_filing_identity.SCHEDULE13G_NAMESPACE
        + "<schemaVersion>X0202</schemaVersion>"
        + "<headerData>"
        + "<submissionType>%s</submissionType>" % params["submission_type"]
        + "<filerInfo><filer><filerCredentials>"
        + "<cik>%s</cik><ccc>XXXXXXXX</ccc>" % params["filer_cik"]
        + "</filerCredentials></filer><liveTestFlag>LIVE</liveTestFlag></filerInfo>"
        + "</headerData>"
        + "<formData>"
        + "<coverPageHeader>"
        + "<amendmentNo>4</amendmentNo>"
        + "<securitiesClassTitle>%s</securitiesClassTitle>" % params["share_class"]
        + "<eventDateRequiresFilingThisStatement>%s</eventDateRequiresFilingThisStatement>"
        % params["event_date"]
        + "<issuerInfo>"
        + "<issuerCik>%s</issuerCik>" % params["issuer_cik"]
        + "<issuerName>%s</issuerName>" % params["issuer_name"]
        + cusip_block
        + "<issuerPrincipalExecutiveOfficeAddress>"
        + "<com:street1>1 Synthetic Way</com:street1>"
        + "<com:city>Synthetic City</com:city>"
        + "<com:stateOrCountry>DE</com:stateOrCountry>"
        + "<com:zipCode>00000</com:zipCode>"
        + "</issuerPrincipalExecutiveOfficeAddress>"
        + "</issuerInfo>"
        + "</coverPageHeader>"
        + "<coverPageHeaderReportingPersonDetails>"
        + "<reportingPersonName>SYNTHETIC FILER LLC</reportingPersonName>"
        + "<citizenshipOrOrganization>DE</citizenshipOrOrganization>"
        + "<classPercent>0</classPercent>"
        + "</coverPageHeaderReportingPersonDetails>"
        + "<items>"
        + "<item1><issuerName>%s</issuerName></item1>" % params["issuer_name"]
        + "<item4><amountBeneficiallyOwned>0</amountBeneficiallyOwned>"
        + "<classPercent>0</classPercent></item4>"
        + "</items>"
        + "<signatureInformation>"
        + "<reportingPersonName>SYNTHETIC FILER LLC</reportingPersonName>"
        + "<signatureDetails><signature>A Synthetic</signature>"
        + "<title>Compliance Officer</title><date>03/26/2026</date>"
        + "</signatureDetails></signatureInformation>"
        + "</formData>"
        + "</edgarSubmission>"
    )


_DEFAULTS = dict(
    issuer_cik=ISSUER_CIK,
    issuer_name=ISSUER_NAME,
    cusip=CUSIP,
    share_class=SHARE_CLASS,
    event_date=EVENT_DATE,
    filer_cik=FILER_CIK,
    filed_by_cik=FILER_CIK,
    header_cik=ISSUER_CIK,
    header_issuer_name=ISSUER_NAME,
    accession=ACCESSION,
    acceptance=ACCEPTANCE_LOCAL,
    submission_type="SCHEDULE 13G/A",
    doc_type="SCHEDULE 13G/A",
    omit_cusip=False,
    duplicate_cusip=False,
)


def build_document(**overrides) -> bytes:
    params = dict(_DEFAULTS)
    params.update(overrides)
    return (
        "<SEC-DOCUMENT>%s.txt : 20260326\n" % params["accession"]
        + _header(params)
        + "\n<DOCUMENT>\n<TYPE>%s\n<SEQUENCE>1\n" % params["doc_type"]
        + "<FILENAME>primary_doc.xml\n<TEXT>\n<XML>\n"
        + _xml_payload(params)
        + "\n</XML>\n</TEXT>\n</DOCUMENT>\n</SEC-DOCUMENT>\n"
    ).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse(raw: bytes, retained_at=RETAINED_UTC):
    return sec_filing_identity.parse_schedule13g_evidence(
        raw, expected_sha256=digest(raw), retained_at=retained_at
    )


def duplicate_segment(raw: bytes, start_tag: str, end_tag: str) -> bytes:
    text = raw.decode("utf-8")
    start = text.index(start_tag)
    end = text.index(end_tag) + len(end_tag)
    segment = text[start:end]
    return (text[:end] + segment + text[end:]).encode("utf-8")


def test_success_parses_synthetic_wire_document():
    evidence = parse(build_document())
    assert evidence.accession == ACCESSION
    assert evidence.issuer_cik == ISSUER_CIK
    assert evidence.issuer_name == ISSUER_NAME
    assert evidence.share_class == SHARE_CLASS
    assert evidence.cusip == CUSIP
    assert evidence.event_on == date(2026, 3, 13)
    assert evidence.raw_sha256 == digest(build_document())


def test_acceptance_datetime_converts_new_york_to_utc():
    evidence = parse(build_document())
    assert evidence.accepted_at == ACCEPTED_UTC
    assert evidence.accepted_at.tzinfo is not None
    assert evidence.accepted_at.utcoffset() == timedelta(0)


def test_known_at_is_max_of_accepted_and_retained():
    evidence = parse(build_document())
    assert evidence.known_at == RETAINED_UTC
    later = RETAINED_UTC + timedelta(days=2)
    evidence_later = parse(build_document(), retained_at=later)
    assert evidence_later.known_at == later
    assert evidence_later.retained_at == later
    one_second_after = ACCEPTED_UTC + timedelta(seconds=1)
    evidence_tight = parse(build_document(), retained_at=one_second_after)
    assert evidence_tight.known_at == one_second_after


def test_evidence_is_frozen():
    evidence = parse(build_document())
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.cusip = "999999999"


def test_byte_tamper_refused():
    raw = build_document()
    tampered = raw.replace(b"Common Stock", b"Common StocK", 1)
    assert tampered != raw
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        sec_filing_identity.parse_schedule13g_evidence(
            tampered, expected_sha256=digest(raw), retained_at=RETAINED_UTC
        )


def test_expected_digest_mismatch_refused():
    raw = build_document()
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        sec_filing_identity.parse_schedule13g_evidence(
            raw, expected_sha256=digest(b"not these bytes"), retained_at=RETAINED_UTC
        )


def test_wrong_digest_format_refused():
    raw = build_document()
    with pytest.raises(ValueError, match="64-hex-digit"):
        sec_filing_identity.parse_schedule13g_evidence(
            raw, expected_sha256="deadbeef", retained_at=RETAINED_UTC
        )


def test_oversized_document_refused():
    raw = b"x" * (2 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="strict limit"):
        sec_filing_identity.parse_schedule13g_evidence(
            raw, expected_sha256=digest(raw), retained_at=RETAINED_UTC
        )


def test_missing_cusip_refused():
    with pytest.raises(ValueError, match="issuerCusip"):
        parse(build_document(omit_cusip=True))


def test_duplicate_cusip_refused():
    with pytest.raises(ValueError, match="exactly one <issuerCusipNumber>"):
        parse(build_document(duplicate_cusip=True))


def test_conflicting_header_cik_refused():
    with pytest.raises(ValueError, match="SUBJECT COMPANY CIK"):
        parse(build_document(header_cik="0008888888"))


def test_filed_by_different_legitimate_cik_never_binds():
    evidence = parse(build_document(filed_by_cik="0002222222"))
    assert evidence.issuer_cik == ISSUER_CIK
    assert evidence.accession == ACCESSION
    dumped = dataclasses.asdict(evidence).values()
    assert not any(value == "0002222222" for value in dumped)


def test_malformed_clock_refused():
    with pytest.raises(ValueError, match="ACCEPTANCE-DATETIME"):
        parse(build_document(acceptance="2026032615060"))
    with pytest.raises(ValueError, match="ACCEPTANCE-DATETIME"):
        parse(build_document(acceptance="20261326150603"))
    with pytest.raises(ValueError, match="ACCEPTANCE-DATETIME"):
        parse(build_document(acceptance="not-a-clock"))


def test_naive_retained_at_refused():
    naive = datetime(2026, 3, 26, 21, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        parse(build_document(), retained_at=naive)


def test_non_utc_retained_at_refused():
    off_utc = datetime(2026, 3, 26, 17, 0, 0, tzinfo=timezone(timedelta(hours=-4)))
    with pytest.raises(ValueError, match="UTC"):
        parse(build_document(), retained_at=off_utc)


def test_future_acceptance_refused():
    before_acceptance = ACCEPTED_UTC - timedelta(seconds=1)
    with pytest.raises(ValueError, match="later than retained_at"):
        parse(build_document(), retained_at=before_acceptance)


def test_backdated_event_refused():
    with pytest.raises(ValueError, match="backdate"):
        parse(build_document(event_date="03/27/2026"))


def test_bad_event_date_format_refused():
    with pytest.raises(ValueError, match="MM/DD/YYYY"):
        parse(build_document(event_date="2026-03-13"))


def test_unsupported_namespace_refused():
    raw = build_document()
    bad = raw.replace(
        sec_filing_identity.SCHEDULE13G_NAMESPACE.encode("utf-8"),
        b"http://example.invalid/not-sec",
        1,
    )
    with pytest.raises(ValueError, match="edgarSubmission"):
        parse(bad)


def test_dtd_declaration_refused():
    raw = build_document()
    bad = raw.replace(
        b"<edgarSubmission",
        b'<!DOCTYPE edgarSubmission [<!ENTITY synthetic "x">]><edgarSubmission',
        1,
    )
    with pytest.raises(ValueError, match="DTD or entity"):
        parse(bad)


def test_entity_declaration_refused():
    raw = build_document()
    bad = raw.replace(
        b"<edgarSubmission", b'<!ENTITY synthetic "x"><edgarSubmission', 1
    )
    with pytest.raises(ValueError, match="DTD or entity"):
        parse(bad)


def test_malformed_xml_refused():
    raw = build_document()
    truncated = raw[: raw.index(b"</edgarSubmission>")] + b"</XML></TEXT></DOCUMENT>\n"
    with pytest.raises(ValueError, match="malformed or ambiguous XML"):
        parse(truncated)


def test_duplicate_cover_page_refused():
    with pytest.raises(ValueError, match="exactly one <coverPageHeader>"):
        parse(duplicate_segment(build_document(), "<coverPageHeader>", "</coverPageHeader>"))


def test_duplicate_document_refused():
    with pytest.raises(ValueError, match="exactly one <DOCUMENT>"):
        parse(duplicate_segment(build_document(), "<DOCUMENT>", "</DOCUMENT>"))


def test_duplicate_header_refused():
    with pytest.raises(ValueError, match="exactly one <SEC-HEADER>"):
        parse(duplicate_segment(build_document(), "<SEC-HEADER>", "</SEC-HEADER>"))


def test_bad_cusip_check_digit_refused():
    with pytest.raises(ValueError, match="check digit"):
        parse(build_document(cusip="123456783"))
    with pytest.raises(ValueError, match="check digit"):
        parse(build_document(cusip="12345Y780"))


def test_lowercase_cusip_refused():
    with pytest.raises(ValueError, match="uppercase"):
        parse(build_document(cusip="12345y780"))


def test_valid_lettered_cusip_accepted():
    evidence = parse(build_document(cusip=LETTERED_CUSIP))
    assert evidence.cusip == LETTERED_CUSIP


def test_unsupported_document_type_refused():
    with pytest.raises(ValueError, match="unsupported DOCUMENT <TYPE>"):
        parse(build_document(doc_type="SCHEDULE 13D"))


def test_type_and_submission_type_mismatch_refused():
    with pytest.raises(ValueError, match="does not match CONFORMED SUBMISSION TYPE"):
        parse(build_document(doc_type="SCHEDULE 13G/A", submission_type="SCHEDULE 13G"))


def test_accession_mismatch_refused():
    raw = build_document()
    bad = raw.replace(
        ("ACCESSION NUMBER:\t\t%s" % ACCESSION).encode("utf-8"),
        b"ACCESSION NUMBER:\t\t0001111111-26-000002",
        1,
    )
    with pytest.raises(ValueError, match="does not match SEC-DOCUMENT accession"):
        parse(bad)


def test_issuer_cik_must_be_ten_digits():
    with pytest.raises(ValueError, match="zero-padded 10-digit CIK"):
        parse(build_document(issuer_cik="99999999"))


def test_subject_cik_cannot_be_borrowed_from_before_subject_section():
    raw = build_document()
    line = ('\t\tCENTRAL INDEX KEY:\t\t\t%s\n' % ISSUER_CIK).encode()
    raw = raw.replace(line,b'',1).replace(b'SUBJECT COMPANY:',line+b'SUBJECT COMPANY:',1)
    with pytest.raises(ValueError): parse(raw)


def test_nested_identity_leaf_cannot_hide_extra_identity_content():
    raw = build_document().replace(
        ('<issuerCusipNumber>%s</issuerCusipNumber>' % CUSIP).encode(),
        ('<issuerCusipNumber>%s<com:street1>conflict</com:street1></issuerCusipNumber>' % CUSIP).encode(),1)
    with pytest.raises(ValueError): parse(raw)


def test_unqualified_shadow_identity_is_not_silently_ignored():
    raw = build_document().replace(b'</issuerCusips>',b'<issuerCusipNumber xmlns="">999999999</issuerCusipNumber></issuerCusips>',1)
    with pytest.raises(ValueError): parse(raw)


@pytest.mark.parametrize('acceptance,event_date',[
    ('20261101013000','10/31/2026'),
    ('20260308023000','03/07/2026'),
])
def test_ambiguous_or_nonexistent_acceptance_clock_refuses(acceptance,event_date):
    with pytest.raises(ValueError):
        parse(build_document(acceptance=acceptance,event_date=event_date),
              retained_at=datetime(2026,12,1,tzinfo=UTC))


def test_missing_iana_timezone_data_never_guesses_clock(monkeypatch):
    monkeypatch.setattr(sec_filing_identity,'AMERICA_NEW_YORK',None)
    with pytest.raises(ValueError,match="IANA"):
        parse(build_document(),retained_at=datetime(2026,3,27,tzinfo=UTC))
