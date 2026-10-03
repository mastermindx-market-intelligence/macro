"""Tests for engine/options_alpha_exact_option_outcome.py — the OA-3 ruler.

Pure fixture-only evaluator mandated by
``DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER``.  These tests cover:

* closed 60-second boundaries on entry and exit;
* first-valid ask and first-valid bid inside the window wins;
* exit window starts at the admitted entry ``event_at + 60m`` (not at
  ``expression.available_at + 60m``);
* missing / malformed / conflicting / source-failure responses go
  ``unavailable``;
* retrieval before the relevant window closes stays ``pending``;
* identity defects are ``invalid`` (no zero return);
* v1 population defects are ``excluded``;
* same-day, non-100, package, short, non-session expressions are excluded;
* premarket, post-close, normal-session-close-crossing and early-close-crossing
  windows all fail closed under explicit reasons;
* raw-bytes/payload mismatch, Decimal precision, all-false authority, causal
  clock ordering, and SHA256 + byte-count receipts are bound to the record;
* the per-role ``QuoteEvidence`` carries an exact source query matching
  ``cohort.source_query`` and per-role independent retrieval clocks;
* the ``ExpressionReceipt`` validates the caller-supplied upstream digest
  against the canonical immutable expression fields;
* non-canonical raw bytes (JSON whitespace / key-order variation) are
  accepted as long as the parsed view agrees with the payload;
* arbitrary tampered expressions or wrong upstream digests are rejected;
* the module never reads the on-disk policy JSON at import time (or any other
  time) — pure by construction.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256

import pytest

from engine import options_alpha_exact_option_outcome as oa3
from engine import options_nbbo_cohort as cohort


UTC = timezone.utc
ET = oa3.ET

# A regular NYSE session (Thursday, full RTH).  Used for happy-path tests.
REGULAR_SESSION = "2026-10-15"
ENTRY_AVAILABLE_UTC = datetime(2026, 10, 15, 14, 0, 0, tzinfo=UTC)  # 10:00 ET
ENTRY_END_UTC = ENTRY_AVAILABLE_UTC + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS)
EXIT_HORIZON = timedelta(minutes=60)
EXIT_WINDOW = timedelta(seconds=oa3.EXIT_WINDOW_SECONDS)


def _request_clock() -> datetime:
    return ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10)


def _response_clock() -> datetime:
    return _request_clock() + timedelta(seconds=1)


def _retrieval_after(entry_event: datetime) -> datetime:
    """A retrieval clock that comfortably clears both entry and exit windows."""

    exit_end = entry_event + EXIT_HORIZON + EXIT_WINDOW
    return exit_end + timedelta(seconds=2)


# NYSE early-close session (Thursday, 1pm ET close, regular full session).
EARLY_CLOSE_SESSION = "2026-12-24"

EXPRESSION_ID = "oa3:expr:0001"
POLICY_VERSION = "v1"
SOURCE_CANDIDATE_ID = "oa3:cand:0001"
DECISION_RECEIPT_SHA = "1" * 64
SOURCE_RULE_SHA = "2" * 64
SELECTION_FENCE_AT = "2026-10-15T13:00:00.000000Z"
DECISION_AT = "2026-10-15T13:00:00.000000Z"
AVAILABLE_AT = ENTRY_AVAILABLE_UTC.isoformat().replace("+00:00", "Z")

RETRIEVAL_AT = datetime(2026, 10, 15, 17, 0, 0, tzinfo=UTC)
COMPUTED_UTC = RETRIEVAL_AT + timedelta(seconds=1)


def _expression(**overrides) -> dict:
    """Return a baseline OA-3 expression receipt mapping."""

    receipt = {
        "expression_id": EXPRESSION_ID,
        "policy_version": POLICY_VERSION,
        "source_candidate_id": SOURCE_CANDIDATE_ID,
        "decision_receipt_sha256": DECISION_RECEIPT_SHA,
        "source_rule_digest_sha256": SOURCE_RULE_SHA,
        "selection_frozen_before_outcomes": True,
        "selection_fence_at": SELECTION_FENCE_AT,
        "root": "SOFI",
        "expiration": "2026-10-16",
        "right": "call",
        "strike": "16",
        "strike_millis": 16000,
        "occ_symbol": "SOFI  261016C00016000",
        "position": "long",
        "quantity_contracts": 1,
        "multiplier": 100,
        "standard_deliverable": True,
        "single_leg": True,
        "package": False,
        "decision_at": DECISION_AT,
        "available_at": AVAILABLE_AT,
    }
    receipt.update(overrides)
    return receipt


def _contract_for(receipt: dict) -> dict:
    return cohort.validate_contract(
        {
            "root": receipt["root"],
            "expiration": receipt["expiration"],
            "right": receipt["right"],
            "strike": receipt["strike"],
            "strike_millis": receipt["strike_millis"],
            "occ_symbol": receipt["occ_symbol"],
        }
    )


def _expression_receipt(**overrides) -> oa3.ExpressionReceipt:
    """Build an ExpressionReceipt whose upstream digest matches canonical."""

    payload = _expression(**overrides)
    raw = cohort.canonical_json_bytes(payload)
    upstream_digest = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(payload))
    ).hexdigest()
    return oa3.ExpressionReceipt(
        raw_bytes=raw,
        parsed_payload=payload,
        upstream_digest_sha256=upstream_digest,
    )


def _canonical_fields_for_digest(receipt: dict) -> dict:
    """Return the canonical immutable expression fields for digest binding.

    Defensive against missing fields: tests that mutate a single immutable
    field can still compute the upstream digest for the resulting payload
    (so the test demonstrates the digest mismatch on the EXACT same
    upstream binding).
    """

    def _opt(key: str, default: str = "") -> str:
        value = receipt.get(key)
        if isinstance(value, str):
            return value
        if value is None:
            return default
        return str(value)

    return {
        "expression_id": _opt("expression_id"),
        "policy_version": _opt("policy_version"),
        "source_candidate_id": _opt("source_candidate_id"),
        "decision_receipt_sha256": _opt("decision_receipt_sha256"),
        "source_rule_digest_sha256": _opt("source_rule_digest_sha256"),
        "selection_frozen_before_outcomes": receipt.get(
            "selection_frozen_before_outcomes", False
        ),
        "selection_fence_at": _opt("selection_fence_at"),
        "root": _opt("root"),
        "expiration": _opt("expiration"),
        "right": _opt("right"),
        "strike": _opt("strike"),
        "strike_millis": receipt.get("strike_millis", 0),
        "occ_symbol": _opt("occ_symbol"),
        "position": _opt("position"),
        "quantity_contracts": receipt.get("quantity_contracts", 0),
        "multiplier": receipt.get("multiplier", 0),
        "standard_deliverable": receipt.get("standard_deliverable", False),
        "single_leg": receipt.get("single_leg", False),
        "package": receipt.get("package", False),
        "decision_at": _opt("decision_at"),
        "available_at": _opt("available_at"),
    }


def _quote_row(
    *,
    timestamp: str,
    bid: str = "2.20",
    ask: str = "2.30",
    bid_size: int = 11,
    ask_size: int = 12,
    bid_exchange: int = 4,
    ask_exchange: int = 11,
    bid_condition: int = 50,
    ask_condition: int = 50,
    symbol: str = "SOFI",
    expiration: str = "2026-10-16",
    strike: float = 16.0,
) -> dict:
    return {
        "symbol": symbol,
        "expiration": expiration,
        "right": "call",
        "strike": strike,
        "timestamp": timestamp,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "bid_exchange": bid_exchange,
        "ask_exchange": ask_exchange,
        "bid_condition": bid_condition,
        "ask_condition": ask_condition,
        "bid": bid,
        "ask": ask,
    }


def _row_at(event_at_utc: datetime, **overrides) -> dict:
    """Format a quote row whose timestamp is ``event_at_utc`` (UTC, microseconds)."""

    ts = event_at_utc.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    return _quote_row(timestamp=ts, **overrides)


def _payload_bytes(*rows: dict) -> bytes:
    return cohort.canonical_json_bytes(list(rows))


def _expected_query(
    contract: Mapping[str, Any],
    boundary_at: datetime,
    request_started_at: datetime,
    query_end_at: datetime,
) -> dict[str, str]:
    """Build the exact source-query contract the evidence must match."""

    return cohort.source_query(
        contract=contract,
        boundary_at=boundary_at,
        available_at=request_started_at,
        ceiling_at=query_end_at,
    )


def _evidence(
    *,
    role: str,
    contract: dict,
    boundary_at: datetime,
    request_started_at: datetime,
    response_observed_at: datetime,
    retrieval_observed_at: datetime,
    computed_at: datetime,
    rows: list[dict],
) -> oa3.QuoteEvidence:
    # Causal law: for the exit role, request_started_at must not precede
    # the exit boundary (the exit window opens at entry.event_at + 60m);
    # honor a caller-passed clock when it is already >= the boundary.  Same
    # for response_observed_at — it must clear request_started_at.
    if role == oa3.ROLE_EXIT:
        if request_started_at < boundary_at:
            request_started_at = boundary_at + timedelta(milliseconds=10)
        if response_observed_at < request_started_at:
            response_observed_at = request_started_at + timedelta(milliseconds=10)
        if retrieval_observed_at < response_observed_at:
            retrieval_observed_at = response_observed_at + timedelta(milliseconds=10)
        if computed_at < retrieval_observed_at:
            computed_at = retrieval_observed_at + timedelta(milliseconds=10)
    query_end_at = boundary_at + timedelta(seconds=oa3.EXIT_WINDOW_SECONDS if role == oa3.ROLE_EXIT else oa3.ENTRY_WINDOW_SECONDS)
    raw_bytes = _payload_bytes(*rows)
    return oa3.quote_evidence_from_bytes(
        role=role,
        contract=contract,
        boundary_at=boundary_at,
        query_end_at=query_end_at,
        query=_expected_query(
            contract,
            boundary_at,
            request_started_at,
            query_end_at,
        ),
        raw_bytes=raw_bytes,
        request_started_at=request_started_at,
        response_observed_at=response_observed_at,
        retrieval_observed_at=retrieval_observed_at,
        computed_at=computed_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────


def test_complete_first_valid_ask_and_bid_inside_60s_windows() -> None:
    """First valid firm ask inside [available_at, available_at+60s] wins,
    and the first valid firm bid inside [entry.event_at+60m, +60s] wins.
    Both observations lie inside the same NYSE RTH session.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)  # inside entry window
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [
        _row_at(
            exit_event,
            bid="2.40",
            bid_size=10,
            bid_exchange=11,
            bid_condition=50,
            ask="2.50",
            ask_size=12,
        )
    ]

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )

    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)

    assert record["status"] == "complete"
    assert record["reason"] is None
    assert record["net_return_pct"] == Decimal("3.771949")
    assert record["entry"]["selected"]["price"] == Decimal("2.30")
    assert record["exit"]["selected"]["price"] == Decimal("2.40")
    assert record["entry"]["query_bounds"]["start_at"] == ENTRY_AVAILABLE_UTC
    assert record["entry"]["query_bounds"]["end_at"] == ENTRY_END_UTC
    assert record["exit"]["query_bounds"]["start_at"] == entry_event + timedelta(minutes=60)
    assert record["exit"]["query_bounds"]["end_at"] == entry_event + timedelta(minutes=60, seconds=60)


