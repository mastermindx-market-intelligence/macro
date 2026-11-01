"""Build the Capital Structure state change ledger over two published generations.

This writer is offline and fail-closed.  It reads the CURRENT published
``state_bundle.json``, requires it to pass the full state-bundle validation, and
derives ONE ``state_changes.json`` between it and the retained previous
generation (``--previous``), or a baseline change set when no previous bundle is
readable.  The replacement is atomic and staged in the target directory, so a
refusal leaves the last good ledger byte-identical.

It never re-compiles a state, never reads raw SEC objects, never performs
network I/O and never widens a frozen contract: the change set is derived by
``engine.capital_structure.state_changes.diff_state_generations`` alone.  The
nightly captures the previous bundle BEFORE the state step overwrites it (the
U2-3 monitor lane owns that step ordering); a missing or unreadable previous
bundle is the stated baseline, never a synthesized diff.

Usage:
    python -m scripts.build_capital_structure_state_changes --root <dir> \
        --previous <path|absent> [--previous-inputs <path|absent>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.capital_structure.state_bundle import (  # noqa: E402
    validate_state_bundle,
)
from engine.capital_structure.state_changes import (  # noqa: E402
    STATE_CHANGES_FILENAME,
    diff_state_generations,
)
from engine.capital_structure.scenario_inputs import (  # noqa: E402
    CAPACITY_INPUTS_FILENAME,
)
from scripts.build_capital_structure_projection import (  # noqa: E402
    _atomic_write_one,
    _data_root,
    _now_iso,
)

STATE_BUNDLE_FILENAME = "state_bundle.json"


def _read_json(path: Path) -> Any:
    """Parsed JSON or ``None`` — absence and unreadability are typed, not raised."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _read_previous(previous_path: Path | None) -> dict[str, Any] | None:
    """The retained previous bundle, or ``None`` — absent or unreadable is the
    stated baseline (SPEC_U2 §1.1), never a retry and never a refusal."""
    if previous_path is None:
        return None
    doc = _read_json(previous_path)
    return dict(doc) if isinstance(doc, dict) else None


def build_from_disk(
    *,
    root: Path | None = None,
    previous: Path | None = None,
    previous_inputs: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Verify the current generation and publish one change ledger, or nothing."""
    root = Path(root) if root is not None else _data_root()
    target = root / STATE_CHANGES_FILENAME

    current = _read_json(root / STATE_BUNDLE_FILENAME)
    if not isinstance(current, dict):
        raise ValueError("current state bundle is required")
    try:
        validate_state_bundle(current)
    except ValueError as exc:
        raise ValueError(f"current state bundle is invalid: {exc}") from exc

    previous_bundle = _read_previous(previous)
    inputs_current = _read_json(root / CAPACITY_INPUTS_FILENAME)
    inputs_current = dict(inputs_current) if isinstance(inputs_current, dict) else None
    inputs_previous = _read_json(previous_inputs) if previous_inputs is not None else None
    inputs_previous = dict(inputs_previous) if isinstance(inputs_previous, dict) else None

    changeset = diff_state_generations(
        previous_bundle,
        current,
        inputs_previous=inputs_previous,
        inputs_current=inputs_current,
        generated_at=generated_at or _now_iso(),
    )
    payload = (
        json.dumps(changeset.as_record(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    _atomic_write_one(payload, target)
    return {
        "status": "baseline" if changeset.baseline else "diffed",
        "from_generation_id": changeset.from_generation_id,
        "to_generation_id": changeset.to_generation_id,
        "baseline": changeset.baseline,
        "changes": len(changeset.changes),
        "counts": changeset.counts,
        "out_path": str(target),
        "byte_length": len(payload),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--previous", type=Path, default=None)
    parser.add_argument("--previous-inputs", type=Path, default=None)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args(argv)
    try:
        summary = build_from_disk(
            root=args.root,
            previous=args.previous,
            previous_inputs=args.previous_inputs,
            generated_at=args.generated_at,
        )
    except ValueError as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
