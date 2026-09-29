from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json, math, sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.china_economy import (build_economy,extend_snapshot,pace,compound,month_index,month_from_index,month_end,select_observations,timestamp,diagnostic,breadth,DOMAINS)
ROOT=Path(__file__).resolve().parents[2]
@pytest.fixture
def doc():return json.loads((Path(__file__).resolve().parent/'fixtures/china_economy_review.json').read_text())

def spec(kind='yoy',frequency='monthly'):
 return {'id':'x','kind':kind,'frequency':frequency,'direction_deadband':.1,'polarity':1,'definition_id':'x.v1'}
def rows(values,start=3,vintages=None):
 return [{'metric_id':'x','period':month_from_index(2026*12+start-1+i),'value':v,'definition_id':'x.v1','vintage_id':(vintages or ['one']*len(values))[i]} for i,v in enumerate(values)]

def test_review_shape(doc):
 s=build_economy(doc)
 assert s['counts']['catalog']==128 and s['counts']['diagnostics']==11
 assert len(s['domains'])==6
 assert s['is_live_feed'] is False and s['original_vintage_replay'] is False
 assert s['metrics']['income_real']['reference_period']=='2026-06'
 assert s['metrics']['income_real']['status']=='older_period'
 assert s['metrics']['income_real']['pace']['current_3m'] is None
 json.dumps(s,allow_nan=False)

@pytest.mark.parametrize('key,current,prior',[
 ('industrial_sa',1.415539,.731461),('retail_sa',.279507,-.210166),('investment_sa',-1.961287,-4.44055)])
def test_real_seasonal_pace(doc,key,current,prior):
 p=build_economy(doc)['metrics'][key]['pace']
 assert p['current_3m']==pytest.approx(current,abs=1e-6)
 assert p['previous_3m']==pytest.approx(prior,abs=1e-6)
 assert p['direction']=='improving'
 assert p['acceleration'] is None
 assert p['is_activity_growth']

def test_contraction_can_improve(doc):
 s=build_economy(doc);i=next(d for d in s['domains'] if d['id']=='investment')
 assert i['state']=='below' and i['momentum']=='improving'
 assert s['metrics']['investment_sa']['pace']['current_3m']<0

def test_growth_can_fade_and_never_become_contraction(doc):
 m=build_economy(doc)['metrics']['services_retail_ytd']
 assert m['value']>0 and m['state']=='above' and m['pace']['direction']=='fading'

def test_six_domain_balance_not_metric_count(doc):
 s=build_economy(doc);b=s['breadth']
 assert b['covered']==5 and b['counts']=={'improving':1,'fading':1,'mixed':3,'steady':0,'unknown':1}
 assert b['universe']==6 and b['is_gdp_nowcast'] is False
 assert b['improvement_lower_bound_pct']==16.7 and b['improvement_upper_bound_pct']==33.3

def test_extra_context_does_not_move_breadth(doc):
 before=build_economy(doc)['breadth'];after=deepcopy(doc)
 for i in range(80):
  meta=deepcopy(doc['catalog']['ppi']);meta['id']='extra_'+str(i);meta['definition_id']=meta['id']+'.v1';after['catalog'][meta['id']]=meta
 assert build_economy(after)['breadth']==before

def test_every_unavailable_domain_keeps_denominator(doc):
 doc['observations']=[];b=build_economy(doc)['breadth']
 assert b['universe']==6 and b['covered']==0 and b['counts']['unknown']==6
 assert not b['eligible'];assert b['improvement_upper_bound_pct']==100

def test_no_trade_fields(doc):
 s=build_economy(doc)
 assert not any(k in s for k in ['buy','sell','target_weight','position_size','entry_permission','recession_probability'])
 assert s['authority']=='economic_description_only'

@pytest.mark.parametrize('values,expected', [([10,10,10],33.1),([1,-1,0],-.01),([0,0,0],0),([-50,-50],-75)])
def test_compound_not_sum(values,expected):assert compound(values)==pytest.approx(expected)
@pytest.mark.parametrize('values',[[],[1,None,3],[float('nan')],[True],[float('inf')],[-100],[-101]])
def test_invalid_compounding(values):assert compound(values) is None

def test_slope_and_acceleration_have_time_units():
 # first slope 1 point/month; recent slope 3; centers are 3 months apart.
 p=pace(spec(),rows([1,2,3,4,7,10]),'2026-08')
 assert p['slope_previous_3m']==1 and p['slope_recent_3m']==3
 assert p['acceleration']==pytest.approx(2/3,abs=1e-6)
 assert p['acceleration_unit']=='percentage points/month²'

def test_no_fake_full_window():
 p=pace(spec(),rows([1,2,3,4,5]),'2026-07')
 assert p['slope_recent_3m']==1
 assert p['direction']=='unknown' and p['acceleration'] is None

