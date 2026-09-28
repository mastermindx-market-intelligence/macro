from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from engine import china_heatmap_live as live
from engine.china_heatmap_live import (
    build_live_payload,
    LiveContractError,
    normalize_tencent_quotes,
    normalize_tushare_rows,
    parse_market_time,
    validate_baseline,
    validate_live_payload,
)


BASELINE = {
    "market": "china",
    "map_type": "stocks",
    "source": "daily-close",
    "asof": "2026-09-24",
    "n_tiles": 2,
    "tiles": [
        {"t": "600519.SS", "sector": "Consumer Defensive", "size": 100.0, "perf": {"1D": 1.0}, "px": 1398.0},
        {"t": "000001.SZ", "sector": "Financial Services", "size": 50.0, "perf": {"1D": -1.0}, "px": 11.2},
    ],
}


def _frame(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_validate_baseline_freezes_order_and_identity() -> None:
    baseline = validate_baseline(BASELINE)
    assert baseline.asof == "2026-09-24"
    assert baseline.tickers == ("600519.SS", "000001.SZ")


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(market="hk"), "identity"),
        (lambda p: p.update(source="tushare-rt-k"), "identity"),
        (lambda p: p.update(asof="2026-02-30"), "date"),
        (lambda p: p.update(n_tiles=3), "count"),
        (lambda p: p["tiles"].append(dict(p["tiles"][0])), "count"),
        (lambda p: p["tiles"][1].update(t="600519.SS"), "duplicate"),
        (lambda p: p["tiles"][1].update(t="430047.BJ"), "mainland"),
    ],
)
def test_validate_baseline_rejects_incoherent_payloads(mutate, message: str) -> None:
    import copy

    payload = copy.deepcopy(BASELINE)
    mutate(payload)
    with pytest.raises(LiveContractError, match=message):
        validate_baseline(payload)


def test_parse_market_time_uses_china_wall_clock() -> None:
    expected = datetime(2026, 9, 28, 2, 15, 30, tzinfo=timezone.utc)
    assert parse_market_time("2026-09-28 10:15:30") == expected
    assert parse_market_time("20260928101530") == expected
    assert parse_market_time(expected) == expected
    assert parse_market_time("not-a-clock") is None


def test_tushare_rows_normalize_suffix_filter_universe_and_recompute_change() -> None:
    baseline = validate_baseline(BASELINE)
    frame = _frame(
        {
            "ts_code": "600519.SH",
            "pre_close": 1398.0,
            "close": 1412.8,
            "open": 1399.5,
            "high": 1418.0,
            "low": 1390.1,
            "vol": 3_214_000,
            "amount": 4_512_000_000,
            "trade_time": "2026-09-28 10:15:30",
        },
        {
            "ts_code": "000001.SZ",
            "pre_close": 11.2,
            "close": 11.2,
            "open": 11.1,
            "high": 11.3,
            "low": 11.0,
            "vol": 8_000_000,
            "amount": 90_000_000,
            "trade_time": "2026-09-28 10:15:29",
        },
        {
            "ts_code": "600000.SH",
            "pre_close": 10.0,
            "close": 10.1,
            "open": 10.0,
            "high": 10.2,
            "low": 9.9,
            "vol": 1,
            "amount": 10,
            "trade_time": "2026-09-28 10:15:30",
        },
    )

    quotes = normalize_tushare_rows(frame, baseline)
    assert tuple(quotes) == ("600519.SS", "000001.SZ")
    moutai = quotes["600519.SS"]
    assert moutai["price"] == 1412.8
    assert moutai["prevClose"] == 1398.0
    assert moutai["changePct"] == pytest.approx((1412.8 / 1398.0 - 1.0) * 100.0)
    assert moutai["ts"] == int(datetime(2026, 9, 28, 2, 15, 30, tzinfo=timezone.utc).timestamp() * 1000)
    assert moutai["vol"] == 3_214_000
    assert "600000.SS" not in quotes
    assert quotes["000001.SZ"]["changePct"] == 0.0


def test_tushare_rows_omit_malformed_and_no_trade_placeholders() -> None:
    baseline = validate_baseline(BASELINE)
    frame = _frame(
        {
            "ts_code": "600519.SH",
            "pre_close": 1398.0,
            "close": 1398.0,
            "open": 0,
            "high": 0,
            "low": 0,
            "vol": 0,
            "amount": 0,
            "trade_time": "2026-09-28 10:15:30",
        },
        {
            "ts_code": "000001.SZ",
            "pre_close": 11.2,
            "close": float("inf"),
            "open": 11.1,
            "high": 11.3,
            "low": 11.0,
            "vol": 8_000_000,
            "amount": 90_000_000,
            "trade_time": "not-a-clock",
        },
    )
    assert normalize_tushare_rows(frame, baseline) == {}


