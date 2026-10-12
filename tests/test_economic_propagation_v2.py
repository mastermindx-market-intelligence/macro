"""Local candidate tests: full native composer, exact old fixtures, no live admission."""
import copy
import itertools
import json
from pathlib import Path
import pytest
from lib import economic_propagation_v2 as ep2
from lib import economic_propagation as native_ep

V2_ROOT = Path(__file__).resolve().parents[1]
V2_FIXTURES = V2_ROOT / 'tests/fixtures/economic_propagation'
V2_BASE = json.loads((V2_FIXTURES / 'golden_supported_hypothesis.json').read_bytes())
# Independent declared admissible-combination oracle, not derived from code tables.
V2_EXPECTED = {
 'demand_transfer': ('revenue','volume','backlog_orders','capacity_utilization'),
 'supply_constraint': ('volume','capacity_utilization','gross_margin','operating_margin','input_cost','revenue'),
 'pricing_power_shift': ('pricing','gross_margin','operating_margin','market_share'),
 'input_cost_shift': ('input_cost','gross_margin','operating_margin'),
 'capacity_reallocation': ('volume','capacity_utilization','backlog_orders','revenue'),
 'share_shift_competitive': ('market_share','volume','revenue'),
 'regulatory_exposure': ('volume','revenue','gross_margin','operating_margin','input_cost'),
 'program_funding_flow': ('backlog_orders','revenue','volume'),
 'common_end_market_demand': ('volume','revenue','pricing','backlog_orders','capacity_utilization'),
}
V2_COMBOS = [(m,k,d) for m,metrics in V2_EXPECTED.items() for k in metrics for d in ('improves','deteriorates','mixed')]
V2_ALT_CLASSES = ('common_cause_macro','sector_factor','narrative_similarity_only','market_sympathy_only','liquidity_flow_technical','coincident_timing')
V2_BAD_TEXT = (
 'Recommend overweighting BETA.',
 'This is bullish; accumulate exposure and hedge the position.',
 'The tariff causes BETA margins to compress by 300 basis points.',
 'BETA accounts for 42% of ACME revenue, so BETA volumes fall.',
 'Plain operating commentary that is not the adopted generated sentence.',
 '<script>arbitrary source text</script>',
)
V2_SLOTS = ('mechanism','alternative','condition','observable','expiry')

def v2_kwargs():
 keys=('source_event','target','asof','compiled_at','generator_admissions','relationship_paths','similarity_evidence','market_evidence')
 kw={k:copy.deepcopy(V2_BASE[k]) for k in keys}
 kw.update(mechanism_spec={'mechanism_class':'demand_transfer','predicted_operating_direction':'improves','operating_metric_class':'revenue'}, alternative_classes=['sector_factor'],review_by=V2_BASE['expiry']['review_by'])
 return kw

def v2_make(): return ep2.compose_hypothesis_v2(**v2_kwargs())
def v2_rehash(record):
 record=copy.deepcopy(record);record['content_sha256']=ep2.content_sha256(record);return record

def v2_set_text(record,slot,text):
 if slot=='mechanism':record['mechanism']['hypothesis_text']=text
 elif slot=='alternative':record['alternatives'][0]['text']=text
 elif slot=='condition':record['falsifiers'][0]['condition']=text
 elif slot=='observable':record['falsifiers'][0]['observable']=text
 elif slot=='expiry':record['expiry']['note']=text
 else:raise AssertionError(slot)

@pytest.mark.parametrize('mechanism,metric,direction',V2_COMBOS)
def test_v2_each_declared_combination_has_valid_conditional_narrative(mechanism,metric,direction):
 kw=v2_kwargs();kw['mechanism_spec']={'mechanism_class':mechanism,'predicted_operating_direction':direction,'operating_metric_class':metric}
 before=copy.deepcopy(kw);record=ep2.compose_hypothesis_v2(**kw)
 assert ep2.validate_hypothesis_v2(record)==[]
 assert record['schema']=='economic_propagation.propagation_hypothesis/v2' and type(record['version']) is int and record['version']==2
 assert record['construction_profile']=='compiler_owned_qualitative.v1'
 assert record['mechanism']['hypothesis_text'].startswith('If ')
 assert record['mechanism']['hypothesis_text'].endswith('This is a qualitative operating hypothesis, not a measured effect.')
 assert record['mechanism']['operating_metric_class']==metric
 assert record['economic_share'] is None and record['authority']==V2_BASE['authority']
 assert record['binding_kills']==V2_BASE['binding_kills']
 assert kw==before and ep2.compose_hypothesis_v2(**kw)==record

