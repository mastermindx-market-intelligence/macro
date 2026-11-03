"""Regression cases for the GOOG contract question and the two distinct options clocks."""
from datetime import date
import json

import pytest

from app import hub, options_auth
from engine.neuralweb import ask_brain, brain_gateway, options_evidence
from scripts import topup_thetadata_day as topup


def test_topup_retains_enrolled_roots(tmp_path, monkeypatch):
    from engine import options_universe
    monkeypatch.setattr(options_universe, "gex_symbols", lambda: ["GOOGL"])
    monkeypatch.setattr(options_universe, "baskets_universe", lambda: ["GOOG", "GOOGL", "NEW"])
    (tmp_path / "_backfill_state.json").write_text(json.dumps({
        "version": 1, "completed": {"BABA": ["2025"], "DEFUNCT": ["2020"], "../BAD": ["2026"]},
    }))
    for symbol, year in [("BABA", 2026), ("DEFUNCT", 2020)]:
        folder = tmp_path / "eod" / symbol
        folder.mkdir(parents=True)
        (folder / f"{year}.parquet").touch()
    roots = topup._maintained_roots(tmp_path, date(2026, 11, 2), topup._daily_universe())
    assert all(roots.count(root) == 1 for root in ["GOOGL", "BABA"])
    assert "DEFUNCT" not in roots and "../BAD" not in roots


def test_mixed_family_dates_do_not_revive_old_volatility():
    row = {"as_of": "2026-11-02", "src_skew_asof": "2026-11-02", "skew": 0.1,
           "src_gex_asof": "2026-08-21", "iv30": 30, "pin_risk": True,
           "src_flow_asof": "2030-01-01", "net_doi": 3}
    out = options_evidence.current_state(row, date(2026, 11, 2))
    assert out["iv30"] is None and out["pin_risk"] is None and out["net_doi"] is None
    assert out["skew"] == 0.1 and out["source_status"]["gex"] == "historical"


def test_screenshot_contract_wording_selects_options():
    query = "Would you recommend doing a $280 strike sell put with end of November expiry on GOOG? Tell me in chinese"
    assert ask_brain._question_profile(query, "GOOG").name == "options_single_name"


@pytest.fixture
def vol_book():
    return {"schema": "options_hub.vol/v1", "asof": "2026-10-30", "root": "GOOG",
            "atm_iv": 30, "iv_rank_252": 0,
            "term": [{"exp": "2026-11-27", "atm_iv": 32}],
            "smile": [{"exp": "2026-11-27", "points": [{"strike": 280, "call_iv": 31, "put_iv": 33}]}]}


def test_expiry_side_strike_and_source_clock_are_independent(monkeypatch, vol_book):
    monkeypatch.setattr(hub, "hub_vol", lambda root: vol_book)
    sel = {"expiration": "2026-11-27", "strike": 280, "right": "put"}
    read = lambda params: options_evidence.hub_volatility("GOOG", params, date(2026, 11, 2))
    selected = read(sel)
    assert selected["status"] == "historical" and selected["iv_percentile_252"] == 0
    assert selected["selected_smile_point"]["iv_pct"] == 33
    assert read({**sel, "expiration": "2026-11-20"})["selected_smile_point"]["iv_pct"] is None
    assert read({**sel, "strike": 285})["selected_smile_point"]["iv_pct"] is None
    assert read({**sel, "expiration": "2026-11"})["expiry_observations"] == [
        {"expiration": "2026-11-27", "atm_iv_pct": 32}]
    assert "selected_smile_point" not in read({**sel, "expiration": "2026-11"})
    vol_book["smile"] = vol_book["smile"] * 2
    assert read(sel)["selected_smile_point"]["iv_pct"] is None
    vol_book["root"] = "GOOGL"
    assert read(sel)["status"] == "unavailable"


def test_empty_success_and_resolved_member_boundary(tmp_path, monkeypatch):
    reads = []
    def empty(root):
        reads.append(root)
        return {"schema": "options_hub.vol/v1", "asof": "2026-10-29", "root": root,
                "atm_iv": None, "smile": [], "term": []}
    monkeypatch.setattr(hub, "hub_vol", empty)
    monkeypatch.setattr(options_auth, "options_product_allowed", lambda uid: uid == "member")
    def dispatch(uid):
        return brain_gateway._dispatch_brain_tool("explain_options_context", {"ticker": "GOOG"},
                                                  tmp_path, tmp_path, "", user_id=uid)
    assert "volatility_evidence" not in dispatch("guest:sample") and not reads
    evidence = dispatch("member")["volatility_evidence"]
    assert evidence["options_hub"]["status"] == "no_observations"
    assert evidence["exact_contract_quote"] == "unavailable"
    assert reads == ["GOOG"]


def test_terminal_catalog_filters_market_type_and_exact_share_class():
    from engine.terminal_options_universe import match_catalogs
    data = {"as_of": "2026-10-31", "symbols": {
        "GOOG": {"sec": "Equities", "mkt": "NASDAQ"},
        "GOOGL": {"sec": "Equities", "mkt": "NASDAQ"},
        "OTHER": {"sec": "Equities", "mkt": "HKEX"},
        "FUT": {"sec": "Futures", "mkt": "US"},
        "ETF": {"sec": "Funds", "mkt": "US"},
        "CBOECO": {"sec": "Equities", "mkt": "Cboe"},
        "../BAD": {"sec": "Equities", "mkt": "US"},
    }}
    symbols, receipt = match_catalogs(data, {"GOOG", "OTHER", "FUT", "ETF", "CBOECO", "../BAD"}, date(2026, 11, 2))
    assert symbols == {"GOOG", "ETF", "CBOECO"} and receipt["unmatched_roots"] == 1
    with pytest.raises(ValueError, match="clock"):
        match_catalogs(data, symbols, date(2026, 11, 30))


def test_terminal_extension_uses_remaining_budget_and_reports_unreached(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from engine import options_universe, terminal_options_universe
    monkeypatch.setattr(terminal_options_universe, "terminal_candidates",
                        lambda _day, _deadline: ({"GOOG", "GOOGL", "THIN"}, {"matched_roots": 3}))
    monkeypatch.setattr(options_universe, "baskets_universe", lambda: ["GOOG", "BASKET"])
    monkeypatch.setattr(topup._time, "monotonic", lambda: 300)
    ctx = topup.RunContext(date(2026, 11, 2), date(2026, 10, 30), False)
    present = {"eod_S": "complete", "oi_S": "complete", "greeks_S": "complete"}
    def pool(store, roots, td, *, workers, deadline_min, ctx):
        assert set(roots) == {"GOOG", "THIN", "BASKET"}
        assert deadline_min == 2 and workers == 2
        return {"GOOG": topup.RootResult("GOOG", "complete", present)}, True, False
    monkeypatch.setattr(topup, "_run_daily_pool", pool)
    prior = {"GOOGL": topup.RootResult("GOOGL", "already_present", present)}
    start = datetime(2026, 11, 2, 22, tzinfo=timezone.utc)
    receipt = topup._terminal_session_coverage(tmp_path, ctx, None, 2, 420, prior, start)
    assert receipt["status"] == "partial" and receipt["not_reached"] == 1
    assert receipt["full_settled_panel"] == 2 and receipt["inspected"] == 2
    assert topup._terminal_session_coverage(tmp_path, ctx, None, 2, 290, prior, start)["status"] == "deferred"
