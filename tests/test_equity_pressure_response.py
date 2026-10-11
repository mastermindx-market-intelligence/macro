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


def test_research_midpoint_location_preserves_precision_beyond_default_decimal_context():
    # The true midpoint is ...003 but default 28-digit Decimal math rounds
    # it down to 1 and can invert an otherwise legitimate quote location.
    bid = "1.00000000000000000000000000000"
    ask = "1.00000000000000000000000000006"
    price = "1.00000000000000000000000000002"
    r = measure(trades=[t("precision", 130, price=price, size=1)],
                quotes=[q("prior", 90, bid=bid, ask=ask)])
    assert r["print_diagnostics_private_only"][0]["side_proxy"] == "SELL_PROXY"


def test_research_large_and_small_print_totals_remain_exact():
    huge = "1000000000000000000000000000000"
    r = measure(trades=[t("big", 130, price=huge, size=1),
                        t("small", 180, price="1", size=1)],
                quotes=[q("prior", 90, bid="0.1", ask=str(int(huge) + 1))])
    assert r["gross_active_notional_usd"] == str(int(huge) + 1)
    assert r["buy_proxy_notional_usd"] == huge
    assert r["sell_proxy_notional_usd"] == "1"


def test_research_source_decimal_exponents_cannot_expand_unbounded_fixed_strings():
    from engine.market_microstructure.pressure_response import _amount
    for exponent in ("1e+999999999", "1e-999999999"):
        with pytest.raises(ValueError, match="bounded"):
            _amount(exponent, "source-price")


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


def test_as_seen_quote_must_precede_trade_original_receipt_not_only_decision():
    quotes = [q("old", 90, available=91, bid="100", ask="101"),
              q("late", 120, available=200, bid="100", ask="102")]
    trade = t("only", 130, available=131, price="101.9")
    for mode in ("ACTUAL_AS_SEEN", "HISTORICAL_RECEIVABILITY"):
        as_seen = measure(trades=[trade], quotes=quotes, evidence_mode=mode)
        assert as_seen["print_diagnostics_private_only"][0]["side_proxy"] == "UNKNOWN"
        assert as_seen["print_diagnostics_private_only"][0]["reason"] == (
            "QUOTE_NOT_AVAILABLE_AT_TRADE_RECEIPT")
    # Later-vintage retrospective analysis remains separately labeled.
    final = measure(trades=[trade], quotes=quotes, evidence_mode="FINAL_VINTAGE")
    assert final["print_diagnostics_private_only"][0]["side_proxy"] == "BUY_PROXY"


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
        "quote_condition_rules_sha256":TP1_QUOTE_POLICY_SHA,
        "max_quote_age_ns":25_000_000_000,
        "source_observation_sha256":"d"*64,
        "n_sampled_prints":10,"n_unclassified":2,
        "n_lit":9,"n_trf":1,"n_unknown_venue":0,
        "n_buy_proxy":4,"n_sell_proxy":2,"n_midpoint":1,
        "n_condition_ineligible":1,
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
        "quote_condition":0,"quote_indicators":[604],
        "correction_status":"STREAM_PROVISIONAL_UNRECONCILED",
    }


def tp1_quotes():
    return [
        tp1_source_q("before",TP1_START-10_000_000_000),
        tp1_source_q("within",TP1_START+15_000_000_000,bs=90,az=100),
        tp1_source_q("ending",TP1_END-5_000_000_000,bs=110,az=190),
    ]