def test_first_valid_ask_wins_when_a_better_ask_appears_later() -> None:
    """The first valid ask inside the 60-second entry window wins even
    when a better later ask (still inside the same window) exists.
    """

    boundary = ENTRY_AVAILABLE_UTC
    early_event = boundary + timedelta(seconds=5)
    late_event = boundary + timedelta(seconds=30)  # still inside window
    rows = [
        _row_at(early_event, ask="2.30", ask_size=10),
        _row_at(late_event, ask="1.50", ask_size=10),  # cheaper, but later
    ]
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=boundary,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=boundary + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["entry"]["selected"]["price"] == Decimal("2.30")


def test_first_valid_bid_wins_when_a_better_bid_appears_later() -> None:
    """The first valid bid inside the 60-second exit window wins even
    when a better later bid (still inside the same window) exists.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_early = entry_event + timedelta(minutes=60, seconds=5)
    exit_late = entry_event + timedelta(minutes=60, seconds=30)  # still inside window
    exit_rows = [
        _row_at(exit_early, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12),
        _row_at(exit_late, bid="3.00", bid_size=10, bid_exchange=11, bid_condition=50, ask="3.10", ask_size=12),
    ]
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "complete"
    assert record["exit"]["selected"]["price"] == Decimal("2.40")


def test_exit_target_is_admitted_entry_event_at_plus_60m() -> None:
    """The exit window starts at the ADMITTED entry event clock + 60m,
    NOT at expression.available_at + 60m.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=45)  # near the right edge
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.50", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.60", ask_size=12)]

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "complete"
    assert record["exit"]["query_bounds"]["start_at"] == entry_event + timedelta(minutes=60)
    assert record["exit"]["query_bounds"]["end_at"] == entry_event + timedelta(minutes=60, seconds=60)


def test_decimal_fees_use_exact_one_contract_formula() -> None:
    """Decimal precision must match the frozen 100-multiplier /
    USD 0.65-per-side formula byte-for-byte.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=2)
    exit_event = entry_event + timedelta(minutes=60, seconds=2)
    entry_rows = [_row_at(entry_event, bid="0.95", bid_size=10, bid_exchange=11, bid_condition=50, ask="1.00", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="1.20", bid_size=10, bid_exchange=11, bid_condition=50, ask="1.30", ask_size=12)]
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert isinstance(record["net_return_pct"], Decimal)
    assert str(record["net_return_pct"]) == "18.579235"
    assert record["cost"]["fee_per_side_usd"] == "0.65"
    assert record["cost"]["multiplier"] == 100


def test_record_carries_exact_all_false_authority() -> None:
    """The fixture record must carry the exact all-false authority block,
    no flag may be true and no fill claim may be made.
    """

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["authority"] == oa3.ALL_FALSE_AUTHORITY
    assert all(value is False for value in record["authority"].values())
    assert "may_claim_fill" in record["authority"]
    assert record["quote_source"]["executable_fill_claim"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Status transitions: pending vs unavailable
# ─────────────────────────────────────────────────────────────────────────────


def test_early_now_is_pending_before_entry_window_matures() -> None:
    """If now is before entry_end, status is pending and net_return is None."""

    contract = _contract_for(_expression())
    retrieval = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval,
        computed_at=retrieval,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval,
        computed_at=retrieval,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "pending"
    assert record["reason"] is None
    assert record["net_return_pct"] is None
    assert record["entry"]["selected"] is None
    assert record["exit"]["selected"] is None


def test_pending_after_entry_window_but_before_exit_window() -> None:
    """Entry window has matured and a quote was found, but the exit
    window has not matured yet: status stays pending.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=2)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    retrieval_at = entry_event + timedelta(minutes=5)  # well before exit_start
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=entry_event + timedelta(seconds=10),
        response_observed_at=retrieval_at,
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "pending"
    assert record["entry"]["selected"]["price"] == Decimal("2.30")
    assert record["exit"]["selected"] is None
    assert record["net_return_pct"] is None


def test_no_quote_inside_entry_window_is_unavailable() -> None:
    """No valid firm ask inside [available_at, available_at+60s] ->
    ENTRY_QUOTE_UNAVAILABLE after the window has matured.
    """

    contract = _contract_for(_expression())
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "ENTRY_QUOTE_UNAVAILABLE"
    assert record["net_return_pct"] is None


