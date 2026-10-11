"""Hermetic TP-B historical-calibration contract tests; no licensed data or I/O."""
import copy

import pytest

from engine.tpb_historical_ruler import (
    HistoricalRulerRefusal, SNAPSHOT, SCHEMA, CALIBRATION, MINUTE_NS,
    measure_source_snapshot, calibrate_history,
)

BASE = 1_791_417_600_000_000_000
BASE -= BASE % MINUTE_NS
END = BASE + 210 * MINUTE_NS
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def trade(uid, minute, *, price="100", shares="1000", pipe=201,
          venue="TRF", available=None, revision=0, action="ACTIVE",
          eligible=True):
    sip = BASE + minute * MINUTE_NS + 3_000_000
    return dict(
        native_id=uid, revision=revision, action=action,
        sip_ns=sip, original_available_ns=sip + 2_000_000 if available is None else available,
        participant_ns=sip-2_000_000,
        trf_report_ns=sip-1_000_000 if venue=="TRF" else None,
        price=price, shares=shares, venue=venue,
        exchange_id=4 if venue == "TRF" else 11,
        trf_id=pipe if venue == "TRF" else None,
        volume_eligible=eligible, source_receipt_sha256=SHA_D,
    )


def point(index, oe="40", total="100", *, prefix=True, available=None):
    return dict(minute_index=index, cumulative_oe_shares=oe,
                cumulative_consolidated_shares=total,
                source_available_ns=BASE+(index+1)*MINUTE_NS+1_000_000
                    if available is None else available,
                source_receipt_sha256=SHA_C,
                prefix_coverage_attested=prefix)


def packet(day="2026-10-08", *, rows=None, points=None, **changes):
    d=dict(
        schema=SNAPSHOT, ticker="SPY", session=day+":RTH",
        start_ns=BASE, end_ns=END, asof_ns=END+60_000_000_000,
        watermark_complete_ns=END, watermark_available_ns=END+1_000_000,
        source_manifest_sha256=SHA_A, source_generation_sha256=SHA_B,
        supersedes_generation_sha256=None,
        calendar_sha256=SHA_C, volume_policy_sha256=SHA_D,
        exchange_reference_sha256=SHA_C, split_basis_id="Q03:RAW_AS_REPORTED",
        split_basis_vintage_sha256=SHA_A, split_segment="C0",
        source_owner_assertion="RECONCILED_AT_CUTOFF_UNVERIFIED_EXTERNALLY",
        source_scope="RTH", full_rth_covered=True,
        prints=[trade("A",30,price="100",shares="1000"),
                trade("B",30,price="100",shares="2000"),
                trade("C",31,price="200",shares="1000")] if rows is None else rows,
        minutes=[point(30,"40","100"),point(209,"210","500")]
            if points is None else points,
    )
    d.update(changes)
    return d


def measured(day="2026-10-08", **kw):
    return measure_source_snapshot(packet(day, **kw))


def history(days=5, *, min_print=500, minutes=None):
    sessions=[]
    for i in range(days):
        p=packet("2026-09-"+str(i+1).zfill(2),
                 rows=[trade("H"+str(i),30,shares=str(min_print+i))],
                 points=[point(30,str(20+i), "100"),point(209,"100","200")])
        sessions.append(measure_source_snapshot(p))
    return sessions


def test_source_rebuild_keeps_print_cluster_day_grains_distinct():
    obj=measured()
    assert obj["schema"]==SCHEMA
    assert obj["n_source_rows"]==3
    assert obj["n_trf_observed"]==3
    assert obj["largest_individual_print_usd"]=="200000"
    assert obj["largest_cluster_usd"]=="300000"
    assert obj["oe_source_notional_usd"]=="500000"
    assert obj["n_clusters"]==1
    assert obj["absolute_block_tier_counts"]=={
        "100000":3,"500000":0,"1000000":0}
    assert obj["absolute_block_tier_rates"]=={
        "100000":"1","500000":"0","1000000":"0"}
    assert obj["absolute_block_tier_notional_fractions"]=={
        "100000":"1","500000":"0","1000000":"0"}
    assert obj["cluster_clock"]=="SIP_REPORT_TIME_PROXY_NOT_EXECUTION_CLOCK"
    assert obj["source_receipts_authenticated"] is False
    assert obj["public_delivery_allowed"] is False
    assert obj["ranking_trading_alert_authority"] is False
    assert "native_id" not in str(obj)
    assert "named_ats" not in str(obj).lower()


