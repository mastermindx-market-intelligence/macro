"""One retained SEC filing binding; no canonical publication or live I/O."""
from datetime import date, datetime, timezone
import pytest
from lib.dataos.identity import AliasRow, VendorAliasTable, IdentityError, alias_binding_sha256

VENDOR = "sec_filing_cusip"
DAY = date(2026, 3, 13)
CLOCK = datetime(2026, 10, 19, 10, 4, tzinfo=timezone.utc)

def test_sec_cusip_cannot_enter_as_timeless_unsealed_alias():
    with pytest.raises(IdentityError):
        AliasRow(VENDOR, "00287Y109", "SEC:US-XNYS-ABBV")

def test_sec_cusip_binding_requires_cutoff_and_excludes_unavailable_source():
    digest = "a" * 64
    end = date(2026, 3, 14)
    seal = alias_binding_sha256(VENDOR, "00287Y109", "SEC:US-XNYS-ABBV", DAY, end, CLOCK, digest)
    row = AliasRow(VENDOR, "00287Y109", "SEC:US-XNYS-ABBV", DAY, end, CLOCK, digest, seal)
    table = VendorAliasTable([row])
    with pytest.raises(IdentityError):
        table.resolve(VENDOR, "00287Y109", DAY)
    assert table.resolve(VENDOR, "00287Y109", DAY, decision_at="2026-10-19T10:03:59Z") is None
    assert table.resolve(VENDOR, "00287Y109", DAY, decision_at=CLOCK) == "SEC:US-XNYS-ABBV"
    assert table.resolve(VENDOR, "00287Y109", date(2026, 3, 14), decision_at=CLOCK) is None
    assert VendorAliasTable.legacy_only_records([{"vendor": VENDOR}]) == []

import hashlib
import io
import pandas as pd
from lib.dataos.sec_cusip_binding import build_sec_cusip_alias


def _inputs():
    # Synthetic wire-shaped documents, never a claimed acquired filing.
    filing = b'''<SEC-DOCUMENT>0000102909-26-000503.txt : 20260326
<SEC-HEADER>0000102909-26-000503.hdr.sgml : 20260326
<ACCEPTANCE-DATETIME>20260326150603
ACCESSION NUMBER: 0000102909-26-000503
CONFORMED SUBMISSION TYPE: SCHEDULE 13G/A
SUBJECT COMPANY:
 COMPANY DATA:
  COMPANY CONFORMED NAME: AbbVie Inc.
  CENTRAL INDEX KEY: 0001551152
FILED BY:
 COMPANY DATA:
  CENTRAL INDEX KEY: 0000102909
</SEC-HEADER>
<DOCUMENT>
<TYPE>SCHEDULE 13G/A
<SEQUENCE>1
<FILENAME>primary_doc.xml
<TEXT><XML><?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13g">
<headerData><submissionType>SCHEDULE 13G/A</submissionType></headerData>
<formData><coverPageHeader><securitiesClassTitle>Common Stock</securitiesClassTitle>
<eventDateRequiresFilingThisStatement>03/13/2026</eventDateRequiresFilingThisStatement>
<issuerInfo><issuerCik>0001551152</issuerCik><issuerName>AbbVie Inc</issuerName>
<issuerCusips><issuerCusipNumber>00287Y109</issuerCusipNumber></issuerCusips>
</issuerInfo></coverPageHeader></formData></edgarSubmission></XML></TEXT>
</DOCUMENT></SEC-DOCUMENT>'''
    registration = b'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2025">
