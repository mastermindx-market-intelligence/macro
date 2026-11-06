"""IM17 transmission-evidence contract tests (INTL-GS Wave 4, engine half).

The frozen models (``engine/contagion_links.py``, ``engine/contagion.py``) are
imported ONLY inside the tests that pin their invariance; the engine module
itself must never import them (T13). Fixtures are synthetic; no data/ path is
read and no network call is made.
"""
import ast
import copy
import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

import engine.intl_transmission_evidence as te
from engine.intl_global_observation import (
    build_observation,
    CONTRACT_VERSION as OBSERVATION_CONTRACT,
)
from engine.intl_global_universe import load_rights_matrix, load_universe

ROOT = Path(__file__).resolve().parents[1]

SESSIONS = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23",
            "2026-10-26"]
AS_OF = "2026-10-21T21:00:00Z"
MATRIX_ROW_IDS = {r["id"] for r in load_rights_matrix()["rows"]}


def _cj(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# IM12 fixtures
# --------------------------------------------------------------------------

def make_clocks(pub="2026-10-21T06:00:00Z", obs_at="2026-10-20T15:00:00Z",
                ing="2026-10-21T06:05:00Z", comp="2026-10-21T06:10:00Z",
                pub_precision="exact"):
    return {
        "observation": {"at": obs_at, "precision": "exact"},
        "source_publication": {"at": pub, "precision": pub_precision},
        "ingestion": {"at": ing, "precision": "exact"},
        "computation": {"at": comp, "precision": "exact"},
    }


def make_observation(market="JP", clocks=None, window_end="2026-10-21T15:00:00Z",
                     window_start="2026-10-20T15:00:00Z", qualified=True):
    identity = {
        "universe_id": market,
        "market_id": market,
        "index_id": f"{market}-IDX",
        "fx_id": f"USD{market}",
        "horizon": "1d",
        "currency_basis": "local",
        "return_basis": "price",
        "window_start": window_start,
        "window_end": window_end,
        "source_content_sha256": "0" * 64,
    }
    return build_observation(
        identity=identity,
        clocks=clocks or make_clocks(),
        values={"local_pct": -4.0, "fx_pct": -1.0, "usd_pct": -4.96},
        rights={"decision_ref": "chairman-user-facing-redistribution-confirmed-2026-10-09"}
        if qualified else {},
        incumbent={"quality": "qualified"} if qualified else {"quality": "withheld"},
        evidence_ref="tests#test_intl_transmission_evidence",
    )


# --------------------------------------------------------------------------
# Edge fixtures
# --------------------------------------------------------------------------

def doc_edge(origin="JP", receiver="us_broad_equity", **kw):
    base = dict(
        origin_market=origin, receiver=receiver, channel="dollar_funding",
        pathway="documented_exposure", model_status="documented_source",
        source_id="bis.statistics", measure_id="cross_border_usd_claims",
        units="usd_bn",
        interpretation_en="Cross-border USD claims of reporting banks on the market.",
        interpretation_zh="报告银行对该市场的跨境美元债权。",
        evidence_family="funding", as_of="2026-09-30",
        denominator="reporting_bank_usd_claims",
        exposure_kind="direct_financial_claims", amount=12.5)
    base.update(kw)
    return te.build_edge(**base)


def dy_edge(origin="JP", receiver="us_broad_equity",
            channel="portfolio_fund_ownership", **kw):
    base = dict(
        origin_market=origin, receiver=receiver, channel=channel,
        pathway="statistical_association", model_status="statistical_estimate_frozen",
        source_id="contagion_dy_var_14etf", measure_id="gfevd_to_us",
        units="share",
        interpretation_en="Frozen 14-ETF connectedness estimate of association with the US market.",
        interpretation_zh="冻结的14只ETF关联度估计。",
        evidence_family="equity", direction="down",
        direction_support="statistical_candidate",
        coverage_state="qualified", coverage_basis="synthetic fixture")
    base.update(kw)
    return te.build_edge(**base)


def hyp_edge(origin="JP", **kw):
    base = dict(
        origin_market=origin, receiver="us_broad_equity", channel="trade_earnings",
        pathway="hypothetical_scenario", model_status="structural_prior_frozen",
        source_id="contagion_links", measure_id="structural_link_prior",
        units="prior",
        interpretation_en="Structural prior link weight under the frozen graph.",
        interpretation_zh="冻结图下的结构性先验联系。",
        evidence_family="equity", coverage_state="qualified")
    base.update(kw)
    return te.build_edge(**base)


def synthetic_matrix(ids_):
    """Rights matrix in which the named rows ARE emission-permitted."""
    return {"rows": [
        {"id": rid, "source_family": rid.split(".")[0],
         "capability": "us_exposure_transmission", "scope": "synthetic test fixture",
         "rights_class": "derived_display_ok", "auth_class": "keyless_public",
         "decision_ref": "test-fixture", "grant_scope": "test", "delay": None,
         "review": {"status": "decided", "next_action": None}}
        for rid in ids_
    ]}


SHOWN_MATRIX = synthetic_matrix(["bis.statistics", "imf.data"])


# --------------------------------------------------------------------------
# Stress / response / factor fixtures
# --------------------------------------------------------------------------

def ind(iid="equity_index_return", uid="JP-IDX",
        label="outside_reference_range"):
    return {"indicator_id": iid, "underlying_id": uid, "attention_label": label}


def stress_block(indicators=None, label="outside_reference_range",
                 persistence=1, receipt="im15:fixture"):
    return {"attention_label": label, "persistence_sessions": persistence,
            "receipt_ref": receipt,
            "indicators": indicators if indicators is not None else [ind()]}


def resp(receiver="us_broad_equity", family="equity", direction="down",
         label="outside_reference_range", qualified=True,
         wstart="2026-10-21T06:00:00Z", wend="2026-10-21T20:00:00Z",
         receipt="resp:fixture"):
    return {"receiver_id": receiver, "measure_id": f"{receiver}_measure",
            "evidence_family": family, "window_start": wstart, "window_end": wend,
            "attention_label": label, "direction": direction, "qualified": qualified,
            "receipt_ref": receipt}


def gf(*fids, session="2026-10-21"):
    return [{"factor_id": f, "attention_label": "outside_reference_range",
             "session": session} for f in fids]


def rs(*markets, session="2026-10-21"):
    return [{"market_id": m, "attention_label": "outside_reference_range",
             "session": session} for m in markets]


def build_jp_event(obs=None, edges=None, responses=None, factors=(),
                   regional=(), indicators=None, as_of=AS_OF,
                   label="outside_reference_range", persistence=1):
    return te.build_event(
        origin_observation=obs or make_observation("JP"),
        stress=stress_block(indicators=indicators, label=label,
                            persistence=persistence),
        edges=edges if edges is not None else [],
        responses=responses if responses is not None else [],
        global_factors=list(factors), regional_stress=list(regional),
        receiver_sessions=SESSIONS, as_of=as_of)


# ==========================================================================
# T1
# ==========================================================================

def test_config_validates_and_matches_constants():
    doc = te.load_channels()
    assert te.validate_channels(doc) == []
    assert te.validate_channels(doc, load_rights_matrix()) == []
    assert [p["id"] for p in doc["pathways"]] == list(te.PATHWAYS)
    assert [c["id"] for c in doc["channels"]] == list(te.CHANNELS)
    assert [g["id"] for g in doc["glyph_families"]] == list(te.GLYPH_FAMILIES)
    th = doc["thresholds"]
    assert th["PERSISTENCE_MIN_SESSIONS"] == te.PERSISTENCE_MIN_SESSIONS == 2
    assert th["COMMON_SHOCK_MIN_MARKETS"] == te.COMMON_SHOCK_MIN_MARKETS == 3
    assert th["COMMON_SHOCK_MIN_REGIONS"] == te.COMMON_SHOCK_MIN_REGIONS == 2
    assert th["CORROBORATION_MIN_FAMILIES"] == te.CORROBORATION_MIN_FAMILIES == 2
    assert len(th["threshold_rationale_en"]) == 4
    for ch in doc["channels"]:
        for cs in ch["candidate_sources"]:
            if cs["rights_ref"] is not None:
                assert cs["rights_ref"] in MATRIX_ROW_IDS
    for f in doc["global_factors"]:
        if f["rights_ref"] is not None:
            assert f["rights_ref"] in MATRIX_ROW_IDS


# ==========================================================================
# T2
# ==========================================================================

def test_glyph_family_mapping_is_frozen():
    expected = {"dollar_funding": "lending", "sovereign_banking": "credit",
                "portfolio_fund_ownership": "flow", "trade_earnings": "flow",
                "commodity_terms_of_trade": "commodity",
                "leverage_liquidity": "credit", "common_global_shock": None}
    doc = te.load_channels()
    got = {c["id"]: c["glyph_family"] for c in doc["channels"]}
    assert got == expected
    assert dy_edge()["glyph_family"] == "flow"
    assert doc_edge()["glyph_family"] == "lending"


# ==========================================================================
# T3
# ==========================================================================

def test_pathway_label_is_exactly_one():
    with pytest.raises(te.TransmissionError):
        dy_edge(pathway=["statistical_association"])
    with pytest.raises(te.TransmissionError):
        dy_edge(pathway=("statistical_association",))
    with pytest.raises(te.TransmissionError):
        dy_edge(pathway={"statistical_association"})
    with pytest.raises(te.TransmissionError):
        dy_edge(pathway="no_such_pathway")
    with pytest.raises(te.TransmissionError):
        doc_edge(model_status="structural_prior_frozen")
    edge = dy_edge()
    assert isinstance(edge["pathway"], str)
    assert edge["pathway"] == "statistical_association"
    labels = {p["id"]: (p["label_en"], p["label_zh"])
              for p in te.load_channels()["pathways"]}
    for pathway_id, (en, zh) in labels.items():
        probe = dy_edge(pathway="observed_source_stress",
                        model_status="observed_qualified",
                        direction=None, direction_support="unsupported") \
            if pathway_id == "observed_source_stress" else None
        if probe is not None:
            assert (probe["pathway_label_en"], probe["pathway_label_zh"]) == (en, zh)
    assert (edge["pathway_label_en"], edge["pathway_label_zh"]) == \
        labels["statistical_association"]


# ==========================================================================
# T4
# ==========================================================================

def test_documented_exposure_requires_vintage_kind_and_denominator():
    with pytest.raises(te.TransmissionError):
        doc_edge(as_of=None)
    with pytest.raises(te.TransmissionError):
        doc_edge(exposure_kind=None)
    with pytest.raises(te.TransmissionError):
        doc_edge(denominator=None)
    with pytest.raises(te.TransmissionError):
        doc_edge(source_id="usda_fas", measure_id="us_ag_trade_with_market",
                 denominator="us_ag_trade", exposure_kind="production_import")


# ==========================================================================
# T5
# ==========================================================================

def test_rights_gate_withholds_value():
    unresolved = doc_edge()
    assert unresolved["source"]["emission_permitted"] is False
    assert unresolved["value"]["display"] == "withheld_rights_unresolved"
    assert unresolved["value"]["amount"] is None
    assert unresolved["source"]["rights_class"] == "unresolved"
    assert unresolved["source"]["authority"] == "rights_matrix"

    no_row = doc_edge(source_id="us_treasury_tic",
                      measure_id="us_holdings_of_securities",
                      denominator="us_portfolio_holdings",
                      exposure_kind="fund_holdings",
                      channel="portfolio_fund_ownership",
                      evidence_family="equity")
    assert no_row["value"]["display"] == "withheld_no_rights_row"
    assert no_row["value"]["amount"] is None
    assert no_row["source"]["rights_ref"] is None
    assert no_row["source"]["authority"] == "no_rights_row"

    house = dy_edge()
    assert house["source"]["emission_permitted"] is True
    assert house["source"]["authority"] == "house_model"
    assert house["source"]["rights_ref"] is None
    assert house["value"]["display"] == "unavailable"  # amount None
    assert house["value"]["amount"] is None

    house_with_value = dy_edge(amount=0.42)
    assert house_with_value["value"]["display"] == "shown"
    assert house_with_value["value"]["amount"] == 0.42


# ==========================================================================
# T6
# ==========================================================================

def test_no_country_exposure_percentage():
    edge = doc_edge()
    kinds = te.exposure_by_kind([edge])
    doc = te.load_channels()
    assert set(kinds) == set(doc["exposure_kinds"])
    row = kinds["direct_financial_claims"][0]
    assert row["denominator"] == "reporting_bank_usd_claims"
    assert row["units"] == "usd_bn"
    assert row["display"] == "withheld_rights_unresolved"
    assert kinds["operating_revenue"] == []
    ev = build_jp_event(edges=[edge], factors=(), regional=())
    summary = te.summarize_event(ev)
    ms = te.market_summary("JP", edges=[edge],
                           observations=[make_observation("JP")])
    strip = te.channel_rank_strip("JP", [], matrix=load_rights_matrix())
    board = te.build_board(market_ids=["JP"], edges=[edge],
                           observations=[make_observation("JP")], events=[ev],
                           as_of=AS_OF)
    assert te.forbidden_keys(edge) == []
    assert te.forbidden_keys(ev) == []
    assert te.forbidden_keys(summary) == []
    assert te.forbidden_keys(ms) == []
    assert te.forbidden_keys(strip) == []
    assert te.forbidden_keys(board) == []
    assert te.forbidden_keys(kinds) == []


# ==========================================================================
# T7
# ==========================================================================

def test_rank_strip_never_mixes_denominators():
    measures = [
        {"market_id": "JP", "channel": "dollar_funding",
         "measure_id": "cross_border_usd_claims", "units": "usd_bn",
         "denominator": "reporting_bank_usd_claims", "value": 100.0,
         "source_id": "bis.statistics", "as_of": "2026-09-30"},
        {"market_id": "KR", "channel": "dollar_funding",
         "measure_id": "cross_border_usd_claims", "units": "usd_bn",
         "denominator": "reporting_bank_usd_claims", "value": 80.0,
         "source_id": "bis.statistics", "as_of": "2026-09-30"},
        {"market_id": "AU", "channel": "dollar_funding",
         "measure_id": "cross_border_usd_claims", "units": "usd_bn",
         "denominator": "reporting_bank_usd_claims", "value": 80.0,
         "source_id": "bis.statistics", "as_of": "2026-09-30"},
        # Same channel, DIFFERENT denominator: must never join the population.
        {"market_id": "GB", "channel": "dollar_funding",
         "measure_id": "external_usd_debt", "units": "usd_bn",
         "denominator": "external_debt_stock", "value": 500.0,
         "source_id": "imf.data", "as_of": "2026-09-30"},
    ]
    strip = te.channel_rank_strip("JP", measures, matrix=SHOWN_MATRIX)
    rows = {r["channel"]: r for r in strip}
    assert [r["channel"] for r in strip] == [c for c in te.CHANNELS
                                             if c != "common_global_shock"]
    jp = rows["dollar_funding"]
    assert jp["state"] == "shown"
    assert jp["value"] == 100.0
    assert jp["rank"] == 1
    assert jp["rank_population"] == 3  # JP+KR+AU, never GB
    kr = te.channel_rank_strip("KR", measures, matrix=SHOWN_MATRIX)
    kr_row = {r["channel"]: r for r in kr}["dollar_funding"]
    assert kr_row["rank"] == 2  # tie with AU shared
    au = te.channel_rank_strip("AU", measures, matrix=SHOWN_MATRIX)
    au_row = {r["channel"]: r for r in au}["dollar_funding"]
    assert au_row["rank"] == 2
    gb = te.channel_rank_strip("GB", measures, matrix=SHOWN_MATRIX)
    gb_row = {r["channel"]: r for r in gb}["dollar_funding"]
    assert gb_row["measure_id"] == "external_usd_debt"
    assert gb_row["rank_population"] == 1
    # Channels without measures abstain; leverage/liquidity has no source.
    assert rows["leverage_liquidity"]["state"] == "unavailable"
    assert rows["leverage_liquidity"]["reason"] == "no_admitted_source"
    assert rows["leverage_liquidity"]["rank"] is None
    # With the real matrix every documented value is withheld today.
    real = {r["channel"]: r for r in
            te.channel_rank_strip("JP", measures, matrix=load_rights_matrix())}
    assert real["dollar_funding"]["state"] == "withheld"
    assert real["dollar_funding"]["reason"] == "rights_unresolved"
    assert real["dollar_funding"]["rank"] is None
    assert real["dollar_funding"]["value"] is None


# ==========================================================================
# T8
# ==========================================================================

def test_receiver_window_worked_cases():
    # (1) Tokyo-close publication 02:00 ET -> same-session open_to_close.
    w = te.receiver_window(make_observation("JP"), SESSIONS)
    assert w["state"] == "qualified"
    assert w["measurement_basis"] == "open_to_close"
    assert w["receiver_session"] == "2026-10-21"
    assert w["knowable_at"] == "2026-10-21T06:00:00Z"
    assert w["start"] == "2026-10-21T13:30:00Z"
    assert w["end"] == "2026-10-21T20:00:00Z"
    assert w["start_et"] == "2026-10-21T09:30:00-04:00"
    assert w["end_et"] == "2026-10-21T16:00:00-04:00"
    assert w["same_session_as_knowable"] is True
    assert w["first_qualified_at"] == "2026-10-21T06:10:00Z"
    assert w["latency"] == {"publication_to_ingestion_s": 300,
                            "ingestion_to_computation_s": 300}

    # (2) London publication 11:35 ET -> close_to_close ending next session.
    obs = make_observation("GB", clocks=make_clocks(
        pub="2026-10-21T15:35:00Z", ing="2026-10-21T15:40:00Z",
        comp="2026-10-21T15:45:00Z"))
    w2 = te.receiver_window(obs, SESSIONS)
    assert w2["measurement_basis"] == "close_to_close"
    assert w2["receiver_session"] == "2026-10-22"
    assert w2["start"] == "2026-10-21T20:00:00Z"
    assert w2["end"] == "2026-10-22T20:00:00Z"
    assert w2["start_et"] == "2026-10-21T16:00:00-04:00"
    assert w2["end_et"] == "2026-10-22T16:00:00-04:00"
    assert w2["same_session_as_knowable"] is False

    # (3) Publication 17:00 ET -> next session's open_to_close.
    obs = make_observation("JP", clocks=make_clocks(
        pub="2026-10-21T21:00:00Z", ing="2026-10-21T21:05:00Z",
        comp="2026-10-21T21:10:00Z"))
    w3 = te.receiver_window(obs, SESSIONS)
    assert w3["measurement_basis"] == "open_to_close"
    assert w3["receiver_session"] == "2026-10-22"
    assert w3["start"] == "2026-10-22T13:30:00Z"
    assert w3["end"] == "2026-10-22T20:00:00Z"
    assert w3["same_session_as_knowable"] is False

    # (4) Friday 17:00 ET -> Monday's open_to_close.
    obs = make_observation(
        "JP",
        clocks=make_clocks(pub="2026-10-23T21:00:00Z",
                           obs_at="2026-10-23T15:00:00Z",
                           ing="2026-10-23T21:05:00Z",
                           comp="2026-10-23T21:10:00Z"))
    w4 = te.receiver_window(obs, SESSIONS)
    assert w4["measurement_basis"] == "open_to_close"
    assert w4["receiver_session"] == "2026-10-26"
    assert w4["start"] == "2026-10-26T13:30:00Z"
    assert w4["end"] == "2026-10-26T20:00:00Z"

    # (5) session_date precision -> knowable 23:59:59 ET that date.
    obs = make_observation("JP", clocks=make_clocks(
        pub="2026-10-21", pub_precision="session_date",
        ing="2026-10-22T00:05:00Z", comp="2026-10-22T00:10:00Z"))
    w5 = te.receiver_window(obs, SESSIONS)
    assert w5["state"] == "qualified"
    assert w5["knowable_at"] == "2026-10-22T03:59:59Z"
    assert w5["measurement_basis"] == "open_to_close"
    assert w5["receiver_session"] == "2026-10-22"

    # (6) Clocks out of order -> abstain clock_order_violation.
    obs = make_observation("JP")
    broken = copy.deepcopy(obs["clocks"])
    broken["ingestion"]["at"] = "2026-10-20T00:00:00Z"
    obs["clocks"] = broken
    w6 = te.receiver_window(obs, SESSIONS)
    assert w6["state"] == "abstain"
    assert w6["reason"] == "clock_order_violation"
    assert w6["receiver_session"] is None

    # No sessions -> closed abstain reason.
    w7 = te.receiver_window(make_observation("JP"), [])
    assert w7["state"] == "abstain"
    assert w7["reason"] == "no_receiver_sessions"

    # A non-IM12 record is refused outright.
    with pytest.raises(te.TransmissionError):
        te.receiver_window({"contract_version": "other-v1"}, SESSIONS)


# ==========================================================================
# T9
# ==========================================================================

def test_classify_response_rules():
    window = te.receiver_window(make_observation("JP"), SESSIONS)
    assert window["state"] == "qualified"
    down = {"down"}
    both = {"up", "down"}

    abstained = {"state": "abstain", "reason": "clock_order_violation"}
    assert te.classify_response(abstained, resp(), expected_directions=down,
                                as_of=AS_OF)["status"] == "unavailable"
    assert te.classify_response(window, None, expected_directions=down,
                                as_of=AS_OF)["status"] == "unavailable"
    assert te.classify_response(window, resp(), expected_directions=down,
                                as_of="2026-10-21T12:00:00Z")["status"] == "pending"
    assert te.classify_response(window, resp(qualified=False),
                                expected_directions=down,
                                as_of=AS_OF)["status"] == "unavailable"
    assert te.classify_response(
        window, resp(wstart="2026-10-20T00:00:00Z"), expected_directions=down,
        as_of=AS_OF)["status"] == "ineligible"
    assert te.classify_response(
        window, resp(wend="2026-10-23T20:00:00Z"), expected_directions=down,
        as_of=AS_OF)["status"] == "ineligible"
    assert te.classify_response(
        window, resp(label="within_reference_range", direction=None),
        expected_directions=down, as_of=AS_OF)["status"] == "absent"
    assert te.classify_response(window, resp(direction="down"),
                                expected_directions=down,
                                as_of=AS_OF)["status"] == "responded_consistent"
    assert te.classify_response(window, resp(direction="up"),
                                expected_directions=down,
                                as_of=AS_OF)["status"] == "responded_inconsistent"
    assert te.classify_response(window, resp(direction="up"),
                                expected_directions=both,
                                as_of=AS_OF)["status"] == \
        "responded_direction_not_assessed"
    out = te.classify_response(window, resp(receiver="us_credit",
                                            family="rates_credit"),
                               expected_directions=down, as_of=AS_OF)
    assert out == {"receiver_id": "us_credit", "status": "responded_consistent",
                   "evidence_family": "rates_credit", "receipt_ref": "resp:fixture"}


# ==========================================================================
# T10
# ==========================================================================

def test_causal_language_scan():
    assert te.scan_causal_language(te.load_channels()) == []
    ceilings = {}
    for stage, (en, zh) in te.LANGUAGE_CEILINGS.items():
        ceilings[f"ceiling.{stage}.summary_en"] = en
        ceilings[f"ceiling.{stage}.summary_zh"] = zh
    assert te.scan_causal_language(ceilings) == []

    edge = doc_edge()
    shown = build_jp_event(edges=[dy_edge()], responses=[resp()],
                           factors=(), regional=())
    assert te.scan_causal_language(shown["language_ceiling_en"]) == []
    assert shown["language_ceiling_en"] == \
        te.LANGUAGE_CEILINGS[shown["us_response_stage"]][0]
    summary = te.summarize_event(shown)
    assert te.scan_causal_language(summary) == []
    favored = build_jp_event(edges=[dy_edge()],
                             responses=[resp(), resp(receiver="us_credit",
                                                     family="rates_credit")],
                             factors=rs_favored(), regional=rs("KR", "GB"))
    assert favored["attribution"] == "common_global_shock_favored"
    assert te.scan_causal_language(te.summarize_event(favored)) == []
    assert te.scan_causal_language(favored) == []

    planted = {"x": {"summary_en": "The move drove US shares lower."},
               "y": {"summary_zh": "压力导致下跌。"},
               "z": {"definition_en": "a contagion from abroad read"}}
    hits = te.scan_causal_language(planted)
    assert "x.summary_en" in hits
    assert "y.summary_zh" in hits
    assert "z.definition_en" in hits


def rs_favored():
    return gf("broad_usd", "us_rates")


# ==========================================================================
# T11
# ==========================================================================

def test_missing_data_non_improvement():
    doc_shown = te.build_edge(
        origin_market="JP", receiver="us_broad_equity",
        channel="dollar_funding", pathway="documented_exposure",
        model_status="documented_source", source_id="bis.statistics",
        measure_id="cross_border_usd_claims", units="usd_bn",
        interpretation_en="Cross-border USD claims of reporting banks on the market.",
        interpretation_zh="报告银行对该市场的跨境美元债权。",
        evidence_family="funding", as_of="2026-09-30",
        denominator="reporting_bank_usd_claims",
        exposure_kind="direct_financial_claims", amount=12.5,
        coverage_state="qualified", coverage_basis="synthetic",
        matrix=SHOWN_MATRIX)

    full = build_jp_event(edges=[doc_shown], responses=[resp()],
                          indicators=[ind(uid="JP-IDX"),
                                     ind("fx_spot_return", uid="USDJPY")],
                          factors=rs_favored(), regional=())
    competitor = build_jp_event(
        obs=make_observation("JP", window_end="2026-10-19T15:00:00Z",
                             window_start="2026-10-16T15:00:00Z"),
        indicators=[ind(uid="JP-IDX")], label="within_reference_range")

    def components(event):
        row = te.us_relevance_order([event, competitor])
        return {k: v["value"] for k, v in
                next(r for r in row if r["event_id"] == event["event_id"])
                ["components"].items()}

    def position(event):
        rows = te.us_relevance_order([event, competitor])
        return [r["event_id"] for r in rows].index(event["event_id"])

    full_comps = components(full)
    full_pos = position(full)

    fewer_indicators = build_jp_event(
        edges=[doc_shown], responses=[resp()], indicators=[ind(uid="JP-IDX")],
        factors=rs_favored(), regional=())
    no_documented_edge = build_jp_event(
        edges=[], responses=[resp()],
        indicators=[ind(uid="JP-IDX"), ind("fx_spot_return", uid="USDJPY")],
        factors=rs_favored(), regional=())
    no_response = build_jp_event(
        edges=[doc_shown], responses=[],
        indicators=[ind(uid="JP-IDX"), ind("fx_spot_return", uid="USDJPY")],
        factors=rs_favored(), regional=())
    no_factors = build_jp_event(
        edges=[doc_shown], responses=[resp()],
        indicators=[ind(uid="JP-IDX"), ind("fx_spot_return", uid="USDJPY")],
        factors=[], regional=())

    for reduced in (fewer_indicators, no_documented_edge, no_response,
                    no_factors):
        comps = components(reduced)
        for name, value in comps.items():
            assert value <= full_comps[name], (name, comps, full_comps)
        assert position(reduced) >= full_pos

    empty_factors_status = te.common_shock_status(
        origin_market="JP", origin_session="2026-10-21",
        global_factors=[], regional_stress=rs("KR", "GB"))["status"]
    assert empty_factors_status == "live"


# ==========================================================================
# T12
# ==========================================================================

def test_im15_label_alignment():
    import engine.intl_global_dislocation as dislocation
    assert te.STRESS_LABELS == dislocation.ATTENTION_LABELS


# ==========================================================================
# T13
# ==========================================================================

def test_engine_imports_no_frozen_model():
    src = (ROOT / "engine" / "intl_transmission_evidence.py").read_text(
        encoding="utf-8")
    modules = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    forbidden_exact = {
        "engine.contagion", "engine.contagion_links", "engine.risk_radar",
        "engine.risk_radar_intl", "engine.intl_global_dislocation",
        "engine.intl_global_dollar_credit", "engine.global_liquidity_transmission",
        "lib.store", "pandas", "numpy"}
    for m in modules:
        assert m not in forbidden_exact, m
        assert not m.startswith("engine.contagion"), m
        assert not m.startswith("engine.risk_radar"), m
    out = subprocess.run(
        [sys.executable, "-c",
         "import engine.intl_transmission_evidence, sys; "
         "print(sorted(m for m in sys.modules if m.startswith('engine.contagion')))"],
        cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]", out.stdout


# ==========================================================================
# T14
# ==========================================================================

def _fingerprint():
    import numpy as np
    import engine.contagion_links as cl
    import engine.contagion as c
    rs_ = np.random.RandomState(20261021)
    Y = rs_.standard_normal((150, 14)) * 0.01
    Amat, Sigma = c._fit_var(Y, c._DY_VAR_LAG)
    Phi = c._var_to_ma(Amat, c._DY_VAR_LAG, c._DY_HORIZON)
    theta = c._gfevd(Phi, Sigma, c._DY_HORIZON)
    dy = c._dy_connectedness(theta)
    payload = {
        "markets": cl.MARKETS,
        "structural_version": cl.STRUCTURAL_VERSION,
        "s_raw": cl._S_RAW,
        "built": np.round(cl._build_structural(), 12).tolist(),
        "structural": np.round(cl._STRUCTURAL, 12).tolist(),
        "etf_basket": c._ETF_BASKET,
        "dy_window": c._DY_WINDOW,
        "dy_var_lag": c._DY_VAR_LAG,
        "dy_horizon": c._DY_HORIZON,
        "dy": {"total": round(dy["total"], 10),
               "to_others": [round(v, 10) for v in dy["to_others"]],
               "from_others": [round(v, 10) for v in dy["from_others"]],
               "own_share": [round(v, 10) for v in dy["own_share"]]},
    }
    return _sha(_cj(payload))


GRAPH_MARKETS = ["US", "CN", "HK", "CA", "KR", "JP", "TW", "IN", "AU", "GB", "EZ"]


def test_frozen_model_invariance_under_twelfth_market():
    import engine.contagion_links as cl
    import engine.contagion as c
    doc = te.load_channels()
    assert doc["structural_graph"]["markets"] == cl.MARKETS
    assert doc["structural_graph"]["structural_version"] == cl.STRUCTURAL_VERSION
    assert doc["statistical_model"]["etf_basket"] == c._ETF_BASKET
    assert doc["statistical_model"]["model_id"] == "contagion_dy_var_14etf"

    fp0 = _fingerprint()
    board11 = te.build_board(market_ids=GRAPH_MARKETS, edges=[],
                             observations=[], events=[], as_of=AS_OF)
    fp1 = _fingerprint()
    board12 = te.build_board(market_ids=GRAPH_MARKETS + ["BR"], edges=[],
                             observations=[], events=[], as_of=AS_OF)
    fp2 = _fingerprint()
    assert fp0 == fp1 == fp2

    summaries11 = {m["market_id"]: _cj(m) for m in board11["markets"]}
    summaries12 = {m["market_id"]: _cj(m) for m in board12["markets"]}
    assert set(summaries12) == set(summaries11) | {"BR"}
    for mid in GRAPH_MARKETS:
        assert summaries11[mid] == summaries12[mid]

    # Pinned RED-time literals (pure-Python data, platform-independent).
    assert _sha(_cj(cl._S_RAW)) == \
        "a919f494a3713c304636fa3cad78814736d77698a191d8357be12f63aeeac19c"
    assert _sha(_cj([cl.MARKETS, cl.STRUCTURAL_VERSION, c._ETF_BASKET,
                     c._DY_WINDOW, c._DY_VAR_LAG, c._DY_HORIZON])) == \
        "d1bea677c41e790f55f89ad3bb344b4de2f2222172f26e3aba4a86bafbcfa21f"


# ==========================================================================
# T15
# ==========================================================================

def test_common_global_shock_is_never_bilateral():
    ev = build_jp_event(
        edges=[doc_edge(), dy_edge()],
        responses=[resp(direction="down"),
                   resp(receiver="us_credit", family="rates_credit",
                        direction="down")],
        factors=rs_favored(), regional=rs("KR", "GB"))
    assert ev["state"] == "qualified"
    assert ev["attribution"] == "common_global_shock_favored"
    common = next(a for a in ev["alternative_explanations"]
                  if a["id"] == "common_global_shock")
    assert common["status"] == "favored"
    assert sorted(common["stressed_markets"]) == ["GB", "JP", "KR"]
    assert common["region_count"] == 2
    assert common["factor_hits"] == ["broad_usd", "us_rates"]
    assert ev["us_response_stage"] != "corroborating"
    summary = te.summarize_event(ev)
    assert "common global shock" in summary["summary_en"]
    for sentence in summary["summary_en"].replace(".", ".\n").split("\n"):
        if "bilateral" in sentence:
            assert "candidate" in sentence
    assert [a["id"] for a in ev["alternative_explanations"]] == \
        ["common_global_shock", "receiver_idiosyncratic"]
    assert te.scan_causal_language(summary) == []
    assert te.scan_causal_language(ev) == []


# ==========================================================================
# T16
# ==========================================================================

def test_three_equity_indicators_are_one_family():
    three = [ind("equity_index_return", uid="U1"),
             ind("equity_etf_return", uid="U2"),
             ind("equity_volatility", uid="U3")]
    assert te.evidence_families(three) == ["equity"]
    shared = [ind("equity_index_return", uid="U1"),
              ind("fx_spot_return", uid="U1")]
    assert te.evidence_families(shared) == ["equity"]
    assert te.evidence_families(shared + [ind("fx_spot_return", uid="U9")]) == \
        ["equity", "fx"]
    with pytest.raises(te.TransmissionError):
        te.evidence_families([ind("not_an_indicator", uid="U0")])

    ev = build_jp_event(indicators=three, edges=[], responses=[])
    assert ev["confidence"]["level"] == "single_family"
    assert ev["confidence"]["independent_family_count"] == 1
    row = te.us_relevance_order([ev])[0]
    assert row["components"]["independent_breadth"]["value"] == 1


# ==========================================================================
# T17
# ==========================================================================

def test_out_of_graph_market_has_no_graph_score():
    br_doc = doc_edge(origin="BR", channel="sovereign_banking",
                      evidence_family="rates_credit",
                      measure_id="us_bank_consolidated_claims",
                      denominator="us_reporting_bank_claims")
    br_dy = dy_edge(origin="BR")
    ms = te.market_summary("BR", edges=[br_doc, br_dy], observations=[])
    assert ms["structural_graph"]["member"] is False
    assert ms["structural_graph"]["state"] == "outside_structural_graph"
    assert ms["structural_graph"]["model_id"] == "contagion_links"
    assert ms["statistical_population"]["member"] is True
    assert ms["statistical_population"]["instrument"] == "EWZ"
    assert ms["display_order"][:2] == ["structural_research",
                                       "qualified_observations"]
    assert ms["display_order"] == ["structural_research",
                                   "qualified_observations",
                                   "statistical_evidence"]
    universe = load_universe()
    br_state = universe["jurisdictions"]["BR"]["capabilities"][
        "equity_index_fx"]["state"]
    assert ms["qualified_observations"]["capability_state"] == br_state == \
        "unavailable"
    assert ms["qualified_observations"]["observation_ids"] == []
    assert [e["edge_id"] for e in ms["structural_research"]] == \
        [br_doc["edge_id"]]
    assert [e["edge_id"] for e in ms["statistical_evidence"]] == \
        [br_dy["edge_id"]]
    assert te.forbidden_keys(ms) == []

    with pytest.raises(te.TransmissionError):
        hyp_edge(origin="BR")

    jp = te.market_summary("JP", edges=[], observations=[make_observation("JP")])
    assert jp["structural_graph"]["member"] is True
    assert jp["structural_graph"]["state"] == "member"
    assert jp["display_order"] == ["qualified_observations",
                                   "structural_research",
                                   "statistical_evidence", "structural_graph"]


# ==========================================================================
# T18
# ==========================================================================

def test_pathway_labels_survive_summary_round_trip():
    ev = build_jp_event(edges=[doc_edge(), dy_edge()], responses=[resp()])
    summary = te.summarize_event(ev)
    blob = json.loads(json.dumps(summary, ensure_ascii=False))
    te.validate_summary(blob, ev)
    labels = {p["id"]: (p["label_en"], p["label_zh"])
              for p in te.load_channels()["pathways"]}
    for s_edge, e_edge in zip(blob["edges"], ev["channel_evidence"]):
        assert s_edge["pathway"] == e_edge["pathway"]
        assert (s_edge["pathway_label_en"], s_edge["pathway_label_zh"]) == \
            labels[s_edge["pathway"]]
        assert s_edge["model_status"] == e_edge["model_status"]
    assert "directional candidate" in blob["summary_en"]

    tampered = copy.deepcopy(blob)
    for s_edge in tampered["edges"]:
        if s_edge["pathway"] == "statistical_association":
            s_edge["pathway"] = "documented_exposure"
            s_edge["pathway_label_en"] = labels["documented_exposure"][0]
            s_edge["pathway_label_zh"] = labels["documented_exposure"][1]
    with pytest.raises(te.TransmissionError):
        te.validate_summary(tampered, ev)


# ==========================================================================
# T19
# ==========================================================================

def test_us_relevance_order_is_permutation_invariant():
    e1 = build_jp_event(
        edges=[doc_edge(matrix=SHOWN_MATRIX), dy_edge()], responses=[resp()],
        indicators=[ind(uid="U1"), ind("fx_spot_return", uid="U2")],
        persistence=2)

    e2 = te.build_event(
        origin_observation=make_observation("KR"),
        stress=stress_block(indicators=[ind("equity_index_return", uid="KR-U1")]),
        edges=[dy_edge(origin="KR")], responses=[resp(receiver="us_credit",
                                                      family="rates_credit")],
        global_factors=[], regional_stress=[], receiver_sessions=SESSIONS,
        as_of="2026-10-22T21:00:00Z")

    e3 = te.build_event(
        origin_observation=make_observation("GB"),
        stress=stress_block(indicators=[ind("equity_index_return", uid="GB-U1")]),
        edges=[], responses=[], global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of="2026-10-22T21:00:00Z")

    e4 = te.build_event(
        origin_observation=make_observation(
            "JP", window_end="2026-10-19T15:00:00Z",
            window_start="2026-10-16T15:00:00Z"),
        stress=stress_block(label="within_reference_range", indicators=[],
                            persistence=1),
        edges=[], responses=[], global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of="2026-10-22T21:00:00Z")

    e5 = te.build_event(
        origin_observation=make_observation(
            "JP", window_end="2026-10-16T15:00:00Z",
            window_start="2026-10-15T15:00:00Z",
            clocks=make_clocks(pub="2026-10-16T06:00:00Z",
                               obs_at="2026-10-15T15:00:00Z",
                               ing="2026-10-16T06:05:00Z",
                               comp="2026-10-16T06:10:00Z")),
        stress=stress_block(label="within_reference_range", indicators=[],
                            persistence=1),
        edges=[], responses=[], global_factors=[], regional_stress=[],
        receiver_sessions=SESSIONS, as_of="2026-10-22T21:00:00Z")

    events = [e1, e2, e3, e4, e5]
    base = _cj(te.us_relevance_order(events))
    for perm in itertools.permutations(events):
        assert _cj(te.us_relevance_order(list(perm))) == base

    rows = te.us_relevance_order(events)
    assert [r["rank"] for r in rows] == [1, 2, 3, 4, 5]
    assert rows[0]["ordering_rule"] == te.ORDERING_RULE
    assert rows[0]["market_id"] == "JP"
    assert rows[0]["event_id"] == e1["event_id"]
    # The tied pair (e4, e5: same components, same market) breaks on event_id.
    tail_ids = [r["event_id"] for r in rows[3:]]
    assert tail_ids == sorted(tail_ids)
    assert set(tail_ids) == {e4["event_id"], e5["event_id"]}
    for row in rows:
        for name in row["components"]:
            assert isinstance(row["components"][name]["value"], int)
    assert te.forbidden_keys(rows) == []
    blob = json.dumps(rows)
    assert "score" not in [k for k in _flat_keys(rows)]


def _flat_keys(node, prefix=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{prefix}.{k}" if prefix else str(k)
            yield from _flat_keys(v, k)
    elif isinstance(node, list):
        for item in node:
            yield from _flat_keys(item, prefix)


# ==========================================================================
# T20
# ==========================================================================

EVENT_KEYS = {
    "contract_version", "event_id", "state", "abstain_reasons", "origin",
    "first_qualified_at", "affected_markets", "origin_stage",
    "channel_evidence", "receivers", "us_response_stage", "attribution",
    "alternative_explanations", "severity", "confidence", "coverage",
    "revision", "as_of", "language_ceiling_en", "language_ceiling_zh"}


def _assert_abstain(ev, reason):
    assert ev["state"] == "abstain"
    assert ev["abstain_reasons"] == [reason]
    assert reason in te.EVENT_ABSTAIN_REASONS
    assert ev["us_response_stage"] == "not_assessed"
    assert set(ev) == EVENT_KEYS
    assert ev["severity"]["tier"] == "none"
    assert ev["confidence"]["level"] == "insufficient"
    assert ev["channel_evidence"] == []


def test_event_abstains_with_closed_reasons():
    unqualified = make_observation("JP", qualified=False)
    ev = build_jp_event(obs=unqualified)
    _assert_abstain(ev, "origin_not_qualified")

    us_obs = make_observation("JP")
    us_obs["identity"]["universe_id"] = "US"
    ev = build_jp_event(obs=us_obs)
    _assert_abstain(ev, "origin_is_receiver")

    broken = make_observation("JP")
    broken["clocks"]["ingestion"]["at"] = "2026-10-20T00:00:00Z"
    ev = build_jp_event(obs=broken)
    _assert_abstain(ev, "clock_order_violation")

    ev = build_jp_event(label=None, indicators=[ind()])
    _assert_abstain(ev, "stress_unqualified")

    ev = build_jp_event()
    ev = te.build_event(
        origin_observation=make_observation("JP"),
        stress=stress_block(), edges=[], responses=[],
        global_factors=[], regional_stress=[], receiver_sessions=[],
        as_of=AS_OF)
    _assert_abstain(ev, "no_receiver_sessions")


# ==========================================================================
# T21
# ==========================================================================

def test_corroborating_requires_independent_families():
    one_family = build_jp_event(edges=[dy_edge()], responses=[resp()],
                                indicators=[ind(uid="U1")])
    assert one_family["confidence"]["level"] == "single_family"
    assert one_family["us_response_stage"] == "mixed"

    two_families = build_jp_event(
        edges=[dy_edge()], responses=[resp()],
        indicators=[ind(uid="U1"), ind("fx_spot_return", uid="U2")])
    assert two_families["confidence"]["level"] == "independent_families"
    assert two_families["us_response_stage"] == "corroborating"
    assert two_families["attribution"] == "bilateral_channel_candidate"

    favored = build_jp_event(
        edges=[dy_edge()], responses=[resp()],
        indicators=[ind(uid="U1"), ind("fx_spot_return", uid="U2")],
        factors=rs_favored(), regional=rs("KR", "GB"))
    assert favored["attribution"] == "common_global_shock_favored"
    assert favored["us_response_stage"] != "corroborating"
    assert favored["us_response_stage"] == "mixed"
