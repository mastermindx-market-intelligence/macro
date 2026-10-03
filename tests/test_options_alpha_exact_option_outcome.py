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
* same-day, non-standard, non-100 multiplier, package, short, non-session
  expressions stay out of the denominator;
* premarket, post-close, normal-session-close-crossing and early-close-crossing
  windows all fail closed under explicit reasons;
* raw-bytes/payload mismatch, Decimal precision, all-false authority, causal
  clock ordering, and SHA256 + byte-count receipts are bound to the record.

The tests deliberately avoid running the existing benchmark cohort fixtures;
they build only the fixtures the OA-3 wrapper itself owns.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from engine import options_alpha_exact_option_outcome as oa3
from engine import options_nbbo_cohort as cohort


UTC = timezone.utc
ET = oa3.ET

# A regular NYSE session (Thursday, full RTH).  Used for happy-path tests.
REGULAR_SESSION = "2026-10-15"
ENTRY_AVAILABLE_UTC = datetime(2026, 10, 15, 14, 0, 0, tzinfo=UTC)  # 10:00 ET
ENTRY_END_UTC = ENTRY_AVAILABLE_UTC + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS)
REQUEST_STARTED_UTC = ENTRY_AVAILABLE_UTC + timedelta(milliseconds=10)
RESPONSE_OBSERVED_UTC = REQUEST_STARTED_UTC + timedelta(seconds=1)


def _retrieval_after(entry_event: datetime) -> datetime:
    """A retrieval clock that comfortably clears both entry and exit windows."""

    exit_end = entry_event + timedelta(minutes=60, seconds=60)
    return exit_end + timedelta(seconds=2)

# NYSE early-close session (Thursday, 1pm ET close, regular full session).
EARLY_CLOSE_SESSION = "2026-12-24"

# Tuesday 2026-11-03 is the day before 2026 Election Day; non-NYSE holiday? In
# practice we use ``EXPRESSION_DATE_NOT_NYSE_SESSION`` cases via a known
# exchange holiday.  2026-11-26 (Thanksgiving) is a NYSE holiday.
THANKSGIVING = "2026-11-26"

EXPRESSION_ID = "oa3:expr:0001"
POLICY_VERSION = "v1"
SOURCE_CANDIDATE_ID = "oa3:cand:0001"
DECISION_RECEIPT_SHA = "1" * 64
SOURCE_RULE_SHA = "2" * 64
SELECTION_FENCE_AT = "2026-10-15T13:00:00.000000Z"
DECISION_AT = "2026-10-15T13:00:00.000000Z"
AVAILABLE_AT = ENTRY_AVAILABLE_UTC.isoformat().replace("+00:00", "Z")

# A retrieval clock that comfortably clears both the 60s entry window and
# any H+60 exit window, well inside the regular session (16:00 ET close).
RETRIEVAL_AT = datetime(2026, 10, 15, 17, 0, 0, tzinfo=UTC)
COMPUTED_UTC = RETRIEVAL_AT + timedelta(seconds=1)


def _expression(**overrides) -> dict:
    """Return a baseline OA-3 expression receipt."""

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
) -> dict:
    return {
        "symbol": symbol,
        "expiration": expiration,
        "right": "call",
        "strike": 16.0,
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
    """Format a quote row whose timestamp is ``event_at_utc`` (UTC, microseconds).
    parse_quote_response accepts naive ET or aware UTC timestamps.
    """

    ts = event_at_utc.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    return _quote_row(timestamp=ts, **overrides)


def _payload(*rows: dict) -> bytes:
    return cohort.canonical_json_bytes(list(rows))


def _quote_payload(*rows) -> bytes:
    return _payload(*rows)


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────


def test_complete_first_valid_ask_and_bid_inside_60s_windows() -> None:
    """First valid firm ask inside [available_at, available_at+60s] wins,
    and the first valid firm bid inside [entry.event_at+60m, +60s] wins.
    Both observations lie inside the same NYSE RTH session.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)  # inside entry window
    exit_event = entry_event + timedelta(minutes=60) + timedelta(seconds=5)
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

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*entry_rows),
        exit_quote=_quote_payload(*exit_rows),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )

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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*rows),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*entry_rows),
        exit_quote=_quote_payload(*exit_rows),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
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

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*entry_rows),
        exit_quote=_quote_payload(*exit_rows),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "complete"
    assert record["exit"]["query_bounds"]["start_at"] == entry_event + timedelta(minutes=60)
    assert record["exit"]["query_bounds"]["end_at"] == entry_event + timedelta(minutes=60, seconds=60)


def test_decimal_fees_use_exact_one_contract_formula() -> None:
    """Decimal precision must match the frozen 100-multiplier /
    USD 0.65-per-side formula byte-for-byte.

    Expected return for entry=1.00 / exit=1.20 is ``18.579235``
    (the same value the existing policy test pins).
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=2)
    exit_event = entry_event + timedelta(minutes=60, seconds=2)
    entry_rows = [_row_at(entry_event, bid="0.95", bid_size=10, bid_exchange=11, bid_condition=50, ask="1.00", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="1.20", bid_size=10, bid_exchange=11, bid_condition=50, ask="1.30", ask_size=12)]
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*entry_rows),
        exit_quote=_quote_payload(*exit_rows),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert isinstance(record["net_return_pct"], Decimal)
    assert str(record["net_return_pct"]) == "18.579235"
    assert record["cost"]["fee_per_side_usd"] == "0.65"
    assert record["cost"]["multiplier"] == 100