def test_same_level_cluster_survives_interleaved_price():
    # TRF 100.0, 101.0, 100.0 are all within an anchored 60s window.
    rows=[trade("A",30,price="100",shares="500"),
          trade("B",30,price="101",shares="10"),
          trade("C",30,price="100",shares="600")]
    obj=measured(rows=rows)
    assert obj["largest_cluster_usd"]=="110000"
    assert obj["n_clusters"]==1


def test_no_transitive_level_cluster_beyond_first_window():
    rows=[trade("A",30,shares="500"),
          trade("B",30,shares="600"),
          trade("C",32,shares="700")]
    obj=measured(rows=rows)
    assert obj["largest_cluster_usd"]=="110000"


def test_largest_cluster_uses_maximum_rolling_60_second_window():
    # Three same-price prints can chain across 60 seconds. The first anchored
    # group is NOT necessarily the maximum valid <=60-second cluster.
    origin = BASE + 30 * MINUTE_NS + 3_000_000
    rows = []
    for uid, delay_s, shares in (("a", 0, "10"), ("b", 50, "20"), ("c", 61, "100")):
        row = trade(uid, 30, price="100", shares=shares)
        stamp = origin + delay_s * 1_000_000_000
        row.update(sip_ns=stamp, original_available_ns=stamp + 2_000_000,
                   participant_ns=stamp - 2_000_000,
                   trf_report_ns=stamp - 1_000_000)
        rows.append(row)
    result = measured(rows=rows)
    assert result["largest_individual_print_usd"] == "10000"
    assert result["largest_cluster_usd"] == "12000"
    assert result["n_clusters"] == 1  # anchored count differs from rolling maximum
    assert result["oe_source_notional_usd"] == "13000"


def test_empty_source_is_not_claimed_zero_market_volume():
    empty=measured(rows=[],points=[])
    assert empty["state"]=="NO_SAMPLED_PRINTS"
    assert empty["oe_source_shares"] is None
    with pytest.raises(HistoricalRulerRefusal,match="target"):
        calibrate_history(target=empty,previous=[],minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=2)


def test_source_partitions_are_not_inferred_as_trf_or_direction():
    obj=measured(rows=[
        trade("lit",30,venue="LIT"),
        trade("u",30,venue="UNKNOWN",eligible=None),
        trade("off",30,shares="500",eligible=False)])
    assert obj["n_trf_observed"]==0
    assert obj["n_unknown_volume_policy"]==1
    assert obj["state"]=="NO_QUALIFIED_OFF_EXCHANGE_OBSERVED"
    assert obj["oe_source_shares"] is None
    assert obj["oe_source_notional_usd"] is None
    assert all(x is None for x in obj["absolute_block_tier_rates"].values())
    assert obj["signal"] is None and obj["actor_identity"] is None


def test_native_participant_report_and_receipt_clocks_remain_distinct():
    item=trade("distinct",30,shares="500")
    obj=measured(rows=[item])
    assert obj["n_participant_timestamps"]==1
    assert obj["n_trf_report_timestamps"]==1
    assert obj["min_sip_minus_trf_report_ns"]==1_000_000
    assert obj["max_sip_minus_trf_report_ns"]==1_000_000
    assert obj["cluster_clock"]=="SIP_REPORT_TIME_PROXY_NOT_EXECUTION_CLOCK"
    # Native report or participant time later than receipt is impossible.
    for clock in ("trf_report_ns", "participant_ns"):
        with pytest.raises(HistoricalRulerRefusal,match="clocks exceed"):
            measured(rows=[dict(item,**{clock:item["original_available_ns"]+1})])
    no_native=measured(rows=[dict(item,participant_ns=None,trf_report_ns=None)])
    assert no_native["n_trf_report_timestamps"]==0
    assert no_native["max_sip_minus_trf_report_ns"] is None


