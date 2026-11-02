"""Bounded forward evaluation for the three active Mastermind Portfolio brains.

This module is deliberately boring.  It reads only durable local artifacts, computes
observational metrics, and writes one deterministic snapshot per ``(book, asof)``.  It
never imports a quote feed, model/provider, allocator, paper-fill writer, or sizing path.

The v2 cohort boundary is an explicit runtime marker.  The deploy transaction stops the
service, initialises ``data/portfolio_forward_evaluation/start.json`` *once* with hashes/IDs
for every legacy row already present, starts the target release, and activates the marker
only after exact-SHA health passes.  Scheduled evaluation is a no-write ``not_started``
until that activation.  Later deployments never reset the cohort.

All runtime files are ignored by git and owned by the canonical VPS:

``data/portfolio_forward_evaluation/start.json``
    Immutable first-v2 deployment identity and per-book legacy baselines.
``data/portfolio_forward_evaluation/<book>/<asof>.json``
    One deterministic forward snapshot for that book/date.
``data/portfolio_forward_evaluation/<book>/latest.json``
    Byte-identical copy of the latest written snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from portfolio import registry


SCHEMA = "mastermind.portfolio_forward_evaluation.v1"
STATUS_SCHEMA = "mastermind.portfolio_forward_evaluation.status.v1"
START_SCHEMA = "mastermind.portfolio_forward_evaluation.start.v1"
ACTIVE_BOOKS = ("autonomous", "china", "hk")
PROPHET_MIN_GROUP_SAMPLE = 30

_ROOT = Path(__file__).resolve().parent.parent
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RELEASE_STATE_ROOT_ENV = "MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT"
_RELEASE_DATA_ROOT: ContextVar[Path | None] = ContextVar(
    "forward_evaluation_release_data_root", default=None,
)


# ---------------------------------------------------------------------------
# Paths and bounded durable reads
# ---------------------------------------------------------------------------

def _state_root() -> Path:
    """Follow the registry root so existing test/VPS state redirection stays coherent."""
    return Path(getattr(registry, "_ROOT", _ROOT))


def _data_root() -> Path:
    """Physical durable-data root in the current execution namespace.

    Normal scheduler/API calls see ``<repo>/data`` (the systemd service bind-mounts canonical VPS
    state there).  Only release CLI commands may install the context-local override used by an SSH
    deploy shell running outside that mount namespace.
    """
    return _RELEASE_DATA_ROOT.get() or (_state_root() / "data")


@contextmanager
def _release_data_root(path: str | Path | None):
    if path is None:
        yield
        return
    root = Path(path)
    if not root.is_absolute():
        raise ValueError(f"{_RELEASE_STATE_ROOT_ENV} must be an absolute path")
    token = _RELEASE_DATA_ROOT.set(root)
    try:
        yield
    finally:
        _RELEASE_DATA_ROOT.reset(token)


def _output_root() -> Path:
    return _data_root() / "portfolio_forward_evaluation"


def _start_path() -> Path:
    return _output_root() / "start.json"


def _canonical_book_id(book: str) -> str:
    """Return only a registry-owned literal; never pass request text into a path."""
    value = str(book or "").lower().strip()
    if value == "flagship":
        return "flagship"
    if value == "heavyweight":
        return "heavyweight"
    if value == "autonomous":
        return "autonomous"
    if value == "etf":
        return "etf"
    if value == "china":
        return "china"
    if value == "hk":
        return "hk"
    if value == "self_directed":
        return "self_directed"
    raise ValueError("unknown portfolio book")


def _book_output_dir(book: str) -> Path:
    return _output_root() / _canonical_book_id(book)


def _post_sell_path(book: str) -> Path:
    return _data_root() / "portfolio_learning" / _canonical_book_id(book) / "post_sell.json"


def _portfolio_data_dir(book: str) -> Path:
    canonical = _canonical_book_id(book)
    meta = registry.get(canonical)
    if meta.get("legacy"):
        return _data_root() / "portfolio"
    return _data_root() / "portfolios" / canonical


def _relative(path: Path) -> str:
    try:
        return str(Path("data") / path.relative_to(_data_root()))
    except ValueError:
        return path.name


def _read_json_object(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "invalid"
    return (value, "available") if isinstance(value, dict) else ({}, "invalid")


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    invalid = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return [], "invalid"
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except Exception:
            invalid += 1
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            invalid += 1
    if invalid and rows:
        return rows, "partial"
    if invalid:
        return [], "invalid"
    return rows, "available"


def _validate_positions_ledger(value: dict[str, Any], status: str) -> tuple[dict[str, Any], str]:
    if status != "available":
        return value, status
    if not value:
        return value, status
    cleaned: dict[str, Any] = {}
    invalid = 0
    recognized = {
        "ticker", "still_open", "history", "open_as_of", "close_as_of",
        "opened_at", "closed_at",
    }
    for key, raw in value.items():
        if not isinstance(raw, dict) or not recognized.intersection(raw):
            invalid += 1
            continue
        row = dict(raw)
        history = raw.get("history")
        if history is not None:
            if not isinstance(history, list):
                invalid += 1
                row.pop("history", None)
            else:
                valid_history = [event for event in history if isinstance(event, dict)]
                invalid += len(history) - len(valid_history)
                row["history"] = valid_history
        cleaned[str(key)] = row
    if not cleaned:
        return {}, "invalid"
    return cleaned, "partial" if invalid else "available"


def _validate_post_sell(value: dict[str, Any], status: str) -> tuple[dict[str, Any], str]:
    if status != "available":
        return value, status
    if value.get("schema") not in (None, "portfolio.post_sell.v1"):
        return {}, "invalid"
    exits = value.get("exits")
    if not isinstance(exits, list):
        return {}, "invalid"
    valid = [row for row in exits if isinstance(row, dict)]
    cleaned = {**value, "exits": valid}
    return cleaned, "partial" if len(valid) != len(exits) else "available"


def _validate_latest(value: dict[str, Any], status: str) -> tuple[dict[str, Any], str]:
    if status != "available":
        return value, status
    positions = value.get("positions")
    if not isinstance(positions, list):
        return value, "partial"
    valid = [row for row in positions if isinstance(row, dict)]
    return {**value, "positions": valid}, "partial" if len(valid) != len(positions) else status


def _read_inputs(book: str) -> dict[str, Any]:
    base = _portfolio_data_dir(book)
    paths = {
        "account": base / "account.json",
        "decisions": base / "decisions.jsonl",
        "fills": base / "fills.jsonl",
        "nav": base / "nav_history.jsonl",
        "positions": base / "positions_ledger.json",
        "latest": base / "latest.json",
        "post_sell": _post_sell_path(book),
    }
    account, account_status = _read_json_object(paths["account"])
    decisions, decisions_status = _read_jsonl(paths["decisions"])
    fills, fills_status = _read_jsonl(paths["fills"])
    nav, nav_status = _read_jsonl(paths["nav"])
    positions, positions_status = _read_json_object(paths["positions"])
    latest, latest_status = _read_json_object(paths["latest"])
    post_sell, post_sell_status = _read_json_object(paths["post_sell"])
    positions, positions_status = _validate_positions_ledger(positions, positions_status)
    latest, latest_status = _validate_latest(latest, latest_status)
    post_sell, post_sell_status = _validate_post_sell(post_sell, post_sell_status)
    values = {
        "account": account,
        "decisions": decisions,
        "fills": fills,
        "nav": nav,
        "positions": positions,
        "latest": latest,
        "post_sell": post_sell,
    }
    statuses = {
        "account": account_status,
        "decisions": decisions_status,
        "fills": fills_status,
        "nav": nav_status,
        "positions": positions_status,
        "latest": latest_status,
        "post_sell": post_sell_status,
    }
    return {"values": values, "statuses": statuses, "paths": paths}


# ---------------------------------------------------------------------------
# Stable row identities and the immutable v2 cohort marker
# ---------------------------------------------------------------------------

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str,
                      ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


_LOGICAL_ID_FIELDS = (
    "decision_id", "fill_id", "transaction_id", "execution_id", "order_id",
    "nav_id", "mark_id", "event_id", "run_id", "id",
)


def _row_ids(rows: list[dict[str, Any]], date_key: str) -> list[str]:
    """Prefer durable logical IDs, then stable content identities for legacy rows."""
    occurrences: dict[str, int] = {}
    out: list[str] = []
    for row in rows:
        logical = next(
            ((field, row.get(field)) for field in _LOGICAL_ID_FIELDS
             if row.get(field) not in (None, "")),
            None,
        )
        if logical is not None:
            field, value = logical
            out.append(f"logical:{field}:{_digest(value)}")
            continue
        digest = _digest(row)
        occurrence = occurrences.get(digest, 0)
        occurrences[digest] = occurrence + 1
        out.append(f"{str(row.get(date_key) or '')[:10]}:{digest}:{occurrence}")
    return out


def _day(value: Any) -> str | None:
    raw = str(value or "")[:10]
    try:
        return date.fromisoformat(raw).isoformat()
    except (TypeError, ValueError):
        return None


def _validate_day(value: str | date) -> str:
    raw = value.isoformat() if isinstance(value, date) else str(value or "")[:10]
    try:
        return date.fromisoformat(raw).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid asof date: {value!r}") from exc


def _utc_today() -> str:
    return datetime.now(UTC).date().isoformat()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _closed_events(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract every durable close event, including close/re-open histories."""
    out: list[dict[str, Any]] = []
    for key, raw in sorted(ledger.items()):
        if not isinstance(raw, dict):
            continue
        opened: str | None = _day(raw.get("open_as_of"))
        emitted = False
        close_occurrences: dict[str, int] = {}
        for event in raw.get("history") or []:
            if not isinstance(event, dict):
                continue
            kind = str(event.get("event") or "").lower()
            event_day = _day(event.get("as_of") or event.get("ts"))
            if kind == "open":
                opened = event_day or opened
                continue
            if kind != "close":
                continue
            closed = event_day or _day(raw.get("close_as_of") or raw.get("closed_at"))
            if not closed:
                continue
            event_digest = _digest(event)
            occurrence_key = f"{opened or ''}:{closed}:{event_digest}"
            occurrence = close_occurrences.get(occurrence_key, 0)
            close_occurrences[occurrence_key] = occurrence + 1
            identity = f"{key}:{occurrence_key}:{occurrence}"
            out.append({
                "id": identity,
                "ticker": raw.get("ticker"),
                "open_asof": opened,
                "close_asof": closed,
            })
            emitted = True
            opened = None
        # Some legacy ledgers persisted top-level close fields without a history event.
        if not raw.get("still_open") and not emitted:
            closed = _day(raw.get("close_as_of") or raw.get("closed_at"))
            opened = _day(raw.get("open_as_of") or raw.get("opened_at"))
            if closed:
                out.append({
                    "id": f"{key}:top:{opened or ''}:{closed}",
                    "ticker": raw.get("ticker"),
                    "open_asof": opened,
                    "close_asof": closed,
                })
    return out


