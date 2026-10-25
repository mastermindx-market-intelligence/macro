"""Capital Protection Briefing is a deterministic display projection over existing owners."""
from copy import deepcopy

from scripts import risk_warning_projection as rw

SESSION = "2026-09-25"


def warning(state="caution", score=80.3, *, market="us", ungated="elevated", status="current"):
    return {
        "schema": rw.SCHEMA, "market": market,
        "id": f"rw-{market}-{SESSION}-{state}", "status": status,
        "attention": {"calm":"none","watch":"watch","caution":"warning","elevated":"high","risk-off":"critical"}[state],
        "state": state if status == "current" else None,
        "state_ungated": ungated if status == "current" else None,
        "confirmation": "pending" if status == "current" and ungated else "unknown",
        "source_schema": "risk_radar.v2" if market == "us" else "risk_radar_intl.v1",
        "source_session": SESSION, "expected_session": SESSION,
        "artifact_freshness": "current" if status == "current" else "unavailable",
        "source_clock_basis": "source_asof_vs_owner_expected_session",
        "score": score if status == "current" else None,
        "score_semantics": "intensity_not_probability",
        "underlying_input_status": "unknown", "underlying_input_details": {},
        "reason_codes": [], "driver_en": "Rates / inflation shock", "driver_zh": "利率/通胀冲击",
        "authority": {"display_only": True, "may_execute": False, "may_size": False, "may_gate": False, "may_rank": False},
        "recovery": {"assessed": False, "reentry_authorized": False},
        "headline_en": "Risk building", "headline_zh": "风险正在累积",
        "detail_en": "", "detail_zh": "",
    }


def us_radar(state="caution", h21=.16, base=.178, above=False):
    return {
        "schema":"risk_radar.v2", "market":"us", "asof":SESSION,
        "state":state, "state_ungated":"elevated", "top_score":80.3,
        "dominant_scare":"rates", "dominant_label_en":"Rates / inflation shock",
        "dominant_label_zh":"利率/通胀冲击",
        "scares":[
            {"scare":"rates","label_en":"Rates / inflation shock","label_zh":"利率/通胀冲击","score":80.3,"band":"caution"},
            {"scare":"credit","label_en":"Credit stress","label_zh":"信用压力","score":44.0,"band":"watch"},
        ],
        "drawdown_prob":{
            "h5":.03,"h10":.08,"h21":h21,"base_h21":base,"lift_h21":round(h21/base,2),
            "state_above_base":above,
            "measure":">=5% SPY pullback",
            "calibration_evidence":{
                "schema":"risk_radar_probability_evidence.v1",
                "evidence_class":"reconstructed_historical","precision_grade":False,
                "target":{"depth":.05,"horizons":[5,10,21],"price_path":"native SPY closing observations"},
                "limitations":["Overlapping forward windows are not independent episodes."]
            }
        }
    }


def regime():
    return {"quad":"Q2","quad_name":"Reflation","transition_state":"NEW_REGIME",
            "growth_score":.20,"inflation_score":.24}


def market_state():
    return {"score":59,"verdict":"MIXED","components":{
        "trend":{"score":62},"breadth":{"score":38},"liquidity":{"score":55}
    }}


def envelope():
    return {"schema":"mastermind.risk_envelope/v1","as_of":SESSION,
            "hazard_summary":{"stage":"FRAGILE"},
            "provenance":{"sources":[
                {"source_id":"leadership-crack-latest","role":"hazard_evidence","state":"BROKEN","label_en":"AI-hardware leaders","label_zh":"AI硬件龙头","coverage":"FRESH"},
                {"source_id":"risk-radar-us","role":"hazard_evidence","state":"caution","label_en":"Cross-asset scares","coverage":"FRESH"},
            ]}}


