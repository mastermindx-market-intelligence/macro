"""Inspector consumes actual owner projections; every source/rights fixture is synthetic."""
from copy import deepcopy
import json
import socket

import numpy as np
import pandas as pd
import pytest

from engine import intl_inputs
from engine.intl_performance_records import build_return_records
from engine.intl_workspace_overview import build_overview
from lib import store
from lib.intl_inspector_view import build_inspector_view, INSPECTOR_COPY


@pytest.fixture
def supplied():
    dates = pd.date_range('2025-12-10', periods=30)
    frame = pd.DataFrame({'^N225':np.linspace(100.,129.,30), 'USDJPY=X':np.linspace(100.,158.,30),
                          '^FTSE':np.linspace(100.,129.,30), 'GBPUSD=X':np.linspace(1.,1.29,30)}, index=dates)
    raw = build_return_records(frame, market_ids=['JP','GB'], source_reference='synthetic:inspector-source')
    countries = intl_inputs.countries()
    roster = [{'market_id':cc, 'name_en':countries[cc]['name'], 'name_zh':countries[cc]['name_zh']} for cc in ['JP','GB']]
    def project(*, basis='usd_unhedged', decisions=True, edit=None, data=None):
        records = deepcopy(raw if data is None else data)
        context = {'horizon':'1m', 'currency_basis':basis, 'return_basis':'price', 'source_reference':records['source_reference']}
        receipts = []
        for row in records['records']:
            if row['horizon'] != '1m':
                continue
            for leg in ('local','usd','fx_contribution'):
                metric = row[leg]
                receipts.append({'binding':{'source_reference':records['source_reference'], 'market_id':row['market_id'],
                    'index_id':row['index_id'],'fx_id':row['fx_id'],'horizon':'1m','currency_basis':basis,'return_basis':'price',
                    'leg':leg,'value':metric['value'],'unit':metric['unit'],'window':deepcopy(metric['window'])},
                    'owner_ref':'synthetic:source-owner','policy_ref':'synthetic:policy','decision_ref':'synthetic:decision',
                    'quality':'qualified','reason':None,'disclosure':{'metadata':'allowed','value':'allowed'}})
        if edit:
            edit(receipts)
        return build_overview(records,roster=roster,context=context,qualifications=receipts if decisions else None)
    return project, raw, frame


def inspect(overview, market='JP', **kwargs):
    context = {k:overview['context'][k] for k in ('horizon','currency_basis','return_basis','source_reference')}
    return build_inspector_view(overview, selected_market=market, context=context, **kwargs)


def test_actual_owner_values_identity_and_detachment(supplied):
    overview = supplied[0]()
    before = deepcopy(overview)
    result = inspect(overview)
    row = overview['rows'][0]
    assert result['status'] == 'available'
    assert result['market']['index_id'] == '^N225'
    assert result['market']['index_label'] == 'Nikkei 225'
    for leg in ('local','usd','fx_contribution'):
        assert result['metrics'][leg] == row[leg]
        assert result['evidence'][('local','usd','fx_contribution').index(leg)]['metric'] == row[leg]
    assert result['metrics']['selected'] == row['metric']
    assert result['interpretation']['decomposition'] == 'reported_same_window'
    result['metrics']['usd']['window']['start'] = 'changed'
    result['market']['name_en'] = 'changed'
    assert overview == before
    assert result['evidence'][1]['metric']['window']['start'] != 'changed'


def test_denied_and_absent_selections_are_indistinguishable(supplied):
    def deny(receipts):
        for r in receipts:
            if r['binding']['market_id']=='JP': r['disclosure']['metadata']='denied'
    overview = supplied[0](edit=deny)
    denied = inspect(overview)
    absent = inspect(overview,'PRIVATE-REQUEST')
    assert denied == absent
    encoded = json.dumps(denied)
    for private in ('JP','Nikkei','PRIVATE-REQUEST','synthetic:inspector-source'):
        assert private not in encoded
    assert denied['market'] is None and denied['metrics'] is None
    assert denied['evidence'] == denied['deeper_links'] == []


def test_unknown_market_does_not_borrow_another_markets_source(supplied):
    overview = supplied[0](edit=lambda r:r.__setitem__(slice(None),[x for x in r if x['binding']['market_id']=='GB']))
    assert overview['context']['source_reference'] is not None
    result = inspect(overview)
    assert result['status']=='partial'
    assert result['market']['market_id']=='JP'
    assert result['market']['index_id'] is None
    assert result['context']['source_reference'] is None
    assert 'synthetic:inspector-source' not in json.dumps(result)
    assert all(result['metrics'][k]['value'] is None for k in ('local','usd','fx_contribution','selected'))