def test_record_carries_exact_all_false_authority() -> None:
    """The fixture record must carry the exact all-false authority block,
    no flag may be true and no fill claim may be made.
    """

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["authority"] == oa3.ALL_FALSE_AUTHORITY
    assert all(value is False for value in record["authority"].values())
    assert "may_claim_fill" in record["authority"]
    assert record["quote_source"]["executable_fill_claim"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Status transitions: pending vs unavailable
# ─────────────────────────────────────────────────────────────────────────────


def test_early_now_is_pending_before_entry_window_matures() -> None:
    """If now is before entry_end, status is pending and net_return is None."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=ENTRY_AVAILABLE_UTC + timedelta(seconds=5),
        computed_at=ENTRY_AVAILABLE_UTC + timedelta(seconds=5),
    )
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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*entry_rows),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at,
    )
    assert record["status"] == "pending"
    assert record["entry"]["selected"]["price"] == Decimal("2.30")
    assert record["exit"]["selected"] is None
    assert record["net_return_pct"] is None


def test_no_quote_inside_entry_window_is_unavailable() -> None:
    """No valid firm ask inside [available_at, available_at+60s] ->
    ENTRY_QUOTE_UNAVAILABLE after the window has matured.
    """

    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),  # empty
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=after_window,
        computed_at=after_window,
    )
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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*entry_rows),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=retrieval_at,
        computed_at=retrieval_at,
    )
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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*rows),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=after_window,
        computed_at=after_window,
    )
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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(bad),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=after_window,
        computed_at=after_window,
    )
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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(bad),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=after_window,
        computed_at=after_window,
    )
    assert record["status"] == "unavailable"
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"


def test_crossed_quote_is_not_selected_and_falls_unavailable() -> None:
    """A row whose ask < bid is crossed; with no other eligible ask the
    window records no candidate and the outcome is unavailable.
    """

    crossed = _row_at(ENTRY_AVAILABLE_UTC + timedelta(seconds=2), bid="2.40", ask="2.30")
    after_window = ENTRY_END_UTC + timedelta(minutes=1)
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(crossed),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=after_window,
        computed_at=after_window,
    )
    assert record["status"] == "unavailable"
    assert record["reason"] == "ENTRY_QUOTE_UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# Identity / population / session law
# ─────────────────────────────────────────────────────────────────────────────


def test_missing_required_field_is_invalid() -> None:
    """A receipt missing an immutable field produces an invalid record."""

    receipt = _expression()
    receipt.pop("decision_at")
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"
    assert record["net_return_pct"] is None
    assert record["entry"]["selected"] is None
    assert record["exit"]["selected"] is None


def test_invalid_occ_symbol_is_invalid() -> None:
    """An OCC symbol that does not match the exact fields -> invalid."""

    receipt = _expression(occ_symbol="SOFI  261016C00099999")
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"
    assert record["net_return_pct"] is None


def test_policy_version_must_be_v_prefixed() -> None:
    receipt = _expression(policy_version="broken")
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"


def test_available_at_preceding_decision_at_is_invalid() -> None:
    """available_at must never precede decision_at."""

    receipt = _expression(
        decision_at="2026-10-15T14:00:00.000000Z",
        available_at="2026-10-15T13:55:00.000000Z",
    )
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"


def test_zero_dte_expression_is_excluded() -> None:
    """Same-day expiration is outside v1: status=excluded, reason=SAME_DAY_EXPIRATION."""

    receipt = _expression(
        expiration=REGULAR_SESSION,  # same date as entry session
        occ_symbol="SOFI  261015C00016000",
    )
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "SAME_DAY_EXPIRATION"
    assert record["net_return_pct"] is None


def test_non_standard_deliverable_is_excluded() -> None:
    """A receipt marking standard_deliverable=False is outside v1."""

    receipt = _expression(standard_deliverable=False)
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "NON_STANDARD_DELIVERABLE"


def test_non_standard_multiplier_is_excluded() -> None:
    """A non-100 multiplier is outside v1."""

    receipt = _expression(multiplier=50)
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "NON_STANDARD_MULTIPLIER"


def test_quantity_not_one_is_excluded() -> None:
    """A quantity other than one contract is outside v1."""

    receipt = _expression(quantity_contracts=5)
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "QUANTITY_NOT_ONE"


def test_short_option_is_excluded() -> None:
    """A short position is outside v1."""

    receipt = _expression(position="short")
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "SHORT_OPTION_NOT_SUPPORTED"


def test_package_receipt_is_excluded() -> None:
    """A receipt carrying package=True is outside v1 (single-leg only)."""

    receipt = _expression(package=True)
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
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
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "EXPRESSION_DATE_NOT_NYSE_SESSION"


def test_premarket_entry_boundary_is_excluded() -> None:
    """available_at before the 9:30 ET open is ENTRY_BOUNDARY_OUTSIDE_RTH."""

    premarket = datetime(2026, 10, 15, 13, 0, 0, tzinfo=UTC)  # 09:00 ET
    receipt = _expression(
        available_at=premarket.isoformat().replace("+00:00", "Z"),
        decision_at=premarket.isoformat().replace("+00:00", "Z"),
    )
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "ENTRY_BOUNDARY_OUTSIDE_RTH"


def test_post_close_entry_boundary_is_excluded() -> None:
    """available_at at or after 16:00 ET is ENTRY_BOUNDARY_OUTSIDE_RTH."""

    post = datetime(2026, 10, 15, 20, 0, 1, tzinfo=UTC)  # 16:00:01 ET
    receipt = _expression(
        available_at=post.isoformat().replace("+00:00", "Z"),
        decision_at=post.isoformat().replace("+00:00", "Z"),
    )
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "ENTRY_BOUNDARY_OUTSIDE_RTH"


def test_normal_session_horizon_crosses_close_is_excluded() -> None:
    """An entry so close to 16:00 ET that the exit window crosses the
    close is excluded under HORIZON_CROSSES_SESSION_CLOSE.
    """

    near_close = datetime(2026, 10, 15, 19, 31, 0, tzinfo=UTC)  # 15:31 ET
    receipt = _expression(
        available_at=near_close.isoformat().replace("+00:00", "Z"),
        decision_at=near_close.isoformat().replace("+00:00", "Z"),
    )
    entry_event = near_close + timedelta(seconds=5)
    rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    request_started = near_close + timedelta(milliseconds=10)
    response_observed = request_started + timedelta(seconds=1)
    retrieval = request_started + timedelta(seconds=2)
    computed = retrieval + timedelta(milliseconds=10)
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(*rows),
        exit_quote=_quote_payload(),
        request_started_at=request_started,
        response_observed_at=response_observed,
        retrieval_observed_at=retrieval,
        computed_at=computed,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "HORIZON_CROSSES_SESSION_CLOSE"


def test_early_close_horizon_crosses_close_is_excluded() -> None:
    """On an early-close session (13:00 ET), an entry that pushes the
    H+60 exit window past the early close is excluded.
    """

    # 2026-12-24 closes at 13:00 ET (17:00 UTC in EST? No — Dec is EST = UTC-5).
    near_close = datetime(2026, 12, 24, 17, 31, 0, tzinfo=UTC)  # 12:31 ET
    receipt = _expression(
        available_at=near_close.isoformat().replace("+00:00", "Z"),
        decision_at=near_close.isoformat().replace("+00:00", "Z"),
        expiration="2025-12-31",  # ensure not 0DTE
        occ_symbol="SOFI  251231C00016000",
    )
    entry_event = near_close + timedelta(seconds=5)
    rows = [
        _quote_row(
            timestamp=entry_event.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            expiration="2025-12-31",
            bid="2.30",
            bid_size=10,
            bid_exchange=11,
            bid_condition=50,
            ask="2.30",
            ask_size=10,
            ask_exchange=11,
            ask_condition=50,
        )
    ]
    request_started = near_close + timedelta(milliseconds=10)
    response_observed = request_started + timedelta(seconds=1)
    retrieval = request_started + timedelta(seconds=2)
    computed = retrieval + timedelta(milliseconds=10)
    record = oa3.evaluate(
        receipt,
        entry_quote=_quote_payload(*rows),
        exit_quote=_quote_payload(),
        request_started_at=request_started,
        response_observed_at=response_observed,
        retrieval_observed_at=retrieval,
        computed_at=computed,
    )
    assert record["status"] == "excluded"
    assert record["reason"] == "HORIZON_CROSSES_SESSION_CLOSE"


# ─────────────────────────────────────────────────────────────────────────────
# Receipt provenance / clocks
# ─────────────────────────────────────────────────────────────────────────────


def test_raw_bytes_and_payload_mismatch_is_invalid() -> None:
    """QuoteReceipt.__post_init__ fails closed when bytes and payload disagree."""

    raw = b'[{"different":true}]'
    parsed = _quote_payload(_row_at(ENTRY_AVAILABLE_UTC + timedelta(seconds=2)))
    with pytest.raises(oa3.Oa3InputError):
        oa3.QuoteReceipt(raw_bytes=raw, parsed_payload=json.loads(parsed))


def test_quote_receipt_construction_is_byte_strict() -> None:
    """QuoteReceipt built from a payload round-trips its own bytes."""

    payload = [_row_at(ENTRY_AVAILABLE_UTC + timedelta(seconds=2))]
    receipt = oa3.quote_receipt_from_payload(payload)
    assert receipt.raw_bytes == cohort.canonical_json_bytes(payload)


def test_quote_receipt_constructor_rejects_malformed_bytes() -> None:
    with pytest.raises(oa3.Oa3InputError):
        oa3.quote_receipt_from_bytes(b"not json")


def test_receipt_provenance_binds_sha256_and_bytecount() -> None:
    """Every entry/exit block carries the SHA-256 and byte count of the
    raw response and the canonicalised payload.
    """

    entry_event = ENTRY_AVAILABLE_UTC + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)
    entry_rows = [_row_at(entry_event, ask="2.30", ask_size=10, ask_exchange=11, ask_condition=50)]
    exit_rows = [_row_at(exit_event, bid="2.40", bid_size=10, bid_exchange=11, bid_condition=50, ask="2.50", ask_size=12)]
    entry_bytes = _quote_payload(*entry_rows)
    exit_bytes = _quote_payload(*exit_rows)

    record = oa3.evaluate(
        _expression(),
        entry_quote=entry_bytes,
        exit_quote=exit_bytes,
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    import hashlib as _hl

    assert record["entry"]["raw_response_sha256"] == _hl.sha256(entry_bytes).hexdigest()
    assert record["entry"]["raw_response_bytes"] == len(entry_bytes)
    assert record["exit"]["raw_response_sha256"] == _hl.sha256(exit_bytes).hexdigest()
    assert record["exit"]["raw_response_bytes"] == len(exit_bytes)
    assert record["entry"]["raw_response_sha256"] == record["entry"]["raw_payload_sha256"]


def test_record_carries_request_response_retrieval_and_computed_clocks() -> None:
    """The fixture record binds all four clocks explicitly."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["clocks"]["request_started_at"] == REQUEST_STARTED_UTC
    assert record["clocks"]["response_observed_at"] == RESPONSE_OBSERVED_UTC
    assert record["clocks"]["retrieval_observed_at"] == RETRIEVAL_AT
    assert record["clocks"]["computed_at"] == COMPUTED_UTC


def test_causal_clock_mismatch_request_after_response() -> None:
    """request_started_at > response_observed_at is invalid."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=RESPONSE_OBSERVED_UTC + timedelta(seconds=10),
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"
    assert "CAUSAL_CLOCK_MISMATCH" in (record["reason"] or "")


def test_causal_clock_mismatch_response_after_retrieval() -> None:
    """response_observed_at > retrieval_observed_at is invalid."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RETRIEVAL_AT + timedelta(seconds=10),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"
    assert "CAUSAL_CLOCK_MISMATCH" in (record["reason"] or "")


def test_causal_clock_mismatch_request_before_available_at() -> None:
    """request_started_at before expression.available_at is invalid."""

    earlier_request = ENTRY_AVAILABLE_UTC - timedelta(seconds=10)
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=earlier_request,
        response_observed_at=earlier_request + timedelta(seconds=1),
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "invalid"
    assert "CAUSAL_CLOCK_MISMATCH" in (record["reason"] or "")


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
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(*rows),
        exit_quote=_quote_payload(*exit_rows),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["status"] == "complete"
    assert record["entry"]["selected"]["price"] == Decimal("2.30")
    assert record["entry"]["selected"]["event_at"] == eligible


def test_expression_digest_is_stable_and_round_trips() -> None:
    """The expression_digest_sha256 must round-trip the same bytes."""

    record_a = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    record_b = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record_a["expression_digest_sha256"] == record_b["expression_digest_sha256"]
    assert record_a["expression_digest_sha256"] != record_a["policy_sha256"]


def test_policy_sha256_carries_disk_frozen_policy() -> None:
    """The record's policy_sha256 matches the on-disk policy file."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    import hashlib

    on_disk = hashlib.sha256(
        oa3.DEFAULT_POLICY_PATH_NO  # type: ignore[attr-defined]
        if False
        else open(
            "research/options_estate/options_alpha_exact_option_outcome_policy_v1.json",
            "rb",
        ).read()
    ).hexdigest()
    assert record["policy_sha256"] == on_disk


def test_benchmark_lag_rule_is_not_inherited() -> None:
    """The 600-second live-capture fence from the benchmark is NOT
    imported; the OA-3 record must make no reference to it.
    """

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
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

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    serialized = json.dumps(record, default=str)
    assert "PnL" not in serialized
    assert "quote_response_body" not in serialized
    assert "raw_response_bytes" in serialized  # byte count is allowed
    # The all-false authority may keep the literal flag name `may_claim_fill`
    # to prove NO fill claim is authorised; check the FLAG is false.
    assert record["authority"]["may_claim_fill"] is False
    assert record["quote_source"]["executable_fill_claim"] is False


def test_record_carries_schema_and_policy_id() -> None:
    """The fixture schema and policy id are present and pinned."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert record["schema"] == oa3.SCHEMA
    assert record["policy_id"] == oa3.POLICY_ID
    assert record["policy_id"] == "oa3.long_single_leg_h60_nbbo/v1"


def test_record_carries_session_window() -> None:
    """The record pins the canonical NYSE RTH window for the session."""

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    # 2026-10-15: 9:30 ET (13:30 UTC) -> 16:00 ET (20:00 UTC)
    assert record["session_rth_open"] == datetime(2026, 10, 15, 13, 30, tzinfo=UTC)
    assert record["session_rth_close"] == datetime(2026, 10, 15, 20, 0, tzinfo=UTC)
    assert record["session_date"] == "2026-10-15"


def test_status_vocabulary_is_closed() -> None:
    """No status outside the five-state vocabulary may be emitted."""

    statuses = set()
    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    statuses.add(record["status"])
    assert statuses.issubset({"pending", "complete", "unavailable", "excluded", "invalid"})


def test_expression_replayability_hash_is_stable() -> None:
    """The expression_digest_sha256 is derived from canonical expression
    fields only and excludes volatile non-deterministic fields.
    """

    record = oa3.evaluate(
        _expression(),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    digest = record["expression_digest_sha256"]
    assert isinstance(digest, str) and len(digest) == 64
    # Different expression_id yields a different digest.
    other = oa3.evaluate(
        _expression(expression_id="oa3:expr:0002"),
        entry_quote=_quote_payload(),
        exit_quote=_quote_payload(),
        request_started_at=REQUEST_STARTED_UTC,
        response_observed_at=RESPONSE_OBSERVED_UTC,
        retrieval_observed_at=RETRIEVAL_AT,
        computed_at=COMPUTED_UTC,
    )
    assert other["expression_digest_sha256"] != digest