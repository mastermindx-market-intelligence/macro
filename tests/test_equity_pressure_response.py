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
