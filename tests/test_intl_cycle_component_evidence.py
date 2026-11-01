from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import intl_regime as ir  # noqa: E402
from engine import intl_run  # noqa: E402


def _frame() -> pd.DataFrame:
    n = 180
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    f = pd.DataFrame(index=idx)
    f["gdp_yoy"] = np.linspace(1.0, 3.0, n)
    f["unemployment"] = np.linspace(7.0, 4.0, n)
    f["index"] = np.linspace(15000.0, 23000.0, n)
    f["copper_gold"] = np.linspace(0.0010, 0.0013, n)
    f["cpi_yoy"] = np.linspace(4.0, 1.5, n)
    f["oil"] = np.linspace(90.0, 60.0, n)
    f["yield_10y"] = np.linspace(4.5, 3.2, n)
    f["short_3m"] = np.concatenate([np.full(n // 2, 4.5), np.linspace(4.5, 2.5, n - n // 2)])
    f["policy_rate"] = f["short_3m"]
    f["curve"] = f["yield_10y"] - f["short_3m"]
    f["real_yield"] = f["yield_10y"] - f["cpi_yoy"]
    f["drawdown"] = 0.0
    return f


def _required_columns() -> set[str]:
    columns = {"growth_score", "inflation_score", "growth_n_components", "inflation_n_components"}
    columns.update(f"c_growth_{key}" for key in ir._GROWTH)
    columns.update(f"c_inflation_{key}" for key in ir._INFLATION)
    return columns


def _no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise AssertionError("helper performed I/O")

    monkeypatch.setattr(ir, "classify", fail)
    monkeypatch.setattr(ir.config, "load", fail)
    monkeypatch.setattr("builtins.open", fail)


def test_component_evidence_extracts_native_row_once() -> None:
    reg = ir.classify(_frame())
    asof = reg["growth_score"].last_valid_index()
    before = reg.copy(deep=True)

    evidence = ir.component_evidence_at(reg, asof)

    assert set(evidence) == {
        "asof", "growth", "inflation", "growth_score", "inflation_score",
        "growth_n_components", "inflation_n_components",
    }
    assert evidence["asof"] == asof.isoformat()
    assert [item["key"] for item in evidence["growth"]] == list(ir._GROWTH)
    assert [item["key"] for item in evidence["inflation"]] == list(ir._INFLATION)
    assert {item["key"]: item["weight"] for item in evidence["growth"]} == ir._GROWTH
    assert {item["key"]: item["weight"] for item in evidence["inflation"]} == ir._INFLATION
    assert all(item["score"] == reg.loc[asof, f"c_growth_{item['key']}"] for item in evidence["growth"])
    assert all(item["score"] == reg.loc[asof, f"c_inflation_{item['key']}"] for item in evidence["inflation"])
    assert evidence["growth_score"] == reg.loc[asof, "growth_score"]
    assert evidence["inflation_score"] == reg.loc[asof, "inflation_score"]
    assert evidence["growth_n_components"] == int(reg.loc[asof, "growth_n_components"])
    assert evidence["inflation_n_components"] == int(reg.loc[asof, "inflation_n_components"])
    assert pd.testing.assert_frame_equal(reg, before) is None
    json.dumps(evidence, allow_nan=False)


def test_component_evidence_uses_owner_constants_not_copies(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = ir.classify(_frame())
    asof = reg["growth_score"].last_valid_index()
    monkeypatch.setitem(ir._GROWTH, "gdp_trend", 3.25)
    monkeypatch.setitem(ir._INFLATION, "oil_trend", 0.125)

    evidence = ir.component_evidence_at(reg, asof)

    weights = {item["key"]: item["weight"] for item in evidence["growth"]}
    assert weights["gdp_trend"] == 3.25
    assert weights["index_trend"] == ir._GROWTH["index_trend"]
    inflation_weights = {item["key"]: item["weight"] for item in evidence["inflation"]}
    assert inflation_weights["oil_trend"] == 0.125
    assert inflation_weights["cpi_direction"] == ir._INFLATION["cpi_direction"]


def test_component_evidence_preserves_true_zero_and_nulls() -> None:
    reg = ir.classify(_frame())
    asof = reg["growth_score"].last_valid_index()
    reg.loc[asof, [column for column in reg.columns if str(column).startswith("c_")]] = 0.0
    reg.loc[asof, "growth_score"] = 0.0
    reg.loc[asof, "inflation_score"] = 0.0
    reg.loc[asof, "growth_n_components"] = len(ir._GROWTH)
    reg.loc[asof, "inflation_n_components"] = len(ir._INFLATION)

    evidence = ir.component_evidence_at(reg, asof)

    assert all(item["score"] == 0.0 and not isinstance(item["score"], bool) for item in evidence["growth"])
    assert all(item["score"] == 0.0 and not isinstance(item["score"], bool) for item in evidence["inflation"])
    assert evidence["growth_score"] == 0.0
    assert evidence["inflation_score"] == 0.0
    assert evidence["growth_n_components"] == len(ir._GROWTH)
    assert evidence["inflation_n_components"] == len(ir._INFLATION)

    thin = _frame()[["index", "oil", "yield_10y"]]
    thin_reg = ir.classify(thin)
    thin_asof = thin_reg.index[0]
    thin_evidence = ir.component_evidence_at(thin_reg, thin_asof)
    thin_growth = {item["key"]: item["score"] for item in thin_evidence["growth"]}
    assert thin_growth["gdp_trend"] is None
    assert thin_growth["unemployment_trend"] is None
    assert thin_growth["global_growth"] is None
    assert thin_evidence["growth_score"] is None or math.isfinite(thin_evidence["growth_score"])


def test_component_evidence_converts_nonfinite_to_json_null() -> None:
    reg = ir.classify(_frame())
    asof = reg.index[-1]
    one_row = reg.loc[[asof]].copy()
    one_row.loc[asof, "c_growth_gdp_trend"] = np.nan
    one_row.loc[asof, "c_growth_index_trend"] = np.inf
    one_row.loc[asof, "growth_score"] = -np.inf
    one_row.loc[asof, "inflation_score"] = np.nan

    evidence = ir.component_evidence_at(one_row, asof)

    scores = {item["key"]: item["score"] for item in evidence["growth"]}
    assert scores["gdp_trend"] is None
    assert scores["index_trend"] is None
    assert evidence["growth_score"] is None
    assert evidence["inflation_score"] is None
    json.dumps(evidence, allow_nan=False)


def test_component_evidence_count_requires_native_integral() -> None:
    reg = ir.classify(_frame())
    asof = reg.index[-1]

    for native, expected in (
        (np.int64(2), 2), (np.float64(2.0), 2), (-1, None), (1.5, None),
        (True, None), ("2", None), (np.nan, None), (np.inf, None),
    ):
        one_row = reg.loc[[asof]].copy()
        one_row["growth_n_components"] = pd.Series([native], index=one_row.index, dtype=object)
        assert ir.component_evidence_at(one_row, asof)["growth_n_components"] == expected


def test_component_evidence_reads_exact_asof_only() -> None:
    reg = ir.classify(_frame())
    asof = reg.index[-2]
    future = reg.index[-1]
    reg.loc[future, "c_growth_gdp_trend"] = 0.99
    reg.loc[future, "growth_score"] = 0.99
    before = reg.copy(deep=True)

    evidence = ir.component_evidence_at(reg, asof)

    assert evidence["growth_score"] != 0.99
    assert {item["key"]: item["score"] for item in evidence["growth"]}["gdp_trend"] != 0.99
    future_evidence = ir.component_evidence_at(reg, future)
    assert future_evidence["growth_score"] == 0.99
    assert pd.testing.assert_frame_equal(reg, before) is None


def test_component_evidence_rejects_invalid_geometry() -> None:
    reg = ir.classify(_frame())
    asof = reg.index[-1]

    with pytest.raises(ValueError):
        ir.component_evidence_at("not a frame", asof)
    with pytest.raises(ValueError):
        ir.component_evidence_at(reg.reset_index(drop=True), 1)
    with pytest.raises(ValueError):
        ir.component_evidence_at(pd.concat([reg, reg]), asof)
    with pytest.raises(ValueError):
        ir.component_evidence_at(reg.drop(columns=["c_growth_gdp_trend"]), asof)
    with pytest.raises(ValueError):
        ir.component_evidence_at(reg, asof + pd.Timedelta(days=1))
    with pytest.raises(ValueError):
        ir.component_evidence_at(reg, pd.NaT)

    empty = reg.iloc[0:0].copy()
    with pytest.raises(ValueError):
        ir.component_evidence_at(empty, asof)


def test_component_evidence_has_no_helper_io(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = ir.classify(_frame())
    asof = reg.index[-1]
    _no_io(monkeypatch)

    evidence = ir.component_evidence_at(reg, asof)

    assert evidence["asof"] == asof.isoformat()


def test_country_record_adds_only_current_components(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame()
    calls = []
    actual_classify = ir.classify

    def classified_once(value):
        calls.append(id(value))
        return actual_classify(value)

    inputs = SimpleNamespace(
        countries=lambda: {"XX": {"name": "Test", "name_zh": "Test", "flag": "T", "region": "Test"}},
        country_frame=lambda cc, closes, macro: frame if cc == "XX" else pd.DataFrame(),
        latest_macro_snapshot=lambda cc, source: {"yield_10y": 3.0, "cpi_yoy": 2.0, "gdp_yoy": 1.0, "unemployment": 5.0},
        macro_freshness=lambda cc, macro: "2024-01-01",
    )
    monkeypatch.setattr(intl_run.intl_inputs, "countries", inputs.countries)
    monkeypatch.setattr(intl_run.intl_inputs, "country_frame", inputs.country_frame)
    monkeypatch.setattr(intl_run.intl_inputs, "latest_macro_snapshot", inputs.latest_macro_snapshot)
    monkeypatch.setattr(intl_run.intl_inputs, "macro_freshness", inputs.macro_freshness)
    monkeypatch.setattr(intl_run, "classify", classified_once)
    monkeypatch.setattr(intl_run, "recession_band", lambda score: "low")
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record helper wrote parquet")))
    monkeypatch.setattr(pd.DataFrame, "to_json", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record helper wrote JSON")))
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record helper wrote CSV")))
    monkeypatch.setattr(intl_run, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record helper called run")))

    record, history = intl_run.country_record("XX", pd.DataFrame(), pd.DataFrame(), {"XX": {"drawdown_risk": 10}})
    reg = actual_classify(frame)
    asof = reg["quad"].last_valid_index()
    row = reg.loc[asof]

    assert calls == [id(frame)]
    assert record is not None and history is not None
    assert record.pop("cycle_components") == ir.component_evidence_at(reg, asof)
    expected = {
        "cc": "XX", "name": "Test", "name_zh": "Test", "flag": "T", "region": "Test",
        "date": str(asof.date()), "quad": row["quad"], "quad_name": row["quad_name"],
        "growth_score": round(float(row["growth_score"]), 3),
        "inflation_score": round(float(row["inflation_score"]), 3),
        "confidence": round(float(row["regime_confidence"]), 3),
        "liquidity": row["liquidity"],
        "recession_score": round(float(row["recession_score"]), 0) if pd.notna(row["recession_score"]) else None,
        "recession_band": "low",
        "macro": {"yield_10y": 3.0, "cpi_yoy": 2.0, "gdp_yoy": 1.0, "unemployment": 5.0},
        "macro_asof": "2024-01-01",
        "equity": {"drawdown_risk": 10},
        "data_limited": False,
    }
    assert record == expected
    expected_history = reg[[column for column in reg.columns if not str(column).startswith("c_")]]
    assert pd.testing.assert_frame_equal(history, expected_history) is None
    assert not any(str(column).startswith("c_") for column in history.columns)


def test_equal_instant_lookup_preserves_native_row_timestamp():
    reg = ir.classify(_frame())
    native = reg.index[-1] + pd.Timedelta(nanoseconds=123)
    reg = reg.iloc[[-1]].copy()
    reg.index = pd.DatetimeIndex([native])
    lookup = native.tz_convert("America/New_York")
    result = ir.component_evidence_at(reg, lookup)
    assert result["asof"] == native.isoformat()
    assert result["asof"] != lookup.isoformat()
