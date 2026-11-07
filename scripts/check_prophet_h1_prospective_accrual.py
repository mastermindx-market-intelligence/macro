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
import os
import stat
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
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
    "identity_spec_schema", "identity_spec_hash",
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


IDENTITY_STATES = frozenset({
    "RESOLVED", "SECURITY_UNRESOLVED", "ISSUER_UNRESOLVED",
    "INVALID_DECISION_DATE", "IDENTITY_UNAVAILABLE", "SOURCE_UNAVAILABLE",
})
GROUP_STATES = frozenset({
    "SOURCE_UNAVAILABLE", "NO_ACTIVE_MEMBERSHIP", "AMBIGUOUS_OVERLAP",
    "UNSUPPORTED_WEIGHTING", "MEMBERSHIP_ROSTER_INCOHERENT",
    "SOLE_ACTIVE_MEMBERSHIP",
})
IDENTITY_BINDING_FIELDS = (
    "security_id", "issuer_id", "identity_epoch", "identity_epoch_state",
    "identity_spec_schema", "identity_spec_hash",
)
SOLE_GROUP_FIELDS = (
    "theme_capture_group_id", "theme_capture_group_weighting",
    "theme_capture_member_tickers", "theme_capture_member_set_sha256",
)


class _SourceIntegrityError(ValueError):
    pass


def _stat_identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
    )


