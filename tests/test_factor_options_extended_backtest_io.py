"""Hermetic canonical-byte 35-day Episode longitudinal runner tests."""
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from importlib import import_module
import hashlib,io,json,subprocess,sys,fcntl
import numpy as np,pandas as pd,pytest
from lib.us_cash_calendar import sessions_between

MODULE='research.factor_atlas.session3.run_extended_backtest'
CAPTURE=datetime(2026,10,11,22,tzinfo=timezone.utc)
ROOTS=('AAA','BBB','CCC')
START=date(2024,1,2)
LAST=date(2024,3,17)

@pytest.fixture
def m():
    assert (Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/run_extended_backtest.py').exists(),'source-bound extended owner reader not implemented'
    return import_module(MODULE)

@pytest.fixture
def source(tmp_path):
    repo=tmp_path/'original_git';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    def blob(raw):
        return subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--stdin'],input=raw).decode().strip()
    from research.factor_atlas.session3.extended_backtest import build_fixed_schedule
    sessions=sessions_between(date(2022,1,3),date(2025,2,28))
    anchors=build_fixed_schedule(start=START,last_nominal=LAST,sessions=sessions)
    assert len(anchors)==3
    store=tmp_path/'existing_store';store.mkdir();(store/'_writer.lock').touch()
    manifest_roots={}
    for i,root in enumerate(ROOTS):
        r=np.random.default_rng(i+41)
        ix=pd.to_datetime(sessions)
        closes=pd.DataFrame({'close':100*np.exp(np.cumsum(r.normal(.0002,.01,len(ix))))},index=ix)
        raw=io.BytesIO();closes.to_parquet(raw)
        priceblob=blob(raw.getvalue())
        rows=[]
        for a in anchors:
            for dte in (29,36):
                for side in ('C','P'):
                    rows.append({'root':root,'date':pd.Timestamp(a),'expiration':pd.Timestamp(a)+pd.Timedelta(days=dte),
                     'right':side,'strike':100.,'bid':9.5,'ask':10.,'underlying_price':100.,
                     'implied_vol':.2+.015*i,'iv_error':0.})
        greek=store/'greeks'/root/'2024.parquet';greek.parent.mkdir(parents=True)
        pd.DataFrame(rows).to_parquet(greek,index=False)
        manifest_roots[root]={'price_blob':priceblob,'years':{'2024':hashlib.sha256(greek.read_bytes()).hexdigest()}}
    registry={'baskets':{'mag7':{'weighting':'equal','members':[{'ticker':x,'added':'2023-05-09','removed':None} for x in ROOTS]}}}
    membership=blob(json.dumps(registry).encode())
    manifest={'schema':'factor_atlas.s3.extended_35day_inputs/v1',
     'basket_id':'mag7','membership_blob':membership,'start_anchor':START.isoformat(),
     'last_nominal':LAST.isoformat(),'source_price_column':'close','roots':manifest_roots}
    return dict(manifest=manifest,source_repository=repo,store_root=store,captured_at=CAPTURE)

def test_exact_source_3_case_hermetic_history_runner(m,source):
    result=m.load_extended_backtest(**source)
    assert result['count_total']==3 and result['count_evaluable']==3
    assert result['longitudinal_summary']['count_declared']==3
    assert result['longitudinal_summary']['paired_sample_n']==3
    assert result['historical_known_at'] is None
    assert result['claims']['predictive_edge_proven'] is False
    assert result['source_receipts']['greeks_year_file_count_verified']==3
    assert result['source_receipts']['original_source_data_mutated'] is False
    assert len(result['measurement_sha256'])==64
    assert result['source_receipts']['source_rights']=='NOT_CERTIFIED'
    json.dumps(result,allow_nan=False)

def test_missing_year_source_file_keeps_original_population(m,source):
    (source['store_root']/'greeks/AAA/2024.parquet').unlink()
    out=m.load_extended_backtest(**source)
    assert out['count_total']==3 and out['count_evaluable']==0
    assert all(case['iv_coverage_count']==2 for case in out['cases'])
    assert out['longitudinal_summary']['incomplete_population_count']==3

def test_hash_mismatch_refuses_untouched_original_data(m,source):
    x=source['store_root']/'greeks/AAA/2024.parquet'
    with x.open('ab') as f:f.write(b'MODIFIED')
    with pytest.raises(ValueError,match='digest'):m.load_extended_backtest(**source)

def test_missing_membership_root_preserves_full_weight(m,source):
    source['manifest']['roots'].pop('AAA')
    out=m.load_extended_backtest(**source)
    assert out['count_total']==3 and out['count_evaluable']==0
    assert all(case['original_count']==3 for case in out['cases'])

def test_unknown_root_name_refused(m,source):
    source['manifest']['roots']['EXTRA']={'price_blob':'a'*40,'years':{}}
    with pytest.raises(ValueError,match='root'):
        m.load_extended_backtest(**source)

def test_explicit_fake_source_quality_admission_refused(m,source):
    source['manifest']['source_quality_certified']=True
    with pytest.raises(ValueError,match='manifest'):
        m.load_extended_backtest(**source)

def test_source_lookback_unchanged_when_price_future_is_modified(m,source):
    a=m.load_extended_backtest(**source)
    # Replacing a bound Git price blob causes a new source SHA but cannot affect
    # the *first* prediction when only post-first-anchor closes were modified.
    root='AAA';repo=source['source_repository'];sha=source['manifest']['roots'][root]['price_blob']
    data=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',sha])
    prices=pd.read_parquet(io.BytesIO(data))
    after=pd.Timestamp(a['cases'][0]['exit_session'])
    prices.loc[after,'close']*=2
    buf=io.BytesIO();prices.to_parquet(buf)
    sha2=subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--stdin'],input=buf.getvalue()).decode().strip()
    source['manifest']['roots'][root]['price_blob']=sha2
    b=m.load_extended_backtest(**source)
    assert a['cases'][0]['expected_move']==pytest.approx(b['cases'][0]['expected_move'])
    assert a['cases'][0]['historical_rv_move']==pytest.approx(b['cases'][0]['historical_rv_move'])
    assert a['cases'][0]['realized_return']!=pytest.approx(b['cases'][0]['realized_return'])

def test_source_read_only_deterministic_and_capture_does_not_change_cohort(m,source):
    originals={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source['store_root'].rglob('*.parquet')}
    a=m.load_extended_backtest(**source)
    source['captured_at']=CAPTURE+timedelta(minutes=11)
    b=m.load_extended_backtest(**source)
    assert a['measurement_sha256']==b['measurement_sha256']
    assert originals=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source['store_root'].rglob('*.parquet')}

