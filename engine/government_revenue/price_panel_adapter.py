"""Bounded current-vintage input projection into the incumbent GRV PricePanel.

No collection, store, family, issuance or outcome write. This adapter qualifies
an adjusted-close ratio convention, not exact ex-close cash reinvestment and
not historical input availability, identity continuity or forecast efficacy.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from io import BytesIO
import json
from hashlib import sha256
import math
import re
from typing import Any, Mapping, Sequence

from engine.government_revenue.candidate_grader import PriceBasis, PricePanel, SessionCalendar, canonical_bytes
from engine.close_pass.massive_split_evidence import SplitEvidenceError, _validate_acquisition

_REVIEWED_PACKET_SHA256 = "6b62d7e6ef2c95c766f6089cde9c51994c0b869746546e86732dc4cdddf5285e"

_REVIEWED_ISSUER_PACKET_SHA256 = "773077fa8070e1c309b5b35542c34767bedd22c5f8ab27dd694210faf35cae1d"

_REVIEWED_COMBINED_PACKET_SHA256 = "f10935de7cacd0cf2c1554cf5a01e35a939645e6459b732b3e9f86f2592e0cd1"

CONVENTION = "backward_adjusted_close_ratio_native_cash_previous_raw_close_v1"


class PriceQualificationError(ValueError):
    pass


def _require(test: bool, reason: str) -> None:
    if not test:
        raise PriceQualificationError(reason)


def _positive(value: Any) -> float:
    _require(not isinstance(value, bool) and isinstance(value, (int, float))
             and math.isfinite(value) and value > 0, "nonpositive_or_nonfinite_price_action")
    return float(value)


def _day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise PriceQualificationError("invalid_action_date") from None


def _instant(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(result.tzinfo is not None, "naive_vintage_clock")
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise PriceQualificationError("invalid_vintage_clock") from None


def _project_current_vintage_panel(
    *, inputs: Mapping[str, Mapping[str, Any]], sessions: Sequence[date],
    calendar: SessionCalendar,
    action_start: date, action_basis_date: date, vintage_observed_at: str,
    convention: str,
) -> tuple[PricePanel, dict[str, Any]]:
    """Require complete requested bars and action scopes, then return PricePanel.

    Each symbol carries raw_closes (including previous sessions needed for
    native factor checks), retained dividend_response, split_acquisition,
    dividend_request_start/end, observed_at and original source_hashes with
    keys raw/dividends/splits. Original object digests and semantic input digests
    both travel in the qualification receipt. Inputs remain untouched.

    Executed splits in this scope are deliberately refused until their RAW
    unit bridge is independently qualified. Pending splits never change units.
    """
    _require(convention == CONVENTION, "registered_return_convention_mismatch")
    vintage = _instant(vintage_observed_at)
    _require(type(action_start) is date and type(action_basis_date) is date
             and action_start <= action_basis_date <= vintage.date(), "future_or_invalid_action_basis")
    days = tuple(sessions)
    _require(bool(days) and all(type(d) is date for d in days)
             and tuple(sorted(set(days))) == days, "invalid_requested_session_window")
    _require(action_start <= days[0] <= days[-1] <= action_basis_date, "partial_action_horizon")
    _require(isinstance(calendar, SessionCalendar) and calendar.calendar_id == "us_equity_sessions", "unqualified_calendar")
    _require(tuple(d for d in calendar.sessions if days[0] <= d <= days[-1]) == days, "partial_calendar_horizon")
    _require(bool(inputs), "empty_symbol_inputs")
    series, symbols = {}, []
    for symbol, inp in sorted(inputs.items()):
        _require(isinstance(symbol, str) and bool(symbol) and isinstance(inp, Mapping), "invalid_symbol_input")
        _require(_instant(inp.get("observed_at")) <= vintage, "future_input_observation")
        hashes = inp.get("source_hashes")
        _require(isinstance(hashes, Mapping) and set(hashes) == {"raw", "dividends", "splits"}
                 and all(isinstance(h, str) and re.fullmatch(r"[a-f0-9]{64}", h) for h in hashes.values()), "unbound_source_objects")
        raw = inp.get("raw_closes")
        _require(inp.get("raw_basis") == "unadjusted" and isinstance(raw, Mapping)
                 and all(type(d) is date for d in raw), "raw_unit_basis_unqualified")
        _require(all(d in raw for d in days), "partial_price_horizon")
        prices = {d: _positive(p) for d, p in raw.items()}
        _require(_day(inp.get("dividend_request_start")) <= action_start
                 and _day(inp.get("dividend_request_end")) == action_basis_date, "partial_dividend_horizon")
        response = inp.get("dividend_response")
        _require(isinstance(response, Mapping) and response.get("status") == "OK"
                 and not response.get("next_url") and isinstance(response.get("results"), list), "incomplete_dividend_response")
        split = inp.get("split_acquisition")
        try:
            _validate_acquisition(split)
        except (SplitEvidenceError, ValueError, TypeError, KeyError):
            raise PriceQualificationError("invalid_split_owner_acquisition") from None
        _require(split["status"] == "complete" and split["request"]["ticker"] == symbol
                 and _day(split["request"]["execution_date.gte"]) <= action_start
                 and _day(split["request"]["basis_date"]) == action_basis_date, "partial_split_horizon")
        _require(split["completed_utc_ns"] / 1e9 <= vintage.timestamp(), "future_split_observation")
        executed = [row for row in split["rows"] if _day(row["execution_date"]) <= action_basis_date]
        _require(not executed, "executed_split_raw_unit_bridge_unqualified")
        dividends = []
        for row in response["results"]:
            _require(isinstance(row, Mapping) and row.get("ticker") == symbol
                     and row.get("currency") == "USD" and row.get("distribution_type") == "recurring", "ambiguous_distribution_units")
            ex = _day(row.get("ex_dividend_date"))
            _require(_day(inp["dividend_request_start"]) <= ex <= action_basis_date, "future_or_out_of_scope_factor")
            cash, factor = _positive(row.get("cash_amount")), _positive(row.get("historical_adjustment_factor"))
            _require(factor <= 1, "invalid_dividend_factor")
            ex_index = calendar.index_of(ex)
            _require(ex_index is not None and ex_index > 0, "dividend_calendar_session_unqualified")
            previous_day = calendar.sessions[ex_index - 1]
            _require(previous_day in prices, "previous_raw_close_missing")
            # Source caller supplies the existing calendar; the factor witness
            # uses the immediately preceding retained RAW session, never a
            # split-adjusted cash field or a pending split ratio.
            previous = prices[previous_day]
            _require(cash < previous, "invalid_native_cash_scale")
            dividends.append({"ex_date": ex, "cash": cash, "factor": factor,
                              "previous_day": previous_day, "previous_raw_close": previous})
        dividends.sort(key=lambda row: row["ex_date"])
        _require(len({d["ex_date"] for d in dividends}) == len(dividends), "coincident_distribution_units_ambiguous")
        product, checks = 1.0, []
        for row in reversed(dividends):
            product *= 1.0 - row["cash"] / row["previous_raw_close"]
            residual = abs(row["factor"] - product)
            _require(residual <= 0.000000500001, "native_cash_raw_factor_incompatible")
            checks.append({"ex_date": row["ex_date"].isoformat(), "native_cash": row["cash"],
                           "previous_raw_session": row["previous_day"].isoformat(),
                           "previous_raw_close": row["previous_raw_close"],
                           "reconstructed_cumulative_factor": product,
                           "retained_cumulative_factor": row["factor"], "absolute_residual": residual})
        adjusted = {}
        for day in days:
            future = next((row for row in dividends if row["ex_date"] > day), None)
            adjusted[day] = prices[day] * (future["factor"] if future else 1.0)
        series[symbol] = adjusted
        semantic = {"raw_closes": [[d.isoformat(), prices[d]] for d in sorted(prices)],
                    "dividends": response, "splits": split}
        symbols.append({"symbol": symbol, "source_hashes": dict(hashes),
                        "semantic_input_sha256": sha256(canonical_bytes(semantic)).hexdigest(),
                        "factor_checks": list(reversed(checks)),
                        "pending_split_count": len(split["rows"]), "executed_split_count": 0})
    receipt = {"contract": "grv_current_vintage_price_projection/v1", "convention": convention,
               "action_start": action_start.isoformat(), "action_basis_date": action_basis_date.isoformat(),
               "vintage_observed_at": vintage_observed_at,
               "requested_sessions": [d.isoformat() for d in days], "symbols": symbols,
               "calendar_id": calendar.calendar_id,
               "calendar_sha256": sha256(canonical_bytes([d.isoformat() for d in calendar.sessions])).hexdigest(),
               "historical_first_seen_admitted": False, "identity_continuity_admitted": False,
               "rights_admitted": False, "permits_issuance": False, "permits_grade": False,
               "return_semantics": "ratio_of_backward_split_dividend_adjusted_closes",
               "projection_rule": "first_strictly_future_ex_date_cumulative_factor_or_one",
               "adjusted_series_sha256": sha256(canonical_bytes(
                   [[symbol, d.isoformat(), series[symbol][d]]
                    for symbol in sorted(series) for d in days])).hexdigest()}
    vintage_id = "grv-price-" + sha256(canonical_bytes(receipt)).hexdigest()
    receipt["vintage_id"] = vintage_id
    return PricePanel(basis=PriceBasis(field="close", adjustment="split_and_dividend_adjusted",
                                     vintage_id=vintage_id, vintage_observed_at=vintage_observed_at),
                      series=series), receipt


def _json_bytes(raw: bytes) -> dict[str, Any]:
    def unique(pairs):
        out = {}
        for key, value in pairs:
            _require(key not in out, "duplicate_source_json_key")
            out[key] = value
        return out
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise PriceQualificationError("invalid_source_json") from None
    _require(isinstance(value, dict), "invalid_source_json")
    return value


def _reviewed_packet_digest() -> str:
    """Fixed production pin; private seam permits synthetic tests only."""
    return _REVIEWED_PACKET_SHA256


def load_reviewed_current_vintage_panel(
    *, packet_root: str | Path, window_start: date, window_end: date,
) -> tuple[PricePanel, dict[str, Any]]:
    """The sole qualification boundary: load the exact reviewed retained bytes.

    This intentionally binds fixed source-reviewed current-vintage packets,
    not generic owner admission. Licensed retained source bytes stay external.
    No caller-supplied prices, actions, calendar, completeness flag, digest or
    expected-packet override is accepted. A different packet requires source
    review of its exact digest before this pinned boundary can consume it.
    This returns an isolated technical projection, never runtime grade/issuance
    admission. It is not wired to either owner path.
    """
    import pandas as pd
    from lib import nyse_calendar

    root = Path(packet_root).resolve()
    packet_path = root / "packet.json"
    _require(not packet_path.is_symlink(), "source_path_escape")
    packet_bytes = packet_path.read_bytes()
    packet_digest = sha256(packet_bytes).hexdigest()
    issuer_packet = packet_digest == _REVIEWED_ISSUER_PACKET_SHA256
    combined_packet = packet_digest == _REVIEWED_COMBINED_PACKET_SHA256
    _require(packet_digest in {_reviewed_packet_digest(), _REVIEWED_ISSUER_PACKET_SHA256,
                               _REVIEWED_COMBINED_PACKET_SHA256}, "unreviewed_packet_digest")
    packet = _json_bytes(packet_bytes)
    if combined_packet:
        _require(packet.get("technical_scope") == "six_symbol_current_input_only"
                 and sorted(ref.get("symbol", "") for ref in packet.get("symbols", []))
                 == ["ITA", "LHX", "LMT", "NOC", "RTX", "SPY"], "combined_packet_scope_mismatch")
    if issuer_packet:
        _require(packet.get("technical_scope") == "four_issuer_current_input_only"
                 and sorted(ref.get("symbol", "") for ref in packet.get("symbols", []))
                 == ["LHX", "LMT", "NOC", "RTX"], "issuer_packet_scope_mismatch")
    _require(packet.get("contract") == "grv_reviewed_retained_price_packet/v1", "invalid_retained_packet")
    _require(sha256(Path(nyse_calendar.__file__).read_bytes()).hexdigest()
             == packet["calendar_owner_sha256"], "calendar_owner_revision_mismatch")
    # Artifact-only verification runs from an evidence directory. The canonical
    # RAW owner module is imported to identify its source, never to acquire data.
    import collectors.massive_stock_day as raw_owner
    _require(sha256(Path(raw_owner.__file__).read_bytes()).hexdigest()
             == packet["raw_owner_sha256"], "raw_owner_revision_mismatch")

    def object_bytes(name: str) -> bytes:
        ref = packet["objects"].get(name)
        _require(isinstance(ref, dict) and ref.get("file") == name
                 and Path(name).name == name, "invalid_retained_object_ref")
        path = root / name
        _require(not path.is_symlink() and path.resolve().parent == root, "source_path_escape")
        raw = path.read_bytes()
        _require(sha256(raw).hexdigest() == ref["sha256"], "retained_source_byte_mismatch")
        return raw

    calendar_snapshot = _json_bytes(object_bytes(packet["calendar_snapshot"]))
    _require(calendar_snapshot["owner_sha256"] == packet["calendar_owner_sha256"]
             and calendar_snapshot["calendar_id"] == "us_equity_sessions", "calendar_owner_binding_mismatch")
    retained_dates = tuple(_day(day) for day in calendar_snapshot["session_dates"])
    _require(bool(retained_dates) and tuple(sorted(set(retained_dates))) == retained_dates, "invalid_retained_calendar")
    owner_dates = tuple(nyse_calendar.sessions_between(retained_dates[0], retained_dates[-1]))
    _require(owner_dates == retained_dates, "canonical_calendar_semantics_mismatch")
    calendar = SessionCalendar.from_dates(owner_dates, calendar_id=calendar_snapshot["calendar_id"])
    _require(type(window_start) is date and type(window_end) is date
             and owner_dates[0] <= window_start <= window_end <= owner_dates[-1], "invalid_requested_window")
    sessions = tuple(nyse_calendar.sessions_between(window_start, window_end))
    _require(bool(sessions) and sessions[0] == window_start and sessions[-1] == window_end,
             "requested_endpoint_is_not_session")
    dividend_owner = _json_bytes(object_bytes(packet["dividend_owner_qualification"]))
    action_start, basis = _day(packet["action_start"]), _day(packet["action_basis_date"])
    inputs = {}
    for ref in packet["symbols"]:
        symbol = ref["symbol"]
        raw_bytes, div_bytes, split_bytes = (object_bytes(ref[key]) for key in ("raw", "dividends", "splits"))
        read_receipt = _json_bytes(object_bytes(ref["read_receipt"]))
        raw_ref = read_receipt["objects"][symbol]
        _require(read_receipt["state"] == "STABLE_CANONICAL_SNAPSHOT_READ"
                 and raw_ref["state"] == "STABLE_BYTE_READ"
                 and raw_ref["key"] == "massive_stock_day/" + symbol + ".parquet"
                 and raw_ref["sha256"] == sha256(raw_bytes).hexdigest()
                 and raw_ref["content_length"] == len(raw_bytes), "raw_read_receipt_binding_mismatch")
        frame = pd.read_parquet(BytesIO(raw_bytes))
        _require("close" in frame.columns and frame.index.is_unique
                 and frame.index.is_monotonic_increasing, "invalid_raw_source_frame")
        _require(all(stamp == stamp.normalize() for stamp in frame.index), "raw_session_units_unqualified")
        prices = {stamp.date(): float(value) for stamp, value in frame["close"].items()}
        _require(len(prices) == len(frame), "duplicate_raw_session")
        dividends, splits = _json_bytes(div_bytes), _json_bytes(split_bytes)
        owner_rows = [row for row in dividend_owner["requests"] if row["ticker"] == symbol]
        _require(len(owner_rows) == 1, "ambiguous_dividend_owner_record")
        owner = owner_rows[0]
        _require(owner["state"] == "COMPLETE_PROVIDER_ASSERTED_BOUNDED_ACTION_RESPONSE"
                 and owner["artifact"]["sha256"] == sha256(div_bytes).hexdigest()
                 and owner["artifact"]["bytes"] == len(div_bytes)
                 and owner["rows"] == len(dividends.get("results", [])), "dividend_owner_byte_binding_mismatch")
        query = owner["query"]
        _require(query["ticker"] == symbol and _day(query["ex_dividend_date.gte"]) <= action_start
                 and _day(query["ex_dividend_date.lte"]) == basis, "dividend_owner_scope_mismatch")
        observed = max(_instant(raw_ref["observed_at"]), _instant(owner["owner_response_observed_at"]),
                       datetime.fromtimestamp(splits["completed_utc_ns"] / 1e9, timezone.utc))
        inputs[symbol] = {"raw_basis": "unadjusted", "raw_closes": prices,
                          "dividend_response": dividends, "split_acquisition": splits,
                          "dividend_request_start": query["ex_dividend_date.gte"],
                          "dividend_request_end": query["ex_dividend_date.lte"],
                          "observed_at": observed.isoformat(),
                          "source_hashes": {"raw": sha256(raw_bytes).hexdigest(),
                                            "dividends": sha256(div_bytes).hexdigest(),
                                            "splits": sha256(split_bytes).hexdigest()}}
    panel, receipt = _project_current_vintage_panel(
        inputs=inputs, sessions=sessions, calendar=calendar, action_start=action_start,
        action_basis_date=basis, vintage_observed_at=packet["vintage_observed_at"], convention=CONVENTION)
    receipt["reviewed_packet_sha256"] = sha256(packet_bytes).hexdigest()
    receipt["retained_object_sha256"] = {name: ref["sha256"] for name, ref in packet["objects"].items()}
    receipt["qualification_boundary"] = "exact_retained_bytes_verified_owner_receipts_canonical_calendar"
    if issuer_packet:
        receipt["technical_scope"] = "four_issuer_current_input_only"
    if combined_packet:
        receipt["technical_scope"] = "six_symbol_current_input_only"
    receipt["not_wired_to_issuance_or_grading"] = True
    # Seal the public closure after every source binding is attached. The sole
    # excluded field is the seal itself; PriceBasis carries this same identity.
    receipt.pop("vintage_id", None)
    receipt["price_basis"] = {"field": panel.basis.field,
                              "adjustment": panel.basis.adjustment,
                              "vintage_observed_at": panel.basis.vintage_observed_at}
    public_vintage_id = "grv-price-" + sha256(canonical_bytes(receipt)).hexdigest()
    receipt["vintage_id"] = public_vintage_id
    panel = PricePanel(basis=PriceBasis(field=panel.basis.field, adjustment=panel.basis.adjustment,
                                       vintage_id=public_vintage_id,
                                       vintage_observed_at=panel.basis.vintage_observed_at),
                       series=panel.series)
    return panel, receipt
