"""Synthetic source-contract checks; no current publication/eligibility claim."""
import copy
import datetime as dt
import hashlib
import json

import pandas as pd
import pytest

from engine import foresight_divergence as owner
from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import theme_state_gap as gap, theme_state_use_reader as reader
from tests.test_theme_state_production import production_world, compose  # noqa: F401

DAY = '2026-10-03'
KNOWN = '2026-10-04T12:00:00Z'
USE = '2026-10-04T13:00:00Z'


def rows():
    return [dict(theme='grid',asof='2026-08-05',ts='2026-08-05T07:45:58Z',
        row_type='observation',quadrant='hidden-opportunity',members=['A','B'],
        n_narrative_legs_live=2,n_money_legs_live=2),
        dict(theme='grid',asof='2026-08-08',ts='2026-08-08T15:28:59Z',
        row_type='transition',quadrant='confirmed',members=['B','C','D'],
        n_narrative_legs_live=2,n_money_legs_live=1)]


def leg_for(data=None):
    data=rows() if data is None else data
    raw='\n'.join(json.dumps(row) for row in data).encode()
    source=dict(path=gap.SOURCE_PATH,sha256=hashlib.sha256(raw).hexdigest(),availability='AVAILABLE',null_reason=None)
    records=[adapter._production_record('divergence_log',row,pos,data,source,DAY,KNOWN)
             for pos,row in enumerate(data)]
    from engine.theme_graph import theme_state_production as p
    return dict(source_ref=source,observed_at=KNOWN,
        scope=dict(status='EXACT_OWNER_SCOPE',selectors=['grid']),records=records,conflicts=p.divergence_conflicts(records),
        presence='AVAILABLE',coverage=dict(completeness='UNPROVEN'),
        qualification=dict(status='UNQUALIFIED',source_receipt=None,historical_knowability='UNPROVEN',
            identity_membership='NOT_APPLICABLE',rights=dict(status='UNAVAILABLE',family=None,
                purpose='research_internal',null_reason='SOURCE_FAMILY_PURPOSE_BINDING_UNAVAILABLE')))


def invoke(leg=None,**kw):
    args=dict(subject_id='theme:grid',flag_asof='2026-08-05',effective_at=DAY,known_at=KNOWN,use_at=USE)
    args.update(kw)
    return gap.compose_divergence_gap(leg_for() if leg is None else leg,**args)


def assert_limits(result):
    assert result['public_display_allowed'] is False and result['materialization_allowed'] is False
    assert not any(result['authority_caps'].values())
    assert result['limits']['current_eligibility']=='NOT_QUALIFIED'
    assert result['limits']['historical_availability']=='UNPROVEN'


@pytest.mark.parametrize('target,expected',[('2026-08-05',False),('2026-08-06',True),('2026-10-04',True),('2026-10-05',False)])
def test_shared_owner_predicate_is_exact_original_calendar_rule(target,expected):
    data=[{'asof':target,'quadrant':'confirmed'}]
    flag=pd.Timestamp('2026-08-05');cutoff=flag+pd.Timedelta(days=60)
    old=any(e.get('quadrant')=='confirmed' for e in data if e.get('asof') and flag<pd.Timestamp(e['asof'])<=cutoff)
    assert owner.CATCHUP_DAYS==60
    assert owner.catchup_observed('2026-08-05',data) is old is expected


def test_shared_owner_any_short_circuit_is_conserved():
    assert owner.catchup_observed('2026-08-05',[{'asof':'2026-08-08','quadrant':'confirmed'},
                                               {'asof':'invalid','quadrant':'confirmed'}]) is True


def test_positive_native_target_preserves_clock_hash_cohort_and_live_leg_change():
    leg=leg_for();result=invoke(leg)
    assert result['status']=='OBSERVED_CATCHUP',result
    assert result['source_observed_at']==KNOWN
    assert result['flag']['recorded_at']=='2026-08-05T07:45:58Z'
    assert result['flag']['record_id']==leg['records'][0]['record_id']
    assert result['input_refs']['divergence_log']['sha256']==leg['source_ref']['sha256']
    assert result['targets'][0]['cohort_change']==dict(same_member_set=False,added_count=2,removed_count=1,
        narrative_leg_delta=0,money_leg_delta=-1)
    assert result['targets'][0]['members']==['B','C','D']
    assert result['source_purpose']['public_grant']=='NOT_ESTABLISHED'
    assert result['window']['end_inclusive']=='2026-10-04'
    assert_limits(result)


