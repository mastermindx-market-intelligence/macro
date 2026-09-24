"""app/hub.py — FastAPI router for the Options Hub nightly analytics.

Provides:
  GET /api/hub/vol/{root}      — IV surface + rank payload (options_hub/vol/{root}.json)
  GET /api/hub/gex/{root}      — Dealer-gamma exposure payload (options_hub/gex/{root}.json)
  GET /api/hub/oi              — OI movers screener (options_hub/oi_movers.json)
  GET /api/hub/hot             — Hottest contracts by premium/volume (options_hub/hot_contracts.json)
  GET /api/hub/prophet/perf    — INTERNAL-ONLY canonical Prophet forward-ledger projection

The existing Options Hub routes are unauthenticated read-throughs of public R2
options_hub/ objects with a 30-second in-memory TTL cache. Prophet performance is
deliberately different: it reads the local canonical effective ledger and reuses the
same loopback-plus-no-X-MM-Peer guard as /api/hub/prophet. It is never fetched from
or published to public R2.

Mirrors the code style and patterns from app/main.py's /api/flow/* routes exactly:
  - same TTL / UA / stale pattern
  - same r2_base resolver (R2_PUBLIC_BASE env or config.yml)
  - self-contained module; no imports from live_flow_poller
  - unauthenticated; display-tier only

DISPLAY-TIER ONLY: no trading signals, no directional recommendations.
Words 'signal' and 'validated' are banned in user-facing strings.
OI is always t-1 or older per the OI timing law.
"""
from __future__ import annotations

from datetime import date
import json
import logging
import math
import os
import re
from statistics import median
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter()
log = logging.getLogger("macro.hub")
_REPO_ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- #
# TTL cache (mirrors app/main.py _FLOW_CACHE pattern)
# --------------------------------------------------------------------------- #
_HUB_CACHE: dict[str, tuple[dict, float]] = {}
_HUB_CACHE_TTL = 30.0       # seconds
_HUB_UA = "mastermind-feed/1.0"

# --------------------------------------------------------------------------- #
# R2 base URL resolver (mirrors app/main.py _flow_r2_base)
# --------------------------------------------------------------------------- #

def _hub_r2_base() -> str:
    base = os.environ.get("R2_PUBLIC_BASE", "")
    if base:
        return base.rstrip("/")
    try:
        import yaml  # noqa: PLC0415
        _cfg_path = Path(os.environ.get("MACRO_REPO", "/opt/macro")) / "config.yml"
        if _cfg_path.exists():
            with open(_cfg_path) as f:
                c = yaml.safe_load(f)
            return (c.get("r2_data_plane", {}).get("public_base") or "").rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return ""


# --------------------------------------------------------------------------- #
# R2 read-through with TTL/stale fallback (mirrors app/main.py _flow_fetch)
# --------------------------------------------------------------------------- #

