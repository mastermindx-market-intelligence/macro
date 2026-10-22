#!/usr/bin/env python3
"""Compile the ``systematic_research.v1`` report from LOCAL price files.

WHAT THIS DOES
--------------
Reads OHLCV files from an explicit ``--input-dir`` plus a ``metadata.json``
sidecar, compiles the frozen research-only report with
``engine.systematic_research.build_report`` and writes it to an explicit
``--output`` path.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
No network. No provider purchase. No ingestion scheduler. No account, QLedger,
credential, allocation or production write. Importing this module performs no
I/O at all: the reader runs only inside ``main()``. Nothing is written except the
single file named by ``--output``, and only after the report has compiled
cleanly — a refused input writes nothing rather than a half-report.

INPUT SCHEMA (per instrument)
----------------------------
``<INPUT_DIR>/<TICKER>.csv`` or ``<INPUT_DIR>/<TICKER>.parquet`` with

  * a session-date column named ``date`` (or a datetime index), and
  * float columns ``open``, ``high``, ``low``, ``close``, ``volume``.

``open`` is REQUIRED. This engine fills at the next session's open, and the
repository's own ``data/stocks/*.parquet`` store carries only ``close``/``high``/
``low``/``volume``. That store is therefore NOT suitable input here: substituting
the close for the open would manufacture a fill price that was never traded.
Point it at a source that actually carries opens, or the loader refuses with
``input_requires_open_column``.

``<INPUT_DIR>/metadata.json`` declares point-in-time and provenance facts::

    {
      "as_of": "2026-10-21",
      "expected_last_session": "2026-10-21",
      "data_revision": "<opaque revision string>",
      "sessions_per_year": 252,
      "synthetic": false,
      "source": "local export",
      "instruments": {
        "AAA": {
          "available_at": ["2026-01-02T21:05:00", ...],   # per session, aligned
          "adjustment_basis": {"open": "split_adj", "high": "split_adj",
                               "low": "split_adj", "close": "split_adj",
                               "volume": "split_adj"},
          "source": "local export"
        }
      }
    }

``available_at`` is REQUIRED per session. A bar whose ``available_at`` is after
``as_of`` is excluded, so appending future data cannot alter reported history.
``adjustment_basis`` may be one string for every column or a per-column mapping,
but the values must agree.

USAGE
-----
    python3 scripts/build_systematic_research.py \
        --input-dir /path/to/prices \
        --output /path/to/systematic_research.json \
        --as-of 2026-10-21 --generated-at 2026-10-22T09:00:00Z \
        --code-revision "$(git rev-parse HEAD)" \
        --expected-last-session 2026-10-21 \
        --cost-bps 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Allow running as a script as well as a module (repo convention).
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from engine.systematic_research import (
    CANDIDATE_KEYS,
    SCHEMA,
    PriceFrame,
    build_report,
    dumps,
)

METADATA_FILENAME = "metadata.json"
_DATE_COLUMNS = ("date", "session", "session_date", "Date", "timestamp", "ts")


class InputRefused(RuntimeError):
    """The inputs cannot support an honest report. Writes nothing."""


def _read_price_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise InputRefused(f"unsupported_price_file_extension:{path.suffix}")
    if df.empty:
        raise InputRefused(f"price_file_is_empty:{path.name}")
    for col in _DATE_COLUMNS:
        if col in df.columns:
            df = df.set_index(col)
            break
    if not isinstance(df.index, pd.DatetimeIndex):
        parsed = pd.to_datetime(df.index, errors="coerce")
        if parsed.isna().all():
            raise InputRefused(f"session_index_is_not_a_date:{path.name}")
        df = df.copy()
        df.index = pd.DatetimeIndex(parsed)
    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
    return df


def load_inputs(input_dir: Path) -> tuple[dict[str, PriceFrame], dict[str, Any]]:
    """Read every instrument the metadata sidecar declares.

    Discovery is driven by the sidecar's ``instruments`` map, not by whatever
    happens to sit in the directory: an undeclared file cannot silently join an
    equal-weight portfolio.
    """
    meta_path = input_dir / METADATA_FILENAME
    if not meta_path.is_file():
        raise InputRefused(f"metadata_sidecar_not_found:{METADATA_FILENAME}")
    try:
        meta = json.loads(meta_path.read_text())
    except json.JSONDecodeError as exc:
        raise InputRefused(f"metadata_sidecar_not_valid_json:{exc.msg}") from exc

    declared = meta.get("instruments")
    if not isinstance(declared, dict) or not declared:
        raise InputRefused("metadata_sidecar_declares_no_instruments")

    default_ppy = int(meta.get("sessions_per_year", 252))
    frames: dict[str, PriceFrame] = {}
    for ticker in sorted(declared):
        spec = declared[ticker] or {}
        path = None
        for suffix in (".csv", ".parquet", ".pq"):
            candidate = input_dir / f"{ticker}{suffix}"
            if candidate.is_file():
                path = candidate
                break
        if path is None:
            raise InputRefused(f"declared_price_file_missing:{ticker}")

        table = _read_price_table(path)
        if "open" not in table.columns:
            raise InputRefused(f"input_requires_open_column:{path.name}")
        for required in ("high", "low", "close", "volume"):
            if required not in table.columns:
                raise InputRefused(f"missing_column_{required}:{path.name}")

        available = spec.get("available_at")
        if not isinstance(available, list) or len(available) != len(table):
            raise InputRefused(
                f"available_at_must_be_declared_for_every_session:{ticker}")
        # NOTE: build from the parsed VALUES. Re-wrapping the parsed Series with
        # `pd.Series(parsed, index=...)` would ALIGN on the parsed RangeIndex
        # against the session DatetimeIndex and silently produce all-NaT.
        parsed = pd.to_datetime(pd.Series(available), errors="coerce").to_numpy()
        available_at = pd.Series(parsed, index=table.index)
        if available_at.isna().any():
            raise InputRefused(f"available_at_not_parseable:{ticker}")

        frames[ticker] = PriceFrame(
            frame=table[["open", "high", "low", "close", "volume"]].copy(),
            available_at=available_at,
            adjustment_basis=spec.get("adjustment_basis", ""),
            sessions_per_year=int(spec.get("sessions_per_year", default_ppy)),
            synthetic=bool(meta.get("synthetic", False)),
            source=str(spec.get("source", meta.get("source", ""))),
            ticker=ticker,
        )
    return frames, meta


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_systematic_research",
        description=("Compile the frozen systematic_research.v1 research report "
                     "from local price files. Research only: no network, no "
                     "provider purchase, no ingestion scheduler, no orders."),
    )
    p.add_argument("--input-dir", required=True, type=Path,
                   help="Directory of <TICKER>.csv/.parquet plus metadata.json.")
    p.add_argument("--output", required=True, type=Path,
                   help="Explicit output path. Nothing is written elsewhere.")
    p.add_argument("--as-of", default=None,
                   help="ISO cutoff. Defaults to metadata.json 'as_of'.")
    p.add_argument("--generated-at", required=True,
                   help="ISO timestamp stamped into the report. Explicit so the "
                        "output is reproducible.")
    p.add_argument("--code-revision", required=True,
                   help="Source revision this report was compiled from.")
    p.add_argument("--data-revision", default=None,
                   help="Data revision. Defaults to metadata.json 'data_revision'.")
    p.add_argument("--cost-bps", type=float, required=True,
                   help="One-way cost in basis points on traded notional. "
                        "Must be finite and non-negative.")
    p.add_argument("--expected-last-session", default=None,
                   help="Explicit freshness contract. Without it the report "
                        "cannot certify data_health and reports inputs_blocked.")
    p.add_argument("--sessions-per-year", type=int, default=None,
                   help="Declared sampling cadence for annualisation.")
    p.add_argument("--aum-usd", type=float, default=None,
                   help="Opt in to square-root impact modelling. Omit and no "
                        "capacity claim is made at all.")
    p.add_argument("--impact-eta", type=float, default=0.1,
                   help="Impact coefficient, used only with --aum-usd.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        frames, meta = load_inputs(args.input_dir)
    except InputRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    as_of = args.as_of or meta.get("as_of")
    if not as_of:
        print("refused: as_of_not_declared", file=sys.stderr)
        return 2
    data_revision = args.data_revision or meta.get("data_revision")
    if not data_revision:
        print("refused: data_revision_not_declared", file=sys.stderr)
        return 2

    try:
        report = build_report(
            frames,
            as_of=str(as_of),
            generated_at=args.generated_at,
            code_revision=args.code_revision,
            data_revision=str(data_revision),
            cost_bps=args.cost_bps,
            expected_last_session=args.expected_last_session,
            sessions_per_year=args.sessions_per_year,
            aum_usd=args.aum_usd,
            impact_eta=args.impact_eta,
        )
    except (ValueError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    text = dumps(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(f"wrote {args.output} ({report['status']}, "
          f"evaluated {report['summary']['evaluated_count']}/"
          f"{report['summary']['candidate_count']} "
          f"candidates, capital_eligible_count "
          f"{report['summary']['capital_eligible_count']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())