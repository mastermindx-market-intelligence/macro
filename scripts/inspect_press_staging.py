"""Read-only replay of Press validation; never a publication approval.

Run with ``python -m scripts.inspect_press_staging``. The report binds every
result to the staged bytes and current config, so saved ``passed`` flags are
not mistaken for current validation. No provider, render, or ledger writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.press import desk_planner, validators
from scripts.run_press import _is_unverified_earnings_story_stage, _paths


def inspect_staging(root: Path) -> dict:
    cfg = desk_planner.load_config(root)
    if not cfg:
        raise ValueError("config/press.yml is missing or unparsable")
    config_path = root / "config" / "press.yml"
    items = []
    for path in sorted(_paths(cfg, root)["staging"].glob("*.json")):
        if path.name.startswith("_"):
            continue
        raw = path.read_bytes()
        item = {"path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(raw).hexdigest()}
        try:
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError("staging record must be an object")
            draft, slot = obj.get("draft"), obj.get("slot")
            item.update(id=obj.get("id"), saved_status=obj.get("status"))
            reasons = []
            if obj.get("status") != "passed":
                reasons.append("saved_status_not_passed")
            if _is_unverified_earnings_story_stage(obj):
                reasons.append("immutable_earnings_approval_required")
            if not isinstance(draft, dict) or not isinstance(slot, dict):
                reasons.append("missing_draft_or_slot")
            else:
                report = validators.validate(draft, slot, cfg, root=root)
                item["validator_report"] = report
                if not report["ok"]:
                    reasons.append("current_validation_failed")
            item.update(validation_current=not reasons, blockers=reasons)
        except (ValueError, TypeError) as exc:
            item.update(validation_current=False, blockers=["malformed_stage"],
                        error=str(exc))
        items.append(item)
    passed = sum(item["validation_current"] for item in items)
    return {
        "schema": "press.staging_inspection.v1",
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "cutover": bool(cfg.get("cutover")),
        "items": items,
        "total": len(items),
        "validation_current": passed,
        "blocked": len(items) - passed,
        "publication_approved": False,
        "source_freshness_verified": False,
        "scope": "Current deterministic validator replay against staged facts and local peers only; "
                 "source freshness, source rights, editorial acceptance, release controls and live "
                 "delivery require their existing owners.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = inspect_staging(args.root.resolve())
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "publication_approved": False}))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["total"] and not report["blocked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
