"""Write site/data/capital_policy_projection.json (B-F09-6b, MO-PAID-067).

Thin builder: project() then atomic replace. Never writes data/.

Usage:
    python -m scripts.build_capital_policy_projection
    python -m scripts.build_capital_policy_projection --root /path/to/repo
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from engine.capital_policy_projection import project  # noqa: E402

ARTIFACT_BUDGET_BYTES = 32_768


def _temp_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def render(root: Path) -> Path:
    """Serialize the projection atomically under site/data/."""
    root = root.resolve()
    payload = project()
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    encoded = text.encode("utf-8")
    if len(encoded) > ARTIFACT_BUDGET_BYTES:
        raise RuntimeError(
            f"artifact over budget: {len(encoded)} > {ARTIFACT_BUDGET_BYTES}"
        )
    dest = root / "site" / "data" / "capital_policy_projection.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_sibling(dest)
    try:
        temp.write_bytes(encoded)
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_REPO_ROOT)
    args = parser.parse_args(argv)
    try:
        path = render(args.root)
    except Exception as exc:  # noqa: BLE001 — named non-zero for the shared render
        print(
            f"::error title=capital_policy_projection::build failed "
            f"({type(exc).__name__}: {exc})",
            flush=True,
        )
        return 1
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
