"""Outcome-blind pre-2020 input consumer for the cohort-first research continuation.

Reads only the two incumbent VIX/VVIX input columns at one immutable Git revision.
The Parquet reader filters dates before decoding. No stock/ETF return, grey-dot
outcome, frozen race or sealed research path is opened. Aggregate counts only are
published; raw vendor observations remain in their existing owner.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd
import pyarrow.parquet as pq

from lib.nyse_calendar import is_session, sessions_between
from scripts.prophet_fusion_cohort_diagnostics import (
    AUTHORITY, CLOCK_LIMIT, DiagnosticRefusal, implied_volatility_trajectory,
)
from scripts.prophet_fusion_mechanism_study import _git_bytes, safe_cache, write_json

DATA_PIN = "6bbc4b0fc694c847077661ff5bf4c19ea41e4e81"
CUTOFF = pd.Timestamp("2019-12-31")
INPUTS = {"vix": ("data/fred/VIXCLS.parquet", "vix_close"),
          "vvix": ("data/cboe/vvix.parquet", "vvix")}


def _window(start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    try:
        a, b = pd.Timestamp(start), pd.Timestamp(end)
    except (TypeError, ValueError) as exc:
        raise DiagnosticRefusal("VALID_DATE_WINDOW_REQUIRED") from exc
    if (pd.isna(a) or pd.isna(b) or a.tz is not None or b.tz is not None
            or a != a.normalize() or b != b.normalize() or a > b):
        raise DiagnosticRefusal("VALID_DATE_WINDOW_REQUIRED")
    if b > CUTOFF:
        raise DiagnosticRefusal("POST_2019_WINDOW_NOT_ADMITTED_BY_THIS_CONSUMER")
    return a, b


def read_inputs(source: str, start: str, end: str) -> tuple[pd.DatetimeIndex, dict, list]:
    a, b = _window(start, end)  # Before any source access.
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise DiagnosticRefusal("IMMUTABLE_GIT_SOURCE_REQUIRED")
    warmup_start = a - pd.Timedelta(days=730)
    grid = pd.DatetimeIndex(sessions_between(warmup_start.date(), b.date()))
    values: dict[str, pd.Series] = {}
    receipts: list[dict[str, Any]] = []
    for name, (path, field) in INPUTS.items():
        raw = _git_bytes(source, path)
        schema = pq.ParquetFile(io.BytesIO(raw)).schema_arrow
        if not {"date", field}.issubset(schema.names):
            raise DiagnosticRefusal(f"{name}:NATIVE_INPUT_SCHEMA_MISMATCH")
        # Selection applies inside Arrow; no post-cutoff rows are converted to Pandas.
        table = pq.read_table(io.BytesIO(raw), columns=["date", field],
            filters=[("date", ">=", warmup_start), ("date", "<=", b)],
            use_threads=False, pre_buffer=False)
        frame = table.to_pandas()
        if "date" in frame.columns:
            frame = frame.set_index("date")
        if not isinstance(frame.index, pd.DatetimeIndex):
            raise DiagnosticRefusal(f"{name}:NATIVE_SESSION_INDEX_REQUIRED")
        if (frame.index.hasnans or not frame.index.is_unique or frame.index.tz is not None
                or not frame.index.equals(frame.index.normalize())
                or (len(frame) and (frame.index.min() < warmup_start or frame.index.max() > b))):
            raise DiagnosticRefusal(f"{name}:SOURCE_DATE_INTEGRITY")
        frame = frame.sort_index()
        off_calendar = ~frame.index.map(lambda x: is_session(x.date())).to_numpy(dtype=bool)
        series = frame.loc[~off_calendar, field]
        values[name] = series
        receipts.append({"name": name, "path": path, "git_source": source,
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "decoded_columns": ["date", field], "decoded_rows": len(frame),
            "decoded_window": [str(frame.index.min().date()), str(frame.index.max().date())] if len(frame) else [],
            "excluded_non_equity_session_rows": int(off_calendar.sum()),
            "missing_native_levels": int(series.isna().sum()),
            "calendar_rule": "house_NYSE_equity_session_grid_no_forward_fill",
            "source_availability": "reconstructed_store_vintage_not_original_publication_receipts"})
    return grid, values, receipts


def census(source: str = DATA_PIN, start: str = "2013-01-02", end: str = "2019-12-31") -> dict:
    a, b = _window(start, end)
    grid, values, receipts = read_inputs(source, start, end)
    frame = implied_volatility_trajectory(values["vix"], values["vvix"], grid)
    selected = frame.loc[(frame.index >= a) & (frame.index <= b)].copy()
    complete = selected.loc[selected["trajectory_available"]]
    high_vix = selected.loc[selected["vix_rank252"].ge(.9) & selected["trajectory_available"]]
    directions = selected["direction_pair"].value_counts(dropna=False)
    disagreement = selected["direction_pair"].isin(
        ["VIX_RISING_VVIX_FALLING", "VIX_FALLING_VVIX_RISING"])
    code = Path(__file__).with_name("prophet_fusion_cohort_diagnostics.py")
    return {"schema": "prophet.cohort_context_census/v1", "authority": AUTHORITY,
        "generated_at": datetime.now(timezone.utc).isoformat(), "source_base": source,
        "diagnostic_code_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
        "consumer_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_receipts": receipts, "window": [str(a.date()), str(b.date())],
        "measurement": {"ma_sessions": 20, "slope_sessions": 5, "rank_sessions": 252,
                        "peak_sessions": 63, "common_session_lag": 1,
                        "high_rank_descriptor": .9, "optimized": False},
        "coverage": {"equity_sessions": len(selected),
            "trajectory_qualified_sessions": int(selected["trajectory_available"].sum()),
            "full_rank_pair_sessions": int(selected["rank_pair_available"].sum()),
            "unavailable_vix_prior_level": int(selected["vix_level"].isna().sum()),
            "unavailable_vvix_prior_level": int(selected["vvix_level"].isna().sum()),
            "first_trajectory_session": str(complete.index.min().date()) if len(complete) else None,
            "last_trajectory_session": str(complete.index.max().date()) if len(complete) else None},
        "direction_counts": {str(k): int(v) for k, v in directions.items()},
        "opposite_ma_direction_sessions": int(disagreement.sum()),
        "high_vix_rank_direction_counts": {str(k): int(v) for k, v in high_vix["direction_pair"].value_counts().items()},
        "clock_limit": CLOCK_LIMIT, "raw_data_published": False,
        "outcomes_read": False, "stock_or_etf_returns_read": False,
        "holdout_opened": False, "forecast_probability": None, "promotion_eligible": False,
        "limitations": [
            "Coverage and descriptor counts cannot establish entry quality, rotation skill or profitability.",
            "A date lag does not prove an index close was published or received at a historical decision time.",
            "Current retained source history is not a contemporaneous-vintage archive.",
            "VIX and VVIX differ economically; neither rising series alone is a bullish or bearish trade rule.",
            "The fixed MA/slope windows are measurement choices, not selected profitable parameters.",
            "No Fable trough event sample or held-out market outcome is read by this consumer."]}


def render(report: dict) -> str:
    coverage = report["coverage"]
    rows = "\n".join(f"| {k} | {v:,} |" for k, v in sorted(report["direction_counts"].items()))
    return f"""# Cohort-first implied-volatility input census

