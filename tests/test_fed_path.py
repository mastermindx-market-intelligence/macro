"""Pure-function tests for the Fed policy-path leaf + ZQ/SR3 collector — no network.

The live fetch (Yahoo ZQ/SR3, FRED FEDTARMD) throttles the sandbox, so these drive
the deterministic math on synthetic prices/dots — the global-liquidity playbook.
"""
import inspect
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import rate_futures as rf  # noqa: E402
from engine import fed_path as fp  # noqa: E402

_CFG = {"horizons_m": [1, 3, 6, 12], "max_months": 18}


# --------------------------------------------------------------------------- #
# collector: contract generation
# --------------------------------------------------------------------------- #
def test_gen_contracts_monthly_rolls_off_asof():
    cs = rf.gen_contracts("ZQ", ["CBT"], "monthly", 14, date(2026, 6, 12))
    assert len(cs) == 14
    # first contract = the run month; symbol uses the CME month code
    assert (cs[0]["year"], cs[0]["month"]) == (2026, 6)
    assert cs[0]["symbols"][0] == "ZQM26.CBT"   # M = June
    # consecutive months, wrapping the year
    assert (cs[7]["year"], cs[7]["month"]) == (2027, 1)
    assert cs[7]["symbols"][0] == "ZQF27.CBT"   # F = January


def test_gen_contracts_quarterly_imm_only():
    qs = rf.gen_contracts("SR3", ["CME"], "quarterly", 4, date(2026, 6, 12))
    months = [(c["year"], c["month"]) for c in qs]
    assert months == [(2026, 6), (2026, 9), (2026, 12), (2027, 3)]
    assert all(c["month"] in (3, 6, 9, 12) for c in qs)


def test_gen_contracts_multiple_exchange_candidates():
    cs = rf.gen_contracts("ZQ", ["CBT", "NYB"], "monthly", 1, date(2026, 6, 1))
    assert cs[0]["symbols"] == ["ZQM26.CBT", "ZQM26.NYB"]


# --------------------------------------------------------------------------- #
# collector: implied-path interpolation
# --------------------------------------------------------------------------- #
def _synthetic_strip(asof: date, n: int, cut_per_month: float):
    """Monthly ZQ strip that prices `cut_per_month` of cuts each month from 4.33%."""
    idx = pd.bdate_range("2026-05-15", "2026-06-12")
    cs = rf.gen_contracts("ZQ", ["CBT"], "monthly", n, asof)
    out = {}
    for c in cs:
        ma = rf._months_diff(c["year"], c["month"], asof.year, asof.month)
        rate = 4.33 - cut_per_month * ma
        out[(c["year"], c["month"])] = pd.Series(100.0 - rate, index=idx)
    return out


def test_implied_path_interpolates_to_horizons():
    strip = _synthetic_strip(date(2026, 6, 12), 14, 0.10)
    path = rf.implied_path(strip, [1, 3, 6, 12], 18, "monthly")
    assert list(path.columns) == ["m1", "m3", "m6", "m12"]
    row = path.iloc[-1]
    # monthly centre offset 0.5 → horizon h maps to rate 4.33 − 0.10*(h−0.5)
    assert abs(row["m1"] - (4.33 - 0.10 * 0.5)) < 1e-6
    assert abs(row["m12"] - (4.33 - 0.10 * 11.5)) < 1e-6
    # monotone decreasing as the market prices steady cuts
    assert row["m1"] > row["m3"] > row["m6"] > row["m12"]


def test_implied_path_never_extrapolates_beyond_strip():
    # only 2 monthly contracts → strip spans ~0.5..1.5 months; 6m/12m must be None
    strip = _synthetic_strip(date(2026, 6, 12), 2, 0.10)
    path = rf.implied_path(strip, [1, 3, 6, 12], 18, "monthly")
    row = path.iloc[-1]
    assert row["m1"] is not None
    assert pd.isna(row.get("m6")) or row.get("m6") is None
    assert pd.isna(row.get("m12")) or row.get("m12") is None


def test_implied_path_empty_input():
    assert rf.implied_path({}, [1, 3], 18, "monthly").empty


# --------------------------------------------------------------------------- #
# engine: dot-plot parsing
# --------------------------------------------------------------------------- #
def test_dots_by_year_keeps_forward_and_latest_write():
    s = pd.Series({
        pd.Timestamp("2024-12-31"): 4.50,   # past year — dropped
        pd.Timestamp("2026-12-31"): 3.90,
        pd.Timestamp("2027-12-31"): 3.40,
    })
    dots = fp._dots_by_year(s, 2026)
    assert [d["year"] for d in dots] == [2026, 2027]
    assert dots[0]["median"] == 3.9


def test_dots_by_year_none_and_empty():
    assert fp._dots_by_year(None, 2026) == []
    assert fp._dots_by_year(pd.Series(dtype=float), 2026) == []


# --------------------------------------------------------------------------- #
# engine: the lean classifier
# --------------------------------------------------------------------------- #
def test_lean_thresholds():
    assert fp._lean(4)[0] == "market ≈ the Fed"      # < half a 25bp move
    assert fp._lean(-40)[0] == "market more dovish than the Fed"
    assert fp._lean(40)[0] == "market more hawkish than the Fed"
    assert fp._lean(None)[0] == "—"


# --------------------------------------------------------------------------- #
# engine: compute()
# --------------------------------------------------------------------------- #
def _dots():
    return pd.Series({pd.Timestamp("2026-12-31"): 3.875,
                      pd.Timestamp("2027-12-31"): 3.375})


def test_compute_full_path_and_gap():
    zq = {"m1": 4.30, "m3": 4.12, "m6": 3.92, "m12": 3.55}
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=_dots(),
                     zq_path_row=zq, sofr_path_row=None, zq_front_implied=4.31,
                     ntfs=-0.42, curve_tp_adj=-0.15, rate_exp_proxy=-0.55, cfg=_CFG)
    assert out["target_mid"] == 4.38
    assert out["implied"]["m12"] == 3.55
    # (4.33 − 3.55) / 0.25 ≈ 3 cuts
    assert out["implied_cuts_12m"] == 3
    assert out["implied_bp_12m"] == -78
    # gap at end-2026 (June→Dec = 6m) compares the 6m-implied to the 2026 dot
    assert out["gap"]["horizon_label"] == "end-2026"
    assert out["gap"]["horizon_months"] == 6
    assert out["gap"]["market"] == 3.92
    assert out["gap"]["fed_dot"] == 3.875
    assert out["gap"]["gap_bp"] == 4
    assert out["gap"]["lean_en"] == "market ≈ the Fed"
    assert out["implied_source_en"] == "ZQ fed-funds futures"
    # display-only contract — no scored leg should ever appear
    assert "score" not in out and "mrs" not in out


def test_compute_prefers_zq_then_sofr():
    sofr = {"m1": 4.25, "m12": 3.40}
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row=None, sofr_path_row=sofr, zq_front_implied=4.31,
                     ntfs=None, curve_tp_adj=None, rate_exp_proxy=None, cfg=_CFG)
    assert out["implied_source_en"] == "SR3 SOFR futures"
    assert out["implied"]["m12"] == 3.40


def test_compute_degraded_no_strip_no_dots():
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row=None, sofr_path_row=None, zq_front_implied=4.31,
                     ntfs=-0.2, curve_tp_adj=None, rate_exp_proxy=-0.5, cfg=_CFG)
    assert out["implied_source_en"] == "ZQ front (30d) only"
    assert out["implied"].get("m1") == 4.31
    # no far horizon → no fabricated cut count, no gap
    assert out["implied_cuts_12m"] is None
    assert out["gap"] is None
    assert out["dots"] == []
    assert out["headline_en"].startswith("Policy set at")


def test_compute_far_dot_shows_dots_but_no_gap():
    # a single 2028 dot is >12m out → cannot compare against the 12m strip
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50,
                     dot_series=pd.Series({pd.Timestamp("2028-12-31"): 3.0}),
                     zq_path_row={"m1": 4.3, "m12": 3.6}, sofr_path_row=None,
                     zq_front_implied=4.3, ntfs=0.1, curve_tp_adj=0.0,
                     rate_exp_proxy=0.0, cfg=_CFG)
    assert out["gap"] is None
    assert [d["year"] for d in out["dots"]] == [2028]


def test_compute_all_empty_returns_none():
    assert fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=None,
                      target_low=None, target_high=None, dot_series=None,
                      zq_path_row=None, sofr_path_row=None, zq_front_implied=None,
                      ntfs=None, curve_tp_adj=None, rate_exp_proxy=None, cfg=_CFG) is None