def test_caution_80_briefing_is_defensive_but_does_not_promote_crash_probability():
    got = rw.compose_capital_protection_briefing(
        warning(), radar=us_radar(), regime=regime(), market_state=market_state(), risk_envelope=envelope())
    assert got["schema"] == "mastermind.risk_warning_briefing/v1"
    assert got["severity"] == {"state":"caution","attention":"warning","ungated_state":"elevated","confirmation":"pending","intensity":80.3}
    assert got["stance"]["label_en"] == "Reduce concentration"
    assert got["stance"]["authority"] == "display_guidance"
    assert got["stance"]["exact_exposure_target"] is None
    assert got["downside"]["h21"] == .16 and got["downside"]["base_h21"] == .178
    assert got["downside"]["interpretation"] == "early_flag_not_edge"
    assert got["downside"]["calibration_status"] == "reconstructed_historical"
    assert got["authority"]["may_execute"] is False and got["authority"]["may_size"] is False


def test_backdrop_explicitly_refuses_to_turn_reflation_into_safety():
    got = rw.compose_capital_protection_briefing(
        warning(), radar=us_radar(), regime=regime(), market_state=market_state(), risk_envelope=envelope())
    assert got["backdrop"]["regime"] == "Reflation"
    assert got["backdrop"]["market_state_verdict"] == "MIXED"
    assert got["backdrop"]["separation_note_en"] == "Reflation does not mean the tape is safe. The economic backdrop and market damage are different reads."
    assert got["backdrop"]["growth_score"] == .20 and got["backdrop"]["inflation_score"] == .24


def test_existing_owner_evidence_builds_driver_and_deterioration_rows_without_new_scores():
    got = rw.compose_capital_protection_briefing(
        warning(), radar=us_radar(), regime=regime(), market_state=market_state(), risk_envelope=envelope())
    assert got["drivers"][0]["key"] == "radar:rates"
    assert got["drivers"][0]["score"] == 80.3
    leadership = next(d for d in got["drivers"] if d["key"] == "leadership-crack-latest")
    assert leadership["state"] == "BROKEN" and leadership["score"] is None
    path = {p["key"]:p for p in got["deterioration_path"]}
    assert path["rates_pressure"]["status"] == "observed"
    assert path["leadership_damage"]["status"] == "observed"
    assert "score" not in path["leadership_damage"]


def test_us_riskoff_can_advocate_capital_protection_without_exact_cash_target():
    w = warning("risk-off",94,ungated="risk-off")
    rr = us_radar("risk-off",.33,.178,True); rr["top_score"] = 94; rr["state_ungated"]="risk-off"
    got = rw.compose_capital_protection_briefing(w, radar=rr, regime=regime(), market_state=market_state())
    assert got["stance"]["label_en"] == "Stand aside / protect capital"
    assert got["downside"]["interpretation"] == "above_base"
    assert got["stance"]["exact_exposure_target"] is None
    assert "all-cash" in got["stance"]["authority_note_en"]


def test_international_intensity_and_native_probability_do_not_inherit_us_calibration():
    w = warning("risk-off",99,market="cn",ungated="risk-off")
    rr = {"schema":"risk_radar_intl.v1","market":"cn","asof":SESSION,"state":"risk-off",
          "state_ungated":"risk-off","top_score":99,"dominant_scare":"breadth",
          "dominant_label_en":"Breadth breakdown","drawdown_prob":{"h21":.50,"base_h21":.29,"lift_h21":1.7}}
    got = rw.compose_capital_protection_briefing(w, radar=rr)
    assert got["severity"]["intensity"] == 99
    assert got["downside"]["calibration_status"] == "directional_only"
    assert got["downside"]["h21"] is None and got["downside"]["base_h21"] is None
    assert "99%" not in str(got)


