"""The off-render yahoo universe backfill (scripts/backfill_yahoo_universe.py).

WHY THIS SUITE EXISTS — a SECOND writer into data/yahoo is a silent-poison seam.
Every hub grader prices names from data/yahoo/<T>.parquet and reads ``close``
directly off the parquet (engine/trajectory.py:66, engine/desk_grader.py:124).
``close`` is total-return (split+dividend) adjusted and ``close_price`` is
split-only, so a backfilled frame that swaps the two, drops one, reorders the
columns, or lands a tz-aware index READS AS COVERAGE and grades wrong — no
exception, no red, just a wrong number on a scorecard. Hence a schema gate with
teeth and a suite that pins them.

Pins (all network-free — the download layer is stubbed):
1. SCHEMA PARITY (the hard gate): the parquet a backfill writes is byte-identical
   to the one the collector's own path writes from the same response, carries
   ``collectors.yahoo.STORE_COLUMNS`` in order, float prices, a tz-naive sorted
   DatetimeIndex named Date — and matches the LIVE collector-produced store
   (data/yahoo/SPY.parquet) on all of it.
2. The gate REFUSES and never writes: wrong columns, wrong order, non-float
   prices, tz-aware index, unsorted/duplicate index, NaN or non-positive close.
3. Adjustment-ratio sanity: constant close/close_price SEGMENTS are the dividend
   adjustment WORKING and must not be flagged; a per-bar-varying ratio, a ratio
   above 1.0, and a tip off 1.0 are named — and none of them parks a name.
4. Priority order (current surface -> ledger-recent -> rest), unsupported symbols
   excluded, already-stored tickers excluded.
5. Cap + budget bound one run; the next run resumes where it stopped and never
   re-fetches a name that already has a parquet.
6. Three failed fetches park a name as ``fetch_failed`` — with NO death or
   delisting claim anywhere in the state file, and without touching
   lib/delisted_symbols.
7. The run annotation is a BARE line-start print (a logger-prefixed annotation is
   silently dropped by GitHub Actions).
8. Refreshes probe a short overlap window, preserve deep history when the basis is
   stable, and escalate to period='max' on a true basis shift or no-overlap. A
   failed full-history heal leaves the prior archive byte-identical.
9. An adjustment-basis comparison that could not be MADE is UNKNOWN, not proven
   stable: it escalates to the same full-history heal, never to a short splice,
   and the legacy boolean guard keeps its documented default for other callers.
10. An adjustment-basis comparison that produced an UNUSABLE row — a non-finite
    close on either side, which the schema gate does not reject — cannot
    certify a stable overlap either: the answer is UNKNOWN, the refresh
    escalates to the full-history heal, a failed or invalid heal leaves the
    prior parquet byte-identical, and the legacy boolean guard keeps its
    documented default.
11. The strict comparison decides on the ORIGINAL common-date evidence: a
    stored row that is missing (NaN) or non-finite (+/-inf) on a common date
    is evidence that could not be compared, so it is UNKNOWN rather than a
    stable basis certified from the usable remainder — and an infinite stored
    value is unusable evidence, not a proven shift. The legacy boolean keeps
    its dropna() rule and its documented answers.

Run: TZ=UTC .venv/bin/python -m pytest tests/test_yahoo_universe_backfill.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import yahoo as yahoo_mod  # noqa: E402
from lib import config, store  # noqa: E402
from scripts import backfill_yahoo_universe as bf  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

YF_FIELDS = ("Open", "High", "Low", "Close", "Adj Close", "Volume")


# ---------------------------------------------------------------------------
# fixtures / builders
# ---------------------------------------------------------------------------
def _bars(n: int, start: str = "2024-01-01", base: float = 100.0,
          div_steps: tuple[int, ...] = (), volume_int: bool = False) -> pd.DataFrame:
    """One symbol's yfinance-shaped bars.

    ``div_steps`` are row positions of ex-dividend dates: Adj Close is discounted
    by 1% for every dividend at or after the bar, which is exactly the shape
    yfinance serves — a ratio that is CONSTANT between dividends and 1.0 at the
    tip."""
    idx = pd.bdate_range(start, periods=n, name="Date")
    close = pd.Series(base + np.arange(n) * 0.1, index=idx)
    factor = np.ones(n)
    for pos in div_steps:
        factor[:pos] *= 0.99
    adj = close * factor
    vol = pd.Series(np.arange(1_000_000, 1_000_000 + n), index=idx)
    return pd.DataFrame({
        "Open": close - 0.5, "High": close + 0.5, "Low": close - 1.0,
        "Close": close, "Adj Close": adj,
        "Volume": vol.astype("int64" if volume_int else "float64"),
    }, index=idx)


def _yf_response(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """A ``yf.download(..., group_by='ticker')`` response: MultiIndex (symbol, field),
    union index, NaN-padded — the exact shape measured live on 2026-08-08."""
    out = {}
    for sym, f in frames.items():
        for field in YF_FIELDS:
            out[(sym, field)] = f[field]
    df = pd.DataFrame(out)
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["Ticker", "Price"])
    df.index.name = "Date"
    return df.sort_index()


@pytest.fixture()
def tree(tmp_path, monkeypatch):
    """An isolated repo-shaped tree: data/ + site/ with a hub ledger and hub.json."""
    data = tmp_path / "data"
    site = tmp_path / "site"
    (data / "yahoo").mkdir(parents=True)
    (data / "hub").mkdir(parents=True)
    (site / "intel_hub").mkdir(parents=True)
    monkeypatch.setattr(config, "data_dir", lambda: data)
    monkeypatch.setattr(config, "site_dir", lambda: site)
    return tmp_path


def _write_ledger(tree, rows: list[tuple[str, str]]) -> None:
    p = tree / "data" / "hub" / "signal_snapshots.jsonl"
    with open(p, "w") as f:
        for date_, ticker in rows:
            f.write(json.dumps({"date": date_, "t": ticker, "opp": 50.0,
                                "edge": 0.5, "stage": "early", "lean": 1}) + "\n")


def _write_hub(tree, **lists) -> None:
    payload = {k: [{"ticker": t} for t in v] for k, v in lists.items()}
    with open(tree / "site" / "intel_hub" / "hub.json", "w") as f:
        json.dump(payload, f)


def _stub_download(monkeypatch, responses, calls=None):
    """Replace the network leg. ``responses`` maps a frozenset of requested symbols
    to a response frame, an Exception to raise, or None (empty response)."""
    def fake(symbols, period):
        key = frozenset(symbols)
        if calls is not None:
            calls.append(sorted(symbols))
        out = responses.get(key, responses.get("*"))
        if isinstance(out, Exception):
            raise out
        return out
    monkeypatch.setattr(bf, "download_batch", fake)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)


# ---------------------------------------------------------------------------
# 1. schema parity — the hard gate
# ---------------------------------------------------------------------------
def test_backfilled_parquet_is_identical_to_the_collector_write(tree, monkeypatch):
    """Same response in, same parquet out — the backfill post-processes NOTHING.

    Both paths share ``extract_store_frame``, so this does not re-test the rename;
    what it pins is that the backfill adds no rounding, cast, reindex, reorder or
    tz step of its own on the way to disk. Any such step would show up here as a
    frame difference, and nowhere else until a grader printed a wrong number."""
    resp = _yf_response({"AAA": _bars(300, div_steps=(100, 200))})
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {frozenset({"AAA"}): resp})

    bf.run(cap=5, batch_size=5, sleep_s=0, period="max")
    written = pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet")

    adapter = yahoo_mod.YahooAdapter()
    ref = adapter.validate("AAA", adapter._extract(resp, "AAA", set(), []))
    store.upsert("yahoo", "COLLECTOR_REF", ref)
    collector = pd.read_parquet(tree / "data" / "yahoo" / "COLLECTOR_REF.parquet")

    pd.testing.assert_frame_equal(written, collector)


def test_backfilled_parquet_carries_the_pinned_store_schema(tree, monkeypatch):
    resp = _yf_response({"AAA": _bars(300, div_steps=(150,))})
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {frozenset({"AAA"}): resp})

    bf.run(cap=5, batch_size=5, sleep_s=0)
    df = pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet")

    assert tuple(df.columns) == yahoo_mod.STORE_COLUMNS == ("close_price", "close", "volume")
    assert df["close"].dtype.kind == "f" and df["close_price"].dtype.kind == "f"
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is None
    assert df.index.name == "Date"
    assert df.index.is_monotonic_increasing and not df.index.has_duplicates
    # `close` is the TOTAL-RETURN basis: dividend-discounted history sits BELOW
    # the split-only close. Swapping the two columns would pass every structural
    # assertion above and silently invert every grader's excess return.
    assert (df["close"] <= df["close_price"] + 1e-9).all()
    assert df["close"].iloc[-1] == pytest.approx(df["close_price"].iloc[-1])


def test_int64_volume_from_the_vendor_is_accepted_not_rejected(tree, monkeypatch):
    """yfinance serves int64 Volume for a homogeneous batch and float64 once
    NaN-padding kicks in; the collector's OWN store carries both (measured
    2026-08-08: 667 files float64, 74 int64, BRK.B among the int64 ones). A gate
    that demanded float would park real names over a vendor detail."""
    resp = _yf_response({"AAA": _bars(120, volume_int=True)})
    # single-symbol response: no NaN padding, so Volume stays int64
    flat = resp["AAA"].dropna(how="all")
    assert flat["Volume"].dtype.kind == "i"
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {frozenset({"AAA"}): resp})

    rep = bf.run(cap=5, batch_size=5, sleep_s=0)
    assert rep["written"] == 1 and rep["schema_rejected"] == 0
    df = pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet")
    assert df["volume"].dtype.kind in "iu"


def test_schema_matches_the_live_collector_store():
    """Cross-check the pinned schema against a parquet the NIGHTLY COLLECTOR wrote.

    Schema only — columns, dtypes, index type/tz/name. Deliberately not values or
    dates: this file is refreshed every night, and a test that asserted about its
    contents would be asserting about today."""
    p = REPO / "data" / "yahoo" / "SPY.parquet"
    if not p.exists():
        pytest.skip("data/yahoo/SPY.parquet not in this checkout")
    spy = pd.read_parquet(p)
    assert tuple(spy.columns) == yahoo_mod.STORE_COLUMNS
    assert spy["close"].dtype.kind == "f" and spy["close_price"].dtype.kind == "f"
    assert spy["volume"].dtype.kind in "fiu"
    assert isinstance(spy.index, pd.DatetimeIndex)
    assert spy.index.tz is None and spy.index.name == "Date"
    assert bf.schema_violation(spy) is None


# ---------------------------------------------------------------------------
# 2. the gate refuses
# ---------------------------------------------------------------------------
def _good_frame() -> pd.DataFrame:
    b = _bars(120, div_steps=(60,))
    return pd.DataFrame({"close_price": b["Close"], "close": b["Adj Close"],
                         "volume": b["Volume"].astype(float)}, index=b.index)


@pytest.mark.parametrize("mutate,expect", [
    (lambda d: d.drop(columns=["close_price"]), "columns"),
    (lambda d: d[["close", "close_price", "volume"]], "columns"),
    (lambda d: d.assign(extra=1.0), "columns"),
    (lambda d: d.assign(close=d["close"].astype(str)), "non-float price"),
    (lambda d: d.set_index(d.index.tz_localize("America/New_York")), "tz-aware"),
    (lambda d: d.iloc[::-1], "not sorted"),
    (lambda d: pd.concat([d, d.iloc[[0]]]).sort_index(), "duplicate index"),
    (lambda d: d.assign(close=d["close"].mask(d.index == d.index[5])), "NaN in close"),
    (lambda d: d.assign(close=d["close"] * -1), "non-positive close"),
    (lambda d: d.iloc[:1], "row(s)"),
    (lambda d: d.iloc[:0], "empty"),
])
def test_schema_gate_refuses_every_divergence(mutate, expect):
    good = _good_frame()
    assert bf.schema_violation(good) is None
    bad = mutate(good.copy())
    reason = bf.schema_violation(bad)
    assert reason is not None and expect in reason, f"{expect!r} not in {reason!r}"


def test_a_refused_frame_is_never_written_and_is_charged_an_attempt(tree, monkeypatch, capsys):
    """The gate's TEETH, not just its verdict: a bad frame leaves NO parquet.

    Drives the real run loop with an extractor that returns a schema-violating
    frame — the one shape that would otherwise reach disk looking like coverage."""
    resp = _yf_response({"AAA": _bars(120)})
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {frozenset({"AAA"}): resp})
    monkeypatch.setattr(bf, "extract_store_frame",
                        lambda sub, t, **kw: _good_frame().drop(columns=["close_price"]))

    rep = bf.run(cap=5, batch_size=5, sleep_s=0)

    assert rep["schema_rejected"] == 1 and rep["written"] == 0
    assert not (tree / "data" / "yahoo" / "AAA.parquet").exists()
    state = json.loads((tree / "data" / bf.STATE_FILE).read_text())
    assert state["pending"]["AAA"]["attempts"] == 1
    assert "schema gate" in state["pending"]["AAA"]["error"]
    warn = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("::warning title=yahoo-backfill-schema")]
    assert warn, "a refused frame must raise a line-start ::warning"


# ---------------------------------------------------------------------------
# 3. adjustment-ratio sanity (soft)
# ---------------------------------------------------------------------------
def test_constant_ratio_segments_are_the_dividend_adjustment_not_an_anomaly():
    """close/close_price steps at each ex-dividend date and is FLAT between them.
    That is the feature. Flagging it would be flagging the dual-basis store."""
    frame = _good_frame()
    ratio = frame["close"] / frame["close_price"]
    rel = (ratio.diff() / ratio.shift()).dropna().abs()
    # exactly one real step (the ex-dividend date); everything else is float noise
    assert int((rel > bf.RATIO_TOL).sum()) == 1
    rep = bf.ratio_report(frame)
    assert rep["anomalies"] == []
    assert rep["tip_ratio"] == pytest.approx(1.0)
    assert rep["step_fraction"] < bf.RATIO_STEP_FRACTION_MAX


def test_a_no_dividend_name_has_a_flat_unit_ratio_and_no_anomaly():
    frame = _good_frame()
    frame["close"] = frame["close_price"]
    rep = bf.ratio_report(frame)
    assert rep["anomalies"] == [] and rep["step_fraction"] == 0.0


def test_ratio_report_names_a_per_bar_varying_ratio():
    """The two bases are supposed to be TR and split-only, which differ only at
    ex-dividend dates. A ratio that moves on every bar is not that."""
    frame = _good_frame()
    rng = np.random.default_rng(7)
    frame["close"] = frame["close_price"] * (1 - rng.uniform(0.01, 0.05, len(frame)))
    rep = bf.ratio_report(frame)
    assert any("of bars step" in a for a in rep["anomalies"])


def test_ratio_report_names_a_ratio_above_one_and_a_tip_off_one():
    frame = _good_frame()
    frame["close"] = frame["close_price"] * 1.01
    rep = bf.ratio_report(frame)
    assert any("> 1.0" in a for a in rep["anomalies"])
    assert any("!= 1.0" in a for a in rep["anomalies"])


def test_a_ratio_anomaly_annotates_but_still_writes_the_name(tree, monkeypatch, capsys):
    """Soft by design. Measured: stored IBIT breaks the <=1 and tip rules (1.002385)
    in the collector's own store, and a full re-pull returns exactly 1.0 — the
    anomaly was a stale-basis store artifact the refresh phase repairs, not a
    property of the security. Parking on it would trade real coverage for
    something already fixable, in a column no grader reads."""
    b = _bars(120)
    b["Adj Close"] = b["Close"] * 1.01          # TR above split-only, tip off 1.0
    resp = _yf_response({"AAA": b})
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {frozenset({"AAA"}): resp})

    rep = bf.run(cap=5, batch_size=5, sleep_s=0)

    assert rep["written"] == 1 and rep["ratio_anomalies"] == 1 and rep["parked"] == 0
    assert (tree / "data" / "yahoo" / "AAA.parquet").exists()
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln.startswith("::warning title=yahoo-backfill-basis")]
    assert lines and "AAA" in lines[0]


# ---------------------------------------------------------------------------
# 4. the needed set + priority order
# ---------------------------------------------------------------------------
def test_priority_order_current_surface_then_recent_then_rest(tree):
    _write_ledger(tree, [
        ("2026-08-01", "CURRENT"), ("2026-08-01", "RECENT"),
        ("2026-01-05", "OLD"), ("2026-08-01", "HAVE"),
    ])
    _write_hub(tree, command=["CURRENT"], emerging=[], discovery=[])
    store.upsert("yahoo", "HAVE", _good_frame())

    queue, census = needed = bf.needed_queue({}, today=pd.Timestamp("2026-08-08").date())
    order = [t for t, _ in queue]

    assert order == ["CURRENT", "RECENT", "OLD"], order
    assert dict(queue) == {"CURRENT": 1, "RECENT": 2, "OLD": 3}
    assert "HAVE" not in order, "a ticker with a parquet is already covered"
    assert census["already_stored"] == 1 and census["missing"] == 3
    assert needed[1]["bucket_1_current"] == 1


def test_hub_only_names_join_the_needed_set(tree):
    """A name on tonight's board that the ledger has not written yet still needs a
    price series — the union is ledger OR hub, not ledger AND hub."""
    _write_ledger(tree, [("2026-08-01", "LEDGONLY")])
    _write_hub(tree, command=["HUBONLY"], discovery=["DISC"], exhausted=["EXH"])
    queue, census = bf.needed_queue({}, today=pd.Timestamp("2026-08-08").date())
    buckets = dict(queue)
    assert buckets["HUBONLY"] == 1 and buckets["DISC"] == 1
    # exhausted/catalysts are universe members but not the CURRENT surface
    assert buckets["EXH"] == 3 and buckets["LEDGONLY"] == 2
    assert census["hub_current_surface"] == 2


def test_unsupported_symbols_never_enter_the_queue(tree):
    """The ledger carries China/HK numeric board codes and parse artifacts
    (measured 886 of the 7,108 missing on 2026-08-08). Asking Yahoo for them
    spends nightly budget to learn nothing — and their exclusion is a statement
    about THIS lane's reach, never about the security."""
    _write_ledger(tree, [("2026-08-01", t) for t in
                         ("GOOD", "000100", "N/A", "()", "ASX:PEX", "IT:ETH")])
    _write_hub(tree)
    queue, census = bf.needed_queue({}, today=pd.Timestamp("2026-08-08").date())
    assert [t for t, _ in queue] == ["GOOD"]
    assert census["unsupported_symbols"] == 5
    for bad in ("000100", "N/A", "()", "ASX:PEX", "IT:ETH"):
        assert not bf.addressable(bad)
    for ok in ("GOOD", "BRK.B", "AAC-UN", "A"):
        assert bf.addressable(ok)


