"""Producer tests for the nightly catalyst-links builder.

Synthetic stages and injected inputs only. No data/ or site/ bytes, no network.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import scripts.build_options_catalyst_links as prod
from engine.event_calendar import _FOMC, fomc_decision_dates
from engine.options_catalyst_link import (
    BINDING_STATES,
    REPO_ROOT,
    SPEC_VERSION,
    CatalystCandidate,
    ContractKeyError,
)
from engine.stock_identity.authority import AUTHORITY_KEYS
from engine.stock_identity.plane import PLANE_STOCKS

ASOF = date(2026, 9, 4)
SESSION = "2026-09-04"
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@pytest.fixture(autouse=True)
def _block_live_stage(monkeypatch):
    """A forgotten patch must not open R2 or the public events index."""

    def _fetch(*_args, **_kwargs):
        raise AssertionError("fetch_event_stage must be patched")

    def _discover(*_args, **_kwargs):
        raise AssertionError("discover_event_sessions must be patched")

    monkeypatch.setattr(prod, "fetch_event_stage", _fetch)
    monkeypatch.setattr(prod, "discover_event_sessions", _discover)


def _event(event_id: str, root: str, exp: str, **extra) -> dict:
    row = {
        "id": event_id,
        "ts": "2026-09-04T18:00:00Z",
        "observed_at": "2026-09-04T18:00:05Z",
        "root": root,
        "right": "C",
        "exp": exp,
        "strike": 100.0,
    }
    row.update(extra)
    return row


def _fresh(next_date: str, age: int = 3) -> dict:
    return {
        "in_blackout": False,
        "days_to_earnings": 4,
        "next_date": next_date,
        "next_time": "amc",
        "as_of_age_td": age,
        "stale": False,
        "reason": "outside_window",
    }


def _stale(next_date: str, age: int = 12) -> dict:
    return {
        "in_blackout": False,
        "days_to_earnings": None,
        "next_date": next_date,
        "next_time": None,
        "as_of_age_td": age,
        "stale": True,
        "reason": "row_stale",
    }


def _missing(reason: str) -> dict:
    return {
        "in_blackout": False,
        "days_to_earnings": None,
        "next_date": None,
        "next_time": None,
        "as_of_age_td": None,
        "stale": False,
        "reason": reason,
    }


def _assert_false_authority(block: dict) -> None:
    assert set(block) == set(AUTHORITY_KEYS)
    assert all(block[key] is False for key in AUTHORITY_KEYS)


def _records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _bind(monkeypatch, tmp_path, rows, symbols, table, *, session=SESSION, asof=ASOF):
    calls = {"plane": None, "today": None, "tickers": []}

    def _symbols(plane_id, repo_root=None):
        calls["plane"] = plane_id
        return set(symbols)

    def _assess(ticker, today=None, store_path=None):
        calls["today"] = today
        calls["tickers"].append(ticker)
        return table[ticker]

    monkeypatch.setattr(prod, "utc_today", lambda: asof)
    monkeypatch.setattr(prod, "fetch_event_stage", lambda _session: rows)
    monkeypatch.setattr(prod, "symbols_on_plane", _symbols)
    monkeypatch.setattr(prod.earnings_blackout, "assess", _assess)
    rc = prod.main(["--session", session, "--out", str(tmp_path)])
    envelope = json.loads((tmp_path / "latest.json").read_text())
    records = _records(tmp_path / f"{session}.jsonl")
    return rc, envelope, records, calls


def test_a_envelope_schema_and_histogram_sum_law(monkeypatch, tmp_path, capsys):
    rows = [
        _event("e1", "AAPL", "2026-10-16"),
        _event("e2", "MSFT", "2026-09-11"),
        _event("e3", "NVDA", "2026-09-11"),
        _event("e4", "ZZZZ", "2026-10-16"),
        _event("e5", "AAPL", "not-a-date"),
        {"root": "AAPL", "exp": "2026-10-16", "strike": 100.0, "right": "C"},
    ]
    table = {
        "AAPL": _fresh("2026-09-16", age=3),
        "MSFT": _stale("2026-09-08", age=12),
        "NVDA": _missing("next_date_missing"),
        "ZZZZ": _missing("ticker_not_in_store"),
    }
    rc, env, records, calls = _bind(
        monkeypatch, tmp_path, rows, {"AAPL", "MSFT", "NVDA"}, table,
    )
    assert rc == 0
    assert calls["plane"] == PLANE_STOCKS
    assert env["schema"] == "mastermind.options_catalyst_links/v1"
    assert env["spec_version"] == SPEC_VERSION
    assert env["session_date"] == SESSION
    assert env["asof"] == "2026-09-04"
    assert _UTC_RE.match(env["generated_utc"])
    assert env["horizon_days"] == 63
    assert env["source"] == {
        "events": "r2:live_flow/events/2026-09-04.jsonl",
        "earnings": "engine.earnings_blackout",
        "macro": "engine.event_calendar",
        "identity": "stock_identity.plane:stocks",
    }
    assert env["links_path"] == "2026-09-04.jsonl"
    assert "links" not in env
    assert env["states"] == ["ok"]
    assert env["is_context_only"] is True
    _assert_false_authority(env["authority"])
    counts = env["counts"]
    assert counts["events"] == 6
    assert counts["dropped_malformed"] == 1
    assert counts["known_symbols"] == 3
    assert counts["candidates_earnings"] == 2
    assert counts["candidates_macro"] == 2
    assert set(counts["by_state"]) == set(BINDING_STATES)
    assert sum(counts["by_state"].values()) == counts["events"] - counts["dropped_malformed"]
    assert [row["event_id"] for row in records] == ["e1", "e2", "e3", "e4", "e5"]
    assert [row["binding_state"] for row in records] == [
        "BOUND",
        "STALE_CATALYST",
        "UNBOUND_NO_CATALYST",
        "IDENTITY_UNRESOLVED",
        "EXPIRY_MISMATCH",
    ]
    for state in BINDING_STATES:
        assert counts["by_state"][state] == sum(1 for row in records if row["binding_state"] == state)
    assert records[0]["catalyst"]["kind"] == "earnings"
    out = capsys.readouterr().out
    summaries = [line for line in out.splitlines() if line.startswith("options_catalyst_links:")]
    assert summaries == [
        "options_catalyst_links: session=2026-09-04 events=6 bound=1 unbound=1 unresolved=1"
    ]


def test_b_no_stage_exits_zero_with_empty_links(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(prod, "utc_today", lambda: ASOF)
    monkeypatch.setattr(prod, "fetch_event_stage", lambda _session: None)
    rc = prod.main(["--session", SESSION, "--out", str(tmp_path)])
    assert rc == 0
    env = json.loads((tmp_path / "latest.json").read_text())
    assert env["states"] == ["no_event_stage"]
    assert env["links"] == []
    assert env["session_date"] == SESSION
    assert env["counts"]["events"] == 0
    assert sum(env["counts"]["by_state"].values()) == 0
    assert (tmp_path / "2026-09-04.jsonl").read_text() == ""
    _assert_false_authority(env["authority"])
    assert env["is_context_only"] is True
    out = capsys.readouterr().out
    assert any(line.startswith("::warning title=options_catalyst_links::") for line in out.splitlines())
    summaries = [line for line in out.splitlines() if line.startswith("options_catalyst_links:")]
    assert summaries == [
        "options_catalyst_links: session=2026-09-04 events=0 bound=0 unbound=0 unresolved=0"
    ]


def test_c_empty_plane_is_identity_unresolved(monkeypatch, tmp_path):
    rows = [_event("e1", "AAPL", "2026-10-16"), _event("e2", "SPY", "2026-10-16")]
    rc, env, records, calls = _bind(
        monkeypatch, tmp_path, rows, set(), {"AAPL": _fresh("2026-09-16"), "SPY": _fresh("2026-09-16")},
    )
    assert rc == 0
    assert calls["plane"] == PLANE_STOCKS
    assert env["counts"]["known_symbols"] == 0
    assert "identity_plane_absent" in env["states"]
    assert "ok" in env["states"]
    assert records and all(row["binding_state"] == "IDENTITY_UNRESOLVED" for row in records)


def test_d_earnings_conversion_fresh_stale_and_missing(monkeypatch, tmp_path):
    fresh_rc, _fresh_env, fresh_rows, fresh_calls = _bind(
        monkeypatch,
        tmp_path / "fresh",
        [_event("e-fresh", "AAPL", "2026-09-11")],
        {"AAPL"},
        {"AAPL": _fresh("2026-09-08", age=2)},
    )
    assert fresh_rc == 0
    assert fresh_calls["today"] == ASOF
    assert fresh_calls["tickers"] == ["AAPL"]
    fresh = fresh_rows[0]
    assert fresh["binding_state"] == "BOUND"
    assert fresh["catalyst"]["kind"] == "earnings"
    assert fresh["catalyst"]["source"] == "earnings_blackout"
    assert fresh["catalyst"]["label"] == "earnings"
    assert fresh["catalyst"]["stale"] is False
    assert fresh["catalyst"]["as_of_age_td"] == 2
    earnings_rows = [row for row in fresh["candidates"] if row["kind"] == "earnings"]
    assert earnings_rows[0]["locator"] == "earnings_blackout:AAPL"
    assert earnings_rows[0]["source"] == "earnings_blackout"

    _stale_rc, _stale_env, stale_rows, _stale_calls = _bind(
        monkeypatch,
        tmp_path / "stale",
        [_event("e-stale", "MSFT", "2026-09-11")],
        {"MSFT"},
        {"MSFT": _stale("2026-09-08", age=12)},
    )
    stale = stale_rows[0]
    assert stale["binding_state"] == "STALE_CATALYST"
    assert any(row["kind"] == "earnings" and row["stale"] is True for row in stale["candidates"])

    missing_rc, missing_env, missing_rows, _missing_calls = _bind(
        monkeypatch,
        tmp_path / "missing",
        [_event("e-miss", "NVDA", "2026-09-11")],
        {"NVDA"},
        {"NVDA": _missing("next_date_missing")},
    )
    assert missing_rc == 0
    assert missing_rows[0]["binding_state"] == "UNBOUND_NO_CATALYST"
    assert all(row["kind"] != "earnings" for row in missing_rows[0]["candidates"])
    assert missing_env["counts"]["candidates_earnings"] == 0


def test_e_fomc_lands_on_calendar_and_binds_etf(monkeypatch, tmp_path):
    captured = {}
    real = prod.bind_events

    def _spy(events, **kwargs):
        captured["calendar"] = kwargs["calendar"]
        captured["catalysts"] = kwargs["catalysts"]
        return real(events, **kwargs)

    monkeypatch.setattr(prod, "bind_events", _spy)
    rc, _env, records, _calls = _bind(
        monkeypatch,
        tmp_path,
        [_event("e-spy", "SPY", "2026-10-16")],
        {"SPY"},
        {"SPY": _missing("ticker_not_in_store")},
    )
    assert rc == 0
    macros = captured["calendar"].macro_catalysts
    assert macros
    assert all(item.kind == "fomc" and item.source == "event_calendar" for item in macros)
    assert [item.date for item in macros] == [date(2026, 9, 16), date(2026, 10, 28)]
    assert captured["calendar"].is_third_friday is None
    assert captured["calendar"].is_quad_witching is None
    assert all(
        item.kind != "fomc"
        for group in captured["catalysts"].values()
        for item in group
    )
    assert "SPY" not in captured["catalysts"]
    bound = records[0]
    assert bound["binding_state"] == "BOUND"
    assert bound["contract"]["root"] == "SPY"
    assert bound["catalyst"]["kind"] == "fomc"
    assert bound["expiry"]["is_third_friday"] is True


def test_f_out_under_repo_data_raises(monkeypatch, tmp_path):
    out = Path(REPO_ROOT) / "data" / "options_catalyst_links_refusal_probe"
    monkeypatch.setattr(prod, "utc_today", lambda: ASOF)
    monkeypatch.setattr(prod, "fetch_event_stage", lambda _session: [_event("e1", "AAPL", "2026-10-16")])
    monkeypatch.setattr(prod, "symbols_on_plane", lambda plane_id, repo_root=None: {"AAPL"})
    monkeypatch.setattr(prod.earnings_blackout, "assess", lambda *args, **kwargs: _fresh("2026-09-16"))
    assert not out.exists()
    with pytest.raises(ValueError, match="refuses repo data"):
        prod.main(["--session", SESSION, "--out", str(out)])
    assert not out.exists()


def test_g_authority_block_is_five_false(monkeypatch, tmp_path):
    _rc, env, records, _calls = _bind(
        monkeypatch,
        tmp_path,
        [_event("e1", "AAPL", "2026-09-11")],
        {"AAPL"},
        {"AAPL": _fresh("2026-09-08", age=2)},
    )
    _assert_false_authority(env["authority"])
    assert env["is_context_only"] is True
    assert records
    for record in records:
        _assert_false_authority(record["authority"])
        assert record["is_context_only"] is True
        assert record["source_rights"] == "research_expression_only"


def test_h_fomc_decision_dates_is_pure_and_sorted():
    before = list(_FOMC)
    none = fomc_decision_dates(date(2026, 2, 1), date(2026, 3, 1))
    assert none == []
    assert fomc_decision_dates(date(2026, 5, 1), date(2026, 4, 1)) == []
    whole = fomc_decision_dates(date(2026, 1, 1), date(2026, 12, 31))
    assert whole == sorted(whole)
    assert whole == [date.fromisoformat(raw) for raw, _sep in _FOMC]
    assert fomc_decision_dates(date(2026, 9, 16), date(2026, 9, 16)) == [date(2026, 9, 16)]
    assert fomc_decision_dates(date(2026, 1, 1), date(2026, 12, 31)) == whole
    assert list(_FOMC) == before


def test_i_envelope_carries_macro_calendar_from_the_same_candidates(monkeypatch, tmp_path):
    """A-F03-W3-2: `macro_calendar` is built from the SAME
    `_macro_candidates(asof, horizon_days)` list the binder reads — never a
    second calendar reader.  The page's chip helper compares two dates from
    this dict to the payoff-lab card's expiry, so the dict must carry every
    FOMC date in the window, sorted by date, with the horizon_end and the
    producer's asof both correctly stamped."""
    rc, env, _records, _calls = _bind(
        monkeypatch,
        tmp_path,
        [_event("e1", "AAPL", "2026-09-11")],
        {"AAPL"},
        {"AAPL": _fresh("2026-09-08", age=2)},
    )
    assert rc == 0
    cal = env["macro_calendar"]
    assert cal["asof"] == "2026-09-04"
    assert cal["horizon_end"] == "2026-11-06"  # asof + 63 days
    assert cal["source"] == "engine.event_calendar"
    # Same FOMC dates the binder would see, sorted.
    expected_dates = fomc_decision_dates(date(2026, 9, 4), date(2026, 11, 6))
    assert [entry["date"] for entry in cal["fomc"]] == [d.isoformat() for d in expected_dates]
    assert list(cal["fomc"]) == sorted(cal["fomc"], key=lambda e: e["date"])
    # Every entry carries the same plain-language label "Fed rate decision".
    assert all(entry["label"] == "Fed rate decision" for entry in cal["fomc"])
    # Authority block still five-false (the new key does not promote authority).
    _assert_false_authority(env["authority"])


