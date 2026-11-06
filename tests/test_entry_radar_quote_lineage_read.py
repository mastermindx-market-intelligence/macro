"""Synthetic native producer -> existing reader; no real-candidate acceptance."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json

import pytest

from engine.entry_radar import earnings_context as ec, live_eval as le, research_read as rr
from lib.evidence_foundation import canonical_json_bytes
from tests.test_entry_radar_candidate_provenance import make_chain
from tests.test_entry_radar_earnings_context_producer import prepared, generation
from tests.test_entry_radar_quote_context import native
from tests.test_earnings_opportunity_qualification import inputs


@pytest.fixture
def published_lineage(prepared,monkeypatch,tmp_path):
    payload,pack,_=prepared
    row,record,journal,ledger,spool,delta=make_chain(monkeypatch,pack.pack_hash)
    payload['episodes']=[row]
    report=ec.attach_retrospective_earnings_context(payload,pack=pack,identity_directory='/synthetic/reference',
        committed=True,ledger=ledger,journal=journal)
    assert report['attached']==report['quote_candidate_provenance']['attached']==1,report
    payload['authority']=le._authority_block();payload['health']['pass']={'at':payload['asof']}
    live=tmp_path/'lineage-live';live.mkdir();path=live/'entry_radar.json';path.write_text(json.dumps(payload))
    return live,path,payload,rr._episode(row)


def rehash(value):
    value['sha256']=sha256(canonical_json_bytes({k:v for k,v in value.items() if k!='sha256'})).hexdigest()


def test_real_producer_shape_projects_only_closed_lineage_metadata(published_lineage):
    live,path,source,episode=published_lineage;before=path.read_bytes()
    assert rr.read_published_research(live)['candidates'][0]['research_state']=='retrospective_context'
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    context=result['case'];lineage=context['quote_lineage']
    assert result['state']=='published_context' and lineage['state']=='recorded_native_lineage'
    assert lineage['episode_binding']==context['episode_binding']
    assert lineage['research_context_ref']=={'case_ref':context['case_ref'],'context_sha256':context['published_context_sha256']}
    assert lineage['identity']['security_id']=='SEC:US-XNAS-MU'
    assert lineage['identity']['cik']==context['research_subject']['key']
    assert lineage['quote']['vendor_symbol']=='MU' and lineage['quote']['provider_identity_attestation']=='not_available'
    assert lineage['origin']['event_spool_recorded'] is True
    assert lineage['origin']['receipt_scope']=='ordinary_ledger_commit_not_spool_replay'
    assert context['candidate_quote_security_join']=='not_established'
    assert context['live_projection_eligible'] is lineage['live_projection_eligible'] is False
    assert lineage['rights_state']=='not_granted_by_provenance' and not any(lineage['authority'].values())
    wire=json.dumps(result)
    assert all(key not in wire for key in ('identity_read_receipt','event_spool_key','transition_spool_key',
                                         'candidate_context_binding','quote_recorded_at'))
    assert set(lineage['identity'])=={'security_id','issuer_id','cik','snapshot_sha256'}
    assert path.read_bytes()==before and set(live.iterdir())=={path}


@pytest.mark.parametrize('mutation',[
    'episode','cutoff','case_ref','context_hash','missing_link','null','top_body','quote_body','observation_body',
    'identity_body','receipt_body','origin_body','context_ref_body','authority','provider','namespace','symbol',
    'identity','snapshot','alias','alias_future','read_after_cutoff','receipt_lineage','late_admission','late_freeze',
    'late_composition','normalized_clock','rights','live','event','spool','pack_hash',
])
def test_rehashed_wrong_context_identity_clock_or_nested_body_refuses(published_lineage,mutation):
    live,path,source,episode=published_lineage
    row=source['episodes'][0];p=row['quote_candidate_provenance'];q=p['quote'];i=p['identity']
    if mutation=='episode':p['episode_binding']['canonical_sha256']='0'*64
    elif mutation=='cutoff':p['episode_binding']['candidate_at']='2026-10-07T14:05:00Z'
    elif mutation=='case_ref':p['research_context_ref']['case_ref']['case_id']='opc_'+'0'*64
    elif mutation=='context_hash':p['research_context_ref']['context_sha256']='0'*64
    elif mutation=='missing_link':p.pop('research_context_ref')
    elif mutation=='null':row['quote_candidate_provenance']=None
    elif mutation=='top_body':p['private_body']='DO_NOT_EXPORT'
    elif mutation=='quote_body':q['private_body']='DO_NOT_EXPORT'
    elif mutation=='observation_body':p['observation']['private_body']='DO_NOT_EXPORT'
    elif mutation=='identity_body':i['private_body']='DO_NOT_EXPORT'
    elif mutation=='receipt_body':i['identity_read_receipt']['private_body']='DO_NOT_EXPORT'
    elif mutation=='origin_body':p['origin']['private_body']='DO_NOT_EXPORT'
    elif mutation=='context_ref_body':p['research_context_ref']['private_body']='DO_NOT_EXPORT'
    elif mutation=='authority':p['authority']['can_rank']=True
    elif mutation=='provider':q['provider_identity_attestation']='authenticated'
    elif mutation=='namespace':q['response_field']='request.symbol'
    elif mutation=='symbol':q['vendor_symbol']='OTHER'
    elif mutation=='identity':i['security_id']='SEC:US-XNAS-OTHER'
    elif mutation=='snapshot':i['identity_snapshot_sha256']='0'*64
    elif mutation=='alias':i['alias_revision_id']='other/decision'
    elif mutation=='alias_future':i['alias_known_at_utc_ns']=str(int(datetime.fromisoformat('2026-10-07T14:05:00+00:00').timestamp()*1e9))
    elif mutation=='read_after_cutoff':
        ns=str(int(datetime.fromisoformat('2026-10-07T14:05:00+00:00').timestamp()*1e9))
        i['identity_read_receipt'].update(read_started_at_utc_ns=ns,read_completed_at_utc_ns=ns)
    elif mutation=='receipt_lineage':i['identity_read_receipt']['artifact_sha256']['security_master.parquet']='0'*64
    elif mutation=='late_admission':q['recorded_at']='2026-10-07T14:00:01Z'
    elif mutation=='late_freeze':p['observation']['recorded_at']='2026-10-07T14:05:00Z'
    elif mutation=='late_composition':p['composed_at']='2026-10-07T14:05:00Z'
    elif mutation=='normalized_clock':q['normalized_timestamp']='2026-10-07T13:59:11Z'
    elif mutation=='rights':p['rights_state']='display_ok'
    elif mutation=='live':p['live_projection_eligible']=True
    elif mutation=='event':p['origin']['event_id']='0'*16
    elif mutation=='spool':p['origin']['event_spool_key']='other-store/current.json'
    elif mutation=='pack_hash':p['observation']['pack_hash']='not-native-pack'
    if mutation!='null':rehash(p)
    path.write_text(json.dumps(source))
    for selection in (None,episode.episode_id):
        with pytest.raises(rr.ResearchReadUnavailable):rr.read_published_research(live,episode_id=selection)
    assert path.read_text()==json.dumps(source)


def test_legacy_context_stays_readable_without_lineage(published_lineage):
    live,path,source,episode=published_lineage
    source['episodes'][0].pop('quote_candidate_provenance');path.write_text(json.dumps(source))
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert result['state']=='published_context' and 'quote_lineage' not in result['case']
    assert result['case']['candidate_quote_security_join']=='not_established'


def test_standalone_quote_receipt_never_becomes_a_case(published_lineage):
    live,path,source,episode=published_lineage
    row=source['episodes'][0];row.pop('research_context');row['quote_candidate_provenance'].pop('research_context_ref')
    rehash(row['quote_candidate_provenance']);path.write_text(json.dumps(source))
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert result['state']=='unqualified' and result['case'] is None
    assert 'SEC:US-XNAS-MU' not in json.dumps(result)