def test_invalid_trf_pipe_and_venue_never_qualify():
    with pytest.raises(HistoricalRulerRefusal,match="TRF pipe"):
        measured(rows=[trade("a",30,pipe=999)])
    with pytest.raises(HistoricalRulerRefusal,match="TRF pipe"):
        measured(rows=[dict(trade("a",30),exchange_id=12)])


def test_correction_generation_can_change_ranks_without_mutating_predecessor():
    first=measured(rows=[trade("A",30,shares="1000")])
    revised=trade("A",30,shares="1000",revision=1,action="CANCELLED")
    second=measured(rows=[revised],source_generation_sha256=SHA_C,
                    supersedes_generation_sha256=SHA_B)
    assert first["oe_source_notional_usd"]=="100000"
    assert second["oe_source_notional_usd"] is None
    assert second["oe_source_shares"] is None
    assert second["n_cancelled"]==1
    assert second["n_revised_rows"]==1
    assert first["snapshot_sha256"]!=second["snapshot_sha256"]
    assert first["source_generation_sha256"]==SHA_B
    assert second["supersedes_generation_sha256"]==SHA_B
    with pytest.raises(HistoricalRulerRefusal,match="prior generation"):
        measured(rows=[revised])


def test_late_source_revision_and_corrections_fail_closed():
    with pytest.raises(HistoricalRulerRefusal,match="knowable"):
        measured(rows=[trade("A",30,available=END+120_000_000_000)])
    with pytest.raises(HistoricalRulerRefusal,match="duplicate"):
        measured(rows=[trade("A",30),trade("A",30)])
    with pytest.raises(HistoricalRulerRefusal,match="watermark"):
        measured(watermark_available_ns=END+100_000_000_000)


def test_minute_receipt_cannot_precede_its_source_minute():
    # A response assembled using a future minute must not be known before
    # the final event boundary of that minute.
    with pytest.raises(HistoricalRulerRefusal,match="minute point before"):
        measured(points=[point(30,available=BASE+30*MINUTE_NS+1_000_000)])


def test_events_and_minute_prefixes_must_be_covered_by_watermark():
    partial=BASE+60*MINUTE_NS
    with pytest.raises(HistoricalRulerRefusal,match="watermark"):
        measured(full_rth_covered=False,watermark_complete_ns=partial,
                 rows=[trade("outside",61)])
    with pytest.raises(HistoricalRulerRefusal,match="watermark"):
        measured(full_rth_covered=False,watermark_complete_ns=partial,
                 points=[point(30),point(209)])


def test_minute_points_are_cumulative_and_require_source_receipt():
    with pytest.raises(HistoricalRulerRefusal,match="cumulative"):
        measured(points=[point(30,"40","100"),point(100,"39","120")])
    with pytest.raises(HistoricalRulerRefusal,match="cumulative"):
        measured(points=[point(30,"101","100")])
    with pytest.raises(HistoricalRulerRefusal,match="increasing"):
        measured(points=[point(30),point(30)])
    with pytest.raises(HistoricalRulerRefusal,match="source_receipt"):
        measured(points=[dict(point(30),source_receipt_sha256="BAD")])


def test_wrong_time_or_unqualified_full_rth_refused():
    with pytest.raises(HistoricalRulerRefusal,match="full RTH"):
        measured(watermark_complete_ns=END-1)
    with pytest.raises(HistoricalRulerRefusal,match="calendar"):
        measured(start_ns=BASE+1)
    with pytest.raises(HistoricalRulerRefusal,match="future minute"):
        measured(points=[point(30,available=END+120_000_000_000)])


