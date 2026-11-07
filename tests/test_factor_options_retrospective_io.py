"""Bounded real-reader tests use only temporary synthetic source repositories."""
from datetime import date,datetime,timedelta,timezone
from importlib import import_module
from pathlib import Path
import hashlib,io,json,os,subprocess,sys
import numpy as np
import pandas as pd
import pytest
from lib.us_cash_calendar import sessions_between

ANCHOR=date(2026,10,8)
CAPTURED=datetime(2026,10,11,22,tzinfo=timezone.utc)
MODULE='research.factor_atlas.session3.run_retrospective'

def test_native_research_reader_exists():
    assert (Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/run_retrospective.py').is_file(), 'read-only research CLI missing'

@pytest.fixture
def m():
    return import_module(MODULE)

@pytest.fixture
def source(tmp_path):
    repo=tmp_path/'source';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    def blob(data):
        return subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--stdin'],input=data).decode().strip()
    store=tmp_path/'original-store';store.mkdir()
    roots=['AAA','BBB','CCC']; rows=[]; manifest_roots={}
    dates=pd.to_datetime(sessions_between(ANCHOR-timedelta(days=500),ANCHOR)[-270:])
    rng=np.random.default_rng(413)
    for i,r in enumerate(roots):
        frame=pd.DataFrame({'close':100*np.exp(np.cumsum(rng.normal(0,.01,len(dates))))},index=dates)
        raw=io.BytesIO();frame.to_parquet(raw)
        pdata=raw.getvalue();price=blob(pdata)
        g=[]
        for days in (29,36):
            for side in ('C','P'):
                g.append(dict(root=r,date=pd.Timestamp(ANCHOR),expiration=pd.Timestamp(ANCHOR)+pd.Timedelta(days=days),
                              strike=100.,right=side,bid=9.5,ask=10.,underlying_price=100.,implied_vol=.2+i*.05,iv_error=0.))
        path=store/'greeks'/r/'2026.parquet';path.parent.mkdir(parents=True);pd.DataFrame(g).to_parquet(path,index=False)
        manifest_roots[r]={'price_blob':price,'greeks_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        rows.append({'ticker':r,'added':'2020-01-01','removed':None})
    registry={'baskets':{'mag7':{'weighting':'equal','members':rows}}}
    reg=blob(json.dumps(registry).encode())
    manifest={'schema':'factor_atlas.s3.retrospective_inputs/v1','anchor':ANCHOR.isoformat(),
              'basket_id':'mag7','membership_blob':reg,'roots':manifest_roots,'price_column':'close'}
    return {'manifest':manifest,'source_repository':repo,'store_root':store,'captured_at':CAPTURED}

def test_reads_original_files_without_source_write(m,source):
    store=source['store_root'];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in store.rglob('*.parquet')}
    r=m.load_study(**source)
    assert r['coverage']['count']==3 and r['models']['252']['move'] is not None
    assert r['product']['expected_move'] is None and r['authority']['publication'] is False
    assert len(r['source_receipts']['roots'])==3
    assert {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in store.rglob('*.parquet')}==before
    json.dumps(r,allow_nan=False)

def test_tampered_greek_file_refused(m,source):
    p=source['store_root']/'greeks/AAA/2026.parquet'
    with p.open('ab') as f:f.write(b'tampered')
    with pytest.raises(ValueError,match='digest'):m.load_study(**source)

def test_missing_file_is_explicit_not_renormalized(m,source):
    (source['store_root']/'greeks/AAA/2026.parquet').unlink()
    r=m.load_study(**source)
    assert r['coverage']['count']==2 and r['coverage']['total_count']==3
    assert r['models']['252']['move'] is None

def test_absent_root_stays_in_denominator(m,source):
    source['manifest']['roots'].pop('AAA')
    r=m.load_study(**source)
    assert r['coverage']['total_count']==3 and r['coverage']['count']==2
    assert r['models']['252']['move'] is None

def test_root_not_in_membership_refused_before_loading(m,source):
    source['manifest']['roots']['EXTRA']={}
    with pytest.raises(ValueError,match='membership'):m.load_study(**source)

@pytest.mark.parametrize('sha',['HEAD','main;echo BAD','../other','0'*39,True])
def test_git_object_identity_strict(m,source,sha):
    source['manifest']['membership_blob']=sha
    with pytest.raises(ValueError,match='object'):m.load_study(**source)

def test_ad_hoc_qualification_flag_rejected(m,source):
    source['manifest']['qualified']=True
    with pytest.raises(ValueError,match='fields'):m.load_study(**source)

def test_measurement_digest_ignores_replay_wall_clock(m,source):
    a=m.load_study(**source)
    source['captured_at']=CAPTURED+timedelta(minutes=10)
    b=m.load_study(**source)
    assert a['measurement_sha256']==b['measurement_sha256']
    assert a['captured_at']!=b['captured_at']

def test_cli_bad_manifest_writes_no_numeric_stdout(m,source,tmp_path):
    p=tmp_path/'bad.json';p.write_text('{"anchor":"2026-10-08","anchor":"2026-10-09"}')
    r=subprocess.run([sys.executable,'-B','-m',MODULE,'--manifest',str(p),'--source-repository',str(source['source_repository']),
                      '--store-root',str(source['store_root'])],capture_output=True,text=True)
    assert r.returncode!=0 and r.stdout==''
    assert 'duplicate' in r.stderr.lower()

def test_git_reader_disables_lazy_fetch_and_replacements(m,source,monkeypatch):
    calls=[];real=m.subprocess.run
    def record(*args,**kwargs):
        calls.append(kwargs.get('env',{}));return real(*args,**kwargs)
    monkeypatch.setattr(m.subprocess,'run',record)
    m.load_study(**source)
    assert calls and all(x.get('GIT_NO_LAZY_FETCH')=='1' and x.get('GIT_NO_REPLACE_OBJECTS')=='1' for x in calls)

def test_original_owner_tier_symlink_is_supported(m,source,tmp_path):
    tier=source['store_root']/'greeks';external=tmp_path/'existing-owner-greeks'
    tier.rename(external);tier.symlink_to(external,target_is_directory=True)
    result=m.load_study(**source)
    assert result['coverage']['count']==3 and result['models']['252']['move'] is not None

def test_nested_file_symlink_cannot_escape_original_tier(m,source,tmp_path):
    path=source['store_root']/'greeks/AAA/2026.parquet';foreign=tmp_path/'foreign.parquet'
    path.rename(foreign);path.symlink_to(foreign)
    with pytest.raises(ValueError,match='original'):m.load_study(**source)

def test_native_private_report_discloses_estimate_and_unknown_clocks(m,source):
    assert hasattr(m,'render_markdown'), 'private research report renderer missing'
    text=m.render_markdown(m.load_study(**source))
    assert 'PRIVATE RETROSPECTIVE RESEARCH' in text
    assert 'not a directly traded basket option' in text
    assert 'Historical availability: unknown' in text
    assert '3/3' in text and 'AAA' in text and '20.00%' in text

def test_sparse_private_report_explains_withholding(m,source):
    assert hasattr(m,'render_markdown'), 'private research report renderer missing'
    source['manifest']['roots'].pop('AAA')
    text=m.render_markdown(m.load_study(**source))
    assert '2/3' in text and 'INCOMPLETE_IV_COVERAGE' in text and 'Unavailable' in text

def test_retrospective_suites_enrolled_in_incumbent_code_group():
    import yaml
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']['options-skew-engine']
    assert job['gate']=='code'
    wanted={'research/factor_atlas/session3/retrospective.py','research/factor_atlas/session3/run_retrospective.py',
            'tests/test_factor_options_retrospective.py','tests/test_factor_options_retrospective_io.py'}
    assert wanted.issubset(set(job['paths'])), 'new retrospective code must be selected by existing code packs'
    run='\n'.join(s.get('run','') for s in job['steps'])
    assert all(p in run for p in wanted if p.startswith('tests/')), 'new retrospective tests must actually execute'