def test_no_quote_inside_exit_window_is_unavailable() -> None:
    """Entry observation exists, no valid firm bid inside the exit
    window after maturity -> EXIT_QUOTE_UNAVAILABLE.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=2)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    retrieval_at = entry_event + timedelta(minutes=60, seconds=120)
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=entry_event + timedelta(minutes=60, seconds=10),
        response_observed_at=entry_event + timedelta(minutes=60, seconds=11),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "EXIT_QUOTE_UNAVAILABLE"
    assert record["entry"]["selected"] is not None
    assert record["exit"]["selected"] is None


def test_conflict_same_timestamp_is_unavailable() -> None:
    """Two different rows at the same event_at conflict -> QUOTE_RESPONSE_INVALID."""

    conflict_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    rows = [
        _row_at(conflict_event, ask="2.30", bid="2.20"),
        _row_at(conflict_event, ask="2.50", bid="2.40"),  # same ts, different price
    ]
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"


def test_malformed_response_is_unavailable() -> None:
    """A row missing required fields -> QUOTE_RESPONSE_INVALID."""

    bad = {
        "symbol": "SOFI",
        "expiration": "2026-10-16",
        "right": "call",
        "strike": 16.0,
        "timestamp": ENTRY_AVAILABLE_UTC.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        "bid_size": 10,
        "ask_size": 10,
        "bid_exchange": 11,
        "ask_exchange": 11,
        "bid_condition": 50,
        "ask_condition": 50,
        # bid/ask missing
    }
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[bad],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"


def test_wrong_contract_in_response_is_unavailable() -> None:
    """A row whose root differs from the exact contract -> QUOTE_RESPONSE_INVALID
    (the reusable parser fails closed).
    """

    bad = {
        "symbol": "MSFT",  # not SOFI
        "expiration": "2026-10-16",
        "right": "call",
        "strike": 16.0,
        "timestamp": ENTRY_AVAILABLE_UTC.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        "bid_size": 10,
        "ask_size": 10,
        "bid_exchange": 11,
        "ask_exchange": 11,
        "bid_condition": 50,
        "ask_condition": 50,
        "bid": 2.2,
        "ask": 2.3,
    }
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[bad],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"


def test_crossed_quote_is_not_selected_and_falls_unavailable() -> None:
    """A row whose ask < bid is crossed; with no other eligible ask the
    window records no candidate and the outcome is unavailable.
    """

    crossed = _row_at(ENTRY_AVAILABLE_UTC + timedelta(seconds=2), bid="2.40", ask="2.30")
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[crossed],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "ENTRY_QUOTE_UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# Identity / population / session law
# ─────────────────────────────────────────────────────────────────────────────


def test_missing_required_field_is_invalid() -> None:
    """A receipt missing an immutable field produces an invalid record."""

    receipt = _expression()
    receipt.pop("decision_at")
    # The upstream digest doesn't matter — validation rejects on missing
    # field before digest comparison.
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw,
        parsed_payload=receipt,
        upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["net_return_pct"] is None
    assert record["entry"]["selected"] is None
    assert record["exit"]["selected"] is None


def test_invalid_occ_symbol_is_invalid() -> None:
    """An OCC symbol that does not match the exact fields -> invalid."""

    receipt = _expression(occ_symbol="SOFI  261016C00099999")
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["net_return_pct"] is None


def test_policy_version_must_be_v_prefixed() -> None:
    receipt = _expression(policy_version="broken")
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"


def test_available_at_preceding_decision_at_is_invalid() -> None:
    """available_at must never precede decision_at."""

    receipt = _expression(
        decision_at="2026-10-15T14:00:00.000000Z",
        available_at="2026-10-15T13:55:00.000000Z",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"


def test_zero_dte_expression_is_excluded() -> None:
    """Same-day expiration is outside v1: status=excluded, reason=SAME_DAY_EXPIRATION."""

    receipt = _expression(
        expiration=REGULAR_SESSION,  # same date as entry session
        occ_symbol="SOFI  261015C00016000",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "SAME_DAY_EXPIRATION"
    assert record["net_return_pct"] is None


def test_non_standard_deliverable_is_excluded() -> None:
    """A receipt marking standard_deliverable=False is outside v1."""

    receipt = _expression(standard_deliverable=False)
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "NON_STANDARD_DELIVERABLE"


def test_non_standard_multiplier_is_excluded() -> None:
    """A non-100 multiplier is outside v1."""

    receipt = _expression(multiplier=50)
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "NON_STANDARD_MULTIPLIER"


def test_quantity_not_one_is_excluded() -> None:
    """A quantity other than one contract is outside v1."""

    receipt = _expression(quantity_contracts=5)
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "QUANTITY_NOT_ONE"


def test_short_option_is_excluded() -> None:
    """A short position is outside v1."""

    receipt = _expression(position="short")
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "SHORT_OPTION_NOT_SUPPORTED"


def test_package_receipt_is_excluded() -> None:
    """A receipt carrying package=True is outside v1 (single-leg only)."""

    receipt = _expression(package=True)
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "PACKAGE_NOT_SUPPORTED"


def test_non_session_entry_date_is_excluded() -> None:
    """A non-NYSE session (holiday) is outside v1."""

    receipt = _expression(
        available_at=datetime(2026, 11, 26, 14, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        decision_at=datetime(2026, 11, 26, 14, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        expiration="2026-12-04",
        occ_symbol="SOFI  261204C00016000",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "EXPRESSION_DATE_NOT_NYSE_SESSION"


def test_premarket_entry_boundary_is_excluded() -> None:
    """available_at before the 9:30 ET open is ENTRY_BOUNDARY_OUTSIDE_RTH."""

    premarket = datetime(2026, 10, 15, 13, 0, 0, tzinfo=UTC)  # 09:00 ET
    receipt = _expression(
        available_at=premarket.isoformat().replace("+00:00", "Z"),
        decision_at=premarket.isoformat().replace("+00:00", "Z"),
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "ENTRY_BOUNDARY_OUTSIDE_RTH"


def test_post_close_entry_boundary_is_excluded() -> None:
    """available_at at or after 16:00 ET is ENTRY_BOUNDARY_OUTSIDE_RTH."""

    post = datetime(2026, 10, 15, 20, 0, 1, tzinfo=UTC)  # 16:00:01 ET
    receipt = _expression(
        available_at=post.isoformat().replace("+00:00", "Z"),
        decision_at=post.isoformat().replace("+00:00", "Z"),
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "ENTRY_BOUNDARY_OUTSIDE_RTH"


def test_normal_session_horizon_crosses_close_is_excluded() -> None:
    """An entry so close to 16:00 ET that the entry window crosses the
    close is excluded under HORIZON_CROSSES_SESSION_CLOSE — even before
    parsing any quote (Ruling 4).
    """

    near_close = datetime(2026, 10, 15, 19, 59, 30, tzinfo=UTC)  # 15:59:30 ET
    # available_at + 60s = 16:00:30 > 16:00 close -> excluded pre-quote
    receipt = _expression(
        available_at=near_close.isoformat().replace("+00:00", "Z"),
        decision_at=near_close.isoformat().replace("+00:00", "Z"),
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(receipt)
    retrieval_at = near_close + timedelta(seconds=2)
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=near_close,
        request_started_at=near_close + timedelta(milliseconds=10),
        response_observed_at=near_close + timedelta(milliseconds=20),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
        rows=[],
    )
    # The exit boundary at entry.event_at+60m lands past the RTH close
    # (20:59:30 UTC > 20:00 UTC), so the engine will return
    # HORIZON_CROSSES_SESSION_CLOSE from the entry side before parsing
    # any exit evidence.  Construct a valid dummy exit evidence so the
    # test does not have to mint a contract-bound source query for a
    # boundary that the source-query helper refuses.
    exit_boundary = ENTRY_AVAILABLE_UTC + timedelta(minutes=30)  # inside RTH
    exit_query_end = exit_boundary + timedelta(seconds=60)
    exit_request = exit_boundary + timedelta(milliseconds=10)
    exit_query = cohort.source_query(
        contract=contract,
        boundary_at=exit_boundary,
        available_at=exit_request,
        ceiling_at=exit_query_end,
    )
    exit_ev = oa3.quote_evidence_from_bytes(
        role="exit",
        contract=contract,
        boundary_at=exit_boundary,
        query_end_at=exit_query_end,
        query=exit_query,
        raw_bytes=_payload_bytes(),
        request_started_at=exit_request,
        response_observed_at=exit_request + timedelta(milliseconds=10),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "HORIZON_CROSSES_SESSION_CLOSE"


def test_early_close_horizon_crosses_close_is_excluded() -> None:
    """On an early-close session (13:00 ET), an entry that pushes the
    H+60 exit window past the early close is excluded.
    """

    # 2026-12-24 early close at 13:00 ET = 18:00 UTC (EST = UTC-5).
    # Use 17:31 UTC (12:31 ET) so the entry window still has 29s inside
    # RTH; the exit window target = 18:31 UTC which is past the early
    # close at 18:00 UTC -> excluded by evaluate() after parsing the
    # entry quote.
    near_close = datetime(2026, 12, 24, 17, 31, 0, tzinfo=UTC)  # 12:31 ET
    receipt = _expression(
        available_at=near_close.isoformat().replace("+00:00", "Z"),
        decision_at=near_close.isoformat().replace("+00:00", "Z"),
        expiration="2026-12-31",
        occ_symbol="SOFI  261231C00016000",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(receipt)
    # Retrieval must clear the entry window end (Ruling C: unconditional maturity).
    retrieval_at = near_close + timedelta(seconds=62)
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=near_close,
        request_started_at=near_close + timedelta(milliseconds=10),
        response_observed_at=near_close + timedelta(milliseconds=20),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
        rows=[_quote_row(
            timestamp=near_close.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            expiration="2026-12-31",
            bid="2.30", bid_size=10, bid_exchange=11, bid_condition=50,
            ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50,
        )],
    )
    # See test_normal_session_horizon_crosses_close_is_excluded: the exit
    # boundary for this scenario lands past the early close, so use a
    # valid dummy exit evidence.
    exit_boundary = datetime(2026, 12, 24, 17, 30, 0, tzinfo=UTC)  # 12:30 ET
    exit_query_end = exit_boundary + timedelta(seconds=60)
    exit_request = exit_boundary + timedelta(milliseconds=10)
    exit_query = cohort.source_query(
        contract=contract,
        boundary_at=exit_boundary,
        available_at=exit_request,
        ceiling_at=exit_query_end,
    )
    exit_ev = oa3.quote_evidence_from_bytes(
        role="exit",
        contract=contract,
        boundary_at=exit_boundary,
        query_end_at=exit_query_end,
        query=exit_query,
        raw_bytes=_payload_bytes(),
        request_started_at=exit_request,
        response_observed_at=exit_request + timedelta(milliseconds=10),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "HORIZON_CROSSES_SESSION_CLOSE"


# ─────────────────────────────────────────────────────────────────────────────
# Receipt provenance / clocks
# ─────────────────────────────────────────────────────────────────────────────


def test_receipt_provenance_binds_sha256_and_bytecount() -> None:
    """Every entry/exit block carries the SHA-256 and byte count of the
    raw response and the canonicalised payload.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    entry_bytes = _payload_bytes(*entry_rows)
    exit_bytes = _payload_bytes(*exit_rows)

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["entry"]["raw_response_sha256"] == sha256(entry_bytes).hexdigest()
    assert record["entry"]["raw_response_bytes"] == len(entry_bytes)
    assert record["exit"]["raw_response_sha256"] == sha256(exit_bytes).hexdigest()
    assert record["exit"]["raw_response_bytes"] == len(exit_bytes)
    assert record["entry"]["raw_response_sha256"] == record["entry"]["raw_payload_sha256"]