def test_retries_trail_never_asked_names_inside_a_bucket(tree):
    _write_ledger(tree, [("2026-08-01", "AAA"), ("2026-08-01", "BBB")])
    _write_hub(tree)
    state = {"pending": {"AAA": {"attempts": 2}}}
    queue, _ = bf.needed_queue(state, today=pd.Timestamp("2026-08-08").date())
    assert [t for t, _ in queue] == ["BBB", "AAA"]


def test_class_share_dots_become_dashes_for_the_vendor():
    """Yahoo serves US class shares with a dash (BRK.B -> BRK-B). Verified live on
    BRK.B: 7,610 bars from 1996-05-09, Berkshire class B's first session. This is
    punctuation, NOT a rename, so it does not belong in lib/ticker_aliases —
    every entry there must be justified by a live pull of a genuine vendor
    disagreement."""
    assert bf.vendor_symbol("BRK.B") == "BRK-B"
    assert bf.vendor_symbol("BF.B") == "BF-B"
    assert bf.vendor_symbol("AAPL") == "AAPL"
    assert bf.vendor_symbol("AAC-UN") == "AAC-UN"
    # the alias table still wins — it encodes real renames
    assert bf.vendor_symbol("MMC") == "MRSH"


def test_the_store_key_is_the_ledger_ticker_not_the_vendor_symbol(tree, monkeypatch):
    """Fetch under the vendor symbol, STORE under the ledger ticker: the ledger
    key is the join key every grader and page uses."""
    resp = _yf_response({"BRK-B": _bars(200)})
    _write_ledger(tree, [("2026-08-01", "BRK.B")])
    _write_hub(tree, command=["BRK.B"])
    calls: list[list[str]] = []
    _stub_download(monkeypatch, {frozenset({"BRK-B"}): resp}, calls=calls)

    rep = bf.run(cap=5, batch_size=5, sleep_s=0)

    assert calls == [["BRK-B"]]
    assert rep["written"] == 1
    assert (tree / "data" / "yahoo" / "BRK.B.parquet").exists()
    assert not (tree / "data" / "yahoo" / "BRK-B.parquet").exists()


