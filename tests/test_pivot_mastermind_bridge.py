import copy
import json
from datetime import datetime,timezone
import pytest
from engine.neuralweb.pivot_context import compose_pivot_context,compact_pivot_context
from engine.neuralweb.mastermind_context import _build_candidate_context

NOW="2026-11-05T22:00:00Z"

def context():
    return compose_pivot_context("ABC",[
        {"field":"coiled_fire","value":True,"source":"fixture","as_of":"2026-11-04","available_at":"2026-11-04T22:00:00Z"},
        {"field":"above200","value":False,"source":"fixture","as_of":"2026-11-04","available_at":"2026-11-04T22:00:00Z"}
    ],decision_at=NOW)


def tree(root,ctx):
    f=root/'site/factordata';f.mkdir(parents=True)
    (f/'us_standouts.json').write_text(json.dumps({'buy':[{'ticker':'ABC'}],'watch':[],'laggards':[]}))
    n=root/'site/neuralwebdata';n.mkdir(parents=True)
    (n/'bottom_sensors.json').write_text(json.dumps({'rows':[
        {'symbol':'ABC','bottom_state':'WATCH','coiled':True,'pivot_context':ctx},
        {'symbol':'NOT_IN_INTAKE','bottom_state':'WATCH','pivot_context':{**ctx,'symbol':'NOT_IN_INTAKE'}}]}))


def test_compact_context_preserves_false_vs_missing_and_no_authority():
    out=compact_pivot_context(context(),symbol='ABC',decision_at=NOW)
    assert out['observed']['coiled_fire'] is True
    assert out['observed']['above200'] is False
    assert 'knife_score' in out['unavailable']
    assert out['probability'] is None and out['action_authority']=='none'
    assert 'explanation' not in out
    assert len(json.dumps(out))<2200


def test_context_expires_at_actual_consumer_clock():
    out=compact_pivot_context(context(),symbol='ABC',decision_at='2026-11-20T22:00:00Z')
    assert out['quality']=='unavailable' and out['observed']=={}
    assert out['unavailable']['coiled_fire']=='stale'
    assert out['source_evaluated_at'] != out['consumer_evaluated_at']


@pytest.mark.parametrize('key,value',[('symbol','OTHER'),('schema','wrong'),('probability',.8),('action_authority','trade'),('is_display_only',False),('decision_at','2026-11-06T23:00:00Z')])
def test_malformed_or_promoted_context_is_not_imported(key,value):
    ctx=context();ctx[key]=value
    assert compact_pivot_context(ctx,symbol='ABC',decision_at=NOW) is None


def test_original_future_evidence_cannot_be_reborn_later():
    ctx=context()
    for e in ctx['evidence']:
        if e['field']=='coiled_fire':e['available_at']='2026-11-06T22:00:00Z'
    out=compact_pivot_context(ctx,symbol='ABC',decision_at='2026-11-07T22:00:00Z')
    assert 'coiled_fire' not in out['observed'] and out['unavailable']['coiled_fire']=='future'


def test_existing_brain_bridge_consumes_same_contract_without_new_names(tmp_path):
    ctx=context();before=copy.deepcopy(ctx);tree(tmp_path,ctx)
    out=_build_candidate_context(tmp_path,[],now=datetime(2026,11,5,22,tzinfo=timezone.utc))
    assert set(out)=={'ABC'}
    assert out['ABC']['pivot_evidence']['observed']['above200'] is False
    assert out['ABC']['allowed_behavior']=='annotate_only'
    assert ctx==before


def test_missing_context_does_not_create_a_fake_evidence_block(tmp_path):
    tree(tmp_path,{})
    out=_build_candidate_context(tmp_path,[],now=datetime(2026,11,5,22,tzinfo=timezone.utc))
    assert 'pivot_evidence' not in out['ABC']


def test_duplicate_envelope_fields_are_not_silently_selected():
    ctx=context();ctx['evidence'].append(dict(ctx['evidence'][0]))
    assert compact_pivot_context(ctx,symbol='ABC',decision_at=NOW) is None


def test_malformed_limitation_list_does_not_abort_brain_build():
    ctx=context();ctx['limitations']=None
    assert compact_pivot_context(ctx,symbol='ABC',decision_at=NOW)['quality']=='partial'


def test_compact_full_field_budget_for_250_candidates():
    vals={'trigger_tier':'T1','trigger_age_ticks':10,'coiled':True,'star':False,'coiled_fire':True,
          'above200':False,'hold_state':'x'*80,'hold_days_basing':10,'hold_ret_since_anchor_pct':1.1,
          'knife_score':.2,'dist_21d_low_pct':1.2,'dist_126d_high_pct':21.0,'sponsorship_state':'x'*80}
    ctx=compose_pivot_context('ABC',[{'field':k,'value':v,'source':'fixture','as_of':'2026-11-04',
        'available_at':'2026-11-04T22:00:00Z'} for k,v in vals.items()],decision_at=NOW)
    out=compact_pivot_context(ctx,symbol='ABC',decision_at=NOW)
    assert len(json.dumps(out,separators=(',',':')).encode()) < 1100
    # This is an incremental block budget, not a claim that all other lobes fit.
    assert len(json.dumps(out,separators=(',',':')).encode())*250 < 275000


def test_briefing_budget_preserves_all_legacy_candidates_and_explicit_coverage():
    from engine.neuralweb.mastermind_context import _bound_pivot_evidence,CONTEXT_SIZE_CAP_BYTES
    compact=compact_pivot_context(context(),symbol='ABC',decision_at=NOW)
    candidates={f'T{i:03}':{'legacy':'present','pivot_evidence':copy.deepcopy(compact)} for i in range(250)}
    payload={'candidate_context':candidates,'gap_notes':[],'large_existing_lobe':'x'*275000}
    _bound_pivot_evidence(payload)
    assert len(payload['candidate_context'])==250
    assert all(r['legacy']=='present' for r in candidates.values())
    coverage=payload['pivot_evidence_coverage']
    assert 0 < coverage['included'] < 250
    assert coverage['included']+coverage['omitted_for_size']==250
    assert len(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()) <= CONTEXT_SIZE_CAP_BYTES-4000
    assert coverage['selection']=='symbol_order_not_signal_rank'
    assert any('limited by briefing size' in g for g in payload['gap_notes'])


def test_no_pivot_payload_is_byte_unchanged_by_budgeting():
    from engine.neuralweb.mastermind_context import _bound_pivot_evidence
    payload={'candidate_context':{'ABC':{'bottom':{'coiled':True}}},'gap_notes':[]}
    before=copy.deepcopy(payload);_bound_pivot_evidence(payload)
    assert payload==before


def test_small_briefing_keeps_all_pivot_evidence():
    from engine.neuralweb.mastermind_context import _bound_pivot_evidence
    pivot=compact_pivot_context(context(),symbol='ABC',decision_at=NOW)
    payload={'candidate_context':{'ABC':{'pivot_evidence':pivot}},'gap_notes':[]}
    _bound_pivot_evidence(payload)
    assert payload['candidate_context']['ABC']['pivot_evidence']==pivot
    assert payload['pivot_evidence_coverage']['omitted_for_size']==0
    assert not payload['gap_notes']