**Outcome-blind input diagnostic. No entry, rotation or trading-performance claim.**

Source `{report['source_base']}`; window {report['window'][0]} through {report['window'][1]}.
The native VIX and implied VVIX stores are read through a date-filtered Arrow reader.
No post-2019 row is decoded, no return outcome is read, and no raw vendor series is published.

The measurement is MA20 direction over five equity sessions, with a one-session delay.
It preserves level, level relative to its average, native trailing rank and retreat from
an earlier peak separately. It does not combine these into a new risk score.

Of {coverage['equity_sessions']:,} equity sessions, {coverage['trajectory_qualified_sessions']:,}
have both qualified MA trajectories and {coverage['full_rank_pair_sessions']:,} have both
full 252-session ranks. Opposite MA directions occur on {report['opposite_ma_direction_sessions']:,}
sessions. These counts establish non-identical input behavior, not incremental predictive value.

| Pair of implied-volatility MA directions | Sessions |
|---|---:|
{rows}

## Interpretation and next proof

A rising VVIX trend is not equivalent to high VVIX, a high VVIX/VIX ratio, or realized
variability of VIX changes. Test its incremental contribution through the existing
Fable event archive and registered outcome contract, alongside market-date and cohort
controls. Preserve the native holdout release and every rejected/unknown entry.

The prior-session lag is `{report['clock_limit']}`. Original publication and data-vintage
proof remain owed. Missing sessions are never forward-filled. This census does not
choose a gate, estimate a win probability or authorize a change in exposure.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DATA_PIN)
    parser.add_argument("--start", default="2013-01-02")
    parser.add_argument("--end", default="2019-12-31")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _window(args.start, args.end)
        out = safe_cache(args.out)
        report = census(args.source, args.start, args.end)
        write_json(out / "cohort_context_census.json", report)
        (out / "cohort_context_census.md").write_text(render(report))
        print(json.dumps({"status": "OUTCOME_BLIND_CONTEXT_CONSUMER_PROVEN",
            "sessions": report["coverage"]["equity_sessions"], "outcomes_read": False,
            "holdout_opened": False, "promotion_eligible": False, "report": str(out / "cohort_context_census.json")}))
        return 0
    except (DiagnosticRefusal, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
