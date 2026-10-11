"""Synthetic BOATS overnight tape receipts: read-only quality, no vendor calls."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest
import pyarrow as pa
import pyarrow.parquet as pq

import collectors.tiingo_archive as a
from lib.dataos.temporal import utc
from lib.dataos.tiingo_reader import TiingoViewRefusal
from lib.dataos.tiingo_boats_tape import audit_boats_tape
from scripts.tiingo_materialize import materialize_one

CUT = "2026-10-10T00:00:00Z"
START = "2026-10-09T00:00:00Z"
END = "2026-10-09T03:59:00Z"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "tiingo", check_mount=False, free_floor=0)


def frame(kind, event_at="2026-10-09T01:00:00Z", ticker="AMD", *,
          price=100.0, shares=20, conditions=("@", "F", "", "X"),
          epoch_shift_ns=0, bid=99.9, ask=100.1, mid=100.0):
    instant = utc(event_at)
    delta = instant - datetime(1970, 1, 1, tzinfo=timezone.utc)
    ns = int((delta.days * 86400 + delta.seconds) * 10**9
             + delta.microseconds * 1000 + epoch_shift_ns)
    if kind == "Q":
        data = [kind, event_at, ns, ticker, 10, bid, mid, ask, 20]
    else:
        data = [kind, event_at, ns, ticker, price, shares, *conditions]
    return json.dumps({"service": "boats", "messageType": "A", "data": data},
                      separators=(",", ":"))


def saved(lake, items):
    r = lake.store_boats_batch(items)
    path = next(
        file for file in (lake.root / "receipts" / "boats-firehose").rglob("*.json")
        if json.loads(file.read_text())["raw_sha256"] == r["raw_sha256"]
    )
    receipt = json.loads(path.read_text())
    assert materialize_one(lake.root, receipt, free_floor=0)["status"] == "WRITTEN"
    return receipt["first_received_at_utc"][:10], r["raw_sha256"]


def audit(lake, refs, **kwargs):
    opts = {
        "root": lake.root, "check_mount": False, "refs": refs,
        "vendor_symbol": "AMD",
        "start_event_at_utc": START, "end_event_at_utc": END,
        "observed_before_utc": CUT,
    }
    opts.update(kwargs)
    return audit_boats_tape(**opts)


def test_trade_breaks_and_unknown_frames_are_not_executed_volume(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:01Z", frame("Q")),
        ("2026-10-09T01:00:02Z", frame("T", "2026-10-09T01:00:01Z",
                                     price=100.08, shares=20)),
        ("2026-10-09T01:00:03Z", frame("B", "2026-10-09T01:00:02Z",
                                     price=100.08, shares=12,
                                     conditions=("@", "F", "T", "H"))),
        ("2026-10-09T01:00:04Z",
         json.dumps({"service": "boats", "messageType": "I", "data": []})),
    ])
    out = audit(lake, [ref])
    assert out["status"] == "OBSERVED_SOURCE_EVENTS_NOT_COVERAGE_PROOF"
    assert out["source_messages_all_tickers"] == 4
    assert out["source_event_kind_counts_all_tickers"] == {
        "Q": 1, "T": 1, "B": 1, "other": 1}
    assert out["selected_kind_counts"] == {"Q": 1, "T": 1, "B": 1}
    assert out["selected_symbol_events"] == 3
    assert out["observed_unfiltered_T_message_shares"] == 20
    assert out["observed_B_trade_break_message_shares_NOT_NETTED"] == 12
    assert out["examples"][2]["raw_sale_conditions"] == ["@", "F", "T", "H"]
    assert out["source_message_projection_reverified"]
    assert out["raw_source_bytes_reverified"]
    assert not out["nbbo"]
    assert not out["net_executed_volume_proven"]
    assert not out["order_level_liquidity_replenishment_proven"]
    assert not out["transport_continuity_proven"]
    assert not out["time_window_completeness_proven"]
    assert not out["trade_initiator_side_proven"]
    assert not out["point_in_time_backtest_eligible"]
    assert not out["redistribution_admitted"]
    assert out["network"] is False and out["writes"] is False


def test_other_tickers_are_not_counted_as_requested_symbol(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:01Z", frame("T", ticker="AMD")),
        ("2026-10-09T01:00:02Z", frame("T", ticker="NVDA", shares=200)),
    ])
    out = audit(lake, [ref])
    assert out["selected_symbol_events"] == 1
    assert out["distinct_symbols_in_selected_segments"] == 2
    assert out["observed_unfiltered_T_message_shares"] == 20
    assert out["source_messages_all_tickers"] == 2


def test_selected_event_time_window_does_not_assume_entire_session(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:01Z", frame("Q")),
        ("2026-10-09T02:00:01Z", frame("Q", event_at="2026-10-09T02:00:00Z")),
    ])
    out = audit(lake, [ref],
                start_event_at_utc="2026-10-09T02:00:00Z",
                end_event_at_utc="2026-10-09T02:00:00Z")
    assert out["selected_symbol_events"] == 1
    assert out["source_messages_all_tickers"] == 2
    assert out["time_window_completeness_proven"] is False


def test_quote_cross_and_mid_discrepancy_are_diagnostics_not_nbbo(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:02Z", frame("Q", bid=101, ask=100, mid=110))
    ])
    out = audit(lake, [ref])
    assert out["quality_flags"]["venue_crossed_quotes"] == 1
    assert out["quality_flags"]["venue_mid_vs_quote_discrepancy_gt_half_cent"] == 1
    assert out["nbbo"] is False
    assert out["venue_scope"] == "SINGLE_ATS_TOP_OF_BOOK_AND_LAST_SALE_ONLY"


def test_late_and_clock_disagreement_are_flagged_not_silently_reinterpreted(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:30Z", frame("T", epoch_shift_ns=3_000_000_000))
    ])
    out = audit(lake, [ref])
    assert out["status"] == "UNQUALIFIED_CLOCKS"
    assert out["quality_flags"]["vendor_datetime_epoch_disagreement_gt_1s"] == 1
    assert out["quality_flags"]["event_to_local_capture_lag_gt_15s"] == 1
    assert out["event_to_local_capture_lag_p95_nonnegative_ms"] == 27_000


def test_repeated_raw_frames_across_segments_are_counted_not_removed(lake):
    raw = frame("T")
    first = saved(lake, [("2026-10-09T01:00:01Z", raw)])
    second = saved(lake, [("2026-10-09T01:00:02Z", raw)])
    out = audit(lake, [second, first])
    assert out["selected_symbol_events"] == 2
    assert out["quality_flags"]["identical_frame_repeats_not_deduplicated"] == 1
    assert out["observed_unfiltered_T_message_shares"] == 40


def test_out_of_arrival_order_epoch_is_counted(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:04Z", frame("Q", "2026-10-09T01:00:03Z")),
        ("2026-10-09T01:00:05Z", frame("T", "2026-10-09T01:00:02Z")),
    ])
    out = audit(lake, [ref])
    assert out["quality_flags"]["event_epoch_out_of_arrival_order"] == 1
    assert out["transport_continuity_proven"] is False


def test_source_batch_capture_cutoff_is_all_or_nothing(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:01Z", frame("Q")),
        ("2026-10-09T01:01:01Z", frame("T", "2026-10-09T01:01:00Z")),
    ])
    with pytest.raises(TiingoViewRefusal, match="extends beyond"):
        audit(lake, [ref], observed_before_utc="2026-10-09T01:00:30Z")


def test_false_received_interval_refuses_without_repair(lake):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("T"))])
    file = next((lake.root / "receipts" / "boats-firehose").rglob("*.json"))
    record = json.loads(file.read_text())
    record["last_received_at_utc"] = "2026-10-09T00:00:00Z"
    file.write_text(json.dumps(record))
    with pytest.raises(TiingoViewRefusal, match="bounds invalid"):
        audit(lake, [ref])


def test_modified_parquet_with_rehashed_manifest_cannot_forge_trade(lake):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("T", shares=20))])
    day, digest = ref
    manifest = lake.root / "manifests" / "boats-firehose" / day / (digest + ".json")
    m = json.loads(manifest.read_text())
    artifact = lake.root / m["output_path"]
    rows = pq.read_table(artifact).to_pylist()
    rows[0]["last_size"] = 2_000_000
    pq.write_table(pa.Table.from_pylist(rows), artifact)
    m["output_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(m))
    with pytest.raises(TiingoViewRefusal, match="original source projection"):
        audit(lake, [ref])


def test_original_raw_corruption_blocks_entire_tape(lake):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("T"))])
    file = next((lake.root / "receipts" / "boats-firehose").rglob("*.json"))
    receipt = json.loads(file.read_text())
    (lake.root / receipt["raw_path"]).write_bytes(b"corrupt")
    with pytest.raises(TiingoViewRefusal, match="raw"):
        audit(lake, [ref])


def test_raw_count_receipt_tamper_fails_closed(lake):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("Q"))])
    file = next((lake.root / "receipts" / "boats-firehose").rglob("*.json"))
    receipt = json.loads(file.read_text())
    receipt["counts"]["T"] += 1
    file.write_text(json.dumps(receipt))
    with pytest.raises(TiingoViewRefusal, match="line count differs"):
        audit(lake, [ref])


def test_overnight_ET_classification_honors_DST_without_nbbo_claim(lake):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("T"))])
    out = audit(lake, [ref])
    assert "event_outside_documented_overnight_ET" not in out["quality_flags"]
    assert out["nbbo"] is False


def test_valid_frame_unsupported_ticker_or_time_never_claims_coverage(lake):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("Q", ticker="NVDA"))])
    out = audit(lake, [ref])
    assert out["selected_symbol_events"] == 0
    assert out["time_window_completeness_proven"] is False
    assert out["source_messages_all_tickers"] == 1


@pytest.mark.parametrize("kwargs", [
    {"vendor_symbol": ""},
    {"refs": []},
    {"observed_before_utc": "2026-10-09"},
    {"start_event_at_utc": "2026-10-10T00:00:00Z",
     "end_event_at_utc": "2026-10-09T00:00:00Z"},
    {"max_captures": True},
    {"max_events_per_capture": 0},
    {"max_observations": 0},
    {"max_examples": 26},
])
def test_budget_time_or_identity_invalid_refused(lake, kwargs):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("T"))])
    params = dict(kwargs)
    refs = params.pop("refs", [ref])
    with pytest.raises(TiingoViewRefusal):
        audit(lake, refs, **params)


def test_local_tape_read_has_no_provider_or_secret_access(lake, monkeypatch):
    ref = saved(lake, [("2026-10-09T01:00:01Z", frame("T"))])
    def forbidden(*args, **kwargs):
        pytest.fail("BOATS tape audit contacted provider or secret")
    monkeypatch.setattr(a, "read_key", forbidden)
    monkeypatch.setattr(a, "collect_one", forbidden)
    from scripts import tiingo_ingest
    monkeypatch.setattr(tiingo_ingest, "boats_stream", forbidden)
    before = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in lake.root.rglob("*") if p.is_file()
    }
    out = audit(lake, [ref])
    after = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in lake.root.rglob("*") if p.is_file()
    }
    assert out["network"] is False and out["writes"] is False
    assert before == after



def test_same_segment_fresh_quote_age_is_observational_only(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z",
         frame("Q", event_at="2026-10-09T01:00:00Z")),
        ("2026-10-09T01:00:00.400Z",
         frame("T", event_at="2026-10-09T01:00:00.300Z",
               conditions=("@", "F", "", "X"))),
    ])
    out = audit(lake, [ref])
    quality = out["trade_quote_age_diagnostics"]
    assert quality["max_age_ms"] == 1000
    assert quality["observed_T_messages"] == 1
    assert quality["fresh_prior_venue_quote"] == 1
    assert quality["fresh_quote_age_p95_ms"] == 300
    assert quality["unqualified_sale_conditions_present"] == 1
    trade = next(e for e in out["examples"] if e["kind"] == "T")
    assert trade["prior_venue_quote_age_ms"] == 300
    assert trade["prior_venue_quote_status"] == "FRESH_SINGLE_ATS_QUOTE_NOT_NBBO"
    assert out["trade_initiator_side_proven"] is False
    assert out["order_level_liquidity_replenishment_proven"] is False
    assert out["net_executed_volume_proven"] is False


def test_quote_stale_and_no_prior_quotes_are_separate_not_hidden(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z", frame("T", event_at="2026-10-09T01:00:00Z")),
        ("2026-10-09T01:00:01.100Z", frame("Q", event_at="2026-10-09T01:00:01Z")),
        ("2026-10-09T01:00:05.100Z", frame("T", event_at="2026-10-09T01:00:05Z")),
    ])
    out = audit(lake, [ref])
    x = out["trade_quote_age_diagnostics"]
    assert x["observed_T_messages"] == 2
    assert x["no_prior_quote"] == 1
    assert x["stale_prior_venue_quote"] == 1
    assert x["fresh_prior_venue_quote"] == 0


def test_prior_quotes_do_not_leak_across_unproven_segment_boundary(lake):
    a1 = saved(lake, [("2026-10-09T01:00:00.100Z",
                       frame("Q", event_at="2026-10-09T01:00:00Z"))])
    a2 = saved(lake, [("2026-10-09T01:00:00.200Z",
                       frame("T", event_at="2026-10-09T01:00:00.150Z"))])
    x = audit(lake, [a1, a2])["trade_quote_age_diagnostics"]
    assert x["no_prior_quote"] == 1
    assert x["fresh_prior_venue_quote"] == 0


def test_quote_arriving_after_trade_cannot_be_used_as_hindsight(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:01.000Z",
         frame("T", event_at="2026-10-09T01:00:00.500Z")),
        ("2026-10-09T01:00:01.100Z",
         frame("Q", event_at="2026-10-09T01:00:00.200Z")),
    ])
    q = audit(lake, [ref])["trade_quote_age_diagnostics"]
    assert q["no_prior_quote"] == 1
    assert q["fresh_prior_venue_quote"] == 0


def test_out_of_order_trade_epoch_cannot_join_future_event_quote(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z", frame("Q", event_at="2026-10-09T01:00:00Z")),
        ("2026-10-09T01:00:00.200Z", frame("T", event_at="2026-10-09T00:59:59.900Z")),
    ])
    q = audit(lake, [ref])
    assert q["trade_quote_age_diagnostics"]["quote_newer_than_trade"] == 1
    assert q["trade_quote_age_diagnostics"]["fresh_prior_venue_quote"] == 0


def test_trade_break_is_not_a_new_quote_matched_execution(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z", frame("Q", event_at="2026-10-09T01:00:00Z")),
        ("2026-10-09T01:00:00.200Z", frame("B", event_at="2026-10-09T01:00:00.100Z")),
    ])
    out = audit(lake, [ref])
    assert out["trade_quote_age_diagnostics"]["observed_T_messages"] == 0
    assert out["trade_quote_age_diagnostics"]["fresh_prior_venue_quote"] == 0
    assert out["selected_kind_counts"]["B"] == 1


def test_invalid_venue_quote_cannot_count_as_qualified_quote(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z",
         frame("Q", event_at="2026-10-09T01:00:00Z", bid=101, ask=100)),
        ("2026-10-09T01:00:00.200Z",
         frame("T", event_at="2026-10-09T01:00:00.100Z")),
    ])
    x = audit(lake, [ref])["trade_quote_age_diagnostics"]
    assert x["no_prior_quote"] == 1
    assert x["fresh_prior_venue_quote"] == 0


def test_quote_age_limit_is_explicit_bounded_research_control(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z", frame("Q", event_at="2026-10-09T01:00:00Z")),
        ("2026-10-09T01:00:00.500Z",
         frame("T", event_at="2026-10-09T01:00:00.400Z")),
    ])
    q = audit(lake, [ref], quote_max_age_ms=250)
    assert q["trade_quote_age_diagnostics"]["stale_prior_venue_quote"] == 1
    assert q["trade_quote_age_diagnostics"]["max_age_ms"] == 250
    with pytest.raises(TiingoViewRefusal):
        audit(lake, [ref], quote_max_age_ms=True)
    with pytest.raises(TiingoViewRefusal):
        audit(lake, [ref], quote_max_age_ms=0)
    with pytest.raises(TiingoViewRefusal):
        audit(lake, [ref], quote_max_age_ms=60001)



def test_quote_event_epoch_mismatch_cannot_be_a_fresh_precursor(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z",
         frame("Q", event_at="2026-10-09T01:00:00Z",
               epoch_shift_ns=3_000_000_000)),
        ("2026-10-09T01:00:00.400Z",
         frame("T", event_at="2026-10-09T01:00:00.300Z")),
    ])
    x = audit(lake, [ref])
    assert x["trade_quote_age_diagnostics"]["fresh_prior_venue_quote"] == 0
    assert x["trade_quote_age_diagnostics"]["no_prior_quote"] == 1
    assert x["status"] == "UNQUALIFIED_CLOCKS"


def test_quote_from_another_vendor_symbol_never_counts_as_prior_venue_quote(lake):
    ref = saved(lake, [
        ("2026-10-09T01:00:00.100Z",
         frame("Q", event_at="2026-10-09T01:00:00Z", ticker="NVDA")),
        ("2026-10-09T01:00:00.400Z",
         frame("T", event_at="2026-10-09T01:00:00.300Z", ticker="AMD")),
    ])
    x = audit(lake, [ref])
    assert x["trade_quote_age_diagnostics"]["fresh_prior_venue_quote"] == 0
    assert x["trade_quote_age_diagnostics"]["no_prior_quote"] == 1
    assert x["distinct_symbols_in_selected_segments"] == 2
    assert x["trade_initiator_side_proven"] is False