def test_j_no_stage_envelope_still_carries_macro_calendar(monkeypatch, tmp_path):
    """A-F03-W3-2: on an events-stage outage, the chip must NOT vanish.  The
    calendar is built from engine.event_calendar (which is independent of the
    events stage), so a missing events stage → `macro_calendar` is still
    populated, and `states` carries `no_event_stage` exactly as before."""
    monkeypatch.setattr(prod, "utc_today", lambda: ASOF)
    monkeypatch.setattr(prod, "fetch_event_stage", lambda _session: None)
    rc = prod.main(["--session", SESSION, "--out", str(tmp_path)])
    assert rc == 0
    env = json.loads((tmp_path / "latest.json").read_text())
    assert env["states"] == ["no_event_stage"]
    assert env["links"] == []
    cal = env["macro_calendar"]
    assert cal["asof"] == "2026-09-04"
    assert cal["source"] == "engine.event_calendar"
    # Calendar must still carry every FOMC date in the window, sorted.
    expected_dates = fomc_decision_dates(date(2026, 9, 4), date(2026, 11, 6))
    assert [entry["date"] for entry in cal["fomc"]] == [d.isoformat() for d in expected_dates]
    assert list(cal["fomc"]) == sorted(cal["fomc"], key=lambda e: e["date"])
    assert all(entry["label"] == "Fed rate decision" for entry in cal["fomc"])
    # Authority still five-false on the no-stage path.
    _assert_false_authority(env["authority"])