# ---------------------------------------------------------------------------
# 5. cap, budget, resumability
# ---------------------------------------------------------------------------
def test_cap_bounds_the_run_and_the_next_run_resumes(tree, monkeypatch):
    names = [f"T{i:02d}" for i in range(10)]
    _write_ledger(tree, [("2026-08-01", t) for t in names])
    _write_hub(tree)
    responses = {frozenset(names[i:i + 3]): _yf_response(
        {t: _bars(120) for t in names[i:i + 3]}) for i in range(0, 10, 3)}
    responses[frozenset(names[9:])] = _yf_response({names[9]: _bars(120)})
    calls: list[list[str]] = []
    _stub_download(monkeypatch, responses, calls=calls)

    first = bf.run(cap=3, batch_size=3, sleep_s=0)
    assert first["planned"] == 3 and first["written"] == 3
    assert first["remaining"] == 7
    assert sorted(p.stem for p in (tree / "data" / "yahoo").glob("*.parquet")) == names[:3]

    second = bf.run(cap=3, batch_size=3, sleep_s=0)
    assert second["written"] == 3
    assert sorted(p.stem for p in (tree / "data" / "yahoo").glob("*.parquet")) == names[:6]
    # never re-requested a name that already has a parquet
    assert calls == [names[0:3], names[3:6]]

    state = json.loads((tree / "data" / bf.STATE_FILE).read_text())
    assert sorted(state["done"]) == names[:6]
    assert state["done"]["T00"]["rows"] == 120


def test_resumability_survives_a_deleted_state_file(tree, monkeypatch):
    """The needed set comes from DISK, so the state file is provenance, not
    correctness: deleting it must not re-fetch what is already stored."""
    names = ["AAA", "BBB"]
    _write_ledger(tree, [("2026-08-01", t) for t in names])
    _write_hub(tree)
    calls: list[list[str]] = []
    _stub_download(monkeypatch, {"*": _yf_response({t: _bars(120) for t in names})},
                   calls=calls)

    bf.run(cap=1, batch_size=1, sleep_s=0)
    (tree / "data" / bf.STATE_FILE).unlink()
    bf.run(cap=1, batch_size=1, sleep_s=0)

    assert calls == [["AAA"], ["BBB"]]


def test_a_corrupt_state_file_warns_and_starts_clean(tree, monkeypatch, capsys):
    (tree / "data" / bf.STATE_FILE).write_text("{not json")
    state = bf.load_state()
    assert state["done"] == {} and state["parked"] == {}
    out = capsys.readouterr().out
    assert any(ln.startswith("::warning title=yahoo-backfill::state file unreadable")
               for ln in out.splitlines())


def test_wall_clock_budget_stops_the_run_between_batches(tree, monkeypatch):
    names = [f"T{i:02d}" for i in range(6)]
    _write_ledger(tree, [("2026-08-01", t) for t in names])
    _write_hub(tree)
    _stub_download(monkeypatch, {"*": _yf_response({t: _bars(120) for t in names})})
    clock = iter([0.0, 0.0, 999.0])   # t0, batch-1 gate (pass), batch-2 gate (over)
    monkeypatch.setattr(bf.time, "monotonic", lambda: next(clock, 999.0))

    rep = bf.run(cap=6, batch_size=2, sleep_s=0, budget_s=10.0)

    assert rep["budget_exhausted"] is True
    assert rep["attempted"] == 2 and rep["planned"] == 6


def test_a_batch_transport_failure_charges_nobody_an_attempt(tree, monkeypatch):
    """A network blip is not evidence about a symbol. Charging the batch would let
    three bad nights park perfectly good names."""
    _write_ledger(tree, [("2026-08-01", "AAA"), ("2026-08-01", "BBB")])
    _write_hub(tree)
    _stub_download(monkeypatch, {"*": RuntimeError("connection reset")})

    rep = bf.run(cap=2, batch_size=2, sleep_s=0)

    assert rep["batch_errors"] == 1 and rep["attempted"] == 0 and rep["parked"] == 0
    state = json.loads((tree / "data" / bf.STATE_FILE).read_text())
    assert state["pending"] == {} and state["parked"] == {}


# ---------------------------------------------------------------------------
# 6. parking is never a death claim
# ---------------------------------------------------------------------------
def test_three_no_data_runs_park_the_name_as_fetch_failed(tree, monkeypatch):
    _write_ledger(tree, [("2026-08-01", "GHOST")])
    _write_hub(tree)
    _stub_download(monkeypatch, {"*": None})     # empty response = no data for the symbol

    for expected in (1, 2, 3):
        rep = bf.run(cap=1, batch_size=1, sleep_s=0, max_attempts=3)
        state = json.loads((tree / "data" / bf.STATE_FILE).read_text())
        if expected < 3:
            assert state["pending"]["GHOST"]["attempts"] == expected
            assert "GHOST" not in state["parked"]
            assert rep["parked"] == 0
        else:
            assert rep["parked"] == 1
            assert "GHOST" not in state.get("pending", {})

    parked = state["parked"]["GHOST"]
    assert parked["reason"] == "fetch_failed" and parked["attempts"] == 3
    assert "GHOST" in parked["error"] or "no data" in parked["error"]

    # A park is a statement about a REQUEST. Nothing in the record may claim the
    # security stopped existing — index exit, a rename nobody told us about, and a
    # non-US listing all 404 identically from here. Swept over every field EXCEPT
    # `note`, which is the disclosure itself and must carry the negation.
    lifecycle = ("delist", "dead", "died", "death", "defunct", "expired", "zombie")
    scrubbed = dict(parked)
    note = scrubbed.pop("note")
    blob = json.dumps({**state, "parked": {"GHOST": scrubbed}}).lower()
    for word in lifecycle:
        assert word not in blob, f"{word!r} in the state record"
    assert "not a delisting or death claim" in note.lower()

    # and the run stops asking once it is parked
    calls: list[list[str]] = []
    _stub_download(monkeypatch, {"*": None}, calls=calls)
    rep = bf.run(cap=1, batch_size=1, sleep_s=0, max_attempts=3)
    assert calls == [] and rep["planned"] == 0


