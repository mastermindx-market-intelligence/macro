"""Adversarial point-in-time, quote-order and correction fixtures; no vendor calls."""

from copy import deepcopy

import pytest

from engine.market_microstructure.pressure_response import measure_window, SCHEMA


def q(name, t, *, available=None, bid="100", ask="101", bs=500, az=1000, bx="N", ax="Q"):
    return {"id": name, "ticker": "SPY", "session": "2026-10-08:RTH",
            "sip_ns": t, "available_ns": t + 1 if available is None else available,
            "bid": bid, "ask": ask, "bid_size": bs, "ask_size": az,
            "bid_exchange": bx, "ask_exchange": ax, "source_receipt": "q:" + name}


def t(name, stamp, *, price="100.9", size=10, available=None, venue="LIT",
      revision=0, action="ORIGINAL", eligible=True):
    return {"id": name, "ticker": "SPY", "session": "2026-10-08:RTH",
            "sip_ns": stamp, "available_ns": stamp + 1 if available is None else available,
            "price": price, "size": size, "revision": revision, "action": action,
            "eligible_for_pressure": eligible, "eligibility_rules_ref": "conditions@hash-1",
            "venue_class": venue, "source_receipt": name + ":r" + str(revision)}


def payload(*, trades=None, quotes=None, **overrides):
    args = {"ticker": "SPY", "session": "2026-10-08:RTH", "start_ns": 100,
            "end_ns": 300, "decision_ns": 400, "watermark_ns": 350,
            "watermark_seen_ns": 350, "watermark_receipt": "wm:sha256:real",
            "source_manifest": "source:qualified:sha256", "evidence_mode": "ACTUAL_AS_SEEN",
            "max_quote_age_ns": 200,
            "trades": [t("buy", 130), t("sell", 180, price="100.1")]
            if trades is None else trades,
            "quotes": [q("start", 90), q("dip", 120, az=400),
                       q("recover", 170, az=900)] if quotes is None else quotes}
    args.update(overrides)
    return args


def measure(**args):
    return measure_window(**payload(**args))


def test_qualified_buy_sell_pressure_and_ask_size_recovery():
    result = measure()
    assert result["schema"] == SCHEMA
    assert result["state"] == "MEASURED"
    assert result["authority"] == "RESEARCH_ONLY"
    assert result["buy_proxy_notional_usd"] == "1009.0"
    assert result["sell_proxy_notional_usd"] == "1001.0"
    assert result["unknown_notional_usd"] == "0"
    assert result["pressure_balance"].startswith("0.0039800995")
    assert result["classified_notional_coverage"] == "1"
    assert result["midpoint_response_bps"] == "0"
    assert result["ask_size_recovery"]["state"] == "MEASURED_PROXY"
    assert result["ask_size_recovery"]["depletion_shares"] == 600
    assert result["ask_size_recovery"]["recovered_shares"] == 500
    assert result["absorption_signal"] is None
    assert {p["side_proxy"] for p in result["print_diagnostics_private_only"]} == {
        "BUY_PROXY", "SELL_PROXY"}


def test_window_not_mature_when_event_watermark_lags():
    r = measure(watermark_ns=299)
    assert r["state"] == "NOT_MATURE"
    assert "pressure_balance" not in r


def test_window_not_mature_when_decision_precedes_end():
    r = measure(decision_ns=299, watermark_seen_ns=290, watermark_ns=290)
    assert r["state"] == "NOT_MATURE"


def test_future_watermark_receipt_rejected():
    with pytest.raises(ValueError, match="future watermark"):
        measure(watermark_seen_ns=401)


def test_quote_arrives_after_decision_and_cannot_enter_as_seen_join():
    qs = [q("old", 90), q("late", 120, available=401, bid="100", ask="101")]
    result = measure(trades=[t("only", 130)], quotes=qs)
    assert result["print_diagnostics_private_only"][0]["quote_id"] == "old"


def test_same_timestamp_quote_cannot_be_ordered_against_trade():
    qs = [q("old", 90), q("tied", 130)]
    result = measure(trades=[t("only", 130)], quotes=qs)
    assert result["print_diagnostics_private_only"][0]["reason"] == "CLOCK_TIE"
    assert result["pressure_balance"] is None