def tp1_proofs(quotes, *, decision_ns):
    # Typed TP-1 evaluator output shape, not a loose eligible=True claim.
    return {
        x["quote_id"]:{
            "schema":"equity.tick_plane.quote_condition_admission/v0",
            "authority":"ORIGINAL_QUOTE_POLICY_CONTEXT_ONLY",
            "quote_id":x["quote_id"],"source_frame_sha256":x["source_frame_sha256"],
            "original_frame_received_ns":x["original_frame_received_ns"],
            "quote_condition":x["quote_condition"],
            "quote_indicators":x["quote_indicators"],
            "policy_available_ns":x["original_frame_received_ns"]+1000000,
            "decision_ns":decision_ns,
            "policy_rules_sha256":TP1_QUOTE_POLICY_SHA,
            "source_reference_sha256":"f"*64,
            "eligible":False if x["valid_firm_nbbo"] is False else True,
            "reason":"SOURCE_CONDITION_ELIGIBLE_FOR_OBSERVATION_ONLY",
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
        source_quotes=qs,
    )
    args.update(other)
    if "quote_condition_receipts" not in args:
        args["quote_condition_receipts"]=tp1_proofs(qs,decision_ns=args["decision_ns"])
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


def test_tp1_stale_source_quote_policy_is_not_requalified_retroactively():
    r=tp1_context(max_quote_age_ns=1_000_000_000)
    assert r["state"]=="MINUTE_NOT_QUALIFIED"
    assert r["reason"]=="SOURCE_QUOTE_AGE_POLICY_TOO_LENIENT"


def test_tp1_mixed_quote_policy_generations_rejected():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["policy_rules_sha256"]="f"*64
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


def test_tp1_receipt_digests_bind_exact_minute_generation():
    a=tp1_context()
    m=tp1_minute()
    m["source_observation_sha256"]="f"*64
    b=tp1_context(minute=[m])
    assert a["pressure_balance"]==b["pressure_balance"]
    assert a["source_minutes_receipt_sha256"]!=b["source_minutes_receipt_sha256"]


def test_tp1_quote_source_digest_changes_with_price_generation():
    a=tp1_context()
    qs=tp1_quotes()
    qs[-1]["ask"]="102"
    b=tp1_context(quotes=qs)
    assert a["source_minutes_receipt_sha256"]==b["source_minutes_receipt_sha256"]
    assert a["source_quote_observations_sha256"]!=b["source_quote_observations_sha256"]
    assert a["midpoint_response_bps"]!=b["midpoint_response_bps"]


def test_tp1_rejects_inconsistent_count_denominators():
    bad=tp1_minute()
    bad["n_trf"]=2
    with pytest.raises(TP1ContextRefusal,match="print denominators"):
        tp1_context(minute=[bad])


def test_tp1_rejects_claimed_measured_minute_without_observed_prints():
    bad=tp1_minute()
    bad["n_sampled_prints"]=0
    with pytest.raises(TP1ContextRefusal,match="contradictory print counts"):
        tp1_context(minute=[bad])


def test_tp1_rejects_legacy_untyped_quote_policy_boolean_receipt():
    data=tp1_args()
    before=data["quote_condition_receipts"]["before"]
    data["quote_condition_receipts"]["before"]={
        "quote_id":before["quote_id"],
        "source_frame_sha256":before["source_frame_sha256"],
        "original_frame_received_ns":before["original_frame_received_ns"],
        "eligible":True,
        "rules_sha256":TP1_QUOTE_POLICY_SHA,
        "policy_available_ns":before["policy_available_ns"],
    }
    result=project_tp1_pressure_context(**data)
    assert result["state"]=="QUOTE_REFERENCE_UNQUALIFIED"


def test_tp1_quote_native_condition_mismatch_rejected():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["quote_condition"]=20
    result=project_tp1_pressure_context(**data)
    assert result["reason"]=="MISSING_OR_MISMATCHED_QUOTE_CONDITION_RECEIPT"


def test_tp1_quote_indicator_mismatch_rejected():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["quote_indicators"]=[603]
    result=project_tp1_pressure_context(**data)
    assert result["state"]=="QUOTE_REFERENCE_UNQUALIFIED"


def test_tp1_quote_policy_decision_after_study_cutoff_rejected():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["decision_ns"]=TP1_CUT+1
    result=project_tp1_pressure_context(**data)
    assert result["reason"]=="QUOTE_CONDITION_POLICY_NOT_AVAILABLE_AT_DECISION"


def test_tp1_quote_policy_decision_before_source_receipt_rejected():
    data=tp1_args()
    data["quote_condition_receipts"]["ending"]["decision_ns"]=TP1_START
    result=project_tp1_pressure_context(**data)
    assert result["reason"]=="QUOTE_CONDITION_POLICY_NOT_AVAILABLE_AT_DECISION"


def test_tp1_minute_and_quote_policy_generation_must_match():
    m=tp1_minute()
    m["quote_condition_rules_sha256"]="9"*64
    output=tp1_context(minute=[m])
    assert output["state"]=="QUOTE_REFERENCE_UNQUALIFIED"
    assert output["reason"]=="MINUTE_AND_QUOTE_POLICY_GENERATION_DISAGREEMENT"


def test_tp1_rejects_missing_minute_quote_policy_generation():
    m=tp1_minute()
    m["quote_condition_rules_sha256"]=None
    with pytest.raises(TP1ContextRefusal,match="minute.quote_condition_rules_sha256"):
        tp1_context(minute=[m])


def test_tp1_source_quote_age_policy_is_in_research_output():
    v=tp1_context()
    assert v["source_quote_age_limit_ns"]==25_000_000_000


def test_tp1_stricter_upstream_quote_age_policy_is_compatible():
    minute=tp1_minute()
    minute["max_quote_age_ns"]=5_000_000_000
    v=tp1_context(minute=[minute])
    assert v["state"]=="PROVISIONAL_RESEARCH_CONTEXT"
    assert v["source_quote_age_limit_ns"]==5_000_000_000


def test_tp1_mixed_source_quote_age_policies_refused():
    first=tp1_minute(TP1_START)
    nextm=tp1_minute(TP1_END)
    nextm["max_quote_age_ns"]=5_000_000_000
    end=TP1_END+TP1_MINUTE_NS
    nextm["decision_ns"]=end+1_000_000_000
    nextm["watermark_available_ns"]=end+500_000_000
    nextm["original_latest_available_ns"]=end-500_000_000
    with pytest.raises(TP1ContextRefusal,match="mixed source quote-age policies"):
        tp1_context(minute=[first,nextm],end_ns=end,
                    decision_ns=end+10_000_000_000,
                    watermark_ns=end,
                    watermark_received_ns=end+2_000_000_000)

from engine.market_microstructure.private_context_view import (
    project_private_research_context, verify_private_research_context_bytes,
    PrivateContextRefusal, SCHEMA as PRIVATE_CONTEXT_SCHEMA,
)


def private_context(value=None, *, manifest_sha="a"*64):
    return project_private_research_context(
        research_context=tp1_context() if value is None else value,
        source_manifest_sha256=manifest_sha,
    )


def test_private_context_can_render_tp1_r0_measurements_without_raw_quote_ids():
    import json
    receipt=private_context()
    assert receipt["state"]=="NOT_PUBLISHED"
    assert receipt["authority"]=="PRIVATE_RESEARCH_HANDOFF_ONLY"
    assert receipt["public_delivery_allowed"] is False
    body=json.loads(receipt["bytes_private_only"])
    assert body["schema"]==PRIVATE_CONTEXT_SCHEMA
    assert body["distribution_class"]=="PRIVATE_SERVICE_HOLD_PENDING_LICENSE_REVIEW"
    assert body["notional_usd"]["buy_proxy_notional_usd"]=="1000"
    assert body["notional_usd"]["sell_proxy_notional_usd"]=="500"
    assert body["rank_trade_alert_authority"] is False
    assert body["absorption_signal"] is None
    assert body["forward_label"] is None
    assert b'quote_id' not in receipt["bytes_private_only"]
    assert b'source_frame_sha256' not in receipt["bytes_private_only"]
    assert b'raw_frame' not in receipt["bytes_private_only"]


def test_private_context_decimal_quote_recovery_is_exact_text_not_json_float():
    import json
    body=json.loads(private_context()["bytes_private_only"])
    recovered=body["ask_size_recovery_proxy"]
    assert recovered["state"]=="MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT"
    assert recovered["depletion_shares"]=="100"
    assert recovered["recovered_shares"]=="90"
    assert recovered["original_shares"]=="200"
    assert recovered["final_shares"]=="190"
    assert recovered["source_best_exchange"]=="12"
    assert recovered["source_best_price"]=="101"
    bid=body["bid_size_recovery_proxy"]
    assert bid["state"]=="MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT"
    assert bid["depletion_shares"]=="10"
    assert bid["recovered_shares"]=="20"
    assert bid["original_shares"]=="100"
    assert bid["final_shares"]=="110"
    assert bid["source_best_exchange"]=="11"
    assert bid["source_best_price"]=="100"


def test_private_context_source_manifest_and_receipt_literals_not_serialized():
    obj=tp1_context()
    obj["source_manifest"]="API_TOKEN_LIKE_SECRET_MANIFEST"
    obj["source_watermark_receipt"]="RECEIPT_PRIVATE_HOLD"
    raw=private_context(obj)["bytes_private_only"]
    assert b"API_TOKEN_LIKE_SECRET_MANIFEST" not in raw
    assert b"RECEIPT_PRIVATE_HOLD" not in raw
    assert b"source_manifest_name_sha256" in raw
    assert b"source_watermark_receipt_sha256" in raw


def test_private_context_derived_bytes_and_hash_are_repeatable():
    a=private_context()
    b=private_context(deepcopy(tp1_context()))
    assert a["sha256"]==b["sha256"]
    assert a["bytes_private_only"]==b["bytes_private_only"]


def test_private_context_source_vintage_hash_changes_content():
    obj=tp1_context()
    obj["source_quote_observations_sha256"]="f"*64
    assert private_context(obj)["sha256"]!=private_context()["sha256"]


def test_private_context_never_exports_live_alert_or_filled_trade():
    for field,value in (
        ("absorption_signal",.9),("rank_authority",True),
        ("forward_outcome_label",".02"),("execution_adjusted_return","123"),
        ("impact_relative_to_control",10),
    ):
        obj=tp1_context()
        obj[field]=value
        with pytest.raises(PrivateContextRefusal,match="authority"):
            private_context(obj)


def test_private_context_does_not_promote_original_feed_authenticity():
    import json
    view=json.loads(private_context()["bytes_private_only"])
    assert view["source_authenticity"]=="ORIGINAL_TQ_RECEIPTS_REQUIRE_EXTERNAL_OWNER_PROOF"
    assert view["market_capture_completeness"]=="NOT_PROVEN_BY_RESEARCH_MATH"
    assert view["public_delivery_allowed"] is False


def test_private_context_nonfinite_or_invalid_midpoint_bps_refused():
    for bad in ("NaN","Infinity","not-a-number"):
        obj=tp1_context()
        obj["midpoint_response_bps"]=bad
        with pytest.raises(PrivateContextRefusal):
            private_context(obj)


def test_private_context_pressure_balance_bounded_to_minus_one_one():
    obj=tp1_context()
    obj["pressure_balance"]="1.5"
    with pytest.raises(PrivateContextRefusal,match="pressure outside"):
        private_context(obj)


def test_private_context_sum_of_trade_notional_is_validated():
    obj=tp1_context()
    obj["gross_sampled_notional_usd"]="9"
    with pytest.raises(PrivateContextRefusal,match="conservation"):
        private_context(obj)


def test_private_context_source_criteria_not_stale_or_unqualified():
    obj=tp1_context()
    obj["state"]="PRICE_CONTEXT_UNOBSERVABLE"
    with pytest.raises(PrivateContextRefusal,match="authority"):
        private_context(obj)
    obj=tp1_context()
    obj["source_qualification"]="VERIFIED_PRODUCTION_SOURCE"
    with pytest.raises(PrivateContextRefusal,match="authority"):
        private_context(obj)


def test_private_context_rejects_raw_data_extra_fields():
    obj=tp1_context()
    obj["raw_websocket_quotes"]=[{"sym":"SPY","p":1.0}]
    with pytest.raises(PrivateContextRefusal,match="unexpected raw/new"):
        private_context(obj)


def test_private_context_invalid_source_digest_never_admitted():
    with pytest.raises(PrivateContextRefusal,match="source_manifest_sha256"):
        private_context(manifest_sha="not-a-source-digest")


def test_private_context_missing_required_quote_evidence_rejected():
    obj=tp1_context()
    obj["source_quote_observations_sha256"]=None
    with pytest.raises(PrivateContextRefusal,match="source_quote_observations"):
        private_context(obj)


def test_private_context_unknown_replenishment_keeps_explicit_reason():
    import json
    obj=tp1_context()
    obj["ask_size_recovery"]={"state":"UNKNOWN","reason":"BEST_PRICE_OR_VENUE_CHANGED"}
    body=json.loads(private_context(obj)["bytes_private_only"])
    assert body["ask_size_recovery_proxy"]=={
        "state":"UNKNOWN","reason":"BEST_PRICE_OR_VENUE_CHANGED"}


def test_private_context_bad_recovery_decimal_refused():
    obj=tp1_context()
    obj["ask_size_recovery"]=dict(obj["ask_size_recovery"])
    obj["ask_size_recovery"]["depletion_shares"]=Decimal("NaN")
    with pytest.raises(PrivateContextRefusal):
        private_context(obj)


def test_private_context_impossible_recovery_trough_refused():
    obj=tp1_context()
    obj["ask_size_recovery"]=dict(obj["ask_size_recovery"])
    obj["ask_size_recovery"]["depletion_shares"]=Decimal("201")
    with pytest.raises(PrivateContextRefusal):
        private_context(obj)


def test_private_context_source_receipt_fingerprint_does_not_change_price():
    import json
    obj=tp1_context()
    obj["source_watermark_receipt"]="a-different-private-receipt"
    a=json.loads(private_context()["bytes_private_only"])
    b=json.loads(private_context(obj)["bytes_private_only"])
    assert a["completed_window_midpoint_response_bps"]==b["completed_window_midpoint_response_bps"]
    assert a["source_watermark_receipt_sha256"]!=b["source_watermark_receipt_sha256"]


def private_readback(receipt):
    return verify_private_research_context_bytes(
        expected_sha256=receipt["sha256"],
        expected_byte_length=receipt["content_length"],
        blob=receipt["bytes_private_only"],
    )


def forged_private_blob(document):
    import json, hashlib
    raw=(json.dumps(document,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    return {"sha256":hashlib.sha256(raw).hexdigest(),
            "content_length":len(raw),"bytes_private_only":raw}


def test_private_readback_accepts_actual_allowlisted_source_context():
    result=private_readback(private_context())
    assert result["schema"]==PRIVATE_CONTEXT_SCHEMA
    assert result["bid_size_recovery_proxy"]["state"]==(
        "MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT")
    assert result["ask_size_recovery_proxy"]["recovered_shares"]=="90"
    assert result["market_capture_completeness"]=="NOT_PROVEN_BY_RESEARCH_MATH"
    assert result["absorption_signal"] is None


def test_private_readback_rejects_raw_tape_added_even_with_recomputed_digest():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["raw_vendor_quotes"]=[{"tick":"private-licensed-tape"}]
    with pytest.raises(PrivateContextRefusal,match="shape/authority"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_native_trade_id_added_to_aggregate_counts():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["n_observations"]["native_trade_id"]="raw-trade-id"
    with pytest.raises(PrivateContextRefusal,match="nested fields outside allowlist"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_recomputed_public_delivery_bit():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["public_delivery_allowed"]=True
    with pytest.raises(PrivateContextRefusal,match="shape/authority"):
        private_readback(forged_private_blob(data))


def test_private_readback_refuses_claim_of_vendor_authenticity():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["source_authenticity"]="CONFIRMED_VENDOR_ORIGINAL"
    with pytest.raises(PrivateContextRefusal,match="shape/authority"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_outcome_labels_after_hash_recompute():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["absorption_signal"]=1  # valid JSON integer; test the authority gate, not float decoding
    with pytest.raises(PrivateContextRefusal,match="shape/authority"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_forged_order_replenishment_label():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["bid_size_recovery_proxy"]["state"]="ORDER_LEVEL_REPLENISHMENT"
    with pytest.raises(PrivateContextRefusal,match="recovery label unknown"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_unqualified_source_digest():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["source_manifest_sha256"]="not-a-source-digest"
    with pytest.raises(PrivateContextRefusal,match="source_manifest_sha256"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_invalid_decimal_recovered_size():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["ask_size_recovery_proxy"]["final_shares"]="999"
    with pytest.raises(PrivateContextRefusal,match="recovery amount inconsistent"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_unqualified_best_quote_exchange():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["ask_size_recovery_proxy"]["source_best_exchange"]="VENUE:TOKEN"
    with pytest.raises(PrivateContextRefusal,match="exchange code"):
        private_readback(forged_private_blob(data))


def test_private_readback_rejects_wrong_byte_length_or_digest():
    a=private_context()
    with pytest.raises(PrivateContextRefusal,match="byte length"):
        verify_private_research_context_bytes(
            expected_sha256=a["sha256"],expected_byte_length=a["content_length"]-1,
            blob=a["bytes_private_only"])
    with pytest.raises(PrivateContextRefusal,match="digest mismatch"):
        verify_private_research_context_bytes(
            expected_sha256="f"*64,expected_byte_length=a["content_length"],
            blob=a["bytes_private_only"])


def test_private_readback_rejects_noncanonical_whitespace_even_with_digest():
    import json, hashlib
    r=private_context()
    data=json.loads(r["bytes_private_only"])
    raw=(json.dumps(data,sort_keys=True,indent=2)+"\n").encode()
    with pytest.raises(PrivateContextRefusal,match="noncanonical"):
        verify_private_research_context_bytes(expected_sha256=hashlib.sha256(raw).hexdigest(),
                                              expected_byte_length=len(raw),blob=raw)


def test_private_readback_rejects_invalid_market_day_and_window():
    import json
    data=json.loads(private_context()["bytes_private_only"])
    data["session"]="2026-10-08:POST:RTH"
    with pytest.raises(PrivateContextRefusal,match="symbol/session"):
        private_readback(forged_private_blob(data))
    data=json.loads(private_context()["bytes_private_only"])
    data["end_ns"]=data["start_ns"]+30_000_000_000
    with pytest.raises(PrivateContextRefusal,match="window or cutoff"):
        private_readback(forged_private_blob(data))


def test_private_readback_requires_canonical_decimals_not_raw_json_floats():
    import hashlib
    a=private_context()
    raw=a["bytes_private_only"].replace(b'"source_best_price":"101"',b'"source_best_price":101.0')
    assert raw!=a["bytes_private_only"]
    with pytest.raises(PrivateContextRefusal,match="JSON native float"):
        verify_private_research_context_bytes(expected_sha256=hashlib.sha256(raw).hexdigest(),
                                              expected_byte_length=len(raw),blob=raw)


def test_private_readback_rejects_nonfinite_recomputed_source():
    import hashlib
    a=private_context()
    raw=a["bytes_private_only"].replace(b'"completed_window_midpoint_response_bps":"0"',
                                        b'"completed_window_midpoint_response_bps":NaN')
    assert raw!=a["bytes_private_only"]
    with pytest.raises(PrivateContextRefusal,match="JSON nonfinite"):
        verify_private_research_context_bytes(expected_sha256=hashlib.sha256(raw).hexdigest(),
                                              expected_byte_length=len(raw),blob=raw)


# The label adapter consumes the same source-owned TP-1 records; no second signer.
from engine.market_microstructure.tp1_matured_response import (
    project_tp1_matured_response, SOURCE_EVIDENCE_SCHEMA, ORIGINAL_EVIDENCE_SCHEMA,
)


def label_source_q(sequence, stamp, **kwargs):
    name=f"2026-10-08:RTH:SPY:Q:{sequence}:{stamp}"
    q=tp1_source_q(name, stamp, **kwargs)
    return {**q, "native_sequence":sequence,
            "source_timestamp_precision":"MILLISECONDS",
            "source_status":"RECEIPT_UNQUALIFIED_UNTIL_OWNER_ATTESTS"}


def label_digest(value):
    import hashlib, json
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",",":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def rebind_label_source(data):
    # Stand-in receipt assembly for synthetic tests, not source capture proof.
    from engine.market_microstructure.tp1_context import _normalize_tp1_quotes, _tp1_quote_digest
    original, _, _ = _normalize_tp1_quotes(
        ticker="SPY", session="2026-10-08:RTH", decision_ns=TP1_CUT,
        source_quotes=data["original_source_quotes"],
        quote_condition_receipts=data["original_quote_condition_receipts"])
    later, _, _ = _normalize_tp1_quotes(
        ticker="SPY", session="2026-10-08:RTH", decision_ns=data["evaluation_cutoff_ns"],
        source_quotes=data["later_source_quotes"],
        quote_condition_receipts=data["later_quote_condition_receipts"], allow_empty=True)
    combined=sorted(original+later, key=lambda q:(q["sip_ns"],q["id"]))
    data["source_evidence"]["quote_observations_sha256"]=_tp1_quote_digest(combined)
    data["source_evidence"]["endpoint_minute_sha256"]=label_digest(data["endpoint_minute"])
    return data


def tp1_label_args(*, horizon_ns=30_000_000_000, include_anchor=True, anchor_valid=True):
    import json
    policy_seen=TP1_START-60_000_000_000
    original=[
        label_source_q(1,TP1_START-10_000_000_000),
        label_source_q(2,TP1_START+15_000_000_000,bs=90,az=100),
        label_source_q(3,TP1_END-5_000_000_000,bs=110,az=190),
    ]
    if include_anchor:
        original.append(label_source_q(4,TP1_CUT-100_000_000,
                                       available=TP1_CUT-50_000_000,valid=anchor_valid))
    original_proofs=tp1_proofs(original,decision_ns=TP1_CUT-2_000_000)
    for p in original_proofs.values():
        p["policy_available_ns"]=policy_seen
    context=project_tp1_pressure_context(**tp1_args(
        quotes=original,quote_condition_receipts=original_proofs,
        watermark_ns=TP1_END,watermark_received_ns=TP1_END+2_000_000_000))
    private=private_context(context)
    feature=json.loads(private["bytes_private_only"])
    end=TP1_CUT+horizon_ns
    minute_start=((end-1)//TP1_MINUTE_NS)*TP1_MINUTE_NS
    minute=tp1_minute(minute_start)
    cutoff=minute["end_ns"]+10_000_000_000
    later=[label_source_q(5,end-100_000_000,bid="102",ask="103",
                          available=end-50_000_000)]
    later_proofs=tp1_proofs(later,decision_ns=end+100_000_000)
    for p in later_proofs.values():
        p["policy_available_ns"]=policy_seen
    original_evidence={
        "schema":ORIGINAL_EVIDENCE_SCHEMA,
        "authority":"SOURCE_OWNER_ASSERTION_REQUIRES_EXTERNAL_PROOF",
        "ticker":"SPY","session":"2026-10-08:RTH","feature_sha256":private["sha256"],
        "source_manifest_sha256":feature["source_manifest_sha256"],
        "quote_observations_sha256":feature["quote_observations_sha256"],
        "quote_condition_receipts_sha256":label_digest(original_proofs),
        "quote_condition_receipts_frozen_ns":TP1_CUT-1_000_000,
        "quote_condition_receipts_receipt":"frozen-original-verdicts-1",
        "coverage_clock":"ORIGINAL_FRAME_RECEIPT","snapshot_cutoff_ns":TP1_CUT,
        "health_available_ns":TP1_CUT-1_000_000_000,
        "health_basis":"LATEST_STATUS_AS_SEEN_AT_SNAPSHOT",
        "source_watermark_receipt":TP1_WATERMARK,
        "source_complete_through_ns":TP1_END,"watermark_available_ns":TP1_END+2_000_000_000,
        "coverage_start_ns":TP1_START-25_000_000_000,"coverage_end_ns":TP1_CUT,
        "available_ns":TP1_CUT+2_000_000,"receipt_id":"original-source-health-1",
        "market_health":"NORMAL","gap_state":"CONTIGUOUS",
        "source_completeness_attested":True,"original_reference_custody_attested":True,
    }
    source_evidence={
        "schema":SOURCE_EVIDENCE_SCHEMA,
        "authority":"SOURCE_OWNER_ASSERTION_REQUIRES_EXTERNAL_PROOF",
        "ticker":"SPY","session":"2026-10-08:RTH","feature_sha256":private["sha256"],
        "source_manifest_sha256":"9"*64,"quote_observations_sha256":"0"*64,
        "endpoint_minute_sha256":label_digest(minute),
        "source_watermark_receipt":minute["source_watermark_receipt"],
        "coverage_start_ns":TP1_CUT-25_000_000_000,
        "coverage_end_ns":minute["end_ns"],
        "available_ns":minute["decision_ns"]+1_000_000_000,
        "health_available_ns":minute["decision_ns"],
        "receipt_id":"later-source-health-1","market_health":"NORMAL",
        "gap_state":"CONTIGUOUS","source_completeness_attested":True,
        "original_reference_custody_attested":True,
    }
    data=dict(
        feature_blob=private["bytes_private_only"],feature_sha256=private["sha256"],
        feature_byte_length=private["content_length"],
        feature_available_ns=TP1_CUT+1_000_000,feature_availability_receipt="feature-readback-1",
        horizon_ns=horizon_ns,evaluation_cutoff_ns=cutoff,max_quote_age_ns=1_000_000_000,
        original_source_quotes=original,original_quote_condition_receipts=original_proofs,
        later_source_quotes=later,later_quote_condition_receipts=later_proofs,
        exchange_reference={
            "schema":"equity.tick_plane.exchange_reference/v0",
            "authority":"SOURCE_REFERENCE_ONLY","source_vintage":"AS_RECEIVED_NOT_RETROACTIVE",
            "reference_available_ns":policy_seen,"original_reference_receipt":"original-exchange-1",
            "source_request_id":"exchange-request-1","reference_sha256":TP1_EXCHANGE_SHA,
            "source_types":{11:"exchange",12:"exchange",4:"TRF",0:"SIP"},
        },
        quote_policy={
            "schema":"equity.tick_plane.quote_condition_policy/v0",
            "authority":"SOURCE_POLICY_CANDIDATE_REQUIRES_CUSTODY",
            "policy_sha256":TP1_QUOTE_POLICY_SHA,"policy_received_ns":policy_seen,
            "policy_receipt_id":"original-quote-policy-1","source_reference_sha256":"f"*64,
            "reviewer_receipt":"source-review-1","allowed_quote_conditions":(0,1),
            "allowed_nbbo_indicators":(602,604,605),"unknown_action":"ABSTAIN",
        },
        endpoint_minute=minute,original_source_evidence=original_evidence,
        source_evidence=source_evidence,
    )
    return rebind_label_source(data)


def test_tp1_label_keeps_verified_feature_and_all_source_inputs_immutable():
    import hashlib, json
    data=tp1_label_args()
    before=deepcopy(data)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["midpoint_response_bps"]=="199.0049751243781094527363200"
    assert out["anchor_ns"]==TP1_CUT
    assert out["label_end_ns"]==TP1_CUT+30_000_000_000
    assert data==before
    assert out["feature_sha256"]==hashlib.sha256(data["feature_blob"]).hexdigest()
    assert out["feature_byte_length"]==len(data["feature_blob"])
    assert json.loads(data["feature_blob"])["forward_label"] is None
    assert out["label_first_knowable_ns"]==data["source_evidence"]["available_ns"]
    assert out["label_first_knowable_ns"]!=out["label_end_ns"]
    assert out["label_first_knowable_ns"]!=out["evaluation_cutoff_ns"]


def test_tp1_label_regression_ineligible_native_condition_cannot_create_199bp_response():
    data=tp1_label_args()
    q=data["later_source_quotes"][0]
    q["quote_condition"]=7
    verdict=data["later_quote_condition_receipts"][q["quote_id"]]
    verdict.update(quote_condition=7,eligible=False,reason="NONFIRM_SOURCE_CONDITION")
    rebind_label_source(data)
    # Generic arithmetic assumes caller-normalized, already-qualified quotes.
    naive=[
        dict(id=q["quote_id"],ticker=q["ticker"],session=q["session"],
             sip_ns=q["sip_timestamp_ns"],available_ns=q["original_frame_received_ns"],
             bid=q["bid"],ask=q["ask"],bid_size=q["bid_size"],ask_size=q["ask_size"],
             source_receipt=q["source_frame_sha256"]+":"+str(q["frame_event_index"]))
        for q in data["original_source_quotes"]+data["later_source_quotes"]
    ]
    raw=measure_matured_response(
        ticker="SPY",session="2026-10-08:RTH",original_decision_ns=TP1_CUT,
        anchor_ns=TP1_CUT,label_end_ns=TP1_CUT+30_000_000_000,
        evaluation_cutoff_ns=data["evaluation_cutoff_ns"],
        source_watermark_ns=data["endpoint_minute"]["source_complete_through_ns"],
        watermark_received_ns=data["endpoint_minute"]["watermark_available_ns"],
        watermark_receipt="synthetic-watermark",source_manifest="synthetic-label-only",
        source_mode="ACTUAL_AS_SEEN",max_quote_age_ns=1_000_000_000,
        market_health="NORMAL",market_health_receipt="synthetic-health",quotes=naive)
    assert raw["midpoint_response_bps"]=="199.0049751243781094527363200"
    out=project_tp1_matured_response(**data)
    assert out["state"]=="UNOBSERVABLE"
    assert out["reason"]["forward"]=="INVALID_NBBO"
    assert out["midpoint_response_bps"] is None


@pytest.mark.parametrize("horizon",[30_000_000_000,120_000_000_000,300_000_000_000])
def test_tp1_label_predeclared_horizons_are_separate_observations(horizon):
    out=project_tp1_matured_response(**tp1_label_args(horizon_ns=horizon))
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["label_end_ns"]==TP1_CUT+horizon
    assert out["signal"] is None and out["absorption_signal"] is None
    assert out["alpha_signal"] is None and out["promotion_authority"] is False
    assert out["rank_trade_alert_authority"] is False
    assert out["public_delivery_allowed"] is False
    assert out["correction_status"]=="STREAM_PROVISIONAL_UNRECONCILED"
    assert out["sampled_trade_volume_inferred"] is None
    assert out["market_capture_completeness"] is None
    assert out["label_knowability_basis"]=="EARLIEST_FROM_SUPPLIED_EVIDENCE_NOT_ACTUAL_EMISSION"
    assert "source_quotes" not in out and "quote_receipts_private_only" not in out


def test_tp1_label_delayed_verdict_receipt_controls_earliest_knowability():
    data=tp1_label_args()
    q=data["later_source_quotes"][0]
    delayed=data["evaluation_cutoff_ns"]-100_000_000
    data["later_quote_condition_receipts"][q["quote_id"]]["decision_ns"]=delayed
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["label_first_knowable_ns"]==delayed
    assert out["first_knowable_components_ns"]["later_quotes_and_verdicts"]==delayed
    assert out["first_knowable_components_ns"]["source_health"]<delayed


def test_tp1_label_delayed_feature_readback_controls_earliest_knowability():
    data=tp1_label_args()
    data["feature_available_ns"]=data["evaluation_cutoff_ns"]-1
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["label_first_knowable_ns"]==data["feature_available_ns"]


@pytest.mark.parametrize("field",["feature_available_ns","available_ns","watermark_available_ns","decision_ns"])
def test_tp1_label_missing_material_availability_is_typed_abstention(field):
    data=tp1_label_args()
    target=(data if field=="feature_available_ns" else data["source_evidence"]
            if field=="available_ns" else data["endpoint_minute"])
    target[field]=None
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert "MISSING_OR_INVALID" in out["reason"]
    assert out["label_first_knowable_ns"] is None
    assert out["midpoint_response_bps"] is None


@pytest.mark.parametrize("field",["feature_available_ns","available_ns","watermark_available_ns","decision_ns"])
def test_tp1_label_future_material_availability_is_typed_abstention(field):
    data=tp1_label_args()
    target=(data if field=="feature_available_ns" else data["source_evidence"]
            if field=="available_ns" else data["endpoint_minute"])
    target[field]=data["evaluation_cutoff_ns"]+1
    if target is data["endpoint_minute"]:
        data["source_evidence"]["endpoint_minute_sha256"]=label_digest(target)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert "NOT_AVAILABLE_AT_CUTOFF" in out["reason"]
    assert out["midpoint_response_bps"] is None


def test_tp1_label_future_quote_archive_entry_cannot_poison_cutoff():
    data=tp1_label_args()
    old=project_tp1_matured_response(**data)
    data["later_source_quotes"].append({
        "original_frame_received_ns":data["evaluation_cutoff_ns"]+1,
        "bid":"MALFORMED_FUTURE_VALUE",
    })
    assert project_tp1_matured_response(**data)==old


def test_tp1_label_later_quote_cannot_repair_stale_original_anchor():
    data=tp1_label_args(include_anchor=False)
    q=label_source_q(6,TP1_CUT-100_000_000,available=TP1_CUT+1_000_000)
    data["later_source_quotes"].append(q)
    proof=tp1_proofs([q],decision_ns=TP1_CUT+2_000_000)
    proof[q["quote_id"]]["policy_available_ns"]=data["quote_policy"]["policy_received_ns"]
    data["later_quote_condition_receipts"].update(proof)
    rebind_label_source(data)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="UNOBSERVABLE"
    assert out["reason"]["anchor"]=="STALE_NBBO"


def test_tp1_label_nonfirm_original_anchor_cannot_be_repaired_by_later_valid_quote():
    out=project_tp1_matured_response(**tp1_label_args(anchor_valid=False))
    assert out["state"]=="UNOBSERVABLE"
    assert out["reason"]["anchor"]=="INVALID_NBBO"


@pytest.mark.parametrize("mutation",["price","availability","frame","subset"])
def test_tp1_label_original_quote_digest_binds_exact_frozen_generation(mutation):
    data=tp1_label_args()
    q=data["original_source_quotes"][-1]
    verdict=data["original_quote_condition_receipts"][q["quote_id"]]
    if mutation=="price":
        q["bid"]="99"
    elif mutation=="availability":
        q["original_frame_received_ns"]+=1
        verdict["original_frame_received_ns"]+=1
    elif mutation=="frame":
        q["source_frame_sha256"]="8"*64
        verdict["source_frame_sha256"]="8"*64
    else:
        data["original_source_quotes"].pop()
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["reason"]=="ORIGINAL_FEATURE_QUOTE_GENERATION_MISMATCH"


def test_tp1_label_does_not_admit_original_quote_in_later_generation():
    data=tp1_label_args()
    q=deepcopy(data["original_source_quotes"][-1])
    data["later_source_quotes"].append(q)
    out=project_tp1_matured_response(**data)
    assert out["reason"]=="LATER_GENERATION_WOULD_REWRITE_ORIGINAL_SNAPSHOT"


@pytest.mark.parametrize("area",["original_verdict","exchange","policy"])
def test_tp1_label_future_source_policy_cannot_retroactively_qualify_feature(area):
    data=tp1_label_args()
    if area=="original_verdict":
        q=data["original_source_quotes"][-1]
        data["original_quote_condition_receipts"][q["quote_id"]]["decision_ns"]=TP1_CUT+1
    elif area=="exchange":
        data["exchange_reference"]["reference_available_ns"]=TP1_CUT+1
    else:
        data["quote_policy"]["policy_received_ns"]=TP1_CUT+1
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert "NOT_AVAILABLE_AT_CUTOFF" in out["reason"]


@pytest.mark.parametrize("area",["quote_policy","exchange","minute","health_quotes","health_minute"])
def test_tp1_label_mixed_source_generations_never_measure(area):
    data=tp1_label_args()
    if area=="quote_policy":
        q=data["later_source_quotes"][0]
        data["later_quote_condition_receipts"][q["quote_id"]]["policy_rules_sha256"]="8"*64
    elif area=="exchange":
        data["exchange_reference"]["reference_sha256"]="8"*64
    elif area=="minute":
        data["endpoint_minute"]["exchange_reference_sha256"]="8"*64
    elif area=="health_quotes":
        data["source_evidence"]["quote_observations_sha256"]="8"*64
    else:
        data["source_evidence"]["endpoint_minute_sha256"]="8"*64
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["midpoint_response_bps"] is None


def test_tp1_label_quote_only_mature_minute_does_not_infer_zero_printed_volume():
    data=tp1_label_args()
    old=data["endpoint_minute"]
    common=("schema","authority","ticker","session","start_ns","end_ns","decision_ns",
            "source_watermark_receipt","source_complete_through_ns","watermark_available_ns",
            "correction_status","source_mode","rank_or_trade_authority")
    minute={k:old[k] for k in common}
    minute.update(state="NO_SAMPLED_PRINTS",n_sampled_prints=0,
                  reason="NO_OBSERVED_ROWS_IS_NOT_PROOF_OF_ZERO_MARKET_VOLUME")
    data["endpoint_minute"]=minute
    rebind_label_source(data)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["endpoint_minute_state"]=="NO_SAMPLED_PRINTS"
    assert out["midpoint_response_bps"]=="199.0049751243781094527363200"
    assert out["sampled_trade_volume_inferred"] is None
    assert "buy_proxy_notional_usd" not in out


def test_tp1_label_unripe_horizon_never_becomes_available():
    data=tp1_label_args()
    data["evaluation_cutoff_ns"]=TP1_CUT+data["horizon_ns"]-1
    out=project_tp1_matured_response(**data)
    assert out["state"]=="NOT_MATURE"
    assert out["label_first_knowable_ns"] is None


def test_tp1_label_incomplete_endpoint_minute_never_becomes_available():
    data=tp1_label_args()
    data["endpoint_minute"]["source_complete_through_ns"]=data["endpoint_minute"]["end_ns"]-1
    out=project_tp1_matured_response(**data)
    assert out["state"]=="NOT_MATURE"
    assert out["reason"]=="ENDPOINT_MINUTE_WATERMARK_NOT_MATURE"


@pytest.mark.parametrize("field,value,reason",[
    ("market_health","HALTED","HALT_OR_UNKNOWN_MARKET_STATUS"),
    ("market_health","UNKNOWN","HALT_OR_UNKNOWN_MARKET_STATUS"),
    ("gap_state","GAP","SOURCE_GAP_OR_UNKNOWN_CONTINUITY"),
    ("gap_state","UNKNOWN","SOURCE_GAP_OR_UNKNOWN_CONTINUITY"),
])
def test_tp1_label_source_halt_and_gap_are_censored(field,value,reason):
    data=tp1_label_args()
    data["source_evidence"][field]=value
    frozen=data["feature_blob"]
    out=project_tp1_matured_response(**data)
    assert data["feature_blob"]==frozen
    assert out["state"]=="CENSORED"
    assert out["reason"]==reason
    assert out["midpoint_response_bps"] is None


@pytest.mark.parametrize("field",["source_completeness_attested","original_reference_custody_attested"])
def test_tp1_label_source_flags_do_not_default_to_proven(field):
    data=tp1_label_args()
    data["source_evidence"][field]=None
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"


@pytest.mark.parametrize("case",["window_end_only","later_original_receipt","original_gap","wrong_original_receipt"])
def test_tp1_label_later_health_cannot_upgrade_unqualified_original_anchor(case):
    data=tp1_label_args()
    old=data["original_source_evidence"]
    if case=="window_end_only":
        old["source_complete_through_ns"]=TP1_END
        old["coverage_end_ns"]=TP1_END
    elif case=="later_original_receipt":
        old["health_available_ns"]=TP1_CUT+1
    elif case=="original_gap":
        old["gap_state"]="GAP"
    else:
        old["source_watermark_receipt"]="wrong-original-watermark"
    out=project_tp1_matured_response(**data)
    assert out["state"] in {"SOURCE_NOT_QUALIFIED","CENSORED"}
    assert out["midpoint_response_bps"] is None
    if case=="window_end_only":
        assert out["reason"]=="ORIGINAL_SOURCE_DOES_NOT_QUALIFY_DECISION_ANCHOR"


@pytest.mark.parametrize("case",["crossed","zero_size","nonfirm","stale","exact_tie","same_sip"])
def test_tp1_label_preserves_canonical_endpoint_abstentions(case):
    data=tp1_label_args()
    q=data["later_source_quotes"][0]
    expected="INVALID_NBBO"
    if case=="crossed":
        q["bid"],q["ask"]="104","103"
    elif case=="zero_size":
        q["bid_size"]=0
    elif case=="nonfirm":
        q["valid_firm_nbbo"]=False
        data["later_quote_condition_receipts"][q["quote_id"]]["eligible"]=False
    else:
        old=q["quote_id"]
        if case=="stale":
            stamp=TP1_CUT+data["horizon_ns"]-1_001_000_000
            expected="STALE_NBBO"
        elif case=="exact_tie":
            stamp=TP1_CUT+data["horizon_ns"]
            expected="CLOCK_TIE"
        else:
            stamp=q["sip_timestamp_ns"]
            expected="AMBIGUOUS_QUOTE_ORDER"
        new=label_source_q(6,stamp,bid="102",ask="103")
        p=tp1_proofs([new],decision_ns=TP1_CUT+data["horizon_ns"]+100_000_000)
        p[new["quote_id"]]["policy_available_ns"]=data["quote_policy"]["policy_received_ns"]
        if case=="same_sip":
            data["later_source_quotes"].append(new)
        else:
            data["later_source_quotes"]=[new]
            del data["later_quote_condition_receipts"][old]
        data["later_quote_condition_receipts"].update(p)
    rebind_label_source(data)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="UNOBSERVABLE"
    assert out["reason"]["forward"]==expected


@pytest.mark.parametrize("case",["trf_venue","unknown_venue","wrong_session","final_vintage","missing_clock_precision"])
def test_tp1_label_requires_source_venue_session_and_provisional_clock_identity(case):
    data=tp1_label_args()
    q=data["later_source_quotes"][0]
    if case=="trf_venue":
        q["bid_exchange"]=4
    elif case=="unknown_venue":
        q["ask_exchange"]=999
    elif case=="wrong_session":
        q["session"]="2026-10-09:RTH"
    elif case=="final_vintage":
        q["correction_status"]="FINAL_VINTAGE"
    else:
        q.pop("source_timestamp_precision")
    if case=="wrong_session":
        with pytest.raises(TP1ContextRefusal,match="original identity"):
            project_tp1_matured_response(**data)
    else:
        out=project_tp1_matured_response(**data)
        assert out["state"]=="SOURCE_NOT_QUALIFIED"
        assert out["midpoint_response_bps"] is None


def test_tp1_label_exact_feature_bytes_checked_before_any_label_math():
    data=tp1_label_args()
    data["feature_blob"]+=b" "
    with pytest.raises(PrivateContextRefusal,match="byte length"):
        project_tp1_matured_response(**data)


def test_tp1_label_bounds_combined_quotes_without_source_capture():
    data=tp1_label_args()
    data["later_source_quotes"]=[data["later_source_quotes"][0]]*20000
    out=project_tp1_matured_response(**data)
    assert out["reason"]=="UNBOUNDED_COMBINED_QUOTE_GENERATION"


def test_tp1_label_rejects_unbounded_verdict_generation():
    data=tp1_label_args()
    data["later_quote_condition_receipts"]={str(i):{} for i in range(20001)}
    out=project_tp1_matured_response(**data)
    assert out["reason"]=="UNBOUNDED_QUOTE_VERDICT_GENERATION"


def test_tp1_label_positive_original_event_and_wrapper_lag_are_not_zero_delay():
    data=tp1_label_args()
    source=data["original_source_evidence"]
    assert source["source_complete_through_ns"]==TP1_END<TP1_CUT
    assert source["watermark_available_ns"]==TP1_END+2_000_000_000<TP1_CUT
    assert source["available_ns"]>source["snapshot_cutoff_ns"]
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["anchor_ns"]==out["original_snapshot_cutoff_ns"]==TP1_CUT
    assert out["original_snapshot_clock"]=="ORIGINAL_FRAME_RECEIPT"
    assert out["original_event_watermark_lag_ns"]==10_000_000_000
    assert out["original_watermark_receipt_lag_ns"]==2_000_000_000
    assert out["original_source_evidence_sha256"]==label_digest(source)


def test_tp1_label_original_typed_verdict_is_frozen_even_when_normalized_quote_is_identical():
    data=tp1_label_args()
    old=project_tp1_matured_response(**data)
    q=data["original_source_quotes"][-1]
    data["original_quote_condition_receipts"][q["quote_id"]]["decision_ns"]-=1_000_000
    out=project_tp1_matured_response(**data)
    assert old["state"]=="MATURED_EVALUATION_LABEL"
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["feature_sha256"]==old["feature_sha256"]
    assert out["reason"]=="FROZEN_ORIGINAL_QUOTE_VERDICT_GENERATION_MISMATCH"


@pytest.mark.parametrize("field",["snapshot_cutoff_ns","coverage_clock","coverage_end_ns"])
def test_tp1_label_original_snapshot_boundary_cannot_be_relabeled(field):
    data=tp1_label_args()
    source=data["original_source_evidence"]
    source[field]=("SIP_EVENT_TIME" if field=="coverage_clock" else TP1_CUT-1)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["midpoint_response_bps"] is None


def test_tp1_label_generation_receipt_cannot_fingerprint_future_raw_quote():
    data=tp1_label_args()
    q=data["later_source_quotes"][0]
    seen=data["source_evidence"]["available_ns"]+1_000_000
    q["original_frame_received_ns"]=seen
    v=data["later_quote_condition_receipts"][q["quote_id"]]
    v["original_frame_received_ns"]=seen
    v["decision_ns"]=seen+1_000_000
    rebind_label_source(data)
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["reason"]=="SOURCE_EVIDENCE_WRAPPER_PRECEDES_BOUND_GENERATION"


def test_tp1_label_later_verdict_metadata_is_a_separate_digest_from_earlier_quote_receipt():
    data=tp1_label_args()
    old=project_tp1_matured_response(**data)
    q=data["later_source_quotes"][0]
    delayed=data["source_evidence"]["available_ns"]+1_000_000
    data["later_quote_condition_receipts"][q["quote_id"]]["decision_ns"]=delayed
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["label_first_knowable_ns"]==delayed
    assert out["source_health_evidence_sha256"]==old["source_health_evidence_sha256"]
    assert out["combined_quote_observations_sha256"]==old["combined_quote_observations_sha256"]
    assert out["later_quote_verdicts_sha256"]!=old["later_quote_verdicts_sha256"]


@pytest.mark.parametrize("field",["health_available_ns","watermark_available_ns"])
def test_tp1_label_original_underlying_receipt_missing_or_future_is_not_repaired_by_wrapper(field):
    for invalid in (None,TP1_CUT+1):
        data=tp1_label_args()
        data["original_source_evidence"][field]=invalid
        out=project_tp1_matured_response(**data)
        assert out["state"]=="SOURCE_NOT_QUALIFIED"
        assert out["label_first_knowable_ns"] is None


def test_tp1_label_delayed_original_wrapper_is_a_material_label_clock():
    data=tp1_label_args()
    data["original_source_evidence"]["available_ns"]=data["evaluation_cutoff_ns"]-1
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["label_first_knowable_ns"]==data["evaluation_cutoff_ns"]-1
    assert out["first_knowable_components_ns"]["original_source_health_and_watermark"]==out["label_first_knowable_ns"]


def test_tp1_label_original_wrapper_cannot_precede_its_original_generation():
    data=tp1_label_args()
    data["original_source_evidence"]["available_ns"]=TP1_CUT-1
    out=project_tp1_matured_response(**data)
    assert out["reason"]=="ORIGINAL_EVIDENCE_WRAPPER_PRECEDES_BOUND_RECEIPTS"


def test_tp1_label_original_verdict_fingerprint_cannot_predate_its_frozen_generation():
    data=tp1_label_args()
    data["original_source_evidence"]["quote_condition_receipts_frozen_ns"]=TP1_CUT-3_000_000
    out=project_tp1_matured_response(**data)
    assert out["reason"]=="ORIGINAL_VERDICT_FINGERPRINT_PRECEDES_GENERATION"


@pytest.mark.parametrize("clock",[None,TP1_CUT+1])
def test_tp1_label_original_verdict_fingerprint_must_have_an_original_receipt_clock(clock):
    data=tp1_label_args()
    data["original_source_evidence"]["quote_condition_receipts_frozen_ns"]=clock
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["label_first_knowable_ns"] is None


def test_tp1_label_original_health_is_a_known_status_point_with_explicit_age():
    data=tp1_label_args()
    out=project_tp1_matured_response(**data)
    assert out["state"]=="MATURED_EVALUATION_LABEL"
    assert out["original_health_basis"]=="LATEST_STATUS_AS_SEEN_AT_SNAPSHOT"
    assert out["original_health_available_ns"]==TP1_CUT-1_000_000_000
    assert out["original_health_age_at_snapshot_ns"]==1_000_000_000
    assert out["original_snapshot_cutoff_ns"]==TP1_CUT


@pytest.mark.parametrize("basis",[None,"EVENT_TIME_HEALTH_COMPLETE_THROUGH_T"])
def test_tp1_label_missing_or_wrong_original_health_basis_cannot_be_assumed(basis):
    data=tp1_label_args()
    if basis is None:
        data["original_source_evidence"].pop("health_basis")
    else:
        data["original_source_evidence"]["health_basis"]=basis
    out=project_tp1_matured_response(**data)
    assert out["state"]=="SOURCE_NOT_QUALIFIED"
    assert out["midpoint_response_bps"] is None
