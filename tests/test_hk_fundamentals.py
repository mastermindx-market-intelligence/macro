"""HK descriptive-fundamentals engine tests (engine/hk_fundamentals.py).

Pure-function checks: Piotroski from the precomputed HK ratios, CAGR, consensus
upside, and the currency-safe valuation gate: the vendor feed is CNY for every name
while labelling it "HKD", so the label is ignored and PE/PB (HKD price over CNY
EPS/BVPS) are never emitted.
HK has no validated selection edge — fundamentals are health/coverage CONTEXT
(research/CHINA_HK_STOCK_SIGNALS.md)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import hk_fundamentals as hf  # noqa: E402


def _row(fy, **kw):
    base = dict(fy=fy, revenue=100e8, ni=20e8, eps=2.0, bvps=10.0, gross_margin=50.0,
                net_margin=20.0, roe=18.0, roa=10.0, debt_ratio=40.0, current_ratio=1.5,
                cfo_ps=2.5, ocf_sales=25.0, currency="HKD")
    base.update(kw)
    return base


def test_cagr():
    assert hf._cagr([100, 140, 196]) == 40.0     # 100->196 over 2 intervals = 40%/yr


def test_piotroski_from_ratios():
    prior = _row(2023, roa=8.0, debt_ratio=45.0, current_ratio=1.3, gross_margin=48.0)
    latest = _row(2024, roa=11.0, debt_ratio=40.0, current_ratio=1.6, gross_margin=51.0)
    p = hf._piotroski([prior, latest])
    assert p is not None and p["of"] >= 4
    assert p["score"] >= 5


def test_consensus_upside():
    c = hf._consensus({"n_analysts": 10, "target_med": 120.0, "buy": 6, "hold": 4, "sell": 0}, price=100.0)
    assert c["upside_pct"] == 20.0
    assert c["buy"] == 6
    assert hf._consensus({}, 100.0) is None          # no coverage -> None


def _write_cache(path, recs):
    pd.DataFrame([{"ticker": r["ticker"], "payload": json.dumps(r), "asof": "2026-06-18"}
                  for r in recs]).to_parquet(path, index=False)


def test_cny_rows_labelled_hkd_get_no_mixed_currency_pe(tmp_path, monkeypatch):
    # 0700.HK / 9988.HK as cached: RMB EPS/BVPS under the vendor's constant "HKD"
    # label. Trusting the label priced HKD over CNY: 424.8 / 24.749 = PE 17.2.
    cache = tmp_path / "fundamentals.parquet"
    _write_cache(cache, [
        {"ticker": "0700.HK", "profile": {}, "forecast": {},
         "financials": [_row(2024, eps=20.486, bvps=106.0),
                        _row(2025, eps=24.749, bvps=126.717)]},
        {"ticker": "9988.HK", "profile": {}, "forecast": {},
         "financials": [_row(2025, eps=6.89, bvps=52.0),
                        _row(2026, eps=5.7, bvps=55.683)]},
    ])
    monkeypatch.setattr(hf, "CACHE", cache)
    out = hf.build_all({"0700.HK": 424.8, "9988.HK": 107.0})
    for t in ("0700.HK", "9988.HK"):
        rec = out[t]
        assert "pe" not in rec["valuation"] and "pb" not in rec["valuation"]
        # the emitted unit is the real one, never the vendor label
        assert rec["currency"] == "CNY" != "HKD"
        assert rec["financials"]["currency"] == "CNY"
    assert out["0700.HK"]["financials"]["eps"][-1] == 24.749   # figures pass through


def test_valuation_ignores_the_vendor_label(tmp_path, monkeypatch):
    # whatever the row claims (incl. a literal "HKD"), the feed cannot confirm HKD
    # statements, so no PE/PB is ever produced from it
    cache = tmp_path / "fundamentals.parquet"
    _write_cache(cache, [{"ticker": f"{i}.HK", "profile": {}, "forecast": {},
                          "financials": [_row(2025, currency=lab)]}
                         for i, lab in enumerate(("HKD", "CNY", "USD", None))])
    monkeypatch.setattr(hf, "CACHE", cache)
    out = hf.build_all({f"{i}.HK": 50.0 for i in range(4)})
    assert len(out) == 4
    assert all(r["valuation"] == {} and r["currency"] == "CNY" for r in out.values())


def test_archetype():
    assert hf._archetype({"roe": 20.0, "ni": 5e8, "debt_ratio": 30.0}, {"rev_cagr": 8.0}) \
        == "quality_compounder"
    assert hf._archetype({"roe": 5.0, "ni": -1e8}, {"rev_cagr": 3.0}) == "speculative_unprofitable"


def test_build_all_empty_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(hf, "CACHE", tmp_path / "missing.parquet")
    assert hf.build_all({}) == {}
