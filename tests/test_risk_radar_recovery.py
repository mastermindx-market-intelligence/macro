"""Risk-Radar DE-ESCALATION (engine/risk_radar_recovery.py + risk_radar.trajectory).

Covers: the trajectory phase classifier (receding / peaking / rising), the liquidity-catalyst
detector, the assembled recovery read, and the load-bearing invariant that it is DISPLAY-ONLY
(it never injects a score ceiling or amplification key into the radar view-model).
RRX2 WA additions: drivers computation, old-artifact compat, channel semantics."""
from pathlib import Path

import numpy as np
import pandas as pd

from engine import risk_radar, risk_radar_intl, risk_radar_recovery


def _subs(vals):
    """A synthetic Tier-A subscore frame whose worst-scare path follows `vals` (0-100)."""
    idx = pd.bdate_range("2026-01-01", periods=len(vals))
    v = np.asarray(vals, dtype=float)
    return pd.DataFrame({"credit": v, "rates": v * 0.6, "bubble": v * 0.5,
                         "growth": v * 0.4, "vol": v * 0.3}, index=idx)


# ---- trajectory phase classifier --------------------------------------------------------------
def test_trajectory_receding_after_peak():
    vals = list(np.linspace(20, 92, 55)) + list(np.linspace(92, 70, 25))   # rise then fall
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    assert t is not None
    assert t["phase"] == "receding"
    assert t["velocity"] < 0                # falling
    assert t["off_peak"] > 0                # below the recent peak
    assert t["reached_risk"] is True
    assert t["spark_pts"]                   # a drawable sparkline


def test_trajectory_peaking_when_flat_at_top():
    vals = list(np.linspace(30, 92, 55)) + [92, 93, 92, 93, 92, 93, 92, 93, 92, 92,
                                            93, 92, 92, 93, 92, 92, 93, 92, 92, 93,
                                            92, 92, 93, 92, 92]               # rise then plateau
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    assert t["phase"] == "peaking"
    assert abs(t["velocity"]) < 1.5         # momentum stalled, not yet falling


def test_trajectory_rising_is_not_a_recovery():
    vals = list(np.linspace(20, 95, 80))    # monotonic up
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    assert t["phase"] == "rising"


def test_trajectory_calm_when_never_hot():
    vals = list(np.linspace(10, 35, 80))    # never reaches the caution band
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    assert t["reached_risk"] is False
    assert t["phase"] == "calm"


# ---- liquidity-catalyst detector --------------------------------------------------------------
def test_liquidity_catalysts_fed_legs():
    latest = {"liquidity_overlay": "expanding",
              "fed_stance": {"stance": "dovish", "implied_cuts_12m": 3.0, "guidance": "easing"},
              "fed_path": {"implied_cuts_12m": 3.0}}
    keys = {c["key"] for c in risk_radar_recovery._liquidity_catalysts(latest)}
    assert "fed_netliq" in keys            # TGA drawdown / net-liquidity expanding
    assert "fed_policy" in keys            # dovish / cuts priced (the emergency-cut case)


def test_liquidity_catalysts_quiet_when_contracting():
    latest = {"liquidity_overlay": "contracting",
              "fed_stance": {"stance": "hawkish", "implied_cuts_12m": -1.0, "guidance": "unknown"},
              "fed_path": {"implied_cuts_12m": -1.0}}
    cats = risk_radar_recovery._liquidity_catalysts(latest)
    assert all(c["key"] not in ("fed_netliq", "fed_policy") for c in cats)


# ---- assembled recovery read ------------------------------------------------------------------
def _receding_latest():
    vals = list(np.linspace(20, 92, 55)) + list(np.linspace(92, 70, 25))
    traj = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    return {"risk_radar": {"trajectory": traj},
            "liquidity_overlay": "expanding",
            "fed_stance": {"stance": "dovish", "implied_cuts_12m": 3.0, "guidance": "easing"},
            "fed_path": {"implied_cuts_12m": 3.0}}


