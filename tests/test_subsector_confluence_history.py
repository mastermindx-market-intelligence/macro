from __future__ import annotations

import json
from pathlib import Path

from engine import subsector_confluence_history as H


def _group(key: str, cls: str, state: str, *, side: str = "neutral", tier: str | None = None):
    return {
        "key": key,
        "label": key.title(),
        "sector": "Technology",
        "class": cls,
        "n_members": 3,
        "n_priced": 3,
        "reliability": "high",
        "entry": {
            "tier": tier,
            "weight": 0.9 if tier else 0.0,
            "ticks": 1 if tier else None,
            "fresh_bars": 1 if tier else None,
            "buyable": bool(tier),
            "reason": "test",
        },
        "regime": {
            "state": state,
            "side": side,
            "action": "test action",
            "rs_60d": 12.0,
        },
        "members": [{"ticker": "AAA"}, {"ticker": "BBB"}, {"ticker": "CCC"}],
    }


def _payload():
    return {
        "ok": True,
        "universe": "sp500_subsectors",
        "as_of": "2026-09-18",
        "subsectors": [
            _group("semiconductors", "entry_now", "EXTENDED", side="avoid", tier="T1"),
            _group("software", "neutral", "NEUTRAL"),
        ],
    }


def test_snapshot_is_first_seen_immutable_and_idempotent(tmp_path: Path):
    p = _payload()
    assert H.snapshot(p, "subsectors", root=tmp_path) == 2

    # A same-session recompute is not allowed to rewrite what users originally saw.
    p["subsectors"][0]["label"] = "REWRITTEN"
    p["subsectors"][0]["regime"]["state"] = "BUY"
    assert H.snapshot(p, "subsectors", root=tmp_path) == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl")
        .read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 2
    semi = next(row for row in rows if row["key"] == "semiconductors")
    assert semi["label"] == "Semiconductors"
    assert semi["regime_state"] == "EXTENDED"
    assert semi["entry_condition"] == "stretched"
    assert semi["members"] == ["AAA", "BBB", "CCC"]


def test_public_projection_reconstructs_daily_recommendations_without_members(tmp_path: Path):
    assert H.snapshot(_payload(), "subsectors", root=tmp_path) == 2
    out = H.public_projection(today="2026-09-18", root=tmp_path)

    assert out["schema"] == H.PROJECTION_SCHEMA
    assert out["history_start"] == "2026-09-18"
    assert out["pit_only_since"] == "2026-09-18"
    assert out["accuracy"]["status"] == "accruing"

    day = out["days"][0]
    desk = day["desks"]["subsectors"]
    assert desk["counts"]["entry_now"] == 1
    assert desk["counts"]["neutral"] == 1
    rec = desk["recommendations"][0]
    assert rec["key"] == "semiconductors"
    assert rec["entry_tier"] == "T1"
    assert rec["entry_condition"] == "stretched"
    assert "members" not in rec


def test_accuracy_summary_separates_extended_from_other_fresh_entries():
    rows = [
        {"fwd_rel": 0.10, "entry_condition": "stretched"},
        {"fwd_rel": -0.04, "entry_condition": "stretched"},
        {"fwd_rel": 0.03, "entry_condition": "clean"},
    ]
    assert H._summary(rows)["n"] == 3
    ext = H._summary([r for r in rows if r["entry_condition"] == "stretched"])
    clean = H._summary([r for r in rows if r["entry_condition"] != "stretched"])
    assert ext == {"n": 2, "mean_fwd_rel": 0.03, "hit_rate": 0.5}
    assert clean == {"n": 1, "mean_fwd_rel": 0.03, "hit_rate": 1.0}


def test_unknown_or_degraded_desk_never_appends(tmp_path: Path):
    assert H.snapshot({"ok": False}, "subsectors", root=tmp_path) == 0
    assert H.snapshot(_payload(), "unknown", root=tmp_path) == 0
    assert not (tmp_path / "data/subsector_rotation/confluence_snapshots.jsonl").exists()
