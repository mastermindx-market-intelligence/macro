"""Synthetic prospective provenance; no provider, live writer or acceptance claim."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from engine import live_quotes
from engine.entry_radar import challengers as ch, live_eval as le, live_ledger as ll
from engine.entry_radar import candidate_provenance as cp, earnings_context as ec
from engine.marketing.live_verify import _quotes_from_snapshot
from lib import evidence_foundation as ef
from lib.quote_native_metadata import copy_native_metadata, from_native_quote
from scripts.build_live_quotes import to_worker_quotes
from tests.test_earnings_opportunity_qualification import inputs
from tests.test_entry_radar_quote_context import native
from tests.test_entry_radar_earnings_context_producer import generation, prepared

CANDIDATE = '2026-10-07T14:00:00Z'
QUOTE = '2026-10-07T13:59:10Z'
ADMITTED = '2026-10-07T13:59:30Z'
FROZEN = '2026-10-07T14:00:01Z'
COMPOSED = '2026-10-07T14:01:00Z'
ORIGINAL = 'live_flow/entry_radar_events/2026-10-07/100001-original.json'


def dt(value):return datetime.fromisoformat(value.replace('Z','+00:00'))


def polygon(symbol='MU'):
    return {'tickers':[{'ticker':symbol,'lastTrade':{'p':100, 't':int(dt(QUOTE).timestamp()*10**9)},
                        'prevDay':{'c':101}}]}


def response_book():
    parsed=live_quotes.parse_polygon_snapshot(polygon(), now=dt(ADMITTED))
    worker=to_worker_quotes(parsed,include_private_provenance=True)
    return _quotes_from_snapshot({'quotes':worker})


def make_chain(monkeypatch, pack_hash='1'*64):
    journal=le.SessionJournal(None)
    record=journal.open_session(session='2026-10-07',ticker='MU',pack_as_of='2026-10-06',
        pack_hash=pack_hash,price_basis='adjusted')
    quote=le.read_quote('MU',response_book()['MU'],now=dt(ADMITTED),session=dt(CANDIDATE).date(),max_age_min=20)
    assert quote.usable
    monkeypatch.setattr(le,'_quote_recorded_now',lambda:dt(ADMITTED))
    assert journal.append_point(record,ts=quote.ts,price=quote.price,basis=quote.basis,
        source=quote.source,basis_audit={},native_quote_metadata=quote.native_quote_metadata)
    obs=ch.Observation(ticker='MU',observed_at=CANDIDATE,market_session='2026-10-07',
        interval_start='2026-10-07T13:55:00Z',availability='provisional',bar_state='provisional',
        sampled_close=100,running_sampled_low=100,running_minute_low=100,k=10,d=12,hist=-1,
        source_bar_time='2026-10-07',source_bar_known_at=None,data_vintage='journal:'+pack_hash[:12],
        price_basis='adjusted',daily_price_basis='adjusted',atr_prior_confirmed=2,atr_basis='native',
        confirmed_bars=300,history_freshness='confirmed')
    monkeypatch.setattr(le,'_quote_recorded_now',lambda:dt(FROZEN))
    assert journal.freeze_observations(record,[obs])==1
    run=ch.run_c1([obs])
    ledger=ll.LiveEpisodeLedger(None)
    delta=ledger.apply_run(ticker='MU',as_of_session='2026-10-07',runs=[run],pass_id='original')
    class SyntheticMemorySpool:
        def __init__(self):self.payload=None
        def append_pass(self,payload,**kwargs):self.payload=deepcopy(payload);return ORIGINAL
    spool=SyntheticMemorySpool()
    receipt,committed=ll.spool_then_commit(ledger,delta,spool=spool,pass_ts=FROZEN,
        session='2026-10-07',stamp='100001',pack_as_of='2026-10-06',pack_hash=pack_hash)
    assert committed and receipt==ORIGINAL
    return ledger.episodes[0].to_dict(),record,journal,ledger,spool,delta


@pytest.fixture
def chain(monkeypatch):return make_chain(monkeypatch)


def compose(chain,inputs,**kw):
    episode,record,journal,ledger,spool,delta=chain
    return cp.compose_candidate_quote_provenance(episode,record=record,identity_read=inputs['identity_read'],
        origin=ledger.candidate_origin(episode['episode_id']),composed_at=COMPOSED,**kw)


def test_native_response_to_kept_observation_to_identity_and_original_commit(chain,inputs):
    before=deepcopy((chain[0],chain[1].to_dict(),chain[3].to_dict() if hasattr(chain[3],'to_dict') else chain[3].events,chain[4].payload))
    result=compose(chain,inputs)
    assert result['schema']==cp.SCHEMA
    assert result['quote']['vendor_symbol']=='MU' and result['quote']['vendor']=='polygon'
    assert result['quote']['response_field']=='tickers[].ticker'
    assert result['quote']['namespace_basis']=='native_endpoint_parser'
    assert result['quote']['provider_identity_attestation']=='not_available'
    assert dt(result['quote']['recorded_at'])==dt(ADMITTED)
    assert dt(result['observation']['recorded_at'])==dt(FROZEN)
    assert result['identity']['security_id']=='SEC:US-XNAS-MU'
    assert result['origin']['event_spool_key']==result['origin']['transition_spool_key']==ORIGINAL
    assert result['live_projection_eligible'] is False and not any(result['authority'].values())
    assert result['sha256']==cp._hash({k:v for k,v in result.items() if k!='sha256'})
    assert before==deepcopy((chain[0],chain[1].to_dict(),chain[3].to_dict() if hasattr(chain[3],'to_dict') else chain[3].events,chain[4].payload))


@pytest.mark.parametrize('provider',['polygon','yahoo'])
def test_exact_response_symbol_private_only_and_no_price_change(provider):
    parsed=(live_quotes.parse_polygon_snapshot(polygon('mU'),now=dt(ADMITTED)) if provider=='polygon' else
        live_quotes.parse_yahoo_spark({'spark':{'result':[{'symbol':'mU','response':[{'meta':{
            'regularMarketPrice':100,'regularMarketTime':int(dt(QUOTE).timestamp()),'previousClose':101}}]}]}},now=dt(ADMITTED)))
    raw=parsed['mU'];assert raw['native_quote_identity']['vendor_symbol']=='mU'
    plain=to_worker_quotes(parsed);private=to_worker_quotes(parsed,include_private_provenance=True)
    assert 'native_quote_identity' not in plain['mU']
    normalized=_quotes_from_snapshot({'quotes':private})['MU']
    assert normalized['native_quote_metadata']['response_identity']['vendor_symbol']=='mU'
    assert normalized['price']==plain['mU']['price']==100
    assert normalized['ts_ms']==plain['mU']['ts']


@pytest.mark.parametrize('mutation',[
    'legacy_ref','legacy_clock','point_hash','observation_hash','late_admission','late_identity',
    'symbol','vendor','synthetic','timestamp','basis','future_composed','no_spool','wrong_origin',
    'ambiguous_origin','wrong_variant','changed_generation','observation_feature','prefix',
    'response_schema','unsupported_basis','future_native_clock','unbound_namespace',
])
def test_refuses_missing_or_mismatched_native_link_without_substitution(chain,inputs,mutation):
    episode,record,journal,ledger,spool,delta=chain
    read=inputs['identity_read'];origin=ledger.candidate_origin(episode['episode_id'])
    point=record.points[0];metadata=point['native_quote_metadata'];ref=record.observation_quote_refs[record.observations[0]['interval_start']]
    composed=COMPOSED
    if mutation=='legacy_ref':record.observation_quote_refs.clear()
    elif mutation=='legacy_clock':point.pop('quote_recorded_at')
    elif mutation=='point_hash':point['price']=200
    elif mutation=='observation_hash':record.observations[0]['hist']=123
    elif mutation=='late_admission':point['quote_recorded_at']=COMPOSED
    elif mutation=='late_identity':
        from lib.dataos.identity import ReferenceReadReceipt
        receipt=read.receipt.as_record();ns=str(int(dt(COMPOSED).timestamp()*1e9));receipt.update(read_started_at_utc_ns=ns,read_completed_at_utc_ns=ns)
        read=replace(read,receipt=ReferenceReadReceipt.from_record(receipt))
    elif mutation=='symbol':metadata['response_identity']['vendor_symbol']='OTHER'
    elif mutation=='vendor':metadata['response_identity']['vendor']='yahoo'
    elif mutation=='synthetic':metadata['quote_ts_synthetic']=True
    elif mutation=='timestamp':metadata['ts']+=1
    elif mutation=='basis':point['basis']='minute'
    elif mutation=='future_composed':composed=ADMITTED
    elif mutation=='no_spool':origin['events'][0].pop('spool_key')
    elif mutation=='wrong_origin':origin['transitions'][0]['at']=COMPOSED
    elif mutation=='ambiguous_origin':origin['transitions']*=2
    elif mutation=='wrong_variant':origin['transitions'][0]['variant']='not-native'
    elif mutation=='changed_generation':read=replace(read,receipt=replace(read.receipt,generation_id='0'*64))
    elif mutation=='observation_feature':
        record.observations[0]['k']=11;ref['observation_sha256']=cp._hash(record.observations[0])
    elif mutation=='prefix':ref['point_count']=len(record.points)+1
    elif mutation=='response_schema':metadata['response_identity']['schema']='unqualified.v1'
    elif mutation=='unsupported_basis':metadata['basis']='prev'
    elif mutation=='future_native_clock':
        point['ts']='2026-10-07T13:59:50Z';metadata['quote_ts']=point['ts'];metadata['ts']=int(dt(point['ts']).timestamp()*1000)
    elif mutation=='unbound_namespace':
        metadata['source']='yahoo';metadata['response_identity'].update(vendor='yahoo',response_field='spark.result[].symbol')
    # Rehash mutable source inputs where needed, so these exercise semantic
    # checks rather than merely a stale hash. Historical missing refs stay absent.
    if mutation not in {'point_hash','legacy_ref','observation_hash'}:
        ref['quote_point_sha256']=cp._hash(point)
    with pytest.raises(cp.CandidateProvenanceUnavailable):
        cp.compose_candidate_quote_provenance(episode,record=record,identity_read=read,origin=origin,composed_at=composed)


def test_equal_price_later_point_does_not_replace_frozen_used_quote(chain,inputs,monkeypatch):
    episode,record,journal,ledger,spool,delta=chain
    old=deepcopy(record.observation_quote_refs)
    monkeypatch.setattr(le,'_quote_recorded_now',lambda:dt(COMPOSED))
    newer=deepcopy(response_book()['MU']['native_quote_metadata'])
    newer['ts']+=20000;newer['quote_ts']='2026-10-07T13:59:30Z'
    assert journal.append_point(record,ts=dt(newer['quote_ts']),price=100,basis='trade',source='quotes',
        basis_audit={},native_quote_metadata=newer)
    assert journal.freeze_observations(record,[le.observation_from_dict(record.observations[0])])==0
    assert record.observation_quote_refs==old
    result=compose(chain,inputs)
    assert dt(result['quote']['vendor_timestamp'])==dt(QUOTE)
    assert result['quote']['point_sha256']==cp._hash(record.points[0])
    restored=le.JournalRecord.from_dict(record.to_dict())
    assert restored.observation_quote_refs==old


def test_legacy_frozen_observation_never_acquires_new_reference(chain,monkeypatch):
    episode,record,journal,ledger,spool,delta=chain
    record.observation_quote_refs.clear()
    assert journal.freeze_observations(record,[le.observation_from_dict(record.observations[0])])==0
    assert record.observation_quote_refs=={}


def test_later_commit_does_not_replace_origin_spool_or_rewrite_event(chain,inputs):
    episode,record,journal,ledger,spool,delta=chain
    before=compose(chain,inputs)
    ledger.commit(delta,spool_receipt='live_flow/entry_radar_events/2026-10-07/101000-later.json')
    after=compose(chain,inputs)
    assert after==before


def test_optional_hook_binds_actual_quote_and_exact_accepted_research_case(prepared,inputs,monkeypatch):
    payload,pack,calls=prepared
    chain=make_chain(monkeypatch,pack.pack_hash)
    row,record,journal,ledger,spool,delta=chain
    payload['episodes']=[deepcopy(row)];before=deepcopy(payload)
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory='/synthetic/reference',
        committed=True,ledger=ledger,journal=journal)
    assert report['attached']==1 and report['quote_candidate_provenance']['attached']==1,report
    raw=payload['episodes'][0];projection=raw.pop('research_context');provenance=raw.pop('quote_candidate_provenance')
    assert payload==before
    assert provenance['research_context_ref']=={'case_ref':projection['case_ref'],'context_sha256':projection['sha256']}
    assert provenance['identity']['cik']==projection['research_subject']['key']
    assert provenance['sha256']==cp._hash({k:v for k,v in provenance.items() if k!='sha256'})
    assert projection['live_projection_eligible'] is False
    assert chain[4].payload['events']==list(delta.events)


def test_optional_provenance_failure_preserves_ordinary_research_context(prepared,monkeypatch):
    payload,pack,calls=prepared
    chain=make_chain(monkeypatch,pack.pack_hash);row,record,journal,ledger,spool,delta=chain
    record.observation_quote_refs.clear();payload['episodes']=[row]
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory='/synthetic/reference',
        committed=True,ledger=ledger,journal=journal)
    assert report['attached']==1 and report['quote_candidate_provenance']['attached']==0
    assert 'research_context' in row and 'quote_candidate_provenance' not in row


@pytest.mark.parametrize('changes',[
    {'vendor':'unknown'}, {'response_field':'request.symbol'}, {'vendor_symbol':''},
    {'vendor_symbol':{'private_body':'sentinel'}}, {'provider_authenticated':True},
])
def test_response_namespace_is_not_inferred_or_upgraded(changes):
    row=response_book()['MU'];metadata=deepcopy(row['native_quote_metadata'])
    metadata['response_identity'].update(changes)
    assert copy_native_metadata(metadata) is None
    assert le.read_quote('MU',{**row,'native_quote_metadata':metadata},now=dt(ADMITTED),
        session=dt(CANDIDATE).date(),max_age_min=20).usable


def test_optional_capture_exception_does_not_remove_observation(chain,monkeypatch):
    episode,record,journal,ledger,spool,delta=chain
    later=replace(le.observation_from_dict(record.observations[0]),
        observed_at='2026-10-07T14:05:00Z',interval_start=CANDIDATE)
    monkeypatch.setattr(cp,'capture_observation_quote_reference',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('sentinel')))
    assert journal.freeze_observations(record,[later])==1
    assert record.observations[-1]==le.observation_to_dict(later)
    assert CANDIDATE not in record.observation_quote_refs


def test_submillisecond_native_clock_is_preserved_not_equalized(chain,inputs):
    point=chain[1].points[0]
    point['native_quote_metadata']['quote_ts']='2026-10-07T13:59:10.000123Z'
    ref=next(iter(chain[1].observation_quote_refs.values()));ref['quote_point_sha256']=cp._hash(point)
    result=compose(chain,inputs)
    assert result['quote']['vendor_timestamp']=='2026-10-07T13:59:10.000123Z'
    assert result['quote']['normalized_timestamp']==QUOTE
    assert result['quote']['normalized_basis'] is None and result['quote']['native_basis']=='trade'


def test_other_native_mechanisms_are_not_joined_to_five_minute_quote(chain,inputs):
    from engine.entry_radar import detectors, four_hour
    row=deepcopy(chain[0]);spec=detectors.get_spec(four_hour.C3_DETECTOR_ID)
    row.update(detector_id=spec.detector_id,detector_version=spec.version,detector_spec_hash=spec.spec_hash)
    row['episode_id']=ll.compute_episode_id(ticker=row['ticker'],detector_id=row['detector_id'],
        variant=row['variant'],first_armed_at=row['first_armed_at'])
    with pytest.raises(cp.CandidateProvenanceUnavailable,match='^candidate_quote_mechanism_unsupported$'):
        cp.compose_candidate_quote_provenance(row,record=chain[1],identity_read=inputs['identity_read'],
            origin=chain[3].candidate_origin(chain[0]['episode_id']),composed_at=COMPOSED)


def test_quote_provenance_does_not_require_an_earnings_generation_or_create_a_case(prepared,monkeypatch):
    payload,pack,calls=prepared;chain=make_chain(monkeypatch,pack.pack_hash)
    row,record,journal,ledger,spool,delta=chain;payload['episodes']=[row]
    report=ec.attach_retrospective_earnings_context(payload,pack=replace(pack,earnings_generation=None),
        identity_directory='/synthetic/reference',committed=True,ledger=ledger,journal=journal)
    assert report['attached']==0 and report['quote_candidate_provenance']['attached']==1
    assert 'research_context' not in row and 'research_context_ref' not in row['quote_candidate_provenance']
    assert calls==[]


def test_wrong_pack_cannot_bind_quote_to_current_context(prepared,monkeypatch):
    payload,pack,calls=prepared;chain=make_chain(monkeypatch,'2'*64)
    row,record,journal,ledger,spool,delta=chain;payload['episodes']=[row]
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory='/synthetic/reference',
        committed=True,ledger=ledger,journal=journal)
    assert report['attached']==1 and report['quote_candidate_provenance']['attached']==0
    assert 'quote_candidate_provenance' not in row


from tests.test_entry_radar_w4_live import pack, NEXT_SESSION, et_now, one_pass, quote_book


def test_complete_new_metadata_path_leaves_detector_delta_and_spool_contents_unchanged(tmp_path,pack,monkeypatch):
    monkeypatch.setattr(le,'_attach_catalyst',lambda *a,**k:None)
    def strip(value):
        if isinstance(value,dict):
            return {k:strip(v) for k,v in value.items() if k not in
                {'native_quote_metadata','quote_recorded_at','observation_quote_refs'}}
        if isinstance(value,(list,tuple)):return [strip(v) for v in value]
        return value
    ledgers=[ll.LiveEpisodeLedger(tmp_path/name) for name in ('plain','metadata')]
    for qm,nm,multiple in [(30,32,0.97),(35,37,0.96)]:
        monkeypatch.setattr(le,'_quote_recorded_now',lambda:et_now(nm))
        book=quote_book(pack,multiple=multiple,ts=et_now(qm));enriched=deepcopy(book)
        for symbol,row in enriched['quotes'].items():
            row['native_quote_metadata']=from_native_quote({'source':'polygon','basis':'trade',
                'ts':row['ts'],'quote_ts':et_now(qm).isoformat(),'quote_ts_synthetic':False,
                'native_quote_identity':{'schema':'native_quote_identity.v1','vendor':'polygon',
                    'vendor_symbol':symbol,'response_field':'tickers[].ticker'}})
        results=[one_pass(pack,quotes,now=et_now(nm),ledger=ledger,state_dir=ledger.state_dir)
            for quotes,ledger in zip((book,enriched),ledgers)]
        assert strip(results[0].payload)==strip(results[1].payload)
        assert results[0].delta==results[1].delta
        assert ledgers[0].events==ledgers[1].events and ledgers[0].transitions==ledgers[1].transitions
        assert [e.canonical for e in ledgers[0].episodes]==[e.canonical for e in ledgers[1].episodes]
