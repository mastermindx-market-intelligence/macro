"""Pure-function tests for the global central-bank liquidity leaf — no network."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import ast
import json


def _compact(liquidity):
    """Execute the actual projection statements, not a reimplemented mapping."""
    source = Path(__file__).resolve().parents[1] / "scripts" / "build_crossasset.py"
    module = ast.parse(source.read_text())
    main = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    start = next(i for i, n in enumerate(main.body)
                 if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
                 and n.target.id == "_liq_block")
    body = main.body[start:start + 2]
    assert isinstance(body[1], ast.If)
    namespace = {"liquidity": liquidity}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(source), "exec"), namespace)
    return json.loads(json.dumps(namespace["_liq_block"], allow_nan=False))


@pytest.mark.parametrize("value", [-4.0, 2.6, 0.0, None])
def test_compact_liquidity_preserves_impulse_zero_and_coverage(value):
    snap = {"asof": "2026-10-02", "state": "expanding", "accel": "steady",
            "total_usd_tn": 10, "impulse_pct": {"13w": value}, "n_banks": 1,
            "banks": [{"id": "fed", "usd_tn": 10, "raw_asof": "2026-11-06"}],
            "asof_by_bank": {"fed": "2026-11-06"}}
    result = _compact(snap)
    assert result["impulse_13w"] == value
    for key in ("asof", "state", "accel", "total_usd_tn", "n_banks", "banks", "asof_by_bank"):
        assert result[key] == snap[key]
    assert result["asof"] != result["asof_by_bank"]["fed"]


@pytest.mark.parametrize("snapshot", [None, {}, {"impulse_pct": None}])
def test_compact_liquidity_absent_values_stay_unavailable(snapshot):
    result = _compact(snapshot)
    if snapshot is None:
        assert result is None
    else:
        assert result["impulse_13w"] is None
        assert result["banks"] is None


@pytest.mark.parametrize("present", [("fed",), ("fed", "ecb", "boj")])
def test_native_parquet_to_compact_liquidity(tmp_path, monkeypatch, present):
    from lib import store
    monkeypatch.setattr(store.config, "data_dir", lambda: tmp_path)
    (tmp_path / "fred").mkdir()
    (tmp_path / "yahoo").mkdir()
    idx = pd.date_range("2024-11-15", periods=104, freq="W-FRI")
    cfg = {"banks": {
        "fed": {"series": "FED", "unit_mult": 1e12, "label_en": "Fed"},
        "ecb": {"series": "ECB", "unit_mult": 1e12, "fx": "EUR", "label_en": "ECB"},
        "boj": {"series": "BOJ", "unit_mult": 1e12, "fx": "JPY", "label_en": "BoJ"}},
        "impulse_windows_w": [13, 52]}
    for bid, ends in {"fed": (8, 10), "ecb": (10, 4), "boj": (6, 4)}.items():
        if bid in present:
            pd.DataFrame({"value": np.linspace(*ends, len(idx))}, index=idx).to_parquet(
                tmp_path / "fred" / (bid.upper() + ".parquet"))
    for fx in ("EUR", "JPY"):
        pd.DataFrame({"close": np.ones(len(idx))}, index=idx).to_parquet(
            tmp_path / "yahoo" / (fx + ".parquet"))
    snap = gl.snapshot(cfg)
    assert snap is not None
    result = _compact(snap)
    assert result["n_banks"] == len(present)
    assert {b["id"] for b in result["banks"]} == set(present)
    assert result["impulse_13w"] == snap["impulse_pct"]["13w"]
    assert result["impulse_13w"] == (2.6 if len(present) == 1 else -4.0)
    assert result["state"] == ("expanding" if len(present) == 1 else "contracting")
    assert result["total_usd_tn"] == (10 if len(present) == 1 else 18)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import global_liquidity as gl  # noqa: E402

_IDX = pd.date_range("2018-01-05", periods=200, freq="W-FRI")


def test_bank_usd_conversions():
    raw = pd.Series(np.full(len(_IDX), 100.0), index=_IDX)        # 100 (raw units)
    # USD leg (Fed): fx None -> just ×unit_mult
    assert gl.bank_usd(raw, 1.0e6, None).iloc[-1] == 100.0 * 1e6
    # EUR leg: local ×1.10 (EURUSD multiply)
    fx_eur = pd.Series(np.full(len(_IDX), 1.10), index=_IDX)
    assert abs(gl.bank_usd(raw, 1.0e6, fx_eur).iloc[-1] - 100.0 * 1e6 * 1.10) < 1
    # JPY leg: invert handled by passing 1/fx -> local /150
    fx_jpy_inv = pd.Series(np.full(len(_IDX), 1.0 / 150.0), index=_IDX)
    assert abs(gl.bank_usd(raw, 1.0e8, fx_jpy_inv).iloc[-1] - 100.0 * 1e8 / 150.0) < 1e3


def test_aggregate_sums_where_all_present():
    a = pd.Series(np.linspace(1e12, 2e12, len(_IDX)), index=_IDX)
    b = pd.Series(np.linspace(3e12, 4e12, len(_IDX)), index=_IDX[50:].union(_IDX[:50]))
    df = gl.aggregate({"fed": a, "ecb": b})
    assert "total" in df and not df.empty
    assert abs(df["total"].iloc[-1] - (df["fed"].iloc[-1] + df["ecb"].iloc[-1])) < 1


def test_impulse_pct():
    s = pd.Series(np.arange(1.0, 121.0), index=pd.date_range("2020-01-03", periods=120, freq="W-FRI"))
    # 13-week change of a +1/wk ramp at the end: (120-107)/107
    assert abs(gl._impulse(s, 13) - (13.0 / 107.0 * 100.0)) < 1e-6
    assert gl._impulse(s, 999) is None


def test_snapshot_smoke(monkeypatch):
    raw = pd.Series(np.linspace(8.0e6, 9.0e6, len(_IDX)), index=_IDX)   # WALCL-like $mn
    monkeypatch.setattr(gl, "_fred_series", lambda sid: raw.copy())
    monkeypatch.setattr(gl, "_fx_to_usd", lambda key, inv: pd.Series(1.10, index=_IDX))
    cfg = {"banks": {
        "fed": {"series": "WALCL", "unit_mult": 1e6, "fx": None, "invert": False, "label_en": "Fed", "label_zh": "美联储"},
        "ecb": {"series": "ECBASSETSW", "unit_mult": 1e6, "fx": "EURUSD=X", "invert": False, "label_en": "ECB", "label_zh": "欧洲央行"}},
        "impulse_windows_w": [13, 52]}
    s = gl.snapshot(cfg)
    assert s and s["n_banks"] == 2 and s["total_usd_tn"] > 0
    assert s["state"] in ("expanding", "contracting", "flat")
    assert abs(sum(b["share"] for b in s["banks"]) - 100.0) < 0.5
    assert "13w" in s["impulse_pct"] and len(s["spark"]) > 0


def test_snapshot_degrades_no_data(monkeypatch):
    monkeypatch.setattr(gl, "_fred_series", lambda sid: None)
    assert gl.snapshot({"banks": {"fed": {"series": "WALCL"}}}) is None


# INTL-51 — per-bank as-of dates must be surfaced in the snapshot
def test_snapshot_asof_by_bank(monkeypatch):
    """snapshot() must return asof_by_bank with a date per bank and expose raw_asof on each bank dict."""
    raw = pd.Series(np.linspace(8.0e6, 9.0e6, len(_IDX)), index=_IDX)
    monkeypatch.setattr(gl, "_fred_series", lambda sid: raw.copy())
    monkeypatch.setattr(gl, "_fx_to_usd", lambda key, inv: pd.Series(1.10, index=_IDX))
    cfg = {"banks": {
        "fed": {"series": "WALCL",      "unit_mult": 1e6, "fx": None,       "invert": False, "label_en": "Fed", "label_zh": "美联储"},
        "ecb": {"series": "ECBASSETSW", "unit_mult": 1e6, "fx": "EURUSD=X", "invert": False, "label_en": "ECB", "label_zh": "欧洲央行"}},
        "impulse_windows_w": [13, 52]}
    s = gl.snapshot(cfg)
    assert s is not None
    # asof_by_bank must be a dict with a key per bank
    asof_map = s.get("asof_by_bank")
    assert isinstance(asof_map, dict)
    assert set(asof_map.keys()) == {"fed", "ecb"}
    # Each value must be a non-empty date string
    for bid, asof_str in asof_map.items():
        assert isinstance(asof_str, str) and len(asof_str) == 10, \
            f"bank {bid!r}: asof_by_bank value should be YYYY-MM-DD, got {asof_str!r}"
    # Each bank dict in the banks list must also carry raw_asof
    for b in s["banks"]:
        assert "raw_asof" in b, f"bank {b['id']!r} dict missing raw_asof"
        assert isinstance(b["raw_asof"], str) and len(b["raw_asof"]) == 10