@pytest.mark.parametrize('field',('hypothesis_text','approved','confidence','weight','economic_share','source_text'))
def test_v2_no_caller_prose_or_approval_slot(field):
 kw=v2_kwargs();kw['mechanism_spec'][field]='safe' if field=='hypothesis_text' else True
 with pytest.raises(ep2.EconomicPropagationError,match='K3D_V2_MECHANISM_SPEC'):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('slot',V2_SLOTS)
@pytest.mark.parametrize('text',V2_BAD_TEXT)
def test_v2_rehashed_narrative_injection_is_rejected(slot,text):
 record=v2_make();v2_set_text(record,slot,text);record=v2_rehash(record)
 findings=ep2.validate_hypothesis_v2(record)
 assert 'K3D_V2_R010' in {f.code for f in findings}
 assert 'K3D_V2_R081' not in {f.code for f in findings}  # not a stale-hash test

@pytest.mark.parametrize('alternative',V2_ALT_CLASSES)
def test_v2_each_bounded_alternative_is_generated(alternative):
 kw=v2_kwargs();kw['alternative_classes']=[alternative];record=ep2.compose_hypothesis_v2(**kw)
 assert ep2.validate_hypothesis_v2(record)==[]
 assert record['alternatives'][0]['explanation_class']==alternative
 assert record['alternatives'][0]['text']!=alternative

@pytest.mark.parametrize('classes',[[],['other_disclosed'],['sector_factor']*2,['buy'],['sector_factor',None],'sector_factor',{},[1]])
def test_v2_unknown_or_unqualified_alternatives_refuse(classes):
 kw=v2_kwargs();kw['alternative_classes']=classes
 with pytest.raises(ep2.EconomicPropagationError):ep2.compose_hypothesis_v2(**kw)

def test_v2_alternative_order_is_canonical_not_a_rank():
 a=v2_kwargs();a['alternative_classes']=list(V2_ALT_CLASSES)
 b=copy.deepcopy(a);b['alternative_classes'].reverse()
 assert ep2.compose_hypothesis_v2(**a)==ep2.compose_hypothesis_v2(**b)
 record=ep2.compose_hypothesis_v2(**a);record['alternative_classes'].reverse();record=v2_rehash(record)
 assert 'K3D_V2_R010' in {f.code for f in ep2.validate_hypothesis_v2(record)}

@pytest.mark.parametrize('key,value',[('mechanism_class','ownership_weight'),('mechanism_class','RELATED'),('operating_metric_class','stock_price'),('operating_metric_class','economic_share'),('predicted_operating_direction','buy'),('predicted_operating_direction','up'),('predicted_operating_direction',True)])
def test_v2_unknown_mechanism_dimension_refuses(key,value):
 kw=v2_kwargs();kw['mechanism_spec'][key]=value
 with pytest.raises(ep2.EconomicPropagationError):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('mechanism,metric',[(m,k) for m in V2_EXPECTED for k in ('revenue','volume','pricing','gross_margin','operating_margin','backlog_orders','capacity_utilization','input_cost','market_share') if k not in V2_EXPECTED[m]])
def test_v2_unsupported_combination_does_not_get_generic_fallback(mechanism,metric):
 kw=v2_kwargs();kw['mechanism_spec'].update(mechanism_class=mechanism,operating_metric_class=metric)
 with pytest.raises(ep2.EconomicPropagationError,match='K3D_V2_UNSUPPORTED_COMBINATION'):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('state',['NOT_IN_MASTER','UNRESOLVED','CONFLICTING','UNSUPPORTED_MARKET','DEFERRED_IDENTITY_EXCEPTION','ENTITY_TYPE_CONFLICT'])
def test_v2_native_unresolved_states_still_abstain(state):
 kw=v2_kwargs();kw['source_event']['source_identity'].update(resolution_state=state,issuer_id=None,security_id=None)
 kw.update(generator_admissions=[],relationship_paths=[],similarity_evidence=[],market_evidence=[],mechanism_spec=None)
 record=ep2.compose_hypothesis_v2(**kw)
 assert ep2.validate_hypothesis_v2(record)==[] and record['hypothesis_state']=='abstained'
 assert record['relationship_paths']==[] and record['mechanism']['hypothesis_text'] is None
 assert record['source_event']['source_identity']['resolution_state']==state
 kw['mechanism_spec']=v2_kwargs()['mechanism_spec']
 with pytest.raises(ep2.EconomicPropagationError,match='K3D_V2_MECHANISM_NOT_ELIGIBLE'):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('state',['rights_blocked','stale','not_yet_knowable','superseded','coverage_insufficient'])
