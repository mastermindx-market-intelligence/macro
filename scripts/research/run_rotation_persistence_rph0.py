#!/usr/bin/env python3
"""Run the research-only Leadership Persistence RPH-0 study."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Direct script execution places scripts/research on sys.path; add the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.research.rotation_persistence.archive import load_basket_archive
from scripts.research.rotation_persistence.contracts import (
    ContractError,
    atomic_write_json,
)
from scripts.research.rotation_persistence.report import (
    build_result,
    render_markdown,
    validate_output_dir,
)


def _iso_clock(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError("produced_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError("produced_at must include a timezone")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("data/signal_archive/baskets.parquet"),
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--produced-at")
    parser.add_argument("--recent-sessions", type=int, default=20)
    parser.add_argument("--bootstrap-resamples", type=int, default=2_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20_260_910)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        produced_at = _iso_clock(args.produced_at)
        if args.recent_sessions <= 0:
            raise ContractError("recent_sessions must be positive")
        if args.bootstrap_resamples <= 0:
            raise ContractError("bootstrap_resamples must be positive")
        out_dir = validate_output_dir(args.out_dir)
        frames, receipt = load_basket_archive(args.archive)
        result = build_result(
            frames,
            receipt,
            produced_at=produced_at,
            recent_sessions=args.recent_sessions,
            bootstrap_resamples=args.bootstrap_resamples,
            bootstrap_seed=args.bootstrap_seed,
        )
        markdown = render_markdown(result)
        atomic_write_json(out_dir / "result.json", result)
        from scripts.research.rotation_persistence.report import atomic_write_text

        atomic_write_text(out_dir / "report.md", markdown)
    except (ContractError, OSError, ValueError) as exc:
        print(f"rotation-persistence-rph0: ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"rotation-persistence-rph0: wrote {out_dir / 'result.json'} and {out_dir / 'report.md'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