def test_external_original_greek_tier_binding_allowed(m,source,tmp_path):
    tier=source['store_root']/'greeks';other=tmp_path/'existing-canonical-tier'
    tier.rename(other);tier.symlink_to(other,target_is_directory=True)
    assert m.load_extended_backtest(**source)['count_evaluable']==3

def test_nested_nonowner_symlink_refused(m,source,tmp_path):
    old=source['store_root']/'greeks/AAA/2024.parquet';other=tmp_path/'other.parquet'
    old.rename(other);old.symlink_to(other)
    with pytest.raises(ValueError,match='tier'):
        m.load_extended_backtest(**source)

def test_coordinator_source_lock_held_by_external_writer_refused(m,source):
    lock=source['store_root']/'_writer.lock'
    # Spawn is the default on macOS; an embedded local multiprocessing
    # function is not pickleable. A bounded short-lived child creates one
    # actual OS advisory lock, with guaranteed join/cleanup.
    code=(
      "import sys,fcntl; "
      "f=open(sys.argv[1],'rb'); "
      "fcntl.flock(f.fileno(),fcntl.LOCK_EX); "
      "print('LOCKED',flush=True); "
      "sys.stdin.readline(); "
      "fcntl.flock(f.fileno(),fcntl.LOCK_UN)"
    )
    proc=subprocess.Popen([sys.executable,'-c',code,str(lock)],
           stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert proc.stdout.readline().strip()=='LOCKED'
        with pytest.raises(ValueError,match='writer lock'):
            m.load_extended_backtest(**source)
    finally:
        if proc.poll() is None:
            proc.stdin.write('DONE\n')
            proc.stdin.flush()
        proc.communicate(timeout=5)


def test_cli_invalid_duplicate_json_fails_no_private_stdout(m,source,tmp_path):
    p=tmp_path/'bad.json';p.write_text('{"start_anchor":"2024-01-02","start_anchor":"2024-01-03"}')
    r=subprocess.run([sys.executable,'-B','-m',MODULE,
        '--manifest',str(p),'--source-repository',str(source['source_repository']),
        '--store-root',str(source['store_root'])],capture_output=True,text=True)
    assert r.returncode!=0 and r.stdout=='' and 'duplicate' in r.stderr.lower()

def test_zero_original_source_years_not_equivalent_qualified_history(m,source):
    source['manifest']['roots']['AAA']['years']={}
    out=m.load_extended_backtest(**source)
    assert out['count_evaluable']==0
    assert out['source_receipts']['roots']['AAA']['years']['2024']['status']=='NOT_DECLARED'

def test_explicit_tolerance_research_expands_only_numeric_eligibility(m,source):
    root='AAA';p=source['store_root']/'greeks'/root/'2024.parquet'
    df=pd.read_parquet(p)
    first=pd.Timestamp(START)
    assert df.loc[df.date==first].shape[0]==4
    df.loc[df.date==first,'iv_error']=[.00001,-.00002,.00003,-.00004]
    df.to_parquet(p,index=False)
    source['manifest']['roots'][root]['years']['2024']=hashlib.sha256(p.read_bytes()).hexdigest()
    baseline=m.load_extended_backtest(**source)
    assert baseline['count_total']==3 and baseline['count_evaluable']==2
    loose=m.load_extended_backtest(**source,research_iv_error_abs_max=5e-5)
    assert loose['count_evaluable']==3
    assert loose['research_sensitivity']=={
      'iv_error_abs_max':5e-5,'only_research':True,
      'original_strict_baseline_unchanged':True,'historical_quote_quality_certified':False,
      'publication_eligible':False
    }
    assert loose['source_receipts']['source_rights']=='NOT_CERTIFIED'
    assert loose['claims']['predictive_edge_proven']==False
    assert baseline.get('research_sensitivity') is None

@pytest.mark.parametrize('bad',[-.1,True,False,'0.00005',float('nan'),float('inf'),.001,1])
def test_unregistered_residual_sensitivity_refused(m,source,bad):
    with pytest.raises(ValueError,match='threshold'):
        m.load_extended_backtest(**source,research_iv_error_abs_max=bad)

def test_zero_tolerance_call_is_byte_identical_to_default(m,source):
    baseline=m.load_extended_backtest(**source)
    explicit_zero=m.load_extended_backtest(**source,research_iv_error_abs_max=0.)
    assert baseline==explicit_zero

def test_extended_study_enrolled_only_in_incumbent_options_code_group():
    import yaml
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    expected={'research/factor_atlas/session3/extended_backtest.py',
              'research/factor_atlas/session3/run_extended_backtest.py',
              'research/factor_atlas/session3/mag7_extended_35day_inputs.json',
              'tests/test_factor_options_extended_backtest.py',
              'tests/test_factor_options_extended_backtest_io.py'}
    assert expected.issubset(set(job['paths']))
    commands='\n'.join(step.get('run','') for step in job['steps'])
    assert 'tests/test_factor_options_extended_backtest.py' in commands
    assert 'tests/test_factor_options_extended_backtest_io.py' in commands

def test_original_hermetic_source_proper_scores_are_separate_from_predictions(m,source):
    out=m.load_extended_backtest(**source)
    sc=out['volatility_scoring']
    assert sc['pair_count']==3
    assert sc['count_declared']==3
    assert sc['mean_qlike_model'] is not None
    assert sc['option_trade_pnl_measured'] is False
    assert sc['predictive_edge_proven'] is False
    assert out['claims']['predictive_edge_proven'] is False
