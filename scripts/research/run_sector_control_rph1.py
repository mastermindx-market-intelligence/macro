#!/usr/bin/env python3
"""Execute the preregistered research-only RPH-1 daily sector control."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.research.rotation_persistence.contracts import ContractError, atomic_write_json
from scripts.research.rotation_persistence.report import atomic_write_text
from scripts.research.rotation_persistence.sector_control import (
    build_result,
    load_price_panel,
    render_markdown,
)

OUTPUT_FILENAMES = ("result.json", "report.md")
_FORBIDDEN_OWNER_ROOTS = ("data", "site", "engine", "config")


def validate_output_dir(out_dir: Path, *, repo_root: Path | None = None) -> Path:
    root = (
        Path(repo_root).expanduser().resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    requested = Path(out_dir).expanduser()
    candidate = (root / requested if not requested.is_absolute() else requested).resolve()
    if candidate == root:
        raise ContractError("research-safe output cannot be the repository root")
    for owner in _FORBIDDEN_OWNER_ROOTS:
        try:
            candidate.relative_to((root / owner).resolve())
        except ValueError:
            continue
        raise ContractError(f"research-safe output cannot be inside {owner}/")
    try:
        candidate.relative_to((root / "research").resolve())
    except ValueError as exc:
        raise ContractError("output directory must be research-safe under research/") from exc
    if candidate.exists() and not candidate.is_dir():
        raise ContractError(f"output path exists and is not a directory: {candidate}")
    return candidate


def _iso_clock(value: str) -> str:
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
    parser.add_argument("--data-dir", type=Path, default=Path("data/yahoo"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--produced-at", required=True)
    return parser


def main(argv: list[str] | None = None, *, repo_root: Path | None = None) -> int:
    args = _parser().parse_args(argv)
    root = (
        Path(repo_root).expanduser().resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    try:
        produced_at = _iso_clock(args.produced_at)
        out_dir = validate_output_dir(args.output_dir, repo_root=root)
        panel, receipt = load_price_panel(args.data_dir, repo_root=root)
        result = build_result(panel, receipt, produced_at)
        markdown = render_markdown(result)
        atomic_write_json(out_dir / OUTPUT_FILENAMES[0], result)
        atomic_write_text(out_dir / OUTPUT_FILENAMES[1], markdown)
    except (ContractError, OSError, ValueError) as exc:
        print(f"rotation-persistence-sector-control-rph1: ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        "rotation-persistence-sector-control-rph1: wrote "
        f"{out_dir / OUTPUT_FILENAMES[0]} and {out_dir / OUTPUT_FILENAMES[1]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