def test_recovery_owner_fields_define_repair_and_resolution_path_without_all_clear_inference():
    rec = {"present":True,"phase":"receding","receding":True,"peaking":False,"suppressed":False,
           "turn_confirmed":True,"turn_confirmed_full":False,
           "channels":{"liquidity":True,"market":False,"veto":True},
           "headline_en":"Risk receding — liquidity turning supportive"}
    got = rw.compose_capital_protection_briefing(warning(), radar=us_radar(), recovery=rec)
    assert got["recovery"]["state"] == "EARLY_REPAIR"
    assert got["recovery"]["reentry_authorized"] is False
    path = {p["key"]:p for p in got["resolution_path"]}
    assert path["liquidity_turn"]["status"] == "observed"
    assert path["market_internals"]["status"] == "missing"
    assert path["volatility_veto"]["status"] == "blocked"
    assert path["full_repair"]["status"] == "near"


def test_full_repair_is_still_display_only_and_does_not_authorize_reentry():
    rec = {"present":True,"phase":"receding","suppressed":False,"turn_confirmed":True,"turn_confirmed_full":True,
           "channels":{"liquidity":True,"market":True,"veto":False}}
    got = rw.compose_capital_protection_briefing(warning("elevated",88), radar=us_radar("elevated",.25,.178,True), recovery=rec)
    assert got["recovery"]["state"] == "CONFIRMED_REPAIR"
    assert got["recovery"]["reentry_authorized"] is False
    assert got["authority"]["may_execute"] is False


def test_unverified_last_known_severe_warning_keeps_defensive_stance_but_withholds_current_probability():
    w = warning("risk-off",94,status="unverified")
    w["attention"]="critical"; w["id"]="rw-us-2026-09-25-risk-off-unverified"
    got = rw.compose_capital_protection_briefing(w, radar=us_radar("risk-off",.33,.178,True))
    assert got["severity"]["state"] is None
    assert got["severity"]["attention"] == "critical"
    assert got["stance"]["label_en"] == "Keep defensive posture pending verification"
    assert got["downside"]["calibration_status"] == "unavailable"
    assert got["downside"]["h21"] is None
    assert got["freshness"]["status"] == "unverified"


def test_projection_is_pure_and_never_mutates_owner_payloads():
    w,rr,rg,ms,re = warning(),us_radar(),regime(),market_state(),envelope()
    originals = deepcopy((w,rr,rg,ms,re))
    rw.compose_capital_protection_briefing(w, radar=rr, regime=rg, market_state=ms, risk_envelope=re)
    assert (w,rr,rg,ms,re) == originals


def test_real_market_state_component_list_is_preserved_as_source_native_rows():
    ms = {"score":59,"verdict":"MIXED","components":[
        {"key":"trend","label_en":"Trend & technicals","score":61,"read_en":"2/3 indices up"},
        {"key":"vol","label_en":"Volatility regime","score":86,"read_en":"VIX term calm"},
        {"key":"breadth","label_en":"Breadth & participation","score":0,"read_en":"Breadth 8%ile; divergence"},
        {"key":"liquidity","label_en":"Liquidity & credit","score":72,"read_en":"Fed liquidity expanding; HY widening"},
    ]}
    got = rw.compose_capital_protection_briefing(warning(), radar=us_radar(), market_state=ms)
    assert got["backdrop"]["components"] == [
        {"key":"trend","label_en":"Trend & technicals","score":61,"read_en":"2/3 indices up"},
        {"key":"vol","label_en":"Volatility regime","score":86,"read_en":"VIX term calm"},
        {"key":"breadth","label_en":"Breadth & participation","score":0,"read_en":"Breadth 8%ile; divergence"},
        {"key":"liquidity","label_en":"Liquidity & credit","score":72,"read_en":"Fed liquidity expanding; HY widening"},
    ]


def test_broken_leadership_is_promoted_beside_dominant_radar_driver_without_fake_score():
    got = rw.compose_capital_protection_briefing(
        warning(), radar=us_radar(), risk_envelope=envelope())
    assert [d["key"] for d in got["drivers"][:3]] == ["radar:rates", "leadership-crack-latest", "radar:credit"]
    assert got["drivers"][1]["score"] is None
