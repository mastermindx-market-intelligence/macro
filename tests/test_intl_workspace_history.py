"""History source disclosure and comparability without invoking a financial engine."""
import copy
import json
from pathlib import Path

import pytest
import lib.intl_workspace_history as owner

CASES = json.loads((Path(__file__).parent/'fixtures/intl_workspace/history_cases.json').read_text())['cases']


def inputs():
    return copy.deepcopy(CASES[0]['args'])


@pytest.mark.parametrize('case', CASES, ids=lambda c:c['id'])
def test_frozen_contract(case):
    args=copy.deepcopy(case['args'])
    inject=case.get('inject')
    if inject:
        values={"float('nan')":float('nan'),"float('inf')":float('inf'),'object()':object()}
        target=args
        for key in inject['path'][:-1]:target=target[key]
        target[inject['path'][-1]]=values[inject['python']]
    if case['expect']=='error':
        with pytest.raises(ValueError,match='^invalid_history_section_input$'):owner.build_history_section(**args)
    else:
        result=owner.build_history_section(**args)
        assert result==case['output']
        encoded=json.dumps(result,allow_nan=False)
        for sentinel in case.get('forbidden_substrings',[]):assert sentinel not in encoded


@pytest.mark.parametrize('status',['missing','failed','invalid','unsupported'])
def test_unbound_failure_never_borrows_source_metadata(status):
    args=inputs();args['history_read'].update(status=status,market_id=None,identity=None,points=[],artifact_ref='PRIVATE/artifact',method_ref='PRIVATE-METHOD')
    result=owner.build_history_section(**args)
    assert result['source_read_status']==status
    for key in ['source_reference','source_reference_kind','acquisition_at','acquisition_kind','method_ref','identity']:assert result[key] is None
    assert 'PRIVATE' not in json.dumps(result)


@pytest.mark.parametrize('ref',['/private/data','C:/private/data','https://example.test/x','a/../b','a/./b','a//b','a\\b','a%20b','a\nb',' a','a ','a/','../a'])
def test_artifact_reference_is_only_a_relative_identifier(ref):
    args=inputs();args['history_read']['artifact_ref']=ref
    with pytest.raises(ValueError,match='^invalid_history_section_input$'):owner.build_history_section(**args)


def test_input_and_output_are_detached_without_touching_owner():
    args=inputs();before=copy.deepcopy(args);result=owner.build_history_section(**args)
    assert args==before
    result['points'][0]['growth_score']=999
    result['identity']['method_ref']='changed'
    result['events']['records'][0]['text_en']='changed'
    result['track_record']['sample_dates'].clear()
    assert args==before


def test_large_integer_and_nanosecond_dates_remain_exact():
    args=inputs();args['history_read']['points'][0]['growth_score']=10**400
    out=owner.build_history_section(**args)
    assert out['points'][0]['growth_score']==10**400
    assert out['points'][-1]['observation_at']=='2026-01-03T00:00:00.123456789+09:00'
    json.dumps(out,allow_nan=False)


@pytest.mark.parametrize('mutate',[
 lambda a:a['history_read']['points'][1].update(observation_at='2026-01'),
 lambda a:a['history_read']['points'][1].update(observation_at='2025-12-31T15:00:00Z'),
 lambda a:a['history_read']['points'][1].update(observation_at='2026-01-01T00:00:00'),
 lambda a:a['history_read'].update(read_at='2026-10-08'),
 lambda a:a['history_read'].update(read_at='2026-10-08T12:00:00'),
 lambda a:a['context'].update(horizon=a),
 lambda a:a['track_record'].update(alert_count=True),
])
def test_bad_geometry_clocks_and_cycles_are_fixed_errors(mutate):
    args=inputs();mutate(args)
    with pytest.raises(ValueError,match='^invalid_history_section_input$'):owner.build_history_section(**args)


def test_month_events_keep_month_precision_and_no_first_known_claim():
    out=owner.build_history_section(**inputs())
    assert out['events']['records'][0]['event_date']=='2026-01'
    assert out['events']['records'][0]['history_kind']=='recomputed'
    assert out['as_known']['available'] is False and out['revisions']['records']==[]


def test_denied_history_does_not_suppress_independently_allowed_event():
    args=inputs();args['capabilities']['history_source']={'metadata':'denied','value':'denied'}
    out=owner.build_history_section(**args)
    assert out['points']==[] and out['identity'] is None
    assert out['events']['status']=='available'
    assert out['snapshot_compare']['available_dates']==[]