def test_k_macro_calendar_filters_non_fomc_kinds():
    """A-F03-W3-2 (MAJOR 1): `_macro_calendar` only emits entries whose
    candidate.kind == "fomc" — the envelope key is named `fomc` and labels
    every entry "Fed rate decision"; a non-fomc candidate must NOT leak
    through with a Fed label.  RED-first: this test fails on the
    round-3 head (no filter) — a `cpi` candidate appears in the FOMC list
    with the wrong date AND the wrong label."""
    real_fomc_dates = fomc_decision_dates(date(2026, 9, 4), date(2026, 11, 6))
    base = [CatalystCandidate(
        kind="fomc", date=d, source="event_calendar", artifact="engine.event_calendar._FOMC",
        stale=False, known_as_of=date(d.year - 1, 6, 1), as_of_age_td=0,
        label="FOMC rate decision", locator=f"event_calendar:fomc:{d.isoformat()}",
    ) for d in real_fomc_dates]
    cpi = CatalystCandidate(
        kind="cpi", date=date(2026, 9, 15), source="event_calendar",
        artifact="engine.event_calendar._CPI", stale=False,
        known_as_of=date(2026, 6, 1), as_of_age_td=0,
        label="CPI release", locator="event_calendar:cpi:2026-09-15",
    )
    nfp = CatalystCandidate(
        kind="nfp", date=date(2026, 10, 2), source="event_calendar",
        artifact="engine.event_calendar._NFP", stale=False,
        known_as_of=date(2026, 6, 1), as_of_age_td=0,
        label="Nonfarm payrolls", locator="event_calendar:nfp:2026-10-02",
    )
    cal = prod._macro_calendar(date(2026, 9, 4), 63, candidates=base + [cpi, nfp])
    fomc_entries = cal["fomc"]
    # Only fomc-kind candidates land in the dict; the cpi/nfp entries are dropped.
    assert [e["date"] for e in fomc_entries] == [d.isoformat() for d in real_fomc_dates]
    assert "2026-09-15" not in [e["date"] for e in fomc_entries], "CPI date leaked into fomc"
    assert "2026-10-02" not in [e["date"] for e in fomc_entries], "NFP date leaked into fomc"
    assert all(e["label"] == "Fed rate decision" for e in fomc_entries)


