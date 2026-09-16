#!/usr/bin/env python3
"""Produce the research-only, outcome-blind RPH-2 Multi-Speed State Frame."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.research.rotation_persistence.contracts import ContractError, atomic_write_json
from scripts.research.rotation_persistence.multi_speed_state import build_result
from scripts.research.rotation_persistence.sector_control import load_price_panel
from scripts.research.run_sector_control_rph1 import _iso_clock, validate_output_dir

OUTPUT_FILENAME = "result.json"


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
        result = build_result(panel, receipt, produced_at=produced_at)
        atomic_write_json(out_dir / OUTPUT_FILENAME, result)
    except (ContractError, OSError, ValueError) as exc:
        print(f"rotation-persistence-multi-speed-rph2: ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"rotation-persistence-multi-speed-rph2: wrote {out_dir / OUTPUT_FILENAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
