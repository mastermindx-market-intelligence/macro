#!/usr/bin/env python3
"""Project committed native registration facts; never enroll or admit a realm."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.provider_native_capability_source import (  # noqa: E402
    NativeSourceError, current_registration_source,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        source = current_registration_source()
        # The source envelope preserves the exact current/predecessor binding
        # for the incumbent qualified source owner. A list alone loses it for
        # the empty registry. This envelope grants no authentication/admission.
        result = {
            "repository_commit": source.repository_commit,
            "previous_repository_commit": source.previous_repository_commit,
            "material_source_digest": source.material_source_digest,
            "registrations": source.registrations,
        }
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         indent=2 if args.pretty else None,
                         separators=None if args.pretty else (",", ":")))
    except NativeSourceError as exc:
        print(f"provider_native_source refused: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("provider_native_source refused: SOURCE_UNAVAILABLE", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