def _post_sell_rows(post_sell: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in (post_sell.get("exits") or []) if isinstance(row, dict)]


def _event_ticker(row: dict[str, Any]) -> str:
    ticker = str(row.get("ticker") or row.get("symbol") or "").upper().strip()
    if ticker:
        return ticker
    parts = str(row.get("exit_id") or "").split(":")
    for index, part in enumerate(parts[:-1]):
        if _day(part) and index + 1 < len(parts):
            return parts[index + 1].upper().strip()
    return ""


def _baseline_for(book: str) -> dict[str, Any]:
    raw = _read_inputs(book)
    values = raw["values"]
    decisions = values["decisions"]
    fills = values["fills"]
    nav = values["nav"]
    closes = _closed_events(values["positions"])
    post = _post_sell_rows(values["post_sell"])
    row_ids = {
        "decisions": _row_ids(decisions, "asof"),
        "fills": _row_ids(fills, "date"),
        "nav": _row_ids(nav, "date"),
        "closed_positions": [str(row["id"]) for row in closes],
        # Post-sell grades update in place.  The immutable exit_id, not the changing row hash,
        # is the cohort identity so a later 21/63-session grade cannot resurrect a legacy sale.
        "post_sell_exits": [
            str(row.get("exit_id")) for row in post if row.get("exit_id")
        ],
    }
    row_hashes = {
        "decisions": [_digest(row) for row in decisions],
        "fills": [_digest(row) for row in fills],
        "nav": [_digest(row) for row in nav],
        "closed_positions": [_digest(row) for row in closes],
        "post_sell_exits": [_digest(row) for row in post],
    }
    return {
        "row_ids": row_ids,
        "row_hashes": row_hashes,
        "row_counts": {key: len(value) for key, value in row_ids.items()},
        "input_status": dict(raw["statuses"]),
    }


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False,
                          default=str) + "\n").encode("utf-8")
    try:
        if path.read_bytes() == encoded:
            return
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        tmp.write_bytes(encoded)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _atomic_create_once(path: Path, payload: dict[str, Any]) -> bool:
    """Publish a complete immutable file only if ``path`` does not already exist."""
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False,
                          default=str) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.create")
    try:
        with tmp.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(tmp, path)
            return True
        except FileExistsError:
            return False
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def load_start() -> dict[str, Any] | None:
    value, state = _read_json_object(_start_path())
    if state != "available" or value.get("schema") != START_SCHEMA:
        return None
    if not _SHA_RE.fullmatch(str(value.get("deployment_sha") or "")):
        return None
    if not _day(value.get("evaluation_start")):
        return None
    if value.get("release_state") not in {"pending_health", "active"}:
        return None
    books = value.get("books")
    required_rows = {"decisions", "fills", "nav", "closed_positions", "post_sell_exits"}
    if not isinstance(books, dict):
        return None
    for book in ACTIVE_BOOKS:
        baseline = books.get(book)
        row_ids = baseline.get("row_ids") if isinstance(baseline, dict) else None
        row_hashes = baseline.get("row_hashes") if isinstance(baseline, dict) else None
        if not isinstance(row_ids, dict) or not required_rows.issubset(row_ids):
            return None
        if any(not isinstance(row_ids.get(key), list) for key in required_rows):
            return None
        if not isinstance(row_hashes, dict) or not required_rows.issubset(row_hashes):
            return None
        if any(not isinstance(row_hashes.get(key), list) for key in required_rows):
            return None
    state = value.get("release_state")
    verified_sha = value.get("health_verified_sha")
    if state == "active" and verified_sha != value.get("deployment_sha"):
        return None
    if state == "pending_health" and verified_sha is not None:
        return None
    return value


def initialize_start(deployment_sha: str, asof: str | date) -> dict[str, Any]:
    """Create the v2 cohort marker once; later deploys can never reset it.

    This is a release operation, not application startup behavior.  The deploy script invokes it
    while the service is stopped, then starts the target release and activates the marker only
    after exact-SHA health, scheduler, and provider-policy probes pass.
    """
    sha = str(deployment_sha or "").lower().strip()
    if not _SHA_RE.fullmatch(sha):
        raise ValueError("deployment_sha must be a full lowercase git SHA")
    start_day = _validate_day(asof)
    existing = load_start()
    if existing is not None:
        if (existing.get("release_state") == "pending_health"
                and existing.get("deployment_sha") != sha):
            raise RuntimeError("pending forward evaluation marker belongs to a different deployment")
        return {**existing, "initialized": False, "preserved_existing_start": True}
    if _start_path().exists():
        # An unreadable authority boundary is a freeze, never permission to reset the cohort.
        raise RuntimeError("existing forward evaluation start marker is invalid; refusing reset")
    marker = {
        "schema": START_SCHEMA,
        "evaluation_start": start_day,
        "deployment_sha": sha,
        "release_state": "pending_health",
        "cohort_policy": "exclude_all_rows_present_at_stopped_service_v2_baseline",
        "books": {book: _baseline_for(book) for book in ACTIVE_BOOKS},
    }
    created = _atomic_create_once(_start_path(), marker)
    if not created:
        # Another initializer won the race.  Preserve it if valid; otherwise fail closed.
        winner = load_start()
        if winner is None:
            raise RuntimeError("concurrent forward evaluation start marker is invalid")
        return {**winner, "initialized": False, "preserved_existing_start": True}
    reread = load_start()
    if reread != marker:
        raise RuntimeError("forward evaluation start marker verification failed")
    return {**marker, "initialized": True, "preserved_existing_start": False}