def test_v2_unusable_economic_evidence_cannot_generate_mechanism(state):
 kw=v2_kwargs();kw['relationship_paths'][0]['usability_state']=state
 with pytest.raises(ep2.EconomicPropagationError,match='K3D_V2_MECHANISM_NOT_ELIGIBLE'):ep2.compose_hypothesis_v2(**kw)
 kw['mechanism_spec']=None;record=ep2.compose_hypothesis_v2(**kw)
 assert ep2.validate_hypothesis_v2(record)==[] and record['hypothesis_state']=='abstained'
 assert record['relationship_paths'][0]['usability_state']==state
 assert record['abstention']['reasons']!=['no_graph1_evidence']

@pytest.mark.parametrize('field',['issuer_id','security_id'])
@pytest.mark.parametrize('value',[None,'',' ',0,False,[],{},'x'*121,'id\npart'])
def test_v2_false_resolved_source_cannot_reach_graph_derivation(field,value,monkeypatch):
 kw=v2_kwargs();kw['source_event']['source_identity'][field]=value
 def forbidden(*a,**k):raise AssertionError('graph derivation ran')
 monkeypatch.setattr(native_ep,'derive_graph_states',forbidden)
 with pytest.raises(ep2.EconomicPropagationError):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('leg',['generator_admissions','relationship_paths','similarity_evidence','market_evidence'])
def test_v2_future_known_inputs_preserve_native_clock_refusal(leg):
 kw=v2_kwargs();kw[leg][0]['known_at']='2026-08-21'
 with pytest.raises(ep2.EconomicPropagationError,match='K3D_R061'):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('field',['asof','review_by'])
@pytest.mark.parametrize('bad',['2026-02-30','2026-99-01','2026-08-20\n','2026-08-20T00:00:00Z','buy',None,1])
def test_v2_dates_cannot_be_prose_slots(field,bad):
 kw=v2_kwargs();kw[field]=bad
 with pytest.raises(ep2.EconomicPropagationError,match='K3D_V2_DATE'):ep2.compose_hypothesis_v2(**kw)

@pytest.mark.parametrize('field',['trading','ranking','gating','sizing','entry','originates_signals'])
def test_v2_authority_cannot_be_enabled(field):
 r=v2_make();r['authority'][field]=True;r=v2_rehash(r)
 assert ep2.validate_hypothesis_v2(r)

@pytest.mark.parametrize('tamper',['profile','economic_share','id','version','extra_field'])
def test_v2_profile_and_reserved_fields_are_not_caller_promotable(tamper):
 r=v2_make()
 if tamper=='profile':r['construction_profile']='approved_by_user'
 elif tamper=='economic_share':r['economic_share']=49
 elif tamper=='id':r['record_id']='eph2:'+'0'*16
 elif tamper=='version':r['version']=1
 else:r['reviewer_approved']=True
 assert ep2.validate_hypothesis_v2(v2_rehash(r))

@pytest.mark.parametrize('direction,expected',[('improves','decrease'),('deteriorates','increase'),('mixed','show mixed changes')])
def test_v2_cost_direction_is_not_inverted(direction,expected):
 kw=v2_kwargs();kw['mechanism_spec'].update(mechanism_class='input_cost_shift',operating_metric_class='input_cost',predicted_operating_direction=direction)
 r=ep2.compose_hypothesis_v2(**kw)
 assert 'input costs may '+expected+'.' in r['mechanism']['hypothesis_text']

def test_v2_ids_and_names_stay_untrusted_metadata_not_interpolated_claims():
 kw=v2_kwargs();kw['target']['requested_key']='<script>buy now</script>'
 kw['source_event']['event_id']='arbitrary analyst phrase 42 percent'
 r=ep2.compose_hypothesis_v2(**kw)
 prose=json.dumps([r['mechanism'],r['alternatives'],r['falsifiers'],r['expiry']])
 assert 'buy now' not in prose and '42 percent' not in prose and '<script>' not in prose
 assert r['target']['requested_key']==kw['target']['requested_key']  # provenance, not authenticated identity

