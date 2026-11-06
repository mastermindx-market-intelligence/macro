"""Pure source binding regressions; no files, feeds or production effects."""
import copy
import json
import pytest
from engine.neuralweb.pivot_source_adapter import build_pivot_observations


def sources():
    return dict(symbol="ABC", signal_gate={"tier_cascade": "T2", "ticks": 0, "asof": "2026-10-21"},
        standout={"ticker": "ABC", "signal": {"above200": False, "asof": "2026-10-21"},
            "coiled": {"coiled": True, "star": False, "fire": True},
            "hold": {"state": "intact", "days_basing": 4, "ret_since_anchor_pct": -2.55},
            "conviction": {"alignment": {"knife": 0.2}}}, standouts_as_of="2026-10-22",
        price_context={"as_of": "2026-10-21", "dist_21d_low_pct": 3.2, "dist_126d_high_pct": -18.7})


def mapped(**overrides):
    args = sources(); args.update(overrides)
    return {x["field"]: x for x in build_pivot_observations(**args)}


def test_mapping_and_signed_basis():
    out = mapped()
    assert len(out) == 12
    assert out["trigger_age_ticks"]["value"] == 0
    assert type(out["trigger_age_ticks"]["value"]) is int
    assert out["above200"]["value"] is False
    assert out["coiled_fire"]["value"] is True
    assert out["dist_126d_high_pct"]["value"] == 18.7
    assert out["hold_ret_since_anchor_pct"]["value"] == -2.55
    assert out["above200"]["as_of"] == "2026-10-21"
    assert all(x["available_at"] is None for x in out.values())


def test_missing_is_not_false_and_ma_does_not_gate():
    args = sources(); del args["standout"]["coiled"]["star"]
    del args["standout"]["signal"]["above200"]
    out = {x["field"]: x for x in build_pivot_observations(**args)}
    assert out["star"]["value"] is None
    assert out["above200"]["value"] is None
    assert out["coiled_fire"]["value"] is True


@pytest.mark.parametrize("ticker", [None, "OTHER", "abc"])
def test_wrong_subject_cannot_bind(ticker):
    args = sources(); args["standout"]["ticker"] = ticker
    out = {x["field"]: x for x in build_pivot_observations(**args)}
    assert out["coiled"]["value"] is None
    assert out["trigger_tier"]["value"] == "T2"


@pytest.mark.parametrize("container", [None, "", "2026-10-20", "20261022", "bad"])
def test_missing_or_inconsistent_container_is_not_fresh(container):
    out = mapped(standouts_as_of=container)
    assert out["coiled"]["as_of"] is None
    assert out["above200"]["as_of"] is None


def test_missing_subject_date_never_uses_container_date():
    args = sources(); args["standout"]["signal"].pop("asof")
    out = {x["field"]: x for x in build_pivot_observations(**args)}
    assert out["coiled"]["as_of"] is None
    assert out["above200"]["as_of"] is None


def test_max_availability_cannot_erase_later_receipt():
    args = sources()
    args["standout"]["available_at"] = "2026-10-22T18:00:00-04:00"
    args["standout"]["signal"]["available_at"] = "2026-10-21T20:00:00Z"
    out = {x["field"]: x for x in build_pivot_observations(**args)}
    assert out["above200"]["available_at"] == "2026-10-22T18:00:00-04:00"


@pytest.mark.parametrize("stamp", ["2026-10-21", "bad", 5, {}, "2026-10-21T09:00:00"])
def test_invalid_availability_not_downgraded_to_unknown(stamp):
    args = sources(); args["standout"]["available_at"] = stamp
    out = {x["field"]: x for x in build_pivot_observations(**args)}
    assert out["coiled"]["available_at"] == "invalid"
    assert out["above200"]["available_at"] == "invalid"


@pytest.mark.parametrize("bad", [18.7, True, float("nan"), float("inf"), "-18.7", []])
def test_high_distance_rejects_invalid_sign_or_type(bad):
    out = mapped(price_context={"as_of": "2026-10-21", "dist_126d_high_pct": bad})
    assert out["dist_126d_high_pct"]["value"] is None
    json.dumps(list(out.values()), allow_nan=False)


@pytest.mark.parametrize("bad", [None, [], "bad", 12])
def test_malformed_nested_sources(bad):
    out = mapped(signal_gate=bad, standout=bad, price_context=bad)
    assert len(out) == 12
    assert all(x["value"] is None for x in out.values())


def test_input_immutable_unknown_keys_ignored():
    args = sources(); args["standout"]["ARMED"] = True; args["standout"]["PRIMED"] = True
    before = copy.deepcopy(args)
    out = build_pivot_observations(**args)
    assert args == before
    assert not any(x["field"] in ("ARMED", "PRIMED") for x in out)
    assert out == build_pivot_observations(**args)
    json.dumps(out, allow_nan=False)


def test_bad_symbol_does_not_create_path():
    out = mapped(symbol="../../secret")
    assert out["dist_21d_low_pct"]["source"] == "data/stocks/<invalid>.parquet"
