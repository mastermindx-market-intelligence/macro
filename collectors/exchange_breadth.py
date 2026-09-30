"""Point-in-time XNYS breadth collector backed by the existing Massive stores.

The collector owns no new identity, price, calendar, or publication plane.  It
observes an XNYS roster and split events, resolves them through the incumbent
Data OS alias table, reads raw closes from ``massive_stock_day``, and publishes
research/display artifacts only after the whole candidate generation validates.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests

from collectors.base import Adapter, safe_exc_text
from engine.exchange_breadth import (
    AUTHORITY,
    SOURCE_RULES_VERSION,
    UNIVERSE_ALL_ISSUES,
    UNIVERSE_OPERATING,
    assemble_entity_close_panel,
    compute_breadth_history,
    normalize_roster,
    update_membership_intervals,
)
from lib import config
from lib.dataos.identity import VendorAliasTable
from lib.nyse_calendar import (
    expected_last_session,
    is_session,
    last_session_on_or_before,
)

ROSTER_PATH = "/v3/reference/tickers"
SPLITS_PATH = "/stocks/v1/splits"
PRICE_BASIS = "massive_stock_day.raw_daily_aggregate+pit_splits"
SCHEMA_VERSION = "exchange_breadth.collector.v1"
OUTPUT_DIR = "exchange_breadth"

_INTERVALS_FILE = "universe_intervals.parquet"
_SPLITS_FILE = "source_splits.parquet"
_STATE_FILE = "_state.json"
_RECEIPT_FILE = "_receipt.json"
_FRAME_FILES = {
    UNIVERSE_OPERATING: "nyse_operating.parquet",
    UNIVERSE_ALL_ISSUES: "nyse_all_issues.parquet",
}

RequestJson = Callable[[str, dict[str, Any]], Mapping[str, Any]]
PriceLoader = Callable[[str], pd.DataFrame]


class CollectionRefused(RuntimeError):
    """Candidate evidence was incomplete or internally inconsistent."""


@dataclass(frozen=True)
class PageBundle:
    rows: tuple[dict[str, Any], ...]
    receipt: dict[str, Any]


@dataclass(frozen=True)
class CollectionResult:
    frames: dict[str, pd.DataFrame]
    receipt: dict[str, Any]
    state: dict[str, Any]


def _safe_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _coerce_date(value: object, *, field: str) -> date:
    try:
        return pd.Timestamp(value).date()
    except Exception as exc:  # noqa: BLE001
        raise CollectionRefused(f"invalid {field}: {value!r}") from exc


def _active(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "active"}
    return bool(value)


def _normal_text(value: object, *, upper: bool = False) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.upper() if upper else text


class MassiveReferenceClient:
    """Mockable, fail-closed paginator for Massive-compatible REST endpoints."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.polygon.io",
        request_json: RequestJson | None = None,
        max_pages: int = 50,
        timeout_s: float = 60.0,
    ) -> None:
        key = str(api_key or "").strip()
        if not key:
            raise ValueError("api_key is required")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        self.api_key = key
        self.base_url = str(base_url).rstrip("/")
        self.max_pages = int(max_pages)
        self.timeout_s = float(timeout_s)
        self._request_json = request_json or self._requests_json

    def _requests_json(self, url: str, params: dict[str, Any]) -> Mapping[str, Any]:
        response = requests.get(
            url,
            params=params,
            timeout=self.timeout_s,
            headers={"User-Agent": "MastermindX exchange-breadth/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise TypeError("source response is not a JSON object")
        return payload

    def _pages(
        self,
        path: str,
        params: dict[str, Any],
        *,
        source_kind: str,
    ) -> PageBundle:
        url = f"{self.base_url}{path}"
        first_params = dict(params)
        first_params["apiKey"] = self.api_key
        call_params = first_params
        limit = int(params.get("limit", 1000))
        rows: list[dict[str, Any]] = []
        request_ids: list[str] = []
        safe_urls: list[str] = []
        seen_urls: set[str] = set()
        page = 0

        while True:
            page += 1
            if page > self.max_pages:
                raise CollectionRefused(
                    f"{source_kind} pagination exceeded page cap {self.max_pages}"
                )
            marker = f"{url}|{sorted((str(k), str(v)) for k, v in call_params.items() if k != 'apiKey')}"
            if marker in seen_urls:
                raise CollectionRefused(f"{source_kind} pagination repeated a cursor")
            seen_urls.add(marker)
            try:
                payload = self._request_json(url, call_params)
            except Exception as exc:  # noqa: BLE001
                raise CollectionRefused(
                    f"{source_kind} request failed: {safe_exc_text(exc)}"
                ) from exc
            if not isinstance(payload, Mapping):
                raise CollectionRefused(f"{source_kind} response is not an object")
            status = str(payload.get("status") or "").upper()
            if status != "OK":
                raise CollectionRefused(
                    f"{source_kind} non-OK response: {status or 'missing status'}"
                )
            page_rows = payload.get("results")
            if not isinstance(page_rows, list):
                raise CollectionRefused(f"{source_kind} results are not a list")
            if not page_rows:
                raise CollectionRefused(f"{source_kind} empty response")
            if not all(isinstance(row, Mapping) for row in page_rows):
                raise CollectionRefused(f"{source_kind} contains a non-object row")

            next_url = payload.get("next_url")
            try:
                reported_count = int(payload.get("count", len(page_rows)))
            except (TypeError, ValueError) as exc:
                raise CollectionRefused(f"{source_kind} count is invalid") from exc
            if reported_count < len(page_rows):
                raise CollectionRefused(
                    f"{source_kind} count is smaller than returned results"
                )
            if not next_url and reported_count >= limit:
                raise CollectionRefused(
                    f"{source_kind} response appears truncated: count={reported_count}, "
                    f"limit={limit}, next_url absent"
                )

            rows.extend(dict(row) for row in page_rows)
            request_id = _normal_text(payload.get("request_id"))
            if request_id:
                request_ids.append(request_id)
            safe_urls.append(_safe_url(url))
            if not next_url:
                break
            if page >= self.max_pages:
                raise CollectionRefused(
                    f"{source_kind} pagination exceeded page cap {self.max_pages}"
                )
            if not isinstance(next_url, str) or not next_url.strip():
                raise CollectionRefused(f"{source_kind} next_url is invalid")
            url = next_url.strip()
            call_params = {"apiKey": self.api_key}

        return PageBundle(
            rows=tuple(rows),
            receipt={
                "endpoint": _safe_url(f"{self.base_url}{path}"),
                "pages": page,
                "row_count": len(rows),
                "request_ids": request_ids,
                "page_urls": safe_urls,
            },
        )

    def fetch_roster(self, session: date, *, min_rows: int) -> PageBundle:
        bundle = self._pages(
            ROSTER_PATH,
            {
                "market": "stocks",
                "exchange": "XNYS",
                "date": session.isoformat(),
                "active": "true",
                "limit": 1000,
                "sort": "ticker",
                "order": "asc",
            },
            source_kind="roster",
        )
        if len(bundle.rows) < int(min_rows):
            raise CollectionRefused(
                f"roster row floor not met: {len(bundle.rows)} < {int(min_rows)}"
            )
        seen: set[str] = set()
        validated: list[dict[str, Any]] = []
        for row in bundle.rows:
            ticker = _normal_text(row.get("ticker"), upper=True)
            if not ticker:
                raise CollectionRefused("roster row missing ticker")
            if ticker in seen:
                raise CollectionRefused(f"roster duplicate ticker: {ticker}")
            seen.add(ticker)
            exchange = _normal_text(row.get("primary_exchange"), upper=True)
            if exchange != "XNYS":
                raise CollectionRefused(
                    f"roster wrong exchange for {ticker}: {exchange!r}"
                )
            if str(row.get("market") or "").lower() != "stocks":
                raise CollectionRefused(f"roster wrong market for {ticker}")
            if not _active(row.get("active")):
                raise CollectionRefused(f"roster inactive row for {ticker}")
            validated.append(dict(row, ticker=ticker, primary_exchange=exchange))
        receipt = dict(bundle.receipt)
        receipt["requested_session"] = session.isoformat()
        return PageBundle(tuple(validated), receipt)

    def fetch_splits(self, start: date, end: date) -> PageBundle:
        if start > end:
            raise ValueError("split start must not be after end")
        bundle = self._pages(
            SPLITS_PATH,
            {
                "execution_date.gte": start.isoformat(),
                "execution_date.lte": end.isoformat(),
                "limit": 1000,
                "sort": "execution_date",
                "order": "asc",
            },
            source_kind="splits",
        )
        seen: set[str] = set()
        validated: list[dict[str, Any]] = []
        for row in bundle.rows:
            ticker = _normal_text(row.get("ticker"), upper=True)
            if not ticker:
                raise CollectionRefused("split row missing ticker")
            event_date = _coerce_date(
                row.get("execution_date"), field="split execution_date"
            )
            if event_date < start or event_date > end:
                raise CollectionRefused(
                    f"split execution date outside requested bound: {event_date}"
                )
            try:
                split_from = float(row.get("split_from"))
                split_to = float(row.get("split_to"))
            except (TypeError, ValueError) as exc:
                raise CollectionRefused("split ratio is not numeric") from exc
            if (
                not math.isfinite(split_from)
                or not math.isfinite(split_to)
                or split_from <= 0
                or split_to <= 0
            ):
                raise CollectionRefused("split ratio must be finite and positive")
            source_id = _normal_text(row.get("id")) or (
                f"{ticker}|{event_date.isoformat()}|{split_from:.12g}|{split_to:.12g}"
            )
            if source_id in seen:
                raise CollectionRefused(f"split duplicate row: {source_id}")
            seen.add(source_id)
            validated.append(
                {
                    **dict(row),
                    "id": source_id,
                    "ticker": ticker,
                    "execution_date": event_date.isoformat(),
                    "split_from": split_from,
                    "split_to": split_to,
                    "adjustment_type": _normal_text(row.get("adjustment_type"))
                    or "unspecified",
                }
            )
        receipt = dict(bundle.receipt)
        receipt["execution_date_gte"] = start.isoformat()
        receipt["execution_date_lte"] = end.isoformat()
        receipt["adjustment_types"] = sorted(
            {str(row["adjustment_type"]) for row in validated}
        )
        return PageBundle(tuple(validated), receipt)


def _read_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        raise CollectionRefused(
            f"cannot read accepted JSON artifact {path.name}"
        ) from exc
    if not isinstance(payload, dict):
        raise CollectionRefused(f"accepted JSON artifact {path.name} is not an object")
    return payload


def _read_parquet(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        raise CollectionRefused(
            f"cannot read accepted parquet artifact {path.name}"
        ) from exc
    if columns is not None:
        for column in columns:
            if column not in frame.columns:
                frame[column] = pd.NA
        frame = frame.reindex(columns=columns)
    return frame


def _completed_session_from_store(
    data_root: Path,
    *,
    now: datetime | None = None,
    min_store_files: int = 100,
) -> date:
    store_dir = Path(data_root) / "massive_stock_day"
    manifest_path = store_dir / "_manifest.json"
    if not store_dir.is_dir() or not manifest_path.exists():
        raise CollectionRefused("massive_stock_day store absent")
    parquet_files = [
        p for p in store_dir.glob("*.parquet") if not p.name.startswith("_")
    ]
    if len(parquet_files) < int(min_store_files):
        raise CollectionRefused(
            f"massive_stock_day store partial: {len(parquet_files)} files < "
            f"{int(min_store_files)}"
        )
    manifest = _read_json(manifest_path, default={})
    latest_raw = manifest.get("latest_date")
    if not latest_raw:
        raise CollectionRefused("massive_stock_day manifest missing latest_date")
    latest = _coerce_date(latest_raw, field="massive manifest latest_date")
    if not is_session(latest):
        raise CollectionRefused(
            f"massive manifest latest_date is not an XNYS session: {latest}"
        )
    expected = expected_last_session(now)
    if latest < expected:
        raise CollectionRefused(
            f"massive_stock_day store stale: latest={latest}, expected={expected}"
        )
    if latest > expected:
        raise CollectionRefused(
            f"massive_stock_day store is ahead of canonical calendar: "
            f"latest={latest}, expected={expected}"
        )
    try:
        manifest_count = int(manifest.get("n_tickers", len(parquet_files)))
    except (TypeError, ValueError) as exc:
        raise CollectionRefused("massive manifest n_tickers is invalid") from exc
    if manifest_count < int(min_store_files):
        raise CollectionRefused(
            f"massive_stock_day manifest indicates partial store: {manifest_count} tickers"
        )
    anchor = manifest.get("anchor")
    if not isinstance(anchor, Mapping) or not anchor.get("last"):
        raise CollectionRefused("massive_stock_day manifest missing anchor last date")
    anchor_last = _coerce_date(anchor.get("last"), field="massive anchor last")
    if anchor_last != latest:
        raise CollectionRefused(
            f"massive_stock_day partial tip: manifest={latest}, anchor={anchor_last}"
        )
    return latest


def _load_alias_table(data_root: Path) -> VendorAliasTable:
    path = Path(data_root) / "reference" / "vendor_aliases.parquet"
    if not path.exists():
        raise CollectionRefused("canonical vendor_aliases.parquet is absent")
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        raise CollectionRefused(
            "canonical vendor_aliases.parquet is unreadable"
        ) from exc
    required = {"vendor", "vendor_symbol", "security_id", "valid_from", "valid_to"}
    missing = required - set(frame.columns)
    if missing:
        raise CollectionRefused(
            f"canonical vendor alias table missing columns: {sorted(missing)}"
        )
    records: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        record = dict(row)
        for key in ("valid_from", "valid_to"):
            value = record.get(key)
            record[key] = (
                None if value is None or pd.isna(value) else pd.Timestamp(value).date()
            )
        records.append(record)
    try:
        return VendorAliasTable.from_records(records)
    except Exception as exc:  # noqa: BLE001
        raise CollectionRefused(
            f"canonical vendor alias table is invalid: {exc}"
        ) from exc


def _source_split_frame(rows: tuple[dict[str, Any], ...]) -> pd.DataFrame:
    columns = [
        "source_split_id",
        "ticker",
        "execution_date",
        "split_from",
        "split_to",
        "adjustment_type",
        "entity_key",
        "resolution_status",
        "source",
    ]
    records = [
        {
            "source_split_id": row["id"],
            "ticker": row["ticker"],
            "execution_date": pd.Timestamp(row["execution_date"]).normalize(),
            "split_from": float(row["split_from"]),
            "split_to": float(row["split_to"]),
            "adjustment_type": row.get("adjustment_type") or "unspecified",
            "entity_key": None,
            "resolution_status": "unresolved",
            "source": "massive_splits",
        }
        for row in rows
    ]
    return pd.DataFrame(records, columns=columns)


def _merge_source_splits(existing: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    columns = (
        list(fresh.columns)
        if not fresh.empty
        else [
            "source_split_id",
            "ticker",
            "execution_date",
            "split_from",
            "split_to",
            "adjustment_type",
            "entity_key",
            "resolution_status",
            "source",
        ]
    )
    if existing.empty:
        merged = fresh.copy().reindex(columns=columns)
    else:
        work = existing.copy()
        for column in columns:
            if column not in work.columns:
                work[column] = pd.NA
        work = work.reindex(columns=columns)
        combined = pd.concat([work, fresh.reindex(columns=columns)], ignore_index=True)
        conflicts = []
        for source_id, group in combined.groupby("source_split_id", dropna=False):
            signature = (
                group[
                    [
                        "ticker",
                        "execution_date",
                        "split_from",
                        "split_to",
                        "adjustment_type",
                    ]
                ]
                .astype(str)
                .drop_duplicates()
            )
            if len(signature) > 1:
                conflicts.append(str(source_id))
        if conflicts:
            raise CollectionRefused(
                f"split source id changed meaning: {sorted(conflicts)[:5]}"
            )
        merged = combined.drop_duplicates("source_split_id", keep="last")
    if merged.empty:
        return pd.DataFrame(columns=columns)
    merged["execution_date"] = (
        pd.to_datetime(merged["execution_date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    merged["split_from"] = pd.to_numeric(merged["split_from"], errors="raise")
    merged["split_to"] = pd.to_numeric(merged["split_to"], errors="raise")
    return merged.sort_values(
        ["execution_date", "ticker", "source_split_id"], kind="stable"
    ).reset_index(drop=True)


def _resolve_split_entities(
    splits: pd.DataFrame,
    intervals: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    if splits.empty:
        return splits.copy(), pd.DataFrame(), []
    work = splits.copy()
    interval_view = intervals[
        ["entity_key", "ticker", "valid_from_session", "valid_to_session"]
    ].drop_duplicates()
    if not interval_view.empty:
        for column in ("valid_from_session", "valid_to_session"):
            interval_view[column] = (
                pd.to_datetime(interval_view[column], errors="raise")
                .dt.tz_localize(None)
                .dt.normalize()
            )
    unresolved: list[dict[str, Any]] = []
    for idx, event in work.iterrows():
        event_date = pd.Timestamp(event["execution_date"]).normalize()
        matches = interval_view[
            (interval_view["ticker"].astype(str) == str(event["ticker"]))
            & (interval_view["valid_from_session"] <= event_date)
            & (interval_view["valid_to_session"] >= event_date)
        ]
        entities = sorted(set(matches["entity_key"].dropna().astype(str)))
        if len(entities) > 1:
            raise CollectionRefused(
                f"split {event['source_split_id']} maps to multiple entities"
            )
        if len(entities) == 1:
            work.at[idx, "entity_key"] = entities[0]
            work.at[idx, "resolution_status"] = "resolved"
        elif str(event["ticker"]) in set(interval_view["ticker"].astype(str)):
            unresolved.append(
                {
                    "ticker": str(event["ticker"]),
                    "execution_date": event_date.date().isoformat(),
                    "source_split_id": str(event["source_split_id"]),
                }
            )
    resolved = work[work["entity_key"].notna()][
        ["entity_key", "execution_date", "split_from", "split_to", "adjustment_type"]
    ].copy()
    return work, resolved, unresolved


def _default_price_loader(ticker: str) -> pd.DataFrame:
    from collectors.massive_stock_day import load_ticker

    return load_ticker(ticker)


def _load_prices(
    tickers: list[str],
    *,
    loader: PriceLoader,
    start: date,
    end: date,
) -> dict[str, pd.Series]:
    prices: dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            frame = loader(ticker)
        except Exception as exc:  # noqa: BLE001
            raise CollectionRefused(
                f"massive price read failed for {ticker}: {safe_exc_text(exc)}"
            ) from exc
        if frame is None or frame.empty or "close" not in frame.columns:
            continue
        series = pd.to_numeric(frame["close"], errors="coerce")
        index = pd.to_datetime(series.index, errors="coerce")
        if index.tz is not None:
            index = index.tz_convert("UTC").tz_localize(None)
        series.index = index.normalize()
        series = series[
            (series.index >= pd.Timestamp(start)) & (series.index <= pd.Timestamp(end))
        ].dropna()
        if not series.empty:
            prices[ticker] = series[~series.index.duplicated(keep="last")].sort_index()
    return prices


def _entity_membership(
    index: pd.DatetimeIndex,
    entities: list[str],
    intervals: pd.DataFrame,
    universe_key: str,
) -> pd.DataFrame:
    out = pd.DataFrame(False, index=index, columns=entities, dtype=bool)
    rows = intervals[
        (intervals["universe_key"] == universe_key) & intervals["entity_key"].notna()
    ]
    for row in rows.itertuples(index=False):
        entity = str(row.entity_key)
        if entity not in out.columns:
            continue
        start = pd.Timestamp(row.valid_from_session).normalize()
        end = pd.Timestamp(row.valid_to_session).normalize()
        out.loc[(out.index >= start) & (out.index <= end), entity] = True
    return out


def _listed_series(
    index: pd.DatetimeIndex,
    state: dict[str, Any],
    current_session: date,
    current_counts: dict[str, dict[str, int]],
    universe_key: str,
) -> pd.Series:
    values = pd.Series(float("nan"), index=index, dtype=float)
    history = state.get("session_counts")
    if isinstance(history, Mapping):
        for raw_session, counts in history.items():
            if not isinstance(counts, Mapping):
                continue
            universe = counts.get(universe_key)
            if not isinstance(universe, Mapping):
                continue
            try:
                ts = pd.Timestamp(raw_session).normalize()
                listed = float(universe["listed_n"])
            except Exception:  # noqa: BLE001
                continue
            if ts in values.index:
                values.loc[ts] = listed
    current_ts = pd.Timestamp(current_session)
    if current_ts in values.index:
        values.loc[current_ts] = float(current_counts[universe_key]["listed_n"])
    return values


def _build_frames(
    *,
    intervals: pd.DataFrame,
    splits: pd.DataFrame,
    prices: dict[str, pd.Series],
    observation_session: date,
    state: dict[str, Any],
    counts: dict[str, dict[str, int]],
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    if prices:
        all_index = pd.DatetimeIndex([])
        for series in prices.values():
            all_index = all_index.union(pd.DatetimeIndex(series.index))
    else:
        all_index = pd.DatetimeIndex([])
    all_index = all_index.union(
        pd.DatetimeIndex([pd.Timestamp(observation_session)])
    ).sort_values()
    frames: dict[str, pd.DataFrame] = {}
    diagnostics: dict[str, dict[str, Any]] = {}
    for universe_key in (UNIVERSE_OPERATING, UNIVERSE_ALL_ISSUES):
        entity_rows = intervals[
            (intervals["universe_key"] == universe_key)
            & intervals["entity_key"].notna()
        ]
        entities = sorted(set(entity_rows["entity_key"].astype(str)))
        panel = assemble_entity_close_panel(
            prices,
            intervals,
            split_events=splits,
            observation_session=observation_session,
            universe_key=universe_key,
        )
        closes = panel.closes.reindex(index=all_index, columns=entities)
        membership = _entity_membership(all_index, entities, intervals, universe_key)
        listed = _listed_series(
            all_index, state, observation_session, counts, universe_key
        )
        frame = compute_breadth_history(
            closes,
            membership=membership,
            listed_counts=listed,
        )
        frame.index.name = "session"
        frames[universe_key] = frame
        diagnostics[universe_key] = {
            "excluded_entity_count": len(panel.excluded_entities),
            "excluded_entity_examples": dict(
                list(panel.excluded_entities.items())[:10]
            ),
        }
    return frames, diagnostics


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def _promote_generation(
    output_dir: Path,
    *,
    intervals: pd.DataFrame,
    splits: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    state: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=".exchange-breadth-stage-", dir=output_dir.parent)
    )
    try:
        intervals.to_parquet(stage / _INTERVALS_FILE, index=False)
        splits.to_parquet(stage / _SPLITS_FILE, index=False)
        for key, filename in _FRAME_FILES.items():
            frames[key].to_parquet(stage / filename)
        _write_json(stage / _RECEIPT_FILE, receipt)
        _write_json(stage / _STATE_FILE, state)
        # The checkpoint moves last.  A process that dies earlier cannot claim a
        # session complete; the next run recomputes the whole candidate.
        order = [
            _FRAME_FILES[UNIVERSE_OPERATING],
            _FRAME_FILES[UNIVERSE_ALL_ISSUES],
            _INTERVALS_FILE,
            _SPLITS_FILE,
            _RECEIPT_FILE,
            _STATE_FILE,
        ]
        for filename in order:
            os.replace(stage / filename, output_dir / filename)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def collect_exchange_breadth(
    *,
    client: MassiveReferenceClient,
    data_root: Path | None = None,
    now: datetime | None = None,
    min_store_files: int = 100,
    min_roster_rows: int = 1_000,
    min_operating_rows: int = 500,
    min_identity_coverage: float = 0.90,
    min_price_coverage: float = 0.85,
    split_lookback_days: int = 550,
    history_lookback_days: int = 800,
    price_loader: PriceLoader | None = None,
) -> CollectionResult:
    """Build and publish one accepted XNYS breadth generation."""
    root = Path(data_root or config.data_dir())
    observed_at = now or datetime.now(timezone.utc)
    session = _completed_session_from_store(
        root, now=observed_at, min_store_files=min_store_files
    )
    split_start = session - timedelta(days=int(split_lookback_days))

    # All network and source-shape validation completes before any accepted file
    # is opened for replacement.
    roster_bundle = client.fetch_roster(session, min_rows=min_roster_rows)
    split_bundle = client.fetch_splits(split_start, session)
    alias_table = _load_alias_table(root)
    observed = normalize_roster(
        list(roster_bundle.rows), session, alias_table=alias_table
    )
    if observed.empty:
        raise CollectionRefused("normalized XNYS roster is empty")

    counts: dict[str, dict[str, int]] = {}
    for universe_key in (UNIVERSE_OPERATING, UNIVERSE_ALL_ISSUES):
        rows = observed[observed["universe_key"] == universe_key]
        listed_n = int(len(rows))
        resolved_n = int(rows["identity_resolved"].fillna(False).sum())
        counts[universe_key] = {
            "listed_n": listed_n,
            "resolved_identity_n": resolved_n,
        }
    if counts[UNIVERSE_OPERATING]["listed_n"] < int(min_operating_rows):
        raise CollectionRefused(
            "operating-company row floor not met: "
            f"{counts[UNIVERSE_OPERATING]['listed_n']} < {int(min_operating_rows)}"
        )
    for universe_key, values in counts.items():
        listed_n = values["listed_n"]
        coverage = values["resolved_identity_n"] / listed_n if listed_n else 0.0
        if coverage < float(min_identity_coverage):
            raise CollectionRefused(
                f"{universe_key} identity coverage {coverage:.3f} below "
                f"{float(min_identity_coverage):.3f}"
            )

    output = root / OUTPUT_DIR
    existing_state = _read_json(
        output / _STATE_FILE,
        default={
            "schema_version": SCHEMA_VERSION,
            "source_rules_version": SOURCE_RULES_VERSION,
            "accepted_sessions": [],
            "session_counts": {},
        },
    )
    existing_intervals = _read_parquet(output / _INTERVALS_FILE)
    last_seen = existing_state.get("last_observed_session")
    previous = last_session_on_or_before(session - timedelta(days=1))
    intervals = update_membership_intervals(
        existing_intervals,
        observed,
        session,
        previous_session=previous,
        last_observed_session=last_seen,
    )

    fresh_splits = _source_split_frame(split_bundle.rows)
    existing_splits = _read_parquet(output / _SPLITS_FILE)
    source_splits = _merge_source_splits(existing_splits, fresh_splits)
    source_splits, resolved_splits, unresolved_splits = _resolve_split_entities(
        source_splits, intervals
    )

    history_start = session - timedelta(days=int(history_lookback_days))
    relevant = intervals[
        (pd.to_datetime(intervals["valid_to_session"]) >= pd.Timestamp(history_start))
        & (pd.to_datetime(intervals["valid_from_session"]) <= pd.Timestamp(session))
    ]
    tickers = sorted(set(relevant["ticker"].dropna().astype(str)))
    prices = _load_prices(
        tickers,
        loader=price_loader or _default_price_loader,
        start=history_start,
        end=session,
    )
    frames, diagnostics = _build_frames(
        intervals=intervals,
        splits=resolved_splits,
        prices=prices,
        observation_session=session,
        state=existing_state,
        counts=counts,
    )

    latest_ts = pd.Timestamp(session)
    for universe_key, frame in frames.items():
        if latest_ts not in frame.index:
            raise CollectionRefused(f"{universe_key} aggregate lacks accepted session")
        latest = frame.loc[latest_ts]
        listed_n = counts[universe_key]["listed_n"]
        priced_n = int(latest.get("priced_n", 0) or 0)
        price_coverage = priced_n / listed_n if listed_n else 0.0
        counts[universe_key]["priced_n"] = priced_n
        counts[universe_key]["price_coverage_pct"] = round(price_coverage * 100.0, 4)
        if price_coverage < float(min_price_coverage):
            raise CollectionRefused(
                f"{universe_key} price coverage {price_coverage:.3f} below "
                f"{float(min_price_coverage):.3f}"
            )
        counts[universe_key]["seasoned_n"] = int(latest.get("seasoned_n", 0) or 0)

    unresolved_rows = observed[~observed["identity_resolved"].fillna(False)]
    unresolved_examples = sorted(set(unresolved_rows["ticker"].astype(str)))[:10]
    accepted_sessions = sorted(
        set(str(value) for value in existing_state.get("accepted_sessions", []))
        | {session.isoformat()}
    )
    session_counts = dict(existing_state.get("session_counts") or {})
    session_counts[session.isoformat()] = counts
    state = {
        "schema_version": SCHEMA_VERSION,
        "source_rules_version": SOURCE_RULES_VERSION,
        "last_observed_session": session.isoformat(),
        "accepted_sessions": accepted_sessions,
        "session_counts": session_counts,
        "last_source_clock": observed_at.astimezone(timezone.utc).isoformat(),
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "accepted": True,
        "accepted_session": session.isoformat(),
        "source_clock": observed_at.astimezone(timezone.utc).isoformat(),
        "source_rules_version": SOURCE_RULES_VERSION,
        "authority": AUTHORITY,
        "price_basis": PRICE_BASIS,
        "universe_scope": {
            UNIVERSE_OPERATING: "XNYS active stocks; types CS and ADRC",
            UNIVERSE_ALL_ISSUES: "all active XNYS stock-market issues",
        },
        "universes": counts,
        "unresolved_identity_count": int(len(unresolved_rows)),
        "unresolved_identity_examples": unresolved_examples,
        "roster": roster_bundle.receipt,
        "splits": {
            **split_bundle.receipt,
            "cache_rows": int(len(source_splits)),
            "resolved_rows": (
                int(source_splits["entity_key"].notna().sum())
                if not source_splits.empty
                else 0
            ),
            "unresolved_relevant_count": len(unresolved_splits),
            "unresolved_relevant_examples": unresolved_splits[:10],
        },
        "diagnostics": diagnostics,
        "massive_store": {
            "latest_date": session.isoformat(),
            "history_start": history_start.isoformat(),
            "tickers_requested": len(tickers),
            "tickers_loaded": len(prices),
        },
    }
    _promote_generation(
        output,
        intervals=intervals,
        splits=source_splits,
        frames=frames,
        state=state,
        receipt=receipt,
    )
    return CollectionResult(frames=frames, receipt=receipt, state=state)


class ExchangeBreadthAdapter(Adapter):
    """Nightly owner for point-in-time XNYS participation artifacts."""

    name = "exchange_breadth"
    group = "exchange_breadth"
    stale_after_days = 2
    manages_persistence = True

    def __init__(self, client: MassiveReferenceClient | None = None) -> None:
        cfg = config.load().get("exchange_breadth", {})
        key = config.secret(
            str(cfg.get("api_key_env", "POLYGON_API_KEY"))
        ) or config.secret("MASSIVE_API_KEY")
        self.cfg = cfg
        self.client = client
        if self.client is None and key:
            self.client = MassiveReferenceClient(
                key,
                base_url=str(
                    cfg.get("base_url")
                    or config.load().get("polygon", {}).get("base_url")
                    or "https://api.polygon.io"
                ),
                max_pages=int(cfg.get("max_pages", 50)),
                timeout_s=float(cfg.get("timeout_s", 60)),
            )
        if self.client is None:
            self.expected_failure = "POLYGON_API_KEY/MASSIVE_API_KEY not set"

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        if self.client is None:
            raise RuntimeError("exchange_breadth vendor key is not configured")
        result = collect_exchange_breadth(
            client=self.client,
            min_store_files=int(self.cfg.get("min_store_files", 100)),
            min_roster_rows=int(self.cfg.get("roster_min_rows", 1_000)),
            min_operating_rows=int(self.cfg.get("operating_min_rows", 500)),
            min_identity_coverage=float(self.cfg.get("min_identity_coverage", 0.90)),
            min_price_coverage=float(self.cfg.get("min_price_coverage", 0.85)),
            split_lookback_days=int(self.cfg.get("split_lookback_days", 550)),
            history_lookback_days=int(self.cfg.get("history_lookback_days", 800)),
        )
        return result.frames
