from __future__ import annotations
import copy
import hashlib
import importlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]

def api():
    try:
        return importlib.import_module('engine.macro_turnaround_replay')
    except ModuleNotFoundError:
        pytest.fail('The canonical full-vintage adapter/replay is not implemented')

def frame(sid='PPIFIS',n=48):
    rows=[]
    for i in range(n):
        p=date(2018+i//12,i%12+1,1)
        rows.append({'series':sid,'period':pd.Timestamp(p),'realtime_start':pd.Timestamp(p+timedelta(days=35)),
                     'realtime_end':date.max,'value':100+i*.1+math.sin(i*.4),'source_output_type':2})
    return pd.DataFrame(rows)

def bindings(sid='PPIFIS'):
    m=api()
    family='labor' if sid=='PAYEMS' else 'inflation'
    return [m.SeriesBinding(sid,sid,family)]

def source_tree(tmp_path,df=None):
    df=frame() if df is None else df
    raw=b'synthetic parquet bytes; decoder is explicitly injected'
    p=tmp_path/'data/fred_vintage/release_targets/PPIFIS_all_vintages.parquet';p.parent.mkdir(parents=True);p.write_bytes(raw)
    manifest={'schema':'release_target_vintage_collection.v1','integrity_profile':'release_target_artifact_sha256_bytes.v1',
              'source':'FRED/ALFRED','source_output_type':2,'status':'ok','publication_status':'complete','dry_run':False,
              'collected_at':'2026-09-10T10:04:10+00:00','completed_at':'2026-09-10T10:05:13+00:00',
              'realtime_start':'1997-01-01','series':{'PPIFIS':{'status':'written','path':p.relative_to(tmp_path).as_posix(),
              'artifact_bytes':len(raw),'artifact_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(df),
              'periods':df.period.nunique(),'release_dates':df.realtime_start.nunique(),
              'period_min':df.period.min().date().isoformat(),'period_max':df.period.max().date().isoformat()}}}
    mp=p.parent/'manifest.json';mp.write_text(json.dumps(manifest))
    return mp,p,hashlib.sha256(mp.read_bytes()).hexdigest(),df

def test_exact_snapshot_loader_uses_existing_normalizer(tmp_path,monkeypatch):
    m=api();mp,p,h,df=source_tree(tmp_path);called=[]
    owner=m.release_truth.normalize_full_vintage_frame
    def observe(raw,**kw):called.append(len(raw));return owner(raw,**kw)
    monkeypatch.setattr(m.release_truth,'normalize_full_vintage_frame',observe)
    snapshot=m.load_panel(tmp_path,bindings(),h,decoder=lambda b: df)
    assert called==[48]
    assert snapshot.receipt['integrity_verified'] is True
    assert snapshot.receipt['production_parser_executed'] is False
    assert snapshot.receipt['historical_system_availability_proven'] is False
    result=m.replay(snapshot,bindings(),['2022-02-10'],domain='inflation')
    assert result['rows'][0]['selected']['PPIFIS']['period']=='2021-12-01'
    assert result['rows'][0]['selected']['PPIFIS']['value']==df.iloc[-1]['value']
    assert result['authority']['calibrated_forecast'] is False

@pytest.mark.parametrize('damage',['manifest','bytes','same_length_corruption','size','path','state','output_type','dry_run','clock','rows','periods'])
def test_loader_refuses_invalid_integrity_or_cohort(tmp_path,damage):
    m=api();mp,p,h,df=source_tree(tmp_path);j=json.loads(mp.read_text());count=[]
    if damage=='manifest':h='0'*64
    elif damage=='bytes':p.write_bytes(b'changed')
    elif damage=='same_length_corruption':p.write_bytes(b'x'*len(p.read_bytes()))
    elif damage=='size':j['series']['PPIFIS']['artifact_bytes']+=1
    elif damage=='path':j['series']['PPIFIS']['path']='../../secret'
    elif damage=='state':j['publication_status']='partial'
    elif damage=='output_type':j['source_output_type']=4
    elif damage=='dry_run':j['dry_run']=True
    elif damage=='clock':j['completed_at']='2026-09-09T00:00:00+00:00'
    elif damage=='rows':j['series']['PPIFIS']['rows']+=1
    elif damage=='periods':j['series']['PPIFIS']['periods']+=1
    if damage not in ('manifest','bytes'):
        mp.write_text(json.dumps(j));h=hashlib.sha256(mp.read_bytes()).hexdigest()
    def decode(b):count.append(True);return df
    with pytest.raises(ValueError):m.load_panel(tmp_path,bindings(),h,decoder=decode)
    if damage not in ('rows','periods'):assert not count

@pytest.mark.parametrize('field,value',[
 ('value',True),('value','100'),('value',None),('value',float('inf')),('value',float('nan')),
 ('source_output_type',True),('source_output_type',4),('source_output_type','2'),
 ('period','2021-01-05'),('period','2021-W01-1'),('realtime_start','bad'),
 ('realtime_start','2021-01-01T12:00:00Z'),('realtime_end',None),('realtime_end','nonsense'),
 ('series',' ppifis '),('series','PAYEMS'),
])
def test_strict_prevalidation_prevents_silent_normalizer_coercion(field,value):
    m=api();df=frame();df[field]=df[field].astype(object);df.at[0,field]=value
    with pytest.raises(ValueError):m.prepare_panel({'PPIFIS':df})

def test_conflicting_expiration_is_not_deduplicated():
    m=api();df=frame();dup=df.iloc[[0]].copy();dup['realtime_end']=date(2020,1,1)
    with pytest.raises(ValueError,match='conflict'):m.prepare_panel({'PPIFIS':pd.concat([df,dup])})

def test_reversed_interval_is_rejected():
    m=api();df=frame();df.at[0,'realtime_end']=date(2010,1,1)
    with pytest.raises(ValueError,match='interval'):m.prepare_panel({'PPIFIS':df})

def test_missing_marker_refused():
    with pytest.raises(ValueError,match='source_output_type'):api().prepare_panel({'PPIFIS':frame().drop(columns=['source_output_type'])})

def test_cutoff_selects_latest_active_revision_and_honors_inclusive_end():
    m=api();df=frame();old=df.iloc[-1].copy();end=date(2022,2,10);df.at[47,'realtime_end']=end
    revised=old.copy();revised['realtime_start']=pd.Timestamp('2022-02-11');revised['value']=200.0
    panel=m.prepare_panel({'PPIFIS':pd.concat([df,pd.DataFrame([revised])],ignore_index=True)})
    report=m.replay(panel,bindings(),['2022-02-11','2022-02-10'],domain='inflation')
    assert [x['selected']['PPIFIS']['value'] for x in report['rows']]==[old['value'],200.0]
    assert report['rows'][1]['assessment']['previous_phase']==report['rows'][0]['assessment']['phase']

def test_expired_latest_period_is_not_replaced_by_older_active_period():
    m=api();df=frame();df.at[47,'realtime_end']=date(2022,2,1)
    report=m.replay(m.prepare_panel({'PPIFIS':df}),bindings(),['2022-02-10'],domain='inflation')
    assert report['rows'][0]['unavailable']['PPIFIS']=='latest_period_has_no_active_vintage'
    assert report['rows'][0]['assessment']['phase']=='indeterminate'

def test_holes_in_monthly_history_are_not_compacted_into_time():
    m=api();df=frame().drop(index=30)
    row=m.replay(m.prepare_panel({'PPIFIS':df}),bindings(),['2022-02-10'],domain='inflation')['rows'][0]
    assert row['unavailable']['PPIFIS']=='incomplete_active_monthly_history'
    assert row['assessment']['confidence']==0

def test_future_extension_and_input_order_preserve_all_historical_rows():
    m=api();df=frame();base=m.prepare_panel({'PPIFIS':df});future=df.copy();future['realtime_start']=pd.Timestamp('2023-01-01');future['value']+=30
    extended=df.copy();extended['realtime_end']=date(2022,12,31)
    latter=m.prepare_panel({'PPIFIS':pd.concat([extended,future]).sample(frac=1,random_state=19)})
    a=m.replay(base,bindings(),['2021-06-10','2022-02-10'],domain='inflation')
    b=m.replay(latter,bindings(),['2022-02-10','2021-06-10'],domain='inflation')
    assert a['rows']==b['rows']

def test_panel_is_detached_from_mutable_input():
    m=api();df=frame();p=m.prepare_panel({'PPIFIS':df});a=m.replay(p,bindings(),['2022-02-10'],domain='inflation')
    df.loc[:,'value']=10.0
    assert m.replay(p,bindings(),['2022-02-10'],domain='inflation')==a

def test_growth_panel_preserves_missing_families():
    m=api();bs=[m.SeriesBinding('payrolls','PAYEMS','labor')]+[m.SeriesBinding(k,None,k) for k in ('activity','housing','consumer','credit')]
    r=m.replay(m.prepare_panel({'PAYEMS':frame('PAYEMS')}),bs,['2022-02-10'],domain='growth')['rows'][0]
    assert r['assessment']['quality']['coverage']==pytest.approx(.2)
    assert r['assessment']['phase']=='indeterminate'
    assert set(r['unavailable'])=={'activity','housing','consumer','credit'}

@pytest.mark.parametrize('family',['activity','labor','housing','credit','consumer'])
def test_price_index_cannot_impersonate_a_growth_family(family):
    with pytest.raises(ValueError,match='family'):api().SeriesBinding('x','PPIFIS',family)

def test_inflation_series_cannot_enter_growth_assessment():
    m=api()
    with pytest.raises(ValueError,match='growth'):m.replay(m.prepare_panel({'PPIFIS':frame()}),bindings(),['2022-02-10'],domain='growth')

def test_duplicate_binding_cannot_manufacture_breadth():
    m=api();bs=[m.SeriesBinding('x','PPIFIS','inflation'),m.SeriesBinding('y','PPIFIS','inflation')]
    with pytest.raises(ValueError,match='duplicate'):m.replay(m.prepare_panel({'PPIFIS':frame()}),bs,['2022-02-10'],domain='inflation')

def test_duplicate_or_intraday_cutoffs_refused():
    m=api();p=m.prepare_panel({'PPIFIS':frame()})
    for ds in (['2022-02-10','2022-02-10'],['2022-02-10T08:00:00Z']):
        with pytest.raises(ValueError):m.replay(p,bindings(),ds,domain='inflation')

def test_observed_movement_is_distinct_from_standardized_anomaly():
    m=api();r=m.replay(m.prepare_panel({'PPIFIS':frame()}),bindings(),['2022-02-10'],domain='inflation')['rows'][0]
    observed=r['selected']['PPIFIS']['movement']
    assert observed['change']==pytest.approx(frame().iloc[-1]['value']-frame().iloc[-2]['value'])
    assert observed['direction'] in ('rising','falling','unchanged')
    assert observed['is_forecast'] is False
    assert 'anomaly' in r['method_note']

def test_raw_first_shock_survives_even_when_standardization_is_unavailable():
    m=api();df=frame();df['value']=100.0;df.at[47,'value']=150.0
    r=m.replay(m.prepare_panel({'PPIFIS':df}),bindings(),['2022-02-10'],domain='inflation')['rows'][0]
    assert r['selected']['PPIFIS']['movement']['change']==50.0
    assert r['selected']['PPIFIS']['movement']['direction']=='rising'
    assert r['assessment']['confidence']==0.0
    assert r['assessment']['quality']['excluded']['PPIFIS']=='unidentifiable_feature_scale'

def test_growth_request_must_declare_missing_families_not_drop_them():
    m=api();p=m.prepare_panel({'PAYEMS':frame('PAYEMS')})
    with pytest.raises(ValueError,match='five.*families'):
        m.replay(p,bindings('PAYEMS'),['2022-02-10'],domain='growth')

def test_every_selected_file_is_checked_before_any_decoder_runs(tmp_path):
    m=api();mp,p,h,df=source_tree(tmp_path);manifest=json.loads(mp.read_text())
    entry=copy.deepcopy(manifest['series']['PPIFIS']);entry['path']='data/fred_vintage/release_targets/CPILFESL_all_vintages.parquet'
    manifest['series']['CPILFESL']=entry
    (mp.parent/'CPILFESL_all_vintages.parquet').write_bytes(b'corrupt second file')
    mp.write_text(json.dumps(manifest));h=hashlib.sha256(mp.read_bytes()).hexdigest();calls=[]
    bs=bindings()+[m.SeriesBinding('core','CPILFESL','inflation')]
    with pytest.raises(ValueError,match='integrity'):
        m.load_panel(tmp_path,bs,h,decoder=lambda b:calls.append(True))
    assert calls==[]

def test_decoder_receives_the_verified_snapshot_not_a_reread_path(tmp_path):
    m=api();mp,p,h,df=source_tree(tmp_path);before=p.read_bytes()
    def decode(stream):
        p.write_bytes(b'concurrent path replacement')
        assert stream.read()==before
        return df
    panel=m.load_panel(tmp_path,bindings(),h,decoder=decode)
    assert panel.receipt['source_files']['PPIFIS']['artifact_sha256']==hashlib.sha256(before).hexdigest()
    assert panel.receipt['integrity_verified']

def test_source_receipt_cannot_be_mutated_through_a_reader():
    m=api();p=m.prepare_panel({'PPIFIS':frame()});receipt=p.receipt;receipt['integrity_verified']=True
    assert p.receipt['integrity_verified'] is False


def test_overlapping_vintage_intervals_use_latest_start():
    m=api();df=frame();revision=df.iloc[-1].copy()
    revision['realtime_start']=pd.Timestamp('2022-02-11');revision['value']=200.0
    panel=m.prepare_panel({'PPIFIS':pd.concat([df,pd.DataFrame([revision])],ignore_index=True)})
    r=m.replay(panel,bindings(),['2022-02-11'],domain='inflation')['rows'][0]
    assert r['selected']['PPIFIS']['value']==200.0
    assert r['selected']['PPIFIS']['vintage_start']=='2022-02-11'

def test_signed_zero_duplicate_order_does_not_change_replay_identity():
    m=api();df=frame();df.at[47,'value']=0.0;dup=df.iloc[[-1]].copy();dup['value']=-0.0
    left=m.prepare_panel({'PPIFIS':pd.concat([df,dup],ignore_index=True)})
    right=m.prepare_panel({'PPIFIS':pd.concat([dup,df],ignore_index=True)})
    assert m.replay(left,bindings(),['2022-02-10'],domain='inflation')==m.replay(right,bindings(),['2022-02-10'],domain='inflation')

def test_report_contains_a_reconstructible_profile_not_only_configuration_hash():
    m=api();p=m.prepare_panel({'PPIFIS':frame()});r=m.replay(p,bindings(),['2022-02-10'],domain='inflation')
    from engine.macro_turnaround import TurnaroundConfig
    bs=[m.SeriesBinding(**x) for x in r['profile']['bindings']]
    config=TurnaroundConfig.from_dict(r['profile']['config'])
    assert m.replay(p,bs,[x['as_of'] for x in r['rows']],domain=r['domain'],config=config)==r

def test_family_evidence_distinguishes_observed_but_unusable_from_missing():
    m=api();df=frame();df['value']=100.0;df.at[47,'value']=150.0
    r=m.replay(m.prepare_panel({'PPIFIS':df}),bindings(),['2022-02-10'],domain='inflation')['rows'][0]
    assert r['family_evidence']['inflation']=={'configured_keys':['PPIFIS'],'observed_keys':['PPIFIS'],'usable_keys':[],'excluded_keys':['PPIFIS']}

def test_missing_family_names_survive_arbitrary_indicator_keys():
    m=api();bs=[m.SeriesBinding('p','PAYEMS','labor')]+[m.SeriesBinding(f'x{i}',None,f) for i,f in enumerate(('activity','housing','consumer','credit'))]
    r=m.replay(m.prepare_panel({'PAYEMS':frame('PAYEMS')}),bs,['2022-02-10'],domain='growth')['rows'][0]
    assert set(r['family_evidence'])=={'labor','activity','housing','consumer','credit'}
    assert r['family_evidence']['credit']['configured_keys']==['x3']
    assert r['family_evidence']['credit']['observed_keys']==[]

def test_backfilled_old_periods_do_not_imply_old_decision_time_coverage():
    m=api();df=frame();df['realtime_start']=pd.Timestamp('2026-01-01')
    r=m.replay(m.prepare_panel({'PPIFIS':df}),bindings(),['2022-02-10'],domain='inflation')['rows'][0]
    assert r['unavailable']['PPIFIS']=='no_vintage_available_at_cutoff'
    assert r['assessment']['score_status']=='unavailable'
    assert not r['selected']


def test_growth_replay_rejects_inflation_with_the_specific_boundary(tmp_path):
    m = api()
    _, _, manifest_hash, df = source_tree(tmp_path)
    panel = m.load_panel(tmp_path, bindings(), manifest_hash, decoder=lambda _: df)

    with pytest.raises(ValueError, match="inflation cannot stand in for growth evidence"):
        m.replay(panel, bindings(), ["2022-02-10"], domain="growth")


def test_replay_future_period_with_early_release_is_invisible():
    m = api()
    df = frame()
    cutoff = "2022-02-10"
    baseline = m.replay(m.prepare_panel({"PPIFIS": df}), bindings(), [cutoff], domain="inflation")
    future = df.iloc[-1].copy()
    future["period"] = pd.Timestamp("2022-03-01")
    future["realtime_start"] = pd.Timestamp("2022-02-01")
    future["realtime_end"] = date.max
    future["value"] = 1_000_000.0
    extended = pd.concat([df, pd.DataFrame([future])], ignore_index=True)

    assert m.replay(
        m.prepare_panel({"PPIFIS": extended}), bindings(), [cutoff], domain="inflation"
    ) == baseline


def test_load_panel_discloses_a_missing_requested_source(tmp_path):
    m = api()
    _, _, manifest_hash, df = source_tree(tmp_path)
    requested = bindings() + [m.SeriesBinding("payrolls", "PAYEMS", "labor")]
    panel = m.load_panel(tmp_path, requested, manifest_hash, decoder=lambda _: df)

    assert panel.receipt["missing_source_series"] == ["PAYEMS"]
    assert panel.series_ids == ("PPIFIS",)


def test_load_panel_refuses_when_every_requested_source_is_missing(tmp_path):
    m = api()
    _, _, manifest_hash, _ = source_tree(tmp_path)
    requested = [m.SeriesBinding("payrolls", "PAYEMS", "labor")]

    with pytest.raises(ValueError, match="no requested full-vintage source"):
        m.load_panel(tmp_path, requested, manifest_hash, decoder=lambda _: frame("PAYEMS"))
