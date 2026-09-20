"""Tests for W1 — the 20-session sector participation calendar (additive to
collectors.breadth, does not touch the existing 50/200 breadth pipeline).

Two independent surfaces:

1. ``BreadthAdapter.licensed_daily_window`` — one bounded licensed-vendor daily
   request per ticker, ``adjusted=true``. Tested here with fake HTTP responses only
   (research/skylit/W1_SOURCE_IMPLEMENTATION_RULING_2026-09-11.md §3: "fake responses
   are sufficient for coding and adversarial failure tests, not real-data release").
   No network call is made by this suite.
2. ``BreadthAdapter.compute_sector_participation_20`` — a pure function of an
   already-fetched wide closes frame + the constituents table. Covers the
   mission's numerical acceptance cases (research/skylit/
   US_SECTOR_PARTICIPATION_W1_2026-09-10.md §5, A01/A02/A03/A04/A06/A07/A08/A09/A10).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from collectors import breadth as bmod
from lib import nyse_calendar
from lib import sector_participation as w1_contract


def _adapter() -> bmod.BreadthAdapter:
    return bmod.BreadthAdapter()


def _sessions(n: int, end_year=2024, end_month=3, end_day=15):
    """n real, consecutive NYSE session dates ending on/before the given date —
    avoids hand-picked dates silently drifting onto a holiday."""
    end = pd.Timestamp(end_year, end_month, end_day).date()
    # walk back far enough to always find n sessions even across a holiday cluster
    start = end - pd.Timedelta(days=int(n * 1.6) + 10)
    all_sessions = nyse_calendar.sessions_between(start, end)
    return all_sessions[-n:]


# --------------------------------------------------------------------------- #
# licensed_daily_window — fake HTTP only, no network
# --------------------------------------------------------------------------- #

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _ts_ms(d) -> int:
    """Vendor daily aggregate start: midnight US/Eastern, encoded as UTC ms."""
    return int(
        pd.Timestamp(d)
        .tz_localize("America/New_York")
        .tz_convert("UTC")
        .timestamp() * 1000
    )


def _agg_row(ts_ms: int, close: float) -> dict:
    return {"t": ts_ms, "o": close, "h": close, "l": close, "c": close, "v": 1000}


def _payload(ticker: str, results: list, **overrides) -> dict:
    """A realistic /v2/aggs envelope (status/ticker/adjusted/next_url), not just a
    bare results list — R3 requires qualifying the whole response, so the fakes
    have to look like one."""
    base = {"status": "OK", "ticker": ticker, "adjusted": True, "queryCount": len(results),
            "resultsCount": len(results), "results": results}
    base.update(overrides)
    return base


def test_licensed_daily_window_returns_split_adjusted_series(monkeypatch):
    days = _sessions(3)
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0 + i) for i, d in enumerate(days)])
    monkeypatch.setattr(bmod.config, "secret",
                        lambda name: "fake-key" if name == "POLYGON_API_KEY" else None)
    captured = {}

    def fake_http_get(self, url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["params"] = kwargs.get("params")
        return _FakeResponse(payload)

    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", fake_http_get)
    a = _adapter()
    s = a.licensed_daily_window("AAPL", days[0], days[-1])
    assert len(s) == 3
    assert list(s.values) == [100.0, 101.0, 102.0]
    assert s.attrs["basis"] == "split_adjusted"
    assert s.attrs["adjusted"] is True
    # W1's documented security law: key rides the header, never the query string
    assert "apiKey" not in (captured["params"] or {})
    assert captured["headers"]["Authorization"] == "Bearer fake-key"
    assert "adjusted" in captured["params"] and captured["params"]["adjusted"] == "true"


def test_licensed_daily_window_preserves_missing_expected_session_hole(monkeypatch):
    """A complete response can legitimately omit one historical observation.

    That is a member-level data hole, not transport truncation.  The sparse series
    remains usable outside every 20-session window that crosses the hole, and the
    missing expected session is carried as typed source evidence for the package.
    """
    days = _sessions(5)
    skip = days[2]
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days if d != skip])
    monkeypatch.setattr(bmod.config, "secret",
                        lambda name: "fake-key" if name == "POLYGON_API_KEY" else None)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get",
                        lambda self, url, **kw: _FakeResponse(payload))
    s = _adapter().licensed_daily_window("AAPL", days[0], days[-1])
    assert list(s.index.date) == [d for d in days if d != skip]
    assert s.attrs["missing_sessions"] == [skip.isoformat()]
    assert s.attrs["invalid_sessions"] == []


def test_licensed_daily_window_raises_without_key(monkeypatch):
    monkeypatch.setattr(bmod.config, "secret", lambda name: None)
    a = _adapter()
    with pytest.raises(bmod.LicensedSourceError, match="no licensed vendor key"):
        a.licensed_daily_window("AAPL", _sessions(2)[0], _sessions(2)[-1])


def test_licensed_daily_window_never_uses_apikey_query_param(monkeypatch):
    """Regression pin for the documented security law (scripts/massive_entitlement_probe.py):
    the key must never appear as a query parameter, only the Authorization header."""
    days = _sessions(2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days])
    adapter = _adapter()
    monkeypatch.setattr(bmod.config, "secret",
                        lambda name: "super-secret-key" if name == "POLYGON_API_KEY" else None)
    seen = {}

    def fake_http_get(self, url, **kwargs):
        seen["params"] = kwargs.get("params") or {}
        seen["url"] = url
        return _FakeResponse(payload)

    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", fake_http_get)
    adapter.licensed_daily_window("AAPL", days[0], days[-1])
    assert "super-secret-key" not in seen["url"]
    assert "apiKey" not in seen["params"]
    assert "super-secret-key" not in str(seen["params"])


def test_licensed_daily_window_passes_bounded_http_controls(monkeypatch):
    days = _sessions(2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(day), 100.0) for day in days])
    adapter = _adapter()
    monkeypatch.setattr(bmod.config, "secret", lambda name: "fake-key")
    monkeypatch.setattr(
        bmod.config, "load",
        lambda: {"polygon": {
            "w1_request_timeout_seconds": 7,
            "w1_request_retries": 2,
            "w1_request_backoff_seconds": 0.25,
        }},
    )
    seen = {}

    def fake_http_get(self, url, **kwargs):
        seen.update(kwargs)
        return _FakeResponse(payload)

    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", fake_http_get)
    adapter.licensed_daily_window("AAPL", days[0], days[-1])
    assert seen["timeout"] == 7
    assert seen["retries"] == 2
    assert seen["backoff_base"] == 0.25


def test_licensed_daily_window_inherits_tighter_existing_polygon_controls(monkeypatch):
    days = _sessions(2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(day), 100.0) for day in days])
    adapter = _adapter()
    monkeypatch.setattr(bmod.config, "secret", lambda name: "fake-key")
    monkeypatch.setattr(
        bmod.config, "load",
        lambda: {"polygon": {"request_timeout": 9, "retries": 1}},
    )
    seen = {}

    def fake_http_get(self, url, **kwargs):
        seen.update(kwargs)
        return _FakeResponse(payload)

    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", fake_http_get)
    adapter.licensed_daily_window("AAPL", days[0], days[-1])
    assert seen["timeout"] == 9
    assert seen["retries"] == 1


def test_licensed_daily_window_marks_http_auth_and_systemic_failures_fatal(monkeypatch):
    import requests

    days = _sessions(2)
    monkeypatch.setattr(bmod.config, "secret", lambda name: "fake-key")

    response = type("Response", (), {"status_code": 401})()
    auth_error = requests.HTTPError("HTTP 401", response=response)
    monkeypatch.setattr(
        bmod.BreadthAdapter, "http_get",
        lambda *args, **kwargs: (_ for _ in ()).throw(auth_error),
    )
    with pytest.raises(bmod.LicensedSourceError) as caught:
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])
    assert caught.value.fatal is True

    monkeypatch.setattr(
        bmod.BreadthAdapter, "http_get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("host timed out")),
    )
    with pytest.raises(bmod.LicensedSourceError) as caught:
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])
    assert caught.value.fatal is True


def test_licensed_daily_window_marks_body_entitlement_refusal_fatal(monkeypatch):
    days = _sessions(2)
    payload = _payload("AAPL", [], status="ERROR", error="NOT_AUTHORIZED for this plan")
    monkeypatch.setattr(bmod.config, "secret", lambda name: "fake-key")
    monkeypatch.setattr(
        bmod.BreadthAdapter, "http_get", lambda *args, **kwargs: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError) as caught:
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])
    assert caught.value.fatal is True


def test_licensed_daily_window_refuses_in_range_non_session_row(monkeypatch):
    from datetime import date

    start, end = date(2024, 3, 1), date(2024, 3, 4)  # Fri through Mon
    saturday = date(2024, 3, 2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(saturday), 100.0)])
    monkeypatch.setattr(bmod.config, "secret", lambda name: "fake-key")
    monkeypatch.setattr(
        bmod.BreadthAdapter, "http_get", lambda *args, **kwargs: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="non-session"):
        _adapter().licensed_daily_window("AAPL", start, end)


def test_licensed_daily_window_refuses_in_range_non_midnight_eastern_timestamp(monkeypatch):
    days = _sessions(2)
    one_am_et = (pd.Timestamp(days[0])
                 .tz_localize("America/New_York")
                 + pd.Timedelta(hours=1))
    one_am_ms = int(one_am_et.tz_convert("UTC").timestamp() * 1000)
    rows = [_agg_row(one_am_ms, 100.0), _agg_row(_ts_ms(days[1]), 101.0)]
    payload = _payload("AAPL", rows)
    monkeypatch.setattr(bmod.config, "secret", lambda name: "fake-key")
    monkeypatch.setattr(
        bmod.BreadthAdapter, "http_get", lambda *args, **kwargs: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="midnight US/Eastern"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


# --------------------------------------------------------------------------- #
# R3 (Sol 1789096018.269229): qualify the RETURNED envelope, not just the request.
# --------------------------------------------------------------------------- #

def _fake_key(monkeypatch, key="fake-key"):
    monkeypatch.setattr(bmod.config, "secret",
                        lambda name: key if name == "POLYGON_API_KEY" else None)


def test_licensed_daily_window_rejects_non_ok_status_R3(monkeypatch):
    days = _sessions(2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days], status="ERROR")
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="status"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_rejects_ticker_identity_mismatch_R3(monkeypatch):
    days = _sessions(2)
    payload = _payload("MSFT", [_agg_row(_ts_ms(d), 100.0) for d in days])  # wrong ticker echoed
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="identity mismatch"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_rejects_explicit_adjusted_false_R3(monkeypatch):
    days = _sessions(2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days], adjusted=False)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="adjusted=false"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_refuses_truncated_next_url_R3(monkeypatch):
    """No pagination/retry authority: a next_url means the vendor truncated our
    bounded request, which we must refuse rather than silently accept partial data."""
    days = _sessions(2)
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days],
                       next_url="https://api.polygon.io/v2/aggs/.../next")
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="truncated"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_requires_mapping_body_R3(monkeypatch):
    days = _sessions(2)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get",
                        lambda self, url, **kw: _FakeResponse(["not", "an", "object"]))
    with pytest.raises(bmod.LicensedSourceError, match="mapping"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_requires_explicit_adjusted_true_R3(monkeypatch):
    days = _sessions(2)
    rows = [_agg_row(_ts_ms(d), 100.0) for d in days]
    payload = _payload("AAPL", rows)
    payload.pop("adjusted")
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="adjusted=true"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_rejects_declared_count_mismatch_R3(monkeypatch):
    days = _sessions(2)
    rows = [_agg_row(_ts_ms(d), 100.0) for d in days]
    payload = _payload("AAPL", rows, resultsCount=999)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="resultsCount"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_requires_case_exact_identity_R3(monkeypatch):
    days = _sessions(2)
    payload = _payload("aapl", [_agg_row(_ts_ms(d), 100.0) for d in days])
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="identity mismatch"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_accepts_only_class_share_separator_normalization_R3(monkeypatch):
    days = _sessions(2)
    payload = _payload("BRK.B", [_agg_row(_ts_ms(d), 100.0) for d in days])
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    s = _adapter().licensed_daily_window("BRK-B", days[0], days[-1])
    assert len(s) == 2
    assert s.attrs["requested_ticker"] == "BRK-B"
    assert s.attrs["response_ticker"] == "BRK.B"


def test_licensed_daily_window_rejects_duplicate_session_R3(monkeypatch):
    days = _sessions(3)
    rows = [_agg_row(_ts_ms(d), 100.0) for d in days]
    rows.append(_agg_row(_ts_ms(days[1]), 999.0))  # a second, conflicting row for the same day
    payload = _payload("AAPL", rows)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    with pytest.raises(bmod.LicensedSourceError, match="duplicate"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_drops_out_of_window_rows_R3(monkeypatch):
    days = _sessions(5)
    in_window = days[-3:]
    stray = days[0]  # outside the requested [start, end]
    stray_one_am = (pd.Timestamp(stray).tz_localize("America/New_York")
                    + pd.Timedelta(hours=1))
    stray_ms = int(stray_one_am.tz_convert("UTC").timestamp() * 1000)
    rows = [_agg_row(stray_ms, 1.0)] + [_agg_row(_ts_ms(d), 100.0) for d in in_window]
    payload = _payload("AAPL", rows)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    s = _adapter().licensed_daily_window("AAPL", in_window[0], in_window[-1])
    assert len(s) == 3
    assert stray not in [d.date() for d in s.index]


def test_licensed_daily_window_types_invalid_close_separately_from_missing_R3(monkeypatch):
    days = _sessions(2)
    rows = [_agg_row(_ts_ms(days[0]), True), _agg_row(_ts_ms(days[1]), 100.0)]
    payload = _payload("AAPL", rows)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    s = _adapter().licensed_daily_window("AAPL", days[0], days[-1])
    assert list(s.index.date) == [days[1]]
    assert s.attrs["invalid_sessions"] == [days[0].isoformat()]
    assert s.attrs["missing_sessions"] == []


# --------------------------------------------------------------------------- #
# compute_sector_participation_20 — pure, no network
# --------------------------------------------------------------------------- #

def _members(symbols, sector="Technology"):
    return pd.DataFrame({"symbol": symbols, "sector": [sector] * len(symbols)})


def _wide(symbols, sessions, value_fn):
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in sessions])
    return pd.DataFrame({t: [value_fn(t, i) for i in range(len(sessions))] for t in symbols}, index=idx)


def test_constant_window_is_not_above_a01():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(5)]
    closes = _wide(syms, days, lambda t, i: 100.0)  # every name flat at exactly 100.0 all 20 sessions
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    assert out is not None
    last = out.iloc[-1]
    assert last["Technology|eligible_20"] == 5
    assert last["Technology|above_20"] == 0          # constant window must never read "above"
    assert last["Technology|pct_above_20"] == 0.0    # valid 0%, not withheld


def test_five_rising_five_falling_is_50pct_a02():
    days = _sessions(20)
    syms = [f"U{i}" for i in range(5)] + [f"D{i}" for i in range(5)]

    def val(t, i):
        base = 100.0
        return base + i if t.startswith("U") else base - i  # rising vs falling trend -> above/below own MA20
    closes = _wide(syms, days, val)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    assert last["Technology|eligible_20"] == 10
    assert last["Technology|above_20"] == 5
    assert last["Technology|pct_above_20"] == 50.0


def test_19_observations_excluded_a03():
    days = _sessions(19)
    syms = [f"T{i}" for i in range(5)]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    # never an abbreviated 19-session MA: eligible stays 0 and percentage stays
    # withheld on every row — 19 observations can never satisfy a 20-window
    assert out is None or (out["Technology|eligible_20"] == 0).all()
    if out is not None:
        assert out["Technology|pct_above_20"].isna().all()


def test_missing_interior_session_excludes_without_compression_a04():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(5)]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    # drop one interior real trading session's row entirely (not NaN-fill — an
    # honestly *missing* row, the case a naive dropna().tail(20) would silently
    # compress away by pulling in an extra earlier session instead)
    closes = closes.drop(index=closes.index[10])
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    # reindexing to the full calendar makes the dropped session reappear as NaN,
    # so no 20-consecutive-session window is satisfied anywhere in this short frame
    assert out is None or out["Technology|eligible_20"].fillna(0).eq(0).all()


def test_boolean_and_nonpositive_values_invalid_a06():
    days = _sessions(20)
    syms = ["BOOL", "ZERO", "NEG", "OK1", "OK2"]

    def val(t, i):
        if t == "BOOL":
            return True
        if t == "ZERO":
            return 0.0
        if t == "NEG":
            return -5.0
        return 100.0 + i
    closes = _wide(syms, days, val)
    closes["BOOL"] = closes["BOOL"].astype(bool)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    # only OK1/OK2 are eligible; BOOL/ZERO/NEG never count toward eligible or above
    assert last["Technology|eligible_20"] == 2


def test_all_below_is_genuine_zero_percent_a07():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(5)]
    # every name strictly falling -> price < its own rising-history MA20 on the last day
    closes = _wide(syms, days, lambda t, i: 200.0 - i)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    assert last["Technology|eligible_20"] == 5
    assert last["Technology|above_20"] == 0
    assert last["Technology|pct_above_20"] == 0.0  # present and zero, not withheld


def test_zero_eligible_denominator_is_unavailable_a08():
    """Before any name has 20 sessions of history, eligible_count is a genuine 0 —
    disclosed as such (no crash, no fabricated percentage), distinct from a true
    0% (A07, where eligible_count > 0 but above_count is 0)."""
    days = _sessions(20)
    syms = [f"T{i}" for i in range(5)]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    first = out.iloc[0]  # only 1 of 20 required sessions observed so far
    assert first["Technology|eligible_20"] == 0
    assert first["Technology|above_20"] == 0
    assert first["Technology|expected_20"] == 5
    assert np.isnan(first["Technology|pct_above_20"])   # unavailable, not 0/0 or a sentinel


def test_90_percent_and_5_name_floor_boundary_a09_a10():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(10)]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    # 9 of 10 eligible (drop one name's history so it can never qualify)
    closes.iloc[:, 9] = np.nan
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    assert last["Technology|eligible_20"] == 9
    assert last["Technology|expected_20"] == 10
    assert not np.isnan(last["Technology|pct_above_20"])  # 9/10 = 90% clears the floor

    # 8 of 10 eligible must fail the 90% floor: percentage withheld, counts kept
    closes2 = _wide(syms, days, lambda t, i: 100.0 + i)
    closes2.iloc[:, 8] = np.nan
    closes2.iloc[:, 9] = np.nan
    out2 = _adapter().compute_sector_participation_20(closes2, members)
    last2 = out2.iloc[-1]
    assert last2["Technology|eligible_20"] == 8
    assert np.isnan(last2["Technology|pct_above_20"])   # withheld, not a fabricated number


def test_thin_sector_below_5_names_percentage_withheld_a10():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(3)]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    assert out is not None
    last = out.iloc[-1]
    assert last["Technology|eligible_20"] == 3
    assert np.isnan(last["Technology|pct_above_20"])   # below the 5-name floor


def test_single_name_sector_never_clears_floor_but_counts_are_honest():
    days = _sessions(20)
    syms = ["ONLY_ONE"]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    assert last["Technology|expected_20"] == 1
    assert last["Technology|eligible_20"] == 1        # the one name really is eligible...
    assert np.isnan(last["Technology|pct_above_20"])  # ...but the 5-name floor withholds %


def test_no_sector_overlap_returns_none():
    """None is reserved for the case where nothing in `members` maps onto `closes` at
    all (e.g. a missing/empty sector column) — not merely "every sector is thin"."""
    days = _sessions(20)
    closes = _wide(["ZZZ"], days, lambda t, i: 100.0 + i)
    empty_members = pd.DataFrame({"symbol": ["ZZZ"], "sector": [None]})
    out = _adapter().compute_sector_participation_20(closes, empty_members)
    assert out is None


# --------------------------------------------------------------------------- #
# R2 (Sol 1789096018.269229): a symbol wholly missing from `closes` must still
# count toward expected_20, and an isolated Boolean inside an object column
# must not be coerced to 1. Both are regressions on the FIRST source pass.
# --------------------------------------------------------------------------- #

def test_missing_whole_symbol_still_counts_toward_expected_R2():
    """The exact bug named in review: expected_n used to be len(tick) over columns
    PRESENT in `closes`, so a symbol absent from the price matrix entirely silently
    shrank the denominator — turning real 50% coverage into apparent 100%."""
    days = _sessions(20)
    present = [f"T{i}" for i in range(5)]
    closes = _wide(present, days, lambda t, i: 100.0 + i)  # all 5 present names ABOVE
    members = pd.DataFrame({"symbol": present + ["MISSING1", "MISSING2",
                                                 "MISSING3", "MISSING4", "MISSING5"],
                            "sector": ["Technology"] * 10})
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    assert last["Technology|expected_20"] == 10          # full roster, not just present-5
    assert last["Technology|eligible_20"] == 5            # only the present 5 can be eligible
    assert last["Technology|above_20"] == 5
    assert np.isnan(last["Technology|pct_above_20"])      # 5/10 = 50% < 90% floor: withheld
    # the pre-fix code would have read expected_20=5, eligible_20=5 -> a false 100%


def test_isolated_boolean_in_object_column_rejected_R2():
    """is_bool_dtype only ever catches a column whose DTYPE is bool. An object-dtype
    column mixing floats and one bare Python True/False slips through pd.to_numeric,
    which happily reads True as 1.0 and False as 0.0."""
    days = _sessions(20)
    syms = ["MIXED", "OK1", "OK2", "OK3", "OK4"]
    closes = _wide(syms, days, lambda t, i: 100.0 + i)
    closes["MIXED"] = closes["MIXED"].astype(object)
    closes.loc[closes.index[3], "MIXED"] = True   # one bare bool inside an object column
    members = _members(syms)
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    # MIXED's window includes the poisoned bool at position 3, so it can never
    # accumulate 20 valid observations by the last row -> ineligible, not "above"
    assert last["Technology|eligible_20"] == 4
    assert last["Technology|expected_20"] == 5


def test_conflicting_membership_is_invalid_until_identity_owner_resolves_R2():
    """A duplicate/conflicting roster is not silently repaired by W1.

    The complete validated reference roster is denominator authority.  Guessing or
    dropping one of two memberships would mint an unowned historical universe, so
    generation stops until the existing identity owner resolves it.
    """
    days = _sessions(20)
    tech = [f"T{i}" for i in range(5)]
    health = [f"H{i}" for i in range(5)]
    dupe = "DUPE"
    closes = _wide(tech + health + [dupe], days, lambda t, i: 100.0 + i)
    members = pd.DataFrame({
        "symbol": tech + health + [dupe, dupe],
        "sector": ["Technology"] * 5 + ["Health Care"] * 5 + ["Technology", "Health Care"],
    })
    with pytest.raises(ValueError, match="duplicate.*membership"):
        _adapter().compute_sector_participation_20(closes, members)


def test_member_states_preserve_holes_invalidity_and_recovery_same_generation():
    days = _sessions(45)
    syms = ["UP", "DOWN", "HOLE", "INVALID", "UNAVAILABLE"]
    closes = _wide(
        syms,
        days,
        lambda ticker, i: (100.0 + i) if ticker != "DOWN" else (200.0 - i),
    )
    hole_i, invalid_i = 20, 21
    closes.loc[closes.index[hole_i], "HOLE"] = np.nan
    closes.loc[closes.index[invalid_i], "INVALID"] = np.nan
    closes["UNAVAILABLE"] = np.nan
    closes.attrs["member_evidence"] = {
        "HOLE": {"missing_sessions": [days[hole_i].isoformat()]},
        "INVALID": {"invalid_sessions": [days[invalid_i].isoformat()]},
        "UNAVAILABLE": {"unavailable": True, "reason": "simulated refusal"},
    }

    out = _adapter().compute_sector_participation_20(closes, _members(syms))
    evidence = out.attrs["members"]
    assert out.attrs["sessions"] == [d.isoformat() for d in days]
    assert evidence["UP"]["states"][18:21] == ["H", "A", "A"]
    assert evidence["DOWN"]["states"][19] == "B"
    assert evidence["HOLE"]["states"][19] == "A"
    assert evidence["HOLE"]["states"][hole_i] == "M"
    assert evidence["HOLE"]["states"][39] == "M"
    assert evidence["HOLE"]["states"][40] == "A"  # hole rolled out of the exact 20-session window
    assert evidence["INVALID"]["states"][invalid_i] == "I"
    assert evidence["INVALID"]["states"][40] == "I"
    assert evidence["INVALID"]["states"][41] == "A"
    assert set(evidence["UNAVAILABLE"]["states"]) == {"U"}
    assert evidence["UP"]["distance_bps"][19] is not None
    assert evidence["HOLE"]["distance_bps"][hole_i] is None
    assert evidence["INVALID"]["distance_bps"][invalid_i] is None
    assert evidence["UNAVAILABLE"]["distance_bps"] == [None] * len(days)
    assert evidence["UP"]["href"] == "stock.html#UP"


def test_leading_history_shortfall_is_H_not_missing_M():
    days = _sessions(30)
    syms = [f"T{i}" for i in range(5)]
    closes = _wide(syms, days, lambda ticker, i: np.nan if i < 10 else 100.0 + i)
    out = _adapter().compute_sector_participation_20(closes, _members(syms))
    states = out.attrs["members"]["T0"]["states"]
    assert states[19] == "H"  # only ten observations since this member first appeared
    assert states[28] == "H"
    assert states[29] == "A"  # first complete 20-session history


# --------------------------------------------------------------------------- #
# Sibling isolation (Sol 1789095151.749809): BreadthAdapter is the parent of
# midcap/smallcap/Russell/China/HK/Canada breadth too. The new W1 methods must
# never be reachable from any sibling's own fetch() — inherited-but-unused is
# fine, INVOKED is not. Two independent checks: (1) a static scan that no
# sibling's fetch() references either new method name at all, so an accidental
# call cannot exist in checked-in code regardless of what gets exercised at
# runtime; (2) each sibling still constructs cleanly with the network hard-
# disabled and no W1 configuration present (MidCap400BreadthAdapter is the
# named case — its __init__ does not call BreadthAdapter.__init__).
# --------------------------------------------------------------------------- #

_SIBLING_MODULES = (
    ("collectors.canada_breadth", None),
    ("collectors.china_breadth", None),
    ("collectors.hk_breadth", None),
    ("collectors.midcap_breadth", "MidCap400BreadthAdapter"),
    ("collectors.russell_breadth", None),
    ("collectors.smallcap_breadth", None),
)

_W1_METHOD_NAMES = ("licensed_daily_window", "compute_sector_participation_20")


def _sibling_adapter_classes():
    import importlib
    classes = []
    for mod_name, hinted_cls in _SIBLING_MODULES:
        mod = importlib.import_module(mod_name)
        if hinted_cls:
            classes.append((mod_name, getattr(mod, hinted_cls)))
            continue
        found = [c for c in vars(mod).values()
                if isinstance(c, type) and issubclass(c, bmod.BreadthAdapter)
                and c is not bmod.BreadthAdapter]
        assert found, f"{mod_name}: no BreadthAdapter subclass found"
        classes.append((mod_name, found[0]))
    return classes


def test_only_exact_us_sp500_adapter_owns_w1_runtime_path():
    assert _adapter()._owns_sector_participation_20() is True
    for mod_name, cls in _sibling_adapter_classes():
        instance = object.__new__(cls)
        assert instance._owns_sector_participation_20() is False, (
            f"{mod_name}.{cls.__name__} inherited W1 runtime ownership — "
            "only the exact US S&P BreadthAdapter may request or publish W1")


def test_all_sibling_fetch_entrypoints_make_zero_w1_requests_or_writes(monkeypatch, tmp_path):
    """Execute every sibling's real fetch method, including inherited parent fetches.

    This is the runtime proof requested by the original Sol review: constructors and
    bytecode/name scans are insufficient because three siblings inherit the exact
    parent method where W1 is wired. Legacy acquisition is stubbed, but method dispatch,
    cache writes, coverage checks and the W1 ownership guard are real.
    """
    days = _sessions(260)
    members = _members([f"T{i}" for i in range(5)])
    closes = _wide(members["symbol"].tolist(), days, lambda ticker, i: 100.0 + i)
    monkeypatch.setattr(bmod, "disclose_stale_constituent_columns", lambda *args: None)

    for mod_name, cls in _sibling_adapter_classes():
        instance = object.__new__(cls)
        instance.cfg = {"lookback_days_live": 220, "min_coverage": 0.8}
        instance.ycfg = {"batch_size": 5, "retries": 1, "backoff_base_s": 0}
        instance.cache_path = tmp_path / cls.__name__ / "_closes_cache.parquet"
        instance.constituents = lambda roster=members: roster.copy()
        instance.constituents_checked = lambda roster: roster
        instance._download_closes = lambda tickers, period, frame=closes: frame.copy()
        instance.compute = lambda frame: pd.DataFrame(
            {"pct_above_50": [50.0], "pct_above_200": [40.0]},
            index=pd.DatetimeIndex([frame.index[-1]]),
        )
        instance.compute_sectors = lambda frame, roster: None
        calls = []
        instance.fetch_sector_participation_20 = (
            lambda *args, _calls=calls, **kwargs: _calls.append("request"))
        instance.publish_sector_participation_20 = (
            lambda *args, _calls=calls, **kwargs: _calls.append("write"))

        out = cls.fetch(instance, full_history=False)
        assert calls == [], (
            f"{mod_name}.{cls.__name__}.fetch() crossed the US-only W1 boundary: {calls}")
        assert "breadth" in out and not out["breadth"].empty
        assert not (instance.cache_path.parent / "sector_participation_20.json").exists()


def test_sibling_adapters_construct_with_network_disabled_and_no_w1_config(monkeypatch):
    def _forbidden_get(*a, **kw):
        raise AssertionError("a sibling breadth adapter made an HTTP call during construction")
    monkeypatch.setattr("requests.get", _forbidden_get)
    monkeypatch.setattr(bmod.config, "secret", lambda name: None)  # no W1 vendor key present
    for mod_name, cls in _sibling_adapter_classes():
        inst = cls()  # must not raise, must not touch the network
        assert hasattr(inst, "licensed_daily_window")  # inherited — merely unused by fetch()
        assert isinstance(inst, bmod.BreadthAdapter)


# --------------------------------------------------------------------------- #
# Canonical derived package + Sector Central projection.  W1 has one generation:
# data/breadth/sector_participation_20.json -> site/sectordata/ same exact bytes.
# --------------------------------------------------------------------------- #


def test_w1_package_contract_has_one_shared_import_light_authority(monkeypatch, tmp_path):
    """Collector and public projection share one digest/validation authority."""
    import json
    from lib import sector_participation as w1_contract

    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    assert bmod.w1_contract is w1_contract
    assert w1_contract.generation_id(package) == package["generation_id"]
    w1_contract.validate_package(package)

    site = tmp_path / "site"
    out = w1_contract.read_public_pointer(
        source_path=path,
        site=site,
        current_expected_session=package["source"]["latest_expected_session"],
    )
    assert out["status"] == "ready"
    assert out["generation_id"] == package["generation_id"]
    assert (site / "sectordata" / "sector_participation_20.json").read_bytes() == path.read_bytes()


def _publish_fixture(monkeypatch, tmp_path, days=None, sectors=("Technology",),
                     n_names=5, stale=False):
    days = days or _sessions(25)
    members = pd.DataFrame({
        "symbol": [f"{sector[:2].upper()}{i}" for sector in sectors for i in range(n_names)],
        "sector": [sector for sector in sectors for _ in range(n_names)],
    })
    closes = _wide(
        members["symbol"].tolist(), days,
        lambda ticker, i: 100.0 + i + members["symbol"].tolist().index(ticker) / 100.0,
    )
    acquired_at = "2024-03-15T21:00:00+00:00"
    closes.attrs["member_evidence"] = {
        symbol: {
            "acquired_at": acquired_at,
            "requested_ticker": symbol,
            "response_ticker": symbol,
            "request_id": f"receipt-{symbol}",
            "response_status": "OK",
            "response_count": len(days),
            "requested_start": days[0].isoformat(),
            "requested_end": days[-1].isoformat(),
        }
        for symbol in members["symbol"]
    }
    result = _adapter().compute_sector_participation_20(closes, members)
    monkeypatch.setattr(bmod.nyse_calendar, "expected_last_session", lambda: days[-1])
    path = tmp_path / "breadth" / "sector_participation_20.json"
    ok = _adapter().publish_sector_participation_20(result, {}, members, path=path)
    assert ok is True
    if stale:
        later = _sessions(1, 2024, 4, 30)[-1]
        monkeypatch.setattr(bmod.nyse_calendar, "expected_last_session", lambda: later)
    return path, result, members


def _read_public(path, *, site=None):
    return w1_contract.read_public_pointer(
        source_path=path,
        site=site,
        current_expected_session=bmod.nyse_calendar.expected_last_session().isoformat(),
    )


def test_public_projection_missing_package_is_honest_not_a_crash(tmp_path):
    out = _read_public(tmp_path / "breadth" / "sector_participation_20.json")
    assert out["status"] == "missing"
    assert out["available"] is False
    assert "url" not in out  # only ready/stale pointers may expose a fetch target


def test_package_binds_invocation_clock_member_names_and_economic_response_receipts(monkeypatch, tmp_path):
    members = pd.DataFrame({
        "symbol": [f"T{i}" for i in range(5)],
        "name": [f"Company {i}" for i in range(5)],
        "sector": ["Technology"] * 5,
    })
    days = _sessions(25)
    closes = _wide(members["symbol"].tolist(), days, lambda ticker, i: 100.0 + i)
    closes.attrs["member_evidence"] = {
        symbol: {"request_id": f"receipt-{symbol}", "response_status": "OK",
                 "response_count": len(days), "requested_start": days[0].isoformat(),
                 "requested_end": days[-1].isoformat(),
                 "acquired_at": "2024-03-15T21:00:00+00:00",
                 "requested_ticker": symbol, "response_ticker": symbol}
        for symbol in members["symbol"]
    }
    result = _adapter().compute_sector_participation_20(closes, members)
    result.attrs["latest_expected_session"] = days[-1].isoformat()
    monkeypatch.setattr(
        bmod.nyse_calendar, "expected_last_session",
        lambda: _sessions(1, 2024, 4, 30)[-1],
    )
    first = _adapter().build_sector_participation_20_package(result, {}, members)
    assert first["source"]["latest_expected_session"] == days[-1].isoformat()
    assert first["source"]["requested_member_count"] == len(members)
    assert first["source"]["accepted_member_count"] == len(members)
    assert first["members"]["T0"]["name"] == "Company 0"

    changed = closes.copy()
    changed.attrs["member_evidence"] = dict(closes.attrs["member_evidence"])
    changed.attrs["member_evidence"]["T0"] = dict(changed.attrs["member_evidence"]["T0"])
    changed.attrs["member_evidence"]["T0"]["request_id"] = "different-receipt"
    second_result = _adapter().compute_sector_participation_20(changed, members)
    second_result.attrs["latest_expected_session"] = days[-1].isoformat()
    second = _adapter().build_sector_participation_20_package(second_result, {}, members)
    # Provider request IDs are transport-instance diagnostics, not economic content.
    # A no-change reacquisition therefore retains response/observation identity.
    assert second["source"]["response_set_id"] == first["source"]["response_set_id"]
    assert second["observation_id"] == first["observation_id"]
    assert second["generation_id"] != first["generation_id"]


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("method coverage law", lambda p: p["method"].pop("coverage_basis")),
        ("method floor", lambda p: p["method"]["display_floor"].update(min_coverage=0.8)),
        ("roster semantics", lambda p: p["reference"].pop("reconstruction_zh")),
        ("research destination", lambda p: p["members"]["TE0"].__setitem__("href", "stock.html#WRONG")),
        ("response identity", lambda p: p["source"].pop("response_set_id")),
        ("request identity", lambda p: p["source"].pop("request_identity")),
        ("requested range", lambda p: p["source"].__setitem__("requested_start", p["sessions"][1])),
        ("latest expected session", lambda p: p["source"].__setitem__("latest_expected_session", "not-a-date")),
        ("acquisition clock", lambda p: p["source"].__setitem__("acquired_at", None)),
        ("computation clock", lambda p: p.__setitem__("computed_at", "not-a-clock")),
        ("publication clock", lambda p: p.__setitem__("published_at", None)),
        ("typed sector count", lambda p: p["sectors"]["Technology"]["above"].__setitem__(0, False)),
        ("coverage counts", lambda p: p["source"].update(
            accepted_member_count=4, unavailable_member_count=1)),
    ],
)
def test_shared_validator_refuses_rehashed_missing_or_malformed_required_contract(
        monkeypatch, tmp_path, case, mutate):
    import json

    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    mutate(package)
    package["generation_id"] = w1_contract.generation_id(package)
    with pytest.raises(ValueError, match="W1"):
        w1_contract.validate_package(package)


def test_publish_writes_one_valid_same_generation_package(monkeypatch, tmp_path):
    import json
    path, _, members = _publish_fixture(
        monkeypatch, tmp_path, sectors=("Technology", "Energy"), n_names=5)
    assert sorted(p.name for p in path.parent.iterdir()) == ["sector_participation_20.json"]
    package = json.loads(path.read_text())
    assert package["schema"] == "sector_participation_20.v1"
    assert package["generation_id"].startswith("sha256:")
    assert package["method"]["window_sessions"] == 20
    assert package["method"]["comparison"] == "close > MA20"
    assert package["method"]["display_floor"] == {"min_eligible": 5, "min_coverage": 0.9}
    assert package["reference"]["universe"] == "S&P 500"
    assert package["reference"]["member_count"] == len(members)
    assert package["reference"]["observed_at"] is None
    assert package["source"]["basis"] == "split_adjusted"
    assert package["source"]["latest_expected_session"] == package["sessions"][-1]
    assert len(package["sessions"]) == 25
    for sector in ("Technology", "Energy"):
        row = package["sectors"][sector]
        assert len(row["pct"]) == len(package["sessions"])
        assert len(row["above"]) == len(package["sessions"])
        assert len(row["excluded"]["M"]) == len(package["sessions"])
    assert package["members"]["TE0"]["states"][-1] == "A"
    assert package["members"]["TE0"]["href"] == "stock.html#TE0"


def test_w1_package_trims_acquisition_warmup_but_preserves_source_range():
    days = _sessions(271, 2026, 9, 18)
    syms = [f"T{i}" for i in range(5)]
    members = _members(syms)
    closes = _wide(syms, days, lambda ticker, i: 100.0 + i + syms.index(ticker) / 100.0)
    closes.attrs["member_evidence"] = {
        symbol: {
            "acquired_at": "2026-09-18T22:00:00+00:00",
            "requested_ticker": symbol, "response_ticker": symbol,
            "request_id": f"receipt-{symbol}", "response_status": "OK",
            "response_count": len(days), "requested_start": days[0].isoformat(),
            "requested_end": days[-1].isoformat(),
        }
        for symbol in syms
    }
    result = _adapter().compute_sector_participation_20(closes, members)
    result.attrs["display_sessions"] = 252
    result.attrs["latest_expected_session"] = days[-1].isoformat()
    package = _adapter().build_sector_participation_20_package(result, {}, members)

    assert len(package["sessions"]) == 252
    assert package["sessions"][0] == days[-252].isoformat()
    assert package["sessions"][-1] == days[-1].isoformat()
    assert package["source"]["requested_start"] == days[0].isoformat()
    assert package["source"]["requested_end"] == days[-1].isoformat()
    assert package["source"]["requested_start"] < package["sessions"][0]
    assert all(len(row[key]) == 252 for row in package["sectors"].values()
               for key in ("above", "eligible", "expected", "pct"))
    assert all(len(values) == 252 for row in package["sectors"].values()
               for values in row["excluded"].values())
    assert all(isinstance(member["states"], str) and len(member["states"]) == 252
               for member in package["members"].values())
    assert all(len(member["distance_bps"]) == 252 for member in package["members"].values())
    w1_contract.validate_package(package)


def test_w1_observation_and_generation_identities_follow_frozen_clock_semantics(monkeypatch, tmp_path):
    import copy
    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = __import__("json").loads(path.read_text())

    assert package["observation_id"] == w1_contract.observation_id(package)
    assert package["generation_id"] == w1_contract.generation_id(package)

    published = copy.deepcopy(package)
    published["published_at"] = "2026-09-19T00:00:00+00:00"
    assert w1_contract.observation_id(published) == package["observation_id"]
    assert w1_contract.generation_id(published) == package["generation_id"]

    recomputed = copy.deepcopy(package)
    recomputed["computed_at"] = "2026-09-19T00:01:00+00:00"
    assert w1_contract.observation_id(recomputed) == package["observation_id"]
    assert w1_contract.generation_id(recomputed) != package["generation_id"]

    reacquired = copy.deepcopy(package)
    reacquired["source"]["acquired_at"] = "2026-09-19T00:02:00+00:00"
    assert w1_contract.observation_id(reacquired) == package["observation_id"]
    assert w1_contract.generation_id(reacquired) != package["generation_id"]


def test_no_change_reacquisition_ignores_transport_request_id_but_changes_generation_clock():
    import copy
    days = _sessions(25)
    syms = [f"T{i}" for i in range(5)]
    members = _members(syms)
    closes = _wide(syms, days, lambda ticker, i: 100.0 + i + syms.index(ticker) / 100.0)

    def evidence(acquired_at, prefix):
        return {
            symbol: {
                "acquired_at": acquired_at,
                "requested_ticker": symbol, "response_ticker": symbol,
                "request_id": f"{prefix}-{symbol}", "response_status": "OK",
                "response_count": len(days), "requested_start": days[0].isoformat(),
                "requested_end": days[-1].isoformat(), "basis": "split_adjusted",
                "adjusted": True,
            }
            for symbol in syms
        }

    first_closes = closes.copy()
    first_closes.attrs["member_evidence"] = evidence("2026-09-18T22:00:00+00:00", "request-one")
    first_result = _adapter().compute_sector_participation_20(first_closes, members)
    first_result.attrs["latest_expected_session"] = days[-1].isoformat()
    first = _adapter().build_sector_participation_20_package(first_result, {}, members)

    second_closes = closes.copy()
    second_closes.attrs["member_evidence"] = evidence("2026-09-19T00:02:00+00:00", "request-two")
    second_result = _adapter().compute_sector_participation_20(second_closes, members)
    second_result.attrs["latest_expected_session"] = days[-1].isoformat()
    second = _adapter().build_sector_participation_20_package(second_result, {}, members)

    assert first["source"]["response_set_id"] == second["source"]["response_set_id"]
    assert first["observation_id"] == second["observation_id"]
    assert first["generation_id"] != second["generation_id"]


def test_price_correction_changes_response_observation_and_generation_identities():
    days = _sessions(25)
    syms = [f"T{i}" for i in range(5)]
    members = _members(syms)
    closes = _wide(syms, days, lambda ticker, i: 100.0 + i + syms.index(ticker) / 100.0)
    common_evidence = {
        symbol: {
            "acquired_at": "2026-09-18T22:00:00+00:00",
            "requested_ticker": symbol, "response_ticker": symbol,
            "request_id": f"receipt-{symbol}", "response_status": "OK",
            "response_count": len(days), "requested_start": days[0].isoformat(),
            "requested_end": days[-1].isoformat(),
        }
        for symbol in syms
    }
    closes.attrs["member_evidence"] = common_evidence
    first_result = _adapter().compute_sector_participation_20(closes, members)
    first_result.attrs["latest_expected_session"] = days[-1].isoformat()
    first = _adapter().build_sector_participation_20_package(first_result, {}, members)

    corrected = closes.copy()
    corrected.iloc[-1, 0] += 0.125
    corrected.attrs["member_evidence"] = common_evidence
    second_result = _adapter().compute_sector_participation_20(corrected, members)
    second_result.attrs["latest_expected_session"] = days[-1].isoformat()
    second = _adapter().build_sector_participation_20_package(second_result, {}, members)

    assert first["source"]["response_set_id"] != second["source"]["response_set_id"]
    assert first["observation_id"] != second["observation_id"]
    assert first["generation_id"] != second["generation_id"]


def test_reordering_json_object_keys_changes_no_w1_content_identity(monkeypatch, tmp_path):
    import json
    source, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(source.read_text())
    reordered = json.loads(json.dumps(package, ensure_ascii=False, sort_keys=True))
    assert w1_contract.observation_id(reordered) == package["observation_id"]
    assert w1_contract.generation_id(reordered) == package["generation_id"]


def test_public_pointer_carries_both_observation_and_generation_ids(monkeypatch, tmp_path):
    source, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = __import__("json").loads(source.read_text())
    pointer = _read_public(source, site=tmp_path / "site")
    assert pointer["observation_id"] == package["observation_id"]
    assert pointer["generation_id"] == package["generation_id"]


def test_full_year_503_member_package_stays_inside_frozen_transfer_budget():
    import gzip
    sector_counts = [
        ("Communication Services", 24), ("Consumer Discretionary", 47),
        ("Consumer Staples", 34), ("Energy", 21), ("Financials", 76),
        ("Health Care", 59), ("Industrials", 83),
        ("Information Technology", 73), ("Materials", 25),
        ("Real Estate", 30), ("Utilities", 31),
    ]
    assert sum(count for _, count in sector_counts) == 503
    days = _sessions(252, 2026, 9, 18)
    symbols = []
    rows = []
    member_payload = {}
    for sector_index, (sector, count) in enumerate(sector_counts):
        for member_index in range(count):
            symbol = f"S{sector_index:02d}{member_index:03d}"
            symbols.append(symbol)
            rows.append({"symbol": symbol, "name": f"{sector} {member_index}", "sector": sector})
            states = ["ABHMIU"[(member_index + position) % 6] for position in range(len(days))]
            distances = [
                round((((member_index * 13 + position * 7) % 2000) / 7.0) - 100.0, 4)
                if state in {"A", "B"} else None
                for position, state in enumerate(states)
            ]
            member_payload[symbol] = {
                "name": f"{sector} {member_index}", "sector": sector,
                "states": states, "distance_bps": distances,
                "href": "stock.html#" + symbol,
            }
    members = pd.DataFrame(rows)
    result = pd.DataFrame({"proof": [1.0] * len(days)},
                          index=pd.DatetimeIndex(pd.Timestamp(day) for day in days))
    result.attrs.update({
        "sessions": [day.isoformat() for day in days],
        "members": member_payload,
        "member_evidence": {
            symbol: {
                "acquired_at": "2026-09-18T22:00:00+00:00",
                "requested_ticker": symbol, "response_ticker": symbol,
                "request_id": f"receipt-{symbol}", "response_status": "OK",
                "response_count": len(days), "requested_start": days[0].isoformat(),
                "requested_end": days[-1].isoformat(),
            }
            for symbol in symbols
        },
        "requested_start": days[0].isoformat(), "requested_end": days[-1].isoformat(),
        "observed_max_session": days[-1].isoformat(),
        "latest_expected_session": days[-1].isoformat(),
        "acquired_at": "2026-09-18T22:00:00+00:00",
        "computed_at": "2026-09-18T22:01:00+00:00",
        "display_sessions": 252,
    })
    package = _adapter().build_sector_participation_20_package(result, {}, members)
    blob = w1_contract.json_bytes(package)
    assert len(package["sessions"]) == 252
    assert len(package["members"]) == 503
    assert len(blob) <= 1_500_000
    assert len(gzip.compress(blob, compresslevel=6)) <= 600_000
    w1_contract.validate_package(package)


def test_package_sector_counts_are_derived_from_same_generation_member_states(monkeypatch, tmp_path):
    import json
    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    sector = package["sectors"]["Technology"]
    names = [m for m in package["members"].values() if m["sector"] == "Technology"]
    for position in range(len(package["sessions"])):
        states = [member["states"][position] for member in names]
        assert sector["above"][position] == states.count("A")
        assert sector["eligible"][position] == states.count("A") + states.count("B")
        assert sector["expected"][position] == len(names)
        for state in ("H", "M", "I", "U"):
            assert sector["excluded"][state][position] == states.count(state)


def test_public_projection_returns_same_generation_pointer(monkeypatch, tmp_path):
    source, _, _ = _publish_fixture(monkeypatch, tmp_path)
    site = tmp_path / "site"
    out = _read_public(source, site=site)
    public = site / "sectordata" / "sector_participation_20.json"
    assert out["status"] == "ready"
    assert out["available"] is True
    assert out["generation_id"].startswith("sha256:")
    assert out["source_session"] == out["latest_expected_session"]
    assert public.read_bytes() == source.read_bytes()


def test_public_pointer_is_stale_only_from_package_clocks(monkeypatch, tmp_path):
    source, _, _ = _publish_fixture(monkeypatch, tmp_path, stale=True)
    out = _read_public(source)
    assert out["status"] == "stale"
    assert out["available"] is True
    assert out["source_session"] == out["latest_expected_session"]
    assert out["latest_expected_session"] < out["current_expected_session"]


def test_preserved_prior_generation_becomes_truthfully_stale_without_mutation(monkeypatch, tmp_path):
    source, _, _ = _publish_fixture(monkeypatch, tmp_path)
    before = source.read_bytes()
    generation_expected = __import__("json").loads(before)["source"]["latest_expected_session"]
    later = _sessions(1, 2025, 1, 31)[-1]
    monkeypatch.setattr(bmod.nyse_calendar, "expected_last_session", lambda: later)

    out = _read_public(source, site=tmp_path / "site")
    assert out["status"] == "stale"
    assert out["latest_expected_session"] == generation_expected
    assert out["current_expected_session"] == later.isoformat()
    assert source.read_bytes() == before
    assert (tmp_path / "site" / "sectordata" /
            "sector_participation_20.json").read_bytes() == before


def test_public_projection_refuses_corrupt_or_generation_tampered_package(monkeypatch, tmp_path):
    import json
    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    package["sectors"]["Technology"]["above"][-1] = 999
    path.write_text(json.dumps(package))
    site = tmp_path / "site"
    out = _read_public(path, site=site)
    assert out["status"] == "invalid"
    assert out["available"] is False
    assert not (site / "sectordata" / "sector_participation_20.json").exists()


def test_public_projection_refuses_rehashed_summary_detail_disagreement(monkeypatch, tmp_path):
    import json
    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    package["sectors"]["Technology"]["above"][-1] = 999
    package["generation_id"] = w1_contract.generation_id(package)
    path.write_text(json.dumps(package))
    out = _read_public(path, site=tmp_path / "site")
    assert out["status"] == "invalid"
    assert out["available"] is False
    assert "url" not in out


def test_unavailable_new_generation_preserves_prior_valid_package(monkeypatch, tmp_path):
    path, _, members = _publish_fixture(monkeypatch, tmp_path)
    before = path.read_bytes()
    sessions = _sessions(25)
    empty = pd.DataFrame(index=pd.DatetimeIndex(pd.Timestamp(d) for d in sessions),
                         columns=members["symbol"], dtype=float)
    empty.attrs["member_evidence"] = {
        symbol: {"state": "U", "unavailable": True, "reason": "simulated outage"}
        for symbol in members["symbol"]
    }
    result = _adapter().compute_sector_participation_20(empty, members)
    assert result is not None
    assert _adapter().publish_sector_participation_20(
        result, {symbol: "simulated outage" for symbol in members["symbol"]},
        members, path=path) is False
    assert path.read_bytes() == before


def test_first_run_unavailable_generation_is_explicit_but_not_fetchable(monkeypatch, tmp_path):
    members = _members([f"T{i}" for i in range(5)])
    sessions = _sessions(25)
    empty = pd.DataFrame(index=pd.DatetimeIndex(pd.Timestamp(d) for d in sessions),
                         columns=members["symbol"], dtype=float)
    empty.attrs["member_evidence"] = {
        symbol: {"state": "U", "unavailable": True, "reason": "no qualified source"}
        for symbol in members["symbol"]
    }
    result = _adapter().compute_sector_participation_20(empty, members)
    target = tmp_path / "breadth" / "sector_participation_20.json"
    assert _adapter().publish_sector_participation_20(
        result, {symbol: "no qualified source" for symbol in members["symbol"]},
        members, path=target) is True
    out = _read_public(target, site=tmp_path / "site")
    assert out["status"] == "withheld"
    assert out["available"] is False
    assert "url" not in out


def test_failed_new_generation_leaves_prior_package_byte_identical(monkeypatch, tmp_path):
    path, _, members = _publish_fixture(monkeypatch, tmp_path)
    before = path.read_bytes()
    ok = _adapter().publish_sector_participation_20(
        None, {"TE0": "simulated source failure"}, members, path=path)
    assert ok is False
    assert path.read_bytes() == before


def test_atomic_replace_fault_leaves_prior_package_byte_identical(monkeypatch, tmp_path):
    path, result, members = _publish_fixture(monkeypatch, tmp_path)
    before = path.read_bytes()

    def fail_replace(src, dst):
        raise OSError("simulated interruption before atomic replace")

    monkeypatch.setattr(w1_contract.os, "replace", fail_replace)
    assert _adapter().publish_sector_participation_20(result, {}, members, path=path) is False
    assert path.read_bytes() == before
    assert not list(path.parent.glob(".sector_participation_20.json.*"))


# --------------------------------------------------------------------------- #
# R1/R5 (Sol 1789096018.269229): the connected producer->consumer path, tested
# with injected fetch stubs — never a real network call, never wired into
# fetch(). Exercises fetch_sector_participation_20 -> compute_... -> publish...
# -> the builder's read, end to end.
# --------------------------------------------------------------------------- #

def test_default_fetch_range_covers_1y_view_plus_19_session_warmup():
    end = _sessions(1, 2024, 12, 31)[-1]
    seen = {}

    def fake_fetch_one(ticker, start, requested_end):
        seen["start"] = start
        seen["end"] = requested_end
        days = nyse_calendar.sessions_between(start, requested_end)
        return pd.Series({pd.Timestamp(day): 100.0 + i for i, day in enumerate(days)})

    result, failures = _adapter().fetch_sector_participation_20(
        _members(["ONLY"]), end=end, fetch_one=fake_fetch_one,
        max_workers=1, operation_budget_seconds=2.0)
    assert failures == {}
    assert result is not None
    expected_start = nyse_calendar.session_n_back(end, 252 + 19 - 1)
    assert seen == {"start": expected_start, "end": end}
    assert len(result.index) == 252 + 19
    assert result.attrs["latest_expected_session"] == end.isoformat()


def test_real_us_fetch_invokes_w1_publisher_on_the_same_owner(monkeypatch, tmp_path):
    days = _sessions(220)
    members = _members([f"T{i}" for i in range(5)])
    closes = _wide(members["symbol"].tolist(), days, lambda ticker, i: 100.0 + i)
    adapter = _adapter()
    adapter.cache_path = tmp_path / "breadth" / "_closes_cache.parquet"
    monkeypatch.setattr(adapter, "constituents", lambda: members)
    monkeypatch.setattr(adapter, "constituents_checked", lambda value: value)
    monkeypatch.setattr(adapter, "_download_closes", lambda tickers, period: closes)
    sentinel = pd.DataFrame({"sentinel": [1.0]})
    calls = []
    monkeypatch.setattr(
        adapter, "fetch_sector_participation_20",
        lambda roster: (calls.append(("fetch", roster.copy())) or (sentinel, {"T4": "x"})),
    )

    def publish(result, failures, roster, *, path):
        calls.append(("publish", result, failures, roster.copy(), path))
        return True

    monkeypatch.setattr(adapter, "publish_sector_participation_20", publish)
    out = adapter.fetch(full_history=False)
    assert [call[0] for call in calls] == ["fetch", "publish"]
    assert calls[1][1] is sentinel
    assert calls[1][2] == {"T4": "x"}
    assert calls[1][4] == adapter.cache_path.parent / "sector_participation_20.json"
    assert "breadth" in out and not out["breadth"].empty


def test_real_us_fetch_invokes_w1_once_and_keeps_old_outputs_on_w1_failure(monkeypatch, tmp_path):
    days = _sessions(220)
    members = _members([f"T{i}" for i in range(5)])
    closes = _wide(members["symbol"].tolist(), days, lambda ticker, i: 100.0 + i)
    adapter = _adapter()
    adapter.cache_path = tmp_path / "breadth" / "_closes_cache.parquet"
    monkeypatch.setattr(adapter, "constituents", lambda: members)
    monkeypatch.setattr(adapter, "constituents_checked", lambda value: value)
    monkeypatch.setattr(adapter, "_download_closes", lambda tickers, period: closes)
    calls = []

    def fail_w1(*args, **kwargs):
        calls.append("fetch")
        raise RuntimeError("simulated W1-only failure")

    monkeypatch.setattr(adapter, "fetch_sector_participation_20", fail_w1)
    out = adapter.fetch(full_history=False)
    assert calls == ["fetch"]
    assert "breadth" in out and not out["breadth"].empty
    assert set(("pct_above_50", "pct_above_200")).issubset(out["breadth"].columns)


def test_fetch_sector_participation_20_connects_producer_to_pure_calc():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(5)]
    members = _members(syms)

    def fake_fetch_one(ticker, start, end):
        i = int(ticker[1:])
        s = pd.Series({pd.Timestamp(d): 100.0 + i + j for j, d in enumerate(days)})
        s.attrs.update(basis="split_adjusted", adjusted=True)
        return s

    result, failures = _adapter().fetch_sector_participation_20(
        members, end=days[-1], window_days=30, fetch_one=fake_fetch_one)
    assert not failures
    assert result is not None
    last = result.iloc[-1]
    assert last["Technology|eligible_20"] == 5
    assert last["Technology|above_20"] == 5


def test_fetch_sector_participation_20_isolates_per_ticker_failures():
    """A per-ticker fetch failure must not sink the whole vertical — the failed
    name simply never becomes eligible, and the failure is disclosed, not hidden."""
    days = _sessions(20)
    syms = [f"T{i}" for i in range(5)]
    members = _members(syms)

    def flaky_fetch_one(ticker, start, end):
        if ticker == "T4":
            raise bmod.LicensedSourceError("T4: simulated vendor failure")
        s = pd.Series({pd.Timestamp(d): 100.0 + j for j, d in enumerate(days)})
        return s

    result, failures = _adapter().fetch_sector_participation_20(
        members, end=days[-1], window_days=30, fetch_one=flaky_fetch_one)
    assert failures == {"T4": "T4: simulated vendor failure"}
    last = result.iloc[-1]
    assert last["Technology|expected_20"] == 5   # full roster, T4 included
    assert last["Technology|eligible_20"] == 4   # T4's fetch failure excludes it, not a crash
    assert set(result.attrs["members"]["T4"]["states"]) == {"U"}


def test_fetch_sector_participation_20_all_tickers_fail_is_explicit_unavailable_generation():
    members = _members(["ONLY"])

    def always_fails(ticker, start, end):
        raise bmod.LicensedSourceError("no key")

    result, failures = _adapter().fetch_sector_participation_20(
        members, fetch_one=always_fails)
    assert result is not None
    assert failures == {"ONLY": "no key"}
    assert set(result.attrs["members"]["ONLY"]["states"]) == {"U"}
    assert result.iloc[-1]["Technology|expected_20"] == 1
    assert result.iloc[-1]["Technology|eligible_20"] == 0
    assert np.isnan(result.iloc[-1]["Technology|pct_above_20"])


def test_fetch_sector_participation_20_never_calls_network(monkeypatch):
    """The orchestrating function must make zero real HTTP calls in this suite —
    every path here is exercised through an injected fetch_one."""
    def _forbidden_get(*a, **kw):
        raise AssertionError("fetch_sector_participation_20 touched the network directly")
    monkeypatch.setattr("requests.get", _forbidden_get)
    members = _members(["ONLY"])
    result, failures = _adapter().fetch_sector_participation_20(
        members, fetch_one=lambda t, s, e: (_ for _ in ()).throw(bmod.LicensedSourceError("x")))
    assert result is not None
    assert failures == {"ONLY": "x"}
    assert set(result.attrs["members"]["ONLY"]["states"]) == {"U"}


def test_fetch_sector_participation_20_fatal_auth_stops_scheduling_new_members():
    import threading
    import time

    syms = [f"T{i}" for i in range(8)]
    members = _members(syms)
    called = []
    lock = threading.Lock()

    def auth_refusal(ticker, start, end):
        with lock:
            called.append(ticker)
        if ticker == "T0":
            raise bmod.LicensedSourceError("entitlement refused", fatal=True)
        time.sleep(0.1)
        return pd.Series(dtype=float)

    result, failures = _adapter().fetch_sector_participation_20(
        members, end=_sessions(1)[0], window_days=30, fetch_one=auth_refusal,
        max_workers=2, operation_budget_seconds=2.0)
    assert set(called).issubset({"T0", "T1"})
    assert set(failures) == set(syms)
    assert all(set(result.attrs["members"][ticker]["states"]) == {"U"} for ticker in syms)


def test_late_fatal_refusal_discards_high_coverage_partial_generation():
    days = _sessions(20)
    syms = [f"T{i}" for i in range(10)]

    def late_fatal(ticker, start, end):
        if ticker == "T9":
            raise bmod.LicensedSourceError("late entitlement refusal", fatal=True)
        return pd.Series({pd.Timestamp(day): 100.0 + i for i, day in enumerate(days)})

    result, failures = _adapter().fetch_sector_participation_20(
        _members(syms), end=days[-1], window_days=30, fetch_one=late_fatal,
        max_workers=1, operation_budget_seconds=2.0)
    assert set(failures) == set(syms)
    assert all(set(result.attrs["members"][ticker]["states"]) == {"U"} for ticker in syms)
    last = result.iloc[-1]
    assert last["Technology|eligible_20"] == 0
    assert np.isnan(last["Technology|pct_above_20"])


def test_budget_expiry_discards_high_coverage_partial_generation():
    import time

    days = _sessions(20)
    syms = [f"T{i}" for i in range(10)]

    def late_slow(ticker, start, end):
        if ticker == "T9":
            time.sleep(0.5)
        return pd.Series({pd.Timestamp(day): 100.0 + i for i, day in enumerate(days)})

    result, failures = _adapter().fetch_sector_participation_20(
        _members(syms), end=days[-1], window_days=30, fetch_one=late_slow,
        max_workers=1, operation_budget_seconds=0.2)
    assert set(failures) == set(syms)
    assert all(set(result.attrs["members"][ticker]["states"]) == {"U"} for ticker in syms)
    last = result.iloc[-1]
    assert last["Technology|eligible_20"] == 0
    assert np.isnan(last["Technology|pct_above_20"])


def test_default_w1_reader_never_starts_when_request_ceiling_exceeds_budget(monkeypatch):
    syms = ["A", "B", "C"]
    adapter = _adapter()
    called = []
    monkeypatch.setattr(
        bmod.config, "load",
        lambda: {"polygon": {
            "w1_request_timeout_seconds": 7,
            "w1_request_retries": 2,
            "w1_request_backoff_seconds": 0.25,
        }},
    )
    monkeypatch.setattr(
        adapter, "licensed_daily_window",
        lambda ticker, start, end: called.append(ticker),
    )
    result, failures = adapter.fetch_sector_participation_20(
        _members(syms), end=_sessions(1)[0], window_days=30,
        max_workers=2, operation_budget_seconds=1.0)
    assert called == []
    assert set(failures) == set(syms)
    assert all(set(result.attrs["members"][ticker]["states"]) == {"U"} for ticker in syms)


def test_fetch_sector_participation_20_zero_budget_makes_no_requests():
    syms = ["A", "B", "C"]
    called = []
    result, failures = _adapter().fetch_sector_participation_20(
        _members(syms), end=_sessions(1)[0], window_days=30,
        fetch_one=lambda ticker, start, end: called.append(ticker),
        max_workers=2, operation_budget_seconds=0.0)
    assert called == []
    assert set(failures) == set(syms)
    assert all(set(result.attrs["members"][ticker]["states"]) == {"U"} for ticker in syms)


def test_fetch_sector_participation_20_respects_bounded_concurrency():
    import threading
    import time

    syms = [f"T{i}" for i in range(9)]
    days = _sessions(20)
    lock = threading.Lock()
    active = 0
    max_active = 0

    def bounded_fetch(ticker, start, end):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        try:
            time.sleep(0.015)
            return pd.Series({pd.Timestamp(day): 100.0 + i for i, day in enumerate(days)})
        finally:
            with lock:
                active -= 1

    result, failures = _adapter().fetch_sector_participation_20(
        _members(syms), end=days[-1], window_days=30, fetch_one=bounded_fetch,
        max_workers=3, operation_budget_seconds=2.0)
    assert failures == {}
    assert result is not None
    assert 1 < max_active <= 3


def test_integrated_publish_and_public_projection_round_trip(monkeypatch, tmp_path):
    """Connected fetch -> compute -> publish -> public-projection path."""
    monkeypatch.setattr(bmod.config, "data_dir", lambda: tmp_path)
    end = _sessions(1)[0]
    window_days = 30
    # mirror fetch_sector_participation_20's own start computation exactly, so the
    # fake HTTP handler covers the FULL requested window — not just the last 20
    # sessions — otherwise licensed_daily_window's missing-session check (correctly)
    # rejects the gap between window start and the first faked session.
    start = nyse_calendar.last_session_on_or_before(end - pd.Timedelta(days=window_days))
    days = nyse_calendar.sessions_between(start, end)
    monkeypatch.setattr(bmod.nyse_calendar, "expected_last_session", lambda: end)
    syms = [f"T{i}" for i in range(5)]
    members = _members(syms)
    _fake_key(monkeypatch)

    def fake_http_get(self, url, **kw):
        ticker = url.split("/ticker/")[1].split("/")[0]
        rows = [_agg_row(_ts_ms(d), 100.0 + i) for i, d in enumerate(days)]
        return _FakeResponse(_payload(ticker, rows))

    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", fake_http_get)
    a = _adapter()
    result, failures = a.fetch_sector_participation_20(members, end=end, window_days=window_days)
    assert not failures
    a.publish_sector_participation_20(result, failures, members)

    out = _read_public(tmp_path / "breadth" / "sector_participation_20.json")
    assert out["status"] == "ready"
    assert out["available"] is True
    assert out["generation_id"].startswith("sha256:")
    assert out["source_session"] == days[-1].isoformat()
    assert out["latest_expected_session"] == days[-1].isoformat()
    assert out["stale"] is False

# --------------------------------------------------------------------------- #
# Historical Money & Breadth browser journey — one lazy package, same generation.
# --------------------------------------------------------------------------- #


def test_w1_browser_asset_is_owned_by_first_money_activation_only():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    workspace = (root / "templates" / "si_workspace.js").read_text()
    compact = "".join(workspace.split())
    assert "money:['heatmap.js','sector_participation_20.js']" in compact
    assert "if(loaded[f])continue;" in compact
    template = (root / "templates" / "sector_central.html.j2").read_text()
    assert "renderSectorParticipation" not in template
    assert '<script src="sector_participation_20.js"' not in template


def test_w1_template_exposes_calendar_detail_and_constituent_contract():
    from pathlib import Path
    template = (Path(__file__).resolve().parents[1] / "templates" / "sector_central.html.j2").read_text()
    for needle in (
        'id="sp-window-controls"', 'data-sp-window="63"', 'data-sp-window="126"',
        'data-sp-window="252"', 'id="sp-clear"', 'id="sp-calendar"',
        'id="sp-detail"', 'id="sp-detail-summary"', 'id="sp-detail-provenance"',
        'id="sp-constituents"', 'aria-live="polite"',
    ):
        assert needle in template


def test_w1_bilingual_accessible_names_are_plain_text_not_html_inside_aria_attributes():
    from pathlib import Path
    template = (Path(__file__).resolve().parents[1] / "templates" / "sector_central.html.j2").read_text()
    assert 'aria-label="Participation calendar window / 参与度日历区间"' in template
    assert 'aria-label="Historical sector participation calendar / 历史板块参与度日历"' in template
    w1 = template.split('id="sector-participation"', 1)[1].split('{% if flows_html %}', 1)[0]
    assert 'aria-label="{{ t(' not in w1


def test_w1_client_refuses_generation_mismatch_and_never_recomputes_prices():
    from pathlib import Path
    client = (Path(__file__).resolve().parents[1] / "templates" / "sector_participation_20.js").read_text()
    assert "fetch(pointer.url" in client
    assert "pointer.generation_id" in client
    assert "pointer.observation_id" in client
    assert "value.generation_id" in client
    assert "value.observation_id" in client
    assert "crypto.subtle.digest" in client
    assert "sector_participation_20.v1" in client
    assert "distance_bps" in client
    assert "member.states" in client
    assert "member.name" in client
    assert "source.basis" in client
    assert "pointer.current_expected_session" in client
    assert "pkg.generation_id" in client
    assert "observation digest" in client
    assert "reconstruction_zh" in client
    assert "stock\\.html#" in client
    for forbidden in ("rolling(", "movingAverage", "price /", "localStorage", "setInterval"):
        assert forbidden not in client


def test_w1_query_state_preserves_workspace_hash_and_supports_back_clear_language():
    from pathlib import Path
    client = (Path(__file__).resolve().parents[1] / "templates" / "sector_participation_20.js").read_text()
    for key in ("sp_window", "sp_sector", "sp_session"):
        assert key in client
    assert "history.pushState" in client
    assert "window.addEventListener('popstate'" in client
    assert "document.addEventListener('langchange'" in client
    assert "url.hash" in client
    assert "location.hash=" not in "".join(client.split())
    assert "removeQueryState" in client


def test_w1_unavailable_state_relocalizes_without_refetch():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    client = (root / "templates" / "sector_participation_20.js").read_text()
    template = (root / "templates" / "sector_central.html.j2").read_text()
    assert "var unavailableKind=null;" in client
    assert "unavailableKind=kind;" in client
    assert "else if(unavailableKind) unavailable(unavailableKind);" in client
    assert "Participation calendar window / 参与度日历区间" in template
    assert "Historical sector participation calendar / 历史板块参与度日历" in template


def test_w1_client_asset_projection_is_shared_and_byte_exact(tmp_path):
    from pathlib import Path

    template_root = Path(__file__).resolve().parents[1] / "templates"
    site = tmp_path / "site"
    assert w1_contract.copy_client_asset(template_root=template_root, site=site) is True
    assert (site / w1_contract.CLIENT_ASSET).read_bytes() == (
        template_root / w1_contract.CLIENT_ASSET
    ).read_bytes()


def test_w1_client_runtime_accepts_exact_published_generation(monkeypatch, tmp_path):
    import subprocess
    from pathlib import Path

    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    client_path = Path(__file__).resolve().parents[1] / "templates" / "sector_participation_20.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),{webcrypto}=require('node:crypto');
const code=fs.readFileSync(process.argv[1],'utf8');
const pkg=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const window={crypto:webcrypto,TextEncoder};
const context={window,crypto:webcrypto,TextEncoder,document:{getElementById:()=>null},console};
vm.createContext(context); vm.runInContext(code,context);
const api=context.window.SectorParticipation20;
if(!api||typeof api.validatePackage!=='function') process.exit(3);
api.validatePackage(pkg,pkg.generation_id,pkg.observation_id).then(value=>{
  if(value.generation_id!==pkg.generation_id) process.exit(4);
  process.exit(0);
}).catch(error=>{console.error(error);process.exit(5);});
"""
    completed = subprocess.run(
        ["node", "-e", script, str(client_path), str(path)],
        text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout



def test_w1_client_roster_identity_is_independent_of_browser_locale(monkeypatch, tmp_path):
    """A valid generation must not self-refuse under locale-specific collation."""
    import os
    import subprocess
    from pathlib import Path

    days = _sessions(25)
    symbols = ["A", "AAPL", "ABBV", "ABNB", "ABT"]
    members = _members(symbols)
    closes = _wide(
        symbols, days,
        lambda ticker, index: 100.0 + index + symbols.index(ticker) / 100.0,
    )
    acquired_at = "2024-03-15T21:00:00+00:00"
    closes.attrs["member_evidence"] = {
        symbol: {
            "acquired_at": acquired_at,
            "requested_ticker": symbol,
            "response_ticker": symbol,
            "request_id": f"receipt-{symbol}",
            "response_status": "OK",
            "response_count": len(days),
            "requested_start": days[0].isoformat(),
            "requested_end": days[-1].isoformat(),
        }
        for symbol in symbols
    }
    result = _adapter().compute_sector_participation_20(closes, members)
    monkeypatch.setattr(bmod.nyse_calendar, "expected_last_session", lambda: days[-1])
    package_path = tmp_path / "breadth" / "sector_participation_20.json"
    assert _adapter().publish_sector_participation_20(
        result, {}, members, path=package_path) is True

    client_path = Path(__file__).resolve().parents[1] / "templates" / "sector_participation_20.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),{webcrypto}=require('node:crypto');
const code=fs.readFileSync(process.argv[1],'utf8');
const pkg=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const locale=Intl.DateTimeFormat().resolvedOptions().locale.toLowerCase();
if(!locale.startsWith('da')) process.exit(6);
const window={crypto:webcrypto,TextEncoder};
const context={window,crypto:webcrypto,TextEncoder,document:{getElementById:()=>null},console};
vm.createContext(context); vm.runInContext(code,context);
context.window.SectorParticipation20.validatePackage(pkg,pkg.generation_id,pkg.observation_id)
  .then(()=>process.exit(0))
  .catch(error=>{console.error(error.message);process.exit(5);});
"""
    env = dict(os.environ, LANG="da_DK.UTF-8", LC_ALL="da_DK.UTF-8")
    completed = subprocess.run(
        ["node", "-e", script, str(client_path), str(package_path)],
        text=True, capture_output=True, check=False, env=env)
    assert completed.returncode == 0, completed.stderr or completed.stdout

@pytest.mark.parametrize("violation", ["missing_response_set", "coverage_counts"])
def test_w1_client_runtime_refuses_rehashed_required_contract_violation(
        monkeypatch, tmp_path, violation):
    import json
    import subprocess
    from pathlib import Path

    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    if violation == "missing_response_set":
        package["source"].pop("response_set_id")
    else:
        package["source"].update(accepted_member_count=4, unavailable_member_count=1)
    package["generation_id"] = w1_contract.generation_id(package)
    package_path = tmp_path / f"{violation}.json"
    package_path.write_text(json.dumps(package))
    client_path = Path(__file__).resolve().parents[1] / "templates" / "sector_participation_20.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),{webcrypto}=require('node:crypto');
const code=fs.readFileSync(process.argv[1],'utf8');
const pkg=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const window={crypto:webcrypto,TextEncoder};
const context={window,crypto:webcrypto,TextEncoder,document:{getElementById:()=>null},console};
vm.createContext(context); vm.runInContext(code,context);
context.window.SectorParticipation20.validatePackage(pkg,pkg.generation_id)
  .then(()=>process.exit(4)).catch(()=>process.exit(0));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(client_path), str(package_path)],
        text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_w1_client_runtime_refuses_rehashed_summary_detail_disagreement(monkeypatch, tmp_path):
    import json
    import subprocess
    path, _, _ = _publish_fixture(monkeypatch, tmp_path)
    package = json.loads(path.read_text())
    package["sectors"]["Technology"]["above"][-1] = 999
    package["generation_id"] = w1_contract.generation_id(package)
    package_path = tmp_path / "tampered.json"
    package_path.write_text(json.dumps(package))
    from pathlib import Path
    client_path = Path(__file__).resolve().parents[1] / "templates" / "sector_participation_20.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),{webcrypto}=require('node:crypto');
const code=fs.readFileSync(process.argv[1],'utf8');
const pkg=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const window={crypto:webcrypto,TextEncoder};
const context={window,crypto:webcrypto,TextEncoder,document:{getElementById:()=>null},console};
vm.createContext(context); vm.runInContext(code,context);
const api=context.window.SectorParticipation20;
if(!api||typeof api.validatePackage!=='function') process.exit(3);
api.validatePackage(pkg,pkg.generation_id).then(()=>process.exit(4)).catch(()=>process.exit(0));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(client_path), str(package_path)],
        text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_w1_semantic_suite_is_owned_by_one_code_gated_ci_job():
    from pathlib import Path
    import yaml

    manifest = yaml.safe_load((Path(__file__).resolve().parents[1] /
                               ".github" / "ci" / "legacy-jobs.yml").read_text())
    owners = []
    for job_id, job in manifest["jobs"].items():
        commands = "\n".join(
            str(step.get("run", "")) for step in job.get("steps", [])
            if isinstance(step, dict))
        if "tests/test_sector_central_participation.py" in commands:
            owners.append((job_id, job.get("gate"), commands))
    assert len(owners) == 1, owners
    assert owners[0][1] == "code", owners
    assert "python -m pytest tests/test_sector_central_participation.py -q" in owners[0][2]