def test_decision_receipts_unwrap_and_availability_is_not_an_event(monkeypatch, tmp_path):
    event = _event("e-receipt", "AAPL", "2026-09-11")
    rows = [
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "decision",
            "event_id": "e-receipt",
            "event": event,
        },
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "availability",
            "event_id": "e-receipt",
            "available_at": "2026-09-04T18:05:00Z",
        },
        {"schema": "live_flow.event_stage/v1", "kind": "decision", "event_id": "bad", "event": {"id": "bad"}},
    ]
    rc, env, records, _calls = _bind(
        monkeypatch, tmp_path, rows, {"AAPL"}, {"AAPL": _fresh("2026-09-08", age=2)},
    )
    assert rc == 0
    assert env["counts"]["events"] == 2
    assert env["counts"]["dropped_malformed"] == 1
    assert [row["event_id"] for row in records] == ["e-receipt"]
    assert records[0]["binding_state"] == "BOUND"


def test_session_defaults_to_latest_retained_on_or_before_today(monkeypatch, tmp_path):
    seen = {}

    def _fetch(session):
        seen["session"] = session
        return []

    monkeypatch.setattr(prod, "utc_today", lambda: date(2026, 9, 5))
    monkeypatch.setattr(prod, "discover_event_sessions", lambda: ["2026-09-02", "2026-09-04", "2026-09-09"])
    monkeypatch.setattr(prod, "fetch_event_stage", _fetch)
    monkeypatch.setattr(prod, "symbols_on_plane", lambda plane_id, repo_root=None: {"AAPL"})
    rc = prod.main(["--out", str(tmp_path)])
    assert rc == 0
    assert seen["session"] == "2026-09-04"
    env = json.loads((tmp_path / "latest.json").read_text())
    assert env["states"] == ["ok"]
    assert env["session_date"] == "2026-09-04"


