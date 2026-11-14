"""Metadata-only bridge from Prophet's original G3 SCREEN archive to cohort context.

This is a research consumer, not a detector, trial registry, event store, or trading
signal. Extraction is standalone so the source owner need not install this repo.
Only the three explicit Parquet metadata projections below are decoded. No outcome
or stock-price column is decoded. Arrow filters metadata to SCREEN before pandas
conversion; physical row-group decoding is not claimed absent. Original IDs remain
unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_SHA256 = "6215ac12fa47ab594f424295365e72c6e71865d5c7a6bd9986df23b6f9aada6c"
SCHEMA = "prophet.recovered_screen_context/v1"
EXPORT_SCHEMA = "prophet.recovered_screen_metadata/v1"
START, END = pd.Timestamp("2013-01-02"), pd.Timestamp("2019-12-31")
EVENTS = "events_v1/EVENTS_G3.parquet"
GUARD = "events_v1/FULL_GUARD_RESULTS.parquet"
PRIMARY = "dot_gate_1/ANALYTIC_EVENTS.parquet"
EVENT_COLUMNS = [
    "event_id", "ticker", "table", "date", "bar_label", "window", "group",
    "family", "coverage_grade", "counting", "in_washout_context",
]
GATES = ["A1", "A2", "A3", "ANY", "A4", "defined"]
PROJECTIONS = {
    EVENTS: EVENT_COLUMNS,
    GUARD: ["event_id", "ticker", "date", "agree"],
    PRIMARY: ["event_id", "ticker", "date", "group", *GATES],
}
EXPORT_COLUMNS = [*EVENT_COLUMNS, "prefix_verified_at_declared_date",
                  "primary_analytic", *GATES]
LIMITATIONS = [
    "Research diagnostic only; no forecast, ranking, sizing, gate or promotion.",
    "Source date is declared known date, verified visible on that price prefix; "
    "it is not an original first-seen receipt or a complete live-event census.",
    "bar_label is a display label and is never substituted for the decision date.",
    "Context uses the preceding expected NYSE session, without forward fill; "
    "input vintage is reconstructed, not original publication evidence.",
    "ANY/A4 are complementary only within the original primary analytic subset. "
    "Events outside that subset remain unclassified, not A4.",
    "Original primary membership reflects the original analysis selection, "
    "including label availability; it is not prospective eligibility.",
    "A2/A3 SCREEN80 cuts use the entire development window and are retrospective "
    "calibrations, not historically available thresholds.",
    "Native coverage grades are retained: 2013–17 survivor-biased, 2018–19 usable. "
    "The latter is the source designation, not a new general certification.",
    "This original archive predates the incumbent W1 split-calendar quarantine. "
    "No W1 exclusions, corrected labels, or corporate-action vintage are inferred.",
    "No new outcome comparison, holdout access, or experiment execution.",
]


class ScreenSourceRefusal(ValueError):
    """A source, identity, timing or outcome-exclusion contract failed."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load_manifest(path: Path) -> dict:
    if sha256(path) != MANIFEST_SHA256:
        raise ScreenSourceRefusal("UNPINNED_SOURCE_MANIFEST")
    m = json.loads(path.read_text())
    if (m.get("schema") != "prophet.recovered_screen_source/v1"
            or m.get("window") != ["2013-01-02", "2019-12-31"]
            or m.get("outcome_access_authorized") is not False):
        raise ScreenSourceRefusal("SOURCE_MANIFEST_CONTRACT")
    return m


def _ids(frame: pd.DataFrame) -> str:
    values = frame["event_id"]
    if (values.isna().any() or not values.map(
            lambda x: isinstance(x, str) and bool(x.strip())).all()
            or not values.is_unique):
        raise ScreenSourceRefusal("DUPLICATE_OR_MISSING_EVENT_ID")
    return hashlib.sha256(("\n".join(sorted(values)) + "\n").encode()).hexdigest()


def _boolean(frame: pd.DataFrame, columns: list[str]) -> None:
    for name in columns:
        if (not pd.api.types.is_bool_dtype(frame[name].dtype)
                or frame[name].isna().any()):
            raise ScreenSourceRefusal(f"BOOLEAN_REQUIRED:{name}")


