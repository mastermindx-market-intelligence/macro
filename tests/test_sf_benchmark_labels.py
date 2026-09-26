"""Declared benchmark labels use identical economic windows, not row offsets.

All writes use private pytest fixtures. No provider or canonical market artifact.
"""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import numpy as np
import pandas as pd
import pytest
from engine.signal_foundry import harness
from engine.signal_foundry.spec import validate_spec
from engine.signal_foundry.screen import screen_candidate


def spec():
    return {"id":"SF-9907", "name":"Benchmark fixture", "market":"US fixture",
            "thesis":"Synthetic excess-return target", "mechanism":"Fixture only",
            "data":[{"path":"data/feature.csv", "column":"feature", "pit":"synthetic"}],
            "feature":{"pipeline":[["lag", {"n":0}]]},
            "target":{"path":"data/asset.csv", "column":"price", "kind":"excess_return",
                      "horizon_d":5, "benchmark":{"path":"data/benchmark.csv", "column":"price"}},
            "universe":"single_series", "baseline":"buy_and_hold",
            "gates":{"min_t_hac":2.0, "fdr_q":0.1, "dsr":0.9},
            "registered_at":"2026-09-16", "history_years":8,
            "orthogonality_note":"Fixture", "evidence_note":"Fixture"}


def write_series(root, filename, values):
    values.to_frame().to_csv(root / 'data' / filename)


@pytest.fixture
def data_repo(tmp_path):
    (tmp_path/'data').mkdir()
    idx = pd.bdate_range('2000-01-03', periods=1700)
    n = np.arange(len(idx))
    asset = pd.Series(100*np.exp(0.0002*n+0.03*np.sin(n/12)), index=idx, name='price')
    benchmark = pd.Series(200*np.exp(0.0001*n+0.02*np.cos(n/17)), index=idx, name='price')
    write_series(tmp_path,'asset.csv',asset)
    write_series(tmp_path,'benchmark.csv',benchmark)
    write_series(tmp_path,'other.csv',benchmark*1.01+2)
    write_series(tmp_path,'feature.csv',pd.Series(np.sin(n/31), index=idx, name='feature'))
    for args in [['init'],['add','data']]:
        subprocess.run(['git','-C',str(tmp_path),*args],check=True,capture_output=True)
    return tmp_path, asset, benchmark


def target(data_repo, candidate=None):
    root, asset, benchmark = data_repo
    return harness._build_target(candidate or spec(), root, asset.index)


def test_explicit_benchmark_computes_simple_return_difference(data_repo):
    _, a, b = data_repo
    actual = target(data_repo)
    expected = ((a.shift(-5)/a-1)-(b.shift(-5)/b-1)).dropna()
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-12)
    assert actual.abs().max() > 0.01


def test_benchmark_endpoints_use_asset_timestamps_not_benchmark_row_stride(data_repo):
    root, a, b = data_repo
    b = b.drop(a.index[12])
    write_series(root,'benchmark.csv',b)
    actual = target(data_repo)
    t, end = a.index[10], a.index[15]
    assert actual.loc[t] == pytest.approx((a.loc[end]/a.loc[t]-1)-(b.loc[end]/b.loc[t]-1))
    assert a.index[12] not in actual.index
    assert a.index[7] not in actual.index


def test_missing_benchmark_endpoints_are_not_forward_filled_or_zeroed(data_repo):
    root,a,b = data_repo
    b.loc[a.index[20]] = np.nan
    write_series(root,'benchmark.csv',b)
    actual = target(data_repo)
    assert a.index[20] not in actual.index and a.index[15] not in actual.index
    assert len(actual) == len(a)-5-2


def test_same_prices_from_explicit_distinct_series_may_legitimately_give_zero(data_repo):
    root,a,_ = data_repo
    write_series(root,'benchmark.csv',a)
    actual = target(data_repo)
    np.testing.assert_allclose(actual, 0.0, atol=1e-12)


@pytest.mark.parametrize('fault', ['missing','missing_asset_column','missing_benchmark_column',
    'same_reference','unknown_benchmark_key','non_dict','bad_horizon','absolute','traversal','untracked'])