def test_assess_present_but_unconfirmed_without_local_evidence():
    rec = risk_radar_recovery.assess(_receding_latest())
    assert rec and rec["present"] is True
    # This fixture has no eligibility or local confirmation. The former True
    # expectation encoded the incident; supported confirmation has its own test.
    assert rec["receding"] is False
    assert rec["turn_confirmed"] is False
    assert rec["headline_en"] and rec["sub_en"] and rec["do_en"] and rec["caveat_en"]
    assert 0 <= rec["strength"] <= 100
    assert rec["n_catalysts"] >= 1  # context is retained, not an all-clear


def test_assess_absent_when_rising():
    vals = list(np.linspace(20, 95, 80))
    latest = {"risk_radar": {"trajectory": risk_radar.trajectory(_subs(vals), risk_radar._calib())},
              "liquidity_overlay": "contracting", "fed_stance": {"stance": "hawkish"}}
    rec = risk_radar_recovery.assess(latest)
    assert rec == {
        "present": False,
        "construction_version": risk_radar_recovery.RECOVERY_CONSTRUCTION_VERSION,
    }


def test_assess_none_without_trajectory():
    assert risk_radar_recovery.assess({"risk_radar": {}}) is None
    assert risk_radar_recovery.assess({}) is None


def test_assess_never_raises_on_garbage():
    # malformed inputs must degrade, never crash the build
    for bad in (None, {"risk_radar": None}, {"risk_radar": {"trajectory": {"phase": "receding"}}}):
        risk_radar_recovery.assess(bad)   # no exception


# ---- shared classifier (used by both US + intl radars) ----------------------------------------
def _win(vals):
    return pd.Series(vals, index=pd.bdate_range("2026-01-01", periods=len(vals)))


def test_shared_classifier_phases():
    receding = risk_radar._trajectory_from_series(_win([90, 88, 85, 80, 75, 70]), None, None, 68.0)
    assert receding["phase"] == "receding" and receding["velocity"] < 0
    rising = risk_radar._trajectory_from_series(_win([50, 58, 66, 74, 82, 90]), None, None, 68.0)
    assert rising["phase"] == "rising"
    peaking = risk_radar._trajectory_from_series(_win([90, 91, 90, 91, 90, 90]), None, None, 68.0)
    assert peaking["phase"] == "peaking"   # plateaued at the top (velocity ~0, still near peak)
    calm = risk_radar._trajectory_from_series(_win([10, 12, 14, 16, 18, 20]), None, None, 68.0)
    assert calm["phase"] == "calm"      # never reached the caution band -> nothing to recede from


# ---- international radar trajectory ------------------------------------------------------------
def test_intl_trajectory_receding():
    idx = pd.bdate_range("2025-01-01", periods=250)
    comp = pd.Series(np.concatenate([np.linspace(0.20, 0.95, 200),
                                     np.linspace(0.95, 0.70, 50)]), index=idx)   # 0-1 percentile
    B = pd.Series(np.linspace(100, 80, 250), index=idx)                          # declining index
    t = risk_radar_intl._trajectory(comp, B, risk_radar_intl._calib(risk_radar_intl.CN_PROFILE))
    assert t is not None
    assert t["phase"] == "receding"
    assert t["reached_risk"] is True
    assert t["odds_now"] is not None      # intl odds series built from the per-market prob surface


def test_intl_assess_uses_market_and_never_crashes():
    # an intl latest carries market='cn' on the radar snapshot and lacks Fed keys; assess must read
    # the Fed legs globally (via the US latest) and never crash on the intl shape.
    idx = pd.bdate_range("2025-01-01", periods=250)
    comp = pd.Series(np.concatenate([np.linspace(0.20, 0.95, 200),
                                     np.linspace(0.95, 0.70, 50)]), index=idx)
    B = pd.Series(np.linspace(100, 80, 250), index=idx)
    traj = risk_radar_intl._trajectory(comp, B, risk_radar_intl._calib(risk_radar_intl.CN_PROFILE))
    rec = risk_radar_recovery.assess({"risk_radar": {"market": "cn", "trajectory": traj}})
    assert rec and rec["present"] is True            # CN risk receding
    assert isinstance(rec["catalysts"], list)        # market-aware catalyst read, no crash


