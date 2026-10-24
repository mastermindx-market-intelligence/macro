"""Operational retirement contract for the three superseded US books.

Historical state remains in the registry and per-book APIs. These tests pin the other half of the
contract: no runner, cron, retry, mark, settle, overnight watch, de-risk sweep, or firm allocator may
treat an archived book as live.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_registry_keeps_history_but_separates_storage_and_product_defaults():
    from portfolio import registry

    assert registry.DEFAULT_ID == "flagship"
    assert registry.DASHBOARD_DEFAULT_ID == "autonomous"
    assert registry.data_dir(None) == registry.data_dir("flagship")
    assert set(registry.ids()) >= {"flagship", "heavyweight", "etf", "autonomous"}
    assert set(registry.active_ids(include_self_directed=False)) == {"autonomous", "china", "hk"}
    for pid in ("flagship", "heavyweight", "etf"):
        meta = registry.get(pid)
        assert meta["active"] is False
        assert meta["status"] == "archived"
        assert meta["superseded_by"] == "autonomous"


def test_archived_dashboard_reads_are_frozen_local_and_write_nothing(tmp_path, monkeypatch):
    """Every archived dashboard surface must agree on the last persisted mark without feeds."""
    from app import web
    from data_layer import yahoo_feed
    from portfolio import market_calendar, market_sessions, paper_account, position_log, registry, safety

    monkeypatch.setattr(registry, "_ROOT", tmp_path)
    book = registry.data_dir("heavyweight")
    book.mkdir(parents=True)
    (book / "latest.json").write_text(json.dumps({
        "schema": "portfolio.v1", "portfolio_id": "heavyweight", "as_of": "2026-08-07",
        "nav": 1_020_000.0, "cash_usd": 420_000.0, "summary": "Final archived book.",
        "positions": [{
            "ticker": "AAPL", "shares": 5_000.0, "cost_basis": 100.0,
            "current_price": 120.0, "market_value": 600_000.0,
            "unrealized_pnl": 100_000.0, "unrealized_pct": 20.0, "weight": 0.588235,
        }], "decisions": [], "rejected": [],
    }))
    (book / "account.json").write_text(json.dumps({
        "inception_date": "2026-08-06", "starting_nav": 1_000_000.0,
        "cash": 420_000.0, "positions": {"AAPL": {
            "shares": 5_000.0, "avg_cost": 100.0, "current_price": 120.0,
        }},
    }))
    (book / "nav_history.jsonl").write_text("\n".join((
        json.dumps({"date": "2026-08-06", "nav": 1_000_000.0, "cash": 400_000.0,
                    "invested": 600_000.0, "spy_nav": 1_000_000.0, "benchmark": "SPY"}),
        json.dumps({"date": "2026-08-07", "nav": 1_020_000.0, "cash": 420_000.0,
                    "invested": 600_000.0, "spy_nav": 1_010_000.0, "benchmark": "SPY"}),
    )) + "\n")
    (book / "safety.json").write_text(json.dumps({
        "portfolio_id": "heavyweight", "safety_score": 77, "grade": "B",
        "verdict": "Final risk snapshot.",
    }))
    (book / "fills.jsonl").write_text(json.dumps({
        "date": "2026-08-06", "ticker": "AAPL", "side": "buy", "shares": 5_000.0,
        "price": 100.0, "value": 500_000.0,
    }) + "\n")
    (book / "positions_ledger.json").write_text(json.dumps({
        "brain:AAPL": {
            "ticker": "AAPL", "sleeve": "brain", "opened_at": "2026-08-06T20:00:00+00:00",
            "still_open": True, "entry_weight": 0.5, "current_weight": 0.588235,
            "entry_price": 100.0, "history": [],
        },
    }))
    before = {path.name: path.read_bytes() for path in book.iterdir()}

    def forbidden(*args, **kwargs):
        raise AssertionError("archived read reached live valuation, quote, or write path")

    monkeypatch.setattr(web, "_book_marks", forbidden)
    monkeypatch.setattr(web, "_live_prices", forbidden)
    monkeypatch.setattr(web, "_quote_provenance", forbidden)
    monkeypatch.setattr(web, "_attach_security_names", lambda rows: None)
    monkeypatch.setattr(yahoo_feed, "warm", forbidden)
    monkeypatch.setattr(market_sessions, "status_for_portfolio", forbidden)
    monkeypatch.setattr(market_calendar, "status", forbidden)
    monkeypatch.setattr(paper_account, "performance", forbidden)
    monkeypatch.setattr(paper_account, "positions_pnl", forbidden)
    monkeypatch.setattr(paper_account, "nav", forbidden)
    monkeypatch.setattr(paper_account, "load_pending", forbidden)
    monkeypatch.setattr(position_log, "open_positions", forbidden)
    monkeypatch.setattr(position_log, "closed_positions", forbidden)
    monkeypatch.setattr(safety, "compute_safety", forbidden)
    monkeypatch.setattr(safety, "persist", forbidden)

    performance = json.loads(web.api_performance("heavyweight").body)
    live = json.loads(web.api_live_marks("heavyweight").body)
    portfolio = json.loads(web.api_portfolio("heavyweight").body)
    switcher = web._portfolio_status(registry.get("heavyweight"))
    risk = json.loads(web.api_risk("heavyweight", recompute=True).body)
    trades = json.loads(web.api_trades("heavyweight").body)

    assert performance["current_nav"] == 1_020_000.0
    assert performance["series"][-1]["date"] == "2026-08-07"
    assert performance["series"][-1]["nav"] == 1_020_000.0
    assert live["archived"] is True and live["poll_after_seconds"] is None
    assert live["positions"][0]["current_price"] == 120.0
    assert live["positions"][0]["quote_source"] == "archived_snapshot"
    assert portfolio["account_preview"]["current_nav"] == 1_020_000.0
    assert portfolio["positions"][0]["current_price"] == 120.0
    assert switcher["status"]["nav"] == 1_020_000.0
    assert switcher["status"]["as_of"] == "2026-08-07"
    assert risk["safety_score"] == 77 and risk["snapshot_only"] is True
    assert trades["archived"] is True and trades["market"]["session"] == "archived"
    assert trades["history"][0]["unrealized_pnl"] == 100_000.0
    assert trades["open"][0]["held_days"] == 1
    assert {path.name: path.read_bytes() for path in book.iterdir()} == before


def test_archived_risk_without_snapshot_does_not_recompute_or_create_file(tmp_path, monkeypatch):
    from app import web
    from portfolio import registry, safety

    monkeypatch.setattr(registry, "_ROOT", tmp_path)
    path = registry.data_dir("etf") / "safety.json"
    monkeypatch.setattr(
        safety, "compute_safety",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not compute")),
    )
    monkeypatch.setattr(
        safety, "persist",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not persist")),
    )

    payload = json.loads(web.api_risk("etf", recompute=True).body)
    assert payload["archived"] is True
    assert payload["snapshot_only"] is True
    assert payload["safety_score"] is None
    assert not path.exists()


def test_nightly_safety_batch_is_active_only(monkeypatch):
    from portfolio import registry, safety

    computed: list[str] = []
    persisted: list[str] = []

    def compute(pid, asof=None, bootstrap=True):
        computed.append(pid)
        return {"safety_score": 80, "grade": "A", "source": "fixture", "n_positions": 1}

    monkeypatch.setattr(safety, "compute_safety", compute)
    monkeypatch.setattr(safety, "persist", lambda report, pid=None: persisted.append(pid))
    out = safety.safety_for_all("2026-08-08", bootstrap=False)

    assert computed == registry.active_ids()
    assert persisted == registry.active_ids()
    assert set(out["portfolios"]) == set(registry.active_ids())
    assert not ({"flagship", "heavyweight", "etf"} & set(out["portfolios"]))


def test_direct_legacy_runners_fail_closed_before_work():
    from bot.daily import run_daily
    from bot.heavyweight import run_heavyweight
    from bot.etf import run_etf
    from bot.phase2 import run, run_flagship

    daily = run_daily(asof="2026-08-08")
    assert daily["skipped"] == "portfolio_archived"
    assert daily["book"]["ran"] is False

    for out in (
        run_heavyweight(asof="2026-08-08"),
        run_etf(asof="2026-08-08"),
        run_flagship(asof="2026-08-08"),
        run(asof="2026-08-08"),
    ):
        assert out["skipped"] == "portfolio_archived"
        assert out["superseded_by"] == "autonomous"


def test_archived_desk_mcp_cannot_submit_or_clear_pending_state(tmp_path, monkeypatch):
    from brain import etf_mcp, flagship_desk_mcp, heavyweight_mcp
    from portfolio import registry

    monkeypatch.setattr(registry, "_ROOT", tmp_path)
    for module in (flagship_desk_mcp, heavyweight_mcp, etf_mcp):
        pending = module.submission_path()
        pending.parent.mkdir(parents=True, exist_ok=True)
        prior = '{"holdings": [{"ticker": "KEEP"}]}'
        pending.write_text(prior)

        module.clear_submission()
        assert pending.read_text() == prior

        result = asyncio.run(module.submit_book.handler({
            "holdings": [{"ticker": "SPY", "weight": 1.0, "rationale": "must not write"}],
            "summary": "must not write",
        }))
        assert "portfolio_archived" in result["content"][0]["text"]
        assert pending.read_text() == prior
        assert not any(name.endswith("__submit_book") for name in module.allowed_tools())


@pytest.mark.parametrize("book", ["flagship", "flagship_judgment", "heavyweight", "etf"])
def test_archived_stdio_mcp_surface_fails_closed(book):
    from brain import codex_mcp_stdio

    with pytest.raises(SystemExit, match="archived"):
        codex_mcp_stdio._servers_for(book)


@pytest.mark.parametrize(
    ("module", "label"),
    [("bot.heavyweight", "Heavyweight is archived"), ("bot.etf", "ETF Brain is archived")],
)
def test_archived_module_clis_report_status_and_exit_zero(module, label):
    root = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root)
    result = subprocess.run(
        [sys.executable, "-m", module, "--offline"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert label in result.stdout
    assert "successor: autonomous" in result.stdout


def test_deploy_includes_reasoning_subagent_policies_and_rollback_state():
    script = (Path(__file__).resolve().parent.parent / "scripts" /
              "deploy_code_to_vps.sh").read_text()
    dirs = next(line for line in script.splitlines() if line.startswith('DIRS="'))
    assert ".claude" in dirs and ".codex" in dirs
    assert "--exclude='.claude'" not in script
    assert "--exclude='.codex'" not in script
    rollback = script.split("rollback_release()", 1)[1]
    assert "A directory introduced by the failed release" in rollback
    assert 'rm -rf \\\"\\$d\\\"' in rollback
    assert "reasoning_policy_ok" in script
    assert 'CODE="$(probe_health "$EXPECTED_SHA")"' in script
    assert 'CODE="$(probe_health "$PREVIOUS_SHA" 0)"' in script
    assert "scheduled_runtime_ok" in script
    assert 'fail_release "rsync did not complete"' in script
    assert 'fail_release "release marker write failed"' in script
    assert 'fail_release "service restart failed"' in script


def test_current_firm_exposure_ignores_archived_books(tmp_path, monkeypatch):
    from portfolio import firm_exposure, registry

    monkeypatch.setattr(registry, "_ROOT", tmp_path)
    monkeypatch.setattr(firm_exposure, "_ROOT", tmp_path)

    def seed(pid: str, ticker: str, weight: float) -> None:
        d = registry.data_dir(pid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "latest.json").write_text(json.dumps({
            "portfolio_id": pid,
            "nav": 1_000_000,
            "positions": [{"ticker": ticker, "weight": weight}],
        }))

    seed("flagship", "NVDA", 0.8)
    seed("heavyweight", "NVDA", 0.8)
    seed("etf", "SMH", 0.8)
    seed("autonomous", "AAPL", 0.2)

    out = firm_exposure.summary()
    assert [b["id"] for b in out["books"]] == ["autonomous"]
    assert {row["ticker"] for row in out["top_exposures"]} == {"AAPL"}


def test_default_shadow_allocation_eligibility_is_active_only():
    import importlib

    module = importlib.import_module("portfolio." + "firm_" + "allocator")
    out = module._compute({}, {}, {})
    assert set(out["books"]) == {"autonomous", "china", "hk"}
    assert out["firm"]["n_eligible"] == 3


def test_us_operational_fanout_contains_only_successor(monkeypatch):
    import importlib

    derisk = importlib.import_module("bot.derisk")
    overnight = importlib.import_module("bot.overnight")
    settle = importlib.import_module("bot.settle")

    settle_calls: list[str] = []
    monkeypatch.setattr(settle, "settle_open",
                        lambda pid, asof=None: settle_calls.append(pid) or {"ok": True})
    assert set(settle.settle_us("2026-08-08")) == {"autonomous"}
    assert settle_calls == ["autonomous"]

    monkeypatch.setattr(derisk, "enabled", lambda: True)
    derisk_calls: list[str] = []
    monkeypatch.setattr(derisk, "derisk_brain",
                        lambda pid, asof=None: derisk_calls.append(pid) or {"action": "hold"})
    assert set(derisk.sweep_us("2026-08-08")) == {"autonomous"}
    assert derisk_calls == ["autonomous"]

    watch_calls: list[str] = []
    monkeypatch.setattr(overnight, "watch",
                        lambda pid, asof=None: watch_calls.append(pid) or {"pid": pid})
    assert set(overnight.watch_us("2026-08-08")) == {"autonomous"}
    assert watch_calls == ["autonomous"]
    assert set(overnight._RUNNERS) == {"autonomous", "china", "hk"}


def test_direct_archived_execution_and_settlement_are_read_only(monkeypatch):
    """Even an old script importing the shared settlement helpers cannot mutate a retired book."""
    from bot import settle
    from portfolio import paper_account

    monkeypatch.setattr(
        paper_account, "save_pending_target",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not write")),
    )
    queued = settle.execute_or_queue(
        "etf", {"SPY": 1.0}, {"SPY": 100.0}, "2026-08-08", market_open=False)
    assert queued["skipped"] == "portfolio_archived"
    assert queued["queued"] is False

    monkeypatch.setattr(settle, "is_open",
                        lambda pid: (_ for _ in ()).throw(AssertionError("must not read market")))
    filled = settle.settle_open("flagship", "2026-08-08")
    assert filled["skipped"] == "portfolio_archived"
    assert filled["ok"] is False

    from scripts import fill_pending_now
    rescued = fill_pending_now.settle("flagship", log=lambda message: None)
    assert rescued["skipped"] == "portfolio_archived"
    assert rescued["filled"] == 0


def test_direct_archived_derisk_cutters_are_read_only(monkeypatch):
    from bot import derisk

    monkeypatch.setattr(
        derisk, "tripwire",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not inspect risk")),
    )
    for pid, fn in (
        ("flagship", derisk.derisk_flagship),
        ("heavyweight", derisk.derisk_heavyweight),
        ("etf", lambda asof, force: derisk.derisk_brain("etf", asof, force=force)),
    ):
        out = fn("2026-08-08", force=True)
        assert out["pid"] == pid
        assert out["skipped"] == "portfolio_archived"


def test_archived_manual_run_routes_return_410(monkeypatch):
    from fastapi.testclient import TestClient
    from app import auth
    from app.main import app

    monkeypatch.setattr(auth, "serve_only", lambda: False)
    monkeypatch.setattr(auth, "is_operator_authorized", lambda request: True)
    client = TestClient(app, raise_server_exceptions=True)

    for path in ("/daily", "/api/heavyweight/run", "/api/etf/run"):
        auth.reset_rate_buckets()
        response = client.post(path)
        assert response.status_code == 410, (path, response.text)
        detail = response.json()["detail"]
        assert detail["error"] == "portfolio_archived"
        assert detail["superseded_by"] == "autonomous"


def test_scheduler_registers_no_archived_book_jobs(monkeypatch):
    from app import scheduler

    monkeypatch.setenv("MASTERMIND_JOBSTORE", "memory")
    monkeypatch.setattr(scheduler, "_scheduler", None)
    sch = scheduler.start()
    if sch is None:
        return
    try:
        ids = {job.id for job in sch.get_jobs()}
        assert "autonomous_daily" in ids
        assert not (set(scheduler._ARCHIVED_BOOK_JOBS) & ids)
        assert scheduler._BRAIN_RETRY_JOBS == {
            "autonomous_daily": "autonomous",
            "china_daily": "china",
            "hk_daily": "hk",
        }
        assert scheduler._MARK_BOOK_IDS == ["autonomous", "china", "hk"]
    finally:
        sch.shutdown(wait=False)
        scheduler._scheduler = None


def test_stale_scheduler_wrappers_and_first_runs_fail_closed(monkeypatch):
    from app import scheduler
    from bot import daily, etf, heavyweight
    from control_plane import run_events

    def forbidden(*args, **kwargs):
        raise AssertionError("archived runner must not be reached")

    monkeypatch.setattr(daily, "run_daily", forbidden)
    monkeypatch.setattr(etf, "run_etf", forbidden)
    monkeypatch.setattr(heavyweight, "run_heavyweight", forbidden)
    monkeypatch.setattr(run_events, "append", lambda event: None)
    monkeypatch.setattr(scheduler, "_ledger_start", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "_ledger_end", lambda *args, **kwargs: None)

    assert scheduler._job() is None
    assert scheduler._heavyweight_job() is None
    assert scheduler._etf_job() is None
    assert scheduler.maybe_first_heavyweight_run() is False
    assert scheduler.maybe_first_etf_run() is False

    health = {row["id"]: row for row in scheduler.scheduler_health()}
    for job_id in ("daily_loop", "heavyweight_daily", "etf_daily"):
        assert health[job_id]["archived"] is True
        assert health[job_id]["status"] == "archived"
        assert health[job_id]["next_run_time"] is None
