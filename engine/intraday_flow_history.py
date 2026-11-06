"""Intraday Flow session-history projection.

This module is a read-only projection over the existing canonical
``data/intraday_flow/ledger.parquet`` ledger. It deliberately does not create a
second history store: the parquet ledger remains the authority, while this code
materializes static JSON that a future Intraday Flow history UI can consume.

Legacy ledger rows are always labelled ``partial`` unless the writer explicitly
recorded ``historical_coverage=full``. Missing live/session fields stay null;
this projector never reconstructs an old session from newer market data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

INDEX_SCHEMA = "intraday_flow_history_index.v1"
SESSION_SCHEMA = "intraday_flow_history_session.v1"
SNAPSHOT_SCHEMA = "intraday_flow_snapshot.v1"

_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STANCE_KEYS = (
    "act",
    "get_ready",
    "in_favour",
    "take_profits",
    "watch",
    "stand_aside",
)
OUTCOME_FIELDS = ("fwd_ret_1d", "fwd_ret_5d", "fwd_ret_10d", "fwd_ret_21d")
LEG_FIELDS = (
    "L1_washout_recent",
    "L2_reclaim",
    "L3_rvol_elevated",
    "L4_vol_durable",
    "L5_flow_bid",
    "L6_upturn_organ",
    "L7_leader_quality",
)

# Public replay fields are intentionally allow-listed. The ledger may gain
# internal/research columns later; they do not become user-visible by accident.
PUBLIC_ROW_FIELDS = (
    "session",
    "ticker",
    "built_utc",
    "history_capture_version",
    "historical_coverage",
    "snapshot_utc",
    "stance",
    "reason_en",
    "reason_zh",
    "K",
    *LEG_FIELDS,
    "close",
    "last",
    "change_pct",
    "vwap",
    "vwap_delta_pct",
    "rvol_tod_close",
    "cum_ncp",
    "flow_durability_eod",
    "stop_ref",
    "mtf_upturn_state",
    "mtf_upturn_K",
    "failed_breakout_trap",
    "quote_status",
    "quote_asof",
    "pulse_status",
    "pulse_asof",
    "flow_status",
    "flow_asof",
)


def _json_value(value: Any) -> Any:
    """Convert pandas/numpy scalars into strict JSON-safe Python values."""
    if value is None:
        return None
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False
    if isinstance(missing, bool) and missing:
        return None

    item = getattr(value, "item", None)
    if callable(item) and not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            value = item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _clean_record(row: pd.Series, fields: Iterable[str]) -> dict[str, Any]:
    return {field: _json_value(row.get(field)) for field in fields}


def _session_key(value: Any) -> str:
    value = _json_value(value)
    text = "" if value is None else str(value)[:10]
    if not _SESSION_RE.fullmatch(text):
        raise ValueError(f"invalid Intraday Flow session value: {value!r}")
    return text


def _validate_ledger(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    missing = {"session", "ticker"}.difference(df.columns)
    if missing:
        raise ValueError(
            f"Intraday Flow ledger missing required columns: {sorted(missing)}"
        )

    out = df.copy()
    out["session"] = out["session"].map(_session_key)
    out["ticker"] = out["ticker"].map(
        lambda v: "" if _json_value(v) is None else str(_json_value(v)).upper()
    )
    if (out["ticker"] == "").any():
        raise ValueError("Intraday Flow ledger contains an empty ticker")
    dupes = out.duplicated(subset=["session", "ticker"], keep=False)
    if dupes.any():
        keys = (
            out.loc[dupes, ["session", "ticker"]]
            .astype(str)
            .agg(":".join, axis=1)
            .tolist()
        )
        raise ValueError(
            f"Intraday Flow ledger contains duplicate session/ticker rows: {keys[:5]}"
        )
    return out


def _explicit_coverage(session_df: pd.DataFrame) -> str:
    """Return full only when every row was explicitly captured as full fidelity."""
    if "historical_coverage" not in session_df.columns:
        return "partial"
    vals = {
        str(v).lower()
        for v in session_df["historical_coverage"].tolist()
        if _json_value(v) is not None
    }
    return "full" if vals == {"full"} and len(session_df) > 0 else "partial"


def _lane_counts(session_df: pd.DataFrame) -> dict[str, int]:
    counts = {key: 0 for key in STANCE_KEYS}
    counts["unknown"] = 0
    if "stance" not in session_df.columns:
        counts["unknown"] = int(len(session_df))
        return counts
    for value in session_df["stance"].tolist():
        key = _json_value(value)
        if key in STANCE_KEYS:
            counts[str(key)] += 1
        else:
            counts["unknown"] += 1
    return counts


def _outcome_summary(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    total = int(len(frame))
    for field in OUTCOME_FIELDS:
        if field not in frame.columns:
            values = pd.Series([], dtype="float64")
        else:
            values = pd.to_numeric(frame[field], errors="coerce").dropna()
            values = values[values.map(lambda value: math.isfinite(float(value)))]
        n = int(len(values))
        summary[field] = {
            "n": n,
            "coverage": round(n / total, 6) if total else 0.0,
            "median_return": _json_value(values.median()) if n else None,
            "mean_return": _json_value(values.mean()) if n else None,
            "positive_share": round(float((values > 0).mean()), 6) if n else None,
        }
    return summary


def _evidence_availability(frame: pd.DataFrame) -> dict[str, float]:
    total = int(len(frame))
    out: dict[str, float] = {}
    for field in ("rvol_tod_close", "cum_ncp", "flow_durability_eod"):
        if not total or field not in frame.columns:
            out[field] = 0.0
            continue
        present = sum(_json_value(value) is not None for value in frame[field])
        out[field] = round(present / total, 6)

    if total and "historical_coverage" in frame.columns:
        full = sum(
            str(_json_value(value)).lower() == "full"
            for value in frame["historical_coverage"]
            if _json_value(value) is not None
        )
        out["full_snapshot"] = round(full / total, 6)
    else:
        out["full_snapshot"] = 0.0
    return out


def _internal_scorecard(session_df: pd.DataFrame) -> dict[str, Any]:
    per_stance: dict[str, Any] = {}
    if "stance" in session_df.columns:
        keys = [key for key in STANCE_KEYS if (session_df["stance"] == key).any()]
    else:
        keys = []

    for key in keys:
        subset = session_df[session_df["stance"] == key]
        per_stance[key] = {
            "n": int(len(subset)),
            "forward_outcomes": _outcome_summary(subset),
        }

    return {
        "n_rows": int(len(session_df)),
        "evidence_availability": _evidence_availability(session_df),
        "forward_outcomes": _outcome_summary(session_df),
        "per_stance": per_stance,
        "not_available_yet": {
            "intraday_stance_transitions": (
                "requires multiple preserved within-session snapshots"
            ),
            "almost_ready_to_buy_now_conversion": (
                "requires preserved within-session stance transitions"
            ),
            "stop_breach_rate": (
                "requires preserved stop reference plus forward session extrema"
            ),
        },
    }


def _public_row(row: pd.Series) -> dict[str, Any]:
    raw = _clean_record(row, PUBLIC_ROW_FIELDS)
    outcomes = _clean_record(row, OUTCOME_FIELDS)
    row_coverage = (
        "full" if str(raw["historical_coverage"]).lower() == "full" else "partial"
    )
    return {
        "ticker": raw["ticker"],
        "session": raw["session"],
        "built_utc": raw["built_utc"],
        "history_capture_version": raw["history_capture_version"],
        "historical_coverage": row_coverage,
        "snapshot_utc": raw["snapshot_utc"],
        "stance": raw["stance"],
        "reason": {"en": raw["reason_en"], "zh": raw["reason_zh"]},
        "confluence": {
            "K": raw["K"],
            **{field: raw[field] for field in LEG_FIELDS},
        },
        "market": {
            "close": raw["close"],
            "last": raw["last"],
            "change_pct": raw["change_pct"],
            "vwap": raw["vwap"],
            "vwap_delta_pct": raw["vwap_delta_pct"],
            "rvol_tod_close": raw["rvol_tod_close"],
            "cum_ncp": raw["cum_ncp"],
            "flow_durability_eod": raw["flow_durability_eod"],
            "stop_ref": raw["stop_ref"],
        },
        "context": {
            "mtf_upturn_state": raw["mtf_upturn_state"],
            "mtf_upturn_K": raw["mtf_upturn_K"],
            "failed_breakout_trap": raw["failed_breakout_trap"],
        },
        "feeds": {
            "quotes": {"status": raw["quote_status"], "as_of": raw["quote_asof"]},
            "pulse": {"status": raw["pulse_status"], "as_of": raw["pulse_asof"]},
            "options_flow": {
                "status": raw["flow_status"],
                "as_of": raw["flow_asof"],
            },
        },
        "outcomes": outcomes,
    }


def _snapshot_fingerprint(leaders: list[dict[str, Any]]) -> str:
    """Fingerprint only what the board said, excluding later-maturing outcomes."""
    snapshot_rows = [
        {key: value for key, value in row.items() if key != "outcomes"}
        for row in leaders
    ]
    raw = json.dumps(
        snapshot_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_session_payload(ledger: pd.DataFrame, session: str) -> dict[str, Any]:
    df = _validate_ledger(ledger)
    session = _session_key(session)
    session_df = (
        df[df["session"] == session].copy().sort_values("ticker", kind="stable")
    )
    if session_df.empty:
        raise KeyError(f"Intraday Flow session not found: {session}")

    leaders = [_public_row(row) for _, row in session_df.iterrows()]
    coverage = _explicit_coverage(session_df)
    return {
        "schema": SESSION_SCHEMA,
        "snapshot_schema": SNAPSHOT_SCHEMA,
        "session": session,
        "historical_coverage": coverage,
        "n_leaders": int(len(leaders)),
        "lane_counts": _lane_counts(session_df),
        "snapshot_sha256": _snapshot_fingerprint(leaders),
        "leaders": leaders,
        "internal_scorecard": _internal_scorecard(session_df),
    }


def build_index_payload(ledger: pd.DataFrame) -> dict[str, Any]:
    df = _validate_ledger(ledger)
    sessions: list[dict[str, Any]] = []
    if not df.empty:
        for session in sorted(df["session"].unique().tolist(), reverse=True):
            payload = build_session_payload(df, session)
            sessions.append(
                {
                    "session": session,
                    "historical_coverage": payload["historical_coverage"],
                    "n_leaders": payload["n_leaders"],
                    "lane_counts": payload["lane_counts"],
                    "snapshot_sha256": payload["snapshot_sha256"],
                    "evidence_availability": payload["internal_scorecard"][
                        "evidence_availability"
                    ],
                }
            )
    return {
        "schema": INDEX_SCHEMA,
        "n_sessions": len(sessions),
        "newest_session": sessions[0]["session"] if sessions else None,
        "oldest_session": sessions[-1]["session"] if sessions else None,
        "sessions": sessions,
    }


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )
    fd, tmp = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def publish_history(ledger: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    """Materialize deterministic per-session JSON plus index from a ledger frame."""
    df = _validate_ledger(ledger)
    out_dir = Path(out_dir)
    index = build_index_payload(df)
    for entry in index["sessions"]:
        session = entry["session"]
        _atomic_json_write(
            out_dir / f"{session}.json",
            build_session_payload(df, session),
        )
    _atomic_json_write(out_dir / "index.json", index)
    return {
        "n_sessions": index["n_sessions"],
        "newest_session": index["newest_session"],
        "out_dir": str(out_dir),
    }


def load_and_publish(ledger_path: Path, out_dir: Path) -> dict[str, Any]:
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        raise FileNotFoundError(f"Intraday Flow ledger not found: {ledger_path}")
    ledger = pd.read_parquet(ledger_path)
    return publish_history(ledger, out_dir)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Publish Intraday Flow session-history JSON from the canonical ledger"
        )
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("data/intraday_flow/ledger.parquet"),
    )
    parser.add_argument("--site-root", type=Path, default=Path("site"))
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    out_dir = args.out_dir or (args.site_root / "flowtracker" / "history")
    result = load_and_publish(args.ledger, out_dir)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