def _dates(frame: pd.DataFrame, column: str = "date") -> None:
    values = frame[column]
    if (not pd.api.types.is_datetime64_any_dtype(values.dtype)
            or isinstance(values.dtype, pd.DatetimeTZDtype)
            or values.isna().any() or not values.eq(values.dt.normalize()).all()
            or not values.between(START, END).all()):
        raise ScreenSourceRefusal(f"SCREEN_DATE_INTEGRITY:{column}")


def _projection(root: Path, relative: str, manifest: dict) -> tuple[pd.DataFrame, dict]:
    path = root / relative
    expected = manifest["files"][relative]
    if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
        raise ScreenSourceRefusal(f"SOURCE_DIGEST_MISMATCH:{relative}")
    columns = PROJECTIONS[relative]
    if not set(columns).issubset(pq.ParquetFile(path).schema_arrow.names):
        raise ScreenSourceRefusal(f"SOURCE_SCHEMA_MISMATCH:{relative}")
    # No read-all/drop-later: both column and SCREEN filters are applied in Arrow.
    table = pq.read_table(path, columns=columns,
        filters=[("date", ">=", START), ("date", "<=", END)],
        use_threads=False, pre_buffer=False)
    frame = table.to_pandas()
    if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
        raise ScreenSourceRefusal(f"SOURCE_CHANGED_DURING_READ:{relative}")
    if list(frame.columns) != columns:
        raise ScreenSourceRefusal(f"UNEXPECTED_DECODED_COLUMNS:{relative}")
    _ids(frame)
    _dates(frame)
    return frame, {"path": relative, **expected, "decoded_columns": columns,
                   "projected_rows_materialized": len(frame),
                   "source_digest_verified_before_and_after_projection": True,
                   "materialized_window": [
                       str(frame.date.min().date()), str(frame.date.max().date())]
                   if len(frame) else []}


def _primary_contract(primary: pd.DataFrame) -> None:
    _boolean(primary, GATES)
    if (not primary["defined"].all()
            or not primary["ANY"].eq(primary[["A1", "A2", "A3"]].any(axis=1)).all()
            or not primary["A4"].eq(~primary["ANY"]).all()):
        raise ScreenSourceRefusal("PRIMARY_GATE_PARTITION_MISMATCH")


def validate_export(frame: pd.DataFrame, manifest: dict) -> dict:
    if list(frame.columns) != EXPORT_COLUMNS:
        raise ScreenSourceRefusal("EXPORT_COLUMN_ALLOWLIST_MISMATCH")
    identity = _ids(frame)
    _dates(frame)
    # Display labels may precede the SCREEN window; they must not exceed known date.
    labels = frame["bar_label"]
    if (not pd.api.types.is_datetime64_any_dtype(labels.dtype)
            or isinstance(labels.dtype, pd.DatetimeTZDtype) or labels.isna().any()
            or not labels.eq(labels.dt.normalize()).all()
            or labels.gt(frame["date"]).any()):
        raise ScreenSourceRefusal("DISPLAY_LABEL_INTEGRITY")
    _boolean(frame, ["prefix_verified_at_declared_date", "primary_analytic", "counting"])
    if (not frame["prefix_verified_at_declared_date"].all()
            or not frame["window"].eq("SCREEN").all()
            or not frame["table"].eq("G3").all()):
        raise ScreenSourceRefusal("SOURCE_POPULATION_CONTRACT")
    primary = frame.loc[frame["primary_analytic"]]
    _primary_contract(primary)
    if frame.loc[~frame["primary_analytic"], GATES].notna().any().any():
        raise ScreenSourceRefusal("UNCLASSIFIED_EVENTS_MUST_REMAIN_UNDEFINED")
    counts = {"screen_retained": len(frame), "primary_analytic": len(primary),
              "primary_any": int(primary["ANY"].sum()),
              "primary_none": int(primary["A4"].sum())}
    if counts != manifest["expected_counts"]:
        raise ScreenSourceRefusal("ORIGINAL_POPULATION_COUNT_MISMATCH")
    return {**counts, "outside_primary_analytic": len(frame) - len(primary),
            "event_id_set_sha256": identity}