def test_local_only_real_frames_remain_useful_without_fx(supplied):
    raw = build_return_records(supplied[2].drop(columns=['USDJPY=X']),market_ids=['JP','GB'],source_reference='synthetic:local-only')
    result = inspect(supplied[0](basis='local',data=raw))
    assert result['status']=='partial'
    assert result['metrics']['local']['quality']=='qualified'
    assert result['metrics']['selected_leg']=='local'
    assert result['metrics']['usd']['value'] is None
    assert result['interpretation']['decomposition']=='unavailable'


@pytest.mark.parametrize('direction,sign', [(1,'positive'),(0,'zero'),(-1,'negative')])
def test_real_owner_selected_signs(supplied,direction,sign):
    frame=supplied[2].copy();frame['^N225']=100+direction*np.arange(len(frame))
    raw=build_return_records(frame,market_ids=['JP','GB'],source_reference='synthetic:sign')
    result=inspect(supplied[0](basis='local',data=raw))
    assert result['interpretation']['selected_sign']==sign
    assert ('selected_return_'+sign) in [item['key'] for item in result['supports']]


@pytest.mark.parametrize('quality', ['stale','missing','denied','failed','unsupported','unknown'])
def test_owner_quality_preserved_and_fixed_bilingual_copy(supplied,quality):
    def edit(receipts):
        for r in receipts:
            if r['binding']['market_id']=='JP':
                if quality=='denied': r['disclosure']['value']='denied'
                else: r.update(quality=quality,reason='synthetic:quality-evidence')
    overview=supplied[0](edit=edit);result=inspect(overview)
    assert result['metrics']['selected']['quality']==quality
    assert result['metrics']['selected']['value'] is None
    assert result['interpretation']['selected_sign']=='unavailable'
    keys=[x['key'] for x in result['limits']]
    assert ('return_not_disclosed' if quality=='denied' else 'return_'+quality) in keys
    assert all(set(INSPECTOR_COPY[key])=={'en','zh'} for key in keys)
    assert 'synthetic:quality-evidence' not in json.dumps(result)


def test_calculation_window_differences_suppress_only_decomposition(supplied):
    raw=deepcopy(supplied[1])
    row=next(x for x in raw['records'] if x['market_id']=='JP' and x['horizon']=='1m')
    row['local']['window']['start']='2025-12-19T00:00:00'
    overview=supplied[0](data=raw);result=inspect(overview)
    assert result['metrics']['local']==overview['rows'][0]['local']
    assert result['interpretation']['decomposition']=='unavailable'
    assert result['interpretation']['fx_effect']=='unavailable'
    assert result['interpretation']['selected_sign']=='negative'


def test_observation_dates_are_not_publication_clocks(supplied):
    frame=supplied[2].copy();frame.iloc[-1,frame.columns.get_loc('USDJPY=X')]=np.nan
    raw=build_return_records(frame,market_ids=['JP','GB'],source_reference='synthetic:carried')
    overview=supplied[0](data=raw);result=inspect(overview)
    evidence=result['evidence'][1]
    assert evidence['endpoint_observations']==overview['rows'][0]['usd']['window']['endpoint_observations']
    assert evidence['clocks']==dict.fromkeys(['observation','publication','ingestion','generation'])
    assert evidence['clock_reason']=='not_supplied_by_overview'
    assert evidence['calculation_window']['end'] != evidence['endpoint_observations']['fx_end']


@pytest.mark.parametrize('key,value',[('horizon','3m'),('currency_basis','local'),('source_reference','synthetic:other')])
def test_context_mismatch_withholds_payload(supplied,key,value):
    overview=supplied[0]();context={k:overview['context'][k] for k in ('horizon','currency_basis','return_basis','source_reference')}
    context[key]=value
    result=build_inspector_view(overview,selected_market='JP',context=context)
    assert result['status']=='unavailable' and result['reason']=='context_mismatch'
    assert result['context']['source_reference'] is None
    assert result['market'] is result['metrics'] is None
    assert result['evidence']==result['deeper_links']==[]


def links():
    return [{'market_id':'JP','tool_key':'performance','label_en':'Returns','label_zh':'回报', 'route_state':'available',
             'target':{'page_id':'macro:intl','route':'/intl.html','region_id':'intl-performance'}},
            {'market_id':'JP','tool_key':'stocks','label_en':'Stocks','label_zh':'股票','route_state':'available',
             'target':{'page_id':'macro:intl_stocks','route':'/intl_stocks.html','region_id':None}}]


