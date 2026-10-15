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