def test_same_timestamp_multiple_prior_quotes_cannot_be_ordered():
    qs = [q("q1", 120), q("q2", 120)]
    result = measure(trades=[t("only", 130)], quotes=qs)
    assert result["print_diagnostics_private_only"][0]["reason"] == "AMBIGUOUS_QUOTE_ORDER"


def test_locked_quote_blocks_reuse_of_older_valid_quote():
    qs = [q("old", 90), q("locked", 120, bid="100", ask="100")]
    result = measure(trades=[t("only", 130)], quotes=qs)
    assert result["print_diagnostics_private_only"][0]["reason"] == "INVALID_NBBO"


def test_stale_quote_abstains():
    result = measure(trades=[t("only", 250)], quotes=[q("old", 1)], max_quote_age_ns=200)
    assert result["print_diagnostics_private_only"][0]["reason"] == "STALE_NBBO"


def test_midpoint_and_outside_prints_are_ambiguous():
    res = measure(trades=[t("mid", 130, price="100.5"), t("outer", 180, price="102")])
    assert res["n_unclassified"] == {"MIDPOINT_AMBIGUOUS": 1, "OUTSIDE_NBBO": 1}
    assert res["classified_notional_coverage"] == "0"
    assert res["pressure_balance"] is None


def test_trf_must_not_be_mixed_with_lit_quote_pressure():
    res = measure(trades=[t("trf", 130, venue="TRF")])
    assert res["n_unclassified"] == {"OFF_EXCHANGE_OR_UNKNOWN_VENUE": 1}
    assert res["unknown_notional_usd"] == "1009.0"


def test_condition_ineligible_is_excluded_not_signed_neutral():
    res = measure(trades=[t("no", 130, eligible=False)])
    assert res["state"] == "NO_ELIGIBLE_PRINTS"
    assert res["n_excluded_revisions_or_conditions"] == {"CONDITION_INELIGIBLE": 1}
    assert res["gross_active_notional_usd"] == "0"
    assert res["pressure_balance"] is None


def test_corrected_trade_only_restates_after_actual_correction_arrival():
    original = t("same", 130, size=10)
    revised = t("same", 130, size=20, revision=1, action="REPLACE", available=501)
    early = measure(trades=[original, revised], decision_ns=400)
    later = measure(trades=[original, revised], decision_ns=600)
    assert early["buy_proxy_notional_usd"] == "1009.0"
    assert later["buy_proxy_notional_usd"] == "2018.0"
    assert early["print_diagnostics_private_only"][0]["revision"] == 0
    assert later["print_diagnostics_private_only"][0]["revision"] == 1


def test_later_cancel_does_not_erase_earlier_decision():
    original = t("same", 130)
    cancelled = t("same", 130, revision=1, action="CANCEL", available=501)
    early = measure(trades=[original, cancelled], decision_ns=400)
    later = measure(trades=[original, cancelled], decision_ns=600)
    assert early["n_active_prints"] == 1
    assert later["state"] == "NO_ELIGIBLE_PRINTS"
    assert later["n_excluded_revisions_or_conditions"] == {"CANCELLED_AS_OF": 1}


def test_orphan_correction_cannot_create_original():
    orphan = t("same", 130, revision=1, action="REPLACE")
    res = measure(trades=[orphan])
    assert res["state"] == "NO_ELIGIBLE_PRINTS"
    assert res["n_excluded_revisions_or_conditions"] == {"UNRESOLVED_ORIGINAL": 1}


def test_duplicate_trade_revision_is_idempotent_but_conflict_rejected():
    original = t("only", 130)
    assert measure(trades=[original, deepcopy(original)])["n_active_prints"] == 1
    wrong = dict(original, size=999)
    with pytest.raises(ValueError, match="conflicting duplicate trade"):
        measure(trades=[original, wrong])


def test_nonmonotone_correction_availability_rejected():
    original = t("only", 130, available=250)
    bad = t("only", 130, revision=1, action="REPLACE", available=240)
    with pytest.raises(ValueError, match="nonmonotone"):
        measure(trades=[original, bad])


def test_venue_change_invalidates_order_replenishment_interpretation():
    qs = [q("base", 90), q("down", 120, az=400),
          q("changed", 170, az=900, ax="other")]
    res = measure(quotes=qs)
    assert res["ask_size_recovery"] == {
        "state": "UNKNOWN", "reason": "BEST_PRICE_OR_VENUE_CHANGED"}


