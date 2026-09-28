#!/usr/bin/env python3
"""Qualify a GD-6A shadow sidecar from exact owner-selected files; stdout only.

No default source paths, publication, scheduler, forward ledger or live switch.
Expected hashes, session and cutoff are independent owner inputs. In production,
reuse build_prophet's frozen source-board receipt rather than read a racing board
again. This CLI is a qualification entry point, not a registered nightly writer.
"""
from __future__ import annotations

import argparse
import gzip
import io
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Mapping
import json
import os
import stat
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from engine.prophet_market_eligibility import (  # noqa: E402
    MAX_INPUT_BYTES, MarketEligibilityError, compose_market_eligibility,
    bind_shadow_view, _exact, _load, _utc, _hash,
)


def _read(path: Path) -> bytes:
    # A path check alone races the open. Bind admission to the actual opened
    # descriptor, and never wait on FIFOs/devices masquerading as source files.
    if path.is_symlink():
        raise MarketEligibilityError("SYMLINKED_SOURCE_REFUSED")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise MarketEligibilityError("SOURCE_DESCRIPTOR_GUARD_UNAVAILABLE")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise MarketEligibilityError("SOURCE_NOT_REGULAR_FILE")
        if info.st_size > MAX_INPUT_BYTES:
            raise MarketEligibilityError("SOURCE_SIZE_LIMIT")
        # fdopen owns the descriptor after successful construction. No path reread.
        handle = os.fdopen(fd, "rb")
        fd = None
        with handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
    finally:
        if fd is not None:
            os.close(fd)
    if len(raw) > MAX_INPUT_BYTES:
        raise MarketEligibilityError("SOURCE_SIZE_LIMIT")
    return raw



def _frozen_raw(snapshot: Path, expected_sha256: str) -> bytes:
    """Read the existing content-addressed gzip, with a bounded decompression."""
    with gzip.GzipFile(fileobj=io.BytesIO(_read(snapshot))) as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES or sha256(raw).hexdigest() != expected_sha256:
        raise MarketEligibilityError("FROZEN_SOURCE_HASH_OR_SIZE_MISMATCH")
    return raw


def _publication_window(observed_at: datetime) -> tuple[datetime, str, datetime]:
    """One native EOD clock interpretation shared by producer and read consumer."""
    from lib.nyse_calendar import (
        expected_last_session, session_n_forward, ET, _CLOSE_PLUS_SETTLE,
    )
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
        raise MarketEligibilityError("NAIVE_PUBLICATION_CLOCK")
    now = observed_at.astimezone(timezone.utc)
    source_day = expected_last_session(now)
    next_session = session_n_forward(source_day, 1)
    if next_session is None:
        raise MarketEligibilityError("SOURCE_ROLLOVER_UNAVAILABLE")
    if isinstance(next_session, str):
        from datetime import date
        next_session = date.fromisoformat(next_session)
    cutoff = datetime.combine(next_session, _CLOSE_PLUS_SETTLE, tzinfo=ET).astimezone(timezone.utc)
    return now, source_day.isoformat(), cutoff


def _index_board(index: Mapping[str, Any], ledger_dir: Path) -> tuple[bytes, str, str, dict[str, Any]]:
    """Resolve only the canonical hash-derived immutable source, never latest."""
    repo = ledger_dir.parents[1]
    digest = _hash(index.get("source_board_sha256"), "INDEX_BOARD_HASH_INVALID")
    snapshot = ledger_dir / "origination_sources" / (digest + ".json.gz")
    relative = snapshot.relative_to(repo).as_posix()
    if (index.get("source_board_snapshot_path") != relative
            or index.get("source_board_snapshot_encoding") != "gzip"):
        raise MarketEligibilityError("INDEX_BOARD_SNAPSHOT_MISMATCH")
    raw = _frozen_raw(snapshot, digest)
    board = _load(raw, "BOARD_UNREADABLE")
    staleness = board.get("staleness")
    through = staleness.get("price_through") if isinstance(staleness, dict) else None
    if (index.get("source_asof") != through
            or index.get("source_board_asof") != board.get("as_of")):
        raise MarketEligibilityError("INDEX_BOARD_CLOCK_MISMATCH")
    return raw, digest, relative, board


