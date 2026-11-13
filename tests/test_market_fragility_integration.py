"""The same observer reaches incumbent publications without changing legacy gates."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import json

import pandas as pd

from engine import market_gamma
from engine.market_fragility import observe
from scripts import build_market_structure

NOW = datetime(2026, 11, 13, 14, tzinfo=timezone.utc)


def source():
    return pd.DataFrame({
        "gamma_regime": ["short"], "net_gex_bn": [-2.5], "gamma_flip": [float("nan")],
        "spot": [7500.0], "dist_to_flip_pct": [float("nan")], "tier": ["full"],
    }, index=pd.to_datetime(["2026-11-12"]))


def test_gamma_owner_snapshot_delegates_to_single_observer(monkeypatch):
    calls = []
    def read(group, name):
        calls.append((group, name))
        return source()
    monkeypatch.setattr(market_gamma.store, "read", read)
    result = market_gamma.fragility_snapshot(now=NOW)
    assert result == observe(source(), now=NOW)
    assert calls == [("cboe", "gex_SPX")]
    assert result["state"] == "amplifying" and result["current"]["gamma_flip"] is None


def test_source_error_is_explicit_without_exception_details(monkeypatch):
    def broken(*args):
        raise OSError("unrelated secret must not enter the observation")
    monkeypatch.setattr(market_gamma.store, "read", broken)
    result = market_gamma.fragility_snapshot(now=NOW)
    assert result["state"] == "unknown"
    assert result["quality"]["reasons"] == ["source_read_error"]
    assert "secret" not in json.dumps(result)


def test_missing_source_emits_unknown_not_null_or_long(monkeypatch):
    monkeypatch.setattr(market_gamma.store, "read", lambda *args: None)
    result = market_gamma.fragility_snapshot(now=NOW)
    assert result["state"] == "unknown"
    assert result["current"]["reported_gamma_regime"] is None


def test_legacy_missing_flip_stays_unchanged(monkeypatch, capsys):
    coarse = pd.DataFrame({"spot_vs_flip_pct": [float("nan")], "spot": [7500.0]},
                          index=pd.to_datetime(["2026-11-12"]))
    def read(group, name):
        return coarse if name == "gex" else source() if name == "gex_SPX" else None
    monkeypatch.setattr(market_gamma.store, "read", read)
    assert market_gamma.snapshot(now=NOW) is None
    assert market_gamma.fragility_snapshot(now=NOW)["state"] == "amplifying"
    assert "::warning " in capsys.readouterr().out


def test_market_structure_projection_reads_exact_same_source_once(monkeypatch, tmp_path):
    calls = []
    def read(path):
        calls.append(path)
        return source()
    monkeypatch.setattr(build_market_structure, "_read_parquet", read)
    result = build_market_structure._build_gamma_block(tmp_path, now=NOW)
    assert result["fragility"] == market_gamma_observation()
    assert result["regime"] == "short" and result["net_gex_bn"] == -2.5
    assert result["gamma_flip"] is None
    assert len(calls) == 1


def market_gamma_observation():
    return observe(source(), now=NOW)


def test_real_parquet_to_both_existing_projections(monkeypatch, tmp_path):
    folder = tmp_path / "cboe"
    folder.mkdir()
    source().to_parquet(folder / "gex_SPX.parquet")
    block = build_market_structure._build_gamma_block(tmp_path, now=NOW)
    monkeypatch.setattr(market_gamma.store.config, "data_dir", lambda: tmp_path)
    snap = market_gamma.fragility_snapshot(now=NOW)
    assert block["fragility"] == snap
    assert snap["source"]["id"] == "cboe/gex_SPX"
    assert snap["clocks"]["source_session"] == "2026-11-12"
    json.dumps(snap, allow_nan=False)


def test_empty_market_structure_preserves_unknown_observation(monkeypatch, tmp_path):
    monkeypatch.setattr(build_market_structure, "_read_parquet", lambda path: None)
    block = build_market_structure._build_gamma_block(tmp_path, now=NOW)
    assert block["regime"] is None
    assert block["fragility"]["state"] == "unknown"


def test_regime_pipeline_wires_additive_field_to_same_owner():
    tree = ast.parse((Path(__file__).resolve().parents[1] / "engine/run.py").read_text())
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    matching = []
    for node in assignments:
        for target in node.targets:
            if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                    and target.value.id == "latest" and isinstance(target.slice, ast.Constant)
                    and target.slice.value == "market_fragility"):
                matching.append(node.value)
    assert any(isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
               and v.func.id == "fragility_snapshot" for v in matching)
    assert any(isinstance(v, ast.Constant) and v.value is None for v in matching)


def test_optional_observer_failure_preserves_legacy_gamma(monkeypatch, tmp_path):
    from engine import market_fragility
    monkeypatch.setattr(build_market_structure, "_read_parquet", lambda path: source())
    def broken(*args, **kwargs):
        raise ValueError("observer failure")
    monkeypatch.setattr(market_fragility, "observe", broken)
    block = build_market_structure._build_gamma_block(tmp_path, now=NOW)
    assert block["regime"] == "short"
    assert block["net_gex_bn"] == -2.5
    assert block["fragility"] is None
