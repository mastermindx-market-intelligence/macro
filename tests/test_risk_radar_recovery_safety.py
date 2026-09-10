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
    monkeypatch.setattr(recovery, "_liquidity_catalysts", lambda *a: [
        {"key": "fed_netliq", "region": "US", "fresh": True}])
    monkeypatch.setattr(recovery, "_market_catalysts", lambda *a: {
        "market_confirmed": True, "veto": {"active": False}})


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


@pytest.mark.parametrize("veto", [True, None, "false", 0])
def test_unknown_or_active_veto_never_confirms(channels, monkeypatch, veto):
    latest = _latest("us")
    latest["risk_radar"]["deescalation"] = {"eligible": True}
    monkeypatch.setattr(recovery, "_market_catalysts", lambda *a: {
        "market_confirmed": True, "veto": {"active": veto}})
    result = recovery.assess(latest)
    assert result["turn_confirmed"] is False
    assert result["turn_confirmed_full"] is False


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
    assert recovery.assess(latest) == {"present": False}


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