def test_intl_market_channel_is_not_applicable():
    # US-ONLY scoping (masterplan §5 / RRX): the market-internal chips read US stores, so on an
    # intl radar the market channel must be N/A (None), never a US-derived read or a hard False —
    # and no US chips may attach to the intl recovery payload.
    idx = pd.bdate_range("2025-01-01", periods=250)
    comp = pd.Series(np.concatenate([np.linspace(0.20, 0.95, 200),
                                     np.linspace(0.95, 0.70, 50)]), index=idx)
    B = pd.Series(np.linspace(100, 80, 250), index=idx)
    traj = risk_radar_intl._trajectory(comp, B, risk_radar_intl._calib(risk_radar_intl.CN_PROFILE))
    rec = risk_radar_recovery.assess({"risk_radar": {"market": "cn", "trajectory": traj}})
    assert rec and rec["present"] is True
    assert rec["market"] is None                     # no US chips on an intl card
    assert rec["channels"]["market"] is None         # N/A, not False
    assert rec["channels"]["veto"] is None
    assert rec["channels"]["veto_evaluated"] is None
    assert rec["turn_confirmed_full"] is None        # conjunction not computed off-US
    assert isinstance(rec["turn_confirmed"], bool)   # presentation flag remains Boolean, now fail-closed


def test_us_market_channel_attached():
    # The US path must attach the market dict (or None on store failure) and boolean channels.
    rec = risk_radar_recovery.assess(_receding_latest())
    assert rec and rec["present"] is True
    assert "market" in rec and "channels" in rec
    assert rec["channels"]["market"] in (True, False)
    assert rec["channels"]["veto_evaluated"] in (True, False)
    assert rec["construction_version"] == risk_radar_recovery.RECOVERY_CONSTRUCTION_VERSION
    assert rec["turn_confirmed_full"] in (True, False)


# ---- DISPLAY-ONLY invariant -------------------------------------------------------------------
def test_recovery_is_display_only_no_ceiling_or_amp():
    """The recovery read must never inject downward-pressure keys (ceiling/amp/amp_keys) — it
    illustrates the turn, it does not relax (or tighten) the radar's one-directional override."""
    rec = risk_radar_recovery.assess(_receding_latest())
    assert "ceiling" not in rec
    assert "amp" not in rec and "amp_keys" not in rec


# ---- RRX2 WA: drivers computation ------------------------------------------------------------
def test_trajectory_emits_drivers_block():
    """trajectory() must emit a 'drivers' dict with 'faded' and 'warm' lists (RRX2 WA-3)."""
    vals = list(np.linspace(20, 92, 55)) + list(np.linspace(92, 70, 25))
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    assert t is not None
    assert "drivers" in t, "trajectory must emit drivers block"
    drv = t["drivers"]
    assert "faded" in drv and "warm" in drv
    assert isinstance(drv["faded"], list)
    assert isinstance(drv["warm"], list)
    # Each driver entry must have key/label_en/label_zh/peak/now
    for d in drv["faded"] + drv["warm"]:
        assert "key" in d and "label_en" in d and "label_zh" in d
        assert "peak" in d and "now" in d


def test_drivers_faded_when_scare_dropped():
    """Scares with peak>=50 and (peak-now)>=10 appear in faded, sorted by drop desc, cap 3."""
    # In the test subs: credit=v, rates=0.6*v, bubble=0.5*v, growth=0.4*v, vol=0.3*v
    # With v rising to 92 then falling to 70: credit peak~92 now~70 (drop 22), rates peak~55 now~42...
    vals = list(np.linspace(20, 92, 55)) + list(np.linspace(92, 70, 25))
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    drv = t["drivers"]
    # credit scare: peak ~92, now ~70, drop ~22 — must appear in faded
    faded_keys = [d["key"] for d in drv["faded"]]
    assert "credit" in faded_keys, f"credit should be in faded, got {faded_keys}"
    assert len(drv["faded"]) <= 3, "faded capped at 3"


