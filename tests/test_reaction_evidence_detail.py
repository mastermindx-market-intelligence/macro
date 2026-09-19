"""Packet D tests for truthful historical reaction evidence detail.

These tests deliberately exercise the existing producer and its real builder enrichment
path.  They do not touch the shared dashboard renderer.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from engine.release_market_context import get_reaction_sensitivity


def _cell(
    bucket: str,
    outcome: str,
    *,
    release: str = "cpi",
    regime: str | None = None,
    n=20,
    mean=3.2,
    ci_lo=-1.0,
    ci_hi=7.0,
) -> dict:
    row = {
        "release": release,
        "bucket": bucket,
        "outcome": outcome,
        "horizon": "h1",
        "era": "2021plus",
        "regime": regime,
        "n": n,
        "mean": mean,
        "median": mean,
    }
    if ci_lo is not _ABSENT:
        row["ci_lo"] = ci_lo
    if ci_hi is not _ABSENT:
        row["ci_hi"] = ci_hi
    return row


_ABSENT = object()


def _base_cells() -> list[dict]:
    return [
        _cell("hot", "dgs10_bp", n=20, mean=3.2, ci_lo=-0.85, ci_hi=8.3),
        _cell("cold", "dgs10_bp", n=22, mean=-4.1, ci_lo=-9.0, ci_hi=0.5),
        _cell("hot", "spy_pct", n=21, mean=-0.4, ci_lo=-1.28, ci_hi=0.29),
        _cell("cold", "spy_pct", n=23, mean=0.55, ci_lo=-0.1, ci_hi=1.4),
    ]


def _write_playbook(tmp_path: Path, cells: list[dict]) -> Path:
    path = tmp_path / "research" / "release_playbook" / "results" / "playbook_v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cells, allow_nan=True), encoding="utf-8")
    return path


def _evidence_cell(result: dict, legacy_field: str) -> dict:
    return result["evidence"]["cells"][legacy_field]


def test_same_mean_different_n_and_interval_remain_distinguishable(tmp_path: Path):
    small = _base_cells()
    small[0].update(n=8, mean=3.2, ci_lo=-12.0, ci_hi=18.0)
    large = _base_cells()
    large[0].update(n=900, mean=3.2, ci_lo=3.0, ci_hi=3.4)

    small_result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path / "small", small)
    )
    large_result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path / "large", large)
    )

    assert small_result["dgs10_h1_hot_bp"] == large_result["dgs10_h1_hot_bp"] == 3.2
    small_detail = _evidence_cell(small_result, "dgs10_h1_hot_bp")
    large_detail = _evidence_cell(large_result, "dgs10_h1_hot_bp")
    assert small_detail["n"] == 8
    assert large_detail["n"] == 900
    assert small_detail["interval"] != large_detail["interval"]


def test_mixed_regime_and_base_cells_never_borrow_metadata(tmp_path: Path):
    cells = _base_cells() + [
        _cell(
            "hot", "dgs10_bp", regime="Q1", n=11, mean=7.77,
            ci_lo=2.0, ci_hi=12.0,
        )
    ]
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, cells), current_regime="Q1"
    )

    conditioned = _evidence_cell(result, "dgs10_h1_hot_bp")
    fallback = _evidence_cell(result, "dgs10_h1_cold_bp")
    assert result["dgs10_h1_hot_bp"] == 7.77
    assert conditioned["regime"] == "Q1"
    assert conditioned["n"] == 11
    assert conditioned["interval"]["lo"] == 2.0
    assert fallback["regime"] is None
    assert fallback["n"] == 22
    assert fallback["interval"]["lo"] == -9.0


def test_missing_interval_stays_absent_not_zero_width(tmp_path: Path):
    cells = _base_cells()
    cells[0] = _cell(
        "hot", "dgs10_bp", n=8, mean=3.2, ci_lo=_ABSENT, ci_hi=_ABSENT
    )
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, cells)
    )
    detail = _evidence_cell(result, "dgs10_h1_hot_bp")
    assert detail["n"] == 8
    assert "interval" not in detail


def test_h1_is_next_session_close_not_one_hour(tmp_path: Path):
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, _base_cells())
    )
    detail = _evidence_cell(result, "dgs10_h1_hot_bp")
    assert detail["horizon"] == "h1"
    assert detail["reference_basis"] == (
        "next_trading_session_close_vs_pre_event_prior_close"
    )
    assert "hour" not in detail["reference_basis"]


def test_cpi_target_is_legacy_index_point_basis_not_official_percent(tmp_path: Path):
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, _base_cells())
    )
    target = result["evidence"]["target"]
    assert target["observed_value"] == "cpi_initial_print_index_point_mom_change"
    assert target["reference_benchmark"] == (
        "prior_period_initial_print_index_point_mom_change"
    )
    assert "pct" not in target["observed_value"]
    assert "percent" not in target["observed_value"]


def test_source_digest_binds_detail_to_exact_playbook_bytes(tmp_path: Path):
    path = _write_playbook(tmp_path, _base_cells())
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    result = get_reaction_sensitivity("cpi_headline", path)
    for detail in result["evidence"]["cells"].values():
        assert detail["source"]["version"] == "playbook_v1"
        assert detail["source"]["sha256"] == expected


def test_duplicate_regime_candidates_fail_safe_to_unique_base(tmp_path: Path):
    cells = _base_cells() + [
        _cell("hot", "dgs10_bp", regime="Q1", n=10, mean=7.0),
        _cell("hot", "dgs10_bp", regime="Q1", n=12, mean=9.0),
    ]
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, cells), current_regime="Q1"
    )
    detail = _evidence_cell(result, "dgs10_h1_hot_bp")
    assert result["dgs10_h1_hot_bp"] == 3.2
    assert detail["regime"] is None
    assert detail["n"] == 20


def test_malformed_metadata_is_omitted_without_hiding_valid_neighbor(tmp_path: Path):
    cells = _base_cells()
    cells[0]["n"] = "20"
    cells[0]["ci_lo"] = 9.0
    cells[0]["ci_hi"] = -9.0
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, cells)
    )

    malformed = _evidence_cell(result, "dgs10_h1_hot_bp")
    neighbor = _evidence_cell(result, "dgs10_h1_cold_bp")
    assert result["dgs10_h1_hot_bp"] == 3.2
    assert "n" not in malformed
    assert "interval" not in malformed
    assert neighbor["n"] == 22
    assert neighbor["interval"]["lo"] == -9.0


def test_nonfinite_conditioned_mean_falls_back_and_nonfinite_interval_is_absent(
    tmp_path: Path,
):
    cells = _base_cells() + [
        _cell(
            "hot", "dgs10_bp", regime="Q1", n=10,
            mean=float("nan"), ci_lo=-1.0, ci_hi=1.0,
        )
    ]
    cells[2]["ci_hi"] = float("inf")
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, cells), current_regime="Q1"
    )

    assert result["dgs10_h1_hot_bp"] == 3.2
    assert _evidence_cell(result, "dgs10_h1_hot_bp")["regime"] is None
    spy_hot = _evidence_cell(result, "spy_h1_hot_pct")
    assert math.isfinite(result["spy_h1_hot_pct"])
    assert "interval" not in spy_hot


def test_untrusted_cell_claims_cannot_relabel_horizon_target_or_regime_knowledge(
    tmp_path: Path,
):
    cells = _base_cells() + [
        {
            **_cell("hot", "dgs10_bp", regime="Q1", n=10, mean=7.0),
            "knowledge_status": "as_observed",
            "horizon_label": "1h",
            "target_unit": "official_mom_pct",
        }
    ]
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, cells), current_regime="Q1"
    )
    detail = _evidence_cell(result, "dgs10_h1_hot_bp")
    assert detail["reference_basis"] == (
        "next_trading_session_close_vs_pre_event_prior_close"
    )
    assert detail["knowledge_status"]["regime_labels"] == (
        "latest_revised_not_as_observed"
    )
    assert result["evidence"]["target"]["observed_value"] == (
        "cpi_initial_print_index_point_mom_change"
    )


def test_legacy_fields_and_missing_family_behavior_are_preserved(tmp_path: Path):
    result = get_reaction_sensitivity(
        "cpi_headline", _write_playbook(tmp_path, _base_cells())
    )
    assert result["dgs10_h1_hot_bp"] == 3.2
    assert result["dgs10_h1_cold_bp"] == -4.1
    assert result["spy_h1_hot_pct"] == -0.4
    assert result["spy_h1_cold_pct"] == 0.55
    assert get_reaction_sensitivity(
        "claims", _write_playbook(tmp_path / "claims", _base_cells())
    ) is None


def test_real_builder_enrichment_carries_reaction_evidence(tmp_path: Path):
    from scripts import build_release_forecast as producer

    _write_playbook(tmp_path, _base_cells())
    regime_path = tmp_path / "data" / "regime" / "latest.json"
    regime_path.parent.mkdir(parents=True, exist_ok=True)
    regime_path.write_text(json.dumps({"quad": "Q1"}), encoding="utf-8")

    item = {
        "release_type": "cpi_headline",
        "release": "cpi",
        "period": "2026-08",
        "release_date": "2026-09-15",
        "projection": {},
        "benchmark_set": {},
        "surprise_skew": {},
    }
    producer._enrich_upcoming_block([item], tmp_path)

    reaction = item["reaction_sensitivity"]
    assert reaction["dgs10_h1_hot_bp"] == 3.2
    assert reaction["evidence"]["schema"] == "reaction_evidence.v1"
    assert reaction["evidence"]["cells"]["dgs10_h1_hot_bp"]["n"] == 20
