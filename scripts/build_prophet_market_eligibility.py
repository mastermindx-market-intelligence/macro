#!/usr/bin/env python3
"""Qualify a GD-6A shadow sidecar from exact owner-selected files; stdout only.

No default source paths, publication, scheduler, forward ledger or live switch.
Expected hashes, session and cutoff are independent owner inputs. In production,
reuse build_prophet's frozen source-board receipt rather than read a racing board
again. This CLI is a qualification entry point, not a registered nightly writer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from engine.prophet_market_eligibility import (  # noqa: E402
    MAX_INPUT_BYTES, MarketEligibilityError, compose_market_eligibility,
)


def _read(path: Path) -> bytes:
    # No interpretation of missing/unreadable files as an observed empty source.
    if path.is_symlink():
        raise MarketEligibilityError("SYMLINKED_SOURCE_REFUSED")
    with path.open("rb") as handle:
        raw = handle.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise MarketEligibilityError("SOURCE_SIZE_LIMIT")
    return raw


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
