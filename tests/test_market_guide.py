"""Hermetic projection contracts. Synthetic records, not production/browser proof."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from lib.market_guide import GuideError, compile_guide, normalize, script_json

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / "research/reference_rethink_20260921/guide-presentation.json"


@pytest.fixture
def raw():
    return json.loads((ROOT / "tests/fixtures/market-guide/synthetic-source.json").read_text())


@pytest.fixture
def presentation(): return json.loads(PRESENTATION.read_text())


def compile_test(raw, presentation):
    # These stubs isolate the new pure projection. They are not the existing
    # production validator and are not claimed as validation of production data.
    return compile_guide(raw,presentation,validate_registry=lambda x:x['entries'],
                         validate_coverage=lambda x,e:(x.get('coverage_exceptions') or []))


def test_existing_validation_owners_are_required(raw,presentation):
    with pytest.raises(TypeError): compile_guide(raw,presentation)


def test_validation_order_and_exact_source(raw,presentation):
    calls=[]
    def validate(x): calls.append('registry');assert x==raw;return x['entries']
    def coverage(x,e): calls.append('coverage');assert e==raw['entries'];return x['coverage_exceptions']
    compile_guide(raw,presentation,validate_registry=validate,validate_coverage=coverage)
    assert calls==['registry','coverage']


def test_owner_rejection_never_becomes_a_success_artifact(raw,presentation):
    def reject(x): raise RuntimeError('owner anchor is hidden')
    with pytest.raises(RuntimeError,match='owner anchor'):
        compile_guide(raw,presentation,validate_registry=reject,validate_coverage=lambda *_:pytest.fail('must not run'))


def test_projection_does_not_mutate_inputs(raw,presentation):
    saved=copy.deepcopy((raw,presentation));out=compile_test(raw,presentation)
    out['entries'][0]['aliases']['en'].append('changed')
    assert (raw,presentation)==saved


def test_all_source_rows_and_full_disclosures_survive(raw,presentation):
    out=compile_test(raw,presentation)
    assert [x['id'] for x in out['entries']]==[x['id'] for x in raw['entries']]
    for original,row in zip(raw['entries'],out['entries']):
        assert row['definition']['en']==original['short_definition_en']
        assert row['definition']['zh']==original['short_definition_zh']
        assert row['caveats']['en']==original['caveats_en']
        assert row['public_source_refs']==original['public_source_refs']
        assert row['related_ids']==original['related_ids']
    assert out['live_values'] is False
    assert out['authority_ceiling']=='reference_only'
    assert 'generated_at' not in out


def test_score_and_risk_keep_opposite_interpretations(raw,presentation):
    score,risk,*_=compile_test(raw,presentation)['entries']
    assert score['presentation']['kind']=='composite'
    assert risk['presentation']['kind']=='risk'
    assert 'supportive' in score['presentation']['readings'][2]['text']['en']
    assert 'not an exit signal' in risk['presentation']['readings'][2]['text']['en']
    assert risk['presentation']['readings'][0]['label']['en']=='Calm / watch'
    assert risk['presentation']['readings'][1]['label']['en']=='Caution'
    assert 'not to override a supportive' in risk['presentation']['readings'][1]['text']['en']


def test_confirmation_has_no_fabricated_up_down_states(raw,presentation):
    row=compile_test(raw,presentation)['entries'][3]
    assert row['presentation']['kind']=='confirmation'
    assert [r['id'] for r in row['presentation']['readings']]==['interpretation_neutral']
    assert row['presentation']['readings'][0]['label'] is None


def test_quadrant_is_not_a_linear_score(raw,presentation):
    row=compile_test(raw,presentation)['entries'][2]
    assert row['presentation']['kind']=='quadrant'
    assert row['presentation']['readings'][0]['label']['en']=='Growth up · inflation down'
    assert not any(k in row['presentation'] for k in ['score','thresholds','weights'])


def test_coverage_alias_deduplicates_existing_alias(raw,presentation):
    out=compile_test(raw,presentation)
    assert out['lookup'][normalize('Regime Badge')]==['market-regime']
    assert out['lookup'][normalize('regime-badge')]==['market-regime']
    assert out['lookup'][normalize('态势标签')]==['posture-dial']


def test_board_is_explained_not_reclassified_as_indicator(raw,presentation):
    out=compile_test(raw,presentation);key=out['lookup'][normalize('Prophet Stock Signals Board')][0]
    assert key not in [e['id'] for e in out['entries']]
    row=next(x for x in out['coverage'] if x['id']==key)
    assert row['state']=='not_an_indicator'
    assert row['related_ids']==['market-state-score','risk-radar']
    assert row['reason']['en']=='A board of names, not a measure.'


def test_uncovered_surface_remains_explicit(raw,presentation):
    raw['coverage_exceptions'][2].update(state='not_covered',see_ids=[],reason_en='Explanation is not available.',reason_zh='暂无说明。')
    row=compile_test(raw,presentation)['coverage'][2]
    assert row['state']=='not_covered' and row['related_ids']==[] and row['reason']['en']


def test_ambiguous_label_never_picks_one_candidate(raw,presentation):
    raw['entries'][1]['label_en']='Market State Score'
    out=compile_test(raw,presentation)
    assert out['lookup'][normalize('Market State Score')]==['market-state-score','risk-radar']


def test_retired_entry_keeps_history_and_exact_replacement(raw,presentation):
    row=raw['entries'][6];row.update(status='deprecated',superseded_by='posture-dial')
    out=compile_test(raw,presentation)['entries'][6]
    assert out['status']=='deprecated' and out['replacement_chain']==['posture-dial']
    assert out['definition']['en']==row['short_definition_en']


@pytest.mark.parametrize('replacement',['market-regime','missing',None])
def test_retirement_cycles_missing_targets_are_rejected(raw,presentation,replacement):
    raw['entries'][6].update(status='deprecated',superseded_by=replacement)
    with pytest.raises(GuideError,match='replacement'):compile_test(raw,presentation)


@pytest.mark.parametrize('kind',['live','forecast',None,[],{}])
def test_unsupported_visual_type_is_rejected(raw,presentation,kind):
    presentation['entries']['risk-radar']['kind']=kind
    with pytest.raises(GuideError):compile_test(raw,presentation)


@pytest.mark.parametrize('field',['thresholds','weights','current_score','model_summary'])
def test_no_numeric_or_model_authority_can_enter_presentation(raw,presentation,field):
    presentation['entries']['risk-radar'][field]=56
    with pytest.raises(GuideError):compile_test(raw,presentation)


@pytest.mark.parametrize('value',['https://evil.invalid/macro.html','//evil.invalid','../macro.html','macro.html?return=https://evil.invalid','javascript:alert(1)','macro.html#x\n'])
def test_unsafe_owner_routes_are_rejected(raw,presentation,value):
    raw['entries'][0]['owner_ref']=value
    with pytest.raises(GuideError):compile_test(raw,presentation)


@pytest.mark.parametrize('field',['label_zh','short_definition_zh','why_it_matters_zh','unit_or_basis_zh','interpretation_up_zh'])
def test_half_translated_fields_fail_closed(raw,presentation,field):
    del raw['entries'][0][field]
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_caveat_mismatch_is_rejected(raw,presentation):
    raw['entries'][0]['caveats_zh']=[]
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_source_interpretation_cannot_be_dropped(raw,presentation):
    presentation['entries']['risk-radar']['readings'].pop()
    with pytest.raises(GuideError,match='drop'):compile_test(raw,presentation)


def test_missing_interpretation_cannot_be_fabricated(raw,presentation):
    presentation['entries']['transition-state']['readings']=[{'field':'interpretation_up','label_en':'Higher','label_zh':'较高'}]
    with pytest.raises(GuideError,match='no source'):compile_test(raw,presentation)


def test_duplicate_reading_is_rejected(raw,presentation):
    presentation['entries']['risk-radar']['readings'].append(presentation['entries']['risk-radar']['readings'][0])
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_unknown_presentation_target_is_rejected(raw,presentation):
    presentation['entries']['nonexistent']={'kind':'risk'}
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_question_must_resolve_and_not_duplicate_members(raw,presentation):
    presentation['questions'][0]['entry_ids']=['risk-radar','risk-radar']
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_related_id_is_not_silently_dropped(raw,presentation):
    raw['entries'][0]['related_ids']=['not-there']
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_coverage_must_resolve(raw,presentation):
    raw['coverage_exceptions'][0]['see_ids']=['not-there']
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_coverage_requires_bilingual_reason(raw,presentation):
    raw['coverage_exceptions'][2]['reason_zh']=''
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_duplicate_coverage_names_rejected(raw,presentation):
    raw['coverage_exceptions'].append(copy.deepcopy(raw['coverage_exceptions'][0]))
    with pytest.raises(GuideError):compile_test(raw,presentation)


def test_content_revision_is_deterministic_and_content_sensitive(raw,presentation):
    one=compile_test(raw,presentation)
    assert one==compile_test(raw,presentation)
    raw['entries'][0]['caveats_en'][0]='Corrected limitation.'
    assert one['content_revision']!=compile_test(raw,presentation)['content_revision']


def test_markup_and_separators_are_inert_script_data(raw,presentation):
    hostile='</script><script>globalThis.pwned=true</script>&\u2028\u2029'
    raw['entries'][0]['label_en']=hostile
    manifest=compile_test(raw,presentation);encoded=script_json(manifest)
    assert '<' not in encoded and '>' not in encoded and '\u2028' not in encoded
    assert json.loads(encoded)['entries'][0]['label']['en']==hostile


def test_private_source_fields_are_not_exposed(raw,presentation):
    raw['entries'][0]['internal_repo_path']='private/path';raw['credential']='not-public'
    encoded=script_json(compile_test(raw,presentation))
    assert 'private/path' not in encoded and 'not-public' not in encoded


@pytest.mark.parametrize('a,b',[('Market State Score','ｍａｒｋｅｔ—ＳＴＡＴＥ score'),('Regime Badge','regime-badge'),('市场状态 分','市场状态分')])
def test_normalization(a,b): assert normalize(a)==normalize(b)


def test_validator_cannot_rewrite_the_source(raw,presentation):
    def rewriting_owner(source):
        source['entries'][0]['short_definition_en']='Silently changed.'
        return source['entries']
    with pytest.raises(GuideError,match='must not rewrite'):
        compile_guide(raw,presentation,validate_registry=rewriting_owner,validate_coverage=lambda s,e:s['coverage_exceptions'])

def test_validator_cannot_drop_rows(raw,presentation):
    with pytest.raises(GuideError,match='drop'):
        compile_guide(raw,presentation,validate_registry=lambda s:s['entries'][:-1],validate_coverage=lambda s,e:s['coverage_exceptions'])

def test_validator_cannot_drop_coverage(raw,presentation):
    with pytest.raises(GuideError,match='drop'):
        compile_guide(raw,presentation,validate_registry=lambda s:s['entries'],validate_coverage=lambda s,e:[])

def test_replacement_chain_keeps_every_step(raw,presentation):
    raw['entries'][6].update(status='deprecated',superseded_by='posture-dial')
    raw['entries'][7].update(status='deprecated',superseded_by='market-state-score')
    assert compile_test(raw,presentation)['entries'][6]['replacement_chain']==['posture-dial','market-state-score']


def test_optional_null_coverage_follows_canonical_owner_semantics(raw,presentation):
    raw['coverage_exceptions']=None
    assert compile_test(raw,presentation)['coverage']==[]

def test_null_optional_lists_remain_missing_not_fabricated(raw,presentation):
    row=raw['entries'][0]
    row.update(aliases_en=None,aliases_zh=None,public_source_refs=None,related_ids=None)
    result=compile_test(raw,presentation)['entries'][0]
    assert result['aliases']=={'en':[],'zh':[]}
    assert result['public_source_refs']==[] and result['related_ids']==[]

def test_null_caveats_allowed_only_for_non_indicator(raw,presentation):
    raw['entries'][0].update(kind='glossary',caveats_en=None,caveats_zh=None)
    row=compile_test(raw,presentation)['entries'][0]
    assert row['visible_caveat'] is None
    raw['entries'][0]['kind']='indicator'
    with pytest.raises(GuideError,match='visible limitation'):compile_test(raw,presentation)