def test_only_actual_bound_public_destination_shapes(supplied):
    destinations=links();destinations.append({**deepcopy(destinations[0]),'market_id':'GB','tool_key':'gb-returns'})
    result=inspect(supplied[0](),deeper_links=destinations)
    assert result['deeper_links']==destinations[:2]
    result['deeper_links'][0]['target']['region_id']='changed'
    assert destinations[0]['target']['region_id']=='intl-performance'


@pytest.mark.parametrize('alter', [lambda x:x[0]['target'].update(route='https://example.com'),
    lambda x:x[0]['target'].update(region_id='a?country=JP'),lambda x:x[0]['target'].update(verified=True),
    lambda x:x[0].update(route_state='unavailable'),lambda x:x.append(deepcopy(x[0]))])
def test_unsafe_unavailable_duplicate_destinations_rejected(supplied,alter):
    destinations=links();alter(destinations)
    with pytest.raises(ValueError,match='^INVALID_INSPECTOR_INPUT$'):inspect(supplied[0](),deeper_links=destinations)


@pytest.mark.parametrize('bad', [True,float('nan'),float('inf'),'4',1+2j])
def test_invalid_values_rejected(supplied,bad):
    overview=supplied[0]();overview['rows'][0]['metric']['value']=bad
    with pytest.raises(ValueError,match='^INVALID_INSPECTOR_INPUT$'):inspect(overview)


@pytest.mark.parametrize('mutate', [lambda x:x.update(private_receipt={}),lambda x:x['rows'].append(deepcopy(x['rows'][0])),
    lambda x:x['rows'][0].update(slot=True),lambda x:x['rows'][0]['metric'].update(secret='x'),
    lambda x:x['context'].update(private_source='x'),lambda x:x['summary'].update(extra='x')])
def test_closed_shapes_and_duplicates(supplied,mutate):
    overview=supplied[0]();mutate(overview)
    with pytest.raises(ValueError,match='^INVALID_INSPECTOR_INPUT$'):inspect(overview)


def test_no_io_nonmutation_and_plain_output(supplied,monkeypatch):
    overview=supplied[0]();before=deepcopy(overview)
    def forbidden(*a,**k):raise AssertionError('Inspector attempted I/O')
    monkeypatch.setattr(store,'read',forbidden);monkeypatch.setattr(intl_inputs,'countries',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    result=inspect(overview)
    assert overview==before
    json.dumps(result,allow_nan=False)
    assert set(result)=={'status','reason','context','market','metrics','interpretation','supports','limits','research_prompts','evidence','deeper_links'}


def test_subclass_and_recursive_input_refused(supplied):
    class Sneaky(dict):
        def items(self):raise AssertionError('custom method executed')
    for bad in [Sneaky(), {'self':None}]:
        if type(bad) is dict:bad['self']=bad
        with pytest.raises(ValueError,match='^INVALID_INSPECTOR_INPUT$'):
            build_inspector_view(bad,selected_market='JP',context={})


@pytest.mark.parametrize('alter', [lambda x:x['rows'][0]['metric'].update(quality=[]),
    lambda x:x['rows'][0].update(metric=[]),lambda x:x['rows'][0]['metric'].update(window={}),
    lambda x:x['context'].update(currency_basis=[]),lambda x:x.update(rows={})])
def test_malformed_nested_types_always_have_public_error(supplied,alter):
    overview=supplied[0](decisions=False);alter(overview)
    context={'horizon':'1m','currency_basis':'usd_unhedged','return_basis':'price','source_reference':None}
    with pytest.raises(ValueError,match='^INVALID_INSPECTOR_INPUT$'):
        build_inspector_view(overview,selected_market='JP',context=context)


def test_nanosecond_timezone_window_labels_preserved(supplied):
    frame=supplied[2].copy()
    frame.index=frame.index.tz_localize('Asia/Tokyo')+pd.Timedelta(nanoseconds=123)
    raw=build_return_records(frame,market_ids=['JP','GB'],source_reference='synthetic:nanoseconds')
    overview=supplied[0](data=raw);result=inspect(overview)
    assert result['metrics']['selected']['window']==overview['rows'][0]['metric']['window']
    assert result['metrics']['selected']['window']['end'].endswith('.000000123+09:00')


def test_no_matching_market_emits_no_bound_links(supplied):
    overview=supplied[0](decisions=False)
    assert inspect(overview,'ABSENT',deeper_links=links())['deeper_links']==[]