@pytest.mark.parametrize('day',['2026-08-06','2026-10-04','2026-10-05','2026-10-19'])
def test_sparse_absence_never_becomes_failure_or_expiry(day):
    # Match the actual observed read clock, not the old flag's append time.
    leg=leg_for(rows()[:1]);leg['observed_at']='2026-10-20T12:00:00Z'
    result=invoke(leg,effective_at=day,known_at=leg['observed_at'],use_at='2026-10-20T13:00:00Z')
    assert result['status']=='INSUFFICIENT_COVERAGE'
    assert result['coverage']['negative_inference_allowed'] is False
    assert result['reason_codes']==['SPARSE_HISTORY_DOES_NOT_ESTABLISH_NON_CATCHUP']
    assert_limits(result)


@pytest.mark.parametrize('mutation',[lambda r:r.pop('ts'),lambda r:r.update(ts='2026-08-08T15:28:59'),
    lambda r:r.update(ts='2026-10-05T00:00:00Z'),lambda r:r.update(recorded_at='2026-08-09T00:00:00Z'),
    lambda r:r.update(members=['B','B']),lambda r:r.update(n_money_legs_live=0)])
def test_unproven_target_metadata_cannot_witness_catchup(mutation):
    data=rows();mutation(data[1]);result=invoke(leg_for(data))
    assert result['status']=='INSUFFICIENT_COVERAGE'
    assert result['coverage']['unproven_target_records']==1
    assert not result['targets']


@pytest.mark.parametrize('change',[lambda leg:leg['source_ref'].update(sha256='0'*64),
    lambda leg:leg['scope'].update(selectors=['travel']),lambda leg:leg.update(observed_at='2026-10-05T00:00:00Z'),
    lambda leg:leg['records'][0]['value'].update(ts='2026-08-05T08:00:00Z')])
def test_hash_theme_read_clock_or_record_mutation_refuses(change):
    leg=leg_for();change(leg)
    assert invoke(leg)['status']=='UNAVAILABLE'


def test_duplicate_native_flags_refuse_without_latest_wins():
    data=rows();data.append(copy.deepcopy(data[0]))
    assert invoke(leg_for(data))['reason_codes']==['NATIVE_HISTORY_CONFLICT']


def test_purpose_promotion_and_unknown_initiating_clock_refuse():
    leg=leg_for();leg['qualification']['rights']['status']='QUALIFIED'
    assert invoke(leg)['status']=='UNAVAILABLE'
    data=rows();data[0].pop('ts')
    assert invoke(leg_for(data))['status']=='UNAVAILABLE'


def test_ts_mapping_is_recording_only_not_knowledge_or_availability():
    record=leg_for()['records'][0]
    assert record['native_clocks']['recorded_at']['value']==rows()[0]['ts']
    assert record['native_clocks']['known_at']['value'] is None
    assert record['native_clocks']['available_at']['value'] is None


def test_existing_theme_state_use_seam_reads_same_native_leg(production_world):
    path=production_world/gap.SOURCE_PATH
    path.write_text('\n'.join(json.dumps(r) for r in rows())+'\n')
    _,result=compose(production_world)
    state=result['state'];before=copy.deepcopy(state)
    answer=reader.read_divergence_gap_at_use(state,node_id='theme:grid',flag_asof='2026-08-05',
        effective_at=DAY,known_at=KNOWN,use_at=USE)
    assert answer['status']=='OBSERVED_CATCHUP'
    assert answer['state_ref']['state_sha256']==state['state_sha256']
    assert state==before
    assert_limits(answer)
    denied=reader.read_divergence_gap_at_use(state,node_id='theme:grid',flag_asof='2026-08-05',
        effective_at=DAY,known_at=KNOWN,use_at=USE,purpose='public_display')
    assert denied['status']=='UNAVAILABLE' and denied['flag'] is None