def extract_metadata(root: Path, manifest_path: Path, out: Path) -> dict:
    manifest = load_manifest(manifest_path)
    root, out = root.resolve(), out.resolve()
    if out == root or root in out.parents:
        raise ScreenSourceRefusal("OUTPUT_INSIDE_ORIGINAL_ARCHIVE")
    if (out / "metadata.parquet").exists() or (out / "receipt.json").exists():
        raise ScreenSourceRefusal("EXPORT_ALREADY_EXISTS")
    frames, inputs = {}, []
    for relative in PROJECTIONS:
        frames[relative], receipt = _projection(root, relative, manifest)
        inputs.append(receipt)
    events, guard, primary = frames[EVENTS], frames[GUARD], frames[PRIMARY]
    _boolean(guard, ["agree"])
    _primary_contract(primary)
    if not set(primary.event_id).issubset(events.event_id):
        raise ScreenSourceRefusal("PRIMARY_EVENT_NOT_IN_SOURCE")
    proof = events[["event_id", "ticker", "date"]].merge(
        guard, on="event_id", how="left", validate="one_to_one", suffixes=("", "_guard"))
    if (proof["agree"].isna().any() or not proof["agree"].all()
            or not proof["ticker"].eq(proof["ticker_guard"]).all()
            or not proof["date"].eq(proof["date_guard"]).all()):
        raise ScreenSourceRefusal("SAME_DATE_PREFIX_PROOF_MISMATCH")
    p = primary.merge(events[["event_id", "ticker", "date", "group"]],
                      on="event_id", validate="one_to_one", suffixes=("", "_source"))
    for key in ["ticker", "date", "group"]:
        if not (p[key].eq(p[key + "_source"])
                | (p[key].isna() & p[key + "_source"].isna())).all():
            raise ScreenSourceRefusal(f"PRIMARY_IDENTITY_MISMATCH:{key}")
    result = events.merge(primary[["event_id", *GATES]], on="event_id", how="left",
                          validate="one_to_one")
    result["prefix_verified_at_declared_date"] = True
    result["primary_analytic"] = result.event_id.isin(primary.event_id)
    for key in GATES:
        result[key] = result[key].astype("boolean")
    result = result[EXPORT_COLUMNS].sort_values(
        ["date", "ticker", "event_id"], kind="stable").reset_index(drop=True)
    counts = validate_export(result, manifest)
    out.mkdir(parents=True, exist_ok=True)
    export = out / "metadata.parquet"
    result.to_parquet(export, index=False)
    receipt = {
        "schema": EXPORT_SCHEMA, "source_manifest_sha256": sha256(manifest_path),
        "source_mode": manifest["source_mode"], "source_root": str(root),
        "extractor_sha256": sha256(Path(__file__)),
        "only_metadata_columns_decoded": True, "inputs": inputs, "counts": counts,
        "export": {"file": "metadata.parquet", "sha256": sha256(export),
                   "bytes": export.stat().st_size, "columns": EXPORT_COLUMNS},
        "outcomes_decoded": False, "holdout_rows_materialized_in_export": False,
        "original_archive_modified": False,
    }
    _json(out / "receipt.json", receipt)
    return receipt