def test_interior_missing_month_disables_six_window():
 r=rows([1,2,3,4,5,6]);r.pop(2);p=pace(spec(),r,'2026-08')
 assert p['acceleration'] is None and p['direction']=='unknown'
 assert p['slope_recent_3m']==1

def test_missing_latest_never_borrows_prior_window():
 p=pace(spec(),rows([1,2,3,4,5,None]),'2026-08')
 assert p['slope_recent_3m'] is None and p['direction']=='unknown'

def test_definition_break_blocks_pace():
 r=rows([1,2,3,4,5,6]);r[-1]['definition_id']='x.v2'
 assert pace(spec(),r,'2026-08')['acceleration'] is None

def test_no_mixed_seasonal_vintages():
 p=pace(spec('sa_mom'),rows([1]*6,vintages=['a']*3+['b']*3),'2026-08')
 assert p['reason']=='mixed_seasonal_revision' and p['change_in_pace'] is None

def test_ytd_does_not_cross_new_year():
 r=rows([1]*6,start=10)
 p=pace(spec('ytd_yoy'),r,'2027-03')
 assert p['direction']=='unknown'

def test_pmi_not_compounded():
 p=pace(spec('survey'),rows([48,49,50,49,50,51]),'2026-08')
 assert p['is_activity_growth'] is False and p['current_3m']==50
 assert p['acceleration_unit']=='index points/month²'

@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),'bogus'])
def test_bad_latest_is_quality_hold(doc,value):
 next(o for o in doc['observations'] if o['metric_id']=='pmi_mfg' and o['period']=='2026-08')['value']=value
 m=build_economy(doc)['metrics']['pmi_mfg']
 assert m['status']=='quality_hold' and m['value'] is None and m['pace']['direction']=='unknown'

@pytest.mark.parametrize('value',[-.1,100.1])
def test_invalid_diffusion(doc,value):
 next(o for o in doc['observations'] if o['metric_id']=='pmi_mfg' and o['period']=='2026-08')['value']=value
 assert build_economy(doc)['metrics']['pmi_mfg']['status']=='quality_hold'

def test_duplicate_same_release_conflict(doc):
 r=deepcopy(next(o for o in doc['observations'] if o['metric_id']=='pmi_mfg' and o['period']=='2026-08'));r['value']=99.;doc['observations'].append(r)
 m=build_economy(doc)['metrics']['pmi_mfg'];assert m['value'] is None and m['status']=='quality_hold'

def test_identical_replay_is_idempotent(doc):
 before=build_economy(doc);doc['observations']+=deepcopy(doc['observations'])
 assert build_economy(doc)==before

def test_publication_future_blocks_access(doc):
 m=build_economy(doc,as_of='2026-09-10T12:00:00+08:00')['metrics']['industrial_sa']
 assert m['value'] is None

def test_future_reference_month_rejected(doc):
 with pytest.raises(ValueError,match='future display'):build_economy(doc,reference_period='2026-10')

def test_reference_selection_cannot_see_next_month(doc):
 m=build_economy(doc,reference_period='2026-07')['metrics']['industrial_sa']
 assert m['value']==.11 and m['chart']['dates'][-1]=='2026-07-01'

def test_review_historical_slice_not_point_in_time(doc):
 s=build_economy(doc,reference_period='2026-06')
 assert s['original_vintage_replay'] is False

def test_timestamp_timezone_required():
 with pytest.raises(ValueError):timestamp('2026-09-29T00:00:00')

def test_source_metadata_must_match(doc):
 r=next(o for o in doc['observations'] if o['metric_id']=='pmi_mfg' and o['period']=='2026-08');r['published_at']='2026-01-01T00:00:00+08:00'
 assert build_economy(doc)['metrics']['pmi_mfg']['status']=='quality_hold'

def test_nominal_and_real_remain_distinct(doc):
 s=build_economy(doc)
 assert 'Real output' in s['metrics']['industrial_yoy']['note_en']
 assert 'Nominal' in s['metrics']['retail_yoy']['note_en']

def test_missing_external_history_not_substituted(doc):
 s=build_economy(doc);d=next(d for d in s['domains'] if d['id']=='external')
 assert d['state']=='above' and d['momentum']=='unknown'
 assert s['metrics']['pmi_exports']['pace']['direction']!='unknown'

def test_same_period_fiscal_arithmetic(doc):
 d={d['id']:d for d in build_economy(doc)['diagnostics']}
 assert d['fiscal_cash_gap']['value']==pytest.approx(2481.8)
 assert d['interest_share']['value']==pytest.approx(9188/181451*100,abs=.001)
 assert d['land_share']['value']==pytest.approx(13753/18127*100,abs=.001)
 assert 'Not an official deficit' in d['fiscal_cash_gap']['method_en']

