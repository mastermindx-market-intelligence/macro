"""start.html Tier-1 plain-language pins (H1).

Producer-level string composition for the signed-in hub: the what-changed
receipt, Other Features chips, China/HK stock-card labels, the IPO lock-up
line, and the hero live-clock skeleton. Full-page render is skipped in a
sparse tree (no data/ / site/).
"""
from __future__ import annotations

import inspect
import json

import pandas as pd
import pytest

from scripts import build_vector as bv


# ---------------------------------------------------------------------------
# P1 — Regime radar EN receipt (home_alert_feed ≠ alert_triage._macro_raw)
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_hub_sibling_feeds(monkeypatch):
    import engine.btc_alerts as ba
    import engine.commodity_alerts as ca
    monkeypatch.setattr(ba, "load_events", lambda: [])
    monkeypatch.setattr(ca, "load_events", lambda: [])


def test_hub_feed_plainifies_transition_receipt(monkeypatch, isolated_hub_sibling_feeds):
    """home_alert_feed must emit alert_view's rewrite, not the parquet enum string.

    Different emit path from engine.alert_triage._macro_raw (alerts.html). Both
    call alert_view; only this feed was still copying r['message'] onto detail.
    """
    poisoned = pd.DataFrame([
        {"date": "2026-08-04", "rule": "transition_state_change", "severity": "act",
         "message": "Transition state NEW_REGIME -> TRANSITIONING (4 flags active)",
         "message_zh": "转换状态 新周期 -> 转换中（4 个预警激活）"},
    ])
    monkeypatch.setattr(bv.pd, "read_parquet", lambda *a, **k: poisoned)

    feed = [i for i in bv.home_alert_feed() if i["source"] == "macro"]
    assert len(feed) == 1
    row = feed[0]
    assert row["detail"] == (
        "The regime's footing went from a new regime to shifting "
        "(4 warning flags active)"
    )
    assert "NEW_REGIME" not in row["detail"]
    assert "TRANSITIONING" not in row["detail"]
    assert "STABLE" not in row["detail"]
    assert "WEAKENING" not in row["detail"]
    assert row["detail_zh"] == "周期状态由「新周期」转为「转换中」（4 个预警激活）"
    assert " -> " not in row["detail_zh"]
    assert "->" not in row["detail_zh"]
    assert "NEW_REGIME" not in row["detail_zh"]
    assert "TRANSITIONING" not in row["detail_zh"]


def test_hub_feed_transition_singular_flag(monkeypatch, isolated_hub_sibling_feeds):
    poisoned = pd.DataFrame([
        {"date": "2026-08-04", "rule": "transition_state_change", "severity": "act",
         "message": "Transition state WEAKENING -> STABLE (1 flags active)",
         "message_zh": ""},
    ])
    monkeypatch.setattr(bv.pd, "read_parquet", lambda *a, **k: poisoned)
    row = [i for i in bv.home_alert_feed() if i["source"] == "macro"][0]
    assert "1 warning flag active" in row["detail"]
    assert "WEAKENING" not in row["detail"]
    assert "STABLE" not in row["detail"]
    assert "走弱" in row["detail_zh"] and "稳定" in row["detail_zh"]
    assert " -> " not in row["detail_zh"]
    assert "->" not in row["detail_zh"]


def test_hub_feed_alert_view_does_not_pass_stored_message_zh():
    """Hub call site must not pass parquet message_zh into alert_view.

    Passing r['message_zh'] would let stored ZH silently outrank
    _zh_needs_rebuild and revive the half-translated class the rebuild
    exists to kill. Pin the three-arg call.
    """
    src = inspect.getsource(bv.home_alert_feed)
    assert 'v = alert_view(r["rule"], r["severity"], r["message"])' in src
    assert 'alert_view(r["rule"], r["severity"], r["message"],' not in src
    call_line = src.split("v = alert_view", 1)[1].splitlines()[0]
    assert "message_zh" not in call_line


# ---------------------------------------------------------------------------
# P2 — Other Features chips
# ---------------------------------------------------------------------------

def test_hub_risk_chip_plain_words_demote_index():
    en, zh, tip_en, tip_zh = bv._hub_risk_chip(
        {"risk_on": True, "risk_word": "ON", "risk_index": 2})
    assert en == "Low risk"
    assert zh == "低风险"
    assert "Risk ON" not in en and "Risk ON" not in zh
    assert "2/100" in tip_en and "2/100" in tip_zh
    assert "0 = calm" in tip_en
    assert "低压力" in tip_zh