def test_ambiguous_or_unsafe_benchmark_is_refused_by_validation_and_screen(data_repo, fault):
    root,a,b = data_repo; s=spec(); t=s['target']
    if fault=='missing':t.pop('benchmark')
    elif fault=='missing_asset_column':t.pop('column')
    elif fault=='missing_benchmark_column':t['benchmark'].pop('column')
    elif fault=='same_reference':t['benchmark']={'path':t['path'],'column':t['column']}
    elif fault=='unknown_benchmark_key':t['benchmark']['allocation']='sma_200'
    elif fault=='non_dict':t['benchmark']='SPY'
    elif fault=='bad_horizon':t['horizon_d']=5.0
    elif fault=='absolute':t['benchmark']['path']=str(root/'data/benchmark.csv')
    elif fault=='traversal':t['benchmark']['path']='data/../data/benchmark.csv'
    else:t['benchmark']['path']='data/untracked.csv';write_series(root,'untracked.csv',b)
    ok,errors = validate_spec(s,root)
    assert not ok and errors, fault
    screened=screen_candidate(s,repo_root=root)
    assert not screened['admit'] and 'target_contract' in screened['gates_failed'], screened
    with pytest.raises((ValueError,TypeError)):
        target(data_repo,s)


def test_legacy_missing_benchmark_is_rejected_before_target_data_read(data_repo,monkeypatch):
    s=spec();s['target'].pop('benchmark')
    def forbidden(*args,**kwargs):raise AssertionError('ambiguous target reached the loader')
    monkeypatch.setattr(harness,'_load_raw_price',forbidden)
    with pytest.raises(ValueError,match='benchmark'):
        target(data_repo,s)


@pytest.mark.parametrize('file', ['asset.csv','benchmark.csv'])
def test_requested_column_is_not_silently_replaced_by_a_fallback(data_repo,file):
    root,a,b=data_repo
    write_series(root,file,(a if file=='asset.csv' else b).rename('Close'))
    with pytest.raises(KeyError):target(data_repo)


@pytest.mark.parametrize('bad', [0.0,-1.0,float('inf'),True])
@pytest.mark.parametrize('file', ['asset.csv','benchmark.csv'])
def test_corrupt_price_values_refuse_evaluation(data_repo,bad,file):
    root,a,b=data_repo
    values=(a if file=='asset.csv' else b).copy()
    if bad is True:values=pd.Series(True,index=values.index,name='price')
    else:values.iloc[10]=bad
    write_series(root,file,values)
    with pytest.raises(ValueError):target(data_repo)


def test_missing_asset_bar_does_not_compress_the_target_clock(data_repo):
    root,a,b=data_repo;a.iloc[10]=np.nan;write_series(root,'asset.csv',a)
    with pytest.raises(ValueError):target(data_repo)


@pytest.mark.parametrize('fault',['duplicate','unsorted','timezone'])
def test_incompatible_benchmark_clock_is_explicit(data_repo,fault):
    root,a,b=data_repo
    if fault=='duplicate':b=pd.concat([b.iloc[:5],b.iloc[4:]])
    elif fault=='unsorted':b=b.iloc[::-1]
    else:b.index=b.index.tz_localize('UTC')
    write_series(root,'benchmark.csv',b)
    with pytest.raises(ValueError):target(data_repo)


def test_run_spec_errors_on_ambiguous_legacy_target(data_repo):
    root,a,b=data_repo;s=spec();s['target'].pop('benchmark')
    out=harness.run_spec(s,repo_root=root,ledger_path=root/'trial.jsonl')
    assert out['verdict']=='error',out
    assert any('benchmark' in reason for reason in out['verdict_reasons'])
    assert out['target_contract']['version']=='sf-excess-target-2'
    assert out['target_contract']['status']=='invalid'


def test_result_and_trial_identity_bind_benchmark_and_label_version(data_repo):
    root,a,b=data_repo;s=spec();path=root/'trial.jsonl'
    first=harness.run_spec(s,repo_root=root,ledger_path=path)
    again=harness.run_spec(s,repo_root=root,ledger_path=path)
    s['target']['benchmark']['path']='data/other.csv'
    second=harness.run_spec(s,repo_root=root,ledger_path=path)
    assert first['target_contract']['benchmark']['path']=='data/benchmark.csv'
    assert first['target_contract']['horizon_bars']==5
    assert first['target_contract']['version']=='sf-excess-target-2'
    assert first['ledger_n_at_run']==again['ledger_n_at_run']
    assert second['ledger_n_at_run']==first['ledger_n_at_run']+1
    assert len(path.read_text().splitlines())>=2


