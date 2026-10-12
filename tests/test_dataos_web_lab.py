"""Boundary/forwarding tests for the existing-Lab web adapter."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from lib.dataos import web_lab


@pytest.fixture
def catalog(monkeypatch):
    entries = {
        "long_event": {
            "signal_id": "long_event",
            "fn": lambda frame: frame["close"],
            "direction": 1,
            "kind": "event",
            "family": "existing_family",
            "display": {"en": "Long event", "zh": "上涨"},
            "default_params": {"window": 14},
            "provenance": "existing catalog",
        },
        "bear_event": {
            "signal_id": "bear_event",
            "fn": lambda frame: frame["close"],
            "direction": -1,
            "kind": "event",
            "family": "existing_family",
            "display": {"en": "Bear event"},
            "default_params": {},
        },
        "neutral_state": {
            "signal_id": "neutral_state",
            "fn": lambda frame: frame["close"],
            "direction": 0,
            "kind": "state",
            "family": "existing_family",
            "display": {"en": "Neutral state"},
            "default_params": {},
        },
    }
    for descriptor in entries.values():
        descriptor["fn"].__module__ = "engine.ma_crosses"
    owner = SimpleNamespace(
        list_signals=lambda: list(entries.values()),
        get_signal=lambda signal_id: dict(entries[signal_id]),
    )
    monkeypatch.setattr(web_lab, "_catalog", lambda: owner)
    return entries


def _request(**overrides):
    request = {
        "signal_id": "long_event",
        "refs": ["macro_snapshot:stocks/AMD.parquet"],
        "horizon_bars": 37,
        "cost_bps": 7.25,
        "n_configs_searched": 42,
    }
    request.update(overrides)
    return request


def test_catalog_metadata_is_searchable_bounded_and_callable_free(catalog):
    result = web_lab.list_signals(limit=1)
    assert result["total_matches"] == 3
    assert result["returned"] == 1 and result["truncated"]
    assert result["signals"][0]["signal_id"] == "bear_event"
    assert not result["signals"][0]["supported_by_web_lab"]
    matched = web_lab.list_signals(query="LONG EVENT", limit=2)
    assert [row["signal_id"] for row in matched["signals"]] == ["long_event"]
    assert "fn" not in matched["signals"][0]
    assert matched["read_only"] and matched["research_only"]
    json.dumps(matched, allow_nan=False)
    assert callable(catalog["long_event"]["fn"])  # owner metadata was not changed


@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "2"])
def test_catalog_rejects_invalid_page_bounds(catalog, limit):
    with pytest.raises(web_lab.WebLabError, match="limit"):
        web_lab.list_signals(limit=limit)


def test_plan_keeps_missing_budget_visible_and_does_not_execute(catalog, monkeypatch):
    lab_loader = Mock(side_effect=AssertionError("must not import Lab when planning"))
    monkeypatch.setattr(web_lab, "_lab", lab_loader)
    result = web_lab.plan("long_event", ["source:AMD.parquet"])
    assert result["request"] == {
        "signal_id": "long_event",
        "refs": ["source:AMD.parquet"],
        "horizon_bars": 21,
        "cost_bps": 5.0,
        "n_configs_searched": None,
    }
    assert not result["execution_ready"]
    assert result["missing_fields"] == ["n_configs_searched"]
    assert result["canonical_function"] == "engine.lab.catalog_backtest"
    assert result["pending_effects"]["temporary_declared_budget_jsonl"]
    assert not result["pending_effects"]["computation_read_only"]
    assert result["signal"]["provenance"] == "existing catalog"
    assert any("survivorship" in item for item in result["limitations"])
    assert any("point-in-time" in item for item in result["limitations"])
    assert any("price basis" in item for item in result["limitations"])
    lab_loader.assert_not_called()


@pytest.mark.parametrize("signal_id", ["bear_event", "neutral_state"])
def test_plan_refuses_directions_canonical_long_pnl_cannot_evaluate(catalog, signal_id):
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.plan(signal_id, ["source:AMD.parquet"])
    assert error.value.code == "UNSUPPORTED_DIRECTION"


@pytest.mark.parametrize("direction", [None, True, "1", 2])
def test_plan_does_not_invent_direction_from_unknown_metadata(catalog, direction):
    catalog["long_event"]["direction"] = direction
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.plan("long_event", ["source:AMD.parquet"])
    assert error.value.code == "UNSUPPORTED_DIRECTION"


def test_unknown_signal_is_not_a_dynamic_import_or_expression(catalog):
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.plan("__import__('os')", ["source:AMD.parquet"])
    assert error.value.code == "UNKNOWN_SIGNAL"


@pytest.mark.parametrize(
    "changes",
    [
        {"refs": []},
        {"refs": ["source:a"] * 2},
        {"refs": [f"source:{n}" for n in range(9)]},
        {"refs": "source:a"},
        {"refs": ["source:\x00a"]},
        {"horizon_bars": 0},
        {"horizon_bars": 253},
        {"horizon_bars": True},
        {"cost_bps": -1},
        {"cost_bps": 1000.01},
        {"cost_bps": float("nan")},
        {"cost_bps": float("inf")},
        {"cost_bps": True},
        {"n_configs_searched": 0},
        {"n_configs_searched": -1},
        {"n_configs_searched": 2.5},
        {"n_configs_searched": True},
    ],
)
def test_plan_rejects_unbounded_or_ambiguous_requests(catalog, changes):
    with pytest.raises(web_lab.WebLabError):
        web_lab.plan(**_request(**changes))


def test_plan_accepts_closed_boundary_values(catalog):
    result = web_lab.plan(**_request(
        refs=[f"source:{n}" for n in range(8)], horizon_bars=252, cost_bps=1000, n_configs_searched=1
    ))
    assert result["execution_ready"]
    assert len(result["request"]["refs"]) == 8
    assert web_lab.plan(**_request(horizon_bars=1, cost_bps=0))["execution_ready"]


def test_execute_requires_budget_before_importing_calculation_engine(catalog, monkeypatch):
    lab_loader = Mock(side_effect=AssertionError("no engine call without budget"))
    monkeypatch.setattr(web_lab, "_lab", lab_loader)
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.execute({"AMD": pd.DataFrame({"close": [1.0]})}, _request(n_configs_searched=None))
    assert error.value.code == "TRIAL_BUDGET_REQUIRED"
    lab_loader.assert_not_called()


@pytest.mark.parametrize("field", ["family", "stop_pct", "kwargs", "code", "sql"])
def test_execute_rejects_arbitrary_overrides_before_engine(catalog, monkeypatch, field):
    lab_loader = Mock(side_effect=AssertionError("unexpected engine call"))
    monkeypatch.setattr(web_lab, "_lab", lab_loader)
    with pytest.raises(web_lab.WebLabError, match="unsupported fields"):
        web_lab.execute({"AMD": pd.DataFrame({"close": [1.0]})}, _request(**{field: "untrusted"}))
    lab_loader.assert_not_called()


def test_execute_forwards_exact_contract_and_preserves_full_trial(catalog, monkeypatch):
    trial = SimpleNamespace(
        name="canonical-name",
        family="canonical-family",
        stats={
            "dsr": np.float64(0.63),
            "sharpe_ci": (np.float64(-0.2), np.float64(0.4)),
            "unknown": None,
            "nan": np.float64("nan"),
            "infinite": float("inf"),
            "nested": {"values": np.array([1.0, np.nan]), "flag": np.bool_(True)},
            "missing": pd.NA,
            "not_a_time": pd.NaT,
        },
        meta={"horizon": 37, "cost_bps": 7.25, "n_configs_searched": 42, "extra": "retained"},
        survivorship_biased=True,
        verdict=lambda: "NO-EDGE",
        to_ledger=Mock(side_effect=AssertionError("production persistence is forbidden")),
    )
    canonical = Mock(return_value=trial)
    monkeypatch.setattr(web_lab, "_lab", lambda: SimpleNamespace(catalog_backtest=canonical))
    universe = {"AMD": pd.DataFrame({"close": [1.0, 1.1]})}
    request = _request()
    result = web_lab.execute(universe, request)
    args, kwargs = canonical.call_args
    assert args[0] == "long_event" and args[1] is universe
    assert kwargs == {"horizon": 37, "cost_bps": 7.25, "n_configs_searched": 42}
    assert result["request"] == request
    assert result["trial"]["name"] == "canonical-name"
    assert result["trial"]["family"] == "canonical-family"
    assert result["trial"]["meta"] == trial.meta
    assert result["trial"]["verdict"] == "NO-EDGE"
    assert result["trial"]["survivorship_biased"] is True
    assert result["trial"]["stats"] == {
        "dsr": 0.63,
        "sharpe_ci": [-0.2, 0.4],
        "unknown": None,
        "nan": None,
        "infinite": None,
        "nested": {"values": [1.0, None], "flag": True},
        "missing": None,
        "not_a_time": None,
    }
    assert set(result["trial"]["stats"]) == set(trial.stats)
    assert not result["read_only"] and result["research_only"]
    assert not result["effects"]["trial_to_ledger_called"]
    assert result["effects"]["temporary_declared_budget_jsonl"]["is_production_trial_ledger"] is False
    json.dumps(result, allow_nan=False)
    trial.to_ledger.assert_not_called()
    assert np.isnan(trial.stats["nan"])  # returned view did not mutate owner values


@pytest.mark.parametrize(
    "universe",
    [{}, {"AMD": "not a dataframe"}, {"AMD": pd.DataFrame({"price": [1.0]})}],
)
def test_execute_rejects_invalid_materialized_inputs(catalog, monkeypatch, universe):
    lab_loader = Mock(side_effect=AssertionError("invalid universe reached engine"))
    monkeypatch.setattr(web_lab, "_lab", lab_loader)
    with pytest.raises(web_lab.WebLabError):
        web_lab.execute(universe, _request())
    lab_loader.assert_not_called()


def test_existing_real_catalog_is_discoverable_without_replacement_engine():
    from engine import tech_catalog

    owner_rows = tech_catalog.list_signals()
    assert owner_rows, "Existing signal catalog must be present in the test environment."
    result = web_lab.list_signals(limit=100)
    assert result["catalog_size"] == len(owner_rows)
    assert result["returned"] == min(100, len(owner_rows))
    assert all("signal_id" in row and "fn" not in row for row in result["signals"])
    eligible = next(row for row in owner_rows if row.get("direction") == 1)
    prepared = web_lab.plan(eligible["signal_id"], ["source:AMD.parquet"], n_configs_searched=3)
    assert prepared["signal"]["family"] == eligible["family"]
    assert prepared["request"]["signal_id"] == eligible["signal_id"]
    json.dumps(prepared, allow_nan=False)


def test_implicit_supplemental_inputs_remain_discovery_only(catalog, monkeypatch):
    catalog["long_event"]["family"] = "insider"
    result = web_lab.list_signals(query="long_event")
    signal = result["signals"][0]
    assert signal["discovery_only"] and not signal["supported_by_web_lab"]
    assert signal["required_supplemental_inputs"] == [
        "data/sec_insider/panel/*.parquet",
        "site/factordata/insider_signals.json",
    ]
    lab_loader = Mock(side_effect=AssertionError("unbound supplemental input reached Lab"))
    monkeypatch.setattr(web_lab, "_lab", lab_loader)
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.plan(**_request())
    assert error.value.code == "UNBOUND_SIGNAL_INPUTS"
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.execute({"AMD": pd.DataFrame({"close": [1.0]})}, _request())
    assert error.value.code == "UNBOUND_SIGNAL_INPUTS"
    lab_loader.assert_not_called()


def test_actual_supplied_universe_execution_never_calls_benchmark_or_store(monkeypatch, tmp_path):
    import builtins
    import tempfile

    from engine import lab, tech_catalog

    # Reuse an existing pure price catalog signal, not a new test calculation engine.
    signal_id = next(
        row["signal_id"] for row in tech_catalog.list_signals()
        if row["direction"] == 1
        and getattr(row["fn"], "__module__", "") == "engine.ma_crosses"
    )
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    benchmark = Mock(side_effect=AssertionError("supplied universe must not load benchmark"))
    monkeypatch.setattr(lab, "bench", benchmark)
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"lib.store", "lib.config"} or (
            name == "lib" and ({"store", "config"} & set(fromlist or ()))
        ):
            raise AssertionError("supplied-universe execution imported a source store/config")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    index = pd.bdate_range("2024-01-02", periods=96)
    close = 100 * np.exp(np.cumsum(0.002 + 0.01 * np.sin(np.arange(96) / 7)))
    frame = pd.DataFrame(
        {"close": close, "open": close, "high": close * 1.01,
         "low": close * 0.99, "volume": np.full(96, 1_000_000)},
        index=index,
    )
    result = web_lab.execute(
        {"AMD": frame},
        _request(signal_id=signal_id, refs=["fixture:AMD"], horizon_bars=9),
    )
    benchmark.assert_not_called()
    assert result["trial"]["stats"]["n_tickers"] == 1
    assert result["trial"]["meta"]["horizon"] == 9
    assert result["trial"]["meta"]["n_configs_searched"] == 42
    assert result["trial"]["survivorship_biased"] is True
    # Canonical declared-budget helper still performs its disclosed temporary effect.
    assert len(list(tmp_path.glob("_declbudget_*.jsonl"))) == 1
    assert not (tmp_path / "data").exists()
    json.dumps(result, allow_nan=False)


def test_unreviewed_callable_module_cannot_use_reviewed_family_label(catalog):
    catalog["long_event"]["family"] = "ma_crosses"
    catalog["long_event"]["fn"].__module__ = "engine.future_signal_module"
    result = web_lab.list_signals(query="long_event")
    assert result["signals"][0]["discovery_only"]
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.plan(**_request())
    assert error.value.code == "UNREVIEWED_SIGNAL_INPUTS"


@pytest.mark.parametrize("signal_id", ["valuation_pctile", "undervalued_state"])
def test_real_fundamental_snapshot_signals_require_explicit_supplemental_inputs(signal_id):
    from engine import tech_catalog

    descriptor = tech_catalog.get_signal(signal_id)
    assert descriptor["direction"] == 1
    result = web_lab.list_signals(query=signal_id)
    listed = next(row for row in result["signals"] if row["signal_id"] == signal_id)
    assert listed["discovery_only"]
    assert listed["required_supplemental_inputs"] == [
        "data/edgar/fundamentals.parquet", "site/factordata/factors.json"
    ]
    with pytest.raises(web_lab.WebLabError) as error:
        web_lab.plan(signal_id, ["fixture:AMD"], n_configs_searched=1)
    assert error.value.code == "UNBOUND_SIGNAL_INPUTS"