def _read_canonical_part(store: Path, part: Path) -> bytes:
    """Read one regular single-link part through a no-follow directory handle."""
    store_fd = part_fd = -1
    try:
        store_fd = os.open(
            store,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
        )
        store_before = os.fstat(store_fd)
        if not stat.S_ISDIR(store_before.st_mode):
            raise _SourceIntegrityError("candidate store is not a real directory")
        part_fd = os.open(
            part.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0),
            dir_fd=store_fd,
        )
        part_before = os.fstat(part_fd)
        if not stat.S_ISREG(part_before.st_mode) or part_before.st_nlink != 1:
            raise _SourceIntegrityError("candidate part is not a regular single-link file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(part_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        part_after = os.fstat(part_fd)
        store_after = os.fstat(store_fd)
        named_store = store.lstat()
        named_part = part.lstat()
        if (
            _stat_identity(store_before) != _stat_identity(store_after)
            or store_before.st_dev != named_store.st_dev
            or store_before.st_ino != named_store.st_ino
            or not stat.S_ISDIR(named_store.st_mode)
            or stat.S_ISLNK(named_store.st_mode)
            or _stat_identity(part_before) != _stat_identity(part_after)
            or _stat_identity(part_after) != _stat_identity(named_part)
            or not stat.S_ISREG(named_part.st_mode)
            or stat.S_ISLNK(named_part.st_mode)
            or named_part.st_nlink != 1
        ):
            raise _SourceIntegrityError("candidate source identity changed while reading")
        raw = b"".join(chunks)
        if len(raw) != part_before.st_size:
            raise _SourceIntegrityError("candidate source size changed while reading")
        return raw
    except (OSError, ValueError) as exc:
        if isinstance(exc, _SourceIntegrityError):
            raise
        raise _SourceIntegrityError("candidate source cannot be opened safely") from exc
    finally:
        if part_fd >= 0:
            os.close(part_fd)
        if store_fd >= 0:
            os.close(store_fd)


def _schema_paths(schema: pa.Schema) -> list[tuple[str, ...]]:
    paths: list[tuple[str, ...]] = []
    def visit(field: pa.Field, prefix: tuple[str, ...]) -> None:
        here = prefix + (field.name,)
        paths.append(here)
        dtype = field.type
        for index in range(getattr(dtype, "num_fields", 0)):
            visit(dtype.field(index), here)
    for field in schema:
        visit(field, ())
    return paths


def _forbidden_schema_paths(schema: pa.Schema) -> list[str]:
    return sorted({
        ".".join(path)
        for path in _schema_paths(schema)
        if any(component in FORBIDDEN for component in path)
    })


def _native_key_schema_is_text(schema: pa.Schema) -> bool:
    fields = {field.name: field.type for field in schema}
    return all(
        name in fields and (pa.types.is_string(fields[name]) or pa.types.is_large_string(fields[name]))
        for name in KEY
    )


def _all_present(row: pd.Series, fields: tuple[str, ...]) -> bool:
    return all(pd.notna(row.get(field)) and isinstance(row.get(field), str)
               and bool(row.get(field).strip()) for field in fields)


def _all_absent(row: pd.Series, fields: tuple[str, ...]) -> bool:
    return all(pd.isna(row.get(field)) or row.get(field) is None for field in fields)


def _identity_row_valid(row: pd.Series) -> bool:
    state = row.get("identity_capture_state")
    if not isinstance(state, str) or state not in IDENTITY_STATES:
        return False
    security = ("security_id", "identity_epoch", "identity_epoch_state",
                "identity_spec_schema", "identity_spec_hash")
    if state == "RESOLVED":
        return _all_present(row, IDENTITY_BINDING_FIELDS) and _all_present(
            row, ("identity_capture_basis",)
        )
    if state == "SECURITY_UNRESOLVED":
        return _all_absent(row, IDENTITY_BINDING_FIELDS)
    if state == "ISSUER_UNRESOLVED":
        return _all_present(row, security) and pd.isna(row.get("issuer_id"))
    if state == "INVALID_DECISION_DATE":
        return False
    # Explicit owner/source unavailable states carry no invented identity facts.
    return _all_absent(row, IDENTITY_BINDING_FIELDS + ("identity_capture_basis",))


def _canonical_pipe_members(value: Any) -> list[str] | None:
    """Check the native owner's sorted, unique, pipe-delimited representation."""
    if pd.isna(value):
        return []
    if not isinstance(value, str):
        return None
    members = value.split("|")
    if (any(not member or member != member.strip() for member in members)
            or members != sorted(set(members))):
        return None
    return members


def _group_row_valid(row: pd.Series) -> bool:
    state = row.get("theme_capture_group_state")
    if not isinstance(state, str) or state not in GROUP_STATES:
        return False
    if state != "SOLE_ACTIVE_MEMBERSHIP" and not _all_absent(row, SOLE_GROUP_FIELDS):
        return False
    if state == "SOURCE_UNAVAILABLE":
        return pd.isna(row.get("theme_membership_source_sha256"))
    if (not _all_present(row, ("theme_membership_source_sha256",
                              "theme_capture_group_rule", "theme_membership_basis"))
            or row.get("theme_capture_group_rule") != ucv.CAPTURE_GROUP_RULE
            or row.get("theme_membership_basis") != ucv.MEMBERSHIP_BASIS):
        return False
    memberships = _canonical_pipe_members(row.get("theme_membership_ids"))
    if memberships is None or any(
        member.startswith(ucv.THEME_ID_EXCLUDE_PREFIX) for member in memberships
    ):
        return False
    if state == "NO_ACTIVE_MEMBERSHIP":
        return not memberships
    if state == "AMBIGUOUS_OVERLAP":
        return len(memberships) > 1
    if len(memberships) != 1:
        return False
    if state != "SOLE_ACTIVE_MEMBERSHIP":
        return True  # One group was present, but its weighting/roster was unavailable.
    if (not _all_present(row, SOLE_GROUP_FIELDS)
            or row.get("theme_capture_group_weighting") != "equal"
            or row.get("theme_capture_group_id") != memberships[0]):
        return False
    members = _canonical_pipe_members(row.get("theme_capture_member_tickers"))
    if not members or row.get("ticker") not in members:
        return False
    # Verify the existing owner's receipt over its captured roster. This does
    # not select peers, resolve today's membership, or add a second group owner.
    expected = "sha256:" + hashlib.sha256(
        json.dumps(members, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return row.get("theme_capture_member_set_sha256") == expected


def _duplicate_keys(rows: pd.DataFrame) -> list[dict[str, Any]]:
    duplicate = rows[rows.duplicated(list(KEY), keep=False)]
    if duplicate.empty:
        return []
    return [
        dict(zip(KEY, map(str, key if isinstance(key, tuple) else (key,)), strict=True))
        for key in duplicate.groupby(list(KEY), dropna=False, sort=True).groups
    ]


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
    try:
        store_info = store.lstat()
    except FileNotFoundError:
        return {**base, "status": STATUS_CAPTURE_NOT_STARTED,
                "reason": "CANDIDATE_STORE_ABSENT"}
    except OSError:
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_STORE_NOT_CANONICAL"}
    if stat.S_ISLNK(store_info.st_mode) or not stat.S_ISDIR(store_info.st_mode):
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_STORE_NOT_CANONICAL"}
    try:
        part_info = part.lstat()
    except FileNotFoundError:
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "EXPECTED_MONTH_PART_ABSENT"}
    except OSError:
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_PART_NOT_CANONICAL"}
    if (stat.S_ISLNK(part_info.st_mode) or not stat.S_ISREG(part_info.st_mode)
            or part_info.st_nlink != 1):
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_PART_NOT_CANONICAL"}

    raw: bytes | None = None
    try:
        raw = _read_canonical_part(store, part)
        source_receipt = _receipt(part, raw)
        physical_schema = pq.ParquetFile(BytesIO(raw)).schema_arrow
        physical_columns = frozenset(physical_schema.names)
    except (_SourceIntegrityError, OSError, ValueError):
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "CANDIDATE_PART_UNREADABLE",
                "source_receipt": _receipt(part, raw) if raw is not None else None}
    forbidden_paths = _forbidden_schema_paths(physical_schema)
    if forbidden_paths:
        return {**base, "outcome_redacted": False,
                "status": STATUS_SOURCE_CONFLICT,
                "reason": "FORBIDDEN_OUTCOME_COLUMNS_PRESENT",
                "source_receipt": source_receipt,
                "forbidden_schema_paths": forbidden_paths}
    missing_schema = sorted(PROSPECTIVE_SCHEMA_WITNESS - physical_columns)
    if missing_schema:
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "PROSPECTIVE_SCHEMA_NOT_PRESENT",
                "source_receipt": source_receipt,
                "missing_required_columns": missing_schema}
    if not _native_key_schema_is_text(physical_schema):
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "INVALID_NATIVE_KEY_SCHEMA",
                "source_receipt": source_receipt}

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
        (frame["stamp_date"] == expected_session)
        & (frame["board_definition"] == board_definition)
    ].copy()
    if rows.empty:
        return {**base, "status": STATUS_CANDIDATE_CAPTURE_DARK,
                "reason": "NO_ROWS_FOR_EXPECTED_SESSION_AND_DEFINITION",
                "source_receipt": source_receipt, "month_rows": int(len(frame))}

    invalid_keys = pd.Series(False, index=rows.index)
    for column in KEY:
        invalid_keys |= ~rows[column].map(
            lambda value: isinstance(value, str) and bool(value.strip())
        )
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

    duplicates = _duplicate_keys(rows)
    if duplicates:
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "DUPLICATE_NATIVE_KEYS", "source_receipt": source_receipt,
                "rows": int(len(rows)), "duplicate_keys": duplicates}

    invalid_identity = ~rows.apply(_identity_row_valid, axis=1)
    if invalid_identity.any():
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "INVALID_IDENTITY_CAPTURE_STATE",
                "source_receipt": source_receipt, "rows": int(len(rows)),
                "invalid_identity_rows": int(invalid_identity.sum())}
    invalid_group = ~rows.apply(_group_row_valid, axis=1)
    if invalid_group.any():
        return {**base, "status": STATUS_SOURCE_CONFLICT,
                "reason": "INVALID_GROUP_CAPTURE_STATE",
                "source_receipt": source_receipt, "rows": int(len(rows)),
                "invalid_group_rows": int(invalid_group.sum())}

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