def test_drivers_warm_when_scare_above_watch_band():
    """Scares with now >= watch_band (55) appear in warm, cap 2."""
    # With v at 92 in the last window: credit=92 (warm), rates=55.2 (just at watch)
    vals = list(np.linspace(60, 92, 80))  # still rising / peaking, high values
    t = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    drv = t["drivers"]
    # credit sub-score = vals[-1] = 92 >= 55 -> warm
    warm_keys = [d["key"] for d in drv["warm"]]
    assert "credit" in warm_keys
    assert len(drv["warm"]) <= 2, "warm capped at 2"


def test_drivers_mirrored_through_assess():
    """assess() must pass drivers from trajectory through to the recovery dict (RRX2 WA-3)."""
    rec = risk_radar_recovery.assess(_receding_latest())
    assert rec and rec["present"] is True
    assert "drivers" in rec
    drv = rec["drivers"]
    assert drv is not None
    assert "faded" in drv and "warm" in drv


def test_drivers_absent_is_none_on_old_artifact():
    """Old artifacts without 'drivers' key in trajectory must produce drivers=None in assess()."""
    vals = list(np.linspace(20, 92, 55)) + list(np.linspace(92, 70, 25))
    traj = risk_radar.trajectory(_subs(vals), risk_radar._calib())
    # Simulate old artifact: remove drivers key
    traj_old = {k: v for k, v in traj.items() if k != "drivers"}
    latest = {
        "risk_radar": {"trajectory": traj_old},
        "liquidity_overlay": "expanding",
        "fed_stance": {"stance": "dovish", "implied_cuts_12m": 3.0, "guidance": "easing"},
        "fed_path": {"implied_cuts_12m": 3.0},
    }
    rec = risk_radar_recovery.assess(latest)
    assert rec and rec["present"] is True
    # drivers key should be None (not present in old trajectory)
    assert rec.get("drivers") is None


# Regression for the shared card's no-liquidity fallback, independent of veto logic.
import pytest

@pytest.mark.parametrize("market", ["cn", "hk", "ca"])
@pytest.mark.parametrize("phase", ["peaking", "receding"])
def test_no_liquidity_card_never_asserts_unconfirmed_risk_is_easing(monkeypatch, market, phase):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from engine import market_state
    monkeypatch.setattr(risk_radar_recovery, "_liquidity_catalysts", lambda *args: [])
    monkeypatch.setattr(market_state, "_rr_scorecard_track", lambda *args: None)
    latest = {"risk_radar": {"market": market, "state": "elevated", "top_score": 85,
        "gross_factor": .78, "can_force": False, "dominant_label_en": "Breadth breakdown (all-boats)",
        "trajectory": {"phase": phase, "reached_risk": True},
        "drawdown_prob": {"h5": .12, "h10": .21, "h21": .40, "base_h21": .30, "lift_h21": 1.31}}}
    rd = market_state._radar_override_intl(latest, [])
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")))
    template = env.from_string('{% import "_risk_radar_dlg.html.j2" as rrd %}{{ rrd.risk_radar_dlg(market, rd, none, none) }}')
    html = template.render(market=market, rd=rd)
    assert "risk easing on its own" not in html
    assert "风险自行回落" not in html
    assert "Liquidity support unconfirmed" in html
    assert "流动性支持尚未确认" in html
    assert rd["top_score"] == 85 and rd["dd21"] == .40 and rd["gross"] == .78


# CONSOLIDATED_RECOVERY_SAFETY_7029: original safety cases preserved in the registered CI suite.
"""False-recovery containment: real producer, synthetic inputs, no ledger I/O."""
from copy import deepcopy
from datetime import date, timedelta

import pytest

from engine import risk_radar_recovery as recovery