def test_parking_never_writes_the_delisted_ledger(tree, monkeypatch):
    from lib import delisted_symbols
    before = set(delisted_symbols.tickers())
    _write_ledger(tree, [("2026-08-01", "GHOST")])
    _write_hub(tree)
    _stub_download(monkeypatch, {"*": None})
    for _ in range(3):
        bf.run(cap=1, batch_size=1, sleep_s=0, max_attempts=3)
    assert set(delisted_symbols.tickers()) == before


def test_a_park_keeps_every_row_the_name_already_had(tree, monkeypatch):
    """Parking removes a name from the FETCH QUEUE and nothing else."""
    store.upsert("yahoo", "AAA", _good_frame())
    rows = len(pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet"))
    _write_ledger(tree, [("2026-08-01", "AAA"), ("2026-08-01", "GHOST")])
    _write_hub(tree)
    _stub_download(monkeypatch, {"*": None})
    for _ in range(3):
        bf.run(cap=5, batch_size=5, sleep_s=0, max_attempts=3)
    assert len(pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet")) == rows


# ---------------------------------------------------------------------------
# 7. the annotation
# ---------------------------------------------------------------------------
def test_run_notice_is_a_bare_line_start_print(tree, monkeypatch, capsys):
    """A logger-prefixed annotation is silently DROPPED by GitHub Actions — the
    call reviews as an alarm, runs clean, and produces nothing in the summary.
    So the line must START the line (see tests/test_gh_annotation_line_start.py)."""
    _write_ledger(tree, [("2026-08-01", "AAA"), ("2026-08-01", "BBB")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {"*": _yf_response({"AAA": _bars(120)})})

    rep = bf.run(cap=1, batch_size=1, sleep_s=0)

    notices = [ln for ln in capsys.readouterr().out.splitlines()
               if ln.startswith("::notice title=yahoo-backfill::")]
    assert len(notices) == 1, notices
    assert notices[0] == (f"::notice title=yahoo-backfill::backfilled {rep['written']}, "
                          f"parked {rep['parked']}, remaining {rep['remaining']}")


def test_dry_run_touches_no_network_and_writes_nothing(tree, monkeypatch, capsys):
    _write_ledger(tree, [("2026-08-01", "AAA"), ("2026-08-01", "BBB")])
    _write_hub(tree, command=["AAA"])

    def explode(*_a, **_k):
        raise AssertionError("--dry-run must not touch the network")
    monkeypatch.setattr(bf, "download_batch", explode)

    rep = bf.run(cap=5, batch_size=5, sleep_s=0, dry_run=True)

    assert rep["written"] == 0 and rep["remaining"] == 2
    assert rep["plan_sample"] == ["AAA", "BBB"]
    assert list((tree / "data" / "yahoo").glob("*.parquet")) == []
    assert not (tree / "data" / bf.STATE_FILE).exists()
    assert any(ln.startswith("::notice title=yahoo-backfill::")
               for ln in capsys.readouterr().out.splitlines())


# ---------------------------------------------------------------------------
# 8. the post-drain refresh phase
# ---------------------------------------------------------------------------
def _no_maintained(monkeypatch, keep: set[str] | None = None):
    """Pretend the collector maintains nothing (or only `keep`), so the test's own
    parquets are the refresh candidates."""
    monkeypatch.setattr(bf, "maintained_stems", lambda: set(keep or ()))


def test_refresh_only_starts_once_the_backfill_queue_under_fills_the_cap(tree, monkeypatch):
    """During the ~16 drain nights the refresh must not compete for the budget."""
    names = ["AAA", "BBB", "CCC"]
    _write_ledger(tree, [("2026-08-01", t) for t in names])
    _write_hub(tree)
    _no_maintained(monkeypatch)
    _stub_download(monkeypatch, {"*": _yf_response({t: _bars(120) for t in names})})

    # cap == queue length -> queue fills the cap -> no refresh
    full = bf.run(cap=3, batch_size=3, sleep_s=0)
    assert full["refresh_ran"] is False and full["refreshed"] == 0
    assert full["written"] == 3

    # queue now empty -> the refresh phase owns the run
    drained = bf.run(cap=3, batch_size=3, sleep_s=0)
    assert drained["planned"] == 0
    assert drained["refresh_ran"] is True
    assert drained["refreshed"] == 3
    assert drained["refreshable"] == 3


def test_refresh_takes_the_oldest_tip_first(tree, monkeypatch):
    tips = {"OLD": "2020-01-01", "MID": "2024-01-01", "NEW": "2026-01-01"}
    for t, tip in tips.items():
        store.upsert("yahoo", t, _good_frame())
    state = {"done": {t: {"last_obs": tip} for t, tip in tips.items()}}
    _no_maintained(monkeypatch)
    order, n = bf.refresh_candidates(state)
    assert order == ["OLD", "MID", "NEW"] and n == 3


def test_refresh_skips_collector_maintained_and_parked_names(tree, monkeypatch):
    """A series the nightly collector owns must never be touched here, and a parked
    name must not be retried forever."""
    for t in ("MINE", "THEIRS", "PARKED"):
        store.upsert("yahoo", t, _good_frame())
    _no_maintained(monkeypatch, keep={"THEIRS"})
    state = {"done": {}, "parked": {"PARKED": {"reason": "refresh_failed"}}}
    order, n = bf.refresh_candidates(state)
    assert order == ["MINE"] and n == 1


def test_maintained_stems_compares_sanitized_store_names(monkeypatch):
    """The collector maintains CL=F / ^GSPC; their files are CL_F / _GSPC. Comparing
    a directory stem against the raw config ticker misses every one of them —
    measured 2026-08-08, a naive compare called 38 collector-maintained FX and
    commodity series 'non-maintained', which would have had this phase re-pulling
    them nightly under a symbol yfinance 404s and parking all 38."""
    assert bf.store_stem("CL=F") == "CL_F"
    assert bf.store_stem("^GSPC") == "_GSPC"
    assert bf.store_stem("BRK.B") == "BRK.B"

    class _Fake:
        def maintained_tickers(self):
            return ["CL=F", "^GSPC", "AAPL"]
    monkeypatch.setattr(bf, "YahooAdapter", _Fake)
    assert bf.maintained_stems() == {"CL_F", "_GSPC", "AAPL"}


def test_an_unresolvable_maintained_set_skips_the_refresh_rather_than_refreshing_all(
        tree, monkeypatch):
    """Fail CLOSED. An empty set would read as 'nothing is maintained', making every
    parquet a candidate — the one direction that trespasses on the collector."""
    store.upsert("yahoo", "AAA", _good_frame())

    class _Boom:
        def maintained_tickers(self):
            raise RuntimeError("config unreadable")
    monkeypatch.setattr(bf, "YahooAdapter", _Boom)
    assert bf.maintained_stems() is None
    assert bf.refresh_candidates({"done": {}}) == ([], 0)


@pytest.mark.parametrize("n,expect_cap,expect_cadence", [
    (0, 0, 0.0),
    (60, 400, 0.1),        # tiny store -> the cap floor; cadence floors at 0.1d
    (2400, 400, 6.0),      # exactly the floor's break-even
    (4500, 750, 6.0),      # expected steady state
    (6222, 1037, 6.0),     # whole addressable set
    (12000, 1500, 8.0),    # past the ceiling -> cadence degrades, and is REPORTED
])
def test_refresh_cadence_math(n, expect_cap, expect_cadence):
    cap = bf.refresh_cap_for(n)
    assert cap == expect_cap
    assert bf.cadence_days(n, cap) == pytest.approx(expect_cadence, abs=0.05)


def test_cadence_target_stays_under_the_house_bar_lag_bound():
    """The 7d number is not ours: engine/name_score_grader.py:96
    _MAX_BAR_LAG_DAYS = 7 (mirrored by collectors/yahoo.py _STALE_CAL_DAYS). Past it
    a name's last bar reads as a dead feed, so a refresh that lands slower than that
    buys nothing. Pinned so a future cap tweak cannot quietly cross it."""
    from engine import name_score_grader as NSG
    assert bf.REFRESH_TARGET_CADENCE_D < NSG._MAX_BAR_LAG_DAYS
    # and the clamp ceiling must be able to HOLD the target for the real universe
    assert bf.cadence_days(6222, bf.refresh_cap_for(6222)) <= bf.REFRESH_TARGET_CADENCE_D


def test_a_parked_refresh_leaves_the_existing_parquet_intact(tree, monkeypatch):
    """stale-but-present beats absent. A refresh that cannot re-pull must not delete,
    truncate or invalidate what is already on disk — the ~7d bound reports the
    staleness honestly instead."""
    store.upsert("yahoo", "AAA", _good_frame())
    # disk-to-disk: the in-memory upsert return carries an index `freq` the parquet
    # round-trip drops, which is an artifact of the comparison, not of the lane.
    before = pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet")
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)
    _stub_download(monkeypatch, {"*": None})

    for _ in range(3):
        rep = bf.run(cap=5, batch_size=5, sleep_s=0, max_attempts=3)

    after = pd.read_parquet(tree / "data" / "yahoo" / "AAA.parquet")
    pd.testing.assert_frame_equal(after, before)
    state = json.loads((tree / "data" / bf.STATE_FILE).read_text())
    parked = state["parked"]["AAA"]
    assert parked["reason"] == "refresh_failed"
    assert "KEPT UNTOUCHED" in parked["note"]
    assert "not a coverage loss" in parked["note"].lower()
    assert rep["refreshed"] == 0


def test_a_refresh_updates_last_obs_but_never_moves_the_backfilled_date(tree, monkeypatch):
    """`backfilled` is the provenance date scripts/run_us_scan_tier.py reads to keep a
    backfilled name scan-eligible. A refresh must not restamp it as 'created today'."""
    store.upsert("yahoo", "AAA", _good_frame())
    state = bf.load_state()
    state["done"] = {"AAA": {"backfilled": "2026-01-15", "rows": 120,
                             "last_obs": "2024-06-14"}}
    bf.save_state(state)
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)
    _stub_download(monkeypatch, {"*": _yf_response({"AAA": _bars(400)})})

    rep = bf.run(cap=5, batch_size=5, sleep_s=0)

    assert rep["refreshed"] == 1
    done = json.loads((tree / "data" / bf.STATE_FILE).read_text())["done"]["AAA"]
    assert done["backfilled"] == "2026-01-15", "creation date must not move"
    assert done["rows"] == 400 and done["last_obs"] > "2024-06-14"
    assert "refreshed" in done


def test_the_notice_carries_the_refresh_cadence(tree, monkeypatch, capsys):
    for t in ("AAA", "BBB"):
        store.upsert("yahoo", t, _good_frame())
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)
    _stub_download(monkeypatch, {"*": _yf_response({t: _bars(120) for t in ("AAA", "BBB")})})

    rep = bf.run(cap=5, batch_size=5, sleep_s=0)

    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("::notice title=yahoo-backfill::")][0]
    assert line == (f"::notice title=yahoo-backfill::backfilled 0, parked 0, "
                    f"remaining 0, refreshed {rep['refreshed']} of {rep['refreshable']}, "
                    f"refresh cadence ~{rep['refresh_cadence_d']}d")


