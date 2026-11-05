"""Controlled exact-contract snapshot bytes, never provider-access evidence."""
from copy import deepcopy
import hashlib
import json
import pytest

from engine.options_plan_quote_context import normalize_massive_plan_quote, QuoteContextError

CONTRACT = dict(root="SPY", expiration="2026-10-30", right="call", strike="100",
                strike_millis=100000, occ_symbol="SPY   261030C00100000")
PATH = "/v3/snapshot/options/SPY/O:SPY261030C00100000"


def snapshot():
    return dict(status="OK", results=dict(details=dict(ticker="O:SPY261030C00100000",
        contract_type="call", expiration_date="2026-10-30", strike_price=100),
        underlying_asset=dict(ticker="SPY"), last_quote=dict(bid=3.01, ask=3.11,
        bid_size=2, ask_size=3, bid_exchange=301, ask_exchange=302,
        last_updated=1792785600123456789, timeframe="REAL-TIME")))


def decode(payload=None, raw=None, **kw):
    return normalize_massive_plan_quote(raw if raw is not None else json.dumps(
        snapshot() if payload is None else payload).encode(), contract=CONTRACT,
        origin=kw.get("origin", "https://api.massive.com"), path=kw.get("path", PATH),
        observed_at=kw.get("observed_at", "2026-10-23T20:00:01Z"), http_status=kw.get("http_status", 200))


def test_exact_bytes_prices_sizes_clock_and_no_current_admission():
    data = snapshot(); before = deepcopy(data); raw = json.dumps(data).encode()
    out = decode(raw=raw)
    assert out["bid"] == "3.01" and out["ask"] == "3.11"
    assert out["raw_last_updated"] == 1792785600123456789
    assert out["event_time_utc"] is None and "UNVERIFIED" in out["clock_kind"]
    assert out["source"]["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert out["source"]["observed_at"] == "2026-10-23T20:00:01Z"
    assert out["recency"] == "VENDOR_REALTIME_DECLARED"
    assert out["current_quote_eligible"] is False
    assert out["bid_size"] == 2 and out["ask_exchange"] == 302
    assert data == before


def test_no_quote_never_uses_trade_day_fmv_or_midpoint():
    data = snapshot(); del data["results"]["last_quote"]
    data["results"].update(last_trade=dict(price=99), day=dict(close=88), fmv=77, midpoint=66)
    out = decode(data)
    assert out["bid"] is None and out["ask"] is None
    assert out["quality"] == ["NO_QUOTE", "ACCESS_UNVERIFIED"]


def test_delayed_remains_delayed_after_new_observation():
    data = snapshot(); data["results"]["last_quote"]["timeframe"] = "DELAYED"
    assert decode(data)["recency"] == "DELAYED"
    assert decode(data)["current_quote_eligible"] is False


@pytest.mark.parametrize("change,quality", [
    ({"bid": None}, "ONE_SIDED"), ({"bid": 3.11}, "LOCKED"),
    ({"bid": 4}, "CROSSED"), ({"bid": 0}, "ZERO_PRICE"),
    ({"bid_size": 0}, "ZERO_SIZE"), ({"ask_size": None}, "SIZE_UNKNOWN"),
    ({"ask_size": True}, "SIZE_UNKNOWN"), ({"bid": -1}, "ONE_SIDED"),
])
def test_quality_is_explicit_without_rewriting_values(change, quality):
    data = snapshot(); data["results"]["last_quote"].update(change)
    out = decode(data)
    assert quality in out["quality"] and out["current_quote_eligible"] is False


@pytest.mark.parametrize("change", [
    {"ticker": "O:SPY261030C00101000"}, {"contract_type": "put"},
    {"expiration_date": "2026-11-06"}, {"strike_price": 101},
])
def test_foreign_exact_identity_refused(change):
    data = snapshot(); data["results"]["details"].update(change)
    with pytest.raises(QuoteContextError, match="contract mismatch"):
        decode(data)


@pytest.mark.parametrize("kw", [
    dict(origin="https://api.massive.com.evil.invalid"), dict(path=PATH + "?key=not-permitted"),
    dict(http_status=403), dict(observed_at="2026-10-23T20:00:01"),
])
def test_transport_and_observation_evidence_must_be_explicit(kw):
    with pytest.raises(QuoteContextError):
        decode(**kw)


@pytest.mark.parametrize("raw", [b'{"status":"OK","status":"OK"}', b'NaN', b'\xff', b' ' * (1024*1024+1)])
def test_ambiguous_invalid_oversize_input_refused(raw):
    with pytest.raises(QuoteContextError):
        decode(raw=raw)


def test_unverified_last_updated_and_vendor_timeframe_are_not_inferred():
    data = snapshot(); data["results"]["last_quote"].update(last_updated=None, timeframe="FUTURE_VENDOR_TOKEN")
    out = decode(data)
    assert out["raw_last_updated"] is None and out["recency"] == "UNKNOWN"
    assert out["vendor_timeframe"] == "FUTURE_VENDOR_TOKEN"


def test_underlying_mismatch_refused():
    data = snapshot(); data["results"]["underlying_asset"]["ticker"] = "QQQ"
    with pytest.raises(QuoteContextError, match="underlying mismatch"):
        decode(data)


def test_bounded_decimal_and_condition_codes_do_not_claim_firmness():
    raw = json.dumps(snapshot()).encode().replace(b'3.01', b'1e-99999999')
    out = decode(raw=raw)
    assert out["bid"] is None and "ONE_SIDED" in out["quality"]
    data = snapshot(); data["results"]["last_quote"]["conditions"] = [0, 12]
    out = decode(data)
    assert out["raw_conditions"] == [0, 12] and out["conditions_status"] == "UNKNOWN"


def test_old_clock_is_not_freshened_by_receive_clock():
    data = snapshot(); data["results"]["last_quote"]["last_updated"] = 1636573458756383500
    out = decode(data)
    assert out["raw_last_updated"] == 1636573458756383500
    assert out["source"]["observed_at"] == "2026-10-23T20:00:01Z"
    assert out["event_time_utc"] is None and not out["current_quote_eligible"]