def test_hub_mom_chip_uses_minus1_to_plus1_scale():
    en, zh, tip_en, tip_zh = bv._hub_mom_chip({"momentum": 0.63})
    assert en == "Strong up-momentum"
    assert zh == "动量偏强向上"
    assert "Mom 0.63" not in en
    assert "0.63" in tip_en and "0.63" in tip_zh
    assert "−1 to +1" in tip_en or "-1 to +1" in tip_en
    assert "−1 到 +1" in tip_zh or "-1 到 +1" in tip_zh

    down, down_zh, _, _ = bv._hub_mom_chip({"momentum": -0.8})
    assert down == "Strong down-momentum"
    assert down_zh == "动量偏强向下"

    # Vote roster is the engine's actual momentum votes (engine/btc_signals.py
    # momentum(): ema_trend, ema_cross, macd_hist, sma200, roc20, rsi_zone,
    # sopr_momentum, sth_cost_basis) — not a shortened "trend, MACD, RSI, SOPR".
    _, _, tip_en, tip_zh = bv._hub_mom_chip({"momentum": 0.63})
    for token in ("EMA trend", "EMA cross", "MACD", "200-day SMA",
                  "20-day ROC", "RSI", "SOPR", "short-term holder cost"):
        assert token in tip_en
    for token in ("EMA 趋势", "EMA 交叉", "MACD", "200日均线",
                  "20日涨跌幅", "RSI", "SOPR", "短线持有成本"):
        assert token in tip_zh
    assert "up to eight" in tip_en
    assert "chain data is present" in tip_en
    assert "最多八" in tip_zh
    assert "链上数据存在" in tip_zh


def test_hub_mom_chip_unavailable_is_a_worded_null():
    en, zh, tip_en, tip_zh = bv._hub_mom_chip({"momentum": None})
    assert en == "Momentum: no reading yet"
    assert zh == "动量：暂无读数"
    assert en != "Momentum" and zh != "动量"
    assert "unavailable" in tip_en.lower()
    empty_en, empty_zh, _, _ = bv._hub_mom_chip({})
    assert empty_en == "Momentum: no reading yet"
    assert empty_zh == "动量：暂无读数"


def test_hub_health_chip_states_scale_and_late_cycle():
    out = bv._hub_health_chip({"score": 88, "phase": "late", "label": "healthy"})
    assert out is not None
    en, zh, tip_en, tip_zh = out
    assert en == "Healthy · late-cycle"
    assert zh == "健康 · 周期晚段"
    assert "Health 88" not in en
    assert "88/100" in tip_en and "88/100" in tip_zh
    assert "healthy ≥ 67" in tip_en
    assert "Late-cycle" in tip_en
    assert "信用偏紧" in tip_zh


def test_g_vectors_chips_carry_lens_tips():
    vm = {"risk_on": True, "risk_word": "ON", "risk_index": 2, "momentum": 0.63}
    html = bv._g_vectors(
        vm, None, None, {"score": 88, "phase": "late", "label": "healthy"},
        None, None, None, None)
    assert "Low risk" in html and "低风险" in html
    assert "Strong up-momentum" in html and "动量偏强向上" in html
    assert "Healthy · late-cycle" in html and "健康 · 周期晚段" in html
    assert "Risk ON · 2" not in html
    assert "Mom 0.63" not in html
    assert "Health 88 · late" not in html
    assert 'data-tip-en="' in html and 'data-tip-zh="' in html
    assert "Risk index 2/100" in html
    assert "Momentum 0.63" in html
    assert "Bond health 88/100" in html
    assert "EMA trend" in html
    null_html = bv._g_vectors(
        {"risk_on": True, "risk_word": "ON", "risk_index": 2, "momentum": None},
        None, None, None, None, None, None, None)
    assert "Momentum: no reading yet" in null_html
    assert "动量：暂无读数" in null_html
    assert ">Momentum<" not in null_html


# ---------------------------------------------------------------------------
# P3 — China/HK ticker names + HK beta exposures
# ---------------------------------------------------------------------------

def _market_blob():
    return [
        {"cc": cc, "flag": flag, "quad": "q1",
         "quad_name_en": "Goldilocks", "quad_name_zh": "理想增长"}
        for cc, flag in (("US", "🇺🇸"), ("CN", "🇨🇳"), ("HK", "🇭🇰"), ("CA", "🇨🇦"))
    ]


def test_hk_card_says_standout_setups_not_beta_exposures():
    html = bv._g_markets(_market_blob(), 63, 12, 24)
    assert "24 standout setups" in html
    assert "24 只精选个股" in html
    assert "beta exposures" not in html
    assert "beta 敞口" not in html
    assert " 个 beta" not in html


