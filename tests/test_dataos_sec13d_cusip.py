"""Actual SEC wire facts plus controlled registration/master boundary cases."""
from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import io

import pandas as pd
import pytest

from lib.dataos.identity import VendorAliasTable
from lib.dataos.sec_cusip_binding import build_sec13d_cusip_alias

CLOCK = datetime(2026, 10, 19, 20, tzinfo=timezone.utc)
SOURCE = Path(__file__).parent / 'fixtures/sec_schedule13d/0001104659-26-053223.txt'


def inputs():
    # The SEC submission is genuinely retained. This small registration/master
    # is a controlled fixture; separate native qualification uses full objects.
    filing = SOURCE.read_bytes()
    registration = b'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2025">
<context id="c1"><entity><identifier scheme="http://www.sec.gov/CIK">0001811210</identifier></entity><period><startDate>2025-01-01</startDate><endDate>2025-12-31</endDate></period></context>
<dei:EntityCentralIndexKey contextRef="c1">0001811210</dei:EntityCentralIndexKey>
<dei:EntityRegistrantName contextRef="c1">Lucid Group, Inc.</dei:EntityRegistrantName>
<dei:Security12bTitle contextRef="c1">Class A Common Stock, $0.0001 par value per share</dei:Security12bTitle>
<dei:TradingSymbol contextRef="c1">LCID</dei:TradingSymbol>
<dei:SecurityExchangeName contextRef="c1">NASDAQ</dei:SecurityExchangeName></xbrl>'''
    record = dict(security_id='SEC:US-XNAS-LCID', issuer_id='ISS:US-XNAS-LCID',
                  issuer_state='RESOLVED', issuer_cik='0001811210', listing_key='US-XNAS-LCID',
                  country='US', mic='XNAS', inception_code='LCID', security_state=None, superseded_by=None)
    out = io.BytesIO(); pd.DataFrame([record]).to_parquet(out, index=False)
    args = {}
    for key, raw in [('filing', filing), ('registration', registration), ('master', out.getvalue())]:
        args[key + '_raw'] = raw
        args[key + '_sha256'] = hashlib.sha256(raw).hexdigest()
        args[key + '_retained_at'] = CLOCK
    return args


def test_explicit_class_a_binds_existing_nasdaq_security_on_assertion_day_only():
    alias = build_sec13d_cusip_alias(**inputs())
    assert (alias.vendor_symbol, alias.security_id, alias.valid_from, alias.valid_to) == (
        '549498202', 'SEC:US-XNAS-LCID', date(2026, 4, 30), date(2026, 5, 1))
    table = VendorAliasTable([alias])
    assert table.resolve(alias.vendor, alias.vendor_symbol, alias.valid_from, decision_at=CLOCK) == alias.security_id
    assert table.resolve(alias.vendor, alias.vendor_symbol, alias.valid_from, decision_at='2026-08-27T09:22:23Z') is None
    for day in [date(2026, 4, 28), date(2026, 6, 30)]:
        assert table.resolve(alias.vendor, alias.vendor_symbol, day, decision_at=CLOCK) is None


@pytest.mark.parametrize('before,after', [
    (b'Class A Common Stock', b'Class B Common Stock'),
    (b'Class A Common Stock', b'Common Stock'),
    (b'$0.0001 par value per share', b'$0.01 par value per share'),
    (b', $0.0001 par value per share', b''),
    (b'>LCID<', b'>OTHER<'),
    (b'>NASDAQ<', b'>NYSE<'),
    (b'>0001811210<', b'>0001874832<'),
    (b'2025-12-31', b'2026-05-01'),
])
def test_similar_or_later_registration_cannot_bind(before, after):
    args = inputs(); raw = args['registration_raw'].replace(before, after)
    args.update(registration_raw=raw, registration_sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        build_sec13d_cusip_alias(**args)


@pytest.mark.parametrize('source', ['filing', 'registration', 'master'])
def test_source_byte_tampering_refuses(source):
    args = inputs(); args[source + '_raw'] += b' '
    with pytest.raises(ValueError, match='digest'):
        build_sec13d_cusip_alias(**args)


def test_issuer_cik_does_not_allocate_or_replace_a_missing_master_security():
    args = inputs(); frame = pd.read_parquet(io.BytesIO(args['master_raw']))
    frame['security_state'] = 'INACTIVE'
    out = io.BytesIO(); frame.to_parquet(out, index=False)
    args.update(master_raw=out.getvalue(), master_sha256=hashlib.sha256(out.getvalue()).hexdigest())
    with pytest.raises(ValueError, match='inactive'):
        build_sec13d_cusip_alias(**args)


def test_a_later_source_read_delays_knowledge():
    args = inputs(); args['master_retained_at'] = datetime(2026, 10, 20, tzinfo=timezone.utc)
    alias = build_sec13d_cusip_alias(**args)
    assert VendorAliasTable([alias]).resolve(alias.vendor, alias.vendor_symbol, alias.valid_from, decision_at=CLOCK) is None