def test_rank_three_distinct_objects_and_strict_record_semantics():
    target=measured()
    prev=history(5)
    result=calibrate_history(target=target,previous=prev,minute_index=30,
                             evaluation_ns=END+90_000_000_000,min_history=3)
    assert result["schema"]==CALIBRATION
    daily=result["daily_object_ranks"]
    assert daily["SINGLE_PRINT"]["rank_desc"]==1
    assert daily["SAME_LEVEL_CLUSTER"]["state"]=="INSUFFICIENT_COMPARABLE_HISTORY"
    assert daily["DAILY_TOTAL"]["rank_desc"]==1
    assert daily["SINGLE_PRINT"]["strict_new_record_in_observed_sample"]
    assert daily["DAILY_TOTAL"]["n_prior"]==5
    assert daily["SINGLE_PRINT"]["coverage_start"]=="2026-09-01:RTH"
    assert result["source_authenticated"] is False
    assert result["ranking_trading_alert_authority"] is False
    assert result["public_delivery_allowed"] is False


def test_early_close_daily_rank_does_not_compare_regular_length_sessions():
    # 210-minute early-close daily TRF total is not a 390-minute daily
    # observation. Their 10:00 cumulative prefixes MAY remain comparable.
    regular_end = BASE + 390 * MINUTE_NS
    full_days = []
    for i in range(4):
        full_days.append(measure_source_snapshot(packet(
            "2026-09-" + str(i+1).zfill(2),
            end_ns=regular_end, asof_ns=regular_end + MINUTE_NS,
            watermark_complete_ns=regular_end,
            watermark_available_ns=regular_end + 1_000_000,
            prints=[trade("old"+str(i), 30, shares="2000")],
            minutes=[point(30, "20", "100"),
                     point(209, "200", "500"),
                     point(389, "300", "600")],
        )))
    # Fixture sessions share an artificial UTC base. Keep their as-of
    # receipts no later than the target cutoff, isolating the duration test.
    target = measured(asof_ns=regular_end + MINUTE_NS)
    out = calibrate_history(
        target=target, previous=full_days, minute_index=30,
        evaluation_ns=regular_end + 2 * MINUTE_NS, min_history=3)
    assert out["n_comparable_previous"] == 4
    assert out["n_daily_session_duration_matches"] == 0
    assert out["n_daily_session_duration_mismatches"] == 4
    assert out["daily_object_ranks"]["DAILY_TOTAL"]["n_prior"] == 0
    assert out["daily_object_ranks"]["DAILY_TOTAL"]["state"] == "INSUFFICIENT_COMPARABLE_HISTORY"
    assert out["minute_conditioned_baseline"]["n_prior"] == 4
    assert out["minute_conditioned_baseline"]["state"] == "NO_ROBUST_DISPERSION"


def test_tied_best_print_is_not_strict_record():
    target=measured(rows=[trade("A",30,shares="1000")])
    prev=history(3,min_print=1000)
    result=calibrate_history(target=target,previous=prev,minute_index=30,
                             evaluation_ns=END+90_000_000_000,min_history=2)
    rank=result["daily_object_ranks"]["SINGLE_PRINT"]
    assert rank["rank_desc"]==3
    assert rank["n_equal_prior"]==1
    assert rank["strict_new_record_in_observed_sample"] is False


