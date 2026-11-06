"""Tests for engine.liquidity_profile — real native chip, no stubs.

Every success case asserts the payload metrics EQUAL a direct call to
``engine.liquidity_chip.compute`` on the same series, and every refusal case
exercises a documented guard of ``liquidity_profile.v1``.  Session dates come
from the real ``lib.nyse_calendar.is_session`` calendar.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from engine.liquidity_chip import (
    TIER_DEEP_THRESHOLD,
    TIER_OK_THRESHOLD,
    TIER_THIN_THRESHOLD,
    WINDOW,
    compute,
)
from engine.liquidity_profile import (
    RIGHTS_EVIDENCE,
    SCHEMA,
    STATUS_NO_COVERAGE,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    project,
)
from lib.nyse_calendar import is_session

EXPECTED_SESSION = date(2024, 1, 31)  # Wednesday, regular NYSE session
RECORDED_AT = datetime(2024, 2, 1, 15, 0, tzinfo=timezone.utc)
INGESTED_AT = "2024-01-31T20:30:00-05:00"  # == 2024-02-01T01:30:00Z, NY Jan 31
SOURCE_SHA256 = "a" * 64
EVIDENCE_SHA256 = "b" * 64

PAYLOAD_KEYS = {
    "schema", "ticker", "producer", "authority", "basis", "window_sessions",
    "sample_selection", "scope", "status", "reason", "metrics", "sample_n", "thinly_traded",
    "coverage", "recorded_at", "expected_session", "source_asof", "ingested_at",
    "published_at", "known_at", "source_sha256", "currency", "rights_evidence",
}


# --------------------------------------------------------------------------- #
#  Input builders (calendar-driven, never hardcode the 20 sessions)           #
# --------------------------------------------------------------------------- #
def _sessions_ending(end_date: date, count: int) -> list[date]:
    """The *count* NYSE sessions ending at *end_date* (inclusive), oldest first."""
    days: list[date] = []
    day = end_date
    while len(days) < count:
        if is_session(day):
            days.append(day)
        day -= timedelta(days=1)
    return list(reversed(days))


def _next_session(after_date: date) -> date:
    day = after_date + timedelta(days=1)
    while not is_session(day):
        day += timedelta(days=1)
    return day


def _previous_session(before_date: date) -> date:
    day = before_date - timedelta(days=1)
    while not is_session(day):
        day -= timedelta(days=1)
    return day


def _a_saturday() -> date:
    day = EXPECTED_SESSION
    while day.weekday() != 5:  # Saturday is never an NYSE session
        day -= timedelta(days=1)
    return day


def _frame(dates, closes, volumes) -> pd.DataFrame:
    index = pd.DatetimeIndex(pd.to_datetime(list(dates)), name="session_date")
    return pd.DataFrame({"close": list(closes), "volume": list(volumes)}, index=index)


def _default_frame(session_count: int = 25) -> pd.DataFrame:
    dates = _sessions_ending(EXPECTED_SESSION, session_count)
    closes = [10.0 + 0.5 * i for i in range(session_count)]
    volumes = [120_000 + 500 * i for i in range(session_count)]
    return _frame(dates, closes, volumes)


def _currency_evidence(**overrides) -> dict:
    evidence = {
        "ticker": "TEST",
        "currency": "USD",
        "source_sha256": EVIDENCE_SHA256,
        "source_asof": EXPECTED_SESSION.isoformat(),
        "valid_from": "2024-01-01",
        "valid_through": EXPECTED_SESSION.isoformat(),
        "vendor_note": "internal only",  # extra field: must never reach payload
    }
    evidence.update(overrides)
    return evidence


def _project(frame=None, **overrides) -> dict:
    kwargs = {
        "ticker": "TEST",
        "expected_session": EXPECTED_SESSION,
        "recorded_at": RECORDED_AT,
        "ingested_at": INGESTED_AT,
        "source_sha256": SOURCE_SHA256,
        "currency_evidence": _currency_evidence(),
    }
    kwargs.update(overrides)
    return project(frame, **kwargs)


def _uniform_frame(close: float, volume: float, count: int = WINDOW) -> pd.DataFrame:
    return _frame(_sessions_ending(EXPECTED_SESSION, count), [close] * count, [volume] * count)


# --------------------------------------------------------------------------- #
#  Success — real native compute                                              #
# --------------------------------------------------------------------------- #
def test_success_metrics_equal_real_native_compute():
    frame = _default_frame(25)
    payload = _project(frame)
    assert payload["status"] == STATUS_OK
    assert payload["reason"] is None
    assert payload["metrics"] == compute(frame["close"], frame["volume"])
    assert set(payload["metrics"]) == {
        "adv_dollar_20d_median", "tier", "days_to_build_100k", "days_to_build_1m",
    }
    assert payload["metrics"]["adv_dollar_20d_median"] > 0


def test_success_payload_shape_and_envelope():
    payload = _project(_default_frame(25))
    assert payload["schema"] == SCHEMA
    assert payload["producer"]["owner"] == "engine.liquidity_chip"
    assert payload["basis"] == "raw_close_times_raw_share_volume"
    assert payload["window_sessions"] == WINDOW == 20
    assert payload["authority"] == {
        "display_only": True,
        "decision_support_only": True,
        "rank": False,
        "gate": False,
        "sizing": False,
        "trading": False,
    }
    assert payload["scope"] == {"order_book_depth": False, "forecast": False}
    assert payload["coverage"] == {"expected_sessions": 20, "observed_sessions": 20, "source_rows": 25}
    assert payload["sample_n"] == 20
    assert payload["recorded_at"] == "2024-02-01T15:00:00Z"
    assert payload["ingested_at"] == "2024-02-01T01:30:00Z"
    assert payload["source_asof"] == EXPECTED_SESSION.isoformat()
    assert payload["expected_session"] == EXPECTED_SESSION.isoformat()
    assert payload["source_sha256"] == SOURCE_SHA256
    assert payload["published_at"] is None
    assert payload["known_at"] is None
    assert payload["rights_evidence"] == RIGHTS_EVIDENCE
    assert set(payload) == PAYLOAD_KEYS
    json.dumps(payload, allow_nan=False)  # payload is strict JSON


def test_integer_columns_and_zero_volume_session_succeed():
    dates = _sessions_ending(EXPECTED_SESSION, WINDOW)
    volumes = [1_000_000] * WINDOW
    volumes[7] = 0  # one zero-volume session inside the window is allowed
    frame = _frame(dates, [50] * WINDOW, volumes)
    payload = _project(frame)
    assert payload["status"] == STATUS_OK
    assert payload["metrics"] == compute(frame["close"], frame["volume"])
    assert payload["metrics"]["adv_dollar_20d_median"] == 50_000_000.0
    assert payload["thinly_traded"] is False


def test_earlier_history_allowed_but_excluded_from_metrics():
    frame = _default_frame(30)
    payload = _project(frame)
    assert payload["status"] == STATUS_OK
    assert payload["coverage"]["observed_sessions"] == 20
    assert payload["coverage"]["source_rows"] == 30
    assert payload["metrics"] == compute(frame["close"].tail(WINDOW), frame["volume"].tail(WINDOW))


def test_thinly_traded_tracks_native_tier():
    payload = _project(_default_frame(25))
    assert payload["thinly_traded"] is (payload["metrics"]["tier"] in ("thin", "illiquid"))


@pytest.mark.parametrize(
    ("close", "volume", "tier", "thin"),
    [
        (100.0, TIER_DEEP_THRESHOLD / 100.0, "deep", False),
        (100.0, TIER_OK_THRESHOLD / 100.0, "ok", False),
        (100.0, TIER_THIN_THRESHOLD / 100.0, "thin", True),
        (100.0, (TIER_THIN_THRESHOLD - 100.0) / 100.0, "illiquid", True),
    ],
    ids=["deep", "ok", "thin", "illiquid"],
)
def test_native_tier_thresholds_are_exact(close, volume, tier, thin):
    payload = _project(_uniform_frame(close, volume))
    assert payload["status"] == STATUS_OK
    assert payload["metrics"]["tier"] == tier
    assert payload["metrics"]["adv_dollar_20d_median"] == close * volume
    assert payload["thinly_traded"] is thin


def test_project_is_pure_and_deterministic():
    frame = _default_frame(25)
    before = frame.copy(deep=True)
    first = _project(frame)
    second = _project(frame)
    assert first == second
    pd.testing.assert_frame_equal(frame, before)


def test_payload_has_no_portfolio_holdings_or_user_fields():
    payload = _project(_default_frame(25))
    keys = set(payload) | set(payload["producer"]) | set(payload["authority"])
    keys |= set(payload["coverage"]) | set(payload["scope"]) | set(payload["currency"])
    assert not any(word in key for key in keys for word in
                   ("portfolio", "holding", "user", "account", "position"))


# --------------------------------------------------------------------------- #
#  READ_NO_COVERAGE — absent / insufficient / window / zero-adv / currency    #
# --------------------------------------------------------------------------- #
def test_none_frame_is_no_coverage():
    payload = _project(None)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "FRAME_ABSENT"
    assert payload["metrics"] is None
    assert payload["thinly_traded"] is None
    assert payload["source_asof"] is None
    assert payload["coverage"] == {"expected_sessions": 20, "observed_sessions": 0, "source_rows": 0}
    assert payload["recorded_at"] == "2024-02-01T15:00:00Z"
    json.dumps(payload, allow_nan=False)


def test_empty_frame_is_no_coverage():
    payload = _project(pd.DataFrame({"close": [], "volume": []}))
    assert payload["reason"] == "FRAME_EMPTY"
    assert payload["status"] == STATUS_NO_COVERAGE


def test_short_series_is_no_coverage():
    payload = _project(_default_frame(WINDOW - 1))
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "INSUFFICIENT_SESSIONS"


def test_gap_in_window_is_no_coverage():
    dates = _sessions_ending(EXPECTED_SESSION, 25)
    gapless = [day for day in dates if day != dates[-10]]
    frame = _frame(gapless, [10.0 + 0.5 * i for i in range(len(gapless))],
                   [100_000 + 500 * i for i in range(len(gapless))])
    payload = _project(frame)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "WINDOW_SESSIONS_MISSING"


def test_stale_frame_is_no_coverage():
    dates = _sessions_ending(_previous_session(EXPECTED_SESSION), WINDOW)
    payload = _project(_frame(dates, [10.0] * WINDOW, [100_000] * WINDOW))
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "STALE_NO_EXPECTED_SESSION"


def test_all_zero_volume_window_is_no_coverage():
    payload = _project(_uniform_frame(25.0, 0))
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "ZERO_ADV_NO_COVERAGE"
    assert payload["metrics"] is None
    assert payload["thinly_traded"] is None


def test_missing_currency_evidence_is_no_coverage():
    payload = _project(_default_frame(25), currency_evidence=None)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "CURRENCY_NOT_QUALIFIED"
    assert payload["metrics"] is None
    assert payload["thinly_traded"] is None
    assert payload["currency"] is None


@pytest.mark.parametrize(
    "evidence",
    [
        "USD",  # not a dict
        {"currency": "EUR", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-01-31",
         "valid_from": "2024-01-01", "valid_through": "2024-01-31"},
        {"currency": "usd", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-01-31",
         "valid_from": "2024-01-01", "valid_through": "2024-01-31"},
        {"currency": "USD", "source_sha256": "nope", "source_asof": "2024-01-31",
         "valid_from": "2024-01-01", "valid_through": "2024-01-31"},
        {"currency": "USD", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-01-32",
         "valid_from": "2024-01-01", "valid_through": "2024-01-31"},
        {"currency": "USD", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-01-31",
         "valid_from": None, "valid_through": "2024-01-31"},
        {"currency": "USD", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-01-31",
         "valid_from": "2024-01-15", "valid_through": "2024-01-31"},  # misses window start
        {"currency": "USD", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-01-31",
         "valid_from": "2024-01-01", "valid_through": "2024-01-30"},  # misses window end
        {"currency": "USD", "source_sha256": EVIDENCE_SHA256, "source_asof": "2024-02-02",
         "valid_from": "2024-01-01", "valid_through": "2024-01-31"},  # after recorded date
    ],
    ids=["nondict", "eur", "lowercase", "badsha", "baddate", "nobound",
         "late_start", "early_end", "future_asof"],
)
def test_unqualified_currency_is_no_coverage(evidence):
    payload = _project(_default_frame(25), currency_evidence=evidence)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["reason"] == "CURRENCY_NOT_QUALIFIED"


def test_currency_evidence_preserved_whitelist_only():
    payload = _project(
        _default_frame(25),
        currency_evidence=_currency_evidence(vendor_note="x", analyst="z"),
    )
    assert payload["status"] == STATUS_OK
    assert set(payload["currency"]) == {
        "ticker", "currency", "source_sha256", "source_asof", "valid_from", "valid_through",
    }
    assert payload["currency"]["currency"] == "USD"


# --------------------------------------------------------------------------- #
#  READ_UNAVAILABLE — malformed frames / index / values                       #
# --------------------------------------------------------------------------- #
def test_non_dataframe_frame_refuses():
    payload = _project({"close": [1.0], "volume": [1]})
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "FRAME_TYPE"
    assert payload["coverage"]["observed_sessions"] is None
    assert payload["coverage"]["source_rows"] == 0


def test_missing_columns_refuse():
    payload = _project(_default_frame(WINDOW).drop(columns=["volume"]))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "COLUMNS_MISSING"


def test_non_datetime_index_refuses():
    payload = _project(_default_frame(WINDOW).reset_index(drop=True))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INDEX_TYPE"


def test_tz_aware_index_refuses():
    frame = _default_frame(WINDOW)
    frame.index = frame.index.tz_localize("America/New_York")
    payload = _project(frame)
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INDEX_TIMEZONE"


def test_intraday_index_refuses():
    frame = _default_frame(WINDOW)
    frame.index = pd.DatetimeIndex(
        list(frame.index[:-1]) + [frame.index[-1] + pd.Timedelta(hours=16)]
    )
    payload = _project(frame)
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INDEX_NOT_MIDNIGHT"


def test_unsorted_index_refuses():
    payload = _project(_default_frame(25).iloc[::-1])
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INDEX_UNORDERED"


def test_duplicate_index_refuses():
    frame = _default_frame(25)
    payload = _project(pd.concat([frame, frame.iloc[[-1]]]))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INDEX_DUPLICATED"


def test_future_row_refuses():
    dates = _sessions_ending(EXPECTED_SESSION, 25)
    dates.append(_next_session(EXPECTED_SESSION))
    payload = _project(_frame(dates, [10.0] * len(dates), [100_000] * len(dates)))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "FUTURE_ROW"


def test_non_session_date_in_index_refuses():
    dates = _sessions_ending(EXPECTED_SESSION, 25)
    for i in range(len(dates) - 1):
        candidate = dates[i] + timedelta(days=1)
        if candidate < dates[i + 1]:  # an in-between day is never a session
            dates.insert(i + 1, candidate)
            break
    payload = _project(_frame(dates, [10.0] * len(dates), [100_000] * len(dates)))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INDEX_NOT_SESSION_DATES"


@pytest.mark.parametrize(
    ("column", "bad", "reason"),
    [
        ("close", float("nan"), "CLOSE_VALUE_INVALID"),
        ("close", float("inf"), "CLOSE_VALUE_INVALID"),
        ("close", 0.0, "CLOSE_VALUE_INVALID"),
        ("close", -5.0, "CLOSE_VALUE_INVALID"),
        ("close", "12.5", "CLOSE_VALUE_INVALID"),
        ("close", True, "CLOSE_VALUE_INVALID"),
        ("volume", float("nan"), "VOLUME_VALUE_INVALID"),
        ("volume", float("-inf"), "VOLUME_VALUE_INVALID"),
        ("volume", -1, "VOLUME_VALUE_INVALID"),
        ("volume", "100", "VOLUME_VALUE_INVALID"),
        ("volume", False, "VOLUME_VALUE_INVALID"),
    ],
    ids=["close_nan", "close_inf", "close_zero", "close_negative", "close_str",
         "close_bool", "volume_nan", "volume_inf", "volume_negative",
         "volume_str", "volume_bool"],
)
def test_invalid_selected_values_refuse(column, bad, reason):
    closes = [10.0 + 0.5 * i for i in range(WINDOW)]
    volumes = [100_000 + 500 * i for i in range(WINDOW)]
    values = {"close": closes, "volume": volumes}
    values[column][-1] = bad
    payload = _project(_frame(_sessions_ending(EXPECTED_SESSION, WINDOW),
                              values["close"], values["volume"]))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == reason
    assert payload["metrics"] is None
    assert payload["thinly_traded"] is None


def test_dollar_volume_overflow_refuses():
    payload = _project(_uniform_frame(1e308, 1e10))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "DOLLAR_VOLUME_OVERFLOW"


# --------------------------------------------------------------------------- #
#  READ_UNAVAILABLE — clocks, ingest bounds, source digest                    #
# --------------------------------------------------------------------------- #
def test_naive_recorded_at_refuses():
    payload = _project(_default_frame(25), recorded_at=datetime(2024, 2, 1, 15, 0))
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "RECORDED_AT_NAIVE"
    assert payload["recorded_at"] is None
    json.dumps(payload, allow_nan=False)


def test_invalid_recorded_at_refuses():
    payload = _project(_default_frame(25), recorded_at="not-a-clock")
    assert payload["reason"] == "RECORDED_AT_INVALID"


def test_non_datetime_recorded_at_refuses():
    payload = _project(_default_frame(25), recorded_at=1234)
    assert payload["reason"] == "RECORDED_AT_TYPE"


def test_recorded_at_offset_converts_to_utc():
    payload = _project(
        _default_frame(25),
        recorded_at=datetime(2024, 2, 1, 10, 0, tzinfo=timezone(timedelta(hours=-5))),
    )
    assert payload["status"] == STATUS_OK
    assert payload["recorded_at"] == "2024-02-01T15:00:00Z"


def test_expected_session_must_be_a_session():
    payload = _project(_default_frame(25), expected_session=_a_saturday())
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "EXPECTED_SESSION_NOT_TRADING_DAY"


def test_expected_session_type_refuses():
    payload = _project(_default_frame(25), expected_session=datetime(2024, 1, 31, 9, 30))
    assert payload["reason"] == "EXPECTED_SESSION_TYPE"


def test_naive_ingested_at_refuses():
    payload = _project(_default_frame(25), ingested_at="2024-01-31T20:30:00")
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INGESTED_AT_INVALID"


def test_future_ingested_at_refuses():
    payload = _project(_default_frame(25), ingested_at="2024-02-01T15:30:00Z")
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INGESTED_AT_AFTER_RECORDED"


def test_ingested_at_before_latest_bar_refuses():
    payload = _project(_default_frame(25), ingested_at="2024-01-30T20:00:00-05:00")
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "INGESTED_AT_BEFORE_LATEST_BAR"


def test_ingested_at_none_is_allowed():
    payload = _project(_default_frame(25), ingested_at=None)
    assert payload["status"] == STATUS_OK
    assert payload["ingested_at"] is None


def test_missing_source_sha_refuses():
    payload = _project(_default_frame(25), source_sha256=None)
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "SOURCE_SHA256_REQUIRED"


def test_invalid_source_sha_refuses():
    payload = _project(_default_frame(25), source_sha256="deadbeef")
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["reason"] == "SOURCE_SHA256_INVALID"
    assert payload["source_sha256"] is None


# Parent integration: source evidence must bind this ticker and exact metadata.
def test_currency_receipt_for_another_ticker_does_not_qualify():
    evidence = _currency_evidence(ticker="OTHER")
    payload = _project(_default_frame(25), currency_evidence=evidence)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["metrics"] is None and payload["thinly_traded"] is None


def test_source_digest_with_trailing_newline_is_not_a_sha256():
    payload = _project(_default_frame(25), source_sha256=SOURCE_SHA256 + "\n")
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["metrics"] is None


def test_non_padded_currency_dates_are_not_strict_iso_dates():
    evidence = _currency_evidence(valid_from="2024-1-1")
    payload = _project(_default_frame(25), currency_evidence=evidence)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["metrics"] is None


def test_market_session_not_yet_completed_cannot_qualify():
    evidence = _currency_evidence(source_asof="2024-01-30")
    payload = _project(_default_frame(25), recorded_at=datetime(2024, 1, 31, 15, tzinfo=timezone.utc),
                       ingested_at=None, currency_evidence=evidence)
    assert payload["status"] == STATUS_UNAVAILABLE
    assert payload["metrics"] is None


def test_currency_receipt_without_ticker_binding_does_not_qualify():
    evidence = _currency_evidence()
    del evidence["ticker"]
    payload = _project(_default_frame(25), currency_evidence=evidence)
    assert payload["status"] == STATUS_NO_COVERAGE
    assert payload["metrics"] is None and payload["sample_n"] is None
