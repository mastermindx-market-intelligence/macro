"""Request binding and actual Python-to-JavaScript transport; synthetic context only."""
from dataclasses import replace
import json,os,subprocess
from pathlib import Path
import pytest
from engine.market_navigator import ContractError
from engine.market_navigator_response import bind_response
from tests.test_market_navigator import build,obs,scenario,receipt,ASOF
ROOT=Path(__file__).resolve().parents[1]


def response(**changes):
    args=dict(packet=build(),request_id='navigator-test',expected_subject='SPY:ARCX',
        expected_horizon='intraday',requested_as_of=ASOF)
    return bind_response(**(args|changes))


def test_response_keeps_correlation_but_excludes_internal_subject():
    out=response()
    assert out['request_id']=='navigator-test' and out['data']['readiness']=='research_only'
    assert 'SPY:ARCX' not in json.dumps(out) and 'internal://' not in json.dumps(out)
    assert not any(out['data']['authority'].values())


@pytest.mark.parametrize('changes',[
    {'expected_subject':'QQQ:XNAS'}, {'expected_horizon':'swing'},
    {'requested_as_of':'2026-10-21T20:01:00.000001Z'}, {'requested_as_of':'2026-10-21'},
    {'request_id':'../bad'}, {'request_id':''}, {'request_id':'x'*97}])
def test_wrong_request_refused(changes):
    with pytest.raises(ContractError):response(**changes)


def test_equivalent_timezone_echo_preserves_original_request_spelling():
    out=response(requested_as_of='2026-10-21T16:01:00-04:00')
    assert out['requested_as_of']=='2026-10-21T16:01:00-04:00'


def test_microsecond_precision_not_rounded():
    p=build(as_of='2026-10-21T20:01:00.000002Z')
    with pytest.raises(ContractError):response(packet=p,requested_as_of='2026-10-21T20:01:00.000001Z')


def test_changed_private_context_cannot_be_reprojected():
    p=build();p['observations'][0]['value']=100
    with pytest.raises(ContractError):response(packet=p)


def test_over_budget_response_refused_without_truncating_population():
    p=build(scenarios=(scenario(support=tuple('x'+str(i) for i in range(4000))),))
    with pytest.raises(ContractError,match='budget'):response(packet=p)


def test_real_javascript_consumer_on_python_wire(tmp_path):
    path=tmp_path/'wire.json';path.write_text(json.dumps(response()))
    result=subprocess.run(['node',str(ROOT/'tests/market_navigator_client_harness.js'),str(path)],
        cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['checks']>=30 and report['late_response_ignored']
    assert report['loading_clears_prior'] and report['no_retry']
