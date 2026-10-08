"""International dashboard build smoke + the display-only invariant.

Renders templates/intl.html.j2 in BOTH modes from a synthetic view-model (no live
data needed) so the template + None-handling can't silently break, and asserts the
universe ticker/flag conversion. The display-only invariant: per-country records
expose descriptive gauges (recession_score, drawdown_risk) but NEVER a portfolio
weight / allocation — the risk reads must not feed a scored buy/sell.
"""
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.intl_universe import _EU_SUFFIX, _clean_local  # noqa: E402
from engine import i18n  # noqa: E402


def _vm() -> dict:
    rec = {"cc": "JP", "name": "Japan", "name_zh": "日本", "flag": "🇯🇵", "region": "Asia",
           "date": "2026-06-16", "quad": "Q1", "quad_name": "Goldilocks",
           "growth_score": 0.7, "inflation_score": -0.5, "confidence": 0.6,
           "liquidity": "neutral", "recession_score": 5, "recession_band": "low",
           "macro": {"policy_rate": 0.5, "yield_10y": 2.6, "curve": 1.4, "real_yield": 0.5,
                     "cpi_yoy": 2.0, "cpi_chg3m": 0.1, "gdp_yoy": 0.3, "unemployment": 2.5,
                     "fx_strength_3m": -0.7, "m2_yoy": 2.0, "fx": 1.5, "realvol": 14.0, "drawdown": 0.0},
           "macro_asof": {"cpi_yoy": "2026-04", "gdp": "2026-03", "unemployment": "2026-04", "yield_10y": "2026-05"},
           "equity": {"price": 23000, "off_52w_high": 0.0, "drawdown_risk": 16, "drawdown_band": "low",
                      "ext_grade": "stretched", "ext_z": 1.6, "bubble_flag": True},
           "data_limited": False, "quad_meaning": ("growth up inflation down", "增长上 通胀下")}
    summary = {"n": 1, "quad_counts": {"Goldilocks": 1}, "dominant_quad": "Goldilocks",
               "recession_watch": 0, "drawdown_watch": 0, "avg_recession": 5}
    rankings = {"recession_score": {"label_en": "Recession pressure", "label_zh": "衰退压力",
                                    "risk_high": True, "rows": [{"cc": "JP", "flag": "🇯🇵", "name": "Japan", "value": 5}]}}
    latest = {"date": "2026-06-16", "summary": summary, "records": [rec], "rankings": rankings,
              "heatmap": [{"cc": "JP", "flag": "🇯🇵", "name": "Japan", "growth": 0.7, "inflation": -0.5,
                           "quad": "Q1", "quad_name": "Goldilocks", "confidence": 0.6, "data_limited": False}],
              "periphery": {"asof": "2026-05", "spreads": [{"label": "Italy (BTP)", "flag": "🇮🇹",
                            "bps": 77, "chg3m_bps": -26, "widening": False}]}}
    setups = {"buy": [{"ticker": "4004.T", "name": "Resonac", "flag": "🇯🇵", "sector": "Materials",
                       "dir": "up", "label": "BOUNCE", "state": "BOUNCE", "alpha": 3.0,
                       "price": 18650, "off_high": -4.0, "spark_svg": ""}]}
    board = [{"cc": "KR", "flag": "🇰🇷", "market": "South Korea", "sector": "Information Technology",
              "n": 8, "mom_20d": 21.3, "mom_60d": 55.3, "above_trend": True, "rank": 1}]
    return {"latest": latest, "built": "2026-06-16 00:00 UTC", "records": [rec], "summary": summary,
            "rankings": rankings, "heatmap": latest["heatmap"], "periphery": latest["periphery"],
            "sector_board": board, "setups": setups}


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def test_render_macro_mode():
    html = _env().get_template("intl.html.j2").render(**_vm(), mode="macro")
    assert "Cross-country comparison" in html and "Regime map" in html
    assert "🇯🇵" in html and "Goldilocks" in html
    assert "{{" not in html and "{%" not in html        # no leaked template tags