# =========================================================================== #
# D0 — provenance: per-strip / per-dot source metadata (RIC-INCLUDED-CORE)
#
# GOLDEN CONTROL: the three strings below are byte-for-byte captures of the
# BASE (pre-D0) compute() output for fixtures F1/F2/F3, `built` excluded, via
# json.dumps(..., sort_keys=True, ensure_ascii=False, default=str). The legacy
# output must never change — D0 only ADDS `implied_source_meta`.
# =========================================================================== #
_GOLDEN_F1 = '''{"asof": "2026-06-12", "curve_tp_adj": -0.15, "dots": [{"median": 3.875, "year": 2026}, {"median": 3.375, "year": 2027}], "gap": {"fed_dot": 3.875, "gap_bp": 4, "horizon_label": "end-2026", "horizon_months": 6, "lean_en": "market ≈ the Fed", "lean_zh": "市场与美联储基本一致", "market": 3.92}, "headline_en": "Market prices ~3 cuts over the next 12m (funds 4.33% → 3.55%)", "headline_zh": "市场为未来12个月定价约降息3次（基金利率 4.33% → 3.55%）", "implied": {"m1": 4.3, "m12": 3.55, "m3": 4.12, "m6": 3.92, "now": 4.33}, "implied_bp_12m": -78, "implied_cuts_12m": 3, "implied_cuts_6m": 2, "implied_source_en": "ZQ fed-funds futures", "implied_source_zh": "ZQ 联邦基金期货", "note_en": "Display / LLM-context only. The implied path is a market PRICE (the futures-implied funds rate), not a forecast edge, and repricing is REACTIVE — it moves after data and the Fed, it does not lead. Never scored, never an MRS leg. ZQ/SR3 = keyless CME futures; dots = FRED FEDTARMD (FOMC SEP median). Cite the CME/FRED.", "note_zh": "仅供展示 / LLM 上下文。隐含路径是市场价格（期货隐含的基金利率），并非预测优势，且重新定价是被动的——它在数据和美联储之后变动，并不领先。从不评分，从不作为 MRS 项。ZQ/SR3=无需密钥的 CME 期货；点阵图=FRED FEDTARMD（FOMC SEP 中位数）。请注明 CME/FRED。", "ntfs": -0.42, "policy_rate": 4.33, "rate_exp_proxy": -0.55, "read_en": "At end-2026 the market implies 3.92% vs the Fed's 3.88% median dot (+4bp — market ≈ the Fed). The near-term forward spread is negative — the market prices cuts ~18m out (-0.42pp).", "read_zh": "在end-2026，市场隐含 3.92% 对比美联储 3.88% 的中位点（+4基点 — 市场与美联储基本一致）。近端远期利差为负——市场为约18个月后的降息定价（-0.42个百分点）。", "sofr_path": null, "target_high": 4.5, "target_low": 4.25, "target_mid": 4.38}'''
_GOLDEN_F2 = '''{"asof": "2026-06-12", "curve_tp_adj": -0.15, "dots": [{"median": 3.875, "year": 2026}, {"median": 3.375, "year": 2027}], "gap": {"fed_dot": 3.875, "gap_bp": 8, "horizon_label": "end-2026", "horizon_months": 6, "lean_en": "market ≈ the Fed", "lean_zh": "市场与美联储基本一致", "market": 3.95}, "headline_en": "Market prices ~3 cuts over the next 12m (funds 4.33% → 3.60%)", "headline_zh": "市场为未来12个月定价约降息3次（基金利率 4.33% → 3.60%）", "implied": {"m1": 4.28, "m12": 3.6, "m3": 4.1, "m6": 3.95, "now": 4.33}, "implied_bp_12m": -73, "implied_cuts_12m": 3, "implied_cuts_6m": 2, "implied_source_en": "SR3 SOFR futures", "implied_source_zh": "SR3 SOFR 期货", "note_en": "Display / LLM-context only. The implied path is a market PRICE (the futures-implied funds rate), not a forecast edge, and repricing is REACTIVE — it moves after data and the Fed, it does not lead. Never scored, never an MRS leg. ZQ/SR3 = keyless CME futures; dots = FRED FEDTARMD (FOMC SEP median). Cite the CME/FRED.", "note_zh": "仅供展示 / LLM 上下文。隐含路径是市场价格（期货隐含的基金利率），并非预测优势，且重新定价是被动的——它在数据和美联储之后变动，并不领先。从不评分，从不作为 MRS 项。ZQ/SR3=无需密钥的 CME 期货；点阵图=FRED FEDTARMD（FOMC SEP 中位数）。请注明 CME/FRED。", "ntfs": -0.42, "policy_rate": 4.33, "rate_exp_proxy": -0.55, "read_en": "At end-2026 the market implies 3.95% vs the Fed's 3.88% median dot (+8bp — market ≈ the Fed). The near-term forward spread is negative — the market prices cuts ~18m out (-0.42pp).", "read_zh": "在end-2026，市场隐含 3.95% 对比美联储 3.88% 的中位点（+8基点 — 市场与美联储基本一致）。近端远期利差为负——市场为约18个月后的降息定价（-0.42个百分点）。", "sofr_path": {"m1": 4.28, "m12": 3.6, "m3": 4.1, "m6": 3.95}, "target_high": 4.5, "target_low": 4.25, "target_mid": 4.38}'''
_GOLDEN_F3 = '''{"asof": "2026-06-12", "curve_tp_adj": -0.15, "dots": [], "gap": null, "headline_en": "Policy set at 4.33%", "headline_zh": "政策利率设定于 4.33%", "implied": {"m1": 4.31, "now": 4.33}, "implied_bp_12m": null, "implied_cuts_12m": null, "implied_cuts_6m": null, "implied_source_en": "ZQ front (30d) only", "implied_source_zh": "仅 ZQ 近月 (30天)", "note_en": "Display / LLM-context only. The implied path is a market PRICE (the futures-implied funds rate), not a forecast edge, and repricing is REACTIVE — it moves after data and the Fed, it does not lead. Never scored, never an MRS leg. ZQ/SR3 = keyless CME futures; dots = FRED FEDTARMD (FOMC SEP median). Cite the CME/FRED.", "note_zh": "仅供展示 / LLM 上下文。隐含路径是市场价格（期货隐含的基金利率），并非预测优势，且重新定价是被动的——它在数据和美联储之后变动，并不领先。从不评分，从不作为 MRS 项。ZQ/SR3=无需密钥的 CME 期货；点阵图=FRED FEDTARMD（FOMC SEP 中位数）。请注明 CME/FRED。", "ntfs": -0.42, "policy_rate": 4.33, "rate_exp_proxy": -0.55, "read_en": "The near-term forward spread is negative — the market prices cuts ~18m out (-0.42pp).", "read_zh": "近端远期利差为负——市场为约18个月后的降息定价（-0.42个百分点）。", "sofr_path": null, "target_high": 4.5, "target_low": 4.25, "target_mid": 4.38}'''

_F1_ZQ = {"m1": 4.30, "m3": 4.12, "m6": 3.92, "m12": 3.55}
_F2_SOFR = {"m1": 4.28, "m3": 4.10, "m6": 3.95, "m12": 3.60}
_SR3_SOFR = {"m1": 4.27, "m3": 4.09, "m6": 3.97, "m12": 3.61}


def _f1(**over):
    kw = dict(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33, target_low=4.25,
              target_high=4.50, dot_series=_dots(), zq_path_row=dict(_F1_ZQ),
              sofr_path_row=None, zq_front_implied=4.31, ntfs=-0.42,
              curve_tp_adj=-0.15, rate_exp_proxy=-0.55, cfg=_CFG)
    kw.update(over)
    return fp.compute(**kw)


def _zq_monthlies(n=18, first=(2026, 7)):
    """ZQN26.CBT .. ZQZ27.CBT — every delivery month from `first`."""
    y, m = first
    out = []
    for _ in range(n):
        out.append(f"ZQ{rf._MONTH_CODE[m]}{y % 100:02d}.CBT")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


_SR3_QUARTERS = ["SR3M26.CME", "SR3U26.CME", "SR3Z26.CME", "SR3H27.CME", "SR3M27.CME"]


def _line(out):
    return json.dumps({k: v for k, v in out.items() if k != "built"},
                      sort_keys=True, ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- #
# 1 — signature
# --------------------------------------------------------------------------- #
def test_compute_new_params_are_keyword_only_and_default_none():
    sig = inspect.signature(fp.compute)
    for name in ("metadata", "cutoff"):
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.KEYWORD_ONLY
        assert p.default is None


# --------------------------------------------------------------------------- #
# 2 — golden control: mode 1 is byte-identical to base
# --------------------------------------------------------------------------- #
def test_no_keyword_output_is_byte_identical_to_base_golden():
    assert _line(_f1()) == _GOLDEN_F1
    assert _line(_f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR))) == _GOLDEN_F2
    assert _line(_f1(zq_path_row=None, sofr_path_row=None, dot_series=None)) == _GOLDEN_F3
    for out in (_f1(), _f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR)),
                _f1(zq_path_row=None, sofr_path_row=None, dot_series=None)):
        assert "implied_source_meta" not in out


# --------------------------------------------------------------------------- #
# 3 — mode 2 only adds the one new key
# --------------------------------------------------------------------------- #
def test_metadata_without_cutoff_only_adds_implied_source_meta():
    md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies()},
          "sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}
    m2 = _f1(metadata=md)
    m1 = _f1()
    strip = {k: v for k, v in m2.items() if k not in ("implied_source_meta", "built")}
    assert strip == {k: v for k, v in m1.items() if k != "built"}
    m2b = _f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR), metadata=md)
    m1b = _f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR))
    stripb = {k: v for k, v in m2b.items() if k not in ("implied_source_meta", "built")}
    assert stripb == {k: v for k, v in m1b.items() if k != "built"}