<context id="c1"><entity><identifier scheme="http://www.sec.gov/CIK">0001551152</identifier></entity><period><startDate>2025-01-01</startDate><endDate>2025-12-31</endDate></period></context>
<dei:EntityCentralIndexKey contextRef="c1">0001551152</dei:EntityCentralIndexKey>
<dei:EntityRegistrantName contextRef="c1">AbbVie Inc.</dei:EntityRegistrantName>
<dei:Security12bTitle contextRef="c1">Common Stock, par value $0.01 per share</dei:Security12bTitle>
<dei:TradingSymbol contextRef="c1">ABBV</dei:TradingSymbol>
<dei:SecurityExchangeName contextRef="c1">NYSE</dei:SecurityExchangeName></xbrl>'''
    record = dict(security_id="SEC:US-XNYS-ABBV", issuer_id="ISS:US-XNYS-ABBV",
                  issuer_state="RESOLVED", issuer_cik="0001551152", listing_key="US-XNYS-ABBV",
                  country="US", mic="XNYS", inception_code="ABBV", security_state=None, superseded_by=None)
    buf = io.BytesIO(); pd.DataFrame([record]).to_parquet(buf, index=False)
    master = buf.getvalue()
    return dict(filing_raw=filing, filing_sha256=hashlib.sha256(filing).hexdigest(), filing_retained_at=CLOCK,
                registration_raw=registration, registration_sha256=hashlib.sha256(registration).hexdigest(), registration_retained_at=CLOCK,
                master_raw=master, master_sha256=hashlib.sha256(master).hexdigest(), master_retained_at=CLOCK)


def test_filing_class_registration_and_existing_master_bind_one_day():
    args = _inputs(); row = build_sec_cusip_alias(**args)
    assert (row.vendor_symbol, row.security_id, row.valid_from, row.valid_to, row.known_at) == (
        "00287Y109", "SEC:US-XNYS-ABBV", date(2026,3,26), date(2026,3,27), CLOCK)
    table = VendorAliasTable.from_records([dict(vendor=row.vendor, vendor_symbol=row.vendor_symbol,
        security_id=row.security_id, valid_from=row.valid_from.isoformat(), valid_to=row.valid_to.isoformat(),
        known_at=row.known_at.isoformat(), evidence_sha256=row.evidence_sha256, binding_sha256=row.binding_sha256)])
    assert table.resolve(VENDOR, "00287Y109", row.valid_from, decision_at=CLOCK) == row.security_id
    assert table.resolve(VENDOR, "00287Y109", row.valid_from, decision_at="2026-08-27T00:00:00Z") is None
    assert table.resolve(VENDOR, "00287Y109", date(2026, 3, 31), decision_at=CLOCK) is None


@pytest.mark.parametrize('source', ['filing', 'registration', 'master'])
def test_every_retained_source_digest_is_checked(source):
    args = _inputs(); args[source + '_raw'] += b' '
    with pytest.raises(ValueError, match='digest'):
        build_sec_cusip_alias(**args)


@pytest.mark.parametrize('old,new', [
    (b'Common Stock, par value $0.01 per share', b'Class A Common Stock'),
    (b'>ABBV<', b'>ABBV27<'),
    (b'>NYSE<', b'>NASDAQ<'),
    (b'>0001551152<', b'>0000000001<'),
])
def test_registration_cannot_guess_security_from_issuer_or_similar_class(old,new):
    args = _inputs(); args['registration_raw'] = args['registration_raw'].replace(old,new)
    args['registration_sha256'] = hashlib.sha256(args['registration_raw']).hexdigest()
    with pytest.raises(ValueError): build_sec_cusip_alias(**args)


def test_duplicate_registration_class_and_duplicate_master_are_ambiguous():
    args = _inputs(); title = b'<dei:Security12bTitle contextRef="c1">Common Stock</dei:Security12bTitle>'
    args['registration_raw'] = args['registration_raw'].replace(b'</xbrl>', title+b'</xbrl>')
    args['registration_sha256'] = hashlib.sha256(args['registration_raw']).hexdigest()
    with pytest.raises(ValueError, match='ambiguous'): build_sec_cusip_alias(**args)
    args = _inputs(); frame = pd.read_parquet(io.BytesIO(args['master_raw']))
    out = io.BytesIO(); pd.concat([frame,frame]).to_parquet(out, index=False)
    args['master_raw'] = out.getvalue(); args['master_sha256'] = hashlib.sha256(out.getvalue()).hexdigest()
    with pytest.raises(ValueError, match='ambiguous'): build_sec_cusip_alias(**args)


def test_later_canonical_read_clock_cannot_be_ignored():
    args = _inputs(); args['master_retained_at'] = datetime(2026,10,20,tzinfo=timezone.utc)
    row = build_sec_cusip_alias(**args)
    assert VendorAliasTable([row]).resolve(VENDOR,'00287Y109',DAY,decision_at=CLOCK) is None


def test_tampered_seal_and_overlap_cannot_resolve():
    args = _inputs(); row = build_sec_cusip_alias(**args)
    with pytest.raises(IdentityError):
        AliasRow(VENDOR, row.vendor_symbol, 'SEC:US-XNYS-OTHER', row.valid_from,row.valid_to,
                 row.known_at,row.evidence_sha256,row.binding_sha256)
    with pytest.raises(IdentityError,match='ambiguous'):
        VendorAliasTable([row,row])


def test_sealed_cusip_reuse_cannot_overlap_and_invalid_dates_refuse():
    digest = "a" * 64
    end = date(2026,3,14)
    rows = [AliasRow(VENDOR, "00287Y109", sec, DAY, end, CLOCK, digest,
        alias_binding_sha256(VENDOR, "00287Y109", sec, DAY, end, CLOCK, digest))
        for sec in ["SEC:US-XNYS-ABBV", "SEC:US-XNYS-OTHER"]]
    with pytest.raises(IdentityError,match="ambiguous"):
        VendorAliasTable(rows)
    with pytest.raises(IdentityError,match="event date"):
        rows[0].covers(CLOCK,decision_at=CLOCK)
    with pytest.raises(IdentityError):
        AliasRow(VENDOR,"00287Y109","SEC:US-XNYS-ABBV",DAY,None,CLOCK,digest,"0"*64)


def test_native_master_null_state_is_not_an_inactive_security():
    args = _inputs(); frame = pd.read_parquet(io.BytesIO(args['master_raw']))
    # Canonical mixed master columns decode nulls as float NaN on the native reader.
    frame['security_state'] = float('nan'); frame['superseded_by'] = float('nan')
    out = io.BytesIO(); frame.to_parquet(out,index=False)
    args['master_raw'] = out.getvalue(); args['master_sha256'] = hashlib.sha256(out.getvalue()).hexdigest()
    assert build_sec_cusip_alias(**args).security_id == 'SEC:US-XNYS-ABBV'