def _latest(market="cn"):
    return {"date": "2026-09-09", "liquidity_overlay": "contracting",
            "risk_radar": {"market": market, "state": "elevated",
                "dominant_scare": "breadth",
                "dominant_label_en": "Breadth breakdown (all-boats)",
                "dominant_label_zh": "市场广度破位",
                "trajectory": {"phase": "receding", "reached_risk": True,
                    "intensity": 85, "peak": 95, "off_peak": 10,
                    "velocity": -2, "peak_days_ago": 27,
                    "odds_now": .40, "odds_peak": .50, "odds_delta": 0}}}


@pytest.fixture
def channels(monkeypatch):
    # Generic local-US confirmation shape. A separate end-to-end case below
    # proves that the real plumbing producer can emit this event.
    monkeypatch.setattr(recovery, "_liquidity_catalysts", lambda *a: [{
        "key": "fed_netliq", "region": "US", "fresh": True,
        "confirmation_markets": ["us"],
    }])
    monkeypatch.setattr(recovery, "_market_catalysts", lambda *a: {
        "market_confirmed": True,
        "veto": {"active": False, "evaluated": True, "state": "clear"},
    })


@pytest.mark.parametrize("gate", [None, {}, {"eligible": None},
    {"eligible": "true"}, {"eligible": 1}, {"eligible": False}])
@pytest.mark.parametrize("market", ["cn", "us"])
def test_unestablished_permission_never_confirms(channels, gate, market):
    latest = _latest(market)
    if gate is not None:
        latest["risk_radar"]["deescalation"] = gate
    before = deepcopy(latest)
    result = recovery.assess(latest)
    assert result and result["present"] is True
    assert result["turn_confirmed"] is False
    assert result["receding"] is False
    assert "recovery not confirmed" in result["headline_en"].lower()
    assert latest == before


@pytest.mark.parametrize("market", ["cn", "hk", "ca", "jp", "kr"])
def test_foreign_liquidity_cannot_confirm_local_repair(channels, market):
    latest = _latest(market)
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    result = recovery.assess(latest)
    assert result["turn_confirmed"] is False
    assert result["turn_confirmed_full"] is None
    assert result["channels"]["market"] is None
    assert result["channels"]["veto"] is None
    assert result["present"] is True  # partial observations remain visible


@pytest.mark.parametrize("veto", [
    {"active": True, "evaluated": True, "state": "active"},
    {"active": None, "evaluated": False, "state": "unknown"},
    {"active": False},
    {"active": "false", "evaluated": True},
    {"active": False, "evaluated": None},
])
def test_unknown_or_active_veto_never_confirms(channels, monkeypatch, veto):
    latest = _latest("us")
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    monkeypatch.setattr(recovery, "_market_catalysts", lambda *a: {
        "market_confirmed": True, "veto": veto})
    result = recovery.assess(latest)
    assert result["turn_confirmed"] is False
    assert result["turn_confirmed_full"] is False
    assert result["channels"]["veto_evaluated"] is not True or veto.get("active") is not False


@pytest.mark.parametrize("phase", ["receding", "peaking"])
def test_context_never_directs_position_changes(channels, phase):
    latest = _latest("us")
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    latest["risk_radar"]["trajectory"]["phase"] = phase
    result = recovery.assess(latest)
    text = result["do_en"].lower()
    assert "does not authorize exposure changes" in text
    for phrase in ["begin scaling", "stop forced", "don't de-gross", "buy plan"]:
        assert phrase not in text
    assert "回补敞口" not in result["do_zh"]
    assert not {"ceiling", "amp", "amp_keys"}.intersection(result)


def test_confirmed_local_observations_still_render_without_trade_advice(channels):
    latest = _latest("us")
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    result = recovery.assess(latest)
    assert result["turn_confirmed"] is True
    assert result["turn_confirmed_full"] is True
    assert result["channels"]["veto_evaluated"] is True
    assert result["construction_version"] == recovery.RECOVERY_CONSTRUCTION_VERSION
    assert result["odds_now"] == .40 and result["odds_peak"] == .50
    assert "earlier window peak" in result["sub_en"].lower()
    assert "not a latest-session change" in result["sub_en"].lower()
    assert "does not authorize exposure changes" in result["do_en"].lower()


