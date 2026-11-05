"""Joint existing-owner producer tests; no vendor/network effects."""
from pathlib import Path
import ast,importlib.util,json,os,shutil
import pytest
from engine.government_revenue import defense_market_context as market
from engine.government_revenue.defense_economics import validate_defense_economics_payload

ROOT=Path(__file__).resolve().parents[1] if not os.environ.get('DFE_SOURCE_ROOT') else Path(os.environ['DFE_SOURCE_ROOT'])
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
producer=module('market_producer_candidate',os.environ['DFE_PRODUCER_PATH']) if os.environ.get('DFE_PRODUCER_PATH') else module('market_producer_installed',ROOT/'engine/government_revenue/defense_economics_producer.py')
financial_helpers=module('financial_test_helpers',ROOT/'tests/test_government_revenue_defense_owner_adapter.py')
market_helpers=module('market_test_helpers',ROOT/'tests/test_defense_market_context.py')
NOW='2026-10-13T06:00:00Z'

def mirrored_owners(tmp_path):
    root=financial_helpers.snapshot_root(tmp_path)
    prices,_,refs,_=market_helpers.fixture()
    store=root/'data/massive_stock_day';scratch=store/'.defense_read';scratch.mkdir(parents=True)
    for ticker,raw in prices['parquet_bytes'].items():(store/(ticker+'.parquet')).write_bytes(raw)
    (scratch/'manifest.json').write_bytes(prices['manifest_bytes'])
    (scratch/'read_receipt.json').write_text(json.dumps(prices['receipt']))
    (store/'_manifest.json').write_text('{"latest_date":"2099-01-01"}')
    for field,path in market._REFERENCE_FILES.items():
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(refs[field])
    for path in ('engine/stock_technicals.py','lib/nyse_calendar.py','lib/dataos/identity.py','lib/dataos/price.py','engine/company_intelligence/identity.py','engine/government_revenue/defense_market_context.py','config/dataset_registry.yml','research/licenses/MASSIVE_ENTITLEMENT_RECORD.md'):
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target)
    return root

def test_actual_joint_composer_preserves_financial_and_zero_stale_market(tmp_path):
    root=mirrored_owners(tmp_path)
    result=producer.build_defense_economics_payload(root,generated_at=NOW,require_market_owner=True)
    assert validate_defense_economics_payload(result)
    for row in result['profiles']:
        assert row['axes']['economics']['facts']
        axis=row['axes']['recognition'];leg=axis['price_response']
        assert leg['return_pct']==0.0 and leg['state']=='stale' and leg['sessions_behind']==1
        assert leg['market_as_of']=='2026-10-09' and leg['previous_session']=='2026-10-08'
        assert leg['security_id']==row['security_id']
        assert result['source_bindings'][leg['owner_ref']]['issuer_id']==row['issuer_id']
        assert axis['expectations_kind']=='not_observed' and axis['valuation_scenario']['state']=='missing_owner'
        assert 'relative_return_pct' not in leg
    assert 'evidence' not in result and 'parquet_bytes' not in result

def test_present_local_cache_integrates_without_live_flag_and_finance_loaded_once(tmp_path,monkeypatch):
    root=mirrored_owners(tmp_path);calls=[];reader=producer.load_defense_owner_snapshot
    def count(path):calls.append(path);return reader(path)
    monkeypatch.setattr(producer,'load_defense_owner_snapshot',count)
    result=producer.build_defense_economics_payload(root,generated_at=NOW)
    assert len(calls)==1
    assert all(row['axes']['recognition']['price_response']['state']=='stale' for row in result['profiles'])

def test_verified_explicit_finance_seam_does_not_reparse(tmp_path,monkeypatch):
    root=mirrored_owners(tmp_path);snapshot=producer.load_defense_owner_snapshot(root)
    def forbidden(*args):raise AssertionError('duplicate financial load')
    monkeypatch.setattr(producer,'load_defense_owner_snapshot',forbidden)
    result=producer.build_defense_economics_payload(root,generated_at=NOW,owner_inputs=snapshot,require_market_owner=True)
    assert result['profiles'][3]['axes']['recognition']['price_response']['return_pct']==0.0

@pytest.mark.parametrize('path',['data/company_intelligence/event_workspaces/manifest.json','data/massive_stock_day/.defense_read/read_receipt.json','data/massive_stock_day/.defense_read/manifest.json','data/massive_stock_day/LHX.parquet','research/licenses/MASSIVE_ENTITLEMENT_RECORD.md','data/reference/security_master.parquet'])
def test_required_owner_input_missing_refuses(tmp_path,path):
    root=mirrored_owners(tmp_path);(root/path).unlink()
    with pytest.raises((ValueError,FileNotFoundError)):producer.build_defense_economics_payload(root,generated_at=NOW,require_market_owner=True)

@pytest.mark.parametrize('path',['data/massive_stock_day/LMT.parquet','data/massive_stock_day/.defense_read/manifest.json','research/licenses/MASSIVE_ENTITLEMENT_RECORD.md','data/reference/security_master.parquet'])
def test_corrupt_present_cache_refuses_even_optional_build(tmp_path,path):
    root=mirrored_owners(tmp_path);p=root/path;p.write_bytes(p.read_bytes()+b'x')
    with pytest.raises((ValueError,KeyError)):producer.build_defense_economics_payload(root,generated_at=NOW)

def test_existing_offline_missing_owner_remains_typed(tmp_path):
    result=producer.build_defense_economics_payload(tmp_path,generated_at=NOW)
    assert all(p['axes']['economics']['state']=='unreviewed' for p in result['profiles'])
    with pytest.raises(ValueError,match='required_financial_owner'):producer.build_defense_economics_payload(tmp_path,generated_at=NOW,require_market_owner=True)

def test_cutoff_excluded_finance_cannot_get_price_only_profiles(tmp_path):
    root=mirrored_owners(tmp_path)
    with pytest.raises(ValueError,match='financial_subject_missing'):
        producer.build_defense_economics_payload(root,generated_at=NOW,as_of='2026-10-12T00:00:00Z',require_market_owner=True)

def test_merge_refuses_identity_change_in_adapter_return(tmp_path,monkeypatch):
    root=mirrored_owners(tmp_path);compose=producer.compose_defense_market_context
    def wrong(*args,**kwargs):
        result=compose(*args,**kwargs);ref=result['recognition_by_ticker']['LMT']['owner_ref'];result['source_bindings'][ref]['security_id']='xnys:RTX';return result
    monkeypatch.setattr(producer,'compose_defense_market_context',wrong)
    with pytest.raises(ValueError,match='market_financial_subject_mismatch'):producer.build_defense_economics_payload(root,generated_at=NOW)

def test_builder_requires_owner_at_live_call_before_any_publication():
    path=Path(os.environ['DFE_BUILDER_PATH']) if os.environ.get('DFE_BUILDER_PATH') else ROOT/'scripts/build_government_revenue.py'
    tree=ast.parse(path.read_text());build=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build')
    calls=[n for n in ast.walk(build) if isinstance(n,ast.Call)]
    call=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='build_defense_economics_payload')
    keyword=next(k for k in call.keywords if k.arg=='require_market_owner')
    assert isinstance(keyword.value,ast.Name) and keyword.value.id=='live_materialization'
    writes=[n for n in calls if isinstance(n.func,ast.Name) and (n.func.id.startswith('_write_') or n.func.id=='_atomic_write_text')]
    assert writes and all(call.lineno<w.lineno for w in writes)
