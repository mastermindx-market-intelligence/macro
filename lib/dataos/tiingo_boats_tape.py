"""Read-only evidence audit of Tiingo/BOATS single-ATS overnight tape captures.

Never consumes API credentials, contacts the vendor, starts a stream, infers
NBBO/consolidated quotes, treats trade breaks as positive trading volume,
constructs order-level replenishment, certifies session coverage, or admits PIT
backtests. Uses the existing Tiingo L0 receipt and research L1 reader only.

Tiingo source schema: https://www.tiingo.com/documentation/websockets/boats
9-slot Q top-of-book; 10-slot T trade / B trade-break; epoch nanoseconds
since POSIX UTC; four raw sale-condition positions.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from lib.dataos.temporal import utc
from lib.dataos.tiingo_reader import (
    TiingoViewRefusal, SHA, _unique_raw_context, read_research_view,
)
from lib.dataos.tiingo_views import boats_messages
from scripts.tiingo_materialize import verified_raw
from collectors.tiingo_archive import (
    DEFAULT_ARCHIVE, TiingoArchiveError, require_external_root,
)

MAX_CAPTURES = 32
MAX_EVENTS_PER_CAPTURE = 20000
MAX_OBSERVATIONS = 100_000
MAX_EXAMPLES = 25
CLOCK_DIFFERENCE_NS = 1_000_000_000
EARLY_RECEIPT_THRESHOLD_NS = 1_000_000_000
STALE_CAPTURE_THRESHOLD_NS = 15_000_000_000
UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NEW_YORK = ZoneInfo("America/New_York")


def _ns(clock: datetime) -> int:
    delta = clock - UTC_EPOCH
    return ((delta.days * 86_400 + delta.seconds) * 1_000_000
            + delta.microseconds) * 1000


def _metric_number(value: Any, field: str, *, nullable: bool = False) -> float | None:
    if nullable and value is None:
        return None
    if type(value) not in (int, float):
        raise TiingoViewRefusal(f"BOATS {field} is not a numeric source value")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise TiingoViewRefusal(f"BOATS {field} must be finite and nonnegative")
    return out


def _share_count(value: Any, field: str, *, nullable: bool = False) -> int | None:
    if nullable and value is None:
        return None
    if type(value) is not int or value < 0 or value > 2**31 - 1:
        raise TiingoViewRefusal(f"BOATS {field} must be a nonnegative int32")
    return value


def _event_quality(row: dict[str, Any]) -> tuple[datetime, int, datetime, int, list[str]]:
    kind = row.get("kind")
    if kind not in ("Q", "T", "B"):
        raise TiingoViewRefusal("BOATS projection includes unrecognized event kind")
    epoch = row.get("event_epoch_ns")
    if type(epoch) is not int or not 0 <= epoch <= 2**63 - 1:
        raise TiingoViewRefusal("BOATS event epoch must be int64 nanoseconds")
    try:
        event_clock = utc(row.get("event_datetime"))
        received_clock = utc(row.get("received_at"))
    except (ValueError, TypeError) as exc:
        raise TiingoViewRefusal("BOATS event/receive clocks must have explicit timezones") from exc
    conditions: list[str] = []
    if kind == "Q":
        for x in ("bid_size", "ask_size"):
            _share_count(row.get(x), x, nullable=True)
        for x in ("bid_raw", "mid_vendor", "ask_raw"):
            _metric_number(row.get(x), x, nullable=True)
    else:
        _share_count(row.get("last_size"), "last_size")
        _metric_number(row.get("last_raw"), "last_raw")
        conditions = row.get("sale_conditions")
        if (not isinstance(conditions, list) or len(conditions) != 4
                or any(not isinstance(c, str) or len(c) > 1 for c in conditions)):
            raise TiingoViewRefusal("BOATS four sale-condition slots must remain distinct")
        if (row.get("is_break") is True) != (kind == "B"):
            raise TiingoViewRefusal("BOATS trade-break flag inconsistent with message kind")
    return event_clock, epoch, received_clock, _ns(received_clock) - epoch, conditions


def _verified_segment(base: Path, day: str, digest: str, max_events: int
                     ) -> tuple[dict[str, Any], list[dict[str, Any]], datetime, datetime]:
    view = read_research_view(
        "boats-firehose", day, digest, root=base, purpose="INSPECTION",
        max_rows=max_events, check_mount=False,
    )
    receipt = _unique_raw_context(base, "boats-firehose", day, digest)
    if (receipt.get("schema") != "mastermind.tiingo.boats_firehose_receipt.v1"
            or receipt.get("vendor") != "tiingo"
            or receipt.get("venue") != "BOATS"
            or receipt.get("nbbo") is not False
            or receipt.get("transport_continuity") != "NOT_PROVEN"):
        raise TiingoViewRefusal("BOATS receipt violates source/venue/continuity contract")
    counts = receipt.get("counts")
    if not isinstance(counts, dict) or set(counts) != {"Q", "T", "B", "other"}:
        raise TiingoViewRefusal("BOATS raw event count classifications absent")
    if any(type(c) is not int or c < 0 for c in counts.values()):
        raise TiingoViewRefusal("BOATS raw event counts invalid")
    total = sum(counts.values())
    if total < 1 or total > max_events:
        raise TiingoViewRefusal("BOATS segment outside bounded message capacity")
    try:
        first = utc(receipt["first_received_at_utc"])
        last = utc(receipt["last_received_at_utc"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TiingoViewRefusal("BOATS original receipt observation interval invalid") from exc
    if first > last or first.date().isoformat() != day:
        raise TiingoViewRefusal("BOATS original receipt observation bounds invalid")
    try:
        raw = verified_raw(base, receipt)
    except (TiingoArchiveError, OSError, EOFError, ValueError, KeyError) as exc:
        raise TiingoViewRefusal("BOATS source bytes could not be verified") from exc
    if type(receipt.get("raw_bytes")) is not int or len(raw) != receipt["raw_bytes"]:
        raise TiingoViewRefusal("BOATS raw receipt size inconsistent with original bytes")
    if raw.count(b"\n") != total:
        raise TiingoViewRefusal("BOATS source batch line count differs from receipt")
    try:
        parsed = boats_messages(raw.splitlines(), receipt)
    except (ValueError, TypeError, KeyError, TiingoArchiveError, OverflowError) as exc:
        raise TiingoViewRefusal("BOATS raw source cannot be projected consistently") from exc
    by_kind = Counter(x["kind"] for x in parsed)
    if any(by_kind[k] != counts[k] for k in ("Q", "T", "B")):
        raise TiingoViewRefusal("BOATS projected quote/trade counts disagree with receipt")
    if len(parsed) + counts["other"] != total:
        raise TiingoViewRefusal("BOATS unparsed frames disagree with source receipt")
    # A mutable Parquet + rehashed mutable manifest cannot invent new BOATS
    # prices/events/conditions if the original immutable body is still present.
    # The materializer unions sparse Q/T/B columns, supplying nulls for blanks.
    keys = sorted({k for row in parsed for k in row})
    expected = [{key: row.get(key) for key in keys} for row in parsed]
    if expected != list(view.rows):
        raise TiingoViewRefusal("BOATS research rows disagree with original source projection")
    return receipt, expected, first, last


def audit_boats_tape(
    refs: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    *,
    vendor_symbol: str,
    start_event_at_utc: str,
    end_event_at_utc: str,
    observed_before_utc: str,
    root: Path = DEFAULT_ARCHIVE,
    max_captures: int = 16,
    max_events_per_capture: int = MAX_EVENTS_PER_CAPTURE,
    max_observations: int = MAX_OBSERVATIONS,
    max_examples: int = 10,
    quote_max_age_ms: int = 1000,
    source_silence_threshold_ms: int = 5000,
    check_mount: bool = True,
) -> dict[str, Any]:
    """Summarize venue-native BOATS events from explicitly selected local L0/L1.

    No market-wide coverage, trading volume net of cancellations, true
    replenishment, venue-join, order-level causality or consolidated NBBO.
    All actual capture receipts must be fully observed before the cutoff.
    """
    if not isinstance(vendor_symbol, str) or not vendor_symbol or len(vendor_symbol) > 96:
        raise TiingoViewRefusal("BOATS audit requires an exact vendor symbol")
    if (type(max_captures) is not int or not 1 <= max_captures <= MAX_CAPTURES
            or type(max_events_per_capture) is not int
            or not 1 <= max_events_per_capture <= MAX_EVENTS_PER_CAPTURE
            or type(max_observations) is not int
            or not 1 <= max_observations <= MAX_OBSERVATIONS
            or type(max_examples) is not int or not 0 <= max_examples <= MAX_EXAMPLES
            or type(quote_max_age_ms) is not int or not 1 <= quote_max_age_ms <= 60000
            or type(source_silence_threshold_ms) is not int
            or not 1 <= source_silence_threshold_ms <= 60000):
        raise TiingoViewRefusal("invalid bounded BOATS analysis budgets")
    if not isinstance(refs, (tuple, list)) or not 1 <= len(refs) <= max_captures:
        raise TiingoViewRefusal("invalid bounded BOATS capture list")
    if any(not isinstance(ref, (tuple, list)) or len(ref) != 2
           or type(ref[0]) is not str or type(ref[1]) is not str
           or not SHA.fullmatch(ref[1]) for ref in refs):
        raise TiingoViewRefusal("BOATS capture reference must be exact day/SHA256")
    ref_tuples = [(x[0], x[1]) for x in refs]
    if len(ref_tuples) != len(set(ref_tuples)):
        raise TiingoViewRefusal("duplicate BOATS capture references cannot prove more data")
    try:
        start = utc(start_event_at_utc)
        end = utc(end_event_at_utc)
        cutoff = utc(observed_before_utc)
    except (ValueError, TypeError) as exc:
        raise TiingoViewRefusal("BOATS analysis requires explicit UTC-offset clocks") from exc
    if start > end:
        raise TiingoViewRefusal("reversed BOATS event-time range")

    base = require_external_root(root, check_mount=check_mount)
    segments = []
    total_source_messages = 0
    counts_by_kind = Counter()
    for day, digest in ref_tuples:
        receipt, rows, first, last = _verified_segment(
            base, day, digest, max_events_per_capture,
        )
        if last > cutoff:
            raise TiingoViewRefusal("partial BOATS segment extends beyond source capture cutoff")
        segments.append((first, last, digest, rows, receipt))
        total_source_messages += sum(receipt["counts"].values())
        counts_by_kind.update(receipt["counts"])
        if total_source_messages > max_observations:
            raise TiingoViewRefusal("BOATS source messages exceed bounded research budget")
    segments.sort(key=lambda item: (item[0], item[2]))
    # Receipt intervals can reveal an unobserved interval, never prove zero
    # missing upstream events, an uninterrupted socket, or a complete session.
    max_between_segment_gap_ms = 0
    positive_segment_gaps = 0
    overlapping_segment_intervals = 0
    prior_segment_last: datetime | None = None
    for first, last, _, _, _ in segments:
        if prior_segment_last is not None:
            gap_ns = _ns(first) - _ns(prior_segment_last)
            if gap_ns > 0:
                positive_segment_gaps += 1
                max_between_segment_gap_ms = max(
                    max_between_segment_gap_ms, gap_ns // 1_000_000
                )
            elif gap_ns < 0:
                overlapping_segment_intervals += 1
        prior_segment_last = max(prior_segment_last, last) if prior_segment_last else last
    max_within_segment_qtb_gap_ms = 0
    qtb_gaps_exceeding_silence_threshold = 0
    qtb_observations_for_gap_measurement = 0
    source_arrival_regressions_all_tickers = 0
    quality = Counter()
    types = Counter()
    examples: list[dict[str, Any]] = []
    total_traded_shares = 0
    total_break_shares = 0
    seen_raw: set[str] = set()
    latency_nonnegative_ns: list[int] = []
    matched = 0
    symbols_in_source = set()
    quote_matches = Counter()
    matched_quote_ages_ns: list[int] = []
    for first, last, digest, rows, receipt in segments:
        # No cross-segment temporal bridging: receipts do not prove that the
        # interval between two BOATS captures was continuously observed.
        last_quotes: tuple[Any, ...] | None = None
        latest_prior_venue_quote: tuple[int, int] | None = None
        prior_arrival_ns: int | None = None
        prior_QTB_arrival_ns: int | None = None
        # A separate source segment cannot establish continuity with another
        # segment's events; epoch-order diagnosis is intra-segment only.
        last_epoch: int | None = None
        for row in rows:
            symbol = row.get("ticker")
            if not isinstance(symbol, str) or not symbol:
                raise TiingoViewRefusal("BOATS research row missing exact ticker")
            symbols_in_source.add(symbol)
            clock, epoch, received, lag_ns, conditions = _event_quality(row)
            if not first <= received <= last:
                raise TiingoViewRefusal("BOATS frame receipt time outside original capture interval")
            # These are observed Q/T/B frame times, not the full raw transport:
            # the original source receipt may include opaque/control frames.
            current_QTB_arrival_ns = _ns(received)
            qtb_observations_for_gap_measurement += 1
            if prior_QTB_arrival_ns is not None:
                interval_ns = current_QTB_arrival_ns - prior_QTB_arrival_ns
                if interval_ns < 0:
                    source_arrival_regressions_all_tickers += 1
                else:
                    max_within_segment_qtb_gap_ms = max(
                        max_within_segment_qtb_gap_ms, interval_ns // 1_000_000
                    )
                    if interval_ns > source_silence_threshold_ms * 1_000_000:
                        qtb_gaps_exceeding_silence_threshold += 1
            prior_QTB_arrival_ns = current_QTB_arrival_ns
            if symbol != vendor_symbol or not start <= clock <= end:
                continue
            matched += 1
            if matched > max_observations:
                raise TiingoViewRefusal("BOATS selected messages exceed bounded audit budget")
            kind = row["kind"]
            types[kind] += 1
            receive_ns = _ns(received)
            if prior_arrival_ns is not None and receive_ns < prior_arrival_ns:
                quality["source_arrival_timestamp_regression"] += 1
                latest_prior_venue_quote = None
            prior_arrival_ns = receive_ns
            example_quote_age_ms = None
            example_quote_status = None
            fingerprint = row.get("raw_message_sha256")
            if not isinstance(fingerprint, str) or not SHA.fullmatch(fingerprint):
                raise TiingoViewRefusal("BOATS raw frame digest absent")
            if fingerprint in seen_raw:
                quality["identical_frame_repeats_not_deduplicated"] += 1
            else:
                seen_raw.add(fingerprint)
            if last_epoch is not None and epoch < last_epoch:
                quality["event_epoch_out_of_arrival_order"] += 1
            last_epoch = epoch
            if abs(_ns(clock) - epoch) > CLOCK_DIFFERENCE_NS:
                quality["vendor_datetime_epoch_disagreement_gt_1s"] += 1
            if lag_ns < -EARLY_RECEIPT_THRESHOLD_NS:
                quality["source_capture_precedes_event_gt_1s"] += 1
            if lag_ns > STALE_CAPTURE_THRESHOLD_NS:
                quality["event_to_local_capture_lag_gt_15s"] += 1
            latency_nonnegative_ns.append(max(0, lag_ns))
            local = clock.astimezone(NEW_YORK)
            if not (local.hour >= 20 or local.hour < 4):
                quality["event_outside_documented_overnight_ET"] += 1
            if kind == "Q":
                bid, ask, mid = row.get("bid_raw"), row.get("ask_raw"), row.get("mid_vendor")
                if (bid is not None and ask is not None and bid > 0 and ask > 0):
                    if bid > ask:
                        quality["venue_crossed_quotes"] += 1
                    elif bid == ask:
                        quality["venue_locked_quotes"] += 1
                    if mid is not None and abs(mid - (bid + ask) / 2) > 0.005:
                        quality["venue_mid_vs_quote_discrepancy_gt_half_cent"] += 1
                current_quote = (bid, ask, row.get("bid_size"), row.get("ask_size"))
                if current_quote == last_quotes:
                    quality["same_venue_quote_repetition"] += 1
                last_quotes = current_quote
                # A single-ATS quote is a research-age proxy, not NBBO,
                # consolidated depth, or executable bid/ask evidence.
                if (bid is not None and ask is not None
                        and bid > 0 and ask > bid
                        and row.get("bid_size") is not None
                        and row.get("ask_size") is not None
                        and row["bid_size"] > 0 and row["ask_size"] > 0
                        and abs(_ns(clock) - epoch) <= CLOCK_DIFFERENCE_NS
                        and lag_ns >= -EARLY_RECEIPT_THRESHOLD_NS):
                    latest_prior_venue_quote = (epoch, receive_ns)
                else:
                    # A newer unqualified quote supersedes the earlier quote.
                    # Do not mask it by retaining a stale "good" quote.
                    latest_prior_venue_quote = None
                    quality["venue_quote_not_qualifiable_for_age_proxy"] += 1
            elif kind == "T":
                total_traded_shares += _share_count(row["last_size"], "last_size")
                quote_matches["observed_T_messages"] += 1
                if any(conditions):
                    # Special sale conditions remain unqualified; quote age
                    # cannot establish an eligible trade or aggressor side.
                    quote_matches["unqualified_sale_conditions_present"] += 1
                if (abs(_ns(clock) - epoch) > CLOCK_DIFFERENCE_NS
                        or lag_ns < -EARLY_RECEIPT_THRESHOLD_NS):
                    example_quote_status = "EVENT_OR_CAPTURE_CLOCK_UNQUALIFIED"
                    quote_matches["trade_temporal_clock_unqualified"] += 1
                elif latest_prior_venue_quote is None:
                    example_quote_status = "NO_PRIOR_SAME_SEGMENT_VENUE_QUOTE"
                    quote_matches["no_prior_quote"] += 1
                else:
                    quote_epoch_ns, quote_received_ns = latest_prior_venue_quote
                    if receive_ns < quote_received_ns or epoch < quote_epoch_ns:
                        example_quote_status = "PRIOR_QUOTE_NEWER_THAN_TRADE_EVENT"
                        quote_matches["quote_newer_than_trade"] += 1
                    else:
                        age_ns = epoch - quote_epoch_ns
                        if age_ns > quote_max_age_ms * 1_000_000:
                            example_quote_status = "STALE_PRIOR_SAME_SEGMENT_VENUE_QUOTE"
                            quote_matches["stale_prior_venue_quote"] += 1
                        else:
                            example_quote_status = "FRESH_SINGLE_ATS_QUOTE_NOT_NBBO"
                            example_quote_age_ms = round(age_ns / 1_000_000, 3)
                            quote_matches["fresh_prior_venue_quote"] += 1
                            matched_quote_ages_ns.append(age_ns)
            else:
                total_break_shares += _share_count(row["last_size"], "last_size")
            if len(examples) < max_examples:
                examples.append({
                    "kind": kind,
                    "ticker": symbol,
                    "source_event_datetime": row["event_datetime"],
                    "source_event_epoch_ns": epoch,
                    "local_received_at": row["received_at"],
                    "event_to_local_capture_lag_ms": round(lag_ns / 1_000_000, 3),
                    "raw_frame_sha256": fingerprint,
                    "venue_bid": row.get("bid_raw") if kind == "Q" else None,
                    "venue_ask": row.get("ask_raw") if kind == "Q" else None,
                    "trade_price": row.get("last_raw") if kind != "Q" else None,
                    "trade_or_break_shares": row.get("last_size") if kind != "Q" else None,
                    "raw_sale_conditions": conditions if kind != "Q" else None,
                    "prior_venue_quote_age_ms": example_quote_age_ms,
                    "prior_venue_quote_status": example_quote_status,
                })
    fresh_quote_age_p95_ms = None
    if matched_quote_ages_ns:
        fresh_quote_age_p95_ms = round(sorted(matched_quote_ages_ns)[
            math.ceil(0.95 * len(matched_quote_ages_ns)) - 1] / 1_000_000, 3)
    lag_p95_ms = None
    if latency_nonnegative_ns:
        lag_p95_ms = round(sorted(latency_nonnegative_ns)[
            math.ceil(0.95 * len(latency_nonnegative_ns)) - 1] / 1_000_000, 3)
    return {
        "schema": "mastermind.tiingo.boats_tape_audit.v1",
        "status": ("UNQUALIFIED_CLOCKS" if (
            quality["vendor_datetime_epoch_disagreement_gt_1s"]
            or quality["source_capture_precedes_event_gt_1s"]
        ) else "OBSERVED_SOURCE_EVENTS_NOT_COVERAGE_PROOF"),
        "vendor": "tiingo",
        "source": "boats-firehose",
        "venue": "BOATS",
        "venue_scope": "SINGLE_ATS_TOP_OF_BOOK_AND_LAST_SALE_ONLY",
        "vendor_symbol": vendor_symbol,
        "start_event_at_utc": start.isoformat(),
        "end_event_at_utc": end.isoformat(),
        "observed_before_utc": cutoff.isoformat(),
        "source_capture_segments_verified": len(segments),
        "source_messages_all_tickers": total_source_messages,
        "source_event_kind_counts_all_tickers": dict(counts_by_kind),
        "capture_observation_gaps": {
            "source_segments": len(segments),
            "source_projected_QTB_observations": qtb_observations_for_gap_measurement,
            "observed_QTB_messages_for_interarrival": qtb_observations_for_gap_measurement,
            "within_segment_silence_threshold_ms": source_silence_threshold_ms,
            "max_positive_within_segment_QTB_arrival_gap_ms": max_within_segment_qtb_gap_ms,
            "within_segment_gaps_exceeding_threshold": qtb_gaps_exceeding_silence_threshold,
            "max_positive_between_segment_arrival_gap_ms": max_between_segment_gap_ms,
            "between_segment_positive_gaps": positive_segment_gaps,
            "overlapping_receipt_intervals": overlapping_segment_intervals,
            "raw_QTB_arrival_timestamp_regressions": source_arrival_regressions_all_tickers,
            "unparsed_other_frames_are_not_in_interarrival_denominator": True,
            "missing_source_message_count_known": False,
            "complete_session_proven": False,
            "transport_continuity_proven": False,
            "cross_segment_event_time_order_proven": False,
            "source_arrival_silence_is_not_packet_loss_proof": True,
        },
        "distinct_symbols_in_selected_segments": len(symbols_in_source),
        "selected_symbol_events": matched,
        "selected_kind_counts": {k: types[k] for k in ("Q", "T", "B")},
        "observed_unfiltered_T_message_shares": total_traded_shares,
        "observed_B_trade_break_message_shares_NOT_NETTED": total_break_shares,
        "event_to_local_capture_lag_p95_nonnegative_ms": lag_p95_ms,
        "trade_quote_age_diagnostics": {
            "max_age_ms": quote_max_age_ms,
            "scope": "BOATS_SINGLE_ATS_SAME_SEGMENT_PRIOR_RECEIPT_ONLY",
            "observed_T_messages": quote_matches["observed_T_messages"],
            "fresh_prior_venue_quote": quote_matches["fresh_prior_venue_quote"],
            "stale_prior_venue_quote": quote_matches["stale_prior_venue_quote"],
            "no_prior_quote": quote_matches["no_prior_quote"],
            "quote_newer_than_trade": quote_matches["quote_newer_than_trade"],
            "trade_temporal_clock_unqualified": quote_matches["trade_temporal_clock_unqualified"],
            "unqualified_sale_conditions_present": quote_matches["unqualified_sale_conditions_present"],
            "fresh_quote_age_p95_ms": fresh_quote_age_p95_ms,
            "not_an_executable_trade_join": True,
            "quote_venue_is_nbbo": False,
            "transport_continuity_proven": False,
            "trade_breaks_excluded_from_T_count": True,
            "quote_age_is_only_diagnostic": True,
        },
        "quality_flags": dict(sorted(quality.items())),
        "examples": examples,
        "raw_source_bytes_reverified": True,
        "source_message_projection_reverified": True,
        "transport_continuity_proven": False,
        "time_window_completeness_proven": False,
        "publisher_entitlement_confirmed": False,
        "source_authenticity_proven": False,
        "nbbo": False,
        "trades_consolidated": False,
        "order_level_liquidity_replenishment_proven": False,
        "net_executed_volume_proven": False,
        "trade_initiator_side_proven": False,
        "point_in_time_backtest_eligible": False,
        "redistribution_admitted": False,
        "network": False, "writes": False, "key_read": False,
        "execution_authorized": False,
        "caveat": (
            "Observed single-ATS source messages only, no continuous feed proof. "
            "T/B conditions require full venue rule qualification. Breaks are "
            "separate corrections, not additive or safely netted shares. "
            "Arrival lag is not guaranteed transport latency; quote changes "
            "are not NBBO nor order-level replenishment."
        ),
    }
