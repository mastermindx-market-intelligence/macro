"""Offline request planning: no provider calls, credentials, or archive writes."""
from datetime import date
import json

import pytest
import scripts.tiingo_ingest as ing

D0, D1 = date(2020, 1, 1), date(2020, 1, 10)


@pytest.mark.parametrize("source", ["distributions", "splits"])
def test_corporate_action_filters_use_ex_dates(source):
    result = ing.plan([source], ["AMD"], D0, D1)
    assert result[0].params == {"startExDate": D0.isoformat(), "endExDate": D1.isoformat()}


def test_forex_and_crypto_resolution_is_explicit():
    for source, symbols in [("forex-bars", ["eurusd"]), ("crypto-bars", ["btcusd"])]:
        tasks = ing.plan([source], symbols, D0, D1)
        assert all(t.params["resampleFreq"] == "1min" for t in tasks)


@pytest.mark.parametrize("source", ["fund-statements", "fund-daily", "distributions", "news", "eod-bars"])
def test_reversed_dates_never_silently_plan(source):
    with pytest.raises(ValueError):
        ing.plan([source], ["AMD"], D1, D0)


@pytest.mark.parametrize("days", [0, -1, True, 367])
def test_invalid_chunk_size_is_not_coerced_to_default(days):
    with pytest.raises(ValueError):
        ing.plan(["eod-bars"], ["AMD"], D0, D1, chunk_override=days)


def test_date_max_interval_finishes_without_overflow():
    assert list(ing.date_ranges(date.max, date.max, 7)) == [(date.max, date.max)]


def test_duplicate_sources_and_symbols_do_not_multiply_tasks():
    tasks = ing.plan(["eod-bars", "eod-bars"], ["AMD", "AMD"], D0, D1)
    assert len(tasks) == 1


def test_case_distinct_source_identifiers_remain_distinct():
    assert ing.load_symbols("idA,ida,idA", None) == ["idA", "ida"]


def test_large_crypto_universe_is_split_into_bounded_queries():
    symbols = [f"coin{i}usd" for i in range(100)]
    tasks = ing.plan(["crypto-bars"], symbols, D0, D0)
    requested = [s for t in tasks for s in t.params["tickers"].split(",")]
    assert requested == symbols
    assert len(tasks) > 1
    assert all(len(t.params["tickers"]) <= 150 for t in tasks)


def test_task_budget_is_checked_as_tasks_are_built(monkeypatch):
    monkeypatch.setattr(ing, "MAX_TASKS", 2)
    with pytest.raises(ValueError, match="task limit"):
        ing.plan(["boats-bars"], ["AMD"], date(2000, 1, 1), date(2026, 1, 1))


def test_offline_page_cursor_is_bound_to_exact_plan():
    tasks = ing.plan(["eod-bars"], ["AMD", "NVDA", "INTC"], D0, D1)
    page = ing.plan_page(tasks, offset=0, limit=2)
    assert page["next_offset"] == 2
    assert page["total_tasks"] == 3
    assert page["execution_authorized"] is False
    second = ing.plan_page(tasks, offset=2, limit=2, expected_digest=page["plan_sha256"])
    assert second["next_offset"] is None
    assert second["items"][0]["symbol"] == "INTC"
    assert second["plan_sha256"] == page["plan_sha256"]
    changed = ing.plan(["eod-bars"], ["NVDA", "AMD", "INTC"], D0, D1)
    with pytest.raises(ValueError, match="plan changed"):
        ing.plan_page(changed, offset=2, limit=2, expected_digest=page["plan_sha256"])


def test_plan_cli_page_never_invokes_collector(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("offline plan called live source")
    monkeypatch.setattr(ing, "collect", forbidden)
    monkeypatch.setattr(ing, "read_key", forbidden)
    assert ing.main(["plan", "--sources", "eod-bars", "--symbols", "AMD,NVDA",
                     "--start", "2020-01-01", "--end", "2020-01-02",
                     "--plan-offset", "1", "--plan-limit", "1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["items"][0]["symbol"] == "NVDA"
    assert out["network"] is False


def test_iex_historical_volume_is_explicitly_requested():
    tasks = ing.plan(["iex-bars"], ["AMD"], D0, D1)
    assert all(t.params["columns"] == "open,high,low,close,volume" for t in tasks)


@pytest.mark.parametrize("source", ["equity-intraday-bars", "iex-bars", "boats-bars"])
def test_all_equity_history_plans_request_explicit_ohlcv(source):
    # Tiingo historical volume is opt-in, including consolidated equity bars.
    tasks = ing.plan([source], ["GLD", "AEM"], D0, D1)
    assert len(tasks) == 4  # Preserve bounded seven-day chunks and both symbols.
    for task in tasks:
        assert task.params["columns"] == "open,high,low,close,volume"
        assert task.params["resampleFreq"] == "1min"
        assert task.source == source


def test_commodity_probe_uses_24_distinct_offline_ohlcv_requests(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("planning attempted credentials or network")

    monkeypatch.setattr(ing, "collect_one", forbidden)
    monkeypatch.setattr(ing, "read_key", forbidden)
    symbols = ["GLD", "AEM", "SLV", "PAAS", "USO", "COP", "COPX", "FCX"]
    windows = [date(2025, 11, 28), date(2026, 1, 30), date(2026, 10, 8)]
    tasks = [task for day in windows
             for task in ing.plan(["equity-intraday-bars"], symbols, day, day)]
    assert len(tasks) == 24
    assert len({(task.symbol, task.params["startDate"]) for task in tasks}) == 24
    assert all(task.params["columns"] == "open,high,low,close,volume" for task in tasks)
    page = ing.plan_page(tasks, limit=24)
    assert page["total_tasks"] == 24
    assert page["execution_authorized"] is False
    assert all("columns=open,high,low,close,volume" in row["request_path"]
               for row in page["items"])


def test_equity_ohlcv_fix_preserves_other_feed_parameters():
    # The correction must not silently change session, fill, or other source policy.
    equity = ing.plan(["equity-intraday-bars"], ["GLD"], D0, D0)[0]
    assert equity.params == {
        "startDate": D0.isoformat(), "endDate": D0.isoformat(),
        "resampleFreq": "1min", "columns": "open,high,low,close,volume",
    }
    for source, symbol in [("eod-bars", "GLD"), ("forex-bars", "eurusd"),
                           ("crypto-bars", "btcusd")]:
        task = ing.plan([source], [symbol], D0, D0)[0]
        assert "columns" not in task.params
        assert "afterHours" not in task.params
        assert "forceFill" not in task.params