def test_tushare_duplicate_normalized_ticker_fails_closed() -> None:
    baseline = validate_baseline(BASELINE)
    frame = _frame(
        {
            "ts_code": "600519.SH",
            "pre_close": 1398.0,
            "close": 1400.0,
            "open": 1399.0,
            "high": 1401.0,
            "low": 1398.0,
            "vol": 10,
            "amount": 100,
            "trade_time": "2026-09-28 10:15:30",
        },
        {
            "ts_code": "600519.SS",
            "pre_close": 1398.0,
            "close": 1401.0,
            "open": 1399.0,
            "high": 1402.0,
            "low": 1398.0,
            "vol": 20,
            "amount": 200,
            "trade_time": "2026-09-28 10:15:31",
        },
    )
    with pytest.raises(LiveContractError, match="duplicate"):
        normalize_tushare_rows(frame, baseline)


def test_tencent_rows_normalize_existing_quote_contract() -> None:
    baseline = validate_baseline(BASELINE)
    raw = {
        "600519.SS": {
            "price": 1412.8,
            "prev_close": 1398.0,
            "quote_ts": "2026-09-28T02:15:30+00:00",
            "day_volume": 3_214_000,
            "day_high": 1418.0,
            "day_low": 1390.1,
        },
        "600000.SS": {
            "price": 10.1,
            "prev_close": 10.0,
            "quote_ts": "2026-09-28T02:15:30+00:00",
        },
    }
    quotes = normalize_tencent_quotes(raw, baseline)
    assert tuple(quotes) == ("600519.SS",)
    assert quotes["600519.SS"]["changePct"] == pytest.approx((1412.8 / 1398.0 - 1) * 100)
    assert quotes["600519.SS"]["vol"] == 3_214_000


LIVE_NOW = datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc)
LIVE_EXPECTED = datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc)


def _live_quotes(ts: datetime | None = None) -> dict[str, dict]:
    observed = ts or datetime(2026, 9, 28, 2, 15, 30, tzinfo=timezone.utc)
    stamp = int(observed.timestamp() * 1000)
    return {
        "600519.SS": {
            "price": 1412.8, "prevClose": 1398.0,
            "changePct": (1412.8 / 1398.0 - 1.0) * 100.0,
            "ts": stamp, "open": 1399.5, "high": 1418.0,
            "low": 1390.1, "vol": 3_214_000, "amount": 4_512_000_000.0,
        },
        "000001.SZ": {
            "price": 11.1, "prevClose": 11.2,
            "changePct": (11.1 / 11.2 - 1.0) * 100.0,
            "ts": stamp - 1000, "open": 11.2, "high": 11.25,
            "low": 11.0, "vol": 8_000_000, "amount": 90_000_000.0,
        },
    }


def _clock(monkeypatch, expected: datetime = LIVE_EXPECTED) -> None:
    monkeypatch.setattr(live.cn_clock, "session_date", lambda now=None: date(2026, 9, 28))
    monkeypatch.setattr(live.cn_clock, "last_completed_session", lambda now=None: "2026-09-24")
    monkeypatch.setattr(live.cn_clock, "expected_latest_quote_time", lambda now=None: expected)


@pytest.mark.parametrize(
    ("phase", "status", "now", "expected", "observed"),
    [
        ("morning", "live", datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc), datetime(2026, 9, 28, 2, 15, 40, tzinfo=timezone.utc), datetime(2026, 9, 28, 2, 15, 30, tzinfo=timezone.utc)),
        ("session_break", "break", datetime(2026, 9, 28, 4, 0, tzinfo=timezone.utc), datetime(2026, 9, 28, 3, 30, tzinfo=timezone.utc), datetime(2026, 9, 28, 3, 29, 50, tzinfo=timezone.utc)),
        ("afternoon", "live", datetime(2026, 9, 28, 5, 15, 40, tzinfo=timezone.utc), datetime(2026, 9, 28, 5, 15, 40, tzinfo=timezone.utc), datetime(2026, 9, 28, 5, 15, 30, tzinfo=timezone.utc)),
        ("closing_auction", "auction", datetime(2026, 9, 28, 6, 58, 20, tzinfo=timezone.utc), datetime(2026, 9, 28, 6, 58, 20, tzinfo=timezone.utc), datetime(2026, 9, 28, 6, 58, 10, tzinfo=timezone.utc)),
        ("post_close", "closed", datetime(2026, 9, 28, 7, 5, tzinfo=timezone.utc), datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc), datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc)),
        ("closed", "closed", datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc), datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc), datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc)),
    ],
)
def test_payload_is_phase_aware_and_coherent(monkeypatch, phase: str, status: str, now: datetime, expected: datetime, observed: datetime) -> None:
    _clock(monkeypatch, expected)
    baseline = validate_baseline(BASELINE)
    payload = build_live_payload(
        baseline, _live_quotes(observed), source="tushare-rt-k",
        fallback=False, phase=phase, now=now,
    )
    assert payload["schema"] == "china_heatmap_live.v1"
    assert payload["status"] == status
    assert payload["requested"] == payload["resolved"] == 2
    assert payload["coverage"] == 1.0
    assert payload["usable"] is True
    assert payload["breadth"] == {
        "n": 2, "adv": 1, "dec": 1, "flat": 0, "pctUp": 50.0,
    }
    assert validate_live_payload(payload, baseline, now=now) == payload


