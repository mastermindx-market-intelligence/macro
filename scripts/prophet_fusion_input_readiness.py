"""Outcome-blind readiness audit over the existing conditional-fusion family registry.

This is a diagnostic consumer, not another feature-admission policy or data writer.
It reuses native family coverage, backtest admission and regime estimability. Date
checks cannot prove intraday availability, original publication, source quality or
predictive edge. No performance label, frozen W3/W2 store or live score is read.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
import io
from pathlib import Path
import re
import subprocess
from typing import Any

# Direct file-path execution must resolve this repository, not the caller cwd.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from engine.regime_conditioning_coverage import assess_axis
from lib import nyse_calendar
from scripts.prophet_fusion_arena import (
    FusionRefusal, Registry, build_folds, check_features, family_coverage, load_registry,
)
from scripts.prophet_fusion_mechanisms import MechanismRefusal, digest_bytes
from scripts.prophet_fusion_mechanism_study import ROOT, _git_bytes, safe_cache, write_json

AXES = ("regime__quad", "regime__pending_quad", "regime__transition_state", "regime__liquidity")
IDENTITY_COLUMNS = ("stamp_date", "ticker", "board_definition", "selection_era")
_NULL_TOKENS = {"", "none", "nan", "null", "unknown", "na", "n/a", "unavailable"}


def clean_observations(values: pd.Series) -> pd.Series:
    """Zero/False are real values; empty/unknown tokens are not observations."""
    def clean(value: Any) -> Any:
        if isinstance(value, str) and value.strip().lower() in _NULL_TOKENS:
            return None
        if isinstance(value, (float, np.floating)) and not np.isfinite(value):
            return None
        return value
    return values.map(clean)


def date_labels(values: pd.Series) -> pd.Series:
    # This deliberately is ONLY a date-label check. It grants no same-day clock proof.
    text = values.astype("string").str.slice(0, 10)
    return pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")


def selected_columns(names: list[str], registry: Registry) -> list[str]:
    wanted = set(IDENTITY_COLUMNS)
    for member in registry.members.values():
        wanted.update(member.columns)
        if member.availability_field:
            wanted.add(member.availability_field)
    wanted -= set(registry.forbidden)
    chosen = sorted(set(names) & wanted)
    forbidden = {"outcome_graded", "graded_at", "outcome_basis", "net_return", "ret_at_read"}
    if any(c in forbidden or re.match(r"^(outcome_|graded_|fwd_|label_)", c) for c in chosen):
        raise MechanismRefusal("OUTCOME_COLUMN_IN_INPUT_REGISTRY")
    if "stamp_date" not in chosen:
        raise MechanismRefusal("CANDIDATE_STAMP_DATE_ABSENT")
    return chosen


def audit_frame(frame: pd.DataFrame, registry: Registry) -> dict:
    if "stamp_date" not in frame.columns or frame.empty:
        raise MechanismRefusal("EMPTY_OR_UNDATED_CANDIDATE_FRAME")
    # RangeIndex prevents duplicate upstream indexes from manufacturing row alignment.
    frame = frame.reset_index(drop=True)
    stamps = date_labels(frame["stamp_date"])
    valid_session = stamps.map(lambda d: bool(pd.notna(d) and nyse_calendar.is_session(d.date())))
    normalized = pd.DataFrame(index=frame.index)
    eligible_dates = pd.DataFrame(index=frame.index)
    for column in registry.columns:
        if column in frame.columns and column not in registry.forbidden:
            normalized[column] = clean_observations(frame[column])
    # Initialize the family denominator with every registered column (missing remains absent).
    eligible_dates = normalized.copy()
    details = []
    for member_id, member in registry.members.items():
        columns = list(member.columns)
        present = [c for c in columns if c in normalized.columns]
        missing = [c for c in columns if c not in normalized.columns]
        native_allowed, refusal = True, None
        if not columns:
            native_allowed, refusal = False, "NO_REGISTERED_HISTORICAL_COLUMNS"
        else:
            try:
                check_features(registry, columns)
            except FusionRefusal as exc:
                native_allowed, refusal = False, f"{type(exc).__name__}:{str(exc)[:240]}"
        field = member.availability_field
        source_dates = date_labels(frame[field]) if field and field in frame else pd.Series(pd.NaT, index=frame.index)
        unknown_clock = source_dates.isna() | stamps.isna() | ~valid_session
        future = source_dates.gt(stamps) & ~unknown_clock
        stale = pd.Series(False, index=frame.index)
        if member.max_staleness_sessions is not None:
            floor_by_date = {
                d: nyse_calendar.session_n_back(d.date(), member.max_staleness_sessions)
                for d in stamps[valid_session].drop_duplicates()
            }
            floor = pd.to_datetime(stamps.map(floor_by_date), errors="coerce")
            stale = source_dates.lt(floor) & ~unknown_clock
        passes_date_checks = ~unknown_clock & ~future & ~stale & native_allowed
        for column in present:
            eligible_dates[column] = normalized[column].where(passes_date_checks)
        raw_count = sum(int(normalized[c].notna().sum()) for c in present)
        usable_count = sum(int(eligible_dates[c].notna().sum()) for c in present)
        denominator = len(frame) * len(columns)
        details.append({
            "member": member_id, "family": member.family, "pit_status": member.pit_status,
            "native_backtest_status_allowed": native_allowed, "native_refusal": refusal,
            "availability_field": field, "availability_field_present": bool(field and field in frame),
            "max_staleness_sessions": member.max_staleness_sessions,
            "registered_columns": columns, "present_columns": present, "absent_columns": missing,
            "raw_known_fraction": raw_count / denominator if denominator else 0.0,
            "date_checked_known_fraction": usable_count / denominator if denominator else 0.0,
            "source_clock_unknown_rows": int(unknown_clock.sum()),
            "source_date_after_row_rows": int(future.sum()), "stale_source_date_rows": int(stale.sum()),
            "same_day_source_rows": int((source_dates.eq(stamps) & ~unknown_clock).sum()),
            "intraday_availability_proven": False,
        })
    raw_families = family_coverage(normalized, registry, split="ungraded_observations").to_dict("records")
    dated_families = family_coverage(eligible_dates, registry, split="native_status_and_date_checks_only").to_dict("records")
    axis_frame = eligible_dates.copy()
    axis_frame["date"] = stamps
    axes = [assess_axis(axis_frame, axis) for axis in AXES]
    counts = {}
    for field in ("board_definition", "selection_era"):
        counts[field] = ({str(k): int(v) for k, v in frame[field].value_counts(dropna=False).items()}
                         if field in frame else {"UNAVAILABLE": len(frame)})
    dates = sorted(str(d.date()) for d in stamps[valid_session].drop_duplicates())
    fold_readiness = {}
    for horizon in (21, 63):
        plan = build_folds(dates, horizon=horizon, embargo=horizon, strict=False)
        fold_readiness[str(horizon)] = {"folds": [f.as_dict() for f in plan.folds],
                                       "refusals": plan.refusals,
                                       "note": "Native default floors unchanged; input dates only, no outcomes."}
    return {
        "native_fold_readiness": fold_readiness,
        "rows": len(frame), "distinct_dates": int(stamps.nunique()),
        "distinct_months": int(stamps.dt.to_period("M").nunique()),
        "invalid_session_or_date_rows": int((~valid_session).sum()),
        "first_date": str(stamps.min().date()) if stamps.notna().any() else None,
        "last_date": str(stamps.max().date()) if stamps.notna().any() else None,
        "identity_populations": counts, "members": details,
        "raw_family_coverage": raw_families, "date_checked_family_coverage": dated_families,
        "native_regime_estimability": axes, "outcomes_read": False, "promotion_eligible": False,
        "date_checks_are_admission": False, "original_receipt_proof": "NOT_ESTABLISHED_BY_THIS_AUDIT",
    }


def collect_source(source: str, registry: Registry) -> tuple[pd.DataFrame, list[dict]]:
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise MechanismRefusal("IMMUTABLE_SOURCE_COMMIT_REQUIRED")
    registry_path = Path(registry.path).resolve().relative_to(ROOT)
    pinned_registry = subprocess.run(["git", "show", f"{source}:{registry_path}"], cwd=ROOT,
                                     capture_output=True, timeout=30, check=True).stdout
    if digest_bytes(pinned_registry) != digest_bytes(Path(registry.path).read_bytes()):
        raise MechanismRefusal("REGISTRY_SOURCE_MISMATCH")
    proc = subprocess.run(["git", "ls-tree", "-r", "--name-only", source, "--",
                           "data/us_prophet_rank/candidates"], cwd=ROOT, capture_output=True,
                          text=True, timeout=30, check=True)
    paths = [p for p in proc.stdout.splitlines()
             if re.fullmatch(r"data/us_prophet_rank/candidates/20\d\d-\d\d\.parquet", p)]
    if not paths:
        raise MechanismRefusal("NO_PINNED_CANDIDATE_FILES")
    frames, inputs = [], []
    for path in sorted(paths):
        raw = _git_bytes(source, path)
        pf = pq.ParquetFile(io.BytesIO(raw))
        columns = selected_columns(pf.schema_arrow.names, registry)
        # Parquet decoding explicitly excludes grades and outcomes; no full-frame read.
        frame = pd.read_parquet(io.BytesIO(raw), columns=columns)
        frames.append(frame)
        inputs.append({"path": path, "sha256": digest_bytes(raw), "rows": len(frame),
                       "decoded_columns": columns, "outcome_columns_decoded": []})
    return pd.concat(frames, ignore_index=True, sort=False), inputs


def render(report: dict) -> str:
    lines = ["# Conditional-fusion input readiness", "", "**Outcome-blind diagnostic; no predictive or trading authority.**", "",
             f"Source `{report['source_base']}`. {report['rows']:,} candidate rows span "
             f"{report['distinct_dates']} dates and {report['distinct_months']} calendar months.", "",
             "The native registry decides research admissibility; its historical-status exclusions are retained. "
             "This audit additionally reports missing, future-dated and stale date labels. It does not prove "
             "actual intraday receipt time or original availability. Populations with different board definitions "
             "are counted separately, not interpreted as one historical strategy.", "",
             "## Family coverage", "",
             "| Native family | Raw known fraction | Native-status + date-check fraction | Registered floor | Abstain after checks |",
             "|---|---:|---:|---:|---|"]
    by_family = {r['family']: r for r in report['raw_family_coverage']}
    for row in report['date_checked_family_coverage']:
        raw = by_family[row['family']]
        lines.append(f"| {row['family']} | {raw['coverage']:.1%} | {row['coverage']:.1%} | "
                     f"{row['coverage_floor']:.1%} | {row['abstain']} |")
    lines += ["", "## Native regime estimability", "",
              "The existing meter requires at least two observed states and twelve distinct months in every "
              "state. Thousands of names on a few dates cannot satisfy that requirement.", "",
              "| Axis | Observed states | Months in thinnest state | Native verdict |",
              "|---|---:|---:|---|"]
    for row in report['native_regime_estimability']:
        lines.append(f"| {row['axis']} | {row['n_states']} | {row['min_state_months']} | {row['verdict']} |")
    lines += ["", "## Native chronological-fold readiness", ""]
    for horizon, item in report["native_fold_readiness"].items():
        lines.append(f"- {horizon}-session horizon: {len(item['folds'])} qualified folds. "
                     "Native training, test, purge and embargo floors are unchanged.")
    lines += ["", "## Consequence", "",
              "Use this to prioritize source repair and prospective accrual, not to infer which feature "
              "makes money. An insufficient cell stays unknown; do not lower its floor or synthesize history. "
              "Historical economic/context combinations need genuine archived source clocks and the existing "
              "arena's frozen chronological tests. No W3 or W2 outcomes were read.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    out = safe_cache(args.out)
    registry = load_registry()
    frame, inputs = collect_source(args.source_sha, registry)
    report = audit_frame(frame, registry)
    report.update(schema="prophet.fusion_input_readiness/v1", source_base=args.source_sha,
                  generated_at=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                  registry_sha256=digest_bytes(Path(registry.path).read_bytes()),
                  code_sha256=digest_bytes(Path(__file__).read_bytes()))
    write_json(out / "readiness.json", report)
    (out / "readiness.md").write_text(render(report))
    print(f"READINESS_COMPLETE rows={report['rows']} dates={report['distinct_dates']} "
          f"months={report['distinct_months']} outcomes_read=False report={out / 'readiness.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
