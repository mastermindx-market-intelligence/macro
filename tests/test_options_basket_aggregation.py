"""Factor Atlas S3 native leaf; every numerical market input here is synthetic."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import json
import math

import numpy as np
import pytest

NOW = datetime(2026, 10, 8, 22, tzinfo=timezone.utc)
HASH = "a" * 64


def test_native_module_exists():
    assert (Path(__file__).resolve().parents[1] / "engine/options_basket_aggregation.py").is_file(), "native aggregation leaf not implemented"


@pytest.fixture
def m():
    return import_module("engine.options_basket_aggregation")


def definition(m, **changes):
    return replace(m.Definition("house:test", "fixture:definition", HASH, NOW-timedelta(days=1)), **changes)


def members(m, n=10, missing=0):
    return [m.Member(root=f"R{i:02}", weight=1/n, iv=.2+.01*i if i<n-missing else None,
                     observed_at=NOW-timedelta(hours=2), known_at=NOW-timedelta(hours=1),
                     qualified=True, premium=float(i+1), source_ref=f"fixture:vol:R{i:02}",
                     source_sha256=HASH, valid_until=NOW+timedelta(hours=2),
                     method="iv30_total_variance_act365f") for i in range(n)]


def corr(m, rows, values=None, **changes):
    n=len(rows)
    return replace(m.Correlation(tuple(r.root for r in rows), np.eye(n) if values is None else values,
                                 "fixture:correlation", HASH, NOW-timedelta(days=1),
                                 NOW-timedelta(hours=1), NOW+timedelta(hours=2),
                                 "historical_correlation"), **changes)


def run(m, rows, correlation=None, **kwargs):
    return m.aggregate(rows, definition=definition(m), asof=NOW, correlation=correlation, **kwargs)


def test_total_variance_not_linear_iv(m):
    value=m.standardized_iv([(20,.2),(40,.4)])
    assert value == pytest.approx(math.sqrt((.2**2*20+.4**2*40)/60))
    assert value != pytest.approx(.3)
    assert m.standardized_iv([(30,.25)]) == .25


@pytest.mark.parametrize("points", [[(10,.2)],[(40,.3)],[(10,.2),(20,.2)],[]])
def test_no_nearest_tenor_or_extrapolation(m, points):
    assert m.standardized_iv(points) is None


@pytest.mark.parametrize("points", [[(20,.2),(20,.3)],[(0,.2)],[(20,-1)],[(20,True)],[(20,float("nan"))],[(20,.8),(40,.1)]])
def test_invalid_variance_brackets_refused(m, points):
    with pytest.raises(ValueError): m.standardized_iv(points)


def test_fully_covered_descriptors_and_hybrid(m):
    rows=members(m); result=run(m,rows,corr(m,rows))
    iv=np.array([r.iv for r in rows])
    assert result["coverage"]["weight"] == pytest.approx(1)
    assert result["covered"]["mean_iv"] == pytest.approx(iv.mean())
    assert result["covered"]["rms_iv"] == pytest.approx(np.sqrt(np.mean(iv**2)))
    assert result["hybrid_expected_move"] == pytest.approx(np.sqrt(np.sum((iv/10)**2)*30/365))
    assert result["horizon"] == {"days":30,"basis":"ACT/365F","unit":"calendar_day"}
    assert result["authority"] == {"display_only":True,"publication":False,"prophet":False,"position_sizing":False}
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize("missing", [3,4,5])
def test_30_40_50_percent_missing_withholds_full_risk(m, missing):
    rows=members(m,missing=missing); result=run(m,rows,corr(m,rows))
    assert result["headline_mean_iv"] is None
    assert result["hybrid_expected_move"] is None
    assert result["covered"]["mean_iv"] is not None
    assert result["coverage"]["weight"] == pytest.approx((10-missing)/10)
    assert "INCOMPLETE_IV_COVERAGE" in result["reasons"]


def test_missing_major_name_cannot_hide_in_count(m):
    rows=[replace(r,weight=.4 if i==0 else .6/9,iv=None if i==0 else r.iv) for i,r in enumerate(members(m))]
    result=run(m,rows,corr(m,rows))
    assert result["coverage"]["count_fraction"] == .9
    assert result["headline_mean_iv"] is None
    assert result["hybrid_expected_move"] is None


def test_small_missing_name_allows_descriptor_not_full_risk(m):
    rows=members(m,missing=1); result=run(m,rows,corr(m,rows))
    assert result["headline_mean_iv"] is not None
    assert result["hybrid_expected_move"] is None


def test_reported_premium_dominance_does_not_reweight_iv(m):
    rows=[replace(r,premium=900 if i==0 else 100/9) for i,r in enumerate(members(m))]
    result=run(m,rows)
    assert result["premium"]["top_share_reported"] == pytest.approx(.9)
    assert "REPORTED_PREMIUM_SINGLE_NAME_DOMINATED" in result["warnings"]
    assert result["covered"]["mean_iv"] == pytest.approx(.245)
    rows[0]=replace(rows[0],premium=None)
    assert not run(m,rows)["premium"]["complete"]


def test_zero_missing_and_empty_distinct(m):
    rows=[replace(r,iv=0) for r in members(m)]
    assert run(m,rows,corr(m,rows))["hybrid_expected_move"] == 0
    missing=run(m,members(m,missing=10))
    assert missing["covered"]["mean_iv"] is None
    with pytest.raises(ValueError): run(m,[])


@pytest.mark.parametrize("field,value", [("iv",True),("iv",float("inf")),("weight",True),("weight",-.1),("premium",-1),("qualified",1)])
def test_malformed_member_refused(m, field, value):
    rows=members(m);rows[0]=replace(rows[0],**{field:value})
    with pytest.raises(ValueError):run(m,rows)


@pytest.mark.parametrize("changes,reason", [
    ({"known_at":NOW+timedelta(seconds=1)},"NOT_KNOWN_ASOF"),
    ({"valid_until":NOW},"OBSERVATION_STALE"),
    ({"valid_until":None},"SOURCE_CLOCKS_MISSING"),
    ({"source_sha256":""},"SOURCE_DIGEST_MISSING"),
    ({"source_ref":""},"SOURCE_REF_MISSING"),
    ({"qualified":False},"IV_QUALITY_UNQUALIFIED"),
    ({"method":"nearest_expiry"},"IV_METHOD_UNQUALIFIED"),
    ({"tenor_calendar_days":20},"IV_TENOR_UNQUALIFIED"),
    ({"year_basis":"TRADING/252"},"IV_YEAR_BASIS_UNQUALIFIED"),
])
def test_source_qualification_never_manufactured(m, changes, reason):
    rows=members(m);rows[0]=replace(rows[0],**changes)
    result=run(m,rows,corr(m,rows))
    assert result["hybrid_expected_move"] is None
    assert reason in result["coverage"]["excluded"][0]["reasons"]


def test_owner_deadline_not_hardcoded_weekend_ttl(m):
    rows=[replace(r,observed_at=NOW-timedelta(days=3),known_at=NOW-timedelta(days=2)) for r in members(m)]
    assert run(m,rows,corr(m,rows))["hybrid_expected_move"] is not None


@pytest.mark.parametrize("changes", [{"known_at":NOW+timedelta(seconds=1)},{"valid_until":NOW},{"source_sha256":""},{"method":"implied_correlation"}])
def test_unqualified_correlation_withholds_only_modeled_risk(m, changes):
    rows=members(m);result=run(m,rows,corr(m,rows,**changes))
    assert result["headline_mean_iv"] is not None
    assert result["hybrid_expected_move"] is None
    assert result["reasons"]


@pytest.mark.parametrize("matrix", [[[1,2],[2,1]],[[1,.3],[.2,1]],[[1,float("nan")],[0,1]],[[2,0],[0,1]],[[1]],[[1,False],[False,1]]])
def test_invalid_correlation_matrix_refused(m, matrix):
    rows=members(m,n=2)
    with pytest.raises(ValueError):run(m,rows,corr(m,rows,matrix))


def test_exact_root_binding(m):
    rows=members(m)
    with pytest.raises(ValueError):run(m,rows,corr(m,rows,roots=tuple("WRONG" for _ in rows)))
    rows[1]=replace(rows[1],root=rows[0].root)
    with pytest.raises(ValueError):run(m,rows)


def test_permutation_and_correlation_sensitivity(m):
    rows=members(m);R=.4*np.ones((10,10))+.6*np.eye(10)
    a=run(m,rows,corr(m,rows,R))
    assert a==run(m,list(reversed(rows)),corr(m,rows,R))
    b=run(m,rows,corr(m,rows,np.ones((10,10))))
    assert b["hybrid_expected_move"] == pytest.approx(.245*math.sqrt(30/365))
    assert b["hybrid_expected_move"] != pytest.approx(.245*math.sqrt(30/252))
    assert a["hybrid_expected_move"] < b["hybrid_expected_move"]


def test_definition_clock_and_weight_contract(m):
    rows=members(m)
    with pytest.raises(ValueError):m.aggregate(rows,definition=definition(m,known_at=NOW+timedelta(seconds=1)),asof=NOW)
    with pytest.raises(ValueError):run(m,[replace(r,weight=.2) for r in rows])
    with pytest.raises(ValueError):m.aggregate(rows,definition=definition(m),asof=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("value", [True,0,-1,1.5])
def test_policy_min_names_is_positive_integer(m, value):
    with pytest.raises(ValueError):run(m,members(m),policy=m.Policy(min_names=value))


def test_future_source_cannot_leak_iv_or_premium_through_diagnostics(m):
    rows=members(m)
    rows[0]=replace(rows[0],known_at=NOW+timedelta(seconds=1),premium=1000000)
    result=run(m,rows,corr(m,rows))
    first=result["inputs"][0]
    assert first["iv"] is None
    assert result["premium"]["root_count"]==9
    assert result["premium"]["complete"] is False
    assert "REPORTED_PREMIUM_SINGLE_NAME_DOMINATED" not in result["warnings"]


@pytest.mark.parametrize("changes",[{"valid_until":NOW},{"known_at":None},{"source_sha256":""}])
def test_unadmitted_source_not_in_activity_population(m,changes):
    rows=members(m);rows[0]=replace(rows[0],**changes)
    result=run(m,rows)
    assert result["premium"]["root_count"]==9
    assert result["inputs"][0]["iv"] is None


def test_quality_withholding_does_not_hide_timely_activity(m):
    rows=members(m);rows[0]=replace(rows[0],qualified=False)
    result=run(m,rows)
    assert result["inputs"][0]["iv"] is None
    assert result["premium"]["root_count"]==10


def test_refusal_output_remains_json_safe_for_malformed_metadata(m):
    rows=members(m)
    rows[0]=replace(rows[0],method={"bad"},source_ref={"bad"},source_sha256={"bad"},year_basis={"bad"})
    result=run(m,rows)
    json.dumps(result,allow_nan=False)
    assert result["inputs"][0]["source_ref"] is None
    assert result["inputs"][0]["method"] is None


def test_native_numeric_scalars_are_normalized_for_json(m):
    rows=[replace(r,tenor_calendar_days=np.int64(30)) for r in members(m)]
    json.dumps(run(m,rows),allow_nan=False)


def test_correlation_refusal_metadata_is_json_safe(m):
    rows=members(m)
    result=run(m,rows,corr(m,rows,method={"unqualified"}))
    assert result["hybrid_expected_move"] is None
    json.dumps(result,allow_nan=False)
    assert result["correlation"]["method"] is None


def test_actual_policy_parameters_travel_with_result(m):
    policy=m.Policy(min_weight=.9,min_count_fraction=.85,min_names=4)
    result=run(m,members(m),policy=policy)
    assert result["policy_parameters"] == {
        "min_weight":.9,"min_count_fraction":.85,"min_names":4,
        "max_missing_name_weight":.1,"premium_dominance":.7,
        "full_risk_requires_complete_coverage":True,
    }