def test_native_read_uses_same_leg_without_full_bundle_or_price_identity_io(production_world,monkeypatch):
    path=production_world/gap.SOURCE_PATH;path.write_text('\n'.join(json.dumps(r) for r in rows())+'\n')
    before={p:p.read_bytes() for p in production_world.rglob('*') if p.is_file()}
    def forbidden(*a,**kw): raise AssertionError('unrelated owner/grade I/O')
    monkeypatch.setattr(adapter,'capture_owner_bundle',forbidden)
    monkeypatch.setattr(adapter.identity_resolution,'resolve_graph_node_identity',forbidden)
    monkeypatch.setattr(owner,'grade_divergence_ledger',forbidden)
    answer=reader.read_native_divergence_gap(production_world,node_id='theme:grid',flag_asof='2026-08-05',effective_at=DAY)
    assert answer['status']=='OBSERVED_CATCHUP',answer
    assert answer['state_ref'] is None
    assert set(answer['input_refs'])=={'divergence_log','theme_crosswalk','rights_registry'}
    assert answer['source_observed_at']=='2026-10-04T11:00:00Z'
    assert before=={p:p.read_bytes() for p in production_world.rglob('*') if p.is_file()}
    assert_limits(answer)


def test_public_purpose_refuses_before_native_io(monkeypatch):
    monkeypatch.setattr(adapter,'capture_native_divergence_leg',lambda *a,**k:pytest.fail('purpose denied before I/O'))
    answer=reader.read_native_divergence_gap('/missing',node_id='theme:grid',flag_asof='2026-08-05',
                                              effective_at=DAY,purpose='private_product')
    assert answer['status']=='UNAVAILABLE' and answer['input_refs']=={}


def test_gap_projection_does_not_forward_arbitrary_source_or_context_fields():
    leg=leg_for();leg['qualification']['rights']['native_read']={'private_body':'SENTINEL','registry_sha256':'a'*64}
    ref={**leg['source_ref'],'private_body':'SENTINEL'}
    result=invoke(leg,input_refs={'divergence_log':ref,'private_context':{'body':'SENTINEL'}})
    assert result['status']=='OBSERVED_CATCHUP'
    assert 'SENTINEL' not in json.dumps(result)
    assert result['source_purpose']['registry_sha256']=='a'*64


def test_input_reference_cannot_rebind_source_hash_or_forward_nested_registry_metadata():
    leg=leg_for()
    assert invoke(leg,input_refs={'divergence_log':{**leg['source_ref'],'sha256':'f'*64}})['status']=='UNAVAILABLE'
    leg['qualification']['rights']['native_read']={'registry_sha256':{'private_body':'SENTINEL'}}
    answer=invoke(leg)
    assert answer['status']=='UNAVAILABLE' and 'SENTINEL' not in json.dumps(answer)


def test_native_read_resource_bound_refuses_whole_population(production_world):
    path=production_world/gap.SOURCE_PATH;path.write_bytes(b' '*(8*1024*1024+1))
    with pytest.raises(ValueError,match='resource bound'):
        adapter.capture_native_divergence_leg(production_world,node_id='theme:grid',effective_at=DAY)


def test_native_theme_selection_does_not_fall_back_to_basket_or_local_theme(production_world):
    for node in ['basket:baskets:grid','ltheme:finviz:grid','theme:unknown']:
        with pytest.raises(ValueError,match='exact canonical native theme'):
            adapter.capture_native_divergence_leg(production_world,node_id=node,effective_at=DAY)


def test_native_read_refuses_race_root_mismatch_and_past_or_future_cutoff(production_world,monkeypatch):
    path=production_world/gap.SOURCE_PATH;path.write_text('\n'.join(json.dumps(r) for r in rows())+'\n')
    with pytest.raises(ValueError,match='configured owner data root'):
        adapter.capture_native_divergence_leg(production_world.parent,node_id='theme:grid',effective_at=DAY)
    for cutoff in ['2026-10-03T00:00:00Z','2026-10-05T00:00:00Z']:
        with pytest.raises(ValueError,match='actual observation cutoff'):
            adapter.capture_native_divergence_leg(production_world,node_id='theme:grid',effective_at=DAY,known_at=cutoff)
    original=adapter._bound_rights_read
    def race(*args,**kwargs):
        answer=original(*args,**kwargs);path.write_text(path.read_text()+'\n');return answer
    monkeypatch.setattr(adapter,'_bound_rights_read',race)
    with pytest.raises(ValueError,match='source changed'):
        adapter.capture_native_divergence_leg(production_world,node_id='theme:grid',effective_at=DAY)
