"""Display-only crypto universe and dated snapshot coverage.

The collector's asset files accrue independently; an old rank must not re-enter
a newer cross-section. Source bytes are never modified by this read projection.
No trading or allocation authority is owned here.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from lib import config


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return out if np.isfinite(out) else None


def _state(change_30d: float | None, change_7d: float | None) -> tuple[str, str]:
    """Return restrained display state and tone from price follow-through."""
    guide = change_30d if change_30d is not None else change_7d
    if guide is None:
        return "Building", "neutral"
    if guide >= 15:
        return "Leading", "bull"
    if guide >= 3:
        return "Firm", "bull"
    if guide <= -15:
        return "Weak", "bear"
    if guide <= -3:
        return "Fading", "bear"
    return "Range", "neutral"


def _history_chip(days: int) -> str:
    if days >= 90:
        return "90D"
    if days >= 30:
        return f"{days}D"
    return "Building"


# Same-day duplicates only. A row whose observed_at is not the snapshot date is
# already excluded, so it cannot win the collapse and re-enter as current.
DUPLICATE_ID_RULE = (
    "same id: drop observed_at that is not the snapshot date and drop ranks on "
    "an absent page, then keep the lowest rank, breaking ties by symbol "
    "ascending and then document order; discarded copies are DUPLICATE_ID"
)
_STRIPPED_FIELDS = ("recommendation", "allocation", "score", "signal", "action")


class UniverseUnavailable(dict):
    """Point-in-time membership this store does not hold.

    ``rows`` is empty. The current roster is not returned in its place.
    """


class UniverseRows(list):
    """Admitted rows plus the coverage denominator actually observed."""

    def __init__(self, iterable, coverage: dict):
        super().__init__(iterable)
        self.coverage = coverage


def _iso_date(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    text = value[:10]
    try:
        date.fromisoformat(text)
    except ValueError:
        return None
    return text


def _unavailable(as_of: str | None, top_n: int, reason: str) -> UniverseUnavailable:
    return UniverseUnavailable({
        "schema": "crypto.universe_snapshot/v1",
        "status": "unavailable",
        "available": False,
        "reason": reason,
        "view": "point-in-time",
        "date": as_of,
        "as_of": as_of,
        "source": None,
        "page_coverage": None,
        "coverage": None,
        "duplicate_rule": DUPLICATE_ID_RULE,
        "rows": [],
        "excluded": [],
        "requested": top_n,
        "observed": 0,
        "sources": [],
    })


def _collapse_duplicate_ids(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    grouped: dict[str, list[tuple[int, dict]]] = {}
    for index, row in enumerate(rows):
        grouped.setdefault(str(row.get("id")), []).append((index, row))
    kept: list[dict] = []
    excluded: list[dict] = []
    for items in grouped.values():
        ordered = sorted(
            items,
            key=lambda item: (item[1]["rank"], item[1]["symbol"], item[1].get("_order", item[0])),
        )
        kept.append(ordered[0][1])
        for _, row in ordered[1:]:
            excluded.append({
                "file": None,
                "symbol": row.get("symbol"),
                "id": row.get("id"),
                "source": row.get("source"),
                "as_of": row.get("as_of"),
                "reason": "DUPLICATE_ID",
            })
    return kept, excluded


def _page_coverage(raw_pages: Any) -> list[dict]:
    pages: list[dict] = []
    if not isinstance(raw_pages, list):
        return pages
    for page in raw_pages:
        if not isinstance(page, dict):
            continue
        rank_from = _number(page.get("rank_from"))
        rank_to = _number(page.get("rank_to"))
        if rank_from is None or rank_to is None or not rank_from.is_integer() or not rank_to.is_integer():
            continue
        pages.append({
            "name": str(page.get("name") or ""),
            "rank_from": int(rank_from),
            "rank_to": int(rank_to),
            "present": bool(page.get("present")),
        })
    return pages


def _coverage(admitted: int, expected: Any, pages: list[dict], ranks: set[int]) -> dict:
    missing_pages = [page["name"] for page in pages if not page["present"]]
    present_pages = [page for page in pages if page["present"]]
    pages_filled = bool(present_pages) and all(
        set(range(page["rank_from"], page["rank_to"] + 1)) <= ranks
        for page in present_pages
    )
    expected_n = expected if isinstance(expected, int) and not isinstance(expected, bool) else None
    complete = (
        expected_n is not None
        and admitted == expected_n
        and not missing_pages
        and pages_filled
    )
    label = f"{admitted}/{expected_n}" if expected_n is not None else f"{admitted}/unavailable"
    return {
        "observed": admitted,
        "expected": expected_n,
        "missing_pages": missing_pages,
        "label": label,
        "complete": complete,
        "pages_declared": True,
    }


def _project_document(doc: dict, top_n: int, view: str, filename: str) -> dict:
    snapshot_date = _iso_date(doc.get("as_of"))
    source = str(doc.get("source") or "Unknown")
    pages = _page_coverage(doc.get("pages"))
    absent = [page for page in pages if not page["present"]]
    excluded: list[dict] = []
    candidates: list[dict] = []
    raw_rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            excluded.append({
                "file": filename, "symbol": None, "id": None, "source": source,
                "as_of": None, "reason": "UNREADABLE_ROW",
            })
            continue
        observed = _iso_date(raw.get("observed_at"))
        identity = str(raw.get("id") or "").strip()
        symbol = str(raw.get("symbol") or "").strip().upper()
        receipt = {
            "file": filename, "symbol": symbol or None, "id": identity or None,
            "source": str(raw.get("source") or source), "as_of": observed,
        }
        if observed != snapshot_date:
            excluded.append({**receipt, "reason": "STALE_OBSERVATION"})
            continue
        if raw.get("source") not in (None, "", source):
            excluded.append({**receipt, "reason": "SOURCE_MISMATCH"})
            continue
        rank = _number(raw.get("rank"))
        if rank is None or not rank.is_integer() or rank < 1:
            excluded.append({**receipt, "reason": "INVALID_RANK"})
            continue
        rank_i = int(rank)
        if any(page["rank_from"] <= rank_i <= page["rank_to"] for page in absent):
            excluded.append({**receipt, "reason": "PAGE_ABSENT", "rank": rank_i})
            continue
        if pages and not any(
            page["present"] and page["rank_from"] <= rank_i <= page["rank_to"]
            for page in pages
        ):
            excluded.append({**receipt, "reason": "RANK_NOT_IN_DECLARED_PAGE", "rank": rank_i})
            continue
        if rank_i > top_n:
            excluded.append({**receipt, "reason": "OUTSIDE_RANK_RANGE", "rank": rank_i})
            continue
        price = _number(raw.get("price", raw.get("current_price")))
        if price is None or price <= 0:
            excluded.append({**receipt, "reason": "INVALID_LATEST_PRICE"})
            continue
        if not identity or not symbol:
            excluded.append({**receipt, "reason": "MISSING_ASSET_IDENTITY"})
            continue
        history_days = raw.get("history_days")
        if isinstance(history_days, bool) or not isinstance(history_days, int) or history_days < 0:
            history_days = 0
        change_30d = _number(raw.get("change_30d_pct", raw.get("change_30d")))
        change_7d = _number(raw.get("change_7d_pct", raw.get("change_7d")))
        change_24h = _number(raw.get("change_24h_pct", raw.get("change_24h")))
        state, tone = _state(change_30d, change_7d)
        rank_prev = _number(raw.get("rank_prev"))
        projected = {
            "id": identity,
            "source": source,
            "symbol": symbol,
            "name": str(raw.get("name") or symbol),
            "rank": rank_i,
            "price": price,
            "change_24h": change_24h,
            "change_7d": change_7d,
            "change_30d": change_30d,
            "market_cap": _number(raw.get("market_cap")),
            "volume": _number(raw.get("total_volume", raw.get("volume"))),
            "state": state,
            "tone": tone,
            "history_days": history_days,
            "history_chip": _history_chip(history_days),
            "history_reset": None,
            "spark_dates": [],
            "spark_values": [],
            "as_of": snapshot_date,
            "_order": index,
        }
        if rank_prev is not None and rank_prev.is_integer():
            projected["rank_prev"] = int(rank_prev)
        for field in _STRIPPED_FIELDS:
            projected.pop(field, None)
        candidates.append(projected)
    kept, duplicate_excluded = _collapse_duplicate_ids(candidates)
    excluded.extend(duplicate_excluded)
    for row in kept:
        row.pop("_order", None)
    kept = sorted(kept, key=lambda item: (item["rank"], item["symbol"]))[:top_n]
    coverage = _coverage(
        len(kept), doc.get("expected_n"), pages, {row["rank"] for row in kept},
    )
    return {
        "schema": str(doc.get("schema") or "crypto.universe_snapshot/v1"),
        "status": view,
        "view": view,
        "available": True,
        "date": snapshot_date,
        "as_of": snapshot_date,
        "source": source,
        "page_coverage": pages,
        "coverage": coverage,
        "duplicate_rule": DUPLICATE_ID_RULE,
        "rows": UniverseRows(kept, coverage),
        "excluded": excluded,
        "requested": top_n,
        "observed": len(raw_rows),
        "sources": sorted({row["source"] for row in kept}),
    }


def _load_snapshot_documents(paths: list[Path], top_n: int, as_of: str | None) -> dict:
    parsed: list[tuple[Path, dict]] = []
    unreadable: list[dict] = []
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or _iso_date(document.get("as_of")) is None:
                raise ValueError("snapshot identity is incomplete")
            parsed.append((path, document))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            unreadable.append({
                "file": path.name, "symbol": None, "id": None, "source": None,
                "as_of": None, "reason": "UNREADABLE_SNAPSHOT",
            })
    by_date: dict[str, list[tuple[Path, dict]]] = {}
    for path, document in parsed:
        by_date.setdefault(_iso_date(document.get("as_of")) or "", []).append((path, document))
    if as_of is not None:
        if _iso_date(as_of) is None:
            return _unavailable(as_of, top_n, "INVALID_AS_OF")
        matches = by_date.get(as_of, [])
        if len(matches) > 1:
            return _unavailable(as_of, top_n, "DUPLICATE_SNAPSHOT_DATE")
        if len(matches) != 1:
            refused = _unavailable(as_of, top_n, "HISTORICAL_MEMBERSHIP_UNAVAILABLE")
            refused["excluded"] = unreadable
            return refused
        path, document = matches[0]
        return _project_document(document, top_n, "point-in-time", path.name)
    if not by_date:
        refused = _unavailable(None, top_n, "SNAPSHOT_UNAVAILABLE")
        refused["view"] = "current-roster"
        refused["excluded"] = unreadable
        return refused
    newest = max(by_date)
    matches = by_date[newest]
    if len(matches) > 1:
        refused = _unavailable(newest, top_n, "DUPLICATE_SNAPSHOT_DATE")
        refused["view"] = "current-roster"
        return refused
    path, document = matches[0]
    return _project_document(document, top_n, "current-roster", path.name)


def _label_parquet_view(snapshot: dict, as_of: str | None, top_n: int) -> dict:
    labeled = dict(snapshot)
    sources = list(labeled.get("sources") or [])
    admitted = len(labeled.get("rows") or [])
    labeled["duplicate_rule"] = DUPLICATE_ID_RULE
    labeled["date"] = labeled.get("as_of")
    labeled["source"] = sources[0] if len(sources) == 1 else None
    labeled["page_coverage"] = None
    labeled["coverage"] = {
        "observed": admitted,
        "expected": top_n,
        "missing_pages": [],
        "label": f"{admitted}/{top_n}",
        "complete": False,
        "pages_declared": False,
    }
    labeled["schema"] = "crypto.universe_snapshot/v1"
    if as_of is None:
        labeled["view"] = "current-roster"
        labeled["status"] = "current-roster"
        labeled["available"] = True
        return labeled
    if _iso_date(as_of) is None:
        return _unavailable(as_of, top_n, "INVALID_AS_OF")
    if labeled.get("as_of") != as_of:
        return _unavailable(as_of, top_n, "HISTORICAL_MEMBERSHIP_UNAVAILABLE")
    labeled["view"] = "point-in-time"
    labeled["status"] = "point-in-time"
    labeled["available"] = True
    return labeled


def _load_parquet_snapshot(top_n: int = 50, root: Path | None = None) -> dict:
    """Read one latest recorded cross-section, with inspectable exclusions.

    `as_of` is the collector observation date, not a live quote or a provider
    publication-time guarantee. An unreadable/invalid latest row is never
    replaced with an older valid quote. Older files remain in the source store.
    """
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    root = root or (config.data_dir() / "crypto_universe")
    observations: list[tuple[dict, pd.DataFrame, pd.Series]] = []
    excluded: list[dict] = []
    today = pd.Timestamp.now(tz="UTC").normalize()
    for path in sorted(root.glob("market_*.parquet")) if root.exists() else []:
        receipt = {"file": path.name, "symbol": path.stem.removeprefix("market_").upper(),
                   "id": None, "source": None, "as_of": None}
        try:
            frame = pd.read_parquet(path)
            if frame.empty:
                excluded.append({**receipt, "reason": "EMPTY_HISTORY"})
                continue
            frame.index = pd.to_datetime(frame.index, utc=True, errors="raise")
            if frame.index.hasnans:
                raise ValueError("missing observation date")
            frame = frame.sort_index(kind="stable")
            # A collector observation is daily; repeated dates do not create
            # additional history coverage. Keep the last recorded row per day.
            frame.index = frame.index.normalize()
            frame = frame.loc[~frame.index.duplicated(keep="last")]
            current = frame.iloc[-1]
            receipt.update({
                "id": str(current.get("coin_id") or path.stem.removeprefix("market_")),
                "source": str(current.get("source") or "Unknown"),
                "symbol": str(current.get("symbol") or "").upper(),
                "as_of": str(frame.index[-1].date()),
            })
            if frame.index[-1] > today:
                excluded.append({**receipt, "reason": "FUTURE_OBSERVATION"})
                continue
            observations.append((receipt, frame, current))
        except Exception:
            excluded.append({**receipt, "reason": "UNREADABLE_HISTORY"})

    as_of = max((r[0]["as_of"] for r in observations), default=None)
    rows: list[dict] = []
    for receipt, frame, current in observations:
        rank = _number(current.get("market_cap_rank"))
        price = _number(current.get("current_price"))
        if receipt["as_of"] != as_of:
            reason = "OLDER_SNAPSHOT"
        elif rank is None or not rank.is_integer() or rank < 1:
            reason = "INVALID_RANK"
        elif rank > top_n:
            reason = "OUTSIDE_RANK_RANGE"
        elif price is None or price <= 0:
            reason = "INVALID_LATEST_PRICE"
        elif not receipt["symbol"]:
            reason = "MISSING_ASSET_IDENTITY"
        else:
            reason = None
        if reason:
            excluded.append({**receipt, "reason": reason})
            continue

        # Files are keyed by ticker, not globally unique asset identity. Without
        # a canonical crosswalk, a source/id change breaks historical continuity.
        same_identity = pd.Series(True, index=frame.index)
        for column, value in (("source", receipt["source"]), ("coin_id", receipt["id"])):
            if column in frame:
                same_identity &= frame[column].eq(value).fillna(False)
        breaks = np.flatnonzero(~same_identity.to_numpy())
        start = int(breaks[-1]) + 1 if len(breaks) else 0
        history_frame = frame.iloc[start:]
        prices = pd.to_numeric(history_frame["current_price"], errors="coerce")
        prices = prices.loc[np.isfinite(prices) & (prices > 0)]
        hist = prices.tail(90)
        c24 = _number(current.get("change_24h_pct"))
        c7 = _number(current.get("change_7d_pct"))
        c30 = _number(current.get("change_30d_pct"))
        state, tone = _state(c30, c7)
        rows.append({
            "id": receipt["id"], "source": receipt["source"],
            "symbol": receipt["symbol"],
            "name": str(current.get("name") or receipt["symbol"]),
            "rank": int(rank), "price": price,
            "change_24h": c24, "change_7d": c7, "change_30d": c30,
            "market_cap": _number(current.get("market_cap")),
            "volume": _number(current.get("total_volume")),
            "state": state, "tone": tone,
            "history_days": len(hist), "history_chip": _history_chip(len(hist)),
            "history_reset": "SOURCE_IDENTITY_CHANGED" if start else None,
            "spark_dates": [str(x.date()) for x in hist.index],
            "spark_values": [round(float(x), 8) for x in hist.to_numpy()],
            "as_of": receipt["as_of"],
        })
    kept, duplicate_excluded = _collapse_duplicate_ids(rows)
    excluded.extend(duplicate_excluded)
    rows = sorted(kept, key=lambda x: (x["rank"], x["symbol"]))[:top_n]
    return {"as_of": as_of, "rows": rows, "excluded": excluded,
            "requested": top_n, "observed": len(observations),
            "sources": sorted({row["source"] for row in rows})}


def load_universe_snapshot(top_n: int = 50, root: Path | None = None, *, as_of: str | None = None) -> dict:
    """Read one recorded cross-section.

    ``as_of=None`` is the current roster. A point-in-time date that has no
    stored membership document is refused; today's rows are not substituted.
    ``snapshot_*.json`` documents are the membership plane. Parquet accrual is
    used only when that directory has no membership document.
    """
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    root = root or (config.data_dir() / "crypto_universe")
    documents = sorted(root.glob("snapshot_*.json")) if root.exists() else []
    if documents:
        return _load_snapshot_documents(documents, top_n, as_of)
    return _label_parquet_view(_load_parquet_snapshot(top_n, root), as_of, top_n)


def load_universe(top_n: int = 50, root: Path | None = None) -> list[dict]:
    """Compatibility projection of the same dated snapshot, not another loader."""
    return load_universe_snapshot(top_n, root)["rows"]


def breadth_read(rows: list[dict]) -> dict:
    """Share with a positive reported 30-day return, not altseason or forecast.

    A missing return is excluded, never counted as zero or a negative vote.
    The existing minimum of ten assets and accrued-history gate are retained.
    """
    as_of = max((r.get("as_of") for r in rows if r.get("as_of")), default=None)
    eligible = []
    for row in rows:
        days = _number(row.get("history_days"))
        change = _number(row.get("change_30d"))
        if (days is not None and days >= 30 and change is not None
                and (as_of is None or row.get("as_of") == as_of)):
            eligible.append(change)
    positive = sum(change > 0 for change in eligible)
    # The ratio uses the eligible rows in hand. A declared universe size is not
    # a substitute denominator, and a missing return was not added in as zero.
    denominator = len(eligible)
    receipt = {"as_of": as_of, "eligible": len(eligible), "required": 10,
               "excluded": len(rows) - len(eligible), "positive": positive,
               "denominator": denominator,
               "basis": "reported_30d_return_positive"}
    coverage = getattr(rows, "coverage", None)
    if isinstance(coverage, dict):
        receipt["coverage"] = {
            "observed": coverage.get("observed"),
            "expected": coverage.get("expected"),
            "missing_pages": list(coverage.get("missing_pages") or []),
            "label": coverage.get("label"),
            "complete": coverage.get("complete"),
        }
    if len(eligible) < 10:
        return {**receipt, "available": False, "value": None,
                "state": "Building history", "tone": "neutral"}
    pct = round(100 * positive / denominator)
    return {**receipt, "available": True, "value": pct,
            "state": "Broad" if pct >= 60 else ("Narrow" if pct <= 40 else "Mixed"),
            "tone": "bull" if pct >= 60 else ("bear" if pct <= 40 else "neutral")}