def test_cn_hk_chips_use_company_names_not_numeric_tickers(tmp_path, monkeypatch):
    from lib import config
    fact = tmp_path / "site" / "factordata"
    fact.mkdir(parents=True)
    (fact / "china_standouts.json").write_text(json.dumps({
        "buy": [
            {"ticker": "600519.SS", "name": "Kweichow Moutai / 贵州茅台",
             "name_zh": "贵州茅台"},
            {"ticker": "000858.SZ", "name": "Wuliangye", "name_zh": "五粮液"},
        ],
    }))
    (fact / "hk_standouts.json").write_text(json.dumps({
        "buy": [
            {"ticker": "0700.HK", "name": "Tencent Holdings", "name_zh": "腾讯控股"},
            {"ticker": "0941.HK", "name": "China Mobile", "name_zh": "中国移动"},
        ],
    }))
    monkeypatch.setattr(config, "ROOT", tmp_path)

    labels_cn = bv._standout_labels("china")
    labels_hk = bv._standout_labels("hk")
    assert labels_cn[0] == ("Kweichow Moutai", "贵州茅台")
    assert labels_hk[0] == ("Tencent Holdings", "腾讯控股")
    assert bv._standout_tickers("china") == ["600519", "000858"]  # order pin unchanged

    html = bv._g_markets(_market_blob(), 3, 2, 2, standout_tickers={
        "CN": labels_cn, "HK": labels_hk,
    })
    assert "Kweichow Moutai" in html and "贵州茅台" in html
    assert "Tencent Holdings" in html and "腾讯控股" in html
    assert "600519" not in html
    assert "0700" not in html
    assert 'class="sb-tickers">' in html
    assert "sb-tickers-code" not in html  # CN/HK names stay proportional


def test_cn_hk_missing_name_falls_back_to_ticker(tmp_path, monkeypatch):
    from lib import config
    fact = tmp_path / "site" / "factordata"
    fact.mkdir(parents=True)
    (fact / "china_standouts.json").write_text(json.dumps({
        "buy": [{"ticker": "600000.SS"}],
    }))
    (fact / "hk_standouts.json").write_text(json.dumps({
        "buy": [{"ticker": "0001.HK", "name": "", "name_zh": ""}],
    }))
    monkeypatch.setattr(config, "ROOT", tmp_path)
    assert bv._standout_labels("china") == [("600000", "600000")]
    assert bv._standout_labels("hk") == [("0001", "0001")]


def test_cn_hk_slash_in_english_name_is_not_truncated(tmp_path, monkeypatch):
    from lib import config
    fact = tmp_path / "site" / "factordata"
    fact.mkdir(parents=True)
    (fact / "hk_standouts.json").write_text(json.dumps({
        "buy": [
            {"ticker": "1299.HK", "name": "AIA Group / Swire joint"},
            {"ticker": "0700.HK", "name": "Tencent Holdings / 腾讯控股"},
            {"ticker": "0941.HK", "name": "China Mobile / 中国移动",
             "name_zh": "中国移动"},
        ],
    }))
    monkeypatch.setattr(config, "ROOT", tmp_path)
    labels = bv._standout_labels("hk")
    # English name containing " / " and no CJK half must stay intact.
    assert labels[0] == ("AIA Group / Swire joint", "AIA Group / Swire joint")
    # Combined EN / 中文 form still splits when the right half is CJK.
    assert labels[1] == ("Tencent Holdings", "腾讯控股")
    # Explicit name_zh wins; the CJK half is still stripped from EN.
    assert labels[2] == ("China Mobile", "中国移动")


def test_us_standout_labels_stay_tickers(tmp_path, monkeypatch):
    from lib import config
    fact = tmp_path / "site" / "factordata"
    fact.mkdir(parents=True)
    (fact / "us_standouts.json").write_text(json.dumps({
        "buy": [
            {"ticker": "AAA", "label": "BUY ZONE", "name": "Alpha Co"},
            {"ticker": "BBB", "label": "BUY ZONE", "name": "Beta Co"},
            {"ticker": "CCC", "label": "BUY ZONE"},
        ],
    }))
    monkeypatch.setattr(config, "ROOT", tmp_path)
    assert bv._standout_tickers("us") == ["AAA", "BBB", "CCC"]
    assert bv._standout_labels("us") == [("AAA", "AAA"), ("BBB", "BBB"), ("CCC", "CCC")]
    html = bv._g_markets(_market_blob(), 3, 0, 0, standout_tickers={
        "US": [("AAA", "AAA"), ("BBB", "BBB")],
    })
    assert 'class="sb-tickers sb-tickers-code"' in html
    assert "AAA" in html and "BBB" in html