# --------------------------------------------------------------------------- #
# 4 — stale ZQ + fresh SR3
# --------------------------------------------------------------------------- #
def test_stale_zq_with_fresh_sr3_never_inherits_zq_dates():
    md = {"zq": {"observation_date": "2026-06-01", "contracts": _zq_monthlies()},
          "sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}
    out = _f1(sofr_path_row=dict(_SR3_SOFR), metadata=md)
    # legacy selection still ZQ, label unchanged
    assert out["implied_source_en"] == "ZQ fed-funds futures"
    meta = out["implied_source_meta"]
    assert meta["strips"]["zq"]["value_state"] == "stale"
    assert "stale" in meta["strips"]["zq"]["quality"]
    assert meta["strips"]["zq"]["observation_time"] == "2026-06-01"
    sm = meta["strips"]["sofr"]
    assert sm["observation_time"] == "2026-06-11"
    assert sm["value_state"] == "present"
    # SR3 reference periods are IMM quarters — never a ZQ calendar month
    assert sm["contracts"] and all(c["reference_start"] for c in sm["contracts"])
    for c in sm["contracts"]:
        start, end = c["reference_start"], c["reference_end"]
        assert int(start[8:10]) >= 15                      # third Wednesday, not day 1
        assert int(start[5:7]) in (3, 6, 9, 12)            # IMM months only
        assert not (start.endswith("-01") and start[:7] == end[:7])
    # no ZQ date anywhere in the SR3 meta
    assert "2026-06-01" not in json.dumps(sm, default=str)
    assert meta["gap"]["status"] == "unavailable"
    assert meta["gap"]["reason"] == "operand_stale:right"


# --------------------------------------------------------------------------- #
# 5 — SR3 fallback labelled SOFR, never fed funds
# --------------------------------------------------------------------------- #
def test_sr3_fallback_is_labelled_sofr_never_fed_funds():
    md = {"sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}
    out = _f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR), metadata=md)
    assert out["implied_source_en"] == "SR3 SOFR futures"
    meta = out["implied_source_meta"]
    assert meta["selected_strip"] == "sofr"
    sm = meta["strips"]["sofr"]
    assert "fallback_strip" in sm["quality"]
    assert sm["rate_index"] == "SOFR"
    assert meta["gap"]["status"] == "not_comparable"
    assert meta["gap"]["reason"] == "basis_mismatch:rate_index"
    blob = json.dumps(sm, default=str)
    assert "fed funds" not in blob and "fed-funds" not in blob and "EFFR" not in blob


# --------------------------------------------------------------------------- #
# 6 — absent contract/date is unknown, never filled
# --------------------------------------------------------------------------- #
def test_absent_contract_date_is_unknown_never_filled():
    md = {"zq": {}, "sofr": {}}
    out = _f1(metadata=md)
    zm = out["implied_source_meta"]["strips"]["zq"]
    assert zm["contracts"] is None
    assert "contract_reference_unknown" in zm["limitations"]
    assert zm["observation_time"] is None
    assert zm["observation_precision"] == "unknown"
    assert out["implied_source_meta"]["gap"]["reason"] == "unknown_basis:reference_end"
    # one unparseable symbol: entry keeps vendor_symbol, everything else None
    md2 = {"zq": {"observation_date": "2026-06-11",
                  "contracts": ["ZQX26.CBT", "ZQ"]}}
    out2 = _f1(metadata=md2)
    cs = out2["implied_source_meta"]["strips"]["zq"]["contracts"]
    assert cs[0]["reference_start"] == "2026-11-01"
    bad = cs[1]
    assert bad["vendor_symbol"] == "ZQ"
    assert all(bad[k] is None for k in ("contract_code", "exchange_suffix",
                                        "listing_exchange", "reference_start",
                                        "reference_end", "centre_months"))
    assert "contract_reference_unknown" in \
        out2["implied_source_meta"]["strips"]["zq"]["limitations"]


# --------------------------------------------------------------------------- #
# 7 — price-type vocabulary
# --------------------------------------------------------------------------- #
def test_price_type_settlement_vs_last_trade_vs_vendor_close():
    def zm(pt):
        md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies(),
                     "price_type": pt}}
        return _f1(metadata=md)["implied_source_meta"]["strips"]["zq"]

    s = zm("settlement")
    assert s["price_type"] == "settlement"
    assert s["vintage"] == "2026-06-11"
    assert "last_trade_not_settlement" not in s["limitations"]
    assert "vendor_close_not_exchange_settlement" not in s["limitations"]
    assert "price_type_unknown" not in s["limitations"]

    lt = zm("last_trade")
    assert lt["vintage"] is None
    assert "last_trade_not_settlement" in lt["limitations"]

    vc = zm("vendor_daily_close")
    assert vc["vintage"] is None
    assert "vendor_close_not_exchange_settlement" in vc["limitations"]

    bogus = zm("bogus")
    assert bogus["price_type"] is None
    assert "price_type_unknown" in bogus["limitations"]


# --------------------------------------------------------------------------- #
# 8 — mismatched horizon refuses the SEP-vs-market gap
# --------------------------------------------------------------------------- #
def test_mismatched_horizon_refuses_sep_market_gap():
    md = {"zq": {"observation_date": "2026-06-29", "contracts": _zq_monthlies()}}
    out = _f1(asof=pd.Timestamp("2026-07-02"), metadata=md)
    # legacy H = 5 → bracket Oct/Nov 2026 → market interval misses December
    assert out["gap"]["horizon_months"] == 5
    gm = out["implied_source_meta"]["gap"]
    assert gm["status"] == "not_comparable"
    assert gm["reason"] == "basis_mismatch:reference_end"
    assert gm["market_reference_start"] == "2026-10-01"
    assert gm["market_reference_end"] == "2026-11-30"
    # the legacy gap dict is still present and unchanged
    legacy = _f1(asof=pd.Timestamp("2026-07-02"))["gap"]
    assert out["gap"] == legacy


# --------------------------------------------------------------------------- #
# 9 — matched horizon is comparable after a named transformation
# --------------------------------------------------------------------------- #
def test_matched_horizon_gap_is_comparable_after_transformation():
    md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies()}}
    out = _f1(metadata=md)
    gm = out["implied_source_meta"]["gap"]
    assert gm["status"] == "comparable_after_transformation"
    assert gm["transform"] == "year_end_interval_match"
    assert gm["market_reference_start"] == "2026-11-01"
    assert gm["market_reference_end"] == "2026-12-31"
    assert gm["market_horizon_months"] == 6
    assert "participant appropriate-policy projection, not a committee promise or probability" \
        in gm["limitations"]


# --------------------------------------------------------------------------- #
# 10 — post-cutoff dots are refused and never leak
# --------------------------------------------------------------------------- #
def test_post_cutoff_dots_are_refused_and_never_leak():
    base_md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies()}}
    out = _f1(metadata={**base_md, "dots": {"release_date": "2026-06-17",
                                            "release_precision": "day"}},
              cutoff="2026-06-15")
    dm = out["implied_source_meta"]["dots"]
    assert dm["value_state"] == "refused"
    assert "after_cutoff" in dm["limitations"]
    assert out["dots"] == []
    assert out["gap"] is None
    blob = json.dumps(out, default=str)
    assert "3.875" not in blob and "3.375" not in blob

    # month precision: an equal month is NOT later
    out_m = _f1(metadata={**base_md, "dots": {"release_date": "2026-06",
                                              "release_precision": "month"}},
                cutoff="2026-06-15")
    assert out_m["implied_source_meta"]["dots"]["value_state"] == "present"
    assert out_m["dots"]

    # a later month IS later
    out_l = _f1(metadata={**base_md, "dots": {"release_date": "2026-07",
                                              "release_precision": "month"}},
                cutoff="2026-06-15")
    assert out_l["implied_source_meta"]["dots"]["value_state"] == "refused"
    assert out_l["dots"] == []


# --------------------------------------------------------------------------- #
# 11 — post-cutoff strip is refused and never leaks
# --------------------------------------------------------------------------- #
def test_post_cutoff_strip_is_refused_and_never_leaks():
    md = {"zq": {"observation_date": "2026-06-09", "contracts": _zq_monthlies()},
          "sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}
    out = _f1(sofr_path_row=dict(_SR3_SOFR), metadata=md, cutoff="2026-06-10")
    sm = out["implied_source_meta"]["strips"]["sofr"]
    assert sm["value_state"] == "refused"
    assert "after_cutoff" in sm["limitations"]
    assert out["sofr_path"] is None
    blob = json.dumps(out, default=str)
    assert "3.97" not in blob and "3.61" not in blob
    assert out["implied_source_en"] == "ZQ fed-funds futures"

    # a strip with no observation_date under a cutoff is withheld
    md2 = {"zq": {"observation_date": "2026-06-09", "contracts": _zq_monthlies()},
           "sofr": {"contracts": _SR3_QUARTERS}}
    out2 = _f1(sofr_path_row=dict(_SR3_SOFR), metadata=md2, cutoff="2026-06-10")
    sm2 = out2["implied_source_meta"]["strips"]["sofr"]
    assert sm2["value_state"] == "withheld"
    assert "evidence_time_unknown" in sm2["limitations"]
    assert out2["sofr_path"] is None


# --------------------------------------------------------------------------- #
# 12 — missing strip is missing, never 0 bp
# --------------------------------------------------------------------------- #
def test_missing_strip_is_missing_never_zero_bp():
    md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies()},
          "sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}
    out = _f1(zq_path_row=None, sofr_path_row=None, dot_series=None, metadata=md)
    meta = out["implied_source_meta"]
    assert meta["strips"]["zq"]["value_state"] == "missing"
    assert meta["strips"]["sofr"]["value_state"] == "missing"
    assert meta["strips"]["zq"]["observation_time"] is None
    assert out["implied_bp_12m"] is None
    assert meta["selected_strip"] == "zq_front"

    out2 = _f1(zq_path_row=None, sofr_path_row=None, dot_series=None,
               zq_front_implied=None, metadata=md)
    assert out2 is not None                 # policy rate alone still shows
    assert out2["implied_bp_12m"] is None   # never 0