def test_no_retained_date_is_no_event_stage(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(prod, "utc_today", lambda: date(2026, 9, 5))
    monkeypatch.setattr(prod, "discover_event_sessions", lambda: ["2026-09-09"])
    rc = prod.main(["--out", str(tmp_path)])
    assert rc == 0
    env = json.loads((tmp_path / "latest.json").read_text())
    assert env["states"] == ["no_event_stage"]
    assert env["links"] == []
    assert env["session_date"] is None
    assert env["links_path"] is None
    summaries = [line for line in capsys.readouterr().out.splitlines() if line.startswith("options_catalyst_links:")]
    assert summaries == ["options_catalyst_links: session=none events=0 bound=0 unbound=0 unresolved=0"]


def _friday_earnings_frame() -> pd.DataFrame:
    """One fresh row whose ``as_of`` is Friday 2026-09-04. No store file."""
    return pd.DataFrame(
        {
            "next_date": ["2026-09-16"],
            "next_time": ["amc"],
            "as_of": ["2026-09-04"],
        },
        index=pd.Index(["AAPL"]),
    )


def _bind_live_assessment(monkeypatch, tmp_path, rows, *, session, asof, frame):
    """Run the producer against ``assess``, not an injected age."""
    prod.earnings_blackout.clear_cache()
    monkeypatch.setattr(prod.earnings_blackout, "_load_store", lambda store_path=None: frame)
    monkeypatch.setattr(prod, "utc_today", lambda: asof)
    monkeypatch.setattr(prod, "fetch_event_stage", lambda _session: rows)
    monkeypatch.setattr(prod, "symbols_on_plane", lambda plane_id, repo_root=None: {"AAPL"})
    rc = prod.main(["--session", session, "--out", str(tmp_path)])
    envelope = json.loads((tmp_path / "latest.json").read_text())
    records = _records(tmp_path / f"{session}.jsonl")
    prod.earnings_blackout.clear_cache()
    return rc, envelope, records


def test_assess_business_day_age_stamps_friday_not_the_prior_session(monkeypatch, tmp_path):
    """A Friday earnings row stays Friday when the run is Saturday or Labor Day.

    ``assess`` reports age 1 for both dates: a weekend already sits on the next
    weekday, and that Monday stays on the business-day index. The stamp is
    Friday. An event on Thursday then loses the earnings link, and the FOMC
    date on the same day wins. Walking sessions back from the last session
    stamps Thursday and keeps the earnings link.
    """
    frame = _friday_earnings_frame()
    prod.earnings_blackout.clear_cache()
    monkeypatch.setattr(prod.earnings_blackout, "_load_store", lambda store_path=None: frame)
    try:
        saturday = prod.earnings_blackout.assess("AAPL", today=date(2026, 9, 5))
        labor_day = prod.earnings_blackout.assess("AAPL", today=date(2026, 9, 7))
    finally:
        prod.earnings_blackout.clear_cache()
    assert saturday["as_of_age_td"] == 1
    assert saturday["stale"] is False
    assert labor_day["as_of_age_td"] == 1
    assert labor_day["stale"] is False

    def _earnings(record):
        return [row for row in record["candidates"] if row["kind"] == "earnings"][0]

    friday_event = _event("e-fri", "AAPL", "2026-10-16", ts="2026-09-04T18:00:00Z")
    thursday_event = _event("e-thu", "AAPL", "2026-10-16", ts="2026-09-03T18:00:00Z")

    sat_rc, _sat_env, sat_rows = _bind_live_assessment(
        monkeypatch,
        tmp_path / "sat",
        [friday_event, thursday_event],
        session="2026-09-04",
        asof=date(2026, 9, 5),
        frame=frame,
    )
    assert sat_rc == 0
    sat_by_id = {row["event_id"]: row for row in sat_rows}
    sat_fri = sat_by_id["e-fri"]
    assert sat_fri["binding_state"] == "BOUND"
    assert sat_fri["catalyst"]["kind"] == "earnings"
    assert sat_fri["catalyst"]["known_as_of"] == "2026-09-04"
    assert sat_fri["catalyst"]["as_of_age_td"] == 1
    sat_earn = _earnings(sat_fri)
    assert sat_earn["known_as_of"] == "2026-09-04"
    assert sat_earn["exclusion_reason"] is None
    assert sat_earn["trusted"] is True
    assert any(item["kind"] == "fomc" for item in sat_fri["catalyst"].get("co_dated", []))

    sat_thu = sat_by_id["e-thu"]
    assert sat_thu["catalyst"]["kind"] == "fomc"
    assert sat_thu["binding_state"] == "BOUND"
    thu_earn = _earnings(sat_thu)
    assert thu_earn["known_as_of"] == "2026-09-04"
    assert thu_earn["exclusion_reason"] == "LOOKAHEAD_EXCLUDED"
    assert thu_earn["trusted"] is False

    mon_rc, _mon_env, mon_rows = _bind_live_assessment(
        monkeypatch,
        tmp_path / "mon",
        [friday_event, thursday_event],
        session="2026-09-04",
        asof=date(2026, 9, 7),
        frame=frame,
    )
    assert mon_rc == 0
    mon_by_id = {row["event_id"]: row for row in mon_rows}
    assert mon_by_id["e-fri"]["catalyst"]["known_as_of"] == "2026-09-04"
    assert mon_by_id["e-fri"]["catalyst"]["kind"] == "earnings"
    assert mon_by_id["e-thu"]["catalyst"]["kind"] == "fomc"
    mon_earn = _earnings(mon_by_id["e-thu"])
    assert mon_earn["known_as_of"] == "2026-09-04"
    assert mon_earn["exclusion_reason"] == "LOOKAHEAD_EXCLUDED"

    # A weekday age of 0 is the run date itself. That stamp is after this
    # Wednesday event, so the earnings row stays excluded.
    early = _event("e-early", "AAPL", "2026-09-11", ts="2026-09-02T18:00:00Z")
    late_rc, _late_env, late_rows, _late_calls = _bind(
        monkeypatch,
        tmp_path / "late",
        [early],
        {"AAPL"},
        {"AAPL": _fresh("2026-09-08", age=0)},
        session="2026-09-04",
        asof=date(2026, 9, 4),
    )
    assert late_rc == 0
    late_earn = _earnings(late_rows[0])
    assert late_earn["known_as_of"] == "2026-09-04"
    assert late_earn["exclusion_reason"] == "LOOKAHEAD_EXCLUDED"
    assert late_earn["trusted"] is False
    assert late_rows[0]["binding_state"] == "STALE_CATALYST"


def test_bad_strike_is_not_swallowed(monkeypatch, tmp_path):
    monkeypatch.setattr(prod, "utc_today", lambda: ASOF)
    monkeypatch.setattr(
        prod,
        "fetch_event_stage",
        lambda _session: [{"id": "e1", "root": "AAPL", "exp": "2026-10-16"}],
    )
    monkeypatch.setattr(prod, "symbols_on_plane", lambda plane_id, repo_root=None: {"AAPL"})
    monkeypatch.setattr(prod.earnings_blackout, "assess", lambda *args, **kwargs: _fresh("2026-09-16"))
    with pytest.raises(ContractKeyError):
        prod.main(["--session", SESSION, "--out", str(tmp_path)])