def test_missing_venue_blocks_replenishment_proxy():
    qs = [q("base", 90, ax=None), q("down", 120, az=400, ax=None),
          q("up", 170, az=900, ax=None)]
    res = measure(quotes=qs)
    assert res["ask_size_recovery"]["reason"] == "VENUE_UNOBSERVED"


def test_missing_endpoint_midpoint_does_not_invent_price_response():
    res = measure(quotes=[q("old", 10)], max_quote_age_ns=100)
    assert res["midpoint_response_bps"] is None
    assert res["response_null_reason"]["end"] == "STALE_NBBO"


def test_invalid_or_missing_condition_decision_rejected():
    trade = t("only", 130)
    del trade["eligible_for_pressure"]
    with pytest.raises(ValueError, match="condition eligibility"):
        measure(trades=[trade])


def test_sip_timestamp_precision_cannot_be_fabricated_from_float():
    trade = t("only", 130)
    trade["sip_ns"] = 130.0
    with pytest.raises(ValueError, match="nonnegative integer"):
        measure(trades=[trade])


def test_conflicting_quote_identity_rejected():
    a = q("same", 120)
    b = q("same", 170)
    with pytest.raises(ValueError, match="conflicting duplicate NBBO"):
        measure(quotes=[q("base", 90), a, b])


def test_quotes_need_real_source_receipts():
    quote = q("only", 90)
    del quote["source_receipt"]
    with pytest.raises(ValueError, match="quote.source_receipt"):
        measure(quotes=[quote])


def test_mixed_evidence_mode_requires_explicit_supported_label():
    with pytest.raises(ValueError, match="unrecognized evidence mode"):
        measure(evidence_mode="REAL_TIME_BRO")
    res = measure(evidence_mode="FINAL_VINTAGE")
    assert res["evidence_mode"] == "FINAL_VINTAGE"
    assert res["authority"] == "RESEARCH_ONLY"


def test_mixed_condition_policy_versions_fail_closed():
    a, b = t("a", 130), t("b", 180)
    b["eligibility_rules_ref"] = "conditions@hash-2"
    with pytest.raises(ValueError, match="mixed trade-condition policies"):
        measure(trades=[a, b])


def test_future_bad_quote_does_not_poison_earlier_snapshot():
    future_bad = q("future", 125, available=501)
    future_bad["bid_size"] = "malformed"
    earlier = measure(quotes=[q("old", 90), q("dip", 120, az=400), future_bad])
    assert earlier["n_active_prints"] == 2


def test_future_correction_condition_ref_does_not_invalidate_old_snapshot():
    original = t("stable", 130)
    future = t("stable", 130, available=501, revision=1, action="REPLACE")
    future["eligibility_rules_ref"] = "conditions@future-not-known"
    early = measure(trades=[original, future], decision_ns=400)
    assert early["condition_policy_refs"] == ["conditions@hash-1"]
    assert early["buy_proxy_notional_usd"] == "1009.0"


def test_unknown_correction_generation_quarantined_only_after_known():
    original = t("rev", 130)
    rev2 = t("rev", 130, revision=2, action="REPLACE", available=501)
    early = measure(trades=[original, rev2], decision_ns=400)
    late = measure(trades=[original, rev2], decision_ns=600)
    assert early["n_active_prints"] == 1
    assert late["n_excluded_revisions_or_conditions"] == {"MISSING_CORRECTION_GENERATION": 1}


def test_ambiguous_same_time_quote_recovery_is_unknown():
    qs = [q("old", 90), q("drop", 120, az=300),
          q("tie", 120, az=350), q("up", 170, az=900)]
    res = measure(quotes=qs)
    assert res["ask_size_recovery"]["reason"] == "AMBIGUOUS_QUOTE_ORDER"


def test_stale_recovery_endpoint_abstains_despite_earlier_depletion():
    qs = [q("old", 90), q("drop", 120, az=400), q("up", 130, az=900)]
    res = measure(trades=[t("only", 121)], quotes=qs, max_quote_age_ns=100)
    assert res["ask_size_recovery"]["reason"] == "STALE_RECOVERY_ENDPOINT"