# --------------------------------------------------------------------------- #
# 13/14/15/16 — collector provenance primitives
# --------------------------------------------------------------------------- #
def test_contract_reference_period_monthly_and_imm():
    assert rf.contract_reference_period(2026, 2, "monthly") == ("2026-02-01", "2026-02-28")
    assert rf.contract_reference_period(2028, 2, "monthly") == ("2028-02-01", "2028-02-29")
    assert rf.contract_reference_period(2026, 12, "monthly") == ("2026-12-01", "2026-12-31")
    assert rf.contract_reference_period(2026, 3, "quarterly") == ("2026-03-18", "2026-06-16")
    assert rf.contract_reference_period(2026, 12, "quarterly") == ("2026-12-16", "2027-03-16")
    assert rf.contract_reference_period(2026, 6, "weekly") == (None, None)
    # independent calendar cross-check of the third-Wednesday rule
    import calendar
    def third_wed(y, m):
        days = [w[calendar.WEDNESDAY] for w in calendar.monthcalendar(y, m)
                if w[calendar.WEDNESDAY]]
        return days[2]
    assert third_wed(2026, 3) == 18 and third_wed(2026, 6) == 17
    assert third_wed(2026, 12) == 16 and third_wed(2027, 3) == 17


def test_parse_contract_symbol():
    p = rf.parse_contract_symbol("ZQX26.CBT")
    assert p == {"vendor_symbol": "ZQX26.CBT", "contract_code": "ZQX26",
                 "symbol_root": "ZQ", "month_code": "X", "year": 2026, "month": 11,
                 "exchange_suffix": "CBT", "listing_exchange": "CBOT"}
    q = rf.parse_contract_symbol("ZQQ26.CBT")
    assert (q["symbol_root"], q["month_code"], q["year"], q["month"]) == ("ZQ", "Q", 2026, 8)
    s = rf.parse_contract_symbol("SR3H26.CME")
    assert (s["symbol_root"], s["year"], s["month"],
            s["listing_exchange"]) == ("SR3", 2026, 3, "CME")
    nyb = rf.parse_contract_symbol("ZQF27.NYB")
    assert nyb["exchange_suffix"] == "NYB" and nyb["listing_exchange"] is None
    for bad in (None, "", "ZQ", "ZQX2", "FOO"):
        assert rf.parse_contract_symbol(bad) is None
    assert rf.strip_basis("ZQ")["rate_index"] == "EFFR"
    assert rf.strip_basis("SR3")["averaging_law"] == "compounded_business_day"
    unknown = rf.strip_basis("ZZ")
    assert set(unknown) == {"rate_index", "averaging_law", "target",
                            "basket_or_index", "cadence"}
    assert all(v is None for v in unknown.values())


def test_contracts_frame_keeps_exact_vendor_symbols():
    s1 = pd.Series([95.70, 95.71], index=pd.DatetimeIndex(["2026-06-10", "2026-06-11"]))
    s2 = pd.Series([95.60], index=pd.DatetimeIndex(["2026-06-11"]))
    cf = rf.contracts_frame({"ZQX26.CBT": s1, "ZQZ26.CBT": s2})
    assert list(cf.columns) == ["ZQX26.CBT", "ZQZ26.CBT"]
    assert list(cf.index) == list(pd.DatetimeIndex(["2026-06-10", "2026-06-11"]))
    assert cf.loc[pd.Timestamp("2026-06-10"), "ZQX26.CBT"] == 95.70
    assert cf.loc[pd.Timestamp("2026-06-11"), "ZQZ26.CBT"] == 95.60
    assert pd.isna(cf.loc[pd.Timestamp("2026-06-10"), "ZQZ26.CBT"])
    assert rf.contracts_frame({}).empty


def test_strip_stale_after_days_pinned_to_adapter():
    assert fp.STRIP_STALE_AFTER_DAYS == rf.RateFuturesAdapter.stale_after_days == 5


# --------------------------------------------------------------------------- #
# 17 — snapshot wires the live strip observation dates
# --------------------------------------------------------------------------- #
def test_snapshot_attaches_strip_observation_dates(monkeypatch):
    idx_zq = pd.DatetimeIndex(["2026-06-10", "2026-06-11"])
    zq_path = pd.DataFrame({"m1": [4.30, 4.30], "m3": [4.12, 4.12],
                            "m6": [3.92, 3.92], "m12": [3.55, 3.55]}, index=idx_zq)
    idx_sf = pd.DatetimeIndex(["2026-06-04", "2026-06-05"])
    sofr_path = pd.DataFrame({"m1": [4.28, 4.28], "m3": [4.10, 4.10],
                              "m6": [3.95, 3.95], "m12": [3.60, 3.60]}, index=idx_sf)
    zq_cf = pd.DataFrame({"ZQN26.CBT": [95.7, None], "ZQQ26.CBT": [95.8, 95.81],
                          "ZQX26.CBT": [95.9, 95.91]}, index=idx_zq)
    frames = {("rate_futures", "zq_path"): zq_path,
              ("rate_futures", "sofr_path"): sofr_path,
              ("rate_futures", "zq_contracts"): zq_cf}
    monkeypatch.setattr(fp.store, "read",
                        lambda ns, key: frames.get((ns, key)))
    import engine.bonds
    monkeypatch.setattr(engine.bonds, "near_term_forward_spread",
                        lambda f: pd.Series([-0.42] * len(f), index=f.index))
    f = pd.DataFrame({"fed_funds": [4.33], "fed_target_lower": [4.25],
                      "fed_target_upper": [4.50], "zq_implied_rate": [4.31],
                      "rate_expectations_proxy": [-0.55], "curve_tp_adj": [-0.15]},
                     index=pd.DatetimeIndex(["2026-06-11"]))
    out = fp.snapshot(f, cfg=_CFG)
    meta = out["implied_source_meta"]
    zm = meta["strips"]["zq"]
    assert zm["observation_time"] == "2026-06-11"          # zq_path's own last date
    assert [c["vendor_symbol"] for c in zm["contracts"]] == \
        ["ZQQ26.CBT", "ZQX26.CBT"]                         # non-null at that date
    assert zm["price_type"] == rf.PRICE_TYPE
    assert zm["vendor"] == rf.VENDOR and zm["rights"] == rf.RIGHTS
    sm = meta["strips"]["sofr"]
    assert sm["observation_time"] == "2026-06-05"          # ITS OWN last date
    assert sm["contracts"] is None
    assert "sep_release_date_unknown" in meta["dots"]["limitations"]


# --------------------------------------------------------------------------- #
# 18 — selected-path basis identity (SR3 is never the EFFR path)
# --------------------------------------------------------------------------- #
def test_selected_basis_identity_marks_sr3_as_non_effr():
    note = ("legacy implied_* values are a compounded-SOFR substitute, "
            "not an EFFR/fed-funds path")
    md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies()},
          "sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}

    f2 = _f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR), metadata=md)
    m2 = f2["implied_source_meta"]
    assert m2["selected_basis"] == "sr3_compounded_sofr"
    assert m2["selected_is_effr"] is False
    assert "zq" in m2["missing_source"] and "sofr" not in m2["missing_source"]
    assert m2["legacy_value_basis_note"] == note
    # every legacy key equals the mode-1 output
    f1_legacy = _f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR))
    assert {k: v for k, v in f2.items()
            if k not in ("implied_source_meta", "built")} == \
        {k: v for k, v in f1_legacy.items() if k != "built"}

    f1 = _f1(metadata=md)
    m1 = f1["implied_source_meta"]
    assert m1["selected_basis"] == "zq_effr_monthly_average"
    assert m1["selected_is_effr"] is True
    assert "zq" not in m1["missing_source"]
    assert m1["legacy_value_basis_note"] is None

    f3 = _f1(zq_path_row=None, sofr_path_row=None, dot_series=None, metadata=md)
    m3 = f3["implied_source_meta"]
    assert m3["selected_basis"] == "zq_front_effr_30d"
    assert m3["selected_is_effr"] is True

    # a stale-but-selected ZQ is still the EFFR path and NOT missing
    st = _f1(sofr_path_row=dict(_SR3_SOFR),
             metadata={"zq": {"observation_date": "2026-06-01",
                              "contracts": _zq_monthlies()},
                       "sofr": {"observation_date": "2026-06-11",
                                "contracts": _SR3_QUARTERS}})
    ms = st["implied_source_meta"]
    assert ms["selected_basis"] == "zq_effr_monthly_average"
    assert ms["selected_is_effr"] is True
    assert "zq" not in ms["missing_source"]

# =========================================================================== #
# D1 — EFFR monthly-identity reading of the ZQ strip (RIC-INCLUDED-CORE, R-1)
#
# All D1 tests preserve every pre-existing test (only ADDED lines after this).
# =========================================================================== #
import datetime as _dt   # noqa: E402  — kept local to this block
import pytest as _pt     # noqa: E402  — kept local to this block
import engine.rates_command_basis as _rcb   # noqa: E402
import engine.event_calendar as _ec        # noqa: E402