def test_pmi_spread_not_profit_margin(doc):
 d={d['id']:d for d in build_economy(doc)['diagnostics']}
 assert d['input_output_prices']['value']==pytest.approx(6.2)
 assert d['orders_inventory']['value']==pytest.approx(2.2)
 assert 'NOT a measured profit margin' in d['input_output_prices']['method_en']

def test_fiscal_single_period_has_no_acceleration(doc):
 m=build_economy(doc)['metrics']['fiscal_general_spending_growth']
 assert m['pace']['current_3m'] is None and m['pace']['acceleration'] is None

def test_short_power_history_no_fake_velocity(doc):
 m=build_economy(doc)['metrics']['power_households']
 assert m['change_1m']==pytest.approx(1.1)
 assert m['pace']['acceleration'] is None
 assert 'not a direct household' in m['note_en']

def test_incomplete_reference_period_excluded(doc):
 # Source-checked monthly August actual activity cannot be admitted in July.
 s=build_economy(doc,as_of='2026-08-20T12:00:00+08:00',reference_period='2026-08')
 assert s['metrics']['retail_yoy']['status']!='current'

def test_survey_release_at_month_end_admitted(doc):
 s=build_economy(doc,as_of='2026-08-31T10:00:00+08:00')
 assert s['metrics']['pmi_mfg']['value']==49.8

def test_extending_does_not_modify_base(doc):
 base={'schema':'base','panels':{'original':{'a':3}}};before=deepcopy(base)
 s=build_economy(doc);ext=extend_snapshot(base,s)
 assert base==before and ext['panels']==base['panels'];assert 'economy' in ext
 with pytest.raises(ValueError):extend_snapshot(ext,s)

@pytest.mark.parametrize('value',['2026-00','2026-13','26-01','2026-1','notdate'])
def test_invalid_month(value):
 with pytest.raises(ValueError):month_index(value)

def test_calendar_roundtrip():
 assert month_from_index(month_index('2026-12')+1)=='2027-01'
 assert month_end('2024-02').day==29

def test_contract_identity_mismatch(doc):
 doc['catalog']['pmi_mfg']['id']='wrong'
 with pytest.raises(ValueError,match='identity'):build_economy(doc)

def test_unknown_schema(doc):
 doc['schema']='something_else'
 with pytest.raises(ValueError,match='unsupported'):build_economy(doc)

def test_shorter_windows_expose_fragile_pace(doc):
 s=build_economy(doc);p=s['activity_pulse']
 assert p['improving_3m']==3 and p['improving_2m']==0 and p['window_sensitive']==3
 for key in p['metric_ids']:
  w=s['metrics'][key]['pace']['window_sensitivity']
  assert w['agrees_with_3m'] is False and w['direction_2m']=='fading'

def test_source_urls_are_admitted_not_arbitrary(doc):
 doc['sources']['pmi_aug']['url']='javascript:alert(1)'
 assert build_economy(doc)['metrics']['pmi_mfg']['status']=='quality_hold'

def test_asof_instant_normalized_to_china(doc):
 assert build_economy(doc,as_of='2026-09-28T20:00:00Z')['as_of'].startswith('2026-09-29T04:00:00')

def test_source_conflict_is_not_erased(doc):
 s=build_economy(doc)
 assert s['known_source_conflicts'][0]['legacy_value']==-13.5
 assert s['metrics']['investment_ytd']['value']==-7.2
 assert 'do not overwrite' in s['known_source_conflicts'][0]['resolution']

def test_rate_change_units_are_not_percent_change(doc):
 m=build_economy(doc)['metrics']['retail_yoy']
 assert m['change_unit']=='percentage points' and m['change_1m']==pytest.approx(-.2)

def test_seasonal_chart_does_not_bridge_vintage_seam(doc):
 r=next(o for o in doc['observations'] if o['metric_id']=='industrial_sa' and o['period']=='2026-08');r['vintage_id']='new_revision'
 m=build_economy(doc)['metrics']['industrial_sa']
 assert m['chart']['vals'][-1]==.54 and all(v is None for v in m['chart']['vals'][:-1])
 assert m['change_1m'] is None

def test_all_catalog_owners_are_exact_bindings(doc):
 from engine.china_economy_store import binding
 for m in doc['catalog'].values():assert len(binding(m['owner_path']))==3

def test_external_money_kept_separate_from_trade_growth(doc):
 s=build_economy(doc);d={r['id']:r for r in s['diagnostics']}
 assert d['fx_conversion_balance']['value']==329
 assert d['external_payment_balance']['value']==pytest.approx(423.2)
 assert s['breadth']['covered']==5
 assert s['metrics']['external_receipts']['pace']['direction']=='unknown'
