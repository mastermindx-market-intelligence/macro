"""Build the Capital Structure state bundle over the verified generation.

This writer is offline and fail-closed.  It verifies the event compiler's
telemetry-last generation receipt, requires an ingestion health horizon bound to
that same generation, requires the SERVED ``projection.json`` to bind it too, and
then publishes ONE ``state_bundle.json`` holding one ``CapitalState`` per covered
issuer -- every state bound to the same three input generations -- or nothing at
all.  The replacement is atomic and staged in the target directory, so a refusal
or a hard stop leaves the last good bundle byte-identical.

It never reads raw SEC objects, never performs network I/O and never widens a
frozen contract: the states are built by
``engine.capital_structure.state_bundle`` through the contract classes, and the
registration family is integrated by the same library function the reader uses.

Usage:
    python -m scripts.build_capital_structure_state
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.capital_structure.projection import (  # noqa: E402
    validate_projection_bundle,
)
from engine.capital_structure.registration_integration import _iso_z  # noqa: E402
from engine.capital_structure.rule_applicability import (  # noqa: E402
    load_rule_applicability_pack,
)
from engine.capital_structure.source_ledger_io import (  # noqa: E402
    read_source_ledger,
    source_ledger_path,
)
from engine.capital_structure.state_bundle import (  # noqa: E402
    build_state_bundle,
    validate_state_bundle,
)
from engine.capital_structure.verified_projection_generation import (  # noqa: E402
    read_verified_projection_generation,
)
from scripts.build_capital_structure_projection import (  # noqa: E402
    _atomic_write_one,
    _data_root,
    _now_iso,
    _read_bound_health,
)

STATE_BUNDLE_FILENAME = "state_bundle.json"
SERVED_PROJECTION_FILENAME = "projection.json"


def _read_served_projection(root: Path) -> tuple[dict[str, Any], str]:
    """The served projection the state generation must bind, plus its byte digest.

    The digest is taken over the EXACT bytes read, so the ``event_projection``
    binding names the artifact the publisher actually served.  Every refusal here
    names "served projection": a state bundle may never be published over a
    projection that is absent, unreadable or invalid.
    """
    path = root / SERVED_PROJECTION_FILENAME
    if not path.exists():
        raise ValueError("served projection is required")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"served projection is unreadable: {exc}") from exc
    try:
        projection = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"served projection is invalid: {exc}") from exc
    if not isinstance(projection, Mapping):
        raise ValueError("served projection is invalid: root must be an object")
    try:
        validate_projection_bundle(dict(projection))
    except ValueError as exc:
        raise ValueError(f"served projection is invalid: {exc}") from exc
    return dict(projection), hashlib.sha256(raw).hexdigest()


def build_from_disk(
    *,
    root: Path | None = None,
    out_path: Path | None = None,
    rule_pack_path: Path | None = None,
    as_of: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Verify the generation and publish one whole state bundle, or nothing."""
    root = Path(root) if root is not None else _data_root()
    target = Path(out_path) if out_path is not None else (root / STATE_BUNDLE_FILENAME)

    generation = read_verified_projection_generation(root)
    telemetry = generation.telemetry
    health = _read_bound_health(root, telemetry)
    if not telemetry.get("generation_id"):
        raise ValueError("no verified capital-structure generation")
    projection, projection_sha256 = _read_served_projection(root)
    pack = load_rule_applicability_pack(
        Path(rule_pack_path) if rule_pack_path is not None else None
    )
    manifests = read_source_ledger(source_ledger_path(root))
    cutoff = as_of or _iso_z(telemetry.get("as_of"), "telemetry.as_of")
    produced = generated_at or _now_iso()

    bundle = build_state_bundle(
        generation=generation,
        projection=projection,
        health=health,
        rule_pack=pack,
        as_of=cutoff,
        generated_at=produced,
        projection_sha256=projection_sha256,
        source_manifests=manifests,
    )
    validate_state_bundle(bundle)
    payload = (
        json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    _atomic_write_one(payload, target)
    return {
        "status": bundle["coverage"]["families"]["registration"]["support"],
        "generation_id": bundle["generation_id"],
        "as_of": bundle["as_of"],
        "issuers": bundle["coverage"]["issuer_count"],
        "evidence_entries": len(bundle["evidence_index"]),
        "out_path": str(target),
        "byte_length": len(payload),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--out-path", type=Path, default=None)
    parser.add_argument("--rule-pack-path", type=Path, default=None)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args(argv)
    try:
        summary = build_from_disk(
            root=args.root,
            out_path=args.out_path,
            rule_pack_path=args.rule_pack_path,
            as_of=args.as_of,
            generated_at=args.generated_at,
        )
    except ValueError as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
