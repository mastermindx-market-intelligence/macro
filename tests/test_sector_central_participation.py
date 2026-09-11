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


def test_licensed_daily_window_raises_on_missing_expected_session(monkeypatch):
    days = _sessions(5)
    skip = days[2]
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days if d != skip])
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
    payload = _payload("AAPL", [_agg_row(_ts_ms(d), 100.0) for d in days])
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
    rows = [_agg_row(_ts_ms(stray), 1.0)] + [_agg_row(_ts_ms(d), 100.0) for d in in_window]
    payload = _payload("AAPL", rows)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    s = _adapter().licensed_daily_window("AAPL", in_window[0], in_window[-1])
    assert len(s) == 3
    assert stray not in [d.date() for d in s.index]


def test_licensed_daily_window_rejects_boolean_close_R3(monkeypatch):
    days = _sessions(2)
    rows = [_agg_row(_ts_ms(days[0]), True), _agg_row(_ts_ms(days[1]), 100.0)]
    payload = _payload("AAPL", rows)
    _fake_key(monkeypatch)
    monkeypatch.setattr(bmod.BreadthAdapter, "http_get", lambda self, url, **kw: _FakeResponse(payload))
    # the boolean row is dropped as unusable, which leaves a real missing-session gap
    with pytest.raises(bmod.LicensedSourceError, match="missing"):
        _adapter().licensed_daily_window("AAPL", days[0], days[-1])


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


def test_conflicting_membership_dropped_from_every_sector_R2():
    """A symbol claimed by two sectors is unresolved identity, not a guessable
    assignment — it must be dropped from BOTH, never double-counted or picked."""
    days = _sessions(20)
    tech = [f"T{i}" for i in range(5)]
    health = [f"H{i}" for i in range(5)]
    dupe = "DUPE"
    closes = _wide(tech + health + [dupe], days, lambda t, i: 100.0 + i)
    members = pd.DataFrame({
        "symbol": tech + health + [dupe, dupe],
        "sector": ["Technology"] * 5 + ["Health Care"] * 5 + ["Technology", "Health Care"],
    })
    out = _adapter().compute_sector_participation_20(closes, members)
    last = out.iloc[-1]
    assert last["Technology|expected_20"] == 5     # DUPE excluded, not counted for Tech
    assert last["Health Care|expected_20"] == 5    # DUPE excluded, not counted for Health either


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


def test_builder_read_missing_meta_sidecar_is_unavailable(monkeypatch, tmp_path):
    """A bare parquet with no meta.json is not "available" — R4: file presence alone
    must never stand in for the metadata contract."""
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    days = _sessions(3)
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days])
    part = pd.DataFrame({"Technology|eligible_20": [5.0, 5.0, 5.0]}, index=idx)
    bdir = tmp_path / "breadth"
    bdir.mkdir(parents=True)
    part.to_parquet(bdir / "sector_participation_20.parquet")
    out = bsc.read_sector_participation_20()
    assert out["available"] is False


def _publish_fixture(monkeypatch, tmp_path, days, sectors=("Technology",), n_names=5, stale=False):
    """Dogfoods BreadthAdapter.publish_sector_participation_20 to build a real
    artifact+sidecar pair, so the builder-read tests exercise the SAME producer
    code the collector actually uses (R1/R5: integrated path, not two isolated
    halves each independently faked).

    Pins nyse_calendar.expected_last_session() to the fixture's own last day so
    "not stale" fixtures stay not-stale regardless of the real wall-clock date —
    otherwise a historical-dated fixture reads as stale the moment real "today"
    moves past it, which is exactly what happened here once real time caught up
    to the originally-hardcoded 2024 fixture dates."""
    monkeypatch.setattr(bmod.nyse_calendar, "expected_last_session", lambda: days[-1])
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days])
    cols = {}
    for sec in sectors:
        cols[f"{sec}|above_20"] = [float(n_names)] * len(idx)
        cols[f"{sec}|eligible_20"] = [float(n_names)] * len(idx)
        cols[f"{sec}|expected_20"] = [float(n_names)] * len(idx)
        cols[f"{sec}|pct_above_20"] = [100.0] * len(idx)
    result = pd.DataFrame(cols, index=idx)
    syms = [f"{sec}_{i}" for sec in sectors for i in range(n_names)]
    members = _members(syms, sector=sectors[0]) if len(sectors) == 1 else pd.DataFrame(
        {"symbol": syms, "sector": [s for s in sectors for _ in range(n_names)]})
    a = _adapter()
    path = tmp_path / "breadth" / "sector_participation_20.parquet"
    a.publish_sector_participation_20(result, {}, members, path=path)
    if stale:
        import json
        mpath = tmp_path / "breadth" / "sector_participation_20_meta.json"
        meta = json.loads(mpath.read_text())
        meta["expected_last_session"] = "2099-01-01"  # force a huge gap
        mpath.write_text(json.dumps(meta))
    return path


def test_builder_read_present_artifact_reports_metadata(monkeypatch, tmp_path):
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    days = _sessions(3)
    _publish_fixture(monkeypatch, tmp_path, days)
    out = bsc.read_sector_participation_20()
    assert out["available"] is True
    assert out["basis"] == "split_adjusted"
    assert out["window_sessions"] == 20
    assert out["as_of"] == days[-1].isoformat()
    assert out["sector_count"] == 1
    assert out["stale"] is False