def test_target_label_suite_is_selected_by_the_binding_code_gate():
    from scripts.run_ci_pack import load_legacy_jobs, select_jobs
    root = Path(__file__).resolve().parents[1]
    jobs = load_legacy_jobs(root / ".github/ci/legacy-jobs.yml", gate="code")
    found = [j for j in jobs if j.job_id == "signal-foundry-regressions"]
    assert len(found) == 1, "Foundry numerical tests must not live only behind gate=data"
    commands = "\n".join(str(s.get("run", "")) for s in found[0].definition["steps"])
    assert "tests/test_sf_*.py" in commands
    assert (root / "tests/test_sf_benchmark_labels.py") in list((root / "tests").glob("test_sf_*.py"))
    for path in ["engine/signal_foundry/harness.py", "engine/signal_foundry/spec.py",
                 "scripts/run_signal_foundry_brainstorm.py", "tests/test_sf_benchmark_labels.py"]:
        selected, _ = select_jobs(found, [path])
        assert [j.job_id for j in selected] == ["signal-foundry-regressions"]



def test_strategy_baseline_cannot_change_price_benchmark_labels(data_repo):
    buyhold = target(data_repo)
    s = spec(); s['baseline'] = 'flat'
    pd.testing.assert_series_equal(target(data_repo,s),buyhold)
    s['baseline'] = 'sma_200'
    pd.testing.assert_series_equal(target(data_repo,s),buyhold)


def test_nonfinite_derived_return_is_not_a_numeric_target(data_repo):
    root,a,b = data_repo
    a.iloc[1] = 1e-300
    a.iloc[6] = 1e300
    write_series(root,'asset.csv',a)
    with pytest.raises(ValueError,match='nonfinite'):
        target(data_repo)


def test_explicit_two_columns_in_one_file_are_not_the_same_series(data_repo):
    root,a,b=data_repo
    pd.DataFrame({'price':a,'benchmark_price':b}).to_csv(root/'data/asset.csv')
    s=spec();s['target']['benchmark']={'path':'data/asset.csv','column':'benchmark_price'}
    np.testing.assert_allclose(target(data_repo,s),((a.shift(-5)/a)-(b.shift(-5)/b)).dropna(),atol=1e-12)


def test_symlink_cannot_disguise_self_benchmark(data_repo):
    root,a,b=data_repo
    alias=root/'data/alias.csv';alias.symlink_to('asset.csv')
    subprocess.run(['git','-C',str(root),'add','data/alias.csv'],check=True,capture_output=True)
    s=spec();s['target']['benchmark']['path']='data/alias.csv'
    with pytest.raises(ValueError,match='identical'):
        target(data_repo,s)



def test_generator_hint_requires_explicit_benchmark_not_strategy_baseline():
    from scripts.run_signal_foundry_brainstorm import _spec_schema_hint
    hint=_spec_schema_hint()
    assert 'target.benchmark' in hint
    assert 'same target-price timestamps' in hint
    assert 'Do not infer' in hint


@pytest.mark.parametrize('filer',['brainstorm','codex'])
def test_existing_filers_accept_explicit_target_and_reject_legacy_ambiguity(data_repo,filer):
    root,a,b=data_repo
    if filer=='brainstorm':
        from scripts.run_signal_foundry_brainstorm import _file_specs
    else:
        from scripts.codex_signal_lane import _file_specs
    good=spec();bad=deepcopy(good);bad['id']='SF-9908';bad['name']='Ambiguous legacy target'
    bad['target'].pop('benchmark')
    path=root/'data/signal_foundry/candidates.jsonl'
    out=_file_specs([bad,good],path,root,'2026-W38',False)
    assert out[:2]==(1,1)
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]['status']=='screen_rejected'
    assert rows[1]['status']=='proposed'
    assert rows[1]['target']['benchmark']==good['target']['benchmark']