def test_render_stocks_mode():
    html = _env().get_template("intl.html.j2").render(**_vm(), mode="stocks")
    assert "What to act on now" in html
    assert "4004.T" in html and "Resonac" in html
    assert "South Korea" in html                          # sector board row


def test_display_only_invariant():
    rec = _vm()["records"][0]
    forbidden = {"weight", "allocation", "position_size", "target_weight", "score_weight"}
    assert not (set(rec) & forbidden)
    assert not (set(rec.get("equity", {})) & forbidden)
    # the risk reads are descriptive 0-100 gauges, not weights
    assert 0 <= rec["recession_score"] <= 100
    assert 0 <= rec["equity"]["drawdown_risk"] <= 100


def _perf_vm() -> dict:
    """A view-model carrying the World Risk Appetite v2 keys the hero reads (RK),
    a global_read (GR) and a turn_board with a US row (the new markets)."""
    vm = _vm()
    RK = {
        "score": 54, "label_en": "Neutral", "label_zh": "中性", "tone": "flat",
        "breadth_above_200d": "7/10", "median_mom_3m": 3.9,
        "coverage_pct": 100.0, "n_available": 10, "n_universe": 10,
        "breakdown_share_pct": 11.5,
        "top_drags": [
            {"cc": "US", "name": "United States", "name_zh": "美国", "flag": "🇺🇸",
             "state": "downtrend", "state_en": "Downtrend", "state_zh": "下行趋势"},
            {"cc": "CN", "name": "China", "name_zh": "中国", "flag": "🇨🇳",
             "state": "breaking", "state_en": "Breaking down", "state_zh": "正在破位"},
        ],
        "per_market": {"US": {"h": 0.3, "state": "downtrend", "weight_pct": 30.0}},
    }
    GR = {"en": "World risk appetite neutral (54/100) — dragged by United States, China.",
          "zh": "全球风险偏好中性（54/100）——受美国、中国拖累。", "dominant_quad": "Goldilocks"}
    vm["perf"] = {"risk_appetite": RK, "global_read": GR, "rrg": None,
                  "correlation": None, "leaderboard": []}
    # turn_board with a US row (the new market) — tile must render None-safe
    vm["turn_board"] = [
        {"cc": "US", "name": "United States", "name_zh": "美国", "flag": "🇺🇸",
         "state": "downtrend", "state_en": "Downtrend", "state_zh": "下行趋势",
         "stance_en": "Stand aside", "stance_zh": "观望", "css": "state-downtrend",
         "urgency": 4, "since": "2026-06-01", "dd_pct": -8.0, "ext_raw_pct": -3.0,
         "ext_pctile": None, "ext_z": None, "mom20_pct": -4.0, "mom5_pct": -1.0,
         "rs20_pct": None, "rsi": 42.0, "rsi_at_high": None, "rsi_divergence": False,
         "macd_state": "bear", "macd_cross_date": None, "dd_vel_10d": -1.0,
         "vol_z": 0.5, "above_ma20": False, "above_ma50": False, "above_ma200": True,
         "was_parabolic_40d": False, "peak_date": None, "data_limited": False,
         "events": [], "risk_radar": None},
    ]
    vm["turn_events"] = []
    vm["rotation_ranks"] = []
    vm["bench_note"] = None
    return vm


def test_render_world_risk_v2_hero_and_turn_board():
    """Test 6: the macro hero renders the v2 drag line + the cap-weight receipt
    attributes, and a turn_board US row renders a tile."""
    html = _env().get_template("intl.html.j2").render(**_perf_vm(), mode="macro")
    # verdict comes from engine label (Neutral), not the old 'Mixed'
    assert "Neutral" in html
    # drag line (EN) — up to 3 drags with flag + name
    assert "Dragged by" in html
    assert "United States" in html and "China" in html
    # cap-weight receipt on the gauge side block (data-tip only, never title=)
    assert "data-tip-en=" in html
    assert "Weighs 10 markets by size" in html
    assert "% of world market value" in html
    # the US turn-board row renders (new market present in the generic loop)
    assert "🇺🇸" in html
    assert "{{" not in html and "{%" not in html


