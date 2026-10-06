"""Build the exact current S&P ticker-news universe from incumbent owner artifacts.

Default mode is CHECK ONLY: owner artifacts are read and cross-checked but no output
is created. Passing --write atomically publishes one derived JSON snapshot. The
source parquets are never rewritten, renamed, or repaired here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable, Mapping, Sequence

import pandas as pd

from engine.qbus_news_universe import qualify_universe
from engine.qbus_news_universe_snapshot import (
    NewsUniverseSnapshotError,
    build_news_universe_snapshot,
)
from lib import config


class NewsUniverseBuildError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"qbus_news_universe_build:{code}")


def _observed_at(raw: str | None) -> datetime:
    if raw is None:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise NewsUniverseBuildError("observed_at_invalid") from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise NewsUniverseBuildError("observed_at_invalid")
    return dt.astimezone(timezone.utc)


def _python_value(value: object) -> object:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    item = getattr(value, "item", None)
    if callable(item):
        try:
            value = item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _records(frame: pd.DataFrame, *, include_index: bool = False) -> list[dict]:
    source = frame.reset_index() if include_index else frame
    out: list[dict] = []
    for raw in source.to_dict(orient="records"):
        out.append({str(key): _python_value(value) for key, value in raw.items()})
    return out


def _read_parquet(path: Path, *, include_index: bool = False) -> list[dict]:
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        raise NewsUniverseBuildError("owner_artifact_unreadable") from exc
    try:
        return _records(frame, include_index=include_index)
    except Exception as exc:
        raise NewsUniverseBuildError("owner_artifact_invalid") from exc


def _atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            temp_name = fh.name
            json.dump(
                payload,
                fh,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def build_from_files(
    *,
    current: Path | str,
    pit: Path | str,
    aliases: Path | str,
    security: Path | str,
    output: Path | str,
    observed_at: datetime,
    fresh_for: timedelta = timedelta(hours=36),
    min_count: int = 400,
    write: bool = False,
) -> dict[str, object]:
    current_path = Path(current)
    pit_path = Path(pit)
    aliases_path = Path(aliases)
    security_path = Path(security)
    output_path = Path(output)

    current_rows = _read_parquet(current_path, include_index=True)
    pit_rows = _read_parquet(pit_path)
    alias_rows = _read_parquet(aliases_path)
    security_rows = _read_parquet(security_path)

    try:
        snapshot = build_news_universe_snapshot(
            current_rows=current_rows,
            pit_rows=pit_rows,
            alias_rows=alias_rows,
            security_rows=security_rows,
            observed_at=observed_at,
            fresh_for=fresh_for,
            min_count=min_count,
        )
    except NewsUniverseSnapshotError as exc:
        raise NewsUniverseBuildError(exc.code) from exc

    qualified = qualify_universe(snapshot, asof=observed_at)
    if qualified.status != "qualified":
        raise NewsUniverseBuildError("qualification_failed")

    if write:
        _atomic_json(output_path, snapshot)

    return {
        "schema": "qbus.news_universe_build.v1",
        "mode": "write" if write else "check_only",
        "qualified": True,
        "count": qualified.count,
        "revision": qualified.revision,
        "owner": qualified.owner,
        "known_at": snapshot["known_at"],
        "fresh_until": snapshot["fresh_until"],
        "output": str(output_path),
    }


def build_parser() -> argparse.ArgumentParser:
    data = config.data_dir()
    parser = argparse.ArgumentParser(
        description="Cross-check and optionally publish the qbus S&P news universe."
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=data / "breadth" / "constituents.parquet",
    )
    parser.add_argument(
        "--pit",
        type=Path,
        default=data / "breadth" / "sp1500_pit_membership.parquet",
    )
    parser.add_argument(
        "--aliases",
        type=Path,
        default=data / "reference" / "vendor_aliases.parquet",
    )
    parser.add_argument(
        "--security-master",
        dest="security",
        type=Path,
        default=data / "reference" / "security_master.parquet",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=data / "qbus" / "news_universe.json",
    )
    parser.add_argument("--fresh-hours", type=float, default=36.0)
    parser.add_argument("--min-count", type=int, default=400)
    parser.add_argument(
        "--observed-at",
        type=str,
        default=None,
        help="aware ISO timestamp override for tests/replay; default is current UTC",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="atomically publish output; omitted means check-only",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fresh_hours <= 0:
        print(
            json.dumps(
                {
                    "schema": "qbus.news_universe_build.v1",
                    "ok": False,
                    "error": "fresh_hours_invalid",
                },
                sort_keys=True,
            )
        )
        return 2
    try:
        report = build_from_files(
            current=args.current,
            pit=args.pit,
            aliases=args.aliases,
            security=args.security,
            output=args.output,
            observed_at=_observed_at(args.observed_at),
            fresh_for=timedelta(hours=float(args.fresh_hours)),
            min_count=int(args.min_count),
            write=bool(args.write),
        )
    except (NewsUniverseBuildError, ValueError, TypeError) as exc:
        code = getattr(exc, "code", "build_failed")
        print(
            json.dumps(
                {
                    "schema": "qbus.news_universe_build.v1",
                    "ok": False,
                    "error": str(code),
                },
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps({**report, "ok": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