# STEP 0(b) golden: byte-for-byte capture of fp.compute(... metadata=md ...).implied_source_meta
# at SOURCE BASE 582660ca342... — copied verbatim from /tmp/d1_golden.py output
_GOLDEN_D0_META = '''{"authority": "display_only", "cutoff": null, "dots": {"evidence_class": "survey_participant_projection", "first_public_evidence": null, "first_public_precision": "unknown", "limitations": ["sep_release_date_unknown", "participant appropriate-policy projection, not a committee promise or probability"], "reference_end": "2026-12-31", "reference_start": "2026-12-01", "rights": "public_official", "source": "fred:FEDTARMD", "source_version": null, "subject": "sep_median_2026", "target": "sep_fed_funds_year_end_median", "target_epoch": "2026-12-31", "value_state": "present", "vintage": null}, "gap": {"left": "dots", "limitations": ["participant appropriate-policy projection, not a committee promise or probability"], "market_horizon_months": 6, "market_reference_end": "2026-12-31", "market_reference_start": "2026-11-01", "reason": null, "right": "zq", "rule_id": "sep_vs_market_year_end.v1", "status": "comparable_after_transformation", "transform": "year_end_interval_match"}, "legacy_value_basis_note": null, "missing_source": ["sofr"], "schema": "fed_path_source_meta.v1", "selected_basis": "zq_effr_monthly_average", "selected_is_effr": true, "selected_strip": "zq", "strips": {"sofr": {"averaging_law": "compounded_business_day", "basket_or_index": "SOFR", "contracts": [{"centre_months": null, "contract_code": "SR3M26", "exchange_suffix": "CME", "listing_exchange": "CME", "reference_end": "2026-09-15", "reference_start": "2026-06-17", "vendor_symbol": "SR3M26.CME"}, {"centre_months": null, "contract_code": "SR3U26", "exchange_suffix": "CME", "listing_exchange": "CME", "reference_end": "2026-12-15", "reference_start": "2026-09-16", "vendor_symbol": "SR3U26.CME"}, {"centre_months": null, "contract_code": "SR3Z26", "exchange_suffix": "CME", "listing_exchange": "CME", "reference_end": "2027-03-16", "reference_start": "2026-12-16", "vendor_symbol": "SR3Z26.CME"}, {"centre_months": null, "contract_code": "SR3H27", "exchange_suffix": "CME", "listing_exchange": "CME", "reference_end": "2027-06-15", "reference_start": "2027-03-17", "vendor_symbol": "SR3H27.CME"}, {"centre_months": null, "contract_code": "SR3M27", "exchange_suffix": "CME", "listing_exchange": "CME", "reference_end": "2027-09-14", "reference_start": "2027-06-16", "vendor_symbol": "SR3M27.CME"}], "evidence_class": "market_implied_expectation", "limitations": ["price_type_unknown"], "observation_precision": "unknown", "observation_time": null, "price_type": null, "quality": [], "rate_index": "SOFR", "rights": "unknown", "source": "rate_futures:SR3", "source_version": null, "target": "sofr_compounded_imm_quarter", "value_state": "missing", "vendor": null, "vintage": null}, "zq": {"averaging_law": "arithmetic_calendar_day", "basket_or_index": "EFFR", "contracts": [{"centre_months": 1.5, "contract_code": "ZQN26", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2026-07-31", "reference_start": "2026-07-01", "vendor_symbol": "ZQN26.CBT"}, {"centre_months": 2.5, "contract_code": "ZQQ26", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2026-08-31", "reference_start": "2026-08-01", "vendor_symbol": "ZQQ26.CBT"}, {"centre_months": 3.5, "contract_code": "ZQU26", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2026-09-30", "reference_start": "2026-09-01", "vendor_symbol": "ZQU26.CBT"}, {"centre_months": 4.5, "contract_code": "ZQV26", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2026-10-31", "reference_start": "2026-10-01", "vendor_symbol": "ZQV26.CBT"}, {"centre_months": 5.5, "contract_code": "ZQX26", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2026-11-30", "reference_start": "2026-11-01", "vendor_symbol": "ZQX26.CBT"}, {"centre_months": 6.5, "contract_code": "ZQZ26", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2026-12-31", "reference_start": "2026-12-01", "vendor_symbol": "ZQZ26.CBT"}, {"centre_months": 7.5, "contract_code": "ZQF27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-01-31", "reference_start": "2027-01-01", "vendor_symbol": "ZQF27.CBT"}, {"centre_months": 8.5, "contract_code": "ZQG27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-02-28", "reference_start": "2027-02-01", "vendor_symbol": "ZQG27.CBT"}, {"centre_months": 9.5, "contract_code": "ZQH27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-03-31", "reference_start": "2027-03-01", "vendor_symbol": "ZQH27.CBT"}, {"centre_months": 10.5, "contract_code": "ZQJ27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-04-30", "reference_start": "2027-04-01", "vendor_symbol": "ZQJ27.CBT"}, {"centre_months": 11.5, "contract_code": "ZQK27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-05-31", "reference_start": "2027-05-01", "vendor_symbol": "ZQK27.CBT"}, {"centre_months": 12.5, "contract_code": "ZQM27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-06-30", "reference_start": "2027-06-01", "vendor_symbol": "ZQM27.CBT"}, {"centre_months": 13.5, "contract_code": "ZQN27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-07-31", "reference_start": "2027-07-01", "vendor_symbol": "ZQN27.CBT"}, {"centre_months": 14.5, "contract_code": "ZQQ27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-08-31", "reference_start": "2027-08-01", "vendor_symbol": "ZQQ27.CBT"}, {"centre_months": 15.5, "contract_code": "ZQU27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-09-30", "reference_start": "2027-09-01", "vendor_symbol": "ZQU27.CBT"}, {"centre_months": 16.5, "contract_code": "ZQV27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-10-31", "reference_start": "2027-10-01", "vendor_symbol": "ZQV27.CBT"}, {"centre_months": 17.5, "contract_code": "ZQX27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-11-30", "reference_start": "2027-11-01", "vendor_symbol": "ZQX27.CBT"}, {"centre_months": 18.5, "contract_code": "ZQZ27", "exchange_suffix": "CBT", "listing_exchange": "CBOT", "reference_end": "2027-12-31", "reference_start": "2027-12-01", "vendor_symbol": "ZQZ27.CBT"}], "evidence_class": "market_implied_expectation", "limitations": ["price_type_unknown"], "observation_precision": "day", "observation_time": "2026-06-11", "price_type": null, "quality": [], "rate_index": "EFFR", "rights": "unknown", "source": "rate_futures:ZQ", "source_version": null, "target": "effr_monthly_average", "value_state": "present", "vendor": null, "vintage": null}, "zq_front": {"averaging_law": "arithmetic_calendar_day", "evidence_class": "market_implied_expectation", "limitations": ["observation_time_unknown", "contract_reference_unknown"], "observation_precision": "unknown", "observation_time": null, "rate_index": "EFFR", "reference_end": null, "reference_start": null, "source": "zq_front_30d", "value_state": "present"}}}'''


def _d0_meta_call():
    """Reconstruct the call that produced _GOLDEN_D0_META on the base."""
    md = {"zq": {"observation_date": "2026-06-11", "contracts": _zq_monthlies()},
          "sofr": {"observation_date": "2026-06-11", "contracts": _SR3_QUARTERS}}
    return fp.compute(
        asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
        target_low=4.25, target_high=4.50, dot_series=_dots(),
        zq_path_row=dict(_F1_ZQ), sofr_path_row=None, zq_front_implied=4.31,
        ntfs=-0.42, curve_tp_adj=-0.15, rate_exp_proxy=-0.55, cfg=_CFG,
        metadata=md)


def _fixture8_md():
    """Fixture shared by tests 8/10/11: asof=2026-10-14, Q4 2026 ZQ strip, effr 4.10."""
    return {
        "zq": {"observation_date": "2026-10-13",
               "contract_closes": {"ZQV26.CBT": 95.8, "ZQX26.CBT": 95.4,
                                   "ZQZ26.CBT": 95.0}},
        "effr": {"value": 4.10, "observation_date": "2026-10-13",
                 "source": "fred:DFF"},
    }


def _make_md(zq_observation_date, closes, effr=None, target=None,
             effr_basis=None):
    md = {"zq": {"observation_date": zq_observation_date,
                 "contract_closes": closes}}
    if effr is not None:
        md["effr"] = effr
    if target is not None:
        md["target_range"] = target
    if effr_basis is not None:
        md["effr_basis"] = effr_basis
    return md