def test_render_world_risk_v2_broad_strength_fallback():
    """When top_drags is empty the substance line reads the broad-strength copy."""
    vm = _perf_vm()
    vm["perf"]["risk_appetite"]["top_drags"] = []
    vm["perf"]["risk_appetite"]["label_en"] = "Risk-on"
    vm["perf"]["risk_appetite"]["tone"] = "up"
    html = _env().get_template("intl.html.j2").render(**vm, mode="macro")
    assert "Broad strength" in html
    assert "no major market breaking down" in html


def test_turn_board_cards_size_independently_and_hovers_stay_concise():
    """One verbose market must not stretch its grid peers or every hover.

    This used to be enforced with `align-items:start`, which stops a short tile from
    painting to the bottom of the row but does NOT stop the row band itself from being
    sized by the tallest tile — so the verbose market (the only one carrying a tech-breadth
    line and a macro-backdrop paragraph) left a ~180px void under every one of its peers.
    The fix moved those two blocks off the tile face entirely (they were already carried,
    in fuller plain-word form, by the hover lens), so the face is uniform by construction
    and the grid can safely stretch. Pin the cause, not the old symptom-patch.
    """
    template = (ROOT / "templates" / "intl.html.j2").read_text(encoding="utf-8")

    assert ".tb-grid { display:grid;" in template
    # tiles fill their row — no ragged void under the short ones
    assert "align-items:stretch;" in template
    assert ".tb-tile { display:flex; flex-direction:column;" in template
    # the pullback strip is pinned to the tile floor so the faces line up
    assert ".tb-rd { margin-top:auto;" in template
    assert "t.display_state_en || t.state_en" in template
    # the two verbose face blocks must NOT come back — they belong to the hover lens
    assert '<div class="tb-confirm">' not in template
    assert '<div class="tb-context">' not in template
    assert "Higher = pricier than its own history" not in template
    assert "Price state and recovery quality are separate" not in template


def _quiet_cn_state() -> dict:
    return {
        "cc": "CN", "name": "China", "name_zh": "中国", "flag": "🇨🇳",
        "state": "calm", "state_en": "Quiet", "state_zh": "平静",
        "stance_en": "Nothing to do", "stance_zh": "无需操作",
        "css": "state-calm", "urgency": 0, "since": "2026-09-01",
        "dd_pct": -7.0, "ext_raw_pct": -1.0, "ext_pctile": 35.0,
        "ext_z": -0.5, "mom20_pct": -0.3, "mom5_pct": -0.6,
        "rs20_pct": -1.0, "rsi": 42.0, "rsi_at_high": None,
        "rsi_divergence": False, "macd_state": "bear",
        "macd_cross_date": None, "dd_vel_10d": -0.5, "vol_z": 0.2,
        "above_ma20": False, "above_ma50": True, "above_ma200": False,
        "was_parabolic_40d": False, "peak_date": None,
        "data_limited": False, "events": [],
    }


def test_risk_context_prevents_quiet_from_reading_as_all_clear():
    """A quiet price turn plus loud leading risk must not look like an all-clear."""
    from engine.intl_market_state import apply_risk_context

    radar = {"state": "risk-off", "asof": "2026-09-14", "can_force": False,
             "dominant_label_en": "Breadth breakdown (all-boats)",
             "dominant_label_zh": "广度普跌（普跌）"}
    out = apply_risk_context(_quiet_cn_state(), radar, page_asof="2026-09-14")

    assert out["state"] == "calm"
    assert out["risk_radar"] is radar
    assert out["risk_context"]["advisory"] is True
    assert out["display_state_en"] == "Quiet tape · risk alert"
    assert out["display_stance_en"] == "No break yet — leading pullback risk is high"


def test_stale_radar_never_hides_an_active_price_break():
    from engine.intl_market_state import apply_risk_context

    state = _quiet_cn_state()
    state.update({"state": "breaking", "state_en": "Breaking down",
                  "state_zh": "正在破位", "stance_en": "Reduce risk now",
                  "stance_zh": "立即降低风险", "urgency": 8})
    radar = {"state": "risk-off", "asof": "2026-09-01", "can_force": False}
    out = apply_risk_context(state, radar, page_asof="2026-09-14")

    assert out["risk_radar_stale"] is True
    assert out.get("display_state_en") is None
    assert out["state_en"] == "Breaking down"


