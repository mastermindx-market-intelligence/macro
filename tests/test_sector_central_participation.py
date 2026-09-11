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
    """UTC ms for 20:00 on session date d — safely mid-afternoon US/Eastern
    regardless of DST, so tz_convert().normalize() always lands back on d."""
    return int(pd.Timestamp(d).timestamp() * 1000) + 20 * 3600 * 1000


def _agg_row(ts_ms: int, close: float) -> dict:
    return {"t": ts_ms, "o": close, "h": close, "l": close, "c": close, "v": 1000}


def test_licensed_daily_window_returns_split_adjusted_series(monkeypatch):
    days = _sessions(3)
    payload = {"results": [_agg_row(_ts_ms(d), 100.0 + i) for i, d in enumerate(days)]}
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


def test_licensed_daily_window_raises_on_missing_expected_session(monkeypatch):
    days = _sessions(5)
    skip = days[2]
    payload = {"results": [_agg_row(_ts_ms(d), 100.0) for d in days if d != skip]}
    monkeypatch.setattr(bmod.config, "secret",
                        lambda name: "fake-key" if name == "POLYGON_API_KEY" else None)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get",
                        lambda self, url, **kw: _FakeResponse(payload))
    a = _adapter()
    with pytest.raises(bmod.LicensedSourceError, match="missing"):
        a.licensed_daily_window("AAPL", days[0], days[-1])


def test_licensed_daily_window_raises_without_key(monkeypatch):
    monkeypatch.setattr(bmod.config, "secret", lambda name: None)
    a = _adapter()
    with pytest.raises(bmod.LicensedSourceError, match="no licensed vendor key"):
        a.licensed_daily_window("AAPL", _sessions(2)[0], _sessions(2)[-1])


def test_licensed_daily_window_never_uses_apikey_query_param(monkeypatch):
    """Regression pin for the documented security law (scripts/massive_entitlement_probe.py):
    the key must never appear as a query parameter, only the Authorization header."""
    days = _sessions(2)
    payload = {"results": [_agg_row(_ts_ms(d), 100.0) for d in days]}
    monkeypatch.setattr(bmod.config, "secret",
                        lambda name: "super-secret-key" if name == "POLYGON_API_KEY" else None)
    seen = {}

    def fake_http_get(self, url, **kwargs):
        seen["params"] = kwargs.get("params") or {}
        seen["url"] = url
        return _FakeResponse(payload)

    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", fake_http_get)
    _adapter().licensed_daily_window("AAPL", days[0], days[-1])
    assert "super-secret-key" not in seen["url"]
    assert "apiKey" not in seen["params"]
    assert "super-secret-key" not in str(seen["params"])


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


def test_sibling_fetch_never_references_w1_methods():
    for mod_name, cls in _sibling_adapter_classes():
        names = cls.fetch.__code__.co_names
        for w1_name in _W1_METHOD_NAMES:
            assert w1_name not in names, (
                f"{mod_name}.{cls.__name__}.fetch() references {w1_name} — "
                "W1 must stay reachable only through the S&P breadth owner")


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
# scripts.build_sector_central.read_sector_participation_20 — the builder-side
# read. Never fetches market data; only reads an artifact if the (separately
# gated, not-yet-wired) licensed acquisition has published one.
# --------------------------------------------------------------------------- #

def test_builder_read_missing_artifact_is_honest_not_a_crash(monkeypatch, tmp_path):
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    out = bsc.read_sector_participation_20()
    assert out == {"available": False, "note": "not yet published"}


def test_builder_read_present_artifact_reports_metadata(monkeypatch, tmp_path):
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    days = _sessions(3)
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days])
    part = pd.DataFrame({"Technology|eligible_20": [5.0, 5.0, 5.0]}, index=idx)
    bdir = tmp_path / "breadth"
    bdir.mkdir(parents=True)
    part.to_parquet(bdir / "sector_participation_20.parquet")
    out = bsc.read_sector_participation_20()
    assert out["available"] is True
    assert out["basis"] == "split_adjusted"
    assert out["window_sessions"] == 20
    assert out["as_of"] == idx.max().isoformat()


def test_builder_read_never_raises_on_corrupt_artifact(monkeypatch, tmp_path):
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    bdir = tmp_path / "breadth"
    bdir.mkdir(parents=True)
    (bdir / "sector_participation_20.parquet").write_bytes(b"not a parquet file")
    out = bsc.read_sector_participation_20()  # must never raise — additive, fail-soft
    assert out["available"] is False