def load_export(directory: Path, manifest_path: Path, receipt_sha256: str) -> tuple[pd.DataFrame, dict]:
    manifest = load_manifest(manifest_path)
    receipt_path, export_path = directory / "receipt.json", directory / "metadata.parquet"
    if sha256(receipt_path) != receipt_sha256:
        raise ScreenSourceRefusal("UNPINNED_EXPORT_RECEIPT")
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get("schema") != EXPORT_SCHEMA
            or receipt.get("source_manifest_sha256") != MANIFEST_SHA256
            or receipt.get("extractor_sha256") != sha256(Path(__file__))
            or receipt.get("outcomes_decoded") is not False
            or receipt.get("holdout_rows_materialized_in_export") is not False
            or receipt.get("only_metadata_columns_decoded") is not True):
        raise ScreenSourceRefusal("EXPORT_RECEIPT_CONTRACT")
    if len(receipt.get("inputs", [])) != len(PROJECTIONS):
        raise ScreenSourceRefusal("SOURCE_PROJECTION_RECEIPT_MISMATCH")
    for entry, (relative, columns) in zip(receipt["inputs"], PROJECTIONS.items()):
        expected = manifest["files"][relative]
        if (entry.get("path") != relative or entry.get("decoded_columns") != columns
                or entry.get("sha256") != expected["sha256"]
                or entry.get("bytes") != expected["bytes"]
                or entry.get("source_digest_verified_before_and_after_projection") is not True):
            raise ScreenSourceRefusal("SOURCE_PROJECTION_RECEIPT_MISMATCH")
    exported = receipt["export"]
    if (exported.get("file") != "metadata.parquet"
            or exported.get("columns") != EXPORT_COLUMNS
            or export_path.stat().st_size != exported["bytes"]
            or sha256(export_path) != exported["sha256"]):
        raise ScreenSourceRefusal("EXPORT_DIGEST_MISMATCH")
    metadata = pq.ParquetFile(export_path)
    if metadata.metadata.num_rows != manifest["expected_counts"]["screen_retained"]:
        raise ScreenSourceRefusal("EXPORT_ROW_COUNT_MISMATCH")
    if metadata.schema_arrow.names != EXPORT_COLUMNS:
        raise ScreenSourceRefusal("EXPORT_COLUMN_ALLOWLIST_MISMATCH")
    frame = pq.read_table(export_path, columns=EXPORT_COLUMNS,
        filters=[("date", ">=", START), ("date", "<=", END)],
        use_threads=False, pre_buffer=False).to_pandas()
    if validate_export(frame, manifest) != receipt["counts"]:
        raise ScreenSourceRefusal("EXPORT_IDENTITY_RECEIPT_MISMATCH")
    return frame, receipt


def join_screen_context(frame: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    # Lazy imports keep extraction standalone on the existing source-owner host.
    from scripts.prophet_fusion_cohort_diagnostics import (
        AUTHORITY, CLOCK_LIMIT, SCHEMA as CONTEXT_SCHEMA, _dates as context_dates,
    )
    _ids(frame)
    context_dates(context.index, complete=True)
    if (context.attrs.get("schema") != CONTEXT_SCHEMA
            or context.attrs.get("authority") != AUTHORITY
            or context.attrs.get("clock_limit") != CLOCK_LIMIT
            or context.attrs.get("promotion_eligible") is not False):
        raise ScreenSourceRefusal("UNQUALIFIED_CONTEXT_CONTRACT")
    required = {"feature_session", "trajectory_available", "direction_pair"}
    if not required.issubset(context.columns):
        raise ScreenSourceRefusal("CONTEXT_FIELDS_REQUIRED")
    _boolean(context, ["trajectory_available"])
    rows = []
    for event in frame.to_dict("records"):
        row = dict(event, join_status="DECLARED_DATE_UNAVAILABLE")
        row.update({f"context_{key}": None for key in context.columns})
        value = event["date"]
        if not pd.isna(value):
            try:
                day = pd.Timestamp(value)
                if day.tz is not None or day != day.normalize():
                    raise ValueError("not a day-level session")
                context_dates(pd.DatetimeIndex([day]))
            except ValueError:
                row["join_status"] = "INVALID_DECLARED_SESSION"
            else:
                if day not in context.index:
                    row["join_status"] = "CONTEXT_SESSION_UNAVAILABLE"
                else:
                    features = context.loc[day]
                    row.update({f"context_{key}": val for key, val in features.items()})
                    row["join_status"] = "CONTEXT_WINDOW_INCOMPLETE"
                    if bool(features["trajectory_available"]):
                        position = context.index.get_loc(day)
                        previous = context.index[position - 1] if position else pd.NaT
                        if pd.isna(previous) or features["feature_session"] != previous:
                            raise ScreenSourceRefusal("CONTEXT_NOT_PREVIOUS_EXPECTED_SESSION")
                        row["join_status"] = "JOINED_DATE_PROXY_ONLY"
        rows.append(row)
    result = pd.DataFrame(rows)
    if _ids(result) != _ids(frame) or len(result) != len(frame):
        raise ScreenSourceRefusal("JOIN_CHANGED_EVENT_POPULATION")
    return result


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("UNAVAILABLE").value_counts().sort_index().items()}