def test_record_carries_per_role_clocks_distinct() -> None:
    """The fixture record binds entry and exit clocks independently so the
    analyst can prove the two retrievals happened at different times.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    entry_request = ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10)
    entry_response = entry_request + timedelta(seconds=1)
    # Retrieval must land AFTER the entry window end (Ruling C: window maturity
    # is unconditional) AND after the selected entry event (Ruling B).
    entry_retrieval = ENTRY_END_UTC + timedelta(seconds=2)
    entry_computed = entry_retrieval + timedelta(milliseconds=10)
    exit_request = exit_event - timedelta(milliseconds=10)
    exit_response = exit_request + timedelta(milliseconds=20)
    exit_retrieval = exit_event + timedelta(seconds=2)
    exit_computed = exit_retrieval + timedelta(milliseconds=10)
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=entry_request,
        response_observed_at=entry_response,
        retrieval_observed_at=entry_retrieval,
        computed_at=entry_computed,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=exit_request,
        response_observed_at=exit_response,
        retrieval_observed_at=exit_retrieval,
        computed_at=exit_computed,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["entry"]["clocks"]["request_started_at"] == entry_request
    assert record["entry"]["clocks"]["response_observed_at"] == entry_response
    assert record["exit"]["clocks"]["request_started_at"] == exit_request
    assert record["exit"]["clocks"]["response_observed_at"] == exit_response
    assert record["entry"]["clocks"]["request_started_at"] != record["exit"]["clocks"]["request_started_at"]
    assert record["entry"]["clocks"]["retrieval_observed_at"] != record["exit"]["clocks"]["retrieval_observed_at"]


def test_evidence_computed_before_retrieval_is_invalid() -> None:
    """A computed_at earlier than retrieval_observed_at is invalid."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    retrieval = ENTRY_AVAILABLE_UTC + timedelta(seconds=10)
    with pytest.raises(oa3.Oa3InvalidError, match="EVIDENCE_COMPUTED_BEFORE_RETRIEVAL"):
        oa3.quote_evidence_from_bytes(
            role="entry",
            contract=contract,
            boundary_at=ENTRY_AVAILABLE_UTC,
            query_end_at=ENTRY_END_UTC,
            query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
            raw_bytes=_payload_bytes(*entry_rows),
            request_started_at=_request_clock(),
            response_observed_at=_response_clock(),
            retrieval_observed_at=retrieval,
            computed_at=retrieval - timedelta(milliseconds=10),
        )


def test_causal_clock_mismatch_response_after_retrieval_is_invalid() -> None:
    """response_observed_at > retrieval_observed_at is invalid."""

    contract = _contract_for(_expression())
    with pytest.raises(oa3.Oa3InvalidError, match="EVIDENCE_CLOCK_INTEGRITY_FAILURE"):
        oa3.quote_evidence_from_bytes(
            role="entry",
            contract=contract,
            boundary_at=ENTRY_AVAILABLE_UTC,
            query_end_at=ENTRY_END_UTC,
            query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
            raw_bytes=_payload_bytes(),
            request_started_at=_request_clock(),
            response_observed_at=RETRIEVAL_AT + timedelta(seconds=10),
            retrieval_observed_at=RETRIEVAL_AT,
            computed_at=COMPUTED_UTC,
        )


def test_quote_event_before_available_at_is_skipped() -> None:
    """Quotes with event_at before available_at do not count toward selection."""

    too_early = ENTRY_AVAILABLE_UTC - timedelta(seconds=1)
    eligible = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    rows = [
        _row_at(too_early, ask="1.00", ask_size=10, ask_exchange=11, ask_condition=50),
        _row_at(eligible, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50),
    ]
    exit_event = eligible + timedelta(minutes=60, seconds=5)
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=rows,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=eligible + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "complete"
    assert record["entry"]["selected"]["price"] == Decimal("2.30")
    assert record["entry"]["selected"]["event_at"] == eligible


def test_expression_digest_is_stable_and_round_trips() -> None:
    """The expression_digest_sha256 must round-trip the same bytes."""

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record_a = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    record_b = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record_a["expression_digest_sha256"] == record_b["expression_digest_sha256"]
    assert record_a["expression_digest_sha256"] != record_a["policy_sha256"]


def test_arbitrary_hash_with_tampered_expression_is_invalid() -> None:
    """If the caller passes an ExpressionReceipt whose upstream digest does
    not match the canonical immutable expression fields, the record is
    invalid under EXPRESSION_DIGEST_MISMATCH.
    """

    payload = _expression()
    raw = cohort.canonical_json_bytes(payload)
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw,
        parsed_payload=payload,
        upstream_digest_sha256="0" * 64,  # arbitrary wrong hash
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EXPRESSION_DIGEST_MISMATCH"


def test_tampered_payload_with_correct_hash_is_invalid() -> None:
    """If the raw bytes parse to a payload that disagrees with the
    upstream-digest binding, the wrapper rejects the receipt at
    construction time (the tampered payload's digest will not match).
    """

    payload = _expression()
    raw = cohort.canonical_json_bytes(payload)
    # Compute digest for the canonical form
    upstream_digest = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(payload))
    ).hexdigest()
    # Now tamper with one immutable field while keeping the original upstream digest
    tampered = dict(payload)
    tampered["expression_id"] = "oa3:expr:TAMPERED"
    # Express the tampered receipt with the WRONG raw bytes (matching the
    # tampered payload) but the SAME upstream digest (computed against the
    # original).  The wrapper must reject via EXPRESSION_DIGEST_MISMATCH.
    raw_tampered = cohort.canonical_json_bytes(tampered)
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw_tampered,
        parsed_payload=tampered,
        upstream_digest_sha256=upstream_digest,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EXPRESSION_DIGEST_MISMATCH"


