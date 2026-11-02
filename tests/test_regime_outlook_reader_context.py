"""E3: the rates_command lobe carries regime_outlook verbatim (deep copy) from
world_state.rates_command.regime_outlook when present and well-formed; nothing
changes otherwise. In-process only — builds a tmp repo root via tmp_path,
never reads committed data/.
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.neuralweb.mastermind_context import _summarize_rates_command
from engine.neuralweb._law import assert_no_authority


RC_BASE: dict = {
    "asof": "2026-09-30",
    "net_state": "balanced",
    "state_label_en": "Balanced",
    "state_label_zh": "平衡",
    "hawk_score": 1,
    "ease_score": 1,
    "stance_en": "hold",
    "stance_zh": "观望",
    "implied_m12": 3.6,
    "policy_rate": 3.88,
    "path_plain_en": "p",
    "path_plain_zh": "q",
    "futures_plain_en": "x",
    "futures_plain_zh": "y",
    "display_only": True,
    "authority": False,
}

PROJECTION: dict = {
    "schema_version": "regime_outlook.v1",
    "scope": "US",
    "analysis_cutoff": "2026-09-30T09:43:58.059037+00:00",
    "built_at": "2026-10-01T02:00:00+00:00",
    "mapping_version": "VERDICT_MAPPING_V2",
    "mapping_sha256": "deadbeef" * 8,
    "inputs": {"daily_run_id": "x", "parents": []},
    "evidence_clock_range": {
        "oldest": "2026-09-25",
        "newest": "2026-09-30",
        "by_clock_semantics": {"owner_snapshot_date": 2},
    },
    "families": ["rates"],
    "evidence": [{"evidence_id": "core_pce", "asof": "2026-09-30"}],
    "conditional_paths": [
        {
            "path_id": "orderly_disinflation",
            "family": "rates",
            "conditions": "core PCE <2.5% AND 10y-2y >= 0",
            "family_readings": [
                {"evidence_family_id": "core_pce", "reading": "fits"},
                {"evidence_family_id": "treasury_curve", "reading": "does_not_fit"},
                {"evidence_family_id": "labour", "reading": "fits"},
                {"evidence_family_id": "credit_and_funding", "reading": "mixed"},
            ],
            "watch": [],
        },
        {
            "path_id": "growth_deterioration",
            "family": "rates",
            "conditions": "claims > 300k AND ISM < 47",
            "family_readings": [
                {"evidence_family_id": "treasury_curve", "reading": "does_not_fit"},
                {"evidence_family_id": "labour", "reading": "unknown"},
            ],
            "watch": [],
        },
    ],
    "baseline": {"path_id": "orderly_disinflation", "score": 0},
    "changes": [],
    "historical_comparisons": [],
    "forecast_distributions": [],
    "conditional_exposures": [],
    "authority": {
        "may_rank": False,
        "may_gate": False,
        "may_size": False,
        "may_trade": False,
        "may_forecast": False,
        "may_escalate": False,
    },
    "tier": "display_research",
    "notes": [],
}


def _make_root(tmp_path: Path, rc: dict) -> Path:
    root = tmp_path / "repo"
    (root / "data" / "neuralweb").mkdir(parents=True, exist_ok=True)
    (root / "data" / "neuralweb" / "world_state.json").write_text(
        json.dumps({"rates_command": rc}), encoding="utf-8"
    )
    return root


def test_projection_carried_verbatim(tmp_path):
    root = _make_root(tmp_path, {**RC_BASE, "regime_outlook": PROJECTION})
    lobe, gap = _summarize_rates_command(root)
    assert gap is None
    assert lobe["regime_outlook"] == PROJECTION
    assert json.dumps(lobe["regime_outlook"], sort_keys=True) == json.dumps(PROJECTION, sort_keys=True)
    assert lobe["regime_outlook_source"] == "world_state.rates_command.regime_outlook"


def test_deep_copy_independence(tmp_path):
    root = _make_root(tmp_path, {**RC_BASE, "regime_outlook": PROJECTION})
    lobe, _ = _summarize_rates_command(root)
    lobe["regime_outlook"]["conditional_paths"][0]["path_id"] = "MUTATED"
    lobe2, _ = _summarize_rates_command(root)
    assert lobe2["regime_outlook"] == PROJECTION
    assert lobe2["regime_outlook"]["conditional_paths"][0]["path_id"] == "orderly_disinflation"


def test_existing_keys_unchanged_with_and_without_projection(tmp_path):
    a, ga = _summarize_rates_command(_make_root(tmp_path, RC_BASE))
    b, gb = _summarize_rates_command(_make_root(tmp_path, {**RC_BASE, "regime_outlook": PROJECTION}))
    assert ga is None and gb is None
    assert {k: b[k] for k in a} == a
    assert set(b) - set(a) == {"regime_outlook", "regime_outlook_source"}


def test_absent_projection_adds_no_key(tmp_path):
    a, gap = _summarize_rates_command(_make_root(tmp_path, RC_BASE))
    assert gap is None
    assert "regime_outlook" not in a
    assert "regime_outlook_source" not in a


def test_malformed_projection_adds_no_key(tmp_path):
    a, _ = _summarize_rates_command(_make_root(tmp_path, RC_BASE))
    for ro in (None, [], "x", {}, {"schema_version": "regime_outlook.v0"}, {"scope": "US"}):
        lobe, gap = _summarize_rates_command(_make_root(tmp_path, {**RC_BASE, "regime_outlook": ro}))
        assert lobe == a
        assert gap is None
        assert "regime_outlook" not in lobe
        assert "regime_outlook_source" not in lobe


def test_gap_notes_unchanged(tmp_path):
    root_no_ws = tmp_path / "no_ws"
    root_no_ws.mkdir()
    lobe, gap = _summarize_rates_command(root_no_ws)
    assert lobe == {}
    assert gap == "data/neuralweb/world_state.json absent or unreadable"

    root_empty = tmp_path / "empty"
    (root_empty / "data" / "neuralweb").mkdir(parents=True)
    (root_empty / "data" / "neuralweb" / "world_state.json").write_text("{}", encoding="utf-8")
    lobe, gap = _summarize_rates_command(root_empty)
    assert lobe == {}
    assert gap == "world_state.rates_command absent (pre-rates-command build)"


def test_authority_law_holds(tmp_path):
    root = _make_root(tmp_path, {**RC_BASE, "regime_outlook": PROJECTION})
    b, gap = _summarize_rates_command(root)
    assert gap is None
    assert assert_no_authority(b) == []
    assert b["is_context_only"] is True
    assert b["display_only"] is True
    assert b["authority"] is False
    assert b["honesty_note"] == "context only — measured rates data, not a trade signal or forecast"
    assert all(v is False for v in b["regime_outlook"]["authority"].values())


def test_analysis_cutoff_verbatim_and_built_at_not_promoted(tmp_path):
    root = _make_root(tmp_path, {**RC_BASE, "regime_outlook": PROJECTION})
    b, _ = _summarize_rates_command(root)
    assert b["regime_outlook"]["analysis_cutoff"] == "2026-09-30T09:43:58.059037+00:00"
    assert b["regime_outlook"]["built_at"] == "2026-10-01T02:00:00+00:00"
    assert b["asof"] == "2026-09-30"
    assert set(b["regime_outlook"]) == set(PROJECTION)


def test_no_derived_numbers(tmp_path):
    root = _make_root(tmp_path, {**RC_BASE, "regime_outlook": PROJECTION})
    b, _ = _summarize_rates_command(root)
    assert set(b["regime_outlook"]) == set(PROJECTION)
    assert b["regime_outlook"]["conditional_paths"] == PROJECTION["conditional_paths"]