def summarize(joined: pd.DataFrame, receipt: dict, receipt_digest: str,
              input_receipts: list[dict]) -> dict:
    primary = joined[joined.primary_analytic]
    grades = []
    for (member, grade), group in joined.groupby(
            ["primary_analytic", "coverage_grade"], dropna=False, sort=True):
        grades.append({"primary_analytic": bool(member), "source_coverage_grade": str(grade),
                       "events": len(group), "join_status_counts": _counts(group.join_status)})
    return {
        "schema": SCHEMA, "authority": "RESEARCH_DIAGNOSTIC_ONLY",
        "promotion_eligible": False, "outcomes_decoded": False,
        "holdout_rows_materialized_in_export": False, "registered_experiment_executed": False,
        "source_manifest_sha256": MANIFEST_SHA256,
        "export_receipt_sha256": receipt_digest, "source_counts": receipt["counts"],
        "preserved_event_id_set_sha256": _ids(joined),
        "context_join_rule": "declared date joins incumbent context already lagged one expected NYSE session",
        "context_inputs": input_receipts,
        "join_status_counts": _counts(joined.join_status),
        "primary_join_status_counts": _counts(primary.join_status),
        "source_grade_breakdown": grades,
        "primary_direction_counts": {
            key: _counts(primary.loc[primary[key], "context_direction_pair"])
            for key in ["ANY", "A4"]},
        "outside_primary_remains_unclassified": int((~joined.primary_analytic).sum()),
        "limitations": LIMITATIONS,
    }


def consume(directory: Path, manifest_path: Path, receipt_digest: str, out: Path) -> dict:
    from scripts.prophet_fusion_cohort_census import DATA_PIN, read_inputs
    from scripts.prophet_fusion_cohort_diagnostics import implied_volatility_trajectory
    from scripts.prophet_fusion_mechanism_study import safe_cache, write_json
    frame, receipt = load_export(directory, manifest_path, receipt_digest)
    grid, levels, inputs = read_inputs(DATA_PIN, str(START.date()), str(END.date()))
    context = implied_volatility_trajectory(levels["vix"], levels["vvix"], grid)
    joined = join_screen_context(frame, context)
    report = summarize(joined, receipt, receipt_digest, inputs)
    out = safe_cache(out)
    joined.to_parquet(out / "joined_metadata.parquet", index=False)
    report["consumer_output"] = {"file": "joined_metadata.parquet",
        "sha256": sha256(out / "joined_metadata.parquet"), "rows": len(joined)}
    write_json(out / "report.json", report)
    lines = ["# Recovered Prophet SCREEN: metadata consumer proof", "",
             "Research diagnostics only. No outcome columns decoded; no post-2019 event rows materialized.", "",
             "| Population | Events |", "| --- | ---: |"]
    for key, value in receipt["counts"].items():
        if isinstance(value, int):
            lines.append(f"| {key} | {value:,} |")
    lines += ["", "## Context join", "", "| Status | Events |", "| --- | ---: |"]
    lines += [f"| {key} | {value:,} |" for key, value in report["join_status_counts"].items()]
    lines += ["", "All original event IDs survive the join. ANY/A4 classify only "
              "the original primary analysis, not prospective eligibility.", "",
              "## Limits", ""] + [f"- {item}" for item in LIMITATIONS]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--source-root", type=Path, required=True)
    extract.add_argument("--manifest", type=Path, required=True)
    extract.add_argument("--out", type=Path, required=True)
    report = sub.add_parser("report")
    report.add_argument("--metadata", type=Path, required=True)
    report.add_argument("--manifest", type=Path, required=True)
    report.add_argument("--receipt-sha256", required=True)
    report.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "extract":
        value = extract_metadata(args.source_root, args.manifest, args.out)
        print(json.dumps({"counts": value["counts"],
                          "receipt_sha256": sha256(args.out / "receipt.json")}, sort_keys=True))
    else:
        sys.path.insert(0, str(_ROOT))
        value = consume(args.metadata, args.manifest, args.receipt_sha256, args.out)
        print(json.dumps({"source_counts": value["source_counts"],
                          "join_status_counts": value["join_status_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