def test_noncanonical_valid_json_raw_bytes_accepted() -> None:
    """QuoteEvidence raw bytes may carry JSON whitespace / key-order
    variation; raw digest differs from canonical payload digest; both are
    preserved and the parsed view agrees with parsed_payload.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    # Whitespace / key-order variant: rebuild JSON with reversed key order
    # and indented formatting.  Both are valid JSON that parses to the
    # SAME view as the canonical form, so the parsed payload agrees.
    canonical_entry_bytes = _payload_bytes(*entry_rows)
    canonical_entry_str = canonical_entry_bytes.decode("utf-8").rstrip("\n")
    noncanonical_entry_str = json.dumps(list(entry_rows), indent=2) + "\n"
    noncanonical_entry_bytes = noncanonical_entry_str.encode("utf-8")
    assert noncanonical_entry_bytes != canonical_entry_bytes
    # The raw SHA differs from the canonical SHA; this is the load-bearing
    # property the evaluator MUST preserve (Ruling 2).
    raw_sha = sha256(noncanonical_entry_bytes).hexdigest()
    canonical_sha = sha256(canonical_entry_bytes).hexdigest()
    assert raw_sha != canonical_sha

    contract = _contract_for(_expression())
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
        raw_bytes=noncanonical_entry_bytes,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    # Raw bytes SHA matches the EXACT bytes the analyst received.
    assert record["entry"]["raw_response_sha256"] == raw_sha
    assert record["entry"]["raw_response_bytes"] == len(noncanonical_entry_bytes)
    # Canonical payload SHA matches the canonical re-serialisation of the
    # parsed view.  The two digests differ — that is the load-bearing fact
    # the evaluator must preserve verbatim (Ruling 2).
    assert record["entry"]["raw_payload_sha256"] == canonical_sha
    assert record["entry"]["raw_payload_sha256"] != record["entry"]["raw_response_sha256"]
    assert record["status"] == "complete"
    assert record["entry"]["selected"] is not None
    assert record["entry"]["selected"]["price"] == Decimal("2.30")


def test_raw_bytes_and_payload_mismatch_is_invalid() -> None:
    """An ExpressionReceipt whose raw bytes parse to a different Mapping
    than parsed_payload is integrity-invalid (Ruling E).
    """

    payload = _expression()
    raw = cohort.canonical_json_bytes({"different": True, **payload})
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(payload))
    ).hexdigest()
    with pytest.raises(oa3.Oa3InvalidError, match="disagrees with raw_bytes"):
        oa3.ExpressionReceipt(
            raw_bytes=raw,
            parsed_payload=payload,
            upstream_digest_sha256=upstream,
        )


def test_quote_evidence_construction_is_byte_strict() -> None:
    """QuoteEvidence built from a payload exposes raw_bytes equal to the
    canonical serialisation of parsed_payload.
    """

    payload = [_row_at(ENTRY_AVAILABLE_UTC + timedelta(seconds=2))]
    contract = _contract_for(_expression())
    ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
        raw_bytes=cohort.canonical_json_bytes(payload),
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert ev.raw_bytes == cohort.canonical_json_bytes(payload)
    assert ev.raw_sha256 == sha256(ev.raw_bytes).hexdigest()
    assert ev.canonical_payload_sha256 == sha256(cohort.canonical_json_bytes([dict(item) for item in ev.parsed_payload])).hexdigest()


def test_quote_evidence_malformed_bytes_emits_unavailable_at_evaluate() -> None:
    """Malformed source bytes: constructor must NOT raise (Ruling E) — the
    evaluator emits QUOTE_RESPONSE_INVALID unavailable with the parse error
    preserved.  The raw SHA/size is bound to the record's entry block.
    """

    contract = _contract_for(_expression())
    malformed = b"not json"
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
        raw_bytes=malformed,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert entry_ev.parsed_payload is None
    assert entry_ev.parse_error and entry_ev.parse_error.startswith("QUOTE_RESPONSE_INVALID")
    # Raw SHA/size is preserved on the evidence block.
    assert entry_ev.raw_sha256 == sha256(malformed).hexdigest()
    assert entry_ev.raw_size == len(malformed)
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"
    assert record["entry"]["raw_response_sha256"] == sha256(malformed).hexdigest()
    assert record["entry"]["raw_response_bytes"] == len(malformed)


def test_policy_sha256_is_module_pinned_constant() -> None:
    """The fixture record's policy_sha256 is the module-level constant and
    never read from disk at runtime.
    """

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["policy_sha256"] == oa3.FROZEN_POLICY_SHA256


def test_benchmark_lag_rule_is_not_inherited() -> None:
    """The 600-second live-capture fence from the benchmark is NOT
    imported; the OA-3 record must make no reference to it.
    """

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    serialized = json.dumps(record, default=str)
    assert "MAX_AVAILABLE_LAG" not in serialized
    assert "capture_lag" not in serialized.lower()
    assert "momoedge" not in serialized.lower()
    assert "cohort_rule_id" not in serialized.lower()
    assert "benchmark" not in serialized.lower()


def test_no_raw_quote_row_or_pnl_claim_in_record() -> None:
    """The fixture record carries selected ruler fields only — no raw
    quote rows, no payload, no PnL/selection/training claim.
    """

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    serialized = json.dumps(record, default=str)
    assert "PnL" not in serialized
    assert "quote_response_body" not in serialized
    assert record["authority"]["may_claim_fill"] is False
    assert record["quote_source"]["executable_fill_claim"] is False


def test_record_carries_schema_and_policy_id() -> None:
    """The fixture schema and policy id are present and pinned."""

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["schema"] == oa3.SCHEMA
    assert record["policy_id"] == oa3.FROZEN_POLICY_ID
    assert record["policy_id"] == "oa3.long_single_leg_h60_nbbo/v1"


def test_record_carries_session_window() -> None:
    """The record pins the canonical NYSE RTH window for the session."""

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    # 2026-10-15: 9:30 ET (13:30 UTC) -> 16:00 ET (20:00 UTC)
    assert record["session_rth_open"] == datetime(2026, 10, 15, 13, 30, tzinfo=UTC)
    assert record["session_rth_close"] == datetime(2026, 10, 15, 20, 0, tzinfo=UTC)
    assert record["session_date"] == "2026-10-15"


def test_status_vocabulary_is_closed() -> None:
    """No status outside the five-state vocabulary may be emitted."""

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    statuses = {record["status"]}
    assert statuses.issubset({"pending", "complete", "unavailable", "excluded", "invalid"})


def test_expression_replayability_hash_is_stable() -> None:
    """The expression_digest_sha256 is derived from canonical expression
    fields only and excludes volatile non-deterministic fields.
    """

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    digest = record["expression_digest_sha256"]
    assert isinstance(digest, str) and len(digest) == 64
    record_other = oa3.evaluate(
        _expression_receipt(expression_id="oa3:expr:0002"),
        entry_evidence=entry_ev,
        exit_evidence=exit_ev,
    )
    assert record_other["expression_digest_sha256"] != digest


# ─────────────────────────────────────────────────────────────────────────────
# Altered query contract / date / bounds / interval
# ─────────────────────────────────────────────────────────────────────────────


def test_evidence_with_altered_query_date_is_invalid() -> None:
    """An evidence whose query carries a wrong date is rejected as
    EVIDENCE_QUERY_MISMATCH — the analyst cannot have sent that query."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    contract = _contract_for(_expression())
    expected = _expected_query(
        contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC
    )
    altered = dict(expected)
    altered["date"] = "20261016"  # wrong session date
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=altered,
        raw_bytes=_payload_bytes(*rows),
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


def test_evidence_with_altered_query_bounds_is_invalid() -> None:
    """An evidence whose query carries the wrong start_time / end_time is
    rejected."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    contract = _contract_for(_expression())
    expected = _expected_query(
        contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC
    )
    altered = dict(expected)
    altered["start_time"] = "10:00:30.000"  # wrong start
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=altered,
        raw_bytes=_payload_bytes(*rows),
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


def test_evidence_with_altered_interval_is_invalid() -> None:
    """An evidence whose query carries the wrong interval is rejected."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    contract = _contract_for(_expression())
    expected = _expected_query(
        contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC
    )
    altered = dict(expected)
    altered["interval"] = "minute"  # wrong interval
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=altered,
        raw_bytes=_payload_bytes(*rows),
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