def test_source_watermark_cannot_be_observed_before_its_event_time():
    with pytest.raises(ValueError, match="watermark receipt precedes"):
        measure(watermark_seen_ns=340)


def test_out_of_window_condition_and_trade_are_not_in_window_denominator():
    outside = t("outside", 350, eligible=False)
    outside["eligibility_rules_ref"] = "unrelated-new-rule"
    res = measure(trades=[t("inside", 130), outside])
    assert res["n_excluded_revisions_or_conditions"] == {}
    assert res["condition_policy_refs"] == ["conditions@hash-1"]
    assert res["n_active_prints"] == 1


def test_cross_window_correction_chain_keeps_consistent_asof_scope():
    original = t("moving", 130)
    replacement = t("moving", 330, revision=1, action="REPLACE", available=370)
    early = measure(trades=[original, replacement], decision_ns=350, watermark_seen_ns=350)
    later = measure(trades=[original, replacement], decision_ns=400)
    assert early["n_active_prints"] == 1
    assert later["n_active_prints"] == 0


def test_zero_bid_size_quote_is_unusable_for_classification():
    qs = [q("previous", 90), q("no_firm_bid", 120, bs=0)]
    obs = measure(trades=[t("only", 130)], quotes=qs)
    assert obs["n_unclassified"] == {"INVALID_NBBO": 1}
    assert obs["pressure_balance"] is None
    assert obs["midpoint_response_bps"] is None


def test_zero_ask_size_quote_is_unusable_for_classification():
    qs = [q("previous", 90), q("no_firm_ask", 120, az=0)]
    obs = measure(trades=[t("only", 130)], quotes=qs)
    assert obs["n_unclassified"] == {"INVALID_NBBO": 1}
    assert obs["ask_size_recovery"]["reason"] == "INVALID_INTERVENING_NBBO"


# Matured response labels are OUTCOMES ONLY, never original live features.
from decimal import Decimal
from engine.market_microstructure.matured_response import measure_matured_response


def label_payload(**overrides):
    data = dict(
        ticker="SPY", session="2026-10-08:RTH",
        original_decision_ns=140, anchor_ns=130, label_end_ns=200,
        evaluation_cutoff_ns=300,
        source_watermark_ns=205, watermark_received_ns=230,
        watermark_receipt="later-tq-watermark-v1",
        source_manifest="source:original:record",
        source_mode="ACTUAL_AS_SEEN",
        max_quote_age_ns=100, market_health="NORMAL",
        market_health_receipt="market-health-original",
        quotes=[q("anchor",120,available=121),
                q("future",190,bid="102",ask="103",available=220)],
    )
    data.update(overrides)
    return data


def label(**overrides):
    return measure_matured_response(**label_payload(**overrides))


def test_matured_response_produces_evaluation_only():
    o=label()
    assert o["state"]=="MATURED_EVALUATION_LABEL"
    expected=(Decimal("102.5")/Decimal("100.5")-1)*10000
    assert Decimal(o["midpoint_response_bps"])==expected
    assert o["authority"]=="RESEARCH_OUTCOME_LABEL_ONLY"
    assert o["label_first_knowable_ns"]==230
    assert o["forward_label_not_available_to_original_decision"] is True
    assert o["absorption_signal"] is None and o["trade_fill"] is None
    assert o["execution_adjusted_return"] is None


def test_future_label_does_not_exist_before_horizon():
    r=label(evaluation_cutoff_ns=199)
    assert r["state"]=="NOT_MATURE"
    assert "midpoint_response_bps" not in r


def test_unmatured_watermark_never_imputes_forward_response():
    r=label(source_watermark_ns=199)
    assert r["state"]=="NOT_MATURE"
    assert "midpoint_response_bps" not in r


def test_watermark_after_evaluation_not_known():
    r=label(watermark_received_ns=301)
    assert r["state"]=="NOT_MATURE"


def test_late_anchor_quote_cannot_retroactively_be_original_decision():
    r=label(quotes=[q("anchor",120,available=150),
                    q("future",190,bid="102",ask="103",available=220)])
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["anchor"]=="NO_PRIOR_QUOTE"


