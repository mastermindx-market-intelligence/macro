#!/usr/bin/env python3
"""Print the current zero-authority HK Opportunities projection as JSON.

Read-only consumer:
  incumbent hk_standouts.json
  + latest hk_discovery_v1 observations
  + frozen hklab_flagship_nogate display-only screen
  -> one machine view model on stdout.

No file is written and no rank, entry, publication, Featured or Brain authority
is created here.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import board_shadow  # noqa: E402
from engine.hk_opportunity_projection import (  # noqa: E402
    ENTRY_OPEN,
    MONITOR,
    PREPARING,
    SCHEMA,
    project_opportunities,
)
from engine.pick_lab.hk import run_book_hk  # noqa: E402
from engine.pick_lab.profile import HK_PROFILE  # noqa: E402
from engine.pick_lab.registry_hk import HK_BY_ID  # noqa: E402
from engine.pick_lab.snapshot import latest_snapshot  # noqa: E402

ATTENTION_ENGINE = "hklab_flagship_nogate"


def _unavailable(reason: str, *, source_asof: dict | None = None) -> dict:
    return {
        "schema": SCHEMA,
        "market": "HK",
        "available": False,
        "reason": reason,
        "source_asof": source_asof or {
            "incumbent": None,
            "discovery": None,
            "attention": None,
        },
        "lanes": {ENTRY_OPEN: [], PREPARING: [], MONITOR: []},
        "diagnostics": {},
    }


def build_projection() -> dict:
    incumbent_path = ROOT / "site" / "factordata" / "hk_standouts.json"
    if not incumbent_path.exists():
        return _unavailable("incumbent_artifact_absent")
    try:
        incumbent = json.loads(incumbent_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _unavailable(f"incumbent_artifact_unreadable:{type(exc).__name__}")

    incumbent_asof = str(incumbent.get("as_of") or "")
    discovery_snapshot = board_shadow.read_discovery_snapshot(
        "HK", "hk_discovery_v1"
    )
    if not isinstance(discovery_snapshot, dict):
        return _unavailable(
            "discovery_owner_unavailable:reader_contract_invalid",
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": None,
                "attention": None,
            },
        )
    discovery_asof = str(discovery_snapshot.get("as_of") or "") or None
    if discovery_snapshot.get("available") is not True:
        owner_reason = str(discovery_snapshot.get("reason") or "unknown")
        return _unavailable(
            "discovery_owner_unavailable:" + owner_reason,
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": discovery_asof,
                "attention": None,
            },
        )
    discovery_rows = discovery_snapshot.get("records")
    if not isinstance(discovery_rows, list):
        return _unavailable(
            "discovery_owner_unavailable:records_contract_invalid",
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": discovery_asof,
                "attention": None,
            },
        )
    if not discovery_asof:
        return _unavailable(
            "discovery_owner_unavailable:asof_missing",
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": None,
                "attention": None,
            },
        )

    snapshot, attention_asof = latest_snapshot(profile=HK_PROFILE)
    if snapshot is None or attention_asof is None:
        return _unavailable(
            "attention_snapshot_absent",
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": discovery_asof,
                "attention": None,
            },
        )
    book = HK_BY_ID.get(ATTENTION_ENGINE)
    if book is None:
        return _unavailable(
            "attention_engine_absent",
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": discovery_asof,
                "attention": str(attention_asof),
            },
        )
    result = run_book_hk(book, snapshot)
    if result.get("disabled_stale"):
        return _unavailable(
            "attention_engine_stale",
            source_asof={
                "incumbent": incumbent_asof or None,
                "discovery": discovery_asof,
                "attention": str(attention_asof),
            },
        )

    owner_context_rows = []
    for context_lane in ("ripening", "ran", "leaders", "watch"):
        for source in incumbent.get(context_lane) or []:
            row = dict(source)
            row["owner_context_lane"] = context_lane
            owner_context_rows.append(row)

    projection = project_opportunities(
        incumbent_asof=incumbent_asof or None,
        discovery_asof=discovery_asof,
        attention_asof=str(attention_asof),
        incumbent_buy=incumbent.get("buy") or [],
        discovery_rows=discovery_rows,
        attention_picks=result.get("picks") or [],
        owner_context_rows=owner_context_rows,
    )
    projection["diagnostics"]["attention_engine"] = ATTENTION_ENGINE
    projection["diagnostics"]["attention_engine_authority"] = "display_only"
    projection["diagnostics"]["attention_engine_n_picks"] = int(
        result.get("n_picks") or 0
    )
    return projection


def main() -> int:
    print(json.dumps(build_projection(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())