def test_evidence_with_wrong_contract_is_invalid() -> None:
    """An evidence whose contract differs from the expression contract is
    rejected (EVIDENCE_QUERY_MISMATCH via post-query contract check)."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    contract = _contract_for(_expression())
    other_contract = cohort.validate_contract(
        {
            "root": "AAPL",
            "expiration": "2026-10-16",
            "right": "call",
            "strike": "16",
            "strike_millis": 16000,
            "occ_symbol": "AAPL  261016C00016000",
        }
    )
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=other_contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=_expected_query(
            other_contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC
        ),
        raw_bytes=_payload_bytes(*rows),
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


# ─────────────────────────────────────────────────────────────────────────────
# Same-clock whole-window maturity: normal AND early close
# ─────────────────────────────────────────────────────────────────────────────


def test_pending_until_whole_60s_window_elapsed_normal_close() -> None:
    """When retrieval sits inside the entry window (before target+60s),
    status is pending — the analyst has not let the whole window mature.
    """

    contract = _contract_for(_expression())
    retrieval = ENTRY_AVAILABLE_UTC + timedelta(seconds=30)  # inside window
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval,
        computed_at=retrieval,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval,
        computed_at=retrieval,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "pending"


def test_pending_until_whole_60s_window_elapsed_early_close() -> None:
    """Same pending-until-maturity law on an early-close session (13:00 ET).

    available_at at 12:30 ET (17:30 UTC); retrieval at +30s sits inside the
    60-second window, so the outcome is pending.  The exit boundary at
    entry.event_at+60m would land past the early close, so the test uses
    a valid dummy exit boundary inside RTH — evaluate() returns
    pending from the entry side before parsing any exit evidence.
    """

    boundary = datetime(2026, 12, 24, 17, 30, 0, tzinfo=UTC)  # 12:30 ET
    # Expiration must be AFTER the session date (Ruling D: same-day excluded;
    # pre-session excluded as EXPRESSION_CONTRACT_EXPIRED).  Use a future
    # expiration so the receipt clears contract validation.
    receipt = _expression(
        available_at=boundary.isoformat().replace("+00:00", "Z"),
        decision_at=boundary.isoformat().replace("+00:00", "Z"),
        expiration="2026-12-31",
        occ_symbol="SOFI  261231C00016000",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(receipt)
    retrieval = boundary + timedelta(seconds=30)
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry",
        contract=contract,
        boundary_at=boundary,
        query_end_at=boundary + timedelta(seconds=60),
        query=_expected_query(
            contract, boundary, boundary + timedelta(milliseconds=10),
            boundary + timedelta(seconds=60),
        ),
        raw_bytes=_payload_bytes(),
        request_started_at=boundary + timedelta(milliseconds=10),
        response_observed_at=boundary + timedelta(milliseconds=20),
        retrieval_observed_at=retrieval,
        computed_at=retrieval + timedelta(milliseconds=10),
    )
    # Dummy exit evidence with a valid in-RTH boundary — the engine
    # returns pending from the entry side before touching the exit
    # evidence, so the exit content is irrelevant.
    exit_boundary = datetime(2026, 12, 24, 15, 0, 0, tzinfo=UTC)  # 10:00 ET
    exit_query_end = exit_boundary + timedelta(seconds=60)
    exit_request = exit_boundary + timedelta(milliseconds=10)
    exit_query = cohort.source_query(
        contract=contract,
        boundary_at=exit_boundary,
        available_at=exit_request,
        ceiling_at=exit_query_end,
    )
    exit_ev = oa3.quote_evidence_from_bytes(
        role="exit",
        contract=contract,
        boundary_at=exit_boundary,
        query_end_at=exit_query_end,
        query=exit_query,
        raw_bytes=_payload_bytes(),
        request_started_at=exit_request,
        response_observed_at=exit_request + timedelta(milliseconds=10),
        retrieval_observed_at=retrieval,
        computed_at=retrieval + timedelta(milliseconds=10),
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "pending"


# ─────────────────────────────────────────────────────────────────────────────
# Import under read-blocking guard
# ─────────────────────────────────────────────────────────────────────────────


def test_module_imports_without_disk_read_of_policy() -> None:
    """The module must import cleanly with the policy JSON file renamed
    out of the way; this proves the frozen policy identity is hardcoded
    and the evaluator never reads disk artefacts.
    """

    # Rename the policy file out of the way for this subprocess only
    import subprocess
    import sys
    import tempfile

    src = "research/options_estate/options_alpha_exact_option_outcome_policy_v1.json"
    backup = src + ".oa3_test_blocked"
    try:
        os.rename(src, backup)
        proc = subprocess.run(
            [sys.executable, "-c",
             "from engine import options_alpha_exact_option_outcome as oa3; "
             "print('frozen_sha', oa3.FROZEN_POLICY_SHA256); "
             "print('frozen_id', oa3.FROZEN_POLICY_ID); "
             "print('frozen_bytes_len', len(oa3._FROZEN_POLICY_BYTES))"],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, (
            f"subprocess import failed:\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}"
        )
        assert "frozen_sha 00b9eb94a97233215dff416975e42a8705cb4fc3c9a3524f9168ee66645098bf" in proc.stdout
        assert "frozen_id oa3.long_single_leg_h60_nbbo/v1" in proc.stdout
    finally:
        if os.path.exists(backup):
            os.rename(backup, src)


# ─────────────────────────────────────────────────────────────────────────────
# evaluate_or_raise contract
# ─────────────────────────────────────────────────────────────────────────────


def test_evaluate_or_raise_actually_raises_on_invalid_expression() -> None:
    """evaluate_or_raise must actually re-raise Oa3InvalidError for
    identity-defective expressions.
    """

    payload = _expression()
    payload.pop("decision_at")
    raw = cohort.canonical_json_bytes(payload)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(payload))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=payload, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
        rows=[],
    )
    with pytest.raises(oa3.Oa3InvalidError):
        oa3.evaluate_or_raise(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)


def test_evaluate_or_raise_returns_fixture_for_unavailable_data() -> None:
    """evaluate_or_raise still returns a fixture record for data-side
    unavailability (a missing quote is not an integrity failure).
    """

    contract = _contract_for(_expression())
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    entry_ev = _evidence(
        role="entry",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit",
        contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(),
        response_observed_at=_response_clock(),
        retrieval_observed_at=after_window,
        computed_at=after_window,
        rows=[],
    )
    record = oa3.evaluate_or_raise(
        _expression_receipt(),
        entry_evidence=entry_ev,
        exit_evidence=exit_ev,
    )
    assert record["status"] == "unavailable"


# ─────────────────────────────────────────────────────────────────────────────
# RED-first behavioral coverage for META-CEO Ruling A-H
# ─────────────────────────────────────────────────────────────────────────────


def test_red_shifted_entry_query_window_is_invalid() -> None:
    """An entry evidence whose boundary_at / query_end_at disagree with the
    canonical expression.available_at/+60s window is rejected as
    EVIDENCE_QUERY_MISMATCH even though the query itself is self-consistent
    (Ruling A: reject wrong per-role windows).
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    shifted_boundary = ENTRY_AVAILABLE_UTC + timedelta(milliseconds=500)
    shifted_window_end = shifted_boundary + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS)
    shifted_query = cohort.source_query(
        contract=contract, boundary_at=shifted_boundary,
        available_at=shifted_boundary + timedelta(milliseconds=10),
        ceiling_at=shifted_window_end,
    )
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract,
        boundary_at=shifted_boundary, query_end_at=shifted_window_end,
        query=shifted_query, raw_bytes=_payload_bytes(*entry_rows),
        request_started_at=shifted_boundary + timedelta(milliseconds=10),
        response_observed_at=shifted_boundary + timedelta(milliseconds=20),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
    )
    exit_ev = _evidence(
        role="exit", contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


def test_red_shortened_entry_window_is_invalid() -> None:
    """A 30-second window instead of 60s is rejected (Ruling A: full 60s)."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    short_end = ENTRY_AVAILABLE_UTC + timedelta(seconds=30)
    short_query = cohort.source_query(
        contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        available_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10),
        ceiling_at=short_end,
    )
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC, query_end_at=short_end,
        query=short_query, raw_bytes=_payload_bytes(*entry_rows),
        request_started_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10),
        response_observed_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=20),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
    )
    exit_ev = _evidence(
        role="exit", contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


def test_red_extended_entry_window_is_invalid() -> None:
    """A 90-second window instead of 60s is rejected (Ruling A: exactly +60s)."""

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    long_end = ENTRY_AVAILABLE_UTC + timedelta(seconds=90)
    long_query = cohort.source_query(
        contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        available_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10),
        ceiling_at=long_end,
    )
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract,
        boundary_at=ENTRY_AVAILABLE_UTC, query_end_at=long_end,
        query=long_query, raw_bytes=_payload_bytes(*entry_rows),
        request_started_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10),
        response_observed_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=20),
        retrieval_observed_at=long_end + timedelta(seconds=2),
        computed_at=long_end + timedelta(seconds=2) + timedelta(milliseconds=10),
    )
    exit_ev = _evidence(
        role="exit", contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=long_end + timedelta(seconds=2),
        computed_at=long_end + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_QUERY_MISMATCH"


def test_red_future_selected_event_with_ordered_clocks_is_invalid() -> None:
    """A selected event after retrieval is rejected (Ruling B: the analyst
    cannot have observed a quote timestamp they had not yet seen).
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    # Retrieval at +3s (still inside window); entry event at +5s — selected
    # event is FUTURE relative to retrieval.
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_AVAILABLE_UTC + timedelta(seconds=3),
        computed_at=ENTRY_AVAILABLE_UTC + timedelta(seconds=3, milliseconds=10),
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_AVAILABLE_UTC + timedelta(seconds=3),
        computed_at=ENTRY_AVAILABLE_UTC + timedelta(seconds=3, milliseconds=10),
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "invalid"
    assert record["reason"] == "EVIDENCE_SELECTED_EVENT_FUTURE"


def test_red_quote_present_but_pre_window_maturity_is_pending() -> None:
    """A quote is observed inside the window but retrieval sits BEFORE
    the window end: pending (Ruling C: window maturity unconditional).
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=2)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    contract = _contract_for(_expression())
    retrieval = ENTRY_AVAILABLE_UTC + timedelta(seconds=10)
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval, computed_at=retrieval,
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval, computed_at=retrieval,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "pending"
    assert record["entry"]["selected"] is not None


def test_red_request_before_full_window_ends_is_pending() -> None:
    """request_started_at sits inside the window; retrieval sits BEFORE
    the window end.  Pending (Ruling C)."""

    contract = _contract_for(_expression())
    retrieval = ENTRY_AVAILABLE_UTC + timedelta(seconds=20)
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10),
        response_observed_at=ENTRY_AVAILABLE_UTC + timedelta(milliseconds=20),
        retrieval_observed_at=retrieval, computed_at=retrieval,
        rows=[],
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=retrieval, computed_at=retrieval,
        rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "pending"


def test_red_naive_clock_in_evidence_is_invalid() -> None:
    """A naive datetime on any of the evidence clocks is integrity-invalid
    (Ruling B: never infer timezone; require tzinfo).
    """

    contract = _contract_for(_expression())
    naive_boundary = ENTRY_AVAILABLE_UTC.replace(tzinfo=None)
    with pytest.raises(oa3.Oa3InvalidError, match="naive"):
        oa3.quote_evidence_from_bytes(
            role="entry", contract=contract,
            boundary_at=naive_boundary,
            query_end_at=ENTRY_END_UTC,
            query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
            raw_bytes=_payload_bytes(),
            request_started_at=_request_clock(),
            response_observed_at=_response_clock(),
            retrieval_observed_at=RETRIEVAL_AT,
            computed_at=COMPUTED_UTC,
        )


def test_red_post_construction_mutation_of_parsed_payload_does_not_corrupt_record() -> None:
    """Caller mutation of the evidence parsed_payload AFTER construction
    does not bleed into the evaluate result (Ruling B: deep-freeze).
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    exit_window_mature = entry_event + EXIT_HORIZON + EXIT_WINDOW + timedelta(seconds=2)
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=exit_window_mature,
        computed_at=exit_window_mature + timedelta(milliseconds=10),
        rows=exit_rows,
    )
    # Caller-side mutation: this must not affect the record (Ruling B:
    # deep-freeze).  parsed_payload is a tuple of read-only mapping proxies
    # over deep-copied dicts; item assignment on the proxy raises TypeError
    # and the eval result is unaffected.
    if entry_ev.parsed_payload is not None:
        with pytest.raises(TypeError):
            entry_ev.parsed_payload[0]["ask"] = "999.99"  # type: ignore[index]
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "complete"
    assert Decimal(str(record["entry"]["selected"]["price"])) == Decimal("2.30")