def test_future_quote_after_label_evaluation_not_available():
    r=label(max_quote_age_ns=50, quotes=[q("anchor",120),q("late",190,bid="102",ask="103",available=310)])
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["forward"]=="STALE_NBBO"


def test_future_malformed_quote_does_not_poison_earlier_outcome():
    future_bad=q("revision",195,bid="invalid",available=500)
    result=label(quotes=[q("anchor",120),q("future",190,bid="102",ask="103",
                               available=220),future_bad])
    assert result["state"]=="MATURED_EVALUATION_LABEL"


def test_locked_quote_blocks_stale_earlier_good_quote():
    r=label(quotes=[q("anchor",120),
                    q("future",180,bid="102",ask="103",available=220),
                    q("locked",195,bid="103",ask="103",available=230)])
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["forward"]=="INVALID_NBBO"


def test_tie_at_forward_endpoint_is_unorderable():
    r=label(quotes=[q("anchor",120),q("future",200,bid="102",ask="103",available=220)])
    assert r["reason"]["forward"]=="CLOCK_TIE"


def test_multiple_latest_quotes_at_same_sip_time_abstain():
    r=label(quotes=[q("anchor",120),q("future1",190,bid="102",ask="103",
                                  available=220),
                    q("future2",190,bid="103",ask="104",available=221)])
    assert r["reason"]["forward"]=="AMBIGUOUS_QUOTE_ORDER"


def test_halt_or_unknown_market_status_censors_endpoint():
    for x in ("HALTED","UNKNOWN"):
        r=label(market_health=x)
        assert r["state"]=="CENSORED"
        assert "midpoint_response_bps" not in r


def test_stale_forward_endpoint_not_carried_as_executable_price():
    r=label(max_quote_age_ns=5)
    assert r["reason"]["forward"]=="STALE_NBBO"
    assert "midpoint_response_bps" not in r


def test_final_vintage_remains_exploratory_not_as_seen():
    r=label(source_mode="FINAL_VINTAGE")
    assert r["source_mode"]=="FINAL_VINTAGE"
    assert r["authority"]=="RESEARCH_OUTCOME_LABEL_ONLY"


def test_future_label_retains_private_source_receipts():
    r=label()
    assert r["quote_receipts_private_only"]=={"anchor":"q:anchor","label":"q:future"}
    assert r["source_quality"]=="REQUIRES_ORIGINAL_SOURCE_OWNER_PROOF"


def test_invalid_time_and_quote_session_are_refused():
    with pytest.raises(ValueError,match="invalid original decision"):
        label(original_decision_ns=120)
    wrong=q("future",190,bid="102",ask="103")
    wrong["ticker"]="QQQ"
    with pytest.raises(ValueError,match="symbol/session"):
        label(quotes=[q("anchor",120),wrong])


def test_unrecognized_source_mode_rejected():
    with pytest.raises(ValueError,match="unrecognized source mode"):
        label(source_mode="LIVE_TODAY")

from engine.market_microstructure.tp1_context import (
    project_tp1_pressure_context, TP1ContextRefusal, MINUTE_NS as TP1_MINUTE_NS,
)

TP1_START=1_791_417_600_000_000_000
TP1_START-=TP1_START%TP1_MINUTE_NS
TP1_END=TP1_START+TP1_MINUTE_NS
TP1_CUT=TP1_END+10_000_000_000
TP1_SHA="a"*64
TP1_EXCHANGE_SHA="b"*64
TP1_QUOTE_POLICY_SHA="c"*64
TP1_WATERMARK="source-owner:contiguous-tq-window-123"