@pytest.mark.parametrize("value", [None, "bad", "2099-01-01"])
def test_missing_invalid_future_catalyst_dates_are_not_recent(value):
    assert recovery._recent(value) is False


def test_existing_recent_event_window_is_preserved():
    today = date.today()
    assert recovery._recent(today.isoformat()) is True
    assert recovery._recent((today - timedelta(days=60)).isoformat()) is True
    assert recovery._recent((today - timedelta(days=61)).isoformat()) is False


@pytest.mark.parametrize("value", [True, False, float("inf"), float("-inf")])
def test_non_measurements_are_not_numeric_evidence(value):
    assert recovery._num(value) is None


@pytest.fixture
def liquidity(monkeypatch):
    from engine import china_pboc_stance, global_liquidity
    monkeypatch.setattr(china_pboc_stance, "snapshot", lambda: None)
    monkeypatch.setattr(global_liquidity, "snapshot", lambda: None)
    monkeypatch.setattr(recovery, "_us_latest", lambda: {
        "date": "2026-09-09", "liquidity_overlay": "expanding",
        "fed_stance": {"stance": "hawkish", "implied_cuts_12m": -3,
                       "guidance": "on_hold"}})
    payload = {"asof": "2026-09-09",
        "quantity": {"netliq_chg_20d_bn": 106.766},
        "fed": {"policy_stance": "hawkish", "assets_chg_20d_bn": -11.363},
        "funding": {"reserve_scarcity_state": "tightening"},
        "components": {"reserves": {"d20_bn": -235.1}},
        "treasury": {"tga_impulse": {"active": True,
            "direction": "drawdown", "magnitude_bn": 86.8, "since": "2026-08-24"}}}
    monkeypatch.setattr(recovery, "_load_liquidity_plumbing", lambda: payload)
    return payload


def test_china_proxy_context_is_not_fed_easing_or_a_fresh_turn(liquidity):
    cats = recovery._liquidity_catalysts(_latest(), "cn")
    cat = next(c for c in cats if c["key"] == "fed_netliq")
    assert cat["label_en"] == "US net-liquidity proxy rising"
    assert cat["fresh"] is False  # category alone has no dated turn evidence
    assert "6pp" not in str(cat) and "6个百分点" not in str(cat)
    assert "hawkish" in cat["detail_en"]
    assert "tightening" in cat["detail_en"]
    assert "2026-09-09" in cat["detail_en"]
    assert not any(c["key"] == "fed_policy" for c in cats)


@pytest.mark.parametrize("payload", [{}, {"quantity": {"netliq_chg_20d_bn": None}}])
def test_missing_plumbing_does_not_invent_reserves_or_treasury_cause(monkeypatch, payload):
    monkeypatch.setattr(recovery, "_load_liquidity_plumbing", lambda: payload)
    en, zh = recovery._fed_netliq_detail()
    assert "reserves added" not in en
    assert "TGA drawdown" not in en
    assert "准备金注入" not in zh
    assert "unavailable" in en.lower()


def test_refilling_treasury_does_not_invent_fed_asset_growth(liquidity):
    liquidity["treasury"]["tga_impulse"]["direction"] = "build"
    en, _ = recovery._fed_netliq_detail()
    assert "WALCL expansion driving" not in en
    assert "-11" in en and "hawkish" in en


def test_renewed_rising_risk_never_shows_recovery(channels):
    latest = _latest()
    latest["risk_radar"]["trajectory"]["phase"] = "rising"
    assert recovery.assess(latest) == {
        "present": False,
        "construction_version": recovery.RECOVERY_CONSTRUCTION_VERSION,
    }