def test_red_malformed_json_is_unavailable_not_invalid() -> None:
    """Malformed source JSON: QUOTE_RESPONSE_INVALID (unavailable) with
    parse_error preserved.  Contrasted with mismatched raw/payload which
    is integrity-invalid (Ruling E).
    """

    contract = _contract_for(_expression())
    malformed = b"\xff\xfe malformed bytes \x00"
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        query_end_at=ENTRY_END_UTC,
        query=_expected_query(contract, ENTRY_AVAILABLE_UTC, _request_clock(), ENTRY_END_UTC),
        raw_bytes=malformed,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC,
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "unavailable"
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"
    assert record["entry"]["raw_response_sha256"] == sha256(malformed).hexdigest()


def test_red_mismatched_raw_and_payload_is_invalid() -> None:
    """A receipt whose raw_bytes parse to a different Mapping than
    parsed_payload is integrity-invalid (Ruling E).  Contrasted with the
    malformed-bytes case which is unavailable.
    """

    payload = _expression()
    raw = cohort.canonical_json_bytes({"different": True, **payload})
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(payload))
    ).hexdigest()
    with pytest.raises(oa3.Oa3InvalidError, match="disagrees"):
        oa3.ExpressionReceipt(
            raw_bytes=raw, parsed_payload=payload,
            upstream_digest_sha256=upstream,
        )


def test_red_exact_close_60s_normal_session_is_excluded() -> None:
    """available_at + 60s lands at or past the RTH close — excluded
    (Ruling D: equality to close is excluded under
    HORIZON_CROSSES_SESSION_CLOSE).
    """

    # Regular session: 09:30-16:00 ET.  Boundary at 15:59:01 ET → entry
    # window end = 16:00:01 ET > session close.
    boundary = datetime(2026, 10, 15, 19, 59, 1, tzinfo=UTC)  # 15:59:01 ET
    receipt = _expression(
        available_at=boundary.isoformat().replace("+00:00", "Z"),
        decision_at=boundary.isoformat().replace("+00:00", "Z"),
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(receipt)
    retrieval_at = boundary + timedelta(seconds=2)
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract, boundary_at=boundary,
        query_end_at=boundary + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS),
        query=_expected_query(
            contract, boundary, boundary + timedelta(milliseconds=10),
            boundary + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS),
        ),
        raw_bytes=_payload_bytes(),
        request_started_at=boundary + timedelta(milliseconds=10),
        response_observed_at=boundary + timedelta(milliseconds=20),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
    )
    # Dummy in-RTH exit (the entry exclusion fires before exit is read).
    exit_boundary = ENTRY_AVAILABLE_UTC + timedelta(minutes=30)
    exit_query_end = exit_boundary + timedelta(seconds=oa3.EXIT_WINDOW_SECONDS)
    exit_request = exit_boundary + timedelta(milliseconds=10)
    exit_query = cohort.source_query(
        contract=contract, boundary_at=exit_boundary,
        available_at=exit_request, ceiling_at=exit_query_end,
    )
    exit_ev = oa3.quote_evidence_from_bytes(
        role="exit", contract=contract, boundary_at=exit_boundary,
        query_end_at=exit_query_end, query=exit_query, raw_bytes=_payload_bytes(),
        request_started_at=exit_request,
        response_observed_at=exit_request + timedelta(milliseconds=10),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "HORIZON_CROSSES_SESSION_CLOSE"


def test_red_exact_close_60s_early_close_is_excluded() -> None:
    """Early close at 13:00 ET: boundary at 12:59:01 ET → entry window
    end = 13:00:01 ET = early close + 1s.  Excluded (Ruling D)."""

    boundary = datetime(2026, 12, 24, 17, 59, 1, tzinfo=UTC)  # 12:59:01 ET
    receipt = _expression(
        available_at=boundary.isoformat().replace("+00:00", "Z"),
        decision_at=boundary.isoformat().replace("+00:00", "Z"),
        expiration="2026-12-31",
        occ_symbol="SOFI  261231C00016000",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    contract = _contract_for(receipt)
    retrieval_at = boundary + timedelta(seconds=2)
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract, boundary_at=boundary,
        query_end_at=boundary + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS),
        query=_expected_query(
            contract, boundary, boundary + timedelta(milliseconds=10),
            boundary + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS),
        ),
        raw_bytes=_payload_bytes(),
        request_started_at=boundary + timedelta(milliseconds=10),
        response_observed_at=boundary + timedelta(milliseconds=20),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
    )
    exit_boundary = datetime(2026, 12, 24, 16, 0, 0, tzinfo=UTC)  # 11:00 ET
    exit_query_end = exit_boundary + timedelta(seconds=oa3.EXIT_WINDOW_SECONDS)
    exit_request = exit_boundary + timedelta(milliseconds=10)
    exit_query = cohort.source_query(
        contract=contract, boundary_at=exit_boundary,
        available_at=exit_request, ceiling_at=exit_query_end,
    )
    exit_ev = oa3.quote_evidence_from_bytes(
        role="exit", contract=contract, boundary_at=exit_boundary,
        query_end_at=exit_query_end, query=exit_query, raw_bytes=_payload_bytes(),
        request_started_at=exit_request,
        response_observed_at=exit_request + timedelta(milliseconds=10),
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at + timedelta(milliseconds=10),
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "HORIZON_CROSSES_SESSION_CLOSE"


def test_red_expired_contract_is_excluded() -> None:
    """available_at sits on 2026-10-15 with expiration 2026-10-14: the
    contract expired yesterday.  EXPRESSION_CONTRACT_EXPIRED (Ruling D).
    The exclusion fires during receipt validation, BEFORE any evidence is
    parsed, so a stub entry/exit evidence is fine.
    """

    boundary = datetime(2026, 10, 15, 14, 0, 0, tzinfo=UTC)
    receipt = _expression(
        available_at=boundary.isoformat().replace("+00:00", "Z"),
        decision_at=boundary.isoformat().replace("+00:00", "Z"),
        expiration="2026-10-14",
        occ_symbol="SOFI  261014C00016000",
    )
    raw = cohort.canonical_json_bytes(receipt)
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(receipt))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=receipt, upstream_digest_sha256=upstream,
    )
    # Dummy in-RTH entry/exit evidence — the expired-contract check fires
    # during receipt validation BEFORE any evidence is consulted, so the
    # only requirement is that the records are well-formed enough for the
    # stub construction to succeed.
    contract = _contract_for(_expression())  # use the default future-dated contract
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=[],
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "excluded"
    assert record["reason"] == "EXPRESSION_CONTRACT_EXPIRED"


