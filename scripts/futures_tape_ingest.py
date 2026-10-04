#!/usr/bin/env python3
"""Acquire, normalize, derive and audit the Mastermind futures tape plane.

This is a bounded Data OS producer, not a scheduler and not a signal engine.

Examples:
  python -m scripts.futures_tape_ingest storage
  python -m scripts.futures_tape_ingest probe-lse --symbol ES.F
  python -m scripts.futures_tape_ingest backfill-lse --symbol ES.F --start 2020-03-01 --end 2020-04-01
  python -m scripts.futures_tape_ingest normalize-lse
  python -m scripts.futures_tape_ingest derive-bars --instrument LSE_ES.F --freq 1min
  python -m scripts.futures_tape_ingest audit

Production hosts should set MMX_FUTURES_TAPE_ROOT to the external SSD. Bulk work
is capacity-gated and defaults to preserving 100 GiB free space.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.dataos.futures_tape import (  # noqa: E402
    PartitionManifest,
    PartitionState,
    SourceRole,
    audit_manifests,
    capacity,
    derived_bar_path,
    manifest_path,
    normalized_day_path,
    raw_export_path,
    require_capacity,
    sha256_file,
    storage_root,
    utc_now,
    write_manifest_atomic,
)

DEFAULT_RESERVE_GIB = 100.0
LSE_KEY_ENV = "LSE_API_KEY"


def _pandas():
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - host dependency
        raise SystemExit(f"pandas is required for this command: {exc}") from exc
    return pd


def _lse_client():
    try:
        from lse import LSE
    except Exception as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "lse-data is not installed. Install the official SDK in the ops environment "
            "(pip install 'lse-data[frames]') before an LSE source probe/backfill."
        ) from exc
    key = (os.environ.get(LSE_KEY_ENV) or "").strip()
    if not key:
        raise SystemExit(f"{LSE_KEY_ENV} is not set; source effects are blocked.")
    return LSE(api_key=key)


def _catalog_row(client: Any, symbol: str) -> dict:
    rows = client.catalog("futures")
    for row in rows or []:
        if str(row.get("symbol") or "").upper() == symbol.upper():
            return dict(row)
    raise SystemExit(f"{symbol!r} not present in LSE futures catalog")


def cmd_storage(args: argparse.Namespace) -> int:
    root = storage_root(args.root)
    c = capacity(root)
    print(json.dumps({
        "root": str(root),
        "total_gib": round(c.total_bytes / 1024 ** 3, 2),
        "used_gib": round(c.used_bytes / 1024 ** 3, 2),
        "free_gib": round(c.free_gib, 2),
        "reserve_gib": args.reserve_gib,
        "bulk_ready": c.free_gib >= args.reserve_gib,
    }, indent=2))
    return 0 if c.free_gib >= args.reserve_gib else 2


def cmd_probe_lse(args: argparse.Namespace) -> int:
    client = _lse_client()
    row = _catalog_row(client, args.symbol)
    usage = None
    fn = getattr(client, "usage", None)
    if callable(fn):
        try:
            usage = fn()
        except Exception:
            usage = {"status": "unavailable"}
    print(json.dumps({
        "source": "lse",
        "role": SourceRole.VENDOR_CONTINUOUS.value,
        "symbol": args.symbol,
        "catalog": row,
        "usage": usage,
        "probed_at_utc": utc_now(),
    }, indent=2, default=str))
    return 0


def _coerce_history_result(result: Any, scratch: Path):
    pd = _pandas()
    if hasattr(result, "to_parquet") and hasattr(result, "columns"):
        return result.copy()
    if isinstance(result, (str, os.PathLike)):
        return pd.read_parquet(Path(result))
    if isinstance(result, list):
        return pd.DataFrame(result)
    if isinstance(result, dict):
        rows = result.get("results") or result.get("rows")
        if isinstance(rows, list):
            return pd.DataFrame(rows)
    raise SystemExit(
        f"unsupported LSE history() return type {type(result).__name__}; "
        "upgrade/adapt the source adapter before writing bytes"
    )


def _timestamp_column(df) -> str | None:
    lower = {str(c).lower(): str(c) for c in df.columns}
    for candidate in ("timestamp", "ts", "datetime", "time"):
        if candidate in lower:
            return lower[candidate]
    return None


def _row_bounds(df) -> tuple[str | None, str | None]:
    col = _timestamp_column(df)
    if not col or len(df) == 0:
        return None, None
    pd = _pandas()
    s = pd.to_datetime(df[col], utc=True, errors="coerce").dropna()
    if s.empty:
        return None, None
    return s.min().isoformat(), s.max().isoformat()


def _write_dataframe_export(df, target: Path, *, source: str, source_role: SourceRole,
                            source_symbol: str, state: PartitionState) -> PartitionManifest:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    if partial.exists():
        partial.unlink()
    df.to_parquet(partial, index=False)
    os.replace(partial, target)
    lo, hi = _row_bounds(df)
    rel = target.relative_to(storage_root()).as_posix()
    manifest = PartitionManifest(
        source=source,
        source_role=source_role.value,
        source_symbol=source_symbol,
        state=state.value,
        relative_path=rel,
        row_count=int(len(df)),
        byte_count=int(target.stat().st_size),
        sha256=sha256_file(target),
        retrieved_at_utc=utc_now(),
        min_timestamp_utc=lo,
        max_timestamp_utc=hi,
    )
    write_manifest_atomic(target, manifest)
    return manifest


def cmd_backfill_lse(args: argparse.Namespace) -> int:
    root = storage_root(args.root)
    # Keep storage_root() coherent for manifest relative paths inside this process.
    os.environ["MMX_FUTURES_TAPE_ROOT"] = str(root)
    require_capacity(root, args.reserve_gib)
    target = raw_export_path(root, "lse", args.symbol, args.start, args.end)
    if target.exists() and manifest_path(target).exists() and not args.force:
        print(json.dumps({"status": "already_present", "path": str(target)}))
        return 0

    client = _lse_client()
    _catalog_row(client, args.symbol)  # fail before export if symbol identity is wrong
    kwargs = {"start": args.start, "end": args.end}
    result = client.history(args.symbol, **kwargs)
    df = _coerce_history_result(result, target.parent)
    manifest = _write_dataframe_export(
        df, target,
        source="lse",
        source_role=SourceRole.VENDOR_CONTINUOUS,
        source_symbol=args.symbol,
        state=PartitionState.FINAL,
    )
    print(manifest.to_json(), end="")
    return 0


def _normalize_lse_frame(df, source_symbol: str):
    pd = _pandas()
    lower = {str(c).lower(): str(c) for c in df.columns}
    ts_col = _timestamp_column(df)
    price_col = next((lower[k] for k in ("price", "last", "close") if k in lower), None)
    if not ts_col or not price_col:
        raise SystemExit(
            f"LSE raw export needs timestamp and price columns; got {list(df.columns)}"
        )
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df[ts_col], utc=True, errors="coerce"),
        "price_raw": pd.to_numeric(df[price_col], errors="coerce"),
        "source_symbol": source_symbol,
    })
    for canonical, candidates in {
        "bid_raw": ("bid", "bid_price"),
        "ask_raw": ("ask", "ask_price"),
        "volume": ("volume", "size", "qty"),
    }.items():
        src = next((lower[k] for k in candidates if k in lower), None)
        out[canonical] = pd.to_numeric(df[src], errors="coerce") if src else None
    out = out.dropna(subset=["timestamp_utc", "price_raw"]).sort_values("timestamp_utc")
    out = out.drop_duplicates(subset=["timestamp_utc", "price_raw", "volume"], keep="last")
    return out


def cmd_normalize_lse(args: argparse.Namespace) -> int:
    pd = _pandas()
    root = storage_root(args.root)
    os.environ["MMX_FUTURES_TAPE_ROOT"] = str(root)
    source_dir = root / "raw" / "source=lse" / f"symbol={args.symbol}"
    paths = sorted(source_dir.glob("window=*/export.parquet"))
    if not paths:
        raise SystemExit(f"no raw LSE exports found under {source_dir}")

    written = 0
    for raw in paths:
        df = pd.read_parquet(raw)
        norm = _normalize_lse_frame(df, args.symbol)
        if norm.empty:
            continue
        norm["_date"] = norm["timestamp_utc"].dt.strftime("%Y-%m-%d")
        for day, part in norm.groupby("_date", sort=True):
            target = normalized_day_path(root, "lse", args.identity, day)
            if target.exists() and not args.force:
                continue
            frame = part.drop(columns=["_date"]).reset_index(drop=True)
            _write_dataframe_export(
                frame, target,
                source="lse",
                source_role=SourceRole.VENDOR_CONTINUOUS,
                source_symbol=args.symbol,
                state=PartitionState.FINAL,
            )
            written += 1
    print(json.dumps({"status": "ok", "daily_partitions_written": written}))
    return 0


def cmd_derive_bars(args: argparse.Namespace) -> int:
    pd = _pandas()
    root = storage_root(args.root)
    os.environ["MMX_FUTURES_TAPE_ROOT"] = str(root)
    src = root / "normalized" / "ticks" / "source=lse" / f"instrument={args.instrument}"
    paths = sorted(src.glob("date=*/part-000.parquet"))
    if not paths:
        raise SystemExit(f"no normalized ticks found under {src}")
    written = 0
    for path in paths:
        df = pd.read_parquet(path)
        if df.empty:
            continue
        idx = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
        x = df.assign(_ts=idx).dropna(subset=["_ts"]).set_index("_ts")
        bars = x["price_raw"].resample(args.freq, label="left", closed="left").ohlc()
        if "volume" in x:
            bars["volume"] = x["volume"].resample(args.freq).sum(min_count=1)
        bars = bars.dropna(subset=["open", "high", "low", "close"]).reset_index()
        bars = bars.rename(columns={"_ts": "window_start_utc"})
        day = path.parent.name.split("=", 1)[-1]
        target = derived_bar_path(root, args.instrument, args.freq, day)
        if target.exists() and not args.force:
            continue
        _write_dataframe_export(
            bars, target,
            source="mmx",
            source_role=SourceRole.MMX_DERIVED_CONTINUOUS,
            source_symbol=args.instrument,
            state=PartitionState.FINAL,
        )
        written += 1
    print(json.dumps({"status": "ok", "bar_partitions_written": written, "freq": args.freq}))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    root = storage_root(args.root)
    problems = audit_manifests(root)
    result = {"root": str(root), "ok": not problems, "problems": problems}
    print(json.dumps(result, indent=2))
    return 0 if not problems else 1


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--root", default=None, help="override MMX_FUTURES_TAPE_ROOT")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("storage")
    p.add_argument("--reserve-gib", type=float, default=DEFAULT_RESERVE_GIB)
    p.set_defaults(func=cmd_storage)

    p = sub.add_parser("probe-lse")
    p.add_argument("--symbol", default="ES.F")
    p.set_defaults(func=cmd_probe_lse)

    p = sub.add_parser("backfill-lse")
    p.add_argument("--symbol", default="ES.F")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--reserve-gib", type=float, default=DEFAULT_RESERVE_GIB)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_backfill_lse)

    p = sub.add_parser("normalize-lse")
    p.add_argument("--symbol", default="ES.F")
    p.add_argument("--identity", default="LSE_ES.F")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_normalize_lse)

    p = sub.add_parser("derive-bars")
    p.add_argument("--instrument", default="LSE_ES.F")
    p.add_argument("--freq", default="1min")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_derive_bars)

    p = sub.add_parser("audit")
    p.set_defaults(func=cmd_audit)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
