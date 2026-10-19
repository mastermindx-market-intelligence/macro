"""Advanced theme textures (engine.basket_score) — display-only, honest.

Verify bull-market age, overbought, clean-entry and roll-over read the level/texture inputs
correctly, every texture carries directional:False, and market_concentration degrades to {}
without the breadth file. Pure functions on synthetic series; no network.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import basket_score as bs


def _ramp(n=300, slope=0.0015, start=1.0):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(start * np.cumprod(1 + np.full(n, slope)), index=idx)


def test_bull_age_uptrend_vs_downtrend():
    up = bs.bull_age(_ramp(slope=0.002))
    assert up["in_bull"] is True and up["days"] > 0
    assert up["stage"] in ("young", "building", "mature", "aging")
    assert up["directional"] is False
    dn = bs.bull_age(_ramp(slope=-0.002))
    assert dn["in_bull"] is False and dn["stage"] == "downtrend"


def test_bull_age_needs_history():
    assert bs.bull_age(_ramp(n=40)) is None


def test_overbought_band_scales_with_rsi_and_rs():
    hot = bs.overbought(_ramp(slope=0.004), 0.95, None)
    cool = bs.overbought(_ramp(slope=0.0001), 0.4, None)
    assert hot["value"] >= cool["value"]
    assert hot["band"] in ("overbought", "extreme", "elevated")
    assert hot["directional"] is False


def test_clean_entry_flag_requires_not_extended():
    lvl = _ramp(slope=0.0015)
    # accelerating, not extended, RSI room, broad → flag on
    on = bs.clean_entry(lvl, {"accel_z": 0.8, "rs_pctile": 0.5}, {"pct50": 0.6}, 55)
    assert on["flag"] is True and on["quality"] >= 0.6
    # same but extended (rs_pctile high) → flag off
    off = bs.clean_entry(lvl, {"accel_z": 0.8, "rs_pctile": 0.95}, {"pct50": 0.6}, 55)
    assert off["flag"] is False
    assert on["directional"] is False


def test_clean_entry_vetoed_on_breaking_backdrop():
    # REGRESSION (cn_banks etc.): accel + not-extended + RSI room alone must NOT advertise a
    # "clean entry" when the tape is BREAKING — collapsed breadth, net new lows, or hard decel.
    lvl = _ramp(slope=0.0015)
    fp = {"accel_z": 0.8, "rs_pctile": 0.3}        # accelerating + not extended
    # collapsed breadth (pct50 < 0.4) → no clean entry
    assert bs.clean_entry(lvl, fp, {"pct50": 0.0, "nh": 0, "nl": 7}, 55)["flag"] is False
    # net new lows → no clean entry even with ok pct50
    assert bs.clean_entry(lvl, fp, {"pct50": 0.55, "nh": 0, "nl": 3}, 55)["flag"] is False
    # hard down-acceleration → no clean entry
    assert bs.clean_entry(lvl, {"accel_z": -0.8, "rs_pctile": 0.3},
                          {"pct50": 0.6, "nh": 2, "nl": 0}, 55)["flag"] is False
    # healthy, broad, turning up → still a clean entry (cn_brokers-style early entry)
    assert bs.clean_entry(lvl, fp, {"pct50": 0.6, "nh": 3, "nl": 0}, 55)["flag"] is True


def test_rollover_risk_rises_with_extension_and_decel():
    lvl = _ramp(slope=0.0015)
    hi = bs.rollover_risk(lvl, {"rs_pctile": 0.92, "accel_z": -0.6},
                          {"accel_z": 0.4}, {"pct50": 0.4, "nh": 0, "nl": 5},
                          {"5d": {"rel": -0.03}})
    lo = bs.rollover_risk(lvl, {"rs_pctile": 0.5, "accel_z": 0.5},
                          {"accel_z": 0.3}, {"pct50": 0.7, "nh": 4, "nl": 0},
                          {"5d": {"rel": 0.02}})
    assert hi["risk"] > lo["risk"]
    assert hi["band"] in ("elevated", "high")
    assert lo["band"] == "low"
    assert hi["directional"] is False


def test_theme_textures_bundles_all_four():
    tx = bs.theme_textures(_ramp(), {"rs_pctile": 0.6, "accel_z": 0.4},
                           {"accel_z": 0.3}, None, {"pct50": 0.55, "nh": 2, "nl": 1},
                           {"5d": {"rel": 0.01}})
    assert set(tx) == {"bull_age", "overbought", "clean_entry", "rollover_risk"}


def test_act_now_stocks_gated_by_theme_health():
    members = [
        {"symbol": "AAA", "conviction": {"score": 72, "verdict": "Buy — pullback", "cycle_blocked": False, "entry_pct": 0.7}},
        {"symbol": "BBB", "conviction": {"score": 80, "verdict": "Add — strong", "cycle_blocked": False, "entry_pct": 0.6}},
        {"symbol": "CCC", "conviction": {"score": 30, "verdict": "Avoid — downtrend", "cycle_blocked": True, "entry_pct": 0.2}},
        {"symbol": "DDD", "conviction": {"score": 90, "verdict": "Strong name, wrong tape", "cycle_blocked": True, "entry_pct": 0.1}},
    ]
    # healthy theme → returns the buys (AAA/BBB), excludes avoid + cycle-blocked
    good = bs.act_now_stocks(members, {"label": "emerging", "reco": "enter",
                                       "textures": {"bull_age": {"in_bull": True}}})
    assert good["status"] == "ok"
    syms = [x["symbol"] for x in good["buys"]]
    assert "AAA" in syms and "BBB" in syms and "CCC" not in syms and "DDD" not in syms
    # out-of-favour theme → NOTHING recommended, with a reason
    for bad in ({"label": "deteriorating", "reco": "avoid", "textures": {"bull_age": {"in_bull": True}}},
                {"label": "fading", "reco": "trim", "textures": {"bull_age": {"in_bull": True}}},
                {"label": "neutral", "reco": "hold", "textures": {"bull_age": {"in_bull": False}}}):
        r = bs.act_now_stocks(members, bad)
        assert r["status"] == "theme_out_of_favour" and r["buys"] == [] and r["note_en"]


def test_act_now_constructive_label_below_200d_not_vetoed():
    # REGRESSION (cn_brokers): an EMERGING / DOMINANT theme freshly turning up off a base is
    # still below its slow 200d SMA (in_bull False). The engine's own constructive label must
    # NOT be overridden into a self-contradicting "out of favour (emerging)" — it proceeds to
    # per-member gating and surfaces members with an open entry.
    members = [
        {"symbol": "AAA", "conviction": {"score": 83, "verdict": "Neutral", "cycle_blocked": False,
                                         "entry_pct": 0.5, "entry": {"status": "buy_now", "act_level": 3}}},
    ]
    for lbl in ("emerging", "dominant"):
        r = bs.act_now_stocks(members, {"label": lbl, "reco": "hold",
                                        "textures": {"bull_age": {"in_bull": False}}})
        assert r["status"] == "ok", lbl
        assert [x["symbol"] for x in r["buys"]] == ["AAA"], lbl
    # a NEUTRAL theme below its 200d still reads as a downtrend, and the reason never echoes a
    # constructive lifecycle label (no more "out of favour (emerging)").
    nr = bs.act_now_stocks(members, {"label": "neutral", "reco": "hold",
                                     "textures": {"bull_age": {"in_bull": False}}})
    assert nr["status"] == "theme_out_of_favour"
    assert "downtrend" in nr["note_en"] and "emerging" not in nr["note_en"]


def test_act_now_no_clean_entries():
    # healthy theme but no member is a buy → honest 'no clean entry', not a forced pick
    members = [{"symbol": "X", "conviction": {"score": 40, "verdict": "Neutral — no edge", "cycle_blocked": False, "entry_pct": 0.5}}]
    r = bs.act_now_stocks(members, {"label": "dominant", "reco": "hold", "textures": {"bull_age": {"in_bull": True}}})
    assert r["status"] == "no_clean_entries" and r["buys"] == []
    assert r["uncovered"] == []


def test_act_now_surfaces_blocked_t1_t2_as_fast_turn_watch():
    members = [
        {"symbol": "FAST", "name": "Fast Miner", "ret_5d": 0.03, "ret_20d": -0.08,
         "conviction": {"score": 12, "cycle_blocked": False,
                        "signal": {"tier": "T2", "provisional": False},
                        "entry": {"status": "bounce_wait", "headline": "turn not confirmed"}}},
        {"symbol": "BLOCK", "name": "Blocked Miner", "ret_5d": 0.01, "ret_20d": -0.05,
         "conviction": {"score": 0, "cycle_blocked": True,
                        "signal": {"tier": "T1", "provisional": False},
                        "entry": {"status": "blocked", "headline": "failed cycle"}}},
    ]
    r = bs.act_now_stocks(
        members,
        {"label": "deteriorating", "reco": "avoid",
         "textures": {"bull_age": {"in_bull": False}}},
    )
    assert r["status"] == "theme_out_of_favour"
    assert [x["symbol"] for x in r["early_turn_watch"]] == ["FAST", "BLOCK"]
    assert all(x["blocker_en"].startswith("theme gate:") for x in r["early_turn_watch"])


def test_act_now_uncovered_disclosed_on_every_path():
    # REGRESSION (hk_banks audit 2026-07-16): members without a conviction read (no stockdata
    # record, or a thin record without a score) were silently dropped from the ranking. Every
    # payload now carries the `uncovered` list so the page prints the gap explicitly.
    members = [
        {"symbol": "AAA", "conviction": {"score": 83, "verdict": "Buy", "cycle_blocked": False,
                                         "entry_pct": 0.7, "entry": {"status": "buy_now", "act_level": 3}}},
        {"symbol": "BBB", "conviction": None},                                    # no record at all
        {"symbol": "CCC", "conviction": {"score": None, "signal": {"tier": "T2"}}},  # thin: no score
    ]
    ok = bs.act_now_stocks(members, {"label": "dominant", "reco": "hold",
                                     "textures": {"bull_age": {"in_bull": True}}})
    assert ok["status"] == "ok" and ok["uncovered"] == ["BBB", "CCC"]
    out = bs.act_now_stocks(members, {"label": "fading", "reco": "avoid",
                                      "textures": {"bull_age": {"in_bull": True}}})
    assert out["status"] == "theme_out_of_favour" and out["uncovered"] == ["BBB", "CCC"]
    # an ALL-uncovered basket (hk_industrials was 9/9) reads as a coverage gap, not a verdict
    bare = bs.act_now_stocks([{"symbol": "ZZZ", "conviction": None}],
                             {"label": "dominant", "reco": "hold",
                              "textures": {"bull_age": {"in_bull": True}}})
    assert bare["status"] == "no_clean_entries" and bare["uncovered"] == ["ZZZ"]


def test_market_concentration_graceful(monkeypatch, tmp_path):
    # point data_dir at an empty tmp → no breadth file → {} (never raises)
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    assert bs.market_concentration() == {}



def test_market_concentration_exposes_source_session_and_honest_universe(monkeypatch, tmp_path):
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    observed = pd.DataFrame(
        {
            "n_members": [490, 501],
            "adv": [250, 270],
            "dec": [240, 230],
            "pct_above_50": [50.0, 54.0],
            "pct_above_200": [61.0, 62.0],
            "nh": [10, 12],
            "nl": [9, 7],
        },
        index=pd.DatetimeIndex(["2026-10-14", "2026-10-15"]),
    )
    monkeypatch.setattr(bs.pd, "read_parquet", lambda _path: observed)
    value = bs.market_concentration("us")
    assert value["source_as_of"] == "2026-10-15"
    assert value["source_universe"] == "sp500_current_constituents"
    assert value["adv"] == 270
    assert value["directional"] is False


def test_market_concentration_absent_or_invalid_source_session_is_unmeasured(monkeypatch, tmp_path):
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    bad = pd.DataFrame(
        {"adv": [9], "dec": [2], "pct_above_50": [70]},
        index=["not-an-observation-date"],
    )
    monkeypatch.setattr(bs.pd, "read_parquet", lambda _path: bad)
    assert bs.market_concentration("us") == {}



def test_unmeasured_breadth_never_becomes_a_mixed_verdict(monkeypatch, tmp_path):
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    incomplete = pd.DataFrame(
        {
            "adv": [90.0],
            "dec": [100.0],
            "pct_above_50": [np.nan],
            "pct_above_200": [float("inf")],
            "nh": [np.nan],
            "nl": [7],
        },
        index=pd.DatetimeIndex(["2026-10-15"]),
    )
    monkeypatch.setattr(bs.pd, "read_parquet", lambda _path: incomplete)
    actual = bs.market_concentration("us")
    assert actual["source_as_of"] == "2026-10-15"
    assert actual["pct_above_50"] is None
    assert actual["pct_above_200"] is None
    assert actual["nh"] is None
    assert actual["nl"] == 7
    assert actual.get("verdict") is None
    assert actual["directional"] is False


def test_market_concentration_ad_horizons_require_full_nyse_sessions(monkeypatch, tmp_path):
    from datetime import date
    from lib import config, nyse_calendar

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

    def frame(days):
        n = len(days)
        return pd.DataFrame(
            {"n_members": [500] * n, "adv": [20] * n, "dec": [10] * n,
             "pct_above_50": [60.0] * n, "pct_above_200": [55.0] * n,
             "nh": [8] * n, "nl": [3] * n},
            index=pd.DatetimeIndex(days),
        )

    # A Thursday/Friday/Tuesday trio spans Labor Day but is three
    # consecutive NYSE sessions, not four calendar days of missing data.
    holiday_span = nyse_calendar.sessions_between(date(2026, 9, 3), date(2026, 9, 8))
    assert len(holiday_span) == 3
    state = {"frame": frame(holiday_span)}
    monkeypatch.setattr(bs.pd, "read_parquet", lambda _path: state["frame"])
    sample = bs.market_concentration("us")
    assert sample["ad_3d"] == 2.0
    assert sample["ad_w"] is None
    assert sample["ad_m"] is None

    # Real 21-session population qualifies all three horizons.
    days = nyse_calendar.sessions_between(date(2026, 9, 1), date(2026, 10, 16))[-21:]
    assert len(days) == 21
    state["frame"] = frame(days)
    observed = bs.market_concentration("us")
    assert observed["ad_3d"] == 2.0
    assert observed["ad_w"] == 2.0
    assert observed["ad_m"] == 2.0

    # An unavailable penultimate NYSE session invalidates every named
    # trailing horizon despite an unchanged latest source-as-of date.
    state["frame"] = frame(days[:-2] + days[-1:])
    sparse = bs.market_concentration("us")
    assert sparse["source_as_of"] == observed["source_as_of"]
    assert sparse["ad_3d"] is None
    assert sparse["ad_w"] is None
    assert sparse["ad_m"] is None

    # A one-row tape cannot be reinterpreted as a weekly/monthly ratio.
    state["frame"] = frame(days[-1:])
    single = bs.market_concentration("us")
    assert all(single[k] is None for k in ("ad_3d", "ad_w", "ad_m"))


def test_market_concentration_ad_lookbacks_never_zero_fill_nan_or_duplicate_rows(
    monkeypatch, tmp_path,
):
    from datetime import date
    from lib import config, nyse_calendar

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    days = nyse_calendar.sessions_between(date(2026, 10, 1), date(2026, 10, 16))
    assert len(days) >= 5
    frame = pd.DataFrame(
        {"adv": [80.0] * len(days), "dec": [40.0] * len(days),
         "pct_above_50": [62.0] * len(days), "pct_above_200": [53.0] * len(days),
         "nh": [12.0] * len(days), "nl": [4.0] * len(days)},
        index=pd.DatetimeIndex(days),
    )
    state = {"frame": frame}
    monkeypatch.setattr(bs.pd, "read_parquet", lambda _path: state["frame"])
    assert bs.market_concentration("us")["ad_w"] == 2.0

    missing = frame.copy()
    missing.loc[days[-4], "adv"] = np.nan
    state["frame"] = missing
    outcome = bs.market_concentration("us")
    assert outcome["ad_3d"] == 2.0
    assert outcome["ad_w"] is None

    nonfinite = frame.copy()
    nonfinite.loc[days[-1], "dec"] = float("inf")
    state["frame"] = nonfinite
    assert bs.market_concentration("us")["ad_3d"] is None

    negative = frame.copy()
    negative.loc[days[-1], "adv"] = -1
    state["frame"] = negative
    assert bs.market_concentration("us")["ad_3d"] is None

    duplicate = pd.concat([frame.iloc[:-1], frame.iloc[-2:-1]])
    state["frame"] = duplicate
    assert bs.market_concentration("us")["ad_3d"] is None



def test_theme_desk_breadth_refuses_missing_vintage_and_false_sp1500():
    """Run the actual Theme Rotation renderer, not only its source strings."""
    from pathlib import Path
    import shutil
    import subprocess
    import pytest

    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "baskets_desk.js").read_bytes()
    served = (root / "site" / "baskets_desk.js").read_bytes()
    assert template == served

    text = template.decode("utf-8")
    assert text.count("function renderConcentration(){") == 1
    fragment = (
        "function renderConcentration(){"
        + text.split("function renderConcentration(){", 1)[1]
        .split("\nfunction _bbase(){", 1)[0]
    )
    assert "Object.prototype.hasOwnProperty.call(vmap,mc.verdict)" in fragment
    assert "vmap[mc.verdict]||vmap.mixed" not in fragment

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable; byte-parity and source guards checked")

    prelude = """