# ---------------------------------------------------------------------------
# P4 — IPO lock-up line + hero skeleton
# ---------------------------------------------------------------------------

def test_ipo_lockup_line_names_the_company_and_the_count():
    en, zh = bv._hub_ipo_lockup_line({
        "next_lockup": "SWMR",
        "next_lockup_company": "SmartRent",
        "next_lockup_date": "2026-09-20",
        "lockups_approaching": 15,
    })
    assert "SmartRent" in en and "SmartRent" in zh
    assert "SWMR" not in en and "SWMR" not in zh
    assert "15 lock-ups approaching" in en
    assert "临近 15 只解禁" in zh
    assert "15 approaching" not in en


def test_ipo_lockup_line_falls_back_to_ticker_without_inventing_a_name():
    en, zh = bv._hub_ipo_lockup_line({
        "next_lockup": "SWMR", "lockups_approaching": 15,
    })
    assert "SWMR" in en and "SWMR" in zh
    assert "15 lock-ups approaching" in en


def test_g_vectors_ipo_line_uses_company_name():
    vm = {"risk_on": False, "risk_word": "OFF", "risk_index": 39, "momentum": -0.2}
    html = bv._g_vectors(
        vm, None, None, None, None, None, None, None,
        ipo={"present": True, "band": "OPEN", "verdict": "trails",
             "next_lockup": "SWMR", "next_lockup_company": "SmartRent",
             "next_lockup_date": "2026-09-20", "lockups_approaching": 15})
    assert "SmartRent" in html
    assert "15 lock-ups approaching" in html
    assert "SWMR" not in html


def test_hub_hero_uses_loading_skeleton_not_em_dash():
    vm = {"risk_on": False, "risk_word": "OFF", "risk_index": 39, "momentum": -0.8,
          "built": "2026-06-14"}
    html = bv._hub_html(
        vm, {"label": "Goldilocks", "date": "2026-06-12"}, [],
        commodities={"present": False}, forex={"present": False},
        bonds={"present": False}, etf={"present": False},
        watchlist={"present": False})
    assert "hub-clock-skel" in html
    assert 'class="hub-clock-skel skel"' in html
    assert 'class="hub-clock-static"' in html
    assert "Live · —" not in html
    assert "实时 · —" not in html
    assert "hub-clock-wrap" in html
    assert "is-live" in html  # JS adds the class after the first tick
    # No-JS / never-ran: the liveness WORD is outside .hub-clock-live so the
    # CSS that hides the live clock until is-live cannot blank the cell.
    assert ".hub-clock-wrap.is-live .hub-clock-static{display:none}" in html
    assert "@media(scripting:none){.hub-clock-skel{display:none}}" in html
    assert ".sb-tickers-code{font-family:var(--font-mono)}" in html
    # JS-enabled-but-IIFE-crashed: stamp no-clock, hide skeleton AND the
    # static "Live" word — failure shows nothing where the clock was.
    assert 'function fail(){if(wrap&&!wrap.classList.contains("is-live"))wrap.classList.add("no-clock");}' in html
    assert "setTimeout(fail,2000);" in html
    assert "}catch(e){fail();}" in html
    assert ".hub-clock-wrap.no-clock .hub-clock-skel" in html
    assert ".hub-clock-wrap.no-clock .hub-clock-static{display:none}" in html
    # Receipt line is prose in the UI face; mono stays on ticker codes only.
    assert ".ha-what ~ .ha-foot .ha-read,.ha-edge ~ .ha-foot .ha-read{font-size:11.5px;color:var(--muted)}" in html
    assert "ha-read{font-family:var(--font-mono)" not in html


def _what_changed_alert(i=0):
    return {
        "source": "macro", "source_label": "Macro", "source_label_zh": "宏观",
        "ts": f"2026-08-0{1 + (i % 9)}", "severity": "high",
        "headline": f"📡 Regime radar moved {i}",
        "headline_zh": f"📡 周期雷达变动 {i}",
        "detail": "The regime's footing went from a new regime to shifting",
        "detail_zh": "周期状态由「新周期」转为「转换中」",
        "link": "macro.html",
    }


def test_what_changed_chip_singular_and_plural_en():
    one = bv._g_alerts([_what_changed_alert(0)])
    assert "1 signal" in one
    assert "1 signals" not in one
    assert "1 条信号" in one
    three = bv._g_alerts([_what_changed_alert(i) for i in range(3)])
    assert "3 signals" in three
    assert "3 条信号" in three
    assert ">3 signal<" not in three and "cnt\">3 signal<" not in three
