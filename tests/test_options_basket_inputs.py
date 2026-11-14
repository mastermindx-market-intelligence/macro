"""Byte-bound legacy source inspection; synthetic documents, not live feed proof."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from importlib import import_module
from pathlib import Path
import hashlib
import json
import pytest

NOW = datetime(2026,10,8,22,tzinfo=timezone.utc)
ROOTS = ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA"]


def test_source_adapter_exists():
    assert (Path(__file__).resolve().parents[1]/"engine/options_basket_inputs.py").exists(), "owner-byte adapter not implemented"


@pytest.fixture
def m(): return import_module("engine.options_basket_inputs")


def packed(obj): return json.dumps(obj,sort_keys=True,allow_nan=False).encode()


def receipt(m, raw, **changes):
    return replace(m.ArtifactReceipt("fixture:owner-artifact",hashlib.sha256(raw).hexdigest(),NOW-timedelta(hours=1)),**changes)


def vol(root="AAPL", value=35.):
    return packed({"schema":"options_hub.vol/v1","root":root,"asof":"2026-10-08","atm_iv":value,"term":[{"dte":30,"atm_iv":value}],"qualified":True,"known_at":NOW.isoformat(),"method":"iv30_total_variance_act365f"})


def registry():
    return packed({"baskets":{"mag7":{"weighting":"equal","members":[{"ticker":r,"added":"2023-05-09","removed":None} for r in ROOTS]}}})


def inspect(m, raw=None, **changes):
    raw=vol() if raw is None else raw
    return m.inspect_legacy_vol(raw,requested_root="AAPL",receipt=receipt(m,raw,**changes),asof=NOW)


def test_legacy_number_never_becomes_certified_iv30(m):
    result=inspect(m)
    assert result["legacy_atm_iv_decimal"]==.35
    assert result["qualified_iv30"] is None
    assert not result["eligible_for_hybrid_risk"]
    assert result["qualified_known_at"] is None
    assert result["artifact_known_at"]==(NOW-timedelta(hours=1)).isoformat()
    assert "CONSTANT_MATURITY_METHOD_NOT_CERTIFIED" in result["reasons"]


@pytest.mark.parametrize("value",[None,True,"35",-1])
def test_invalid_numbers_do_not_coerce(m,value):
    assert inspect(m,vol(value=value))["legacy_atm_iv_decimal"] is None


def test_supplied_zero_survives_without_qualification(m):
    result=inspect(m,vol(value=0))
    assert result["legacy_atm_iv_decimal"]==0
    assert not result["eligible_for_hybrid_risk"]


@pytest.mark.parametrize("changes",[{"known_at":None},{"known_at":NOW+timedelta(seconds=1)}])
def test_unknown_or_future_known_artifact_cannot_enter_replay(m,changes):
    result=inspect(m,**changes)
    assert result["legacy_atm_iv_decimal"] is None
    assert not result["eligible_for_hybrid_risk"]


def test_mismatched_digest_and_root_rejected(m):
    raw=vol()
    with pytest.raises(ValueError):m.inspect_legacy_vol(raw+b" ",requested_root="AAPL",receipt=receipt(m,raw),asof=NOW)
    with pytest.raises(ValueError):inspect(m,vol(root="MSFT"))


@pytest.mark.parametrize("raw",[b'{"schema":"options_hub.vol/v1","root":"AAPL","atm_iv":NaN}',b'{"root":"AAPL","root":"MSFT"}',b'[]',b'{}',b'\xff'])
def test_malformed_ambiguous_json_rejected(m,raw):
    with pytest.raises(ValueError):inspect(m,raw)


def test_malformed_dates_refused(m):
    for date in ["2026-02-31","2026-10-08T22:00:00Z",None,True]:
        raw=packed({"schema":"options_hub.vol/v1","root":"AAPL","atm_iv":35,"asof":date})
        with pytest.raises(ValueError):inspect(m,raw)


def test_full_legacy_population_is_still_zero_qualified(m):
    raw=registry();inputs={r:vol(r,20+i) for i,r in enumerate(ROOTS)}
    result=m.legacy_house_view(raw,definition_receipt=receipt(m,raw),basket_id="mag7",payloads=inputs,receipts={r:receipt(m,b) for r,b in inputs.items()},asof=NOW)
    assert result["coverage"]["payload_count"]==7
    assert result["coverage"]["qualified_count"]==0
    assert result["legacy_covered_mean_iv"]==pytest.approx(.23)
    assert result["hybrid_expected_move"] is None
    assert result["authority"]["prophet"] is False
    assert result["population_basis"]=="current_registry_membership_not_pit_backtest"
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize("missing",[2,3,4])
def test_sparse_legacy_membership_denominator_preserved(m,missing):
    raw=registry();inputs={r:vol(r) for r in ROOTS[:-missing]}
    result=m.legacy_house_view(raw,definition_receipt=receipt(m,raw),basket_id="mag7",payloads=inputs,receipts={r:receipt(m,b) for r,b in inputs.items()},asof=NOW)
    assert result["coverage"]["total_count"]==7
    assert result["coverage"]["payload_count"]==7-missing
    assert result["coverage"]["reported_weight"]==pytest.approx((7-missing)/7)
    assert len(result["members"])==7
    assert result["hybrid_expected_move"] is None


def test_unknown_definition_availability_refuses_view(m):
    raw=registry()
    with pytest.raises(ValueError):m.legacy_house_view(raw,definition_receipt=receipt(m,raw,known_at=None),basket_id="mag7",payloads={},receipts={},asof=NOW)


def test_duplicate_and_non_equal_membership_refused(m):
    for change in ["duplicate","non_equal"]:
        obj=json.loads(registry());basket=obj["baskets"]["mag7"]
        if change=="duplicate":basket["members"].append(basket["members"][0])
        else:basket["weighting"]="market_cap"
        raw=packed(obj)
        with pytest.raises(ValueError):m.legacy_house_view(raw,definition_receipt=receipt(m,raw),basket_id="mag7",payloads={},receipts={},asof=NOW)


def test_no_io_or_producer_imports():
    import ast
    path=Path(__file__).resolve().parents[1]/"engine/options_basket_inputs.py"
    tree=ast.parse(path.read_text())
    names={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    assert not names.intersection({"engine.options_hub","engine.thetadata_store","requests","pathlib","subprocess","os"})