def finalize_start(deployment_sha: str) -> dict[str, Any]:
    """Activate a pending cohort only after the deploy health gate has passed."""
    sha = str(deployment_sha or "").lower().strip()
    if not _SHA_RE.fullmatch(sha):
        raise ValueError("deployment_sha must be a full lowercase git SHA")
    marker = load_start()
    if marker is None:
        raise RuntimeError("forward evaluation start marker is missing or invalid")
    if marker.get("release_state") == "active":
        return {**marker, "finalized": False, "preserved_existing_start": True}
    if marker.get("deployment_sha") != sha:
        raise RuntimeError("pending forward evaluation marker belongs to a different deployment")
    finalized = {**marker, "release_state": "active", "health_verified_sha": sha}
    _atomic_write(_start_path(), finalized)
    reread = load_start()
    if reread != finalized:
        raise RuntimeError("forward evaluation start finalization verification failed")
    return {**finalized, "finalized": True, "preserved_existing_start": False}


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _metric(value: Any, sample_n: int, status: str,
            missing_reason: str | None = None) -> dict[str, Any]:
    return {
        "value": value,
        "sample_n": max(0, int(sample_n)),
        "status": status,
        "missing_reason": missing_reason,
    }


def _available(value: Any, sample_n: int) -> dict[str, Any]:
    return _metric(value, sample_n, "available", None)


def _missing(reason: str, sample_n: int = 0, *, status: str = "missing") -> dict[str, Any]:
    return _metric(None, sample_n, status, reason)


def _source_missing(status: str) -> bool:
    return status in {"missing", "invalid"}


def _in_window(value: Any, start: str, end: str) -> bool:
    day = _day(value)
    return bool(day and start <= day <= end)


def _new_indexed_rows(rows: list[dict[str, Any]], date_key: str,
                      baseline: Iterable[str], start: str, end: str) -> list[dict[str, Any]]:
    blocked = set(baseline)
    return [
        row for row, row_id in zip(rows, _row_ids(rows, date_key), strict=True)
        if row_id not in blocked
        and _in_window(row.get(date_key), start, end)
    ]