def test_red_evaluate_or_raise_refuses_non_expression_receipt() -> None:
    """evaluate_or_raise refuses a Mapping / bytes input (Ruling G:
    ExpressionReceipt with preserved raw bytes is the only public entry
    point)."""

    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    with pytest.raises((oa3.Oa3InvalidError, oa3.Oa3InputError)):
        oa3.evaluate_or_raise(_expression(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    raw = cohort.canonical_json_bytes(_expression())
    with pytest.raises((oa3.Oa3InvalidError, oa3.Oa3InputError)):
        oa3.evaluate_or_raise(raw, entry_evidence=entry_ev, exit_evidence=exit_ev)


def test_red_digest_mismatch_evaluate_or_raise_raises() -> None:
    """evaluate_or_raise must raise when upstream_digest disagrees with
    the canonical-immutable digest (Ruling G).
    """

    payload = _expression()
    raw = cohort.canonical_json_bytes(payload)
    expr = oa3.ExpressionReceipt(
        raw_bytes=raw, parsed_payload=payload,
        upstream_digest_sha256="0" * 64,
    )
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    with pytest.raises(oa3.Oa3InvalidError, match="EXPRESSION_DIGEST_MISMATCH"):
        oa3.evaluate_or_raise(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)


def test_red_query_mismatch_evaluate_or_raise_raises() -> None:
    """evaluate_or_raise must raise on EVIDENCE_QUERY_MISMATCH
    (Ruling F: every returned invalid/excluded is raised).
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    shifted_boundary = ENTRY_AVAILABLE_UTC + timedelta(milliseconds=500)
    shifted_end = shifted_boundary + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS)
    shifted_query = cohort.source_query(
        contract=contract, boundary_at=shifted_boundary,
        available_at=shifted_boundary + timedelta(milliseconds=10),
        ceiling_at=shifted_end,
    )
    entry_ev = oa3.quote_evidence_from_bytes(
        role="entry", contract=contract, boundary_at=shifted_boundary,
        query_end_at=shifted_end, query=shifted_query,
        raw_bytes=_payload_bytes(*entry_rows),
        request_started_at=shifted_boundary + timedelta(milliseconds=10),
        response_observed_at=shifted_boundary + timedelta(milliseconds=20),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
    )
    exit_ev = _evidence(
        role="exit", contract=contract,
        boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=exit_rows,
    )
    with pytest.raises(oa3.Oa3InvalidError, match="EVIDENCE_QUERY_MISMATCH"):
        oa3.evaluate_or_raise(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)


def test_red_non_canonical_valid_json_remains_valid() -> None:
    """Raw bytes with JSON whitespace / key-order variation parse to the
    same canonical Mapping; the receipt stays valid and the upstream
    digest binds to the canonical form.
    """

    payload = _expression()
    canonical_raw = cohort.canonical_json_bytes(payload)
    # Re-serialize with extra whitespace and a slightly different key order
    non_canonical = (
        b'{\n  "expression_id": "' + payload["expression_id"].encode() + b'",\n'
        b'  "policy_version": "v1",\n'
        b'  "source_candidate_id": "' + payload["source_candidate_id"].encode() + b'",\n'
        b'  "decision_receipt_sha256": "' + payload["decision_receipt_sha256"].encode() + b'",\n'
        b'  "source_rule_digest_sha256": "' + payload["source_rule_digest_sha256"].encode() + b'",\n'
        b'  "selection_frozen_before_outcomes": true,\n'
        b'  "selection_fence_at": "' + payload["selection_fence_at"].encode() + b'",\n'
        b'  "root": "SOFI",\n  "expiration": "2026-10-16",\n'
        b'  "right": "call",\n  "strike": "16",\n  "strike_millis": 16000,\n'
        b'  "occ_symbol": "SOFI  261016C00016000",\n  "position": "long",\n'
        b'  "quantity_contracts": 1,\n  "multiplier": 100,\n'
        b'  "standard_deliverable": true,\n  "single_leg": true,\n'
        b'  "package": false,\n  "decision_at": "' + payload["decision_at"].encode() + b'",\n'
        b'  "available_at": "' + payload["available_at"].encode() + b'"\n}\n'
    )
    assert non_canonical != canonical_raw
    upstream = sha256(
        cohort.canonical_json_bytes(_canonical_fields_for_digest(payload))
    ).hexdigest()
    expr = oa3.ExpressionReceipt(
        raw_bytes=non_canonical, parsed_payload=payload,
        upstream_digest_sha256=upstream,
    )
    # The receipt accepted the non-canonical bytes; the raw SHA differs from
    # the canonical payload SHA, both are bound to the record.
    contract = _contract_for(_expression())
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=RETRIEVAL_AT, computed_at=COMPUTED_UTC, rows=[],
    )
    record = oa3.evaluate(expr, entry_evidence=entry_ev, exit_evidence=exit_ev)
    # The status is pending (no quotes) but the receipt itself is valid:
    # the upstream digest matches and the raw SHA is bound to the receipt block.
    assert record["status"] in {"pending", "complete", "unavailable"}


def test_red_exact_decimal_arithmetic_100_contracts_at_0_65_fee() -> None:
    """Net return formula (Ruling G): exact Decimal arithmetic.

    entry ask = $2.30, exit bid = $2.40, quantity=1 contract, multiplier=100.
    Formula:
      cost_in    = 100 * entry_ask + 0.65 = 230.65
      proceeds   = 100 * exit_bid  - 0.65 = 239.35
      net_pct    = 100 * (proceeds - cost_in) / cost_in
                = 100 * 8.70 / 230.65 = 3.771949...
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    contract = _contract_for(_expression())
    exit_window_mature = entry_event + EXIT_HORIZON + EXIT_WINDOW + timedelta(seconds=2)
    entry_ev = _evidence(
        role="entry", contract=contract, boundary_at=ENTRY_AVAILABLE_UTC,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=ENTRY_END_UTC + timedelta(seconds=2),
        computed_at=ENTRY_END_UTC + timedelta(seconds=2) + timedelta(milliseconds=10),
        rows=entry_rows,
    )
    exit_ev = _evidence(
        role="exit", contract=contract, boundary_at=entry_event + EXIT_HORIZON,
        request_started_at=_request_clock(), response_observed_at=_response_clock(),
        retrieval_observed_at=exit_window_mature,
        computed_at=exit_window_mature + timedelta(milliseconds=10),
        rows=exit_rows,
    )
    record = oa3.evaluate(_expression_receipt(), entry_evidence=entry_ev, exit_evidence=exit_ev)
    assert record["status"] == "complete"
    expected = (
        Decimal("100") * (
            (Decimal("100") * Decimal("2.40") - Decimal("0.65"))
            - (Decimal("100") * Decimal("2.30") + Decimal("0.65"))
        ) / (Decimal("100") * Decimal("2.30") + Decimal("0.65"))
    )
    actual = Decimal(str(record["net_return_pct"]))
    # Tolerate the canonical 6-decimal rounding the record emits.
    assert abs(actual - expected) < Decimal("0.00001")