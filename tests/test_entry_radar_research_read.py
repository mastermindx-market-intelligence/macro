"""Native synthetic payload composition; no live run or ledger mutation."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from engine.entry_radar import live_eval as le
from engine.entry_radar import research_read as rr
from tests.test_entry_radar_w4_live import _synthetic_research_case
from tests.test_entry_radar_w4_ledger import ledger_with_candidate
from tests.test_entry_radar_earnings_context_producer import prepared, generation
from tests.test_entry_radar_quote_context import native
from tests.test_earnings_opportunity_qualification import inputs


@pytest.fixture
def published(tmp_path):
    ledger, _, _ = ledger_with_candidate(tmp_path / 'ledger')
    episode = next(e for e in ledger.episodes if e.state == 'CANDIDATE')
    case = _synthetic_research_case(episode)
    row = episode.to_dict()
    row['research_case'] = le._project_opportunity_case(case, row, now=episode.candidate_at)
    value = {'schema':'entry_radar.live/v1','asof':episode.candidate_at,
             'episodes':[row], 'authority':le._authority_block(),
             'health':{'state':'live','pass':{'at':episode.candidate_at}}}
    live = tmp_path / 'live';live.mkdir()
    path = live / 'entry_radar.json';path.write_text(json.dumps(value))
    return live, path, value, episode


def test_reads_exact_published_generation_and_candidate_without_writing(published):
    live,path,_,episode=published
    before=path.read_bytes()
    listing=rr.read_published_research(live)
    assert listing['candidate_count']==1 and listing['ordering']=='native_episode_id_not_priority'
    assert listing['candidates'][0]['episode_id']==episode.episode_id
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert result['state']=='published_case'
    assert result['case']['episode_binding']['candidate_at']==episode.candidate_at
    assert result['case']['evidence_refs'][0]['provenance']['body_embedded'] is False
    assert result['source']['asof']==episode.candidate_at
    assert result['source']['freshness_state']=='owner_reported_only'
    assert path.read_bytes()==before and set(p.name for p in live.iterdir())=={'entry_radar.json'}
    assert le.forward_knowledge_keys(result['case'])==[]


def test_missing_case_is_unqualified_not_fabricated_or_silently_empty(published):
    live,path,value,episode=published
    value['episodes'][0].pop('research_case');path.write_text(json.dumps(value))
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert result['state']=='unqualified' and result['case'] is None
    with pytest.raises(rr.ResearchReadUnavailable,match='^candidate_not_found$'):
        rr.read_published_research(live,episode_id='other')


@pytest.mark.parametrize('mutation',['digest','episode','authority','case_hash','case_schema','duplicate','future','naive','clock_mismatch','body','terminal'])
def test_refuses_broken_native_binding(published,mutation):
    live,path,value,episode=published
    row=value['episodes'][0];projection=row['research_case']
    if mutation=='digest':projection['episode_binding']['canonical_sha256']='0'*64
    elif mutation=='episode':row['ticker']='OTHER'
    elif mutation=='authority':projection['authority']['can_rank']=True
    elif mutation=='case_hash':projection['case_ref']['sha256']='not-a-hash'
    elif mutation=='case_schema':projection['schema']='invented'
    elif mutation=='duplicate':value['episodes'].append(deepcopy(row))
    elif mutation=='future':value['asof']='2099-01-01T00:00:00Z';value['health']['pass']['at']=value['asof']
    elif mutation=='naive':value['asof']=value['asof'].split('+')[0].rstrip('Z')
    elif mutation=='clock_mismatch':value['health']['pass']['at']='2026-01-01T00:00:00Z'
    elif mutation=='body':projection['evidence_refs'][0]['provenance']['body_embedded']=True
    else:row['state']='RESOLVED'
    path.write_text(json.dumps(value))
    with pytest.raises(rr.ResearchReadUnavailable):rr.read_published_research(live,episode_id=episode.episode_id)


@pytest.mark.parametrize('mode',['missing','symlink','oversize','duplicate_key','nonfinite','directory'])
def test_native_file_refusals_are_bounded(published,mode,monkeypatch):
    live,path,_,episode=published
    if mode=='missing':path.unlink()
    elif mode=='symlink':
        original=path.with_name('original.json');path.rename(original);path.symlink_to(original)
    elif mode=='oversize':monkeypatch.setattr(rr,'MAX_BYTES',1)
    elif mode=='duplicate_key':path.write_text('{"schema":1,"schema":2}')
    elif mode=='nonfinite':path.write_text('{"x":NaN}')
    else:path.unlink();path.mkdir()
    with pytest.raises(rr.ResearchReadUnavailable):rr.read_published_research(live,episode_id=episode.episode_id)


def test_bad_selection_never_reads(monkeypatch,tmp_path):
    monkeypatch.setattr(rr,'_read',lambda _:pytest.fail('read before selection validation'))
    with pytest.raises(rr.ResearchReadUnavailable,match='^invalid_episode_selection$'):
        rr.read_published_research(tmp_path,episode_id='../../secret')


@pytest.mark.parametrize('field',['private_body','can_rank','grant_token'])
def test_nested_context_fields_are_never_exported(published,field):
    live,path,value,episode=published
    for context in ('company_context','transmission'):
        value['episodes'][0]['research_case'][context][field]={'sentinel':'DO_NOT_EXPORT'}
    path.write_text(json.dumps(value))
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert 'DO_NOT_EXPORT' not in json.dumps(result)
    assert set(result['case']['company_context'])=={'state'}


@pytest.mark.parametrize('field',['provenance','native_digest','rights','freshness','clocks'])
def test_nested_evidence_objects_are_recursively_closed(published,field):
    live,path,value,episode=published
    target=value['episodes'][0]['research_case']['evidence_refs'][0][field]
    if isinstance(target,list):target=target[0]
    target['private_body']='DO_NOT_EXPORT'
    path.write_text(json.dumps(value))
    for selected in (None,episode.episode_id):
        with pytest.raises(rr.ResearchReadUnavailable):
            rr.read_published_research(live,episode_id=selected)


@pytest.fixture
def published_context(prepared,tmp_path):
    from engine.entry_radar.earnings_context import attach_retrospective_earnings_context
    payload,pack,_=prepared
    report=attach_retrospective_earnings_context(payload,pack=pack,
        identity_directory=tmp_path/'reference',committed=True)
    assert report['attached']==1,report
    payload['authority']=le._authority_block()
    payload['health']['pass']={'at':payload['asof']}
    live=tmp_path/'context-live';live.mkdir()
    path=live/'entry_radar.json';path.write_text(json.dumps(payload))
    episode=rr._episode(payload['episodes'][0])
    return live,path,payload,episode


def test_reads_real_producer_projection_as_retrospective_not_live_case(published_context):
    live,path,_,episode=published_context;before=path.read_bytes()
    listing=rr.read_published_research(live)
    assert listing['candidates'][0]['research_state']=='retrospective_context'
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert result['state']=='published_context'
    case=result['case']
    assert case['observation']['value']==1234 and case['observation']['unit']=='usd_millions'
    assert case['composed_at']>case['evidence_cutoff']
    assert case['live_projection_eligible'] is False
    assert case['candidate_quote_security_join']=='not_established'
    assert 'candidate_context_binding' not in case
    assert 'identity_read_receipt' not in json.dumps(result)
    assert path.read_bytes()==before


@pytest.mark.parametrize('mutation',['hash','future_composition','before_cutoff','quote_join','live','private_observation','private_metadata','issuer','generation','binding','document_body','span_body','future_evidence','clock_order','period','date_without_end','different_fiscal'])
def test_retrospective_context_refuses_cross_binding_clock_and_body_errors(published_context,mutation):
    from hashlib import sha256
    from lib.evidence_foundation import canonical_json_bytes
    live,path,value,episode=published_context
    c=value['episodes'][0]['research_context']
    if mutation=='future_composition':c['composed_at']='2099-01-01T00:00:00Z'
    elif mutation=='before_cutoff':c['composed_at']='2026-10-01T00:00:00Z'
    elif mutation=='quote_join':c['candidate_quote_security_join']='established'
    elif mutation=='live':c['live_projection_eligible']=True
    elif mutation=='private_observation':c['observation']['private_body']='DO_NOT_EXPORT'
    elif mutation=='private_metadata':c['evidence_refs'][0]['provenance']['private_body']='DO_NOT_EXPORT'
    elif mutation=='issuer':c['research_subject']['key']='0000320193'
    elif mutation=='generation':c['native_earnings_identity']['generation_id']='0'*24
    elif mutation=='binding':c['candidate_context_binding']['ticker']='SPY'
    elif mutation=='document_body':c['observation']['document_id']='PRIVATE BODY SENTINEL: source text'
    elif mutation=='span_body':c['observation']['span_id']='PRIVATE BODY SENTINEL: source text'
    elif mutation=='future_evidence':c['evidence_refs'][0]['clocks'][2]['value']='2099-01-01T00:00:00Z'
    elif mutation=='clock_order':c['evidence_refs'][0]['clocks'][1]['value']='2026-10-01T00:00:00Z'
    elif mutation=='period':c['observation']['period']='2026Q2'
    elif mutation=='date_without_end':c['observation']['period']='2026-06-27'
    elif mutation=='different_fiscal':c['fiscal_period']['quarter']=2
    c['sha256']=sha256(canonical_json_bytes({k:v for k,v in c.items() if k!='sha256'})).hexdigest()
    if mutation=='hash':c['sha256']='0'*64
    path.write_text(json.dumps(value))
    for selection in (None,episode.episode_id):
        with pytest.raises(rr.ResearchReadUnavailable):rr.read_published_research(live,episode_id=selection)


def test_calendar_date_requires_explicit_native_fiscal_end(published_context):
    from hashlib import sha256
    from lib.evidence_foundation import canonical_json_bytes
    live,path,value,episode=published_context
    c=value['episodes'][0]['research_context']
    c['fiscal_period']['calendar_end']='2026-06-27'
    c['observation']['period']='2026-06-27'
    c['sha256']=sha256(canonical_json_bytes({k:v for k,v in c.items() if k!='sha256'})).hexdigest()
    path.write_text(json.dumps(value))
    result=rr.read_published_research(live,episode_id=episode.episode_id)
    assert result['case']['observation']['period']=='2026-06-27'