def test_a_drain_night_notice_is_byte_identical_to_the_pre_refresh_format(
        tree, monkeypatch, capsys):
    """No refresh -> no tail. The drain-phase line must not change shape."""
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree, command=["AAA"])
    _stub_download(monkeypatch, {"*": _yf_response({"AAA": _bars(120)})})

    rep = bf.run(cap=1, batch_size=1, sleep_s=0)

    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("::notice title=yahoo-backfill::")][0]
    assert line == (f"::notice title=yahoo-backfill::backfilled {rep['written']}, "
                    f"parked {rep['parked']}, remaining {rep['remaining']}")
    assert rep["refresh_ran"] is False


def test_a_cadence_over_target_raises_a_line_start_warning(tree, monkeypatch, capsys):
    store.upsert("yahoo", "AAA", _good_frame())
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)
    _stub_download(monkeypatch, {"*": _yf_response({"AAA": _bars(120)})})
    # 1 refreshable at 1/night is a 1-day cadence; force the over-target branch by
    # claiming a much larger refreshable population than tonight's cap can cover.
    monkeypatch.setattr(bf, "refresh_candidates", lambda s, **kw: (["AAA"], 20000))

    bf.run(cap=5, batch_size=5, sleep_s=0, refresh_cap=1000)

    warn = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("::warning title=yahoo-backfill-cadence")]
    assert warn and "past the 6d target" in warn[0]


def test_dry_run_reports_the_refresh_plan_without_touching_the_network(tree, monkeypatch):
    store.upsert("yahoo", "AAA", _good_frame())
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    def explode(*_a, **_k):
        raise AssertionError("--dry-run must not touch the network")
    monkeypatch.setattr(bf, "download_batch", explode)

    rep = bf.run(cap=5, batch_size=5, sleep_s=0, dry_run=True)

    assert rep["refresh_sample"] == ["AAA"] and rep["refreshable"] == 1
    assert rep["refreshed"] == 0


def test_cli_exits_zero_so_the_lane_can_never_red_the_night(tree, monkeypatch):
    """Additive off-render lane: a night that backfilled nothing must not fail the
    collect job. The ::notice / ::warning lines carry the outcome."""
    _write_ledger(tree, [("2026-08-01", "AAA")])
    _write_hub(tree)
    _stub_download(monkeypatch, {"*": None})
    assert bf.main(["--cap", "1", "--batch-size", "1", "--sleep", "0"]) == 0


# Daily discovery needs an explicit whole-maintained-scope attempt, while the
# existing collector, canonical writer, time budget and exclusions keep ownership.
def _daily_archive_seed(tree, monkeypatch, names=("AAA", "BBB", "CCC", "DDD")):
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)
    raw = _bars(220)
    for ticker in names:
        store.upsert("yahoo", ticker, yahoo_mod.extract_store_frame(raw, ticker))
    return raw


def test_refresh_all_selects_every_eligible_archive_name(tree, monkeypatch):
    names = ("AAA", "BBB", "CCC", "DDD")
    raw = _daily_archive_seed(tree, monkeypatch, names)
    monkeypatch.setattr(bf, "refresh_cap_for", lambda n: 1)
    calls = []
    _stub_download(monkeypatch, {"*": _yf_response({t: raw for t in names})}, calls)
    report = bf.run(cap=1, batch_size=2, sleep_s=0, refresh_all=True)
    assert report["refreshable"] == report["refresh_planned"] == report["refreshed"] == 4
    assert report["refresh_cap"] == 4 and report["refresh_scope"] == "all_unmaintained"
    assert sorted(t for batch in calls for t in batch) == list(names)


def test_refresh_all_does_not_starve_existing_prices_behind_new_name_backlog(tree, monkeypatch):
    raw = _daily_archive_seed(tree, monkeypatch, ("OLD",))
    _write_ledger(tree, [("2026-09-16", "NEW")])
    calls = []
    _stub_download(monkeypatch, {"*": _yf_response({"NEW": raw, "OLD": raw})}, calls)
    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)
    assert calls == [["NEW"], ["OLD"]]
    assert report["written"] == 1 and report["refreshed"] == 1
    assert report["planned"] == report["cap"] == 1