# --------------------------------------------------------------------------- #
# 1 — day-weighted identity canonical witness
# --------------------------------------------------------------------------- #
def test_d1_day_weighted_identity_canonical_witness(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                  effr={"value": 4.50, "observation_date": "2026-06-11",
                        "source": "fred:DFF"},
                  target={"low": 4.25, "high": 4.50,
                          "observation_date": "2026-06-11"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert block["status"] == "computed"
    assert block["cutoff_effective"] == "2026-06-13"
    assert block["cutoff_basis"] == "live_asof_plus_1d"
    assert block["effective_date_law"] == "decision_plus_1d"
    assert block["calendar_years_covered"] == [2026]
    assert block["assumptions"] == [
        "effective_date_convention=decision_plus_1d", "no_intermeeting_change",
        "effr_level_constant_between_effective_dates"]
    assert len(block["months"]) == 1
    june = block["months"][0]
    assert june["contract"] == "ZQM26.CBT"
    assert june["reference_start"] == "2026-06-01"
    assert june["reference_end"] == "2026-06-30"
    assert june["month_days"] == 30
    assert _pt.approx(june["monthly_average"]["value"]) == 4.25
    assert june["monthly_average"]["rate_index"] == "EFFR"
    assert june["effective_dates_inside"] == ["2026-06-16"]
    assert june["status"] == "identified_conditional"
    segs = june["identification"]["identified"]["segments"]
    assert segs[0] == ["2026-06-01", "2026-06-16", 4.5]
    assert _pt.approx(segs[1][2]) == 4.0
    assert segs[1][0] == "2026-06-16"
    assert segs[1][1] == "2026-06-30"
    assert _pt.approx(june["identification"]["identified"]["end_rate"]) == 4.0
    assert june["pre_change_rate"] == 4.5
    assert june["pre_change_rate_source"] == "observed_effr:fred:DFF@2026-06-11"
    assert june["reason"] == "pre_change_rate:observed_effr:fred:DFF@2026-06-11"
    assert june["weights"] == {"days_pre": 15, "days_post": 15,
                               "realised_days": 11, "remaining_days": 19}
    assert june["post_rate_sensitivity"] == 2.0
    # A16 witness:
    assert _pt.approx((june["monthly_average"]["value"] - 4.5) * 100) == -25
    assert _pt.approx((june["identification"]["identified"]["end_rate"]
                       - 4.5) * 100) == -50
    # vs_target_midpoint ALWAYS computed:
    vt = june["vs_target_midpoint"]
    assert vt["status"] == "comparable_after_transformation"
    # measured gap: 4.50 - 4.375 = 0.125 -> 12.5 bp (single_day_gap limitation)
    assert any("single_day_gap" == lim for lim in block["limitations"])


# --------------------------------------------------------------------------- #
# 2 — same average without pre rate is not unique
# --------------------------------------------------------------------------- #
def test_d1_same_average_without_pre_rate_is_not_unique(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75})  # avg = 4.25, no effr/target
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    june = block["months"][0]
    assert june["status"] == "missing_inputs"
    assert june["identification"] is not None
    assert june["identification"]["identified"] is None
    assert june["identification"]["missing"] and "pre_change_rate" in june["identification"]["missing"]
    assert june["pre_change_rate"] is None
    assert june["reason"] == "pre_change_rate_unavailable"
    # prove two paths share 4.25 average under 15/15 split:
    for (r_pre, r_post) in [(4.50, 4.00), (4.40, 4.10)]:
        assert _pt.approx(r_pre * 0.5 + r_post * 0.5) == 4.25


# --------------------------------------------------------------------------- #
# 3 — SR3 contract is refused and never solves
# --------------------------------------------------------------------------- #
def test_d1_sr3_contract_is_refused_never_solved(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75,
                                 "SR3U26.CME": 95.9,
                                 "GARBAGE": 50.0})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    refused = {(r["contract"], r["reason"]) for r in block["refused_contracts"]}
    assert ("SR3U26.CME", "basis_mismatch:rate_index") in refused
    assert ("GARBAGE", "unknown_basis:rate_index") in refused
    # only ZQM26 in months:
    assert len(block["months"]) == 1
    assert block["months"][0]["contract"] == "ZQM26.CBT"
    # adding metadata["sofr"]["contract_closes"] leaves the byte-identical block
    md_with_sofr = dict(md)
    md_with_sofr["sofr"] = {"observation_date": "2026-06-11",
                            "contract_closes": {"SR3Z26.CME": 95.85}}
    out2 = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                      target_low=None, target_high=None, dot_series=None,
                      zq_path_row={"m1": 4.30}, sofr_path_row=None,
                      zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                      rate_exp_proxy=None, cfg=_CFG, metadata=md_with_sofr)
    blob1 = json.dumps(out["implied_source_meta"]["effr_meeting_path"],
                        sort_keys=True, default=str)
    blob2 = json.dumps(out2["implied_source_meta"]["effr_meeting_path"],
                        sort_keys=True, default=str)
    assert blob1 == blob2
    # B0 witness — SR3 SOFR compounded vs ZQ EFFR arithmetic: not_comparable
    sr3_obs = _rcb.qualify_observation(4.32, {
        "subject": "sr3_quarter_avg", "evidence_class": "market_implied_expectation",
        "unit": "pct_ann_rate", "target": "sofr_compounded_imm_quarter",
        "basket_or_index": "SOFR", "rate_index": "SOFR",
        "averaging_law": "compounded_business_day",
        "reference_start": "2026-06-17", "reference_end": "2026-09-15",
        "observation_time": "2026-06-15", "observation_precision": "day",
        "first_public_evidence": "2026-06-15", "first_public_precision": "day",
        "rights": "public_official", "source": "rate_futures:SR3",
    }, "2026-06-15")
    zq_obs = _rcb.qualify_observation(4.25, {
        "subject": "zq_month_avg", "evidence_class": "market_implied_expectation",
        "unit": "pct_ann_rate", "target": "effr_monthly_average",
        "basket_or_index": "EFFR", "rate_index": "EFFR",
        "averaging_law": "arithmetic_calendar_day",
        "reference_start": "2026-06-01", "reference_end": "2026-06-30",
        "observation_time": "2026-06-11", "observation_precision": "day",
        "first_public_evidence": "2026-06-11", "first_public_precision": "day",
        "rights": "unknown", "source": "yfinance:ZQM26.CBT",
    }, "2026-06-15")
    res = _rcb.compare_qualified(sr3_obs, zq_obs, _rcb.RULES["sr3_vs_zq.v1"])
    assert res.status == "not_comparable"
    assert res.difference is None


# --------------------------------------------------------------------------- #
# 4 — target route without gap is not_identified; with explicit gap resolves
# --------------------------------------------------------------------------- #
def test_d1_target_route_without_gap_is_not_identified_never_zero(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    # no effr, no effr_basis; target present
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                  target={"low": 4.25, "high": 4.50,
                          "observation_date": "2026-06-11"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    june = out["implied_source_meta"]["effr_meeting_path"]["months"][0]
    assert june["status"] == "not_identified"
    assert june["reason"] == "underidentified:effr_target_basis"
    assert june["identification"] is None
    assert june["pre_change_rate"] is None
    assert out["implied_source_meta"]["effr_meeting_path"]["gap"]["usable"] is False
    assert out["implied_source_meta"]["effr_meeting_path"]["gap"]["value_bp"] is None
    assert june["vs_target_midpoint"]["status"] == "not_identified"
    assert june["vs_target_midpoint"]["difference"] is None

    # with effr_basis explicit
    md2 = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                   target={"low": 4.25, "high": 4.50,
                           "observation_date": "2026-06-11"},
                   effr_basis={"effr_minus_midpoint_bp": -8.0,
                               "observation_date": "2026-06-10",
                               "source": "fixture"})
    out2 = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                      target_low=4.25, target_high=4.50, dot_series=None,
                      zq_path_row={"m1": 4.30}, sofr_path_row=None,
                      zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                      rate_exp_proxy=None, cfg=_CFG, metadata=md2)
    june2 = out2["implied_source_meta"]["effr_meeting_path"]["months"][0]
    assert june2["status"] == "identified_conditional"
    assert _pt.approx(june2["pre_change_rate"]) == 4.295
    assert june2["pre_change_rate_source"].startswith("target_midpoint_plus_gap:explicit:")
    assert out2["implied_source_meta"]["effr_meeting_path"]["gap"]["usable"] is True


