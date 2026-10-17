"""Bounded real-owner I/O path for retrospective risk validation (synthetic fixtures)."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib, io, json, subprocess, sys
import numpy as np
import pandas as pd
import pytest

MODULE='research.factor_atlas.session3.run_retrospective_outcomes'

@pytest.fixture
def reader():
    from importlib import import_module
    assert (Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/run_retrospective_outcomes.py').is_file(), 'missing retrospective outcomes runner'
    return import_module(MODULE)

@pytest.fixture
def source(tmp_path):
    repo=tmp_path/'owned-repo';repo.mkdir();subprocess.run(['git','init','-q',str(repo)],check=True)
    def add(raw):
        return subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--stdin'],input=raw).decode().strip()
    store=tmp_path/'owned-store';store.mkdir()
    dates=pd.bdate_range('2024-01-02',periods=560)
    anchors=[dates[360].date(),dates[410].date()]
    np.random.seed(43)
    roots=['AAA','BBB','CCC']
    inputs={}
    for i,root in enumerate(roots):
        values=100*np.exp(np.cumsum(np.random.default_rng(i+9).normal(.0003,.011,len(dates))))
        frame=pd.DataFrame({'close':values},index=dates)
        bio=io.BytesIO();frame.to_parquet(bio)
        price=add(bio.getvalue())
        rows=[]
        for anchor in anchors:
            for dte in (29,36):
                for side in ('C','P'):
                    rows.append({'root':root,'date':pd.Timestamp(anchor),'expiration':pd.Timestamp(anchor)+pd.Timedelta(days=dte),
                       'right':side,'strike':100.,'bid':9.5,'ask':10.,'underlying_price':100.,
                       'implied_vol':.25+i*.02,'iv_error':0.})
        f=store/'greeks'/root/f'{anchors[0].year}.parquet';f.parent.mkdir(parents=True);pd.DataFrame(rows).to_parquet(f,index=False)
        inputs[root]={'price_blob':price,'greeks_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    membership={'baskets':{'mag7':{'weighting':'equal','members':[{'ticker':r,'added':'2020-01-01','removed':None} for r in roots]}}}
    mblob=add(json.dumps(membership).encode())
    manifest={'schema':'factor_atlas.s3.retrospective_outcomes_inputs/v1','basket_id':'mag7','membership_blob':mblob,
              'anchors':[d.isoformat() for d in anchors],'price_column':'close','roots':inputs}
    return dict(manifest=manifest,source_repository=repo,store_root=store,
                captured_at=datetime(2026,10,11,22,tzinfo=timezone.utc))

def test_source_bound_multi_anchor_cli_calibrates_privately(reader,source):
    r=reader.load_outcomes(**source)
    assert r['count_total']==2 and r['count_evaluable']==2
    assert r['source_receipts']['roots']['AAA']['greeks']['state']=='READ_VERIFIED'
    assert r['measurement_sha256'] and len(r['measurement_sha256'])==64
    assert not r['claims']['calibrated_probability'] and not r['published']
    assert r['source_receipts']['source_use_status']=='RETROSPECTIVE_UNQUALIFIED'
    assert all(case['expected_move'] is not None for case in r['cases'])
    json.dumps(r,allow_nan=False)

def test_greek_sha_change_is_refused(reader,source):
    f=next(source['store_root'].rglob('*.parquet'))
    with f.open('ab') as o:o.write(b'tamper')
    with pytest.raises(ValueError,match='digest'):
        reader.load_outcomes(**source)

def test_missing_greek_is_withheld_not_dropped(reader,source):
    f=next(source['store_root'].rglob('*.parquet'));f.unlink()
    r=reader.load_outcomes(**source)
    assert r['count_total']==2 and r['count_evaluable']==0
    assert all(case['iv_coverage_count']==2 for case in r['cases'])

def test_missing_member_source_does_not_change_denominator(reader,source):
    source['manifest']['roots'].pop('AAA')
    r=reader.load_outcomes(**source)
    assert r['count_total']==2 and r['count_evaluable']==0
    assert all(case['original_count']==3 for case in r['cases'])

def test_mutated_price_blob_rejected(reader,source):
    source['manifest']['roots']['AAA']['price_blob']='f'*40
    with pytest.raises(ValueError,match='local Git object'):
        reader.load_outcomes(**source)

@pytest.mark.parametrize('key,value', [('publication','true'),('rights',True),('quote_known_at','2025-01-01')])
def test_ad_hoc_certification_cannot_change_source_contract(reader,source,key,value):
    source['manifest'][key]=value
    with pytest.raises(ValueError,match='manifest'):
        reader.load_outcomes(**source)

def test_readonly_source_objects_dont_change(reader,source):
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source['store_root'].rglob('*.parquet')}
    reader.load_outcomes(**source)
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source['store_root'].rglob('*.parquet')}

def test_deterministic_measurement_excludes_capture_clock(reader,source):
    a=reader.load_outcomes(**source)
    source['captured_at']+=timedelta(minutes=11)
    b=reader.load_outcomes(**source)
    assert a['measurement_sha256']==b['measurement_sha256']
    assert a['captured_at']!=b['captured_at']

def test_cli_duplicate_manifest_fails_before_printing_values(reader,source,tmp_path):
    p=tmp_path/'input.json';p.write_text('{"anchor":"2026-10-08","anchor":"2026-10-09"}')
    r=subprocess.run([sys.executable,'-B','-m',MODULE,'--manifest',str(p),
      '--source-repository',str(source['source_repository']),'--store-root',str(source['store_root'])],capture_output=True,text=True)
    assert r.returncode!=0 and r.stdout=='' and 'duplicate' in r.stderr

def test_predeclared_outcome_suites_enrolled_in_existing_options_ci():
    import yaml
    root=Path(__file__).resolve().parents[1]
    manifest=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())
    job=manifest['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    required={'research/factor_atlas/session3/retrospective_calibration.py',
              'research/factor_atlas/session3/run_retrospective_outcomes.py',
              'research/factor_atlas/session3/mag7_retrospective_outcomes_inputs.json',
              'tests/test_factor_options_retro_calibration.py',
              'tests/test_factor_options_retro_outcomes_io.py'}
    assert required.issubset(set(job['paths']))
    runs='\n'.join(step.get('run','') for step in job['steps'])
    assert 'tests/test_factor_options_retro_calibration.py' in runs
    assert 'tests/test_factor_options_retro_outcomes_io.py' in runs