def _dedupe_nav_sessions(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Keep the last durable row for each canonical session date."""
    by_day: dict[str, dict[str, Any]] = {}
    duplicate_n = 0
    for row in rows:
        day = _day(row.get("date"))
        if day is None:
            continue
        if day in by_day:
            duplicate_n += 1
        by_day[day] = row
    return [by_day[day] for day in sorted(by_day)], duplicate_n


def _partialize(metric: dict[str, Any], reason: str) -> dict[str, Any]:
    """Never promote a value derived from a known-partial source to available."""
    if metric.get("status") != "available":
        return metric
    return {**metric, "status": "partial", "missing_reason": reason}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _rate_metric(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool],
                 empty_reason: str) -> dict[str, Any]:
    if not rows:
        return _missing(empty_reason, status="insufficient_sample")
    return _available(round(100.0 * sum(bool(predicate(row)) for row in rows) / len(rows), 4),
                      len(rows))


def _artifact_count_metric(status: str, rows: list[Any], value: int,
                           missing_reason: str) -> dict[str, Any]:
    if _source_missing(status):
        return _missing(missing_reason)
    metric_status = "partial" if status == "partial" else "available"
    reason = "some_artifact_rows_were_invalid" if metric_status == "partial" else None
    return _metric(int(value), len(rows), metric_status, reason)


def _metric_status_counts(metrics: dict[str, dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for metric in metrics.values():
        key = str(metric.get("status") or "unknown")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _forward_full_exit_outcomes(all_fills: list[dict[str, Any]], baseline: Iterable[str],
                                start: str, end: str) -> list[dict[str, Any]]:
    """FIFO-grade only post-baseline fills that fully close a durable paper position."""
    blocked = set(baseline)
    lots: dict[str, list[list[float]]] = {}
    net: dict[str, float] = {}
    outcomes: list[dict[str, Any]] = []
    ids = _row_ids(all_fills, "date")
    indexed = sorted(enumerate(zip(all_fills, ids, strict=True)), key=lambda pair: (
        _day(pair[1][0].get("date")) or "", pair[0]))
    for _, (row, row_id) in indexed:
        ticker = str(row.get("ticker") or "").upper().strip()
        side = str(row.get("side") or "").lower().strip()
        shares = _number(row.get("shares"))
        price = _number(row.get("price"))
        if not ticker or shares is None or shares <= 0 or price is None or price <= 0:
            continue
        queue = lots.setdefault(ticker, [])
        held_before = net.get(ticker, 0.0)
        if side == "buy":
            queue.append([shares, price])
            net[ticker] = held_before + shares
            continue
        if side != "sell":
            continue
        remaining = shares
        matched = 0.0
        realized = 0.0
        while remaining > 1e-9 and queue:
            take = min(queue[0][0], remaining)
            realized += (price - queue[0][1]) * take
            matched += take
            queue[0][0] -= take
            remaining -= take
            if queue[0][0] <= 1e-9:
                queue.pop(0)
        held_after = max(0.0, held_before - shares)
        net[ticker] = held_after
        if (held_before > 1e-9 and held_after <= 1e-9 and row_id not in blocked
                and _in_window(row.get("date"), start, end)):
            outcomes.append({
                "ticker": ticker,
                "date": _day(row.get("date")),
                "realized_pnl": round(realized, 8) if matched + 1e-9 >= shares else None,
            })
    return outcomes


# ---------------------------------------------------------------------------
# Durable funnel/action projections
# ---------------------------------------------------------------------------

def _memo(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("decision_memo")
    return value if isinstance(value, dict) else {}


def _count_from(value: Any, *, keys: tuple[str, ...] = ()) -> int | None:
    number = _number(value)
    if number is not None and number >= 0:
        return int(number)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    if not isinstance(value, dict):
        return None
    for key in keys:
        if key in value:
            found = _count_from(value.get(key))
            if found is not None:
                return found
    for key in ("count", "n", "total", "reviewed", "evaluated"):
        found = _count_from(value.get(key)) if key in value else None
        if found is not None:
            return found
    return None


def _funnel_count(row: dict[str, Any], kind: str) -> int | None:
    funnel = _memo(row).get("candidate_funnel")
    if not isinstance(funnel, dict):
        return None
    if kind == "candidate":
        keys = ("candidates", "candidate_count", "candidates_n", "n_candidates",
                "reviewed", "evaluated", "total")
    else:
        keys = ("finalists", "finalist_count", "finalists_n", "n_finalists", "shortlist")
    for key in keys:
        if key in funnel:
            found = _count_from(funnel.get(key))
            if found is not None:
                return found
    return None


def _rows_from(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(dict(item))
            elif _present(item):
                out.append({"ticker": str(item), "reason": None})
        return out
    if not isinstance(value, dict):
        return []
    for key in ("items", "candidates", "names", "rows"):
        if key in value:
            nested = _rows_from(value.get(key))
            if nested:
                return nested
    # A ticker/name -> detail mapping is common in free-form decision memos.
    aggregate_keys = {"count", "n", "total", "summary", "note", "rationale"}
    out: list[dict[str, Any]] = []
    for key, item in value.items():
        if key in aggregate_keys:
            continue
        if isinstance(item, dict):
            out.append({"ticker": key, **item})
        elif _present(item):
            out.append({"ticker": key, "reason": item})
    return out


def _selected_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    selected = _rows_from(_memo(row).get("selected"))
    if selected:
        return selected
    return [dict(item) for item in (row.get("effective_holdings") or [])
            if isinstance(item, dict)]


def _rejected_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    rejected = _rows_from(_memo(row).get("rejected"))
    if rejected:
        return rejected
    audit = row.get("submission_audit")
    return [dict(item) for item in ((audit or {}).get("rejected") or [])
            if isinstance(item, dict)] if isinstance(audit, dict) else []


def _reported_count(row: dict[str, Any], kind: str) -> int | None:
    if kind in {"candidate", "finalist"}:
        return _funnel_count(row, kind)
    rows = _selected_rows(row) if kind == "selected" else _rejected_rows(row)
    if rows:
        return len(rows)
    value = _memo(row).get(kind)
    return _count_from(value, keys=(kind, f"{kind}_count", f"n_{kind}"))


def _coverage_reason(row: dict[str, Any]) -> bool:
    return any(_present(row.get(key)) for key in ("reason", "why", "rationale", "reject_reason"))


def _provenance_values(row: dict[str, Any]) -> list[Any]:
    return [row.get(key) for key in
            ("source_provenance", "provenance", "sources", "evidence_planes", "evidence")
            if key in row]


def _has_provenance(row: dict[str, Any]) -> bool:
    return any(_present(value) for value in _provenance_values(row))


def _contains_prophet(value: Any) -> bool:
    if isinstance(value, str):
        return "prophet" in value.lower()
    if isinstance(value, dict):
        return any(_contains_prophet(key) or _contains_prophet(item)
                   for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_prophet(item) for item in value)
    return False


def _has_prophet(row: dict[str, Any]) -> bool:
    return any(_contains_prophet(value) for value in _provenance_values(row))


def _effective(row: dict[str, Any]) -> bool:
    if isinstance(row.get("decision_effective"), bool):
        return bool(row["decision_effective"])
    return str(row.get("target_status") or "") in {"executed", "queued"}


def _action_projection(decisions: list[dict[str, Any]]) -> tuple[dict[str, int], int, int]:
    counts = {"add": 0, "hold": 0, "trim": 0, "exit": 0, "no_change": 0}
    effective_n = 0
    material_n = 0
    for row in decisions:
        if not _effective(row):
            continue
        effective_n += 1
        material = False
        for holding in row.get("effective_holdings") or []:
            if not isinstance(holding, dict):
                continue
            action = str(holding.get("action_effective") or "").lower()
            if action in {"add", "hold", "trim"}:
                counts[action] += 1
                material = material or action in {"add", "trim"}
        exits = [item for item in (row.get("exit_decisions") or []) if isinstance(item, dict)]
        counts["exit"] += len(exits)
        material = material or bool(exits)
        # Older accepted rows may lack typed actions but preserve actual fills.
        if not material and row.get("executed"):
            material = True
        if material:
            material_n += 1
        else:
            counts["no_change"] += 1
    return counts, effective_n, material_n


# ---------------------------------------------------------------------------
# Snapshot assembly
# ---------------------------------------------------------------------------

def _current_exposure_metrics(raw: dict[str, Any], asof: str) -> dict[str, dict[str, Any]]:
    values, statuses = raw["values"], raw["statuses"]
    nav_all = [row for row in values["nav"] if _day(row.get("date"))]
    future_nav = any((_day(row.get("date")) or "") > asof for row in nav_all)
    eligible = sorted(
        (row for row in nav_all if (_day(row.get("date")) or "") <= asof),
        key=lambda row: _day(row.get("date")) or "",
    )
    if not eligible:
        reason = ("nav_history_artifact_unavailable" if _source_missing(statuses["nav"])
                  else "no_mark_at_or_before_asof")
        return {key: _missing(reason) for key in (
            "gross_exposure_pct", "cash_pct", "net_exposure_pct", "top_1_weight_pct",
            "top_3_weight_pct", "position_hhi")}
    row = eligible[-1]
    mark_day = _day(row.get("date"))
    nav = _number(row.get("nav"))
    cash = _number(row.get("cash"))
    invested = _number(row.get("invested"))
    if nav is None or nav <= 0 or cash is None:
        basic = {key: _missing("latest_mark_lacks_positive_nav_or_cash", 1) for key in
                 ("gross_exposure_pct", "cash_pct", "net_exposure_pct")}
    else:
        if invested is None:
            invested = nav - cash
        basic = {
            "gross_exposure_pct": _available(round(abs(invested) / nav * 100.0, 4), 1),
            "cash_pct": _available(round(cash / nav * 100.0, 4), 1),
            "net_exposure_pct": _available(round(invested / nav * 100.0, 4), 1),
        }

    if future_nav:
        concentration = {key: _missing(
            "current_account_is_not_point_in_time_for_historical_asof") for key in
            ("top_1_weight_pct", "top_3_weight_pct", "position_hhi")}
        return {**basic, **concentration}

    weights: list[float] | None = None
    missing_positions = 0
    account_positions = (values["account"].get("positions")
                         if isinstance(values["account"], dict) else None)
    exposure_claimed = bool((invested is not None and abs(invested) > 1e-9)
                            or (isinstance(account_positions, dict) and account_positions))
    # Published weights are point-in-time only when they match the chosen NAV session exactly.
    # A merely earlier latest.json is stale and must not override post-mark account prices.
    latest_day = _day(values["latest"].get("as_of"))
    latest_positions = values["latest"].get("positions")
    if latest_day and latest_day == mark_day and isinstance(latest_positions, list):
        candidate_weights: list[float] = []
        invalid = 0
        for position in latest_positions:
            weight = _number(position.get("weight")) if isinstance(position, dict) else None
            if weight is None or weight < 0:
                invalid += 1
            else:
                candidate_weights.append(weight)
        if invalid == 0 and (sum(candidate_weights) > 1e-12 or not exposure_claimed):
            weights = candidate_weights

    # Fall back to account shares * the durable post-mark current_price only when latest weights
    # cannot supply a complete set.  avg_cost is deliberately not treated as a current mark here.
    if weights is None:
        account_weights: list[float] = []
        if isinstance(account_positions, dict) and nav is not None and nav > 0:
            for position in account_positions.values():
                if not isinstance(position, dict):
                    missing_positions += 1
                    continue
                shares = _number(position.get("shares"))
                price = _number(position.get("current_price"))
                if shares is None or shares < 0 or price is None or price <= 0:
                    missing_positions += 1
                    continue
                account_weights.append(max(0.0, shares * price / nav))
            weights = account_weights
            if exposure_claimed and not account_weights:
                missing_positions += 1
        else:
            missing_positions = 1
            weights = []

    if missing_positions:
        concentration = {key: _metric(
            None, len(weights), "partial", "some_current_positions_lack_durable_weight_or_mark"
        ) for key in ("top_1_weight_pct", "top_3_weight_pct", "position_hhi")}
    else:
        ordered = sorted(weights, reverse=True)
        concentration = {
            "top_1_weight_pct": _available(round((ordered[0] if ordered else 0.0) * 100.0, 4),
                                             len(ordered)),
            "top_3_weight_pct": _available(round(sum(ordered[:3]) * 100.0, 4), len(ordered)),
            "position_hhi": _available(round(sum(weight * weight for weight in ordered), 6),
                                       len(ordered)),
        }
    return {**basic, **concentration}


def _count_with_reporting(decisions: list[dict[str, Any]], kind: str,
                          source_status: str) -> dict[str, Any]:
    if _source_missing(source_status):
        return _missing("decision_log_artifact_unavailable")
    reported = [value for row in decisions if (value := _reported_count(row, kind)) is not None]
    if not decisions:
        return _available(0, 0)
    if not reported:
        return _missing(f"{kind}_count_unreported_in_decision_memos")
    partial = len(reported) != len(decisions) or source_status == "partial"
    return _metric(sum(reported), len(reported), "partial" if partial else "available",
                   f"{kind}_count_unreported_for_some_decisions" if partial else None)


def build_snapshot(book: str, asof: str | date,
                   *, start: dict[str, Any] | None = None) -> dict[str, Any]:
    """Purely assemble one forward snapshot from local artifacts; perform no writes."""
    b = str(book or "").lower().strip()
    if b not in ACTIVE_BOOKS:
        raise ValueError(f"unsupported active forward-evaluation book: {b!r}")
    end = _validate_day(asof)
    marker = start or load_start()
    if marker is None:
        return _not_started_book(b)
    if marker.get("release_state") != "active":
        return _not_started_book(b, marker)
    begin = _validate_day(marker["evaluation_start"])
    if end < begin:
        return {
            "schema": STATUS_SCHEMA,
            "book": b,
            "asof": end,
            "status": "before_evaluation_start",
            "evaluation_start": begin,
            "write_permitted": False,
            "sample_counts": _zero_sample_counts(),
        }

    baseline_book = ((marker.get("books") or {}).get(b) or {})
    baseline = baseline_book.get("row_ids") or {}
    raw = _read_inputs(b)
    values = dict(raw["values"])
    statuses = dict(raw["statuses"])
    decisions = _new_indexed_rows(values["decisions"], "asof", baseline.get("decisions") or [],
                                  begin, end)
    fills = _new_indexed_rows(values["fills"], "date", baseline.get("fills") or [], begin, end)
    nav_rows = _new_indexed_rows(values["nav"], "date", baseline.get("nav") or [], begin, end)
    nav_rows, forward_nav_duplicates = _dedupe_nav_sessions(nav_rows)
    values["nav"], all_nav_duplicates = _dedupe_nav_sessions(values["nav"])
    if all_nav_duplicates:
        statuses["nav"] = "partial"
    raw = {**raw, "values": values, "statuses": statuses}
    closes = [row for row in _closed_events(values["positions"])
              if row["id"] not in set(baseline.get("closed_positions") or [])
              and _in_window(row.get("close_asof"), begin, end)]
    post_rows = [row for row in _post_sell_rows(values["post_sell"])
                 if str(row.get("exit_id") or "") not in set(baseline.get("post_sell_exits") or [])
                 and _in_window(row.get("exit_date"), begin, end)]

    metrics: dict[str, dict[str, Any]] = {}
    metrics.update(_current_exposure_metrics(raw, end))
    metrics["marked_session_count"] = _artifact_count_metric(
        statuses["nav"], nav_rows, len(nav_rows), "nav_history_artifact_unavailable")
    metrics["fill_count"] = _artifact_count_metric(
        statuses["fills"], fills, len(fills), "fills_artifact_unavailable")
    metrics["closed_position_count"] = _artifact_count_metric(
        statuses["positions"], closes, len(closes), "position_ledger_artifact_unavailable")
    metrics["post_sell_sale_count"] = _artifact_count_metric(
        statuses["post_sell"], post_rows, len(post_rows), "post_sell_artifact_unavailable")

    # Traded-value turnover: all forward fill notional divided by mean forward marked NAV.
    valid_nav = [_number(row.get("nav")) for row in nav_rows]
    valid_nav = [value for value in valid_nav if value is not None and value > 0]
    fill_values: list[float] = []
    invalid_fill_values = 0
    for row in fills:
        value = _number(row.get("value"))
        if value is None:
            shares, price = _number(row.get("shares")), _number(row.get("price"))
            value = shares * price if shares is not None and price is not None else None
        if value is None:
            invalid_fill_values += 1
        else:
            fill_values.append(abs(value))
    if _source_missing(statuses["fills"]):
        metrics["traded_value_turnover_pct"] = _missing("fills_artifact_unavailable")
    elif not valid_nav:
        metrics["traded_value_turnover_pct"] = _missing(
            "no_forward_marked_nav_denominator", len(fill_values), status="insufficient_sample")
    elif invalid_fill_values:
        metrics["traded_value_turnover_pct"] = _metric(
            None, len(fill_values), "partial", "some_fill_notional_is_missing")
    else:
        denominator = statistics.fmean(valid_nav)
        metrics["traded_value_turnover_pct"] = _available(
            round(sum(fill_values) / denominator * 100.0, 4), len(fill_values))

    # Closed holding duration/churn.  Calendar-day metrics preserve the explicit <=1d/<=3d
    # contract; canonical persisted benchmark-session companions avoid conflating weekends and
    # venue holidays.  Legacy NAV rows may supply only the session calendar, never v2 samples.
    held_days = [
        max(0, (date.fromisoformat(str(row["close_asof"]))
                - date.fromisoformat(str(row["open_asof"]))).days)
        for row in closes if row.get("open_asof") and row.get("close_asof")
    ]
    benchmark = registry.benchmark(b)
    benchmark_sessions = sorted({
        day for row in values["nav"]
        if (day := _day(row.get("date")))
        and (row.get("benchmark") == benchmark
             or (row.get("benchmark") is None and benchmark == "SPY"))
        and (_number(row.get("spy_nav")) or 0.0) > 0
    })
    session_index = {day: index for index, day in enumerate(benchmark_sessions)}
    held_sessions = [
        session_index[str(row["close_asof"])] - session_index[str(row["open_asof"])]
        for row in closes
        if row.get("open_asof") in session_index and row.get("close_asof") in session_index
        and session_index[str(row["close_asof"])] >= session_index[str(row["open_asof"])]
    ]
    if _source_missing(statuses["positions"]):
        for key in ("closed_hold_days_average", "closed_hold_days_median",
                    "closed_within_1_day_rate_pct", "closed_within_3_days_rate_pct",
                    "closed_hold_sessions_average", "closed_hold_sessions_median",
                    "closed_within_1_session_rate_pct", "closed_within_3_sessions_rate_pct"):
            metrics[key] = _missing("position_ledger_artifact_unavailable")
    else:
        if not held_days:
            reason = "no_closed_positions_with_durable_open_and_close_dates"
            for key in ("closed_hold_days_average", "closed_hold_days_median",
                        "closed_within_1_day_rate_pct", "closed_within_3_days_rate_pct"):
                metrics[key] = _missing(reason, status="insufficient_sample")
        else:
            metrics["closed_hold_days_average"] = _available(
                round(statistics.fmean(held_days), 4), len(held_days))
            metrics["closed_hold_days_median"] = _available(
                round(statistics.median(held_days), 4), len(held_days))
            metrics["closed_within_1_day_rate_pct"] = _available(
                round(100.0 * sum(value <= 1 for value in held_days) / len(held_days), 4),
                len(held_days))
            metrics["closed_within_3_days_rate_pct"] = _available(
                round(100.0 * sum(value <= 3 for value in held_days) / len(held_days), 4),
                len(held_days))
    if _source_missing(statuses["positions"]):
        pass
    elif not held_sessions:
        reason = "no_closed_positions_with_authoritative_benchmark_session_path"
        for key in ("closed_hold_sessions_average", "closed_hold_sessions_median",
                    "closed_within_1_session_rate_pct", "closed_within_3_sessions_rate_pct"):
            metrics[key] = _missing(reason, status="insufficient_sample")
    else:
        metrics["closed_hold_sessions_average"] = _available(
            round(statistics.fmean(held_sessions), 4), len(held_sessions))
        metrics["closed_hold_sessions_median"] = _available(
            round(statistics.median(held_sessions), 4), len(held_sessions))
        metrics["closed_within_1_session_rate_pct"] = _available(
            round(100.0 * sum(value <= 1 for value in held_sessions) / len(held_sessions), 4),
            len(held_sessions))
        metrics["closed_within_3_sessions_rate_pct"] = _available(
            round(100.0 * sum(value <= 3 for value in held_sessions) / len(held_sessions), 4),
            len(held_sessions))

    # Forward NAV/benchmark outcomes.  ``spy_nav`` is the legacy field name for each book's
    # configured benchmark-normalised NAV; rows with a conflicting benchmark are excluded.
    paired: list[tuple[str, float, float]] = []
    portfolio_nav: list[tuple[str, float]] = []
    for row in sorted(nav_rows, key=lambda item: _day(item.get("date")) or ""):
        day = _day(row.get("date"))
        nav_value = _number(row.get("nav"))
        if day and nav_value is not None and nav_value > 0:
            portfolio_nav.append((day, nav_value))
        row_benchmark = row.get("benchmark")
        benchmark_matches = row_benchmark == benchmark or (row_benchmark is None and benchmark == "SPY")
        bench_value = _number(row.get("spy_nav"))
        if day and nav_value is not None and nav_value > 0 and benchmark_matches \
                and bench_value is not None and bench_value > 0:
            paired.append((day, nav_value, bench_value))
    if len(paired) < 2:
        metrics["inception_benchmark_relative_return_pct"] = _missing(
            "fewer_than_two_forward_book_and_benchmark_marks", len(paired),
            status="insufficient_sample")
        metrics["benchmark_session_hit_rate_pct"] = _missing(
            "fewer_than_two_forward_book_and_benchmark_marks", max(0, len(paired) - 1),
            status="insufficient_sample")
    else:
        portfolio_return = paired[-1][1] / paired[0][1] - 1.0
        benchmark_return = paired[-1][2] / paired[0][2] - 1.0
        metrics["inception_benchmark_relative_return_pct"] = _available(
            round((portfolio_return - benchmark_return) * 100.0, 4), len(paired))
        hits = 0
        for prior, current in zip(paired, paired[1:]):
            p_ret = current[1] / prior[1] - 1.0
            b_ret = current[2] / prior[2] - 1.0
            hits += p_ret > b_ret
        metrics["benchmark_session_hit_rate_pct"] = _available(
            round(hits / (len(paired) - 1) * 100.0, 4), len(paired) - 1)
    if len(portfolio_nav) < 2:
        metrics["max_drawdown_pct"] = _missing(
            "fewer_than_two_forward_nav_marks", len(portfolio_nav), status="insufficient_sample")
    else:
        peak = portfolio_nav[0][1]
        drawdown = 0.0
        for _, value in portfolio_nav:
            peak = max(peak, value)
            drawdown = min(drawdown, value / peak - 1.0)
        metrics["max_drawdown_pct"] = _available(round(drawdown * 100.0, 4), len(portfolio_nav))

    full_exit_outcomes = _forward_full_exit_outcomes(
        values["fills"], baseline.get("fills") or [], begin, end)
    graded_full_exits = [row for row in full_exit_outcomes
                         if _number(row.get("realized_pnl")) is not None]
    durable_full_close_keys = {
        (_event_ticker(row), str(row.get("close_asof") or "")) for row in closes
    }
    durable_full_close_keys.update({
        (_event_ticker(row), str(row.get("exit_date") or ""))
        for row in post_rows if row.get("sale_kind") == "full_exit"
    })
    durable_full_close_keys.discard(("", ""))
    fifo_keys = {(_event_ticker(row), str(row.get("date") or ""))
                 for row in full_exit_outcomes}
    unreconciled_full_closes = durable_full_close_keys - fifo_keys
    reconciliation_unavailable = (
        _source_missing(statuses["positions"]) and _source_missing(statuses["post_sell"])
    )
    reconciliation_partial = (
        statuses["positions"] == "partial" or statuses["post_sell"] == "partial"
    )
    if _source_missing(statuses["fills"]):
        metrics["full_exit_hit_rate_pct"] = _missing("fills_artifact_unavailable")
    elif not full_exit_outcomes and durable_full_close_keys:
        metrics["full_exit_hit_rate_pct"] = _missing(
            "durable_full_closes_lack_complete_fifo_basis", status="partial")
    elif not full_exit_outcomes:
        metrics["full_exit_hit_rate_pct"] = _missing(
            "no_forward_full_exit_fifo_episodes", status="insufficient_sample")
    elif not graded_full_exits:
        metrics["full_exit_hit_rate_pct"] = _missing(
            "forward_full_exits_lack_complete_fifo_basis", status="missing")
    else:
        partial = (len(graded_full_exits) != len(full_exit_outcomes)
                   or bool(unreconciled_full_closes) or reconciliation_unavailable
                   or reconciliation_partial or statuses["fills"] == "partial")
        hits = sum(float(row["realized_pnl"]) > 0 for row in graded_full_exits)
        if unreconciled_full_closes:
            reason = "some_durable_full_closes_lack_complete_fifo_basis"
        elif reconciliation_unavailable:
            reason = "durable_full_close_reconciliation_artifacts_unavailable"
        elif reconciliation_partial:
            reason = "some_durable_full_close_rows_were_invalid"
        elif statuses["fills"] == "partial":
            reason = "some_fill_artifact_rows_were_invalid"
        else:
            reason = "some_forward_full_exits_lack_complete_fifo_basis" if partial else None
        metrics["full_exit_hit_rate_pct"] = _metric(
            round(100.0 * hits / len(graded_full_exits), 4), len(graded_full_exits),
            "partial" if partial else "available",
            reason)

    # Decision counts, typed actions, funnel reporting, and evidence coverage.
    metrics["decision_count"] = _artifact_count_metric(
        statuses["decisions"], decisions, len(decisions), "decision_log_artifact_unavailable")
    action_counts, effective_n, material_n = _action_projection(decisions)
    if _source_missing(statuses["decisions"]):
        metrics["effective_decision_count"] = _missing("decision_log_artifact_unavailable")
        metrics["material_change_decision_count"] = _missing("decision_log_artifact_unavailable")
        metrics["action_counts"] = _missing("decision_log_artifact_unavailable")
    else:
        metrics["effective_decision_count"] = _available(effective_n, len(decisions))
        metrics["material_change_decision_count"] = _available(material_n, effective_n)
        metrics["action_counts"] = _available(action_counts, effective_n)
    for kind in ("candidate", "finalist", "selected", "rejected"):
        metrics[f"{kind}_count"] = _count_with_reporting(decisions, kind, statuses["decisions"])

    selected_rows = [item for row in decisions for item in _selected_rows(row)]
    rejected_rows = [item for row in decisions for item in _rejected_rows(row)]
    if _source_missing(statuses["decisions"]):
        metrics["reject_reason_coverage_pct"] = _missing("decision_log_artifact_unavailable")
        metrics["provenance_coverage_pct"] = _missing("decision_log_artifact_unavailable")
        metrics["prophet_selected_context_presence_pct"] = _missing("decision_log_artifact_unavailable")
        metrics["prophet_rejected_context_presence_pct"] = _missing("decision_log_artifact_unavailable")
    else:
        metrics["reject_reason_coverage_pct"] = _rate_metric(
            rejected_rows, _coverage_reason, "no_structured_rejected_names_in_forward_decisions")
        evaluated_rows = selected_rows + rejected_rows
        metrics["provenance_coverage_pct"] = _rate_metric(
            evaluated_rows, _has_provenance, "no_structured_selected_or_rejected_names")
        metrics["prophet_selected_context_presence_pct"] = _rate_metric(
            selected_rows, _has_prophet, "no_structured_selected_names")
        metrics["prophet_rejected_context_presence_pct"] = _rate_metric(
            rejected_rows, _has_prophet, "no_structured_rejected_names")

    requested_exits = [item for row in decisions for item in (row.get("requested_exit_decisions") or [])
                       if isinstance(item, dict)]
    effective_exits = [item for row in decisions if _effective(row)
                       for item in (row.get("exit_decisions") or [])
                       if isinstance(item, dict)]
    blocked_exits: list[dict[str, Any]] = []
    omission_carried: list[dict[str, Any]] = []
    for row in decisions:
        audit = row.get("submission_audit") if isinstance(row.get("submission_audit"), dict) else {}
        blocked_exits.extend(item for item in (audit.get("blocked_exits") or []) if isinstance(item, dict))
        carried = [item for item in (audit.get("carried") or []) if isinstance(item, dict)]
        omission_carried.extend(item for item in carried
                                if item.get("reason") == "missing_explicit_exit_decision")
    for key, rows in (
        ("requested_exit_count", requested_exits),
        ("effective_exit_count", effective_exits),
        ("blocked_exit_count", blocked_exits),
        ("omission_carried_exit_count", omission_carried),
    ):
        metrics[key] = (_missing("decision_log_artifact_unavailable")
                        if _source_missing(statuses["decisions"])
                        else _available(len(rows), len(decisions)))

    # Strict memo coverage: reason + why-now + evidence must all be durably attached to the sale.
    full_exits = [row for row in post_rows if row.get("sale_kind") == "full_exit"]
    trims = [row for row in post_rows if row.get("sale_kind") == "partial_trim"]
    explicit_memo = lambda row: all(_present((row.get("decision") or {}).get(key))
                                    for key in ("reason", "why_now", "evidence"))
    if _source_missing(statuses["post_sell"]):
        metrics["full_exit_explicit_memo_coverage_pct"] = _missing("post_sell_artifact_unavailable")
        metrics["partial_trim_explicit_memo_coverage_pct"] = _missing("post_sell_artifact_unavailable")
    else:
        metrics["full_exit_explicit_memo_coverage_pct"] = _rate_metric(
            full_exits, explicit_memo, "no_forward_full_exits")
        metrics["partial_trim_explicit_memo_coverage_pct"] = _rate_metric(
            trims, explicit_memo, "no_forward_partial_trims")

    entries = [holding for row in decisions if _effective(row)
               for holding in (row.get("effective_holdings") or [])
               if isinstance(holding, dict)
               and str(holding.get("action_effective") or "").lower() == "add"]
    coverage_fields = {
        "entry_evidence_coverage_pct": "evidence",
        "entry_why_now_coverage_pct": "why_now",
        "entry_falsifier_coverage_pct": "falsifier",
        "entry_horizon_coverage_pct": "expected_horizon",
        "entry_exit_plan_coverage_pct": "exit_plan",
    }
    for metric_name, field in coverage_fields.items():
        if _source_missing(statuses["decisions"]):
            metrics[metric_name] = _missing("decision_log_artifact_unavailable")
        else:
            metrics[metric_name] = _rate_metric(
                entries, lambda row, field=field: _present(row.get(field)), "no_forward_entries")

    # Explicitly unavailable until a point-in-time, per-ticker path is approved and durable.
    excursion_reason = "authoritative_point_in_time_per_ticker_price_path_unavailable"
    metrics["early_max_adverse_excursion_pct"] = _missing(excursion_reason)
    metrics["early_max_favorable_excursion_pct"] = _missing(excursion_reason)
    metrics["return_contribution_by_sleeve_pct"] = _missing(
        "authoritative_fill_to_sleeve_return_attribution_unavailable")
    metrics["return_contribution_by_candidate_source_pct"] = _missing(
        "authoritative_fill_to_candidate_source_return_attribution_unavailable")

    partial_dependencies = {
        "decisions": {
            "effective_decision_count", "material_change_decision_count", "action_counts",
            "candidate_count", "finalist_count", "selected_count", "rejected_count",
            "reject_reason_coverage_pct", "provenance_coverage_pct",
            "prophet_selected_context_presence_pct", "prophet_rejected_context_presence_pct",
            "requested_exit_count", "effective_exit_count", "blocked_exit_count",
            "omission_carried_exit_count", "entry_evidence_coverage_pct",
            "entry_why_now_coverage_pct", "entry_falsifier_coverage_pct",
            "entry_horizon_coverage_pct", "entry_exit_plan_coverage_pct",
        },
        "nav": {
            "gross_exposure_pct", "cash_pct", "net_exposure_pct", "top_1_weight_pct",
            "top_3_weight_pct", "position_hhi", "traded_value_turnover_pct",
            "closed_hold_sessions_average", "closed_hold_sessions_median",
            "closed_within_1_session_rate_pct", "closed_within_3_sessions_rate_pct",
            "inception_benchmark_relative_return_pct", "benchmark_session_hit_rate_pct",
            "max_drawdown_pct",
        },
        "fills": {"traded_value_turnover_pct", "full_exit_hit_rate_pct"},
        "positions": {
            "closed_hold_days_average", "closed_hold_days_median",
            "closed_within_1_day_rate_pct", "closed_within_3_days_rate_pct",
            "closed_hold_sessions_average", "closed_hold_sessions_median",
            "closed_within_1_session_rate_pct", "closed_within_3_sessions_rate_pct",
            "full_exit_hit_rate_pct",
        },
        "post_sell": {
            "full_exit_explicit_memo_coverage_pct",
            "partial_trim_explicit_memo_coverage_pct", "full_exit_hit_rate_pct",
        },
    }
    for source, names in partial_dependencies.items():
        if statuses[source] != "partial":
            continue
        reason = ("duplicate_or_invalid_nav_session_rows_were_excluded"
                  if source == "nav" and all_nav_duplicates
                  else f"some_{source}_artifact_rows_were_invalid")
        for name in names:
            if name in metrics:
                metrics[name] = _partialize(metrics[name], reason)

    sample_counts = {
        "marked_sessions": len(nav_rows),
        "decisions": len(decisions),
        "effective_decisions": effective_n,
        "fills": len(fills),
        "closed_positions": len(closes),
        "post_sell_sales": len(post_rows),
        "selected_names": len(selected_rows),
        "rejected_names": len(rejected_rows),
    }
    selected_n, rejected_n = len(selected_rows), len(rejected_rows)
    first_mark = min((_day(row.get("date")) for row in nav_rows if _day(row.get("date"))),
                     default=None)
    last_mark = max((_day(row.get("date")) for row in nav_rows if _day(row.get("date"))),
                    default=None)
    inputs = {}
    row_counts = {
        "account": 1 if statuses["account"] in {"available", "partial"} else 0,
        "latest": 1 if statuses["latest"] in {"available", "partial"} else 0,
        "decisions": len(decisions), "fills": len(fills), "nav": len(nav_rows),
        "positions": len(closes), "post_sell": len(post_rows),
    }
    for key, path in raw["paths"].items():
        inputs[key] = {
            "path": _relative(path),
            "status": statuses[key],
            "forward_row_count": row_counts[key],
        }
        if key == "nav" and all_nav_duplicates:
            inputs[key]["deduplicated_row_count"] = all_nav_duplicates
            inputs[key]["forward_deduplicated_row_count"] = forward_nav_duplicates
    return {
        "schema": SCHEMA,
        "book": b,
        "asof": end,
        "paper_only": True,
        "authority": "observational_read_only",
        "cohort": {
            "evaluation_start": begin,
            "deployment_sha": marker["deployment_sha"],
            "release_state": marker["release_state"],
            "boundary": "stopped_service_baseline_ids_plus_inclusive_date_window",
            "quarantined_start_day_sources": [],
            "first_forward_mark": first_mark,
            "last_forward_mark": last_mark,
        },
        "benchmark": benchmark,
        "sample_counts": sample_counts,
        "prophet_context": {
            "authority": "context_only_non_causal",
            "causal_claim_permitted": False,
            "minimum_group_sample_n": PROPHET_MIN_GROUP_SAMPLE,
            "selected_sample_n": selected_n,
            "rejected_sample_n": rejected_n,
            "comparison_status": (
                "partial_source_non_causal" if statuses["decisions"] == "partial"
                else "descriptive_only" if min(selected_n, rejected_n) >= PROPHET_MIN_GROUP_SAMPLE
                else "insufficient_sample_non_causal"
            ),
        },
        "inputs": inputs,
        "metrics": metrics,
        "metric_status_counts": _metric_status_counts(metrics),
    }


# ---------------------------------------------------------------------------
# Idempotent persistence and compact read-only status surface
# ---------------------------------------------------------------------------

def _zero_sample_counts() -> dict[str, int]:
    return {
        "marked_sessions": 0,
        "decisions": 0,
        "effective_decisions": 0,
        "fills": 0,
        "closed_positions": 0,
        "post_sell_sales": 0,
        "selected_names": 0,
        "rejected_names": 0,
    }


def _not_started_book(book: str, marker: dict[str, Any] | None = None) -> dict[str, Any]:
    pending = bool(marker and marker.get("release_state") == "pending_health")
    return {
        "schema": STATUS_SCHEMA,
        "book": book,
        "status": "not_started",
        "release_state": marker.get("release_state") if marker else None,
        "evaluation_start": marker.get("evaluation_start") if marker else None,
        "deployment_sha": marker.get("deployment_sha") if marker else None,
        "write_permitted": False,
        "sample_counts": _zero_sample_counts(),
        "missing_reason": (
            "exact_v2_deployment_health_not_verified" if pending
            else "exact_v2_deployment_start_marker_unavailable"
        ),
    }


def _persist_snapshot(book: str, snapshot: dict[str, Any]) -> None:
    """Persist one dated row and retain an immutable receipt for same-asof corrections."""
    out = _book_output_dir(book)
    dated = out / f"{snapshot['asof']}.json"
    if dated.exists():
        prior, prior_status = _read_json_object(dated)
        if prior_status != "available" or prior.get("schema") != SCHEMA:
            raise RuntimeError("existing forward snapshot is invalid; refusing unaudited overwrite")
        if prior != snapshot:
            prior_hash = _digest(prior)
            replacement_hash = _digest(snapshot)
            revision_path = out / "revisions" / str(snapshot["asof"]) / f"{prior_hash}.json"
            receipt_path = (out / "corrections" / str(snapshot["asof"]) /
                            f"{prior_hash}--{replacement_hash}.json")
            _atomic_create_once(revision_path, prior)
            _atomic_create_once(receipt_path, {
                "schema": "mastermind.portfolio_forward_evaluation.correction.v1",
                "book": book,
                "asof": snapshot["asof"],
                "reason": "durable_source_artifact_changed_for_same_asof",
                "prior_snapshot_sha256": prior_hash,
                "replacement_snapshot_sha256": replacement_hash,
                "prior_revision_path": _relative(revision_path),
                "replacement_path": _relative(dated),
            })
    _atomic_write(dated, snapshot)
    latest_path = out / "latest.json"
    latest, latest_status = _read_json_object(latest_path)
    latest_asof = _day(latest.get("asof")) if latest_status == "available" else None
    if latest_asof is None or str(snapshot["asof"]) >= latest_asof:
        _atomic_write(latest_path, snapshot)


def _run_status_path(book: str) -> Path:
    return _book_output_dir(book) / "run_status.json"


def record_failure(book: str, asof: str | date, exc: BaseException) -> None:
    """Publish a durable, read-only-visible failure without interrupting the paper book."""
    b = str(book or "").lower().strip()
    if b not in ACTIVE_BOOKS:
        return
    _atomic_write(_run_status_path(b), {
        "schema": STATUS_SCHEMA,
        "book": b,
        "status": "error",
        "stale": True,
        "last_attempt_asof": _validate_day(asof),
        "error_type": type(exc).__name__,
        "error": str(exc)[:300],
    })


def _record_success(book: str, asof: str) -> None:
    _atomic_write(_run_status_path(book), {
        "schema": STATUS_SCHEMA,
        "book": book,
        "status": "ok",
        "stale": False,
        "last_success_asof": asof,
    })


def evaluate(book: str, asof: str | date) -> dict[str, Any]:
    """Build and atomically persist one active-book snapshot.

    Archived books return a stable no-op before looking for or creating any path.  Missing cohort
    authority also returns ``not_started`` with no directory or file write.
    """
    b = str(book or "").lower().strip()
    end = _validate_day(asof)
    if registry.is_archived(b):
        return {
            **registry.archived_run_result(b, end),
            "schema": STATUS_SCHEMA,
            "write_permitted": False,
            "sample_counts": _zero_sample_counts(),
        }
    if b not in ACTIVE_BOOKS:
        raise ValueError(f"unsupported active forward-evaluation book: {b!r}")
    if end > _utc_today():
        return {
            "schema": STATUS_SCHEMA,
            "book": b,
            "asof": end,
            "status": "future_asof",
            "write_permitted": False,
            "sample_counts": _zero_sample_counts(),
            "missing_reason": "asof_is_after_current_utc_date",
        }
    marker = load_start()
    if marker is None:
        return _not_started_book(b)
    if marker.get("release_state") != "active":
        return _not_started_book(b, marker)
    snapshot = build_snapshot(b, end, start=marker)
    if snapshot.get("schema") != SCHEMA:
        return snapshot
    _persist_snapshot(b, snapshot)
    _record_success(b, snapshot["asof"])
    return snapshot


run = evaluate


def load_snapshot(book: str, asof: str | date | None = None) -> dict[str, Any] | None:
    b = str(book or "").lower().strip()
    if not registry.is_known(b):
        return None
    name = "latest.json" if asof is None else f"{_validate_day(asof)}.json"
    value, state = _read_json_object(_book_output_dir(b) / name)
    return value if state == "available" and value.get("schema") == SCHEMA else None


def _book_status(book: str, asof: str | date | None = None) -> dict[str, Any]:
    if registry.is_archived(book):
        return {
            "book": book,
            "status": "archived",
            "lifecycle": "archived",
            "write_permitted": False,
            "sample_counts": _zero_sample_counts(),
            "snapshot": load_snapshot(book, asof),
        }
    marker = load_start()
    if marker is None:
        return _not_started_book(book)
    if marker.get("release_state") != "active":
        return _not_started_book(book, marker)
    if asof is not None and _validate_day(asof) < marker["evaluation_start"]:
        return {
            "book": book,
            "status": "before_evaluation_start",
            "lifecycle": "active",
            "write_permitted": False,
            "evaluation_start": marker["evaluation_start"],
            "deployment_sha": marker["deployment_sha"],
            "sample_counts": _zero_sample_counts(),
            "snapshot": None,
        }
    snapshot = load_snapshot(book, asof)
    run_state, run_state_status = _read_json_object(_run_status_path(book))
    evaluation_run = (run_state if run_state_status == "available"
                      and run_state.get("schema") == STATUS_SCHEMA else None)
    if snapshot is None:
        return {
            "book": book,
            "status": ("stale_after_error" if evaluation_run
                       and evaluation_run.get("status") == "error"
                       else "awaiting_first_post_mark_snapshot"),
            "lifecycle": "active",
            "write_permitted": True,
            "evaluation_start": marker["evaluation_start"],
            "deployment_sha": marker["deployment_sha"],
            "latest_asof": None,
            "sample_counts": _zero_sample_counts(),
            "evaluation_run": evaluation_run,
            "snapshot": None,
        }
    return {
        "book": book,
        "status": ("stale_after_error" if evaluation_run
                   and evaluation_run.get("status") == "error" else "available"),
        "lifecycle": "active",
        "write_permitted": True,
        "evaluation_start": marker["evaluation_start"],
        "deployment_sha": marker["deployment_sha"],
        "latest_asof": snapshot.get("asof"),
        "sample_counts": snapshot.get("sample_counts") or _zero_sample_counts(),
        "metric_status_counts": snapshot.get("metric_status_counts") or {},
        "evaluation_run": evaluation_run,
        "snapshot": snapshot,
    }


def status(book: str | None = None, asof: str | date | None = None) -> dict[str, Any]:
    """Read-only status/API contract.  It never computes or writes a snapshot."""
    if book is not None:
        b = str(book or "").lower().strip()
        if not registry.is_known(b):
            return {
                "schema": STATUS_SCHEMA,
                "book": b,
                "status": "unknown_book",
                "write_permitted": False,
                "sample_counts": _zero_sample_counts(),
                "snapshot": None,
            }
        if b not in ACTIVE_BOOKS and not registry.is_archived(b):
            return {
                "schema": STATUS_SCHEMA,
                "book": b,
                "status": "unsupported_book",
                "lifecycle": "unsupported",
                "write_permitted": False,
                "sample_counts": _zero_sample_counts(),
                "snapshot": None,
            }
        return {"schema": STATUS_SCHEMA, **_book_status(b, asof)}
    marker = load_start()
    books = [_book_status(item, asof) for item in ACTIVE_BOOKS]
    active = bool(marker and marker.get("release_state") == "active")
    return {
        "schema": STATUS_SCHEMA,
        "status": "started" if active else "not_started",
        "release_state": marker.get("release_state") if marker else None,
        "evaluation_start": marker.get("evaluation_start") if marker else None,
        "deployment_sha": marker.get("deployment_sha") if marker else None,
        "books": books,
    }


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded Mastermind Portfolio forward evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="initialise the exact-deployment v2 cohort once")
    init.add_argument("--deployment-sha", required=True)
    init.add_argument("--asof", default=datetime.now(UTC).date().isoformat())
    finalize = sub.add_parser("finalize", help="activate the cohort after exact-SHA health")
    finalize.add_argument("--deployment-sha", required=True)
    show = sub.add_parser("status", help="read the cohort/snapshot status without writing")
    show.add_argument("--book", choices=registry.ids())
    show.add_argument("--asof")
    run_parser = sub.add_parser("run", help="evaluate one active book after a durable mark")
    run_parser.add_argument("--book", choices=ACTIVE_BOOKS, required=True)
    run_parser.add_argument("--asof", required=True)
    args = parser.parse_args(argv)
    # Only deploy-facing cohort commands honor the host-namespace override. The scheduler/API and
    # even the CLI ``run`` leaf remain confined to their ordinary in-service data namespace.
    release_root = (os.environ.get(_RELEASE_STATE_ROOT_ENV)
                    if args.command in {"init", "finalize", "status"} else None)
    with _release_data_root(release_root):
        if args.command == "init":
            payload = initialize_start(args.deployment_sha, args.asof)
        elif args.command == "finalize":
            payload = finalize_start(args.deployment_sha)
        elif args.command == "run":
            payload = evaluate(args.book, args.asof)
        else:
            payload = status(args.book, args.asof)
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    if args.command == "status" and payload.get("status") in {"not_started", "unknown_book"}:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by deploy provenance tests
    raise SystemExit(_cli())
