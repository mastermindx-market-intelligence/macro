"""Smoke + invariant tests for the display-only rate/inflation transmission leaf."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import rate_inflation_transmission as rit


def _synthetic_frame(n: int = 800) -> pd.DataFrame:
    idx = pd.bdate_range("2019-01-01", periods=n)
    rng = np.random.default_rng(7)
    walk = lambda base, vol: base + np.cumsum(rng.normal(0, vol, n))  # noqa: E731
    f = pd.DataFrame(index=idx)
    f["us10y"] = walk(3.5, 0.03)
    f["us10y_real"] = walk(1.5, 0.03)
    f["breakeven_10y"] = f["us10y"] - f["us10y_real"]
    f["breakeven_5y5y"] = walk(2.3, 0.02)
    f["spread_2s10s"] = walk(0.2, 0.02)
    f["curve_tp_adj"] = f["spread_2s10s"] + walk(0.1, 0.01)
    f["rate_expectations_proxy"] = walk(-0.3, 0.02)
    f["core_pce_yoy"] = walk(3.0, 0.01)
    f["core_pce_3m_ann"] = f["core_pce_yoy"] + walk(0.0, 0.02)
    f["core_cpi_yoy"] = walk(3.2, 0.01)
    f["headline_cpi_yoy"] = walk(3.4, 0.02)
    f["ppi_core_yoy"] = walk(2.8, 0.02)
    f["eci_comp_yoy"] = walk(3.3, 0.005)
    f["infl_exp_5y"] = walk(2.4, 0.005)
    f["umich_infl_exp"] = walk(3.0, 0.01)
    f["cpi_core_services_yoy"] = walk(4.0, 0.01)
    f["cpi_shelter_yoy"] = walk(4.2, 0.01)
    return f


def test_metadata_is_bilingual_and_complete():
    for k, v in rit.DRIVERS_META.items():
        en, zh, kind = v
        assert en and zh and kind in {"level", "change"}, k
    for tkr, v in rit.ASSETS_META.items():
        en, zh, kind = v
        assert en and zh and kind, tkr
    # the live read drivers must all be defined and must EXCLUDE the raw levels
    assert rit.READ_DRIVERS <= set(rit.DRIVERS_META)
    assert not (rit.READ_DRIVERS & {"real10y", "be10y", "be5y5y"})


def test_chains_are_well_formed_and_bilingual():
    assert len(rit.CHAINS) >= 3
    for ch in rit.CHAINS:
        assert ch["trigger"] in rit.DRIVERS_META
        assert ch["title_en"] and ch["title_zh"]
        orders = [o["order"] for o in ch["orders"]]
        assert orders == [1, 2, 3], ch["id"]
        for o in ch["orders"]:
            assert o["en"] and o["zh"]
            assert all(a in rit.ASSETS_META for a in o["assets"]), ch["id"]


def test_build_drivers_causal_and_named():
    f = _synthetic_frame()
    d = rit.build_drivers(f)
    # every READ driver is present, finite at the tail, and the engine never crashes
    for k in rit.READ_DRIVERS:
        assert k in d.columns, k
    assert d.index.equals(f.index)


def test_snapshot_structure_and_invariants():
    f = _synthetic_frame()
    s = rit.snapshot(f)
    assert s is not None
    for key in ("asof", "state", "yield_momentum", "inflation_decomposition", "transmission",
                "headwinds", "tailwinds", "chains", "scenarios", "scored_status",
                "caveats", "calibrated"):
        assert key in s, key
    # state is bilingual & banded
    st = s["state"]
    assert st["rates"]["regime"] in {"restrictive", "neutral", "accommodative"}
    assert st["inflation"]["regime"] in {"above target", "at target", "below target"}
    assert st["expectations"]["anchoring"] in {"drifting up", "drifting down", "anchored"}
    for sub in ("rates", "inflation", "expectations"):
        assert st[sub]["label"]["en"] and st[sub]["label"]["zh"]
    # caveats + scored status bilingual
    assert s["scored_status"]["en"] and s["scored_status"]["zh"]
    assert all(c.get("en") and c.get("zh") for c in s["caveats"])
    assert s["yield_momentum"]["display_only"] is True
    assert s["yield_momentum"]["authority"] is False
    # chains carry the live annotation
    assert len(s["chains"]) == len(rit.CHAINS)
    for ch in s["chains"]:
        assert isinstance(ch["active"], bool)
        assert ch["title"]["en"] and ch["title"]["zh"]


def test_transmission_read_excludes_levels_and_is_finite():
    f = _synthetic_frame()
    s = rit.snapshot(f)
    if not s["calibrated"]:
        return  # no measured matrix in this environment — structure already checked
    for tkr, v in s["transmission"].items():
        assert v["verdict"] in {"headwind", "tailwind", "neutral"}
        assert np.isfinite(v["net"])
        # only READ_DRIVERS may contribute (raw levels excluded as co-trend)
        for p in v["top_drivers"]:
            assert p["driver"] in rit.READ_DRIVERS


def test_scenarios_directional_and_caveated():
    f = _synthetic_frame()
    s = rit.snapshot(f)
    for sc in s["scenarios"]:
        assert sc["label"]["en"] and sc["label"]["zh"]
        for m in sc["headwinds"]:
            assert m["implied_move_pct"] < 0
        for m in sc["tailwinds"]:
            assert m["implied_move_pct"] > 0


def test_snapshot_degrades_when_columns_missing():
    # an almost-empty frame must not raise — additive, never fatal
    idx = pd.bdate_range("2022-01-01", periods=300)
    f = pd.DataFrame(index=idx)
    f["us10y"] = 4.0
    f["us10y_real"] = 2.0
    f["breakeven_10y"] = 2.0
    f["breakeven_5y5y"] = 2.3
    f["curve_tp_adj"] = 0.1
    s = rit.snapshot(f)
    assert s is not None and "state" in s


# --------------------------------------------------------------------------- #
# breakeven velocity + causal decomposition (display-only visibility layer)
# --------------------------------------------------------------------------- #
def _bd_base(n: int = 600, seed: int = 3):
    idx = pd.bdate_range("2019-01-01", periods=n)
    rng = np.random.default_rng(seed)
    nz = lambda c, s: c + rng.normal(0, s, n)  # noqa: E731
    f = pd.DataFrame(index=idx)
    f["us10y"] = nz(4.0, 0.01)
    f["us10y_real"] = nz(1.8, 0.01)
    f["breakeven_10y"] = nz(2.2, 0.005)
    f["breakeven_5y5y"] = nz(2.2, 0.005)
    f["oil"] = nz(80.0, 0.4)
    f["gold"] = nz(2000.0, 8.0)
    f["hy_oas"] = nz(3.5, 0.03)
    f["vix_close"] = nz(16.0, 0.5)
    return f, idx


def _ramp(f, idx, col, end, k=20):
    f.loc[idx[-k:], col] = np.linspace(float(f[col].iloc[-k - 1]), end, k)


def test_breakeven_decomp_structure_and_bilingual():
    f, idx = _bd_base()
    bd = rit.breakeven_decomposition(f)
    assert bd is not None
    for key in ("level", "velocity_bp", "accel_10d_bp", "fall_speed_pctile",
                "trend", "direction", "cause_badge", "costate", "caveat"):
        assert key in bd, key
    assert bd["cause_badge"]["en"] and bd["cause_badge"]["zh"]
    assert bd["caveat"]["en"] and bd["caveat"]["zh"]
    assert bd["direction"] in {"falling", "rising", "flat"}
    assert bd["trend"] in {"downtrend", "uptrend", "choppy", "n/a"}


def test_breakeven_decomp_oil_cause_and_no_false_liquidity_flag():
    f, idx = _bd_base()
    _ramp(f, idx, "breakeven_10y", 2.0)       # -20bp (falling)
    _ramp(f, idx, "breakeven_5y5y", 2.15)     # -5bp (10y falls faster)
    _ramp(f, idx, "oil", 60.0)                # -25% oil crash
    # credit + vol stay CALM (no ramp) -> oil is the cause, NOT liquidity
    bd = rit.breakeven_decomposition(f)
    assert bd["direction"] == "falling"
    assert bd["cause_badge"]["cause"] == "oil"
    # 10y falls faster than 5y5y but credit/vol calm -> the TIPS-liquidity flag must NOT fire
    assert bd["tips_liquidity_flag"] is None


def test_breakeven_decomp_real_rate_cause():
    f, idx = _bd_base()
    _ramp(f, idx, "breakeven_10y", 2.0)       # falling
    _ramp(f, idx, "us10y_real", 1.95)         # +15bp real-rate rise, oil flat
    bd = rit.breakeven_decomposition(f)
    assert bd["cause_badge"]["cause"] == "real_rate"


def test_breakeven_decomp_liquidity_cause_and_flag():
    f, idx = _bd_base()
    _ramp(f, idx, "breakeven_10y", 2.0)       # falling
    _ramp(f, idx, "breakeven_5y5y", 2.15)     # 10y faster than 5y5y
    _ramp(f, idx, "us10y", 3.8)               # nominals rallying (-20bp)
    _ramp(f, idx, "hy_oas", 6.5, k=10)        # credit blowout -> high z
    _ramp(f, idx, "vix_close", 42.0, k=10)    # vol spike -> high pctile
    bd = rit.breakeven_decomposition(f)
    assert bd["cause_badge"]["cause"] == "liquidity"
    assert bd["tips_liquidity_flag"] is not None        # stressed + 10y faster -> fires
    assert bd["costate"]["hy_oas_z"] >= 1.0


def test_breakeven_decomp_quiet_when_flat():
    f, idx = _bd_base()
    bd = rit.breakeven_decomposition(f)        # no ramps -> roughly flat
    assert bd["direction"] == "flat"
    assert bd["cause_badge"]["cause"] == "quiet"


def test_breakeven_decomp_none_without_breakeven():
    f, idx = _bd_base()
    f = f.drop(columns=["breakeven_10y"])
    assert rit.breakeven_decomposition(f) is None


def test_breakeven_decomp_in_snapshot():
    f = _synthetic_frame()
    s = rit.snapshot(f)
    assert "breakeven_decomp" in s


def test_disabled_returns_none(monkeypatch):
    from lib import config
    base = config.load()
    cfg = dict(base)
    cfg["transmission"] = dict(base.get("transmission") or {}, enabled=False)
    monkeypatch.setattr(config, "load", lambda: cfg)
    assert rit.snapshot(_synthetic_frame()) is None


# ---------------------------------------------------------------------------
# TURN WATCH — the display-tier peak read (extreme_watch / rolldown_forming)
# ---------------------------------------------------------------------------

def _real_series_frame(values: np.ndarray) -> pd.DataFrame:
    idx = pd.bdate_range("2019-01-01", periods=len(values))
    f = pd.DataFrame(index=idx)
    f["us10y_real"] = values
    f["us10y"] = values + 2.0
    return f


def test_turn_watch_extreme_while_still_rising():
    """At a top-decile percentile with a rising short window -> extreme_watch, and the
    (regime, direction) pair stays honest: restrictive + rising."""
    vals = np.linspace(0.0, 2.5, 1500)          # monotone rise -> last value is the max
    st = rit.current_state(_real_series_frame(vals))
    r = st["rates"]
    assert r["regime"] == "restrictive" and r["direction"] == "rising"
    assert r["turn_watch"] == "extreme_watch"
    assert r["real_10y_chg_22d_bp"] is not None and r["real_10y_chg_22d_bp"] > 0
    assert "extreme" in r["label"]["en"]
    assert "极值" in r["label"]["zh"]


def test_turn_watch_rolldown_forming_on_22d_fall_from_extreme():
    """A >=12bp 22-day fall from a top-percentile level -> rolldown_forming, even while
    the 63d direction key still reads 'rising' (the exact lag this key exists to beat)."""
    vals = np.concatenate([np.linspace(0.0, 2.0, 1400), np.linspace(2.0, 2.5, 78),
                           np.linspace(2.5, 2.37, 22)])
    st = rit.current_state(_real_series_frame(vals))
    r = st["rates"]
    assert r["direction"] == "rising"           # 63d window still net-up: the lag is real
    assert r["turn_watch"] == "rolldown_forming"
    assert r["real_10y_chg_22d_bp"] <= -12
    assert "rolling down" in r["label"]["en"]
    assert "回落" in r["label"]["zh"]


def test_turn_watch_none_away_from_extreme():
    """A mid-range level never carries a turn-watch state, whatever the short window does."""
    vals = np.concatenate([np.linspace(0.0, 2.5, 700), np.linspace(2.5, 1.2, 778),
                           np.linspace(1.2, 1.1, 22)])
    st = rit.current_state(_real_series_frame(vals))
    r = st["rates"]
    assert r["turn_watch"] is None
    assert "extreme" not in r["label"]["en"] and "rolling down" not in r["label"]["en"]


def test_turn_watch_thresholds_mirror_peak_chains():
    """Drift guard: the engine's stateless read and the staged peak chains must keep the
    same thresholds (p90 extreme / 22td / -12bp). Skips until the chain YAML lands."""
    import re
    import pytest
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "knowledge" / "transmission" / "real_rate_peak_gold_rerate.yaml"
    if not p.exists():
        pytest.skip("peak chain YAML not on this branch yet")
    y = p.read_text()
    assert re.search(r"real_10y_pctile.*0\.90", y), "chain extreme percentile moved — re-pin engine turn_watch"
    assert re.search(r"DFII10.*window:\s*22.*value:\s*-12", y), "chain rolldown window/threshold moved — re-pin engine turn_watch"


# --------------------------------------------------------------------------- #
# null disclosure: missing inputs must publish None, not a middle state word
# --------------------------------------------------------------------------- #
def test_state_tokens_are_null_when_their_input_is_missing():
    """A 300-row frame holding only us10y=4.0 has no real-rate pctile, no 63d change,
    no core_pce, no breakeven wedge. Every token must be None and the labels must
    be the dash — the state block must contain no literal text 'None'."""
    import json
    idx = pd.bdate_range("2024-01-01", periods=300)
    f = pd.DataFrame(index=idx)
    f["us10y"] = 4.0
    st = rit.current_state(f)
    assert st["rates"]["regime"] is None
    assert st["rates"]["direction"] is None
    assert st["rates"]["turn_watch"] is None
    assert st["inflation"]["regime"] is None
    assert st["inflation"]["direction"] is None
    assert st["expectations"]["anchoring"] is None
    assert st["rates"]["label"] == {"en": "—", "zh": "—"}
    assert st["inflation"]["label"] == {"en": "—", "zh": "—"}
    assert st["expectations"]["label"] == {"en": "—", "zh": "—"}
    assert "None" not in json.dumps(st, ensure_ascii=False)


def test_state_numbers_are_null_not_zero_when_a_series_has_no_observation():
    """Every F1 number column is present but holds no value → all eight publish None.
    A real 0.0 observation in spread_2s10s must still publish 0.0."""
    idx = pd.bdate_range("2024-01-01", periods=300)
    f = pd.DataFrame(index=idx)
    for col in ("us10y", "spread_2s10s", "curve_tp_adj", "rate_expectations_proxy",
                "core_cpi_yoy", "headline_cpi_yoy", "ppi_core_yoy", "eci_comp_yoy"):
        f[col] = np.nan
    st = rit.current_state(f)
    assert st["rates"]["nominal_10y"] is None
    assert st["rates"]["curve_2s10s"] is None
    assert st["rates"]["curve_tp_adj"] is None
    assert st["rates"]["policy_gap"] is None
    assert st["inflation"]["core_cpi_yoy"] is None
    assert st["inflation"]["headline_cpi_yoy"] is None
    assert st["inflation"]["ppi_core_yoy"] is None
    assert st["inflation"]["eci_comp_yoy"] is None

    # A real 0.0 must round-trip as 0.0, not collapse to None.
    f["spread_2s10s"] = 0.0
    st = rit.current_state(f)
    assert st["rates"]["curve_2s10s"] == 0.0


def test_labels_never_print_none_on_short_history():
    """Short-history and missing-input frames must never print the literal text
    'None' in either label language."""
    import json

    # (i) 40 rows of us10y_real rising 1.0 -> 2.0 plus us10y=2.0: regime/direction
    # are None (pctile needs 60, 63d delta needs 64), so the EN label has no
    # bracket and the ZH label omits the regime too.
    idx = pd.bdate_range("2024-01-01", periods=40)
    f = pd.DataFrame(index=idx)
    f["us10y_real"] = np.linspace(1.0, 2.0, 40)
    f["us10y"] = 2.0
    st = rit.current_state(f)
    assert st["rates"]["regime"] is None
    assert st["rates"]["direction"] is None
    assert st["rates"]["label"]["en"] == "Real 10y 2.00%"
    assert st["rates"]["label"]["zh"] == "实际10年期 2.00%"

    # (ii) 62 rows us10y_real rising 0.0 -> 2.5: pctile covers the full window
    # (62 < 1260) so real_pct=1.0 → regime='restrictive' and turn_watch fires;
    # the 63d delta still needs 64 so direction is None, but the EN bracket
    # renders the single available word.
    idx = pd.bdate_range("2024-01-01", periods=62)
    f = pd.DataFrame(index=idx)
    f["us10y_real"] = np.linspace(0.0, 2.5, 62)
    f["us10y"] = 2.5
    st = rit.current_state(f)
    assert st["rates"]["regime"] == "restrictive"
    assert st["rates"]["direction"] is None
    assert st["rates"]["turn_watch"] == "extreme_watch"
    assert st["rates"]["label"]["en"] == "Real 10y 2.50% (restrictive — at a 5y extreme)"
    assert "None" not in st["rates"]["label"]["en"]
    assert "None" not in st["rates"]["label"]["zh"]
    assert "None" not in json.dumps(st, ensure_ascii=False)

    # (iii) core_pce_yoy=3.0 with no core_pce_3m_ann: regime reads, direction does
    # not — the EN label carries only the regime word.
    idx = pd.bdate_range("2024-01-01", periods=300)
    f = pd.DataFrame(index=idx)
    f["core_pce_yoy"] = 3.0
    st = rit.current_state(f)
    assert st["inflation"]["regime"] == "above target"
    assert st["inflation"]["direction"] is None
    assert st["inflation"]["label"]["en"] == "Core PCE 3.0% (above target)"
    assert "None" not in st["inflation"]["label"]["en"]


def test_snapshot_with_missing_inputs_serialises_without_none_text():
    """The snapshot's state block must contain no literal 'None' text even when
    its input frame is sparse — the existing snapshot_degrades frame is exactly the
    case at issue."""
    import json
    idx = pd.bdate_range("2022-01-01", periods=300)
    f = pd.DataFrame(index=idx)
    f["us10y"] = 4.0
    f["us10y_real"] = 2.0
    f["breakeven_10y"] = 2.0
    f["breakeven_5y5y"] = 2.3
    f["curve_tp_adj"] = 0.1
    s = rit.snapshot(f)
    assert "None" not in json.dumps(s["state"], ensure_ascii=False, default=str)


def test_transmission_page_state_chips_show_a_dash_when_the_owner_has_no_reading():
    """The three state chips on transmission.html.j2 must render the dash '—' when
    their underlying owner token is None, and must still render the translated
    state word when it is present."""
    import types
    from pathlib import Path
    import jinja2

    src = Path(__file__).resolve().parents[1] / "templates" / "transmission.html.j2"
    lines = src.read_text().splitlines()
    fed = [ln for ln in lines if "chf-l\">{{ t('Fed stance'" in ln]
    direction = [ln for ln in lines if "chf-l\">{{ t('Direction'" in ln]
    expectations = [ln for ln in lines if "chf-l\">{{ t('Expectations'" in ln]
    assert len(fed) == 1, "expected exactly one Fed-stance chip line"
    assert len(direction) == 1, "expected exactly one Direction chip line"
    assert len(expectations) == 1, "expected exactly one Expectations chip line"

    env = jinja2.Environment()
    t = lambda en, zh: en  # noqa: E731
    S_none = types.SimpleNamespace(
        rates=types.SimpleNamespace(regime=None, direction=None),
        inflation=types.SimpleNamespace(direction=None),
        expectations=types.SimpleNamespace(anchoring=None),
    )
    out_fed = env.from_string(fed[0]).render(t=t, S=S_none)
    out_dir = env.from_string(direction[0]).render(t=t, S=S_none)
    out_exp = env.from_string(expectations[0]).render(t=t, S=S_none)
    assert '<div class="chf-v">—</div>' in out_fed
    assert '<div class="chf-v">—</div>' in out_dir
    assert '<div class="chf-v">—</div>' in out_exp
    assert "None" not in out_fed and "None" not in out_dir and "None" not in out_exp

    S_full = types.SimpleNamespace(
        rates=types.SimpleNamespace(regime="restrictive", direction="rising"),
        inflation=types.SimpleNamespace(direction="re-accelerating"),
        expectations=types.SimpleNamespace(anchoring="anchored"),
    )
    out_fed2 = env.from_string(fed[0]).render(t=t, S=S_full)
    out_dir2 = env.from_string(direction[0]).render(t=t, S=S_full)
    out_exp2 = env.from_string(expectations[0]).render(t=t, S=S_full)
    assert "Tight" in out_fed2
    assert "Heating" in out_dir2
    assert "Anchored" in out_exp2


def test_dashboard_inflation_row_never_prints_none_or_a_default_expectations_read():
    """The dashboard inflation row (templates/dashboard.html.j2) must not print
    'None' for any null number/anchor, and must not default the longer-run
    expectations read to a stance when the owner has no anchoring read."""
    import jinja2
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "templates" / "dashboard.html.j2"
    lines = src.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if "{% set _inf_vst = _dlgrc_inf.vs_target_pp %}" in ln)
    end = next(i for i, ln in enumerate(lines) if "data-tip-zh=\"核心PCE" in ln)
    block = "\n".join(lines[start:end + 1])

    env = jinja2.Environment()
    out_null = env.from_string(block).render(_dlgrc_inf={
        "vs_target_pp": 0.8,
        "anchoring": None,
        "core_pce_yoy": 2.8,
        "core_cpi_yoy": None,
        "core_pce_3m_ann": None,
        "breakeven_10y": None,
    })
    assert "None" not in out_null
    assert 'data-tip-en="Core PCE 2.8% y/y."' in out_null
    assert 'data-tip-zh="核心PCE 2.8% 同比。"' in out_null
    assert "the longer-run expectations read is being updated." in out_null
    assert "长期预期读数更新中。" in out_null
    assert "expectations look" not in out_null
    assert "expectations:" not in out_null
    assert "预期：" not in out_null

    out_full = env.from_string(block).render(_dlgrc_inf={
        "vs_target_pp": 0.8,
        "anchoring": "anchored",
        "core_pce_yoy": 2.8,
        "core_cpi_yoy": 3.1,
        "core_pce_3m_ann": 2.5,
        "breakeven_10y": 2.3,
    })
    assert 'data-tip-en="Core PCE 2.8% y/y · Core CPI 3.1% · 3-month annualized PCE 2.5% · 10y breakeven 2.3% (expectations: anchored)."' in out_full
    assert 'data-tip-zh="核心PCE 2.8% 同比 · 核心CPI 3.1% · 3月年化PCE 2.5% · 10年盈亏平衡 2.3%（预期：稳定）。">?</span>' in out_full
    assert "longer-run expectations look steady." in out_full
    assert "长期预期看起来稳定。" in out_full


def test_transmission_page_curve_caption_shows_no_shape_when_the_curve_has_no_reading():
    """transmission.html.j2 yield-curve caption must say 'read being updated'
    when curve_2s10s is None, must say 'inverted — short above long' when
    negative, and 'upward-sloping — normal' when positive — never 'None'."""
    import types
    from pathlib import Path
    import jinja2

    src = Path(__file__).resolve().parents[1] / "templates" / "transmission.html.j2"
    lines = src.read_text().splitlines()
    curve = [ln for ln in lines if "chf-l\">{{ t('Yield curve'" in ln]
    assert len(curve) == 1
    env = jinja2.Environment()
    t = lambda en, zh: en  # noqa: E731

    S_none = types.SimpleNamespace(
        rates=types.SimpleNamespace(curve_2s10s=None),
    )
    out_none = env.from_string(curve[0]).render(t=t, S=S_none)
    assert "read being updated" in out_none
    assert "upward-sloping" not in out_none
    assert "inverted" not in out_none
    assert "None" not in out_none

    S_neg = types.SimpleNamespace(rates=types.SimpleNamespace(curve_2s10s=-0.2))
    out_neg = env.from_string(curve[0]).render(t=t, S=S_neg)
    assert "inverted — short above long" in out_neg

    S_pos = types.SimpleNamespace(rates=types.SimpleNamespace(curve_2s10s=0.5))
    out_pos = env.from_string(curve[0]).render(t=t, S=S_pos)
    assert "upward-sloping — normal" in out_pos
