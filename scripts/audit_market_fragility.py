"""Read-only source audit for market fragility; no collection, ledger or gate writes.

Run against the canonical daily SPX parquet or an explicitly retained snapshot.
An --as-of argument is a diagnostic cutoff, NOT proof of historical availability.
The existing scripts.validate_gex owner retains promotion decisions.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import market_fragility  # noqa: E402
from lib import config  # noqa: E402

_MAX_INPUT_BYTES = 64 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(
    path: Path,
    *,
    now: datetime | None = None,
    window_sessions: int = 20,
    run_existing_diagnostic: bool = False,
) -> dict:
    """Return bounded evidence; do not write or promote anything."""
    now = now or datetime.now(timezone.utc)
    snapshot = {"name": path.name, "sha256": None, "bytes": None, "rows": 0, "read_error": None}
    frame = None
    try:
        size = path.stat().st_size
        if size > _MAX_INPUT_BYTES:
            snapshot["read_error"] = "source_bound_exceeded"
        else:
            # Parse and hash the exact same bounded byte snapshot. Separate path
            # reads can otherwise attribute frame B to digest A during a rewrite.
            with path.open("rb") as handle:
                raw = handle.read(_MAX_INPUT_BYTES + 1)
            if len(raw) > _MAX_INPUT_BYTES:
                snapshot["read_error"] = "source_bound_exceeded"
            else:
                frame = pd.read_parquet(BytesIO(raw))
                snapshot.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), rows=len(frame))
    except (OSError, ValueError, ImportError, TypeError) as exc:
        snapshot["read_error"] = type(exc).__name__
        frame = None
    observation = market_fragility.observe(frame, now=now, window_sessions=window_sessions)
    if snapshot["read_error"]:
        observation["quality"]["reasons"] = ["source_read_error", snapshot["read_error"]]
    available = 0
    if frame is not None and "available_at" in frame and frame.columns.is_unique:
        available = sum(market_fragility._clock(v) is not None for v in frame["available_at"])
    diagnostic = None
    if run_existing_diagnostic and frame is not None:
        # evaluate() returns strings. main() is deliberately NOT invoked: it owns
        # reports/gex-validation.md and the existing scoring gate's publication.
        from scripts.validate_gex import evaluate
        diagnostic = evaluate("SPX", frame.copy(deep=True), store_label="cboe")
    return {
        "schema": "market_fragility_audit/v1",
        "audit_kind": "snapshot_diagnostic_not_pit_backtest",
        "source_snapshot": snapshot,
        "implementation_sha256": _sha256(Path(market_fragility.__file__)),
        "observation": observation,
        "research_readiness": {
            "availability_clock_rows": available,
            "availability_clock_fraction": available / len(frame) if frame is not None and len(frame) else None,
            "historical_vintages_verified": False,
            "predictive_validation": "NOT_ESTABLISHED",
            "promotion_authorized": False,
            "existing_validation_owner": "scripts/validate_gex.py",
            "existing_diagnostic": diagnostic,
            "diagnostic_is_promotion": False,
            "remaining_proof": [
                "immutable_available_at_vintages_and_source_revision_lineage",
                "pre_registered_chronological_holdout_and_overlap_purge",
                "incremental_value_over_volatility_baseline_with_episode_honest_uncertainty",
                "prospective_consumer_and_policy_specific_admission",
            ],
        },
    }


def _as_of(text: str) -> datetime:
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("timezone is required")
        return value.astimezone(timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--as-of requires an ISO timestamp with timezone") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="canonical SPX daily parquet or retained snapshot")
    parser.add_argument("--as-of", type=_as_of, help="diagnostic clock, never historical-vintage proof")
    parser.add_argument("--window-sessions", type=int, default=20)
    parser.add_argument("--output", type=Path, help="new audit artifact (existing files are never overwritten)")
    parser.add_argument("--require-current", action="store_true", help="exit 2 when current observation is unusable")
    parser.add_argument("--run-existing-gex-diagnostic", action="store_true", help="read-only existing validator; never writes its gate")
    args = parser.parse_args(argv)
    if not 1 <= args.window_sessions <= 252:
        parser.error("--window-sessions must be in [1, 252]")
    path = args.input or config.data_dir() / "cboe" / "gex_SPX.parquet"
    report = audit(path, now=args.as_of, window_sessions=args.window_sessions,
                   run_existing_diagnostic=args.run_existing_gex_diagnostic)
    encoded = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    print(encoded, end="")
    return 2 if args.require_current and not report["observation"]["current"]["usable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
