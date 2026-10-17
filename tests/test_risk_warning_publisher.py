"""Existing rr_banner publisher gains an additive warning/briefing without changing legacy alert semantics."""
from __future__ import annotations

import json
from pathlib import Path

from scripts import build_rr_banner as rb
from scripts import risk_warning_projection as rw

SESSION = "2026-09-25"


def radar(state="caution", *, asof=SESSION, score=80.3, ungated="elevated"):
    return {
        "schema":"risk_radar.v2","asof":asof,"state":state,"state_ungated":ungated,
        "top_score":score,"dominant_scare":"rates","dominant_label_en":"Rates / inflation shock",
        "dominant_label_zh":"利率/通胀冲击",
        "scares":[
            {"scare":"rates","label_en":"Rates / inflation shock","label_zh":"利率/通胀冲击","score":score,"band":"elevated" if state=="caution" else state,"firing_legs":[]},
            {"scare":"credit","label_en":"Credit stress","label_zh":"信用压力","score":67.9,"band":"watch","firing_legs":[]},
        ],
        "drawdown_prob":{"h5":.03,"h10":.08,"h21":.16 if state=="caution" else .33,
                         "base_h21":.178,"lift_h21":.9 if state=="caution" else 1.9,
                         "state_above_base":False if state=="caution" else True,
                         "conjunction_n":1,
                         "calibration_evidence":{"schema":"risk_radar_probability_evidence.v1",
                            "evidence_class":"reconstructed_historical","precision_grade":False,
                            "target":{"depth":.05,"horizons":[5,10,21],"price_path":"native SPY closing observations"},
                            "limitations":["Overlapping forward windows are not independent episodes."]}},
    }


def regime_doc(rr):
    return {"asof":rr["asof"],"quad":"Q2","quad_name":"Reflation","transition_state":"NEW_REGIME",
            "growth_score":.20,"inflation_score":.24,"risk_radar":rr}


def market_state(expected=SESSION, recovery=None):
    return {"schema":"market_state.v1","asof":expected,"score":59,"verdict":"MIXED",
            "components":[
                {"key":"trend","label_en":"Trend & technicals","score":61,"read_en":"2/3 US indices in an uptrend"},
                {"key":"vol","label_en":"Volatility regime","score":86,"read_en":"VIX term contango; vol 11%ile"},
                {"key":"breadth","label_en":"Breadth & participation","score":0,"read_en":"Breadth 8%ile; divergence"},
                {"key":"liquidity","label_en":"Liquidity & credit","score":72,"read_en":"Fed liquidity expanding; HY widening"},
            ],
            "freshness":{"expected_asof":expected,"data_asof":expected,"stale":False,"any_input_stale":True,"worst_input_age_days":86},
            "radar":{"recovery": recovery or {"present":False}}}


def envelope(asof=SESSION):
    return {"schema":"mastermind.risk_envelope/v1","as_of":asof,"hazard_summary":{"stage":"FRAGILE"},
            "provenance":{"sources":[
                {"source_id":"leadership-crack-latest","role":"hazard_evidence","state":"BROKEN",
                 "label_en":"Leadership cohort","label_zh":"龙头股群体","coverage":"FRESH"},
                {"source_id":"risk-radar-us","role":"hazard_evidence","state":"caution",
                 "label_en":"Cross-asset scares","label_zh":"跨资产风险扫描","coverage":"FRESH"},
            ]}}


def write_json(root: Path, relative: str, value):
    p=root/relative; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(value))


def run_build(tmp_path, rr, ms=None, env=None, previous=None):
    data=tmp_path/"data"; site=tmp_path/"site"; site.mkdir()
    write_json(data,"regime/latest.json",regime_doc(rr))
    if ms is not None: write_json(data,"market_state/latest.json",ms)
    if env is not None: write_json(data,"risk_envelope/latest.json",env)
    if previous is not None: (site/"rr_banner.json").write_text(json.dumps(previous))
    old=rb.config.data_dir; rb.config.data_dir=lambda:data
    try: out=rb.build(site)
    finally: rb.config.data_dir=old
    return json.loads(out.read_text())


def test_caution_becomes_visible_additive_warning_while_legacy_extreme_alert_stays_null(tmp_path):
    payload=run_build(tmp_path,radar(),market_state(),envelope())
    assert payload["schema"] == "rr_banner.v1"
    assert payload["alert"] is None
    assert payload["warning_projection"]["state"] == "caution"
    assert payload["warning_projection"]["attention"] == "warning"
    assert payload["briefing"]["stance"]["label_en"] == "Reduce concentration"
    assert payload["briefing"]["downside"]["interpretation"] == "early_flag_not_edge"
    assert [d["key"] for d in payload["briefing"]["drivers"][:2]] == ["radar:rates","leadership-crack-latest"]


def test_riskoff_preserves_exact_legacy_alert_value_and_adds_critical_briefing(tmp_path):
    rr=radar("risk-off",score=94,ungated="risk-off")
    legacy=rb.build_alert(rr)
    payload=run_build(tmp_path,rr,market_state(),envelope())
    assert payload["alert"] == legacy
    assert payload["warning_projection"]["attention"] == "critical"
    assert payload["briefing"]["stance"]["label_en"] == "Stand aside / protect capital"
    assert payload["briefing"]["stance"]["exact_exposure_target"] is None


def test_publisher_uses_market_state_expected_session_not_radar_as_its_own_freshness_clock(tmp_path):
    rr=radar(asof="2026-09-24")
    payload=run_build(tmp_path,rr,market_state(SESSION),envelope())
    assert payload["warning_projection"]["status"] == "unavailable"
    assert payload["warning_projection"]["artifact_freshness"] == "stale"
    assert "stale_source_session" in payload["warning_projection"]["reason_codes"]


def test_previous_severe_warning_survives_an_unverifiable_new_refresh_without_reviving_legacy_alert(tmp_path):
    previous_warning=rw.project_radar_warning(radar("risk-off",asof="2026-09-24",score=94,ungated="risk-off"),
                                              market="us",expected_session="2026-09-24")
    previous={"schema":"rr_banner.v1","asof":"2026-09-24","generated_at":"x","alert":None,
              "warning_projection":previous_warning}
    payload=run_build(tmp_path,radar("caution",asof="2026-09-24"),market_state(SESSION),envelope(),previous)
    assert payload["alert"] is None
    assert payload["warning_projection"]["status"] == "unverified"
    assert payload["warning_projection"]["attention"] == "critical"
    assert payload["warning_projection"]["last_known"]["state"] == "risk-off"
    assert payload["briefing"]["downside"]["h21"] is None
    assert payload["briefing"]["stance"]["label_en"] == "Keep defensive posture pending verification"


def test_missing_market_state_clock_is_unavailable_not_calm_and_does_not_self_date_from_radar(tmp_path):
    payload=run_build(tmp_path,radar(),None,envelope())
    assert payload["warning_projection"]["status"] == "unavailable"
    assert payload["warning_projection"]["state"] is None
    assert "expected_session_unavailable" in payload["warning_projection"]["reason_codes"]
    assert payload["briefing"]["stance"]["label_en"] == "Verification unavailable"


def test_market_state_stale_input_receipt_is_not_laundered_into_radar_input_quality(tmp_path):
    payload=run_build(tmp_path,radar(),market_state(),envelope())
    assert payload["warning_projection"]["underlying_input_status"] == "unknown"
    assert payload["briefing"]["backdrop"]["market_state_score"] == 59
    breadth=next(c for c in payload["briefing"]["backdrop"]["components"] if c["key"]=="breadth")
    assert breadth["score"] == 0