def test_missing_radar_date_is_unresolved_when_page_date_is_known():
    from engine.intl_market_state import apply_risk_context

    radar = {"state": "risk-off", "can_force": False}
    out = apply_risk_context(_quiet_cn_state(), radar, page_asof="2026-09-14")

    assert out["risk_radar_stale"] is True
    assert out["risk_radar_age_days"] is None
    assert out["display_state_en"] == "Risk read stale"
    assert out["display_stance_en"] == "Refresh required — quiet is not an all-clear"


def test_stale_radar_hides_old_probability_receipts():
    from engine.intl_market_state import apply_risk_context

    vm = _perf_vm()
    radar = {
        "state": "risk-off", "asof": "2026-09-01", "can_force": False,
        "drawdown_prob": {"h21": 0.50, "base_h21": 0.31, "lift_h21": 1.6},
    }
    vm["turn_board"] = [
        apply_risk_context(_quiet_cn_state(), radar, page_asof="2026-09-14")
    ]
    html = _env().get_template("intl.html.j2").render(**vm, mode="macro")

    assert "Risk read stale" in html
    assert "Refresh required — risk read is 13 days old" in html
    assert "≥5% dip in a month" not in html


def test_render_cn_quiet_plus_risk_off_is_not_a_bare_quiet_tile():
    from engine.intl_market_state import apply_risk_context

    vm = _perf_vm()
    radar = {"state": "risk-off", "asof": "2026-09-14", "can_force": False,
             "dominant_label_en": "Breadth breakdown (all-boats)",
             "dominant_label_zh": "广度普跌（普跌）",
             "drawdown_prob": {"h21": 0.50, "base_h21": 0.31, "lift_h21": 1.6}}
    vm["turn_board"] = [
        apply_risk_context(_quiet_cn_state(), radar, page_asof="2026-09-14")
    ]
    vm["records"][0]["turn"] = vm["turn_board"][0]
    html = _env().get_template("intl.html.j2").render(**vm, mode="macro")

    assert "Quiet tape · risk alert" in html
    assert "No break yet — leading pullback risk is high" in html
    assert "The price-only tape is quiet, but the leading pullback radar is risk-off" in html
    assert "Breadth breakdown (all-boats)" in html
    assert "ts-risk-alert" in html
    assert "Nothing to do" not in html


def test_extra_market_context_attaches_china_radar_without_writing_ledgers(monkeypatch):
    from scripts import build_intl

    radar = {"state": "risk-off", "asof": "2026-09-14", "can_force": False,
             "dominant_label_en": "Breadth breakdown (all-boats)"}
    monkeypatch.setattr(build_intl, "_readonly_radar_snapshot", lambda _profile: radar)
    states = {"CN": _quiet_cn_state()}

    out = build_intl._attach_extra_market_risk_context(
        states, page_asof="2026-09-14", market_codes=("CN",)
    )
    assert out["CN"]["risk_radar"] is radar
    assert out["CN"]["display_state_en"] == "Quiet tape · risk alert"


def test_builder_joins_extra_market_risk_before_world_verdict_compose():
    builder = (ROOT / "scripts" / "build_intl.py").read_text(encoding="utf-8")

    attach_pos = builder.index("_world_states = _attach_extra_market_risk_context(")
    compose_pos = builder.index("perf = intl_performance.performance_panel(")
    assert attach_pos < compose_pos


def test_universe_ticker_conversion():
    assert _clean_local("8306") == "8306"                # JP code
    assert _clean_local("BP.") == "BP"                   # LSE trailing dot
    assert _clean_local("BT.A") == "BT-A"                # class share -> dash
    assert _clean_local("CASH") is None                  # cash row skipped
    assert _EU_SUFFIX["Germany"] == ".DE" and _EU_SUFFIX["France"] == ".PA"
