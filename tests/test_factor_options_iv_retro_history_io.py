"""Hermetic exact-byte and year-bound PRIVATE history CLI acceptance."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import hashlib, io, json, subprocess, sys
import numpy as np
import pandas as pd
import pytest
from lib.us_cash_calendar import sessions_between

MODULE='research.factor_atlas.session3.run_retro_iv_history'
ANCHOR=date(2026,10,8)
NOW=datetime(2026,10,11,22,tzinfo=timezone.utc)
DAYS=sessions_between(ANCHOR-timedelta(days=400),ANCHOR)[-252:]
ROOTS=('AAA','BBB','CCC')

@pytest.fixture
def m():
    from importlib import import_module
    path=Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/run_retro_iv_history.py'
    assert path.exists(),'bounded IV-year source reader absent'
    return import_module(MODULE)

@pytest.fixture
def source(tmp_path):
    repo=tmp_path/'source';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    def blob(data):
        return subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--stdin'],input=data).decode().strip()
    registry={'baskets':{'mag7':{'weighting':'equal','members':[{'ticker':r,'added':'2023-05-09','removed':None} for r in ROOTS]}}}
    member_blob=blob(json.dumps(registry).encode())
    store=tmp_path/'greek-store';store.mkdir()
    rootmap={}
    for index,root in enumerate(ROOTS):
        entries=[]
        for i,day in enumerate(DAYS):
            for days in (29,36):
                for side in ('C','P'):
                    entries.append({'date':pd.Timestamp(day),'root':root,'expiration':pd.Timestamp(day)+pd.Timedelta(days=days),
                        'right':side,'strike':100.,'bid':9.5,'ask':10.,'underlying_price':100.,
                        'implied_vol':.22+.0004*i+.01*index,'iv_error':0.})
        frame=pd.DataFrame(entries)
        year_hash={}
        for year,part in frame.groupby(frame.date.dt.year):
            p=store/'greeks'/root/f'{year}.parquet'
            p.parent.mkdir(parents=True,exist_ok=True)
            part.to_parquet(p,index=False)
            year_hash[str(year)]=hashlib.sha256(p.read_bytes()).hexdigest()
        rootmap[root]={'years':year_hash}
    manifest={'schema':'factor_atlas.s3.private_iv_history_inputs/v1','basket_id':'mag7',
              'anchor':ANCHOR.isoformat(),'membership_blob':member_blob,'roots':rootmap}
    return {'manifest':manifest,'source_repository':repo,'store_root':store,'captured_at':NOW}

def test_complete_252_synthetic_year_files_produce_private_rank(m,source):
    r=m.load_private_iv_history(**source)
    assert r['coverage']['complete_sessions']==252
    assert r['stats']['iv_rank_minmax_pct']==pytest.approx(100)
    assert r['stats']['iv_percentile_midrank_pct']==pytest.approx(100*251.5/252)
    assert r['product']['iv_rank'] is None
    assert len(r['source_receipts']['roots'])==3
    assert r['source_receipts']['source_use_status']=='RETROSPECTIVE_UNQUALIFIED'
    assert len(r['measurement_sha256'])==64
    json.dumps(r,allow_nan=False)

def test_changed_source_sha_refused_before_selection(m,source):
    p=source['store_root']/'greeks'/'AAA'/'2026.parquet'
    with p.open('ab') as f:f.write(b'TAMPER')
    with pytest.raises(ValueError,match='digest'):
        m.load_private_iv_history(**source)

def test_missing_year_or_root_stays_in_original_population(m,source):
    (source['store_root']/'greeks'/'AAA'/'2025.parquet').unlink()
    r=m.load_private_iv_history(**source)
    assert 0<r['coverage']['complete_sessions']<252
    assert r['coverage']['per_root']['AAA']<252
    assert r['stats']['iv_rank_minmax_pct'] is None
    assert len(r['population']['roots'])==3

def test_missing_entire_member_source_refuses_full_history(m,source):
    source['manifest']['roots'].pop('AAA')
    r=m.load_private_iv_history(**source)
    assert r['coverage']['complete_sessions']==0
    assert r['stats']['current_mean_iv'] is None
    assert r['population']['roots']==list(ROOTS)

def test_nested_year_symlink_escape_is_denied(m,source,tmp_path):
    path=source['store_root']/'greeks'/'AAA'/'2025.parquet'
    foreign=tmp_path/'foreign.parquet';path.rename(foreign)
    path.symlink_to(foreign)
    with pytest.raises(ValueError,match='tier'):
        m.load_private_iv_history(**source)

def test_existing_external_owner_tier_binding_allowed(m,source,tmp_path):
    tier=source['store_root']/'greeks'
    external=tmp_path/'existing-root-tier';tier.rename(external)
    tier.symlink_to(external,target_is_directory=True)
    assert m.load_private_iv_history(**source)['coverage']['complete_sessions']==252

def test_unrecognized_root_or_certification_fields_refused(m,source):
    source['manifest']['roots']['EXTRA']={}
    with pytest.raises(ValueError,match='root'):
        m.load_private_iv_history(**source)
    source['manifest']['roots'].pop('EXTRA')
    source['manifest']['qualified']=True
    with pytest.raises(ValueError,match='manifest'):
        m.load_private_iv_history(**source)

def test_greek_year_hash_must_be_exact(m,source):
    source['manifest']['roots']['AAA']['years']['2026']='HEAD'
    with pytest.raises(ValueError,match='digest'):
        m.load_private_iv_history(**source)

def test_capture_a_day_before_source_anchor_refuses(m,source):
    source['captured_at']=datetime(2026,10,7,22,tzinfo=timezone.utc)
    with pytest.raises(ValueError,match='capture'):
        m.load_private_iv_history(**source)

def test_source_read_only_and_measurement_reproducible(m,source):
    old={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source['store_root'].rglob('*.parquet')}
    a=m.load_private_iv_history(**source)
    source['captured_at']=NOW+timedelta(minutes=20)
    b=m.load_private_iv_history(**source)
    assert a['measurement_sha256']==b['measurement_sha256']
    assert a['captured_at']!=b['captured_at']
    assert old=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source['store_root'].rglob('*.parquet')}

def test_future_day_ignored_even_if_embedded_in_same_year_source(m,source):
    root='AAA'; p=source['store_root']/'greeks'/root/'2026.parquet'
    data=pd.read_parquet(p)
    future=data.loc[data.date==pd.Timestamp(ANCHOR)].copy()
    future['date']=pd.Timestamp(ANCHOR)+pd.Timedelta(days=1)
    future['implied_vol']=1.5
    combined=pd.concat([data,future],ignore_index=True)
    combined.to_parquet(p,index=False)
    source['manifest']['roots'][root]['years']['2026']=hashlib.sha256(p.read_bytes()).hexdigest()
    a=m.load_private_iv_history(**source)
    assert a['stats']['iv_rank_minmax_pct']==pytest.approx(100)
    assert a['coverage']['complete_sessions']==252

def test_cli_rejects_duplicate_json_keys_without_stdout(m,source,tmp_path):
    file=tmp_path/'bad.json';file.write_text('{"anchor":"2026-10-08","anchor":"2026-10-09"}')
    cmd=[sys.executable,'-B','-m',MODULE,'--manifest',str(file),'--source-repository',str(source['source_repository']),
         '--store-root',str(source['store_root'])]
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode!=0 and result.stdout=='' and 'duplicate' in result.stderr.lower()

def test_unqualified_real_history_does_not_use_product_producer_api(m):
    file=Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/run_retro_iv_history.py'
    txt=file.read_text()
    for forbidden in ('supabase','requests.get','httpx.Client','options_hub.publish','prophet_bridge'):
        assert forbidden not in txt

def test_private_iv_history_registered_in_existing_options_code_group():
    import yaml
    root=Path(__file__).resolve().parents[1]
    manifest=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())
    job=manifest['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    paths=set(job['paths'])
    for p in ('research/factor_atlas/session3/retrospective_iv_history.py',
              'research/factor_atlas/session3/run_retro_iv_history.py',
              'research/factor_atlas/session3/mag7_retrospective_iv_history_inputs.json',
              'tests/test_factor_options_iv_retro_history.py',
              'tests/test_factor_options_iv_retro_history_io.py'):
        assert p in paths, p
    commands='\n'.join(x.get('run','') for x in job['steps'])
    assert 'tests/test_factor_options_iv_retro_history.py' in commands
    assert 'tests/test_factor_options_iv_retro_history_io.py' in commands