def test_minute_conditioning_never_uses_full_day_baseline():
    target=measured(points=[point(30,"40","100"),point(209,"400","500")])
    prev=history(5)
    out=calibrate_history(target=target,previous=prev,minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    minute=out["minute_conditioned_baseline"]
    assert minute["state"]=="OBSERVED_COVERAGE_ONLY"
    assert minute["conditioning"]=="EXACT_MINUTE_INDEX_RTH_CUMULATIVE_ONLY"
    assert minute["minute_index"]==30 and minute["n_prior"]==5
    assert minute["median"]=="0.22"
    assert minute["share"]=="0.4"
    assert minute["robust_z"] is not None
    assert float(minute["robust_z"])>5  # full-day 0.5 would hide the morning event


def test_valid_source_generated_tiny_minute_shares_remain_calibratable():
    # Each input volume fits the bounded source integer-decimal contract,
    # while an exact cumulative participation fraction may need more than
    # the 128 characters allowed for native source amounts.
    large = "1" + "0"*127
    target = measured(points=[point(30,"4",large),point(209,"4",large)])
    prior = [
        measured("2026-09-"+str(i).zfill(2),
                 rows=[trade("p"+str(i),30,shares="500")],
                 points=[point(30,str(i),large),point(209,str(i),large)])
        for i in (1,2,3)
    ]
    result = calibrate_history(
        target=target, previous=prior, minute_index=30,
        evaluation_ns=END+90_000_000_000, min_history=3)
    assert result["minute_conditioned_baseline"]["state"]=="OBSERVED_COVERAGE_ONLY"
    assert result["minute_conditioned_baseline"]["n_prior"]==3
    assert result["minute_conditioned_baseline"]["robust_z"] is not None


def test_missing_or_nonmatching_minute_is_not_filled_from_daily():
    target=measured(points=[point(209,"400","500")])
    out=calibrate_history(target=target,previous=history(5),minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["minute_conditioned_baseline"]["state"]=="TARGET_MINUTE_SOURCE_UNQUALIFIED"
    assert out["minute_conditioned_baseline"]["robust_z"] is None
    target=measured(points=[point(30,"40","100",prefix=False)])
    out=calibrate_history(target=target,previous=history(5),minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["minute_conditioned_baseline"]["state"]=="TARGET_MINUTE_SOURCE_UNQUALIFIED"


def test_split_basis_is_quarantined_not_rebased_from_jump():
    target=measured()
    old=history(5)
    for obj in old[:3]:
        obj["split_segment"]="BEFORE_SPLIT"
    out=calibrate_history(target=target,previous=old,minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["excluded_previous"]["SPLIT_BASIS_INCOMPATIBLE"]==3
    assert out["n_comparable_previous"]==2
    assert out["daily_object_ranks"]["DAILY_TOTAL"]["state"]=="INSUFFICIENT_COMPARABLE_HISTORY"
    assert out["minute_conditioned_baseline"]["robust_z"] is None


def test_policy_and_calendar_vintage_mismatches_cannot_rank_as_comparable():
    target = measured()
    prior = history(5)
    # Original source may change venue policy, consolidated volume eligibility
    # or the session/calendar basis without changing the declared split segment.
    for i, (field, digest) in enumerate((
        ("volume_policy_sha256", SHA_B),
        ("exchange_reference_sha256", SHA_A),
        ("calendar_sha256", SHA_D),
    )):
        prior[i] = copy.deepcopy(prior[i])
        prior[i][field] = digest
    result = calibrate_history(
        target=target, previous=prior, minute_index=30,
        evaluation_ns=END + 90_000_000_000, min_history=2)
    assert result["excluded_previous"]["HISTORICAL_POLICY_VINTAGE_INCOMPATIBLE"] == 2
    assert result["excluded_previous"]["HISTORICAL_CALENDAR_VINTAGE_INCOMPATIBLE"] == 1
    assert result["n_comparable_previous"] == 2
    assert result["daily_object_ranks"]["DAILY_TOTAL"]["n_prior"] == 2
    assert result["minute_conditioned_baseline"]["n_prior"] == 2


def test_malformed_source_reference_hashes_cannot_enter_ranks():
    target = measured()
    for field in (
        "source_manifest_sha256", "source_generation_sha256",
        "calendar_sha256", "volume_policy_sha256",
        "exchange_reference_sha256", "split_basis_vintage_sha256",
    ):
        forged = copy.deepcopy(target)
        forged[field] = "not-an-original-source-hash"
        with pytest.raises(HistoricalRulerRefusal, match="target source/authority"):
            calibrate_history(
                target=forged, previous=history(3), minute_index=30,
                evaluation_ns=END+90_000_000_000, min_history=2)
    past = history(3)
    past[0]["source_manifest_sha256"] = "unqualified"
    out = calibrate_history(
        target=target, previous=past, minute_index=30,
        evaluation_ns=END+90_000_000_000, min_history=2)
    assert out["excluded_previous"]["HISTORICAL_SOURCE_UNQUALIFIED"] == 1
    assert out["n_comparable_previous"] == 2


def test_derived_daily_source_summaries_must_be_internally_consistent():
    # An immutable original digest is not validation of an altered Python
    # result dict. The historical reader must independently refuse impossible
    # sample sizes, daily notional bounds and observed tier counts.
    target = measured()
    bad_target = copy.deepcopy(target)
    bad_target["largest_individual_print_usd"] = "9999999999"
    with pytest.raises(HistoricalRulerRefusal, match="target source/authority"):
        calibrate_history(
            target=bad_target, previous=history(4), minute_index=30,
            evaluation_ns=END+90_000_000_000, min_history=3)
    prior = history(4)
    prior[0] = copy.deepcopy(prior[0])
    prior[0]["oe_source_notional_usd"] = "1"
    prior[1] = copy.deepcopy(prior[1])
    prior[1]["n_trf_observed"] = prior[1]["n_source_rows"] + 1
    prior[2] = copy.deepcopy(prior[2])
    prior[2]["absolute_block_tier_counts"]["100000"] = 100
    result = calibrate_history(
        target=target, previous=prior, minute_index=30,
        evaluation_ns=END+90_000_000_000, min_history=3)
    assert result["excluded_previous"]["HISTORICAL_SOURCE_UNQUALIFIED"] == 3
    assert result["n_comparable_previous"] == 1
    assert result["daily_object_ranks"]["DAILY_TOTAL"]["n_prior"] == 1


def test_tampered_historical_minute_ratio_and_availability_are_quarantined():
    original = measured()
    past = history(5)
    tampered_ratio = copy.deepcopy(past)
    tampered_ratio[0]["minute_points_private_only"][0]["share"] = "0.95"
    out = calibrate_history(
        target=original, previous=tampered_ratio, minute_index=30,
        evaluation_ns=END + 90_000_000_000, min_history=3)
    assert out["excluded_previous"]["HISTORICAL_SOURCE_UNQUALIFIED"] == 1
    assert out["minute_conditioned_baseline"]["n_prior"] == 4
    late = copy.deepcopy(past)
    late[0]["minute_points_private_only"][0]["source_available_ns"] = (
        late[0]["asof_ns"] + 1)
    out2 = calibrate_history(
        target=original, previous=late, minute_index=30,
        evaluation_ns=END + 90_000_000_000, min_history=3)
    assert out2["excluded_previous"]["HISTORICAL_SOURCE_UNQUALIFIED"] == 1


def test_historical_cumulative_counts_cannot_decrease_after_derived_tamper():
    current = measured()
    previous = history(4)
    forged = copy.deepcopy(previous[0])
    forged["minute_points_private_only"][1]["oe_shares"] = "1"
    forged["minute_points_private_only"][1]["share"] = "0.005"
    previous[0] = forged
    result = calibrate_history(
        target=current, previous=previous, minute_index=30,
        evaluation_ns=END+90_000_000_000, min_history=3)
    assert result["excluded_previous"]["HISTORICAL_SOURCE_UNQUALIFIED"] == 1


def test_tampered_target_minute_ratio_rejected_before_calibration():
    value = measured()
    value["minute_points_private_only"][0]["share"] = "1.3"
    with pytest.raises(HistoricalRulerRefusal, match="target source/authority"):
        calibrate_history(
            target=value, previous=history(5), minute_index=30,
            evaluation_ns=END + 90_000_000_000, min_history=3)


def test_causal_availability_and_duplicate_revision_seam():
    prev=history(5)
    future=copy.deepcopy(prev[0])
    future["asof_ns"]=END+900_000_000_000
    old=copy.deepcopy(prev)
    old[0]=future
    out=calibrate_history(target=measured(),previous=old,minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["excluded_previous"]["HISTORICAL_REVISION_NOT_AVAILABLE"]==1
    with pytest.raises(HistoricalRulerRefusal,match="duplicate"):
        calibrate_history(target=measured(),previous=[prev[0],prev[0]],
                          minute_index=30,evaluation_ns=END+90_000_000_000,
                          min_history=2)


def test_later_historical_revision_cannot_backfill_original_target_baseline():
    target = measured()
    prior = history(4)
    # The later researcher asks after a revision was received, but the
    # target source snapshot had already closed. Never retroactively let
    # the amended historical observation affect an as-seen target rank.
    later = copy.deepcopy(prior[0])
    later["asof_ns"] = target["asof_ns"] + 20_000_000_000
    prior[0] = later
    out = calibrate_history(
        target=target, previous=prior, minute_index=30,
        evaluation_ns=target["asof_ns"] + 30_000_000_000,
        min_history=3)
    assert out["excluded_previous"]["HISTORICAL_REVISION_NOT_AVAILABLE"] == 1
    assert out["n_comparable_previous"] == 3
    assert out["minute_conditioned_baseline"]["n_prior"] == 3


def test_thin_history_and_zero_mad_are_not_invented():
    target=measured()
    out=calibrate_history(target=target,previous=history(1),minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["daily_object_ranks"]["DAILY_TOTAL"]["rank_desc"] is None
    assert out["minute_conditioned_baseline"]["state"]=="INSUFFICIENT_MINUTE_MATCHED_HISTORY"
    # Build source-consistent flat baseline fixtures instead of mutating
    # derived ratios independently of their recorded share denominators.
    flat=[
        measured("2026-09-"+str(i+1).zfill(2),
                 rows=[trade("flat"+str(i),30,shares="500")],
                 points=[point(30,"20","100"),point(209,"100","200")])
        for i in range(4)
    ]
    out=calibrate_history(target=target,previous=flat,minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["minute_conditioned_baseline"]["state"]=="NO_ROBUST_DISPERSION"
    assert out["minute_conditioned_baseline"]["robust_z"] is None


def test_partial_target_only_allows_minute_baseline_not_daily_rank():
    target=measured(full_rth_covered=False,watermark_complete_ns=BASE+60*MINUTE_NS,
                    points=[point(30,"40","100")])
    out=calibrate_history(target=target,previous=history(4),minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["daily_object_ranks"]["DAILY_TOTAL"]["state"]=="NOT_FULL_RTH"
    assert out["minute_conditioned_baseline"]["state"]=="OBSERVED_COVERAGE_ONLY"


def test_live_morning_partial_rth_can_request_minute_baseline_before_close():
    morning=BASE+60*MINUTE_NS
    target=measured(full_rth_covered=False,
                    asof_ns=morning+4_000_000,
                    watermark_complete_ns=morning,
                    watermark_available_ns=morning+1_000_000,
                    points=[point(30,"40","100")])
    out=calibrate_history(target=target,previous=[],minute_index=30,
                          evaluation_ns=morning+5_000_000,min_history=2)
    assert out["daily_object_ranks"]["DAILY_TOTAL"]["state"]=="NOT_FULL_RTH"
    assert out["minute_conditioned_baseline"]["state"]=="INSUFFICIENT_MINUTE_MATCHED_HISTORY"
    assert out["minute_conditioned_baseline"]["share"]=="0.4"


def test_forged_candidate_authority_cannot_become_comparable_history():
    target=measured()
    forged=copy.deepcopy(target)
    forged["public_delivery_allowed"]=True
    with pytest.raises(HistoricalRulerRefusal,match="target.*authority"):
        calibrate_history(target=forged,previous=history(4),minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=2)
    candidate=history(4)
    candidate[0]["ranking_trading_alert_authority"]=True
    out=calibrate_history(target=target,previous=candidate,minute_index=30,
                          evaluation_ns=END+90_000_000_000,min_history=3)
    assert out["excluded_previous"]["HISTORICAL_SOURCE_UNQUALIFIED"]==1


def test_no_op_research_only_is_not_a_live_source_or_named_ats():
    from engine import tpb_historical_ruler
    assert not hasattr(tpb_historical_ruler,"connect")
    assert not hasattr(tpb_historical_ruler,"publish")
    out=calibrate_history(target=measured(),previous=[],minute_index=30,
                          evaluation_ns=END+90_000_000_000)
    assert out["signal"] is None
    assert out["named_ats_attribution"] is None
    assert out["source_authenticated"] is False
    assert out["ranking_trading_alert_authority"] is False