def test_undated_fed_pricing_is_context_not_a_fresh_policy_event(liquidity):
    latest = {"liquidity_overlay": "expanding", "fed_stance": {
        "stance": "dovish", "guidance": "easing", "implied_cuts_12m": 3}}
    cats = recovery._liquidity_catalysts(latest, "us")
    policy = next(c for c in cats if c["key"] == "fed_policy")
    assert policy["fresh"] is False
    assert "priced" in policy["label_en"].lower()
    assert "easing — aggressive" not in policy["label_en"].lower()


def test_undated_global_acceleration_is_not_a_fresh_event(liquidity, monkeypatch):
    from engine import global_liquidity
    monkeypatch.setattr(global_liquidity, "snapshot", lambda: {
        "state": "expanding", "accel": "accelerating", "impulse_pct": {"13w": 3}})
    cats = recovery._liquidity_catalysts(_latest(), "cn")
    assert next(c for c in cats if c["key"] == "global_cb")["fresh"] is False


def test_dated_pboc_event_remains_visible(liquidity, monkeypatch):
    from engine import china_pboc_stance
    monkeypatch.setattr(china_pboc_stance, "snapshot", lambda: {
        "stance": "easing", "last_moves": [
            {"easing": True, "date": date.today().isoformat()}]})
    cats = recovery._liquidity_catalysts(_latest(), "cn")
    assert next(c for c in cats if c["key"] == "pboc")["fresh"] is True


@pytest.mark.parametrize("market", ["cn", "hk", "ca"])
@pytest.mark.parametrize("can_force", [False, True])
def test_actual_market_consumer_and_dialog_keep_risk_without_false_turn(
        channels, monkeypatch, market, can_force):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from engine import market_state
    monkeypatch.setattr(market_state, "_rr_scorecard_track", lambda *a: None)
    latest = _latest(market)
    latest["risk_radar"].update({"top_score": 85, "gross_factor": .78,
        "can_force": can_force, "drawdown_prob": {"h5": .12, "h10": .21,
            "h21": .40, "lift_h21": 1.31, "base_h21": .30}})
    before = deepcopy(latest)
    overrides = []
    rd = market_state._radar_override_intl(latest, overrides)
    assert rd["state"] == "elevated" and rd["top_score"] == 85
    assert rd["gross"] == .78 and rd["dd21"] == .40
    assert rd["ceiling"] == (38 if can_force else None)
    assert rd["binding"] is can_force
    assert len(overrides) == int(can_force)
    assert latest == before
    env = Environment(loader=FileSystemLoader(
        str(Path(__file__).resolve().parents[1] / "templates")), autoescape=False)
    template = env.from_string('{% import "_risk_radar_dlg.html.j2" as rrd %}'
                              '{{ rrd.risk_radar_dlg(market, rd, none, none) }}')
    html = template.render(market=market, rd=rd)
    assert "Recovery not confirmed" in html and "修复尚未确认" in html
    assert "Breadth breakdown (all-boats)" in html
    assert 'class="rrx-rec is-turn"' not in html
    assert 'class="rrx-rec-tag"' not in html
    assert "Begin scaling exposure" not in html and "回补敞口" not in html
    assert "does not authorize exposure changes" in html
    # The real JSON projection preserves the same safety flags and risk figures.
    import json
    projected = json.loads(json.dumps(rd, allow_nan=False))
    assert projected["recovery"]["turn_confirmed"] is False
    assert projected["dd21"] == .40 and projected["gross"] == .78



def _dated_us_plumbing_event():
    today = date.today().isoformat()
    return {
        "asof": today,
        "authority": {"deescalate": True},
        "quantity": {"overlay": "expanding", "netliq_chg_20d_bn": 106.8},
        "treasury": {
            "asof": today,
            "tga_impulse": {
                "active": True,
                "direction": "drawdown",
                "magnitude_bn": 86.8,
                "since": today,
            },
        },
    }