def test_v2_alias_equivalence_uses_existing_target_identity_component():
 a=v2_kwargs();b=copy.deepcopy(a);b['target']['requested_key']='second caller alias'
 assert ep2.compose_hypothesis_v2(**a)['record_id']==ep2.compose_hypothesis_v2(**b)['record_id']
 b['target']['resolution']['security_id']='SEC-OTHER'
 assert ep2.compose_hypothesis_v2(**a)['record_id']!=ep2.compose_hypothesis_v2(**b)['record_id']

@pytest.mark.parametrize('path',sorted(V2_FIXTURES.glob('golden*.json')),ids=lambda p:p.stem)
def test_v2_does_not_relabel_or_rewrite_v1_archives(path):
 raw=path.read_bytes();r=json.loads(raw)
 assert ep2.validate_hypothesis(r)==[] and ep2.validate_hypothesis_v2(r)
 assert path.read_bytes()==raw and ep2.content_sha256(r)==r['content_sha256']

def test_v2_legacy_prose_cannot_gain_profile_by_rehash_and_version_change():
 r=v2_make()
 r['mechanism']['hypothesis_text']=V2_BASE['mechanism']['hypothesis_text']
 assert 'K3D_V2_R010' in {f.code for f in ep2.validate_hypothesis_v2(v2_rehash(r))}

@pytest.mark.parametrize('value',[None,[],1,True,'bad',float('nan'),{'version':2},object()])
def test_v2_validator_refuses_malformed_without_exception(value):
 assert ep2.validate_hypothesis_v2(value)

def test_v2_cycles_and_excessive_depth_are_bounded():
 cycle={};cycle['self']=cycle;assert ep2.validate_hypothesis_v2(cycle)[0].code=='K3D_V2_R000'
 deep={};p=deep
 for _ in range(30):p['x']={};p=p['x']
 assert ep2.validate_hypothesis_v2(deep)[0].code=='K3D_V2_R000'

@pytest.mark.parametrize('field,value',[('source_event','bad'),('target',[]),('generator_admissions',[None]),('relationship_paths',[{'construct':[]}]),('market_evidence','bad')])
def test_v2_malformed_native_input_refuses_before_legacy_lookup(field,value):
 kw=v2_kwargs();kw[field]=value
 with pytest.raises(ep2.EconomicPropagationError):ep2.compose_hypothesis_v2(**kw)

def test_v2_generated_sentences_have_no_unsupported_numbers():
 r=v2_make();prose=json.dumps([r['mechanism'],r['alternatives'],r['falsifiers'],r['expiry']['note']])
 assert not any(ch.isdigit() for ch in prose)
 assert 'missing disclosure alone does not resolve this test' in r['falsifiers'][0]['observable']

def test_v2_representative_exact_sentence_is_fixed_independently():
 assert v2_make()['mechanism']['hypothesis_text']==(
  "If a shift in demand between operating businesses occurs along the evidenced relationship, "
  "the target's revenue may increase. This is a qualitative operating hypothesis, not a measured effect."
 )

@pytest.mark.parametrize('field',['issuer_id','security_id'])
@pytest.mark.parametrize('value',[None,' ','\t'])
def test_v2_rehashed_false_source_identity_still_hits_native_validator(field,value):
 r=v2_make();r['source_event']['source_identity'][field]=value;r=v2_rehash(r)
 assert 'K3D_R015' in {f.code for f in ep2.validate_hypothesis_v2(r)}

@pytest.mark.parametrize('leg',['generator_admissions','relationship_paths','similarity_evidence','market_evidence'])
def test_v2_rehashed_future_evidence_cannot_bypass_native_validator(leg):
 r=v2_make();r[leg][0]['known_at']='2026-08-21';r=v2_rehash(r)
 assert 'K3D_R061' in {f.code for f in ep2.validate_hypothesis_v2(r)}

@pytest.mark.parametrize('state',['rights_blocked','stale','not_yet_knowable','superseded','coverage_insufficient'])
def test_v2_rehashed_unusable_leg_cannot_keep_supported_headline(state):
 r=v2_make();r['relationship_paths'][0]['usability_state']=state;r=v2_rehash(r)
 assert 'K3D_R051' in {f.code for f in ep2.validate_hypothesis_v2(r)}