# --------------------------------------------------------------------------- #
# 5 — measured gap vs target midpoint
# --------------------------------------------------------------------------- #
def test_d1_measured_gap_comparison_subtracts_gap(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.7},
                  effr={"value": 4.33, "observation_date": "2026-06-11",
                        "source": "fred:DFF"},
                  target={"low": 4.25, "high": 4.50,
                          "observation_date": "2026-06-11"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert _pt.approx(block["gap"]["value_bp"]) == -4.5
    assert block["gap"]["source"].startswith("measured:")
    june = block["months"][0]
    assert june["vs_target_midpoint"]["status"] == "comparable_after_transformation"
    assert _pt.approx(june["vs_target_midpoint"]["difference"], abs=1e-9) == -3.0
    assert "effr_minus_midpoint_bp=-4.5" in june["vs_target_midpoint"]["assumptions"]


# --------------------------------------------------------------------------- #
# 6 — post-cutoff evidence is refused and never leaks
# --------------------------------------------------------------------------- #
def test_d1_post_cutoff_evidence_is_refused_never_leaks(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    cutoff = "2026-06-10"
    # effr obs_date == cutoff; first_public = obs_date+1 = 06-11 > cutoff -> refused
    md = _make_md("2026-06-09", {"ZQM26.CBT": 95.75},
                  effr={"value": 4.4321, "observation_date": "2026-06-10",
                        "source": "fred:DFF"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md, cutoff=cutoff)
    block = out["implied_source_meta"]["effr_meeting_path"]
    # no source starts with observed_effr:
    for m in block["months"]:
        assert not (m["pre_change_rate_source"] or "").startswith("observed_effr:")
    blob = json.dumps(block, default=str)
    assert "4.4321" not in blob

    # part B: ZQ strip dated after cutoff -> strips["zq"]["value_state"]="refused"
    md_after = _make_md("2026-06-11", {"ZQM26.CBT": 95.75})
    out2 = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                      target_low=None, target_high=None, dot_series=None,
                      zq_path_row={"m1": 4.30}, sofr_path_row=None,
                      zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                      rate_exp_proxy=None, cfg=_CFG, metadata=md_after,
                      cutoff=cutoff)
    block2 = out2["implied_source_meta"]["effr_meeting_path"]
    assert block2["status"] == "unavailable"
    assert block2["reason"] == "zq_strip_refused"
    assert block2["months"] == []
    assert block2["refused_contracts"] == []
    assert json.dumps(block2, default=str).find("4.25") == -1


# --------------------------------------------------------------------------- #
# 7 — uncovered year is meeting_calendar_unknown
# --------------------------------------------------------------------------- #
def test_d1_uncovered_year_is_meeting_calendar_unknown(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-03-18", True)])  # only 2026 dates
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75,
                                 "ZQF27.CBT": 95.0})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    months = out["implied_source_meta"]["effr_meeting_path"]["months"]
    jan = next(m for m in months if m["contract"] == "ZQF27.CBT")
    assert jan["status"] == "missing_inputs"
    assert jan["reason"] == "meeting_calendar_unknown"
    assert jan["identification"] is None
    assert jan["month_days"] == 31
    assert jan["pre_change_rate"] is None
    assert jan["pre_change_rate_source"] is None


# --------------------------------------------------------------------------- #
# 8 — chaining only from identified months (real calendar)
# --------------------------------------------------------------------------- #
def test_d1_chaining_only_from_identified_months():
    md = _fixture8_md()
    out = fp.compute(asof=pd.Timestamp("2026-10-14"), policy_rate=4.20,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.20}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    months = out["implied_source_meta"]["effr_meeting_path"]["months"]
    by = {m["contract"]: m for m in months}
    oct26 = by["ZQV26.CBT"]
    assert oct26["status"] == "identified_conditional"
    assert oct26["pre_change_rate"] == 4.10
    assert oct26["pre_change_rate_source"] == "observed_effr:fred:DFF@2026-10-13"
    assert oct26["reason"] == "pre_change_rate:observed_effr:fred:DFF@2026-10-13"
    nov = by["ZQX26.CBT"]
    assert nov["status"] == "identified_conditional"
    assert nov["reason"] == "no_intra_month_change"
    dec = by["ZQZ26.CBT"]
    assert dec["status"] == "identified_conditional"
    assert dec["pre_change_rate_source"].startswith("chained:2026-11")
    assert "chained_identification" in dec["limitations"]

    # variant without ZQX26 -> Dec has no preceding identified month
    md_no_nov = _make_md("2026-10-13", {"ZQV26.CBT": 95.8,
                                        "ZQZ26.CBT": 95.0},
                         effr={"value": 4.10, "observation_date": "2026-10-13",
                               "source": "fred:DFF"})
    out_no_nov = fp.compute(asof=pd.Timestamp("2026-10-14"), policy_rate=4.20,
                            target_low=None, target_high=None, dot_series=None,
                            zq_path_row={"m1": 4.20}, sofr_path_row=None,
                            zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                            rate_exp_proxy=None, cfg=_CFG, metadata=md_no_nov)
    months2 = out_no_nov["implied_source_meta"]["effr_meeting_path"]["months"]
    dec2 = next(m for m in months2 if m["contract"] == "ZQZ26.CBT")
    assert dec2["status"] == "missing_inputs"
    assert dec2["reason"] == "pre_change_rate_unavailable"


# --------------------------------------------------------------------------- #
# 9 — stale ZQ strip makes block unavailable
# --------------------------------------------------------------------------- #
def test_d1_stale_zq_strip_makes_block_unavailable(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-09-16", True)])
    asof = pd.Timestamp("2026-10-14")
    zq_obs = (asof - _dt.timedelta(days=10)).date().isoformat()  # 2026-10-04
    md = _make_md(zq_obs, {"ZQV26.CBT": 95.8})
    out = fp.compute(asof=asof, policy_rate=4.20,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert block["status"] == "unavailable"
    assert block["reason"] == "zq_strip_stale"
    assert block["months"] == []


# --------------------------------------------------------------------------- #
# 10 — weights + post_rate_sensitivity (fixture 8's Oct)
# --------------------------------------------------------------------------- #
def test_d1_weights_and_post_rate_sensitivity():
    md = _fixture8_md()
    out = fp.compute(asof=pd.Timestamp("2026-10-14"), policy_rate=4.20,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.20}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    oct26 = next(m for m in out["implied_source_meta"]
                 ["effr_meeting_path"]["months"] if m["contract"] == "ZQV26.CBT")
    assert oct26["month_days"] == 31
    assert oct26["weights"]["days_pre"] == 28
    assert oct26["weights"]["days_post"] == 3
    assert _pt.approx(oct26["post_rate_sensitivity"], abs=1e-4) == 10.3333
    assert oct26["weights"]["realised_days"] == 13
    assert oct26["weights"]["remaining_days"] == 18


# --------------------------------------------------------------------------- #
# 11 — effective date is decision + 1 day
# --------------------------------------------------------------------------- #
def test_d1_effective_date_is_decision_plus_one_day():
    md = _fixture8_md()
    out = fp.compute(asof=pd.Timestamp("2026-10-14"), policy_rate=4.20,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.20}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    months = out["implied_source_meta"]["effr_meeting_path"]["months"]
    effs = {m["contract"]: m["effective_dates_inside"] for m in months}
    assert effs["ZQV26.CBT"] == ["2026-10-29"]   # decision 2026-10-28
    assert effs["ZQZ26.CBT"] == ["2026-12-10"]   # decision 2026-12-09


# --------------------------------------------------------------------------- #
# 12 — token law: no forecast vocabulary anywhere in the block
# --------------------------------------------------------------------------- #
def test_d1_block_names_carry_no_forecast_vocabulary(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC",
                        [("2026-06-15", False), ("2026-07-29", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75,
                                 "ZQN26.CBT": 95.50,
                                 "ZQQ26.CBT": 95.25},
                  effr={"value": 4.50, "observation_date": "2026-06-11",
                        "source": "fred:DFF"},
                  target={"low": 4.25, "high": 4.50,
                          "observation_date": "2026-06-11"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    BANNED = {"prob", "probability", "probabilities", "cut", "cuts",
              "hike", "hikes", "dot", "dots", "sep", "terminal",
              "odds", "count", "moves", "priced"}

    def walk_keys(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                for w in str(k).split("_"):
                    assert w not in BANNED, f"banned token in key: {k} ({w}) at {path}"
                walk_keys(v, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                walk_keys(v, f"{path}[{i}]")

    def walk_values(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk_values(v, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                walk_values(v, f"{path}[{i}]")
        elif obj is not None:
            for w in str(obj).split("_"):
                assert w not in BANNED, f"banned token in value: {obj!r} ({w}) at {path}"

    walk_keys(block)
    walk_values(block)


# --------------------------------------------------------------------------- #
# 13 — D0 meta byte-identical minus the new key, legacy outputs unchanged
# --------------------------------------------------------------------------- #
def test_d1_d0_meta_and_legacy_outputs_unchanged():
    # mode-1 outputs are byte-identical to base (D1 only adds the new key).
    assert _line(_f1()) == _GOLDEN_F1
    assert _line(_f1(zq_path_row=None, sofr_path_row=dict(_F2_SOFR))) == _GOLDEN_F2
    assert _line(_f1(zq_path_row=None, sofr_path_row=None, dot_series=None)) == _GOLDEN_F3
    # the D0 meta minus the new key equals the captured base meta.
    out = _d0_meta_call()
    meta = out["implied_source_meta"]
    sans_new = {k: v for k, v in meta.items() if k != "effr_meeting_path"}
    blob = json.dumps(sans_new, sort_keys=True, ensure_ascii=False, default=str)
    assert blob == _GOLDEN_D0_META


# --------------------------------------------------------------------------- #
# 14 — compute source pin unchanged
# --------------------------------------------------------------------------- #
def test_d1_compute_rule_pin_unchanged():
    import ast as _ast
    import hashlib as _hl
    _src = open("engine/fed_path.py").read()
    _defs = [x for x in _ast.parse(_src).body
             if getattr(x, "name", None) == "compute"]
    assert len(_defs) == 1
    _n = _defs[0]
    _body = "\n".join(_src.splitlines()[_n.lineno-1:_n.end_lineno])
    _h = _hl.sha256(_body.encode()).hexdigest()
    assert _h == "da05ae6617a54c0eb166e9e340cb74034d78c37c61a313d46ebe402239f39a35"


# --------------------------------------------------------------------------- #
# 15 — snapshot wires closes + effr + target
# --------------------------------------------------------------------------- #
def test_d1_snapshot_wires_closes_effr_and_target(monkeypatch):
    idx = pd.DatetimeIndex(["2026-10-13"])
    zq_path = pd.DataFrame({"m1": [4.30], "m3": [4.30], "m6": [4.30], "m12": [4.30]},
                            index=idx)
    zq_cf = pd.DataFrame({"ZQV26.CBT": [95.80], "ZQX26.CBT": [95.40],
                          "ZQZ26.CBT": [95.00]}, index=idx)
    dff_df = pd.DataFrame({"DFF": [4.10]}, index=idx)
    tl_df = pd.DataFrame({"DFEDTARL": [4.25]}, index=idx)
    tu_df = pd.DataFrame({"DFEDTARU": [4.50]}, index=idx)
    frames = {
        ("rate_futures", "zq_path"): zq_path,
        ("rate_futures", "zq_contracts"): zq_cf,
        ("fred", "DFF"): dff_df,
        ("fred", "DFEDTARL"): tl_df,
        ("fred", "DFEDTARU"): tu_df,
    }
    monkeypatch.setattr(fp.store, "read", lambda ns, key: frames.get((ns, key)))
    import engine.bonds as _eb
    monkeypatch.setattr(_eb, "near_term_forward_spread",
                        lambda f: pd.Series([0.0] * len(f), index=f.index))
    f = pd.DataFrame({"fed_funds": [4.10], "fed_target_lower": [4.25],
                      "fed_target_upper": [4.50], "zq_implied_rate": [4.10]},
                     index=idx)
    out = fp.snapshot(f, cfg=_CFG)
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert block["status"] == "computed"
    months = block["months"]
    assert any((m["pre_change_rate_source"] or "").startswith("observed_effr:fred:DFF@")
               for m in months)


# --------------------------------------------------------------------------- #
# 16 — multiple inside dates stay missing_inputs
# --------------------------------------------------------------------------- #
def test_d1_multiple_inside_dates_stay_missing_inputs(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False),
                                        ("2026-06-29", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                  effr={"value": 4.50, "observation_date": "2026-06-11",
                        "source": "fred:DFF"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=None, target_high=None, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    june = out["implied_source_meta"]["effr_meeting_path"]["months"][0]
    assert june["status"] == "missing_inputs"
    assert "rate_step_bp" in june["identification"]["missing"]
    assert june["reason"] == "multiple_effective_dates"
    assert june["effective_dates_inside"] == ["2026-06-16", "2026-06-30"]


# --------------------------------------------------------------------------- #
# 17 — internal error in solver degrades, never raises
# --------------------------------------------------------------------------- #
def test_d1_internal_error_degrades_never_raises(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                  effr={"value": 4.50, "observation_date": "2026-06-11",
                        "source": "fred:DFF"})
    out_base = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                          target_low=4.25, target_high=4.50, dot_series=None,
                          zq_path_row={"m1": 4.30}, sofr_path_row=None,
                          zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                          rate_exp_proxy=None, cfg=_CFG, metadata=md)

    def boom(*a, **kw):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(_rcb, "solve_reference_average", boom)
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    assert out is not None  # compute returns normally
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert block["status"] == "unavailable"
    assert block["reason"] == "internal_error:RuntimeError"
    assert block["months"] == []
    base_no_new = {k: v for k, v in out_base["implied_source_meta"].items()
                   if k != "effr_meeting_path"}
    new_no_new = {k: v for k, v in out["implied_source_meta"].items()
                  if k != "effr_meeting_path"}
    assert new_no_new == base_no_new


# --------------------------------------------------------------------------- #
# A16 — unidentified predecessor is never chained (route 2 / route 3 rule)
# --------------------------------------------------------------------------- #
def test_d1_unidentified_predecessor_is_never_chained(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC",
                        [("2026-05-19", False), ("2026-06-15", False)])
    md = _make_md("2026-05-11",
                  {"ZQK26.CBT": 95.80, "ZQM26.CBT": 95.70},
                  target={"low": 4.25, "high": 4.50,
                          "observation_date": "2026-05-11"})
    out = fp.compute(asof=pd.Timestamp("2026-05-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert block["status"] == "computed"
    assert block["gap"]["usable"] is False
    assert block["gap"]["value_bp"] is None

    m = {r["reference_start"]: r for r in block["months"]}
    may = m["2026-05-01"]
    assert may["status"] == "not_identified"
    assert may["reason"] == "underidentified:effr_target_basis"
    assert may["pre_change_rate"] is None
    assert _pt.approx(may["monthly_average"]["value"]) == 4.20

    june = m["2026-06-01"]
    assert june["status"] == "missing_inputs"
    assert june["reason"] == "pre_change_rate_unavailable"
    assert june["pre_change_rate"] is None
    assert june["pre_change_rate_source"] is None
    assert "chained_identification" not in june["limitations"]


# --------------------------------------------------------------------------- #
# A17 — DFF route refuses an intervening effective date (route 1 rule)
# --------------------------------------------------------------------------- #
def test_d1_dff_route_refuses_an_intervening_effective_date(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC",
                        [("2026-05-19", False), ("2026-06-15", False)])

    md_neg = _make_md("2026-05-08", {"ZQM26.CBT": 95.75},
                     effr={"value": 4.50,
                           "observation_date": "2026-05-08",
                           "source": "fred:DFF"})
    out_neg = fp.compute(asof=pd.Timestamp("2026-05-09"), policy_rate=4.33,
                         target_low=4.25, target_high=4.50, dot_series=None,
                         zq_path_row={"m1": 4.30}, sofr_path_row=None,
                         zq_front_implied=None, ntfs=None,
                         curve_tp_adj=None, rate_exp_proxy=None,
                         cfg=_CFG, metadata=md_neg)
    block_neg = out_neg["implied_source_meta"]["effr_meeting_path"]
    m_neg = {r["reference_start"]: r for r in block_neg["months"]}
    june_neg = m_neg["2026-06-01"]
    assert june_neg["status"] == "missing_inputs"
    assert june_neg["reason"] == "pre_change_rate_unavailable"
    assert june_neg["pre_change_rate"] is None
    assert june_neg["pre_change_rate_source"] is None

    md_pos = _make_md("2026-05-21", {"ZQM26.CBT": 95.75},
                     effr={"value": 4.50,
                           "observation_date": "2026-05-21",
                           "source": "fred:DFF"})
    out_pos = fp.compute(asof=pd.Timestamp("2026-05-22"), policy_rate=4.33,
                         target_low=4.25, target_high=4.50, dot_series=None,
                         zq_path_row={"m1": 4.30}, sofr_path_row=None,
                         zq_front_implied=None, ntfs=None,
                         curve_tp_adj=None, rate_exp_proxy=None,
                         cfg=_CFG, metadata=md_pos)
    block_pos = out_pos["implied_source_meta"]["effr_meeting_path"]
    m_pos = {r["reference_start"]: r for r in block_pos["months"]}
    june_pos = m_pos["2026-06-01"]
    assert june_pos["status"] == "identified_conditional"
    assert june_pos["pre_change_rate"] == _pt.approx(4.50)
    assert june_pos["pre_change_rate_source"] == (
        "observed_effr:fred:DFF@2026-05-21"
    )
    assert june_pos["reason"] == (
        "pre_change_rate:observed_effr:fred:DFF@2026-05-21"
    )


# --------------------------------------------------------------------------- #
# A19 — effr_basis dated after the cutoff is refused (gap unused)
# --------------------------------------------------------------------------- #
def test_d1_effr_basis_after_cutoff_is_refused_never_used(monkeypatch):
    monkeypatch.setattr(_ec, "_FOMC", [("2026-06-15", False)])
    md = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                  target={"low": 4.25, "high": 4.50,
                          "observation_date": "2026-06-11"},
                  effr_basis={"effr_minus_midpoint_bp": -8.0,
                              "observation_date": "2026-06-14",
                              "source": "fixture"})
    out = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                     target_low=4.25, target_high=4.50, dot_series=None,
                     zq_path_row={"m1": 4.30}, sofr_path_row=None,
                     zq_front_implied=None, ntfs=None, curve_tp_adj=None,
                     rate_exp_proxy=None, cfg=_CFG, metadata=md)
    block = out["implied_source_meta"]["effr_meeting_path"]
    assert block["gap"]["usable"] is False
    assert block["gap"]["value_bp"] is None
    assert block["gap"]["reason"] == "effr_basis_after_cutoff"

    m = {r["reference_start"]: r for r in block["months"]}
    june = m["2026-06-01"]
    assert june["status"] == "not_identified"
    assert june["reason"] == "underidentified:effr_target_basis"
    assert june["pre_change_rate"] is None
    assert june["vs_target_midpoint"]["difference"] is None

    md_ctrl = _make_md("2026-06-11", {"ZQM26.CBT": 95.75},
                       target={"low": 4.25, "high": 4.50,
                               "observation_date": "2026-06-11"},
                       effr_basis={"effr_minus_midpoint_bp": -8.0,
                                   "observation_date": "2026-06-10",
                                   "source": "fixture"})
    out_ctrl = fp.compute(asof=pd.Timestamp("2026-06-12"), policy_rate=4.33,
                          target_low=4.25, target_high=4.50, dot_series=None,
                          zq_path_row={"m1": 4.30}, sofr_path_row=None,
                          zq_front_implied=None, ntfs=None,
                          curve_tp_adj=None, rate_exp_proxy=None,
                          cfg=_CFG, metadata=md_ctrl)
    june_ctrl = out_ctrl["implied_source_meta"]["effr_meeting_path"]["months"][0]
    assert june_ctrl["status"] == "identified_conditional"
    assert june_ctrl["pre_change_rate"] == _pt.approx(4.295)