def _hub_fetch(key: str) -> dict:
    """Fetch options_hub/<key> from R2 with TTL caching and stale fallback.

    Returns the parsed JSON dict. On failure returns last-cached dict with
    {"stale": true} merged. Raises HTTPException(503) only if never fetched.
    """
    cached = _HUB_CACHE.get(key)
    now = time.monotonic()

    # Fresh cache hit
    if cached is not None and (now - cached[1]) < _HUB_CACHE_TTL:
        return cached[0]

    base = _hub_r2_base()
    if not base:
        if cached:
            return {**cached[0], "stale": True}
        raise HTTPException(503, f"hub/{key}: R2 base URL not configured")

    url = f"{base}/options_hub/{key}"
    req = urllib.request.Request(url, headers={"User-Agent": _HUB_UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data: dict = json.loads(resp.read())
        _HUB_CACHE[key] = (data, now)
        return data
    except Exception:  # noqa: BLE001
        if cached:
            return {**cached[0], "stale": True}
        raise HTTPException(503, f"hub/{key} unavailable and no cached copy") from None


# --------------------------------------------------------------------------- #
# parameter sanitization helpers
# --------------------------------------------------------------------------- #

_ROOT_RE = re.compile(r"^[A-Z0-9\^]{1,16}$")


def _sanitize_root(root: str) -> str:
    """Uppercase, strip whitespace, validate against safe root pattern.

    Raises HTTPException(400) on invalid input to prevent path traversal.
    """
    root = root.strip().upper()
    if not _ROOT_RE.match(root):
        raise HTTPException(400, f"Invalid root symbol: {root!r}")
    return root


# --------------------------------------------------------------------------- #
# Prophet forward-ledger private projection
# --------------------------------------------------------------------------- #

_PROPHET_LEDGER_SCHEMA = "prophet.ledger/v1"
_PROPHET_PERF_SCHEMA = "prophet.perf_projection/v1"
_PROPHET_OUTCOMES = (
    "T1_HIT",
    "T2_HIT",
    "INVALIDATED",
    "EXPIRED",
    "CLOSED_EARLY",
    "NO_ENTRY",
)


class ProphetPerfProjectionError(ValueError):
    "Canonical Prophet ledger cannot be projected truthfully."


def _canonical_date(value: Any, *, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ProphetPerfProjectionError(f"{label} must be a canonical ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ProphetPerfProjectionError(f"{label} is not a valid ISO date") from exc
    if parsed.isoformat() != value:
        raise ProphetPerfProjectionError(f"{label} must be YYYY-MM-DD")
    return value


def _finite_pct(value: Any, *, label: str, nullable: bool = True) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProphetPerfProjectionError(f"{label} must be a finite number or null")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ProphetPerfProjectionError(f"{label} must be finite")
    return numeric


def _validate_prophet_terminal_row(row: Any, *, ordinal: int) -> dict[str, Any]:
    "Validate projection-critical fields; tolerate unrelated additive fields."
    prefix = f"canonical ledger row {ordinal}"
    if not isinstance(row, dict):
        raise ProphetPerfProjectionError(f"{prefix} must be an object")
    if row.get("schema") != _PROPHET_LEDGER_SCHEMA:
        raise ProphetPerfProjectionError(f"{prefix} has unknown schema")

    for key in ("id", "asset", "direction", "outcome", "plan_adherence"):
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ProphetPerfProjectionError(f"{prefix}.{key} must be a non-empty string")
        if value != value.strip():
            raise ProphetPerfProjectionError(f"{prefix}.{key} must be canonical")

    if row["direction"] not in {"BULL", "BEAR"}:
        raise ProphetPerfProjectionError(f"{prefix}.direction is unsupported")
    if row["outcome"] not in _PROPHET_OUTCOMES:
        raise ProphetPerfProjectionError(f"{prefix}.outcome is unsupported")

    _canonical_date(row.get("signal_date"), label=f"{prefix}.signal_date", nullable=True)
    _canonical_date(row.get("entry_date"), label=f"{prefix}.entry_date", nullable=True)
    _canonical_date(row.get("close_date"), label=f"{prefix}.close_date")
    _canonical_date(row.get("asof"), label=f"{prefix}.asof")

    days = row.get("days_held")
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ProphetPerfProjectionError(f"{prefix}.days_held must be a non-negative integer")
    _finite_pct(row.get("stock_result_pct"), label=f"{prefix}.stock_result_pct")
    _finite_pct(row.get("option_result_pct"), label=f"{prefix}.option_result_pct")
    return row


def _raw_stock_return_summary(closed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        float(row["stock_result_pct"])
        for row in closed_rows
        if row.get("stock_result_pct") is not None
    ]
    unavailable = len(closed_rows) - len(values)
    if not values:
        return {
            "label": "Raw underlying return (unweighted per entered plan)",
            "available_count": 0,
            "unavailable_count": unavailable,
            "mean_pct": None,
            "median_pct": None,
            "min_pct": None,
            "max_pct": None,
            "positive_count": 0,
            "negative_count": 0,
            "zero_count": 0,
            "unavailable_reason": "no_canonical_stock_return_values",
        }

    return {
        "label": "Raw underlying return (unweighted per entered plan)",
        "available_count": len(values),
        "unavailable_count": unavailable,
        "mean_pct": round(math.fsum(values) / len(values), 4),
        "median_pct": round(float(median(values)), 4),
        "min_pct": round(min(values), 4),
        "max_pct": round(max(values), 4),
        "positive_count": sum(value > 0 for value in values),
        "negative_count": sum(value < 0 for value in values),
        "zero_count": sum(value == 0 for value in values),
        "unavailable_reason": None,
    }


def build_prophet_perf_projection(repo_root: str | Path = _REPO_ROOT) -> dict[str, Any]:
    "Project the canonical effective forward ledger without a second store or grader."
    from engine.prophet_integrity import (
        PlanCorrectionError,
        load_effective_ledger,
    )

    try:
        projection = load_effective_ledger(repo_root)
    except (OSError, PlanCorrectionError) as exc:
        raise ProphetPerfProjectionError(f"canonical effective ledger unavailable: {exc}") from exc

    canonical_rows = [
        _validate_prophet_terminal_row(row, ordinal=index)
        for index, row in enumerate(projection.rows, start=1)
    ]
    ids = {row["id"] for row in canonical_rows}
    effective_rows = [
        row for row in canonical_rows if row["id"] not in projection.quarantined_ids
    ]
    closed_rows = [row for row in effective_rows if row["outcome"] != "NO_ENTRY"]

    outcome_counts = {outcome: 0 for outcome in _PROPHET_OUTCOMES}
    for row in effective_rows:
        outcome_counts[row["outcome"]] += 1

    plans = []
    for row in sorted(
        effective_rows,
        key=lambda item: (item["close_date"], item["id"]),
        reverse=True,
    ):
        no_entry = row["outcome"] == "NO_ENTRY"
        plans.append({
            "id": row["id"],
            "ticker": row["asset"],
            "direction": row["direction"],
            "signal_date": row.get("signal_date"),
            "signal_date_unavailable_reason": (
                None if row.get("signal_date") is not None else "canonical_ledger_null"
            ),
            "entry_date": row.get("entry_date"),
            "entry_date_unavailable_reason": (
                None if row.get("entry_date") is not None else "canonical_ledger_null"
            ),
            "close_date": row["close_date"],
            "outcome": row["outcome"],
            "days_held": row["days_held"],
            "plan_adherence": row["plan_adherence"],
            "stock_result_pct": row.get("stock_result_pct"),
            "stock_result_pct_unavailable_reason": (
                None
                if row.get("stock_result_pct") is not None
                else ("no_entry_no_position" if no_entry else "canonical_ledger_null")
            ),
            "option_result_pct": row.get("option_result_pct"),
            "option_result_pct_unavailable_reason": (
                None
                if row.get("option_result_pct") is not None
                else ("no_entry_no_position" if no_entry else "canonical_ledger_null")
            ),
            "asof": row["asof"],
        })

    latest_asof = max((row["asof"] for row in effective_rows), default=None)
    latest_close_date = max((row["close_date"] for row in effective_rows), default=None)
    corrected_ids = ids.intersection(projection.applied_by_id)
    correction_applications = sum(
        len(projection.applied_by_id[plan_id]) for plan_id in corrected_ids
    )

    return {
        "schema": _PROPHET_PERF_SCHEMA,
        "source": {
            "path": "data/prophet/ledger.jsonl",
            "schema": _PROPHET_LEDGER_SCHEMA,
            "projection": "canonical_effective_ledger",
            "latest_asof": latest_asof,
            "latest_close_date": latest_close_date,
            "freshness_unavailable_reason": (
                None if latest_asof is not None else "no_effective_terminal_rows"
            ),
        },
        "summary": {
            "terminal_plan_count": len(effective_rows),
            "closed_plan_count": len(closed_rows),
            "no_entry_count": outcome_counts["NO_ENTRY"],
            "outcome_counts": outcome_counts,
            "raw_stock_return": _raw_stock_return_summary(closed_rows),
            "benchmarked_performance": {
                "available": False,
                "benchmark_return_pct": None,
                "excess_return_pct": None,
                "unavailable_reason": (
                    "canonical_effective_ledger_has_no_benchmark_return_evidence"
                ),
            },
        },
        "integrity": {
            "canonical_row_count": len(canonical_rows),
            "effective_row_count": len(effective_rows),
            "quarantined_excluded_count": len(canonical_rows) - len(effective_rows),
            "quarantined_id_count": len(projection.quarantined_ids),
            "corrected_row_count": len(corrected_ids),
            "correction_application_count": correction_applications,
        },
        "semantics": {
            "outcome_count_basis": (
                "Terminal ledger outcome labels only; T1_HIT/T2_HIT are closing "
                "outcomes, not ever-reached target frequencies."
            ),
            "raw_stock_return_basis": (
                "Unweighted per-plan underlying returns for entered plans; not option "
                "P&L, portfolio return, benchmarked return, or alpha."
            ),
        },
        "plans": plans,
    }


# --------------------------------------------------------------------------- #
# routes
# --------------------------------------------------------------------------- #

@router.get("/api/hub/vol/{root}")
def hub_vol(root: str) -> dict[str, Any]:
    """IV surface, IV rank, term structure, smile, RV20, VRP for one root.

    Display-tier analytics. IV rank is percentile vs trailing 252 sessions
    (null when <60 observations). OI used is always t-1 or older.
    """
    root = _sanitize_root(root)
    return _hub_fetch(f"vol/{root}.json")


@router.get("/api/hub/gex/{root}")
def hub_gex(root: str) -> dict[str, Any]:
    """Dealer-gamma exposure profile for one root.

    Dealer long-call / short-put sign convention (unobservable assumption —
    display context only). OI used is always t-1. GEX ladders replicate
    engine/gex_model dealer-sign convention exactly.
    """
    root = _sanitize_root(root)
    return _hub_fetch(f"gex/{root}.json")


@router.get("/api/hub/oi")
def hub_oi() -> dict[str, Any]:
    """Top ΔOI contract movers screener (cross-root, by |ΔOI|).

    Labeled heuristic — large ΔOI may reflect positioning, rolls,
    or expiry activity. Display context only.
    """
    return _hub_fetch("oi_movers.json")


@router.get("/api/hub/hot")
def hub_hot() -> dict[str, Any]:
    """Contracts with highest gross premium or volume for the session.

    Labeled heuristic — high premium or volume may reflect hedging,
    speculation, or rolls. Display context only.
    """
    return _hub_fetch("hot_contracts.json")


@router.get("/api/hub/ctx")
def hub_ctx() -> dict[str, Any]:
    """Options Hub market context: index_gex, fear_greed, sector_etf_flows.

    Nightly-computed aggregate context. Display context only.
    """
    return _hub_fetch("context.json")


@router.get("/api/hub/oiconf")
def hub_oiconf() -> dict[str, Any]:
    """OI-confirmed contracts: prev session notable ∩ today ΔOI movers.

    OI is always t-1 or older per the OI timing law. Display context only.
    """
    return _hub_fetch("oi_confirmed.json")


@router.get("/api/hub/tctx/{root}")
def hub_tctx(root: str) -> dict[str, Any]:
    """Ticker context: tape-flow z-scores for one root.

    z is null when history_n < 20. Display context only.
    """
    root = _sanitize_root(root)
    return _hub_fetch(f"tickers_ctx/{root}.json")

@router.get("/api/hub/prophet/perf")
def hub_prophet_perf(request: Request) -> JSONResponse:
    "INTERNAL-ONLY truthful history/return projection over the Prophet ledger."
    from app.prophet_lab import _hub_prophet_authorized

    if not _hub_prophet_authorized(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
            headers={"Cache-Control": "no-store"},
        )
    try:
        payload = build_prophet_perf_projection(_REPO_ROOT)
    except ProphetPerfProjectionError as exc:
        log.warning("hub_prophet_perf: projection unavailable (%s)", exc)
        return JSONResponse(
            {"error": "prophet_perf_unavailable"},
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})