def tp1_minute(start=TP1_START, *, buy="1000", sell="500", mid="100",
               unknown="200", ineligible="100", trf="100"):
    from decimal import Decimal as D
    gross=sum(map(D,(buy,sell,mid,unknown,ineligible)))
    return {
        "schema":"equity.tick_plane.minute_observation/v0",
        "authority":"OBSERVATIONAL_PROVISIONAL_ONLY",
        "ticker":"SPY","session":"2026-10-08:RTH",
        "start_ns":start,"end_ns":start+TP1_MINUTE_NS,
        "decision_ns":start+TP1_MINUTE_NS+1_000_000_000,
        "source_complete_through_ns":start+TP1_MINUTE_NS,
        "watermark_available_ns":start+TP1_MINUTE_NS+500_000_000,
        "original_latest_available_ns":start+TP1_MINUTE_NS-500_000_000,
        "source_watermark_receipt":TP1_WATERMARK,
        "source_mode":"ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS",
        "correction_status":"STREAM_PROVISIONAL_UNRECONCILED",
        "state":"PROVISIONAL_MEASURED_CONTEXT",
        "absorption_signal":None,"rank_or_trade_authority":False,
        "market_capture_coverage":None,
        "condition_rules_ref":TP1_SHA,
        "exchange_reference_sha256":TP1_EXCHANGE_SHA,
        "source_observation_sha256":"d"*64,
        "n_sampled_prints":10,"n_unclassified":2,
        "gross_sampled_notional_usd":str(gross),
        "buy_proxy_notional_usd":buy,
        "sell_proxy_notional_usd":sell,
        "midpoint_notional_usd":mid,
        "unknown_notional_usd":unknown,
        "ineligible_notional_usd":ineligible,
        "trf_gross_notional_usd":trf,
    }


def tp1_source_q(name, stamp, *, bid="100", ask="101", bs=100, az=200,
                 available=None, bx=11, ax=12, valid=True):
    if available is None:
        available=stamp+1_000_000
    return {
        "schema":"equity.tick_plane.stream_event/v0",
        "source":"MASSIVE_STOCKS_SIP_WS",
        "ticker":"SPY","session":"2026-10-08:RTH","event_type":"Q",
        "quote_id":name,"sip_timestamp_ns":stamp,
        "original_frame_received_ns":available,
        "bid":bid,"ask":ask,"bid_size":bs,"ask_size":az,
        "bid_exchange":bx,"ask_exchange":ax,
        "source_frame_sha256":"e"*64,"source_receipt_id":"original-frame:"+name,
        "frame_event_index":0,"valid_firm_nbbo":valid,
        "correction_status":"STREAM_PROVISIONAL_UNRECONCILED",
    }


def tp1_quotes():
    return [
        tp1_source_q("before",TP1_START-10_000_000_000),
        tp1_source_q("within",TP1_START+15_000_000_000,bs=90,az=100),
        tp1_source_q("ending",TP1_END-5_000_000_000,bs=110,az=190),
    ]


def tp1_proofs(quotes):
    return {
        x["quote_id"]:{
            "quote_id":x["quote_id"],"source_frame_sha256":x["source_frame_sha256"],
            "original_frame_received_ns":x["original_frame_received_ns"],
            "policy_available_ns":x["original_frame_received_ns"]+1000000,
            "rules_sha256":TP1_QUOTE_POLICY_SHA,"eligible":True,
        } for x in quotes
    }


def tp1_args(quotes=None, minute=None, **other):
    qs=tp1_quotes() if quotes is None else quotes
    args=dict(
        ticker="SPY",session="2026-10-08:RTH",
        start_ns=TP1_START,end_ns=TP1_END,decision_ns=TP1_CUT,
        watermark_ns=TP1_END,watermark_received_ns=TP1_END+2_000_000_000,
        watermark_receipt=TP1_WATERMARK,source_manifest="TP1:source:private",
        source_completeness_attested=True,max_quote_age_ns=25_000_000_000,
        minute_observations=[tp1_minute()] if minute is None else minute,
        source_quotes=qs,quote_condition_receipts=tp1_proofs(qs),
    )
    args.update(other)
    return args


def tp1_context(**kwargs):
    return project_tp1_pressure_context(**tp1_args(**kwargs))


def test_tp1_bridge_reuses_existing_minute_signs_without_reclassifying_prints():
    out=tp1_context()
    assert out["state"]=="PROVISIONAL_RESEARCH_CONTEXT"
    assert out["authority"]=="RESEARCH_CONTEXT_ONLY"
    assert out["buy_proxy_notional_usd"]=="1000"
    assert out["sell_proxy_notional_usd"]=="500"
    assert out["unknown_notional_usd"]=="200"
    assert out["trf_gross_notional_usd"]=="100"
    assert out["pressure_balance"]==str(Decimal(500)/Decimal(1500))
    assert out["midpoint_response_bps"]=="0"
    assert out["classified_notional_coverage"]==str(Decimal(1500)/Decimal(1900))
    assert out["absorption_signal"] is None
    assert out["forward_outcome_label"] is None
    assert out["source_qualification"]=="EXTERNAL_OWNER_RECEIPTS_REQUIRED"
    assert out["n_source_minute_packets"]==1
    assert out["source_quote_condition_rules_sha256"]==TP1_QUOTE_POLICY_SHA
    assert "trade_id" not in out and "source_quotes" not in out