def test_actual_dated_us_plumbing_event_can_supply_positive_local_path(monkeypatch):
    """Positive TURN uses an existing producer event, not fabricated fresh metadata."""
    from engine import china_pboc_stance, global_liquidity
    latest = _latest("us")
    latest["liquidity_overlay"] = "expanding"
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    monkeypatch.setattr(recovery, "_load_liquidity_plumbing", _dated_us_plumbing_event)
    monkeypatch.setattr(china_pboc_stance, "snapshot", lambda: None)
    monkeypatch.setattr(global_liquidity, "snapshot", lambda: None)
    monkeypatch.setattr(recovery, "_market_catalysts", lambda *a: {
        "market_confirmed": True,
        "veto": {"active": False, "evaluated": True, "state": "clear"},
    })
    result = recovery.assess(latest)
    netliq = next(c for c in result["catalysts"] if c["key"] == "fed_netliq")
    assert netliq["fresh"] is True
    assert netliq["confirmation_markets"] == ["us"]
    assert result["confirmation_catalysts"] == ["fed_netliq"]
    assert result["n_confirmation_fresh"] == 1
    assert result["turn_confirmed"] is True
    assert result["turn_confirmed_full"] is True


def test_fresh_pboc_context_cannot_confirm_us_recovery(monkeypatch):
    from engine import china_pboc_stance, global_liquidity
    latest = _latest("us")
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    monkeypatch.setattr(recovery, "_load_liquidity_plumbing", lambda: {})
    monkeypatch.setattr(china_pboc_stance, "snapshot", lambda: {
        "stance": "easing",
        "last_moves": [{"easing": True, "date": date.today().isoformat()}],
        "rationale": {"en": "Dated PBoC easing event.", "zh": "有日期的央行宽松事件。"},
    })
    monkeypatch.setattr(global_liquidity, "snapshot", lambda: None)
    monkeypatch.setattr(recovery, "_market_catalysts", lambda *a: {
        "market_confirmed": True,
        "veto": {"active": False, "evaluated": True, "state": "clear"},
    })
    result = recovery.assess(latest)
    pboc = next(c for c in result["catalysts"] if c["key"] == "pboc")
    assert pboc["fresh"] is True
    assert pboc["confirmation_markets"] == ["cn"]
    assert result["n_fresh"] == 1
    assert result["n_confirmation_fresh"] == 0
    assert result["channels"]["liquidity_context"] is True
    assert result["channels"]["liquidity"] is False
    assert result["turn_confirmed"] is False


def test_us_plumbing_event_requires_current_dated_producer_evidence(monkeypatch):
    payload = _dated_us_plumbing_event()
    payload["asof"] = "2000-01-01"
    monkeypatch.setattr(recovery, "_load_liquidity_plumbing", lambda: payload)
    assert recovery._fresh_us_netliq_event() is False
    payload["asof"] = date.today().isoformat()
    payload["treasury"]["asof"] = "2000-01-01"
    assert recovery._fresh_us_netliq_event() is False
    payload["treasury"]["asof"] = date.today().isoformat()
    payload["treasury"]["tga_impulse"]["since"] = "2099-01-01"
    assert recovery._fresh_us_netliq_event() is False
    payload["treasury"]["tga_impulse"]["since"] = date.today().isoformat()
    payload["authority"]["deescalate"] = False
    assert recovery._fresh_us_netliq_event() is False


@pytest.mark.parametrize("scope", [None, [], "us", ["cn"], ["US"], [1]])
def test_confirmation_scope_requires_explicit_matching_list(scope):
    cats = [{"key": "x", "fresh": True, "confirmation_markets": scope}]
    assert recovery._confirmation_fresh(cats, "us") == []


def test_template_exposes_unknown_or_legacy_veto_state():
    template = (Path(__file__).resolve().parents[1] / "templates" /
                "_risk_radar_card.html.j2").read_text()
    assert "volatility veto unknown — turn not trusted" in template
    assert "波动否决状态未知 — 转向暂不可信" in template
    assert "(not rv.market.veto) or" in template
    assert "rv.market.veto.evaluated is not sameas true" in template
    assert "rv.market.veto.active is not sameas false" in template