def test_refresh_all_keeps_one_existing_budget_for_backfill_and_refresh(tree, monkeypatch):
    raw = _daily_archive_seed(tree, monkeypatch, ("OLD",))
    _write_ledger(tree, [("2026-09-16", "NEW")])
    clock = {"now": 0.0}
    monkeypatch.setattr(bf.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(bf.time, "sleep", lambda _: None)
    calls = []
    def download(symbols, period):
        calls.append((symbols, period))
        clock["now"] = 11.0
        return _yf_response({t: raw for t in symbols})
    monkeypatch.setattr(bf, "download_batch", download)
    report = bf.run(cap=1, batch_size=1, sleep_s=0, budget_s=10, refresh_all=True)
    assert calls == [(["NEW"], "max")]
    assert report["budget_exhausted"] is True
    assert report["refresh_planned"] == 1 and report["refreshed"] == 0
    assert report["attempted"] == 1


def test_refresh_all_preserves_other_collector_and_parked_bytes(tree, monkeypatch):
    raw = _daily_archive_seed(tree, monkeypatch, ("MINE", "THEIRS", "PARKED"))
    _no_maintained(monkeypatch, keep={"THEIRS"})
    state = bf.load_state()
    state["parked"] = {"PARKED": {"reason": "refresh_failed"}}
    bf.save_state(state)
    paths = [tree / "data/yahoo" / (t + ".parquet") for t in ("THEIRS", "PARKED")]
    before = {p: p.read_bytes() for p in paths}
    calls = []
    _stub_download(monkeypatch, {"*": _yf_response({"MINE": raw})}, calls)
    report = bf.run(cap=1, sleep_s=0, refresh_all=True)
    assert calls == [["MINE"]] and report["refreshed"] == 1
    assert {p: p.read_bytes() for p in paths} == before


def test_refresh_all_dry_run_is_a_plan_not_a_freshness_receipt(tree, monkeypatch):
    _daily_archive_seed(tree, monkeypatch)
    monkeypatch.setattr(bf, "refresh_cap_for", lambda _: 1)
    monkeypatch.setattr(bf, "download_batch", lambda *a: pytest.fail("dry run fetched data"))
    before = {p: p.read_bytes() for p in (tree / "data").rglob("*") if p.is_file()}
    report = bf.run(cap=1, refresh_all=True, dry_run=True)
    after = {p: p.read_bytes() for p in (tree / "data").rglob("*") if p.is_file()}
    assert before == after
    assert report["refresh_planned"] == 4 and report["refreshed"] == 0
    assert report["refresh_scope"] == "all_unmaintained"


def test_refresh_all_cannot_override_unresolved_maintained_scope(tree, monkeypatch):
    _daily_archive_seed(tree, monkeypatch)
    monkeypatch.setattr(bf, "maintained_stems", lambda: None)
    monkeypatch.setattr(bf, "download_batch", lambda *a: pytest.fail("unknown scope fetched data"))
    report = bf.run(cap=1, refresh_all=True)
    assert report["refresh_planned"] == report["refreshed"] == 0


def test_refresh_all_and_explicit_refresh_cap_are_not_silently_mixed(tree):
    with pytest.raises(ValueError, match="refresh_cap"):
        bf.run(refresh_all=True, refresh_cap=3, dry_run=True)


def test_refresh_all_cli_is_explicit_and_the_default_cadence_is_unchanged(tree, monkeypatch):
    _daily_archive_seed(tree, monkeypatch)
    monkeypatch.setattr(bf, "refresh_cap_for", lambda _: 1)
    report = bf.run(cap=1, dry_run=True)
    assert report["refresh_planned"] == 1 and "refresh_scope" not in report
    calls = []
    original = bf.run
    def observe(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(bf, "run", observe)
    assert bf.main(["--refresh-all", "--batch-size", "160", "--budget-s", "480", "--dry-run"]) == 0
    assert calls[0]["refresh_all"] is True
    assert calls[0]["budget_s"] == 480


def test_daily_consumer_requests_the_whole_archive_without_a_second_writer_or_budget():
    import shlex
    import yaml
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] /
                               ".github/workflows/daily.yml").read_text())
    owners = [(job, step.get("run", ""))
              for job, spec in workflow["jobs"].items()
              for step in spec.get("steps", [])
              if "python -m scripts.backfill_yahoo_universe" in step.get("run", "")]
    assert len(owners) == 1 and owners[0][0] == "collect"
    command = owners[0][1].replace("\\\n", " ")
    line = next(line for line in command.splitlines()
                if "python -m scripts.backfill_yahoo_universe" in line)
    tokens = shlex.split(line)
    assert "--refresh-all" in tokens
    assert tokens[tokens.index("--cap") + 1] == "400"
    assert tokens[tokens.index("--batch-size") + 1] == "160"
    assert tokens[tokens.index("--budget-s") + 1] == "480"
    assert "--period" not in tokens, "workflow must not override the owner's backfill period"
    assert bf.REFRESH_PROBE_PERIOD == "1mo", "refresh probe is an owner-level contract"
    assert "|| echo" in command, "retain graceful degradation rather than hiding source failure"


def test_refresh_all_basis_stable_uses_short_probe_and_preserves_deep_history(
        tree, monkeypatch):
    """Stable overlap must never pay for period=max or rewrite old complete years."""
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    new_raw = _bars(301)
    old_store = yahoo_mod.extract_store_frame(old_raw, "AAA")
    store.upsert("yahoo", "AAA", old_store)
    before = store.read("yahoo", "AAA").copy(deep=True)

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        assert period == bf.REFRESH_PROBE_PERIOD
        return _yf_response({"AAA": new_raw.iloc[-22:]})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)
    after = store.read("yahoo", "AAA")

    assert calls == [(["AAA"], "1mo")]
    assert report["refresh_basis_shifted"] == 0
    assert report["refresh_rebased"] == report["refresh_rebase_failed"] == 0
    assert report["refreshed"] == 1
    assert len(after) == 301
    pd.testing.assert_frame_equal(
        after.loc[before.index[:250]],
        before.loc[before.index[:250]],
        check_freq=False,
    )


def test_refresh_all_true_basis_shift_escalates_to_full_history_before_write(
        tree, monkeypatch):
    """A re-adjusted overlap is healed with max history, never short-spliced."""
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    rebased_raw = _bars(301, div_steps=(300,))
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))
    before_first = float(store.read("yahoo", "AAA")["close"].iloc[0])

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        frame = rebased_raw.iloc[-22:] if period == "1mo" else rebased_raw
        return _yf_response({"AAA": frame})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)
    after = store.read("yahoo", "AAA")

    assert calls == [(["AAA"], "1mo"), (["AAA"], "max")]
    assert report["refresh_basis_shifted"] == report["refresh_rebased"] == 1
    assert report["refresh_rebase_failed"] == 0 and report["refreshed"] == 1
    assert len(after) == 301
    assert float(after["close"].iloc[0]) == pytest.approx(before_first * 0.99)


def test_refresh_all_no_overlap_escalates_to_full_history(tree, monkeypatch):
    """No overlap is unverifiable and therefore requires the same max-history heal."""
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    full_raw = _bars(1700, start="2020-01-01")
    old_raw = full_raw.iloc[:300]
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        frame = full_raw.iloc[-22:] if period == "1mo" else full_raw
        return _yf_response({"AAA": frame})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)

    assert calls == [(["AAA"], "1mo"), (["AAA"], "max")]
    assert report["refresh_basis_shifted"] == report["refresh_rebased"] == 1
    assert report["refresh_rebase_failed"] == 0
    assert len(store.read("yahoo", "AAA")) == 1700


def test_refresh_all_failed_basis_heal_keeps_existing_archive_byte_identical(
        tree, monkeypatch):
    """A detected shift plus failed max heal is a deferred refresh, never a splice."""
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    rebased_raw = _bars(301, div_steps=(300,))
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))
    path = tree / "data" / "yahoo" / "AAA.parquet"
    before = path.read_bytes()

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        if period == "max":
            raise ConnectionError("full-history heal unavailable")
        return _yf_response({"AAA": rebased_raw.iloc[-22:]})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)

    assert calls == [(["AAA"], "1mo"), (["AAA"], "max")]
    assert report["refresh_basis_shifted"] == 1
    assert report["refresh_rebased"] == 0
    assert report["refresh_rebase_failed"] == 1
    assert report["refreshed"] == 0
    assert path.read_bytes() == before
    state = bf.load_state()
    assert not (state.get("done", {}).get("AAA", {}).get("refreshed"))


def test_refresh_all_does_not_report_a_stored_old_frame_as_current(tree, monkeypatch):
    from lib import nyse_calendar
    raw = _daily_archive_seed(tree, monkeypatch, ("AAA", "BBB"))
    completed = raw.index[-1].date()
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: completed)
    _stub_download(monkeypatch, {"*": _yf_response({"AAA": raw, "BBB": raw.iloc[:-1]})})
    report = bf.run(cap=1, sleep_s=0, refresh_all=True)
    assert report["refreshed"] == 2, "storage success keeps its existing meaning"
    assert report["refresh_expected_session"] == completed.isoformat()
    assert report["refresh_current_returned"] == 1
    assert report["refresh_noncurrent_returned"] == 1
    assert report["refresh_attempted"] == 2 and report["refresh_unattempted"] == 0
    # BBB's prior same-date value remains in the historical archive, but cannot
    # count as a freshly returned observation in this attempt's receipt.
    assert pd.Timestamp(completed) in store.read("yahoo", "BBB").index


def test_refresh_all_budget_discloses_names_not_attempted(tree, monkeypatch):
    from lib import nyse_calendar
    raw = _daily_archive_seed(tree, monkeypatch, ("AAA", "BBB"))
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: raw.index[-1].date())
    now = {"t": 0}
    monkeypatch.setattr(bf.time, "monotonic", lambda: now["t"])
    monkeypatch.setattr(bf.time, "sleep", lambda _: None)
    def download(symbols, period):
        now["t"] = 11
        return _yf_response({ticker: raw for ticker in symbols})
    monkeypatch.setattr(bf, "download_batch", download)
    report = bf.run(cap=1, batch_size=1, sleep_s=0, budget_s=10, refresh_all=True)
    assert report["refresh_planned"] == 2
    assert report["refresh_attempted"] == report["refresh_current_returned"] == 1
    assert report["refresh_unattempted"] == 1
    assert report["budget_exhausted"] is True


def test_refresh_all_transport_failure_counts_the_request_not_current_data(tree, monkeypatch):
    _daily_archive_seed(tree, monkeypatch, ("AAA", "BBB"))
    _stub_download(monkeypatch, {"*": ConnectionError("provider unavailable")})
    report = bf.run(cap=1, batch_size=2, sleep_s=0, refresh_all=True)
    assert report["batch_errors"] == 1
    assert report["refresh_attempted"] == 2 and report["refresh_unattempted"] == 0
    assert report["refreshed"] == report["refresh_current_returned"] == 0
    assert report["attempted"] == 0, "legacy processed-row counter retains its meaning"