@pytest.mark.parametrize("phase", ["pre_open", "holiday", "weekend"])
def test_nontrading_phases_cannot_claim_usable(monkeypatch, phase: str) -> None:
    _clock(monkeypatch)
    baseline = validate_baseline(BASELINE)
    payload = build_live_payload(
        baseline, _live_quotes(), source="tushare-rt-k",
        fallback=False, phase=phase, now=LIVE_NOW,
    )
    assert payload["status"] == phase
    assert payload["usable"] is False
    assert validate_live_payload(payload, baseline, now=LIVE_NOW) == payload


def test_low_coverage_and_future_source_are_valid_but_unusable(monkeypatch) -> None:
    _clock(monkeypatch)
    baseline = validate_baseline(BASELINE)
    one = {"600519.SS": _live_quotes()["600519.SS"]}
    low = build_live_payload(
        baseline, one, source="tushare-rt-k",
        fallback=False, phase="morning", now=LIVE_NOW,
    )
    assert low["coverage"] == 0.5 and low["usable"] is False

    future = _live_quotes(LIVE_EXPECTED.replace(second=50))
    ahead = build_live_payload(
        baseline, future, source="tushare-rt-k",
        fallback=False, phase="morning", now=LIVE_NOW,
    )
    assert ahead["usable"] is False


def test_heartbeat_never_relabels_the_source_clock(monkeypatch) -> None:
    _clock(monkeypatch)
    baseline = validate_baseline(BASELINE)
    first = build_live_payload(
        baseline, _live_quotes(), source="tushare-rt-k",
        fallback=False, phase="morning", now=LIVE_NOW,
    )
    later = LIVE_NOW.replace(minute=16)
    _clock(monkeypatch, LIVE_EXPECTED)
    heartbeat = build_live_payload(
        baseline, _live_quotes(), source="tushare-rt-k",
        fallback=False, phase="session_break", now=later,
    )
    assert heartbeat["generated_at"] != first["generated_at"]
    assert heartbeat["source_observed_at"] == first["source_observed_at"]


def test_wrong_baseline_is_rejected_before_publication(monkeypatch) -> None:
    baseline = validate_baseline(BASELINE)
    _clock(monkeypatch)
    monkeypatch.setattr(live.cn_clock, "last_completed_session", lambda now=None: "2026-09-23")
    with pytest.raises(LiveContractError, match="completed-session baseline"):
        build_live_payload(
            baseline, _live_quotes(), source="tushare-rt-k",
            fallback=False, phase="morning", now=LIVE_NOW,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(requested=3),
        lambda p: p.update(resolved=1),
        lambda p: p.update(coverage=0.5),
        lambda p: p.update(baseline_asof="2026-09-23"),
        lambda p: p.update(session_date="2026-09-29"),
        lambda p: p.update(source="yahoo"),
        lambda p: p.update(fallback=True),
        lambda p: p.update(status="closed"),
        lambda p: p.update(usable=False),
        lambda p: p["breadth"].update(adv=2),
        lambda p: p["quotes"]["600519.SS"].update(changePct=99.0),
        lambda p: p["quotes"].update({"600000.SS": dict(p["quotes"]["600519.SS"])}),
        lambda p: p.update(private_vendor_body={"secret": True}),
    ],
)
def test_validation_rejects_incoherent_or_leaky_payloads(monkeypatch, mutate) -> None:
    import copy

    _clock(monkeypatch)
    baseline = validate_baseline(BASELINE)
    payload = build_live_payload(
        baseline, _live_quotes(), source="tushare-rt-k",
        fallback=False, phase="morning", now=LIVE_NOW,
    )
    broken = copy.deepcopy(payload)
    mutate(broken)
    with pytest.raises(LiveContractError):
        validate_live_payload(broken, baseline, now=LIVE_NOW)
