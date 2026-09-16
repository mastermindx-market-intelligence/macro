"""Fail-closed freshness contract for the published China A-share heatmap.

The heatmap has two independent freshness boundaries:

1. ``data/china_search/closes.parquet`` must have reached the latest completed
   mainland session; otherwise a stale source and stale JSON can agree with each
   other and still look healthy.
2. ``site/marketdata/china_heatmap.json`` must describe that exact source
   session and contain a coherent, non-empty China tile set.

This checker is intentionally binding.  It is used both by the China heatmap
builder (before any stale payload can overwrite the published artifact) and by
``asia-close.yml`` immediately before broad staging/push.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import cn_calendar, config  # noqa: E402


MIN_LATEST_SESSION_COVERAGE = 0.95
MAX_GENERATED_FUTURE = timedelta(hours=1)


class ChinaHeatmapFreshnessError(RuntimeError):
    """A binding China heatmap freshness invariant was not satisfied."""

    def __init__(self, title: str, detail: str) -> None:
        super().__init__(detail)
        self.title = title
        self.detail = detail


@dataclass(frozen=True)
class ChinaHeatmapFreshnessState:
    expected_session: str
    source_session: str
    payload_session: str
    tile_count: int
    latest_session_observations: int
    latest_session_coverage: float
    latest_session_source_count: int
    latest_session_source_representation: float
    generated_utc: str


def _normalise_now(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def latest_nonempty_session(closes: pd.DataFrame) -> str:
    """Return the newest close-panel row carrying at least one real observation."""
    if not isinstance(closes, pd.DataFrame) or closes.empty:
        raise ChinaHeatmapFreshnessError(
            "China heatmap source unreadable",
            "china_search/closes.parquet is empty or is not a DataFrame",
        )
    usable = closes.dropna(axis=0, how="all")
    if usable.empty:
        raise ChinaHeatmapFreshnessError(
            "China heatmap source unreadable",
            "china_search/closes.parquet has no non-empty session rows",
        )
    index = pd.to_datetime(usable.index, errors="coerce")
    index = index[~pd.isna(index)]
    if len(index) == 0:
        raise ChinaHeatmapFreshnessError(
            "China heatmap source unreadable",
            "china_search/closes.parquet has no parseable session index",
        )
    return pd.Timestamp(index.max()).date().isoformat()


def latest_session_observed_tickers(closes: pd.DataFrame, session: str) -> set[str]:
    """Tickers carrying a real close on ``session`` (duplicate rows are unioned)."""
    parsed = pd.to_datetime(closes.index, errors="coerce")
    target = date.fromisoformat(session)
    mask = [not pd.isna(stamp) and pd.Timestamp(stamp).date() == target for stamp in parsed]
    rows = closes.loc[mask]
    if rows.empty:
        return set()
    numeric = rows.apply(pd.to_numeric, errors="coerce")
    observed = numeric.notna().any(axis=0)
    return {str(column) for column in observed.index[observed]}


def _generated_utc(value: Any, *, payload_session: str, now: datetime) -> str:
    text = str(value or "").strip()
    if not text:
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            "generated_utc is absent",
        )
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"generated_utc is not an ISO-8601 timestamp: {text!r}",
        ) from exc
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    stamp = stamp.astimezone(timezone.utc)
    if stamp.date() < date.fromisoformat(payload_session):
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"generated_utc={text!r} predates payload session {payload_session}",
        )
    if stamp > now + MAX_GENERATED_FUTURE:
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"generated_utc={text!r} is implausibly ahead of now={now.isoformat()}",
        )
    return text


def _iso_date(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text).isoformat()
    except (TypeError, ValueError) as exc:
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"{label} is not an ISO session date: {text!r}",
        ) from exc


def validate_china_heatmap(
    payload: Any,
    closes: pd.DataFrame,
    *,
    now: datetime | None = None,
) -> ChinaHeatmapFreshnessState:
    """Validate source clock, payload/source parity, and the payload contract.

    Raises :class:`ChinaHeatmapFreshnessError` before a caller can publish a
    stale or malformed JSON.  A source ahead of the exchange clock is accepted:
    the completed-session calculation is deliberately a lower bound, matching
    the existing China core-price gate.
    """
    current = _normalise_now(now)
    expected = cn_calendar.expected_last_session(current).isoformat()
    source = latest_nonempty_session(closes)
    if source < expected:
        raise ChinaHeatmapFreshnessError(
            "China heatmap source stale",
            f"source={source} expected={expected}; refusing to publish a self-consistent old day",
        )

    if not isinstance(payload, dict):
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            "payload root is not a JSON object",
        )
    if payload.get("market") != "china":
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"market={payload.get('market')!r}; expected 'china'",
        )
    if payload.get("source") != "daily-close":
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"source label={payload.get('source')!r}; expected 'daily-close'",
        )

    payload_session = _iso_date(payload.get("asof"), label="payload.asof")
    tiles = payload.get("tiles")
    n_tiles = payload.get("n_tiles")
    if not isinstance(tiles, list) or not tiles:
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            "tiles must be a non-empty list",
        )
    if isinstance(n_tiles, bool) or not isinstance(n_tiles, int) or n_tiles != len(tiles):
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            f"n_tiles={n_tiles!r} but len(tiles)={len(tiles)}",
        )

    tile_tickers: list[str] = []
    for position, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise ChinaHeatmapFreshnessError(
                "China heatmap malformed",
                f"tiles[{position}] is not an object",
            )
        ticker = str(tile.get("t") or "").strip()
        if not ticker:
            raise ChinaHeatmapFreshnessError(
                "China heatmap malformed",
                f"tiles[{position}].t is absent",
            )
        tile_tickers.append(ticker)
    if len(set(tile_tickers)) != len(tile_tickers):
        raise ChinaHeatmapFreshnessError(
            "China heatmap malformed",
            "tile tickers are not unique",
        )

    if payload_session != source:
        raise ChinaHeatmapFreshnessError(
            "China heatmap stale",
            f"payload={payload_session} source={source} expected={expected}",
        )

    observed = latest_session_observed_tickers(closes, source)
    observed_count = len(set(tile_tickers) & observed)
    coverage = observed_count / n_tiles
    source_count = len(observed)
    if source_count == 0:
        raise ChinaHeatmapFreshnessError(
            "China heatmap source unreadable",
            f"source session {source} has no numeric close observations",
        )
    source_representation = observed_count / source_count
    if (
        coverage < MIN_LATEST_SESSION_COVERAGE
        or source_representation < MIN_LATEST_SESSION_COVERAGE
    ):
        raise ChinaHeatmapFreshnessError(
            "China heatmap source incomplete",
            "latest_session_coverage="
            f"{observed_count}/{n_tiles} ({coverage:.1%}); "
            "source_representation="
            f"{observed_count}/{source_count} ({source_representation:.1%}); "
            f"source={source}; minimum={MIN_LATEST_SESSION_COVERAGE:.0%}",
        )

    generated_utc = _generated_utc(
        payload.get("generated_utc"),
        payload_session=payload_session,
        now=current,
    )
    return ChinaHeatmapFreshnessState(
        expected_session=expected,
        source_session=source,
        payload_session=payload_session,
        tile_count=n_tiles,
        latest_session_observations=observed_count,
        latest_session_coverage=coverage,
        latest_session_source_count=source_count,
        latest_session_source_representation=source_representation,
        generated_utc=generated_utc,
    )


def _default_payload_path() -> Path:
    site = config.ROOT / config.load()["storage"]["site_dir"]
    return site / "marketdata" / "china_heatmap.json"


def _default_closes_path() -> Path:
    return config.data_dir() / "china_search" / "closes.parquet"


def _emit_error(title: str, detail: str) -> None:
    clean = " ".join(str(detail).splitlines())
    print(f"::error title={title}::{clean}", flush=True)


def check_china_heatmap_freshness(
    *,
    payload_path: str | Path | None = None,
    closes_path: str | Path | None = None,
    now: datetime | None = None,
) -> int:
    payload_file = Path(payload_path) if payload_path is not None else _default_payload_path()
    closes_file = Path(closes_path) if closes_path is not None else _default_closes_path()

    try:
        closes = pd.read_parquet(closes_file)
    except Exception as exc:  # noqa: BLE001 — all read failures are binding
        _emit_error(
            "China heatmap source unreadable",
            f"{closes_file}: {type(exc).__name__}: {exc}",
        )
        return 3
    try:
        payload = json.loads(payload_file.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — missing/corrupt output must fail closed
        _emit_error(
            "China heatmap unreadable",
            f"{payload_file}: {type(exc).__name__}: {exc}",
        )
        return 3

    try:
        state = validate_china_heatmap(payload, closes, now=now)
    except ChinaHeatmapFreshnessError as exc:
        _emit_error(exc.title, exc.detail)
        return 3

    if state.source_session == state.expected_session:
        sessions = f"payload=source=expected={state.source_session}"
    else:
        sessions = (
            f"payload=source={state.source_session}; "
            f"expected_completed={state.expected_session}"
        )
    print(
        "China heatmap freshness OK: "
        f"{sessions}; tiles={state.tile_count}; "
        "latest_session_coverage="
        f"{state.latest_session_observations}/{state.tile_count} "
        f"({state.latest_session_coverage:.1%}); "
        "source_representation="
        f"{state.latest_session_observations}/{state.latest_session_source_count} "
        f"({state.latest_session_source_representation:.1%}); "
        f"generated_utc={state.generated_utc}",
        flush=True,
    )
    return 0


def _parse_now(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    value = raw.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless the China heatmap matches the current close session"
    )
    parser.add_argument("--payload", type=Path, help="override china_heatmap.json path")
    parser.add_argument("--closes", type=Path, help="override china_search closes parquet path")
    parser.add_argument("--now", help="override current time (ISO-8601; tests/replay only)")
    args = parser.parse_args(argv)
    try:
        now = _parse_now(args.now)
    except ValueError as exc:
        parser.error(f"invalid --now: {exc}")
    return check_china_heatmap_freshness(
        payload_path=args.payload,
        closes_path=args.closes,
        now=now,
    )


if __name__ == "__main__":
    sys.exit(main())