let THEME, html='', zh=false;
const window={BASKET_BASE:'basket/'};
const document={getElementById:(id)=>id==='concentration'
  ?{set innerHTML(s){html=s;}}
  :id==='concentration-section'?{style:{}}:null};
const L=(en,cn)=>zh?cn:en;
const esc=(s)=>String(s);
const heatDot=()=>'<span></span>';
"""
    cases = """
function render(mc, asOf='2026-10-16', language=false){
  zh=language;html='';
  THEME={as_of:asOf,bench_label:'S&P 1500',bench_label_zh:'标普1500',
    market_concentration:mc, themes:[],breadth_leaders:[],breadth_laggards:[],
    entries:[],rollover:[]};
  renderConcentration();
  return html;
}
const d='2026-10-16';
const valid={source_as_of:d,source_universe:'sp500_current_constituents',
  verdict:'broad',ad_ratio:1.6,ad_3d:1.5,ad_w:1.4,ad_m:null,
  pct_above_50:65,pct_above_200:61,nh:12,nl:3};
const unknown=render({});
const stale=render({...valid,source_as_of:'2026-10-14'});
const forged=render({...valid,source_universe:'sp1500'});
for(const x of [unknown,stale,forged]){
  if(!x.includes('not measured')||!x.includes('Source session or coverage unverified')||
     x.includes('1.60')||x.includes('65%')||x.includes('>null<')){
    throw Error('unsupported breadth became a measurement: '+x.slice(0,1000));
  }
}
const current=render(valid);
if(!current.includes('S&P 500 sampled breadth')||!current.includes('broad')||
   !current.includes('1.60')||!current.includes('1.50')||
   !current.includes('61%')||!current.includes('>—<')){
  throw Error('valid S&P500 source not displayed correctly: '+current.slice(0,1400));
}
const limited=render({...valid,verdict:null});
if(!limited.includes('not measured')||!limited.includes('1.60')){
  throw Error('separate measured A/D lost when verdict absent: '+limited.slice(0,1000));
}
const chinese=render({},d,true);
if(!chinese.includes('未测')||!chinese.includes('数据来源交易日或覆盖范围未核验')){
  throw Error('unmeasured Chinese state not visible');
}
"""
    done = subprocess.run(
        [node, "-e", prelude + fragment + cases],
        capture_output=True, text=True, timeout=15,
    )
    assert done.returncode == 0, done.stderr
