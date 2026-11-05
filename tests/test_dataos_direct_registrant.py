"""Direct registrant intake: synthetic captured bytes and isolated canonical builds."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lib import symbol_directory_receipts as receipts
from scripts import build_security_master as b

EVIDENCE = None
DAY = date(2026, 10, 15)
NOW = '2026-10-15T10:00:00+00:00'


def observation():
    return ((EVIDENCE / 'spy-sec-submissions.json').read_bytes(),
            json.loads((EVIDENCE / 'spy-registrant-captures.json').read_bytes())[0])


def prepared(raw=None, capture=None, **changes):
    original_raw, original_capture = observation()
    args = dict(symbol='SPY', response_body=original_raw if raw is None else raw,
                capture=original_capture if capture is None else capture,
                listing_body=(EVIDENCE / 'listing-2026-10-15.parquet').read_bytes(),
                listing_receipt_body=(EVIDENCE / 'listing-2026-10-15-receipt.json').read_bytes(),
                decision_at=NOW)
    args.update(changes)
    return b.prepare_direct_registrant(**args)


def test_captured_shape_prepares_precise_listing_and_explicit_clocks():
    assert hasattr(b, 'prepare_direct_registrant'), 'canonical writer lacks direct submissions intake'
    result = prepared()
    assert result['resolution'].listing_key.render() == 'US-ARCX-SPY'
    assert result['resolution'].effective_at == DAY
    assert result['registrant']['cik'] == '0000884394'
    assert result['registrant']['title'] == 'Synthetic SPY Registrant'
    assert result['registrant']['known_at'] == '2026-10-15T09:59:20.281686+00:00'
    assert result['registrant']['scope'] == 'pending_transition_independence_only'
    assert result['registrant']['listing_snapshot_sha256'] == hashlib.sha256((EVIDENCE / 'listing-2026-10-15.parquet').read_bytes()).hexdigest()
    assert result['registrant']['response_sha256'] == observation()[1]['sha256']


def intake_input():
    raw, capture = observation()
    return dict(symbol='SPY', response_body=raw, capture=capture,
                listing_body=(EVIDENCE / 'listing-2026-10-15.parquet').read_bytes(),
                listing_receipt_body=(EVIDENCE / 'listing-2026-10-15-receipt.json').read_bytes())


def cohort():
    return [dict(security_id=f'SEC:US-XNAS-LOST{i}',issuer_id=f'ISS:US-XNAS-LOST{i}',
        issuer_state='RESOLVED',issuer_cik=f'{1000+i:010d}',issuer_evidence_snapshot='2026-10-07',
        listing_key=f'US-XNAS-LOST{i}',country='US',mic='XNAS',inception_code=f'LOST{i}',
        effective_at='2026-10-07T00:00:00',ingested_at='2026-10-07T10:00:00',
        security_state=None,superseded_by=None) for i in range(11)]


def run_mint(rows=None, inputs=None, **kw):
    return b.mint_master_rows([prepared()['resolution']], cohort() if rows is None else rows,
        NOW, direct_registrant_inputs=[intake_input()] if inputs is None else inputs, **kw)


def test_new_evidence_composes_with_existing_fence_without_changing_old_rows_or_issuer_axis():
    old = cohort()
    assert len(old) == 11
    baseline = b.mint_master_rows([prepared()['resolution']], old, NOW)
    assert not baseline[1] and len(baseline[4]) == 1
    result = run_mint(old)
    assert result[1] == {'SPY': 'SEC:US-ARCX-SPY'}
    assert not result[3] and not result[4]
    rows = {r['security_id']: r for r in result[0]}
    assert len(rows) == 12
    for row in old:
        assert {k: rows[row['security_id']][k] for k in row} == row
    spy = rows['SEC:US-ARCX-SPY']
    assert spy['issuer_id'] is None and spy['issuer_cik'] is None
    assert spy['issuer_evidence_snapshot'] is None
    assert spy['effective_at'] == '2026-10-15T00:00:00'


@pytest.mark.parametrize('cik', [None, '0000884394'])
def test_fence_still_refuses_null_or_same_registrant(cik):
    old = cohort()
    old[0]['issuer_cik'] = cik
    result = run_mint(old)
    assert not result[1] and len(result[4]) == 1
    assert len(result[0]) == 11


def test_stored_tombstone_still_refuses_resurrection():
    row = dict(cohort()[0], security_id='SEC:US-ARCX-SPY', listing_key='US-ARCX-SPY',
               inception_code='SPY', country='US', mic='ARCX', security_state='SUPERSEDED',
               superseded_by='SEC:US-XNAS-OTHER')
    result = run_mint([row])
    assert not result[1] and len(result[3]) == 1


@pytest.mark.parametrize('kw', [dict(ambiguous_tickers=frozenset({'SPY'})),
                                dict(cik_map={'SPY': ('0000000001', 'conflicting registrant')})])
def test_conflicting_ordinary_registrant_evidence_refuses(kw):
    with pytest.raises(b.IdentityError):
        run_mint(**kw)


def test_new_input_cannot_add_an_unresolved_seed_or_bypass_gmi_equity_gate():
    with pytest.raises(b.IdentityError):
        b.mint_master_rows([], cohort(), NOW, direct_registrant_inputs=[intake_input()])
    result = run_mint(gmi_admission_targets=frozenset({'SPY'}),
        directory_flags={'SPY': dict(etf=True, test_issue=False, is_preferred=False)})
    assert not result[1] and result[7]


@pytest.mark.parametrize('field,value', [('sha256','0'*64), ('bytes',True), ('status',403),
    ('final_url','https://example.com/submissions/CIK0000884394.json'),
    ('url','https://data.sec.gov/submissions/CIK0000000001.json'),
    ('request_started_at','2026-10-14T09:59:20Z'),
    ('request_started_at','2026-10-15T10:00:01Z'),
    ('read_completed_at','2026-10-15T09:59:20'),
    ('read_completed_at','2026-10-15T10:00:01Z')])
def test_bad_capture_refuses(field,value):
    raw, capture = observation()
    capture[field] = value
    with pytest.raises(b.IdentityError):
        prepared(raw, capture)


@pytest.mark.parametrize('changes', [dict(cik='884394'), dict(cik=True), dict(cik='0000000000'),
    dict(tickers=['QQQ']), dict(tickers=['SPY','SPY']), dict(tickers=[None]),
    dict(name=''), dict(name='a'*513)])
def test_payload_identity_conflicts_refuse_even_when_hash_matches(changes):
    raw, capture = observation()
    value=json.loads(raw); value.update(changes)
    raw=json.dumps(value).encode()
    capture.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    with pytest.raises(b.IdentityError):
        prepared(raw,capture)


@pytest.mark.parametrize('raw', [b'{"cik":"0000884394","cik":"0000884394"}',
    b'{"value":NaN}', b'{"value":1e999}', b'[]', b'\xff', b' '* (2*1024*1024+1)], ids=['duplicate','nan','overflow','array','utf8','oversize'])
def test_invalid_or_oversize_json_refuses(raw):
    _, capture = observation()
    capture.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    with pytest.raises(b.IdentityError):
        prepared(raw,capture)


@pytest.mark.parametrize('changes', [dict(symbol='SPX'), dict(symbol='MU'),
    dict(decision_at='2026-10-07T10:00:00Z'), dict(decision_at='2026-10-15T09:59:20.281685Z'),
    dict(listing_body=b'not parquet'), dict(listing_receipt_body=b'{}')])
def test_scope_clock_and_listing_fail_closed(changes):
    with pytest.raises(b.IdentityError):
        prepared(**changes)


def test_exact_listing_bytes_and_canonical_receipt_not_hand_written_metadata():
    value = json.loads((EVIDENCE / 'listing-2026-10-15-receipt.json').read_bytes())
    value['authority']['listing_identity_observation_eligible'] = False
    with pytest.raises(b.IdentityError):
        prepared(listing_receipt_body=json.dumps(value).encode())
    body = bytearray((EVIDENCE / 'listing-2026-10-15.parquet').read_bytes())
    body[100] ^= 1
    with pytest.raises(b.IdentityError):
        prepared(listing_body=bytes(body))


@pytest.fixture
def build_scratch(tmp_path, monkeypatch):
    repo = Path.cwd()
    spec = importlib.util.spec_from_file_location('retained_reference_fixture', repo / 'tests/test_dataos_prospective_reference.py')
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    fixture.b = b
    path, _, rows = fixture.evidence.__wrapped__(tmp_path, monkeypatch)
    fixture.setup_builder(monkeypatch, tmp_path, rows)
    monkeypatch.setattr(b, '_git_sha', lambda: 'copied-source-test-only')
    monkeypatch.setattr(b, '_iso_now', lambda: '2026-10-07T10:00:01')
    out = tmp_path / 'out'
    b.build(out)
    masters = b._read_existing(out / b.MASTER_NAME, b.MASTER_COLUMNS, b.MASTER_DTYPES)
    lost = dict(masters[0], security_id='SEC:US-XNAS-LOST', listing_key='US-XNAS-LOST',
                inception_code='LOST')
    b._write_parquet(masters+[lost], b.MASTER_COLUMNS, out / b.MASTER_NAME, b.MASTER_DTYPES)
    monkeypatch.setattr(b, 'load_cik_map', lambda: ({'LOST': ('0000000001', 'synthetic lost registrant')},
        '2026-10-07', tmp_path / 'cik.parquet', frozenset()))
    b.build(out)  # settle the synthetic issuer fixture before bounded intake
    original = b.build(out, reference_evidence_path=path)['prospective_reference']
    assert original['probes']['SPY']['status'] == 'REFUSED'
    monkeypatch.setattr(b, '_iso_now', lambda: '2026-10-15T10:00:00')
    monkeypatch.setattr(b.time, 'time_ns', lambda: b._reference_clock_ns(NOW))
    current = b.SYMBOL_DIR_SNAPSHOTS / '2026-10-15.parquet'
    current.write_bytes((EVIDENCE/'listing-2026-10-15.parquet').read_bytes())
    mapping, flags, _, _ = b.load_directory()
    monkeypatch.setattr(b, 'load_directory', lambda: (mapping, flags, '2026-10-15', current))
    return out, copy.deepcopy(original)


def test_full_copied_build_preserves_old_disposition_and_carries_new_binding_without_replay(build_scratch):
    out, original = build_scratch
    result = b.build(out, direct_registrant_inputs=[intake_input()])
    assert result['prospective_reference'] == original
    new = result['direct_registrant_intake']['observations']['SPY']
    assert new['status'] == 'BOUND' and new['security_id'] == 'SEC:US-ARCX-SPY'
    master = b._read_existing(out / b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
    spy = next(r for r in master if r['security_id'] == new['security_id'])
    assert spy['issuer_id'] is None and spy['issuer_cik'] is None
    aliases = pd.read_parquet(out / b.ALIASES_NAME)
    assert not aliases.security_id.eq(new['security_id']).any()
    again = b.build(out)
    assert again['direct_registrant_intake'] == result['direct_registrant_intake']
    assert again['prospective_reference'] == original
    assert 'SPY' not in again['listing_continuity']
    assert any(r['symbol']=='SPY' and r['code']=='structural_etf'
               for r in again['us_gmi_admission']['refusals_this_run'])
    before = {p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError,match='already retained'):
        b.build(out,direct_registrant_inputs=[intake_input()])
    assert {p.name:p.read_bytes() for p in out.iterdir()} == before


def test_full_build_cannot_hide_conflicting_cik_by_etf_issuer_filter(build_scratch, monkeypatch):
    out, _ = build_scratch
    old = b.load_cik_map
    def conflict():
        mapping, *rest = old()
        return {**mapping, 'SPY': ('0000000001', 'conflicting input')}, *rest
    monkeypatch.setattr(b, 'load_cik_map', conflict)
    before = {p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError, match='conflict'):
        b.build(out, direct_registrant_inputs=[intake_input()])
    assert {p.name:p.read_bytes() for p in out.iterdir()} == before


def test_full_build_refusal_is_retained_without_automatic_retry(build_scratch, monkeypatch):
    out, original = build_scratch
    # A synthetic unknown registrant among the lost rows keeps the real fence closed.
    rows = b._read_existing(out / b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
    lost = next(r for r in rows if r['inception_code']=='LOST')
    lost['issuer_cik'] = None
    lost['issuer_id'] = None
    lost['issuer_state'] = 'NO_ISSUER_EVIDENCE'
    lost['issuer_evidence_snapshot'] = None
    b._write_parquet(rows,b.MASTER_COLUMNS,out / b.MASTER_NAME,b.MASTER_DTYPES)
    monkeypatch.setattr(b,'load_cik_map',lambda: ({},'2026-10-07',out / 'absent',frozenset()))
    b.build(out)  # settle all synthetic issuer artifacts after the fixture edit
    result=b.build(out,direct_registrant_inputs=[intake_input()])
    assert result['direct_registrant_intake']['observations']['SPY']['status']=='REFUSED'
    assert result['prospective_reference']==original
    again=b.build(out)
    assert again['direct_registrant_intake']==result['direct_registrant_intake']


@pytest.mark.parametrize('mutation',['missing','duplicate','listing','tombstone'])
def test_retained_binding_never_remints_or_retargets(build_scratch,mutation):
    out,_=build_scratch
    first=b.build(out,direct_registrant_inputs=[intake_input()])
    rows=b._read_existing(out / b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
    spy=next(r for r in rows if r['inception_code']=='SPY')
    if mutation=='missing': rows.remove(spy)
    elif mutation=='duplicate': rows.append(dict(spy))
    elif mutation=='listing': spy['listing_key']='US-XNYS-SPY'
    else: spy['security_state']='SUPERSEDED'; spy['superseded_by']='SEC:US-XNAS-OTHER'
    directory,flags,day,_=b.load_directory()
    current=dict(directory=directory,directory_flags=flags,delisted=b.load_delisted(),snapshot_date=day)
    if mutation=='tombstone':
        assert b._retained_direct_resolutions(first['direct_registrant_intake'],rows,**current)==[]
    else:
        with pytest.raises(b.IdentityError):
            b._retained_direct_resolutions(first['direct_registrant_intake'],rows,**current)


def manifest(tmp_path):
    source=intake_input()
    for key in ('response_body','listing_body','listing_receipt_body'):
        (tmp_path/key).write_bytes(source[key]); source[key]=key
    path=tmp_path/'input.json'
    path.write_text(json.dumps({'schema':'mastermind.direct_registrant_input.v1','sources':[source]}))
    return path


def test_explicit_cli_uses_bounded_input_and_preserves_dry_run(tmp_path,monkeypatch):
    path=manifest(tmp_path); calls=[]
    monkeypatch.setattr(b,'build',lambda *a,**kw: calls.append(kw) or {'notes':[]})
    monkeypatch.setattr(b,'_report',lambda *a,**kw: None)
    assert b.main(['--direct-registrant-evidence',str(path),'--dry-run'])==0
    assert calls[0]['dry_run'] is True
    assert calls[0]['direct_registrant_inputs']==[intake_input()]


@pytest.mark.parametrize('bad',['../response_body','/etc/passwd','missing','symlink'])
def test_explicit_input_has_no_arbitrary_path_or_symlink_reader(tmp_path,bad):
    path=manifest(tmp_path)
    value=json.loads(path.read_bytes())
    if bad=='symlink': (tmp_path/'symlink').symlink_to(tmp_path/'response_body')
    value['sources'][0]['response_body']=bad;path.write_text(json.dumps(value))
    with pytest.raises(b.IdentityError): b.read_direct_registrant_inputs(path)


def test_nightly_cannot_activate_explicit_intake(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(b,'run_nightly_refresh',lambda *a: calls.append(a))
    with pytest.raises(SystemExit) as exc:
        b.main(['--nightly','--direct-registrant-evidence',str(tmp_path/'does-not-exist')])
    assert exc.value.code==2 and calls==[]


@pytest.mark.parametrize('change',['seal','future','status'])
def test_retained_receipt_corruption_refuses_before_writes(build_scratch,change):
    out,_=build_scratch
    b.build(out,direct_registrant_inputs=[intake_input()])
    path=out / b.RECEIPT_NAME; value=json.loads(path.read_bytes())
    state=value['direct_registrant_intake']
    if change=='seal': state['sha256']='0'*64
    else:
        row=state['observations']['SPY']
        if change=='future': row['known_at']='2026-10-16T10:00:00Z'
        else: row['status']='PENDING'
        state['sha256']=b._reference_digest({k:state[k] for k in ('schema','observations')})
    path.write_text(json.dumps(value))
    before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError): b.build(out)
    assert {p.name:p.read_bytes() for p in out.iterdir()}==before


def test_direct_dry_run_has_no_publication(build_scratch):
    out,_=build_scratch
    before={p.name:p.read_bytes() for p in out.iterdir()}
    result=b.build(out,dry_run=True,direct_registrant_inputs=[intake_input()])
    assert result['direct_registrant_intake']['observations']['SPY']['status']=='BOUND'
    assert {p.name:p.read_bytes() for p in out.iterdir()}==before


@pytest.mark.parametrize('mode',['unsettled_reference','not_newer'])
def test_direct_intake_cannot_backdate_an_old_reference(build_scratch,monkeypatch,mode):
    out, original=build_scratch
    state=copy.deepcopy(original)
    if mode=='unsettled_reference': state['probes']['SPY']['status']='EVIDENCE_READY'
    else: state['probes']['SPY']['known_at']=NOW
    monkeypatch.setattr(b,'_load_reference_input',lambda *a: state)
    before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError,match='newer|unsettled'):
        b.build(out,direct_registrant_inputs=[intake_input()])
    assert {p.name:p.read_bytes() for p in out.iterdir()}==before


@pytest.fixture(scope='session',autouse=True)
def synthetic_captures(tmp_path_factory):
    """Full receipt profile with synthetic rows; never live-market evidence."""
    global EVIDENCE
    EVIDENCE=tmp_path_factory.mktemp('direct-registrant-synthetic')
    n,o=5000,6500
    frame=pd.DataFrame(dict(
        date=['2026-10-15']*(n+o),
        symbol=[f'N{i:07d}' for i in range(n)]+[f'O{i:07d}' for i in range(o-1)]+['SPY'],
        security_name=['Synthetic listing']*(n+o),
        exchange=['NASDAQ']*n+['N']*(o-1)+['P'],
        etf=[False]*(n+o-1)+[True],test_issue=[False]*(n+o),is_preferred=[False]*(n+o),
        source=['nasdaqlisted']*n+['otherlisted']*o))
    artifact=EVIDENCE/'snapshots'/'2026-10-15.parquet'
    artifact.parent.mkdir()
    frame.to_parquet(artifact,index=False)
    sources=[]
    for sid,url in [(receipts.NASDAQ_LISTED_SOURCE_ID,'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'),
                    (receipts.OTHER_LISTED_SOURCE_ID,'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt')]:
        sources.append((sid,receipts.SourceFetch(value='synthetic',content=b'synthetic source',requested_url=url,
            started_at='2026-10-15T01:00:00.000000Z',completed_at='2026-10-15T01:00:01.000000Z')))
    receipt=receipts.build_symbol_directory_completion_receipt(kind='listing_snapshot',
        observation_date='2026-10-15',artifact_path=artifact,source_fetches=sources,
        collector_started_at='2026-10-15T00:59:59.000000Z',collector_completed_at='2026-10-15T01:00:02.000000Z',
        pre_dedupe_rows=n+o,duplicate_occurrences=0,duplicate_key_count=0,
        source_row_counts=((receipts.NASDAQ_LISTED_SOURCE_ID,n),(receipts.OTHER_LISTED_SOURCE_ID,o)),
        pre_dedupe_spy_occurrences=({'source_id':receipts.OTHER_LISTED_SOURCE_ID,'symbol':'SPY',
            'security_name':'Synthetic listing','exchange':'P','etf':True,'test_issue':False,'is_preferred':False},),
        non_authoritative_footers=tuple(receipts.footer_diagnostic(source_id=sid,
            text='File Creation Time: 10/15/2026 01:00:00') for sid,_ in sources))
    (EVIDENCE/'listing-2026-10-15.parquet').write_bytes(artifact.read_bytes())
    (EVIDENCE/'listing-2026-10-15-receipt.json').write_bytes(
        json.dumps(receipt,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n')
    raw=json.dumps({'cik':'0000884394','name':'Synthetic SPY Registrant','tickers':['SPY'],'exchanges':['NYSE']}).encode()
    (EVIDENCE/'spy-sec-submissions.json').write_bytes(raw)
    capture=dict(url='https://data.sec.gov/submissions/CIK0000884394.json',
        final_url='https://data.sec.gov/submissions/CIK0000884394.json',status=200,
        bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
        request_started_at='2026-10-15T09:59:20.050194Z',read_completed_at='2026-10-15T09:59:20.281686Z')
    (EVIDENCE/'spy-registrant-captures.json').write_text(json.dumps([capture]))


@pytest.mark.parametrize('change',['missing','unsupported','not_etf','delisted','stale_date','different_bytes'])
def test_new_intake_requires_the_actual_current_listing(build_scratch,monkeypatch,change,tmp_path):
    out,_=build_scratch
    mapping,flags,day,path=b.load_directory();mapping=dict(mapping);flags=copy.deepcopy(flags)
    if change=='missing': mapping.pop('SPY')
    elif change=='unsupported': mapping['SPY']='UNKNOWN'
    elif change=='not_etf': flags['SPY']['etf']=False
    elif change=='delisted': monkeypatch.setattr(b,'load_delisted',lambda: {'SPY':{'exchange':'NYSE','last_session':'2026-10-14'}})
    elif change=='stale_date': day='2026-10-16'
    else: path=tmp_path/'different.parquet';path.write_bytes(b'different source bytes')
    monkeypatch.setattr(b,'load_directory',lambda: (mapping,flags,day,path))
    before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError): b.build(out,direct_registrant_inputs=[intake_input()])
    assert before=={p.name:p.read_bytes() for p in out.iterdir()}


def test_retained_loss_still_fences_other_new_candidates(build_scratch,monkeypatch):
    out,_=build_scratch
    initial=b.build(out,direct_registrant_inputs=[intake_input()])
    mapping,flags,day,path=b.load_directory();mapping=dict(mapping);mapping.pop('SPY');mapping['NEWX']='N'
    monkeypatch.setattr(b,'load_directory',lambda: (mapping,flags,day,path))
    old_universe=b.load_universe
    monkeypatch.setattr(b,'load_universe',lambda: {**old_universe(),'NEWX':{'sources':['fixture'],'first_seen':DAY}})
    monkeypatch.setattr(b,'load_delisted',lambda: {'LOST':{'exchange':'NASDAQ','last_session':'2026-10-14'}})
    result=b.build(out)
    assert 'SPY' in result['listing_continuity']
    assert any(r['symbol']=='NEWX' for r in result['pending_transition_refusals'])
    assert not any(r['inception_code']=='NEWX' for r in b._read_existing(out/b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES))
    assert result['direct_registrant_intake']==initial['direct_registrant_intake']
    assert result['direct_registrant_rederivation']['SPY']=='LISTING_UNAVAILABLE'


def test_retained_refusal_keeps_cause_and_capture(build_scratch,monkeypatch):
    out,_=build_scratch
    rows=b._read_existing(out/b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
    lost=next(r for r in rows if r['inception_code']=='LOST')
    lost.update(issuer_cik=None,issuer_id=None,issuer_state='NO_ISSUER_EVIDENCE',issuer_evidence_snapshot=None)
    b._write_parquet(rows,b.MASTER_COLUMNS,out/b.MASTER_NAME,b.MASTER_DTYPES)
    monkeypatch.setattr(b,'load_cik_map',lambda: ({},'2026-10-07',out/'none',frozenset()))
    b.build(out)
    result=b.build(out,direct_registrant_inputs=[intake_input()])
    row=result['direct_registrant_intake']['observations']['SPY']
    assert row['status']=='REFUSED' and row['owner_refusals']
    assert row['capture']==observation()[1]
    assert 'pending-transition' in row['owner_refusals'][0]['reason']


@pytest.mark.parametrize('field,value',[
    ('listing_key',None),('observed_on',None),('cik',None),('title',None),
    ('security_id',None),('capture',None),('status',[]),
    ('listing_key','US-XNYS-SPY'),('observed_on','not-a-date'),('cik','884394'),
    ('response_sha256','x'),('listing_snapshot_sha256',123),
])
def test_resealed_bad_retention_is_a_typed_refusal(build_scratch,field,value):
    out,_=build_scratch
    b.build(out,direct_registrant_inputs=[intake_input()])
    path=out/b.RECEIPT_NAME;record=json.loads(path.read_bytes())
    state=record['direct_registrant_intake'];state['observations']['SPY'][field]=value
    state['sha256']=b._reference_digest({k:state[k] for k in ('schema','observations')})
    path.write_text(json.dumps(record));before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError): b.build(out)
    assert {p.name:p.read_bytes() for p in out.iterdir()}==before


@pytest.mark.parametrize('change',['missing','extra','symbol_list','not_object','not_list','empty_object'])
def test_programmatic_input_shape_is_a_typed_refusal(build_scratch,change):
    out,_=build_scratch;source=intake_input();inputs=[source]
    if change=='missing': source.pop('capture')
    elif change=='extra': source['extra']='invalid'
    elif change=='symbol_list': source['symbol']=[]
    elif change=='not_object': inputs=[None]
    elif change=='not_list': inputs='bad'
    else: inputs={}
    before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(b.IdentityError): b.build(out,direct_registrant_inputs=inputs)
    assert {p.name:p.read_bytes() for p in out.iterdir()}==before


@pytest.mark.parametrize('change',['supported','other_exit','missing','venue','flags','delisted','older'])
def test_retained_resolution_requires_present_support(build_scratch,change):
    out,_=build_scratch
    first=b.build(out,direct_registrant_inputs=[intake_input()])
    assert first['direct_registrant_rederivation']['SPY']=='CURRENT'
    rows=b._read_existing(out/b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
    directory,flags,day,_=b.load_directory();directory=dict(directory);flags=copy.deepcopy(flags);delisted={}
    if change=='missing': directory.pop('SPY')
    elif change=='venue': directory['SPY']='N'
    elif change=='flags': flags['SPY']['test_issue']=True
    elif change=='delisted': delisted['SPY']={'exchange':'NYSE','last_session':'2026-10-14'}
    elif change=='other_exit': delisted['AVB']={'exchange':'NYSE','last_session':'2026-10-14'}
    elif change=='older': day='2026-10-14'
    result=b._retained_direct_resolutions(first['direct_registrant_intake'],rows,
        directory=directory,directory_flags=flags,delisted=delisted,snapshot_date=day)
    assert len(result)==(1 if change in {'supported','other_exit'} else 0)


def test_tombstone_reports_retired_without_changing_admission_history(build_scratch):
    out,_=build_scratch
    first=b.build(out,direct_registrant_inputs=[intake_input()])
    rows=b._read_existing(out/b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
    spy=next(r for r in rows if r['inception_code']=='SPY')
    spy.update(security_state='SUPERSEDED',superseded_by='SEC:US-XNAS-OTHER')
    b._write_parquet(rows,b.MASTER_COLUMNS,out/b.MASTER_NAME,b.MASTER_DTYPES)
    current=b.build(out)
    assert current['direct_registrant_intake']==first['direct_registrant_intake']
    assert current['direct_registrant_rederivation']['SPY']=='RETIRED'


# Bounded SPY option-root source admission; synthetic fixtures only.
from datetime import datetime, timezone

ROOT_NOW='2026-10-15T12:00:00+00:00'
ROOT_URLS={
 'cboe_reference':'https://cdn.cboe.com/data/us/options/market_statistics/symbol_reference/cone-underlying.csv',
 'cboe_product':'https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications',
 'theta_contract':'https://thetadata.net/docs/operations/option_history_eod.html',
 'registrant':'https://data.sec.gov/submissions/CIK0000884394.json'}

def root_capture(role,body):
 return dict(url=ROOT_URLS[role],final_url=ROOT_URLS[role],status=200,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),
   request_started_at='2026-10-15T11:00:00Z',read_completed_at='2026-10-15T11:00:01Z')

def root_body_change(s,role,body):
 s[role]={'body':body,'capture':root_capture(role,body)}

@pytest.fixture
def root_sources():
 d=intake_input()
 raw=json.loads(d['response_body']);raw['name']='SPDR S&P 500 ETF TRUST'
 values={
  'registrant':json.dumps(raw).encode(),
  'cboe_reference':b'Symbol,Company,Symbol Type,Options Type,Clearing\nSPY,STATE STR SPDR S&P 500 ETF TR TR UNIT,ETF,Standard,OCC\n',
  'cboe_product':('<table><tr><th></th><th>SPDR ® S&P 500 ® ETF Options</th></tr>'
    '<tr><td>Root Ticker Symbol</td><td>SPY</td></tr><tr><td>Options Chain</td><td>SPY</td></tr>'
    '<tr><td>Settlement Type</td><td>Physical Shares of ETF</td></tr>'
    '<tr><td>Exercise Style</td><td>American</td></tr></table>').encode(),
  'theta_contract':b'<p>/v3/option/history/eod</p><p>symbol Required - The stock or index symbol, or underlying symbol for options. Type: string</p>'}
 return {**{k:{'body':v,'capture':root_capture(k,v)} for k,v in values.items()},
  'listing_body':d['listing_body'],'listing_receipt_body':d['listing_receipt_body']}

def root_master():
 return dict(security_id='SEC:US-ARCX-SPY',listing_key='US-ARCX-SPY',country='US',mic='ARCX',
  inception_code='SPY',security_state=None,superseded_by=None,
  effective_at='2026-10-15T00:00:00',ingested_at='2026-10-15T10:00:00')

def test_root_prepare_and_canonical_admission(root_sources):
 row,e=b.admit_spy_option_root(root_sources,[root_master()],decision_at=ROOT_NOW)
 assert row.security_id=='SEC:US-ARCX-SPY' and row.alias_kind=='occ_root'
 assert row.valid_from==date(2026,10,15) and row.valid_to==date(2026,10,16)
 assert row.known_at.isoformat()=='2026-10-15T11:00:01+00:00'
 assert e['listing']['listing_key']=='US-ARCX-SPY'

@pytest.mark.parametrize('field,value', [('status',403),('status',True),('url','https://wrong.example'),
 ('final_url','https://wrong.example'),('bytes',True),('bytes',1),('sha256','0'*64),
 ('request_started_at','2026-10-14T11:00:00Z'),('read_completed_at','2026-10-16T11:00:00Z'),
 ('request_started_at','2026-10-15T11:00:02Z'),('read_completed_at','2026-10-15T11:00:01')])
def test_root_capture_refusal(root_sources,field,value):
 root_sources['cboe_reference']['capture'][field]=value
 with pytest.raises(b.IdentityError):b.prepare_spy_option_root(root_sources,decision_at=ROOT_NOW)

@pytest.mark.parametrize('role,old,new',[
 ('cboe_reference',b'SPY,',b'QQQ,'),('cboe_reference',b',ETF,',b',Index,'),
 ('cboe_reference',b',Standard,',b',Adjusted,'),('cboe_reference',b',OCC',b',Other'),
 ('cboe_reference',b'STATE STR SPDR S&P 500 ETF TR TR UNIT',b'Other ETF'),
 ('cboe_product',b'<td>SPY</td>',b'<td>SPY1</td>'),
 ('cboe_product',b'Physical Shares of ETF',b'Cash'),('cboe_product',b'American',b'European'),
 ('theta_contract',b'/v3/option/history/eod',b'/v2/history'),
 ('theta_contract',b'underlying symbol for options',b'issuer ticker for options'),
 ('registrant',b'0000884394',b'0000000001'),('registrant',b'SPDR S&P 500 ETF TRUST',b'Other fund')])
def test_root_semantic_refusals_even_with_matching_hash(root_sources,role,old,new):
 root_body_change(root_sources,role,root_sources[role]['body'].replace(old,new))
 with pytest.raises(b.IdentityError):b.prepare_spy_option_root(root_sources,decision_at=ROOT_NOW)

@pytest.mark.parametrize('change',['duplicate_reference','duplicate_column','duplicate_product','split_tables','nested_table','invalid_utf8','oversize'])
def test_root_source_shape(root_sources,change):
 if change=='duplicate_reference':role='cboe_reference';raw=root_sources[role]['body']+root_sources[role]['body'].splitlines(True)[1]
 elif change=='duplicate_column':role='cboe_reference';raw=root_sources[role]['body'].replace(b'Symbol,Company',b'Symbol,Symbol')
 elif change=='duplicate_product':role='cboe_product';raw=root_sources[role]['body']*2
 elif change=='split_tables':role='cboe_product';raw=root_sources[role]['body'].replace(b'<tr><td>Root',b'</table><table><tr><td>Root')
 elif change=='nested_table':role='cboe_product';raw=b'<table>'+root_sources[role]['body']+b'</table>'
 elif change=='invalid_utf8':role='theta_contract';raw=b'\xff'
 else:role='cboe_reference';raw=b' '*(b._REFERENCE_MAX_BYTES+1)
 root_body_change(root_sources,role,raw)
 with pytest.raises(b.IdentityError):b.prepare_spy_option_root(root_sources,decision_at=ROOT_NOW)

@pytest.mark.parametrize('field,value', [('security_id','IDX:SPX'),('security_state','SUPERSEDED'),
 ('superseded_by','SEC:US-XNYS-OTHER'),('listing_key','US-XNYS-SPY'),('country','CA'),('mic','XNYS'),
 ('inception_code','QQQ'),('effective_at','2026-10-16T00:00:00'),('ingested_at','2026-10-15T13:00:00'),
 ('ingested_at','2026-10-14T23:00:00'),('effective_at',None)])
def test_root_bad_existing_target(root_sources,field,value):
 m=root_master();m[field]=value
 with pytest.raises(b.IdentityError):b.admit_spy_option_root(root_sources,[m],decision_at=ROOT_NOW)

@pytest.mark.parametrize('rows',[[],[root_master(),root_master()]])
def test_root_missing_or_duplicate_target(root_sources,rows):
 with pytest.raises(b.IdentityError):b.admit_spy_option_root(root_sources,rows,decision_at=ROOT_NOW)

@pytest.fixture
def root_published(build_scratch,monkeypatch):
 out,original=build_scratch
 b.build(out,direct_registrant_inputs=[intake_input()])
 monkeypatch.setattr(b,'_iso_now',lambda:'2026-10-15T12:00:00')
 return out,original

def root_contents(out):return {p.name:p.read_bytes() for p in out.iterdir()}
def root_records(out):return b._read_existing(out/b.ALIASES_NAME,b.ALIAS_COLUMNS,b.ALIAS_DTYPES,allow_missing=b.OPTIONAL_ALIAS_COLUMNS)

def test_root_full_writer_preserves_records_and_root_lookup(root_published,root_sources):
 out,original=root_published;before=root_contents(out);old=root_records(out)
 result=b.build(out,spy_option_root_input=root_sources)
 assert result['prospective_reference']==original
 new=root_records(out);assert len(new)==len(old)+1 and all(r in new for r in old)
 for name,body in before.items():
  if name not in (b.ALIASES_NAME,b.RECEIPT_NAME):assert (out/name).read_bytes()==body
 ev=(json.dumps(result['spy_option_root'],indent=2,sort_keys=True)+'\n').encode()
 table=b.VendorAliasTable.from_records(new)
 assert table.resolve_option_underlying('thetadata','SPY',date(2026,10,15),decision_at=ROOT_NOW,evidence_bytes=ev).security_id=='SEC:US-ARCX-SPY'
 assert table.resolve('thetadata','SPY',date(2026,10,15)) is None
 assert table.vendor_symbol_for('thetadata','SEC:US-ARCX-SPY',date(2026,10,15)) is None
 saved=root_contents(out)
 again=b.build(out)
 assert again['spy_option_root']==result['spy_option_root'] and root_records(out)==new
 with pytest.raises(b.IdentityError,match='no replay'):b.build(out,spy_option_root_input=root_sources)
 assert root_contents(out)==saved

@pytest.mark.parametrize('change',['missing_target','retired_target','current_listing','listing_bytes','ordinary_change','retained_tamper','missing_evidence','combined'])
def test_root_writer_refuses_before_outputs(root_published,root_sources,monkeypatch,change,tmp_path):
 out,_=root_published
 if change in ('missing_target','retired_target'):
  rows=b._read_existing(out/b.MASTER_NAME,b.MASTER_COLUMNS,b.MASTER_DTYPES)
  if change=='missing_target':rows=[r for r in rows if r['inception_code']!='SPY']
  else:next(r for r in rows if r['inception_code']=='SPY').update(security_state='SUPERSEDED',superseded_by='SEC:US-XNYS-OTHER')
  b._write_parquet(rows,b.MASTER_COLUMNS,out/b.MASTER_NAME,b.MASTER_DTYPES)
 elif change in ('current_listing','listing_bytes'):
  mapping,flags,day,path=b.load_directory()
  if change=='current_listing':mapping=dict(mapping);mapping.pop('SPY')
  else:path=tmp_path/'changed.parquet';path.write_bytes(root_sources['listing_body']+b' ')
  monkeypatch.setattr(b,'load_directory',lambda:(mapping,flags,day,path))
 elif change=='ordinary_change':
  old=b.build_alias_rows
  monkeypatch.setattr(b,'build_alias_rows',lambda *a,**k:old(*a,**k)+[b.AliasRow('yahoo','EXTRA','SEC:US-ARCX-SPY')])
 elif change in ('retained_tamper','missing_evidence'):
  b.build(out,spy_option_root_input=root_sources)
  path=out/b.RECEIPT_NAME;value=json.loads(path.read_bytes())
  if change=='retained_tamper':value['spy_option_root']['scope']='changed bytes'
  else:del value['spy_option_root']
  path.write_text(json.dumps(value))
 before=root_contents(out)
 with pytest.raises(b.IdentityError):
  if change in ('retained_tamper','missing_evidence'):b.build(out)
  elif change=='combined':b.build(out,spy_option_root_input=root_sources,direct_registrant_inputs=[intake_input()])
  else:b.build(out,spy_option_root_input=root_sources)
 assert root_contents(out)==before

def root_manifest(tmp_path,root_sources):
 value=copy.deepcopy(root_sources)
 for role in ROOT_URLS:
  name=role+'.dat';(tmp_path/name).write_bytes(value[role]['body']);value[role]['body']=name
 for role in ('listing_body','listing_receipt_body'):
  name=role+'.dat';(tmp_path/name).write_bytes(value[role]);value[role]=name
 p=tmp_path/'input.json';p.write_text(json.dumps({'schema':'mastermind.spy_option_root_input.v1','sources':value}));return p

def test_root_cli_and_manifest(root_published,root_sources,tmp_path):
 out,_=root_published;p=root_manifest(tmp_path,root_sources)
 assert b.main(['--out',str(out),'--spy-option-root-evidence',str(p)])==0
 assert json.loads((out/b.RECEIPT_NAME).read_text())['spy_option_root']['root']=='SPY'

@pytest.mark.parametrize('kind',['duplicate','traversal','wrong_schema','missing_file','symlink','nightly'])
def test_root_bad_local_manifest(root_sources,tmp_path,kind):
 p=root_manifest(tmp_path,root_sources)
 if kind=='nightly':
  with pytest.raises(SystemExit) as e:b.main(['--nightly','--spy-option-root-evidence',str(p)])
  assert e.value.code==2;return
 if kind=='duplicate':p.write_text('{"schema":1,"schema":2}')
 elif kind=='missing_file':(tmp_path/'registrant.dat').unlink()
 elif kind=='symlink':
  f=tmp_path/'registrant.dat';f.rename(tmp_path/'real.dat');f.symlink_to(tmp_path/'real.dat')
 else:
  v=json.loads(p.read_text())
  if kind=='traversal':v['sources']['registrant']['body']='../parent.dat'
  else:v['schema']='unknown'
  p.write_text(json.dumps(v))
 with pytest.raises(b.IdentityError):b.read_spy_option_root_input(p)


@pytest.mark.parametrize('decision', ['2026-10-16T00:00:00Z', '2026-10-17T12:00:00Z'])
def test_root_new_admission_refuses_after_observed_day(root_sources, decision):
    with pytest.raises(b.IdentityError, match='observed date'):
        b.admit_spy_option_root(root_sources, [root_master()], decision_at=decision)


def test_root_retains_listing_clocks_and_exact_canonical_target_in_seal(root_sources):
    master = root_master()
    row, evidence = b.admit_spy_option_root(root_sources, [master], decision_at=ROOT_NOW)
    assert evidence['canonical_target'] == {key: master.get(key) for key in b.MASTER_COLUMNS}
    assert evidence['listing']['listing_snapshot_sha256'] == hashlib.sha256(root_sources['listing_body']).hexdigest()
    assert evidence['listing']['listing_receipt_sha256'] == hashlib.sha256(root_sources['listing_receipt_body']).hexdigest()
    assert evidence['listing']['response_sha256'] == root_sources['registrant']['capture']['sha256']
    for role in ROOT_URLS:
        assert evidence['sources'][role]['request_started_at'] == '2026-10-15T11:00:00+00:00'
    assert any('No verified Matrix session' in text for text in evidence['limits'])
    changed = dict(master, ingested_at='2026-10-15T10:01:00')
    changed_row, _ = b.admit_spy_option_root(root_sources, [changed], decision_at=ROOT_NOW)
    assert changed_row.evidence_sha256 != row.evidence_sha256
    assert changed_row.binding_sha256 != row.binding_sha256


def test_root_capture_uses_one_closed_grammar(root_sources):
    root_sources['theta_contract']['capture']['http_status'] = 200
    with pytest.raises(b.IdentityError):
        b.prepare_spy_option_root(root_sources, decision_at=ROOT_NOW)


@pytest.mark.parametrize('tag', ['script', 'style', 'template'])
@pytest.mark.parametrize('role', ['theta_contract', 'cboe_product'])
def test_root_hidden_markup_is_not_product_semantics(root_sources, tag, role):
    raw = ('<' + tag + '>').encode() + root_sources[role]['body'] + ('</' + tag + '>').encode()
    root_body_change(root_sources, role, raw)
    with pytest.raises(b.IdentityError):
        b.prepare_spy_option_root(root_sources, decision_at=ROOT_NOW)


def test_root_refuses_spy_in_a_second_product_column(root_sources):
    role = 'cboe_product'
    raw = root_sources[role]['body'].replace(b'<td>Root Ticker Symbol</td><td>SPY</td>',
        b'<td>Root Ticker Symbol</td><td>SPY</td><td>SPY</td>')
    root_body_change(root_sources, role, raw)
    with pytest.raises(b.IdentityError):
        b.prepare_spy_option_root(root_sources, decision_at=ROOT_NOW)


def test_root_late_cli_admission_preserves_all_outputs(root_published, root_sources, monkeypatch, tmp_path):
    out, _ = root_published
    manifest = root_manifest(tmp_path, root_sources)
    monkeypatch.setattr(b, '_iso_now', lambda: '2026-10-16T00:00:00')
    before = root_contents(out)
    with pytest.raises(b.IdentityError, match='observed date'):
        b.main(['--out', str(out), '--spy-option-root-evidence', str(manifest)])
    assert root_contents(out) == before


def test_root_later_ordinary_refresh_keeps_historical_window(root_published, root_sources, monkeypatch):
    out, _ = root_published
    first = b.build(out, spy_option_root_input=root_sources)
    saved = root_records(out)
    monkeypatch.setattr(b, '_iso_now', lambda: '2026-10-16T12:00:00')
    later = b.build(out, dry_run=True)
    assert later['spy_option_root'] == first['spy_option_root']
    assert root_records(out) == saved
    body = (json.dumps(first['spy_option_root'], indent=2, sort_keys=True) + '\n').encode()
    assert b.VendorAliasTable.from_records(saved).resolve_option_underlying(
        'thetadata', 'SPY', date(2026, 10, 16), decision_at='2026-10-16T12:00:00Z', evidence_bytes=body) is None


# R19: fund registrants may legitimately expose an empty submissions ticker list.
FUND_URL = 'https://www.sec.gov/files/company_tickers_mf.json'
FUND_IDS = {'QQQ': ('0001067839', 'S000101292', 'C000271435'),
            'SMH': ('0001137360', 'S000034411', 'C000105869')}


@pytest.fixture(scope='session')
def fund_listing(synthetic_captures, tmp_path_factory):
    root = tmp_path_factory.mktemp('fund-reference-synthetic')
    frame = pd.read_parquet(EVIDENCE / 'listing-2026-10-15.parquet')
    for i, symbol in enumerate(('QQQ', 'SMH')):
        frame.loc[i, 'symbol'] = symbol
        frame.loc[i, 'etf'] = True
    artifact = root / 'snapshots' / '2026-10-15.parquet'
    artifact.parent.mkdir()
    frame.to_parquet(artifact, index=False)
    sources = [(sid, receipts.SourceFetch(value='synthetic', content=b'synthetic source', requested_url=url,
        started_at='2026-10-15T01:00:00.000000Z', completed_at='2026-10-15T01:00:01.000000Z'))
        for sid, url in [(receipts.NASDAQ_LISTED_SOURCE_ID, 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'),
                         (receipts.OTHER_LISTED_SOURCE_ID, 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt')]]
    receipt = receipts.build_symbol_directory_completion_receipt(kind='listing_snapshot', observation_date='2026-10-15',
        artifact_path=artifact, source_fetches=sources,
        collector_started_at='2026-10-15T00:59:59.000000Z', collector_completed_at='2026-10-15T01:00:02.000000Z',
        pre_dedupe_rows=len(frame), duplicate_occurrences=0, duplicate_key_count=0,
        source_row_counts=((receipts.NASDAQ_LISTED_SOURCE_ID, 5000), (receipts.OTHER_LISTED_SOURCE_ID, 6500)),
        pre_dedupe_spy_occurrences=({'source_id':receipts.OTHER_LISTED_SOURCE_ID,'symbol':'SPY',
            'security_name':'Synthetic listing','exchange':'P','etf':True,'test_issue':False,'is_preferred':False},),
        non_authoritative_footers=tuple(receipts.footer_diagnostic(source_id=sid,
            text='File Creation Time: 10/15/2026 01:00:00') for sid,_ in sources))
    return artifact.read_bytes(), json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()+b'\n'


def fund_source(fund_listing, symbol='QQQ'):
    cik, series, shareclass = FUND_IDS[symbol]
    body = json.dumps({'cik':cik,'name':'Synthetic '+symbol+' Registrant','tickers':[],'exchanges':[]}).encode()
    capture = dict(url=f'https://data.sec.gov/submissions/CIK{cik}.json',
        final_url=f'https://data.sec.gov/submissions/CIK{cik}.json',status=200,bytes=len(body),
        sha256=hashlib.sha256(body).hexdigest(),request_started_at='2026-10-15T09:59:20Z',read_completed_at='2026-10-15T09:59:21Z')
    mapping = json.dumps({'fields':['cik','seriesId','classId','symbol'],'data':[[int(cik),series,shareclass,symbol]]}).encode()
    mc = dict(url=FUND_URL,final_url=FUND_URL,status=200,bytes=len(mapping),sha256=hashlib.sha256(mapping).hexdigest(),
        request_started_at='2026-10-15T09:59:30Z',read_completed_at='2026-10-15T09:59:31Z')
    return dict(symbol=symbol,response_body=body,capture=capture,listing_body=fund_listing[0],
        listing_receipt_body=fund_listing[1],fund_reference_body=mapping,fund_reference_capture=mc)


def change_fund_body(source, body):
    source['fund_reference_body'] = body
    source['fund_reference_capture'].update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())


@pytest.mark.parametrize('symbol',['QQQ','SMH'])
def test_fund_empty_submissions_can_bind_captured_series_class(fund_listing,symbol):
    source=fund_source(fund_listing,symbol); before=copy.deepcopy(source)
    result=b.prepare_direct_registrant(**source,decision_at=NOW)
    row=result['registrant']; link=row['fund_reference']
    assert result['resolution'].listing_key.render()=='US-XNAS-'+symbol
    assert row['known_at']=='2026-10-15T09:59:31+00:00'
    assert link['schema']=='mastermind.sec_fund_reference.v1'
    assert (link['cik'],link['series_id'],link['class_id'],link['symbol'])==(*FUND_IDS[symbol],symbol)
    assert link['capture']==source['fund_reference_capture']
    assert row['scope']=='pending_transition_independence_only'
    assert source==before and 'security_id' not in row


@pytest.mark.parametrize('mode',['missing_body','missing_capture','missing_both','wrong_scope','contradictory_tickers'])
def test_fund_requires_explicit_complete_evidence(fund_listing,mode):
    source=fund_source(fund_listing)
    if mode=='missing_body':source.pop('fund_reference_body')
    elif mode=='missing_capture':source.pop('fund_reference_capture')
    elif mode=='missing_both':source.pop('fund_reference_body');source.pop('fund_reference_capture')
    elif mode=='wrong_scope':source['symbol']='SPY'
    else:
        x=json.loads(source['response_body']);x['tickers']=['OTHER'];source['response_body']=json.dumps(x).encode()
        source['capture'].update(bytes=len(source['response_body']),sha256=hashlib.sha256(source['response_body']).hexdigest())
    with pytest.raises(b.IdentityError):b.prepare_direct_registrant(**source,decision_at=NOW)


@pytest.mark.parametrize('kind',['wrong_cik','bool_cik','bad_series','bad_class','no_symbol','duplicate','conflicting','bad_fields','unknown_key','bad_row','nonfinite'])
def test_fund_mapping_disagreement_is_not_resolved_by_ticker_equality(fund_listing,kind):
    source=fund_source(fund_listing);x=json.loads(source['fund_reference_body']);row=x['data'][0]
    if kind=='wrong_cik':row[0]=1137360
    elif kind=='bool_cik':row[0]=True
    elif kind=='bad_series':row[1]='C000101292'
    elif kind=='bad_class':row[2]='S000271435'
    elif kind=='no_symbol':row[3]='QQQM'
    elif kind=='duplicate':x['data'].append(list(row))
    elif kind=='conflicting':x['data'].append([1137360,'S000034411','C000105869','QQQ'])
    elif kind=='bad_fields':x['fields'][0]='unknown'
    elif kind=='unknown_key':x['extra']='unrecognized'
    elif kind=='bad_row':row.pop()
    else:row[0]=float('nan')
    change_fund_body(source,json.dumps(x).encode())
    with pytest.raises(b.IdentityError):b.prepare_direct_registrant(**source,decision_at=NOW)


@pytest.mark.parametrize('field,value',[('url','https://example.com/funds.json'),('final_url','https://example.com/funds.json'),
    ('status',True),('status',403),('bytes',True),('sha256','0'*64),
    ('request_started_at','2026-10-14T09:59:30Z'),('request_started_at','2026-10-15T09:59:32Z'),
    ('read_completed_at','2026-10-15T10:00:01Z'),('read_completed_at','2026-10-15T09:59:31')])
def test_fund_capture_provenance_and_clock_are_required(fund_listing,field,value):
    source=fund_source(fund_listing);source['fund_reference_capture'][field]=value
    with pytest.raises(b.IdentityError):b.prepare_direct_registrant(**source,decision_at=NOW)


@pytest.mark.parametrize('raw',[b'{"fields":[],"fields":[],"data":[]}',b'[]',b'\xff',b' '*(2*1024*1024+1)], ids=['duplicate-key','nonobject','invalid-utf8','oversize'])
def test_fund_strict_bounded_json(fund_listing,raw):
    source=fund_source(fund_listing);change_fund_body(source,raw)
    with pytest.raises(b.IdentityError):b.prepare_direct_registrant(**source,decision_at=NOW)


def test_fund_native_manifest_v2_roundtrip_and_v1_unchanged(fund_listing,tmp_path):
    source=fund_source(fund_listing);record=copy.deepcopy(source)
    for key in ('response_body','listing_body','listing_receipt_body','fund_reference_body'):
        (tmp_path/key).write_bytes(record[key]);record[key]=key
    p=tmp_path/'manifest.json';p.write_text(json.dumps({'schema':'mastermind.direct_registrant_input.v2','sources':[record]}))
    assert b.read_direct_registrant_inputs(p)==[source]
    p.write_text(json.dumps({'schema':'mastermind.direct_registrant_input.v1','sources':[record]}))
    with pytest.raises(b.IdentityError):b.read_direct_registrant_inputs(p)


def test_fund_retained_state_preserves_metadata_and_no_replay(fund_listing,tmp_path):
    source=fund_source(fund_listing);state,res=b._direct_registrant_state(tmp_path,[source],NOW)
    row=state['observations']['QQQ'];row.update(status='BOUND',security_id='SEC:US-XNAS-QQQ')
    state['sha256']=b._reference_digest({k:state[k] for k in ('schema','observations')})
    p=tmp_path/b.RECEIPT_NAME;p.write_text(json.dumps({'direct_registrant_intake':state}));before=p.read_bytes()
    replay,_=b._direct_registrant_state(tmp_path,[],NOW)
    assert replay['observations']==state['observations'] and p.read_bytes()==before
    with pytest.raises(b.IdentityError,match='already retained'):b._direct_registrant_state(tmp_path,[source],NOW)


@pytest.mark.parametrize('change',['series','future','source_url'])
def test_fund_retained_metadata_cannot_be_silently_relabelled(fund_listing,tmp_path,change):
    source=fund_source(fund_listing);state,_=b._direct_registrant_state(tmp_path,[source],NOW)
    row=state['observations']['QQQ'];row.update(status='BOUND',security_id='SEC:US-XNAS-QQQ')
    link=row['fund_reference']
    if change=='series':link['series_id']='S000000001'
    elif change=='future':link['capture']['read_completed_at']='2026-10-15T10:00:01Z'
    else:link['capture']['url']='https://example.com/funds.json'
    state['sha256']=b._reference_digest({k:state[k] for k in ('schema','observations')})
    p=tmp_path/b.RECEIPT_NAME;p.write_text(json.dumps({'direct_registrant_intake':state}));before=p.read_bytes()
    with pytest.raises(b.IdentityError):b._direct_registrant_state(tmp_path,[],NOW)
    assert p.read_bytes()==before


def test_fund_canonical_independence_fence_still_owns_mint(fund_listing):
    source=fund_source(fund_listing);result=b.prepare_direct_registrant(**source,decision_at=NOW)
    old=cohort();mint=b.mint_master_rows([result['resolution']],old,NOW,direct_registrant_inputs=[source])
    assert mint[1]=={'QQQ':'SEC:US-XNAS-QQQ'} and len(mint[0])==len(old)+1
    new=next(row for row in mint[0] if row['security_id']=='SEC:US-XNAS-QQQ')
    assert new['issuer_id'] is None and new['issuer_cik'] is None
    old[0]['issuer_cik']=FUND_IDS['QQQ'][0]
    refused=b.mint_master_rows([result['resolution']],old,NOW,direct_registrant_inputs=[source])
    assert not refused[1] and refused[4]


def test_fund_unassigned_symbol_row_is_not_a_conflicting_ticker(fund_listing):
    source=fund_source(fund_listing)
    value=json.loads(source['fund_reference_body'])
    value['data'].append([1048606,'S000002797','C000219432',''])
    change_fund_body(source,json.dumps(value).encode())
    prepared=b.prepare_direct_registrant(**source,decision_at=NOW)
    assert prepared['registrant']['fund_reference']['symbol']=='QQQ'
    assert prepared['registrant']['fund_reference']['series_id']=='S000101292'