# ---------------------------------------------------------------------------
# 9. adjustment-basis comparison: UNKNOWN is not STABLE
# ---------------------------------------------------------------------------
def _flaky_first_store_read(monkeypatch):
    """Fail ONLY the first archive read; every later read succeeds.

    That is the exact shape the defect needs: the guard's read fails, the
    upsert's own read afterwards succeeds, so a short probe reaches the durable
    archive with nothing having ever compared it."""
    real_read = store.read
    reads = {"n": 0}

    def flaky_read(group, name):
        reads["n"] += 1
        if reads["n"] == 1:
            raise OSError("transient archive read failure")
        return real_read(group, name)

    monkeypatch.setattr(store, "read", flaky_read)
    return reads


def test_refresh_all_unknown_basis_comparison_never_splices_a_short_probe(
        tree, monkeypatch):
    """An UNVERIFIABLE basis is not a verified stable overlap.

    The adjustment-basis guard can answer "not shifted" for two very different
    reasons: the comparison RAN and found the same basis, or the comparison
    could not be MADE at all. Only the first may authorize splicing a short
    probe into the durable archive. Here the archive read fails once inside the
    guard and succeeds again inside the upsert, so a rebased 22-row probe would
    land inside a 300-row stale-basis archive without period='max' — a
    mixed-basis series that reads as one. The refresh must treat the
    unverifiable comparison as needing the full-history heal.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    rebased_raw = _bars(301, div_steps=(300,))
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))
    path = tree / "data" / "yahoo" / "AAA.parquet"
    stale_first = float(pd.read_parquet(path)["close"].iloc[0])
    rebased_first = float(
        yahoo_mod.extract_store_frame(rebased_raw, "AAA")["close"].iloc[0])

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        frame = (rebased_raw.iloc[-22:] if period == bf.REFRESH_PROBE_PERIOD
                 else rebased_raw)
        return _yf_response({"AAA": frame})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)
    _flaky_first_store_read(monkeypatch)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)
    after = pd.read_parquet(path)

    # THE DEFECT: a rebased probe spliced onto a stale archive leaves the
    # pre-rebase rows un-rebased — one series carrying two adjustment bases.
    assert float(after["close"].iloc[0]) == pytest.approx(rebased_first, rel=1e-9), (
        "every stored row must sit on the basis of the response that was "
        f"written (stale first close {stale_first!r}, rebased {rebased_first!r})")
    assert len(after) == 301, "the full-history heal owns every date it returned"
    assert calls == [(["AAA"], bf.REFRESH_PROBE_PERIOD), (["AAA"], "max")]
    assert report["refresh_basis_unknown"] == 1
    assert report["refresh_basis_shifted"] == 0
    assert report["refresh_rebased"] == 1
    assert report["refresh_rebase_failed"] == 0
    assert report["refreshed"] == 1


def test_refresh_all_unknown_basis_with_failed_heal_keeps_the_archive_and_claims_nothing(
        tree, monkeypatch):
    """An unverifiable basis plus a failed required heal is a deferred refresh.

    The prior parquet stays byte-identical, the name is not marked refreshed,
    and no provider-currentness is claimed for a name nothing was written for.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    rebased_raw = _bars(301, div_steps=(300,))
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))
    path = tree / "data" / "yahoo" / "AAA.parquet"
    before = path.read_bytes()

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        if period == "max":
            raise ConnectionError("full-history heal unavailable")
        return _yf_response({"AAA": rebased_raw.iloc[-22:]})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)
    _flaky_first_store_read(monkeypatch)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)

    assert calls == [(["AAA"], bf.REFRESH_PROBE_PERIOD), (["AAA"], "max")]
    assert report["refresh_basis_unknown"] == 1
    assert report["refresh_rebased"] == 0
    assert report["refresh_rebase_failed"] == 1
    assert report["refreshed"] == 0
    assert path.read_bytes() == before
    state = bf.load_state()
    assert not (state.get("done", {}).get("AAA", {}).get("refreshed"))
    # A name nothing was written for may claim no provider-currentness either.
    assert report["refresh_current_returned"] == 0
    assert report["refresh_noncurrent_returned"] == 0


def test_basis_guard_separates_an_unusable_comparison_from_a_verified_stable_one(
        tree, monkeypatch):
    """The guard's source contract: an unusable comparison is UNKNOWN.

    "Not proven different" is not "proven the same". The tri-state guard has to
    say so out loud, because the refresh path may only splice a short probe
    onto a comparison that actually RAN. The legacy boolean default is
    unchanged for the other callers: an unusable comparison is still "not
    shifted" there.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    rebased_raw = _bars(301, div_steps=(300,))
    old_frame = yahoo_mod.extract_store_frame(old_raw, "AAA")
    store.upsert("yahoo", "AAA", old_frame)
    stable_probe = yahoo_mod.extract_store_frame(old_raw.iloc[-22:], "AAA")
    rebased_probe = yahoo_mod.extract_store_frame(rebased_raw.iloc[-22:], "AAA")

    # The legacy boolean contract, unchanged for every existing caller.
    assert store.basis_shifted("yahoo", "AAA", stable_probe) is False
    assert store.basis_shifted("yahoo", "AAA", rebased_probe) is True

    # The tri-state contract the refresh path depends on.
    assert store.basis_comparison("yahoo", "AAA", stable_probe) == store.BASIS_STABLE
    assert store.basis_comparison("yahoo", "AAA", rebased_probe) == store.BASIS_SHIFTED

    # (a) the comparison column is missing from the stored archive
    store.upsert("yahoo", "NOCOL", old_frame.drop(columns=["close"]))
    assert store.basis_comparison("yahoo", "NOCOL", stable_probe) == store.BASIS_UNKNOWN
    assert store.basis_shifted("yahoo", "NOCOL", stable_probe) is False

    # (b) the stored comparison values are all unusable
    store.upsert("yahoo", "NAN", old_frame.assign(close=np.nan))
    assert store.basis_comparison("yahoo", "NAN", stable_probe) == store.BASIS_UNKNOWN
    assert store.basis_shifted("yahoo", "NAN", stable_probe) is False

    # (c) the incoming comparison values are not numbers
    unusable = stable_probe.copy()
    unusable["close"] = "not-a-number"
    assert store.basis_comparison("yahoo", "AAA", unusable) == store.BASIS_UNKNOWN
    assert store.basis_shifted("yahoo", "AAA", unusable) is False

    # (d) the stored archive cannot be read at all
    real_read = store.read
    def broken_read(group, name):
        raise OSError("transient archive read failure")
    monkeypatch.setattr(store, "read", broken_read)
    assert store.basis_comparison("yahoo", "AAA", stable_probe) == store.BASIS_UNKNOWN
    assert store.basis_shifted("yahoo", "AAA", stable_probe) is False
    monkeypatch.setattr(store, "read", real_read)


# ---------------------------------------------------------------------------
# 10. adjustment-basis comparison: a MIXED usable/unusable overlap
# ---------------------------------------------------------------------------
def _basis_frame(close_values, start: str = "2024-01-01") -> pd.DataFrame:
    """A store-shaped frame (the schema lib/store writes) carrying exactly the
    given close values, so a comparison can be posed against a chosen value."""
    n = len(close_values)
    idx = pd.bdate_range(start, periods=n, name="Date")
    close = np.asarray(close_values, dtype="float64")
    return pd.DataFrame({
        "close_price": close,
        "close": close,
        "volume": np.arange(1000.0, 1000.0 + n),
    }, index=idx)


#: (case id, stored close, incoming close). Both rows of each overlap sit on
#: the same dates, so BOTH rows are compared and one of them cannot be.
_MIXED_NONFINITE_OVERLAPS = (
    ("new-inf", (100.0, 100.0), (100.0, float("inf"))),
    ("old-and-new-inf", (100.0, float("inf")), (100.0, float("inf"))),
)


@pytest.mark.parametrize(
    "stored_close,incoming_close",
    [(stored, incoming) for _case, stored, incoming in _MIXED_NONFINITE_OVERLAPS],
    ids=[case for case, _s, _i in _MIXED_NONFINITE_OVERLAPS],
)
def test_basis_comparison_never_certifies_stable_over_a_mixed_nonfinite_overlap(
        tree, monkeypatch, stored_close, incoming_close):
    """One unusable row makes the whole overlap unverifiable.

    The counterexample: old close [100, 100] against new close [100, +inf]. The
    relative differences are [0, NaN] — an infinite new value divides an
    infinite numerator — and a maximum that skips missing values reads 0, so
    the comparison used to certify a VERIFIED stable overlap on a row it could
    not compare at all. The same happens when the STORED value is infinite too:
    |inf - inf| is undefined, so that row compares as NaN and is skipped.

    An archive that cannot prove its whole overlap is on one basis cannot be
    spliced onto, so the answer is UNKNOWN — never "stable".
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    store.upsert("yahoo", "AAA", _basis_frame(stored_close))
    incoming = _basis_frame(incoming_close)

    assert store.basis_comparison("yahoo", "AAA", incoming) == store.BASIS_UNKNOWN, (
        "an overlap with an unusable row is not a verified stable overlap")

    # The legacy boolean is NOT moved by this: an unusable comparison is still
    # "not shifted" for every existing caller.
    assert store.basis_shifted("yahoo", "AAA", incoming) is False


