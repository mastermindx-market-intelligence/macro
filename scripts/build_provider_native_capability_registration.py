#!/usr/bin/env python3
"""Emit current secret-free native provider-capability registration facts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.provider_native_capabilities import (  # noqa: E402
    ProviderNativeCapabilityError,
    canonical_json,
    current_registration_facts,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit current mastermind.provider_native_capability_registration/v1 facts",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="indent the already-canonical secret-free facts for operator reading",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        facts = list(current_registration_facts(repo_root=_ROOT))
        sys.stdout.write(canonical_json(facts, pretty=args.pretty))
    except ProviderNativeCapabilityError as exc:
        print(f"provider_native_capability refused: {exc}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - never expose private/source exception text
        print("provider_native_capability refused: INTERNAL_PROJECTION_ERROR", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