def _publication_receipt(sidecar: Mapping[str, Any], board_snapshot: str,
                         envelope_snapshot: str | None) -> dict[str, Any]:
    """Single receipt shape; no independent authority or duplicated policy logic."""
    return {
        "schema": sidecar["schema"], "mode": "SHADOW_ONLY",
        "production_behavior": "UNCHANGED", "file": "market_eligibility.json",
        "sidecar_id": sidecar["sidecar_id"], "source_state": sidecar["source_state"],
        "source_board_sha256": sidecar["board"]["sha256"],
        "source_board_snapshot_path": board_snapshot,
        "risk_envelope_sha256": sidecar["risk_envelope"]["sha256"],
        "risk_envelope_snapshot_path": envelope_snapshot,
        "risk_source_read": "SNAPSHOT_READ" if envelope_snapshot is not None else "UNAVAILABLE",
        "decision_at": sidecar["decision_at"], "valid_until": sidecar["valid_until"],
        "validity_basis": "NATIVE_EXPECTED_LAST_SESSION_ROLLOVER",
        "row_count": len(sidecar["rows"]), "errors": list(sidecar["errors"]),
    }


def prepare_publication_shadow(
    index: Mapping[str, Any], *, ledger_dir: Path, risk_envelope_path: Path,
    observed_at: datetime,
    freeze_source: Callable[[Path], tuple[dict[str, Any], str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prepare the existing builder's non-activating sidecar and index receipt.

    No mutable-board reread, source collection, own calendar, or direct publication.
    The builder supplies its exact frozen board and its existing JSON snapshot helper.
    The native completed-session owner fixes the session and the next rollover.
    The returned receipt becomes visible only alongside a successfully written artifact.
    """
    now, session, cutoff = _publication_window(observed_at)
    raw_board, digest, relative, board = _index_board(index, ledger_dir)
    repo = ledger_dir.parents[1]
    envelope_raw = None
    envelope_digest = None
    envelope_snapshot = None
    try:
        _, envelope_digest, envelope_snapshot = freeze_source(risk_envelope_path)
        frozen = ledger_dir / "origination_sources" / (envelope_digest + ".json.gz")
        if frozen.relative_to(repo).as_posix() != envelope_snapshot:
            raise MarketEligibilityError("ENVELOPE_SNAPSHOT_PATH_MISMATCH")
        envelope_raw = _frozen_raw(frozen, envelope_digest)
    except (OSError, RuntimeError, ValueError, EOFError):
        # This names an unavailable read, not an observed empty/zero-policy source.
        envelope_raw, envelope_digest, envelope_snapshot = None, None, None
    decision = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    expiry = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
    sidecar = compose_market_eligibility(
        raw_board, envelope_raw, expected_board_sha256=digest,
        expected_board_definition=board.get("board_definition"),
        expected_source_session=session, expected_envelope_sha256=envelope_digest,
        decision_at=decision, valid_until=expiry,
    )
    receipt = _publication_receipt(sidecar, relative, envelope_snapshot)
    return sidecar, receipt


def read_publication_shadow(
    index: Mapping[str, Any], *, ledger_dir: Path, index_dir: Path,
    read_at: datetime,
) -> dict[str, Any] | None:
    """Read the exact published assessment without rereading mutable source files.

    A legacy index with no new receipt, or an honest artifact-write failure,
    returns None and NEVER opens an old sidecar. A WRITTEN unavailable assessment
    still returns the full research view. Claimed artifacts must pass exact raw
    hashes, source snapshots, native calendar window and complete recomposition.
    No network, registry mutation, source snapshot creation or live action occurs.
    """
    if not isinstance(index, Mapping):
        raise MarketEligibilityError("INDEX_NOT_OBJECT")
    if "market_eligibility_shadow" not in index:
        return None
    receipt = index["market_eligibility_shadow"]
    if not isinstance(receipt, dict):
        raise MarketEligibilityError("PUBLICATION_RECEIPT_NOT_OBJECT")
    if receipt.get("artifact_status") == "UNAVAILABLE":
        expected = {
            "mode": "SHADOW_ONLY", "production_behavior": "UNCHANGED",
            "source_state": "UNAVAILABLE", "artifact_status": "UNAVAILABLE",
            "file": None, "error_type": receipt.get("error_type"),
        }
        error_type = receipt.get("error_type")
        if (not _exact(receipt, expected) or not isinstance(error_type, str)
                or not error_type.isidentifier() or len(error_type) > 128):
            raise MarketEligibilityError("PUBLICATION_UNAVAILABLE_RECEIPT_INVALID")
        return None
    if receipt.get("artifact_status") != "WRITTEN" or receipt.get("file") != "market_eligibility.json":
        raise MarketEligibilityError("PUBLICATION_ARTIFACT_REFERENCE_INVALID")
    # The index/path roots are supplied by the existing server/source owner.
    # Input JSON cannot select a path or create an identity through its strings.
    decision = _utc(receipt.get("decision_at"), "PUBLICATION_DECISION_INVALID")
    _, session, cutoff = _publication_window(decision)
    expiry = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
    if receipt.get("valid_until") != expiry:
        raise MarketEligibilityError("PUBLICATION_WINDOW_MISMATCH")
    if not isinstance(read_at, datetime) or read_at.tzinfo is None:
        raise MarketEligibilityError("NAIVE_READ_CLOCK")
    read_clock = read_at.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    try:
        raw_sidecar = _read(index_dir / "market_eligibility.json")
        actual_sha = sha256(raw_sidecar).hexdigest()
        if _hash(receipt.get("sha256"), "PUBLICATION_HASH_INVALID") != actual_sha:
            raise MarketEligibilityError("PUBLICATION_ARTIFACT_HASH_MISMATCH")
        sidecar = _load(raw_sidecar, "PUBLICATION_ARTIFACT_UNREADABLE")
        raw_board, board_hash, board_ref, board = _index_board(index, ledger_dir)
        raw_risk = None
        risk_hash = receipt.get("risk_envelope_sha256")
        risk_ref = receipt.get("risk_envelope_snapshot_path")
        if risk_hash is None:
            if risk_ref is not None:
                raise MarketEligibilityError("PUBLICATION_RISK_REFERENCE_INVALID")
        else:
            risk_hash = _hash(risk_hash, "PUBLICATION_RISK_HASH_INVALID")
            path = ledger_dir / "origination_sources" / (risk_hash + ".json.gz")
            if risk_ref != path.relative_to(ledger_dir.parents[1]).as_posix():
                raise MarketEligibilityError("PUBLICATION_RISK_REFERENCE_INVALID")
            raw_risk = _frozen_raw(path, risk_hash)
        view = bind_shadow_view(
            sidecar, raw_board, raw_risk,
            expected_board_sha256=board_hash,
            expected_board_definition=board.get("board_definition"),
            expected_source_session=session, expected_envelope_sha256=risk_hash,
            expected_decision_at=receipt["decision_at"], expected_valid_until=expiry,
            read_at=read_clock,
        )
        expected = _publication_receipt(sidecar, board_ref, risk_ref)
        expected.update(sha256=actual_sha, artifact_status="WRITTEN")
        if not _exact(receipt, expected):
            raise MarketEligibilityError("PUBLICATION_RECEIPT_MISMATCH")
        return view
    except MarketEligibilityError:
        raise
    except (OSError, EOFError, ValueError, RuntimeError) as exc:
        raise MarketEligibilityError("PUBLICATION_SOURCE_UNREADABLE") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--board-sha256", required=True)
    parser.add_argument("--board-definition", required=True)
    parser.add_argument("--source-session", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--risk-envelope", type=Path)
    group.add_argument("--risk-unavailable", action="store_true")
    parser.add_argument("--envelope-sha256")
    parser.add_argument("--decision-at", required=True)
    parser.add_argument("--valid-until", required=True)
    args = parser.parse_args(argv)
    if args.risk_envelope and not args.envelope_sha256:
        parser.error("--risk-envelope requires --envelope-sha256")
    if args.risk_unavailable and args.envelope_sha256:
        parser.error("--risk-unavailable cannot carry --envelope-sha256")
    try:
        board = _read(args.board)
        envelope = _read(args.risk_envelope) if args.risk_envelope else None
        result = compose_market_eligibility(
            board, envelope, expected_board_sha256=args.board_sha256,
            expected_board_definition=args.board_definition,
            expected_source_session=args.source_session,
            expected_envelope_sha256=args.envelope_sha256,
            decision_at=args.decision_at, valid_until=args.valid_until,
        )
    except (OSError, MarketEligibilityError) as exc:
        code = str(exc) if isinstance(exc, MarketEligibilityError) else "SOURCE_READ_FAILED"
        print(json.dumps({"status": "REFUSED", "reason": code}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if result["source_state"] == "AVAILABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