def test_refresh_all_nonfinite_overlap_escalates_and_a_failed_heal_keeps_the_archive(
        tree, monkeypatch):
    """An unusable comparison row must not authorise a splice.

    The probe's overlap carries one infinite close. The schema gate rejects a
    NaN or a non-positive close but NOT an infinity, so that row reaches the
    basis comparison exactly as a vendor response would — and the comparison
    cannot be made on it. The refresh must escalate to the full-history heal;
    when that heal FAILS the prior parquet stays byte-identical, the name is
    not marked refreshed, and no provider-currentness is claimed for a name
    nothing was written for.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))
    path = tree / "data" / "yahoo" / "AAA.parquet"
    before = path.read_bytes()

    probe_raw = _bars(301)
    probe_raw.loc[probe_raw.index[-5], "Adj Close"] = float("inf")

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        if period == "max":
            raise ConnectionError("full-history heal unavailable")
        return _yf_response({"AAA": probe_raw.iloc[-22:]})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)

    assert calls == [(["AAA"], bf.REFRESH_PROBE_PERIOD), (["AAA"], "max")], (
        "an overlap with an unusable row must not certify a stable basis: the "
        "refresh has to escalate to the full-history heal")
    assert report["refresh_basis_unknown"] == 1
    assert report["refresh_basis_shifted"] == 0
    assert report["refresh_rebased"] == 0
    assert report["refresh_rebase_failed"] == 1
    assert report["refreshed"] == 0
    assert path.read_bytes() == before
    state = bf.load_state()
    assert not (state.get("done", {}).get("AAA", {}).get("refreshed"))
    assert report["refresh_current_returned"] == 0
    assert report["refresh_noncurrent_returned"] == 0


def test_refresh_all_nonfinite_overlap_keeps_the_archive_when_the_heal_is_invalid(
        tree, monkeypatch):
    """A required heal that returns an unusable frame is a deferred refresh too.

    The escalation is required, so the full-history heal is attempted; when the
    response it gets back cannot be written (a one-bar stub), the prior parquet
    stays byte-identical, the name is not marked refreshed, and no
    provider-currentness is claimed for it.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))
    path = tree / "data" / "yahoo" / "AAA.parquet"
    before = path.read_bytes()

    probe_raw = _bars(301)
    probe_raw.loc[probe_raw.index[-5], "Adj Close"] = float("inf")

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        if period == "max":
            return _yf_response({"AAA": probe_raw.iloc[-1:]})   # a one-bar stub
        return _yf_response({"AAA": probe_raw.iloc[-22:]})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)

    assert calls == [(["AAA"], bf.REFRESH_PROBE_PERIOD), (["AAA"], "max")], (
        "an overlap with an unusable row must not certify a stable basis: the "
        "refresh has to escalate to the full-history heal")
    assert report["refresh_basis_unknown"] == 1
    assert report["refresh_rebased"] == 0
    assert report["refresh_rebase_failed"] == 1
    assert report["refreshed"] == 0
    assert path.read_bytes() == before
    assert report["refresh_current_returned"] == 0
    assert report["refresh_noncurrent_returned"] == 0


def test_refresh_all_stable_finite_overlap_still_avoids_the_full_history_heal(
        tree, monkeypatch):
    """A fully usable stable overlap must NOT pay for period='max'.

    The strict reading of the comparison must not over-tighten: an overlap
    whose every row is a usable number and compares equal is exactly the case
    the short probe exists for, and it must stay a single request.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    old_raw = _bars(300)
    store.upsert("yahoo", "AAA", yahoo_mod.extract_store_frame(old_raw, "AAA"))

    calls = []
    def download(symbols, period):
        calls.append((sorted(symbols), period))
        return _yf_response({"AAA": _bars(301).iloc[-22:]})
    monkeypatch.setattr(bf, "download_batch", download)
    monkeypatch.setattr(bf.time, "sleep", lambda *_a, **_k: None)

    report = bf.run(cap=1, batch_size=1, sleep_s=0, refresh_all=True)

    assert calls == [(["AAA"], bf.REFRESH_PROBE_PERIOD)], (
        "a fully usable stable overlap must not trigger the full-history heal")
    assert report["refresh_basis_shifted"] == 0
    assert report["refresh_basis_unknown"] == 0
    assert report["refresh_rebased"] == report["refresh_rebase_failed"] == 0
    assert report["refreshed"] == 1


def test_legacy_basis_shifted_default_is_unchanged_for_the_affected_behaviours(
        tree, monkeypatch):
    """The legacy boolean guard keeps every documented default.

    The strict reading belongs to the tri-state comparator only. ~10 other
    collectors call this boolean, and its answers must not move: an unusable
    comparison is still "not shifted" there, and an infinite stored value
    against a finite new one is still a shift. These are the receiver's own
    answers, pinned here so that a future tightening of the shared comparator
    is caught instead of silently inherited.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    stable = _basis_frame((100.0, 100.0))
    shifted = _basis_frame((90.0, 90.0))
    new_inf = _basis_frame((100.0, float("inf")))
    old_inf = _basis_frame((float("inf"), 100.0))
    both_inf = _basis_frame((float("inf"), float("inf")))
    all_nan = _basis_frame((float("nan"), float("nan")))

    store.upsert("yahoo", "STABLE", stable)
    store.upsert("yahoo", "SHIFTED", stable)
    store.upsert("yahoo", "NEWINF", stable)
    store.upsert("yahoo", "OLDINF", old_inf)
    store.upsert("yahoo", "BOTHINF", both_inf)
    store.upsert("yahoo", "NAN", all_nan)
    store.upsert("yahoo", "NOCOL", stable.drop(columns=["close"]))

    # A verified stable overlap is not a shift.
    assert store.basis_shifted("yahoo", "STABLE", stable) is False
    # A proven shift is a shift.
    assert store.basis_shifted("yahoo", "SHIFTED", shifted) is True
    # An infinite STORED value against a finite new one is still a shift.
    assert store.basis_shifted("yahoo", "OLDINF", stable) is True
    # An unusable comparison is still "not shifted" for the legacy callers.
    assert store.basis_shifted("yahoo", "NEWINF", new_inf) is False
    assert store.basis_shifted("yahoo", "BOTHINF", both_inf) is False
    assert store.basis_shifted("yahoo", "NAN", stable) is False
    assert store.basis_shifted("yahoo", "NOCOL", stable) is False

    # An unreadable archive is still "not shifted", and never raises.
    real_read = store.read
    def broken_read(group, name):
        raise OSError("transient archive read failure")
    monkeypatch.setattr(store, "read", broken_read)
    assert store.basis_shifted("yahoo", "STABLE", stable) is False
    monkeypatch.setattr(store, "read", real_read)


# ---------------------------------------------------------------------------
# 11. adjustment-basis comparison: the ORIGINAL common-date evidence decides
# ---------------------------------------------------------------------------
def test_basis_comparison_never_certifies_stable_from_the_remainder_of_a_dropped_row(
        tree, monkeypatch):
    """A stored row that could not be compared must not be dropped BEFORE the
    comparison.

    The counterexample: stored close [100, NaN] against incoming close
    [100, 200] on the same two dates. The missing stored row was dropped
    before the dates were intersected, so only the comparable remainder
    survived and the overlap was certified STABLE — a verified basis built on
    evidence for a date that was never compared at all. The strict comparison
    keeps the original common-date evidence and answers UNKNOWN instead.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    store.upsert("yahoo", "AAA", _basis_frame((100.0, float("nan"))))
    incoming = _basis_frame((100.0, 200.0))

    assert store.basis_comparison("yahoo", "AAA", incoming) == store.BASIS_UNKNOWN, (
        "an overlap with an unusable stored row is not a verified stable overlap")

    # The legacy boolean is NOT moved by this: it keeps the dropna() rule, so
    # the comparable remainder still answers "not shifted".
    assert store.basis_shifted("yahoo", "AAA", incoming) is False


def test_basis_comparison_calls_an_unusable_stored_infinity_unknown_in_strict_mode(
        tree, monkeypatch):
    """An infinite stored value cannot be compared, so strict mode is UNKNOWN.

    The counterexample: stored close [100, +inf] against incoming close
    [100, 100]. The relative difference of the infinite row is infinite —
    decisive-looking evidence — but it is a statement about a value that cannot
    be compared at all, so the strict comparison answers UNKNOWN and never
    certifies a basis across evidence that is not usable.
    """
    _write_ledger(tree, [])
    _write_hub(tree)
    _no_maintained(monkeypatch)

    store.upsert("yahoo", "AAA", _basis_frame((100.0, float("inf"))))
    incoming = _basis_frame((100.0, 100.0))

    assert store.basis_comparison("yahoo", "AAA", incoming) == store.BASIS_UNKNOWN, (
        "an infinite stored value is unusable evidence, not a proven shift")

    # The legacy boolean keeps its documented answer for the same evidence:
    # an infinite stored value against a finite new one is still a shift.
    assert store.basis_shifted("yahoo", "AAA", incoming) is True