def test_builder_read_present_artifact_exposes_actual_sector_rates_R1(monkeypatch, tmp_path):
    """R1: 'read_sector_participation_20() currently returns only metadata' — the
    consumer (the Money & Breadth UI) needs the actual derived rate per sector, not
    just a count of how many sectors exist."""
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    days = _sessions(3)
    _publish_fixture(monkeypatch, tmp_path, days, sectors=("Technology", "Energy"), n_names=5)
    out = bsc.read_sector_participation_20()
    assert out["available"] is True
    assert len(out["sectors"]) == 2
    by_name = {s["sector"]: s for s in out["sectors"]}
    assert by_name["Technology"]["pct_above_20"] == 100.0
    assert by_name["Technology"]["eligible_20"] == 5
    assert by_name["Technology"]["expected_20"] == 5
    assert by_name["Energy"]["pct_above_20"] == 100.0


def test_builder_read_flags_stale_artifact_R4(monkeypatch, tmp_path):
    """R4: an old artifact must not read as current merely because the file exists —
    staleness is judged against the DECLARED expected-session clock."""
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    days = _sessions(3)
    _publish_fixture(monkeypatch, tmp_path, days, stale=True)
    out = bsc.read_sector_participation_20()
    assert out["available"] is True   # data is real, just old
    assert out["stale"] is True


def test_builder_read_rejects_artifact_with_no_usable_rows_R4(monkeypatch, tmp_path):
    """A parquet that is technically nonempty but carries only all-NaN eligible
    columns must not read as available (the exact gap Sol flagged: "marks any
    nonempty parquet as available even when it only contains an eligible_20 column")."""
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    import json
    days = _sessions(3)
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days])
    part = pd.DataFrame({"Technology|eligible_20": [np.nan, np.nan, np.nan]}, index=idx)
    bdir = tmp_path / "breadth"
    bdir.mkdir(parents=True)
    part.to_parquet(bdir / "sector_participation_20.parquet")
    (bdir / "sector_participation_20_meta.json").write_text(json.dumps({
        "available": True, "basis": "split_adjusted",
        "expected_last_session": days[-1].isoformat(),
        "observed_max_session": days[-1].isoformat(),
    }))
    out = bsc.read_sector_participation_20()
    assert out["available"] is False


def test_publish_never_merges_over_a_prior_stale_result_R4(tmp_path):
    """publish_sector_participation_20 must overwrite wholesale, never combine_first
    a stale prior file into today's newly-unavailable cells."""
    a = _adapter()
    path = tmp_path / "sector_participation_20.parquet"
    days = _sessions(3)
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days])
    old = pd.DataFrame({"Technology|eligible_20": [5.0, 5.0, 5.0],
                        "Technology|pct_above_20": [80.0, 80.0, 80.0]}, index=idx)
    members = _members([f"T{i}" for i in range(5)])
    a.publish_sector_participation_20(old, {}, members, path=path)
    assert path.exists()
    # today's run produced NO usable result — publish must remove the stale file,
    # never leave old numbers looking current
    a.publish_sector_participation_20(None, {"T0": "boom"}, members, path=path)
    assert not path.exists()
    import json
    meta = json.loads((path.parent / "sector_participation_20_meta.json").read_text())
    assert meta["available"] is False


def test_builder_read_never_raises_on_corrupt_artifact(monkeypatch, tmp_path):
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    import json
    bdir = tmp_path / "breadth"
    bdir.mkdir(parents=True)
    (bdir / "sector_participation_20.parquet").write_bytes(b"not a parquet file")
    (bdir / "sector_participation_20_meta.json").write_text(json.dumps({"available": True}))
    out = bsc.read_sector_participation_20()  # must never raise — additive, fail-soft
    assert out["available"] is False


def test_builder_read_never_raises_on_corrupt_meta_json(monkeypatch, tmp_path):
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
    days = _sessions(3)
    _publish_fixture(monkeypatch, tmp_path, days)
    (tmp_path / "breadth" / "sector_participation_20_meta.json").write_text("{not json")
    out = bsc.read_sector_participation_20()
    assert out["available"] is False


# --------------------------------------------------------------------------- #
# R1/R5 (Sol 1789096018.269229): the connected producer->consumer path, tested
# with injected fetch stubs — never a real network call, never wired into
# fetch(). Exercises fetch_sector_participation_20 -> compute_... -> publish...
# -> the builder's read, end to end.
# --------------------------------------------------------------------------- #

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


def test_fetch_sector_participation_20_all_tickers_fail_returns_none_not_crash():
    members = _members(["ONLY"])

    def always_fails(ticker, start, end):
        raise bmod.LicensedSourceError("no key")

    result, failures = _adapter().fetch_sector_participation_20(
        members, fetch_one=always_fails)
    assert result is None
    assert failures == {"ONLY": "no key"}


def test_fetch_sector_participation_20_never_calls_network(monkeypatch):
    """The orchestrating function must make zero real HTTP calls in this suite —
    every path here is exercised through an injected fetch_one."""
    def _forbidden_get(*a, **kw):
        raise AssertionError("fetch_sector_participation_20 touched the network directly")
    monkeypatch.setattr("requests.get", _forbidden_get)
    members = _members(["ONLY"])
    result, failures = _adapter().fetch_sector_participation_20(
        members, fetch_one=lambda t, s, e: (_ for _ in ()).throw(bmod.LicensedSourceError("x")))
    assert result is None


def test_integrated_publish_and_builder_read_round_trip(monkeypatch, tmp_path):
    """The full connected path: fetch -> compute -> publish -> builder read, with a
    real (fake-HTTP) licensed_daily_window underneath — the integration R5 asks for,
    not two halves each independently unit-tested."""
    from scripts import build_sector_central as bsc
    monkeypatch.setattr(bsc.config, "data_dir", lambda: tmp_path)
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

    out = bsc.read_sector_participation_20()
    assert out["available"] is True
    assert out["as_of"] == days[-1].isoformat()
    assert out["fetch_failure_count"] == 0
    assert out["stale"] is False
