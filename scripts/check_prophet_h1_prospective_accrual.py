#!/usr/bin/env python3
"""Pre-outcome Prophet H1 prospective-accrual verifier.

This tool verifies whether a specific ordinary US nightly candidate/context capture
exists and reports only source/coverage metadata.  It never reads the forward-grade
store, model outputs, return fields, rankings after fitting, or trade outcomes.

It is intentionally not an evaluator or admission authority.  A successful S0
receipt proves candidate capture exists; it does not admit H1, establish price
rights, or prove future label maturity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from engine import us_context_vector as ucv

STATUS_CAPTURE_NOT_STARTED = "CAPTURE_NOT_STARTED"
STATUS_CANDIDATE_CAPTURE_DARK = "CANDIDATE_CAPTURE_DARK"
STATUS_SOURCE_CONFLICT = "SOURCE_CONFLICT"
STATUS_S0_CAPTURE_PRESENT = "S0_CAPTURE_PRESENT"

KEY = tuple(ucv.DEDUPE_KEY)
READ_COLUMNS = (
    "stamp_date", "ticker", "board_definition", "lane",
    "security_id", "issuer_id", "identity_epoch", "identity_epoch_state",
    "identity_capture_state", "identity_capture_basis",
    "identity_alias_source_sha256", "identity_master_source_sha256",
    "cycle_state", "cycle_label", "cycle_label_vocab_sha256",
    "theme_membership_ids", "theme_membership_source_sha256",
    "theme_membership_source_version", "theme_membership_source_curated",
    "theme_membership_basis", "theme_capture_group_id",
    "theme_capture_group_state", "theme_capture_group_rule",
    "theme_capture_group_weighting", "theme_capture_member_tickers",
    "theme_capture_member_set_sha256", "context_dims",
)
FORBIDDEN = {
    "entry_price", "fwd_ret", "bench_ret", "excess_spy", "fwd_mfe", "fwd_mdd",
    "predicted_return", "score_after_fit", "rank_after_fit",
}
assert not (set(READ_COLUMNS) & FORBIDDEN)

# S0 is a *prospective Context Vector* capture, not merely any historical
# candidate row.  These physical Parquet columns are the minimum schema witness
# that #8091's prospective capture contract has actually reached the monthly
# store.  Row values may still be null/typed unavailable; absence of the columns
# themselves means this is a legacy pre-contract part and cannot start S0.
PROSPECTIVE_SCHEMA_WITNESS = frozenset({
    "security_id", "issuer_id", "identity_epoch", "identity_capture_state",
    "cycle_state", "cycle_label", "cycle_label_vocab_sha256",
    "theme_membership_source_sha256", "theme_capture_group_state",
    "theme_capture_group_weighting", "theme_capture_member_set_sha256",
    *KEY,
})
# Every new producer row stamps these even when source facts are unavailable.
# Schema union alone can add columns to old rows but cannot supply these values.
PROSPECTIVE_ROW_WITNESS = ("identity_capture_state", "theme_capture_group_state")


def _present(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype("string").str.strip().fillna("").ne("")


def _ratio(mask: pd.Series, total: int) -> float | None:
    return None if total == 0 else float(mask.sum()) / float(total)


def _part_path(expected_session: str, root: Path | None) -> Path:
    # The storage layout is owned by us_context_vector.  Use its owner helper so this
    # verifier cannot silently invent another candidate-store location.
    return Path(ucv._part_path(expected_session, root))  # noqa: SLF001


def _receipt(path: Path, raw: bytes) -> dict[str, Any]:
    return {
        "relative_part": f"candidates/{path.name}",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def _conflicting_keys(rows: pd.DataFrame) -> list[dict[str, Any]]:
    if rows.empty:
        return []
    conflicts: list[dict[str, Any]] = []
    duplicate = rows[rows.duplicated(list(KEY), keep=False)]
    if duplicate.empty:
        return conflicts
    for key, group in duplicate.groupby(list(KEY), dropna=False, sort=True):
        normalized = group.astype("string").fillna("<NA>").drop_duplicates()
        if len(normalized) > 1:
            values = key if isinstance(key, tuple) else (key,)
            conflicts.append(dict(zip(KEY, map(str, values), strict=True)))
    return conflicts


def _cycle_pair_mismatch(rows: pd.DataFrame) -> int:
    state = _present(rows["cycle_state"])
    label = _present(rows["cycle_label"])
    return int((state ^ label).sum())


def inspect(*, expected_session: str, board_definition: str,
            root: Path | None = None) -> dict[str, Any]:
    if (not isinstance(expected_session, str) or len(expected_session) != 10
            or date.fromisoformat(expected_session).isoformat() != expected_session):
        raise ValueError("expected_session must be a valid YYYY-MM-DD date")
    if not isinstance(board_definition, str) or not board_definition.strip():
        raise ValueError("board_definition must be nonempty text")
    month = expected_session[:7]
    part = _part_path(expected_session, root)
    base = {
        "schema": "mastermind.prophet.h1.prospective_accrual.v1",
        "expected_session": expected_session,
        "board_definition": board_definition,
        "outcome_redacted": True,
        "h1_admitted": False,
        "model_fit_executed": False,
    }
    store = part.parent
    if not store.is_dir():
        return {**base, "status": STATUS_CAPTURE_NOT_STARTED,
                "reason": "CANDIDATE_STORE_ABSENT"}
    if not part.is_file():
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "EXPECTED_MONTH_PART_ABSENT"}

    raw: bytes | None = None
    try:
        raw = part.read_bytes()
        source_receipt = _receipt(part, raw)
        physical_columns = frozenset(pq.ParquetFile(BytesIO(raw)).schema_arrow.names)
    except (OSError, ValueError):
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_PART_UNREADABLE",
                "source_receipt": _receipt(part, raw) if raw is not None else None}
    missing_schema = sorted(PROSPECTIVE_SCHEMA_WITNESS - physical_columns)
    if missing_schema:
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "PROSPECTIVE_SCHEMA_NOT_PRESENT",
                "source_receipt": source_receipt,
                "missing_required_columns": missing_schema}

    try:
        frame = ucv.load_candidates(root, months=[month], columns=READ_COLUMNS,
                                    snapshot_parts={month: raw})
    except (OSError, ValueError, TypeError):
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_PART_UNREADABLE", "source_receipt": source_receipt}
    if frame.empty:
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "MONTH_PART_HAS_NO_READABLE_ROWS", "source_receipt": source_receipt}

    rows = frame[
        (frame["stamp_date"].astype("string") == expected_session)
        & (frame["board_definition"].astype("string") == board_definition)
    ].copy()
    if rows.empty:
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "NO_ROWS_FOR_EXPECTED_SESSION_AND_DEFINITION",
                "source_receipt": source_receipt, "month_rows": int(len(frame))}

    invalid_keys = ~_present(rows["ticker"])
    if invalid_keys.any():
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "INVALID_NATIVE_KEYS", "source_receipt": source_receipt,
                "rows": int(len(rows)), "invalid_key_rows": int(invalid_keys.sum())}
    row_witness = pd.Series(True, index=rows.index)
    for column in PROSPECTIVE_ROW_WITNESS:
        row_witness &= _present(rows[column])
    if not row_witness.all():
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "PROSPECTIVE_ROW_WITNESS_NOT_PRESENT",
                "source_receipt": source_receipt, "rows": int(len(rows)),
                "rows_missing_prospective_witness": int((~row_witness).sum())}

    conflicts = _conflicting_keys(rows)
    if conflicts:
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CONFLICTING_NATIVE_KEYS", "source_receipt": source_receipt,
                "rows": int(len(rows)), "conflicting_keys": conflicts}

    n = int(len(rows))
    identity = _present(rows["security_id"]) & _present(rows["issuer_id"]) & _present(rows["identity_epoch"])
    membership_receipt = _present(rows["theme_membership_source_sha256"])
    sole_group = (
        rows["theme_capture_group_state"].astype("string").eq("SOLE_ACTIVE_MEMBERSHIP")
        & _present(rows["theme_capture_group_id"])
        & rows["theme_capture_group_weighting"].astype("string").eq("equal")
        & _present(rows["theme_capture_member_set_sha256"])
    )
    context = _present(rows["context_dims"])
    cycle_mismatch = _cycle_pair_mismatch(rows)

    return {
        **base,
        "status": STATUS_S0_CAPTURE_PRESENT,
        "reason": "NONEMPTY_NATIVE_CANDIDATE_CAPTURE",
        "source_receipt": source_receipt,
        "rows": n,
        "unique_tickers": int(rows["ticker"].astype("string").nunique()),
        "duplicate_key_rows": int(rows.duplicated(list(KEY), keep=False).sum()),
        "cycle_pair_mismatch_rows": cycle_mismatch,
        "coverage": {
            "identity_resolved": _ratio(identity, n),
            "membership_source_receipt": _ratio(membership_receipt, n),
            "sole_supported_peer_group": _ratio(sole_group, n),
            "context_dims_present": _ratio(context, n),
        },
        "source_states": {
            "identity_capture_state": rows["identity_capture_state"].astype("string").fillna("<NA>").value_counts().sort_index().to_dict(),
            "group_state": rows["theme_capture_group_state"].astype("string").fillna("<NA>").value_counts().sort_index().to_dict(),
        },
        "claim_limit": (
            "Candidate/context capture only. Does not establish H1 source eligibility, "
            "grade maturity, price rights, selected-outcome completeness, or trading authority."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-session", required=True)
    parser.add_argument("--board-definition", required=True)
    parser.add_argument("--root", type=Path, default=None,
                        help="Repository/runtime root whose data/ directory contains the candidate store")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    result = inspect(expected_session=args.expected_session,
                     board_definition=args.board_definition, root=args.root)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == STATUS_S0_CAPTURE_PRESENT else 2


if __name__ == "__main__":
    raise SystemExit(main())
