"""Discriminating regressions for the original independent illustration review."""
from unittest.mock import patch

import pytest

from engine.neuralweb import brain_gateway as gw
from engine.neuralweb.brain_visuals import compile_visual, validate_view
from tests.test_brain_visuals import spec
from tests.test_brain_visuals_integration import client_for, no_external_sources  # noqa: F401


@pytest.mark.parametrize('formatted', ['$1,234', 'USD 1234', '≈1234', '(1234)', '€1.234,56', '25bp', 'Paused'])
def test_every_source_value_string_requires_its_own_binding(formatted):
    request = spec('metrics', columns=['Metric','Value'], rows=[['P/E',17.5],['Price',formatted]], basis='source',
                   bindings=[{'row':0,'column':1,'tool':'get_quote','call_id':'q1','pointer':'/pe'}])
    observations = [('get_quote', {'pe':17.5,'formatted':formatted}, 'q1')]
    assert 'error' in compile_visual(request, observations, 'draw')
    request['bindings'].append({'row':1,'column':1,'tool':'get_quote','call_id':'q1','pointer':'/formatted'})
    result = compile_visual(request, observations, 'draw')
    assert result['visual']['rows'][1][1] == formatted
    assert result['visual']['provenance']['text_cells_matched'] == 1
    assert validate_view(result)


@pytest.mark.parametrize('template', ['status','scenarios','timeline','flow'])
def test_observed_text_templates_bind_all_non_null_cells(template):
    request = spec(template, columns=['Date','Event'], rows=[['2026-10-15','CPI release']], basis='source', bindings=[
        {'row':0,'column':0,'tool':'get_market_events','call_id':'event1','pointer':'/date'},
        {'row':0,'column':1,'tool':'get_market_events','call_id':'event1','pointer':'/name'}])
    observations = [('get_market_events', {'date':'2026-10-15','name':'CPI release'}, 'event1')]
    wire = compile_visual(request, observations, 'draw')
    assert wire['visual']['basis'] == 'source'
    assert wire['visual']['provenance']['numeric_cells_matched'] == 0
    assert wire['visual']['provenance']['text_cells_matched'] == 2
    assert validate_view(wire)
    request['bindings'].pop()
    assert 'error' in compile_visual(request, observations, 'draw')


@pytest.mark.parametrize('source,pointer', [
    ({'available':False,'v':0},'/v'), ({'ok':False,'v':0},'/v'),
    ({'success':False,'v':0},'/v'), ({'quote':{'available':False,'v':0}},'/quote/v'),
    ({'quote':{'error':'unavailable','v':0}},'/quote/v'),
])
def test_failed_ancestors_do_not_supply_a_bound_value(source, pointer):
    request = spec(rows=[['A',0]], basis='source', bindings=[{'row':0,'column':1,'tool':'get_quote','pointer':pointer}])
    assert 'error' in compile_visual(request,[('get_quote',source)],'draw')


def test_unrelated_failed_sibling_does_not_erase_a_valid_source_cell():
    request = spec(rows=[['A',2]], basis='source', bindings=[{'row':0,'column':1,'tool':'get_quote','pointer':'/good/v'}])
    assert 'visual' in compile_visual(request,[('get_quote',{'good':{'v':2},'missing':{'error':'unavailable'}})],'draw')


@pytest.mark.parametrize('message', ['Illustrate the price history of NVDA', "Give me a sample of yesterday's closing prices", 'Chart an example of the past year of yields', 'Show a hypothetical SPX path since 2020', '用示意图显示上周价格'])
def test_historical_requests_cannot_receive_invented_numeric_examples(tmp_path, message):
    assert gw._run_brain_loop(message,'fast',[],{},tmp_path,tmp_path,'',client_for(spec()),'test-model',1000,3)[-1] == []


def test_history_queries_only_the_existing_visual_subfield():
    with patch.object(gw,'_thread_read_rows',side_effect=[[{'id':'11111111-1111-1111-1111-111111111111'}],[]]) as read:
        gw.get_thread('11111111-1111-1111-1111-111111111111','owner')
    query = read.call_args_list[1].args[0]
    assert 'visuals:meta->visuals' in query and ',meta&' not in query


@pytest.mark.parametrize('state', ['source_unavailable','rights_blocked','not_covered','not_applicable','conflicted'])
def test_gateway_reuses_existing_evidence_state_owner(state):
    request=spec(rows=[['A',2]], basis='source', bindings=[{'row':0,'column':1,'tool':'get_quote','pointer':'/quote/v'}])
    charts=[]
    result=gw._prepare_inline_visual({'visual_request':request}, [('get_quote', {'quote':{'v':2,'status':state}}, 'q1')], 'draw', charts, 'Compare retrieved data')
    assert 'error' in result and charts == []