def test_tp1_quote_exchange_numbers_project_to_research_string_format():
    out=tp1_context()
    assert out["state"]=="PROVISIONAL_RESEARCH_CONTEXT"
    assert out["ask_size_recovery"]["state"]=="MEASURED_PROXY"
    assert out["ask_size_recovery"]["recovered_shares"]==90


def test_tp1_missing_original_completeness_abstains_before_calculation():
    out=tp1_context(source_completeness_attested=False)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert "pressure_balance" not in out


def test_tp1_source_watermark_not_mature():
    out=tp1_context(watermark_ns=TP1_END-1)
    assert out["state"]=="NOT_MATURE"
    assert "midpoint_response_bps" not in out


def test_tp1_provisional_correction_never_promoted_to_final_action():
    out=tp1_context()
    assert out["correction_status"]=="STREAM_PROVISIONAL_UNRECONCILED"
    assert "trade_action" not in out
    assert out["rank_authority"] is False


def test_tp1_missing_quote_policy_receipt_fails_closed():
    out=tp1_context(quote_condition_receipts={})
    assert out["state"]=="QUOTE_REFERENCE_UNQUALIFIED"


def test_tp1_future_quote_condition_receipt_is_not_backfilled():
    data=tp1_args()
    data["quote_condition_receipts"]["before"]["policy_available_ns"]=TP1_CUT+1
    out=project_tp1_pressure_context(**data)
    assert out["state"]=="QUOTE_REFERENCE_UNQUALIFIED"
    assert out["reason"]=="QUOTE_CONDITION_POLICY_NOT_AVAILABLE_AT_DECISION"


def test_tp1_mismatched_original_frame_identity_does_not_qualify():
    data=tp1_args()
    data["quote_condition_receipts"]["before"]["source_frame_sha256"]="f"*64
    out=project_tp1_pressure_context(**data)
    assert out["state"]=="QUOTE_REFERENCE_UNQUALIFIED"


def test_tp1_unknown_quote_condition_never_becomes_firm_liquidity():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["eligible"]=None
    out=project_tp1_pressure_context(**data)
    assert out["state"]=="QUOTE_REFERENCE_UNQUALIFIED"


def test_tp1_nonfirm_latest_quote_blocks_older_valid_midpoint():
    qs=tp1_quotes()
    qs[-1]["valid_firm_nbbo"]=False
    out=tp1_context(quotes=qs)
    assert out["state"]=="PRICE_CONTEXT_UNOBSERVABLE"
    assert out["reason"]["end"]=="INVALID_NBBO"


def test_tp1_quote_after_cutoff_does_not_poison_older_decision():
    qs=tp1_quotes()+[tp1_source_q("future",TP1_END-1_000_000_000,
                                  bid="UNPARSABLE",available=TP1_CUT+1000000)]
    out=tp1_context(quotes=qs)
    assert out["state"]=="PROVISIONAL_RESEARCH_CONTEXT"


def test_tp1_same_sip_timestamp_quotes_abstain_instead_of_ordering_by_id():
    qs=tp1_quotes()+[tp1_source_q("tie",TP1_END-5_000_000_000,
                                  bid="102",ask="103")]
    out=tp1_context(quotes=qs)
    assert out["state"]=="PRICE_CONTEXT_UNOBSERVABLE"
    assert out["reason"]["end"]=="AMBIGUOUS_QUOTE_ORDER"


def test_tp1_quote_source_session_mismatch_is_rejected():
    qs=tp1_quotes()
    qs[0]["ticker"]="QQQ"
    with pytest.raises(TP1ContextRefusal,match="original identity"):
        tp1_context(quotes=qs)


def test_tp1_duplicate_quote_identity_rejected():
    qs=tp1_quotes()+[deepcopy(tp1_quotes()[0])]
    with pytest.raises(TP1ContextRefusal,match="duplicate source quote"):
        tp1_context(quotes=qs)


