"""Read-only adapters for the compact financial presentation tool.

The gateway supplies its existing authorized dispatcher. This module has no
user-supplied URL, credential handling, model call, background task or data store.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Callable

from engine.quote_resolution import safe_symbol
from engine.neuralweb.brain_financial_views import normalize_request

# This is Terminal's existing public market-data surface, not a new data endpoint.
_PUBLIC_FUND_BASE = "https://app.mastermind-x.com/data/"
_RAW_LIMIT = 2 * 1024 * 1024
_CACHE: OrderedDict = OrderedDict()
_LOCK = Lock()


def read_statement_snapshot(params: dict, terminal_data_dir: Path) -> dict:
    symbol = safe_symbol(params.get("symbol"))
    if not symbol:
        return {"available": False, "note": "A company symbol is required."}
    path = terminal_data_dir / (symbol + ".fund.json")
    try:
        if path.is_file():
            if path.stat().st_size > _RAW_LIMIT:
                return {"available": False, "note": "Statement snapshot exceeds the supported size."}
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            now = time.monotonic()
            with _LOCK:
                cached = _CACHE.get(symbol)
                if cached and now - cached[0] < 60:
                    _CACHE.move_to_end(symbol)
                    return cached[1]
            request = urllib.request.Request(
                _PUBLIC_FUND_BASE + symbol + ".fund.json",
                headers={"User-Agent": "Mastermind-Brain-Financial-View/1.0"},
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                body = response.read(_RAW_LIMIT + 1)
            if len(body) > _RAW_LIMIT:
                return {"available": False, "note": "Statement snapshot exceeds the supported size."}
            data = json.loads(body)
        if not isinstance(data, dict) or data.get("schema") != "mastermind.fund/v1" or safe_symbol(data.get("ticker")) != symbol:
            return {"available": False, "note": "Statement source identity could not be verified."}
        result = {"available": True, "symbol": symbol, "fund": data}
        # Only immutable source results are shared. Compilers project/copy without mutation.
        with _LOCK:
            _CACHE[symbol] = (time.monotonic(), result)
            _CACHE.move_to_end(symbol)
            while len(_CACHE) > 128:
                _CACHE.popitem(last=False)
        return result
    except (OSError, ValueError, TypeError):
        # Failed reads are never cached and local filesystem/provider details stay private.
        with _LOCK:
            _CACHE.pop(symbol, None)
        return {"available": False, "symbol": symbol, "note": "Financial statements are unavailable from the current source."}


def _daily_closes(symbol: str, root: Path) -> list[dict]:
    try:
        from engine.marketing.chart_render import load_ohlcv
        loaded = load_ohlcv(symbol, root, n=600)
        if not loaded:
            return []
        dates, _, _, _, closes, _ = loaded
        if len(dates) != len(closes):
            return []
        rows = []
        previous = ""
        for day, close in zip(dates, closes):
            day = str(day)[:10]
            # No null/blank/bool conversion. The owner may synthesize OHLC for
            # close-only feeds; this adapter publishes measured closes only.
            if type(close) not in (int, float) or not math.isfinite(close) or close <= 0:
                continue
            if day <= previous:
                return []
            previous = day
            rows.append({"date": day, "close": close})
        return rows
    except Exception:
        return []


def prepare_widget_read(params: dict, dispatch: Callable[[str, dict], dict],
                        available_tools: set[str], root: Path) -> dict:
    """Prepare a private observation; the loop assigns its existing tool-use identity."""
    try:
        request = normalize_request(params)
    except (ValueError, TypeError, KeyError):
        return {"error": "invalid_financial_view", "note": "Choose a supported financial template and symbol."}
    if "render_financial_widget" not in available_tools:
        return {"error": "financial_view_not_admitted"}
    if request["source_ref"]:
        return {"financial_request": request}
    template, symbol = request["template"], request["symbol"]
    reader = {"price": "get_quote", "company": "get_fundamentals",
              "financial_statement": "read_financial_statements", "transcript": "get_earnings"}[template]
    permission_reader = "get_fundamentals" if template == "financial_statement" else reader
    if template == "transcript" and "read_earnings_evidence" in available_tools:
        reader = permission_reader = "read_earnings_evidence"
    if permission_reader not in available_tools:
        return {"error": "financial_source_not_admitted", "note": "This source is not available in the current request."}
    args = {"ticker": symbol} if reader == "read_earnings_evidence" else {"symbol": symbol}
    result = dispatch(reader, args)
    if template == "transcript" and (not isinstance(result, dict) or result.get("error") or result.get("available") is False) and "get_earnings" in available_tools:
        # A denied/unavailable exact source never becomes a quote. A separately
        # authorized public summary is a different, visibly labelled evidence kind.
        reader = "get_earnings"
        result = dispatch(reader, {"symbol": symbol})
    if template == "price" and isinstance(result, dict) and not result.get("error") and result.get("price") is not None:
        bars = _daily_closes(symbol, root)
        result = {"quote": result, "bars": bars,
                  "history_asof": bars[-1]["date"] if bars else None, "symbol": symbol}
    return {"financial_request": request,
            "financial_observation": {"reader": reader, "result": result}}