def test_tp1_two_minute_contiguity_and_policy_consistency():
    minute1=tp1_minute(TP1_START)
    minute2=tp1_minute(TP1_END)
    # First packet retains its own original cutoff; second must mature by the study cutoff.
    window_end=TP1_END+TP1_MINUTE_NS
    cut=window_end+10_000_000_000
    minute2["decision_ns"]=window_end+1_000_000_000
    minute2["watermark_available_ns"]=window_end+500_000_000
    minute2["original_latest_available_ns"]=window_end-500_000_000
    quotes=tp1_quotes()+[tp1_source_q("later",window_end-5_000_000_000,
                                      available=window_end-4_000_000_000)]
    out=tp1_context(minute=[minute1,minute2],quotes=quotes,end_ns=window_end,
                    decision_ns=cut,watermark_ns=window_end,
                    watermark_received_ns=window_end+2_000_000_000,
                    max_quote_age_ns=70_000_000_000)
    assert out["state"]=="PROVISIONAL_RESEARCH_CONTEXT"
    assert out["n_source_minute_packets"]==2
    assert out["buy_proxy_notional_usd"]=="2000"


def test_tp1_gap_in_minute_sequence_is_not_imputed():
    minutes=[tp1_minute(TP1_START),tp1_minute(TP1_END+TP1_MINUTE_NS)]
    with pytest.raises(TP1ContextRefusal,match="gap, duplicate"):
        tp1_context(minute=minutes,end_ns=TP1_END+TP1_MINUTE_NS,
                    decision_ns=TP1_CUT+TP1_MINUTE_NS,
                    watermark_ns=TP1_END+TP1_MINUTE_NS,
                    watermark_received_ns=TP1_END+TP1_MINUTE_NS+2_000_000_000)


def test_tp1_mixed_source_reference_generations_rejected():
    first=tp1_minute(TP1_START)
    nextm=tp1_minute(TP1_END)
    nextm["exchange_reference_sha256"]="f"*64
    window_end=TP1_END+TP1_MINUTE_NS
    nextm["decision_ns"]=window_end+1_000_000_000
    nextm["watermark_available_ns"]=window_end+500_000_000
    nextm["original_latest_available_ns"]=window_end-500_000_000
    with pytest.raises(TP1ContextRefusal,match="mixed condition or exchange"):
        tp1_context(minute=[first,nextm],end_ns=window_end,
                    decision_ns=window_end+10_000_000_000,
                    watermark_ns=window_end,
                    watermark_received_ns=window_end+2_000_000_000)


def test_tp1_wrong_correction_finality_is_not_accepted():
    m=tp1_minute()
    m["correction_status"]="FINAL"
    r=tp1_context(minute=[m])
    assert r["state"]=="MINUTE_NOT_QUALIFIED"


def test_tp1_tampered_notional_denominators_rejected():
    m=tp1_minute()
    m["gross_sampled_notional_usd"]="9999"
    with pytest.raises(TP1ContextRefusal,match="denominators inconsistent"):
        tp1_context(minute=[m])


def test_tp1_stale_quote_context_is_never_carried_to_price_response():
    r=tp1_context(max_quote_age_ns=1_000_000_000)
    assert r["state"]=="PRICE_CONTEXT_UNOBSERVABLE"
    assert r["reason"]["start"]=="STALE_NBBO"


def test_tp1_mixed_quote_policy_generations_rejected():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["rules_sha256"]="f"*64
    r=project_tp1_pressure_context(**data)
    assert r["state"]=="QUOTE_REFERENCE_UNQUALIFIED"
    assert r["reason"]=="MIXED_OR_MISSING_QUOTE_CONDITION_POLICY"


def test_tp1_does_not_support_30_second_windows_with_minute_only_source():
    with pytest.raises(TP1ContextRefusal,match="whole minutes"):
        tp1_context(end_ns=TP1_START+30_000_000_000)


def test_tp1_null_or_nonfinite_signed_notional_rejected():
    m=tp1_minute()
    m["buy_proxy_notional_usd"]="NaN"
    with pytest.raises(TP1ContextRefusal,match="invalid notional"):
        tp1_context(minute=[m])
